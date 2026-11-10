from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from soltui.experiments import ExperimentError, ExperimentStore
from soltui.research_admission import admit_read, inspect_history, optimizer_lease
from soltui.research_owner import handle, identity

from .research_fixtures import grid, recording


class OwnerProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.authority = self.root / "evidence"
        from unittest.mock import patch

        environment = patch.dict(
            os.environ,
            {
                "SOLTUI_CONFIG_DIR": str(self.root / "config"),
                "SOLTUI_RESEARCH_REGISTRY": str(
                    self.root / "namespace" / "authority.json"
                ),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.request = {
            "version": 2,
            "operation": "status",
            "authority": {
                "id": str(uuid4()),
                "root": str(self.authority),
                "known_clients": [
                    {"root": str(self.authority), "kind": "native", "active": False}
                ],
                "inventory_complete": True,
            },
            "params": {"run_id": None},
            "expected_identity": identity(),
        }

    def bind(self):
        from soltui import commands
        from soltui.config import Settings
        from soltui.roster import Roster
        from soltui.signals import SignalDefaults

        request = {
            **self.request,
            "operation": "register",
            "params": {"accept_registered_roots_only": True, "initialize_first": False},
        }
        result = commands.dispatch(
            "research.protocol",
            {"request": request},
            ctx=commands.Context(Settings(), Roster([]), SignalDefaults()),
            quiet=True,
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["result"]["registration"]["registered"])
        self.assertEqual(
            result["result"]["registration"]["coverage"], "registered_roots_only"
        )

    def test_inert_status_does_not_initialize_absent_owner(self):
        self.assertFalse(handle(self.request)["initialized"])
        self.assertFalse(self.authority.exists())
        with self.assertRaises(ExperimentError):
            handle({**self.request, "expected_identity": {}})
        with self.assertRaises(ExperimentError):
            handle({**self.request, "extra": "metadata"})

    def test_actual_headless_stdio_uses_registry_without_default_writes(self):
        env = {
            **os.environ,
            "SOLTUI_CONFIG_DIR": str(self.root / "config"),
            "SOLTUI_RESEARCH_REGISTRY": str(self.root / "namespace" / "authority.json"),
        }
        p = subprocess.run(
            [sys.executable, "-B", "-m", "soltui.research_owner"],
            check=False,
            input=json.dumps(self.request),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        self.assertEqual(p.returncode, 0, (p.stdout, p.stderr))
        self.assertFalse(json.loads(p.stdout)["result"]["initialized"])
        self.assertFalse((self.root / "config").exists())
        self.assertFalse(self.authority.exists())

    def test_real_canonical_backtest_consumes_history(self):
        owner = ExperimentStore(self.authority)
        self.bind()
        d = recording(self.root, 40)
        result = handle(
            {
                **self.request,
                "operation": "backtest",
                "params": {"spec": grid().to_dict(), "descriptor": d},
            }
        )
        self.assertFalse(result["report"]["certified"])
        with owner._connect() as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM manager_exposures").fetchone()[0], 1
            )
        bad = {
            **self.request,
            "authority": {**self.request["authority"], "id": str(uuid4())},
        }
        with self.assertRaises(ExperimentError):
            handle(bad)

    def test_global_optimizer_and_pre_read_fence(self):
        ExperimentStore(self.authority)
        from concurrent.futures import ThreadPoolExecutor

        def compete():
            with optimizer_lease(self.authority):
                pass

        with (
            optimizer_lease(self.authority),
            ThreadPoolExecutor(max_workers=1) as pool,
            self.assertRaisesRegex(ExperimentError, "optimizer"),
        ):
            pool.submit(compete).result()
        from unittest.mock import patch

        with patch.dict(os.environ, {"SOLTUI_RESEARCH_AUTHORITY": str(self.authority)}):
            admit_read("SOL", source="f5-fixture", end=100, attempts=3)
        owner = ExperimentStore(self.authority)
        with owner._connect() as db:
            self.assertEqual(
                db.execute("SELECT SUM(attempts) FROM manager_imports").fetchone()[0], 3
            )

    def test_missing_and_unknown_history_explicit(self):
        self.assertTrue(inspect_history(self.root / "missing", "f5")["absence_checked"])
        (self.root / "partial.json").write_text("{}")
        self.assertEqual(
            inspect_history(self.root, "bg")["coverage"], "unknown_history"
        )

    def test_hash_bound_f5_import_counts_all_attempts_idempotently(self):
        import hashlib
        import sqlite3

        directory = self.root / "batches" / "fixture"
        directory.mkdir(parents=True)
        prices = self.root / "SOL_1h.csv"
        prices.write_text(
            "timestamp,open,high,low,close,volume\n100,1,1,1,1,1\n3700,1,1,1,1,1\n"
        )
        with sqlite3.connect(directory / "batch.sqlite3") as db:
            db.executescript(
                "CREATE TABLE meta(key TEXT,value TEXT); CREATE TABLE cell(id INTEGER,asset TEXT,interval TEXT,state TEXT); CREATE TABLE attempt(cell INTEGER,job_id TEXT,state TEXT,result TEXT); CREATE TABLE series(asset TEXT,interval TEXT,path TEXT,sha256 TEXT);"
            )
            db.executemany(
                "INSERT INTO meta VALUES (?,?)",
                [("phase", '"completed"'), ("assets", '["SOL"]')],
            )
            db.execute('INSERT INTO cell VALUES (1,"SOL","1h","completed")')
            db.execute('INSERT INTO attempt VALUES (1,"failed-variant","failed","{}")')
            db.execute(
                "INSERT INTO series VALUES (?,?,?,?)",
                (
                    "SOL",
                    "1h",
                    str(prices),
                    hashlib.sha256(prices.read_bytes()).hexdigest(),
                ),
            )
        owner = ExperimentStore(self.authority)
        client = {"root": str(directory.parent), "kind": "f5", "active": False}
        evidence = owner.manager_register_client(client)
        self.assertEqual(evidence["coverage"], "verified")
        self.assertEqual(
            evidence["records"][0]["intervals"],
            [{"coin": "SOL", "start": 100.0, "end": 7300.0}],
        )
        owner.manager_register_client(client)
        with owner._connect() as db:
            self.assertEqual(
                db.execute("SELECT SUM(attempts) FROM manager_imports").fetchone()[0], 1
            )
        prices.write_text("timestamp,open,high,low,close,volume\n100,2,2,2,2,1\n")
        self.assertEqual(
            owner.manager_register_client(client)["coverage"], "unknown_history"
        )

    def test_owner_binding_cannot_reset_with_new_authority_root(self):
        ExperimentStore(self.authority)
        self.bind()
        descriptor = recording(self.root, 8)
        handle(
            {
                **self.request,
                "operation": "backtest",
                "params": {"spec": grid().to_dict(), "descriptor": descriptor},
            }
        )
        other = self.root / "new-home"
        ExperimentStore(other)
        changed = {
            **self.request,
            "authority": {
                **self.request["authority"],
                "root": str(other),
                "id": str(uuid4()),
            },
        }
        with self.assertRaisesRegex(ExperimentError, "identity mismatch"):
            handle(changed)

    def test_new_owner_config_root_refuses_instead_of_resetting_authority(self):
        from unittest.mock import patch

        ExperimentStore(self.authority)
        self.bind()
        new_authority = self.root / "new-authority"
        ExperimentStore(new_authority)
        request = {
            **self.request,
            "authority": {
                **self.request["authority"],
                "root": str(new_authority),
                "id": str(uuid4()),
            },
        }
        with (
            patch.dict(
                os.environ, {"SOLTUI_CONFIG_DIR": str(self.root / "new-config")}
            ),
            self.assertRaisesRegex(
                ExperimentError, "authority_registration_required|identity mismatch"
            ),
        ):
            handle(request)
        self.assertFalse((self.root / "new-config").exists())

    def test_public_registration_idempotent_and_second_config_uses_same_authority(self):
        from unittest.mock import patch

        ExperimentStore(self.authority)
        self.bind()
        first = (self.root / "namespace" / "authority.json").read_bytes()
        self.bind()
        self.assertEqual(
            (self.root / "namespace" / "authority.json").read_bytes(), first
        )
        with patch.dict(
            os.environ, {"SOLTUI_CONFIG_DIR": str(self.root / "second-owner")}
        ):
            with self.assertRaisesRegex(ExperimentError, "registration_required"):
                handle(self.request)
            receipt = handle(
                {
                    **self.request,
                    "operation": "register",
                    "params": {
                        "accept_registered_roots_only": True,
                        "initialize_first": False,
                    },
                }
            )
            self.assertEqual(receipt["registration"]["isolation_mode"], "isolated")
            self.assertFalse(receipt["registration"]["production_eligible"])
            self.assertTrue(handle(self.request)["initialized"])
            conflict = {
                **self.request,
                "operation": "register",
                "params": {
                    "accept_registered_roots_only": True,
                    "initialize_first": False,
                },
                "authority": {**self.request["authority"], "id": str(uuid4())},
            }
            with self.assertRaisesRegex(ExperimentError, "identity mismatch"):
                handle(conflict)

    def test_public_first_initialization_records_unknown_history_and_never_replaces(
        self,
    ):
        from soltui import commands
        from soltui.config import Settings
        from soltui.roster import Roster
        from soltui.signals import SignalDefaults

        request = {
            **self.request,
            "operation": "register",
            "params": {"accept_registered_roots_only": True, "initialize_first": True},
        }
        ctx = commands.Context(Settings(), Roster([]), SignalDefaults())
        result = commands.dispatch(
            "research.protocol", {"request": request}, ctx=ctx, quiet=True
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(
            result["result"]["registration"]["initialization_history"], "unknown"
        )
        self.assertTrue((self.authority / "experiments.sqlite3").is_file())
        status = handle(self.request)
        self.assertEqual(
            status["coverage_report"]["blockers"][0]["code"], "unknown_prior_history"
        )
        repeated = commands.dispatch(
            "research.protocol", {"request": request}, ctx=ctx, quiet=True
        )
        self.assertEqual(result, repeated)
        saved = self.authority / "experiments.saved"
        (self.authority / "experiments.sqlite3").rename(saved)
        refused = commands.dispatch(
            "research.protocol", {"request": request}, ctx=ctx, quiet=True
        )
        self.assertFalse(refused["ok"])
        self.assertFalse((self.authority / "experiments.sqlite3").exists())

    def test_final_receipt_survives_future_reads_but_rejects_prior_overlap(self):
        from botmanager.blind import decide
        from botmanager.data import load_recording
        from botmanager.research import execute

        from soltui.experiments import fingerprint
        from soltui.research_admission import registered_authority

        owner = ExperimentStore(self.authority)
        self.bind()
        spec = grid()
        data = load_recording(recording(self.root, 800))
        registration = registered_authority(
            self.request["authority"], self.root / "config"
        )
        authority = {
            k: registration[k] for k in ("namespace_id", "isolation_mode", "coverage")
        }
        authority["roster_revision"] = fingerprint(registration)
        options = {
            "ranges": {"rungs": [8]},
            "horizon_bars": 1,
            "warmup_bars": 1,
            "blocks": 10,
            "confidence": {
                "method": "block_bootstrap",
                "seed": 0,
                "minimum_blocks": 10,
            },
        }

        def fixture(candidate, snapshot):
            return {
                "metrics": {
                    "net_return": 0.03
                    if candidate.resolved_values["rungs"] == 8
                    else 0.01,
                    "drawdown": 0.01,
                    "turnover": 1.0,
                    "trades": 4,
                    "uncertainty": 0.01,
                },
                "certified": True,
            }

        run = execute(
            owner,
            spec,
            data,
            options,
            judge=decide,
            evaluator=fixture,
            authority_context=authority,
        )
        request = {
            **self.request,
            "operation": "proposal",
            "params": {"run_id": run["run_id"]},
        }
        before = handle(request)
        self.assertTrue(before["reconcilable"])
        self.assertTrue(before["proposal"]["authority"]["scoped_fresh"])
        self.assertFalse(before["proposal"]["production_eligible"])
        end = data["bars"][-1]["ts"] + 60
        owner.manager_import(
            "later-paper",
            "new-dates",
            "a" * 64,
            [{"coin": "SOL", "start": end, "end": end + 60}],
            attempts=0,
        )
        self.assertEqual(handle(request), before)
        interval = owner.get_run(run["run_id"])["spec"]["geometry"]["holdout"][0]
        owner.manager_import(
            "later-training", "spent-dates", "b" * 64, [interval], attempts=1
        )
        self.assertEqual(handle(request), before)
        owner.manager_import(
            "imported-old-client",
            "prior-exposure",
            "c" * 64,
            [interval],
            attempts=1,
            historical=True,
        )
        after = handle(request)
        self.assertFalse(after["reconcilable"])
        self.assertEqual(after["proposal"], before["proposal"])
        self.assertEqual(
            after["reason"], "research_authority_roster_or_history_changed"
        )

    def test_hostile_nested_canary_never_reaches_logs_or_artifacts(self):
        from unittest.mock import patch

        from soltui import commands
        from soltui.config import Settings
        from soltui.roster import Roster
        from soltui.signals import SignalDefaults

        ExperimentStore(self.authority)
        self.bind()
        canary = "DO-NOT-PERSIST-hostile-private-credential-4187"
        hostile = {
            **self.request,
            "params": {"run_id": None, "unknown_private_field": {"secret": canary}},
        }
        ctx = commands.Context(Settings(), Roster([]), SignalDefaults())
        with patch.dict(os.environ, {"SOLTUI_LOG_DIR": str(self.root / "logs")}):
            envelope = commands.dispatch(
                "research.protocol", {"request": hostile}, ctx=ctx
            )
            self.assertFalse(envelope["ok"])
            self.assertNotIn(canary, json.dumps(envelope))
            log = (self.root / "logs" / "calls.jsonl").read_text()
            self.assertEqual(json.loads(log)["params_keys"], ["request"])
            self.assertNotIn("unknown_private_field", log)
            process = subprocess.run(
                [sys.executable, "-B", "-m", "soltui.research_owner"],
                input=json.dumps(hostile),
                capture_output=True,
                text=True,
                env=os.environ,
                timeout=30,
                check=False,
            )
        self.assertEqual(process.returncode, 3)
        self.assertNotIn(canary, process.stdout + process.stderr)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(canary.encode(), path.read_bytes(), str(path))

    def test_omitted_client_list_still_enrolls_bounded_known_owners(self):
        from unittest.mock import patch

        from soltui.research_admission import known_clients

        with patch.dict(os.environ, {"SOLTUI_RESEARCH_REGISTRY": ""}):
            rows, unknown = known_clients(
                self.root / "config",
                {
                    "source": "oracle_archive",
                    "archive_path": str(
                        self.root
                        / "selected-ecosystem"
                        / "oracle"
                        / "SOL"
                        / "history.sqlite3"
                    ),
                },
            )
        paths = {r["root"] for r in rows}
        self.assertIn(
            str(Path.home() / ".local/share/solmargintrader/ecosystem/batches"), paths
        )
        self.assertIn(
            str(
                Path.home() / ".local/share/solmargintrader/ecosystem-paper-v1/batches"
            ),
            paths,
        )
        self.assertIn(
            str((self.root / "selected-ecosystem" / "batches").resolve()), paths
        )
        self.assertFalse(unknown)
        # Discovery above only constructs paths; enrollment below stays isolated.
        ExperimentStore(self.authority)
        request = {
            **self.request,
            "operation": "register",
            "authority": {**self.request["authority"], "known_clients": []},
            "params": {"accept_registered_roots_only": True, "initialize_first": False},
        }
        result = handle(request)
        paths = {r["root"] for r in result["registration"]["history"]}
        self.assertIn(str((self.root / "config" / "f5-batches").resolve()), paths)
        self.assertNotIn(
            str(Path.home() / ".local/share/solmargintrader/ecosystem/batches"), paths
        )

    def test_preledger_bot_history_imports_even_without_experiment_directory(self):
        bots = self.root / "config" / "bots"
        bots.mkdir(parents=True)
        (bots / "optimize.json").write_text(
            json.dumps({"runs": 3, "log": [{"at": 1000}]})
        )
        history = inspect_history(self.root / "config" / "experiments", "native")
        self.assertEqual(history["records"][0]["attempts"], 3)
        self.assertEqual(history["records"][0]["intervals"][0]["end"], 1000)
        ExperimentStore(self.authority)
        self.bind()
        from soltui.research_admission import registered_authority

        registered = registered_authority(
            self.request["authority"], self.root / "config"
        )
        self.assertIn(
            str(self.authority.resolve()),
            {c["root"] for c in registered["known_clients"]},
        )

    def test_operation_enrolls_explicit_new_owner_before_read(self):
        ExperimentStore(self.authority)
        self.bind()
        other = self.root / "other-ecosystem" / "batches"
        request = {
            **self.request,
            "operation": "backtest",
            "authority": {
                **self.request["authority"],
                "known_clients": [
                    *self.request["authority"]["known_clients"],
                    {"root": str(other), "kind": "f5", "active": True},
                ],
            },
            "params": {
                "spec": grid().to_dict(),
                "descriptor": recording(self.root, 40),
            },
        }
        handle(request)
        status = handle(self.request)
        self.assertTrue(
            any(
                b.get("root") == str(other.resolve())
                for b in status["coverage_report"]["blockers"]
            )
        )

    def test_unknown_nested_client_field_rejected_even_on_inert_status(self):
        bad = {
            **self.request,
            "authority": {
                **self.request["authority"],
                "known_clients": [
                    {
                        **self.request["authority"]["known_clients"][0],
                        "secret": "private",
                    }
                ],
            },
        }
        with self.assertRaises(ExperimentError):
            handle(bad)
        self.assertFalse(self.authority.exists())

    def test_missing_previously_observed_history_is_not_fresh_absence(self):
        owner = ExperimentStore(self.authority)
        legacy = self.root / "legacy"
        ExperimentStore(legacy)
        client = {"root": str(legacy), "kind": "native", "active": False}
        self.assertEqual(owner.manager_register_client(client)["coverage"], "verified")
        (legacy / "experiments.sqlite3").rename(legacy / "saved.sqlite3")
        self.assertEqual(
            owner.manager_register_client(client)["coverage"], "unavailable"
        )
        self.assertTrue(owner.manager_coverage()["blockers"])

    def test_public_describe_is_inert_and_reuses_canonical_binding(self):
        request = {
            **self.request,
            "operation": "describe",
            "params": {},
            "authority": None,
            "expected_identity": None,
        }
        result = handle(request)
        self.assertEqual(result["identity"], identity())
        self.assertIsNone(result["canonical_authority"])
        self.assertFalse(self.authority.exists())
        self.assertFalse((self.root / "config").exists())
        ExperimentStore(self.authority)
        self.bind()
        result = handle(request)
        self.assertEqual(
            result["canonical_authority"],
            {
                "id": self.request["authority"]["id"],
                "root": str(self.authority.resolve()),
            },
        )
        process = subprocess.run(
            [sys.executable, "-B", "-m", "soltui.research_owner"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            env=os.environ,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["result"], result)
