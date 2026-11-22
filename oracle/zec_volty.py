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
from collections import Counter
from contextlib import closing, nullcontext
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles

from .cli import owner
from .gum_orders import GumError, GumOrders, gum_account_owner
from .gum_signer import load_signer
from .gum_webhook_orders import VENUE, client_order_id, process_one, recover_planning
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
ACTIVITY_LIMIT = 6
STUCK_ORDER_TICKS = 4
_ACTIVITY_OUTCOMES = {
    "queued": "evaluating", "planning": "evaluating", "submitting": "pending",
    "pending": "pending", "expired": "expired", "refused": "refused",
    "cancelled": "cancelled", "unknown": "unknown", "complete": "complete",
}


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


def _private_state(path: Path, *, create: bool = True) -> Path:
    if create:
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


def _check_private_inbox(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("live_inbox_not_private")


def _read_inbox(path: Path):
    _check_private_inbox(path)
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def _leg_rows(db, *, limit=None):
    if limit is None:
        return db.execute(
            "SELECT event_id,portfolio_id,plan FROM signals WHERE plan IS NOT NULL ORDER BY rowid"
        )
    return db.execute(
        "SELECT event_id,status,plan,timestamp FROM signals WHERE plan IS NOT NULL ORDER BY rowid DESC LIMIT ?",
        (limit,),
    )


def _verify_inbox_binding(db, binding: str) -> None:
    policy = db.execute("SELECT binding FROM volty_policy WHERE slot=1").fetchone()
    if policy is None or policy["binding"] != binding:
        raise GumError("volty_live_inbox_policy_changed")
    retired = db.execute(
        "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='volty_retired_events'"
    ).fetchone()
    if retired is None:
        foreign = db.execute(
            "SELECT 1 FROM signals WHERE mode IS NOT 'live' OR portfolio_id IS NOT ? LIMIT 1",
            (binding,),
        ).fetchone()
    else:
        foreign = db.execute(
            """SELECT 1 FROM signals AS s LEFT JOIN volty_retired_events AS r USING (event_id)
                WHERE s.mode IS NOT 'live'
                   OR (r.event_id IS NULL AND s.portfolio_id IS NOT ?)
                   OR (r.event_id IS NOT NULL AND (
                       s.portfolio_id IS NOT r.binding
                       OR s.status NOT IN ('complete','expired','refused','cancelled')
                   )) LIMIT 1""",
            (binding,),
        ).fetchone()
    if foreign is not None:
        raise GumError("volty_live_inbox_binding_mismatch")


def _require_idle_inbox(db, binding: str) -> None:
    _verify_inbox_binding(db, binding)
    outstanding = db.execute(
        "SELECT 1 FROM signals WHERE status NOT IN ('complete','expired','refused','cancelled') LIMIT 1"
    ).fetchone()
    if outstanding is not None:
        raise GumError("volty_execution_requires_reconciliation")


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
                settling = (
                    outcome == "pending" and leg["plan"]["action"] == "close"
                    and receipt.get("status") == "filled" and receipt.get("settled") is False
                )
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
                        **({"settlement_pending": True} if settling else {}),
                    }
                )
    return projected


