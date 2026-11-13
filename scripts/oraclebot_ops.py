#!/usr/bin/env python3
"""Read-only Oraclebot operations observer; no trading or service repair commands.

A separate launchd job samples the existing solbot owner. SQLite preserves
incidents and delivery retries. Reports count observed samples, not uptime.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import plistlib
import re
import selectors
import shlex
import signal
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from itertools import pairwise
from pathlib import Path
from urllib.parse import urlsplit

VERSION = "1.2.0"
LABEL = "com.mitchhudson.oraclebot-operations"
COMPONENTS = ("suite", "manager", "control_room", "market_data")
STOP = threading.Event()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".new")
    with temp.open("w") as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write("\n")
    temp.chmod(0o600)
    temp.replace(path)


def database(home):
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    if home.is_symlink() or home.stat().st_uid != os.getuid():
        raise ValueError("invalid_monitor_home")
    for name in ("state.sqlite3", "owner.lock"):
        if (home / name).is_symlink():
            raise ValueError("unsafe_monitor_file")
    connection = sqlite3.connect(home / "state.sqlite3")
    (home / "state.sqlite3").chmod(0o600)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS samples(at REAL PRIMARY KEY, health TEXT);
        CREATE TABLE IF NOT EXISTS states(component TEXT PRIMARY KEY, bad INTEGER,
            episode TEXT, candidate INTEGER, consecutive INTEGER);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, payload TEXT,
            delivered INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
    """)
    return connection


def probe_output(solbot, limit=131072, timeout=15, *, arguments=None):
    """Read both child pipes under one byte/deadline budget; never buffer a flood."""
    command = arguments if arguments is not None else [str(solbot), "health-check"]
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "INDEX_NO_AUTO": "1"},
    ) as child:
        output = bytearray()
        consumed = 0
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as poller:
                for name, pipe in (("stdout", child.stdout), ("stderr", child.stderr)):
                    os.set_blocking(pipe.fileno(), False)
                    poller.register(pipe, selectors.EVENT_READ, name)
                while poller.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValueError("probe_timeout")
                    for key, _ in poller.select(min(remaining, 0.1)):
                        chunk = os.read(key.fd, min(65536, limit + 1 - consumed))
                        if not chunk:
                            poller.unregister(key.fd)
                            continue
                        consumed += len(chunk)
                        if consumed > limit:
                            raise ValueError("probe_output_limit")
                        if key.data == "stdout":
                            output.extend(chunk)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or child.wait(timeout=remaining):
                raise ValueError("probe_failed")
            return output.decode("utf-8")
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=1)


def probe(solbot):
    try:
        value = json.loads(probe_output(solbot))
        data = value.get("data")
        if value.get("ok") is not True or not isinstance(data, dict):
            raise ValueError("invalid_health")
        observed = data.get("observed_at")
        if type(observed) not in (int, float) or not -5 <= time.time() - observed <= 60:
            raise ValueError("stale_health")
        rows = data.get("components", {})
        if any(
            not isinstance(rows.get(key), dict)
            or type(rows[key].get("ready")) is not bool
            for key in COMPONENTS
        ):
            raise ValueError("invalid_components")
        return {
            "ready": data.get("ready") is True,
            "overall": data.get("overall"),
            "components": {
                key: {
                    field: rows[key].get(field)
                    for field in ("ready", "state", "reason")
                }
                for key in COMPONENTS
            },
        }
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
        AttributeError,
        OverflowError,
    ):
        return {
            "ready": False,
            "overall": "unknown",
            "components": {
                key: {"ready": False, "state": "unknown", "reason": "probe_unavailable"}
                for key in COMPONENTS
            },
        }


PIPELINE_COMPONENTS = (
    "paper_pipeline",
    "backtest_worker",
    "oracle_forecasts",
    "oracle_market_data",
)
RUNTIME_COMPONENTS = (*PIPELINE_COMPONENTS, "live_price_forecast")


