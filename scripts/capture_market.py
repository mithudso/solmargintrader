"""Bounded public market-event capture with durable spool and separate Mongo upload.

No orders, private market subscriptions, sampling, or drop/rebuild operations.
The capture and upload roles have separate locks and independent lifecycles.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import signal
import sys
import tempfile
import time
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from soltui.pricefeed import WebSocket

VERSION = "1.0.1"
DATABASE = "market_capture"
CHANNELS = ["matches", "level2_batch", "heartbeat"]
SUBSCRIPTION_ACK_TIMEOUT_S = 10.0


class CaptureError(RuntimeError):
    """A local contract failure; raw driver exceptions must not reach logs."""


def utc(seconds=None):
    return datetime.fromtimestamp(time.time() if seconds is None else seconds,
                                  UTC).isoformat()


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".capture-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {} if default is None else default


@contextmanager
def lock(path):
    with Path(path).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CaptureError("another owner holds this role/product lock") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def prepare(home, product, duration, dotenv, certificate, uri_env="MONGODB_URI2"):
    if not re.fullmatch(r"[A-Z0-9]+-USD", product):
        raise CaptureError("product must be a Coinbase USD product")
    if not math.isfinite(duration) or duration <= 0:
        raise CaptureError("duration must be positive and finite")
    if uri_env not in {"MONGODB_URI", "MONGODB_URI2"}:
        raise CaptureError("unsupported URI environment variable")
    home = Path(home)
    home.mkdir(parents=True, exist_ok=False)
    home.chmod(0o700)
    now = time.time()
    cfg = {"version": VERSION, "run_id": uuid.uuid4().hex, "product": product,
           "venue": "coinbase_exchange", "channels": CHANNELS,
           "start_epoch": now, "deadline_epoch": now + duration,
           "start_utc": utc(now), "deadline_utc": utc(now + duration),
           "dotenv": str(Path(dotenv).expanduser().resolve()),
           "certificate": str(Path(certificate).expanduser().resolve()),
           "uri_env": uri_env, "database": DATABASE,
           "collection": "events_" + product.lower().replace("-", "_") + "_" + uuid.uuid4().hex,
           "coverage": "all received application messages; public book batches are50ms"}
    atomic_json(home / "config.json", cfg)
    return cfg


def config(home):
    cfg = read_json(Path(home) / "config.json")
    if cfg.get("database") != DATABASE or not re.fullmatch(r"events_[a-z0-9_]+", cfg.get("collection", "")):
        raise CaptureError("invalid dedicated capture namespace")
    if cfg.get("uri_env") not in {"MONGODB_URI", "MONGODB_URI2"}:
        raise CaptureError("unsupported URI variable")
    if not cfg.get("run_id") or not math.isfinite(cfg["deadline_epoch"]):
        raise CaptureError("invalid run configuration")
    return cfg


def repair_tail(path):
    """Retain every complete WAL line; remove only an interrupted final write."""
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r+b") as handle:
        size = handle.seek(0, os.SEEK_END)
        handle.seek(size - 1)
        if handle.read(1) == b"\n":
            return 0
        position = size
        while position:
            start = max(0, position - 65536)
            handle.seek(start)
            chunk = handle.read(position - start)
            index = chunk.rfind(b"\n")
            if index >= 0:
                position = start + index + 1
                break
            position = start
        handle.truncate(position)
        handle.flush()
        os.fsync(handle.fileno())
        return size - position


def last_record(path):
    if not path.exists() or not path.stat().st_size:
        return {}
    with path.open("rb") as handle:
        end = handle.seek(0, os.SEEK_END)
        start = end
        while start:
            start = max(0, start - 65536)
            handle.seek(start)
            raw = handle.read(end - start)
            lines = raw.splitlines()
            if len(lines) >= 2 or start == 0:
                return json.loads(lines[-1])
    return {}


class Spool:
    def __init__(self, home, cfg):
        self.home, self.cfg = Path(home), cfg
        path = self.home / "events.jsonl"
        self.repaired_bytes = repair_tail(path)
        last = last_record(path)
        self.sequence = last.get("seq", 0)
        if last and last.get("run_id") != cfg["run_id"]:
            raise CaptureError("spool belongs to a different run")
        self.handle = path.open("a", encoding="utf-8")
        self.types = Counter()

    def append(self, raw, connection_id, *, control=None):
        self.sequence += 1
        ns = time.time_ns()
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        event_type = control or payload.get("type", "unparsed")
        if not isinstance(event_type, str) or not event_type:
            event_type = "unparsed"
        event_type = event_type[:128]
        row = {"run_id": self.cfg["run_id"], "seq": self.sequence,
               "received_ns": ns, "received_utc": utc(ns / 1e9),
               "connection_id": connection_id, "type": event_type,
               "exchange_time_raw": payload.get("time"), "exchange_sequence": payload.get("sequence"),
               "trade_id": payload.get("trade_id"), "raw": raw}
        self.handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
        self.handle.flush()
        # This finite single-product capture favors durable events over write throughput.
        os.fsync(self.handle.fileno())
        self.types[row["type"]] += 1
        return row

    def close(self):
        self.handle.close()


def capture(home, *, ws_factory=WebSocket):
    home = Path(home)
    cfg = config(home)
    stopping = [False]
    old_handlers = {}
    for sig in (signal.SIGTERM, signal.SIGINT):
        old_handlers[sig] = signal.signal(sig, lambda *_: stopping.__setitem__(0, True))
    product_lock = home.parent / (cfg["product"].lower() + ".capture.lock")
    try:
        with lock(product_lock), lock(home / "capture.lock"):
            spool = Spool(home, cfg)
            reconnects = 0
            acknowledged_connections = 0
            unacknowledged_connections = 0
            subscribed = False
            last_status = 0.0
            def status(state, error=None):
                atomic_json(home / "capture-status.json", {
                    "state": state, "product": cfg["product"], "run_id": cfg["run_id"],
                    "deadline_utc": cfg["deadline_utc"], "deadline_epoch": cfg["deadline_epoch"],
                    "records": spool.sequence, "types_this_process": dict(spool.types),
                    "reconnects_this_process": reconnects, "last_error_type": error,
                    "subscription_confirmed": subscribed, "requested_channels": cfg["channels"],
                    "acknowledged_connections": acknowledged_connections,
                    "unacknowledged_connections": unacknowledged_connections,
                    "tail_bytes_repaired": spool.repaired_bytes, "updated_utc": utc(),
                    "pid": os.getpid()})
            try:
                while time.time() < cfg["deadline_epoch"] and not stopping[0]:
                    if (home / "stop-requested").exists():
                        break
                    connection = uuid.uuid4().hex
                    subscribed = False
                    ws = ws_factory()
                    try:
                        status("connecting")
                        ws.open()
                        ws.settimeout(1.0)
                        spool.append(json.dumps({"type": "connection_open"}), connection, control="connection_open")
                        ws.send_text(json.dumps({"type": "subscribe", "product_ids": [cfg["product"]],
                                                 "channels": cfg["channels"]}))
                        last_message = time.monotonic()
                        ack_deadline = last_message + SUBSCRIPTION_ACK_TIMEOUT_S
                        trade_high_water = None
                        while time.time() < cfg["deadline_epoch"] and not stopping[0]:
                            if (home / "stop-requested").exists():
                                break
                            if not subscribed and time.monotonic() >= ack_deadline:
                                raise CaptureError("subscription acknowledgement deadline exceeded")
                            try:
                                raw = ws.recv_text()
                            except TimeoutError:
                                if time.monotonic() - last_message > 15:
                                    raise CaptureError("feed idle")
                                continue
                            last_message = time.monotonic()
                            if time.time() >= cfg["deadline_epoch"]:
                                break
                            row = spool.append(raw, connection)
                            if row["type"] in {"match", "last_match"} and isinstance(row["trade_id"], int):
                                trade_id = row["trade_id"]
                                if trade_high_water is not None and trade_id > trade_high_water + 1:
                                    spool.append(json.dumps({"type": "trade_gap_candidate",
                                        "first_trade_id": trade_high_water + 1, "last_trade_id": trade_id - 1,
                                        "qualification": "observed ID jump; late delivery/backfill not resolved"}),
                                        connection, control="trade_gap_candidate")
                                trade_high_water = max(trade_id, trade_high_water or trade_id)
                            if row["type"] == "subscriptions":
                                ack = json.loads(raw)
                                channels = ack.get("channels")
                                if not isinstance(channels, list) or not all(
                                    isinstance(x, dict) and isinstance(x.get("name"), str)
                                    and isinstance(x.get("product_ids"), list) for x in channels
                                ):
                                    raise CaptureError("invalid subscription acknowledgement")
                                names = {"level2_batch" if x["name"] == "level2_50" else x["name"]
                                         for x in channels
                                         if cfg["product"] in x.get("product_ids", [])}
                                was_subscribed = subscribed
                                subscribed = set(cfg["channels"]).issubset(names)
                                if not subscribed:
                                    raise CaptureError("subscription coverage mismatch")
                                if not was_subscribed:
                                    acknowledged_connections += 1
                            if row["type"] == "error":
                                raise CaptureError("feed rejected subscription")
                            if time.monotonic() - last_status >= 1:
                                status("recording" if subscribed else "awaiting_subscription")
                                last_status = time.monotonic()
                    except (OSError, ValueError, RuntimeError) as error:
                        reconnects += 1
                        spool.append(json.dumps({"type": "connection_gap", "error_type": type(error).__name__}),
                                     connection, control="connection_gap")
                        status("reconnecting", type(error).__name__)
                        remaining = cfg["deadline_epoch"] - time.time()
                        if remaining > 0 and not stopping[0]:
                            time.sleep(min(2.0, remaining))
                    finally:
                        if not subscribed:
                            unacknowledged_connections += 1
                        ws.close()
                coverage_complete = acknowledged_connections > 0 and unacknowledged_connections == 0
                state = ("completed" if coverage_complete else "incomplete") if time.time() >= cfg["deadline_epoch"] else "stopped_early" if (home / "stop-requested").exists() else "interrupted"
                status(state)
                return 1 if state in {"interrupted", "incomplete"} else 0
            finally:
                spool.close()
    finally:
        for sig, previous in old_handlers.items():
            signal.signal(sig, previous)


def read_batch(path, offset, maximum=200):
    if not path.exists():
        return [], offset
    rows = []
    with path.open("rb") as handle:
        handle.seek(offset)
        while len(rows) < maximum:
            raw = handle.readline()
            if not raw or not raw.endswith(b"\n"):
                break
            rows.append(json.loads(raw))
            offset = handle.tell()
    return rows, offset


def mongo_document(row, cfg):
    if row["run_id"] != cfg["run_id"]:
        raise CaptureError("wrong run in upload spool")
    result = dict(row)
    raw = result.pop("raw")
    try:
        result["payload"] = json.loads(raw)
    except ValueError:
        result["raw_unparsed"] = raw
    result["received_at"] = datetime.fromtimestamp(row["received_ns"] // 1_000_000 / 1000,
                                                    UTC)
    result["meta"] = {"venue": cfg["venue"], "product": cfg["product"], "run_id": cfg["run_id"]}
    return result


def normalise_uri(uri):
    # Explicit supplied client certificate replaces stale URI paths. A missing CA
    # reference falls back to system trust; certificate/hostname verification stays on.
    parts = urlsplit(uri)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() == "tlscertificatekeyfile":
            continue
        if key.lower() == "tlscafile" and not Path(value).expanduser().is_file():
            continue
        if key.lower() in {"tlsinsecure", "tlsallowinvalidcertificates", "tlsallowinvalidhostnames"} and value.lower() not in {"false", "0"}:
            raise CaptureError("insecure TLS options refused")
        query.append((key, value))
    # All data writes explicitly select DATABASE and X509 uses $external. The
    # URI default database is unused and may contain an installation placeholder.
    return urlunsplit(parts._replace(path="/", query=urlencode(query)))


def mongo_client(cfg):
    from dotenv import dotenv_values
    from pymongo import MongoClient
    uri = os.environ.get(cfg["uri_env"]) or dotenv_values(cfg["dotenv"], interpolate=False).get(cfg["uri_env"])
    if not uri:
        raise CaptureError("authorized URI variable is missing")
    uri = normalise_uri(uri)
    client = MongoClient(uri, tls=True, tlsCertificateKeyFile=cfg["certificate"],
                         authMechanism="MONGODB-X509", authSource="$external",
                         serverSelectionTimeoutMS=10000, connectTimeoutMS=5000,
                         appname="bounded-zec-event-capture", w="majority")
    try:
        client.admin.command("ping")
    except Exception:
        client.close()
        raise
    return client


def collection(client, cfg):
    db = client[cfg["database"]]
    name = cfg["collection"]
    names = db.list_collection_names(filter={"name": name})
    if name not in names:
        db.create_collection(name, timeseries={"timeField": "received_at", "metaField": "meta",
                                              "granularity": "seconds"})
    result = db[name]
    options = result.options().get("timeseries", {})
    if options.get("timeField") != "received_at" or options.get("metaField") != "meta":
        raise CaptureError("existing collection has a different layout")
    return result


def upload_once(home, sink_factory=mongo_client):
    home = Path(home)
    cfg = config(home)
    progress = read_json(home / "upload-progress.json", {"offset": 0, "records": 0})
    if progress.get("inflight"):
        raise CaptureError("ambiguous previous insert requires reconciliation")
    rows, end = read_batch(home / "events.jsonl", progress["offset"])
    if not rows:
        return progress, False
    documents = [mongo_document(row, cfg) for row in rows]
    client = sink_factory(cfg)
    try:
        target = collection(client, cfg)
        pending = dict(progress, inflight={"end_offset": end, "count": len(rows),
                                          "first_seq": rows[0]["seq"], "last_seq": rows[-1]["seq"]})
        atomic_json(home / "upload-progress.json", pending)
        # An ambiguous insert is never automatically resubmitted: TS collections
        # cannot enforce a unique event key. The raw spool remains available.
        target.insert_many(documents, ordered=True)
        progress = {"offset": end, "records": progress["records"] + len(rows)}
        atomic_json(home / "upload-progress.json", progress)
        return progress, True
    finally:
        client.close()


def upload(home):
    home = Path(home)
    cfg = config(home)
    with lock(home / "upload.lock"):
        while True:
            try:
                progress, changed = upload_once(home)
                producer = read_json(home / "capture-status.json")
                done = producer.get("state") in {"completed", "stopped_early"} and progress["records"] == producer.get("records")
                atomic_json(home / "upload-status.json", {"state": "completed" if done else "uploading",
                            "uploaded_records": progress["records"], "database": cfg["database"],
                            "collection": cfg["collection"], "updated_utc": utc(), "pid": os.getpid()})
                if done:
                    return 0
                if not changed:
                    time.sleep(1)
            except Exception as error:  # noqa: BLE001 -- preserve spool and sanitize all driver failures
                progress = read_json(home / "upload-progress.json")
                ambiguous = bool(progress.get("inflight"))
                atomic_json(home / "upload-status.json", {
                    "state": "needs_reconciliation" if ambiguous else "waiting_for_mongodb",
                    "last_error_type": type(error).__name__, "updated_utc": utc(),
                    "uploaded_records": progress.get("records", 0), "pid": os.getpid()})
                if ambiguous:
                    # Successful exit prevents launchd retry loops; producer continues.
                    return 0
                time.sleep(30)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "capture", "upload", "status"])
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--product", default="ZEC-USD")
    parser.add_argument("--duration-seconds", type=float, default=86400)
    parser.add_argument("--dotenv", type=Path, default=Path.home() / ".env")
    parser.add_argument("--certificate", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            if args.certificate is None:
                raise CaptureError("explicit X509 certificate is required")
            result = prepare(args.home, args.product, args.duration_seconds, args.dotenv, args.certificate)
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.action == "capture":
            return capture(args.home)
        if args.action == "upload":
            return upload(args.home)
        print(json.dumps({"config": config(args.home), "capture": read_json(args.home / "capture-status.json"),
                          "upload": read_json(args.home / "upload-status.json")}, sort_keys=True))
        return 0
    except Exception as error:  # noqa: BLE001 -- URI/auth details must not reach a traceback
        # Driver exceptions can contain URI/auth material. Emit only their class.
        print(json.dumps({"error_type": type(error).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
