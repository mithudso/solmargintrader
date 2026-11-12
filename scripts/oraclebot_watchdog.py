#!/usr/bin/env python3
"""Independent GitHub-hosted availability observer for the Oraclebot Mac service."""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.request

MARKER = "<!-- oraclebot-operations-watchdog:v1 -->"
TITLE = "Oraclebot availability alert"


def assess(raw, now=None):
    now = time.time() if now is None else now
    try:
        value = json.loads(raw)
        at = value["at"]
        if type(at) not in (int, float) or not math.isfinite(at):
            raise ValueError("invalid_time")
        age = now - at
        if not -15 <= age <= 300:
            return False, "heartbeat_stale", value
        if type(value.get("ready")) is not bool:
            raise ValueError("invalid_readiness")
        return (
            value["ready"],
            "available" if value["ready"] else "ecosystem_not_ready",
            value,
        )
    except (ValueError, TypeError, KeyError):
        return False, "heartbeat_unavailable", {}


def api(path, payload=None, method=None):
    token = os.environ["GH_TOKEN"]
    request = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read(2_000_000))


def website_health():
    try:
        with urllib.request.urlopen(
            "https://oraclebot.io/api/health", timeout=15
        ) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                raise ValueError("invalid_website_health")
            value = json.loads(raw)
            if value.get("status") != "ok" or value.get("storage") is not True:
                raise ValueError("website_not_ready")
            return {
                key: value.get(key)
                for key in ("status", "version", "engine", "billing", "liveExecution")
            }
    except (OSError, ValueError, TypeError, AttributeError):
        return {"status": "unavailable"}


def reconcile(repo, healthy, reason, run_url, request=api, acceptance=False):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid_repository")
    marker = MARKER + (" acceptance" if acceptance else "")
    title = TITLE + (" — acceptance test" if acceptance else "")
    owned = []
    for page in range(1, 101):
        rows = request(f"/repos/{repo}/issues?state=open&per_page=100&page={page}")
        owned.extend(
            row
            for row in rows
            if row.get("title") == title
            and row.get("body", "").startswith(marker)
            and not row.get("pull_request")
        )
        if len(rows) < 100:
            break
    if not healthy and not owned:
        body = (
            f"{marker}\n\n@{repo.split('/')[0]} — the independent observer reports **{reason}**.\n\n"
            f"Run: {run_url}\n\nCheck the Mac's suite and operations LaunchAgents. "
            "A stale heartbeat may mean host power, sleep, network, monitor or GitHub-auth failure. "
            "GitHub schedules are best effort. This alert does not establish trading readiness."
        )
        row = request(f"/repos/{repo}/issues", {"title": title, "body": body}, "POST")
        return {"action": "opened", "issue": row["number"]}
    if healthy and owned:
        for row in owned:
            request(
                f"/repos/{repo}/issues/{row['number']}/comments",
                {
                    "body": f"A fresh heartbeat now reports readiness. Recovery observed in {run_url}"
                },
                "POST",
            )
            request(
                f"/repos/{repo}/issues/{row['number']}",
                {"state": "closed", "state_reason": "completed"},
                "PATCH",
            )
        return {"action": "resolved", "issues": [row["number"] for row in owned]}
    return {"action": "unchanged", "issues": [row["number"] for row in owned]}


def main():
    healthy, reason, heartbeat = assess(os.environ.get("ORACLEBOT_HEARTBEAT", ""))
    website = website_health()
    if website["status"] != "ok":
        healthy, reason = False, "website_unavailable"
    mode = os.environ.get("ACCEPTANCE_MODE", "normal")
    if mode not in ("normal", "failure", "recovery"):
        raise ValueError("invalid_acceptance_mode")
    if mode == "failure":
        healthy, reason = False, "synthetic_heartbeat_stale"
    if mode == "recovery" and not healthy:
        raise ValueError("real_heartbeat_must_be_healthy_before_acceptance_recovery")
    repo = os.environ["GITHUB_REPOSITORY"]
    run_url = f"https://github.com/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    result = reconcile(repo, healthy, reason, run_url, acceptance=mode != "normal")
    summary = (
        f"# Oraclebot operations\n\nReadiness: **{reason}**\n\n"
        f"Latest heartbeat: `{json.dumps(heartbeat, sort_keys=True)}`\n\n"
        f"Website capabilities: `{json.dumps(website)}`\n\n"
        f"Incident update: `{json.dumps(result)}`\n\n"
        "Reports run every weekday morning in addition to five-minute best-effort checks. "
        "Counts of continuously observed checks and market-data warnings are in the Mac's daily reports. "
        "A fresh heartbeat proves observed service readiness, not data certification, profitable trading or phone delivery.\n"
    )
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
        out.write(summary)
    print(json.dumps({"healthy": healthy, "reason": reason, "incident": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
