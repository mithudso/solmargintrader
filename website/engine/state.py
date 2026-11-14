"""Integrity-checked, epoch-fenced public-analysis checkpoints.

The remote head is the commit point. Local SQLite is backed up before chunking;
no WAL file, authentication secret or operator directory enters a checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

CHUNK_BYTES = 512 * 1024
MAX_STATE_BYTES = 8 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
SHA = re.compile(r"[a-f0-9]{64}\Z")
PATH = re.compile(
    r"(?:jobs\.sqlite3|oracle/(?:SOL|BTC|ETH|ZEC)/history\.sqlite3|data/(?:SOL|BTC|ETH|ZEC)_(?:1m|5m|15m|1h|6h|1d)\.(?:csv|json)|inputs/[a-f0-9]{64}/(?:SOL|BTC|ETH|ZEC)_(?:1m|5m|15m|1h|6h|1d)\.(?:csv|json)|bootstrap/(?:SOL|BTC|ETH|ZEC)\.json)\Z"
)


class StateError(RuntimeError):
    """Symbolic state failure; readiness must remain withheld."""


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class RemoteState:
    def __init__(self, origin, token, epoch, *, transport=None, tls_context=None):
        from urllib.parse import urlsplit

        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise StateError("invalid_state_origin")
        if (
            not isinstance(token, str)
            or len(token) < 32
            or type(epoch) is not int
            or epoch < 1
        ):
            raise StateError("invalid_state_authority")
        self.origin, self.token, self.epoch = origin.rstrip("/"), token, epoch
        self.transport = transport
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=tls_context))

    def _request(self, method, path, body=None, limit=MAX_MANIFEST_BYTES):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Runtime-Epoch": str(self.epoch),
            "User-Agent": "oraclebot-analysis-runtime/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/octet-stream"
        if self.transport:
            return self.transport(method, path, body, headers)
        try:
            request = Request(self.origin + path, body, headers, method=method)
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(limit + 1)
            if len(raw) > limit:
                raise StateError("state_response_too_large")
            return raw
        except HTTPError as error:
            if (
                error.code == 404
                and method == "GET"
                and path == "/internal/state/manifest"
            ):
                return None
            raise StateError(
                "state_authority_refused" if error.code == 409 else "state_unavailable"
            ) from None
        except StateError:
            raise
        except Exception:  # noqa: BLE001 - the public state boundary never exposes URLs or bearer values.
            raise StateError("state_unavailable") from None

    def head(self):
        raw = self._request("GET", "/internal/state/manifest")
        return None if raw is None else json.loads(raw)

    def chunk(self, digest):
        raw = self._request(
            "GET", "/internal/state/chunks/" + digest, limit=CHUNK_BYTES
        )
        if not isinstance(raw, bytes) or sha(raw) != digest or len(raw) > CHUNK_BYTES:
            raise StateError("state_chunk_integrity")
        return raw

    def put_chunk(self, digest, raw):
        if sha(raw) != digest or len(raw) > CHUNK_BYTES:
            raise StateError("state_chunk_integrity")
        self._request("PUT", "/internal/state/chunks/" + digest, raw)

    def commit(self, sequence, files):
        manifest = {
            "schemaVersion": 1,
            "epoch": self.epoch,
            "sequence": sequence,
            "files": files,
        }
        raw = canonical(manifest)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise StateError("state_manifest_too_large")
        result = self._request("PUT", "/internal/state/manifest", raw)
        receipt = json.loads(result)
        if receipt != {"sequence": sequence, "sha256": sha(raw), "epoch": self.epoch}:
            raise StateError("state_commit_unverified")
        return manifest


def validate_manifest(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schemaVersion", "epoch", "sequence", "files"}
        or value["schemaVersion"] != 1
    ):
        raise StateError("invalid_state_manifest")
    if any(
        type(value[k]) is not int or value[k] < 1 for k in ("epoch", "sequence")
    ) or not isinstance(value["files"], dict):
        raise StateError("invalid_state_manifest")
    total = 0
    for name, item in value["files"].items():
        if (
            not PATH.fullmatch(name)
            or not isinstance(item, dict)
            or set(item) != {"bytes", "sha256", "chunks"}
        ):
            raise StateError("invalid_state_path")
        size, chunks = item["bytes"], item["chunks"]
        if (
            type(size) is not int
            or size < 0
            or not isinstance(item["sha256"], str)
            or not SHA.fullmatch(item["sha256"])
            or not isinstance(chunks, list)
            or len(chunks) != (size + CHUNK_BYTES - 1) // CHUNK_BYTES
            or any(not isinstance(d, str) or not SHA.fullmatch(d) for d in chunks)
        ):
            raise StateError("invalid_state_file")
        total += size
    if total > MAX_STATE_BYTES:
        raise StateError("state_capacity_exceeded")
    return value


class Checkpoint:
    def __init__(self, root: Path, remote):
        self.root, self.remote = Path(root), remote
        self.sequence, self.known_chunks = 0, set()
        if self.root.is_symlink():
            raise StateError("state_symlink_refused")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def restore(self):
        if any(p.is_symlink() for p in self.root.rglob("*")):
            raise StateError("state_symlink_refused")
        head = self.remote.head()
        if head is None:
            if any(p.is_file() for p in self.root.rglob("*")):
                raise StateError("unowned_local_state_refused")
            return False
        validate_manifest(head)
        if head["epoch"] > self.remote.epoch:
            raise StateError("state_epoch_mismatch")
        # Verified files must share the destination filesystem so publication
        # remains atomic even when /tmp and the state root are separate mounts.
        with tempfile.TemporaryDirectory(
            prefix="oraclebot-restore-", dir=self.root
        ) as temp:
            staging = Path(temp)
            for name, item in head["files"].items():
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                digest, size = hashlib.sha256(), 0
                with (
                    path.open("xb") as handle,
                    ThreadPoolExecutor(max_workers=8) as pool,
                ):
                    for offset in range(0, len(item["chunks"]), 8):
                        # Prefetch stays bounded; never buffer the full archive.
                        pending = [
                            pool.submit(self.remote.chunk, chunk)
                            for chunk in item["chunks"][offset : offset + 8]
                        ]
                        for future in pending:
                            raw = future.result()
                            handle.write(raw)
                            digest.update(raw)
                            size += len(raw)
                if size != item["bytes"] or digest.hexdigest() != item["sha256"]:
                    raise StateError("state_file_integrity")
                if name.endswith(".sqlite3"):
                    with closing(
                        sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                    ) as db:
                        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            raise StateError("state_database_integrity")
            # All bytes validate before any live path is replaced.
            for existing in self.root.rglob("*"):
                name = existing.relative_to(self.root).as_posix()
                if (
                    existing.is_file()
                    and PATH.fullmatch(name)
                    and name not in head["files"]
                ):
                    existing.unlink()
            databases = {p for p in self.root.rglob("*.sqlite3")} | {
                self.root / p for p in head["files"] if p.endswith(".sqlite3")
            }
            for database in databases:
                for suffix in ("-wal", "-shm"):
                    Path(str(database) + suffix).unlink(missing_ok=True)
            for name in head["files"]:
                destination = self.root / name
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if destination.is_symlink():
                    raise StateError("state_symlink_refused")
                os.replace(staging / name, destination)
                destination.chmod(0o600)
        self.sequence = head["sequence"]
        self.known_chunks = {
            d for item in head["files"].values() for d in item["chunks"]
        }
        return True

    def save(self):
        files, total, uploaded = {}, 0, set(self.known_chunks)
        with tempfile.TemporaryDirectory(prefix="oraclebot-checkpoint-") as temp:
            for path in sorted(self.root.rglob("*")):
                if path.is_symlink():
                    raise StateError("state_symlink_refused")
                if not path.is_file() or not PATH.fullmatch(
                    path.relative_to(self.root).as_posix()
                ):
                    continue
                name = path.relative_to(self.root).as_posix()
                source = path
                if name.endswith(".sqlite3"):
                    source = Path(temp) / (str(len(files)) + ".sqlite3")
                    with (
                        closing(
                            sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                        ) as db,
                        closing(sqlite3.connect(source)) as backup,
                    ):
                        db.backup(backup)
                size = source.stat().st_size
                total += size
                if total > MAX_STATE_BYTES:
                    raise StateError("state_capacity_exceeded")
                digest, chunks = hashlib.sha256(), []
                with source.open("rb") as handle:
                    while raw := handle.read(CHUNK_BYTES):
                        key = sha(raw)
                        if key not in uploaded:
                            self.remote.put_chunk(key, raw)
                            uploaded.add(key)
                        chunks.append(key)
                        digest.update(raw)
                files[name] = {
                    "bytes": size,
                    "sha256": digest.hexdigest(),
                    "chunks": chunks,
                }
            manifest = self.remote.commit(self.sequence + 1, files)
        self.sequence = manifest["sequence"]
        self.known_chunks = {d for item in files.values() for d in item["chunks"]}
        return self.sequence
