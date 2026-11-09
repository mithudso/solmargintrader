"""Access, framing, logging and install behaviour of the command bridge."""

from __future__ import annotations

import io
import json
import os
import stat
import struct
import threading
import unittest
from pathlib import Path
from unittest import mock

from soltui import api, commands, native_host, native_host_install as inst

from .bridge_support import ApiServer, TOKEN, World, host_call, via_cli


class ConfirmGateTests(unittest.TestCase):
    """liquidity.resume deletes the KILL file: it needs confirm=true on every surface."""

    def test_refused_without_confirm_and_file_survives_on_every_surface(self) -> None:
        with World() as world, ApiServer() as server:
            from soltui import liquidity as liq
            for surface in ("tui", "cli", "api", "host"):
                world.reset_state()
                liq.set_kill(True)
                for params in ({}, {"confirm": False}):
                    if surface == "tui":
                        env = commands.dispatch("liquidity.resume", params, "tui")
                    elif surface == "cli":
                        env = json.loads(via_cli("liquidity.resume", params))
                    elif surface == "api":
                        env = json.loads(server.request("POST", "/v1/liquidity.resume", params)[1])
                    else:
                        env = host_call({"id": 1, "op": "call", "command": "liquidity.resume",
                                         "params": params})[1]["response"]
                    with self.subTest(surface=surface, params=params):
                        self.assertEqual(env["error"]["code"], "forbidden")
                        self.assertTrue(liq.is_killed())

    def test_confirm_must_be_the_boolean_true(self) -> None:
        with World():
            from soltui import liquidity as liq
            liq.set_kill(True)
            env = commands.dispatch("liquidity.resume", {"confirm": "true"}, "api")
            self.assertEqual(env["error"]["code"], "bad_params")
            self.assertTrue(liq.is_killed())
            self.assertTrue(commands.dispatch("liquidity.resume", {"confirm": True}, "api")["ok"])
            self.assertFalse(liq.is_killed())

    def test_cli_flag_confirms(self) -> None:
        with World():
            from soltui import liquidity as liq
            liq.set_kill(True)
            out = io.StringIO()
            from soltui import cli
            self.assertEqual(cli.main(["call", "liquidity.resume", "-p", "confirm=true"], out=out), 0)
            self.assertFalse(liq.is_killed())

    def test_kill_needs_no_confirm(self) -> None:
        with World():
            from soltui import liquidity as liq
            self.assertTrue(commands.dispatch("liquidity.kill", {}, "cli")["ok"])
            self.assertTrue(liq.is_killed())

    def test_tui_resume_button_asks_twice(self) -> None:
        import asyncio
        from soltui.config import Settings
        from soltui.tui import SolTuiApp

        async def go():
            with World():
                from soltui import liquidity as liq
                liq.set_kill(True)
                app = SolTuiApp(Settings(poll_interval_seconds=60))
                async with app.run_test(size=(180, 55)) as pilot:
                    await pilot.pause()
                    app._liq_set_kill(False)
                    self.assertTrue(liq.is_killed(), "first press must only arm")
                    app._liq_set_kill(False)
                    self.assertFalse(liq.is_killed())
        asyncio.run(go())


