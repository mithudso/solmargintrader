"""Durable future-only PAPER predictions from the frozen reversal/shape rule."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import signal
import threading
import time
from pathlib import Path

from oracle_leverage.market import VENUE, LiveMarket, MarketError
from oracle_leverage.store import Store, default_home
from research import reversal_shapes as strategy

MAX_SELECTION_BYTES = 256 * 1024


class ForwardError(RuntimeError):
    """A fixed rule or owned worker state cannot safely continue."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_selection(value):
    if isinstance(value, (str, Path)):
        with Path(value).open("rb") as stream:
            body = stream.read(MAX_SELECTION_BYTES + 1)
        if len(body) > MAX_SELECTION_BYTES:
            raise ForwardError("selection_size_limit")
        try:
            value = json.loads(body)
        except (ValueError, UnicodeError, RecursionError):
            raise ForwardError("selection_json_invalid") from None
    try:
        # Freeze a private copy and refuse nonfinite values before hashing it.
        value = json.loads(canonical(value))
    except (ValueError, TypeError, RecursionError):
        raise ForwardError("selection_json_invalid") from None
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("schema"), str)
        or not value["schema"]
        or not isinstance(value.get("run_id"), str)
        or not value["run_id"]
        or not isinstance(value.get("rules"), list)
        or len(value["rules"]) > 8
    ):
        raise ForwardError("selection_schema_invalid")
    identities = set()
    target_rules = set()
    known = {rule["id"]: rule for rule in strategy.rules()}
    for rule in value["rules"]:
        if (
            not isinstance(rule, dict)
            or rule.get("asset") not in ("BTC", "ZEC")
            or not isinstance(rule.get("id"), str)
            or not rule["id"]
            or type(rule.get("interval_minutes")) is not int
            or rule["interval_minutes"] not in strategy.INTERVALS
            or rule.get("pair") not in ("UU", "DD")
            or rule.get("shape_group") not in ("all", "rising", "falling", "range")
            or rule.get("direction") not in ("UP", "DOWN")
            or not isinstance(rule.get("evidence"), str)
        ):
            raise ForwardError("selection_rule_invalid")
        identity = (rule["asset"], rule["id"])
        if identity in identities:
            raise ForwardError("selection_rule_duplicate")
        identities.add(identity)
        expected = known.get(rule["id"])
        if expected is None or any(
            rule[key] != expected[key]
            for key in ("interval_minutes", "pair", "shape_group", "direction")
        ):
            raise ForwardError("selection_rule_identity_mismatch")
        target = (rule["asset"], rule["interval_minutes"])
        if target in target_rules:
            raise ForwardError("selection_target_rule_ambiguous")
        target_rules.add(target)
    return value


def _freeze(store, selection):
    text = canonical(selection)
    sha = hashlib.sha256(text.encode()).hexdigest()
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        metadata = {
            row["key"]: json.loads(row["value"])
            for row in db.execute(
                "SELECT key,value FROM meta WHERE key IN ('selection_sha256','selection','observation_count')"
            )
        }
        existing = metadata.get("selection_sha256")
        saved = metadata.get("selection")
        if (
            existing is not None
            and saved is not None
            and hashlib.sha256(canonical(saved).encode()).hexdigest() != existing
        ):
            raise ForwardError("stored_selection_hash_mismatch")
        has_observations = (
            bool(metadata.get("observation_count", 0))
            or db.execute("SELECT 1 FROM predictions LIMIT 1").fetchone() is not None
        )
        if existing not in (None, sha) and has_observations:
            raise ForwardError("selection_change_refused_after_observations")
        if existing is None and has_observations:
            raise ForwardError("observations_have_no_selection_binding")
        for key, item in (("selection_sha256", sha), ("selection", selection)):
            db.execute(
                "INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, canonical(item)),
            )
    return sha


