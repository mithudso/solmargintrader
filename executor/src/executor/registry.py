"""The executor command registry: one set of calls for the CLI and the HTTP API.

Every surface calls `dispatch(name, params, surface)`, which validates parameters, applies the confirm gate, runs the
handler, wraps the outcome in the response envelope and appends one line to the call log. The surfaces only carry
bytes; none holds command logic. This is the same envelope as soltui's registry so soltui can wrap these calls:

    {"ok": true,  "command": "<name>", "result": <json>, "error": null}
    {"ok": false, "command": "<name>", "result": null, "error": {"code": "...", "message": "..."}}

Codes: bad_params, unknown_command, forbidden, refused, failed, timeout, ambiguous. Nothing in `result` or `error`
names a surface, a time or a request id. The call log records parameter KEYS only, never values.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import gates, ledger
from .config import Config, home, load_config, log_dir, public_view
from .engine import Engine
from .errors import ExecutorError
from .signer import check_key_file_mode
from .tokens import USDC_MINT, WSOL_MINT, raw_to_ui

LOG_ROTATE_BYTES = 5 * 1024 * 1024
PARAM_TYPES = ("string", "number", "bool", "json")


class CommandError(ExecutorError):
    pass


@dataclass(frozen=True)
class Param:
    name: str
    type: str
    describe: str
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "required": self.required, "describe": self.describe}


@dataclass(frozen=True)
class Command:
    name: str
    describe: str
    handler: Callable[[Context, dict[str, Any]], Any]
    params: tuple[Param, ...] = ()
    read_only: bool = True
    long_running: bool = False
    requires_confirm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "describe": self.describe,
            "params": [p.to_dict() for p in self.params],
            "read_only": self.read_only,
            "long_running": self.long_running,
            "requires_confirm": self.requires_confirm,
        }


COMMANDS: dict[str, Command] = {}
CONFIRM_PARAM = Param("confirm", "bool", "Must be true. This command removes a safety stop on a real-money system.")


def P(name: str, type_: str, describe: str, required: bool = False) -> Param:
    return Param(name, type_, describe, required)


def command(name: str, describe: str, params=(), *, read_only=True, long_running=False, requires_confirm=False):
    def wrap(fn):
        declared = tuple(params) + ((CONFIRM_PARAM,) if requires_confirm else ())
        if name in COMMANDS:
            raise RuntimeError(f"duplicate command {name}")
        COMMANDS[name] = Command(name, describe, fn, declared, read_only, long_running, requires_confirm)
        return fn

    return wrap


# -- context -------------------------------------------------------------------------------------------------


class Context:
    """Per-call view: config is re-read on every call so an edit takes effect, and nothing is cached across calls."""

    def __init__(self, cfg: Config, engine: Engine):
        self.cfg = cfg
        self.engine = engine

    @classmethod
    def load(cls) -> Context:
        cfg = load_config(create=False)
        return cls(cfg, Engine(cfg))


# Tests replace this to inject a fake network; production never touches it.
CONTEXT_FACTORY: Callable[[], Context] = Context.load


# -- envelope ------------------------------------------------------------------------------------------------


def dumps(envelope: Any) -> str:
    """The one serialiser every surface uses, so equal envelopes are equal bytes."""
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def ok_envelope(name: str, result: Any) -> dict[str, Any]:
    return {"ok": True, "command": name, "result": result, "error": None}


def error_envelope(name: str, code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "command": name, "result": None, "error": {"code": code, "message": message}}


def jsonable(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [jsonable(v) for v in obj]
    if isinstance(obj, set | frozenset):
        return sorted(jsonable(v) for v in obj)
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, Path):
        return str(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return jsonable(dataclasses.asdict(obj))
    return obj


# -- call log ------------------------------------------------------------------------------------------------

_LOG_LOCK = threading.Lock()


def log_path() -> Path:
    return log_dir() / "calls.jsonl"


def _log_call(surface: str, name: str, env: dict[str, Any], ms: int, keys: list[str]) -> None:
    """One JSON line per call: parameter keys only, never values. Never raises."""
    line = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "surface": surface,
        "command": name,
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
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, (json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n").encode())
            finally:
                os.close(fd)
    except OSError:
        pass  # a full disk must not fail the call being logged


# -- parameters ----------------------------------------------------------------------------------------------


def _check_type(param: Param, value: Any) -> None:
    kind = param.type
    ok = (
        (kind == "string" and isinstance(value, str))
        or (kind == "number" and (type(value) is int or (type(value) is float and math.isfinite(value))))
        or (kind == "bool" and isinstance(value, bool))
        or kind == "json"
    )
    if not ok:
        raise ExecutorError(f'parameter "{param.name}" must be {kind}', "bad_params")


def validate_params(cmd: Command, params: Any) -> dict[str, Any]:
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ExecutorError("params must be an object", "bad_params")
    declared = {p.name: p for p in cmd.params}
    for key in params:
        if key not in declared:
            raise ExecutorError(f'command "{cmd.name}" has no parameter "{key}"', "bad_params")
    out: dict[str, Any] = {}
    for p in cmd.params:
        value = params.get(p.name)
        if value is None:
            if p.required:
                raise ExecutorError(f'missing required parameter "{p.name}"', "bad_params")
            continue
        _check_type(p, value)
        out[p.name] = value
    return out


def coerce_cli_value(param: Param, raw: str) -> Any:
    """Command-line / query-string text -> the declared type."""
    if param.type == "number":
        try:
            n = float(raw)
        except ValueError:
            raise ExecutorError(f'"{param.name}" must be a number', "bad_params") from None
        return int(n) if n.is_integer() and "." not in raw and "e" not in raw.lower() else n
    if param.type == "bool":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ExecutorError(f'"{param.name}" must be true or false', "bad_params")
    if param.type == "json":
        try:
            return json.loads(raw)
        except ValueError:
            raise ExecutorError(f'"{param.name}" must contain valid JSON', "bad_params") from None
    return raw


def coerce_pairs(name: str, pairs: dict[str, str]) -> dict[str, Any]:
    cmd = COMMANDS.get(name)
    declared = {p.name: p for p in cmd.params} if cmd else {}
    return {k: (coerce_cli_value(declared[k], v) if k in declared else v) for k, v in pairs.items()}


# -- dispatch ------------------------------------------------------------------------------------------------


def describe_commands() -> list[dict[str, Any]]:
    return [COMMANDS[n].to_dict() for n in sorted(COMMANDS)]


def _execute(name: str, params: Any) -> dict[str, Any]:
    if name == "list":
        return ok_envelope("list", describe_commands())
    cmd = COMMANDS.get(name)
    if cmd is None:
        return error_envelope(str(name), "unknown_command", f'unknown command "{name}"')
    try:
        clean = validate_params(cmd, params)
        if cmd.requires_confirm and clean.get("confirm") is not True:
            raise ExecutorError(
                f"{name} removes a safety stop on a real-money system; pass confirm=true to proceed", "forbidden"
            )
        clean.pop("confirm", None)
        result = cmd.handler(CONTEXT_FACTORY(), clean)
        return ok_envelope(name, jsonable(result))
    except ExecutorError as exc:
        return error_envelope(name, exc.code, exc.message)
    except Exception as exc:  # noqa: BLE001 - a surface must always get an envelope back
        # Only the type: a message from deep in a library could carry request content.
        return error_envelope(name, "failed", f"internal error: {type(exc).__name__}")


def dispatch(name: str, params: dict[str, Any] | None = None, surface: str = "api") -> dict[str, Any]:
    """Run one command and log it. The only entry point any surface may use."""
    t0 = time.monotonic()
    env = _execute(name, params)
    keys = sorted(params) if isinstance(params, dict) else []
    _log_call(surface, str(name), env, int((time.monotonic() - t0) * 1000), [str(k) for k in keys])
    return env


# -- commands ------------------------------------------------------------------------------------------------


@command(
    "quote",
    "Best price for a swap on Solana (Jupiter) checked against an independent price; with to_chain, a quote-only "
    "cross-chain price (LI.FI). Moves no funds.",
    (
        P("from", "string", "Token symbol or mint to sell (SOL, USDC)", True),
        P("to", "string", "Token symbol or mint to buy; with to_chain, a token on that chain (ETH, USDC)", True),
        P("amount", "string", "Amount of `from` in UI units as a decimal string, e.g. '1.5'", True),
        P("to_chain", "string", "Destination chain for a quote-only cross-chain price, e.g. 'base'"),
        P("slippage_bps", "number", "Tighter slippage than the configured cap (never looser)"),
    ),
)
def _quote(ctx: Context, p: dict[str, Any]) -> Any:
    return ctx.engine.quote(p["from"], p["to"], p["amount"], p.get("to_chain"), p.get("slippage_bps"))


@command(
    "swap",
    "Build, verify and simulate a Jupiter swap; sign and send only when live=true and config mode is live. "
    "Dry-run (the default) simulates exactly what live would send.",
    (
        P("from", "string", "Token symbol or mint to sell", True),
        P("to", "string", "Token symbol or mint to buy", True),
        P("amount", "string", "Amount of `from` in UI units as a decimal string", True),
        P("strategy", "string", "Strategy id; required for live. Positions and gates are tracked per strategy"),
        P("live", "bool", "Actually send. Also needs config mode = live. Default false"),
        P(
            "exit",
            "bool",
            "Reduce-only sell of the strategy's open position; not stopped by KILL, the loss stop or gates",
        ),
        P("reason", "string", "Why; required for live, written to the journal before sending"),
        P("request_id", "string", "Durable caller UUID; identical replay never sends again"),
        P("slippage_bps", "number", "Tighter slippage than the configured cap (never looser)"),
    ),
    read_only=False,
    long_running=True,
)
def _swap(ctx: Context, p: dict[str, Any]) -> Any:
    s = p.get("slippage_bps")
    return ctx.engine.swap(
        p["from"],
        p["to"],
        p["amount"],
        strategy=p.get("strategy"),
        live=bool(p.get("live", False)),
        exit_only=bool(p.get("exit", False)),
        reason=p.get("reason"),
        request_id=p.get("request_id"),
        slippage_bps=int(s) if s is not None else None,
    )


@command(
    "status", "Mode, KILL state, balances, unresolved sends, per-strategy positions, gates and the effective rails."
)
def _status(ctx: Context, p: dict[str, Any]) -> Any:
    cfg, eng = ctx.cfg, ctx.engine
    states = eng.journal.states()
    strategies = sorted(
        {s["intent"].get("strategy") for s in states.values() if s.get("intent") and s["intent"].get("strategy")}
    )
    out: dict[str, Any] = {
        "mode": cfg.mode,
        "kill": (eng.root / "KILL").exists(),
        "config": public_view(cfg),
        "key_file_ok": True,
        "unresolved": [{"id": s["id"], "state": s["state"]} for s in eng.journal.unresolved()],
        "journal_corrupt_lines": eng.journal.corrupt_lines(),
        "daily_pnl_usd": str(ledger.realized_pnl_usd(states, ledger.utc_day(time.time()))),
        "strategies": {},
    }
    try:
        check_key_file_mode(Path(cfg.key_file).expanduser())
    except ExecutorError as exc:
        out["key_file_ok"] = False
        out["key_file_problem"] = exc.message
    for sid in strategies:
        out["strategies"][sid] = {
            "positions": {
                mint: {"qty_raw": pos.qty_raw, "cost_usd": str(pos.cost_usd)}
                for mint, pos in ledger.positions(states, sid).items()
            },
            "gates": gates.summary(eng.root, cfg, sid),
        }
    try:
        from .txverify import ata_address

        usdc_ata = ata_address(cfg.owner, USDC_MINT)
        sol = eng.rpc.balance(cfg.owner)
        acct = eng.rpc.accounts([usdc_ata])[0]
        usdc_raw = int.from_bytes(acct["data"][64:72], "little") if acct and len(acct["data"]) >= 72 else 0
        out["balances"] = {
            "SOL": str(raw_to_ui(sol, 9)),
            "USDC": str(raw_to_ui(usdc_raw, 6)),
            "sol_lamports": sol,
            "usdc_raw": usdc_raw,
        }
    except ExecutorError as exc:
        out["balances_error"] = exc.message
    out["wsol_mint"] = WSOL_MINT
    return out


@command(
    "journal",
    "The append-only journal: recent records (intents, sends, results, unknowns).",
    (P("limit", "number", "How many recent records (default 20)"), P("strategy", "string", "Only this strategy")),
)
def _journal(ctx: Context, p: dict[str, Any]) -> Any:
    limit = int(p.get("limit", 20))
    if limit <= 0 or limit > 500:
        raise ExecutorError("limit must be 1..500", "bad_params")
    recs = ctx.engine.journal.tail(500 if p.get("strategy") else limit)
    states = ctx.engine.journal.states()
    if p.get("strategy"):
        ids = {i for i, s in states.items() if (s.get("intent") or {}).get("strategy") == p["strategy"]}
        recs = [r for r in recs if r.get("id") in ids][-limit:]
    return {"records": recs, "unresolved": [s["id"] for s in ctx.engine.journal.unresolved()]}


@command(
    "kill",
    "Halt all live swaps (creates the KILL file). Only --exit sells still run. Needs no confirm.",
    (P("reason", "string", "Why"),),
    read_only=False,
)
def _kill(ctx: Context, p: dict[str, Any]) -> Any:
    path = ctx.engine.root / "KILL"
    ctx.engine.root.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"{datetime.now(UTC).isoformat()} {str(p.get('reason', 'kill'))[:200]}\n")
    return {"kill": True, "path": str(path)}


@command(
    "resume",
    "Remove the KILL file. Removes a safety stop on a real-money system, so it needs confirm=true.",
    (),
    read_only=False,
    requires_confirm=True,
)
def _resume(ctx: Context, p: dict[str, Any]) -> Any:
    path = ctx.engine.root / "KILL"
    existed = path.exists()
    if existed:
        path.unlink()
    return {"kill": False, "was_present": existed}


@command(
    "gates",
    "Pre-live gates for a strategy: dry-run soak and research gate.",
    (P("strategy", "string", "Strategy id", True),),
)
def _gates(ctx: Context, p: dict[str, Any]) -> Any:
    return gates.summary(ctx.engine.root, ctx.cfg, p["strategy"])


@command(
    "gates.record_research",
    "Record a backtest/research gate result for a strategy. Never record a pass that did not happen.",
    (
        P("strategy", "string", "Strategy id", True),
        P("result", "string", "pass or fail", True),
        P("source", "string", "Where the result came from (report path, run id)", True),
        P("note", "string", "Free text"),
    ),
    read_only=False,
)
def _record_research(ctx: Context, p: dict[str, Any]) -> Any:
    return gates.record_research_result(
        ctx.engine.root, ctx.cfg, p["strategy"], p["result"], p["source"], p.get("note", "")
    )


@command(
    "reconcile",
    "Resolve unknown sends from the chain by signature. The only way to clear the block; never re-sends anything.",
    read_only=False,
)
def _reconcile(ctx: Context, p: dict[str, Any]) -> Any:
    return ctx.engine.reconcile()


def default_home() -> Path:
    return home()


@command("wallet.capabilities", "Versioned installed executor identity and supported guarded capabilities.")
def _wallet_capabilities(ctx, p):
    from .manager import capabilities

    return capabilities(ctx.engine)


@command(
    "wallet.register",
    "Enroll explicit shared-wallet writers and portfolio cap; never enable live mode.",
    (
        P("portfolio_cap_usd", "string", "Explicit wallet-wide capital cap", True),
        P("clients", "json", "Complete writer inventory: absolute root and aware boolean", True),
        P("inventory_complete", "bool", "Explicit complete known writer inventory", True),
    ),
    read_only=False,
)
def _wallet_register(ctx, p):
    return ctx.engine.authority.register(p["portfolio_cap_usd"], p["clients"], p["inventory_complete"])


@command(
    "manager.admit",
    "Read exact current scoped evidence and guarded executor admission; never sign.",
    (P("request", "json", "Exact protocol1 scope and intent", True),),
)
def _manager_admit(ctx, p):
    from .manager import admit

    return admit(ctx.engine, p["request"])


@command(
    "manager.swap",
    "Delegate exact caller intent through the existing verifier, shared writer and journal.",
    (P("request", "json", "Exact protocol1 scope and intent", True),),
    read_only=False,
    long_running=True,
)
def _manager_swap(ctx, p):
    from .manager import execute

    return execute(ctx.engine, p["request"])


@command(
    "manager.status",
    "Read a caller request receipt without initializing a wallet authority.",
    (P("request_id", "string", "Original caller UUID", True),),
)
def _manager_status(ctx, p):
    return ctx.engine.authority.status(p["request_id"])
