"""botcli: the DCA bot and the triangle replay run from the command line, offline."""

from __future__ import annotations

import contextlib
import gzip
import io
import json
import tempfile
import unittest
from pathlib import Path

from backtester import botcli


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = botcli.main(argv)
    return code, out.getvalue(), err.getvalue()


class BotCli(unittest.TestCase):
    def test_no_arguments_prints_usage(self) -> None:
        code, out, _ = run([])
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())

    def test_dca_on_synthetic_data_prints_the_plan_and_json(self) -> None:
        code, out, _ = run(["dca", "--synthetic", "300", "--max-safety-orders", "3"])
        self.assertEqual(code, 0)
        self.assertIn("safety 3", out)
        self.assertIn("NOT investment advice", out)
        code, out, _ = run(["dca", "--synthetic", "300", "--json"])
        payload = json.loads(out)
        self.assertIn("hold_total_return", payload)
        self.assertIn("disclaimer", payload)

    def test_a_bad_config_exits_2(self) -> None:
        code, _, err = run(["dca", "--synthetic", "50", "--take-profit-pct", "0"])
        self.assertEqual(code, 2)
        self.assertIn("take_profit_pct", err)

    def test_triangle_replays_recorded_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-11-08.jsonl.gz"
            with gzip.open(path, "wt") as fh:
                for t in range(5):
                    fh.write(json.dumps({"t": t, "q": {"ETH-USD": [3000, 3000.3, 3000, 1, 1, t],
                                                       "BTC-USD": [60000, 60006, 60000, 1, 1, t],
                                                       "ETH-BTC": [0.05, 0.050005, 0.05, 1, 1, t]}}) + "\n")
            code, out, _ = run(["triangle", "--snapshots", str(path), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["triangles"], ["USD-ETH-BTC"])
        self.assertEqual(payload["snapshots"], 5)
        self.assertEqual(payload["executed"], 0)


if __name__ == "__main__":
    unittest.main()
