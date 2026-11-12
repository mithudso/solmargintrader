from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from botmanager.config import resolve_config
from botmanager.data import load_recording
from botmanager.domain import BotSpec, ManagerError
from botmanager.strategies.grid import evaluate


def recording(root: Path, count: int = 8) -> dict:
    path = root / "recording.jsonl.gz"
    with gzip.open(path, "wt") as out:
        for second in range(count * 60):
            price = [100, 92, 101, 108][(second // 60) % 4]
            out.write(
                json.dumps(
                    {
                        "t": 1700000040 + second,
                        "q": {
                            "SOL-USD": [
                                price - 0.1,
                                price + 0.1,
                                price,
                                10,
                                10,
                                1700000040 + second,
                            ]
                        },
                    }
                )
                + "\n"
            )
    return {
        "schema_version": 1,
        "installation_id": "fixture-recorder",
        "source": "coinbase_exchange_recorder",
        "paths": [str(path)],
        "product": "SOL-USD",
        "quote_currency": "USD",
        "bar_seconds": 60,
        "start_ts": 1700000040,
        "end_ts": 1700000040 + count * 60,
        "fee_bps": 6.0,
        "slippage_bps": 2.0,
        "carry_bps_per_hour": 0.0,
        "min_order_quote": 10.0,
        "capital_quote": 1000.0,
    }


def grid(name="grid"):
    return BotSpec.create(name, "grid", resolve_config("grid", {}, {}, None))


class PaperTests(unittest.TestCase):
    def test_economics_and_prefix_parity(self):
        from dataclasses import asdict

        import numpy as np

        from backtester.core.gridsim import GridConfig, run_grid_backtest
        from backtester.core.types import CostConfig

        with tempfile.TemporaryDirectory() as tmp:
            data = load_recording(recording(Path(tmp)))
            spec = grid()
            actual = evaluate(spec, data, 8)
            expected = run_grid_backtest(
                GridConfig(
                    100 * (1 - 0.15), 100 * (1 + 0.15), 7, 1000 / 7, "geom", 25, 10
                ),
                {
                    k: np.array([b[k] for b in data["bars"]])
                    for k in ("ts", "high", "low", "close")
                },
                initial_capital=1000,
                interval="1m",
                costs=CostConfig(fee_bps=6, slippage_bps=2),
                close_at_end=False,
            )
            self.assertEqual(actual["fills"], [asdict(t) for t in expected.trades])
            self.assertEqual(
                actual["lots"], [asdict(t) for t in expected.open_lots_at_end]
            )
            self.assertAlmostEqual(actual["equity_quote"], expected.equity[-1])
            for count in range(1, 8):
                prefix = evaluate(spec, data, count)
                self.assertEqual(
                    prefix["fills"],
                    [t for t in actual["fills"] if t["bar_index"] < count],
                )
            self.assertEqual(data["identity"]["venue"], "coinbase_proxy")
            self.assertEqual(
                data["identity"]["quote_provenance"],
                "not_recorded_book_or_ticker_unknown",
            )
            self.assertEqual(data["identity"]["quote_currency"], "USD")

    def test_missing_stale_future_gap_and_limit_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = recording(Path(tmp))
            for key, value in [
                ("fee_bps", None),
                ("quote_currency", "USDC"),
                ("end_ts", d["end_ts"] + 60),
                ("max_bars", 2),
            ]:
                with self.subTest(key=key), self.assertRaises(ManagerError):
                    load_recording({**d, key: value})
            path = Path(d["paths"][0])
            with gzip.open(path, "rt") as stream:
                rows = [json.loads(line) for line in stream]
            self.assertGreater(len(rows), 1)
            load_recording(d)  # Complete, current recording is admitted before mutation.
            for age in (20, -1):
                with gzip.open(path, "wt") as out:
                    for row in rows:
                        row["q"]["SOL-USD"][5] = row["t"] - age
                        out.write(json.dumps(row) + "\n")
                with self.assertRaises(ManagerError):
                    load_recording(d)

    def test_relative_grid_preserves_reference_constructor(self):
        import ast

        from backtester.core.gridsim import SPACINGS, GridConfig

        source = Path(__file__).resolve().parents[2] / "soltui" / "bots.py"
        tree = ast.parse(source.read_text())
        function = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "grid_sim_config"
        )
        module = ast.Module(body=[function], type_ignores=[])
        namespace = {"GridConfig": GridConfig, "SPACINGS": SPACINGS, "Any": object}
        exec(compile(module, str(source), "exec"), namespace)  # noqa: S102 -- one tracked pure constructor, no owner imports
        with tempfile.TemporaryDirectory() as tmp:
            data = load_recording(recording(Path(tmp)))
            spec = grid()
            canonical = namespace["grid_sim_config"](
                dict(spec.resolved_values), data["bars"][0]["close"]
            )
            self.assertEqual(
                evaluate(spec, data, 1)["identity"]["grid"], canonical.to_dict()
            )

    def test_engine_identity_change_refuses_replay(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            data = load_recording(recording(Path(tmp)))
            with (
                patch(
                    "botmanager.strategies.grid.engine_identity",
                    return_value={"package": "different"},
                ),
                self.assertRaises(ManagerError) as caught,
            ):
                evaluate(grid(), data, 1)
            self.assertEqual(caught.exception.code, "engine_identity_changed")

    def test_multi_member_capture_and_changed_source_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = recording(Path(tmp))
            path = Path(d["paths"][0])
            with gzip.open(path, "rt") as stream:
                lines = stream.readlines()
            path.write_bytes(
                gzip.compress("".join(lines[:120]).encode())
                + gzip.compress("".join(lines[120:]).encode())
            )
            snapshot = load_recording(d)
            frozen = list(snapshot["bars"])
            with gzip.open(path, "at") as stream:
                stream.write(json.dumps({"t": d["end_ts"] + 10, "q": {}}) + "\n")
            later = load_recording(d)
            self.assertEqual(snapshot["bars"], frozen)
            self.assertEqual(later["bars"], snapshot["bars"])
            self.assertNotEqual(later["snapshot_hash"], snapshot["snapshot_hash"])
            path.write_bytes(gzip.compress("".join(lines).encode())[:-12])
            with self.assertRaises(ManagerError):
                load_recording(d)

    def test_usdc_results_are_not_usd_financials(self):
        import time
        from uuid import uuid4

        from botmanager.ledger import RuntimeLedger
        from botmanager.status import runtime_snapshot

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = recording(root)
            path = Path(d["paths"][0])
            with gzip.open(path, "rt") as stream:
                content = stream.read().replace("SOL-USD", "SOL-USDC")
            with gzip.open(path, "wt") as stream:
                stream.write(content)
            d.update(product="SOL-USDC", quote_currency="USDC")
            data = load_recording(d)
            spec = grid()
            ledger = RuntimeLedger(root)
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            gen = ledger.claim(spec.bot_id, "test")
            ledger.commit_tick(spec.bot_id, gen, 0, evaluate(spec, data, 8))
            status = runtime_snapshot(
                spec,
                ledger.get(spec.bot_id),
                now=time.time(),
                worker_alive=True,
                supervisor_alive=True,
            )
            self.assertEqual(status["reference_financials"]["quote_currency"], "USDC")
            self.assertIsNone(status["financials"]["realized_net_pnl_usd"]["value"])
            self.assertFalse(
                status["evidence"]["paper"]["venue_compatibility_verified"]
            )
