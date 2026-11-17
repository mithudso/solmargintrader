"""Actual bounded subprocess fixtures; no fixture contacts a trading venue."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import cli, sdkbridge


def base58_public_key(raw):
    number = int.from_bytes(raw, "big")
    result = ""
    while number:
        number, remainder = divmod(number, 58)
        result = cli.BASE58_ALPHABET[remainder] + result
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + result


def transaction_fixture(*, versioned=False, signed=False, owner=None, data=b"\x01\x02"):
    """Structural bytes only; these fixture signatures are not cryptographic."""

    def shortvec(value):
        result = bytearray()
        while value >= 128:
            result.append((value & 127) | 128)
            value >>= 7
        result.append(value)
        return bytes(result)

    owner = owner if owner is not None else bytes(range(1, 33))
    accounts = owner + bytes(range(33, 65)) + bytes(range(65, 97))
    message = (
        (b"\x80" if versioned else b"")
        + b"\x02\x01\x01\x03"
        + accounts
        + b"\x09" * 32
        + b"\x01\x02\x02\x00\x01"
        + shortvec(len(data))
        + data
        + (b"\x00" if versioned else b"")
    )
    raw = b"\x02" + (b"\x07" if signed else b"\0") * 64 + b"\x03" * 64 + message
    return base64.b64encode(raw).decode("ascii")


class ProcessFixtures(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        patcher = patch.dict(os.environ, {"HOME": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / ".local/state/oracle-leverage").mkdir(parents=True, mode=0o700)

    def argv(self, source, *args):
        return [sys.executable, "-I", "-S", "-c", source, *map(str, args)]

    def assert_gone(self, pid):
        deadline = time.monotonic() + 2
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            self.assertLess(
                time.monotonic(), deadline, f"fixture process {pid} survived"
            )
            time.sleep(0.01)

    def test_json_stdin_and_literal_argv_are_not_shell_interpreted(self):
        value = cli.run_json(
            self.argv(
                "import json,sys; print(json.dumps({'data':json.load(sys.stdin),'args':sys.argv[1:]}))",
                "$(touch should-never-exist); BTC",
            ),
            timeout=2,
            payload=b'{"action":"build-open","asset":"BTC"}',
        )
        self.assertEqual(value["data"]["asset"], "BTC")
        self.assertEqual(value["args"], ["$(touch should-never-exist); BTC"])

    def test_nonzero_exit_keeps_safe_stderr_evidence(self):
        message = "fake-private-key=NEVER-LEAK-THIS"
        with self.assertRaises(cli.AdapterError) as caught:
            cli.run_json(
                self.argv(
                    "import sys; sys.stderr.write(sys.argv[1]); sys.exit(7)", message
                ),
                timeout=2,
                ambiguous=True,
            )
        error = caught.exception
        self.assertEqual(error.code, "process_nonzero_exit")
        self.assertEqual(error.returncode, 7)
        self.assertTrue(error.ambiguous)
        self.assertEqual(error.stderr_bytes, len(message))
        self.assertEqual(
            error.stderr_sha256, hashlib.sha256(message.encode()).hexdigest()
        )
        self.assertNotIn(message, str(error))
        self.assertNotIn(message, repr(error))

    def test_sdk_nonzero_known_error_is_safe_and_private_receipt_is_redacted(self):
        argv = [
            "/opt/homebrew/bin/node",
            str(Path(cli.__file__).resolve().parent / "sdk/bridge.mjs"),
        ]
        stdout = b'{"status":"error","message":"service_keeper_mismatch"}'
        stderr = (
            b"authorization=private-token https://rpc.invalid/?api_key=secret-value"
        )
        with (
            patch.object(cli, "_bounded_process", return_value=(1, stdout, stderr)),
            self.assertRaises(cli.AdapterError) as caught,
        ):
            cli.run_json(argv, timeout=2, payload=b'{"action":"service-build-open"}')
        self.assertEqual(caught.exception.code, "service_keeper_mismatch")
        receipt = (
            self.root / ".local/state/oracle-leverage/diagnostics/process-errors.jsonl"
        )
        text = receipt.read_text()
        self.assertNotIn("private-token", text)
        self.assertNotIn("secret-value", text)
        entry = json.loads(text)
        self.assertEqual(entry["action"], "service-build-open")
        self.assertEqual(entry["stdout"]["structured_code"], "service_keeper_mismatch")
        self.assertEqual(entry["stderr"]["sha256"], hashlib.sha256(stderr).hexdigest())
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

    def test_unrecognized_sdk_error_does_not_expose_untrusted_output(self):
        argv = [
            "/opt/homebrew/bin/node",
            str(Path(cli.__file__).resolve().parent / "sdk/bridge.mjs"),
        ]
        with (
            patch.object(
                cli,
                "_bounded_process",
                return_value=(
                    1,
                    b'{"status":"error","message":"secret_token_leak"}',
                    b"",
                ),
            ),
            self.assertRaises(cli.AdapterError) as caught,
        ):
            cli.run_json(argv, timeout=2)
        self.assertEqual(caught.exception.code, "process_nonzero_exit")
        self.assertNotIn("secret_token_leak", str(caught.exception))

    def test_stdout_and_stderr_limits_reap_the_child(self):
        for output in (1, 2):
            with self.subTest(output=output):
                marker = self.root / f"pid-{output}"
                source = "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); os.write(int(sys.argv[2]),b'x'*10000); time.sleep(10)"
                with self.assertRaises(cli.AdapterError) as caught:
                    cli._bounded_process(
                        self.argv(source, marker, output),
                        timeout=2,
                        stdout_limit=128,
                        stderr_limit=128,
                    )
                self.assertEqual(caught.exception.code, "process_output_limit")
                self.assert_gone(int(marker.read_text()))

    def test_timeout_is_ambiguous_and_direct_child_is_reaped(self):
        marker = self.root / "timeout-pid"
        source = "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); time.sleep(10)"
        started = time.monotonic()
        with self.assertRaises(cli.AdapterError) as caught:
            cli.run_json(self.argv(source, marker), timeout=0.1, ambiguous=True)
        self.assertEqual(caught.exception.code, "process_timeout")
        self.assertTrue(caught.exception.ambiguous)
        self.assertLess(time.monotonic() - started, 2)
        self.assert_gone(int(marker.read_text()))

    def test_eof_on_both_pipes_does_not_hide_a_running_child(self):
        marker = self.root / "closed-pipes-pid"
        source = "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); os.close(1); os.close(2); time.sleep(10)"
        with self.assertRaises(cli.AdapterError) as caught:
            cli.run_json(self.argv(source, marker), timeout=0.1)
        self.assertEqual(caught.exception.code, "process_timeout")
        self.assert_gone(int(marker.read_text()))

    def test_timeout_kills_descendant_holding_the_pipes(self):
        marker = self.root / "descendants"
        source = "import os,sys,time,subprocess,json; child=subprocess.Popen([sys.executable,'-I','-S','-c','import time; time.sleep(10)']); open(sys.argv[1],'w').write(json.dumps([os.getpid(),child.pid])); time.sleep(10)"
        with self.assertRaises(cli.AdapterError) as caught:
            cli.run_json(self.argv(source, marker), timeout=0.2)
        self.assertEqual(caught.exception.code, "process_timeout")
        for pid in json.loads(marker.read_text()):
            self.assert_gone(pid)

    def test_successful_parent_cannot_leave_a_silent_descendant(self):
        marker = self.root / "silent-descendant"
        source = "import os,sys,subprocess,json; child=subprocess.Popen([sys.executable,'-I','-S','-c','import time; time.sleep(10)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); open(sys.argv[1],'w').write(json.dumps([os.getpid(),child.pid])); print('{}')"
        self.assertEqual(cli.run_json(self.argv(source, marker), timeout=2), {})
        for pid in json.loads(marker.read_text()):
            self.assert_gone(pid)

    def test_strict_json_rejects_nonfinite_duplicate_trailing_and_scalar(self):
        for value in ('{"x":NaN}', '{"x":1e999}', '{"x":1,"x":2}', "{} trailing", "42"):
            with (
                self.subTest(value=value),
                self.assertRaises(cli.AdapterError) as caught,
            ):
                cli.run_json(
                    self.argv("import sys; sys.stdout.write(sys.argv[1])", value),
                    timeout=2,
                )
            self.assertEqual(caught.exception.code, "invalid_process_json")
        with self.assertRaises(cli.AdapterError) as caught:
            cli.run_json(self.argv("import os; os.write(1,b'\\xff')"), timeout=2)
        self.assertEqual(caught.exception.code, "invalid_process_json")

    def test_secret_named_response_fields_are_redacted(self):
        value = cli.run_json(
            self.argv(
                'print(\'{"ok":true,"privateKey":"fake-secret","nested":{"api_key":"fake-key"}}\')'
            ),
            timeout=2,
        )
        self.assertEqual(value["privateKey"], "[REDACTED]")
        self.assertEqual(value["nested"]["api_key"], "[REDACTED]")

    def test_input_size_and_timeout_validation_precede_spawn(self):
        with patch.object(cli.subprocess, "Popen") as process:
            for timeout in (0, -1, True, float("nan"), float("inf"), 61):
                with self.assertRaises(cli.AdapterError):
                    cli.run_json(self.argv("print('{}')"), timeout=timeout)
            with self.assertRaises(cli.AdapterError):
                cli.run_json(
                    self.argv("print('{}')"),
                    timeout=1,
                    payload=b"x" * (cli.MAX_INPUT + 1),
                )
            process.assert_not_called()

    def test_untrusted_node_environment_is_not_inherited(self):
        with patch.dict(
            os.environ,
            {
                "NODE_OPTIONS": "--require /private/unknown.js",
                "PYTHONPATH": "/private/unknown",
            },
        ):
            value = cli.run_json(
                self.argv(
                    "import os,json; print(json.dumps({'node':os.getenv('NODE_OPTIONS'),'python':os.getenv('PYTHONPATH'),'path':os.getenv('PATH')}))"
                ),
                timeout=2,
            )
        self.assertIsNone(value["node"])
        self.assertIsNone(value["python"])
        self.assertEqual(value["path"], cli.SAFE_PATH)

    def test_no_signal_is_sent_after_reaping(self):
        events = []
        real_wait = cli.subprocess.Popen.wait
        real_killpg = cli.os.killpg

        def wait(process, *args, **kwargs):
            result = real_wait(process, *args, **kwargs)
            events.append(("reaped", process.pid))
            return result

        def killpg(pid, sig):
            if sig:
                self.assertNotIn(("reaped", pid), events)
            events.append(("signal" if sig else "probe", pid))
            return real_killpg(pid, sig)

        with (
            patch.object(cli.subprocess.Popen, "wait", wait),
            patch.object(cli.os, "killpg", killpg),
        ):
            self.assertEqual(cli.run_json(self.argv("print('{}')"), timeout=2), {})

    def test_macos_zombie_group_eperm_reaps_then_only_probes(self):
        real_killpg = cli.os.killpg
        signals = []

        def zombie_eperm(pid, sig):
            signals.append(sig)
            if sig:
                raise PermissionError("fixture zombie group")
            return real_killpg(pid, sig)

        with patch.object(cli.os, "killpg", zombie_eperm):
            self.assertEqual(cli.run_json(self.argv("print('{}')"), timeout=2), {})
        self.assertEqual(signals, [cli.signal.SIGKILL, 0])


class JupiterProtocol(unittest.TestCase):
    def test_known_structured_insufficient_funds_maps_to_a_fixed_safe_code(self):
        message = "Insufficient funds to execute the request. Please check your SOL or token balance."
        with (
            patch.object(
                cli,
                "_bounded_process",
                return_value=(
                    1,
                    json.dumps({"error": message}).encode(),
                    b"private stderr fake-secret",
                ),
            ),
            self.assertRaises(cli.AdapterError) as caught,
        ):
            cli.JupiterCLI().preview("BTC", "short", 10)
        self.assertEqual(caught.exception.code, "jupiter_insufficient_funds")
        self.assertEqual(caught.exception.returncode, 1)
        self.assertFalse(caught.exception.ambiguous)
        self.assertNotIn("fake-secret", repr(caught.exception))

    def test_unknown_structured_errors_and_stderr_remain_private(self):
        known = "Insufficient funds to execute the request. Please check your SOL or token balance."
        responses = [
            json.dumps({"error": "malicious fake-private-key=do-not-leak"}).encode(),
            json.dumps({"error": known + " fake-private-key=do-not-leak"}).encode(),
            json.dumps({"error": known, "privateKey": "do-not-leak"}).encode(),
            b'{"error":"ignored","error":"do-not-leak"}',
            b"not JSON do-not-leak",
        ]
        for stdout in responses:
            with (
                self.subTest(stdout=stdout[:40]),
                patch.object(
                    cli,
                    "_bounded_process",
                    return_value=(1, stdout, known.encode() + b" do-not-leak"),
                ),
            ):
                with self.assertRaises(cli.AdapterError) as caught:
                    cli.JupiterCLI().preview("BTC", "short", 10)
                self.assertEqual(caught.exception.code, "process_nonzero_exit")
                self.assertNotIn("do-not-leak", repr(caught.exception))
                self.assertNotIn(known, str(caught.exception))

    def test_frozen_named_key_is_passed_without_switching_global_active_key(self):
        adapter = cli.JupiterCLI()
        with (
            patch.object(adapter, "identity", return_value={}),
            patch.object(cli, "run_json", return_value={}) as process,
        ):
            adapter.preview("BTC", "long", 10, key_name="frozen-owner")
            self.assertEqual(
                process.call_args.args[0][-3:], ["--key", "frozen-owner", "--dry-run"]
            )
            adapter.execute("BTC", "long", 10, key_name="frozen-owner")
            self.assertEqual(process.call_args.args[0][-2:], ["--key", "frozen-owner"])
            adapter.positions(key_name="frozen-owner")
            self.assertEqual(process.call_args.args[0][-2:], ["--key", "frozen-owner"])
            adapter.close("11111111111111111111111111111111", key_name="frozen-owner")
            self.assertEqual(process.call_args.args[0][-2:], ["--key", "frozen-owner"])
            self.assertFalse(
                any("use" in call.args[0] for call in process.call_args_list)
            )
            before = process.call_count
            for name in ("--help", "../owner", "owner\nsecret", ""):
                with self.assertRaises(cli.AdapterError):
                    adapter.execute("BTC", "long", 10, key_name=name)
            self.assertEqual(process.call_count, before)

    def test_wallet_returns_public_active_metadata_only(self):
        public = "11111111111111111111111111111111"
        rows = [
            {"name": "unused", "address": public, "type": "keypair", "active": False},
            {
                "name": "owner",
                "address": public,
                "type": "keypair",
                "active": True,
                "privateKey": "fake-secret",
            },
        ]
        with patch.object(cli, "run_json", return_value=rows) as process:
            self.assertEqual(
                cli.JupiterCLI().wallet(),
                {"address": public, "name": "owner", "type": "keypair", "active": True},
            )
            self.assertEqual(
                process.call_args.args[0],
                ["/opt/homebrew/bin/jup", "-f", "json", "keys", "list"],
            )

    def test_wallet_refuses_missing_ambiguous_or_invalid_active_identity(self):
        public = "11111111111111111111111111111111"
        row = {"name": "owner", "address": public, "type": "keypair", "active": True}
        for result in (
            [],
            [row, row],
            {"keys": [row]},
            [{**row, "active": "yes"}],
            [{**row, "address": "not-a-wallet"}],
        ):
            with (
                self.subTest(result=result),
                patch.object(cli, "run_json", return_value=result),
                self.assertRaises(cli.AdapterError),
            ):
                cli.JupiterCLI().wallet()

    def test_exact_named_wallet_does_not_depend_on_the_active_key(self):
        public = base58_public_key(bytes(range(1, 33)))
        rows = [
            {"name": "owner", "address": public, "type": "keypair", "active": False},
            {"name": "other", "address": public, "type": "keypair", "active": True},
        ]
        with patch.object(cli, "run_json", return_value=rows):
            self.assertEqual(cli.JupiterCLI().wallet(key_name="owner")["name"], "owner")
            self.assertFalse(cli.JupiterCLI().wallet(key_name="owner")["active"])
        for metadata in ([], [rows[0], rows[0]]):
            with (
                self.subTest(metadata=metadata),
                patch.object(cli, "run_json", return_value=metadata),
                self.assertRaisesRegex(cli.AdapterError, "exactly_one_named_wallet"),
            ):
                cli.JupiterCLI().wallet(key_name="owner")

    def test_actual_loopback_cli_argv_and_dryrun_boundary(self):
        real_runner = cli.run_json

        def fixture(argv, **kwargs):
            return real_runner(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-c",
                    "import sys,json; print(json.dumps({'argv':sys.argv[1:]}))",
                    *argv[1:],
                ],
                **kwargs,
            )

        adapter = cli.JupiterCLI()
        with (
            patch.object(cli, "run_json", fixture),
            patch.object(adapter, "identity", return_value={}) as identity,
        ):
            preview = adapter.preview("BTC", "short", Decimal("10.1250000"))
            expected = [
                "-f",
                "json",
                "perps",
                "open",
                "--asset",
                "BTC",
                "--side",
                "short",
                "--amount",
                "10.125",
                "--input",
                "USDC",
                "--leverage",
                "10",
            ]
            self.assertEqual(preview["argv"], [*expected, "--dry-run"])
            identity.assert_not_called()
            self.assertEqual(
                adapter.execute("BTC", "short", Decimal("10.125"))["argv"], expected
            )
            identity.assert_called_once()
            self.assertEqual(
                adapter.positions()["argv"], ["-f", "json", "perps", "positions"]
            )
            position = "11111111111111111111111111111111"
            self.assertEqual(
                adapter.close(position)["argv"],
                ["-f", "json", "perps", "close", "--position", position],
            )

    def test_unsupported_asset_invalid_amount_and_mass_close_are_refused(self):
        adapter = cli.JupiterCLI()
        with (
            patch.object(cli, "run_json") as process,
            patch.object(adapter, "identity") as identity,
        ):
            with self.assertRaisesRegex(cli.AdapterError, "BTC_SOL_ETH_only"):
                adapter.preview("ZEC", "short", 10)
            for amount in (
                True,
                None,
                "NaN",
                "Infinity",
                "9.99",
                "10.0000001",
                "1e1000000",
            ):
                with self.subTest(amount=amount), self.assertRaises(cli.AdapterError):
                    adapter.execute("BTC", "short", amount)
            for position in (
                "all",
                "--help",
                "111111111111111111111111111111111",
                "0" * 32,
            ):
                with self.assertRaises(cli.AdapterError):
                    adapter.close(position)
            process.assert_not_called()
            identity.assert_not_called()
        with self.assertRaises(cli.AdapterError):
            cli.JupiterCLI(binary="/tmp/fake-jup")

    def test_identity_refusal_prevents_money_command(self):
        adapter = cli.JupiterCLI()
        with (
            patch.object(
                adapter,
                "identity",
                side_effect=cli.AdapterError("jupiter_cli_hash_mismatch"),
            ),
            patch.object(cli, "run_json") as process,
        ):
            with self.assertRaisesRegex(cli.AdapterError, "hash_mismatch") as caught:
                adapter.execute("BTC", "long", 10)
            self.assertFalse(caught.exception.ambiguous)
            process.assert_not_called()

    def test_identity_checks_hash_and_runtime_version(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory).resolve() / "jup"
            executable.write_bytes(b"fixture entrypoint")
            sha = hashlib.sha256(executable.read_bytes()).hexdigest()
            with (
                patch.object(cli, "APPROVED_BINARY", executable),
                patch.object(cli, "APPROVED_ENTRYPOINT", executable),
                patch.object(cli, "CLI_SHA256", sha),
                patch.object(
                    cli, "_bounded_process", return_value=(0, b"0.10.1\n", b"")
                ),
            ):
                adapter = cli.JupiterCLI(binary=executable)
                self.assertEqual(adapter.identity()["version"], "0.10.1")
                executable.write_bytes(b"changed")
                with self.assertRaisesRegex(cli.AdapterError, "hash_mismatch"):
                    adapter.identity()


class JupiterSigningProtocol(unittest.TestCase):
    def setUp(self):
        self.adapter = cli.JupiterCLI(timeout=2)
        self.owner = base58_public_key(bytes(range(1, 33)))
        self.rows = [
            {
                "name": "frozen-owner",
                "address": self.owner,
                "type": "keypair",
                "active": False,
            }
        ]

    def sign_response(self, response, *, unsigned=None, rows=None):
        unsigned = unsigned if unsigned is not None else transaction_fixture()
        with (
            patch.object(self.adapter, "identity", return_value={}),
            patch.object(
                cli,
                "run_json",
                side_effect=[self.rows if rows is None else rows, response],
            ),
        ):
            return self.adapter.sign_transaction(unsigned, key_name="frozen-owner")

    def test_actual_loopback_signs_only_the_exact_named_key_without_transmitting(self):
        real_runner = cli.run_json
        for versioned in (False, True):
            with self.subTest(versioned=versioned):
                unsigned = transaction_fixture(versioned=versioned, data=b"x" * 130)
                signed = transaction_fixture(
                    versioned=versioned, signed=True, data=b"x" * 130
                )
                commands = []

                def fixture(argv, *, commands=commands, signed=signed, **kwargs):
                    commands.append(argv)
                    response = (
                        self.rows
                        if argv[3:] == ["keys", "list"]
                        else {"signer": self.owner, "signedTransaction": signed}
                    )
                    return real_runner(
                        [
                            sys.executable,
                            "-I",
                            "-S",
                            "-c",
                            "import sys; print(sys.argv[1])",
                            json.dumps(response),
                        ],
                        **kwargs,
                    )

                with (
                    patch.object(cli, "run_json", fixture),
                    patch.object(self.adapter, "identity", return_value={}) as identity,
                ):
                    result = self.adapter.sign_transaction(
                        unsigned, key_name="frozen-owner"
                    )
                self.assertEqual(
                    result, {"signer": self.owner, "signedTransaction": signed}
                )
                identity.assert_called_once()
                self.assertEqual(
                    commands,
                    [
                        [str(cli.APPROVED_BINARY), "-f", "json", "keys", "list"],
                        [
                            str(cli.APPROVED_BINARY),
                            "-f",
                            "json",
                            "sign",
                            "--tx",
                            unsigned,
                            "--key",
                            "frozen-owner",
                        ],
                    ],
                )

    def test_invalid_key_wire_base64_size_and_header_are_refused_before_spawn(self):
        original = base64.b64decode(transaction_fixture())
        malformed = [
            None,
            b"not-a-string",
            "",
            "!not-base64!",
            transaction_fixture() + "=",
            transaction_fixture() + "\n",
            base64.b64encode(b"x" * (cli.MAX_TRANSACTION_BYTES + 1)).decode(),
            base64.b64encode(b"\x82\x00" + original[1:]).decode(),
            base64.b64encode(b"\xff\xff\x04" + original[1:]).decode(),
        ]
        for cutoff in (1, 64, 128, 129, 130, 133, 200, len(original) - 1):
            malformed.append(base64.b64encode(original[:cutoff]).decode())
        for offset, value in ((129, 1), (130, 2), (131, 2), (132, 0)):
            raw = bytearray(original)
            raw[offset] = value
            malformed.append(base64.b64encode(raw).decode())
        v0 = bytearray(base64.b64decode(transaction_fixture(versioned=True)))
        v0[129] = 0x81
        malformed.append(base64.b64encode(v0).decode())
        malformed.append(base64.b64encode(original + b"trailing").decode())
        with (
            patch.object(self.adapter, "identity") as identity,
            patch.object(cli, "run_json") as process,
        ):
            for value in malformed:
                with (
                    self.subTest(value=str(value)[:30]),
                    self.assertRaises(cli.AdapterError),
                ):
                    self.adapter.sign_transaction(value, key_name="frozen-owner")
            for name in (None, "--help", "owner\nsecret", "../owner", ""):
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(cli.AdapterError, "invalid_named_cli_key"),
                ):
                    self.adapter.sign_transaction(transaction_fixture(), key_name=name)
            identity.assert_not_called()
            process.assert_not_called()

    def test_named_wallet_must_be_a_required_signer_before_sign_is_invoked(self):
        metadata = [{**self.rows[0], "address": base58_public_key(b"\x08" * 32)}]
        with (
            patch.object(self.adapter, "identity", return_value={}),
            patch.object(cli, "run_json", return_value=metadata) as process,
            self.assertRaisesRegex(
                cli.AdapterError, "not_a_required_transaction_signer"
            ),
        ):
            self.adapter.sign_transaction(
                transaction_fixture(), key_name="frozen-owner"
            )
        self.assertEqual(process.call_count, 1)

    def test_identity_metadata_and_sign_share_one_deadline(self):
        with (
            patch.object(self.adapter, "identity", return_value={}),
            patch.object(cli.time, "monotonic", side_effect=[100.0, 101.0, 103.0]),
            patch.object(cli, "run_json", return_value=self.rows) as process,
            self.assertRaisesRegex(
                cli.AdapterError, "signing_deadline_exceeded"
            ) as caught,
        ):
            self.adapter.sign_transaction(
                transaction_fixture(), key_name="frozen-owner"
            )
        self.assertFalse(caught.exception.ambiguous)
        self.assertEqual(process.call_count, 1)
        self.assertEqual(process.call_args.kwargs["timeout"], 1)

    def test_wrong_signer_message_other_signature_and_unsigned_response_are_refused(
        self,
    ):
        signed = bytearray(base64.b64decode(transaction_fixture(signed=True)))
        altered_message = bytearray(signed)
        altered_message[-1] ^= 1
        altered_cosignature = bytearray(signed)
        altered_cosignature[65] ^= 1
        responses = [
            (
                {
                    "signer": "wrong",
                    "signedTransaction": transaction_fixture(signed=True),
                },
                "signer_mismatch",
            ),
            (
                {
                    "signer": self.owner,
                    "signedTransaction": base64.b64encode(altered_message).decode(),
                },
                "message_changed",
            ),
            (
                {
                    "signer": self.owner,
                    "signedTransaction": base64.b64encode(altered_cosignature).decode(),
                },
                "other_signature_changed",
            ),
            (
                {"signer": self.owner, "signedTransaction": transaction_fixture()},
                "owner_signature_missing",
            ),
            (
                {
                    "signer": self.owner,
                    "signedTransaction": base64.b64encode(b"x" * 1233).decode(),
                },
                "invalid_cli_signed_transaction",
            ),
            ({"signer": self.owner}, "invalid_cli_signed_transaction"),
            ([], "signer_mismatch"),
        ]
        for response, error in responses:
            with (
                self.subTest(error=error),
                self.assertRaisesRegex(cli.AdapterError, error) as caught,
            ):
                self.sign_response(response)
            self.assertFalse(caught.exception.ambiguous)

    def test_signing_identity_refusal_and_timeout_never_transmit_or_retry(self):
        with (
            patch.object(
                self.adapter,
                "identity",
                side_effect=cli.AdapterError("jupiter_cli_hash_mismatch"),
            ),
            patch.object(cli, "run_json") as process,
            self.assertRaisesRegex(cli.AdapterError, "hash_mismatch"),
        ):
            self.adapter.sign_transaction(
                transaction_fixture(), key_name="frozen-owner"
            )
        process.assert_not_called()
        real_runner = cli.run_json
        commands = []

        def fixture(argv, **kwargs):
            commands.append(argv)
            if argv[3:] == ["keys", "list"]:
                return self.rows
            return real_runner(
                [sys.executable, "-I", "-S", "-c", "import time; time.sleep(10)"],
                **kwargs,
            )

        adapter = cli.JupiterCLI(timeout=0.1)
        with (
            patch.object(adapter, "identity", return_value={}),
            patch.object(cli, "run_json", fixture),
            self.assertRaises(cli.AdapterError) as caught,
        ):
            adapter.sign_transaction(transaction_fixture(), key_name="frozen-owner")
        self.assertEqual(caught.exception.code, "process_timeout")
        self.assertFalse(caught.exception.ambiguous)
        self.assertEqual(len(commands), 2)


class SDKProtocol(unittest.TestCase):
    def test_actions_stay_in_json_stdin_and_never_sign(self):
        bridge = sdkbridge.SDKBridge()
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(
                sdkbridge, "run_json", return_value={"status": "built"}
            ) as process,
        ):
            self.assertEqual(
                bridge.call(
                    {"action": "build-open", "asset": "ZEC", "owner": "public-wallet"}
                ),
                {"status": "built"},
            )
            args, kwargs = process.call_args
            self.assertEqual(
                args[0], ["/opt/homebrew/bin/node", str(sdkbridge.BRIDGE_SCRIPT)]
            )
            self.assertEqual(json.loads(kwargs["payload"])["action"], "build-open")
            self.assertNotIn("public-wallet", " ".join(args[0]))

    def test_checked_service_actions_are_explicit_and_only_execute_is_ambiguous(self):
        bridge = sdkbridge.SDKBridge()
        actions = (
            "service-markets",
            "service-positions",
            "service-build-open",
            "service-build-close",
            "service-signed",
            "service-execute",
            "service-request",
        )
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(
                sdkbridge, "run_json", return_value={"status": "ready"}
            ) as process,
        ):
            for action in actions:
                with self.subTest(action=action):
                    payload = {"action": action, "owner": "public-owner"}
                    self.assertEqual(bridge.call(payload), {"status": "ready"})
                    args, kwargs = process.call_args
                    self.assertNotIn("public-owner", " ".join(args[0]))
                    self.assertEqual(json.loads(kwargs["payload"]), payload)
                    self.assertEqual(kwargs["ambiguous"], action == "service-execute")

    def test_service_execute_timeout_is_ambiguous_and_never_retried(self):
        real_runner = cli.run_json
        calls = []

        def fixture(argv, **kwargs):
            calls.append(argv)
            return real_runner(
                [sys.executable, "-I", "-S", "-c", "import time; time.sleep(10)"],
                **kwargs,
            )

        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(sdkbridge, "run_json", fixture),
            self.assertRaises(cli.AdapterError) as caught,
        ):
            sdkbridge.SDKBridge(timeout=0.1).call({"action": "service-execute"})
        self.assertEqual(caught.exception.code, "process_timeout")
        self.assertTrue(caught.exception.ambiguous)
        self.assertEqual(len(calls), 1)

    def test_funded_actions_secrets_and_malformed_payloads_are_refused(self):
        bridge = sdkbridge.SDKBridge()
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(sdkbridge, "run_json") as process,
        ):
            for payload in (
                {"action": "execute"},
                {"action": "sendTransaction"},
                {"action": []},
                [],
                {"action": "simulate", "private_key": "fake-secret"},
                {"action": "status", "nested": {"seedPhrase": "fake words"}},
                {"action": "simulate", "amount": float("nan")},
            ):
                with (
                    self.subTest(payload=payload),
                    self.assertRaises(sdkbridge.AdapterError),
                ):
                    bridge.call(payload)
            process.assert_not_called()
        with self.assertRaises(sdkbridge.AdapterError):
            sdkbridge.SDKBridge(binary="/tmp/fake-node")
        with self.assertRaises(sdkbridge.AdapterError):
            sdkbridge.SDKBridge(script="/tmp/fake-bridge.mjs")


if __name__ == "__main__":
    unittest.main()
