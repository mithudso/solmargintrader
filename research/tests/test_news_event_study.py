"""Protect timestamp alignment, selection independence and missing-data behavior."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.news_event_report import _paired_latency
from research.news_event_study import (
    canonical_url,
    cluster_interval,
    entry_minute,
    epoch,
    event_returns,
    measure,
    reviewed_events,
    select_events,
)


class NewsEvents(unittest.TestCase):
    def test_entry_is_strictly_after_publication(self):
        self.assertEqual(entry_minute(120), 180)
        self.assertEqual(entry_minute(121), 180)
        self.assertEqual(entry_minute(179), 180)

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            epoch("2026-01-01T00:00:00")
        self.assertEqual(
            epoch("2026-01-01T01:00:00+01:00"), epoch("2026-01-01T00:00:00Z")
        )

    def test_missing_minute_is_not_next_observed_row(self):
        self.assertIsNone(event_returns({60: 10, 180: 12}, 60, 1))
        self.assertAlmostEqual(event_returns({60: 10, 180: 12}, 60, 2), 20)

    def test_nonpositive_price_refused(self):
        with self.assertRaises(ValueError):
            event_returns({60: 0, 120: 1}, 60, 1)

    def test_tracking_query_is_not_an_independent_story(self):
        self.assertEqual(
            canonical_url("https://example.com/news/?utm_source=feed"),
            "https://example.com/news",
        )

    @staticmethod
    def article(
        title="Solana launches protocol upgrade",
        date="2026-08-20T01:00:01Z",
        url="https://example.com/a",
    ):
        return {
            "title": title,
            "published_at": date,
            "url": url,
            "source": "fixture",
            "timestamp_source": "publisher_api",
        }

    def test_conflicting_rolling_publication_is_excluded(self):
        a = self.article()
        b = self.article(date="2026-08-21T01:00:01Z")
        selected, rejected = select_events([a, b], [], 0, 9999999999)
        self.assertFalse(selected)
        self.assertEqual(rejected[0]["reason"], "conflicting_publication_times_for_url")

    def test_market_control_holdout_protects_other_asset_event(self):
        a = self.article()
        start = entry_minute(epoch(a["published_at"]))
        reservations = [
            {"coin": "USD-ETH-BTC", "start": start + 60, "end": start + 120}
        ]
        selected, rejected = select_events([a], reservations, 0, 9999999999)
        self.assertFalse(selected)
        self.assertEqual(rejected[0]["reason"], "protected_event_or_prior_week_window")

    def test_price_reaction_headline_is_not_catalyst(self):
        selected, rejected = select_events(
            [self.article(title="Solana price surges after ETF launch")],
            [],
            0,
            9999999999,
        )
        self.assertFalse(selected)
        self.assertEqual(
            rejected[0]["reason"], "price_commentary_evergreen_or_promotion"
        )

    def test_spaced_selection_is_deterministic_without_outcomes(self):
        rows = [
            self.article(
                date=f"2026-08-{day:02}T01:00:01Z", url=f"https://example.com/{day}"
            )
            for day in range(1, 25)
        ]
        a, _ = select_events(rows, [], 0, 9999999999, limit=5)
        b, _ = select_events(list(reversed(rows)), [], 0, 9999999999, limit=5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 5)

    def test_returns_use_correct_market_control_and_paired_clock(self):
        entry = 800000
        e = {
            **self.article(),
            "coin": "SOL",
            "entry": entry,
            "published": entry - 20,
            "event_type": "protocol_adoption",
        }
        prices = {
            c: {
                entry: 100,
                entry + 60: p,
                entry - 3600: 100,
                entry - 604800: 100,
                entry - 604800 + 60: 100,
            }
            for c, p in (("SOL", 110), ("BTC", 102), ("ETH", 104))
        }
        row = measure([e], prices)[0]
        self.assertAlmostEqual(row["return_pct"], 10)
        self.assertAlmostEqual(row["benchmark_pct"], 3)
        self.assertAlmostEqual(row["excess_pp"], 7)
        self.assertAlmostEqual(row["paired_excess_delta_pp"], 7)

    def test_uncertainty_needs_multiple_dates(self):
        self.assertEqual(
            cluster_interval([{"published_at": "2026-01-01", "x": 1}], "x"),
            (None, None, 1),
        )

    def test_prepublication_window_does_not_include_post_news_entry(self):
        published = epoch("2026-08-20T01:00:20Z")
        entry = entry_minute(published)
        pre_end = (published // 60 - 1) * 60
        event = {
            **self.article(),
            "coin": "SOL",
            "published": published,
            "entry": entry,
            "event_type": "protocol_adoption",
        }
        prices = {
            coin: {pre_end - 3600: 100, pre_end: 100, entry: 200, entry + 60: 200}
            for coin in ("SOL", "BTC", "ETH")
        }
        row = measure([event], prices)[0]
        self.assertEqual(row["pre60_return_pct"], 0)
        self.assertLess(epoch(row["pre60_end_utc"]), published)

    def test_replacing_frozen_cohort_needs_independent_review_too(self):
        event = {
            **self.article(),
            "coin": "SOL",
            "event_type": "protocol_adoption",
            "published": epoch(self.article()["published_at"]),
        }
        event["entry"] = entry_minute(event["published"])
        decision = {
            **event,
            "include": True,
            "corrected_event_type": event["event_type"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            events = home / "events-frozen.json"
            review = home / "eligibility-review-v2.json"
            manifest = home / "selection-v2-manifest.json"
            events.write_text(json.dumps([event]))
            review.write_text(
                json.dumps(
                    {
                        "price_data_accessed": False,
                        "new_articles_added": 0,
                        "rejected_rows_replaced": 0,
                        "decisions": [decision],
                    }
                )
            )

            def bind():
                manifest.write_text(
                    json.dumps(
                        {
                            "files": {
                                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (events, review)
                            }
                        }
                    )
                )

            bind()
            self.assertEqual(reviewed_events(home), [event])
            events.write_text(
                json.dumps([event, {**event, "url": "https://example.com/extra"}])
            )
            with self.assertRaisesRegex(ValueError, "checksum"):
                reviewed_events(home)
            bind()
            with self.assertRaisesRegex(ValueError, "identities"):
                reviewed_events(home)

    def test_delay_comparison_uses_same_available_event_rows(self):
        base = [
            {"coin": "SOL", "url": url, "horizon_minutes": "1", "return_pct": value}
            for url, value in (("a", "10"), ("b", "-10"))
        ]
        delayed = [
            {"coin": "SOL", "url": url, "horizon_minutes": "1", "return_pct": value}
            for url, value in (("a", "1"), ("b", ""))
        ]
        pair = _paired_latency(base, delayed)[("SOL", 1)]
        self.assertEqual(pair["n"], 1)
        self.assertEqual(pair["immediate_mean"], 10)
        self.assertEqual(pair["delayed_mean"], 1)


if __name__ == "__main__":
    unittest.main()
