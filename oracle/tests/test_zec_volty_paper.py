import sqlite3
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

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
