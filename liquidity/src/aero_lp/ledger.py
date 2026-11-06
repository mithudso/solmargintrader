"""P&L ledger (SQLite, stdlib only).

A *slot* is one strategy line. It keeps its id when a rebalance replaces the NFT, so its P&L runs across
rebalances. Money flows in and out of a slot as `flows` (deposit, topup, withdraw). Gas and rewards are
`events`. Periodic `snapshots` hold the slot's market value and its HODL value: what the deposited token
amounts would be worth now if never deployed.

    P&L         = value_now + withdrawn_usd + rewards_claimed_usd - deposited_usd - gas_usd
    P&L vs HODL = value_now + withdrawn_usd + rewards_claimed_usd - hodl_now - gas_usd

`wallet_balances` records the wallet's token balances over time. The allocator counts a coin as idle only
if its balance has been present for the whole idle window, so a token you just received or are about to
use is left alone.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    slot TEXT PRIMARY KEY,
    pool TEXT NOT NULL,
    pair TEXT NOT NULL,
    token0 TEXT NOT NULL,
    token1 TEXT NOT NULL,
    dec0 INTEGER NOT NULL,
    dec1 INTEGER NOT NULL,
    token_id INTEGER,
    opened_at REAL NOT NULL,
    closed_at REAL,
    experiment TEXT,
    source TEXT NOT NULL DEFAULT 'allocator'
);
CREATE TABLE IF NOT EXISTS flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot TEXT NOT NULL,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,          -- deposit | topup | withdraw
    amount0 REAL NOT NULL,       -- human units
    amount1 REAL NOT NULL,
    usd REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    slot TEXT,
    kind TEXT NOT NULL,          -- rebalance | compound | deploy | withdraw | topup | claim | unwrap | swap | error ...
    gas_usd REAL NOT NULL DEFAULT 0,
    reward_usd REAL NOT NULL DEFAULT 0,
    detail TEXT,
    tx TEXT                      -- JSON list of hashes
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot TEXT NOT NULL,
    ts REAL NOT NULL,
    token_id INTEGER,
    value_usd REAL NOT NULL,
    hodl_usd REAL NOT NULL,
    unclaimed_usd REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    status TEXT NOT NULL,        -- running | graduated
    winner TEXT,
    note TEXT
);
CREATE TABLE IF NOT EXISTS wallet_balances (
    ts REAL NOT NULL,
    token TEXT NOT NULL,
    amount REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_snap ON snapshots(slot, ts);
CREATE INDEX IF NOT EXISTS ix_wb ON wallet_balances(token, ts);
"""


@dataclass
class SlotPnl:
    slot: str
    pair: str
    pool: str
    token_id: int | None
    experiment: str | None
    opened_at: float
    closed_at: float | None
    deposited_usd: float
    withdrawn_usd: float
    rewards_usd: float
    gas_usd: float
    value_usd: float
    hodl_usd: float
    unclaimed_usd: float

    @property
    def pnl_usd(self) -> float:
        return (
            self.value_usd
            + self.unclaimed_usd
            + self.withdrawn_usd
            + self.rewards_usd
            - self.deposited_usd
            - self.gas_usd
        )

    @property
    def pnl_vs_hodl_usd(self) -> float:
        return (
            self.value_usd + self.unclaimed_usd + self.withdrawn_usd + self.rewards_usd - self.hodl_usd - self.gas_usd
        )

    @property
    def apr_realized(self) -> float:
        days = ((self.closed_at or time.time()) - self.opened_at) / 86400
        if days <= 0 or self.deposited_usd <= 0:
            return 0.0
        return self.pnl_usd / self.deposited_usd * 365 / days * 100


