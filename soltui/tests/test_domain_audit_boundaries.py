"""Malformed local evidence and public explorer data never become valid facts."""
from __future__ import annotations

import csv
import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from soltui import (
    analyze,
    bots,
    coin_fit,
    cumulative,
    live_score,
    signals,
    top5,
    utxo_scan,
    wallet_activity,
)
from soltui.wallet import WalletHttpError


class DomainBoundaryTests(unittest.TestCase):
    def test_signal_defaults_reject_invalid_declared_numbers(self):
        for field, value in (("sma_fast", 2.5), ("sma_fast", True),
                             ("bollinger_std", float("nan")), ("vol_target", float("inf")),
                             ("dual_skip", 0.5), ("hurst_lag", True),
                             ("adx_threshold", "untrusted")):
            with self.subTest(field=field, value=value), self.assertRaises(signals.SignalError):
                signals.from_dict({field: value})
        with self.assertRaises(signals.SignalError):
            signals.from_dict(["invalid object"])
        self.assertEqual(signals.from_dict({"sma_fast": 10}).sma_fast, 10)

    def test_cumulative_invalid_evidence_stays_unranked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            path.write_text("label,median_sharpe,total_trades,n_paths\n"
                            "valid,0.5,12,5\ninfinite,inf,12,5\n"
                            "invalid-count,0.7,inf,5\nfractional,0.8,10.5,5\n"
                            "missing,nan,12,5\n")
            summary = cumulative.load_result_file(path)
            self.assertEqual([r.label for r in summary.rankable], ["valid"])
            self.assertEqual(summary.best.label, "valid")
            self.assertEqual(len(summary.below_floor), 4)

    def test_top5_nonfinite_metrics_and_counts_cannot_crash_or_win(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top5.csv"
            path.write_text("asset,rank,label,horizon,median_sharpe,total_trades,n_paths\n"
                            "SOL,1,rsi,long,0.5,12,5\nSOL,2,macd,long,inf,12,5\n"
                            "SOL,3,grid,long,0.2,inf,2.5\n")
            configs = top5.load_top5(path)
            self.assertEqual([c.rank for c in configs], [1, 3])
            self.assertIsNone(configs[1].home.trades)
            self.assertIsNone(configs[1].home.n_paths)

    def test_top5_rank_cannot_pool_different_configurations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top5.csv"
            path.write_text("asset,rank,label,horizon,median_sharpe\n"
                            "SOL,1,rsi,long,0.5\nDOGE,1,grid,long,0.4\n")
            with self.assertRaises(top5.EvidenceUnavailable):
                top5.load_top5(path)

    def test_explorer_counters_use_sanitized_domain_errors(self):
        for value in (float("inf"), float("nan"), -1, 1.5, True):
            with self.subTest(value=value), self.assertRaises(WalletHttpError):
                utxo_scan._int(value)
        self.assertEqual(utxo_scan._int(42), 42)

    def test_blockcypher_error_cannot_echo_private_derived_address(self):
        canary = "DERIVED-ADDRESS-PRIVATE-CANARY"
        backend = utxo_scan.BlockCypherBackend(lambda _url: {"error": canary})
        with self.assertRaises(WalletHttpError) as captured:
            backend.stats(["inert-address"])
        self.assertNotIn(canary, str(captured.exception))

    def test_live_vote_requires_whole_counts_and_a_valid_clock(self):
        row = {"label": "strategy", "accuracy": 75., "resolved": 20,
               "pred_1m": "UP", "acc_1m": 75., "resolved_1m": 20,
               "issued_1m": 0., "expires_1m": 100.}
        self.assertTrue(live_score.aggregate_predictions([row], now=1.)["available"])
        for changes, kwargs in (({"resolved": 20.5}, {"now": 1.}),
                                ({}, {"now": True}),
                                ({}, {"now": 1., "min_resolved": 10 ** 400})):
            with self.subTest(changes=changes, kwargs=kwargs):
                self.assertFalse(live_score.aggregate_predictions([{**row, **changes}], **kwargs)["available"])

    def test_analysis_price_change_uses_the_same_replayed_array(self):
        arrays = {"close": np.array([100., 110.])}
        with patch.object(analyze, "_prepare", return_value=(arrays, 1, analyze.parse_as_of("2026-01-01"), False)), \
                patch("research.decide.strategy_decisions", return_value=[]), \
                patch.object(analyze, "_first_close", return_value=9999.) as reload:
            result = analyze.analyse("INERT")
        self.assertAlmostEqual(result.net_pct, .1)
        reload.assert_not_called()

    def test_coinfit_huge_input_refuses_with_domain_error(self):
        with self.assertRaises(bots.BotError):
            coin_fit._finite(10 ** 400, "capital")

    def test_coinfit_output_cannot_overwrite_loaded_candles(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "SOL_1h.csv"
            source.write_text("original market input\n")
            report = {"errors": {}, "rows": [{"data_source": str(source)}]}
            with patch.object(coin_fit, "rank_coins", return_value=report), \
                    patch.object(coin_fit, "render_report", return_value="would destroy input"), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                try:
                    result = coin_fit.cli_main(["--coin", "SOL", "--data-dir", directory, "--output", str(source)])
                except SystemExit as exc:
                    result = exc.code
            self.assertEqual(result, 2)
            self.assertEqual(source.read_text(), "original market input\n")

    def test_coinfit_csv_cells_are_literal_and_negative_results_remain_numeric(self):
        report = {"bot": "grid", "mode": "quick", "common_start": 0, "common_end": 3600,
                  "capital_usd": 1000, "fee_bps": 6, "slippage_bps": 2,
                  "rows": [{"rank": 1, "coin": "=1+1", "fit": "INSUFFICIENT_DATA",
                            "reason": "@PRIVATE-INPUT", "metrics": {"total_return": -.1}}]}
        values = next(csv.DictReader(io.StringIO(coin_fit.render_report([report], "csv"))))
        self.assertEqual(values["coin"], "'=1+1")
        self.assertEqual(values["reason"], "'@PRIVATE-INPUT")
        self.assertEqual(values["net_return"], "-0.1")

    def test_coinfit_bad_csv_cell_does_not_escape_into_report(self):
        canary = "PRIVATE-CSV-CELL-CANARY"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SOL_1h.csv"
            path.write_text("timestamp,open,high,low,close,volume\n"
                            f"3600,1,1,1,{canary},1\n")
            report = coin_fit.rank_coins("grid", ["SOL"], SimpleNamespace(data_dir=directory),
                                         days=7, config=dict(bots.GRID_DEFAULTS))
        self.assertNotIn(canary, str(report))
        self.assertEqual(report["rows"][0]["fit"], "INSUFFICIENT_DATA")

    def test_wallet_history_transport_events_never_include_input_or_exception_text(self):
        canary = "PRIVATE-RPC-OR-CREDENTIAL-CANARY"
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"result": []}'
        with patch.object(wallet_activity.urllib.request, "urlopen", return_value=response), \
                self.assertLogs(wallet_activity.logger, level="DEBUG") as success:
            self.assertEqual(wallet_activity._rpc("getSignaturesForAddress", [canary], 1.), [])
        self.assertEqual([record.phase for record in success.records], ["request", "success"])
        with patch.object(wallet_activity.urllib.request, "urlopen", side_effect=urllib.error.URLError(canary)), \
                self.assertLogs(wallet_activity.logger, level="DEBUG") as failure, \
                self.assertRaises(urllib.error.URLError):
            wallet_activity._rpc("getSignaturesForAddress", [canary], 1.)
        self.assertEqual([record.phase for record in failure.records], ["request", "failure"])
        self.assertEqual(failure.records[-1].error_kind, "URLError")
        self.assertNotIn(canary, " ".join(success.output + failure.output))

    def test_cdp_history_records_request_outcome_without_sql_or_stderr(self):
        canary = "PRIVATE-CDP-SQL-AND-STDERR-CANARY"
        result = SimpleNamespace(returncode=0, stdout='{"result": []}', stderr=canary)
        with patch.object(wallet_activity.shutil, "which", return_value="/inert/cdp"), \
                patch.object(wallet_activity.subprocess, "run", return_value=result) as run, \
                self.assertLogs(wallet_activity.logger, level="DEBUG") as success:
            self.assertEqual(wallet_activity._cdp_query(canary, 1.), [])
        self.assertIn("sql=" + canary, run.call_args.args[0])
        self.assertEqual([record.phase for record in success.records], ["request", "success"])
        result.returncode = 1
        with patch.object(wallet_activity.shutil, "which", return_value="/inert/cdp"), \
                patch.object(wallet_activity.subprocess, "run", return_value=result), \
                self.assertLogs(wallet_activity.logger, level="DEBUG") as failure, self.assertRaises(RuntimeError):
            wallet_activity._cdp_query(canary, 1.)
        self.assertEqual([record.phase for record in failure.records], ["request", "failure"])
        self.assertNotIn(canary, " ".join(success.output + failure.output))


if __name__ == "__main__":
    unittest.main()
