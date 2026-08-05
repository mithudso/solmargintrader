"""The multi-asset universe fetch.

No test here touches the network. `list_coinbase_products` takes an injected
`get_json` and `fetch_universe` takes an injected `fetcher`, for the reason
`fetch.py`'s own docstring gives: fetching is an explicit step, and a test suite
that performs it is neither deterministic nor polite to the venue.

The behaviour most worth pinning is the refusal. Coinbase does not list TRX or
RAIN, so the honest top-10 fetch is an 8-of-10 fetch, and the failure mode is not
an error — it is eight files that look like a complete universe.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from backtester.core import universe as uni
from backtester.core.fetch import FetchError

LISTED = [
    {"id": "BTC-USD", "status": "online", "trading_disabled": False},
    {"id": "ETH-USD", "status": "online", "trading_disabled": False},
    {"id": "SOL-USD", "status": "online", "trading_disabled": False},
    {"id": "DOGE-USD", "status": "online", "trading_disabled": False},
    {"id": "DEAD-USD", "status": "delisted", "trading_disabled": True},
    {"id": "PAUSED-USD", "status": "online", "trading_disabled": True},
]


def bars(n: int = 40, start: int = 1_600_000_000, step: int = 86_400) -> pd.DataFrame:
    ts = [start + i * step for i in range(n)]
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.5] * n,
            "volume": [10.0] * n,
        }
    )


class PlanTests(unittest.TestCase):
    def test_the_venue_is_asked_what_it_lists_rather_than_assumed(self):
        listed = uni.list_coinbase_products(get_json=lambda _url: LISTED)
        self.assertIn("BTC-USD", listed)
        self.assertIn("DOGE-USD", listed)

    def test_a_delisted_or_paused_product_does_not_count_as_listed(self):
        """Both exist in the catalogue and neither can produce a usable series. A
        product that is present but not trading is the subtle one: it passes an
        `id in products` check and then returns nothing.
        """
        listed = uni.list_coinbase_products(get_json=lambda _url: LISTED)
        self.assertNotIn("DEAD-USD", listed)
        self.assertNotIn("PAUSED-USD", listed)

    def test_the_plan_splits_available_from_unlisted(self):
        plan = uni.plan_universe_fetch(["BTC", "TRX", "SOL"], [p["id"] for p in LISTED])
        self.assertEqual(plan.available, ("BTC", "SOL"))
        self.assertEqual(plan.missing, ("TRX",))
        self.assertTrue(plan.partial)

    def test_a_complete_universe_is_not_flagged_partial(self):
        plan = uni.plan_universe_fetch(["BTC", "ETH"], [p["id"] for p in LISTED])
        self.assertFalse(plan.partial)
        self.assertEqual(plan.missing, ())

    def test_the_real_top_ten_is_partial_on_this_venue(self):
        """The finding that motivates the refusal, pinned so it cannot regress into a
        silent 8-of-10. If Coinbase lists TRX or RAIN later, this test should be
        updated deliberately rather than discovered by accident.
        """
        plan = uni.plan_universe_fetch(uni.TOP10_NON_PEGGED, [p["id"] for p in LISTED])
        self.assertIn("TRX", plan.missing)
        self.assertIn("RAIN", plan.missing)

    def test_the_tradeable_universe_drops_assets_the_evidence_does_not_support(self):
        """RAIN ranks top-20 by market cap and is excluded anyway.

        Three aggregators disagree on its rank by ~190 places on the same day, total bid
        depth across all venues is ~$294k against an $8.6B nominal cap, and ~66% of supply
        is in vesting, treasury, or one Nasdaq holder. The market-cap list stays factual;
        the tradeable list is what a strategy should point at, and it is nine long. A
        universe that backfilled a tenth to keep a round number would be choosing the
        number over the evidence.
        """
        self.assertIn("RAIN", uni.TOP10_NON_PEGGED)
        self.assertNotIn("RAIN", uni.TRADEABLE_UNIVERSE)
        self.assertEqual(len(uni.TRADEABLE_UNIVERSE), 9)
        self.assertIn("RAIN", uni.EXCLUDED)
        self.assertIn("rain-rain.md", uni.EXCLUDED["RAIN"])

    def test_short_history_assets_are_flagged_separately_from_unlisted_ones(self):
        """Availability and sufficiency are different failures and only one of them is
        loud. An unlisted asset produces no file; a six-month asset produces a file that
        looks exactly like a five-year one, and the evidence floor is breached silently.
        """
        self.assertIn("HYPE", uni.SHORT_HISTORY)
        self.assertIn("2026-02-05", uni.SHORT_HISTORY["HYPE"])
        self.assertIn("TRX", uni.SHORT_HISTORY)

    def test_zec_is_recorded_as_usd_only(self):
        """A cross-pair strategy needs a cross pair. Coinbase delisted ZEC-BTC and
        ZEC-USDC, so ZEC can serve a USD-leg study and not a triangle.
        """
        self.assertIn("ZEC", uni.USD_ONLY)
        self.assertIn("ZEC-USD", uni.USD_ONLY["ZEC"])

    def test_a_series_with_a_known_hole_is_recorded_as_such(self):
        """Worse than a short series, because a short one is at least contiguous.

        Coinbase suspended XRP 2021-01-19 and relisted 2023-07-13. Concatenated blind, the
        join is a single bar spanning two and a half years and every return, volatility and
        drawdown computed across it is wrong -- while the file looks perfectly ordinary.
        strict_gaps is what catches it; this records that we know it is there.
        """
        self.assertIn("XRP", uni.KNOWN_GAPS)
        self.assertIn("2021-01-19", uni.KNOWN_GAPS["XRP"])
        self.assertIn("2023-07-13", uni.KNOWN_GAPS["XRP"])

    def test_bnb_is_flagged_for_covering_a_single_regime(self):
        """288 bars is not merely few, it is few *and* monotone -- one bull-to-bear leg
        offers no independent folds, so a good CPCV number off it would be one regime
        wearing 28 paths.
        """
        self.assertIn("BNB", uni.SHORT_HISTORY)
        self.assertIn("288", uni.SHORT_HISTORY["BNB"])

    def test_the_summary_names_what_is_missing(self):
        plan = uni.plan_universe_fetch(["BTC", "TRX"], [p["id"] for p in LISTED])
        self.assertIn("TRX", plan.summary())
        self.assertIn("1 of 2", plan.summary())


class FetchTests(unittest.TestCase):
    def test_each_available_asset_is_written_to_its_own_cache_file(self):
        plan = uni.plan_universe_fetch(["BTC", "SOL"], [p["id"] for p in LISTED])
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            results = uni.fetch_universe(
                plan, "2021-01-01", "2021-02-01", "1d",
                fetcher=lambda *a, **k: bars(), out_dir=out, verbose=False,
            )
            self.assertTrue((out / "BTC_1d.csv").exists())
            self.assertTrue((out / "SOL_1d.csv").exists())
            self.assertIn("wrote 40 bars", results["BTC"])

    def test_an_unlisted_asset_is_reported_not_silently_absent(self):
        plan = uni.plan_universe_fetch(["BTC", "TRX"], [p["id"] for p in LISTED])
        with TemporaryDirectory() as tmp:
            results = uni.fetch_universe(
                plan, "2021-01-01", "2021-02-01", "1d",
                fetcher=lambda *a, **k: bars(), out_dir=Path(tmp), verbose=False,
            )
        self.assertEqual(results["TRX"], "not-listed")

    def test_one_asset_failing_does_not_abandon_the_others(self):
        """A ten-asset fetch that dies on the third leaves a cache nobody can reason
        about -- some assets current, some stale, no record of which.
        """
        plan = uni.plan_universe_fetch(["BTC", "ETH", "SOL"], [p["id"] for p in LISTED])

        def flaky(product, *a, **k):
            if product == "ETH-USD":
                raise FetchError("boom")
            return bars()

        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            results = uni.fetch_universe(
                plan, "2021-01-01", "2021-02-01", "1d",
                fetcher=flaky, out_dir=out, verbose=False,
            )
        self.assertIn("FAILED", results["ETH"])
        self.assertIn("wrote", results["BTC"])
        self.assertIn("wrote", results["SOL"])
        self.assertFalse((out / "ETH_1d.csv").exists())

    def test_a_series_that_fails_validation_is_not_written(self):
        """A cache file is trusted by every later run, so a bad series must not reach
        disk at all -- reporting the failure and leaving no file is the safe pair.
        """
        plan = uni.plan_universe_fetch(["BTC"], [p["id"] for p in LISTED])
        gappy = bars(10)
        gappy.loc[5, "timestamp"] = int(gappy.loc[5, "timestamp"]) + 4242  # break the grid

        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            results = uni.fetch_universe(
                plan, "2021-01-01", "2021-02-01", "1d",
                fetcher=lambda *a, **k: gappy, out_dir=out, verbose=False,
            )
        self.assertIn("FAILED validation", results["BTC"])
        self.assertFalse((out / "BTC_1d.csv").exists())

    def test_an_already_cached_asset_is_skipped_unless_asked(self):
        plan = uni.plan_universe_fetch(["BTC"], [p["id"] for p in LISTED])
        calls = []

        def counting(*a, **k):
            calls.append(1)
            return bars()

        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            uni.fetch_universe(plan, "2021-01-01", "2021-02-01", "1d",
                               fetcher=counting, out_dir=out, verbose=False)
            uni.fetch_universe(plan, "2021-01-01", "2021-02-01", "1d",
                               fetcher=counting, out_dir=out, verbose=False)
            self.assertEqual(len(calls), 1)
            uni.fetch_universe(plan, "2021-01-01", "2021-02-01", "1d",
                               fetcher=counting, out_dir=out, skip_existing=False, verbose=False)
            self.assertEqual(len(calls), 2)


class CliTests(unittest.TestCase):
    def test_a_partial_universe_is_refused_by_default(self):
        """The whole point of the module. Eight files presented as a ten-asset
        universe biases every cross-sectional statistic computed over it, and the
        filter is the listing venue rather than anything economic.
        """
        uni.list_coinbase_products = lambda **_k: tuple(p["id"] for p in LISTED)  # type: ignore[assignment]
        try:
            rc = uni.main(["--assets", "BTC,TRX", "--plan-only"])
            self.assertEqual(rc, 0)
            rc = uni.main(["--assets", "BTC,TRX"])
            self.assertEqual(rc, 1)
        finally:
            import importlib

            importlib.reload(uni)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