class ApiAccessTests(unittest.TestCase):
    def test_binds_loopback_only(self) -> None:
        with World(), ApiServer() as server:
            self.assertEqual(server.server.server_address[0], "127.0.0.1")

    def test_health_needs_no_token_everything_else_does(self) -> None:
        with World(), ApiServer() as server:
            self.assertEqual(server.request("GET", "/v1/health", token=None)[0], 200)
            self.assertEqual(server.request("GET", "/v1/settings.get", token=None)[0], 401)
            self.assertEqual(server.request("GET", "/v1/settings.get", token="wrong")[0], 401)
            self.assertEqual(server.request("GET", "/v1/commands", token=None)[0], 401)
            self.assertEqual(server.request("GET", "/v1/settings.get")[0], 200)

    def test_browser_requests_are_refused_even_with_the_token(self) -> None:
        with World(), ApiServer() as server:
            for header in ({"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
                status, body = server.request("POST", "/v1/roster.reset", {}, headers=header)
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(body)["error"]["code"], "forbidden")
            self.assertEqual(server.request("GET", "/v1/health", headers={"Origin": "x"})[0], 200)

    def test_get_is_read_only_commands_only(self) -> None:
        with World(), ApiServer() as server:
            self.assertEqual(server.request("GET", "/v1/roster.reset")[0], 405)
            self.assertEqual(server.request("GET", "/v1/roster.list")[0], 200)

    def test_status_codes_and_body_limits(self) -> None:
        with World(), ApiServer() as server:
            self.assertEqual(server.request("POST", "/v1/nope.nothing", {})[0], 404)
            self.assertEqual(server.request("POST", "/v1/roster.add", {"name": 1})[0], 400)
            self.assertEqual(server.request("POST", "/v1/liquidity.resume", {})[0], 403)
            big = {"text": "x" * (api.MAX_BODY_BYTES + 10)}
            self.assertEqual(server.request("POST", "/v1/docs.write", big)[0], 413)

    def test_get_query_is_typed_from_the_declaration(self) -> None:
        with World(), ApiServer() as server:
            status, body = server.request("GET", "/v1/docs.list?limit=2&query=soltui")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["result"]["shown"], 2)

    def test_token_file_is_created_mode_600_and_compared_safely(self) -> None:
        with World() as world:
            token = api.load_token()
            path = api.token_path()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(api.load_token(), token)
            os.chmod(path, 0o644)
            api.load_token()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertTrue(api.token_matches(token, token))
            self.assertFalse(api.token_matches("", token))
            self.assertFalse(api.token_matches("x", " "))
            self.assertNotIn(token, world.log.read_text() if world.log.exists() else "")