class ForwardWorker:
    def __init__(
        self, home, selection, *, market=None, clock=time.time, stop_event=None
    ):
        self.store = Store(home)
        self.selection = load_selection(selection)
        self.market = market or LiveMarket(clock=clock)
        self.clock = clock
        self.stop_event = stop_event or threading.Event()
        self.selection_sha256 = None
        self._lock = None
        self.asset_state = {}
        self._observations = 0
        self._recovery_at = {}
        self._recovery_index = {}

    def start(self):
        if self._lock is not None:
            return
        path = self.store.home / "forward.lock"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        lock = os.fdopen(descriptor, "a+")
        try:
            stat = os.fstat(descriptor)
            if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
                raise ForwardError("forward_lock_permissions_invalid")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ForwardError("paper_forward_already_running") from None
            self.selection_sha256 = _freeze(self.store, self.selection)
            self._observations = self.store.meta("observation_count", 0)
            self._lock = lock
            self._heartbeat("starting")
        except BaseException:
            lock.close()
            raise

    def _heartbeat(self, status, error=None):
        self.store.put_meta(
            "heartbeat",
            {
                "at": self.clock(),
                "pid": os.getpid(),
                "status": status,
                "error": error,
                "paper_only": True,
                "venue": VENUE,
                "quote_currency": "USD",
                "selection_sha256": self.selection_sha256,
                "assets": self.asset_state,
            },
        )

    def _quote_valid(self, quote, now, asset):
        if not isinstance(quote, dict) or quote.get("asset") != asset:
            return False
        for key in ("price", "event_at", "observed_at"):
            if type(quote.get(key)) not in (int, float) or not math.isfinite(
                quote[key]
            ):
                return False
        return (
            quote["price"] > 0
            and 0 <= now - quote["event_at"] <= 15
            and 0 <= now - quote["observed_at"] <= 15
        )

    def _emit(self, asset, rules, rows, quote):
        now = self.clock()
        if not self._quote_valid(quote, now, asset):
            raise MarketError("entry_quote_stale_or_invalid")
        for rule in rules:
            minutes = rule["interval_minutes"]
            step = minutes * 60
            target_start = int(now // step) * step
            target_end = target_start + step
            if not 0 <= now - target_start <= 30 or target_end <= now:
                continue
            closed = [row for row in rows if row[0] + 60 <= target_start]
            bars = strategy.candles(closed, minutes)
            if not bars or bars[-1][0] + step != target_start:
                continue
            labels = strategy.shape_labels(bars, minutes)
            event = strategy.setup(bars, labels, len(bars) - 1, minutes)
            if (
                event is None
                or event["signal_available_at"] != target_start
                or not strategy.matches(event, rule)
            ):
                continue
            decision_at = self.clock()
            if not 0 <= decision_at - target_start <= 30 or not self._quote_valid(
                quote, decision_at, asset
            ):
                continue
            identity = hashlib.sha256(
                canonical(
                    [self.selection_sha256, asset, rule["id"], target_start, target_end]
                ).encode()
            ).hexdigest()
            # This transaction commits before the worker inspects outcomes.
            self.store.add_prediction(
                {
                    "id": identity,
                    "asset": asset,
                    "rule_id": rule["id"],
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision_at": decision_at,
                    "entry_price": quote["price"],
                    "entry_time": quote["event_at"],
                    "direction": rule["direction"],
                    "rule_json": canonical(
                        {
                            "rule": rule,
                            "setup": event,
                            "quote": quote,
                            "selection_sha256": self.selection_sha256,
                            "venue_transfer": "Historical study venue differs; unqualified transfer",
                        }
                    ),
                    "status": "open",
                }
            )

    def _settle(self, asset, rows):
        now = self.clock()
        table = {row[0]: row for row in rows}
        waiting = 0
        for pending in self.store.predictions("open"):
            if pending["asset"] != asset or pending["target_end"] > now:
                continue
            minutes = (pending["target_end"] - pending["target_start"]) // 60
            required = [
                table.get(t)
                for t in range(pending["target_start"], pending["target_end"], 60)
            ]
            if any(row is None for row in required):
                waiting += 1
                continue
            target = strategy.candles(required, minutes)
            if len(target) != 1 or target[0][0] != pending["target_start"]:
                waiting += 1
                continue
            ending = target[0][4]
            sign = 1 if pending["direction"] == "UP" else -1
            gross = (ending / pending["entry_price"] - 1) * 10000 * sign
            correct = (
                ending > pending["entry_price"]
                if sign == 1
                else ending < pending["entry_price"]
            )
            self.store.settle(
                pending["id"],
                exit_price=ending,
                correct=correct,
                gross_bps=gross,
                net_bps=gross - 16,
            )
        return waiting

    def _recover_outcome(self, asset, rows):
        """Recover one existing outcome, never generate a missed prediction."""
        now = self.clock()
        if now < self._recovery_at.get(asset, 0) or self.stop_event.is_set():
            return rows, None
        table = {row[0]: row for row in rows}
        pending = []
        for row in self.store.predictions("open"):
            if (
                row["asset"] != asset
                or not now - 86400 <= row["target_start"] < row["target_end"] <= now
            ):
                continue
            if any(
                t not in table or table[t][5] <= 0
                for t in range(row["target_start"], row["target_end"], 60)
            ):
                pending.append(row)
        if not pending:
            return rows, None
        index = self._recovery_index.get(asset, 0) % len(pending)
        selected = pending[index]
        self._recovery_index[asset] = index + 1
        self._recovery_at[asset] = now + 60
        try:
            fetched = self.market.fetch(
                asset,
                selected["target_start"],
                selected["target_end"],
                cancelled=self.stop_event.is_set,
            )
        except MarketError as error:
            return rows, str(error)
        table.update(fetched)
        return [table[t] for t in sorted(table)], None

    def tick(self):
        self.start()
        grouped = {}
        for rule in self.selection["rules"]:
            grouped.setdefault(rule["asset"], []).append(rule)
        self._heartbeat("running")
        for asset, rules in grouped.items():
            if self.stop_event.is_set():
                break
            state = {
                "status": "loading",
                "venue": VENUE,
                "product": f"{asset}-USD",
                "quote_currency": "USD",
            }
            self.asset_state[asset] = state
            self._heartbeat("running")
            try:
                rows = self.market.history(
                    asset,
                    max(rule["interval_minutes"] for rule in rules),
                    cancelled=self.stop_event.is_set,
                )
                if self.stop_event.is_set():
                    break
                self._heartbeat("running")
                quote_error = None
                try:
                    quote = self.market.quote(asset)
                    if self.stop_event.is_set():
                        break
                    now = self.clock()
                    if not self._quote_valid(quote, now, asset):
                        raise MarketError("entry_quote_stale_or_invalid")
                    self._observations += 1
                    self.store.put_meta("observation_count", self._observations)
                    self.store.put_meta(f"last_observation:{asset}", quote)
                    self._emit(asset, rules, rows, quote)
                    state["quote"] = quote
                except MarketError as error:
                    quote_error = str(error)
                if self.stop_event.is_set():
                    break
                rows, outcome_error = self._recover_outcome(asset, rows)
                waiting = self._settle(asset, rows)
                state.update(self.market.cache_status(asset))
                state.update(
                    {
                        "status": "unavailable"
                        if quote_error
                        else "waiting-outcome-data"
                        if waiting
                        else "observing",
                        "pending_missing_outcomes": waiting,
                        "error": quote_error,
                        "outcome_error": outcome_error,
                    }
                )
            except MarketError as error:
                state.update({"status": "unavailable", "error": str(error)})
            except (ValueError, TypeError, KeyError, ArithmeticError):
                state.update(
                    {"status": "unavailable", "error": "causal_model_or_source_invalid"}
                )
            self._heartbeat("running")
        if not grouped:
            self._heartbeat("waiting-no-selected-rules")
        return self.store.meta("heartbeat")

    def close(self, *, error=None):
        if self._lock is None:
            return
        try:
            self._heartbeat("failed" if error else "stopped", error=error)
        finally:
            self._lock.close()
            self._lock = None

    def run(self, *, poll=5, once=False):
        if (
            type(poll) not in (int, float)
            or not math.isfinite(poll)
            or not 0.2 <= poll <= 60
        ):
            raise ForwardError("invalid_forward_poll")
        failure = None
        try:
            self.start()
            while not self.stop_event.is_set():
                self.tick()
                if once:
                    break
                self.stop_event.wait(poll)
        except BaseException:
            failure = "paper_worker_failed"
            raise
        finally:
            self.close(error=failure)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close(error="paper_worker_failed" if exc_type else None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=default_home())
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--poll", type=float, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    stop = threading.Event()
    previous = {}

    def stop_requested(signum, frame):
        stop.set()

    for name in (signal.SIGINT, signal.SIGTERM):
        previous[name] = signal.signal(name, stop_requested)
    try:
        worker = ForwardWorker(args.home, args.selection, stop_event=stop)
        worker.run(poll=args.poll, once=args.once)
    except (ForwardError, MarketError, OSError):
        print(
            canonical(
                {
                    "status": "failed",
                    "message": "Paper worker could not start or continue; inspect owner-only state and configured sources.",
                }
            ),
            flush=True,
        )
        return 1
    finally:
        for name, handler in previous.items():
            signal.signal(name, handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