def _recent_activity(path: Path) -> list[dict]:
    """Project the latest recorded crossings without exporting plan or account data."""
    with _read_inbox(path) as db:
        rows = db.execute(
            """SELECT inputs.observation, inputs.skip_reason, signals.status,
                      json_extract(signals.result, '$.reason') AS reason
               FROM volty_inputs AS inputs LEFT JOIN signals USING (event_id)
               ORDER BY inputs.rowid DESC LIMIT ?""",
            (ACTIVITY_LIMIT,),
        ).fetchall()
    events = []
    for row in rows:
        signal = json.loads(row["observation"])
        outcome = row["skip_reason"] or _ACTIVITY_OUTCOMES.get(row["status"], "unknown")
        if outcome == "complete" and row["reason"] == "target_position_already_held":
            outcome = "already_held"
        events.append({"at": signal["at"], "side": signal["side"], "mark": signal["mark"], "outcome": outcome})
    return events


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
            _verify_inbox_binding(db, self.binding)
            db.execute(
                "CREATE TABLE IF NOT EXISTS volty_inputs ("
                "event_id TEXT PRIMARY KEY, observation TEXT NOT NULL, skip_reason TEXT)"
            )

    def verify_lineage(self, position: dict) -> None:
        expected_side, expected_size = None, Decimal(0)
        filled_orders = set()
        if os.path.lexists(self.path):
            with _read_inbox(self.path) as db:
                _verify_inbox_binding(db, self.binding)
                for row in _leg_rows(db):
                    state = json.loads(row["plan"])
                    binding = row["portfolio_id"]
                    if state["binding"] != binding or state["venue"] != VENUE:
                        raise GumError("volty_live_inbox_binding_mismatch")
                    for index, leg in enumerate(state["legs"]):
                        if leg["state"] != "filled":
                            continue
                        plan = leg["plan"]
                        receipt = leg["receipt"]
                        fill_id = (receipt["order_id"], receipt["client_order_id"])
                        if (
                            leg["client_order_id"] != client_order_id(binding, row["event_id"], index)
                            or receipt["client_order_id"] != leg["client_order_id"]
                            or receipt["status"] != "filled"
                            or plan["binding"] != binding
                            or fill_id in filled_orders
                            or any(
                                values[field] != expected
                                for values in (plan, receipt)
                                for field, expected in (
                                    ("owner", self.owner),
                                    ("account_id", self.account_id),
                                    ("subaccount_id", self.subaccount_id),
                                    ("symbol", "ZEC"),
                                )
                            )
                        ):
                            raise GumError("volty_fill_lineage_unverified")
                        filled_orders.add(fill_id)
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
        if plan["action"] == "open" and self.entries_paused():
            raise GumError("gum_disarmed_or_expired")
        return plan

    def entries_paused(self) -> bool:
        # A dangling marker must also fence openings after a restart.
        return os.path.lexists(self.path.parent / "PAUSE_ENTRIES")

    def submit_leg(self, plan, client_order_id, *, enabled=lambda: True,
                   deadline=None, approve_fresh=None, timing=None):
        reduce_only = isinstance(plan, dict) and plan.get("action") == "close" and plan.get("reduce_only") is True
        return super().submit_leg(
            plan, client_order_id,
            enabled=lambda: enabled() and (reduce_only or not self.entries_paused()),
            deadline=deadline, approve_fresh=approve_fresh, timing=timing,
        )


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
        self.observation = None
        self.tick_path = state_dir / "learning-ticks.sqlite3"
        self.tick_watermark = None
        self.capture = "waiting"
        self.checked_owner = False
        self.unresolved_order = None
        self.unresolved_ticks = 0
        self.last_stuck_reset_at = None
        if venue is not None:
            venue.verify_binding()
            recover_planning(self.inbox)
            with database(self.inbox) as db, db:
                db.execute("UPDATE signals SET status='expired' WHERE status='queued'")

    def publish(self, state: str) -> str:
        now = int(self.clock())
        observation = self.observation
        market = None
        if (
            observation is not None and state not in {"paused", "stopped", "data-unavailable"}
            and 0 <= now - observation.mark_at <= MARK_MAX_AGE_SEC
            and now < observation.window_start + WINDOW_SEC
        ):
            market = asdict(observation)
        activity = []
        if self.venue is not None:
            try:
                activity = _recent_activity(self.inbox)
            except (OSError, sqlite3.Error, KeyError, TypeError, ValueError, RecursionError):
                # Optional activity must never interrupt the owner's loop.
                activity = None
        _write_status(
            self.state_dir / "status.json",
            {
                "schema": 1,
                "mode": "live" if self.venue is not None else "observe",
                "state": state,
                "updated_at": now,
                "signal": None if self.last_signal is None else asdict(self.last_signal),
                "orders": _orders(self.inbox),
                "telemetry": {
                    "market": market, "activity": activity, "capture": self.capture,
                    "entries_paused": self.venue is not None and self.venue.entries_paused(),
                    "reconciliation": {
                        "unresolved_fresh_ticks": self.unresolved_ticks,
                        "reset_threshold": STUCK_ORDER_TICKS,
                        "last_reset_at": self.last_stuck_reset_at,
                    },
                },
            },
        )
        return state

    def _envelope(self):
        with database(self.inbox) as db:
            return db.execute(
                """SELECT event_id, status, client_order_id,
                          CASE WHEN json_valid(plan) THEN json_extract(plan, '$.phase') END AS phase
                   FROM signals WHERE status IN ('pending','submitting','unknown') ORDER BY rowid LIMIT 1"""
            ).fetchone()

    def _watch_unresolved(self, row, *, fresh: bool) -> bool:
        # A settled close awaiting a new leg is no longer an unresolved order.
        key = (row["event_id"], row["client_order_id"]) if row is not None and row["phase"] == "awaiting_fill" else None
        if key != self.unresolved_order:
            self.unresolved_order = key
            self.unresolved_ticks = 0
        if key is None or not fresh or self.unresolved_ticks >= STUCK_ORDER_TICKS:
            return False
        self.unresolved_ticks += 1
        if self.unresolved_ticks < STUCK_ORDER_TICKS:
            return False
        self.active = None
        self.engine.reset()
        self.checked_owner = False
        self.last_stuck_reset_at = int(self.clock())
        return True

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
        received = self.clock()
        event = self.engine.observe(observation, now=received)
        self.observation = observation
        self.window_start = observation.window_start
        self.mark_at = observation.mark_at
        if event is not None:
            self.last_signal = event
            # A newer opposite intent supersedes an unfinished reversal. The
            # pending order still reconciles, but its old direction cannot open.
            if self.active is not None and event.side != self.active.side:
                self.active = None
        self._capture_tick(observation, int(received * 1000))
        return event

    def _capture_tick(self, observation, received_ms: int) -> None:
        if self.tick_watermark is not None and observation.mark_at <= self.tick_watermark:
            return
        try:
            with os.fdopen(os.open(self.tick_path, os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_WRONLY, 0o600), "wb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ValueError("volty_ticks_not_private")
            with closing(sqlite3.connect(self.tick_path, timeout=0.05)) as db, db:
                if self.tick_watermark is None:
                    db.execute("PRAGMA journal_mode=WAL")
                    db.execute("""CREATE TABLE IF NOT EXISTS ticks (
                        mark_at INTEGER PRIMARY KEY, received_ms INTEGER NOT NULL,
                        mark REAL NOT NULL, lower REAL NOT NULL, upper REAL NOT NULL, window_start INTEGER NOT NULL
                    )""")
                latest = db.execute("SELECT mark_at,received_ms FROM ticks ORDER BY mark_at DESC LIMIT 1").fetchone()
                if latest is None or observation.mark_at > latest[0]:
                    if latest and received_ms <= latest[1]:
                        raise ValueError("volty_receipt_clock_regressed")
                    db.execute("INSERT INTO ticks VALUES (?,?,?,?,?,?)", (
                        observation.mark_at, received_ms, observation.mark, observation.lower,
                        observation.upper, observation.window_start,
                    ))
            self.tick_watermark = max(observation.mark_at, latest[0]) if latest else observation.mark_at
            self.capture = "recording"
        except (OSError, ValueError, sqlite3.Error):
            # An analytical write cannot interrupt existing funded lifecycle checks.
            self.capture = "unavailable"

    def step(self) -> str:
        if self._paused():
            self.active = None
            self.engine.reset()
            if self.venue is not None:
                self._reconcile(self._envelope())
            return self.publish("paused")
        previous_mark = self.mark_at
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
        reset = self._watch_unresolved(outstanding, fresh=previous_mark is None or self.mark_at > previous_mark)
        if outstanding is not None:
            state = self._reconcile(outstanding)
            if reset:
                if event is not None:
                    self._record(event, skip="preceding_order_unresolved")
                return self.publish(state)
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
            if (event is not None and self.venue.entries_paused()
                    and account["position"]["side"] in (None, event.side)):
                self.active = None
                self._record(event, skip="funded_entries_paused")
                return self.publish("armed")
        if event is None or not self._record(event):
            return self.publish("armed")
        self.active = event
        if not self._enabled():
            self._expire(event.event_id, "signal_not_current")
            self.active = None
            return self.publish("armed")
        entries_paused = self.venue.entries_paused()
        outcome = self._dispatch(self._enabled)
        if entries_paused or self.venue.entries_paused():
            # Removing the marker cannot revive a reversal initiated in close-only mode.
            self.active = None
        if outcome == "disarmed":
            self._expire(event.event_id, "signal_disarmed")
        return self.publish(_state(outcome))

    def _dispatch(self, enabled) -> str:
        return process_one(
            self.inbox, self.venue, self.venue.binding, enabled=enabled, allow_live=True, record_timing=True,
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
        entries_paused = self.venue.entries_paused()
        if entries_paused:
            self.active = None
        owns_event = self.active is not None and self.active.event_id == row["event_id"]
        if row["phase"] == "ready_to_open" and not (owns_event and self._enabled()):
            reason = "funded_entries_paused" if entries_paused else "reversal_signal_no_longer_authorized"
            self._expire(row["event_id"], reason)
            return "armed"
        outcome = self._dispatch(lambda: owns_event and self._enabled())
        if outcome == "closed" and (entries_paused or self.venue.entries_paused()):
            self.active = None
            self._expire(row["event_id"], "funded_entries_paused")
            return "armed"
        return _state(outcome)


def _state(outcome: str) -> str:
    if outcome in {"pending", "closed"}:
        return "checking"
    if outcome in {"refused", "blocked", "unknown"}:
        return "blocked"
    return "armed"


def execution_timing(path: Path) -> dict:
    """Report only measured local dispatch timing from the private live inbox."""
    outcome_counts = Counter()
    signals = measured_signals = cap_refusals = posts = 0
    stages = {
        "signal_to_post_ms": [],
        "planning_ms": [],
        "fresh_quote_ms": [],
        "fresh_quote_to_post_ms": [],
    }

    def elapsed(value):
        return value if type(value) is int and 0 <= value <= 86_400_000 else None

    def sample(series, first, last):
        start, end = elapsed(first), elapsed(last)
        if start is not None and end is not None and end >= start:
            stages[series].append(end - start)

    with _read_inbox(path) as db:
        for row in db.execute("SELECT plan FROM signals WHERE mode='live'"):
            signals += 1
            if row["plan"] is None:
                continue
            plan = json.loads(row["plan"])
            if not isinstance(plan, dict):
                continue
            attempts = plan.get("execution_timing")
            if not isinstance(attempts, list) or not attempts:
                continue
            measured_signals += 1
            for attempt in attempts:
                if not isinstance(attempt, dict) or not isinstance(attempt.get("elapsed_ms"), dict):
                    continue
                times = attempt["elapsed_ms"]
                outcome = attempt.get("outcome")
                if outcome in ("pending", "unknown", "refused", "expired", "dry-run", "prepared", "noop"):
                    outcome_counts[outcome] += 1
                cap_refusals += attempt.get("diagnostic") == "gum_price_cap_widened"
                post = elapsed(times.get("post_started"))
                age = elapsed(attempt.get("signal_age_at_dispatch_ms"))
                if post is not None:
                    posts += 1
                    if age is not None:
                        stages["signal_to_post_ms"].append(age + post)
                sample("planning_ms", times.get("planning_started"), times.get("planning_finished"))
                sample("fresh_quote_ms", times.get("fresh_quote_started"), times.get("fresh_quote_finished"))
                sample("fresh_quote_to_post_ms", times.get("fresh_quote_finished"), post)
    return {
        "journal_signals": signals,
        "signals_with_timing": measured_signals,
        "post_attempts_observed": posts,
        "price_cap_refusals_observed": cap_refusals,
        "dispatch_outcomes": dict(outcome_counts),
        "latency": {
            name: {"samples": len(values), "p50": round(median(values)) if values else None,
                   "p90": round(quantiles(values, n=10, method="inclusive")[8]) if len(values) > 1 else None}
            for name, values in stages.items()
        },
    }


def preflight(venue: VoltyVenue) -> dict:
    """Check both opening sides through the exact planner using only venue reads."""
    if os.path.lexists(venue.path):
        with _read_inbox(venue.path) as db:
            _require_idle_inbox(db, venue.binding)
    return _opening_preview(venue, venue)


def _verify_flat_lineage(venue: VoltyVenue, position: dict) -> None:
    venue.verify_lineage(position)
    if position["side"] is not None:
        raise GumError("volty_open_position_requires_reconciliation")


def _opening_preview(candidate: VoltyVenue, current: VoltyVenue) -> dict:
    # During rotation the candidate supplies economics, while the current
    # binding continues to authorize the immutable journal and fill lineage.
    account = candidate.preflight()
    _verify_flat_lineage(current, account["position"])
    plans = []
    for side in ("buy", "sell"):
        plan = GumOrders.plan(candidate, "ZEC", side, candidate.account_id)
        _verify_flat_lineage(current, plan["position_before"])
        plans.append({key: plan[key] for key in ("side", "quantity", "notional_cap")})
    return {
        "eligible": True,
        "selected_leverage": account["selected_leverage"],
        "max_order_notional_usdc": candidate.max_order_notional_usdc.to_eng_string(),
        "free_usdc": account["free_usdc"],
        "preview": plans,
    }


def rotate_allocation(state_dir: Path, old_policy: LivePolicy, new_policy: LivePolicy, *, call=None) -> dict:
    """Promote a new allocation only on an offline, reconciled Volty account."""
    if replace(old_policy, allocation=new_policy.allocation) != new_policy:
        raise GumError("volty_rotation_requires_allocation_only_change")
    state_dir = _private_state(state_dir, create=False)
    inbox = state_dir / "live.sqlite3"
    _check_private_inbox(inbox)
    current = VoltyVenue(old_policy, inbox, call=call)
    candidate = VoltyVenue(new_policy, inbox, call=call)
    if current.allocation == candidate.allocation:
        raise GumError("volty_rotation_requires_new_allocation")

    with owner(state_dir / "status.json"), gum_account_owner(current, STRATEGY_ID, inbox):
        with _read_inbox(inbox) as db:
            _require_idle_inbox(db, current.binding)
        preview = _opening_preview(candidate, current)
        _check_private_inbox(inbox)
        uri = f"{inbox.as_uri()}?mode=rw"
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            _require_idle_inbox(db, current.binding)
            db.execute(
                "CREATE TABLE IF NOT EXISTS volty_retired_events "
                "(event_id TEXT PRIMARY KEY, binding TEXT NOT NULL)"
            )
            db.execute(
                """INSERT INTO volty_retired_events (event_id,binding)
                   SELECT event_id,portfolio_id FROM signals AS s
                   WHERE s.portfolio_id=? AND NOT EXISTS (
                       SELECT 1 FROM volty_retired_events AS r WHERE r.event_id=s.event_id
                   )""",
                (current.binding,),
            )
            updated = db.execute(
                "UPDATE volty_policy SET binding=? WHERE slot=1 AND binding=?",
                (candidate.binding, current.binding),
            )
            if updated.rowcount != 1:
                raise GumError("volty_live_inbox_policy_changed")
            _require_idle_inbox(db, candidate.binding)
    return {**preview, "allocation": str(candidate.allocation)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--timing", action="store_true", help="report measured execution latency from the journal")
    mode.add_argument("--rotate-allocation-from", type=Path, metavar="OLD_CONFIG")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".soltui" / "zec-volty")
    args = parser.parse_args(argv)
    rotating = args.rotate_allocation_from is not None
    if (args.live or args.preflight or rotating) != (args.config is not None):
        parser.error("--config is required with --live, --preflight, or --rotate-allocation-from")
    if args.live and not args.watch:
        parser.error("--live requires --watch")
    if (args.preflight or args.timing) and args.watch:
        parser.error("--preflight and --timing run once")
    if rotating and args.watch:
        parser.error("--rotate-allocation-from requires an offline watcher")
    if not math.isfinite(args.interval) or not 0.5 <= args.interval <= 10:
        parser.error("interval must be between 0.5 and 10 seconds")
    if args.timing:
        try:
            state_dir = _private_state(args.state_dir, create=False)
            print(json.dumps(execution_timing(state_dir / "live.sqlite3")))
            return 0
        except (OSError, ValueError, TypeError, sqlite3.Error):
            print(json.dumps({"available": False, "reason": "volty_execution_timing_unavailable"}))
            return 2
    if args.preflight or rotating:
        try:
            policy = LivePolicy.load(args.config)
            if rotating:
                old_policy = LivePolicy.load(args.rotate_allocation_from)
                result = rotate_allocation(args.state_dir, old_policy, policy)
            else:
                result = preflight(VoltyVenue(policy, args.state_dir / "live.sqlite3"))
        except GumError as error:
            print(json.dumps({"eligible": False, "reason": str(error)}))
            return 2
        except (OSError, ValueError, TypeError, RuntimeError, sqlite3.Error):
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
