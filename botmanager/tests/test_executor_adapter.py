from __future__ import annotations

import json
import sys
import unittest
from unittest.mock import patch

from botmanager.adapters.executor import ExecutorAdapter
from botmanager.domain import ManagerError
from botmanager.executor_commands import command_specs


def descriptor():
    return {
        "version": 1,
        "interpreter": sys.executable,
        "home": "/nonexistent/executor-fixture",
        "identity": {
            "protocol": 1,
            "wallet": "synthetic-wallet",
            "source_digest": "a" * 64,
            "installation_digest": "b" * 64,
            "config_digest": "c" * 64,
            "venue": "jupiter-swap-v1",
        },
    }


def response(command, result):
    return (
        0,
        json.dumps(
            {"ok": True, "command": command, "result": result, "error": None}
        ).encode(),
        b"",
    )


class ExecutorAdapterTests(unittest.TestCase):
    def test_optional_adapter_does_not_import_signer_or_executor(self):
        import inspect

        import botmanager.adapters.executor as module

        source = inspect.getsource(module)
        self.assertNotIn("from executor", source)
        self.assertNotIn("import executor", source)

    def test_exact_installed_identity_is_required(self):
        bad = descriptor()
        bad["identity"] = {"protocol": 1}
        with self.assertRaises(ManagerError):
            ExecutorAdapter(bad)
        owner = ExecutorAdapter(descriptor())
        with (
            patch(
                "botmanager.adapters.executor.bounded_process",
                return_value=response(
                    "wallet.capabilities",
                    {**owner.descriptor["identity"], "config_digest": "f" * 64},
                ),
            ),
            self.assertRaisesRegex(ManagerError, "changed"),
        ):
            owner.capabilities()

    def test_transport_is_installed_isolated_bounded_and_has_no_pythonpath(self):
        owner = ExecutorAdapter(descriptor())
        with patch(
            "botmanager.adapters.executor.bounded_process",
            return_value=response("wallet.capabilities", owner.descriptor["identity"]),
        ) as process:
            self.assertEqual(owner.capabilities(), owner.descriptor["identity"])
            args, kwargs = process.call_args
            self.assertEqual(
                args[0][:5], [sys.executable, "-I", "-B", "-m", "executor.cli"]
            )
            self.assertNotIn("PYTHONPATH", kwargs["env"])
            self.assertEqual(kwargs["cwd"], "/")
            self.assertEqual(kwargs["limit"], 262144)

    def test_ambiguous_or_broken_send_never_retries(self):
        owner = ExecutorAdapter(descriptor())
        with patch(
            "botmanager.adapters.executor.bounded_process",
            side_effect=[
                response("wallet.capabilities", owner.descriptor["identity"]),
                ValueError("deadline"),
            ],
        ) as process:
            with self.assertRaises(ManagerError) as error:
                owner.call("manager.swap", {"request": {"fixture": True}})
            self.assertEqual(error.exception.code, "executor_outcome_unknown")
            self.assertEqual(process.call_count, 2)

    def test_refusal_sanitizes_untrusted_response_and_rejects_unknown_commands(self):
        owner = ExecutorAdapter(descriptor())
        body = {
            "ok": False,
            "command": "manager.admit",
            "result": None,
            "error": {"code": "refused", "message": "CANARY-PRIVATE"},
        }
        with patch(
            "botmanager.adapters.executor.bounded_process",
            return_value=(1, json.dumps(body).encode(), b""),
        ):
            with self.assertRaises(ManagerError) as error:
                owner._call("manager.admit", {})
            self.assertNotIn("CANARY", str(error.exception))
        with self.assertRaises(ManagerError):
            owner._call("gates.record_research", {})

    def test_setup_probes_public_capabilities_and_writes_immutable_descriptor(self):
        import tempfile
        from pathlib import Path

        from botmanager.adapters.executor import prepare_descriptor

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "owner.json"
            with patch(
                "botmanager.adapters.executor.bounded_process",
                return_value=response("wallet.capabilities", descriptor()["identity"]),
            ) as process:
                result = prepare_descriptor(
                    sys.executable, str(Path(directory) / "home"), output
                )
            self.assertFalse(result["authority_initialized"])
            self.assertFalse(result["live_enabled"])
            self.assertEqual(
                json.loads(output.read_text())["identity"], descriptor()["identity"]
            )
            self.assertEqual(process.call_count, 1)
            self.assertFalse((Path(directory) / "home").exists())

    def test_registry_exports_all_actions(self):
        from botmanager.registry import CommandSpec

        specs = command_specs(CommandSpec)
        self.assertEqual(
            {s.name for s in specs},
            {
                "executor-setup",
                "executor-capabilities",
                "executor-admit",
                "executor-intent",
                "executor-status",
                "executor-reconcile",
            },
        )
