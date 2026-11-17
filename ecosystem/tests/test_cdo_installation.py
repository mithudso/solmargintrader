"""Concurrent installation reuse must not replace an already completed owner."""
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ecosystem import installation


class InstallationRaceTests(unittest.TestCase):
    def test_completion_between_precheck_and_lock_is_reused_without_pip(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            env = root / "venv"
            env.mkdir()
            (env / "pyvenv.cfg").write_text("fixture")
            receipt = {"schema_version": 1, "source_fingerprint": "fixture", "projects": {}}
            installation._write_receipt(env / installation.OWNER_NAME, receipt)

            @contextmanager
            def after_other_owner_completes(path):
                self.assertEqual(path, env)
                installation._write_receipt(env / installation.RECEIPT_NAME, receipt)
                yield

            with patch.object(installation, "_manifests", return_value={}), \
                 patch.object(installation, "source_fingerprint", return_value="fixture"), \
                 patch.object(installation, "_installation_lock", after_other_owner_completes), \
                 patch.object(installation, "verify_environment", return_value={"status": "complete"}), \
                 patch.object(installation, "_run", return_value=(0, "")) as run:
                actual = installation.install_environment(repo, env)
            self.assertEqual(actual["status"], "complete")
            self.assertTrue(actual["reused"])
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
