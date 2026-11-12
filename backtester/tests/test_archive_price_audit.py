"""Unusable provider observations cannot poison the append-only spot archive."""

from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backtester.core import archive_price as archive


class ArchivePriceTests(unittest.TestCase):
    def _fetch(self, payload):
        @contextmanager
        def response(*_args, **_kwargs):
            yield io.BytesIO(json.dumps(payload).encode())
        with patch.object(archive.urllib.request, "urlopen", response):
            return archive.fetch_spot("fixture")

    def test_provider_refuses_nonfinite_boolean_or_malformed_price(self):
        for value in [float("inf"), float("nan"), True, False, -1, 0, None, "1.2", 10 ** 1000]:
            with self.subTest(value=value), self.assertRaises(archive.ArchiveError):
                self._fetch({"fixture": {"usdPrice": value}})

    def test_provider_refuses_nonobject_envelope(self):
        for payload in [[], None, "malformed", 3]:
            with self.subTest(payload=payload), self.assertRaises(archive.ArchiveError):
                self._fetch(payload)

    def test_direct_append_refuses_invalid_price_before_mutating_file(self):
        for value in [float("inf"), float("nan"), True, -1, 0, "1.2", 10 ** 1000]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / "archive.csv"
                original = b"existing archive\n"
                destination.write_bytes(original)
                with self.assertRaises(archive.ArchiveError):
                    archive.append_observation(destination, "fixture", value)
                self.assertEqual(destination.read_bytes(), original)

    def test_valid_provider_price_and_append_remain_available(self):
        self.assertEqual(self._fetch({"fixture": {"usdPrice": 1.25}}), 1.25)
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "archive.csv"
            archive.append_observation(destination, "fixture", 1.25)
            self.assertEqual(archive.count_rows(destination), 1)
            self.assertIn(",fixture,1.25,jupiter-price-v3", destination.read_text())


if __name__ == "__main__":
    unittest.main()
