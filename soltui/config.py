"""Settings load/save for the TUI. Pure logic; no UI, no I/O beyond one file.

Config lives at `~/.config/soltui/config.yaml`, following the same convention as
`netdnsmonitor`. YAML is optional at runtime -- if PyYAML is missing the app falls
back to JSON at the same path with a `.json` suffix, so a missing optional
dependency degrades rather than crashes.

## Safe defaults are a non-negotiable, not a preference

`CLAUDE.md` for this repo states: dry-run is the default, the extension installs
disarmed, and "never change a default so that a fresh install can place an
order." Accordingly `mode` defaults to `dry-run` and `armed` defaults to False,
and `validate()` refuses `armed` without the explicit simulation acknowledgement.
These fields govern strategy simulations only. The manual Coinbase form has a
separate, session-only arm control and cannot inherit this setting.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

# SOLTUI_CONFIG_DIR exists so tests and the bridge parity suite never touch the owner's real config.
CONFIG_DIR = Path(os.environ.get("SOLTUI_CONFIG_DIR") or Path.home() / ".config" / "soltui")
CONFIG_PATH = CONFIG_DIR / "config.yaml"
CONFIG_PATH_JSON = CONFIG_DIR / "config.json"

# Bar intervals the backtester understands. Kept here so the Settings tab can
# offer a closed list rather than a free-text field that fails at load time.
INTERVALS = ("1m", "5m", "15m", "1h", "6h", "1d")
XPUB_FIELDS = {"btc_xpub": "btc", "ltc_xpub": "ltc", "doge_xpub": "doge"}
MODES = ("dry-run",)  # live execution is deliberately absent, see module docstring


class ConfigError(ValueError):
    """Raised when a config would be unsafe or unusable."""


@dataclass
class Settings:
    """Everything the TUI needs to run a sweep or a paper session."""

    asset: str = "SOL"
    interval: str = "1d"
    start: str = "2021-01-01"
    end: str = ""  # empty means "through the end of the data"
    capital: float = 10_000.0
    fee_schedule: str = "jupiter-perps"
    use_leverage: bool = False
    leverage: float = 2.0
    allow_short: bool = False
    min_confidence: float = 0.80
    borrow_long_bps_hour: float = 0.8
    borrow_short_bps_hour: float = 0.15
    fee_bps: float = 6.0
    slippage_bps: float = 2.0
    fill_delay: int = 1
    # CPCV geometry.
    cpcv_groups: int = 8
    cpcv_k: int = 2
    # Execution mode. Only 'dry-run' exists in this build.
    mode: str = "dry-run"
    armed: bool = False
    i_understand_this_is_simulated_only: bool = False
    # Menu-bar refresh cadence, seconds.
    poll_interval_seconds: float = 2.0
    data_dir: str = "data"
    enabled_strategies: list[str] = field(
        default_factory=lambda: ["buy_and_hold", "ma_crossover", "rsi", "breakout"]
    )
    # Editable signal parameters from the Signals tab. Stored as a plain dict so
    # the config file round-trips through YAML/JSON without a custom
    # representer; `signals.from_dict()` rebuilds and validates the dataclass.
    signal_defaults: dict[str, Any] = field(default_factory=dict)
    # Roster entries with their parameters ([{"name", "params"}]). `enabled_strategies` keeps only
    # names, which loses pinned params across a restart; the command registry persists every roster
    # change here so a CLI/API/extension call and the TUI see the same roster. Empty = use the names.
    roster: list[dict[str, Any]] = field(default_factory=list)
    # PUBLIC addresses the read-only wallet scan looks at. These are not secrets: they are the owner's
    # two wallets as already written in CLAUDE.md. There is deliberately no field for a private key.
    solana_address: str = "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV"
    base_address: str = "0x901a89cEC0608eB5435A915f006b45bD46405314"
    # Ethereum mainnet. The same EVM key as `base_address`, seen on L1.
    eth_address: str = ""
    # The Hyperliquid account the compound 5m tab sizes calls from (read-only `info` calls). The owner
    # confirmed on 2026-11-07 that it is the same EVM address as `base_address`.
    hyperliquid_address: str = "0x901a89cEC0608eB5435A915f006b45bD46405314"
    # EXTENDED PUBLIC keys for the UTXO chains. They derive every address of a wallet but cannot spend,
    # yet they expose its whole history, so the surfaces redact them (`public_dict`) and the file is 0600.
    btc_xpub: str = ""
    ltc_xpub: str = ""
    doge_xpub: str = ""
    # Automatically start forward testing across all coins, strategies, and timeframes on TUI launch.
    forwardtest_autostart: bool = True
    live_vote_min_accuracy: float = 60.0
    live_vote_min_resolved: int = 20

    def to_dict(self) -> dict[str, Any]:
        """Plain dict for serialisation to the config file. Holds the full xpubs."""
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        """The dict every surface returns: xpubs replaced by a short prefix and a `*_set` flag."""
        from .hdwallet import redact

        out = asdict(self)
        for name in XPUB_FIELDS:
            out[f"{name}_set"] = bool(out[name])
            out[name] = redact(out[name])
        return out


def default_settings() -> Settings:
    """A fresh, safe configuration."""
    return Settings()


def validate(settings: Settings) -> Settings:
    """Return `settings` if usable, else raise ConfigError naming the problem."""
    from .simulation import from_settings

    try:
        from_settings(settings)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    if settings.interval not in INTERVALS:
        raise ConfigError(
            f"interval {settings.interval!r} is not one of {INTERVALS}"
        )
    if settings.mode not in MODES:
        raise ConfigError(
            f"mode {settings.mode!r} is not supported. This build is "
            f"{MODES[0]}-only for strategy execution. Manual Coinbase orders are separate."
        )
    for name in ("capital", "poll_interval_seconds"):
        value = getattr(settings, name)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0):
            raise ConfigError(f"{name} must be a finite positive number")
    if settings.fee_bps < 0 or settings.slippage_bps < 0:
        raise ConfigError("fee_bps and slippage_bps cannot be negative")
    for name in ("fill_delay", "cpcv_groups", "cpcv_k"):
        value = getattr(settings, name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{name} must be an integer")
    if settings.fill_delay < 0:
        raise ConfigError("fill_delay cannot be negative (that would be look-ahead)")
    if settings.cpcv_groups < 2:
        raise ConfigError("cpcv_groups must be at least 2")
    if not 1 <= settings.cpcv_k < settings.cpcv_groups:
        raise ConfigError("cpcv_k must be at least 1 and fewer than cpcv_groups")
    # Wallet addresses may be blank (no scan for that chain) but not malformed: a typo would otherwise
    # scan, or show an empty balance for, the wrong account.
    # Messages never echo the value: a private key pasted here must not be repeated into a log or screen.
    from . import hdwallet

    checks = [("solana_address", hdwallet.validate_solana_address), ("base_address", hdwallet.validate_evm_address),
              ("eth_address", hdwallet.validate_evm_address), ("hyperliquid_address", hdwallet.validate_evm_address)]
    for name, check in checks:
        value = getattr(settings, name)
        if value:
            try:
                check(value)
            except hdwallet.ExtKeyError as exc:
                raise ConfigError(f"{name}: {exc}") from None
    for name, coin in XPUB_FIELDS.items():
        value = getattr(settings, name)
        if value:
            try:
                hdwallet.parse_extended_key(value, coin)
            except hdwallet.ExtKeyError as exc:
                raise ConfigError(f"{name}: {exc}") from None
    # Simulation settings cannot arm the separate manual Coinbase form.
    if settings.armed and not settings.i_understand_this_is_simulated_only:
        raise ConfigError(
            "armed=True requires i_understand_this_is_simulated_only=True. "
            "This setting cannot arm manual Coinbase orders."
        )
    # Signal defaults are validated by their own module, which knows the
    # relationships (fast < slow, oversold < exit). Surfacing the failure as a
    # ConfigError keeps one error type for the caller to handle.
    if settings.signal_defaults:
        from .signals import SignalError, from_dict

        try:
            from_dict(settings.signal_defaults)
        except SignalError as exc:
            raise ConfigError(f"signal_defaults: {exc}") from exc
    if (isinstance(settings.live_vote_min_accuracy, bool)
            or not isinstance(settings.live_vote_min_accuracy, (int, float))
            or not math.isfinite(settings.live_vote_min_accuracy)
            or not 0 <= settings.live_vote_min_accuracy <= 100):
        raise ConfigError("live_vote_min_accuracy must be a finite percentage from 0 to 100")
    if (isinstance(settings.live_vote_min_resolved, bool)
            or not isinstance(settings.live_vote_min_resolved, int)
            or settings.live_vote_min_resolved < 1):
        raise ConfigError("live_vote_min_resolved must be a positive whole number")
    if not isinstance(settings.forwardtest_autostart, bool):
        raise ConfigError("forwardtest_autostart must be a boolean")
    return settings


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, falling back to defaults when no file exists.

    Unknown keys are ignored rather than fatal, so a config written by a newer
    build still loads in an older one.
    """
    # Parser installation must not resurrect an older representation. Explicit
    # paths stay authoritative; automatic loading follows the newest saved file.
    candidates = ([path] if path else sorted(
        (p for p in (CONFIG_PATH, CONFIG_PATH_JSON) if p.exists()),
        key=lambda p: p.stat().st_mtime_ns, reverse=True))
    raw: dict[str, Any] | None = None
    for candidate in candidates:
        if candidate and candidate.exists():
            if candidate.suffix in (".yaml", ".yml") and _yaml() is None:
                # A previous YAML installation may coexist with a usable JSON
                # replacement after its optional parser becomes unavailable.
                try:
                    raw = _read(candidate)  # JSON written without PyYAML remains readable.
                except json.JSONDecodeError:
                    if path is None and CONFIG_PATH_JSON.exists():
                        continue
                    raise ConfigError("PyYAML is required to read the existing YAML configuration") from None
                break
            raw = _read(candidate)
            break
    if raw is None:
        return default_settings()
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")

    # Migrate the old venue-independent (often Coinbase) fee assumption once.
    if "fee_schedule" not in raw:
        raw["fee_bps"] = 6.0
    known = {f.name for f in fields(Settings)}
    filtered = {k: v for k, v in raw.items() if k in known}
    return validate(Settings(**filtered))


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    """Persist settings, validating first. Returns the path written."""
    validate(settings)
    target = path or (CONFIG_PATH if _yaml() else CONFIG_PATH_JSON)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.to_dict()
    yaml = _yaml()
    if yaml and target.suffix in (".yaml", ".yml"):
        text = yaml.safe_dump(payload, sort_keys=True)
    else:
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    # Keep the old settings intact on failure and never place an xpub in an
    # existing inode that another account can read.
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def _read(path: Path) -> dict[str, Any]:
    """Parse a config file as YAML when available, else JSON."""
    text = path.read_text()
    yaml = _yaml()
    if yaml and path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text) or {}
    return json.loads(text or "{}")


def _yaml():
    """PyYAML if installed, else None. Optional by design."""
    try:
        import yaml  # noqa: PLC0415 - optional dependency, probed at call time

        return yaml
    except ImportError:
        return None
