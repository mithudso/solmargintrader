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
