"""Preflight and report regressions use generated artifacts and fake clients only."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mongo import load, schema


class ObservationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        (self.root / "results").mkdir()
        self.enterContext(mock.patch.object(load, "REPO", self.root))

    def context(
        self,
        *,
        equity="timestamp,equity\n60,100\n",
        trades="ts,side,price\n60,buy,100\n",
    ):
        contents = {"equity_s.csv": equity, "trades_s.csv": trades}
        for name, body in contents.items():
            (self.root / "results" / name).write_text(body)
        return (
            {
                "strategies": ["s"],
                "asset": "SOL",
                "interval": "1d",
                "mode": "spot",
                "artifact_sha256": {
                    name: hashlib.sha256(body.encode()).hexdigest()
                    for name, body in contents.items()
                },
            },
            {
                "source_path": "results/run_manifest.json",
                "source_sha256": "fixture",
                "loaded_at": load.LOADED_AT,
            },
        )

    def test_invalid_observation_times_refuse_before_connect_or_drop(self):
        for collection, header in [
            ("trades", "ts,side,price"),
            ("equity_points", "timestamp,equity"),
        ]:
            for timestamp in ("", "nan", "infinity", "bad-time"):
                body = (
                    header
                    + "\n"
                    + timestamp
                    + (",buy,100\n" if collection == "trades" else ",100\n")
                )
                context = self.context(
                    **({"trades": body} if collection == "trades" else {"equity": body})
                )
                with (
                    self.subTest(collection=collection, timestamp=timestamp),
                    mock.patch.object(load, "run_context", return_value=context),
                    mock.patch.object(load, "connect") as connect,
                    mock.patch.object(load, "create") as create,
                    self.assertRaisesRegex(
                        ValueError, r"CSV row 2: missing or invalid timestamp"
                    ),
                ):
                    load.main(["--only", collection])
                connect.assert_not_called()
                create.assert_not_called()

    def test_integer_form_trade_price_is_normalized_to_schema_double(self):
        docs = load.load_trades(run_snapshot=self.context())
        self.assertIs(type(docs[0]["price"]), float)
        self.assertEqual(docs[0]["price"], 100.0)
        schema.validate_batches({"trades": docs})
        docs[0]["price"] = 100
        with self.assertRaisesRegex(ValueError, "price"):
            schema.validate_batches({"trades": docs})

    def test_preflight_rejects_batch_before_database_mutation(self):
        docs = load.load_trades(run_snapshot=self.context())
        docs[0]["price"] = True
        with (
            mock.patch.object(load, "build_all", return_value={"trades": docs}),
            mock.patch.object(load, "connect") as connect,
            mock.patch.object(load, "create") as create,
            self.assertRaisesRegex(ValueError, "price"),
        ):
            load.main(["--only", "trades"])
        connect.assert_not_called()
        create.assert_not_called()

    def test_time_series_preflight_requires_timestamp_and_meta(self):
        for doc in (
            {},
            {"ts": "60", "curve": {}, "loaded_at": load.LOADED_AT},
            {"ts": load.LOADED_AT, "curve": "wrong", "loaded_at": load.LOADED_AT},
        ):
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                schema.validate_batches({"equity_points": [doc]})

    def test_empty_proven_artifacts_remain_valid(self):
        context = self.context(equity="timestamp,equity\n", trades="ts,side,price\n")
        batches = {
            "equity_points": load.load_equity_points(run_snapshot=context),
            "trades": load.load_trades(run_snapshot=context),
        }
        self.assertEqual(batches, {"equity_points": [], "trades": []})
        schema.validate_batches(batches)