def runtime_health(data, now):
    """Observe actual pipeline/worker/Oracle owners, separately from UI liveness."""
    heartbeat_at = data.get("heartbeat_at")
    fresh = type(heartbeat_at) in (int, float) and -5 <= now - heartbeat_at <= 30
    active = data.get("supervisor_running") is True and fresh
    paused = data.get("phase") == "stopped" and not data.get("supervisor_running")
    controls = data.get("runtime_controls_observed", {})
    batch = data.get("batch", {})
    oracle_rows = data.get("oracle", {})
    desired = {
        "paper_pipeline": not paused,
        "backtest_worker": not paused and controls.get("batch_enabled") is not False,
        "oracle_forecasts": not paused and controls.get("oracle_enabled") is not False,
        "oracle_market_data": not paused
        and controls.get("oracle_enabled") is not False,
    }
    observed = {
        "paper_pipeline": active,
        "backtest_worker": active
        and batch.get("running") is True
        and batch.get("phase") not in ("failed", "stopped"),
        "oracle_forecasts": active and controls.get("oracle_enabled") is True,
    }
    observed["oracle_market_data"] = (
        bool(oracle_rows)
        and active
        and all(
            isinstance(row, dict)
            and row.get("market") == "available"
            and type(row.get("received_at")) in (int, float)
            and -5 <= now - row["received_at"] <= 15
            for row in oracle_rows.values()
        )
    )
    return {
        key: {
            "ready": bool(observed[key] or not desired[key]),
            "state": "paused"
            if not desired[key]
            else "up"
            if observed[key]
            else "down",
            "reason": "operator_paused"
            if not desired[key]
            else "available"
            if observed[key]
            else key + "_unavailable",
        }
        for key in PIPELINE_COMPONENTS
    }


def probe_runtime(config, now):
    try:
        python, home = config["pipeline_python"], config["pipeline_home"]
        raw = probe_output(
            python,
            limit=524288,
            arguments=[python, "-I", "-m", "ecosystem.cli", "status", "--home", home],
        )
        value = json.loads(raw)
        if value.get("ok") is not True or not isinstance(value.get("data"), dict):
            raise ValueError("pipeline_probe_failed")
        return runtime_health(value["data"], now)
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        OverflowError,
    ):
        return {
            key: {
                "ready": False,
                "state": "unknown",
                "reason": "pipeline_probe_unavailable",
            }
            for key in PIPELINE_COMPONENTS
        }


def probe_forecast(config, now):
    """A retained forecast is visible but does not prove current evaluation."""
    try:
        python = config["forecast_python"]
        raw = probe_output(
            python,
            arguments=[
                python,
                "-I",
                "-m",
                "ecosystem.forecast",
                "--status",
                "--home",
                config["pipeline_home"],
            ],
        )
        value = json.loads(raw)
        frame = value["data"]
        selected = frame.get("selected", {})
        seconds = frame.get("settings", {}).get("seconds")
        ready = (
            value.get("ok") is True
            and frame.get("status") == "fresh"
            and type(seconds) is int
            and 5 <= seconds <= 300
            and frame.get("refresh_seconds") == seconds
            and frame.get("horizon_seconds") == seconds
            and frame.get("source_current") is True
            and frame.get("instrument") == "SOL/USD"
            and type(selected.get("direction")) is int
            and selected.get("direction") in (-1, 0, 1)
            and type(selected.get("predicted_price")) in (int, float)
            and math.isfinite(selected["predicted_price"])
            and selected["predicted_price"] > 0
            and type(frame.get("issued_at")) in (int, float)
            and -1 <= now - frame["issued_at"] <= seconds + 5
        )
        return {
            "ready": ready,
            "state": "up" if ready else "down",
            "reason": "available" if ready else "live_forecast_not_current",
        }
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        OverflowError,
    ):
        return {
            "ready": False,
            "state": "unknown",
            "reason": "live_forecast_probe_unavailable",
        }


