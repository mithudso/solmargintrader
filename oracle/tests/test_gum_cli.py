"""CLI policy units and explicit live selection are part of the order boundary."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from oracle.cli import main


class GumCliTests(unittest.TestCase):
    def test_readonly_discovery_does_not_construct_signer_or_worker(self):
        stream = io.StringIO()
        with (
            patch(
                "oracle.gum_orders.discover",
                return_value={"accounts": {"exists": False}},
            ) as discover,
            patch("oracle.gum_signer.load_signer") as signer,
            patch("oracle.webhook.serve") as serve,
            redirect_stdout(stream),
        ):
            code = main(["jupiter-preflight", "--owner", "public-owner"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stream.getvalue())["ok"])
        discover.assert_called_once_with("public-owner")
        signer.assert_not_called()
        serve.assert_not_called()

    def test_jupiter_default_is_75_percent_dry_run_and_integer_slippage(self):
        with tempfile.TemporaryDirectory() as root:
            with (
                patch.dict(os.environ, {"ORACLE_WEBHOOK_SECRET": "test-secret-" * 4}),
                patch("oracle.gum_orders.GumOrders") as venue,
                patch("oracle.gum_signer.load_signer") as signer,
                patch("oracle.webhook.serve") as serve,
            ):
                venue.return_value.binding = "immutable-gum-policy"
                code = main(
                    [
                        "webhook",
                        "--inbox",
                        str(Path(root) / "gum.sqlite3"),
                        "--jupiter-perps",
                        "--owner",
                        "public-owner",
                        "--trading-account",
                        "public-account",
                        "--leverage",
                        "2",
                        "--allocation-basis",
                        "collateral",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(venue.call_args.kwargs["allocation"], "75")
            self.assertEqual(venue.call_args.kwargs["max_slippage_bps"], 10)
            self.assertIsNone(venue.call_args.kwargs["signer"])
            self.assertFalse(serve.call_args.kwargs["live"])
            self.assertEqual(
                serve.call_args.kwargs["portfolio_id"], "immutable-gum-policy"
            )
            self.assertEqual(
                serve.call_args.kwargs["processor"].__module__,
                "oracle.gum_webhook_orders",
            )
            signer.assert_not_called()

    def test_missing_account_leverage_basis_or_live_key_is_refused(self):
        base = ["webhook", "--inbox", "/unused/gum.sqlite3", "--jupiter-perps"]
        for args in [
            [],
            ["--owner", "public-owner", "--trading-account", "public-account"],
            [
                "--owner",
                "public-owner",
                "--trading-account",
                "public-account",
                "--leverage",
                "2",
            ],
            [
                "--owner",
                "public-owner",
                "--trading-account",
                "public-account",
                "--leverage",
                "2",
                "--allocation-basis",
                "collateral",
                "--live",
            ],
        ]:
            with (
                self.subTest(args=args),
                patch("oracle.gum_orders.GumOrders") as venue,
                patch("oracle.webhook.serve") as serve,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(base + args), 2)
                venue.assert_not_called()
                serve.assert_not_called()
