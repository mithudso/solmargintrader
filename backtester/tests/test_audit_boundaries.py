from __future__ import annotations

import csv
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from backtester import botcli, cli
from backtester.core import archive_price, data, kucoin_history, pairs, strategy_cards
from backtester.core.types import BarWindow
from backtester.tests import test_history_store as history_fixtures


class AuditBoundaryTests(unittest.TestCase):
    def test_archiver_refuses_unusable_financial_prices(self):
        for price in (True, float("nan"), float("inf"), 10**400):
            response = MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = json.dumps({"mint": {"usdPrice": price}}).encode()
            with self.subTest(price=type(price).__name__), patch.object(archive_price.urllib.request, "urlopen", return_value=response), self.assertRaises(archive_price.ArchiveError):
                archive_price.fetch_spot("mint")

    def test_archiver_nonobject_payload_uses_fetch_error_contract(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"[]"
        with patch.object(archive_price.urllib.request, "urlopen", return_value=response), self.assertRaises(archive_price.ArchiveError):
            archive_price.fetch_spot("mint")

    def test_invalid_direct_append_creates_no_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prices.csv"
            with self.assertRaises(archive_price.ArchiveError):
                archive_price.append_observation(path, "mint", float("inf"))
            self.assertFalse(path.exists())

    def test_stale_existence_checks_cannot_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prices.csv"
            with patch.object(Path, "exists", return_value=False):
                archive_price.append_observation(path, "mint", 1)
                archive_price.append_observation(path, "mint", 2)
            with path.open() as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(rows.count(list(archive_price.HEADER)), 1)
            self.assertEqual(len(rows), 3)

    def test_explicit_midnight_does_not_expand_to_whole_day(self):
        frame = pd.DataFrame({"timestamp": [0, 43200]})
        self.assertEqual(data._slice_dates(frame, None, "1970-01-01T00:00:00")["timestamp"].tolist(), [0])
        self.assertEqual(data._slice_dates(frame, None, "1970-01-01")["timestamp"].tolist(), [0, 43200])

    def test_snapshot_cutoff_one_second_before_close_excludes_that_bar(self):
        fixture = history_fixtures.HistoryStoreTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        key = history_fixtures.import_history(fixture.db, fixture.csv, **fixture.kw)
        frame = data.SnapshotLoader(fixture.db, key).load("SOL", None, "1970-01-01 00:01:59", "1m")
        self.assertEqual(frame["timestamp"].tolist(), [0])

    def test_provider_timestamp_is_an_exact_integer(self):
        for timestamp in (0.9, True, "0.9"):
            raw = json.dumps({"code": "200000", "data": [[timestamp, "1", "1", "1", "1", "0", "0"]]}).encode()
            with self.subTest(timestamp=timestamp), self.assertRaises(kucoin_history.HistoryError):
                kucoin_history.decode_page(raw, 0, 60)

    def test_provider_read_is_bounded_before_json_parse(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = lambda maximum=None: b"[]" if maximum is None else b"x" * maximum
        with patch.object(kucoin_history.urllib.request, "urlopen", return_value=response), self.assertRaises(kucoin_history.HistoryError):
            kucoin_history._get_unlocked("https://invalid.example")
        self.assertIsInstance(response.read.call_args.args[0], int)

    def test_trailing_comment_cannot_change_scalar_type(self):
        with self.assertRaises(strategy_cards.CardError):
            strategy_cards._parse_scalar("12 # comment", where="synthetic")
        self.assertEqual(strategy_cards._parse_scalar('"a # literal"', where="synthetic"), "a # literal")

    def test_presets_obey_declared_parameter_types(self):
        path = strategy_cards.CARD_DIR / "ma_crossover.md"
        text = path.read_text().replace("short: {fast: 12,", "short: {fast: 12.5,")
        with self.assertRaises(strategy_cards.CardError):
            strategy_cards.load_card(path, text=text)

    def test_nonfinite_pair_stop_is_refused(self):
        for stop in (float("nan"), float("-inf"), float("inf")):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                pairs.PeerSpreadReversion(stop_z=stop)

    def test_refused_pair_window_clears_holding_state(self):
        values = np.ones(80) * 10
        strategy = pairs.PeerSpreadReversion(peer_closes=values, fit_window=30)
        strategy._holding = True
        window = BarWindow(np.arange(80) * 86400, values, values, values, values, values, 40)
        with patch.object(pairs, "engle_granger", side_effect=ValueError("invalid window")):
            self.assertEqual(strategy.on_bar(window), 0)
        self.assertFalse(strategy._holding)

    def test_invalid_boolean_cannot_disable_depth_constraints(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            botcli.build_parser().parse_args(["triangle", "--snapshots", "synthetic", "--use-displayed-size", "tru"])

    def test_missing_snapshot_is_a_cli_refusal(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            args = botcli.build_parser().parse_args(["triangle", "--snapshots", str(Path(directory) / "missing.jsonl"), "--json"])
            with patch.object(botcli, "read_snapshot_files", side_effect=AssertionError("validate input existence first")):
                self.assertNotEqual(botcli._triangle(args), 0)

    def test_perp_cli_passes_requested_fee_to_its_cost_model(self):
        split = SimpleNamespace(full=SimpleNamespace(strategy_name="buy_and_hold", params={}))
        with (patch.object(cli, "_run_one", return_value=split) as run,
              patch.object(cli.report, "render_report", return_value="synthetic"),
              patch.object(cli.report, "library_versions", return_value={}), redirect_stdout(StringIO())):
            self.assertEqual(cli.main(["--synthetic", "4", "--start", "1970-01-01", "--mode", "perp", "--fee-bps", "15", "--strategy", "buy_and_hold", "--no-charts"]), 0)
        self.assertEqual(run.call_args.args[2].costs.perp_base_fee_bps, 15)