class NativeFramingTests(unittest.TestCase):
    def frame(self, obj) -> bytes:
        raw = json.dumps(obj).encode()
        return struct.pack("<I", len(raw)) + raw

    def test_many_requests_per_connection_with_ids_outside_the_envelope(self) -> None:
        with World():
            stdin = io.BytesIO(self.frame({"id": "a", "op": "ping"}) + self.frame({"id": 2, "op": "list"})
                               + self.frame({"id": "c", "op": "call", "command": "roster.list"}))
            stdout = io.BytesIO()
            native_host.serve(stdin, stdout)
            stdout.seek(0)
            replies = []
            while (body := native_host.read_frame(stdout)) is not None:
                replies.append(json.loads(body))
            self.assertEqual([r["id"] for r in replies], ["a", 2, "c"])
            self.assertEqual(replies[0]["response"]["result"]["pong"], True)
            self.assertEqual(len(replies[1]["response"]["result"]), len(commands.COMMANDS))
            for r in replies:
                self.assertEqual(set(r["response"]), {"ok", "command", "result", "error"})

    def test_status_can_cancel_a_long_call_without_losing_the_shared_runtime(self) -> None:
        started = threading.Event()
        cancelled = threading.Event()

        def long_job(ctx, params):
            ctx.runtime.session_label = "retained"
            started.set()
            if not cancelled.wait(3):
                raise RuntimeError("status/cancel was blocked behind the long job")
            return {"cancelled": True}

        def cancel_job(ctx, params):
            if not started.wait(3):
                raise RuntimeError("long job never started")
            retained = ctx.runtime.session_label
            cancelled.set()
            return {"retained": retained}

        with World(), mock.patch.dict(commands.COMMANDS, {
            "test.long": commands.Command("test.long", "d", long_job, long_running=True),
            "test.cancel": commands.Command("test.cancel", "d", cancel_job),
        }):
            source = io.BytesIO(self.frame({"id": "job", "op": "call", "command": "test.long"})
                                + self.frame({"id": "cancel", "op": "call", "command": "test.cancel"}))
            output = io.BytesIO()
            native_host.serve(source, output)
            output.seek(0)
            replies = {}
            while (body := native_host.read_frame(output)) is not None:
                reply = json.loads(body)
                replies[reply["id"]] = reply["response"]
            self.assertTrue(replies["job"]["ok"], replies)
            self.assertEqual(replies["cancel"]["result"], {"retained": "retained"})
            self.assertTrue(replies["job"]["result"]["cancelled"])

    def test_bad_requests_get_envelopes(self) -> None:
        with World():
            for req, code in (({"id": 1, "op": "dance"}, "unknown_command"),
                              ({"id": 1, "op": "call"}, "bad_params"),
                              ({"id": 1, "op": "call", "command": "x.y"}, "unknown_command")):
                self.assertEqual(host_call(req)[1]["response"]["error"]["code"], code)
            reply = json.loads(native_host.handle_request(b"not json"))
            self.assertEqual(reply["response"]["error"]["code"], "bad_params")

    def test_reply_over_one_megabyte_becomes_a_failed_envelope(self) -> None:
        with World():
            huge = {"text": "x" * (native_host.MAX_REPLY_BYTES + 5)}
            cmd = commands.Command("big.thing", "d", lambda ctx, p: huge)
            with mock.patch.dict(commands.COMMANDS, {"big.thing": cmd}):
                text, reply = host_call({"id": 9, "op": "call", "command": "big.thing"})
            self.assertLess(len(text.encode()), native_host.MAX_REPLY_BYTES)
            self.assertEqual(reply["id"], 9)
            self.assertEqual(reply["response"]["error"]["code"], "failed")
            self.assertIn("CLI or API", reply["response"]["error"]["message"])

    def test_oversize_and_truncated_incoming_frames_end_the_connection_cleanly(self) -> None:
        for data in (struct.pack("<I", native_host.MAX_REQUEST_BYTES + 1),
                     struct.pack("<I", 50) + b"short", b"\x01\x00"):
            stdout = io.BytesIO()
            native_host.serve(io.BytesIO(data), stdout)
            stdout.seek(0)
            reply = json.loads(native_host.read_frame(stdout))
            self.assertEqual(reply["response"]["error"]["code"], "failed")

    def test_empty_stream_is_a_clean_exit(self) -> None:
        out = io.BytesIO()
        native_host.serve(io.BytesIO(b""), out)
        self.assertEqual(out.getvalue(), b"")

    def test_build_hash_tracks_manifest_and_src(self) -> None:
        with World() as world:
            ext = world.root / "ext"
            (ext / "src" / "core").mkdir(parents=True)
            (ext / "manifest.json").write_text("{}")
            (ext / "src" / "core" / "a.js").write_text("a")
            with mock.patch.dict(os.environ, {"SOLTUI_EXTENSION_DIR": str(ext)}):
                first = host_call({"id": 1, "op": "buildHash"})[1]["response"]
                again = host_call({"id": 1, "op": "buildHash"})[1]["response"]
                self.assertEqual(first, again)
                self.assertEqual(first["result"]["files"], 2)
                self.assertEqual(first["result"]["root"], str(ext.resolve()))
                self.assertEqual(len(first["result"]["hash"]), 64)
                (ext / "src" / "core" / "a.js").write_text("b")
                changed = host_call({"id": 1, "op": "buildHash"})[1]["response"]
                self.assertNotEqual(changed["result"]["hash"], first["result"]["hash"])
                (ext / "src" / "new.js").write_text("c")
                self.assertEqual(host_call({"id": 1, "op": "buildHash"})[1]["response"]["result"]["files"], 3)
                (ext / "manifest.json").unlink()
                gone = host_call({"id": 1, "op": "buildHash"})[1]["response"]
                self.assertEqual(gone["error"]["code"], "failed")


