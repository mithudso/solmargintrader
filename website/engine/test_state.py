from __future__ import annotations

import copy
import datetime as dt
import errno
import hashlib
import json
import os
import sqlite3
import ssl
import tempfile
import threading
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from website.engine.state import (
    CHUNK_BYTES,
    Checkpoint,
    RemoteState,
    StateError,
    canonical,
    validate_manifest,
)


class MemoryState:
    def __init__(self):
        self.epoch, self.value, self.parts = 1, None, {}
        self.uploads, self.fail = 0, False

    def head(self):
        return copy.deepcopy(self.value)

    def chunk(self, key):
        raw = self.parts[key]
        if hashlib.sha256(raw).hexdigest() != key:
            raise StateError("state_chunk_integrity")
        return raw

    def put_chunk(self, key, raw):
        self.parts[key] = raw
        self.uploads += 1

    def commit(self, sequence, files):
        if self.fail:
            raise StateError("fixture_store_failed")
        if sequence != (self.value or {}).get("sequence", 0) + 1:
            raise StateError("state_sequence_changed")
        self.value = copy.deepcopy(
            {
                "schemaVersion": 1,
                "epoch": self.epoch,
                "sequence": sequence,
                "files": files,
            }
        )
        return self.value


class StateTests(unittest.TestCase):
    def test_restore_uses_state_filesystem_under_cross_device_rename_fault(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            source = Checkpoint(Path(temp) / "source", remote)
            (source.root / "data").mkdir()
            (source.root / "data/ZEC_1m.csv").write_bytes(b"verified remote bytes")
            source.save()
            restored = Checkpoint(Path(temp) / "restored", remote)
            original_replace = os.replace

            def separate_temporary_filesystem(source_path, destination):
                # Portable EXDEV fault model: an unrelated system-temp mount
                # cannot atomically rename into the state filesystem.
                if not Path(source_path).is_relative_to(restored.root):
                    raise OSError(errno.EXDEV, "controlled cross-device rename fault")
                return original_replace(source_path, destination)

            with mock.patch(
                "website.engine.state.os.replace",
                side_effect=separate_temporary_filesystem,
            ):
                self.assertTrue(restored.restore())
            self.assertEqual(
                (restored.root / "data/ZEC_1m.csv").read_bytes(),
                b"verified remote bytes",
            )
            self.assertFalse(
                any(
                    path.name.startswith("oraclebot-restore-")
                    for path in restored.root.iterdir()
                )
            )

    def test_multichunk_restore_keeps_order_and_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            source = Checkpoint(Path(temp) / "source", remote)
            (source.root / "data").mkdir()
            raw = b"a" * CHUNK_BYTES + b"b" * CHUNK_BYTES + b"tail"
            (source.root / "data/ZEC_1m.csv").write_bytes(raw)
            source.save()
            restored = Checkpoint(Path(temp) / "restored", remote)
            restored.restore()
            self.assertEqual((restored.root / "data/ZEC_1m.csv").read_bytes(), raw)

    def test_round_trip_reuses_chunks_and_removes_unpublished_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "original"
            remote = MemoryState()
            checkpoint = Checkpoint(root, remote)
            self.assertFalse(checkpoint.restore())
            (root / "data").mkdir()
            (root / "data/SOL_1m.csv").write_bytes(b"public fixture")
            checkpoint.save()
            uploads = remote.uploads
            checkpoint.save()
            self.assertEqual(remote.uploads, uploads)
            restored = Path(temp) / "restored"
            (restored / "data").mkdir(parents=True)
            (restored / "data/BTC_1m.csv").write_bytes(b"unpublished future")
            remote.epoch = 2
            recovered = Checkpoint(restored, remote)
            self.assertTrue(recovered.restore())
            self.assertEqual(
                (restored / "data/SOL_1m.csv").read_bytes(), b"public fixture"
            )
            self.assertFalse((restored / "data/BTC_1m.csv").exists())
            recovered.save()
            self.assertEqual(remote.value["epoch"], 2)
            self.assertEqual(remote.value["sequence"], 3)

    def test_sqlite_backup_captures_committed_wal_without_pending_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            checkpoint = Checkpoint(Path(temp) / "source", remote)
            db = sqlite3.connect(checkpoint.root / "jobs.sqlite3")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE sample(value)")
            db.execute("INSERT INTO sample VALUES(1)")
            db.commit()
            db.execute("INSERT INTO sample VALUES(2)")
            checkpoint.save()
            db.rollback()
            db.close()
            restored = Checkpoint(Path(temp) / "destination", remote)
            restored.restore()
            with closing(sqlite3.connect(restored.root / "jobs.sqlite3")) as saved:
                self.assertEqual(
                    saved.execute("SELECT value FROM sample").fetchall(), [(1,)]
                )
            self.assertFalse(
                any(name.endswith(("-wal", "-shm")) for name in remote.value["files"])
            )

    def test_corrupt_checkpoint_never_replaces_live_files(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            source = Checkpoint(Path(temp) / "source", remote)
            (source.root / "data").mkdir()
            (source.root / "data/SOL_1m.csv").write_bytes(b"committed")
            source.save()
            remote.parts[next(iter(remote.parts))] = b"corrupt"
            target = Checkpoint(Path(temp) / "target", remote)
            (target.root / "data").mkdir()
            marker = target.root / "data/SOL_1m.csv"
            marker.write_bytes(b"previous")
            with self.assertRaises(StateError):
                target.restore()
            self.assertEqual(marker.read_bytes(), b"previous")

    def test_failed_commit_does_not_advance_checkpoint_head(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            checkpoint = Checkpoint(Path(temp), remote)
            checkpoint.save()
            before = remote.head()
            remote.fail = True
            with self.assertRaises(StateError):
                checkpoint.save()
            self.assertEqual(checkpoint.sequence, 1)
            self.assertEqual(remote.head(), before)

    def test_paths_symlinks_and_future_epochs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            remote = MemoryState()
            checkpoint = Checkpoint(Path(temp), remote)
            remote.value = {"schemaVersion": 1, "epoch": 2, "sequence": 1, "files": {}}
            with self.assertRaisesRegex(StateError, "epoch"):
                checkpoint.restore()
            for path in ("../secret", "data/../../secret", "oracle/SOL/private.key"):
                manifest = {
                    "schemaVersion": 1,
                    "epoch": 1,
                    "sequence": 1,
                    "files": {path: {"bytes": 0, "sha256": "a" * 64, "chunks": []}},
                }
                with self.assertRaises(StateError):
                    validate_manifest(manifest)
            (checkpoint.root / "data").symlink_to(Path(temp).parent)
            with self.assertRaisesRegex(StateError, "symlink"):
                checkpoint.restore()


class HTTPSStateTests(unittest.TestCase):
    """Actual TLS/client serialization against an explicitly controlled stand-in."""

    def setUp(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = dt.datetime.now(dt.UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=1))
            .not_valid_after(now + dt.timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
            )
            .sign(key, hashes.SHA256())
        )
        certificate, secret = self.root / "cert.pem", self.root / "key.pem"
        certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        secret.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        secret.chmod(0o600)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, secret)
        state = self.state = MemoryState()
        requests = self.requests = []
        agents = self.agents = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, code, body):
                raw = body if isinstance(body, bytes) else canonical(body)
                self.send_response(code)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                agents.append(self.headers.get("User-Agent"))
                if (
                    owner.require_agent
                    and self.headers.get("User-Agent")
                    != "oraclebot-analysis-runtime/1.0"
                ):
                    return self.answer(403, b"error code: 1010")
                requests.append(
                    (self.command, self.path, self.headers.get("X-Runtime-Epoch"))
                )
                if self.headers.get("Authorization") != "Bearer " + "x" * 32:
                    return self.answer(401, {})
                if owner.redirect:
                    self.send_response(302)
                    self.send_header(
                        "Location", "https://external.invalid/must-not-receive-token"
                    )
                    self.end_headers()
                    return
                if self.path.endswith("/manifest"):
                    return (
                        self.answer(404, {})
                        if state.value is None
                        else self.answer(200, state.value)
                    )
                return self.answer(200, state.parts[self.path.rsplit("/", 1)[-1]])

            def do_PUT(self):
                agents.append(self.headers.get("User-Agent"))
                if (
                    owner.require_agent
                    and self.headers.get("User-Agent")
                    != "oraclebot-analysis-runtime/1.0"
                ):
                    return self.answer(403, b"error code: 1010")
                requests.append(
                    (self.command, self.path, self.headers.get("X-Runtime-Epoch"))
                )
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path.endswith("/manifest"):
                    value = json.loads(raw)
                    state.value = value
                    return self.answer(
                        200,
                        {
                            "sequence": value["sequence"],
                            "epoch": value["epoch"],
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        },
                    )
                state.parts[self.path.rsplit("/", 1)[-1]] = raw
                return self.answer(200, {})

        self.redirect = False
        self.require_agent = False
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client_context = ssl.create_default_context(cafile=str(certificate))
        self.origin = f"https://localhost:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def test_actual_https_checkpoint_and_restore(self):
        remote = RemoteState(self.origin, "x" * 32, 1, tls_context=self.client_context)
        local = Checkpoint(self.root / "local", remote)
        self.assertFalse(local.restore())
        (local.root / "data").mkdir()
        (local.root / "data/ZEC_1m.csv").write_bytes(b"explicit fixture bytes")
        local.save()
        restored = Checkpoint(self.root / "restored", remote)
        self.assertTrue(restored.restore())
        self.assertEqual(
            (restored.root / "data/ZEC_1m.csv").read_bytes(), b"explicit fixture bytes"
        )
        self.assertTrue(
            any(
                method == "PUT" and "/chunks/" in path
                for method, path, _ in self.requests
            )
        )
        self.assertTrue(all(epoch == "1" for _, _, epoch in self.requests))

    def test_redirect_and_wrong_authority_refuse(self):
        client = RemoteState(
            self.origin, "wrong" * 8, 1, tls_context=self.client_context
        )
        with self.assertRaises(StateError):
            client.head()
        self.redirect = True
        client = RemoteState(self.origin, "x" * 32, 1, tls_context=self.client_context)
        with self.assertRaises(StateError):
            client.head()
        self.assertTrue(
            all(path == "/internal/state/manifest" for _, path, _ in self.requests)
        )

    def test_truthful_product_user_agent_survives_actual_https_browser_integrity_gate(
        self,
    ):
        self.require_agent = True
        request = Request(
            self.origin + "/internal/state/manifest",
            headers={"Authorization": "Bearer " + "x" * 32},
        )
        with self.assertRaises(HTTPError) as refused:
            urlopen(request, context=self.client_context, timeout=5)
        self.assertEqual(refused.exception.code, 403)
        self.assertEqual(refused.exception.read(), b"error code: 1010")
        self.assertTrue(self.agents[0].startswith("Python-urllib/"))
        remote = RemoteState(self.origin, "x" * 32, 1, tls_context=self.client_context)
        checkpoint = Checkpoint(self.root / "with_product_agent", remote)
        self.assertFalse(checkpoint.restore())
        (checkpoint.root / "data").mkdir()
        (checkpoint.root / "data/ZEC_1m.csv").write_bytes(
            b"explicit integrity-gate fixture"
        )
        checkpoint.save()
        restored = Checkpoint(self.root / "product_agent_restored", remote)
        self.assertTrue(restored.restore())
        self.assertEqual(
            (restored.root / "data/ZEC_1m.csv").read_bytes(),
            b"explicit integrity-gate fixture",
        )
        self.assertTrue(
            all(agent == "oraclebot-analysis-runtime/1.0" for agent in self.agents[1:])
        )
