import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from oracle.cli import owner
from oracle.zec_volty_paper import GumPaperFeed, PaperSession, PaperTick, _connect
from oracle.zec_volty_signal import VoltyDataError, VoltyObservation

START = 1_800_000_000
D = Decimal


def tick(offset, mark=100, *, ask="100.01", ask_size="2", funding=None):
    at = START + offset
    market = {
        "markPrice": 100, "bestBid": 100, "bestAsk": ask, "takerFeeBps": "3.5",
        "maxAccountPositionNotional": "1000",
        "riskTiers": [{"notionalCap": "1000", "maxLeverage": 50,
                       "maintenanceMarginRatioBps": "100", "maintenanceAmount": 0}],
        "orderLimitConfig": {
            "market": {"minOrderQty": "0.001", "minOrderNotional": 5,
                       "maxOpenOrderQty": 25, "maxCloseOrderQty": 25,
                       "maxOpenOrderNotional": "20000", "maxCloseOrderNotional": "20000"},
        },
    }
    return PaperTick(VoltyObservation(at // 300 * 300, at, mark, 101, 99), at + 0.5,
                     market, D(100), D(2), D(ask), D(ask_size), funding)


class VoltyPaperTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.session = PaperSession(self.db)

    def test_shared_quotes_preserve_short_exit_and_distinguish_reopening(self):
        for offset, mark in enumerate((100, 101, 101, 99, 99, 99, 99)):
            status = self.session.observe(tick(offset, mark))
        variants = status["variants"]
        both, short, wait = (variants[name] for name in ("funded-rules", "short-only", "close-and-wait"))
        self.assertEqual((both["position"], short["position"], wait["position"]), ("sell", "sell", None))
        self.assertEqual((both["closed"], short["closed"], wait["closed"]), (1, 0, 1))
        self.assertLess(wait["realized_net_usdc"], 0)
        self.assertGreater(wait["fees_usdc"], 0)
        self.assertGreater(wait["max_drawdown_usdc"], 0)

        self.session.observe(tick(7, 100))
        self.session.observe(tick(8, 101))
        self.session.observe(tick(9, 101))
        self.session.observe(tick(10, 101))
        status = self.session.observe(tick(11, 101))
        self.assertEqual(status["variants"]["short-only"]["closed"], 1)
        self.assertIsNone(status["variants"]["short-only"]["position"])
        self.assertEqual(status["variants"]["close-and-wait"]["position"], "buy")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM paper_ticks").fetchone()[0], 12)

    def test_fok_does_not_assume_depth_preflight_does_not_widen_cap(self):
        self.session.observe(tick(0))
        self.session.observe(tick(1, 101))
        status = self.session.observe(tick(2, 101, ask_size="0.001"))
        self.assertEqual(status["variants"]["funded-rules"]["refusals"], {"fok_top_of_book": 1})
        self.assertIsNone(status["variants"]["funded-rules"]["position"])

        self.session.observe(tick(3))
        self.session.observe(tick(4, 101))
        status = self.session.observe(tick(5, 101, ask="100.00"))
        self.assertEqual(status["variants"]["funded-rules"]["refusals"], {
            "fok_top_of_book": 1,
            "price_cap_widened": 1,
        })
        self.assertIsNone(status["variants"]["funded-rules"]["position"])

    def test_restart_retains_positions_but_requires_warmup_and_discards_old_intent(self):
        self.session.observe(tick(0))
        self.session.observe(tick(1, 101))
        with self.assertRaises(VoltyDataError):
            self.session.observe(tick(1, 101))
        resumed = PaperSession(self.db)
        status = resumed.observe(tick(2, 101))
        self.assertEqual(status["ticks"], 3)
        self.assertIsNone(status["variants"]["funded-rules"]["position"])
        resumed.observe(tick(3))
        resumed.observe(tick(4, 101))
        resumed.observe(tick(5, 101))
        status = PaperSession(self.db).observe(tick(6, 101))
        self.assertEqual(status["variants"]["funded-rules"]["position"], "buy")

    def test_only_an_identical_mark_is_a_benign_duplicate(self):
        prior = tick(1, 101).observation
        feed = GumPaperFeed()
        for observation, reason in (
            (prior, "gum_no_distinct_paper_mark"),
            (replace(prior, mark=100), "gum_zec_mark_replayed"),
            (tick(0).observation, "gum_zec_mark_replayed"),
        ):
            with (
                self.subTest(reason=reason),
                patch.object(feed.source, "read", return_value=observation),
                self.assertRaisesRegex(VoltyDataError, reason),
            ):
                feed.read(prior)

    def test_opposite_crossing_replaces_an_unsubmitted_open(self):
        self.session.observe(tick(0))
        self.session.observe(tick(1, 101))
        status = self.session.observe(tick(2, 99))["variants"]["funded-rules"]
        self.assertIsNone(status["position"])
        self.assertEqual(status["pending"], "sell")
        self.assertEqual(status["refusals"], {"signal_superseded": 1})
        status = self.session.observe(tick(3, 99))["variants"]["funded-rules"]
        self.assertEqual(status["position"], "sell")

    def test_opposite_crossing_does_not_cancel_a_reduce_only_close(self):
        for offset, mark in enumerate((100, 101, 101, 99, 101)):
            status = self.session.observe(tick(offset, mark))["variants"]["funded-rules"]
        self.assertIsNone(status["position"])
        self.assertEqual(status["closed"], 1)
        self.assertEqual(status["refusals"], {})
        status = self.session.observe(tick(5, 101))["variants"]["funded-rules"]
        self.assertEqual(status["pending"], "buy")

    def test_venue_tier_must_cover_opening_notional_at_plan_and_fill(self):
        def low_tier_tick(offset):
            row = tick(offset, 101)
            row.market["riskTiers"][0]["notionalCap"] = "3"
            return row

        self.session.observe(tick(0))
        status = self.session.observe(low_tier_tick(1))["variants"]["funded-rules"]
        self.assertIsNone(status["pending"])
        self.assertEqual(status["refusals"], {"venue_leverage_limit": 1})

        self.session.observe(tick(2))
        self.session.observe(tick(3, 101))
        status = self.session.observe(low_tier_tick(4))["variants"]["funded-rules"]
        self.assertIsNone(status["position"])
        self.assertEqual(status["refusals"], {"venue_leverage_limit": 2})

    def test_maintenance_without_a_covering_tier_makes_results_unavailable(self):
        for offset, mark in enumerate((100, 101, 101)):
            self.session.observe(tick(offset, mark))
        invalid = tick(3, 101)
        invalid.market["riskTiers"][0]["notionalCap"] = "3"
        status = self.session.observe(invalid)["variants"]["funded-rules"]
        self.assertIsNone(status["net_pnl_usdc"])
        self.assertFalse(status["margin_breach"])
        self.assertTrue(status["maintenance_unavailable"])
        restarted = PaperSession(self.db).observe(tick(4))
        self.assertIsNone(restarted["variants"]["funded-rules"]["net_pnl_usdc"])

    def test_old_checkpoints_remain_readable_without_mixing_method_totals(self):
        for offset, mark in enumerate((100, 101, 101)):
            self.session.observe(tick(offset, mark))
        last = tick(2, 101).observation
        for mark_at, data in self.db.execute("SELECT mark_at, checkpoint FROM paper_ticks").fetchall():
            payload = json.loads(data)
            payload["method"] = "zec-volty-shared-gum-v1"
            for book in payload["books"].values():
                book.pop("maintenance_unavailable", None)
            self.db.execute("UPDATE paper_ticks SET checkpoint=? WHERE mark_at=?", (json.dumps(payload), mark_at))
        resumed = PaperSession(self.db)
        self.assertEqual(resumed.last_observation, last)
        with self.assertRaisesRegex(VoltyDataError, "gum_no_distinct_paper_mark"):
            resumed.observe(tick(2, 101))
        status = resumed.observe(tick(3, 101))
        self.assertEqual(status["method"], "zec-volty-shared-gum-v2")
        self.assertEqual((status["ticks"], status["first_mark_at"]), (1, START + 3))
        self.assertIsNone(status["variants"]["funded-rules"]["position"])
        rows = self.db.execute("SELECT json_extract(checkpoint, '$.method') FROM paper_ticks ORDER BY mark_at")
        self.assertEqual([row[0] for row in rows], ["zec-volty-shared-gum-v1"] * 3 + ["zec-volty-shared-gum-v2"])
        self.assertEqual(PaperSession(self.db).observe(tick(4, 101))["ticks"], 2)

    def test_funding_charges_positions_when_known_and_invalidates_pnl_on_gap(self):
        self.session.observe(tick(-5))
        self.session.observe(tick(-4, 101))
        self.session.observe(tick(-3, 101))
        status = self.session.observe(tick(0, 100, funding=D("0.125")))
        self.assertEqual(status["variants"]["funded-rules"]["funding_charged"], 1)
        self.assertLess(status["variants"]["funded-rules"]["funding_usdc"], 0)
        self.assertIsNotNone(status["variants"]["funded-rules"]["net_pnl_usdc"])
        status = self.session.observe(tick(3600))
        self.assertEqual(status["variants"]["funded-rules"]["funding_missing"], 1)
        self.assertIsNone(status["variants"]["funded-rules"]["net_pnl_usdc"])
        self.assertEqual(status["variants"]["short-only"]["funding_missing"], 0)

    def test_invalid_funding_does_not_become_a_zero_charge(self):
        with patch("oracle.zec_volty_paper._get_json", return_value={
            "entries": [{"symbol": "ZEC", "timestamp": START, "rateBps1h": "invalid"}],
        }):
            self.assertIsNone(GumPaperFeed._funding(START))
        with patch("oracle.zec_volty_paper._get_json", return_value={
            "entries": [{"symbol": "ZEC", "timestamp": START, "rateBps1h": "-0.5"}],
        }):
            self.assertEqual(GumPaperFeed._funding(START), D("-0.5"))

    def test_journal_is_private_and_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paper.sqlite3"
            with closing(_connect(path)) as db:
                PaperSession(db).observe(tick(0))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            link = Path(directory) / "link.sqlite3"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                _connect(link)

    def test_duplicate_watcher_refuses_without_private_traceback(self):
        with tempfile.TemporaryDirectory() as directory, owner(Path(directory) / "paper.sqlite3"):
            result = subprocess.run(
                [sys.executable, "-m", "oracle.zec_volty_paper", "--state-dir", directory],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "paper_owner_already_running")
        self.assertEqual(result.stderr, "")

    def test_rejects_regular_file_as_state_directory_without_echoing_its_path(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "private-state-path"
            invalid.touch()
            result = subprocess.run(
                [sys.executable, "-m", "oracle.zec_volty_paper", "--state-dir", str(invalid)],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "paper_journal_unavailable")
        self.assertNotIn(invalid.name, result.stdout)
        self.assertEqual(result.stderr, "")
