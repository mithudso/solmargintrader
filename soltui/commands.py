"""The soltui command registry: one set of calls for the TUI, CLI, HTTP API and native host.

Every action the console can take is a registered `Command`. Every surface goes through
`dispatch(name, params, surface)`, which validates parameters, applies the confirm gate, runs the
handler, wraps the outcome in the response envelope and appends one line to the call log. The
surfaces only carry bytes and render results; none of them holds command logic. That is what makes
"the same call, the same answer" structural rather than a promise, and `tests/test_bridge_parity.py`
walks this registry to prove it for every entry.

Envelope (byte-identical JSON on every surface for the same call):

    {"ok": true,  "command": "<name>", "result": <json>, "error": null}
    {"ok": false, "command": "<name>", "result": null,
     "error": {"code": "bad_params|unknown_command|forbidden|failed|timeout", "message": "..."}}

Nothing in `result` or `error` names a surface, a time or a request id.

Boundaries this module keeps:

* soltui has no order path (no keys, no signing, no venue client), so no command here moves funds.
  `backtest.*` and `paper.*` replay history; `live.spawn_dryrun` runs the extension's *dry-run* tool.
* `liquidity.resume` deletes the aero-lp `KILL` file, which removes a safety stop on a real-money
  daemon. It is `requires_confirm`: it refuses with `forbidden` unless `params.confirm is True`, on
  every surface, the TUI included. `liquidity.kill` only adds the stop, so it needs no confirm.
* The call log records parameter *keys* only. Values (paths, document text) never reach it.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from . import analyze as analyze_mod
from . import compound as compound_mod
from . import bgcontrol, bgqueue, forwardtest
from . import cumulative as cumulative_mod
from . import docs_browser, live_run, pnl as pnl_mod, presets as presets_mod, wallet as wallet_mod
from . import portfolio as portfolio_mod
from . import liquidity as liq
from . import top5 as top5_mod
from .config import INTERVALS, Settings, load_settings, save_settings
from .netpct import labelled
from .paper import MODE_LABEL, PaperSession, start_session
from .reference import FAMILY_NOTES, RESEARCH_DRIVERS, RESEARCH_FINDINGS, SIGNAL_REFERENCE
from .roster import Roster, RosterEntry, RosterError, available_strategies
from .runner import SweepRunner, engine_config, load_arrays
from .signals import (
    SIGNAL_GROUPS,
    SignalDefaults,
    coerce,
    from_dict,
    mapped_strategies,
    merged_params,
)
from .status import AppState, Phase, build_title

REPO = Path(__file__).resolve().parent.parent

# The research scripts import pandas and numpy, so they must run on the interpreter running this
# process (its venv has them). A bare "python3" resolves through PATH and, after a Homebrew upgrade
# made it 3.15 with no pandas, the button failed with "ModuleNotFoundError: No module named 'pandas'"
# (2026-11-07; Stele KNOW-546).
UNTESTED_SWEEP_TIMEOUT_S = 30 * 60

# Rows the Docs listing returns at once. The repo has ~470 tracked files; leave headroom.
DOCS_TABLE_CAP = 1000

ERROR_CODES = ("bad_params", "unknown_command", "forbidden", "failed", "timeout")
PARAM_TYPES = ("string", "number", "bool", "json")

LOG_ROTATE_BYTES = 5 * 1024 * 1024


def untested_sweep_command(repo: Path) -> list[str]:
    """argv for research/sweep_untested.py on this process's own interpreter."""
    return [sys.executable, str(repo / "research" / "sweep_untested.py")]


def failure_summary(stderr: str, lines: int = 3) -> str:
    """The end of a traceback, where the exception is; its start only names the entry file."""
    tail = [line for line in (stderr or "").strip().splitlines() if line.strip()][-lines:]
    return "\n".join(tail) or "no error output"


# -- errors, params, registry --------------------------------------------------------------------


class CommandError(Exception):
    """A handler's way to report a failure with a specific envelope code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Param:
    """One declared parameter. `type` is one of string, number, bool, json."""

    name: str
    type: str
    describe: str
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "required": self.required,
                "describe": self.describe}


@dataclass(frozen=True)
class Command:
    """A registered action. `handler(ctx, params)` returns JSON-serialisable data."""

    name: str
    describe: str
    handler: Callable[["Context", dict[str, Any]], Any]
    params: tuple[Param, ...] = ()
    read_only: bool = True
    long_running: bool = False
    requires_confirm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "describe": self.describe,
            "params": [p.to_dict() for p in self.params],
            "read_only": self.read_only, "long_running": self.long_running,
            "requires_confirm": self.requires_confirm,
        }


COMMANDS: dict[str, Command] = {}

CONFIRM_PARAM = Param("confirm", "bool",
                      "Must be true. This command removes a safety stop on a real-money system.")


def P(name: str, type_: str, describe: str, required: bool = False) -> Param:
    return Param(name, type_, describe, required)


def command(name: str, describe: str, params: tuple[Param, ...] = (), *, read_only: bool = True,
            long_running: bool = False, requires_confirm: bool = False):
    """Register `handler` under `name`. A `requires_confirm` command gains the `confirm` param."""

    def wrap(fn):
        declared = tuple(params) + ((CONFIRM_PARAM,) if requires_confirm else ())
        if name in COMMANDS:
            raise RuntimeError(f"duplicate command {name}")
        COMMANDS[name] = Command(name, describe, fn, declared, read_only, long_running,
                                 requires_confirm)
        return fn

    return wrap


# -- shared state --------------------------------------------------------------------------------


class Runtime:
    """Process-wide mutable state that outlives one call.

    The TUI owns one; the API server and native host share the module default. It holds only
    things that cannot be rebuilt from disk per call: the running sweep, the open dry-run replay,
    the queue-results cursor and the docs catalogue cache.
    """

    def __init__(self) -> None:
        self.state = AppState()
        self.runner = SweepRunner(self.state)
        self.session: PaperSession | None = None
        self.session_label = ""
        self.session_asset = ""
        # Backtest equity curves for the P&L tab, keyed by everything that changes them.
        self.pnl_cache: dict[str, Any] = {}
        self.queue_results: list[bgqueue.JobResult] = []
        self.queue_cursor = bgqueue.ResultsCursor()
        self.lock = threading.RLock()
        self.forward_plan: dict[str, Any] | None = None
        self.forward_stop = threading.Event()
        self.forward_busy = False
        # Suitability scans share the command registry across UI/API/CLI. The event is
        # cooperative: declaring a Textual worker cancelled cannot stop its Python thread.
        self.coin_fit_stop = threading.Event()
        self.coin_fit_job: dict[str, Any] | None = None
        self.coin_fit_cancelled_requests: set[str] = set()
        self.coin_fit_interrupted_requests: set[str] = set()
        # The Forwardtest runner: a thread of this process, so a test keeps checking prices whatever
        # tab (or none) the console shows. One summary per coin from its latest check.
        self.forward_thread: threading.Thread | None = None
        self.forward_last: dict[str, dict[str, Any]] = {}
        self.forward_started_at: float | None = None
        self._catalog: list[docs_browser.DocEntry] | None = None
        self._catalog_key: tuple | None = None

    def catalog(self) -> list[docs_browser.DocEntry]:
        """The Docs catalogue, re-read only when `index/INDEX.json` changes."""
        try:
            stat = docs_browser.INDEX_JSON.stat()
            key = (str(docs_browser.INDEX_JSON), stat.st_mtime_ns, stat.st_size)
        except OSError:
            key = None
        if self._catalog is None or key != self._catalog_key:
            self._catalog = docs_browser.load_catalog()
            self._catalog_key = key
        return self._catalog


_DEFAULT_RUNTIME = Runtime()


def default_runtime() -> Runtime:
    return _DEFAULT_RUNTIME


def reset_default_runtime() -> Runtime:
    """Replace the shared runtime (tests)."""
    global _DEFAULT_RUNTIME
    _DEFAULT_RUNTIME = Runtime()
    return _DEFAULT_RUNTIME


class Context:
    """What a handler reads: settings, roster and signal defaults, plus the shared runtime.

    The TUI builds one Context and keeps it for the life of the app, so its in-memory edits and the
    commands it dispatches see the same objects. Every other surface lets `dispatch` build a fresh
    one from disk per call (`Context.load`), which is why every mutating command persists.
    """

    def __init__(self, settings: Settings, roster: Roster, signals: SignalDefaults,
                 runtime: Runtime | None = None) -> None:
        self.settings = settings
        self.roster = roster
        self.signals = signals
        self.runtime = runtime or default_runtime()
        # Tests and the TUI may pin the Docs catalogue; None means "read index/INDEX.json".
        self.catalog_override: list[docs_browser.DocEntry] | None = None
        self.progress: Callable[[str], None] | None = None

    @classmethod
    def from_settings(cls, settings: Settings, runtime: Runtime | None = None) -> "Context":
        roster = Roster.from_list(settings.roster or [{"name": n} for n in settings.enabled_strategies])
        if len(roster) == 0 and settings.enabled_strategies:
            roster = Roster.default()
        return cls(settings, roster, from_dict(settings.signal_defaults), runtime)

    @classmethod
    def load(cls, runtime: Runtime | None = None) -> "Context":
        return cls.from_settings(load_settings(), runtime)

    @property
    def state(self) -> AppState:
        return self.runtime.state

    @property
    def runner(self) -> SweepRunner:
        return self.runtime.runner

    @property
    def session(self) -> PaperSession | None:
        return self.runtime.session

    @session.setter
    def session(self, value: PaperSession | None) -> None:
        self.runtime.session = value

    def catalog(self) -> list[docs_browser.DocEntry]:
        if self.catalog_override is not None:
            return self.catalog_override
        return self.runtime.catalog()

    def persist_roster(self) -> None:
        """Write the roster (with params) and the signal defaults into the settings file."""
        self.settings.roster = self.roster.to_list()
        self.settings.enabled_strategies = [e.name for e in self.roster]
        self.settings.signal_defaults = self.signals.to_dict()
        save_settings(self.settings)


# -- envelope, JSON, logging ---------------------------------------------------------------------


def jsonable(value: Any) -> Any:
    """Reduce `value` to plain JSON types. NaN/inf become null so the output is strict JSON."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, Enum):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return jsonable(value.value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else value
        return [jsonable(v) for v in items]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    item = getattr(value, "item", None)  # numpy scalars
    if callable(item):
        try:
            return jsonable(item())
        except (TypeError, ValueError):
            pass
    tolist = getattr(value, "tolist", None)  # numpy arrays
    if callable(tolist):
        return jsonable(tolist())
    return str(value)


def dumps(envelope: Any) -> str:
    """The one serialiser every surface uses, so equal envelopes are equal bytes."""
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def ok_envelope(command_name: str, result: Any) -> dict[str, Any]:
    return {"ok": True, "command": command_name, "result": result, "error": None}


def error_envelope(command_name: str, code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "command": command_name, "result": None,
            "error": {"code": code, "message": message}}


def log_dir() -> Path:
    return Path(os.environ.get("SOLTUI_LOG_DIR") or Path.home() / "Library" / "Logs" / "soltui")


def log_path() -> Path:
    return log_dir() / "calls.jsonl"


_LOG_LOCK = threading.Lock()


def _log_call(surface: str, command_name: str, env: dict[str, Any], ms: int, keys: list[str]) -> None:
    """Append one line per call. Parameter keys only, never values. Never raises."""
    line = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "surface": surface,
        "command": command_name,
        "ok": env["ok"],
        "error_code": (env["error"] or {}).get("code"),
        "ms": ms,
        "params_keys": keys,
    }
    try:
        with _LOG_LOCK:
            path = log_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                if path.stat().st_size > LOG_ROTATE_BYTES:
                    os.replace(path, path.with_name(path.name + ".1"))
            except FileNotFoundError:
                pass
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError:
        pass  # a full disk or unwritable log must not fail the call that was logged


# -- parameter validation ------------------------------------------------------------------------


def _check_type(param: Param, value: Any) -> None:
    kind = param.type
    ok = (
        (kind == "string" and isinstance(value, str))
        or (kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))
        or (kind == "bool" and isinstance(value, bool))
        or kind == "json"
    )
    if not ok:
        raise CommandError("bad_params", f'parameter "{param.name}" must be {kind}')


def validate_params(cmd: Command, params: Any) -> dict[str, Any]:
    """Strict check of `params` against the declaration. Optional nulls count as absent."""
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise CommandError("bad_params", "params must be an object")
    declared = {p.name: p for p in cmd.params}
    for key in params:
        if key not in declared:
            raise CommandError("bad_params", f'command "{cmd.name}" has no parameter "{key}"')
    out: dict[str, Any] = {}
    for p in cmd.params:
        value = params.get(p.name)
        if value is None:
            if p.required:
                raise CommandError("bad_params", f'missing required parameter "{p.name}"')
            continue
        _check_type(p, value)
        out[p.name] = value
    return out


def coerce_cli_value(param: Param, raw: str) -> Any:
    """Turn a command-line string into the declared type (the CLI and GET query strings)."""
    if param.type == "number":
        try:
            n = float(raw)
        except ValueError:
            raise CommandError("bad_params", f'"{param.name}" must be a number') from None
        return int(n) if n.is_integer() and "." not in raw and "e" not in raw.lower() else n
    if param.type == "bool":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise CommandError("bad_params", f'"{param.name}" must be true or false')
    if param.type == "json":
        try:
            return json.loads(raw)
        except ValueError:
            raise CommandError("bad_params", f'"{param.name}" must contain valid JSON') from None
    return raw


def coerce_pairs(name: str, pairs: dict[str, str]) -> dict[str, Any]:
    """Coerce string pairs for command `name`. Unknown names pass through for dispatch to refuse."""
    cmd = COMMANDS.get(name)
    declared = {p.name: p for p in cmd.params} if cmd else {}
    return {k: (coerce_cli_value(declared[k], v) if k in declared else v) for k, v in pairs.items()}


# -- dispatch ------------------------------------------------------------------------------------

_DOMAIN_ERRORS = (ValueError, RuntimeError, OSError)


def describe_commands() -> list[dict[str, Any]]:
    return [COMMANDS[n].to_dict() for n in sorted(COMMANDS)]


def _execute(name: str, params: Any, ctx: Context | None) -> dict[str, Any]:
    if name == "list":
        return ok_envelope("list", describe_commands())
    cmd = COMMANDS.get(name)
    if cmd is None:
        return error_envelope(str(name), "unknown_command", f'unknown command "{name}"')
    try:
        clean = validate_params(cmd, params)
        if cmd.requires_confirm and clean.get("confirm") is not True:
            raise CommandError(
                "forbidden",
                f"{name} removes a safety stop on a real-money system; pass confirm=true to proceed")
        clean.pop("confirm", None)
        result = cmd.handler(ctx if ctx is not None else Context.load(), clean)
        return ok_envelope(name, jsonable(result))
    except CommandError as exc:
        return error_envelope(name, exc.code, exc.message)
    except subprocess.TimeoutExpired as exc:
        return error_envelope(name, "timeout", f"timed out after {int(exc.timeout)} s")
    except _DOMAIN_ERRORS as exc:
        return error_envelope(name, "failed", str(exc))
    except Exception as exc:  # noqa: BLE001 - a surface must always get an envelope back
        return error_envelope(name, "failed", f"{type(exc).__name__}: {exc}")


