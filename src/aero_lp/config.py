"""TOML configuration."""

from __future__ import annotations

import tomllib
import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .chain import DEFAULT_RPCS
from .executor import ExecConfig
from .strategy import StrategyConfig

REWARD_MODES = ("auto", "aero", "fees", "keep")


@dataclass(frozen=True)
class SafetyConfig:
    max_position_usd: float = 10_000.0  # live mode refuses to touch bigger positions
    max_gas_usd: float = 2.0  # live mode refuses a rebalance whose gas estimate exceeds this
    max_twap_deviation_bps: float = 75.0  # skip when spot is this far from the 10-min TWAP (manipulation guard)
    min_check_interval_s: float = 30.0

    def __post_init__(self) -> None:
        if min(self.max_position_usd, self.max_gas_usd, self.max_twap_deviation_bps, self.min_check_interval_s) < 0:
            raise ValueError("safety limits must be >= 0")


@dataclass(frozen=True)
class Config:
    owner: str
    token_ids: list[int]
    rpc_url: str = DEFAULT_RPCS[0]
    pools: list[str] = field(default_factory=list)  # pools whose gauges to scan for staked positions
    poll_seconds: float = 60.0
    reward_mode: str = "auto"
    state_path: str = "~/.aero-lp/state.json"
    gas_units_estimate: int = 2_700_000  # measured: full staked rebalance with two swaps ~2.6M gas
    l1_fee_usd_estimate: float = 0.05
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    execution: ExecConfig = field(default_factory=ExecConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)

    def __post_init__(self) -> None:
        if self.reward_mode not in REWARD_MODES:
            raise ValueError(f"reward_mode must be one of {REWARD_MODES}")
        if not (self.owner.startswith("0x") and len(self.owner) == 42):
            raise ValueError("owner must be a 0x-prefixed 20-byte address")
        if self.gas_units_estimate <= 0 or self.poll_seconds <= 0:
            raise ValueError("gas_units_estimate and poll_seconds must be > 0")

    @property
    def state_file(self) -> Path:
        return Path(self.state_path).expanduser()


def _pick(cls: type, data: dict[str, Any]) -> Any:
    names = {f.name for f in fields(cls)}
    unknown = set(data) - names
    if unknown:
        raise ValueError(f"unknown {cls.__name__} keys: {sorted(unknown)}")
    return cls(**data)


def load(path: str | Path) -> Config:
    raw = tomllib.loads(Path(path).expanduser().read_text())
    strategy_raw = raw.pop("strategy", {})
    execution_raw = raw.pop("execution", {})
    if "max_slippage_bps" in strategy_raw and "max_slippage_bps" not in execution_raw:
        # StrategyConfig.max_slippage_bps is accepted for old configs but never read; the on-chain
        # min-out protection comes from [execution].max_slippage_bps.
        warnings.warn(
            "[strategy].max_slippage_bps has no effect; set [execution].max_slippage_bps "
            f"(currently {ExecConfig().max_slippage_bps})",
            stacklevel=2,
        )
    strategy = _pick(StrategyConfig, strategy_raw)
    execution = _pick(ExecConfig, execution_raw)
    safety = _pick(SafetyConfig, raw.pop("safety", {}))
    top_names = {f.name for f in fields(Config)} - {"strategy", "execution", "safety"}
    unknown = set(raw) - top_names
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")
    return Config(strategy=strategy, execution=execution, safety=safety, **raw)
