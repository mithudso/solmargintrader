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


class ExecutorManagerAuthorizationTests(unittest.TestCase):
    def fixture(self):
        from types import SimpleNamespace
        from uuid import uuid4

        bot_id, runtime_id = str(uuid4()), str(uuid4())
        pinned = {
            "strategy_id": "trend",
            "strategy_version": "sma-crossover-v1",
            "config_hash": "a" * 64,
            "config_revision": 1,
            "bar_seconds": 60,
            "execution_model": "next_open",
            "mode": "paper",
            "resolved_values": {"armed": False},
        }
        row = {
            "spec": pinned,
            "runtime_id": runtime_id,
            "generation": 1,
            "desired": "stopped",
            "observed": "stopped",
            "input": {"descriptor": {}},
            "checkpoint": {},
            "heartbeat": None,
            "evaluated": None,
        }
        authorization = {
            "mode": "paper",
            "armed": False,
            "desired": "stopped",
            "observed": "stopped",
            "input_state": "reference",
            "accounting_state": "independent_virtual_account_not_funded_wallet",
            "entries_paused": False,
        }
        scope = {
            "bot_id": bot_id,
            "runtime_id": runtime_id,
            "generation": 1,
            "strategy": "trend",
            "strategy_version": "sma-crossover-v1",
            "config_hash": "a" * 64,
            "revision": 1,
            "timeframe": 60,
            "execution_model": "next_open",
            "authorization": authorization,
        }
        return (
            SimpleNamespace(bot_id=bot_id),
            row,
            {"scope": scope, "swap": {"live": False, "exit": False}},
        )

    def call_boundary(self, spec, row, request):
        from types import SimpleNamespace

        from botmanager.executor_commands import _request

        with (
            patch("botmanager.executor_commands.ManagerStore") as store,
            patch("botmanager.executor_commands.RuntimeLedger") as ledger,
            patch("botmanager.executor_commands.read_document", return_value=request),
            patch("botmanager.executor_commands.entries_paused", return_value=False),
        ):
            store.return_value.get_spec.return_value = spec
            ledger.return_value.get.return_value = row
            return _request(
                {"request": "/unused.json", "identity": spec.bot_id},
                SimpleNamespace(home="/nonexistent/manager-fixture"),
            )

    def test_paper_disarmed_stopped_runtime_never_forwards_live_flag(self):
        spec, row, request = self.fixture()
        for exit_only in (False, True):
            request["swap"].update(live=True, exit=exit_only)
            with self.assertRaises(ManagerError) as error:
                self.call_boundary(spec, row, request)
            self.assertEqual(error.exception.code, "executor_runtime_disarmed")

    def test_preview_binds_actual_authorization_not_client_claims(self):
        spec, row, request = self.fixture()
        self.assertEqual(self.call_boundary(spec, row, request), request)
        request["scope"]["authorization"]["armed"] = True
        with self.assertRaises(ManagerError) as error:
            self.call_boundary(spec, row, request)
        self.assertEqual(error.exception.code, "executor_scope_changed")

    def test_generation_transplant_refuses_before_owner_transport(self):
        spec, row, request = self.fixture()
        request["scope"]["generation"] += 1
        with self.assertRaises(ManagerError) as error:
            self.call_boundary(spec, row, request)
        self.assertEqual(error.exception.code, "executor_scope_changed")

    def test_forged_live_spec_stopped_or_reference_runtime_still_refuses(self):
        spec, row, request = self.fixture()
        row["spec"].update(mode="live", resolved_values={"armed": True})
        request["swap"]["live"] = True
        with self.assertRaises(ManagerError) as error:
            self.call_boundary(spec, row, request)
        self.assertEqual(error.exception.code, "executor_runtime_ineligible")
        row.update(desired="running", observed="running")
        with self.assertRaises(ManagerError) as error:
            self.call_boundary(spec, row, request)
        self.assertEqual(error.exception.code, "executor_runtime_ineligible")
