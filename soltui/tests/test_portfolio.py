"""Snapshots, balance changes, the notice line, the wallet value curve and the hourly LaunchAgent plist."""

from __future__ import annotations

import json
import os
import plistlib
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from soltui import commands, config, pnl, portfolio, portfolio_agent
from soltui.tests.bridge_support import World
from soltui.tests.test_hdwallet import V2_M
from soltui.tests.test_utxo_scan import Net, addr


def chain(status="ok", balances=None, prices=None, usd=None, complete=True, **extra):
    balances = balances or {}
    prices = prices or {}
    usd = sum(balances[s] * prices.get(s, 0.0) for s in balances) if usd is None else usd
    return {"status": status, "balances": balances, "prices": prices, "usd": usd, "usd_complete": complete,
            "unpriced": [] if complete else ["X"], "positions": 0, **extra}


def snap(ts, chains, complete=True):
    total = sum(c["usd"] for c in chains.values())
    return {"ts": ts, "at": f"2026-11-0{int(ts)}T00:00:00+00:00", "label": "wallet (live)", "partial": not complete,
            "total_usd": total, "total_complete": complete and all(c["status"] == "ok" for c in chains.values()),
            "chains": chains}


class DiffTests(unittest.TestCase):
    def test_balance_change_with_usd_effect(self) -> None:
        old = snap(1, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 100.0}),
                       "solana": chain(balances={"SOL": 5.0}, prices={"SOL": 10.0})})
        new = snap(2, {"bitcoin": chain(balances={"BTC": 1.5}, prices={"BTC": 110.0}),
                       "solana": chain(balances={"SOL": 5.0}, prices={"SOL": 10.0})})
        rep = portfolio.diff_snapshots(old, new)
        (c,) = rep["changes"]
        self.assertEqual((c["chain"], c["symbol"], c["delta"]), ("bitcoin", "BTC", 0.5))
        self.assertAlmostEqual(c["usd_delta"], 55.0)
        self.assertAlmostEqual(rep["value"]["change_usd"], 215.0 - 150.0)   # the value change includes the price move
        self.assertEqual(rep["skipped"], [])

    def test_a_failed_or_partial_read_is_skipped_not_reported_as_a_loss(self) -> None:
        old = snap(1, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 100.0})})
        for bad in ("partial", "error"):
            new = snap(2, {"bitcoin": chain(status=bad, balances={})})
            rep = portfolio.diff_snapshots(old, new)
            self.assertEqual(rep["changes"], [])
            self.assertEqual(rep["skipped"][0]["chain"], "bitcoin")
            self.assertIsNone(rep["value"]["change_usd"])

    def test_a_newly_added_chain_is_not_a_change(self) -> None:
        old = snap(1, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 1.0})})
        new = snap(2, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 1.0}),
                       "litecoin": chain(balances={"LTC": 9.0}, prices={"LTC": 1.0})})
        rep = portfolio.diff_snapshots(old, new)
        self.assertEqual(rep["changes"], [])
        self.assertIn("no earlier snapshot", rep["skipped"][0]["reason"])

    def test_unpriced_change_has_unknown_usd(self) -> None:
        old = snap(1, {"dogecoin": chain(balances={"DOGE": 1.0}, complete=False, usd=0.0)})
        new = snap(2, {"dogecoin": chain(balances={"DOGE": 3.0}, complete=False, usd=0.0)})
        (c,) = portfolio.diff_snapshots(old, new)["changes"]
        self.assertIsNone(c["usd_delta"])

    def test_dust_noise_below_tolerance_is_not_a_change(self) -> None:
        old = snap(1, {"bitcoin": chain(balances={"BTC": 1.0})})
        new = snap(2, {"bitcoin": chain(balances={"BTC": 1.0 + 1e-12})})
        self.assertEqual(portfolio.diff_snapshots(old, new)["changes"], [])

    def test_changes_report_windows(self) -> None:
        a = snap(1, {"bitcoin": chain(balances={"BTC": 1.0})})
        b = snap(1 + 3600 * 5, {"bitcoin": chain(balances={"BTC": 2.0})})
        c = snap(1 + 3600 * 6, {"bitcoin": chain(balances={"BTC": 2.5})})
        self.assertEqual(portfolio.changes_report([a], None)["changes"], [])
        self.assertIn("need two", portfolio.changes_report([a])["message"])
        self.assertEqual(portfolio.changes_report([a, b, c])["changes"][0]["delta"], 0.5)
        self.assertEqual(portfolio.changes_report([a, b, c], hours=5.5)["changes"][0]["delta"], 1.5)
        self.assertIn("no snapshot", portfolio.changes_report([a, b, c], hours=100)["message"])


