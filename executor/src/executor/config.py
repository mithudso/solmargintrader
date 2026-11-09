"""Configuration: `~/.executor/config.toml` (or `$EXECUTOR_HOME/config.toml`), created mode 600 with safe defaults.

Fail closed: an unknown key, a wrong type, a non-finite or non-positive number, or a file that other users can
write is an error. Defaults are the owner's (2026-11-07): max position $25 per strategy, daily loss stop $10.
The code default mode is `dry-run`; live needs `mode = "live"` here AND `--live` on the call.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

from .errors import ExecutorError
from .tokens import TOKENS, resolve

OWNER_SOLANA = "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV"
OWNER_BASE = "0x901a89cEC0608eB5435A915f006b45bD46405314"

# The reserved strategy id for proving the live path. It is not a trading strategy: the code caps it at
# $2 per trade and $4 per rolling 24 h, and it exists only while `[validation].enabled = true`.
VALIDATION_STRATEGY = "path-validation"
VALIDATION_MAX_TRADE_USD = 2.0
VALIDATION_MAX_DAILY_USD = 4.0

HEADER = """\
# executor configuration. Created with safe defaults; mode 600.
# Code default is dry-run. Live needs mode = "live" here AND --live on the call.
# Never raise a limit on an agent's own initiative: these are the owner's numbers.
"""


@dataclass
class Rails:
    max_position_usd: float = 25.0  # per strategy, cost basis of the open position (owner: 25)
    daily_loss_stop_usd: float = 10.0  # realized loss + fees per UTC day; stops new buys (owner: 10)
    max_trade_usd: float = 10.0  # one swap, valued with the independent price reference
    max_slippage_bps: int = 50
    max_price_impact_bps: int = 50
    max_price_deviation_bps: int = 100  # quote rate vs the Jupiter Price API reference
    max_priority_fee_lamports: int = 200_000
    max_quote_age_s: float = 20.0
    min_sol_reserve_lamports: int = 5_000_000  # a swap may not leave less native SOL than this
    allowed_mints: list[str] = field(default_factory=lambda: ["SOL", "USDC"])
    confirm_timeout_s: float = 60.0


@dataclass
class Gates:
    soak_hours: float = 24.0
    min_dry_runs: int = 5
    allow_failed_research_gate: bool = False  # the owner's explicit override; every use is logged
    research_gate_file: str = ""


@dataclass
class Validation:
    enabled: bool = False  # lets the reserved strategy `path-validation` skip the strategy gates, tiny caps only


@dataclass
class Bridge:
    max_cost_bps: int = 100  # a cross-chain quote costing more than this is refused
    evm_address: str = OWNER_BASE


@dataclass
class Config:
    mode: str = "dry-run"
    owner: str = OWNER_SOLANA
    key_file: str = "~/.ssh/solana.private"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    jupiter_base_url: str = "https://lite-api.jup.ag"
    lifi_base_url: str = "https://li.quest"
    rails: Rails = field(default_factory=Rails)
    gates: Gates = field(default_factory=Gates)
    validation: Validation = field(default_factory=Validation)
    bridge: Bridge = field(default_factory=Bridge)
    path: Path | None = None  # where it was loaded from; not part of the fingerprint

    def mint_allowlist(self) -> set[str]:
        return {resolve(x).mint for x in self.rails.allowed_mints}


def home() -> Path:
    return Path(os.environ.get("EXECUTOR_HOME", "~/.executor")).expanduser()


def log_dir() -> Path:
    return Path(os.environ.get("EXECUTOR_LOG_DIR") or Path.home() / "Library" / "Logs" / "executor")


def default_toml() -> str:
    c = Config()
    r, g, b = c.rails, c.gates, c.bridge

    def arr(xs: list[str]) -> str:
        return "[" + ", ".join(json.dumps(x) for x in xs) + "]"

    return (
        HEADER
        + f'mode = "{c.mode}"\nowner = "{c.owner}"\nkey_file = "{c.key_file}"\nrpc_url = "{c.rpc_url}"\n'
        + f'jupiter_base_url = "{c.jupiter_base_url}"\nlifi_base_url = "{c.lifi_base_url}"\n\n'
        + "[rails]\n"
        + f"max_position_usd = {r.max_position_usd}\ndaily_loss_stop_usd = {r.daily_loss_stop_usd}\n"
        + f"max_trade_usd = {r.max_trade_usd}\nmax_slippage_bps = {r.max_slippage_bps}\n"
        + f"max_price_impact_bps = {r.max_price_impact_bps}\nmax_price_deviation_bps = {r.max_price_deviation_bps}\n"
        + f"max_priority_fee_lamports = {r.max_priority_fee_lamports}\nmax_quote_age_s = {r.max_quote_age_s}\n"
        + f"min_sol_reserve_lamports = {r.min_sol_reserve_lamports}\nconfirm_timeout_s = {r.confirm_timeout_s}\n"
        + f"allowed_mints = {arr(r.allowed_mints)}\n\n"
        + "[gates]\n"
        + f"soak_hours = {g.soak_hours}\nmin_dry_runs = {g.min_dry_runs}\n"
        + 'allow_failed_research_gate = false\nresearch_gate_file = ""\n\n'
        + "[validation]\nenabled = false\n\n"
        + f'[bridge]\nmax_cost_bps = {b.max_cost_bps}\nevm_address = "{b.evm_address}"\n'
    )


def _check_file_mode(path: Path) -> None:
    st = path.stat()
    if st.st_uid != os.getuid():
        raise ExecutorError(f"config {path} is not owned by you")
    if st.st_mode & 0o022:
        raise ExecutorError(f"config {path} is writable by others (mode {oct(stat.S_IMODE(st.st_mode))}); chmod 600")


def _merge(cls: type, raw: Any, where: str):
    if not isinstance(raw, dict):
        raise ExecutorError(f"config [{where}] must be a table")
    known = {f.name: f for f in fields(cls) if f.name != "path"}
    extra = set(raw) - set(known)
    if extra:
        raise ExecutorError(f"config [{where}] has unknown key(s): {', '.join(sorted(extra))}")
    base = cls()
    for key, value in raw.items():
        default = getattr(base, key)
        if isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, int):
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif isinstance(default, float):
            ok = isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)
            value = float(value) if ok else value
        elif isinstance(default, list):
            ok = isinstance(value, list) and all(isinstance(x, str) for x in value)
        elif isinstance(default, str):
            ok = isinstance(value, str)
        else:
            ok = False
        if not ok:
            raise ExecutorError(f"config [{where}].{key} has the wrong type or value")
        setattr(base, key, value)
    return base


def _endpoint(url: str) -> SplitResult:
    try:
        endpoint = urlsplit(url)
        port = endpoint.port
        if not endpoint.hostname or (port is not None and port == 0):
            raise ValueError
        if endpoint.scheme != "https" and not (endpoint.scheme == "http" and endpoint.hostname == "127.0.0.1"):
            raise ValueError
    except (TypeError, ValueError):
        raise ExecutorError("config URLs must be valid https:// endpoints (or http://127.0.0.1 for tests)") from None
    return endpoint


def validate(cfg: Config) -> Config:
    if cfg.mode not in ("dry-run", "live"):
        raise ExecutorError('config mode must be "dry-run" or "live"')
    r = cfg.rails
    for name in ("max_position_usd", "daily_loss_stop_usd", "max_trade_usd", "max_quote_age_s", "confirm_timeout_s"):
        if not getattr(r, name) > 0:
            raise ExecutorError(f"config rails.{name} must be positive")
    for name in ("max_slippage_bps", "max_price_impact_bps", "max_price_deviation_bps", "max_priority_fee_lamports"):
        if getattr(r, name) <= 0:
            raise ExecutorError(f"config rails.{name} must be positive")
    if r.max_slippage_bps > 1000 or r.max_price_impact_bps > 1000 or r.max_price_deviation_bps > 1000:
        raise ExecutorError("config slippage, impact and deviation caps may not exceed 1000 bps")
    if r.min_sol_reserve_lamports < 0:
        raise ExecutorError("config rails.min_sol_reserve_lamports may not be negative")
    if r.max_trade_usd > r.max_position_usd:
        raise ExecutorError("config rails.max_trade_usd may not exceed rails.max_position_usd")
    if not r.allowed_mints:
        raise ExecutorError("config rails.allowed_mints may not be empty")
    for ref in r.allowed_mints:
        resolve(ref)  # raises Refused for a token the table does not know
    if cfg.gates.soak_hours < 0 or cfg.gates.min_dry_runs < 0:
        raise ExecutorError("config gates.soak_hours and gates.min_dry_runs may not be negative")
    if not 0 < cfg.bridge.max_cost_bps <= 1000:
        raise ExecutorError("config bridge.max_cost_bps must be in (0, 1000]")
    for url in (cfg.rpc_url, cfg.jupiter_base_url, cfg.lifi_base_url):
        _endpoint(url)
    return cfg


def load_config(path: Path | None = None, create: bool = True) -> Config:
    """Load and validate. Creates the file (mode 600, safe defaults) if missing and `create` is true."""
    path = path or home() / "config.toml"
    if not path.exists():
        if not create:
            return validate(Config(path=path))
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(default_toml())
    _check_file_mode(path)
    try:
        raw = tomllib.loads(path.read_text())
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ExecutorError(f"config {path} is unreadable: {exc}") from None
    sections = {"rails": Rails, "gates": Gates, "validation": Validation, "bridge": Bridge}
    top = {k: v for k, v in raw.items() if k not in sections}
    cfg = _merge(Config, top, "top level")
    for name, cls in sections.items():
        if name in raw:
            setattr(cfg, name, _merge(cls, raw[name], name))
    cfg.path = path
    return validate(cfg)


def fingerprint(cfg: Config, strategy: str) -> str:
    """Hash of everything that changes what a strategy may do. A change resets that strategy's dry-run soak."""
    doc = {
        "strategy": strategy,
        "owner": cfg.owner,
        "rails": asdict(cfg.rails),
    }
    return hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()


def public_view(cfg: Config) -> dict[str, Any]:
    """Config for `status`: nothing secret lives in it, but the key file path is shown as a name only."""
    endpoint = _endpoint(cfg.rpc_url)
    host = endpoint.hostname
    if ":" in host:
        host = f"[{host}]"
    if endpoint.port is not None:
        host = f"{host}:{endpoint.port}"
    return {
        "mode": cfg.mode,
        "owner": cfg.owner,
        "rpc_host": host,
        "rails": asdict(cfg.rails),
        "gates": asdict(cfg.gates),
        "validation": asdict(cfg.validation),
        "bridge": asdict(cfg.bridge),
        "tokens": sorted(TOKENS),
    }
