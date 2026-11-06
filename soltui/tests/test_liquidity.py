"""The Liquidity tab: loader tolerance, formatting, summary math, KILL toggle.

The logic is in `soltui.liquidity` (pure); the last class mounts the real app
against a fixture state dir. Fixtures follow `liquidity/STATE_FILES.md`.

The load-bearing test is `test_every_percentage_column_carries_a_source_word`:
a bare "+4.6%" under a header with no source reads as "my money is up".
"""

from __future__ import annotations

import ast
import json
import os
import re
import unittest
from datetime import timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from textual.widgets import DataTable, Static, TabbedContent

from soltui import liquidity as liq
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp

NOW = 1762400100.0
TX1 = "0x" + "ab" * 32
TX2 = "0x" + "cd" * 32


def status_doc(**over) -> dict:
    doc = {
        "schema": liq.STATUS_SCHEMA,
        "generated_at": NOW - 30,
        "mode": "live",
        "killed": False,
        "owner": "0x901a…5314",
        "last_scout_at": NOW - 10000,
        "wallet": {
            "eth": 0.0000926, "idle_usd": 45.6, "deployed_usd": 88.1,
            "tokens": [{"symbol": "WETH", "address": "0x4200…0006",
                        "amount": 0.0193796, "usd": 43.1, "idle": True}],
        },
        "positions": [
            {"slot": "1609324", "token_id": 1609324, "pool": "0xeC3c", "pair": "WETH/cbBTC",
             "tick_spacing": 1, "staked": True, "in_range": False,
             "range": [0.0296403, 0.0296847], "price": 0.0294201, "value_usd": 43.10,
             "deposited_usd": 45.0, "pnl_usd": -1.92, "pnl_vs_hodl_usd": -0.92,
             "apr_realized": -12.3, "decision": "skip_unprofitable",
             "reason": "re-entering is expected to lose [more] than it earns " + "x" * 120},
            {"slot": "1700001", "pair": "WETH/wstETH", "staked": False, "in_range": True,
             "range": [1.0, 1.1], "price": 1.05, "value_usd": 45.0, "deposited_usd": 44.0,
             "pnl_usd": 1.0, "pnl_vs_hodl_usd": 0.5, "apr_realized": 4.6,
             "decision": "hold"},
        ],
        "experiments": [{
            "id": "exp-1", "status": "running", "winner": "1700001",
            "arms": [
                {"slot": "1609324", "pair": "WETH/cbBTC", "pool": "0xa", "deposited_usd": 20.0,
                 "pnl_usd": -0.1, "pnl_pct": -0.5, "apr_realized": -3.0},
                {"slot": "1700001", "pair": "WETH/wstETH", "pool": "0xb", "deposited_usd": 20.0,
                 "pnl_usd": 0.05, "pnl_pct": 0.25, "apr_realized": 4.6},
            ],
        }],
        "actions": [
            {"ts": NOW - 300, "kind": "deploy", "slot": "1700001", "detail": "opened", "tx": [TX1]},
            {"ts": NOW - 100, "kind": "rebalance", "slot": "1609324", "detail": "moved",
             "tx": [TX1, TX2]},
            {"ts": NOW - 200, "kind": "skip", "slot": "1609324", "detail": "no"},
        ],
    }
    doc.update(over)
    return doc


def scout_doc() -> dict:
    def pool(pair, net, **kw):
        d = {"pool": "0x", "pair": pair, "tvl_usd": 1_200_000.0, "volume_24h_usd": 3_400_000.0,
             "fee_apr_ref": 3.1, "aero_apr_ref": 6.4, "lvr_apr_ref": 0.2, "edge_ratio": 31.0,
             "best_mode": "aero", "best_half_width_pct": 0.4, "expected_net_apr": net,
             "break_even_deposit_usd": 4.1, "confidence": "high", "flags": []}
        d.update(kw)
        return d
    return {"schema": liq.SCOUT_SCHEMA, "generated_at": NOW - 5000, "deposit_usd": 50.0,
            "pools": [pool("LOW/POOL", 2.0), pool("TOP/POOL", 18.2, flags=["thin", "new"]),
                      pool("NONE/POOL", None)]}