class ValueCurveTests(unittest.TestCase):
    def test_only_complete_snapshots_of_the_same_wallets_are_used(self) -> None:
        a = snap(1, {"bitcoin": chain(balances={"BTC": 1.0}, usd=100.0)})
        partial = snap(2, {"bitcoin": chain(status="partial", usd=1.0)})
        other_set = snap(3, {"bitcoin": chain(usd=100.0), "solana": chain(usd=5.0)})
        latest = snap(4, {"bitcoin": chain(usd=120.0), "solana": chain(usd=5.0)})
        rows, left_out = portfolio.value_rows([a, partial, other_set, latest])
        self.assertEqual([r["total_usd"] for r in rows], [105.0, 125.0])
        self.assertEqual(left_out, 2)

    def test_the_value_curve_feeds_the_wallet_live_pnl_section_alone(self) -> None:
        rows, _ = portfolio.value_rows([snap(1, {"bitcoin": chain(usd=100.0)}),
                                        snap(2, {"bitcoin": chain(usd=110.0)})])
        curve = pnl.curve_from_wallet_history(rows)
        self.assertEqual(curve.source, "wallet (live)")
        self.assertTrue(curve.value_only)


class StorageAndNoticeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"SOLTUI_SUPPORT_DIR": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)

    def test_files_are_mode_600_and_hold_no_address(self) -> None:
        result = {"ts": 1.0, "scanned_at": "2026-11-01T00:00:00+00:00", "partial": False, "total_usd": 5.0,
                  "chains": {"solana": {
                      "status": "ok", "total_usd": 5.0, "total_complete": True, "unpriced": [],
                      "address": "SomePublicAddressThatMustNotBeStored", "native": {
                          "symbol": "SOL", "amount": 1.0, "price_usd": 5.0, "usd": 5.0, "kind": "native"},
                      "holdings": [], "stakes": [], "positions": []}}}
        s = portfolio.build_snapshot(result)
        path = portfolio.append_snapshot(s)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertNotIn("SomePublicAddress", path.read_text())
        self.assertEqual(portfolio.load_snapshots()[0]["chains"]["solana"]["balances"], {"SOL": 1.0})
        portfolio.notice(mark_seen=True)
        self.assertEqual(stat.S_IMODE(os.stat(Path(self.tmp.name) / "portfolio" / "last-view.json").st_mode), 0o600)

    def test_airdrop_flagged_holdings_do_not_count_toward_balances(self) -> None:
        result = {"ts": 1.0, "scanned_at": "x", "partial": False, "total_usd": 0.0, "chains": {"base": {
            "status": "ok", "total_usd": 0.0, "native": None, "stakes": [], "positions": [],
            "holdings": [{"symbol": "SPAM", "amount": 9.0, "included": False, "airdrop": True, "kind": "erc20",
                          "price_usd": None, "usd": None}]}}}
        self.assertEqual(portfolio.build_snapshot(result)["chains"]["base"]["balances"], {})

    def test_notice_flow(self) -> None:
        self.assertFalse(portfolio.notice()["changed"])                       # no snapshots
        portfolio.append_snapshot(snap(1, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 100.0})}))
        self.assertFalse(portfolio.notice()["changed"])                       # one snapshot, nothing to compare
        portfolio.append_snapshot(snap(2, {"bitcoin": chain(balances={"BTC": 1.25}, prices={"BTC": 100.0})}))
        n = portfolio.notice()
        self.assertTrue(n["changed"])
        self.assertIn("BTC +0.25", n["line"])
        self.assertIn("wallet (live)", n["line"])
        self.assertTrue(portfolio.notice()["changed"])                        # not marked yet: still news
        portfolio.notice(mark_seen=True)
        self.assertFalse(portfolio.notice()["changed"])                       # seen
        portfolio.append_snapshot(snap(3, {"bitcoin": chain(balances={"BTC": 1.25}, prices={"BTC": 100.0})}))
        self.assertFalse(portfolio.notice()["changed"])                       # a snapshot with no change is quiet
        portfolio.append_snapshot(snap(4, {"bitcoin": chain(balances={"BTC": 1.0}, prices={"BTC": 100.0})}))
        self.assertIn("BTC -0.25", portfolio.notice()["line"])

    def test_a_corrupt_line_is_skipped(self) -> None:
        path = portfolio.snapshots_path()
        path.parent.mkdir(parents=True)
        path.write_text('not json\n{"ts": "x"}\n')
        self.assertEqual(portfolio.load_snapshots(), [])


