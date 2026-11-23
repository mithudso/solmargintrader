import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from oracle.cli import main, owner, snapshot
from oracle.engine import OracleEngine
from oracle.feeds import SOL_MINT, USDC_MINT
from oracle.reader import ReadOnlyOracle


class CliTests(unittest.TestCase):
    def jupiter_run(self, archive, *options, key="synthetic-only"):
        payload = {
            SOL_MINT: {"usdPrice": 165, "blockId": 100},
            USDC_MINT: {"usdPrice": 1, "blockId": 100},
            "A" * 32: {"usdPrice": 20, "blockId": 100},
            "B" * 32: {"usdPrice": 2, "blockId": 100},
        }
        stream = io.StringIO()
        with (
            patch.dict(os.environ, {"JUPITER_API_KEY": key}),
            patch("oracle.feeds._get_json", return_value=payload) as transport,
            redirect_stdout(stream),
        ):
            code = main(["--archive", str(archive), "run", "--source", "jupiter", "--max-ticks", "1", *options])
        return code, json.loads(stream.getvalue()), transport.call_count

    def test_jupiter_archive_refuses_reversed_or_changed_mints_and_accepts_same_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive.sqlite3"
            code, _, calls = self.jupiter_run(archive)
            self.assertEqual((code, calls), (0, 1))
            before = archive.read_bytes()
            for base, quote in ((USDC_MINT, SOL_MINT), ("A" * 32, "B" * 32)):
                with self.subTest(base=base, quote=quote):
                    code, result, calls = self.jupiter_run(archive, "--base-mint", base, "--quote-mint", quote)
                    self.assertEqual((code, calls), (2, 0))
                    self.assertEqual(result["reason"], "archive_jupiter_mint_scope_mismatch_use_new_archive")
                    self.assertEqual(archive.read_bytes(), before)

            code, result, calls = self.jupiter_run(archive, "--quote-mint", USDC_MINT, "--base-mint", SOL_MINT)
            self.assertEqual((code, calls), (0, 1))
            self.assertEqual(result["market"]["observation"]["price"], 165)
            reader = ReadOnlyOracle(archive, instrument="SOL/USDC")
            self.assertEqual(reader.status()["counts"]["observations"], 2)

    def test_legacy_jupiter_history_stays_readable_but_refuses_unproven_append(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive.sqlite3"
            writer = OracleEngine(archive)
            writer.ingest({
                "source": "jupiter_price_v3", "instrument": "SOL/USDC", "venue": "jupiter",
                "kind": "polled_reference_ratio", "event_id": "old", "observed_at": 1000,
                "received_at": 1000, "price": 165, "base_usd_price": 165, "quote_usd_price": 1,
                "provider_block_ids": {SOL_MINT: 100, USDC_MINT: 100},
            }, now=1000)
            before = archive.read_bytes()
            code, result, calls = self.jupiter_run(archive)
            self.assertEqual((code, calls), (2, 0))
            self.assertEqual(result["reason"], "archive_jupiter_mint_order_unverified_use_new_archive")
            self.assertIn("--archive", result["remedy"])
            self.assertEqual(archive.read_bytes(), before)
            reader = ReadOnlyOracle(archive, instrument="SOL/USDC")
            self.assertEqual(reader.market(1000)["observation"]["price"], 165)

    def test_failed_jupiter_poll_does_not_bind_the_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive.sqlite3"
            code, result, calls = self.jupiter_run(archive, key="")
            self.assertEqual((code, result["status"], calls), (3, "feed_unavailable", 0))
            code, result, calls = self.jupiter_run(archive, "--base-mint", "A" * 32, "--quote-mint", "B" * 32)
            self.assertEqual((code, calls), (0, 1))
            self.assertEqual(result["market"]["observation"]["price"], 10)

    def test_source_scope_survives_first_jupiter_ingest_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive.sqlite3"
            with patch.object(OracleEngine, "ingest", side_effect=OSError("synthetic write failure")):
                code, _, calls = self.jupiter_run(archive)
            self.assertEqual((code, calls), (2, 1))

            stamp = time.time()
            (root / "latest.json").write_text(json.dumps({
                "t": stamp, "q": {"SOL-USDC": [99, 101, 100, 1, 1, stamp]},
            }))
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main([
                    "--archive", str(archive), "run", "--source", "recorder", "--recorder-root", str(root),
                    "--max-ticks", "1",
                ])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stream.getvalue())["error"], "oracle_operation_failed")

            code, result, calls = self.jupiter_run(archive)
            self.assertEqual((code, calls), (0, 1))
            self.assertEqual(result["market"]["observation"]["source"], "jupiter_price_v3")
            reader = ReadOnlyOracle(archive, instrument="SOL/USDC")
            self.assertEqual(reader.status()["counts"]["observations"], 1)

    def test_missing_dependencies_are_cli_prerequisites_and_help_remains_available(self):
        root = Path(__file__).resolve().parents[2]
        bootstrap = """
import builtins, runpy, sys
module = sys.argv[1]
sys.argv = [module, *sys.argv[2:]]
original = builtins.__import__
def refused(name, *args, **kwargs):
    if name.split('.')[0] in ('numpy', 'mcp'):
        raise ModuleNotFoundError('private dependency canary', name=name.split('.')[0])
    return original(name, *args, **kwargs)
builtins.__import__ = refused
runpy.run_module(module, run_name='__main__')
"""
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "unused.sqlite3"
            for module, command in [("oracle", ["--archive", str(archive), "status"]),
                                    ("oracle.server", ["--archive", str(archive)])]:
                for arguments, expected in [(command, 3), (["--help"], 0)]:
                    with self.subTest(module=module, arguments=arguments):
                        result = subprocess.run([sys.executable, "-c", bootstrap, module, *arguments],
                                                check=False, cwd=root, capture_output=True, text=True, timeout=5)
                        self.assertEqual(result.returncode, expected, result.stderr)
                        if expected == 3:
                            self.assertIn("uv pip install --python", result.stdout + result.stderr)
                            self.assertNotIn("Traceback", result.stderr)
                            self.assertNotIn("private dependency canary", result.stdout + result.stderr)
                        else:
                            self.assertIn("usage:", result.stdout)
                        self.assertFalse(archive.exists())

    def test_bad_arguments_show_usage_without_echoing_private_values(self):
        root = Path(__file__).resolve().parents[2]
        for module in ["oracle", "oracle.server"]:
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, "-m", module, "--private-input-canary"],
                                        check=False, cwd=root, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)
                self.assertNotIn("private-input-canary", result.stdout + result.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a POSIX FIFO")
    def test_secret_fifo_is_refused_before_starting_a_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "secret.fifo"
            os.mkfifo(secret, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "oracle", "--archive", str(root / "archive.sqlite3"),
                 "webhook", "--inbox", str(root / "inbox.sqlite3"), "--secret-file", str(secret)],
                cwd=Path(__file__).resolve().parents[2],
                env={"PATH": os.defpath, "PYTHONPATH": str(Path(__file__).resolve().parents[2]), "ORACLE_WEBHOOK_SECRET": ""},
                capture_output=True, text=True, timeout=1, check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["error"], "oracle_operation_failed")
            self.assertFalse((root / "inbox.sqlite3").exists())

    def test_archive_owner_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.sqlite3"
            with (
                owner(path),
                self.assertRaisesRegex(RuntimeError, "already_running"),
                owner(path),
            ):
                pass
            with owner(path):
                pass

    def test_snapshot_is_consistent_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.sqlite3"
            out = Path(root) / "snapshot.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE evidence (value INTEGER)")
                db.execute("INSERT INTO evidence VALUES (42)")
            receipt = snapshot(path, out)
            self.assertEqual(len(receipt["sha256"]), 64)
            with closing(sqlite3.connect(out)) as db:
                self.assertEqual(
                    db.execute("SELECT value FROM evidence").fetchone(), (42,)
                )
            with self.assertRaises(ValueError):
                snapshot(path, out)

    def test_bounded_unavailable_feed_has_nonzero_status(self):
        with tempfile.TemporaryDirectory() as root:
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(
                    [
                        "--archive",
                        str(Path(root) / "archive.sqlite3"),
                        "run",
                        "--recorder-root",
                        str(Path(root) / "absent"),
                        "--max-ticks",
                        "1",
                    ]
                )
            self.assertEqual(code, 3)
            self.assertEqual(
                json.loads(stream.getvalue())["reason"], "recorder_unavailable"
            )

    def test_guidance_is_available_without_an_usable_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            guide = repo / "docs" / "COMPOUND-5M.md"
            guide.parent.mkdir(parents=True)
            guide.write_text("Fixture forward guide\n")
            missing = root / "new" / "history.sqlite3"
            incompatible = root / "incompatible.sqlite3"
            with closing(sqlite3.connect(incompatible)) as db, db:
                db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, body TEXT)")
                db.execute("INSERT INTO metadata VALUES ('policy', '{}')")
            original = incompatible.read_bytes()

            for archive in (missing, incompatible):
                with self.subTest(archive=archive.name), redirect_stdout(io.StringIO()) as stream:
                    code = main(["--archive", str(archive), "guidance", "--stage", "forward", "--repo", str(repo)])
                    self.assertEqual(code, 0)
                    response = json.loads(stream.getvalue())
                    self.assertTrue(response["ok"])
                    self.assertEqual(response["data"]["stage"], "forward")
                    self.assertEqual(response["data"]["guides"][0]["path"], str(guide))
                    self.assertTrue(response["data"]["guides"][0]["available"])

            self.assertFalse(missing.parent.exists())
            self.assertEqual(incompatible.read_bytes(), original)

    def test_bad_run_limits_do_not_echo_submitted_input(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["run", "--interval", "nan"])
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stream.getvalue())["error"], "oracle_operation_failed"
        )


if __name__ == "__main__":
    unittest.main()
