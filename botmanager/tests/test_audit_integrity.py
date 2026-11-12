from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.health import HealthStore

from botmanager import backup
from tests import test_backup as fixtures


class AuditIntegrityTests(unittest.TestCase):
    def test_health_connection_open_failure_is_translated(self):
        with (tempfile.TemporaryDirectory() as directory,
              patch("botmanager.health.sqlite3.connect", side_effect=sqlite3.OperationalError("unavailable")),
              self.assertRaises(ManagerError), HealthStore(Path(directory)).connection(True)):
            self.fail("connection cannot open")

    def test_restore_never_executes_a_snapshot_selected_interpreter(self):
        fixture = fixtures.BackupTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        registry, _, descriptor = fixture.authority()
        expected = backup._authority_binding(descriptor, registry, verify_owner=False)
        executable = fixture.root / "untrusted"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        descriptor["interpreter"] = str(executable)
        with patch("botmanager.research_owner.OwnerClient.call") as call:
            with self.assertRaises(ManagerError):
                backup._validate_authority(descriptor, expected)
            call.assert_not_called()
