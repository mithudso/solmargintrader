"""The shared owner route must not silently create a second session."""

import json
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import autotrade
from soltui.commands import dispatch


class Routing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.route_dir = self.home / ".config/oracle-autotrade"
        self.default = self.home / ".local/state/oracle-autotrade"
        self.route_dir.mkdir(parents=True, mode=0o700)
        self.route = self.route_dir / "connection.json"
        self.home_patch = patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def write_route(self, value):
        self.route.write_text(value)
        self.route.chmod(0o600)

    def test_explicit_environment_wins_even_over_unsafe_route(self):
        self.write_route("invalid")
        self.route.chmod(0o666)
        with patch.dict(
            os.environ, {"ORACLE_AUTOTRADE_HOME": str(self.home / "explicit")}
        ):
            self.assertEqual(autotrade._home(), self.home / "explicit")

    def test_absent_route_uses_unchanged_default(self):
        self.assertEqual(autotrade._home(), self.default)
        self.assertFalse(self.default.exists())

    def test_registry_reaches_existing_routed_owner_without_spawning(self):
        owner = self.home / "owner"
        owner.mkdir(mode=0o700)
        journal = owner / "journal.sqlite3"
        with sqlite3.connect(journal) as db:
            db.execute(
                "CREATE TABLE requests (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL, at REAL NOT NULL)"
            )
        journal.chmod(0o600)
        before = journal.read_bytes()
        self.write_route(json.dumps({"version": 1, "state_home": str(owner)}))
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(str(owner / "owner.sock"))
        listener.listen(1)
        seen = []

        def serve():
            with listener.accept()[0] as client:
                seen.append(json.loads(client.recv(4096)))
                client.sendall(
                    b'{"ok":true,"result":{"session_id":"existing","state":"stopped"}}\n'
                )

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        with (
            patch("subprocess.Popen", side_effect=AssertionError("must not spawn")),
            patch.object(autotrade, "_home", wraps=autotrade._home) as resolve,
        ):
            result = dispatch("autotrade.status", {}, surface="tui", quiet=True)
        self.assertEqual(resolve.call_count, 1)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["session_id"], "existing")
        self.assertEqual(seen[0]["action"], "status")
        self.assertEqual(journal.read_bytes(), before)
        self.assertFalse(self.default.exists())

    def test_bootstrap_pins_resolved_home_when_route_changes(self):
        first = self.home / "first"
        second = self.home / "second"
        self.write_route(json.dumps({"version": 1, "state_home": str(first)}))
        received = {}

        def spawn(*args, **kwargs):
            received.update(kwargs["env"])
            self.write_route(json.dumps({"version": 1, "state_home": str(second)}))
            raise OSError("simulated spawn failure")

        with (
            patch("subprocess.Popen", side_effect=spawn),
            self.assertRaisesRegex(RuntimeError, "owner failed to start"),
        ):
            autotrade.status()
        self.assertEqual(received["ORACLE_AUTOTRADE_HOME"], str(first))
        self.assertTrue((first / "journal.sqlite3").exists())
        self.assertFalse(second.exists())
        self.assertFalse(self.default.exists())

    def test_direct_owner_binds_home_before_route_changes(self):
        from oracle_leverage import autotrade_worker

        first = self.home / "first"
        second = self.home / "second"
        self.write_route(json.dumps({"version": 1, "state_home": str(first)}))
        real_connect = autotrade._connect

        def connect(home=None):
            self.write_route(json.dumps({"version": 1, "state_home": str(second)}))
            return real_connect(home)

        with (
            patch.object(autotrade, "_connect", side_effect=connect),
            patch.object(autotrade_worker.fcntl, "flock", side_effect=BlockingIOError),
        ):
            autotrade_worker.serve()
        self.assertTrue((first / "journal.sqlite3").exists())
        self.assertTrue((first / "owner.lock").exists())
        self.assertFalse(second.exists())
        self.assertFalse(self.default.exists())

    def test_invalid_and_unsafe_routes_refuse_before_creating_or_spawning(self):
        forbidden = self.home / "forbidden"
        path = str(forbidden)
        cases = [
            "{",
            json.dumps({"version": 1, "state_home": "relative"}),
            json.dumps({"version": True, "state_home": path}),
            json.dumps({"version": 1, "state_home": path, "extra": 1}),
            '{"version":1,"version":1,"state_home":' + json.dumps(path) + "}",
            " " * 4097,
        ]
        for value in cases:
            with self.subTest(value=value[:40]):
                self.write_route(value)
                with (
                    patch(
                        "subprocess.Popen", side_effect=AssertionError("must not spawn")
                    ),
                    self.assertRaises(ValueError),
                ):
                    autotrade.status()
                self.assertFalse(self.default.exists())
                self.assertFalse(forbidden.exists())
        self.write_route(json.dumps({"version": 1, "state_home": path}))
        self.route.chmod(0o644)
        with self.assertRaises(ValueError):
            autotrade.status()
        self.route.unlink()
        self.route.symlink_to(self.home / "missing")
        with self.assertRaises(ValueError):
            autotrade.status()
        self.assertFalse(self.default.exists())
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()
