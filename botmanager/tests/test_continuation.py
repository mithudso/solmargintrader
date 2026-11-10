"""Segment boundaries preserve the canonical economic account and timing."""

from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict

import numpy as np

from backtester.core.dcasim import DcaConfig, run_dca_backtest
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.gridsim import GridConfig, run_grid_backtest
from backtester.core.strategies.signals import TsMomentum
from backtester.core.types import CostConfig
from soltui.trend import TrendConfig, TrendFollowing


def prices(count=2307):
    t = np.arange(count)
    close = 100 + 12 * np.sin(t / 17) + 4 * np.sin(t / 3)
    return {
        "ts": 1700000040 + t * 60,
        "open": close + np.cos(t / 5),
        "high": close + 3,
        "low": close - 3,
        "close": close,
    }


def run(family, arrays, continuation=None, **kwargs):
    costs = CostConfig(fee_bps=6, slippage_bps=2)
    common = dict(
        interval="1m",
        costs=costs,
        close_at_end=False,
        continuation=continuation,
        **kwargs,
    )
    if family == "grid":
        return run_grid_backtest(
            GridConfig(100 * (1 - 0.15), 100 * (1 + 0.15), 7, 1000 / 7, "geom", 25, 10),
            arrays,
            initial_capital=1000,
            **common,
        )
    if family == "dca":
        return run_dca_backtest(DcaConfig(), arrays, initial_capital=1000, **common)
    strategy = (
        TrendFollowing(TrendConfig(7, 31, 15, 1000))
        if family == "trend"
        else TsMomentum(37, 0.001)
    )
    return run_backtest(
        strategy,
        arrays,
        EngineConfig(initial_capital=1000, interval="1m", costs=costs),
        close_at_end=False,
        price_only=True,
        continuation=continuation,
    )


