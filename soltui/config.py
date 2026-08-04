"""Settings load/save for the TUI. Pure logic; no UI, no I/O beyond one file.

Config lives at `~/.config/soltui/config.yaml`, following the same convention as
`netdnsmonitor`. YAML is optional at runtime -- if PyYAML is missing the app falls
back to JSON at the same path with a `.json` suffix, so a missing optional
dependency degrades rather than crashes.

## Safe defaults are a non-negotiable, not a preference

`CLAUDE.md` for this repo states: dry-run is the default, the extension installs
disarmed, and "never change a default so that a fresh install can place an
order." Accordingly `mode` defaults to `dry-run` and `armed` defaults to False,
and `validate()` REFUSES a config that sets `armed` without an explicit
`i_understand_this_is_simulated_only` acknowledgement -- which, in this build,
nothing can satisfy, because there is no live order path to arm. The field exists
so that a future live surface has to pass through a gate rather than inherit one.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "soltui"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
CONFIG_PATH_JSON = CONFIG_DIR / "config.json"

# Bar intervals the backtester understands. Kept here so the Settings tab can
# offer a closed list rather than a free-text field that fails at load time.
INTERVALS = ("1m", "5m", "15m", "1h", "6h", "1d")
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

    def to_dict(self) -> dict[str, Any]:
        """Plain dict for serialisation."""
        return asdict(self)


def default_settings() -> Settings:
    """A fresh, safe configuration."""
    return Settings()


def validate(settings: Settings) -> Settings:
    """Return `settings` if usable, else raise ConfigError naming the problem."""
    if settings.interval not in INTERVALS:
        raise ConfigError(
            f"interval {settings.interval!r} is not one of {INTERVALS}"
        )
    if settings.mode not in MODES:
        raise ConfigError(
            f"mode {settings.mode!r} is not supported. This build is "
            f"{MODES[0]}-only: there is no live order path to select."
        )
    if settings.capital <= 0:
        raise ConfigError("capital must be positive")
    if settings.fee_bps < 0 or settings.slippage_bps < 0:
        raise ConfigError("fee_bps and slippage_bps cannot be negative")
    if settings.fill_delay < 0:
        raise ConfigError("fill_delay cannot be negative (that would be look-ahead)")
    if settings.cpcv_groups < 2:
        raise ConfigError("cpcv_groups must be at least 2")
    if not 1 <= settings.cpcv_k < settings.cpcv_groups:
        raise ConfigError("cpcv_k must be at least 1 and fewer than cpcv_groups")
    if settings.poll_interval_seconds <= 0:
        raise ConfigError("poll_interval_seconds must be positive")
    # The arming gate. Both flags must be set together, and even then this build
    # has nothing to arm -- the check exists so a future live surface cannot
    # inherit an armed default from an old config file.
    if settings.armed and not settings.i_understand_this_is_simulated_only:
        raise ConfigError(
            "armed=True requires i_understand_this_is_simulated_only=True. "
            "Note that this build has no live order path regardless."
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
    return settings


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, falling back to defaults when no file exists.

    Unknown keys are ignored rather than fatal, so a config written by a newer
    build still loads in an older one.
    """
    candidates = [path] if path else [CONFIG_PATH, CONFIG_PATH_JSON]
    raw: dict[str, Any] | None = None
    for candidate in candidates:
        if candidate and candidate.exists():
            raw = _read(candidate)
            break
    if raw is None:
        return default_settings()

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
        target.write_text(yaml.safe_dump(payload, sort_keys=True))
    else:
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
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
