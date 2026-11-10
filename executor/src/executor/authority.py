"""One wallet authority across executor homes; enrollment never enables live mode.

The authority location depends only on the OS user's home and wallet. Client
homes cannot select another authority. All supported live writers use this lock,
shared journal, immutable request bindings and conservative aggregate limits.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pwd
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from . import ledger
from .config import Config, public_view
from .errors import Refused
from .gates import _atomic_write
from .journal import Journal
from .tokens import WSOL_MINT, raw_to_ui

STRATEGIES = frozenset(("grid", "dca", "trend", "momentum", "path-validation"))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def wallet_root(owner):
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".executor-wallets" / hashlib.sha256(owner.encode()).hexdigest()


def default_client_root():
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".executor"


def positive(value, label, *, zero=False):
    try:
        if isinstance(value, bool):
            raise ValueError
        number = Decimal(str(value))
        if not number.is_finite() or (number < 0 if zero else number <= 0):
            raise ValueError
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise Refused(f"missing or invalid {label}") from None


def identity(cfg):
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}
    config = public_view(cfg)
    return {
        "protocol": 1,
        "wallet": cfg.owner,
        "source_digest": digest(source),
        "installation_digest": digest([str(Path(sys.executable).resolve()), str(Path(__file__).parent.resolve())]),
        "config_digest": digest({**config, "rpc": cfg.rpc_url, "jupiter": cfg.jupiter_base_url}),
        "venue": "jupiter-swap-v1",
    }


class WalletAuthority:
    def __init__(self, cfg: Config, client: Path):
        self.cfg = cfg
        self.client = Path(client).resolve()
        self.root = wallet_root(cfg.owner)
        self.policy_path = self.root / "policy.json"
        self.journal = Journal(self.root / "journal.jsonl")

    @contextmanager
    def lock(self, *, create=False):
        if create:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise Refused("shared wallet authority is not enrolled; explicit wallet.register required")
        fd = os.open(self.root / "wallet.lock", os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise Refused("another shared wallet writer is active") from None
            yield self
        finally:
            os.close(fd)

    def _policy(self):
        try:
            policy = json.loads(self.policy_path.read_text())
            if policy["version"] != 1 or policy["wallet"] != self.cfg.owner:
                raise ValueError
            positive(policy["portfolio_cap_usd"], "shared wallet portfolio cap")
            return policy
        except (OSError, ValueError, KeyError, TypeError):
            raise Refused("shared wallet policy missing or incompatible") from None

    @staticmethod
    def _live_history(root):
        journal = Journal(Path(root) / "journal.jsonl")
        if journal.corrupt_lines():
            raise Refused("client journal is corrupt")
        return [r for r in journal.records() if r["kind"] != "dry_run"]

    def register(self, cap, clients, inventory_complete):
        cap = positive(cap, "explicit shared wallet portfolio cap")
        if inventory_complete is not True or not isinstance(clients, list) or not clients:
            raise Refused("complete explicit wallet writer inventory required")
        normalized = {}
        for client in clients:
            if not isinstance(client, dict) or set(client) != {"root", "aware"}:
                raise Refused("invalid wallet client descriptor")
            root = client["root"]
            if not isinstance(root, str) or not Path(root).is_absolute() or type(client["aware"]) is not bool:
                raise Refused("invalid wallet client descriptor")
            root = str(Path(root).resolve())
            if root in normalized:
                raise Refused("duplicate wallet writer")
            normalized[root] = {"root": root, "aware": client["aware"]}
        if str(self.client) not in normalized:
            raise Refused("current executor home must be in writer inventory")
        with self.lock(create=True):
            old = self._policy() if self.policy_path.exists() else None
            if old is None and ((self.root / "requests.sqlite3").exists() or self.journal.path.exists()):
                raise Refused("wallet policy disappeared or enrollment is incomplete; refusing authority reset")
            default = default_client_root().resolve()
            if (
                default.exists()
                and str(default) not in normalized
                and (old is None or str(default) not in old["clients"])
            ):
                normalized[str(default)] = {"root": str(default), "aware": False}
            if old and not (self.root / "requests.sqlite3").is_file():
                raise Refused("registered wallet request ledger is missing; refusing recreation")
            if old:
                self.check_anchor()
            if old and cap > positive(old["portfolio_cap_usd"], "portfolio cap"):
                raise Refused("enrollment cannot increase the shared wallet portfolio cap")
            if old:
                for root, client in old["clients"].items():
                    if root not in normalized:
                        normalized[root] = client
                    elif client["aware"] is False:
                        normalized[root]["aware"] = False
            for root, client in normalized.items():
                history = self._live_history(root)
                previous = old["clients"].get(root) if old else None
                if previous:
                    if previous["history_digest"] != digest(history):
                        raise Refused("previously enrolled local history changed; unaware writer must be reconciled")
                    client["history_digest"] = previous["history_digest"]
                    continue
                # Import legacy risk and unknown sends before accepting this home.
                prefix = hashlib.sha256(root.encode()).hexdigest()[:16] + ":"
                existing = list(self.journal.records())
                for record in history:
                    fields = {k: v for k, v in record.items() if k not in ("seq", "kind", "id")}
                    fields["legacy_source_sequence"] = record["seq"]
                    expected = {"kind": record["kind"], "id": prefix + record["id"], **fields}
                    prior = [
                        r
                        for r in existing
                        if r.get("id") == expected["id"] and r.get("legacy_source_sequence") == record["seq"]
                    ]
                    if prior:
                        if len(prior) != 1 or {k: v for k, v in prior[0].items() if k != "seq"} != expected:
                            raise Refused("legacy journal import conflicts with durable history")
                        continue
                    self.journal.append(record["kind"], prefix + record["id"], **fields)
                client["history_digest"] = digest(history)
            limits = {
                name: getattr(self.cfg.rails, name)
                for name in ("max_position_usd", "max_trade_usd", "daily_loss_stop_usd")
            }
            if old:
                limits = {name: min(value, old["limits"][name]) for name, value in limits.items()}
            policy = {
                "version": 1,
                "wallet": self.cfg.owner,
                "portfolio_cap_usd": str(cap),
                "clients": normalized,
                "limits": limits,
            }
            _atomic_write(self.policy_path, policy)
            with self._database(create=True):
                pass
            return {"registered": True, "policy_digest": digest(policy), "live_enabled": False}

    def check(self):
        policy = self._policy()
        if str(self.client) not in policy["clients"]:
            raise Refused("executor home is not enrolled in the shared wallet authority")
        for root, client in policy["clients"].items():
            if not client["aware"]:
                raise Refused("known unaware wallet writer prevents sole-owner admission")
            if digest(self._live_history(root)) != client["history_digest"]:
                raise Refused("local client history changed outside shared wallet authority")
        if self.journal.corrupt_lines():
            raise Refused("shared wallet journal is corrupt")
        self.check_anchor()
        return policy

    def check_anchor(self):
        with self._database() as db:
            anchor = db.execute("SELECT count,digest FROM journal_anchor WHERE singleton=1").fetchone()
        records = list(self.journal.records())
        if anchor is None or len(records) < anchor["count"] or digest(records[: anchor["count"]]) != anchor["digest"]:
            raise Refused("shared wallet journal history disappeared or changed")

    def save_anchor(self):
        records = list(self.journal.records())
        with self._database() as db:
            db.execute("UPDATE journal_anchor SET count=?,digest=? WHERE singleton=1", (len(records), digest(records)))

    def killed(self):
        if not self.policy_path.is_file():
            return False
        return any((Path(root) / "KILL").exists() for root in self._policy()["clients"])

    def effective_config(self):
        policy = self.check()
        limits = {name: min(getattr(self.cfg.rails, name), value) for name, value in policy["limits"].items()}
        return replace(self.cfg, rails=replace(self.cfg.rails, **limits))

    @contextmanager
    def _database(self, *, create=False):
        path = self.root / "requests.sqlite3"
        if not create and not path.is_file():
            raise Refused("registered wallet request ledger is missing; refusing recreation")
        db = sqlite3.connect(path) if create else sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)
        db.row_factory = sqlite3.Row
        if create:
            db.execute(
                "CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL, intent_id TEXT, reserved_usd TEXT NOT NULL, result TEXT)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS journal_anchor (singleton INTEGER PRIMARY KEY CHECK(singleton=1), count INTEGER NOT NULL, digest TEXT NOT NULL)"
            )
            db.execute("INSERT OR IGNORE INTO journal_anchor VALUES (1,0,?)", (digest([]),))
            db.commit()
            path.chmod(0o600)
        try:
            with db:
                yield db
        finally:
            db.close()

    def bind(self, request_id, body):
        try:
            if str(UUID(request_id)) != request_id:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise Refused("caller request_id must be a canonical UUID") from None
        text = encoded(body)
        with self._database() as db:
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row:
                if row["body"] != text:
                    raise Refused("caller request_id conflicts with its original exact intent")
                return dict(row)
            db.execute("INSERT INTO requests VALUES (?,?,?,NULL,?,NULL)", (request_id, text, "bound", "0"))
        return None

    def update(self, request_id, state, *, reserved="0", intent_id=None, result=None):
        with self._database() as db:
            db.execute(
                "UPDATE requests SET state=?, reserved_usd=?, intent_id=COALESCE(?,intent_id), result=? WHERE request_id=?",
                (state, str(reserved), intent_id, encoded(result) if result is not None else None, request_id),
            )

    def status(self, request_id):
        if not self.policy_path.is_file():
            if (self.root / "requests.sqlite3").exists() or self.journal.path.exists():
                raise Refused("wallet policy is missing; retained requests require authority recovery")
            return {"registered": False, "request": None}
        with self._database() as db:
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            return {"registered": True, "request": None}
        result = json.loads(row["result"]) if row["result"] else None
        return {
            "registered": True,
            "request": {
                "request_id": row["request_id"],
                "state": row["state"],
                "reserved_usd": row["reserved_usd"],
                "intent_id": row["intent_id"],
                "result": result,
            },
        }

    def require_no_pending(self, request_id, *, exit_only=False):
        with self._database() as db:
            rows = db.execute(
                "SELECT * FROM requests WHERE request_id<>? AND state IN ('bound','reserved','executing','unknown')",
                (request_id,),
            ).fetchall()
        if rows:
            raise Refused("unresolved send or shared wallet request; reconcile before another swap")

    def budget(self, report, native, fee, *, request_id, exit_only=False):
        policy = self.check()
        if type(native) is not int or native < 0 or type(fee) is not int or fee < 0:
            raise Refused("missing measured wallet balance or transaction fee")
        states = self.journal.states()
        strategies = {s["intent"]["strategy"] for s in states.values() if s.get("intent", {}).get("strategy")}
        cost = Decimal(0)
        for strategy in strategies:
            positions = ledger.positions(states, strategy)
            if (
                not exit_only
                and strategy not in STRATEGIES
                and (
                    any(pos.qty_raw for pos in positions.values())
                    or ledger.realized_pnl_usd(states, ledger.utc_day(time.time()), strategy) < 0
                )
            ):
                raise Refused("legacy strategy risk family is unclassified; reconcile before canonical entries")
            for mint, pos in positions.items():
                if pos.qty_raw:
                    # All position marks must be available; this venue supports
                    # SOL/USDC initially, never substitute a zero for a mark.
                    if mint != WSOL_MINT:
                        raise Refused("missing independent mark for shared wallet position")
                    positive(report.sol_price_usd, "SOL position mark")
                    cost += max(pos.cost_usd, raw_to_ui(pos.qty_raw, 9) * report.sol_price_usd)
        with self._database() as db:
            pending = db.execute(
                "SELECT reserved_usd FROM requests WHERE request_id<>? AND state IN ('reserved','executing','unknown')",
                (request_id,),
            ).fetchall()
        reserved = sum((positive(r[0], "pending reservation", zero=True) for r in pending), Decimal(0))
        fee_usd = raw_to_ui(fee, 9) * positive(report.sol_price_usd, "SOL fee price")
        native_reserve = raw_to_ui(self.cfg.rails.min_sol_reserve_lamports, 9) * report.sol_price_usd
        spend = positive(report.in_usd, "independent spend")
        if not exit_only and cost + reserved + spend + fee_usd + native_reserve > positive(
            policy["portfolio_cap_usd"], "portfolio cap"
        ):
            raise Refused("shared wallet portfolio cap exhausted by positions, pending spends, fees and reserve")
        if (
            native - fee - (report.quote.in_raw if report.token_in.mint == WSOL_MINT else 0)
            < self.cfg.rails.min_sol_reserve_lamports
        ):
            raise Refused("shared wallet spend and fee would consume SOL reserve")
        if not exit_only:
            self.update(request_id, "reserved", reserved=spend + fee_usd)
        return spend + fee_usd

    def replay(self, row):
        if row["result"] is not None:
            return json.loads(row["result"])
        return {
            "request_id": row["request_id"],
            "sent": None,
            "state": "unknown",
            "reason": "accepted request interrupted; reconcile, never retry",
        }

    def reconcile_requests(self):
        states = self.journal.states()
        with self._database() as db:
            rows = db.execute(
                "SELECT * FROM requests WHERE state IN ('bound','reserved','executing','unknown')"
            ).fetchall()
            for row in rows:
                intent = states.get(row["intent_id"])
                if intent is None or intent["state"] == "intent":
                    result = {
                        "request_id": row["request_id"],
                        "state": "terminal",
                        "sent": False,
                        "reason": "proven_no_send: shared writer held and no sending journal exists",
                    }
                    db.execute(
                        "UPDATE requests SET state='terminal',reserved_usd='0',result=? WHERE request_id=?",
                        (encoded(result), row["request_id"]),
                    )
                elif intent["state"] in ("result", "reconciled"):
                    result = {
                        "request_id": row["request_id"],
                        "state": "terminal",
                        "outcome": intent["outcome"],
                        "sent": intent["outcome"]["status"] in ("confirmed", "failed"),
                    }
                    db.execute(
                        "UPDATE requests SET state='terminal',reserved_usd='0',result=? WHERE request_id=?",
                        (encoded(result), row["request_id"]),
                    )
