"""Run the fixed GUM ZEC Volty strategy behind an explicitly enabled local owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import sqlite3
import stat
import sys
import tempfile
import threading
import time
from contextlib import closing, nullcontext
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from .cli import owner
from .gum_orders import GumError, GumOrders, gum_account_owner
from .gum_signer import load_signer
from .gum_webhook_orders import client_order_id, process_one, recover_planning
from .webhook_orders import database
from .zec_volty_signal import (
    MARK_MAX_AGE_SEC,
    STRATEGY_ID,
    WINDOW_SEC,
    GumVoltySource,
    VoltyDataError,
    VoltySignal,
    VoltySignalEngine,
)

LEVERAGE = 25
MAX_POLICY_BYTES = 4096
STATUS_LIMIT = 16
MAX_FILLS_PER_ORDER = 32


@dataclass(frozen=True)
class LivePolicy:
    owner: str
    trading_account: str
    subaccount_id: int
    key_file: Path
    allocation: str
    allocation_basis: str
    max_slippage_bps: int
    max_order_notional_usdc: str

    @classmethod
    def load(cls, path: Path) -> LivePolicy:
        with os.fdopen(
            os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
        ) as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("live_policy_not_private")
            raw = handle.read(MAX_POLICY_BYTES + 1)
        if len(raw) > MAX_POLICY_BYTES:
            raise ValueError("live_policy_too_large")
        inputs = json.loads(raw, object_pairs_hook=_unique_policy_fields)
        if not isinstance(inputs, dict) or set(inputs) != cls.__dataclass_fields__.keys():
            raise ValueError("invalid_live_policy")
        if not isinstance(inputs["key_file"], str):
            raise TypeError("invalid_signer_path")
        inputs["key_file"] = Path(inputs["key_file"])
        if not inputs["key_file"].is_absolute():
            raise ValueError("invalid_signer_path")
        return cls(**inputs)


def _unique_policy_fields(pairs: list[tuple[str, object]]) -> dict:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("duplicate_live_policy_field")
    return fields


def _private_state(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("state_directory_not_private")
    return path.resolve()


def _write_status(path: Path, data: dict) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".status-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, allow_nan=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _read_inbox(path: Path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("live_inbox_not_private")
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def _leg_rows(db, *, limit=None):
    if limit is None:
        return db.execute("SELECT event_id,status,plan,timestamp FROM signals WHERE plan IS NOT NULL ORDER BY rowid")
    return db.execute(
        "SELECT event_id,status,plan,timestamp FROM signals WHERE plan IS NOT NULL ORDER BY rowid DESC LIMIT ?",
        (limit,),
    )


def _orders(path: Path) -> list[dict]:
    if not path.exists():
        return []
    projected = []
    with _read_inbox(path) as db:
        for row in _leg_rows(db, limit=STATUS_LIMIT):
            legs = json.loads(row["plan"])["legs"]
            for index in range(len(legs) - 1, -1, -1):
                if len(projected) == STATUS_LIMIT:
                    return projected
                leg = legs[index]
                receipt = leg.get("receipt") or {}
                outcome = leg["state"]
                if index == len(legs) - 1 and outcome != "filled" and row["status"] in {"refused", "unknown"}:
                    outcome = row["status"]
                if outcome == "pending" and not receipt:
                    outcome = "acknowledged"
                projected.append(
                    {
                        "event_id": row["event_id"],
                        "side": leg["plan"]["side"],
                        "leg": leg["plan"]["action"],
                        "state": outcome,
                        "client_order_id": leg["client_order_id"],
                        "order_id": receipt.get("order_id"),
                        "requested_quantity": leg["plan"]["quantity"],
                        "filled_quantity": receipt.get("filled_quantity"),
                        "updated_at": leg.get("updated_at", row["timestamp"]),
                        "fills": _fill_details(receipt),
                    }
                )
    return projected


def _fill_details(receipt: dict) -> list[dict]:
    keys = ("signature", "price", "size", "fee", "timestamp")
    return [
        {key: fill[key] for key in keys}
        for fill in receipt.get("transactions", [])
        if fill.get("type") == "fill" and all(key in fill for key in keys)
    ][:MAX_FILLS_PER_ORDER]


class VoltyVenue(GumOrders):
    """Add fixed strategy authority and lineage to the existing GUM writer."""

    def __init__(self, policy: LivePolicy, path: Path, *, call=None, signer=None):
        if policy.max_order_notional_usdc is None or policy.trading_account is None:
            raise GumError("volty_execution_cap_and_dedicated_account_required")
        super().__init__(
            policy.owner,
            policy.trading_account,
            policy.subaccount_id,
            leverage=LEVERAGE,
            allocation=policy.allocation,
            allocation_basis=policy.allocation_basis,
            max_slippage_bps=policy.max_slippage_bps,
            signer=signer,
            call=call,
            max_order_notional_usdc=policy.max_order_notional_usdc,
            require_exact_leverage=True,
        )
        self.path = path

    @property
    def binding(self) -> str:
        return hashlib.sha256(f"{STRATEGY_ID}:{super().binding}".encode()).hexdigest()

    def verify_binding(self) -> None:
        with database(self.path) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS volty_policy (slot INTEGER PRIMARY KEY CHECK (slot=1), binding TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO volty_policy (slot,binding) VALUES (1,?)", (self.binding,))
            if db.execute("SELECT binding FROM volty_policy WHERE slot=1").fetchone()[0] != self.binding:
                raise GumError("volty_live_inbox_policy_changed")
            foreign = db.execute(
                "SELECT 1 FROM signals WHERE mode IS NOT 'live' OR portfolio_id IS NOT ? LIMIT 1",
                (self.binding,),
            ).fetchone()
            if foreign is not None:
                raise GumError("volty_live_inbox_binding_mismatch")
            db.execute(
                "CREATE TABLE IF NOT EXISTS volty_inputs ("
                "event_id TEXT PRIMARY KEY, observation TEXT NOT NULL, skip_reason TEXT)"
            )

    def verify_lineage(self, position: dict) -> None:
        expected_side, expected_size = None, Decimal(0)
        filled_orders = set()
        if os.path.lexists(self.path):
            with _read_inbox(self.path) as db:
                for row in _leg_rows(db):
                    state = json.loads(row["plan"])
                    if state["binding"] != self.binding:
                        raise GumError("volty_live_inbox_binding_mismatch")
                    for index, leg in enumerate(state["legs"]):
                        if leg["state"] != "filled":
                            continue
                        receipt = leg["receipt"]
                        if (
                            leg["client_order_id"] != client_order_id(self.binding, row["event_id"], index)
                            or receipt["client_order_id"] != leg["client_order_id"]
                            or receipt["status"] != "filled"
                            or receipt["account_id"] != self.account_id
                        ):
                            raise GumError("volty_fill_lineage_unverified")
                        filled_orders.add((receipt["order_id"], receipt["client_order_id"]))
                        expected_side = receipt["position"]["side"]
                        expected_size = Decimal(receipt["position"]["size"])
        if (
            position["side"] != expected_side
            or Decimal(position["size"]) != expected_size
            or self.filled_order_identifiers() != filled_orders
        ):
            raise GumError("volty_external_position_or_fill")

    def plan(self, symbol, side, account_id=None):
        plan = super().plan(symbol, side, account_id)
        self.verify_lineage(plan["position_before"])
        return plan


class VoltyRunner:
    def __init__(
        self, state_dir: Path, *, source=None, venue: VoltyVenue | None = None,
        clock=time.time, stop=None,
    ):
        self.state_dir = state_dir
        self.venue = venue
        self.inbox = venue.path if venue is not None else state_dir / "live.sqlite3"
        self.source = source if source is not None else GumVoltySource()
        self.clock = clock
        self.stop = stop if stop is not None else threading.Event()
        self.engine = VoltySignalEngine()
        self.last_signal = None
        self.active = None
        self.window_start = None
        self.mark_at = None
        self.checked_owner = False
        if venue is not None:
            venue.verify_binding()
            recover_planning(self.inbox)
            with database(self.inbox) as db, db:
                db.execute("UPDATE signals SET status='expired' WHERE status='queued'")

    def publish(self, state: str) -> str:
        _write_status(
            self.state_dir / "status.json",
            {
                "schema": 1,
                "mode": "live" if self.venue is not None else "observe",
                "state": state,
                "updated_at": int(self.clock()),
                "signal": None if self.last_signal is None else asdict(self.last_signal),
                "orders": _orders(self.inbox),
            },
        )
        return state

    def _envelope(self):
        with database(self.inbox) as db:
            return db.execute(
                "SELECT event_id,status,plan FROM signals WHERE status IN ('pending','submitting','unknown') ORDER BY rowid LIMIT 1"
            ).fetchone()

    def _paused(self) -> bool:
        # A dangling symlink is also a deliberate halt marker.
        return self.stop.is_set() or os.path.lexists(self.state_dir / "KILL")

    def _enabled(self) -> bool:
        now = self.clock()
        return (
            not self._paused()
            and self.active is not None
            and self.window_start is not None
            and self.mark_at is not None
            and 0 <= now - self.mark_at <= MARK_MAX_AGE_SEC
            and self.window_start <= self.active.at < self.window_start + WINDOW_SEC
            and now < self.window_start + WINDOW_SEC
        )

    def _record(self, event: VoltySignal, *, skip: str | None = None) -> bool:
        payload = json.dumps(asdict(event), sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with database(self.inbox) as db, db:
            first = db.execute(
                "INSERT OR IGNORE INTO volty_inputs (event_id,observation,skip_reason) VALUES (?,?,?)",
                (event.event_id, payload, skip),
            )
            if first.rowcount != 1 or skip is not None:
                return False
            created = db.execute(
                "INSERT OR IGNORE INTO signals (event_id,digest,symbol,side,timestamp,status,mode,portfolio_id) "
                "VALUES (?,?, 'ZEC', ?,?,'queued','live',?)",
                (event.event_id, digest, event.side, event.at, self.venue.binding),
            )
            # A previously observed crossing cannot be recycled after a restart.
            return created.rowcount == 1

    def _poll(self) -> VoltySignal | None:
        observation = self.source.read()
        event = self.engine.observe(observation, now=self.clock())
        self.window_start = observation.window_start
        self.mark_at = observation.mark_at
        if event is not None:
            self.last_signal = event
            # A newer opposite intent supersedes an unfinished reversal. The
            # pending order still reconciles, but its old direction cannot open.
            if self.active is not None and event.side != self.active.side:
                self.active = None
        return event

    def step(self) -> str:
        if self._paused():
            self.active = None
            self.engine.reset()
            if self.venue is not None:
                self._reconcile(self._envelope())
            return self.publish("paused")
        try:
            event = self._poll()
        except VoltyDataError:
            self.active = None
            self.engine.reset()
            if self.venue is not None:
                self._reconcile(self._envelope())
            return self.publish("data-unavailable")
        if self.venue is None:
            return self.publish("watching")
        outstanding = self._envelope()
        if outstanding is not None:
            state = self._reconcile(outstanding)
            if event is None:
                return self.publish(state)
            remaining = self._envelope()
            if remaining is not None and self.active is None:
                # Reconciliation may just have verified a close for the old
                # direction. Retire that open leg, then handle the fresh crossing.
                state = self._reconcile(remaining)
                remaining = self._envelope()
            if remaining is not None:
                self._record(event, skip="preceding_order_unresolved")
                return self.publish(state)
        if not self.checked_owner or event is not None:
            try:
                account = self.venue.preflight()
                self.venue.verify_lineage(account["position"])
            except GumError:
                if event is not None:
                    self._record(event, skip="owner_preflight_refused")
                raise
            self.checked_owner = True
        if event is None or not self._record(event):
            return self.publish("armed")
        self.active = event
        if not self._enabled():
            self._expire(event.event_id, "signal_not_current")
            self.active = None
            return self.publish("armed")
        outcome = self._dispatch(self._enabled)
        if outcome == "disarmed":
            self._expire(event.event_id, "signal_disarmed")
        return self.publish(_state(outcome))

    def _dispatch(self, enabled) -> str:
        return process_one(
            self.inbox, self.venue, self.venue.binding, enabled=enabled, allow_live=True,
        )

    def _expire(self, event_id: str, reason: str) -> None:
        with database(self.inbox) as db, db:
            db.execute(
                "UPDATE signals SET status='expired', result=? WHERE event_id=?",
                (json.dumps({"reason": reason}), event_id),
            )

    def _reconcile(self, row) -> str:
        if row is None:
            return "armed"
        state = json.loads(row["plan"])
        owns_event = self.active is not None and self.active.event_id == row["event_id"]
        if state["phase"] == "ready_to_open" and not (owns_event and self._enabled()):
            self._expire(row["event_id"], "reversal_signal_no_longer_authorized")
            return "armed"
        return _state(self._dispatch(lambda: owns_event and self._enabled()))


def _state(outcome: str) -> str:
    if outcome in {"pending", "closed"}:
        return "checking"
    if outcome in {"refused", "blocked", "unknown"}:
        return "blocked"
    return "armed"


def preflight(venue: VoltyVenue) -> dict:
    """Check both opening sides through the exact planner using only venue reads."""
    if os.path.lexists(venue.path):
        with _read_inbox(venue.path) as db:
            configuration = db.execute("SELECT binding FROM volty_policy WHERE slot=1").fetchone()
            if configuration is None or configuration["binding"] != venue.binding:
                raise GumError("volty_live_inbox_policy_changed")
            if db.execute(
                "SELECT 1 FROM signals WHERE status IN ('queued','planning','submitting','unknown','pending') LIMIT 1"
            ).fetchone() is not None:
                raise GumError("volty_execution_requires_reconciliation")
    account = venue.preflight()
    venue.verify_lineage(account["position"])
    if account["position"]["side"] is not None:
        raise GumError("volty_open_position_requires_reconciliation")
    plans = [venue.plan("ZEC", side, venue.account_id) for side in ("buy", "sell")]
    return {
        "eligible": True,
        "selected_leverage": account["selected_leverage"],
        "max_order_notional_usdc": venue.max_order_notional_usdc.to_eng_string(),
        "free_usdc": account["free_usdc"],
        "preview": [
            {key: plan[key] for key in ("side", "quantity", "notional_cap")}
            for plan in plans
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".soltui" / "zec-volty")
    args = parser.parse_args(argv)
    if (args.live or args.preflight) != (args.config is not None):
        parser.error("--config is required with --live or --preflight")
    if args.live and not args.watch:
        parser.error("--live requires --watch")
    if args.preflight and args.watch:
        parser.error("--preflight runs once")
    if not math.isfinite(args.interval) or not 0.5 <= args.interval <= 10:
        parser.error("interval must be between 0.5 and 10 seconds")
    if args.preflight:
        try:
            policy = LivePolicy.load(args.config)
            result = preflight(VoltyVenue(policy, args.state_dir / "live.sqlite3"))
        except GumError as error:
            print(json.dumps({"eligible": False, "reason": str(error)}))
            return 2
        except (OSError, ValueError, TypeError, sqlite3.Error):
            print(json.dumps({"eligible": False, "reason": "volty_policy_or_inbox_unavailable"}))
            return 2
        print(json.dumps(result))
        return 0
    stop = threading.Event()
    sigs = (signal.SIGINT, signal.SIGTERM)
    old = {sig: signal.signal(sig, lambda *_: stop.set()) for sig in sigs}
    try:
        state_dir = _private_state(args.state_dir)
        inbox = state_dir / "live.sqlite3"
        venue = None
        if args.live:
            policy = LivePolicy.load(args.config)

            def sign_action(message):
                # Load the secret only after the adapter validates a fresh order.
                return load_signer(policy.key_file, policy.owner)(message)

            venue = VoltyVenue(policy, inbox, signer=sign_action)
        account_claim = gum_account_owner(venue, STRATEGY_ID, inbox) if venue is not None else nullcontext()
        with owner(state_dir / "status.json"), account_claim:
            runner = VoltyRunner(state_dir, venue=venue, stop=stop)
            if not args.watch:
                return 3 if runner.step() == "data-unavailable" else 0
            try:
                while not stop.is_set():
                    try:
                        runner.step()
                    except GumError:
                        runner.active = None
                        runner.engine.reset()
                        runner.checked_owner = False
                        runner.publish("blocked")
                    stop.wait(args.interval)
            finally:
                if stop.is_set():
                    runner.publish("stopped")
        return 0
    except (OSError, ValueError, TypeError, GumError, sqlite3.Error):
        # The errors can originate in private paths and should not enter logs.
        print("Volty owner could not start or persist execution state.", file=sys.stderr)
        return 2
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
