"""Shared fixtures for the command-bridge tests: an isolated world and the four surface runners."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from soltui import api, bgcontrol, bgqueue, cli, commands, live_run, native_host

TOKEN = "test-token-not-a-secret"

# Commands that run for minutes, spawn processes, hit the network or write repo files. The parity suite
# replaces their handlers with fixed answers; the registry, validation, envelope and surfaces are real.
HEAVY = {
    "batch.list": {"runs": []},
    "batch.create": {"run_id": "a" * 32, "phase": "planned"},
    "batch.start": {"run_id": "a" * 32, "pid": 1},
    "batch.status": {"run_id": "a" * 32, "phase": "planned", "running": False, "counts": {}},
    "batch.cells": {"rows": []},
    "batch.stop": {"run_id": "a" * 32, "stopping": False},
    "backtest.run": {"rows": [], "evaluable": 0, "positive": 0, "skipped": [], "cancelled": False,
                     "message": "stub"},
    "backtest.untested_sweep": {"output": "stub"},
    "paper.start": {"summary": {"bar": 0}, "text": "stub", "fills": [], "mode": "stub"},
    "paperexperiment.start": {"id": "stub", "phase": "starting"},
    "paperexperiment.resume": {"id": "stub", "phase": "starting"},
    "paperexperiment.stop": {"id": "stub", "stopping": True},
    "paperexperiment.status": {"experiments": []},
    "coinbase.account": {"accounts": [], "complete": False},
    "coinbase.sync": {"accounts": [], "complete": True},
    "coinbase.markets": {"count": 0, "global_count": 0, "scopes": {}},
    "coinbase.pairs": {"scope":"SPOT", "complete":True, "count":0, "pairs":[]},
    "coinbase.order_preview": {"preview_id":"stub", "product_id":"SOL-USDC", "side":"BUY",
                               "size":"1", "size_currency":"quote", "estimate":{}, "expires_at":0,
                               "notice":"stub"},
    "coinbase.order_submit": {"order_id":"stub", "status":"FILLED"},
    "coinbase.order_quick": {"order_id":"stub", "status":"FILLED"},
    "coinbase.order_status": {"order_id":"stub", "status":"FILLED"},
    "coinbase.order_state": {"unresolved":False, "orders":[]},
    "live.spawn_dryrun": {"command": ["node"], "returncode": 0, "stdout": "stub"},
    "queue.start": {"started": True, "asset": "SOL"},
    "queue.start_fresh": {"started": True, "asset": "SOL"},
    "queue.stop": {"stopping": False},
    "queue.backtest": {"started": True, "scope": "all", "strategies": [], "jobs": 0, "asset": "SOL",
                       "message": "stub"},
    # These start ollama and the idle indexer; the parity suite must not.
    "docs.search": {"query": "x", "mode": "keyword", "mode_used": "keyword", "hits": [], "notes": []},
    "docs.search_unload": {"message": "stub"},
    "queue.fetch": {"fetching": [], "log": None},
    "analyze.run": {"headline": "stub", "truncated": False, "decisions": [], "actions": {}},
    "docs.write": {"path": "x", "bytes": 1, "file": "x"},
    # Compound: live reads hit public market-data endpoints; backtests read the real 5m cache.
    "forwardtest.tick": {"asset": "SOL", "bar": None, "recorded": 0, "rows": [], "message": "stub"},
    "forwardtest.status": {"asset": "SOL", "rows": []},
    "compound.signal": {"call": "FLAT", "composite": None, "components": []},
    "compound.forward_tick": {"asset": "SOL", "recorded": False, "call": "FLAT", "resolved": 0},
    "compound.unattended_start": {"started": True, "asset": "SOL", "pid": 1, "log": "x"},
    "compound.unattended_stop": {"stopping": False, "asset": "SOL", "message": "not running"},
    # Autopilot starts a detached training loop per coin; a real call here once left 32 of them running.
    "compound.autopilot": {"autopilot": False, "running": [], "agent": {"loaded": False}, "adoptions": [],
                           "ensure": None},
    "compound.autopilot_status": {"autopilot": True, "running": [], "agent": {"loaded": False}, "adoptions": []},
    "compound.autopilot_ensure": {"autopilot": True, "started": [], "already_running": [], "skipped": {}},
    "compound.backtest": {"run_id": "stub", "configurations": 0, "assets": [], "skipped": {},
                          "errors": [], "rows": []},
    # The P&L commands run the roster's backtests, which need a cached price series.
    "portfolio.scan": {"label": "wallet (live)", "chains": {}, "total_usd": 0.0, "skipped": [],
                       "partial": False, "counts": {}},
    "portfolio.snapshot": {"label": "wallet (live)", "at": "2026-11-07T00:00:00+00:00", "partial": False,
                           "total_usd": 0.0, "total_complete": True, "skipped": [], "chains": {},
                           "snapshot_file": "stub"},
    "pnl.summary": {"window": {"label": "stub"}, "sections": [], "notice": "stub", "groups": {}},
    "pnl.series": {"window": {"label": "stub"}, "sections": [], "notice": "stub", "groups": {}},
    "pnl.breakdown": {"window": {"label": "stub"}, "sections": [], "notice": "stub", "groups": {}},
    # Bots: backtests carry an id and a time, forward_start and prices.start spawn the detached price
    # recorder (a real call would leave it running), and optimize sweeps every cached coin.
    "bots.backtest": {"bot": "grid", "coins": ["SOL"], "runs": [], "errors": {}, "summary": [],
                      "beat_hold": 0, "ran": 0},
    "bots.forward_start": {"forward": {"id": "stub", "bot": "grid"}, "recorder": {"started": False}},
    "bots.optimize": {"bot": "grid", "verdict": {"reliable": False, "adopted": False}, "table": []},
    "bots.schedule_start": {"enabled": True, "running": True, "phase": "running", "items": []},
    "bots.schedule_stop": {"enabled": False, "running": False, "phase": "stopped", "items": []},
    "bots.schedule_status": {"enabled": False, "running": False, "phase": "stopped", "items": []},
    "bots.rank_coins": {"bot": "grid", "mode": "quick", "rows": [], "errors": {}, "cancelled": False},
    "bots.audit_coin": {"bot": "grid", "mode": "audit", "rows": [], "errors": {}, "cancelled": False},
    # Starts the background Forwardtest thread, which reads public Coinbase candles every minute.
    "forwardtest.run": {"running": True, "assets": ["SOL"], "since": 0},
    # Experiment creation fingerprints local evidence; starts/finalization spawn an explicit process.
    "experiments.create": {"id": "stub", "status": "created"},
    "experiments.start": {"id": "stub", "status": "running"},
    "experiments.finalize": {"id": "stub", "status": "completed"},
    # Installs a LaunchAgent and starts the recorder; a real call would leave both behind.
    "prices.ensure": {"running": True, "agent": {"installed": True, "loaded": True}},
}


def default_params() -> dict[str, dict]:
    """A valid call for every command with a required parameter."""
    from backtester.core.strategies import REGISTRY

    fresh = next(n for n in sorted(REGISTRY) if n not in ("buy_and_hold", "ma_crossover", "rsi", "breakout"))
    return {
        "batch.start": {"run_id": "a" * 32},
        "batch.status": {"run_id": "a" * 32},
        "batch.cells": {"run_id": "a" * 32},
        "batch.stop": {"run_id": "a" * 32},
        "strategies.source": {"name": "rsi"},
        "roster.add": {"name": fresh},
        "roster.toggle": {"name": fresh},
        "roster.remove": {"label": "rsi_14_30_50"},
        "signals.save": {"values": {"rsi_period": 9}},
        "paper.start": {"label": "rsi_14_30_50"},
        "coinbase.order_preview": {"product_id":"SOL-USDC", "side":"BUY", "size":"1", "size_currency":"quote"},
        "coinbase.order_quick": {"product_id":"SOL-USDC", "side":"BUY", "size":"1", "size_currency":"quote", "skip_confirm":True},
        "coinbase.order_status": {"order_id":"stub"},
        "paperexperiment.start": {"strategy": "rsi"},
        "paperexperiment.resume": {"id": "aaaaaaaaaaaaaaaaaaaaaaaa"},
        "paperexperiment.stop": {"id": "aaaaaaaaaaaaaaaaaaaaaaaa"},
        "live.spawn_dryrun": {"strategy": "buy_and_hold"},
        "analyze.run": {"asset": "SOL"},
        "docs.read": {"path": "soltui/commands.py"},
        "docs.write": {"path": "scratch.txt", "text": "x"},
        "liquidity.resume": {"confirm": True},
        "queue.backtest": {"scope": "all"},
        "docs.search": {"query": "slippage"},
        "compound.autopilot": {"enabled": False},
        "bots.config": {"bot": "grid"},
        "bots.save": {"bot": "dca", "text": "take_profit_pct=3"},
        "bots.backtest": {"bot": "grid"},
        "bots.rank_coins": {"bot": "grid"},
        "bots.audit_coin": {"bot": "grid", "asset": "SOL"},
        "bots.forward_start": {"bot": "grid"},
        "bots.forward_stop": {"bot": "grid"},
        "bots.forward_status": {"bot": "grid"},
        "bots.optimize": {"bot": "grid"},
        "bots.optimize_result": {"bot": "grid"},
        "bots.progress": {"bot": "grid"},
        "experiments.schema": {"bot": "grid"},
        "experiments.preview": {"bot": "grid"},
        "experiments.create": {"bot": "grid"},
        "experiments.get": {"run_id": "fixture"},
        "experiments.start": {"run_id": "fixture"},
        "experiments.pause": {"run_id": "fixture"},
        "experiments.cancel": {"run_id": "fixture"},
        "experiments.finalize": {"run_id": "fixture"},
        "experiments.candidates": {"run_id": "fixture"},
        "experiments.cells": {"run_id": "fixture"},
        "experiments.heatmap": {"run_id": "fixture", "x": "rungs", "y": "range_pct"},
        "experiments.compare": {"left": "fixture", "right": "fixture"},
    }


class World:
    """Throwaway config, log, support, aero-lp and queue directories, and a clean shared runtime."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="soltui-bridge-"))
        self.stack = ExitStack()

    def __enter__(self) -> "World":
        env = {
            "SOLTUI_CONFIG_DIR": self.root / "config", "SOLTUI_LOG_DIR": self.root / "logs",
            "SOLTUI_SUPPORT_DIR": self.root / "support", "AERO_LP_HOME": self.root / "aero",
            "SOLTUI_KEY_DIR": self.root / "keys",
        }
        self.stack.enter_context(mock.patch.dict(os.environ, {k: str(v) for k, v in env.items()}))
        for mod, attr, value in (
            ("config", "CONFIG_DIR", self.root / "config"),
            ("config", "CONFIG_PATH", self.root / "config" / "config.yaml"),
            ("config", "CONFIG_PATH_JSON", self.root / "config" / "config.json"),
        ):
            import importlib
            self.stack.enter_context(mock.patch.object(
                importlib.import_module(f"soltui.{mod}"), attr, value))
        self.stack.enter_context(mock.patch.object(bgqueue, "RESULTS_PATH", self.root / "bg" / "r.jsonl"))
        self.stack.enter_context(mock.patch.object(bgqueue, "STATE_PATH", self.root / "bg" / "s.json"))
        self.stack.enter_context(mock.patch.object(bgqueue, "BG_DIR", self.root / "bg"))
        self.stack.enter_context(mock.patch.object(bgcontrol, "LOCK_PATH", self.root / "bg" / "w.lock"))
        self.stack.enter_context(mock.patch.object(live_run, "RECOMMENDATION_FILE",
                                                   self.root / "none.json"))
        commands.reset_default_runtime()
        return self

    def reset_state(self) -> None:
        """Back to a fresh install between surfaces, so each sees identical starting state."""
        for sub in ("config", "aero", "bg"):
            shutil.rmtree(self.root / sub, ignore_errors=True)
        commands.reset_default_runtime()

    def __exit__(self, *exc) -> None:
        self.stack.close()
        shutil.rmtree(self.root, ignore_errors=True)

    @property
    def log(self) -> Path:
        return self.root / "logs" / "calls.jsonl"

    def log_lines(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


def stub_heavy(stack: ExitStack) -> None:
    for name, result in HEAVY.items():
        cmd = commands.COMMANDS[name]
        stack.enter_context(mock.patch.dict(
            commands.COMMANDS,
            {name: commands.Command(name, cmd.describe, lambda ctx, p, r=result: r, cmd.params,
                                    cmd.read_only, cmd.long_running, cmd.requires_confirm)}))


# -- the four surfaces: each returns the envelope as the exact text it would put on the wire ----------


def via_tui(name: str, params: dict) -> str:
    return commands.dumps(commands.dispatch(name, params, surface="tui"))


def via_cli(name: str, params: dict) -> str:
    out = io.StringIO()
    if name == "list":
        cli.main(["list"], out=out)
    else:
        cli.main(["call", name, "--json", json.dumps(params)], out=out)
    return out.getvalue().rstrip("\n")


class ApiServer:
    def __enter__(self) -> "ApiServer":
        self.server = api.create_server(0, TOKEN)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()

    def request(self, method: str, path: str, body: dict | None = None,
                headers: dict | None = None, token: str | None = TOKEN) -> tuple[int, str]:
        h = dict(headers or {})
        if token is not None:
            h["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                     method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode()


def via_api(server: ApiServer):
    def run(name: str, params: dict) -> str:
        path = "/v1/commands" if name == "list" else f"/v1/{name}"
        method, body = ("GET", None) if name == "list" else ("POST", params)
        return server.request(method, path, body)[1]
    return run


def host_call(request: dict) -> tuple[str, dict]:
    """(raw reply text, parsed reply) for one request through the real framing code."""
    import struct
    payload = json.dumps(request).encode()
    stdin = io.BytesIO(struct.pack("<I", len(payload)) + payload)
    stdout = io.BytesIO()
    native_host.serve(stdin, stdout)
    raw = stdout.getvalue()
    (length,) = struct.unpack("<I", raw[:4])
    text = raw[4:4 + length].decode()
    return text, json.loads(text)


def via_host(name: str, params: dict) -> str:
    request = {"id": "t1", "op": "list"} if name == "list" else {
        "id": "t1", "op": "call", "command": name, "params": params}
    text, parsed = host_call(request)
    envelope_text = commands.dumps(parsed["response"])
    assert envelope_text in text, "host reply must embed the envelope bytes unchanged"
    return envelope_text
