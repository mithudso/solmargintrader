import hashlib
import json
import tempfile
import unittest
import zlib
from pathlib import Path

from research.exit50_backtest import replay
from research.exit50_run import (
    btc_taker_filter,
    minute_reader,
    price_int,
    slot_data,
    verify_wave_joins,
)


class RawEvidenceTests(unittest.TestCase):
    def test_future_gap_does_not_hide_valid_terminal_prefix(self):
        slot = 120
        stamp = (slot - 60) * 1_000_000
        rows = []
        for i in range(6):
            rows.append(
                {
                    "price_feed_id": 1,
                    "publish_time": stamp + i * 200_000,
                    "feed_update_timestamp": stamp + i * 200_000,
                    "price": 10_000_000_000 if i < 5 else 10_009_800_000,
                    "exponent": -8,
                }
            )
        rows.append(
            {
                "price_feed_id": 1,
                "publish_time": stamp + 80_000_000,
                "feed_update_timestamp": stamp + 80_000_000,
                "price": 0,
                "exponent": -8,
            }
        )
        raw = json.dumps({"data": rows}).encode()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "BTC-120.json.zlib").write_bytes(zlib.compress(raw))
            (p / "BTC-120.meta.json").write_text(
                json.dumps({"sha256": hashlib.sha256(raw).hexdigest()})
            )
            points = slot_data(p, "BTC", slot)
        samples = [(x["publish_time_us"], price_int(x["price"])) for x in points]
        result = replay(stamp - 200_000, stamp + 20_000_000, samples, {}, "fixed", 10)
        self.assertEqual(result["status"], "liquidated")
        self.assertEqual(result["exit_us"], stamp + 1_000_000)

    def test_conflict_invalidates_only_its_own_grid_point(self):
        stamp = 60_000_000
        rows = [
            {
                "price_feed_id": 1,
                "publish_time": stamp + i * 200_000,
                "feed_update_timestamp": stamp + i * 200_000,
                "price": 10_000_000_000 if i != 5 else 10_009_800_000,
                "exponent": -8,
            }
            for i in range(8)
        ]
        raw = json.dumps({"data": rows}).encode()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "BTC-120.json.zlib").write_bytes(zlib.compress(raw))
            for offset, expected in ((1_200_000, "liquidated"), (400_000, "unscored")):
                (p / "BTC-120.meta.json").write_text(
                    json.dumps(
                        {
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "price_conflict_timestamps": [stamp + offset],
                        }
                    )
                )
                samples = [
                    (x["publish_time_us"], price_int(x["price"]))
                    for x in slot_data(p, "BTC", 120)
                ]
                result = replay(
                    stamp - 200_000, stamp + 20_000_000, samples, {}, "fixed", 10
                )
                self.assertEqual(result["status"], expected)

    def test_malformed_hash_verified_response_is_missing_grid(self):
        raw = b"{bad json"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "BTC-120.json.zlib").write_bytes(zlib.compress(raw))
            (p / "BTC-120.meta.json").write_text(
                json.dumps({"sha256": hashlib.sha256(raw).hexdigest()})
            )
            self.assertEqual(slot_data(p, "BTC", 120), [])

    def test_archived_conflict_ledger_removes_only_marked_point(self):
        stamp = 60_000_000
        rows = [
            {
                "price_feed_id": 1,
                "publish_time": stamp + i * 200_000,
                "feed_update_timestamp": stamp + i * 200_000,
                "price": 10_000_000_000,
                "exponent": -8,
            }
            for i in range(3)
        ]
        raw = json.dumps({"data": rows}).encode()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "BTC-120.json.zlib").write_bytes(zlib.compress(raw))
            (p / "BTC-120.meta.json").write_text(
                json.dumps({"sha256": hashlib.sha256(raw).hexdigest()})
            )
            (p / "conflicts.json").write_text(
                json.dumps({"conflicts": [{"asset": "BTC", "stamp": stamp + 200_000}]})
            )
            points = minute_reader("BTC", p, p)(60)
            self.assertEqual([x[0] for x in points], [stamp, stamp + 400_000])

    def test_taker_filter_uses_available_closed_minute_only(self):
        doc = {
            "schema": "binance-btc-taker-quote-pressure/v1",
            "rows": [
                {"available_at_ms": 60000, "sma3": None},
                {"available_at_ms": 120000, "sma3": -0.1},
                {"available_at_ms": 180000, "sma3": 0.2},
            ],
        }
        flow = btc_taker_filter(doc)
        self.assertNotIn(60, flow)
        self.assertTrue(flow[120])
        self.assertFalse(flow[180])

    def test_cross_window_conflicts_are_exact_timestamps(self):
        stamp = 180_000_000

        def raw(price):
            return json.dumps(
                {
                    "data": [
                        {
                            "price_feed_id": 1,
                            "publish_time": stamp,
                            "feed_update_timestamp": stamp,
                            "price": price,
                            "exponent": -8,
                        }
                    ]
                }
            ).encode()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wave = root / "wave"
            entry = root / "entry"
            cache = root / "cache"
            for d in (wave, entry, cache):
                d.mkdir()
            for d, slot, price in (
                (wave, 120, 10_000_000_000),
                (entry, 240, 10_000_000_001),
            ):
                body = raw(price)
                (d / f"BTC-{slot}.json.zlib").write_bytes(zlib.compress(body))
                (d / f"BTC-{slot}.meta.json").write_text(
                    json.dumps({"sha256": hashlib.sha256(body).hexdigest()})
                )
            (wave / "manifest.json").write_text(
                json.dumps({"records": [{"asset": "BTC", "slot": 120}]})
            )
            proof = verify_wave_joins(wave, entry, cache)
            self.assertEqual(proof["join_points_checked"], 1)
            self.assertEqual(proof["conflicts"][0]["stamp"], stamp)

    def test_rejects_nonrepresentable_price(self):
        with self.assertRaises(ValueError):
            price_int("0.0000000000001")


if __name__ == "__main__":
    unittest.main()