class Ledger:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self.db:
            yield self.db

    # ------------------------------------------------------------------ writes

    def open_slot(
        self,
        slot: str,
        pool: str,
        pair: str,
        token0: str,
        token1: str,
        dec0: int,
        dec1: int,
        token_id: int | None,
        experiment: str | None = None,
        source: str = "allocator",
        ts: float | None = None,
    ) -> None:
        with self.tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO slots"
                "(slot,pool,pair,token0,token1,dec0,dec1,token_id,opened_at,experiment,source)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (slot, pool, pair, token0, token1, dec0, dec1, token_id, ts or time.time(), experiment, source),
            )

    def set_token_id(self, slot: str, token_id: int) -> None:
        with self.tx() as db:
            db.execute("UPDATE slots SET token_id=? WHERE slot=?", (token_id, slot))

    def close_slot(self, slot: str, ts: float | None = None) -> None:
        with self.tx() as db:
            db.execute("UPDATE slots SET closed_at=? WHERE slot=? AND closed_at IS NULL", (ts or time.time(), slot))

    def flow(self, slot: str, kind: str, amount0: float, amount1: float, usd: float, ts: float | None = None) -> None:
        if kind not in ("deposit", "topup", "withdraw"):
            raise ValueError(f"unknown flow kind {kind}")
        with self.tx() as db:
            db.execute(
                "INSERT INTO flows(slot,ts,kind,amount0,amount1,usd) VALUES (?,?,?,?,?,?)",
                (slot, ts or time.time(), kind, amount0, amount1, usd),
            )

    def event(
        self,
        kind: str,
        slot: str | None = None,
        gas_usd: float = 0.0,
        reward_usd: float = 0.0,
        detail: str = "",
        tx: list[str] | None = None,
        ts: float | None = None,
    ) -> None:
        with self.tx() as db:
            db.execute(
                "INSERT INTO events(ts,slot,kind,gas_usd,reward_usd,detail,tx) VALUES (?,?,?,?,?,?,?)",
                (ts or time.time(), slot, kind, gas_usd, reward_usd, detail[:2000], json.dumps(tx or [])),
            )

    def snapshot(
        self,
        slot: str,
        token_id: int | None,
        value_usd: float,
        hodl_usd: float,
        unclaimed_usd: float = 0.0,
        ts: float | None = None,
    ) -> None:
        with self.tx() as db:
            db.execute(
                "INSERT INTO snapshots(slot,ts,token_id,value_usd,hodl_usd,unclaimed_usd) VALUES (?,?,?,?,?,?)",
                (slot, ts or time.time(), token_id, value_usd, hodl_usd, unclaimed_usd),
            )

    def wallet_snapshot(self, balances: dict[str, float], ts: float | None = None) -> None:
        t = ts or time.time()
        with self.tx() as db:
            db.executemany(
                "INSERT INTO wallet_balances(ts,token,amount) VALUES (?,?,?)",
                [(t, tok.lower(), amt) for tok, amt in balances.items()],
            )
            db.execute("DELETE FROM wallet_balances WHERE ts < ?", (t - 30 * 86400,))

    def start_experiment(self, exp_id: str, note: str = "", ts: float | None = None) -> None:
        with self.tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO experiments(id,started_at,status,note) VALUES (?,?,?,?)",
                (exp_id, ts or time.time(), "running", note),
            )

    def graduate(self, exp_id: str, winner_slot: str) -> None:
        with self.tx() as db:
            db.execute("UPDATE experiments SET status='graduated', winner=? WHERE id=?", (winner_slot, exp_id))

    # ------------------------------------------------------------------ reads

    def open_slots(self) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM slots WHERE closed_at IS NULL ORDER BY opened_at"))

    def slot_row(self, slot: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM slots WHERE slot=?", (slot,)).fetchone()

    def deposited_amounts(self, slot: str) -> tuple[float, float]:
        """Net token amounts put in (deposits + topups - withdrawals); the basis of the HODL value."""
        row = self.db.execute(
            "SELECT COALESCE(SUM(CASE WHEN kind='withdraw' THEN -amount0 ELSE amount0 END),0),"
            " COALESCE(SUM(CASE WHEN kind='withdraw' THEN -amount1 ELSE amount1 END),0) FROM flows WHERE slot=?",
            (slot,),
        ).fetchone()
        return float(row[0]), float(row[1])

    def pnl(self, slot: str) -> SlotPnl | None:
        s = self.slot_row(slot)
        if s is None:
            return None
        dep = self.db.execute(
            "SELECT COALESCE(SUM(usd),0) FROM flows WHERE slot=? AND kind IN ('deposit','topup')", (slot,)
        ).fetchone()[0]
        wd = self.db.execute(
            "SELECT COALESCE(SUM(usd),0) FROM flows WHERE slot=? AND kind='withdraw'", (slot,)
        ).fetchone()[0]
        ev = self.db.execute(
            "SELECT COALESCE(SUM(gas_usd),0), COALESCE(SUM(reward_usd),0) FROM events WHERE slot=?", (slot,)
        ).fetchone()
        snap = self.db.execute(
            "SELECT value_usd, hodl_usd, unclaimed_usd FROM snapshots WHERE slot=? ORDER BY ts DESC LIMIT 1", (slot,)
        ).fetchone()
        value, hodl, unclaimed = (snap[0], snap[1], snap[2]) if snap else (0.0, float(dep), 0.0)
        if s["closed_at"] is not None:
            value, unclaimed = 0.0, 0.0
        return SlotPnl(
            slot=slot,
            pair=s["pair"],
            pool=s["pool"],
            token_id=s["token_id"],
            experiment=s["experiment"],
            opened_at=s["opened_at"],
            closed_at=s["closed_at"],
            deposited_usd=float(dep),
            withdrawn_usd=float(wd),
            rewards_usd=float(ev[1]),
            gas_usd=float(ev[0]),
            value_usd=float(value),
            hodl_usd=float(hodl),
            unclaimed_usd=float(unclaimed),
        )

    def experiments(self) -> list[dict[str, Any]]:
        out = []
        for e in self.db.execute("SELECT * FROM experiments ORDER BY started_at"):
            arms = [r["slot"] for r in self.db.execute("SELECT slot FROM slots WHERE experiment=?", (e["id"],))]
            out.append(
                {
                    "id": e["id"],
                    "started_at": e["started_at"],
                    "status": e["status"],
                    "winner": e["winner"],
                    "arms": arms,
                }
            )
        return out

    def recent_events(self, n: int = 50) -> list[dict[str, Any]]:
        rows = list(self.db.execute("SELECT * FROM events ORDER BY ts DESC, id DESC LIMIT ?", (n,)))
        return [
            {
                "ts": r["ts"],
                "kind": r["kind"],
                "slot": r["slot"],
                "detail": r["detail"] or "",
                "tx": json.loads(r["tx"] or "[]"),
            }
            for r in reversed(rows)
        ]

    def idle_amount(self, token: str, now_amount: float, window_s: float, now: float | None = None) -> float:
        """The part of `now_amount` that has been in the wallet for the whole window.

        That is the minimum recorded balance over the window, capped by the current amount. If the history
        does not cover the full window yet, the answer is 0 (not proven idle).
        """
        t = now or time.time()
        first = self.db.execute("SELECT MIN(ts) FROM wallet_balances WHERE token=?", (token.lower(),)).fetchone()[0]
        if first is None or first > t - window_s:
            return 0.0
        low = self.db.execute(
            "SELECT MIN(amount) FROM wallet_balances WHERE token=? AND ts >= ?", (token.lower(), t - window_s)
        ).fetchone()[0]
        return max(0.0, min(float(low if low is not None else 0.0), now_amount))