def record(db, health, now, threshold=2):
    """Persist transition and retry key together; debounce failure AND recovery."""
    with db:
        db.execute(
            "INSERT OR REPLACE INTO samples VALUES(?,?)", (now, json.dumps(health))
        )
        for component, state in health["components"].items():
            bad = int(not state["ready"])
            row = db.execute(
                "SELECT bad,episode,candidate,consecutive FROM states WHERE component=?",
                (component,),
            ).fetchone()
            active, episode, candidate, count = row if row else (0, None, bad, 0)
            count = count + 1 if bad == candidate else 1
            if bad != active and count >= threshold:
                if bad:
                    episode = uuid.uuid4().hex
                identifier = f"{component}:{episode}:{bad}"
                payload = {
                    "key": f"oraclebot:{component}",
                    "action": "trigger" if bad else "resolve",
                    "title": f"Oraclebot {component.replace('_', ' ')} {'unavailable' if bad else 'recovered'}",
                    "body": str(state.get("reason") or "unknown")[:120],
                    "severity": "warning"
                    if component in {"market_data", "oracle_market_data"}
                    else "critical",
                }
                db.execute(
                    "INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)",
                    (identifier, json.dumps(payload)),
                )
                active = bad
            db.execute(
                "INSERT OR REPLACE INTO states VALUES(?,?,?,?,?)",
                (component, active, episode, bad, count),
            )
        db.execute("DELETE FROM samples WHERE at < ?", (now - 90 * 86400,))
        db.execute(
            "DELETE FROM outbox WHERE (delivered=1 OR EXISTS "
            "(SELECT 1 FROM metadata WHERE key='remote_superseded:' || outbox.id)) "
            "AND EXISTS (SELECT 1 FROM metadata WHERE key='notified:' || outbox.id) "
            "AND rowid NOT IN (SELECT rowid FROM outbox ORDER BY rowid DESC LIMIT 1000)"
        )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def ingest_token(path):
    """Read only a static ingest credential from the existing private env file."""
    limit = 65536
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or info.st_size > limit
    ):
        raise ValueError("private_credential_file_required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > limit
        ):
            raise ValueError("private_credential_file_required")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            content = stream.read(limit + 1)
        if len(content) > limit:
            raise ValueError("private_credential_file_required")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    for line in content.decode("utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "ALERTLANE_INGEST_TOKEN":
            values = shlex.split(value, comments=True)
            if (
                len(values) == 1
                and len(values[0]) >= 32
                and not any(c.isspace() for c in values[0])
            ):
                return values[0]
    raise ValueError("ingest_credential_unavailable")


def send_alert(url, token, identifier, payload):
    parts = urlsplit(url)
    if (
        (
            parts.scheme != "https"
            and not (parts.scheme == "http" and parts.hostname == "127.0.0.1")
        )
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError("invalid_alert_url")
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/events",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
            "Idempotency-Key": "oraclebot:" + identifier,
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=5
        ) as response:
            body = json.loads(response.read(8192))
            if (
                response.status != 202
                or not isinstance(body, dict)
                or body.get("accepted") is not True
            ):
                raise ValueError("alert_not_accepted")
    except urllib.error.HTTPError as error:
        error.close()
        raise


def notify(title, body):
    # Pass text as argv, never interpolate it into executable AppleScript.
    script = "on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv)\nend run"
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script, title, body],
            capture_output=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def deliver(db, config):
    result = {
        "pending": 0,
        "alertlane_accepted": 0,
        "alertlane_error": None,
        "notification_commands_accepted": 0,
    }
    latest_by_key = {
        json.loads(raw)["key"]: identifier
        for identifier, raw in db.execute(
            "SELECT id,payload FROM outbox ORDER BY rowid"
        )
    }
    for identifier, raw, remote_done in db.execute("""
        SELECT id,payload,delivered FROM outbox WHERE
        (delivered=0 AND NOT EXISTS
        (SELECT 1 FROM metadata WHERE key='remote_superseded:' || outbox.id))
        OR NOT EXISTS (SELECT 1 FROM metadata WHERE key='notified:' || outbox.id)
        ORDER BY delivered, rowid LIMIT 20
    """).fetchall():
        payload = json.loads(raw)
        # Local notification attempts have independent durable state to avoid
        # duplicate banners while the remote outbox retries.
        local_key = "notified:" + identifier
        if latest_by_key[payload["key"]] != identifier:
            with db:
                db.execute(
                    "INSERT OR REPLACE INTO metadata VALUES(?,?)",
                    (local_key, "superseded"),
                )
                if not remote_done:
                    db.execute(
                        "INSERT OR REPLACE INTO metadata VALUES(?,?)",
                        ("remote_superseded:" + identifier, "superseded"),
                    )
            # Never let an older component generation reopen a newer recovery.
            # Superseded is distinct from remote acceptance: delivered stays0.
            continue
        if not db.execute(
            "SELECT 1 FROM metadata WHERE key=?", (local_key,)
        ).fetchone() and notify(payload["title"], payload["body"]):
            with db:
                db.execute(
                    "INSERT OR REPLACE INTO metadata VALUES(?,?)", (local_key, "1")
                )
            result["notification_commands_accepted"] += 1
        if remote_done:
            continue
        try:
            send_alert(
                config["alertlane_url"],
                ingest_token(Path(config["alertlane_env"])),
                identifier,
                payload,
            )
        except (OSError, ValueError) as error:
            result["alertlane_error"] = (
                f"http_{error.code}"
                if isinstance(error, urllib.error.HTTPError)
                else "delivery_unavailable"
            )
            continue
        with db:
            db.execute("UPDATE outbox SET delivered=1 WHERE id=?", (identifier,))
        result["alertlane_accepted"] += 1
    result["alertlane_pending"] = db.execute(
        "SELECT count(*) FROM outbox WHERE delivered=0 AND NOT EXISTS "
        "(SELECT 1 FROM metadata WHERE key='remote_superseded:' || outbox.id)"
    ).fetchone()[0]
    result["notification_pending"] = db.execute("""
        SELECT count(*) FROM outbox WHERE NOT EXISTS
        (SELECT 1 FROM metadata WHERE key='notified:' || outbox.id)
    """).fetchone()[0]
    result["pending"] = result["alertlane_pending"] + result["notification_pending"]
    return result


