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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from . import analyze as analyze_mod
from . import bgcontrol, bgqueue
from . import cumulative as cumulative_mod
from . import docs_browser, live_run
from . import liquidity as liq
from . import top5 as top5_mod
from .config import INTERVALS, Settings, load_settings, save_settings
from .paper import MODE_LABEL, PaperSession, start_session
from .reference import FAMILY_NOTES, RESEARCH_DRIVERS, RESEARCH_FINDINGS, SIGNAL_REFERENCE
from .roster import Roster, RosterError, available_strategies
from .runner import SweepRunner, engine_config, load_arrays
from .signals import (
    SIGNAL_GROUPS,
    SignalDefaults,
    coerce,
    from_dict,
    mapped_strategies,
    merged_params,
)
from .status import AppState, Phase, build_title, format_pct

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
        self.queue_results: list[bgqueue.JobResult] = []
        self.queue_cursor = bgqueue.ResultsCursor()
        self.lock = threading.RLock()
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

    @classmethod
    def from_settings(cls, settings: Settings, runtime: Runtime | None = None) -> "Context":
        roster = Roster.from_list(settings.roster or [{"name": n} for n in settings.enabled_strategies])
        if len(roster) == 0:
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
}


@command("settings.get", "The saved settings (asset, interval, dates, costs, CPCV geometry).")
def settings_get(ctx: Context, p: dict[str, Any]) -> Any:
    return {"settings": ctx.settings.to_dict(), "intervals": list(INTERVALS)}


@command(
    "settings.save",
    "Validate and save settings. Only the parameters you pass change.",
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
    return {"path": str(path), "settings": new.to_dict()}


# -- strategies and roster -----------------------------------------------------------------------


def _entry(e) -> dict[str, Any]:
    return {"name": e.name, "params": dict(e.params), "label": e.label, "family": e.family,
            "warmup": e.warmup}


@command("strategies.list", "Every registered strategy and its family.")
def strategies_list(ctx: Context, p: dict[str, Any]) -> Any:
    return [{"name": n, "family": f} for n, f in available_strategies()]


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


@command("backtest.run", "CPCV sweep over the roster, ranked by median Sharpe. Blocks until done.",
         read_only=False, long_running=True)
def backtest_run(ctx: Context, p: dict[str, Any]) -> Any:
    ctx.runner.start(ctx.roster, ctx.settings)
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
        "rows": [dataclasses.asdict(r) for r in outcome.ranked()],
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
    return {"summary": s, "text": (
        f"bar {s['bar']}/{s['bars_total']}  {s['when']}   equity {s['equity']:,.2f}   "
        f"P&L {format_pct(s['pnl'])}   exposure {s['exposure']:.2f}   fills {s['fills']}   "
        f"live orders placed: {s['live_orders_placed']}"), "fills": fills, "mode": MODE_LABEL}


@command("paper.start", "Backtest one roster strategy and open a bar-by-bar dry-run replay.",
         (P("label", "string", "Roster label to replay.", True),
          P("bars", "number", "Bars to advance right after starting (default 0).")),
         read_only=False, long_running=True)
def paper_start(ctx: Context, p: dict[str, Any]) -> Any:
    from backtester.core.strategies import build

    label = p.get("label")
    if not label:
        raise CommandError("failed", "pick a strategy first")
    entry = next((e for e in ctx.roster if e.label == label), None)
    if entry is None:
        raise CommandError("failed", "strategy left the roster")
    try:
        arrays = load_arrays(ctx.settings)
        session = start_session(build(entry.name, **entry.params), arrays,
                                engine_config(ctx.settings))
    except Exception as exc:  # noqa: BLE001 - the type is the most useful part of a load failure
        raise CommandError("failed", f"{type(exc).__name__}: {exc}") from exc
    ctx.session = session
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
    return live_run.run_dryrun(p["strategy"].strip())


# -- Top 5 ---------------------------------------------------------------------------------------


def _asset_result(r) -> dict[str, Any]:
    return dataclasses.asdict(r)


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
          P("as_of", "string", "YYYY-MM-DD or YYYY-MM-DD HH:MM UTC; omit for the last bar.")))
def analyze_run(ctx: Context, p: dict[str, Any]) -> Any:
    raw = (p.get("as_of") or "").strip()
    when = analyze_mod.parse_as_of(raw) if raw else None
    result = analyze_mod.analyse(p["asset"], p.get("interval", "1d"), as_of=when)
    return {
        "headline": result.headline, "truncated": result.truncated,
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
            "best": ({"label": s.best.label, "median_sharpe": s.best.median_sharpe}
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


@command("queue.progress", "Background sweep progress line (cheap; no results re-read).")
def queue_progress(ctx: Context, p: dict[str, Any]) -> Any:
    return _queue_progress(ctx, bgqueue.read_state())


@command("queue.status", "Background sweep: progress, missing price data and the ranked leaderboard.")
def queue_status(ctx: Context, p: dict[str, Any]) -> Any:
    rt = ctx.runtime
    with rt.lock:
        # Only what the worker appended since last time: the results file grows without bound.
        fresh, cursor, restarted = bgqueue.read_results_since(rt.queue_cursor)
        if restarted:
            rt.queue_results = []  # truncated or replaced: what we hold belongs to a dead sweep
        rt.queue_results.extend(fresh)
        rt.queue_cursor = cursor
        results = list(rt.queue_results)
    ranked, floor = bgqueue.leaderboard(results, ctx.settings.asset)
    missing = _missing_series(ctx)
    fetch_log = bgqueue.BG_DIR / "fetch.log"
    return {
        **_queue_progress(ctx, bgqueue.read_state()),
        "missing": [{"asset": m.asset, "interval": m.interval, "command": m.command_text}
                    for m in missing],
        "fetch_log": str(fetch_log) if fetch_log.exists() else None,
        "ranked": [{**dataclasses.asdict(r), "label": r.label} for r in ranked[:200]],
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