def dispatch(name: str, params: dict[str, Any] | None = None, surface: str = "api",
             ctx: Context | None = None, *, quiet: bool = False) -> dict[str, Any]:
    """Run command `name` and return its envelope. Every surface calls this and nothing else.

    `ctx` is for the TUI, which keeps one live Context; other surfaces omit it and get a fresh
    one read from disk. The call is logged here, once, by parameter keys only. `quiet` skips the
    log for the TUI's timer-driven refreshes of read-only commands (a 15 s poll would otherwise
    fill the log with calls nobody made); every user-initiated call is logged.
    """
    started = time.perf_counter()
    env = _execute(name, params, ctx)
    if quiet:
        return env
    keys = sorted(str(k) for k in params) if isinstance(params, dict) else []
    _log_call(surface, str(name), env, int((time.perf_counter() - started) * 1000), keys)
    return env


# -- settings ------------------------------------------------------------------------------------

_SETTING_CASTS = {
    "asset": str, "start": str, "end": str, "interval": str, "capital": float,
    "fee_bps": float, "slippage_bps": float, "fill_delay": int, "cpcv_groups": int, "cpcv_k": int,
    "solana_address": str, "base_address": str, "eth_address": str, "hyperliquid_address": str,
    "btc_xpub": str, "ltc_xpub": str, "doge_xpub": str,
}


@command("settings.get", "The saved settings (asset, interval, dates, costs, CPCV geometry, public wallet "
         "addresses). Extended public keys are shown as a short prefix and a *_set flag, never in full.")
def settings_get(ctx: Context, p: dict[str, Any]) -> Any:
    return {"settings": ctx.settings.public_dict(), "intervals": list(INTERVALS)}


@command(
    "settings.save",
    "Validate and save settings. Only the parameters you pass change. An empty string clears a wallet "
    "field. Private keys are refused: settings take public addresses and extended public keys only.",
    tuple(P(n, "number" if c in (int, float) else "string", f"Setting {n}.")
          for n, c in _SETTING_CASTS.items()),
    read_only=False,
)
def settings_save(ctx: Context, p: dict[str, Any]) -> Any:
    changes: dict[str, Any] = {}
    for name, cast in _SETTING_CASTS.items():
        if name not in p:
            continue
        value = p[name]
        if cast is int:
            if float(value) != int(value):
                raise CommandError("bad_params", f'parameter "{name}" must be a whole number')
            value = int(value)
        elif cast is float:
            value = float(value)
        changes[name] = value
    new = Settings(**{**ctx.settings.to_dict(), **changes,
                      "enabled_strategies": [e.name for e in ctx.roster],
                      "roster": ctx.roster.to_list()})
    path = save_settings(new)
    ctx.settings = new
    return {"path": str(path), "settings": new.public_dict()}


# -- strategies and roster -----------------------------------------------------------------------


def _entry(e) -> dict[str, Any]:
    return {"name": e.name, "params": dict(e.params), "label": e.label, "family": e.family,
            "warmup": e.warmup}


@command("strategies.list", "Every registered strategy and its family.")
def strategies_list(ctx: Context, p: dict[str, Any]) -> Any:
    return [{"name": n, "family": f} for n, f in available_strategies()]


