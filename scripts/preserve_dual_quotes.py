#!/usr/bin/env python3
"""Retain closed-hour normalized quotes without touching the live collector."""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import tempfile
import threading
import time
from pathlib import Path

SOURCE = Path("/Users/mitch/.local/state/oracle-leverage/dual-quotes")
DEST = Path("/Users/mitch/.local/state/oracle-exit50-2309/retained-dual-quotes")
PATTERN = re.compile(r"^dual-quotes-(\d{8}T\d{2})-[0-9a-f]+\.jsonl\.gz$")
CAP = 2 * 1024**3
MIN_FREE = 20 * 1024**3


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, obj):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".status-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def retain(source, dest, now, cap=CAP, min_free=MIN_FREE):
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    retained = sum(p.stat().st_size for p in dest.glob("dual-quotes-*.jsonl.gz"))
    copied = 0
    for src in sorted(source.iterdir()):
        match = PATTERN.fullmatch(src.name)
        if not match or not src.is_file():
            continue
        hour = dt.datetime.strptime(match.group(1), "%Y%m%dT%H").replace(tzinfo=dt.UTC)
        if hour + dt.timedelta(hours=1) > now:
            continue
        with gzip.open(src, "rb") as stream:
            while stream.read(1024 * 1024):
                pass
        before = src.stat()
        source_hash = sha(src)
        target = dest / src.name
        if target.exists():
            if target.stat().st_size != before.st_size or sha(target) != source_hash:
                raise RuntimeError(f"immutable destination conflict: {target}")
        else:
            if (
                retained + before.st_size > cap
                or shutil.disk_usage(dest).free - before.st_size < min_free
            ):
                raise RuntimeError("retention byte cap or minimum free disk reached")
            fd, name = tempfile.mkstemp(dir=dest, prefix=".copy-")
            try:
                with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
                    shutil.copyfileobj(inp, out)
                    out.flush()
                    os.fsync(out.fileno())
                tmp = Path(name)
                if (
                    tmp.stat().st_size != before.st_size
                    or sha(tmp) != source_hash
                    or sha(src) != source_hash
                ):
                    raise RuntimeError(f"source changed or copy mismatch: {src}")
                os.link(tmp, target)  # Fails rather than overwriting a concurrent copy.
                retained += before.st_size
                copied += 1
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        receipt = dest / (src.name + ".receipt.json")
        data = {
            "name": src.name,
            "bytes": before.st_size,
            "sha256": source_hash,
            "source": str(src),
            "utc_hour": match.group(1),
            "qualification": "normalized Jupiter Oracle and Coinbase quotes; not raw wire or full order book",
        }
        if receipt.exists():
            if json.loads(receipt.read_text()) != data:
                raise RuntimeError(f"immutable receipt conflict: {receipt}")
        else:
            fd, name = tempfile.mkstemp(dir=dest, prefix=".receipt-")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, sort_keys=True)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.link(name, receipt)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
    return {"files_copied": copied, "retained_bytes": retained}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()
    if not 0 < args.hours <= 24 or not 1 <= args.interval <= 3600:
        parser.error("hours must be in (0,24], interval in [1,3600]")
    args.dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    status = args.dest / "preserver-status.json"
    deadline_file = args.dest / "preserver-deadline.json"
    if deadline_file.exists():
        deadline = json.loads(deadline_file.read_text())["deadline"]
    else:
        deadline = time.time() + args.hours * 3600
        atomic_json(deadline_file, {"deadline": deadline})
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while time.time() < deadline and not stop.is_set():
            result = retain(args.source, args.dest, dt.datetime.now(dt.UTC))
            atomic_json(
                status,
                {
                    "state": "running",
                    "heartbeat_utc": dt.datetime.now(dt.UTC).isoformat(),
                    "deadline": deadline,
                    **result,
                },
            )
            stop.wait(min(args.interval, max(0, deadline - time.time())))
        atomic_json(
            status,
            {
                "state": "stopped" if stop.is_set() else "complete",
                "heartbeat_utc": dt.datetime.now(dt.UTC).isoformat(),
                "deadline": deadline,
            },
        )
    except (OSError, ValueError, RuntimeError, EOFError) as exc:
        atomic_json(
            status,
            {
                "state": "stopped",
                "error": str(exc),
                "heartbeat_utc": dt.datetime.now(dt.UTC).isoformat(),
                "deadline": deadline,
            },
        )
        raise


if __name__ == "__main__":
    main()
