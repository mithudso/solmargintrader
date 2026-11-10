"""Collectors must measure observed owners without creating runtime state."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.suite import _directory, _write, save_config
from botmanager.worker import lifetime_lock

from botmanager import machine_health as health


class MachineHealthTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home, self.ecosystem = self.root / "manager", self.root / "ecosystem"

    def test_absent_check_is_inert_and_does_not_make_missing_values_zero(self):
        value = health.check(self.home, self.ecosystem)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.ecosystem.exists())
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(value["overall"], "down")
        self.assertFalse(value["ready"])
        self.assertIsNone(value["components"]["market_data"]["ready"])
        self.assertNotIn("freshness_age_seconds", value["components"]["market_data"])
        self.assertNotIn("solbot_component_age_seconds{", health.prometheus(value))

    def test_homes_preserves_explicit_environment_and_saved_bindings(self):
        save_config(self.home, self.ecosystem)
        alternate = self.root / "alternate"
        with patch.dict(os.environ, {"SOLBOT_HOME": str(self.home)}, clear=True):
            self.assertEqual(health.homes(), (self.home, self.ecosystem))
            with patch.dict(os.environ, {"SOLBOT_ECOSYSTEM_HOME": str(alternate)}):
                self.assertEqual(health.homes(), (self.home, alternate))
                self.assertEqual(
                    health.homes(ecosystem_home=self.ecosystem),
                    (self.home, self.ecosystem),
                )
        self.assertEqual(
            health.private_read(self.home / ".suite/config.json")["ecosystem_home"],
            str(self.ecosystem),
        )

    def test_private_records_refuse_permissions_symlinks_oversize_and_invalid_type(
        self,
    ):
        directory = _directory(self.home)
        path = directory / "config.json"
        _write(
            path,
            {
                "schema_version": 1,
                "manager_home": str(self.home),
                "ecosystem_home": str(self.ecosystem),
            },
        )
        path.chmod(0o644)
        with self.assertRaises(ManagerError):
            health.homes(self.home)
        path.chmod(0o600)
        path.unlink()
        path.symlink_to(self.root / "missing")
        with self.assertRaises(OSError):
            health.private_read(path)
        path.unlink()
        path.write_bytes(b"x" * 100)
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            health.private_read(path, limit=50)
        path.write_text("[]")
        with self.assertRaises(TypeError):
            health.private_read(path)

    def test_private_fifo_is_refused_without_waiting_for_a_writer(self):
        fifo = self.root / "control-server.json"
        os.mkfifo(fifo, 0o600)
        readers = (
            ("botmanager.machine_health", "private_read", fifo),
            ("botmanager.suite_service", "_read_definition", fifo),
            ("ecosystem.ui_service", "_read", self.root),
        )
        for module, name, path in readers:
            with self.subTest(reader=module + "." + name):
                code = (
                    "import sys; from pathlib import Path; "
                    "from botmanager.domain import ManagerError; "
                    f"from {module} import {name} as read_record\n"
                    "try: read_record(Path(sys.argv[1]))\n"
                    "except (ValueError, ManagerError): raise SystemExit(0)\n"
                    "raise SystemExit(1)\n"
                )
                result = subprocess.run(
                    [sys.executable, "-c", code, str(path)],
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_fifo_startup_logs_are_refused_without_spawning_children(self):
        programs = {
            "ui": (
                "from ecosystem.ui_service import ensure\n"
                "value = ensure(home)\n"
                "assert not value['running']\n"
                "assert value['reason'] == 'control_server_start_failed'\n"
            ),
            "suite": (
                "from botmanager.suite import _start\n"
                "with patch('botmanager.service.installed_executable', return_value=Path(sys.executable)), "
                "patch('botmanager.suite_service.operation', return_value={'installed': False}):\n"
                " try: _start(home, home / 'ecosystem')\n"
                " except ManagerError as exc:\n"
                "  assert exc.code == 'suite_unavailable'\n"
                "  raise SystemExit(0)\n"
                " raise AssertionError('FIFO log was accepted')\n"
            ),
        }
        for owner, program in programs.items():
            for with_reader in (False, True):
                with self.subTest(owner=owner, with_reader=with_reader):
                    home = self.root / f"{owner}-{with_reader}"
                    directory = home if owner == "ui" else home / ".suite"
                    directory.mkdir(mode=0o700, parents=True)
                    fifo = directory / (
                        "control-room.log" if owner == "ui" else "suite.stderr.log"
                    )
                    os.mkfifo(fifo, 0o600)
                    reader = (
                        os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
                        if with_reader
                        else None
                    )
                    code = (
                        "import sys; from pathlib import Path; from unittest.mock import patch; "
                        "from botmanager.domain import ManagerError\n"
                        "home=Path(sys.argv[1])\n"
                        "with patch('subprocess.Popen', side_effect=AssertionError('unexpected child')):\n"
                        + "\n".join(" " + line for line in program.splitlines())
                        + "\n"
                    )
                    try:
                        result = subprocess.run(
                            [sys.executable, "-c", code, str(home)],
                            capture_output=True,
                            timeout=2,
                            check=False,
                        )
                    finally:
                        if reader is not None:
                            os.close(reader)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())

    def archive(self, observed):
        path = self.ecosystem / "oracle/SOL/history.sqlite3"
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA application_id=1330791244")
            db.execute("CREATE TABLE observations (observed REAL)")
            db.execute("CREATE INDEX observation_time ON observations(observed)")
            if observed is not None:
                db.execute("INSERT INTO observations VALUES (?)", (observed,))
        return path

    def test_reference_freshness_is_separate_from_server_readiness(self):
        now = time.time()
        archive = self.archive(now - 400)
        before = archive.read_bytes()
        good = health.component("up", "available", ready=True)
        value = health.snapshot(
            self.home,
            self.ecosystem,
            now=now,
            owned_manager=good,
            owned_suite=good,
            ui=(good, "http://127.0.0.1:12345"),
        )
        self.assertTrue(value["ready"])
        self.assertEqual(value["overall"], "degraded")
        row = value["components"]["market_data"]
        self.assertEqual(row["freshness_age_seconds"], 400)
        self.assertFalse(row["certified"])
        self.assertEqual(archive.read_bytes(), before)
        self.assertFalse(Path(str(archive) + "-journal").exists())
        self.assertIn(
            'component="market_data",kind="freshness_age_seconds"} 400',
            health.prometheus(value),
        )

    def test_reference_future_or_missing_clock_is_unknown_not_fresh(self):
        now = time.time()
        path = self.archive(now + 100)
        self.assertEqual(health.market_probe(self.ecosystem, now)["state"], "unknown")
        with sqlite3.connect(path) as db:
            db.execute("DELETE FROM observations")
        self.assertEqual(
            health.market_probe(self.ecosystem, now)["reason"],
            "reference_observations_absent",
        )

    def test_manager_owner_without_responsive_control_socket_is_not_green(self):
        with lifetime_lock(self.home / "supervisor.lock"):
            value = health.manager_probe(self.home)
        self.assertEqual(value["state"], "degraded")
        self.assertFalse(value["ready"])

    def test_prometheus_uses_fixed_labels_and_omits_unknown_clocks(self):
        value = {
            "ready": False,
            "components": {
                "market_data": {
                    "state": "secret\nlabel",
                    "reason": "private-secret",
                    "ready": None,
                    "freshness_age_seconds": float("nan"),
                }
            },
        }
        output = health.prometheus(value)
        self.assertNotIn("secret", output)
        self.assertNotIn(" nan", output)
        self.assertNotIn("solbot_component_age_seconds{", output)
        self.assertIn('component="market_data",state="unknown"} 1', output)

    def test_bad_suite_checkpoint_is_unknown_even_when_a_lock_is_held(self):
        _directory(self.home)
        with lifetime_lock(self.home / ".suite/owner.lock"):
            path = self.home / ".suite/state.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "manager_home": str(self.home),
                        "instance": "a" * 32,
                        "heartbeat": float("nan"),
                    }
                )
            )
            path.chmod(0o600)
            self.assertEqual(
                health.suite_probe(self.home, time.time())["state"], "unknown"
            )
        self.assertEqual(
            json.loads((self.home / ".suite/state.json").read_text())["schema_version"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