class LastScanTests(unittest.TestCase):
    """The Wallet tab forgot the wallet on every restart: a scan lived only in the widgets."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"SOLTUI_SUPPORT_DIR": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)

    def test_round_trip_owner_only_and_a_torn_file_reads_as_none(self) -> None:
        self.assertIsNone(portfolio.load_last_scan())
        path = portfolio.save_last_scan({"total_usd": 12.5, "chains": {}}, "all")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        last = portfolio.load_last_scan()
        self.assertEqual((last["chain"], last["result"]["total_usd"]), ("all", 12.5))
        path.write_text("{torn")
        self.assertIsNone(portfolio.load_last_scan())

    def test_a_scan_is_kept_and_portfolio_last_returns_it(self) -> None:
        fake = {"scanned_at": "2026-11-07 12:00", "chains": {}, "partial": False, "total_usd": 1.0,
                "skipped": [], "counts": {}}
        with mock.patch.object(commands, "_portfolio_scan", return_value=fake):
            env = commands.dispatch("portfolio.scan", {"chain": "solana"}, surface="cli")
        self.assertTrue(env["ok"], env)
        last = commands.dispatch("portfolio.last", {}, surface="cli")["result"]
        self.assertEqual(last["chain"], "solana")
        self.assertEqual(last["result"]["scanned_at"], "2026-11-07 12:00")


class SnapshotCommandTests(unittest.TestCase):
    """portfolio.snapshot end to end with a fake network and xpubs from a public test vector."""

    def test_snapshot_changes_and_notice_commands(self) -> None:
        with World() as world:
            hist = {addr("btc", V2_M, "p2wpkh", 0, 0): (100_000_000, 1)}
            net = Net(hist)
            config.save_settings(config.Settings(btc_xpub=V2_M, solana_address="", base_address=""))
            with mock.patch("soltui.wallet.HttpFetcher", lambda *a, **k: net):
                first = commands.dispatch("portfolio.snapshot", {}, surface="cli")
                hist[addr("btc", V2_M, "p2wpkh", 0, 1)] = (50_000_000, 1)
                second = commands.dispatch("portfolio.snapshot", {}, surface="cli")
            self.assertTrue(first["ok"] and second["ok"], (first, second))
            r = second["result"]
            self.assertEqual(r["label"], "wallet (live)")
            self.assertEqual(r["chains"]["bitcoin"]["script_types"], ["p2wpkh"])
            self.assertAlmostEqual(r["chains"]["bitcoin"]["total_usd"], 75_000.0)
            self.assertNotIn(V2_M, json.dumps(second))
            ch = commands.dispatch("portfolio.changes", {}, surface="cli")["result"]
            (c,) = ch["changes"]
            self.assertEqual((c["chain"], c["symbol"]), ("bitcoin", "BTC"))
            self.assertAlmostEqual(c["delta"], 0.5)
            notice = commands.dispatch("portfolio.notice", {}, surface="cli")["result"]
            self.assertTrue(notice["changed"])
            pnl_rep = commands.dispatch("pnl.summary", {"window": "all", "source": "wallet"}, surface="cli")["result"]
            (sec,) = pnl_rep["sections"]
            self.assertEqual(sec["source"], "wallet (live)")
            self.assertEqual(sec["group"], "real")
            self.assertEqual(world.log_lines()[-1]["command"], "pnl.summary")

    def test_snapshot_with_nothing_configured_fails_clearly(self) -> None:
        with World():
            config.save_settings(config.Settings(solana_address="", base_address=""))
            env = commands.dispatch("portfolio.snapshot", {}, surface="cli")
            self.assertFalse(env["ok"])
            self.assertIn("nothing to snapshot", env["error"]["message"])

    def test_commands_are_registered_with_the_right_flags(self) -> None:
        reg = commands.COMMANDS
        self.assertTrue(reg["portfolio.changes"].read_only)
        self.assertTrue(reg["wallet.addresses"].read_only)
        self.assertFalse(reg["portfolio.snapshot"].read_only)
        self.assertTrue(reg["portfolio.snapshot"].long_running)
        self.assertFalse(any(reg[n].requires_confirm for n in reg if n.startswith(("portfolio.", "wallet."))))


class AgentTests(unittest.TestCase):
    def test_plist_runs_the_snapshot_hourly_through_the_registry(self) -> None:
        d = portfolio_agent.plist_dict(Path("/venv/bin/python"), Path("/repo"))
        self.assertEqual(d["Label"], "com.mitchhudson.soltui.portfolio")
        self.assertEqual(d["StartInterval"], 3600)
        self.assertTrue(d["RunAtLoad"])
        self.assertEqual(d["ProgramArguments"],
                         ["/venv/bin/python", "-m", "soltui.cli", "call", "portfolio.snapshot"])
        self.assertEqual(d["WorkingDirectory"], "/repo")
        round_trip = plistlib.loads(plistlib.dumps(d))
        self.assertEqual(round_trip, d)
        self.assertNotIn("xpub", json.dumps(d))

    def test_install_writes_the_plist_without_starting_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"SOLTUI_LAUNCHAGENTS_DIR": tmp}):
            py = Path(tmp) / "python"
            py.write_text("")
            with mock.patch.object(portfolio_agent, "_launchctl") as lc, mock.patch.object(
                portfolio_agent, "log_path", return_value=Path(tmp) / "logs" / "portfolio.log"
            ):
                out = portfolio_agent.install(py, Path("/repo"), start=False)
                lc.assert_not_called()
                self.assertEqual(plistlib.loads(Path(out["plist"]).read_bytes())["Label"], portfolio_agent.LABEL)
                self.assertTrue(portfolio_agent.uninstall()["removed"])
                lc.assert_called_once_with("bootout", f"{portfolio_agent.domain()}/{portfolio_agent.LABEL}")


if __name__ == "__main__":
    unittest.main()
