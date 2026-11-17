import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from research.exit50_acquire import fetch_one
from research.exit50_run import slot_data


def payload(count, changed=False):
    first = 60_000_000
    rows = []
    for i in range(count):
        stamp = first + i * 200_000
        rows.append(
            {
                "price_feed_id": 1,
                "publish_time": stamp,
                "feed_update_timestamp": stamp,
                "price": 10_000_000_001 if changed and i == 0 else 10_000_000_000,
                "exponent": -8,
            }
        )
    return json.dumps({"data": rows}).encode()


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.status = 200
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        return self.raw

    def geturl(self):
        return "https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/prices?feedId=1&fromMs=60000&toMs=180000"


class AcquisitionTests(unittest.TestCase):
    def test_partial_retry_preserves_and_marks_conflicting_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with (
                patch(
                    "research.exit50_acquire.urllib.request.urlopen",
                    side_effect=[Response(payload(2)), Response(payload(601, True))],
                ),
                patch("research.exit50_acquire.time.sleep"),
            ):
                result = fetch_one(("BTC", 120, p))
            self.assertEqual(result["attempts"], 2)
            self.assertEqual(result["price_conflict_timestamps"], [60_000_000])
            self.assertTrue((p / "BTC-120.attempt1.body.zlib").exists())
            self.assertFalse(
                any(
                    x["publish_time_us"] == 60_000_000 for x in slot_data(p, "BTC", 120)
                )
            )

    def test_failed_retries_leave_permanent_marker(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with (
                patch(
                    "research.exit50_acquire.urllib.request.urlopen",
                    side_effect=urllib.error.URLError("fixture"),
                ),
                patch("research.exit50_acquire.time.sleep"),
            ):
                result = fetch_one(("BTC", 120, p))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["attempts"], 3)
            self.assertEqual(
                json.loads((p / "BTC-120.meta.json").read_text())["status"], "failed"
            )
            self.assertIsNone(slot_data(p, "BTC", 120))


if __name__ == "__main__":
    unittest.main()