@command("strategies.cards", "Implemented strategy cards and their execution capabilities.")
def strategies_cards(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core.strategy_cards import load_all

    registered = dict(available_strategies())
    rows = []
    for card in load_all().values():
        if not card.registry_key or card.registry_key not in registered or not card.runner:
            continue
        key = card.registry_key
        is_registered = key in registered and card.registry_key is not None
        rows.append({
            "key": key, "id": card.id, "name": card.name, "family": card.family,
            "status": card.status, "summary": card.summary, "runner": card.runner,
            "registered": is_registered,
            "testable": is_registered and card.buildable and card.data_available,
            "data_available": card.data_available,
            "path": f"backtester/strategy_cards/{card.path.name}",
        })
    rows.sort(key=lambda row: (row["name"].casefold(), row["key"]))
    return {"cards": rows, "count": len(rows),
            "registered": sum(row["registered"] for row in rows),
            "tradingview": sum(row["id"].startswith("tv_") for row in rows)}


def _testable_strategies() -> set[str]:
    """Registry names the background sweep can run: a buildable card with its data on hand."""
    from backtester.core.strategy_cards import load_all

    return {c.registry_key or c.id for c in load_all().values() if c.buildable and c.data_available}


@command("strategies.history",
         "Per registered strategy: tested or not, how many runs, when last, and the card-preset result.")
def strategies_history(ctx: Context, p: dict[str, Any]) -> Any:
    history = bgqueue.strategy_history(_queue_results(ctx), ctx.settings.asset)
    testable = _testable_strategies()
    rows = []
    for name, family in available_strategies():
        h = history.get(name, bgqueue.StrategyHistory(name))
        rows.append({
            "name": name, "family": family, "testable": name in testable, "tested": h.tested,
            "runs": h.runs, "evaluable": h.evaluable, "ranked": h.ranked, "positive": h.positive,
            "last_at": h.last_at,
            "last_tested": bgqueue.format_when(h.last_at) if h.tested else "never",
            "result": h.result_text if (h.tested or name in testable) else "no card or data to test it",
            "preset": dataclasses.asdict(h.preset) if h.preset else None,
        })
    return {"asset": ctx.settings.asset, "rows": rows,
            "tested": sum(1 for r in rows if r["tested"]),
            "untested": sum(1 for r in rows if not r["tested"] and r["testable"])}


@command("strategies.source", "Catalogue path of the file that defines a strategy, or null.",
         (P("name", "string", "Registered strategy name.", True),))
def strategies_source(ctx: Context, p: dict[str, Any]) -> Any:
    import inspect

    from backtester.core.strategies import REGISTRY

    func = REGISTRY.get(p["name"])
    if func is None:
        return {"path": None}
    try:
        rel = str(Path(inspect.getfile(func)).resolve().relative_to(docs_browser.REPO))
    except (TypeError, OSError, ValueError):
        return {"path": None}
    # The catalogue is an allowlist: a strategy file missing from index/INDEX.json fails closed.
    return {"path": rel if any(e.path == rel for e in ctx.catalog()) else None}


@command("roster.list", "The strategies the Backtest will sweep, with labels and warm-up bars.")
def roster_list(ctx: Context, p: dict[str, Any]) -> Any:
    return {"entries": [_entry(e) for e in ctx.roster], "count": len(ctx.roster)}


@command("roster.add", "Add a strategy to the roster; signal defaults fill params you omit.",
         (P("name", "string", "Registered strategy name.", True),
          P("params", "json", "Object of explicit params; these win over the signal defaults.")),
         read_only=False)
def roster_add(ctx: Context, p: dict[str, Any]) -> Any:
    explicit = p.get("params") or {}
    if not isinstance(explicit, dict):
        raise CommandError("bad_params", 'parameter "params" must be an object')
    entry = ctx.roster.add(p["name"], **merged_params(p["name"], ctx.signals, explicit))
    ctx.persist_roster()
    return {"added": _entry(entry), "count": len(ctx.roster)}


@command("roster.remove", "Remove a roster entry by its generated label.",
         (P("label", "string", "Label such as rsi_14_30_50.", True),), read_only=False)
def roster_remove(ctx: Context, p: dict[str, Any]) -> Any:
    removed = ctx.roster.remove(p["label"])
    ctx.persist_roster()
    return {"removed": _entry(removed), "count": len(ctx.roster)}


@command("roster.toggle", "Toggle the highlighted strategy configuration in the roster.",
         (P("name", "string", "Registered strategy name.", True),
          P("params", "json", "Explicit parameters (optional).")), read_only=False)
def roster_toggle(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core.strategies import build

    name, params = p["name"], p.get("params") or {}
    if not isinstance(params, dict):
        raise CommandError("bad_params", "params must be an object")
    matching = [e for e in ctx.roster if e.name == name]
    if not params and len(matching) == 1:
        return roster_remove(ctx, {"label": matching[0].label})
    merged = merged_params(name, ctx.signals, params)
    if name not in dict(available_strategies()):
        raise CommandError("bad_params", f"Unknown strategy {name!r}")
    label = build(name, **merged).name
    if any(e.label == label for e in matching):
        return roster_remove(ctx, {"label": label})
    if matching and not params:
        raise CommandError("bad_params", "Several versions are in the roster; highlight one on the right to remove it")
    return roster_add(ctx, {"name": name, "params": params})


@command("roster.add_all", "Add every missing registered strategy using the signal defaults.", read_only=False)
def roster_add_all(ctx: Context, p: dict[str, Any]) -> Any:
    present = {e.name for e in ctx.roster}
    # Validate all additions before replacing the roster or saving anything.
    roster = Roster(ctx.roster.entries)
    added = [_entry(roster.add(name, **merged_params(name, ctx.signals)))
             for name, _ in available_strategies() if name not in present]
    ctx.roster = roster
    ctx.persist_roster()
    return {"added": added, "count": len(roster)}


FORWARD_GRACE_S = 4  # Coinbase publishes a closed minute a moment after it closes


def forward_coins() -> list[str]:
    """Coins a Forwardtest can watch: every Coinbase USD market of the cached coins."""
    from . import pricefeed

    try:
        products = pricefeed.stream_products()
    except Exception:  # noqa: BLE001 - the offline fallback list covers every failure
        products = list(pricefeed.FALLBACK_PRODUCTS)
    return sorted({p.split("-")[0] for p in products if p.endswith("-USD")})


def _forward_check_all(rt: "Runtime", plan: dict[str, Any]) -> dict[str, Any]:
    """One check of every planned coin, each settled and forecast on its own."""
    out: dict[str, Any] = {}
    for asset in plan["assets"]:
        if rt.forward_stop.is_set():
            break
        try:
            r = forwardtest.tick(asset, plan["trials"], plan["horizons"], plan["cost"], stop=rt.forward_stop,
                                 code=plan["code"], tune=plan["tune"])
            out[asset] = {"at": time.time(), "bar": r["bar"], "recorded": r["recorded"], "message": r["message"]}
        except Exception as exc:  # noqa: BLE001 - one coin's failure must not stop the others
            out[asset] = {"at": time.time(), "error": f"{type(exc).__name__}: {exc}"[:300]}
        with rt.lock:
            rt.forward_last[asset] = out[asset]
    return out


def _forward_runner(rt: "Runtime") -> None:
    """Check every planned coin once per closed minute until stopped. Runs on its own thread."""
    checked_minute = -1
    try:
        while not rt.forward_stop.is_set():
            with rt.lock:
                plan = rt.forward_plan
            if plan is None:
                break
            now = time.time()
            minute = int(now // 60)
            if minute != checked_minute and now % 60 >= FORWARD_GRACE_S:
                checked_minute = minute
                with rt.lock:
                    rt.forward_busy = True
                try:
                    _forward_check_all(rt, plan)
                finally:
                    with rt.lock:
                        rt.forward_busy = False
            rt.forward_stop.wait(1.0)
    finally:
        with rt.lock:
            rt.forward_thread = None
            rt.forward_busy = False


@command("forwardtest.start", "Prepare an adaptive paper forward test (forwardtest.run starts checking).",
         (P("scope", "string", "all, roster, or combinations."),
          P("horizons", "json", "Subset of 1, 5, 10 and 30 minutes. Default: all four."),
          P("combinations", "json", "Lists of strategy names or roster labels."),
          P("mode", "string", "Combination rule: all, any, vote or mean."),
          P("coins", "json", "Coins to test: a list, or \"all\" for every Coinbase USD market; default the "
                             "Settings asset."),
          P("optimize", "bool", "Auto-optimize (default true): after a miss, move to a neighbouring setting "
                                "that tested superior on paired calls and save it as that trial's default.")),
         read_only=False)
def forwardtest_start(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core.strategies import COMBINE_MODES

    scope = p.get("scope", "all")
    horizons = p.get("horizons", list(forwardtest.HORIZONS))
    combos = p.get("combinations", [])
    mode = p.get("mode", "all")
    if scope not in ("all", "roster", "combinations") or mode not in COMBINE_MODES:
        raise CommandError("bad_params", "Choose a valid trial scope and combination rule")
    if (not isinstance(horizons, list) or not horizons
            or any(type(h) is not int or h not in forwardtest.HORIZONS for h in horizons)):
        raise CommandError("bad_params", "Horizons must be chosen from 1, 5, 10 and 30")
    if (not isinstance(combos, list) or len(combos) > 8
            or any(not isinstance(c, list) or not 2 <= len(c) <= 8
                   or any(not isinstance(v, str) for v in c) or len(set(c)) != len(c) for c in combos)):
        raise CommandError("bad_params", "Enter up to 8 combinations of 2–8 distinct names or roster labels")

    roster = {e.label: e for e in ctx.roster}
    entries = list(roster.values())
    if scope != "roster":
        present = {e.name for e in entries}
        entries.extend(RosterEntry(n, merged_params(n, ctx.signals))
                       for n, _ in available_strategies() if n not in present)
    labels = {e.label: e for e in entries}
    for e in entries:
        labels.setdefault(e.name, e)

    def spec(e: RosterEntry) -> dict:
        return forwardtest.member(e.name, e.params)

    trials = [{"label": e.label, "mode": "all", "members": [spec(e)]}
              for e in entries] if scope != "combinations" else []
    for combo in combos:
        unknown = next((name for name in combo if name not in labels), None)
        if unknown is not None:
            raise CommandError("bad_params", f"Unknown combination member: {unknown}")
        members = sorted((labels[n] for n in combo), key=lambda e: e.label)
        if len({e.label for e in members}) != len(members):
            raise CommandError("bad_params", "A combination cannot include the same configuration twice")
        trials.append({"label": f"{mode}({', '.join(e.label for e in members)})",
                       "mode": mode, "members": [spec(e) for e in members]})
    if not trials:
        raise CommandError("bad_params", "Add a strategy or enter a combination first")
    coins = p.get("coins")
    if coins in (None, [], ""):
        assets = [bgqueue.validate_asset(ctx.settings.asset)]
    elif coins == "all":
        assets = forward_coins()
    elif isinstance(coins, list) and all(isinstance(c, str) for c in coins):
        assets = list(dict.fromkeys(bgqueue.validate_asset(c) for c in coins))
    else:
        raise CommandError("bad_params", 'parameter "coins" must be a list of coins or "all"')
    if not assets:
        raise CommandError("bad_params", "no coin to test")
    tune = bool(p.get("optimize", True))
    cost = 2 * (ctx.settings.fee_bps + ctx.settings.slippage_bps)
    rt = ctx.runtime
    with rt.lock:
        if rt.forward_plan or rt.forward_busy or rt.forward_thread is not None:
            raise CommandError("failed", "A forward test is running or stopping")
        rt.forward_stop.clear()
        rt.forward_last = {}
        rt.forward_plan = {"asset": assets[0], "assets": assets, "trials": trials,
                           "horizons": tuple(sorted(set(horizons))), "cost": cost, "code": forwardtest.revision(),
                           "tune": tune}
    return {"asset": assets[0], "assets": assets, "trials": len(trials), "horizons": sorted(set(horizons)),
            "cost_bps": cost, "optimize": tune}


@command("forwardtest.run", "Start checking the prepared forward test in the background: every planned coin "
         "once per closed minute, on its own thread, whatever tab the console shows, until stopped.",
         read_only=False)
def forwardtest_run(ctx: Context, p: dict[str, Any]) -> Any:
    rt = ctx.runtime
    with rt.lock:
        if rt.forward_plan is None:
            raise CommandError("failed", "Prepare a forward test first (forwardtest.start)")
        if rt.forward_thread is None:
            rt.forward_started_at = time.time()
            rt.forward_thread = threading.Thread(target=_forward_runner, args=(rt,), name="forwardtest",
                                                 daemon=True)
            rt.forward_thread.start()
        return {"running": True, "assets": rt.forward_plan["assets"], "since": rt.forward_started_at}


@command("forwardtest.state", "Whether the background forward test runs, what it watches, and each coin's "
         "latest check.")
def forwardtest_state(ctx: Context, p: dict[str, Any]) -> Any:
    rt = ctx.runtime
    with rt.lock:
        plan = rt.forward_plan
        return {"running": plan is not None and rt.forward_thread is not None, "prepared": plan is not None,
                "busy": rt.forward_busy, "assets": list(plan["assets"]) if plan else [],
                "optimize": bool(plan["tune"]) if plan else None, "since": rt.forward_started_at,
                "last": {k: dict(v) for k, v in rt.forward_last.items()},
                "defaults_saved": len(forwardtest.load_defaults())}


@command("forwardtest.stop", "Stop issuing forward predictions in this session.", read_only=False)
def forwardtest_stop(ctx: Context, p: dict[str, Any]) -> Any:
    rt = ctx.runtime
    with rt.lock:
        rt.forward_stop.set()
        rt.forward_plan = None
        return {"stopping": rt.forward_busy}


@command("forwardtest.tick", "Settle due predictions and record the next paper calls.",
         read_only=False, long_running=True)
def forwardtest_tick(ctx: Context, p: dict[str, Any]) -> Any:
    rt = ctx.runtime
    with rt.lock:
        plan = rt.forward_plan
        if plan is None or rt.forward_busy:
            raise CommandError("failed", "Forwardtest is stopped or already checking prices")
        rt.forward_busy = True
    try:
        checks = _forward_check_all(rt, plan)
        rows = [r for a in plan["assets"] for r in forwardtest.status(a)]
        first = checks.get(plan["assets"][0], {})
        return {"asset": plan["asset"], "assets": plan["assets"], "checks": checks, "bar": first.get("bar"),
                "recorded": sum(c.get("recorded", 0) for c in checks.values()),
                "message": first.get("message") or first.get("error") or "", "rows": rows}
    finally:
        with rt.lock:
            rt.forward_busy = False


@command("forwardtest.status", "Read saved forward results, separately for each coin and forecast horizon.",
         (P("coins", "json", "Coins to read: a list or \"all\"; default the running test's coins, else the "
                             "Settings asset."),))
def forwardtest_status(ctx: Context, p: dict[str, Any]) -> Any:
    coins = p.get("coins")
    with ctx.runtime.lock:
        plan = ctx.runtime.forward_plan
    if coins == "all":
        assets = forward_coins()
    elif isinstance(coins, list) and coins:
        assets = [bgqueue.validate_asset(c) for c in coins]
    elif plan is not None:
        assets = list(plan["assets"])
    else:
        assets = [bgqueue.validate_asset(ctx.settings.asset)]
    return {"asset": assets[0], "assets": assets, "rows": [r for a in assets for r in forwardtest.status(a)]}


@command("roster.reset", "Restore the backtester's default comparison set.", read_only=False)
def roster_reset(ctx: Context, p: dict[str, Any]) -> Any:
    ctx.roster = Roster.default()
    ctx.persist_roster()
    return {"entries": [_entry(e) for e in ctx.roster], "count": len(ctx.roster)}


# -- signals -------------------------------------------------------------------------------------


def _signal_view(ctx: Context) -> dict[str, Any]:
    return {"values": ctx.signals.to_dict(),
            "groups": [{"group": g, "names": list(names)} for g, names in SIGNAL_GROUPS]}


@command("signals.get", "Signal parameter defaults, grouped by indicator.")
def signals_get(ctx: Context, p: dict[str, Any]) -> Any:
    return _signal_view(ctx)


@command("signals.save",
         "Validate and save signal defaults. Names you omit keep their current value.",
         (P("values", "json", "Object of signal name to value.", True),), read_only=False)
def signals_save(ctx: Context, p: dict[str, Any]) -> Any:
    values = p["values"]
    if not isinstance(values, dict):
        raise CommandError("bad_params", 'parameter "values" must be an object')
    names = [n for _, group in SIGNAL_GROUPS for n in group]
    unknown = sorted(set(values) - set(names))
    if unknown:
        raise CommandError("bad_params", f"unknown signal(s): {', '.join(unknown)}")
    updated = SignalDefaults(**{
        name: (coerce(name, str(values[name]), ctx.signals) if name in values
               else getattr(ctx.signals, name))
        for name in names})
    ctx.signals = from_dict(updated.to_dict())  # validates; a bad pair raises before anything sticks
    ctx.settings.signal_defaults = ctx.signals.to_dict()
    path = save_settings(ctx.settings)
    return {**_signal_view(ctx), "path": str(path), "affects": len(mapped_strategies())}


@command("signals.reset", "Restore and save the backtester's shipped signal values.", read_only=False)
def signals_reset(ctx: Context, p: dict[str, Any]) -> Any:
    ctx.signals = SignalDefaults()
    ctx.settings.signal_defaults = ctx.signals.to_dict()
    save_settings(ctx.settings)
    return _signal_view(ctx)


@command("signals.reference", "Indicator equations and when each strategy family fails.")
def signals_reference(ctx: Context, p: dict[str, Any]) -> Any:
    return {"signals": [{"signal": s, "equation": e, "family": f} for s, e, f in SIGNAL_REFERENCE],
            "families": [{"family": f, "note": n} for f, n in sorted(FAMILY_NOTES.items())]}


@command("research.get", "The research drivers, what each established, and the constraining findings.")
def research_get(ctx: Context, p: dict[str, Any]) -> Any:
    return {"drivers": [{"driver": d, "answers": a, "established": e} for d, a, e in RESEARCH_DRIVERS],
            "findings": list(RESEARCH_FINDINGS)}


# -- backtest ------------------------------------------------------------------------------------


def _backtest_status(ctx: Context) -> dict[str, Any]:
    s = ctx.state
    return {"running": ctx.runner.running, "phase": str(s.phase), "done": s.done, "total": s.total,
            "remaining": s.remaining, "percent": s.percent, "title": build_title(s),
            "error": s.error}


@command("backtest.status", "Progress of the sweep and the menu-bar style title line.")
def backtest_status(ctx: Context, p: dict[str, Any]) -> Any:
    return _backtest_status(ctx)


@command("backtest.cancel", "Ask the running sweep to stop at the next configuration boundary.",
         read_only=False)
def backtest_cancel(ctx: Context, p: dict[str, Any]) -> Any:
    ctx.runner.cancel()
    return {"cancelling": True}


@command("backtest.run", "CPCV sweep over the roster (or the listed roster labels), ranked by median "
         "Sharpe. Blocks until done.",
         (P("labels", "json", "Roster labels to test; default the whole roster."),),
         read_only=False, long_running=True)
def backtest_run(ctx: Context, p: dict[str, Any]) -> Any:
    roster = ctx.roster
    labels = p.get("labels")
    if labels is not None:
        if not isinstance(labels, list) or not labels or not all(isinstance(x, str) for x in labels):
            raise CommandError("bad_params", "labels must be a non-empty list of roster labels")
        unknown = [x for x in labels if x not in roster.labels]
        if unknown:
            raise CommandError("bad_params", f"not in the roster: {', '.join(unknown)}")
        roster = Roster([e for e in roster if e.label in labels])
    try:
        ctx.runner.start(roster, ctx.settings)
    except (RuntimeError, ValueError) as exc:
        raise CommandError("failed", str(exc)) from exc
    ctx.runner.join()
    outcome = ctx.runner.outcome
    if outcome is None:
        raise CommandError("failed", "the sweep produced no outcome")
    if outcome.error:
        raise CommandError("failed", outcome.error.splitlines()[0])
    skipped = [r for r in outcome.rows if not r.evaluable]
    message = f"done — {len(outcome.evaluable)} evaluable, {len(outcome.positive)} positive"
    if outcome.cancelled:
        message = "cancelled — partial results shown"
    if skipped:
        message += f" · {len(skipped)} skipped (warm-up or trade floor)"
    return {
        "rows": [{**dataclasses.asdict(r), "net_pct": r.median_return,
                  "net_pct_text": labelled(r.median_return, "backtest", "median net")}
                 for r in outcome.ranked()],
        "evaluable": len(outcome.evaluable), "positive": len(outcome.positive),
        "skipped": [{"label": r.label, "reason": r.reason} for r in skipped],
        "cancelled": outcome.cancelled, "message": message,
    }


@command("backtest.untested_sweep",
         "Run research/sweep_untested.py on this interpreter (30 minute limit).",
         read_only=False, long_running=True)
def backtest_untested_sweep(ctx: Context, p: dict[str, Any]) -> Any:
    try:
        result = subprocess.run(
            untested_sweep_command(REPO), capture_output=True, text=True, cwd=str(REPO),
            timeout=UNTESTED_SWEEP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise CommandError(
            "timeout", f"untested sweep timed out after {UNTESTED_SWEEP_TIMEOUT_S // 60} min") from None
    if result.returncode != 0:
        raise CommandError("failed", f"error: {failure_summary(result.stderr)}")
    return {"output": result.stdout[-200:]}


# -- dry-run replay ------------------------------------------------------------------------------


def _paper_view(ctx: Context) -> dict[str, Any]:
    session = ctx.session
    if session is None:
        raise CommandError("failed", "start a dry run first")
    s = session.summary()
    ctx.state.paper_return = session.pnl
    ctx.state.paper_fills = session.fill_count
    fills = [{"bar": f.bar_index, "when": f.when, "side": f.side, "reason": f.reason,
              "price": f.price, "units": f.units, "cost": f.cost, "equity": f.equity_after}
             for f in session.intended_fills()[-200:]]
    s["net_pct"] = s["pnl"]
    s["net_pct_text"] = labelled(s["pnl"], "paper", "net")
    return {"summary": s, "text": (
        f"bar {s['bar']}/{s['bars_total']}  {s['when']}   equity {s['equity']:,.2f}   "
        f"{s['net_pct_text']}   exposure {s['exposure']:.2f}   fills {s['fills']}   "
        f"live orders placed: {s['live_orders_placed']}"), "fills": fills, "mode": MODE_LABEL}


@command("paper.start", "Backtest one roster strategy or Top 5 preset (top5:N) and open a bar-by-bar dry-run replay.",
         (P("label", "string", "Roster label to replay, or top5:N for a Top 5 preset.", True),
          P("bars", "number", "Bars to advance right after starting (default 0).")),
         read_only=False, long_running=True)
def paper_start(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core.strategies import build

    label = p.get("label")
    if not label:
        raise CommandError("failed", "pick a strategy first")
    rank = presets_mod.parse_value(label)
    entry = None if rank is not None else next((e for e in ctx.roster if e.label == label), None)
    if rank is None and entry is None:
        raise CommandError("failed", "strategy left the roster")
    try:
        if rank is not None:
            # A Top 5 preset replays on the series it was fitted on, not on the Settings asset.
            preset = presets_mod.find_preset(rank)
            arrays = presets_mod.load_preset_arrays(preset, ctx.settings.data_dir)
            session = start_session(presets_mod.build_strategy(preset), arrays,
                                    engine_config(ctx.settings, interval=preset["interval"]))
        else:
            arrays = load_arrays(ctx.settings)
            session = start_session(build(entry.name, **entry.params), arrays,
                                    engine_config(ctx.settings))
    except Exception as exc:  # noqa: BLE001 - the type is the most useful part of a load failure
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    ctx.session = session
    ctx.runtime.session_label = label
    ctx.runtime.session_asset = (preset["asset"] if rank is not None else ctx.settings.asset)
    ctx.state.phase = Phase.PAPER
    if p.get("bars"):
        session.advance(int(p["bars"]))
    return _paper_view(ctx)


@command("paper.step", "Advance the dry-run replay by some bars.",
         (P("bars", "number", "Bars to advance (default 1)."),), read_only=False)
def paper_step(ctx: Context, p: dict[str, Any]) -> Any:
    if ctx.session is None:
        raise CommandError("failed", "start a dry run first")
    ctx.session.advance(int(p.get("bars", 1)))
    return _paper_view(ctx)


@command("paper.seek_end", "Jump the dry-run replay to its final bar.", read_only=False)
def paper_seek_end(ctx: Context, p: dict[str, Any]) -> Any:
    if ctx.session is None:
        raise CommandError("failed", "start a dry run first")
    ctx.session.seek_end()
    return _paper_view(ctx)


@command("paper.reset", "Rewind the dry-run replay to its first bar.", read_only=False)
def paper_reset(ctx: Context, p: dict[str, Any]) -> Any:
    if ctx.session is None:
        raise CommandError("failed", "start a dry run first")
    ctx.session.reset()
    return _paper_view(ctx)


@command("paper.summary", "The open dry-run replay's state and intended fills.")
def paper_summary(ctx: Context, p: dict[str, Any]) -> Any:
    return _paper_view(ctx)


# -- live run (the extension's dry-run tool) -----------------------------------------------------


@command("live.recommendation", "The strategy the Live Run tab would launch, and why.")
def live_recommendation(ctx: Context, p: dict[str, Any]) -> Any:
    return live_run.get_best_strategy()


@command("live.spawn_dryrun", "Run extension/tools/dryrun.js for a strategy (dry-run only).",
         (P("strategy", "string", "Strategy name or Top 5 label.", True),),
         read_only=False, long_running=True)
def live_spawn_dryrun(ctx: Context, p: dict[str, Any]) -> Any:
    out = live_run.run_dryrun(p["strategy"].strip())
    net = live_run.dryrun_net_pct(out["stdout"])
    out["net_pct"] = net
    out["net_pct_text"] = labelled(net, "dry-run", "net")
    return out


# -- Top 5 ---------------------------------------------------------------------------------------


def _asset_result(r) -> dict[str, Any]:
    return {**dataclasses.asdict(r), "net_pct": r.median_return,
            "net_pct_text": labelled(r.median_return, "backtest", "median net")}


@command("top5.list", "The five recommended configurations with their evidence and transfer tests.")
def top5_list(ctx: Context, p: dict[str, Any]) -> Any:
    configs = top5_mod.load_top5()  # EvidenceUnavailable carries the regenerate command
    return {
        "configs": [{
            "rank": c.rank, "label": c.label, "horizon": c.horizon,
            "members": list(c.members), "mode": c.mode,
            "home": _asset_result(c.home) if c.home else None,
            "transfers": [_asset_result(t) for t in c.transfers],
        } for c in configs],
        "home_asset": top5_mod.HOME_ASSET,
        "transfer_assets": sorted({t.asset for c in configs for t in c.transfers}),
        "repro_command": top5_mod.REPRO_COMMAND,
    }


@command("top5.presets",
         "The five Top 5 configurations as one-click presets for Analyze, Live Run and Execute.")
def top5_presets(ctx: Context, p: dict[str, Any]) -> Any:
    return {"presets": presets_mod.build_presets(), "home_asset": top5_mod.HOME_ASSET,
            "note": "Parameters are the SOL-tuned values of research/sweep.py HORIZONS; "
                    "net % is the backtest median path return, not a live result."}


@command("top5.add_to_roster",
         "Add the member signals of Top 5 configurations to the roster (all when no ranks given).",
         (P("ranks", "json", "List of ranks, e.g. [1, 3]. Omit for all five."),), read_only=False)
def top5_add_to_roster(ctx: Context, p: dict[str, Any]) -> Any:
    configs = top5_mod.load_top5()
    ranks = p.get("ranks")
    if ranks is not None:
        if not isinstance(ranks, list) or not all(isinstance(r, int) and not isinstance(r, bool)
                                                  for r in ranks):
            raise CommandError("bad_params", 'parameter "ranks" must be a list of whole numbers')
        configs = [c for c in configs if c.rank in ranks]
        missing = sorted(set(ranks) - {c.rank for c in configs})
        if missing:
            raise CommandError("failed", f"no Top 5 configuration with rank {missing}")
    added: list[str] = []
    present: list[str] = []
    for name in top5_mod.roster_candidates(configs):
        try:
            ctx.roster.add(name, **merged_params(name, ctx.signals))
            added.append(name)
        except RosterError:
            present.append(name)  # clicking twice must not become a wall of errors
    ctx.persist_roster()
    return {"added": added, "present": present, "count": len(ctx.roster)}


# -- Analyze, Cumulative -------------------------------------------------------------------------


@command("analyze.assets", "Cached (asset, interval) price series available to Analyze.")
def analyze_assets(ctx: Context, p: dict[str, Any]) -> Any:
    return [{"asset": a, "interval": i} for a, i in analyze_mod.available_assets()]


@command("analyze.run", "Replay every strategy up to a moment and report what each would decide.",
         (P("asset", "string", "Coin symbol, e.g. SOL.", True),
          P("interval", "string", "Bar interval (default 1d)."),
          P("as_of", "string", "YYYY-MM-DD or YYYY-MM-DD HH:MM UTC; omit for the last bar."),
          P("preset", "string", "top5:N: judge only that Top 5 configuration, with its parameters.")))
def analyze_run(ctx: Context, p: dict[str, Any]) -> Any:
    raw = (p.get("as_of") or "").strip()
    when = analyze_mod.parse_as_of(raw) if raw else None
    rank = presets_mod.parse_value(p["preset"]) if p.get("preset") else None
    if p.get("preset") and rank is None:
        raise CommandError("bad_params", 'parameter "preset" must look like top5:1')
    if rank is not None:
        preset = presets_mod.find_preset(rank)
        result = analyze_mod.analyse(
            p["asset"], p.get("interval", preset["interval"]), as_of=when, keys=[],
            extra=[(preset["label"], "top5", presets_mod.build_strategy(preset))])
    else:
        result = analyze_mod.analyse(p["asset"], p.get("interval", "1d"), as_of=when)
    net = result.net_pct
    return {
        "headline": result.headline, "truncated": result.truncated,
        "net_pct": net, "net_pct_text": labelled(net, "backtest", "data price change"),
        "decisions": [{"name": d.name, "family": d.family, "action": d.action, "detail": d.detail,
                       "warmup": d.warmup, "bars": d.bars} for d in result.decisions],
        "actions": result.actions,
    }


@command("cumulative.summary", "Every committed result file, with the evidence floor applied.")
def cumulative_summary(ctx: Context, p: dict[str, Any]) -> Any:
    summaries = cumulative_mod.load_all()
    return {
        "headline": cumulative_mod.headline(summaries),
        "totals": cumulative_mod.totals(summaries),
        "files": [{
            "source": s.source, "rankable": len(s.rankable), "below_floor": len(s.below_floor),
            "positive": s.positive, "made_money": s.made_money, "median_sharpe": s.median_sharpe,
            "path_range": s.path_range,
            "best": ({"label": s.best.label, "median_sharpe": s.best.median_sharpe,
                      "net_pct": s.best.median_return,
                      "net_pct_text": labelled(s.best.median_return, "backtest", "median net")}
                     if s.best else None),
        } for s in summaries],
        "casualties": [{"source": r.source, "label": r.label, "median_sharpe": r.median_sharpe,
                        "trades": r.trades or 0, "n_paths": r.n_paths or 0}
                       for r in cumulative_mod.floor_casualties(summaries)],
    }


# -- the background queue ------------------------------------------------------------------------


def _missing_series(ctx: Context) -> list[bgqueue.MissingSeries]:
    try:
        return bgqueue.missing_series(ctx.settings.asset, data_dir=ctx.settings.data_dir)
    except ValueError:
        # An unusable asset symbol is the Settings tab's problem to report.
        return []


def _queue_progress(ctx: Context, state: bgqueue.QueueState) -> dict[str, Any]:
    alive = bgcontrol.is_running()
    detail = f" · now: {state.current}" if state.current and alive else ""
    live = " · worker alive" if alive else ""
    summary = bgqueue.summarise(state, ctx.runtime.queue_results, ctx.settings.asset,
                                worker_alive=alive) + detail + live
    return {"state": dataclasses.asdict(state), "alive": alive, "summary": summary,
            "percent": state.percent, "remaining": state.remaining}


def _queue_results(ctx: Context) -> list[bgqueue.JobResult]:
    """Every result so far, reading only what the worker appended since the last call.

    The results file grows without bound, so re-reading it whole on each poll would make watching
    a sweep quadratic in its length.
    """
    rt = ctx.runtime
    with rt.lock:
        fresh, cursor, restarted = bgqueue.read_results_since(rt.queue_cursor)
        if restarted:
            rt.queue_results = []  # truncated or replaced: what we hold belongs to a dead sweep
        rt.queue_results.extend(fresh)
        rt.queue_cursor = cursor
        return list(rt.queue_results)


def _queue_state() -> bgqueue.QueueState:
    """Do not attribute the preceding sweep's status to the selected file."""
    state = bgqueue.read_state()
    selected = bgqueue.active_results_path()
    if state.results_path:
        if Path(state.results_path) != selected:
            return bgqueue.QueueState()
    elif selected != bgqueue.RESULTS_PATH:
        return bgqueue.QueueState()
    return state


@command("queue.progress", "Background sweep progress line (cheap; no results re-read).")
def queue_progress(ctx: Context, p: dict[str, Any]) -> Any:
    return _queue_progress(ctx, _queue_state())


@command("queue.status", "Background sweep: progress, missing price data and the ranked leaderboard.")
def queue_status(ctx: Context, p: dict[str, Any]) -> Any:
    results = _queue_results(ctx)
    ranked, floor = bgqueue.leaderboard(results, ctx.settings.asset)
    missing = _missing_series(ctx)
    fetch_log = bgqueue.BG_DIR / "fetch.log"
    return {
        **_queue_progress(ctx, _queue_state()),
        "missing": [{"asset": m.asset, "interval": m.interval, "command": m.command_text}
                    for m in missing],
        "fetch_log": str(fetch_log) if fetch_log.exists() else None,
        "ranked": [{**dataclasses.asdict(r), "label": r.label, "net_pct": r.median_return,
                    "net_pct_text": labelled(r.median_return, "backtest", "median net")}
                   for r in ranked[:200]],
        "floor": [{**dataclasses.asdict(r), "label": r.label,
                   "why": r.reason or f"under the {bgqueue.MIN_TRADES}-trade floor"}
                  for r in floor[:200]],
        "ranked_total": len(ranked), "floor_total": len(floor),
    }


@command("queue.start", "Start the low-priority background sweep for the configured asset.",
         read_only=False)
def queue_start(ctx: Context, p: dict[str, Any]) -> Any:
    try:
        bgcontrol.start(ctx.settings.asset)
    except Exception as exc:  # noqa: BLE001
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    return {"started": True, "asset": ctx.settings.asset}


@command("queue.start_fresh", "Start a fresh background sweep while preserving previous results.",
         read_only=False)
def queue_start_fresh(ctx: Context, p: dict[str, Any]) -> Any:
    try:
        bgcontrol.start(ctx.settings.asset, fresh=True)
    except Exception as exc:  # noqa: BLE001
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    return {"started": True, "asset": ctx.settings.asset}


BACKTEST_SCOPES = ("selected", "untested", "undertested", "all")
# "Little testing": fewer recorded configurations than this for the asset.
UNDERTESTED_MIN_RUNS = 3


@command("queue.backtest",
         "Backtest strategies in the background at each card's own parameters (all horizons). "
         "Scope selected, untested, undertested (never tested, or fewer than min_runs recorded "
         "configurations; also runs the near variations so each gets several) or all; skips "
         "configurations already recorded for this code and data.",
         (P("scope", "string", "selected, untested, undertested or all.", True),
          P("names", "json", "List of registered strategy names; required when scope is selected."),
          P("min_runs", "number", f"undertested only: fewer recorded runs than this counts as little "
                                  f"testing (default {UNDERTESTED_MIN_RUNS}).")),
         read_only=False)
def queue_backtest(ctx: Context, p: dict[str, Any]) -> Any:
    scope = p["scope"]
    if scope not in BACKTEST_SCOPES:
        raise CommandError("bad_params", f"scope must be one of {', '.join(BACKTEST_SCOPES)}")
    testable = _testable_strategies()
    max_tier = 0
    note = ""
    if scope == "selected":
        names = p.get("names")
        if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
            raise CommandError("bad_params", 'scope "selected" needs "names" as a non-empty list')
        untestable = [n for n in names if n not in testable]
        if untestable:
            raise CommandError(
                "failed", f"cannot backtest {', '.join(untestable)}: no buildable card with data")
    elif scope == "untested":
        history = bgqueue.strategy_history(_queue_results(ctx), ctx.settings.asset)
        names = sorted(n for n in testable if n not in history)
    elif scope == "undertested":
        min_runs = int(UNDERTESTED_MIN_RUNS if p.get("min_runs") is None else p["min_runs"])
        if min_runs < 1:
            raise CommandError("bad_params", "min_runs must be at least 1")
        history = bgqueue.strategy_history(_queue_results(ctx), ctx.settings.asset)
        never = sorted(n for n in testable if n not in history)
        thin = sorted(n for n in testable if n in history and history[n].runs < min_runs)
        names = never + thin
        # The card's own parameters are one configuration per horizon; a strategy with little
        # testing needs more than that, so the near variations run too.
        max_tier = 1
        note = f" ({len(never)} never tested, {len(thin)} with fewer than {min_runs} runs)"
    else:
        names = sorted(testable)
    asset = ctx.settings.asset
    if not names:
        return {"started": False, "scope": scope, "strategies": [], "jobs": 0,
                "message": "nothing to backtest: every strategy already has a recorded run"
                + (" and enough testing" if scope == "undertested" else "")}
    jobs = bgqueue.build_queue(asset, max_tier=max_tier, strategies=names)
    todo = bgqueue.pending(jobs, bgqueue.completed_ids(bgqueue.read_results()))
    if not todo:
        return {"started": False, "scope": scope, "strategies": names, "jobs": 0,
                "message": f"already tested: all {len(jobs)} configuration(s) have recorded results"}
    try:
        bgcontrol.start(asset, max_tier=max_tier, strategies=names)
    except RuntimeError as exc:
        raise CommandError(
            "failed", f"{exc}; stop it on the Queue tab first, or wait for it to finish") from exc
    except Exception as exc:  # noqa: BLE001
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    return {"started": True, "scope": scope, "strategies": names, "jobs": len(todo), "asset": asset,
            "message": f"started: {len(todo)} configuration(s) across {len(names)} strategy(ies){note}, "
                       "results appear in the table as they finish"}


@command("queue.stop", "Ask the background sweep to stop at the next job boundary.", read_only=False)
def queue_stop(ctx: Context, p: dict[str, Any]) -> Any:
    return {"stopping": bool(bgcontrol.stop())}


@command("queue.fetch",
         "Fetch the price series the sweep is missing (the one network action; no sweep starts).",
         read_only=False)
def queue_fetch(ctx: Context, p: dict[str, Any]) -> Any:
    missing = _missing_series(ctx)
    if not missing:
        return {"fetching": [], "log": None}
    try:
        bgcontrol.start_fetch([(m.asset, m.interval) for m in missing])
    except Exception as exc:  # noqa: BLE001
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    return {"fetching": [{"asset": m.asset, "interval": m.interval} for m in missing],
            "log": str(bgqueue.BG_DIR / "fetch.log")}


# -- compound five-minute scorecard (backtester/core/scorecard.py; soltui/compound.py) ----------


def _compound_asset(ctx: Context, p: dict[str, Any]) -> str:
    return str(p.get("asset") or ctx.settings.asset)


def _compound(fn, *args, **kwargs) -> Any:
    """Run a compound helper, mapping its user-facing errors onto the `failed` envelope."""
    from backtester.core import compound as cbt
    from backtester.core import scorecard as sc
    try:
        return fn(*args, **kwargs)
    except (compound_mod.CompoundError, cbt.CompoundDataError, sc.ScorecardError) as exc:
        raise CommandError("failed", str(exc)) from exc


@command("compound.catalog", "Every five-minute scorecard component and gate: formula, parameters, "
         "when it works and when it fails; plus catalogue entries that are not direction calls.")
def compound_catalog(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core import scorecard as sc
    return sc.catalog()


@command("compound.config", "The compound configuration for a coin (the shared base with that coin's "
         "own settings on top), its hash, the coin's own overrides, and the scheduled-event list.",
         (P("asset", "string", "Coin; default the configured asset."),))
def compound_config(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core import scorecard as sc
    asset = _compound_asset(ctx, p)
    state = _compound(compound_mod.load_state, asset)
    return {"config": state["config"], "config_hash": sc.config_hash(state["config"]),
            "events": state["events"], "asset": state["asset"],
            "own_settings": state["overrides"].get(state["asset"], {}),
            "coins_with_own_settings": sorted(state["overrides"])}


@command("compound.save",
         "Update the compound configuration: a partial patch {components: {id: {enabled, weight, "
         "params}}, aggregate, execution, blocked_hours}, and/or replace the event list.",
         (P("patch", "json", "Partial configuration to merge."),
          P("events", "json", "Scheduled events [{ts: epoch seconds, title}] (replaces the list)."),
          P("asset", "string", "With scope coin: the coin whose own settings change."),
          P("scope", "string", "all (default: the shared base every coin starts from) or coin.")),
         read_only=False)
def compound_save(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core import scorecard as sc
    patch, events = p.get("patch"), p.get("events")
    scope = p.get("scope") or "all"
    if scope not in ("all", "coin"):
        raise CommandError("bad_params", "scope must be all or coin")
    if patch is not None and not isinstance(patch, dict):
        raise CommandError("bad_params", "patch must be an object")
    if events is not None and not isinstance(events, list):
        raise CommandError("bad_params", "events must be a list")
    if patch is None and events is None:
        raise CommandError("bad_params", "give a patch, events, or both")
    asset = _compound_asset(ctx, p) if scope == "coin" else None
    state = _compound(compound_mod.save_state, patch, events, asset=asset)
    if asset is None and p.get("asset"):
        state = _compound(compound_mod.load_state, p["asset"])  # show the asked-for coin's view
    return {"config": state["config"], "config_hash": sc.config_hash(state["config"]),
            "events": state["events"], "asset": state["asset"], "scope": scope}


@command("compound.reset", "Restore defaults: scope coin clears one coin's own settings; scope all resets "
         "the shared base; scope everything also clears every coin's own settings.",
         (P("asset", "string", "With scope coin: the coin to clear."),
          P("scope", "string", "all (default), coin or everything.")),
         read_only=False)
def compound_reset(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core import scorecard as sc
    scope = p.get("scope") or "all"
    if scope not in ("all", "coin", "everything"):
        raise CommandError("bad_params", "scope must be all, coin or everything")
    asset = _compound_asset(ctx, p) if scope == "coin" else None
    state = _compound(compound_mod.save_state, None, None, reset=True, asset=asset,
                      reset_all=scope == "everything")
    if asset is None and p.get("asset"):
        state = _compound(compound_mod.load_state, p["asset"])
    return {"config": state["config"], "config_hash": sc.config_hash(state["config"]), "scope": scope}


@command("compound.signal",
         "Score the latest CLOSED 5m bar live (public Coinbase candles; Hyperliquid and RSS only for "
         "components that need them) and explain every metric's score, weight and vote. No order path.",
         (P("asset", "string", "Asset symbol; default the configured asset."),),
         long_running=True)
def compound_signal(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.signal, _compound_asset(ctx, p), wallet_address=ctx.settings.solana_address,
                     hyperliquid_address=ctx.settings.hyperliquid_address)


@command("compound.backtest",
         "Backtest the saved compound and each enabled component alone on cached 5m data: next-bar hit "
         "rate and engine P&L net of fees, in-sample vs out-of-sample. Appends to the results file.",
         (P("asset", "string", "Asset symbol; default the configured asset."),
          P("all", "bool", "Every coin with cached data, in parallel processes, each with its own settings."),
          P("perturb", "bool", "Also run one-at-a-time parameter variations."),
          P("aggregate_grid", "bool", "Also run threshold, gate, regime and leverage variations."),
          P("frontier", "bool", "Also run every metric alone (on or off): its strongest 2% of readings, "
                                "held 1 h, 4 h and 24 h.")),
         read_only=False, long_running=True)
def compound_backtest(ctx: Context, p: dict[str, Any]) -> Any:
    if p.get("all"):
        return _compound(compound_mod.backtest_all, perturb=bool(p.get("perturb")),
                         aggregate_grid=bool(p.get("aggregate_grid")), frontier=bool(p.get("frontier")), progress=ctx.progress)
    return _compound(compound_mod.backtest, _compound_asset(ctx, p), perturb=bool(p.get("perturb")),
                     aggregate_grid=bool(p.get("aggregate_grid")), frontier=bool(p.get("frontier")), progress=ctx.progress)


@command("compound.results", "The latest compound backtest run and the all-time OOS leaderboard "
         "(evidence floor applied: thin rows are listed, never ranked).",
         (P("asset", "string", "Limit to one asset; default every asset."),))
def compound_results(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.latest_results, p.get("asset") or None)


@command("compound.forward_tick",
         "Forward test: record the call for the latest closed 5m bar (once per configuration) and "
         "resolve earlier calls whose next bar has closed. Read-only market data; no orders.",
         (P("asset", "string", "Asset symbol; default the configured asset."),),
         read_only=False, long_running=True)
def compound_forward_tick(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.forward_tick, _compound_asset(ctx, p),
                     wallet_address=ctx.settings.solana_address,
                     hyperliquid_address=ctx.settings.hyperliquid_address)


@command("compound.unattended_start",
         "Start fully unattended forward training: a detached background process that records and "
         "resolves one call per closed 5m bar (learning from each) until stopped. Survives closing the "
         "console. Read-only market data; no orders.",
         (P("asset", "string", "Asset symbol; default the configured asset."),
          P("all", "bool", "Every coin: one process each, staggered a few seconds apart.")),
         read_only=False)
def compound_unattended_start(ctx: Context, p: dict[str, Any]) -> Any:
    if p.get("all"):
        return _compound(compound_mod.start_unattended_all)
    return _compound(compound_mod.start_unattended, _compound_asset(ctx, p))


@command("compound.unattended_stop", "Stop the unattended forward training for an asset (it finishes "
         "the current tick, then exits).",
         (P("asset", "string", "Asset symbol; default the configured asset."),
          P("all", "bool", "Stop every coin's unattended run.")),
         read_only=False)
def compound_unattended_stop(ctx: Context, p: dict[str, Any]) -> Any:
    if p.get("all"):
        return _compound(compound_mod.stop_unattended_all)
    return _compound(compound_mod.stop_unattended, _compound_asset(ctx, p))


@command("compound.autopilot",
         "Turn autopilot for the compound 5m trainer on or off. On: tuning runs, each forward tick "
         "adopts evidence-gated tuned settings as the coin's own, and every coin's unattended loop is "
         "kept running (any coin not running starts now). Off: no automatic adoption or restarts; "
         "running loops keep going. Read-only market data; no orders.",
         (P("enabled", "bool", "true turns autopilot on, false turns it off.", required=True),),
         read_only=False)
def compound_autopilot(ctx: Context, p: dict[str, Any]) -> Any:
    on = bool(p["enabled"])
    _compound(compound_mod.set_autopilot, on)
    started = _compound(compound_mod.autopilot_ensure) if on else None
    return {**_compound(compound_mod.autopilot_status), "ensure": started}


@command("compound.autopilot_status",
         "Autopilot for the compound 5m trainer: the switch, which coins train now, the LaunchAgent "
         "that keeps them training, and the most recent automatic adoptions of tuned settings.")
def compound_autopilot_status(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.autopilot_status)


@command("compound.autopilot_ensure",
         "With autopilot on, start every coin's unattended forward-training loop that is not running "
         "(what the autopilot LaunchAgent runs every five minutes). Does nothing when autopilot is off.",
         read_only=False)
def compound_autopilot_ensure(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.autopilot_ensure)


@command("compound.overview", "One row per coin: its own settings, cached data, latest backtest verdict, "
         "forward-test calls and hit rate, paper dollars, and whether unattended training runs.")
def compound_overview(ctx: Context, p: dict[str, Any]) -> Any:
    return {"coins": _compound(compound_mod.overview)}


@command("compound.unattended_status", "Whether unattended forward training is running for an asset, "
         "since when, and its last log line.",
         (P("asset", "string", "Asset symbol; default the configured asset."),))
def compound_unattended_status(ctx: Context, p: dict[str, Any]) -> Any:
    return _compound(compound_mod.unattended_status, _compound_asset(ctx, p))


@command("compound.forward_status",
         "Forward-test hit rates for the compound, the compound without gates, and each component "
         "alone, plus the most recent calls.",
         (P("asset", "string", "Asset symbol; default the configured asset."),
          P("current_only", "bool", "Only calls made under the current configuration.")))
def compound_forward_status(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core import scorecard as sc
    h = None
    if p.get("current_only"):
        h = sc.config_hash(_compound(compound_mod.load_state)["config"])
    return _compound(compound_mod.forward_status, _compound_asset(ctx, p), h)


# -- liquidity (read-only view of the aero-lp daemon, plus its KILL file) ------------------------


def _liq_table(table: liq.Table) -> dict[str, Any]:
    return {"headers": list(table.headers), "rows": [list(r) for r in table.rows]}


def _liq_mtime(home: Path, name: str) -> int | None:
    try:
        return (home / name).stat().st_mtime_ns
    except OSError:
        return None


@command("liquidity.status", "Aero LP daemon state files: summary, positions, scout, experiments, actions.")
def liquidity_status(ctx: Context, p: dict[str, Any]) -> Any:
    home = liq.state_dir()
    status = liq.load_status(home)
    scout = liq.load_scout(home)
    killed_file = liq.is_killed(home)
    empty = liq.Table((), ())
    out: dict[str, Any] = {
        "home": str(home),
        "status_ok": status.data is not None, "status_reason": status.reason,
        "scout_ok": scout.data is not None, "scout_reason": scout.reason,
        "kill_file": killed_file,
        "killed": killed_file or bool(status.data and status.data.get("killed")),
        "signature": [_liq_mtime(home, liq.STATUS_FILE), _liq_mtime(home, liq.SCOUT_FILE),
                      _liq_mtime(home, liq.KILL_FILE)],
        "summary": None, "wallet": "", "mode_badge": None, "live": False,
        "scout_note": (liq.scout_line(scout.data) if scout.data
                       else f"Scout: no data. {scout.reason}"),
        "tables": {
            "positions": _liq_table(liq.positions_table(status.data) if status.data else empty),
            "experiments": _liq_table(liq.experiments_table(status.data) if status.data else empty),
            "actions": _liq_table(liq.actions_table(status.data) if status.data else empty),
            "scout": _liq_table(liq.scout_table(scout.data) if scout.data else empty),
        },
    }
    if status.data is not None:
        s = liq.summarise(status.data, kill_file_present=killed_file)
        out["summary"] = s.line()
        out["live"] = bool(s.live)
        out["mode_badge"] = liq.mode_badge_text(s.mode)
        out["wallet"] = liq.wallet_line(status.data)
    return out


_SCOUT_FIELDS = ("pool", "pair", "token0", "token1", "tick_spacing", "fee_pct", "tvl_usd", "volume_24h_usd",
                 "expected_net_apr", "backtest_net_apr", "backtest_days", "best_mode", "best_half_width_pct",
                 "confidence", "flags", "gauge_active", "history_days", "break_even_deposit_usd")
# Every APR here is in percent: apr_realized (STATE_FILES.md) and the scout's *_net_apr (scout.format_report).
_POSITION_FIELDS = ("slot", "token_id", "pool", "pair", "tick_spacing", "in_range", "value_usd", "deposited_usd",
                    "pnl_usd", "pnl_vs_hodl_usd", "apr_realized", "opened_at", "decision")
_WALLET_TOKEN_FIELDS = ("symbol", "address", "amount", "usd", "idle")


def _pick(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: row[k] for k in fields if isinstance(row, dict) and k in row}


@command("liquidity.data",
         "Machine-readable aero-lp state for the extension's alerts: the scout's measured pools (expected and "
         "backtest net APR, in percent), the daemon's positions and its idle wallet balances. Read-only.",
         (P("top", "number", "Scout pools to return, best first (default 25, at most 100)."),))
def liquidity_data(ctx: Context, p: dict[str, Any]) -> Any:
    top = p.get("top", 25)
    if not math.isfinite(float(top)) or int(top) < 1:
        raise CommandError("bad_params", 'parameter "top" must be a positive number')
    home = liq.state_dir()
    status = liq.load_status(home)
    scout = liq.load_scout(home)
    sdoc = scout.data or {}
    st = status.data or {}
    wallet = st.get("wallet") if isinstance(st.get("wallet"), dict) else {}
    return {
        "status_ok": status.data is not None, "status_reason": status.reason,
        "scout_ok": scout.data is not None, "scout_reason": scout.reason,
        "killed": liq.is_killed(home) or bool(st.get("killed")),
        "mode": st.get("mode"),
        "scout": {
            "generated_at": sdoc.get("generated_at"), "deposit_usd": sdoc.get("deposit_usd"),
            "pools": [_pick(r, _SCOUT_FIELDS) for r in (sdoc.get("pools") or [])[:min(100, int(top))]
                      if isinstance(r, dict)],
            "measured": True,
        },
        "positions": [_pick(r, _POSITION_FIELDS) for r in liq.positions_of(st)],
        "wallet": {"idle_usd": wallet.get("idle_usd"), "deployed_usd": wallet.get("deployed_usd"),
                   "tokens": [_pick(t, _WALLET_TOKEN_FIELDS) for t in (wallet.get("tokens") or [])
                              if isinstance(t, dict)]},
    }


def _liq_write(on: bool) -> dict[str, Any]:
    try:
        liq.set_kill(on)
    except OSError as exc:
        raise CommandError("failed", f"could not {'create' if on else 'delete'} KILL: {exc}") from exc
    return {"killed": liq.is_killed(), "home": str(liq.state_dir())}


@command("liquidity.kill",
         "Create the aero-lp KILL file: the daemon pauses and sends no transactions. Safe to call.",
         read_only=False)
def liquidity_kill(ctx: Context, p: dict[str, Any]) -> Any:
    return _liq_write(True)


@command("liquidity.resume",
         "Delete the aero-lp KILL file so the daemon may act again. Requires confirm=true.",
         read_only=False, requires_confirm=True)
def liquidity_resume(ctx: Context, p: dict[str, Any]) -> Any:
    return _liq_write(False)


# -- docs ----------------------------------------------------------------------------------------


def _doc_row(e: docs_browser.DocEntry) -> dict[str, Any]:
    return {"path": e.path, "name": e.name, "directory": e.directory, "kind": e.kind,
            "summary": e.summary, "lines": e.lines, "size": e.size,
            "editable": docs_browser.is_editable(e)}


@command("docs.list", "Repo files from the committed index, filtered by text and kind.",
         (P("query", "string", "Substring of path or summary."),
          P("kind", "string", "Exact file kind, e.g. code-python."),
          P("limit", "number", f"Max rows (default {DOCS_TABLE_CAP}).")))
def docs_list(ctx: Context, p: dict[str, Any]) -> Any:
    entries = ctx.catalog()
    rows = docs_browser.filter_entries(entries, p.get("query", ""), p.get("kind", ""))
    limit = int(p.get("limit", DOCS_TABLE_CAP))
    shown = rows[:limit]
    return {
        "entries": [_doc_row(e) for e in shown], "total": len(entries), "matched": len(rows),
        "shown": len(shown), "kinds": docs_browser.kinds_of(entries),
        "headline": docs_browser.summarise_catalog(entries),
    }


DOCS_SEARCH_MODES = ("keyword", "semantic", "hybrid")


def _repo_search():
    """The index/search.py module, imported on first use and never before.

    The keyword postings (12 MB of JSON), the embedding matrix and the ~670 MB embedding model
    are only worth holding while someone is searching, so nothing here runs at import time and
    `docs.search_unload` can give it all back.
    """
    import importlib.util

    module = sys.modules.get("repo_index_search")
    if module is None:
        path = REPO / "index" / "search.py"
        spec = importlib.util.spec_from_file_location("repo_index_search", path)
        if spec is None or spec.loader is None:
            raise CommandError("failed", f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["repo_index_search"] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop("repo_index_search", None)
            raise
    return module


@command("docs.search",
         "Search the repo index: keyword (BM25), semantic (mxbai-embed-large via local ollama, "
         "started if needed) or hybrid. Loads the index on first use.",
         (P("query", "string", "What to look for.", True),
          P("mode", "string", "keyword, semantic or hybrid (default hybrid)."),
          P("kind", "string", "Restrict to a file kind, e.g. code-python."),
          P("limit", "number", "Max hits (default 30).")),
         read_only=False, long_running=True)
def docs_search(ctx: Context, p: dict[str, Any]) -> Any:
    query = str(p["query"]).strip()
    mode = p.get("mode") or "hybrid"
    if not query:
        raise CommandError("bad_params", "query must not be empty")
    if mode not in DOCS_SEARCH_MODES:
        raise CommandError("bad_params", f"mode must be one of {', '.join(DOCS_SEARCH_MODES)}")
    try:
        limit = max(1, min(int(p.get("limit", 30)), 200))
    except (TypeError, ValueError) as exc:
        raise CommandError("bad_params", 'parameter "limit" must be a number') from exc
    search = _repo_search()
    try:
        result = search.run_query(query, mode, limit, p.get("kind") or None)
    except SystemExit as exc:  # search.load() exits with the rebuild command when an index is missing
        raise CommandError("failed", str(exc)) from exc
    # The Docs tab only opens catalogued files, so only catalogued files are listed.
    editable = {e.path: docs_browser.is_editable(e) for e in ctx.catalog()}
    hits = [{"path": h.path, "kind": h.kind, "lines": h.lines, "summary": h.summary,
             "score": round(h.score, 4), "editable": editable[h.path]}
            for h in result.hits if h.path in editable]
    return {"query": query, "mode": mode, "mode_used": result.mode_used, "hits": hits,
            "notes": result.notes}


@command("docs.search_unload",
         "Free the search index from memory and ask ollama to unload the embedding model.",
         read_only=False)
def docs_search_unload(ctx: Context, p: dict[str, Any]) -> Any:
    module = sys.modules.get("repo_index_search")
    if module is None:
        return {"message": "search was never loaded in this process; nothing to free"}
    return {"message": module.unload()}


@command("docs.read", "Read one catalogued file.", (P("path", "string", "Catalogue path.", True),))
def docs_read(ctx: Context, p: dict[str, Any]) -> Any:
    entries = ctx.catalog()
    text, language, real = docs_browser.read_document(p["path"], entries)
    entry = next((e for e in entries if e.path == p["path"]), None)
    return {"path": p["path"], "text": text, "language": language, "real_text": real,
            "editable": bool(real and entry is not None and docs_browser.is_editable(entry))}


@command("docs.write", "Save text to a catalogued, editable file (never research/results/).",
         (P("path", "string", "Catalogue path.", True), P("text", "string", "New file contents.", True)),
         read_only=False)
def docs_write(ctx: Context, p: dict[str, Any]) -> Any:
    try:
        target = docs_browser.write_document(p["path"], p["text"], ctx.catalog())
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise CommandError("failed", f"save failed: {exc}") from exc
    return {"path": p["path"], "bytes": len(p["text"].encode("utf-8")), "file": str(target)}


# -- P&L -----------------------------------------------------------------------------------------

JOURNAL_ENV = "SOLTUI_JOURNAL"
DEFAULT_JOURNAL = Path.home() / ".solmargintrader" / "journal.json"

PNL_PARAMS = (
    P("window", "string", "24h, 7d, 30d (default), 90d, ytd or all. start/end override it."),
    P("start", "string", "Custom window start, UTC: YYYY-MM-DD or YYYY-MM-DD HH:MM."),
    P("end", "string", "Custom window end, UTC. A date alone includes that whole day."),
    P("source", "string", "all (default), backtest, paper, dry-run, dry-run LP or live LP."),
)


def _backtest_curves(ctx: Context) -> tuple[list[pnl_mod.Curve], list[str]]:
    """One full-history run per roster strategy, cached until settings, roster or data change."""
    s = ctx.settings
    path = Path(s.data_dir) / f"{s.asset.upper()}_{s.interval}.csv"
    try:
        stamp = (path.stat().st_mtime_ns, path.stat().st_size)
    except OSError:
        stamp = None
    key = json.dumps([s.asset, s.interval, s.start, s.end, s.capital, s.fee_bps, s.slippage_bps,
                      s.fill_delay, s.data_dir, ctx.roster.to_list(), stamp], sort_keys=True)
    cached = ctx.runtime.pnl_cache.get("backtest")
    if cached and cached[0] == key:
        return cached[1], cached[2]
    curves: list[pnl_mod.Curve] = []
    notes: list[str] = []
    try:
        arrays = load_arrays(s)
        cfg = engine_config(s)
    except Exception as exc:  # noqa: BLE001 - say what is missing instead of failing the tab
        notes.append(f"no backtest data: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        arrays = None
    if arrays is not None:
        from backtester.core.engine import run_backtest
        from backtester.core.strategies import build

        for e in ctx.roster:
            try:
                res = run_backtest(build(e.name, **e.params), arrays, cfg)
            except Exception as exc:  # noqa: BLE001
                notes.append(f"{e.label}: {type(exc).__name__}: {exc}")
                continue
            curves.append(pnl_mod.curves_from_backtest(res, "backtest", e.label, s.asset.upper(),
                                                       s.capital))
        notes.append(f"{len(curves)} roster strategies, {s.asset.upper()} {s.interval}, each on "
                     f"${s.capital:,.0f}; sections add independent runs (equal-capital sleeves)")
    ctx.runtime.pnl_cache["backtest"] = (key, curves, notes)
    return curves, notes


def _paper_curves(ctx: Context) -> tuple[list[pnl_mod.Curve], list[str]]:
    if ctx.session is None:
        return [], ["no paper session is open: start one on the Execute tab"]
    rt = ctx.runtime
    curve = pnl_mod.curve_from_paper(ctx.session, rt.session_label or "paper session",
                                     rt.session_asset or ctx.settings.asset.upper())
    return [curve], [f"replay up to bar {ctx.session.cursor}; bars after the cursor are not counted"]


def _journal_curves() -> tuple[list[pnl_mod.Curve], list[str]]:
    path = Path(os.environ.get(JOURNAL_ENV) or DEFAULT_JOURNAL)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], [f"extension journal not found at {path}"]
    except (OSError, ValueError) as exc:
        return [], [f"extension journal unreadable: {exc}"]
    curves = pnl_mod.curves_from_journal(doc)
    return curves, ([] if curves else ["extension journal has no fills"])


def _lp_curves() -> list[tuple[str, list[pnl_mod.Curve], list[str]]]:
    """The liquidity daemon's files, read-only. History from the ledger when it has snapshots."""
    import sqlite3

    home = liq.state_dir()
    status = liq.load_status(home)
    if status.data is None:
        return [("live LP", [], [f"liquidity state unavailable: {status.reason}"])]
    mode = status.data.get("mode")
    source = pnl_mod.lp_source(mode)
    notes = [f"daemon mode: {mode if isinstance(mode, str) else 'unknown'}"]
    curve = None
    ledger = home / "ledger.sqlite"
    if ledger.exists():
        try:
            conn = sqlite3.connect(f"file:{ledger}?mode=ro", uri=True, timeout=2)
            try:
                curve = pnl_mod.curve_from_lp_ledger(conn, mode)
            finally:
                conn.close()
        except sqlite3.Error as exc:
            notes.append(f"ledger.sqlite unreadable: {exc}")
    if curve is None:
        curve = pnl_mod.curve_from_lp_status(status.data)
        if curve is not None:
            notes.append("no ledger history: showing the status.json cumulative figure")
    return [(source, [curve] if curve else [], notes)]


def _wallet_curves() -> tuple[list[pnl_mod.Curve], list[str]]:
    """Wallet value at each complete portfolio snapshot (the hourly job and portfolio.scan append them)."""
    snaps = portfolio_mod.load_snapshots()
    rows, left_out = portfolio_mod.value_rows(snaps)
    if not snaps:  # snapshots began after the single-scan history; use that only when there are none
        rows = [r for r in wallet_mod.load_history() if not r.get("partial")]
    curve = pnl_mod.curve_from_wallet_history(rows)
    if curve is None:
        return [], ["no wallet snapshot recorded yet: run portfolio.snapshot (the hourly job does) to add a point"]
    notes = [curve.note, f"{len(rows)} snapshot(s) used"]
    if left_out:
        notes.append(f"{left_out} snapshot(s) left out: a chain read partially, had no USD price, or the set of "
                     "wallets was different")
    if len(rows) == 1:
        notes.append("history starts with the first snapshot; a second snapshot is needed to show a change")
    return [curve], notes


def _pnl_report(ctx: Context, p: dict[str, Any]) -> dict[str, Any]:
    try:
        window = pnl_mod.resolve_window(p.get("window"), p.get("start"), p.get("end"))
        only = pnl_mod.normalise_source(p.get("source"))
    except pnl_mod.PnlError as exc:
        raise CommandError("bad_params", str(exc)) from exc
    inputs: list[tuple[str, list[pnl_mod.Curve], list[str]]] = []
    wanted = lambda *names: only is None or only in names  # noqa: E731
    if wanted("backtest"):
        c, n = _backtest_curves(ctx)
        inputs.append(("backtest", c, n))
    if wanted("paper"):
        c, n = _paper_curves(ctx)
        inputs.append(("paper", c, n))
    if wanted("dry-run"):
        c, n = _journal_curves()
        inputs.append(("dry-run", c, n))
    if wanted("wallet (live)"):
        c, n = _wallet_curves()
        inputs.append(("wallet (live)", c, n))
    if wanted("dry-run LP", "live LP", "reported LP"):
        for src, c, n in _lp_curves():
            if only is None or only == src or (only == "live LP" and src == "reported LP"):
                inputs.append((src, c, n))
    return pnl_mod.build_report(inputs, window)


_SUMMARY_KEYS = ("source", "group", "label", "status", "message", "data_range", "runs", "windowed", "notes",
                 "totals", "drawdown")
_SERIES_KEYS = ("source", "group", "label", "status", "message", "data_range", "windowed", "notes", "days",
                "drawdown", "best_worst")
_BREAKDOWN_KEYS = ("source", "group", "label", "status", "message", "data_range", "windowed", "notes",
                   "by_strategy", "by_asset", "best_worst")


def _pnl_slice(report: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {**{k: v for k, v in report.items() if k != "sections"},
            "sections": [{k: s[k] for k in keys if k in s} for s in report["sections"]]}


@command("pnl.summary",
         "Net and gross P&L, fees, slippage, borrow, realized vs unrealized, win rate, expectancy and "
         "drawdown for a window. One section per source; simulated and real are never summed.",
         PNL_PARAMS)
def pnl_summary(ctx: Context, p: dict[str, Any]) -> Any:
    return _pnl_slice(_pnl_report(ctx, p), _SUMMARY_KEYS)


@command("pnl.series",
         "Daily P&L with the cumulative curve, drawdown, recovery and best/worst day, week and month.",
         PNL_PARAMS)
def pnl_series(ctx: Context, p: dict[str, Any]) -> Any:
    return _pnl_slice(_pnl_report(ctx, p), _SERIES_KEYS)


@command("pnl.breakdown",
         "P&L by strategy and by asset, with each one's contribution to its section's net %.",
         PNL_PARAMS)
def pnl_breakdown(ctx: Context, p: dict[str, Any]) -> Any:
    return _pnl_slice(_pnl_report(ctx, p), _BREAKDOWN_KEYS)


# -- wallet (read-only) --------------------------------------------------------------------------


@command("coinbase.account", "Read the last saved Coinbase account snapshot without affecting other wallets.")
def coinbase_account(ctx: Context, p: dict[str, Any]) -> Any:
    from . import coinbase_account as cb
    return cb.last_account()


@command("coinbase.sync", "Refresh Coinbase balances using the separately authenticated Coinbase CLI.")
def coinbase_sync(ctx: Context, p: dict[str, Any]) -> Any:
    from . import coinbase_account as cb
    return cb.sync_account()


@command("coinbase.markets", "Download the public Coinbase market catalog, reporting incomplete scopes.")
def coinbase_markets(ctx: Context, p: dict[str, Any]) -> Any:
    from . import coinbase_account as cb
    return cb.download_markets()


def _daemon_context() -> dict[str, Any]:
    """What the liquidity daemon's own files say about tokens and positions (read-only)."""
    import sqlite3

    home = liq.state_dir()
    status = liq.load_status(home).data
    tokens: list[str] = []
    ledger = home / "ledger.sqlite"
    if ledger.exists():
        try:
            conn = sqlite3.connect(f"file:{ledger}?mode=ro", uri=True, timeout=2)
            try:
                tokens = [r[0] for r in conn.execute("SELECT DISTINCT token FROM wallet_balances")]
            finally:
                conn.close()
        except sqlite3.Error:
            tokens = []
    return wallet_mod.daemon_context(status, tokens)


@command("wallet.key_sources",
         "Whether the signing-key files exist and are mode 600, by stat only. Never opens them.")
def wallet_key_sources(ctx: Context, p: dict[str, Any]) -> Any:
    return wallet_mod.key_sources()


@command("wallet.addresses",
         "The public Solana and EVM addresses saved in Settings, and nothing else. Extended public keys "
         "and any key material are never returned. The extension's Wallet pubkey button reads this.")
def wallet_addresses(ctx: Context, p: dict[str, Any]) -> Any:
    st = ctx.settings
    return {"solana_address": st.solana_address, "base_address": st.base_address, "eth_address": st.eth_address,
            "hyperliquid_address": st.hyperliquid_address,
            "note": "Public addresses only. Signing keys live in separate files this console never opens."}


def _portfolio_scan(ctx: Context, chain: str, extra: list[str] | None = None) -> dict[str, Any]:
    st = ctx.settings
    return wallet_mod.scan_wallet(
        st.solana_address, st.base_address, portfolio_mod.make_fetcher(), chain=chain,
        daemon=_daemon_context(), extra_tokens=extra, eth_address=st.eth_address,
        xpubs={"btc": st.btc_xpub, "ltc": st.ltc_xpub, "doge": st.doge_xpub})


@command("portfolio.scan",
         "Find the coins, token contracts, stake accounts, LP positions and UTXO balances at the wallets in "
         "Settings (Solana, Base, Ethereum, and Bitcoin, Litecoin and Dogecoin from their extended public "
         "keys), using public reads and optional configured CDP indexed balances. Appends a snapshot the P&L tab and portfolio.changes read. "
         "Derived addresses are counted, never listed.",
         (P("chain", "string", "all (default), solana, base, ethereum, bitcoin, litecoin or dogecoin."),
          P("tokens", "json", "Extra Base token contract addresses to check, as a list."),
          P("record", "bool", "Append this scan as a snapshot (default true; only an all-chain scan is kept).")),
         read_only=False, long_running=True)
def portfolio_scan(ctx: Context, p: dict[str, Any]) -> Any:
    chain = wallet_mod.normalise_chain(p.get("chain") or "all")
    if chain is None:
        raise CommandError("bad_params", f'parameter "chain" must be all or one of {", ".join(wallet_mod.CHAINS)}')
    extra = p.get("tokens")
    if extra is not None and (not isinstance(extra, list) or not all(isinstance(t, str) for t in extra)):
        raise CommandError("bad_params", 'parameter "tokens" must be a list of addresses')
    result = _portfolio_scan(ctx, chain, extra)
    try:
        portfolio_mod.save_last_scan(result, chain)
    except OSError as exc:
        result.setdefault("notes", []).append(f"scan not kept for the next start: {exc}")
    # A one-chain scan is not a snapshot of the whole portfolio; recording it would read as the others
    # having gone to zero.
    if p.get("record", True) and result["chains"] and chain == "all":
        try:
            portfolio_mod.append_snapshot(portfolio_mod.build_snapshot(result))
        except OSError as exc:
            result["notes"] = [f"scan not recorded: {exc}"]
    return result


@command("portfolio.last",
         "The newest wallet scan kept on disk ({chain, saved_at, result}, or result null), so a console "
         "shows the wallet at once after a restart. No network.")
def portfolio_last(ctx: Context, p: dict[str, Any]) -> Any:
    return portfolio_mod.load_last_scan() or {"chain": None, "saved_at": None, "result": None}


@command("portfolio.snapshot",
         "Scan every configured wallet and append one timestamped snapshot to the portfolio history "
         "(mode 600). Returns counts and USD totals per chain: no addresses. The hourly LaunchAgent runs this.",
         read_only=False, long_running=True)
def portfolio_snapshot(ctx: Context, p: dict[str, Any]) -> Any:
    result = _portfolio_scan(ctx, "all")
    snap = portfolio_mod.build_snapshot(result)
    if not snap["chains"]:
        raise CommandError("failed", "nothing to snapshot: no wallet address or extended public key in Settings")
    path = portfolio_mod.append_snapshot(snap)
    chains = {}
    for name, ch in snap["chains"].items():
        full = result["chains"][name]
        chains[name] = {"status": ch["status"], "total_usd": ch["usd"], "usd_complete": ch["usd_complete"],
                        "unpriced": ch["unpriced"], "holdings": full["counts"]["holdings"],
                        "balances": ch["balances"],
                        **({"script_types": ch["script_types"], "derived_addresses": ch["derived_addresses"]}
                           if "script_types" in ch else {}),
                        "errors": [f"{e['source']}: {e['message']}" for e in full["errors"]]}
    return {"label": snap["label"], "at": snap["at"], "partial": result["partial"],
            "total_usd": snap["total_usd"], "total_complete": snap["total_complete"],
            "skipped": result["skipped"], "chains": chains, "snapshot_file": str(path)}


@command("portfolio.changes",
         "Balance changes between the latest portfolio snapshot and the previous one (or the newest one at "
         "least `hours` older). A chain that was partial or failed in either snapshot is skipped, not "
         "reported as a change.",
         (P("hours", "number", "Compare against the newest snapshot at least this many hours older."),))
def portfolio_changes(ctx: Context, p: dict[str, Any]) -> Any:
    hours = p.get("hours")
    if hours is not None and (not math.isfinite(float(hours)) or float(hours) <= 0):
        raise CommandError("bad_params", 'parameter "hours" must be a positive number')
    return portfolio_mod.changes_report(portfolio_mod.load_snapshots(), None if hours is None else float(hours))


@command("portfolio.notice",
         "One line saying a balance changed since the wallet was last viewed, or null. With mark_seen the "
         "last-view marker moves to the latest snapshot. The TUI and menu bar show this line.",
         (P("mark_seen", "bool", "Record that the changes were seen (default false)."),), read_only=False)
def portfolio_notice(ctx: Context, p: dict[str, Any]) -> Any:
    return portfolio_mod.notice(mark_seen=bool(p.get("mark_seen", False)))


# -- bots and the price stream -------------------------------------------------------------------
#
# The Bots tab's grid, triangle-arbitrage and DCA bots (`bots.py`) are simulations: backtests over
# cached bars, dry-run forward tests over the recorded Coinbase stream (`pricefeed.py`), and an
# auto-optimizer. None places an order. `prices.ensure` keeps the recorder running (LaunchAgent or a
# detached process); it reads public market data only and writes only under <config dir>/prices/.


def _bots(fn, *args, **kwargs) -> Any:
    from . import bots as bots_mod
    from . import pricefeed

    try:
        return fn(*args, **kwargs)
    except (bots_mod.BotError, pricefeed.PriceFeedError) as exc:
        raise CommandError("failed", str(exc)) from exc


def _bot_param(p: dict[str, Any]) -> str:
    from . import bots as bots_mod

    name = str(p.get("bot") or "").strip().lower()
    if name not in bots_mod.BOTS:
        raise CommandError("bad_params", f'parameter "bot" must be one of {", ".join(bots_mod.BOTS)}')
    return name


BOT_PARAM = P("bot", "string", "grid, triangle or dca.", required=True)


@command("bots.overview", "Every bot: what it does, its saved configuration, the latest backtest, its forward "
         "test and the latest auto-optimize verdict; and the coins with cached data.")
def bots_overview(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return _bots(bots_mod.overview, ctx.settings)


@command("bots.config", "One bot's configuration, its defaults and the grid auto-optimize searches.",
         (BOT_PARAM,))
def bots_config(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    bot = _bot_param(p)
    return {"bot": bot, "config": _bots(bots_mod.get_config, bot), "defaults": bots_mod.DEFAULTS[bot],
            "space": bots_mod.SPACE[bot], "about": bots_mod.ABOUT[bot]}


@command("bots.save", "Change a bot's configuration: values as a JSON object or text as name=value pairs; "
         "reset restores the defaults. Unknown names and unbuildable values are refused.",
         (BOT_PARAM, P("values", "json", "Settings to change, e.g. {\"range_pct\": 10}."),
          P("text", "string", "Settings as name=value pairs, e.g. range_pct=10 rungs=9."),
          P("reset", "bool", "Restore the defaults instead.")), read_only=False)
def bots_save(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    bot = _bot_param(p)
    if p.get("reset"):
        return {"bot": bot, "config": _bots(bots_mod.reset_config, bot)}
    values = p.get("values") or {}
    if not isinstance(values, dict):
        raise CommandError("bad_params", 'parameter "values" must be a JSON object')
    if p.get("text"):
        values = {**values, **_bots(bots_mod.parse_kv, p["text"])}
    if not values:
        raise CommandError("bad_params", "nothing to save: pass values, text or reset")
    return {"bot": bot, "config": _bots(bots_mod.save_config, bot, values)}


@command("bots.backtest", "Start a bot at a past moment (what it would have set from the price then) and "
         "simulate it forward with fees and slippage, on one or several coins; grid and DCA on cached hourly "
         "bars from the beginning of the usable data by default, triangle on recorded quotes or, failing "
         "those, a labelled 1m candle proxy (fetched from Coinbase). Returns every run and a per-coin summary.",
         (BOT_PARAM, P("asset", "string", "One coin for grid and DCA; default the configured asset."),
          P("coins", "json", "Several coins, e.g. [\"SOL\", \"BTC\"], or \"all\"; overrides asset."),
          P("start", "string", "UTC date or epoch seconds; default the beginning of the usable data."),
          P("days", "number", "How long to run; default to the end of the data.")),
         read_only=False, long_running=True)
def bots_backtest(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    coins = p.get("coins")
    if coins is not None and not (coins == "all" or (isinstance(coins, list) and all(isinstance(c, str) for c in coins))):
        raise CommandError("bad_params", 'parameter "coins" must be a list of coin symbols or "all"')
    if coins is None:
        coins = [str(p.get("asset") or ctx.settings.asset)]
    return _bots(bots_mod.backtest_many, _bot_param(p), coins, ctx.settings, start=p.get("start"),
                 days=p.get("days"), progress=(lambda _fraction, message: ctx.progress(message)) if ctx.progress else None)


def _coin_fit_run(ctx: Context, p: dict[str, Any], mode: str) -> Any:
    from . import coin_fit

    bot = _bot_param(p)
    if bot == "triangle":
        raise CommandError("bad_params", "coin suitability supports grid and dca, not triangle arbitrage")
    coins = p.get("coins", "ALL") if mode == "quick" else [p.get("asset")]
    if isinstance(coins, str):
        if coins.upper() != "ALL":
            raise CommandError("bad_params", 'coins must be a list of symbols or "all"')
        coins = "ALL"
    elif not isinstance(coins, list) or not coins or not all(isinstance(c, str) and c.strip() for c in coins):
        raise CommandError("bad_params", "coins must be a nonempty list of symbols")
    days = p.get("days")
    if days is not None and (not math.isfinite(float(days)) or float(days) <= 0):
        raise CommandError("bad_params", "days must be finite and positive")
    for key in ("reference_end", "fee_bps", "slippage_bps", "capital"):
        value = p.get(key)
        if value is not None and (not math.isfinite(float(value)) or float(value) < 0):
            raise CommandError("bad_params", f"{key} must be finite and nonnegative")
    if p.get("capital") == 0:
        raise CommandError("bad_params", "capital must be positive")
    for key in ("config", "policy"):
        if p.get(key) is not None and not isinstance(p[key], dict):
            raise CommandError("bad_params", f"{key} must be a JSON object")
    if p.get("expected_data_sha256") is not None:
        value = p["expected_data_sha256"]
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise CommandError("bad_params", "expected_data_sha256 must be a lowercase SHA256 digest")
    request_id = p.get("request_id") or uuid.uuid4().hex
    with ctx.runtime.lock:
        active = ctx.runtime.coin_fit_job
        if active and active.get("status") in ("running", "cancelling"):
            raise CommandError("failed", "a coin suitability job is still running; cancel it and wait for it to stop")
        cancelled_before_start = request_id in ctx.runtime.coin_fit_cancelled_requests
        interrupted = request_id in ctx.runtime.coin_fit_interrupted_requests
        ctx.runtime.coin_fit_cancelled_requests.discard(request_id)
        ctx.runtime.coin_fit_interrupted_requests.discard(request_id)
        if cancelled_before_start:
            ctx.runtime.coin_fit_stop.set()
        else:
            ctx.runtime.coin_fit_stop.clear()
        job: dict[str, Any] = {"request_id": request_id, "bot": bot, "mode": mode, "status": "running", "fraction": 0.0,
                              "message": "starting suitability backtests", "error": None,
                              "interrupt_requested": interrupted}
        ctx.runtime.coin_fit_job = job

    def progress(fraction: float, message: str) -> None:
        with ctx.runtime.lock:
            if ctx.runtime.coin_fit_job is job:
                job.update(fraction=max(0.0, min(1.0, float(fraction))), message=str(message))

    try:
        if cancelled_before_start:
            result = {"bot": bot, "mode": mode, "rows": [], "errors": {}, "cancelled": True,
                      "notes": ["Cancelled before simulation started."]}
        else:
            frozen = {key: p[key] for key in ("reference_end", "config", "fee_bps", "slippage_bps",
                      "selection_id", "expected_data_sha256", "policy", "capital") if key in p}
            result = coin_fit.rank_coins(bot, coins, ctx.settings, mode=mode,
                                        start=p.get("start"), days=days, progress=progress,
                                        cancelled=ctx.runtime.coin_fit_stop.is_set, **frozen)
        if not isinstance(result, dict):
            raise TypeError("coin suitability engine returned a non-object report")
    except Exception as exc:
        with ctx.runtime.lock:
            job.update(status="failed", error=f"{type(exc).__name__}: {exc}", message=str(exc))
        raise
    with ctx.runtime.lock:
        was_cancelled = bool(result.get("cancelled") or ctx.runtime.coin_fit_stop.is_set())
        result["cancelled"] = was_cancelled
        interrupted = bool(was_cancelled and job.get("interrupt_requested"))
        result["interrupted"] = interrupted
        terminal = "interrupted" if interrupted else "cancelled" if was_cancelled else "completed"
        job.update(status=terminal, fraction=1.0,
                   message=f"{terminal}; completed rows retained" if was_cancelled else "completed")
    return result


_COIN_FIT_PARAMS = (BOT_PARAM, P("start", "string", "UTC start; the same comparison window is used for every coin."),
                   P("days", "number", "Window length in days; must be finite and positive."),
                   P("reference_end", "number", "Freeze the exclusive UTC endpoint from quick ranking."),
                   P("config", "json", "Frozen bot settings from the quick ranking; does not save them."),
                   P("fee_bps", "number", "Frozen per-side fee assumption from quick ranking."),
                   P("slippage_bps", "number", "Frozen per-side slippage assumption from quick ranking."),
                   P("policy", "json", "Frozen heuristic policy/score weights from the quick ranking."),
                   P("capital", "number", "Frozen full funded account capital from the quick ranking."),
                   P("selection_id", "string", "Identity of the quick ranking this audit follows."),
                   P("expected_data_sha256", "string", "Selected quick row's data fingerprint; audit refuses changed history."),
                   P("request_id", "string", "Caller request identity, used for race-safe cancellation."))


@command("bots.rank_coins", "Quick, provisional coin suitability ranking on the selected bot's current "
         "settings and cached data. Returns costs, full-equity backtests, reasons and retained error rows; "
         "never adopts settings or places an order.",
         (*_COIN_FIT_PARAMS, P("coins", "json", 'Symbols or "all"; default every cached coin.')),
         long_running=True)
def bots_rank_coins(ctx: Context, p: dict[str, Any]) -> Any:
    return _coin_fit_run(ctx, p, "quick")


@command("bots.audit_coin", "Audit one coin with chronological windows and stressed costs. Shows "
         "equity, drawdown and unresolved inventory; does not adopt settings or promise future returns.",
         (*_COIN_FIT_PARAMS, P("asset", "string", "One coin symbol to audit.", required=True)),
         long_running=True)
def bots_audit_coin(ctx: Context, p: dict[str, Any]) -> Any:
    return _coin_fit_run(ctx, p, "audit")


@command("bots.fit_status", "State and progress of this process's latest coin suitability job.")
def bots_fit_status(ctx: Context, p: dict[str, Any]) -> Any:
    with ctx.runtime.lock:
        return dict(ctx.runtime.coin_fit_job) if ctx.runtime.coin_fit_job is not None else None


@command("bots.fit_cancel", "Request cooperative cancellation of the current suitability job. "
         "It remains cancelling until the active simulation window finishes.",
         (P("request_id", "string", "Cancel this caller request, including one not started yet."),
          P("interrupted", "bool", "Mark cancellation as interrupted by application shutdown or context change.")),
         read_only=False)
def bots_fit_cancel(ctx: Context, p: dict[str, Any]) -> Any:
    with ctx.runtime.lock:
        job = ctx.runtime.coin_fit_job
        request_id = p.get("request_id")
        if request_id and (job is None or job.get("request_id") != request_id):
            if len(ctx.runtime.coin_fit_cancelled_requests) >= 128:
                raise CommandError("failed", "too many unmatched cancellation requests")
            ctx.runtime.coin_fit_cancelled_requests.add(request_id)
            if p.get("interrupted"):
                ctx.runtime.coin_fit_interrupted_requests.add(request_id)
        if job and job.get("status") in ("running", "cancelling") and (
                request_id is None or job.get("request_id") == request_id):
            ctx.runtime.coin_fit_stop.set()
            if p.get("interrupted"):
                job["interrupt_requested"] = True
            job.update(status="cancelling", message="cancelling after the current bounded simulation window")
        return dict(job) if job is not None else None


@command("bots.results", "Saved bot backtests, newest first.",
         (P("bot", "string", "Limit to one bot."), P("limit", "number", "How many (default 10).")))
def bots_results(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    bot = _bot_param(p) if p.get("bot") else None
    limit = int(p.get("limit") or 10)
    if not 1 <= limit <= 200:
        raise CommandError("bad_params", 'parameter "limit" must be in [1, 200]')
    return _bots(bots_mod.latest_results, bot, limit)


@command("bots.forward_start", "Start (or restart) a bot's dry-run forward test now, on its current "
         "configuration, replaying the recorded price stream as it arrives. Starts the recorder if needed.",
         (BOT_PARAM, P("asset", "string", "Coin for grid and DCA; default the configured asset.")),
         read_only=False)
def bots_forward_start(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return _bots(bots_mod.forward_start, _bot_param(p), str(p.get("asset") or ctx.settings.asset), ctx.settings)


@command("bots.forward_stop", "Stop a bot's forward test; its results freeze at the stop time.",
         (BOT_PARAM,), read_only=False)
def bots_forward_stop(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return _bots(bots_mod.forward_stop, _bot_param(p))


@command("bots.forward_status", "A bot's forward test so far: everything recorded since it started, replayed "
         "through the bot in dry-run.", (BOT_PARAM,), long_running=True)
def bots_forward_status(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return _bots(bots_mod.forward_status, _bot_param(p), ctx.settings)


@command("bots.optimize", "Auto-optimize a bot: its representative configuration grid on every cached coin "
         "(every recorded triangle) over chronological windows. Picks on the older windows, then adopts the "
         "pick only if it beats the current config on the newer windows by a sign test (p < 0.05).",
         (BOT_PARAM, P("coins", "json", "List of coins; default every coin with cached data."),
          P("windows", "number", "Windows per coin (default 6; half train, half test)."),
          P("window_days", "number", "Days per window (default 30)."),
          P("adopt", "bool", "Adopt a reliable winner (default true).")),
         read_only=False, long_running=True)
def bots_optimize(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    coins = p.get("coins")
    if coins is not None and (not isinstance(coins, list) or not all(isinstance(c, str) for c in coins)):
        raise CommandError("bad_params", 'parameter "coins" must be a list of coin symbols')
    return _bots(bots_mod.optimize, _bot_param(p), ctx.settings, coins=coins,
                 windows=int(p.get("windows") or bots_mod.OPTIMIZE_WINDOWS),
                 window_days=int(p.get("window_days") or bots_mod.OPTIMIZE_WINDOW_DAYS),
                 adopt=bool(p.get("adopt", True)))


@command("bots.optimize_result", "The latest auto-optimize report for a bot, or null.", (BOT_PARAM,))
def bots_optimize_result(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return _bots(bots_mod.latest_optimize, _bot_param(p))


# -- durable optimization experiments ------------------------------------------------------------

EXPERIMENT_ID = P("run_id", "string", "Saved experiment identifier.", required=True)
EXPERIMENT_SPACE = (
    BOT_PARAM,
    P("space", "json", "Typed parameter specifications (fixed, enum, linear/log range)."),
    P("coins", "json", "Coin symbols; defaults to every cached coin."),
    P("windows", "number", "Chronological windows per coin, including untouched final holdout."),
    P("window_days", "number", "Days per bar window."),
    P("max_candidates", "number", "Hard valid-configuration budget (at most 97)."),
    P("max_evaluations", "number", "Hard candidate × coin × window evaluation budget."),
)


def _experiment(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    from .experiments import ExperimentError
    try:
        return fn(*args, **kwargs)
    except (ExperimentError, ValueError, OSError) as exc:
        raise CommandError("experiment_refused", str(exc)) from None


def _experiment_options(p: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for name in ("space", "coins", "windows", "window_days", "max_candidates", "max_evaluations"):
        if name not in p:
            continue
        value = p[name]
        if name == "space" and not isinstance(value, dict):
            raise CommandError("bad_params", "space must be an object of typed parameter specifications")
        if name == "coins" and (not isinstance(value, list) or not value or
                                not all(isinstance(c, str) and c for c in value)):
            raise CommandError("bad_params", "coins must be a nonempty list of symbols")
        if name not in {"space", "coins"} and (isinstance(value, bool) or not math.isfinite(value)
                                                or int(value) != value):
            raise CommandError("bad_params", f"{name} must be an integer")
        out[name] = value if name in {"space", "coins"} else int(value)
    return out


@command("experiments.schema", "Current bot configuration and typed search parameter domains.", (BOT_PARAM,))
def experiments_schema(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots
    bot = _bot_param(p)
    return _experiment(lambda: {"bot": bot, "baseline": bots.get_config(bot), "domains": bots.DOMAINS[bot]})


@command("experiments.preview", "Validate a bounded search and preview actual cached-data workload; no evaluations.",
         EXPERIMENT_SPACE, long_running=True)
def experiments_preview(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_runner import preview_experiment
    return _experiment(preview_experiment, _bot_param(p), ctx.settings, **_experiment_options(p))


@command("experiments.create", "Freeze a native experiment specification without starting its worker.",
         EXPERIMENT_SPACE, read_only=False, long_running=True)
def experiments_create(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_runner import prepare_experiment
    return _experiment(prepare_experiment, _bot_param(p), ctx.settings, **_experiment_options(p))


@command("experiments.list", "Saved native and imported experiments, newest first.",
         (P("bot", "string", "Filter by bot."), P("source", "string", "native or tradingview."),
          P("limit", "number", "Maximum rows, 1 to 200 (default 100).")))
def experiments_list(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore
    limit = p.get("limit", 100)
    if isinstance(limit, bool) or not 1 <= limit <= 200 or int(limit) != limit:
        raise CommandError("bad_params", "limit must be an integer in [1, 200]")
    return _experiment(lambda: ExperimentStore().list_runs(bot=p.get("bot"), source=p.get("source"), limit=int(limit)))


@command("experiments.get", "Experiment specification, decision, progress, worker state and diagnostic log tail.",
         (EXPERIMENT_ID,))
def experiments_get(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_jobs import status
    from .experiments import ExperimentStore
    return _experiment(lambda: status(ExperimentStore(), p["run_id"]))


@command("experiments.start", "Start or resume the saved experiment; completed evidence is reused only after verification.",
         (EXPERIMENT_ID,), read_only=False)
def experiments_start(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_jobs import launch
    from .experiments import ExperimentStore
    return _experiment(lambda: launch(ExperimentStore(), p["run_id"], ctx.settings))


@command("experiments.pause", "Request pause after the current evaluation cell commits.",
         (EXPERIMENT_ID,), read_only=False)
def experiments_pause(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_jobs import request
    from .experiments import ExperimentStore
    return _experiment(lambda: request(ExperimentStore(), p["run_id"], "pause"))


@command("experiments.cancel", "Request cancellation at the next durable evaluation boundary; keep completed evidence.",
         (EXPERIMENT_ID,), read_only=False)
def experiments_cancel(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_jobs import request
    from .experiments import ExperimentStore
    return _experiment(lambda: request(ExperimentStore(), p["run_id"], "cancel"))


@command("experiments.finalize", "Freeze the training-selected candidate and validate on fresh reserved final holdout dates.",
         (EXPERIMENT_ID, P("adopt", "bool", "Save native settings only if all existing evidence gates pass (default false).")),
         read_only=False)
def experiments_finalize(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiment_jobs import launch
    from .experiments import ExperimentStore
    return _experiment(lambda: launch(ExperimentStore(), p["run_id"], ctx.settings, final=True,
                                      adopt=p.get("adopt", False)))


@command("experiments.candidates", "Full configurations, observed train/validation metrics, coverage and failures.",
         (EXPERIMENT_ID,))
def experiments_candidates(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore, candidate_summary
    return _experiment(lambda: candidate_summary(ExperimentStore(), p["run_id"]))


@command("experiments.cells", "Individual coin/window evaluation metrics and failures; final evidence stays sealed until finalization.",
         (EXPERIMENT_ID, P("coin", "string", "Coin filter."), P("split", "string", "train, validation or holdout."),
          P("candidate_id", "string", "Candidate filter.")))
def experiments_cells(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore
    def read() -> Any:
        store = ExperimentStore()
        run = store.get_run(p["run_id"])
        return store.cells(p["run_id"], coin=p.get("coin") or None, split=p.get("split") or None,
                           candidate_id=p.get("candidate_id") or None,
                           include_holdout=run["status"] == "completed")
    return _experiment(read)


@command("experiments.heatmap", "Observed two-parameter return/risk map and stability; missing points remain missing.",
         (EXPERIMENT_ID, P("x", "string", "First parameter.", True), P("y", "string", "Second parameter.", True),
          P("metric", "string", "Metric (default total_return)."), P("fixed", "json", "Values of all other varied parameters."),
          P("coin", "string", "Coin filter."), P("split", "string", "train or validation only.")))
def experiments_heatmap(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore, sparse_heatmap
    if p.get("fixed") is not None and not isinstance(p["fixed"], dict):
        raise CommandError("bad_params", "fixed must be an object")
    return _experiment(lambda: sparse_heatmap(ExperimentStore(), p["run_id"], p["x"], p["y"],
                        metric=p.get("metric") or "total_return", fixed=p.get("fixed"),
                        coin=p.get("coin") or None, split=p.get("split") or None))


@command("experiments.import", "Import read-only TradingView CSV evidence with explicit units and provenance; never adopts.",
         (P("csv", "string", "CSV text (use this or path)."), P("path", "string", "Local CSV file, at most 10 MB."),
          P("metadata", "json", "Explicit bot, coin, dates, units, costs, fill timing and script provenance.")),
         read_only=False, long_running=True)
def experiments_import(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore, import_tradingview
    if bool(p.get("csv")) == bool(p.get("path")):
        raise CommandError("bad_params", "supply exactly one of csv or path")
    if p.get("metadata") is not None and not isinstance(p["metadata"], dict):
        raise CommandError("bad_params", "metadata must be an object")
    def read() -> Any:
        if p.get("path"):
            path = Path(p["path"]).expanduser()
            with path.open("rb") as fh:
                raw = fh.read(10_000_001)
            if len(raw) > 10_000_000:
                raise ValueError("CSV exceeds 10 MB import budget")
            content = raw.decode("utf-8-sig")
        else:
            content = p["csv"]
            if len(content.encode("utf-8")) > 10_000_000:
                raise ValueError("CSV exceeds 10 MB import budget")
        return import_tradingview(ExperimentStore(), content, p.get("metadata"))
    return _experiment(read)


@command("experiments.compare", "Compare experiment provenance and metrics only when units, dates and evaluation assumptions match.",
         (P("left", "string", "First experiment ID.", True), P("right", "string", "Second experiment ID.", True)))
def experiments_compare(ctx: Context, p: dict[str, Any]) -> Any:
    from .experiments import ExperimentStore, compare_runs
    return _experiment(lambda: compare_runs(ExperimentStore(), p["left"], p["right"]))


@command("prices.status", "The streaming price recorder: running or not, what it has recorded, and the "
         "newest bid, ask and spread of every streamed market.")
def prices_status(ctx: Context, p: dict[str, Any]) -> Any:
    from . import pricefeed
    return _bots(pricefeed.status)


@command("prices.ensure", "Keep the price recorder on (public Coinbase level-2 batch and ticker channels; "
         "writes <config dir>/prices/): install its LaunchAgent if missing so it survives a closed console "
         "and a reboot, else start a detached recorder. Idempotent; the console calls it every minute.",
         read_only=False)
def prices_ensure(ctx: Context, p: dict[str, Any]) -> Any:
    from . import pricefeed
    return _bots(pricefeed.ensure_recorder)


@command("bots.progress", "A running auto-optimize: run number, fraction done, the configurations it is "
         "testing; null when none ran in this process.", (BOT_PARAM,))
def bots_progress(ctx: Context, p: dict[str, Any]) -> Any:
    from . import bots as bots_mod
    return bots_mod.runtime().progress.get(_bot_param(p))