class ContinuationTests(unittest.TestCase):
    def test_segmented_restart_matches_uninterrupted_after_2048_bars(self):
        arrays = prices()
        for family in ("grid", "dca", "trend", "momentum"):
            with self.subTest(family=family):
                full = run(family, arrays)
                checkpoint = None
                trades, equity = [], []
                sizes = []
                for start in range(0, len(arrays["ts"]), 127):
                    result = run(
                        family,
                        {k: v[start : start + 127] for k, v in arrays.items()},
                        checkpoint,
                    )
                    trades.extend(asdict(t) for t in result.trades)
                    equity.extend(result.equity)
                    checkpoint = json.loads(json.dumps(result.continuation))
                    sizes.append(len(json.dumps(checkpoint)))
                self.assertEqual(trades, [asdict(t) for t in full.trades])
                np.testing.assert_array_equal(equity, full.equity)
                if family in ("trend", "momentum"):
                    self.assertEqual(asdict(result.account), asdict(full.account))
                else:
                    for key in (
                        "realized_pnl_usd",
                        "fees_paid_usd",
                        "slippage_paid_usd",
                    ):
                        self.assertEqual(getattr(result, key), getattr(full, key))
                    if family == "grid":
                        self.assertEqual(result.open_lots_at_end, full.open_lots_at_end)
                    else:
                        self.assertEqual(result.open_deal_at_end, full.open_deal_at_end)
                self.assertLess(max(sizes), 30000)
                self.assertEqual(checkpoint["cursor"], len(arrays["ts"]))

    def test_source_gap_duplicate_and_config_tampering_refuse(self):
        arrays = prices(100)
        for family in ("grid", "dca", "trend", "momentum"):
            with self.subTest(family=family):
                checkpoint = run(
                    family, {k: v[:50] for k, v in arrays.items()}
                ).continuation
                for start in (49, 51):
                    with self.assertRaisesRegex(ValueError, "source gap"):
                        run(
                            family,
                            {k: v[start:] for k, v in arrays.items()},
                            checkpoint,
                        )
                changed = copy.deepcopy(checkpoint)
                changed["binding"] = "changed engine/config"
                with self.assertRaisesRegex(ValueError, "configuration changed"):
                    run(family, {k: v[50:] for k, v in arrays.items()}, changed)

    def test_pause_entries_preserves_exits(self):
        arrays = prices(120)
        for family in ("grid", "dca"):
            checkpoint = run(
                family, {k: v[:70] for k, v in arrays.items()}
            ).continuation
            result = run(
                family,
                {k: v[70:] for k, v in arrays.items()},
                checkpoint,
                entries_paused=True,
            )
            self.assertFalse(any(t.side == "buy" for t in result.trades))
            self.assertTrue(any(t.side == "sell" for t in result.trades))

    def test_prospective_segments_archive_atomically_and_restart(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from uuid import uuid4

        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec, ManagerError, fingerprint
        from botmanager.ledger import RuntimeLedger
        from botmanager.oracle_data import capture, prepare_descriptor
        from botmanager.worker import prospective_tick

        from tests.test_oracle_data import START, archive

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oracle.sqlite3"
            archive(path, 60)
            descriptor = prepare_descriptor(
                path, capital_quote=1000, strategy_id="grid", now=START + 60
            )
            data = capture(descriptor, now=START + 60)
            base = descriptor["activation_watermark"]
            origin = descriptor["start_ts"]
            count = 2307
            cursor = base

            def page(_path, *, after, now, **unused):
                nonlocal cursor
                end = min(after + 1536, base + count * 12 + 1)
                points = []
                for sequence in range(after + 1, end + 1):
                    t = origin + (sequence - base - 1) * 5
                    bar = (t - origin) // 60
                    price = float(100 + 12 * np.sin(bar / 17) + 4 * np.sin(bar / 3))
                    observation = {
                        "event_id": f"p-{sequence}",
                        "source": "coinbase_recorder",
                        "venue": "coinbase_exchange",
                        "instrument": "SOL/USD",
                        "kind": "stream_snapshot_mid",
                        "observed_at": t,
                        "received_at": t,
                        "price": price,
                    }
                    points.append(
                        {
                            "sequence": sequence,
                            "sha256": fingerprint(observation),
                            "observation": observation,
                        }
                    )
                cursor = end
                return {
                    "policy_hash": descriptor["policy_hash"],
                    "high_watermark": end,
                    "observations": points,
                    "latest_observed": now,
                    "latest_received": now,
                }

            spec = BotSpec.create(
                "continued", "grid", resolve_config("grid", {}, {}, None)
            )
            ledger = RuntimeLedger(Path(tmp) / "manager")
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            generation = ledger.claim(spec.bot_id, "owner")
            crashed = False
            with patch("botmanager.oracle_data.read_page", side_effect=page):
                while ledger.get(spec.bot_id)["cursor"] < count:
                    row = ledger.get(spec.bot_id)
                    now = origin + min(count * 60, (cursor - base + 1536) * 5)
                    if len(row["input"]["bars"]) >= 512 and not crashed:
                        with self.assertRaisesRegex(RuntimeError, "crash"):
                            prospective_tick(
                                ledger,
                                row,
                                generation,
                                now=now,
                                before_commit=lambda: (_ for _ in ()).throw(
                                    RuntimeError("crash")
                                ),
                            )
                        self.assertEqual(ledger.get(spec.bot_id)["input"], row["input"])
                        ledger.recover("restarted")
                        generation = ledger.claim(spec.bot_id, "restarted")
                        row = ledger.get(spec.bot_id)
                        crashed = True
                    prospective_tick(ledger, row, generation, now=now)
                    restarted = RuntimeLedger(ledger.home).get(spec.bot_id)
                    self.assertLessEqual(len(restarted["input"]["bars"]), 640)
                    self.assertLess(len(json.dumps(restarted["checkpoint"])), 250000)
            row = ledger.get(spec.bot_id)
            self.assertTrue(crashed)
            self.assertEqual(row["cursor"], count)
            t = np.arange(count)
            close = 100 + 12 * np.sin(t / 17) + 4 * np.sin(t / 3)
            expected = run(
                "grid",
                {
                    "ts": origin + t * 60,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                },
            )
            self.assertEqual(
                ledger.fills(spec.bot_id), [asdict(t) for t in expected.trades]
            )
            self.assertEqual(row["checkpoint"]["equity_quote"], expected.equity[-1])
            self.assertEqual(row["checkpoint"]["fees_quote"], expected.fees_paid_usd)
            with ledger.connection(True) as db:
                self.assertGreater(
                    db.execute("SELECT count(*) FROM segments").fetchone()[0], 2
                )
                db.execute(
                    "DELETE FROM segments WHERE digest=?",
                    (row["input"]["prior_segment"],),
                )
            with self.assertRaises(ManagerError):
                ledger.get(spec.bot_id)

    def test_dispatcher_continues_every_supported_family_without_prefix_replay(self):
        import tempfile
        from pathlib import Path

        from botmanager.config import resolve_config
        from botmanager.data import load_recording
        from botmanager.domain import BotSpec, fingerprint
        from botmanager.strategies import evaluate

        from tests.test_paper import recording

        arrays = prices()
        with tempfile.TemporaryDirectory() as tmp:
            for family in ("grid", "dca", "trend", "momentum"):
                overrides = (
                    {"fast_period": 7, "slow_period": 31, "entry_buffer_bps": 15}
                    if family == "trend"
                    else (
                        {"window": 37, "threshold": 0.001}
                        if family == "momentum"
                        else {}
                    )
                )
                spec = BotSpec.create(
                    family, family, resolve_config(family, {}, overrides, None)
                )
                base = load_recording(recording(Path(tmp), 8), strategy_id=family)
                checkpoint = None
                trades = []
                for start in range(0, len(arrays["ts"]), 128):
                    data = copy.deepcopy(base)
                    data.update(
                        origin_hash=base["snapshot_hash"],
                        bar_offset=start,
                        origin_close=float(arrays["close"][0]),
                        prior_segment=str(start) if start else None,
                        bars=[
                            {k: v.item() for k, v in zip(arrays, row)}
                            for row in zip(
                                *(v[start : start + 128] for v in arrays.values())
                            )
                        ],
                    )
                    data["snapshot_hash"] = fingerprint(
                        {k: v for k, v in data.items() if k != "snapshot_hash"}
                    )
                    checkpoint = evaluate(
                        spec, data, start + len(data["bars"]), previous=checkpoint
                    )
                    checkpoint = json.loads(json.dumps(checkpoint))
                    trades.extend(checkpoint["fills"])
                expected = run(family, arrays)
                self.assertEqual(trades, [asdict(t) for t in expected.trades])
                self.assertEqual(checkpoint["equity_quote"], expected.equity[-1])
                self.assertEqual(data["descriptor"]["capital_quote"], 1000)

    def test_flat_rebind_preserves_account_and_refuses_unobserved_warmup(self):
        import tempfile
        from pathlib import Path

        from botmanager.config import resolve_config
        from botmanager.data import load_recording
        from botmanager.domain import BotSpec, ManagerError, fingerprint
        from botmanager.strategies import evaluate, rebind_checkpoint

        from tests.test_paper import recording

        with tempfile.TemporaryDirectory() as tmp:
            for family, change in (
                ("grid", {"range_pct": 10}),
                ("dca", {"take_profit_pct": 2}),
                ("trend", {"entry_buffer_bps": 20}),
                ("momentum", {"threshold": 0.002}),
            ):
                spec = BotSpec.create(
                    family, family, resolve_config(family, {}, {}, None)
                )
                data = load_recording(recording(Path(tmp), 80), strategy_id=family)
                for bar in data["bars"]:
                    bar.update(open=100, high=100, low=100, close=100)
                data["snapshot_hash"] = fingerprint(
                    {k: v for k, v in data.items() if k != "snapshot_hash"}
                )
                before = evaluate(
                    spec, data, 70, entries_paused=family in ("grid", "dca")
                )
                updated = spec.edited(change)
                after = rebind_checkpoint(updated, data, before, entries_paused=True)
                self.assertNotEqual(after["run_hash"], before["run_hash"])
                for key in before:
                    if key not in ("identity", "run_hash", "continuation"):
                        self.assertEqual(after[key], before[key])
                resumed = evaluate(updated, data, 80, previous=after)
                self.assertEqual(resumed["cursor"], 80)
                with self.assertRaises(ManagerError):
                    rebind_checkpoint(updated, data, before, entries_paused=False)
                if family in ("trend", "momentum"):
                    larger = spec.edited(
                        {"slow_period": 200} if family == "trend" else {"window": 200}
                    )
                    with self.assertRaisesRegex(
                        ManagerError, "retained observed history"
                    ):
                        rebind_checkpoint(larger, data, before, entries_paused=True)

    def test_grid_rollover_commits_empty_waiting_segment_and_resumes_same_account(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from uuid import uuid4

        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec, fingerprint
        from botmanager.ledger import RuntimeLedger
        from botmanager.oracle_data import capture, prepare_descriptor
        from botmanager.worker import prospective_tick

        from tests.test_oracle_data import START, archive

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oracle.sqlite3"
            archive(path, 60)
            descriptor = prepare_descriptor(
                path, capital_quote=1000, strategy_id="grid", now=START + 60
            )
            data = capture(descriptor, now=START + 60)
            base, origin = descriptor["activation_watermark"], descriptor["start_ts"]
            completed = 512

            def page(_path, *, after, now, **unused):
                end = min(after + 1536, base + completed * 12 + 1)
                points = []
                for sequence in range(after + 1, end + 1):
                    observed = origin + (sequence - base - 1) * 5
                    bar = (observed - origin) // 60
                    price = float(100 + 12 * np.sin(bar / 17) + 4 * np.sin(bar / 3))
                    observation = {
                        "event_id": f"p-{sequence}",
                        "source": "coinbase_recorder",
                        "venue": "coinbase_exchange",
                        "instrument": "SOL/USD",
                        "kind": "stream_snapshot_mid",
                        "observed_at": observed,
                        "received_at": observed,
                        "price": price,
                    }
                    points.append(
                        {
                            "sequence": sequence,
                            "sha256": fingerprint(observation),
                            "observation": observation,
                        }
                    )
                return {
                    "policy_hash": descriptor["policy_hash"],
                    "high_watermark": end,
                    "observations": points,
                    "latest_observed": now,
                    "latest_received": now,
                }

            spec = BotSpec.create(
                "empty-boundary", "grid", resolve_config("grid", {}, {}, None)
            )
            from botmanager.store import ManagerStore

            ledger = RuntimeLedger(Path(tmp) / "manager")
            manager = ManagerStore(ledger.home)
            manager.create_spec(spec)
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            generation = ledger.claim(spec.bot_id, "owner")
            now = origin + 512 * 60 + 1
            with patch("botmanager.oracle_data.read_page", side_effect=page):
                while ledger.get(spec.bot_id)["cursor"] < 512:
                    prospective_tick(
                        ledger, ledger.get(spec.bot_id), generation, now=now
                    )
                before = ledger.get(spec.bot_id)
                self.assertEqual(len(before["input"]["bars"]), 512)
                prospective_tick(ledger, before, generation, now=now)
                boundary = RuntimeLedger(ledger.home).get(spec.bot_id)
                self.assertEqual(boundary["input"]["bars"], [])
                self.assertEqual(boundary["input"]["bar_offset"], 512)
                self.assertEqual(
                    boundary["input"]["prospective"]["health"],
                    "waiting_for_completed_bin",
                )
                self.assertEqual(
                    boundary["input"]["prior_segment"],
                    fingerprint(
                        {"input": before["input"], "checkpoint": before["checkpoint"]}
                    ),
                )
                for key, value in before["checkpoint"].items():
                    if key not in ("fills", "prior_segment"):
                        self.assertEqual(boundary["checkpoint"][key], value)
                self.assertEqual(
                    ledger.fills(spec.bot_id), before["checkpoint"]["fills"]
                )
                # Public reads use the pinned active account, even after a
                # conflicting saved draft. They must never replay a fresh prefix.
                manager.edit(
                    spec.bot_id,
                    {"capital_usd": 2000},
                    expected_revision=1,
                    request_id=str(uuid4()),
                )

                def public_read_check(row):
                    from botmanager.registry import CommandContext, dispatch

                    files = {
                        name: (ledger.home / name).read_bytes()
                        for name in ("manager.sqlite3", "runtime.sqlite3")
                    }
                    current = row["input"]["prospective"]
                    source = {
                        "policy_hash": descriptor["policy_hash"],
                        "high_watermark": current["cursor"],
                        "latest_observed": now,
                        "latest_received": now,
                        "read_at": now,
                    }
                    with (
                        patch(
                            "botmanager.input_commands.read_page", return_value=source
                        ),
                        patch("botmanager.input_commands.time.time", return_value=now),
                        patch(
                            "botmanager.strategies.evaluate",
                            side_effect=AssertionError(
                                "data-check replayed a fresh account"
                            ),
                        ),
                    ):
                        answer = dispatch(
                            "data-check",
                            {"identity": spec.bot_id},
                            CommandContext(home=ledger.home),
                        )
                    self.assertTrue(answer["ok"], answer)
                    self.assertTrue(answer["data"]["compatible"], answer)
                    self.assertEqual(ledger.get(spec.bot_id), row)
                    for name, content in files.items():
                        self.assertEqual((ledger.home / name).read_bytes(), content)

                public_read_check(boundary)
                from botmanager.domain import ManagerError

                fresh = RuntimeLedger(Path(tmp) / "must-not-reset")
                with self.assertRaises(ManagerError) as error:
                    fresh.register(spec, boundary["input"])
                self.assertEqual(error.exception.code, "reconciliation_required")
                self.assertFalse(fresh.path.exists())
                ledger.recover("boundary-restart")
                generation = ledger.claim(spec.bot_id, "boundary-restart")
                completed = 513
                prospective_tick(
                    ledger,
                    ledger.get(spec.bot_id),
                    generation,
                    now=origin + 513 * 60 + 1,
                )
            resumed = ledger.get(spec.bot_id)
            self.assertEqual(resumed["cursor"], 513)
            public_read_check(resumed)
            t = np.arange(513)
            close = 100 + 12 * np.sin(t / 17) + 4 * np.sin(t / 3)
            full = run(
                "grid",
                {
                    "ts": origin + t * 60,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                },
            )
            self.assertEqual(
                ledger.fills(spec.bot_id), [asdict(trade) for trade in full.trades]
            )
            self.assertEqual(resumed["checkpoint"]["equity_quote"], full.equity[-1])
            self.assertEqual(
                resumed["checkpoint"]["lots"],
                [asdict(lot) for lot in full.open_lots_at_end],
            )

    def test_draft_extremes_refuse_before_runtime_allocation_source_research_or_adoption(
        self,
    ):
        from unittest.mock import patch

        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec, ManagerError
        from botmanager.input_commands import check, prepare
        from botmanager.learning import learned_spec, shadow_pair
        from botmanager.research import candidate_spec, candidates, execute
        from botmanager.strategies import (
            evaluate,
            rebind_checkpoint,
            validate_registration,
            validate_runtime_config,
        )

        for family, field in (("trend", "slow_period"), ("momentum", "window")):
            for lookback in (2049, 1_000_000_000):
                spec = BotSpec.create(
                    family, family, resolve_config(family, {}, {field: lookback}, None)
                )
                self.assertEqual(
                    spec.resolved_values[field], lookback
                )  # retained editable draft
                with (
                    patch(
                        "numpy.array",
                        side_effect=AssertionError("allocation before guard"),
                    ),
                    patch(
                        "botmanager.input_commands.prepare_descriptor",
                        side_effect=AssertionError("source capture before guard"),
                    ),
                ):
                    for action in (
                        lambda spec=spec: validate_runtime_config(spec),
                        lambda spec=spec: validate_registration(spec, None),
                        lambda spec=spec: evaluate(spec, None, 1, research=True),
                        lambda spec=spec: rebind_checkpoint(
                            spec, None, None, entries_paused=True
                        ),
                        lambda spec=spec: prepare(spec, {}, {}),
                        lambda spec=spec: candidate_spec(spec, {}),
                        lambda spec=spec: candidates(spec, {}),
                        lambda spec=spec: execute(None, spec, None, {}),
                    ):
                        with self.assertRaises(ManagerError) as error:
                            action()
                        self.assertEqual(error.exception.code, "resource_limit")
                    diagnosed = check(spec, descriptor_path="/absent/not-read")
                    self.assertFalse(diagnosed["compatible"])
                    self.assertEqual(diagnosed["reason"], "resource_limit")
            baseline = BotSpec.create(
                family, family, resolve_config(family, {}, {}, None)
            )
            for action in (
                lambda baseline=baseline, field=field: candidate_spec(
                    baseline, {field: 1_000_000_000}
                ),
                lambda baseline=baseline, field=field: learned_spec(
                    baseline, {field: 1_000_000_000}, "evidence"
                ),
                lambda baseline=baseline, field=field: shadow_pair(
                    "/absent/not-created",
                    baseline,
                    {field: 1_000_000_000},
                    "evidence",
                    {},
                ),
            ):
                with self.assertRaises(ManagerError) as error:
                    action()
                self.assertEqual(error.exception.code, "resource_limit")

    def test_at_limit_manager_tail_and_checkpoint_stay_bounded_across_many_segments(
        self,
    ):
        import tempfile
        from pathlib import Path

        from botmanager.config import resolve_config
        from botmanager.data import load_recording
        from botmanager.domain import BotSpec, ManagerError, fingerprint
        from botmanager.strategies import (
            MAX_RUNTIME_LOOKBACK_BARS,
            MAX_RUNTIME_RETAINED_BARS,
            evaluate,
            rebind_checkpoint,
            validate_runtime_config,
        )

        from tests.test_paper import recording

        arrays = prices(4353)
        with tempfile.TemporaryDirectory() as tmp:
            for family, field in (("trend", "slow_period"), ("momentum", "window")):
                spec = BotSpec.create(
                    family,
                    family,
                    resolve_config(
                        family, {}, {field: MAX_RUNTIME_LOOKBACK_BARS}, None
                    ),
                )
                validate_runtime_config(spec)
                base = load_recording(recording(Path(tmp), 8), strategy_id=family)
                checkpoint = None
                for start in range(0, len(arrays["ts"]), 128):
                    data = copy.deepcopy(base)
                    data.update(
                        origin_hash=base["snapshot_hash"],
                        bar_offset=start,
                        prior_segment=str(start) if start else None,
                        bars=[
                            {key: value.item() for key, value in zip(arrays, row)}
                            for row in zip(
                                *(
                                    values[start : start + 128]
                                    for values in arrays.values()
                                )
                            )
                        ],
                    )
                    data["snapshot_hash"] = fingerprint(
                        {
                            key: value
                            for key, value in data.items()
                            if key != "snapshot_hash"
                        }
                    )
                    checkpoint = evaluate(
                        spec, data, start + len(data["bars"]), previous=checkpoint
                    )
                    checkpoint = json.loads(json.dumps(checkpoint))
                    self.assertLessEqual(
                        len(checkpoint["continuation"]["tail"]["ts"]),
                        MAX_RUNTIME_RETAINED_BARS,
                    )
                    self.assertLess(len(json.dumps(checkpoint)), 400000)
                saved = copy.deepcopy(checkpoint)
                with self.assertRaises(ManagerError) as error:
                    rebind_checkpoint(
                        spec.edited({field: 1_000_000_000}),
                        data,
                        checkpoint,
                        entries_paused=True,
                    )
                self.assertEqual(error.exception.code, "resource_limit")
                self.assertEqual(checkpoint, saved)
                expected_tail = 2048 if family == "trend" else 2050
                self.assertEqual(
                    len(checkpoint["continuation"]["tail"]["ts"]), expected_tail
                )

    def test_legacy_unsupported_runtime_cannot_be_admitted_but_can_be_stopped(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from uuid import uuid4

        from botmanager.config import resolve_config
        from botmanager.data import load_recording
        from botmanager.domain import BotSpec, ManagerError
        from botmanager.ledger import RuntimeLedger

        from tests.test_paper import recording

        with tempfile.TemporaryDirectory() as tmp:
            spec = BotSpec.create(
                "old-huge-lookback",
                "momentum",
                resolve_config("momentum", {}, {"window": 1_000_000_000}, None),
            )
            data = load_recording(recording(Path(tmp), 8), strategy_id="momentum")
            ledger = RuntimeLedger(Path(tmp) / "manager")
            # Seed the state an older manager could register; the current public
            # registration guard rejects this same draft before opening a store.
            with patch("botmanager.strategies.validate_registration"):
                ledger.register(spec, data)
            with self.assertRaises(ManagerError) as error:
                ledger.control(spec, "start", str(uuid4()))
            self.assertEqual(error.exception.code, "resource_limit")
            self.assertEqual(ledger.get(spec.bot_id)["desired"], "stopped")
            with ledger.connection() as db:
                self.assertEqual(
                    db.execute("SELECT count(*) FROM requests").fetchone()[0], 0
                )
            self.assertEqual(
                ledger.control(spec, "stop", str(uuid4()))["outcome"], "skipped"
            )

    def test_direct_research_owner_refuses_extremes_before_temporal_exposure(self):
        from unittest.mock import patch

        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec

        from soltui.experiments import ExperimentError, ExperimentStore
        from soltui.research_owner import handle
        from soltui.tests.test_research_owner import OwnerProtocolTests

        fixture = OwnerProtocolTests(
            "test_inert_status_does_not_initialize_absent_owner"
        )
        fixture.setUp()
        try:
            ExperimentStore(fixture.authority)
            fixture.bind()
            for operation, spec, options in (
                (
                    "backtest",
                    BotSpec.create(
                        "huge",
                        "momentum",
                        resolve_config("momentum", {}, {"window": 1_000_000_000}, None),
                    ),
                    None,
                ),
                (
                    "research",
                    BotSpec.create(
                        "normal", "momentum", resolve_config("momentum", {}, {}, None)
                    ),
                    {"ranges": {"window": [1_000_000_000]}},
                ),
            ):
                params = {
                    "spec": spec.to_dict(),
                    "descriptor": {"start_ts": 1700000040, "end_ts": 1700000640},
                }
                if options is not None:
                    params["options"] = options
                with (
                    patch.object(
                        ExperimentStore,
                        "manager_pre_read",
                        side_effect=AssertionError("temporal exposure before guard"),
                    ),
                    patch(
                        "botmanager.data.load_recording",
                        side_effect=AssertionError("source read before guard"),
                    ),
                    self.assertRaisesRegex(ExperimentError, "resource_limit"),
                ):
                    handle(
                        {
                            **fixture.request,
                            "operation": operation,
                            "params": params,
                        }
                    )
            with ExperimentStore(fixture.authority)._connect() as db:
                self.assertEqual(
                    db.execute("SELECT count(*) FROM manager_exposures").fetchone()[0],
                    0,
                )
                self.assertEqual(
                    db.execute("SELECT count(*) FROM manager_attempts").fetchone()[0], 0
                )
        finally:
            fixture.doCleanups()