def write(home: Path, name: str, doc) -> None:
    (home / name).write_text(doc if isinstance(doc, str) else json.dumps(doc))


class TestHome(unittest.TestCase):
    def test_env_wins(self) -> None:
        self.assertEqual(liq.state_dir({"AERO_LP_HOME": "/x/y"}), Path("/x/y"))

    def test_default_is_dot_aero_lp_under_home(self) -> None:
        self.assertEqual(liq.state_dir({}), Path("~/.aero-lp").expanduser())
        self.assertEqual(liq.state_dir({"AERO_LP_HOME": "  "}), Path("~/.aero-lp").expanduser())


class TestLoaderTolerance(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_missing_file_is_no_data(self) -> None:
        r = liq.load_status(self.home)
        self.assertFalse(r.ok)
        self.assertIn("not found", r.reason)
        self.assertFalse(liq.load_scout(self.home).ok)

    def test_missing_dir_is_no_data(self) -> None:
        self.assertFalse(liq.load_status(self.home / "nope").ok)

    def test_corrupt_json_is_no_data(self) -> None:
        for body in ("{not json", "", "\x00\x01", "[" * 100000):
            with self.subTest(body=body[:10]):
                write(self.home, liq.STATUS_FILE, body)
                r = liq.load_status(self.home)
                self.assertFalse(r.ok)
                self.assertIn("JSON", r.reason)

    def test_non_object_json_is_no_data(self) -> None:
        write(self.home, liq.STATUS_FILE, "[1, 2]")
        self.assertFalse(liq.load_status(self.home).ok)

    def test_unknown_or_missing_schema_is_no_data(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc(schema="aero-lp-status/2"))
        r = liq.load_status(self.home)
        self.assertFalse(r.ok)
        self.assertIn("aero-lp-status/2", r.reason)
        write(self.home, liq.STATUS_FILE, {"mode": "live"})
        self.assertFalse(liq.load_status(self.home).ok)

    def test_scout_schema_is_not_accepted_as_status(self) -> None:
        write(self.home, liq.STATUS_FILE, scout_doc())
        self.assertFalse(liq.load_status(self.home).ok)

    def test_valid_files_load(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc())
        write(self.home, liq.SCOUT_FILE, scout_doc())
        self.assertTrue(liq.load_status(self.home).ok)
        self.assertTrue(liq.load_scout(self.home).ok)

    def test_minimal_documents_never_raise_anywhere(self) -> None:
        """Missing optional keys and wrong-typed values give dashes, not errors."""
        junk = [{}, {"positions": "x"}, {"positions": [1, None, {}]},
                {"positions": [{"range": "bad", "price": "x", "pnl_usd": True,
                                "in_range": "yes", "reason": 5}]},
                {"experiments": [{"arms": "x"}, {"arms": [None, {}]}, 3]},
                {"actions": [{"tx": 5}, {"tx": "nothash"}, {"ts": "x"}, "s"]},
                {"wallet": 5, "mode": 3, "generated_at": "x"}, {"wallet": {"tokens": 4}}]
        for extra in junk:
            with self.subTest(extra=extra):
                doc = {"schema": liq.STATUS_SCHEMA, **extra}
                liq.summarise(doc).line()
                liq.wallet_line(doc)
                liq.positions_table(doc)
                liq.experiments_table(doc)
                liq.actions_table(doc, timezone.utc)
        liq.scout_table({"pools": [{}, "x", {"flags": "z", "expected_net_apr": "n"}]})
        liq.scout_table({})
        liq.scout_line({})

    def test_nan_and_inf_are_not_numbers(self) -> None:
        self.assertIsNone(liq.num(float("nan")))
        self.assertIsNone(liq.num(float("inf")))
        self.assertIsNone(liq.num(True))
        self.assertEqual(liq.fmt_usd(float("nan")), liq.DASH)


class TestFormatting(unittest.TestCase):
    def test_usd(self) -> None:
        self.assertEqual(liq.fmt_usd(1234.5), "$1,234.50")
        self.assertEqual(liq.fmt_usd(-1.92, signed=True), "-$1.92")
        self.assertEqual(liq.fmt_usd(1.0, signed=True), "+$1.00")
        self.assertEqual(liq.fmt_usd(-0.001, signed=True), "$0.00")
        self.assertEqual(liq.fmt_usd(None), liq.DASH)
        self.assertEqual(liq.fmt_usd_compact(1_200_000), "$1.2M")
        self.assertEqual(liq.fmt_usd_compact(950), "$950")

    def test_range_and_price(self) -> None:
        self.assertEqual(liq.fmt_range([0.0296403, 0.0296847]), "0.0296403–0.0296847")
        self.assertEqual(liq.fmt_range(None), liq.DASH)
        self.assertEqual(liq.fmt_range([1]), liq.DASH)
        self.assertEqual(liq.fmt_price(0.0294201), "0.0294201")

    def test_age(self) -> None:
        self.assertEqual(liq.fmt_age(30), "30s ago")
        self.assertEqual(liq.fmt_age(600), "10m ago")
        self.assertEqual(liq.fmt_age(7200), "2h ago")
        self.assertEqual(liq.fmt_age(None), "age unknown")

    def test_tx_link_only_for_full_hashes(self) -> None:
        self.assertEqual(liq.tx_link(TX1), f"https://basescan.org/tx/{TX1}")
        self.assertEqual(liq.tx_link("0x…"), "0x…")

    def test_positions_rows(self) -> None:
        t = liq.positions_table(status_doc())
        self.assertEqual(len(t.rows), 2)
        first = dict(zip(t.headers, t.rows[0]))
        self.assertEqual(first["pair"], "WETH/cbBTC")
        self.assertEqual(first["range status"], "OUT of range")
        self.assertEqual(first["staked"], "yes")
        self.assertEqual(first["live LP P&L $"], "-$1.92")
        self.assertEqual(first["live LP P&L vs HODL $"], "-$0.92")
        self.assertEqual(first["live realized APR"], "-12.3%")
        self.assertTrue(first["decision: reason"].startswith("skip_unprofitable: re-entering"))
        self.assertLessEqual(len(first["decision: reason"]), 17 + 2 + liq.REASON_CLIP)
        second = dict(zip(t.headers, t.rows[1]))
        self.assertEqual(second["range status"], "IN range")
        self.assertEqual(second["decision: reason"], "hold")

    def test_scout_sorted_by_net_apr_with_missing_last(self) -> None:
        t = liq.scout_table(scout_doc())
        self.assertEqual([r[0] for r in t.rows], ["TOP/POOL", "LOW/POOL", "NONE/POOL"])
        top = dict(zip(t.headers, t.rows[0]))
        self.assertEqual(top["TVL"], "$1.2M")
        self.assertEqual(top["best mode, half-width (modelled)"], "aero ±0.4%")
        self.assertEqual(top["modelled net APR"], "+18.2%")
        self.assertEqual(top["edge ratio (income/LVR)"], "31.0x")
        self.assertEqual(top["flags"], "thin, new")

    def test_scout_row_limit(self) -> None:
        doc = {"pools": [{"pair": f"P{i}", "expected_net_apr": i} for i in range(60)]}
        self.assertEqual(len(liq.scout_table(doc, limit=10).rows), 10)
        self.assertEqual(len(liq.scout_table(doc).rows), liq.SCOUT_ROWS)

    def test_experiment_arms_side_by_side_and_winner_marked(self) -> None:
        t = liq.experiments_table(status_doc())
        self.assertEqual(len(t.rows), 2)
        rows = [dict(zip(t.headers, r)) for r in t.rows]
        self.assertEqual(rows[0]["experiment"], "exp-1")
        self.assertEqual(rows[1]["experiment"], "")
        self.assertEqual([r["winner"] for r in rows], ["", "WINNER"])
        self.assertEqual(rows[1]["live LP P&L %"], "+0.25%")
        self.assertEqual(rows[1]["live LP P&L $"], "+$0.05")

    def test_no_winner_means_no_mark(self) -> None:
        doc = status_doc()
        doc["experiments"][0]["winner"] = None
        self.assertNotIn("WINNER", [r[-1] for r in liq.experiments_table(doc).rows])

    def test_actions_newest_first_with_basescan_links(self) -> None:
        t = liq.actions_table(status_doc(), timezone.utc)
        self.assertEqual([r[1] for r in t.rows], ["rebalance", "skip", "deploy"])
        self.assertEqual(t.rows[0][4], f"https://basescan.org/tx/{TX1} https://basescan.org/tx/{TX2}")
        self.assertEqual(t.rows[1][4], liq.DASH)
        self.assertEqual(liq.fmt_ts(1762400000.0, timezone.utc), "11-06 03:33:20")

    def test_action_limit(self) -> None:
        doc = {"actions": [{"ts": i, "kind": "scout"} for i in range(80)]}
        t = liq.actions_table(doc, timezone.utc)
        self.assertEqual(len(t.rows), liq.ACTION_ROWS)
        self.assertEqual(t.rows[0][0], liq.fmt_ts(79, timezone.utc))


class TestSummary(unittest.TestCase):
    def test_math(self) -> None:
        s = liq.summarise(status_doc(), now=NOW)
        self.assertEqual(s.idle_usd, 45.6)
        self.assertEqual(s.deployed_usd, 88.1)
        self.assertAlmostEqual(s.total_pnl_usd, -0.92)
        self.assertAlmostEqual(s.total_vs_hodl_usd, -0.42)
        self.assertEqual(s.n_positions, 2)
        self.assertFalse(s.stale)
        self.assertTrue(s.live)
        self.assertEqual(s.age, 30)

    def test_experiment_arms_are_not_double_counted(self) -> None:
        with_exp = liq.summarise(status_doc(), now=NOW).total_pnl_usd
        without = liq.summarise(status_doc(experiments=[]), now=NOW).total_pnl_usd
        self.assertEqual(with_exp, without)

    def test_no_positions_gives_dashes_not_zero(self) -> None:
        s = liq.summarise(status_doc(positions=[]), now=NOW)
        self.assertIsNone(s.total_pnl_usd)
        self.assertIn(f"live LP P&L {liq.DASH}", s.line())
        self.assertIn("0 positions", s.line())

    def test_stale_state_is_flagged(self) -> None:
        s = liq.summarise(status_doc(generated_at=NOW - 3600), now=NOW)
        self.assertTrue(s.stale)
        self.assertIn("STALE", s.line())
        self.assertTrue(liq.summarise(status_doc(generated_at=None), now=NOW).stale)

    def test_killed_from_flag_or_file(self) -> None:
        self.assertFalse(liq.summarise(status_doc(), now=NOW).killed)
        self.assertTrue(liq.summarise(status_doc(killed=True), now=NOW).killed)
        self.assertTrue(liq.summarise(status_doc(), kill_file_present=True, now=NOW).killed)

    def test_mode_is_never_guessed_live(self) -> None:
        for mode in ("dry-run", "weird", None):
            with self.subTest(mode=mode):
                s = liq.summarise(status_doc(mode=mode), now=NOW)
                self.assertFalse(s.live)
                self.assertNotIn("live", s.line())
        self.assertEqual(liq.mode_badge_text("live"), "LIVE")
        self.assertEqual(liq.mode_badge_text("dry-run"), "dry-run")
        self.assertIn("dry-run LP P&L", liq.summarise(status_doc(mode="dry-run"), now=NOW).line())

    def test_wallet_line(self) -> None:
        line = liq.wallet_line(status_doc())
        self.assertIn("WETH $43.10 (idle)", line)
        self.assertIn("0x901a…5314", line)


class TestLabellingRule(unittest.TestCase):
    """No percentage may appear without a source word."""

    def _tables(self, mode):
        s = status_doc(mode=mode)
        return [liq.positions_table(s), liq.experiments_table(s), liq.scout_table(scout_doc())]

    def test_every_percentage_column_carries_a_source_word(self) -> None:
        for mode in ("live", "dry-run", "other"):
            for table in self._tables(mode):
                for i, col in enumerate(table.columns):
                    cells = [r[i] for r in table.rows]
                    has_pct = any("%" in c for c in cells)
                    with self.subTest(mode=mode, header=col.header):
                        if col.pct:
                            self.assertTrue(
                                any(w in col.header for w in liq.SOURCE_WORDS), col.header)
                        if has_pct:
                            # Any column that renders a % must be declared pct.
                            self.assertTrue(col.pct, f"undeclared % column: {col.header}")

    def test_pnl_headers_name_the_source(self) -> None:
        for mode, word in (("live", "live"), ("dry-run", "dry-run"), (None, "reported")):
            t = liq.positions_table(status_doc(mode=mode))
            self.assertIn(f"{word} LP P&L $", t.headers)

    def test_summary_line_labels_every_money_pnl(self) -> None:
        for mode in ("live", "dry-run", "x"):
            line = liq.summarise(status_doc(mode=mode), now=NOW).line()
            for m in re.finditer(r"P&L", line):
                head = line[: m.start()].split(" | ")[-1]
                self.assertTrue(any(w in head + "P&L" for w in liq.SOURCE_WORDS + ("reported",)),
                                line)
            self.assertNotRegex(line, r"%")

    def test_scout_percentages_are_marked_modelled(self) -> None:
        t = liq.scout_table(scout_doc())
        for col in t.columns:
            if col.pct:
                self.assertIn("modelled", col.header)
        self.assertIn("modelled", liq.scout_line(scout_doc(), NOW))


class TestKillSwitch(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "aero"  # does not exist yet

    def test_create_then_delete(self) -> None:
        self.assertFalse(liq.is_killed(self.home))
        self.assertTrue(liq.set_kill(True, self.home))
        self.assertTrue((self.home / "KILL").is_file())
        self.assertTrue(liq.is_killed(self.home))
        self.assertFalse(liq.set_kill(False, self.home))
        self.assertFalse((self.home / "KILL").exists())

    def test_idempotent_both_ways(self) -> None:
        liq.set_kill(True, self.home)
        first = (self.home / "KILL").read_text()
        self.assertTrue(liq.set_kill(True, self.home))
        self.assertEqual((self.home / "KILL").read_text(), first)
        self.assertFalse(liq.set_kill(False, self.home))
        self.assertFalse(liq.set_kill(False, self.home))

    def test_only_the_kill_file_is_written(self) -> None:
        self.home.mkdir()
        write(self.home, liq.STATUS_FILE, status_doc())
        before = (self.home / liq.STATUS_FILE).read_text()
        liq.set_kill(True, self.home)
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), ["KILL", "status.json"])
        self.assertEqual((self.home / liq.STATUS_FILE).read_text(), before)
        liq.set_kill(False, self.home)
        self.assertEqual([p.name for p in self.home.iterdir()], ["status.json"])

    def test_uses_env_home_by_default(self) -> None:
        with mock.patch.dict(os.environ, {"AERO_LP_HOME": str(self.home)}):
            liq.set_kill(True)
            self.assertTrue((self.home / "KILL").exists())
            liq.set_kill(False)
            self.assertFalse((self.home / "KILL").exists())


