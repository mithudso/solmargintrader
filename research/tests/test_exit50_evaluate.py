import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EvaluationGateTests(unittest.TestCase):
    def test_pending_source_blocks_final_evaluation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            models = root / "models.json"
            models.write_text("{}")
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "asset": "BTC",
                        "all_needed_count": 1,
                        "selected_slots": [{"asset": "BTC", "slot": 600}],
                        "cases": [],
                    }
                )
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research.exit50_evaluate",
                    "--asset",
                    "BTC",
                    "--plan",
                    str(plan),
                    "--entry-root",
                    td,
                    "--cache-root",
                    td,
                    "--models",
                    str(models),
                    "--output",
                    str(root / "output.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cohort_source_proof_incomplete", result.stderr)
            self.assertFalse((root / "output.json").exists())


if __name__ == "__main__":
    unittest.main()
