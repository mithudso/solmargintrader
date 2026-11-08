"""Non-Coinbase 1m fetcher: venue row orders, sanity abort, backward paging, resume, manifest."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backtester.core import fetch_minutes as fm
from backtester.core import fetch_minutes_alt as alt

NOW = 1_800_000_000  # a minute boundary


class ParserTests(unittest.TestCase):
    def test_close_before_high_venues_are_reordered(self) -> None:
        # KuCoin/WhiteBIT: [t, open, CLOSE, high, low, vol, ...]
        k = alt._kucoin_rows({"code": "200000", "data": [["60", "10", "11", "12", "9", "5", "50"]]})
        w = alt._whitebit_rows({"success": True, "result": [[60, "10", "11", "12", "9", "5", "50"]]})
        self.assertEqual(k, [[60, 10.0, 12.0, 9.0, 11.0, 5.0]])
        self.assertEqual(w, k)

    def test_ohlc_venues_and_unclosed_okx_candles(self) -> None:
        o = alt._okx_rows({"code": "0", "data": [["60000", "10", "12", "9", "11", "5", "x", "x", "1"],
                                                 ["120000", "11", "12", "10", "11", "1", "x", "x", "0"]]})
        b = alt._bitget_rows({"code": "00000", "data": [["60000", "10", "12", "9", "11", "5", "50", "50"]]})
        self.assertEqual(o, [[60, 10.0, 12.0, 9.0, 11.0, 5.0]])   # the unconfirmed candle is dropped
        self.assertEqual(b, o)

    def test_error_payloads_raise(self) -> None:
        for fn, bad in ((alt._okx_rows, {"code": "51001"}), (alt._kucoin_rows, {"code": "400100"}),
                        (alt._bitget_rows, {"code": "40034"}), (alt._whitebit_rows, {"success": False})):
            with self.subTest(fn=fn.__name__), self.assertRaises(alt.AltFetchError):
                fn(bad)

    def test_sanity_rejects_impossible_ohlc(self) -> None:
        good, bad = alt.sane([[60, 10, 12, 9, 11, 1], [120, 10, 9, 12, 11, 1]])
        self.assertEqual((len(good), bad), (1, 1))


class WalkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="alt-"))
        for mod, name, value in ((fm, "DATA", self.dir), (alt, "DATA", self.dir)):
            patcher = mock.patch.object(mod, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def venue(self, history_from: int, swapped: bool = False):
        calls = []

        def url(pair, s, e):
            return json.dumps([s, e])

        def rows(payload):
            s, e = payload
            out = []
            for t in range(max(s, history_from), e + 1, 60):
                r = [t, 10.0, 12.0, 9.0, 11.0, 1.0]
                out.append([t, 10.0, 9.0, 12.0, 11.0, 1.0] if swapped else r)
            return out

        v = alt.Venue("fake", 100 * 60, 1000.0, lambda a: f"{a}-USDT", url, rows)

        def get(u):
            calls.append(u)
            return json.loads(u)
        return v, get, calls

    def test_walks_back_to_listing_and_resumes_only_new_minutes(self) -> None:
        listing = NOW - 3 * 86400
        v, get, calls = self.venue(listing)
        r = alt.fetch_asset("XYZ", v, 7, get=get, now=NOW, log=lambda s: None, pacer=alt.Pacer(1e6))
        df = alt.finalise("XYZ")
        self.assertEqual(int(df["timestamp"].min()), listing)
        self.assertTrue((df["timestamp"].diff().dropna() == 60).all())
        self.assertEqual(r["rejected"], 0)
        first_calls = len(calls)
        # Ten minutes later only the new minutes are requested.
        alt.fetch_asset("XYZ", v, 7, get=get, now=NOW + 600, log=lambda s: None, pacer=alt.Pacer(1e6))
        df2 = alt.finalise("XYZ")
        self.assertEqual(len(df2), len(df) + 10)
        self.assertLessEqual(len(calls) - first_calls, 1 + alt.EMPTY_PAGES_TO_STOP)
        meta = json.loads(alt.source_path("XYZ").read_text())
        self.assertEqual((meta["venue"], meta["pair"], meta["quote"]), ("fake", "XYZ-USDT", "USDT"))

    def test_a_page_with_swapped_columns_aborts_before_writing(self) -> None:
        v, get, _ = self.venue(NOW - 86400, swapped=True)
        with self.assertRaises(alt.AltFetchError):
            alt.fetch_asset("BAD", v, 7, get=get, now=NOW, log=lambda s: None, pacer=alt.Pacer(1e6))
        self.assertEqual(fm.minute_path("BAD").read_text().strip(), ",".join(fm.BAR_COLUMNS))


class ManifestTests(unittest.TestCase):
    def test_a_partial_run_keeps_other_assets(self) -> None:
        path = Path(tempfile.mkdtemp(prefix="manifest-")) / "m.json"
        path.write_text(json.dumps({"assets": [{"asset": "BTC", "span_days": 9}, {"asset": "ETH", "span_days": 8}]}))

        class C:
            asset = "ETH"
            span_days = 3

            def as_dict(self):
                return {"asset": "ETH", "span_days": 3, "fresh": True}

        fm.write_manifest([C()], path)
        rows = {r["asset"]: r for r in json.loads(path.read_text())["assets"]}
        self.assertEqual(set(rows), {"BTC", "ETH"})
        self.assertTrue(rows["ETH"].get("fresh"))


if __name__ == "__main__":
    unittest.main()