class TestNoOrderPath(unittest.TestCase):
    """soltui must stay free of keys, web3 and network access."""

    FORBIDDEN = {"aero_lp", "web3", "eth_account", "requests", "urllib", "http",
                 "socket", "httpx", "aiohttp", "subprocess"}

    def test_liquidity_module_imports(self) -> None:
        tree = ast.parse(Path(liq.__file__).read_text())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
        self.assertFalse(mods & self.FORBIDDEN, mods & self.FORBIDDEN)


class TestLiquidityTab(unittest.IsolatedAsyncioTestCase):
    """Mount the real app against a fixture state dir."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        patcher = mock.patch.dict(os.environ, {"AERO_LP_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _rows(app, sel: str) -> int:
        return app.query_one(sel, DataTable).row_count

    async def test_tab_exists_and_shows_no_data_without_files(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            self.assertTrue(app.query("#tab-liquidity"))
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            self.assertIn("no data", text_of(app, "#liq-summary"))
            self.assertEqual(self._rows(app, "#liq-positions"), 0)
            self.assertEqual(self._rows(app, "#liq-scout"), 0)

    async def test_fixture_populates_every_table(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc(generated_at=__import__("time").time()))
        write(self.home, liq.SCOUT_FILE, scout_doc())
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            self.assertEqual(self._rows(app, "#liq-positions"), 2)
            self.assertEqual(self._rows(app, "#liq-scout"), 3)
            self.assertEqual(self._rows(app, "#liq-experiments"), 2)
            self.assertEqual(self._rows(app, "#liq-actions"), 3)
            summary = text_of(app, "#liq-summary")
            self.assertIn("LIVE", summary)
            self.assertIn("live LP P&L", summary)
            self.assertEqual(text_of(app, "#liq-banner").strip(), "")

    async def test_corrupt_status_does_not_crash(self) -> None:
        write(self.home, liq.STATUS_FILE, "{oops")
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            self.assertIn("no data", text_of(app, "#liq-summary"))

    async def test_kill_and_resume_buttons_write_only_the_kill_file(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc(generated_at=__import__("time").time()))
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            await pilot.click("#liq-kill")
            await pilot.pause()
            self.assertTrue((self.home / "KILL").exists())
            self.assertIn("KILLED", text_of(app, "#liq-banner"))
            await pilot.click("#liq-resume")
            await pilot.pause()
            self.assertFalse((self.home / "KILL").exists())
            self.assertEqual(text_of(app, "#liq-banner").strip(), "")
            self.assertEqual(sorted(p.name for p in self.home.iterdir()), ["status.json"])

    async def test_killed_flag_in_status_shows_banner(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc(killed=True))
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertIn("KILLED", text_of(app, "#liq-banner"))

    async def test_refresh_button_and_tick_pick_up_a_new_file(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            self.assertEqual(self._rows(app, "#liq-positions"), 0)
            write(self.home, liq.STATUS_FILE, status_doc())
            app._liq_tick()
            await pilot.pause()
            self.assertEqual(self._rows(app, "#liq-positions"), 2)
            write(self.home, liq.STATUS_FILE, status_doc(positions=[]))
            await pilot.click("#liq-refresh")
            await pilot.pause()
            self.assertEqual(self._rows(app, "#liq-positions"), 0)

    async def test_bracketed_reason_is_not_parsed_as_markup(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc())
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-liquidity"
            await pilot.pause()
            cell = app.query_one("#liq-positions", DataTable).get_row_at(0)[-1]
            self.assertIn("[more]", str(cell))

    async def test_dry_run_is_not_styled_as_live(self) -> None:
        write(self.home, liq.STATUS_FILE, status_doc(mode="dry-run"))
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            summary = text_of(app, "#liq-summary")
            self.assertIn("dry-run LP P&L", summary)
            self.assertNotIn("LIVE", summary)


if __name__ == "__main__":
    unittest.main()
