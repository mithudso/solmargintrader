"""Lossless storage and integrity checks for the offline keyword index."""

import gzip
import hashlib
import io
import json
import zlib
from pathlib import Path


def write(path: Path, text: dict) -> str:
    raw = (json.dumps(text, separators=(",", ":"), sort_keys=True) + "\n").encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(raw)
    path.write_bytes(buffer.getvalue())
    digest = hashlib.sha256(raw).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(digest + "\n")
    return digest


def read(path: Path, expected_sha256: str | None = None) -> dict:
    digest = path.with_suffix(path.suffix + ".sha256")
    try:
        raw = gzip.decompress(path.read_bytes())
        expected = digest.read_text().strip()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected or (expected_sha256 is not None and actual != expected_sha256):
            raise ValueError("decoded text index checksum mismatch")
        return json.loads(raw)
    except (OSError, EOFError, ValueError, zlib.error) as exc:
        raise ValueError(f"text index missing or corrupt: {exc}") from exc