class LoggingTests(unittest.TestCase):
    def test_only_parameter_keys_are_logged_never_values(self) -> None:
        with World() as world:
            secret = "VALUE-THAT-MUST-NOT-APPEAR-123"
            commands.dispatch("docs.read", {"path": secret}, "cli")
            commands.dispatch("roster.add", {"name": secret, "params": {"k": secret}}, "api")
            commands.dispatch("settings.save", {"asset": secret}, "native")
            raw = world.log.read_text()
            self.assertNotIn(secret, raw)
            lines = world.log_lines()
            self.assertEqual([l["params_keys"] for l in lines], [["path"], ["name", "params"], ["asset"]])
            self.assertEqual(set(lines[0]), {"ts", "surface", "command", "ok", "error_code", "ms",
                                             "params_keys"})
            self.assertEqual([l["surface"] for l in lines], ["cli", "api", "native"])
            self.assertEqual(lines[0]["error_code"], "failed")

    def test_every_surface_logs_through_dispatch_exactly_once(self) -> None:
        with World() as world, ApiServer() as server:
            commands.dispatch("settings.get", {}, "tui")
            via_cli("settings.get", {})
            server.request("POST", "/v1/settings.get", {})
            host_call({"id": 1, "op": "call", "command": "settings.get"})
            self.assertEqual([l["surface"] for l in world.log_lines()], ["tui", "cli", "api", "native"])

    def test_host_level_ops_and_quiet_polls_are_not_logged(self) -> None:
        with World() as world:
            host_call({"id": 1, "op": "ping"})
            host_call({"id": 1, "op": "buildHash"})
            commands.dispatch("liquidity.status", {}, "tui", quiet=True)
            self.assertEqual(world.log_lines(), [])

    def test_unknown_command_and_bad_params_are_logged_with_codes(self) -> None:
        with World() as world:
            commands.dispatch("nope.x", {}, "api")
            commands.dispatch("roster.add", {"name": 1}, "api")
            self.assertEqual([l["error_code"] for l in world.log_lines()], ["unknown_command", "bad_params"])

    def test_log_rotates_at_five_megabytes(self) -> None:
        with World() as world:
            world.log.parent.mkdir(parents=True)
            world.log.write_text("x" * (commands.LOG_ROTATE_BYTES + 1))
            commands.dispatch("settings.get", {}, "cli")
            self.assertTrue(world.log.with_name("calls.jsonl.1").exists())
            self.assertEqual(len(world.log_lines()), 1)

    def test_unwritable_log_never_fails_the_call(self) -> None:
        with World() as world:
            world.log.parent.mkdir(parents=True)
            world.log.parent.chmod(0o500)
            try:
                self.assertTrue(commands.dispatch("settings.get", {}, "cli")["ok"])
            finally:
                world.log.parent.chmod(0o700)


class ValidationTests(unittest.TestCase):
    def test_unknown_missing_and_mistyped_params_are_bad_params(self) -> None:
        with World():
            for name, params in (("settings.get", {"x": 1}), ("roster.add", {}),
                                 ("roster.add", {"name": True}), ("paper.step", {"bars": "3"}),
                                 ("paper.step", {"bars": True}), ("settings.save", {"capital": "5"}),
                                 ("roster.list", [1])):
                with self.subTest(name=name, params=params):
                    self.assertEqual(commands.dispatch(name, params, "api")["error"]["code"], "bad_params")

    def test_cli_types_values_from_the_declaration(self) -> None:
        with World():
            from soltui.cli import params_from_args
            self.assertEqual(params_from_args("paper.step", ["bars=5"], None), {"bars": 5})
            self.assertEqual(params_from_args("top5.add_to_roster", ['ranks=[1,2]'], None), {"ranks": [1, 2]})
            self.assertEqual(params_from_args("roster.add", ["name=rsi"], '{"params":{"period":9}}'),
                             {"params": {"period": 9}, "name": "rsi"})
            with self.assertRaises(commands.CommandError):
                params_from_args("paper.step", ["bars=abc"], None)
            with self.assertRaises(commands.CommandError):
                params_from_args("paper.step", ["bars"], None)

    def test_handler_exceptions_become_failed_envelopes(self) -> None:
        with World():
            boom = commands.Command("t.boom", "d", lambda ctx, p: 1 / 0)
            with mock.patch.dict(commands.COMMANDS, {"t.boom": boom}):
                env = commands.dispatch("t.boom", {}, "cli")
            self.assertEqual(env["error"]["code"], "failed")
            self.assertIn("ZeroDivisionError", env["error"]["message"])

    def test_non_finite_numbers_serialise_as_null(self) -> None:
        self.assertIsNone(commands.jsonable(float("nan")))
        self.assertEqual(commands.dumps({"a": commands.jsonable(float("inf"))}), '{"a":null}')