def heartbeat(config, health, now):
    """Publish availability only; GitHub credentials stay in gh's own store."""
    value = {
        "at": now,
        "ready": health["ready"],
        "overall": health["overall"],
        "version": VERSION,
    }
    repo = config["github_repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return False
    payload = json.dumps({"name": "ORACLEBOT_HEARTBEAT", "value": json.dumps(value)})
    endpoint = f"repos/{repo}/actions/variables/ORACLEBOT_HEARTBEAT"
    try:
        result = subprocess.run(
            [config["gh"], "api", "--method", "PATCH", endpoint, "--input", "-"],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        if result.returncode and "HTTP 404" in result.stderr:
            result = subprocess.run(
                [
                    config["gh"],
                    "api",
                    "--method",
                    "POST",
                    f"repos/{repo}/actions/variables",
                    "--input",
                    "-",
                ],
                input=payload,
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def reports(db, home, health, delivery, now):
    local = dt.datetime.fromtimestamp(now).astimezone()
    midnight = dt.datetime.combine(local.date(), dt.time()).timestamp()
    previous_day = (local.date() - dt.timedelta(days=1)).isoformat()
    day_end = midnight
    day_start = dt.datetime.combine(
        local.date() - dt.timedelta(days=1), dt.time()
    ).timestamp()
    folder = home / "reports"
    folder.mkdir(mode=0o700, exist_ok=True)
    periods = [("latest", midnight, now)]
    if local.hour >= 9 and not (folder / (previous_day + ".json")).exists():
        periods.append((previous_day, day_start, day_end))
    for name, start, end in periods:
        all_samples = [
            (at, json.loads(raw))
            for at, raw in db.execute(
                "SELECT at,health FROM samples WHERE at>=? AND at<=? ORDER BY at",
                (start, end),
            )
        ]
        samples = [
            (at, value)
            for at, value in all_samples
            if all(key in value.get("components", {}) for key in RUNTIME_COMPONENTS)
        ]
        report = {
            "version": VERSION,
            "generated_at": now,
            "period_start": start,
            "period_end": end,
            "observed_checks": len(samples),
            "excluded_legacy_availability_checks": len(all_samples) - len(samples),
            "ready_checks": sum(row["ready"] for _, row in samples),
            "max_gap_seconds": max(
                (b[0] - a[0] for a, b in pairwise(samples)), default=None
            ),
            "current": health,
            "delivery": delivery,
            "limits": [
                "Counts describe observed checks, not continuous uptime.",
                "Mac sleep, power loss and monitor outages need an independent external observer.",
                "Alertlane acceptance is not proof of phone delivery; current phone readiness is separate.",
                "Notification command success is not proof the user saw a banner.",
            ],
        }
        write_json(folder / (name + ".json"), report)
        text = (
            f"# Oraclebot operations — {name}\n\nObserved checks: {len(samples)}; ready checks: {report['ready_checks']}.\n"
            f"Current readiness: {health['ready']}; overall: {health['overall']}.\n\n"
            + "\n".join(
                f"- {key}: {value['state']} ({value['reason']})"
                for key, value in health["components"].items()
            )
            + f"\n\nPending alert deliveries: {delivery['pending']}.\n\n"
            + "\n".join(report["limits"])
            + "\n"
        )
        temp = folder / (name + ".md.new")
        temp.write_text(text)
        temp.chmod(0o600)
        temp.replace(folder / (name + ".md"))
        if name != "latest":
            notify(
                "Oraclebot daily report",
                f"{report['ready_checks']}/{len(samples)} observed checks ready. Report: {folder / (name + '.md')}",
            )
    for file in folder.glob("????-??-??.*"):
        if file.stat().st_mtime < now - 90 * 86400:
            file.unlink()


def tick(home, config, db):
    now = time.time()
    health = probe(config["solbot"])
    health["components"].update(probe_runtime(config, now))
    health["components"]["live_price_forecast"] = probe_forecast(config, now)
    health["ready"] = (
        health["ready"]
        and all(health["components"][key]["ready"] for key in RUNTIME_COMPONENTS[:3])
        and health["components"]["live_price_forecast"]["ready"]
    )
    health["overall"] = (
        "down"
        if not health["ready"]
        else "degraded"
        if any(not row["ready"] for row in health["components"].values())
        else "up"
    )
    record(db, health, now)
    delivery = deliver(db, config)
    delivery["external_heartbeat_accepted"] = heartbeat(config, health, now)
    reports(db, home, health, delivery, now)
    result = {
        "version": VERSION,
        "observed_at": now,
        "pid": os.getpid(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "health": health,
        "delivery": delivery,
    }
    write_json(home / "status.json", result)
    return result


def _main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "once", "status", "install"))
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--solbot", type=Path)
    parser.add_argument("--alertlane-env", type=Path)
    parser.add_argument("--alertlane-url")
    parser.add_argument("--gh", type=Path)
    parser.add_argument("--github-repository", default="mithudso/solmargintrader")
    parser.add_argument("--pipeline-python", type=Path)
    parser.add_argument("--pipeline-home", type=Path)
    parser.add_argument("--forecast-python", type=Path)
    args = parser.parse_args(argv)
    if args.action == "install" and not all(
        (
            args.solbot,
            args.alertlane_env,
            args.gh,
            args.alertlane_url,
            args.pipeline_python,
            args.pipeline_home,
            args.forecast_python,
        )
    ):
        parser.error(
            "install requires --solbot, --alertlane-env, --alertlane-url, --gh, --pipeline-python, --pipeline-home and --forecast-python"
        )
    home = args.home.expanduser().absolute()
    if args.action == "status":
        result = json.loads((home / "status.json").read_text())
        result["fresh"] = -5 <= time.time() - result["observed_at"] <= 150
        print(json.dumps(result))
        return 0 if result["fresh"] else 1
    config = None
    if args.action != "install":
        config = json.loads((home / "config.json").read_text())
        if not isinstance(config, dict):
            raise ValueError("invalid_monitor_configuration")
    db = database(home)
    if args.action == "install":
        config = {
            "solbot": str(args.solbot.absolute()),
            "alertlane_env": str(args.alertlane_env.absolute()),
            "alertlane_url": args.alertlane_url,
            "gh": str(args.gh.absolute()),
            "github_repository": args.github_repository,
            "pipeline_python": str(args.pipeline_python.absolute()),
            "pipeline_home": str(args.pipeline_home.absolute()),
            "forecast_python": str(args.forecast_python.absolute()),
        }
        for executable in (
            args.solbot,
            args.gh,
            args.pipeline_python,
            args.forecast_python,
        ):
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError("installed_executable_required")
        ingest_token(args.alertlane_env)  # Validate without printing/copying it.
        config_path = home / "config.json"
        if config_path.exists() and json.loads(config_path.read_text()) != config:
            raise ValueError("existing_monitor_configuration_differs")
        app = home / (
            "monitor-"
            + VERSION
            + "-"
            + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
            + ".py"
        )
        if not app.exists():
            app.write_bytes(Path(__file__).read_bytes())
            app.chmod(0o600)
        elif app.read_bytes() != Path(__file__).read_bytes():
            raise ValueError("installed_monitor_hash_mismatch")
        definition = {
            "Label": LABEL,
            "ProgramArguments": [sys.executable, str(app), "run", "--home", str(home)],
            "RunAtLoad": True,
            "KeepAlive": True,
            "ThrottleInterval": 10,
            "Umask": 0o077,
            "WorkingDirectory": str(Path.home()),
            "StandardOutPath": str(home / "stdout.log"),
            "StandardErrorPath": str(home / "stderr.log"),
        }
        path = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
        if path.exists() and plistlib.loads(path.read_bytes()) != definition:
            raise ValueError("existing_monitor_definition_differs")
        write_json(config_path, config)
        path.write_bytes(plistlib.dumps(definition))
        path.chmod(0o600)
        target = f"gui/{os.getuid()}/{LABEL}"
        check = subprocess.run(
            ["launchctl", "print", target], capture_output=True, check=False
        )
        if check.returncode == 113:
            subprocess.run(
                ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)], check=True
            )
        elif check.returncode:
            raise ValueError("monitor_registration_unknown")
        print(json.dumps({"installed": True, "plist": str(path), "app": str(app)}))
        return 0
    with (home / "owner.lock").open("a+") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "once":
            print(json.dumps(tick(home, config, db)))
            return 0
        for event in (signal.SIGTERM, signal.SIGINT):
            signal.signal(event, lambda *_: STOP.set())
        while not STOP.is_set():
            tick(home, config, db)
            STOP.wait(60)
    return 0


def main(argv=None):
    try:
        return _main(argv)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, sqlite3.Error):
        print(
            "Oraclebot operations prerequisite unavailable. Verify --home, the installed "
            "configuration/status, private credential file and declared executables; "
            "see docs/ORACLEBOT-OPERATIONS.md before an explicit install or migration.",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
