"""Offline bridge parity and safety gates for the shared owner."""

import unittest
from unittest.mock import patch

from soltui import commands


class AutoTradeRegistryTest(unittest.TestCase):
    def test_status_and_mutations_forward_same_arguments(self):
        cases = [
            ("autotrade.status", {}, "status", ()),
            (
                "autotrade.start_paper",
                {"request_id": "a", "config": {"mode": "paper"}},
                "start",
                ("a", {"mode": "paper"}),
            ),
            (
                "autotrade.start_live",
                {"request_id": "b", "config": {"mode": "live"}, "confirm": True},
                "start",
                ("b", {"mode": "live"}),
            ),
            ("autotrade.stop", {"request_id": "c"}, "stop", ("c", False)),
            (
                "autotrade.configure",
                {"request_id": "d", "config": {}},
                "configure",
                ("d", {}),
            ),
            (
                "autotrade.ingest_forecast",
                {"request_id": "e", "forecast": {"forecast_id": "f"}},
                "ingest_forecast",
                ("e", {"forecast_id": "f"}),
            ),
        ]
        for name, params, method, args in cases:
            with (
                self.subTest(name=name),
                patch(
                    "soltui.commands._autotrade_call", return_value={"state": "stopped"}
                ) as call,
            ):
                for surface in ("tui", "native", "api"):
                    result = commands.dispatch(
                        name, params, surface=surface, ctx=object(), quiet=True
                    )
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(result["result"], {"state": "stopped"})
                self.assertEqual(call.call_args.args, (method, *args))

    def test_live_requires_confirmation_and_paper_cannot_smuggle_live(self):
        with patch("soltui.commands._autotrade_call") as call:
            denied = commands.dispatch(
                "autotrade.start_live",
                {"request_id": "a", "config": {"mode": "live"}},
                ctx=object(),
                quiet=True,
            )
            self.assertEqual(denied["error"]["code"], "forbidden")
            bad = commands.dispatch(
                "autotrade.start_paper",
                {"request_id": "a", "config": {"mode": "live"}},
                ctx=object(),
                quiet=True,
            )
            self.assertEqual(bad["error"]["code"], "bad_params")
            call.assert_not_called()

    def test_validation_error_has_standard_envelope(self):
        with patch(
            "oracle_leverage.autotrade.start", side_effect=ValueError("precise refusal")
        ):
            result = commands.dispatch(
                "autotrade.start_paper",
                {"request_id": "a", "config": {"mode": "paper"}},
                ctx=object(),
                quiet=True,
            )
        self.assertEqual(
            result["error"], {"code": "bad_params", "message": "precise refusal"}
        )

    def test_status_never_exports_parameters_or_feature_vectors(self):
        with patch(
            "oracle_leverage.autotrade.status",
            return_value={
                "learner": {"weights": [1], "samples": 5},
                "position": {"forecast": {"features": [1], "score": 0.5}},
            },
        ):
            result = commands.dispatch("autotrade.status", {}, ctx=object(), quiet=True)
        self.assertEqual(
            result["result"],
            {
                "learner": {"samples": 5},
                "position": {"forecast": {"score": 0.5}},
            },
        )


if __name__ == "__main__":
    unittest.main()
