import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from research.exit50_lazy import main
from research.reversal_shapes import boundaries


class FetchConcurrencyTests(unittest.TestCase):
    def test_two_workers_preserve_plan_bindings_out_of_order(self):
        start = boundaries()[0]
        slots = [(start // 120 + 2 + i) * 120 for i in range(6)]
        lock = threading.Lock()
        state = {"active": 0, "maximum": 0, "completion": []}

        def fake_fetch(job):
            asset, slot, _root = job
            with lock:
                state["active"] += 1
                state["maximum"] = max(state["maximum"], state["active"])
            time.sleep(0.03 if slot == slots[0] else 0.002)
            with lock:
                state["active"] -= 1
                state["completion"].append(slot)
            return {
                "asset": asset,
                "slot": slot,
                "status": 200,
                "sha256": hashlib.sha256(str(slot).encode()).hexdigest(),
            }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / "plan.json"
            output = root / "wave"
            plan.write_text(
                json.dumps(
                    {
                        "schema": "exit50-lazy-wave-plan/v1",
                        "selected_slots": [{"asset": "BTC", "slot": s} for s in slots],
                    }
                )
            )
            argv = [
                "exit50_lazy",
                "fetch",
                "--plan",
                str(plan),
                "--output",
                str(output),
                "--workers",
                "2",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("research.exit50_lazy.fetch_one", side_effect=fake_fetch),
            ):
                main()
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(
                manifest["plan_sha256"], hashlib.sha256(plan.read_bytes()).hexdigest()
            )
            self.assertEqual([r["slot"] for r in manifest["records"]], slots)
            for record in manifest["records"]:
                self.assertEqual(
                    record["sha256"],
                    hashlib.sha256(str(record["slot"]).encode()).hexdigest(),
                )
        self.assertLessEqual(state["maximum"], 2)
        self.assertEqual(state["maximum"], 2)
        self.assertNotEqual(state["completion"][0], slots[0])


if __name__ == "__main__":
    unittest.main()