class InstallerTests(unittest.TestCase):
    def test_install_status_uninstall_roundtrip(self) -> None:
        with World() as world:
            dirs = [world.root / "A" / "NativeMessagingHosts", world.root / "B" / "NativeMessagingHosts"]
            wrapper = world.root / "native-host" / "soltui-native-host"
            with mock.patch.dict(os.environ, {"SOLTUI_EXTRA_EXTENSION_IDS": "extraidone, extraidtwo"}):
                result = inst.install(Path("/repo/x"), Path("/venv/bin/python"), ["cli-id"], dirs, wrapper)
            self.assertEqual(len(result["manifests"]), 2)
            self.assertTrue(os.access(wrapper, os.X_OK))
            text = wrapper.read_text()
            self.assertIn('exec "/venv/bin/python" -m soltui.native_host', text)
            self.assertIn('cd "/repo/x"', text)
            manifest = json.loads((dirs[0] / "com.mitchhudson.soltui.json").read_text())
            self.assertEqual(manifest["name"], "com.mitchhudson.soltui")
            self.assertEqual(manifest["type"], "stdio")
            self.assertEqual(manifest["path"], str(wrapper))
            self.assertTrue(Path(manifest["path"]).is_absolute())
            self.assertEqual(manifest["allowed_origins"], [
                "chrome-extension://pnokcppamfghgaimmmghoegjllhonhbh/",
                "chrome-extension://extraidone/", "chrome-extension://extraidtwo/",
                "chrome-extension://cli-id/"])
            state = inst.status(dirs, wrapper)
            self.assertTrue(all(m["exists"] and m["points_at_wrapper"] for m in state["manifests"]))
            removed = inst.uninstall(dirs, wrapper)
            self.assertEqual(len(removed["removed"]), 3)
            self.assertFalse(wrapper.exists())
            self.assertFalse(any(m["exists"] for m in inst.status(dirs, wrapper)["manifests"]))

    def test_only_installed_browsers_get_a_manifest(self) -> None:
        with World() as world:
            (world.root / "Google" / "Chrome").mkdir(parents=True)
            (world.root / "BraveSoftware" / "Brave-Browser").mkdir(parents=True)
            found = inst.browser_host_dirs(world.root)
            self.assertEqual([p.parent.name for p in found], ["Chrome", "Brave-Browser"])

    def test_wrapper_runs_the_host_end_to_end(self) -> None:
        import subprocess
        import sys
        with World() as world:
            wrapper = world.root / "w" / "h"
            inst.install(Path(__file__).resolve().parents[2], Path(sys.executable), [], [world.root / "N"], wrapper)
            payload = json.dumps({"id": "z", "op": "ping"}).encode()
            proc = subprocess.run([str(wrapper)], input=struct.pack("<I", len(payload)) + payload,
                                  capture_output=True, timeout=60, env={**os.environ})
            (length,) = struct.unpack("<I", proc.stdout[:4])
            reply = json.loads(proc.stdout[4:4 + length])
            self.assertEqual(reply["id"], "z")
            self.assertTrue(reply["response"]["ok"])


if __name__ == "__main__":
    unittest.main()
