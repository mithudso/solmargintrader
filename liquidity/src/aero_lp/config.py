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


DEFAULT_ALLOWED = ("WETH", "USDC", "USDT", "cbBTC", "wstETH", "cbETH", "weETH", "rETH", "AERO", "DAI", "USDbC", "EURC")


@dataclass(frozen=True)
class AllocatorConfig:
    """Idle-capital deployment, compounding and experiments (used by `aero-lp daemon`)."""

    enabled: bool = True
    min_net_apr: float = 5.0  # both the model and the historical backtest must clear this (APR %)
    min_edge_ratio: float = 1.2  # income / LVR
    min_confidence: str = "medium"  # high | medium | low
    min_tvl_usd: float = 100_000.0
    min_position_usd: float = 10.0
    max_position_usd: float = 200.0
    max_total_deployed_usd: float = 500.0
    max_arms: int = 3  # side-by-side experiment size when candidates are close
    compare_margin: float = 0.30  # candidates within 30% of the best score join the experiment
    experiment_days: float = 7.0
    graduate_margin_apr: float = 5.0  # winner must beat an arm by this much realized APR to close the arm
    idle_window_hours: float = 24.0  # a coin is idle only if it sat in the wallet this long
    gas_reserve_eth: float = 0.0003
    unwrap_chunk_eth: float = 0.0005
    allowed_tokens: tuple[str, ...] = DEFAULT_ALLOWED
    exclude_tokens: tuple[str, ...] = ()
    scout_interval_h: float = 6.0
    allocate_interval_h: float = 1.0
    compound_interval_h: float = 1.0
    compound_min_usd: float = 1.0
    compound_gas_multiple: float = 10.0  # compound only when the reward is >= this many times the gas
    scout_top_by_volume: int = 20
    snapshot_interval_min: float = 15.0

    def __post_init__(self) -> None:
        if self.min_confidence not in ("high", "medium", "low"):
            raise ValueError("min_confidence must be high, medium or low")
        if self.max_arms < 1 or self.min_position_usd <= 0 or self.max_position_usd < self.min_position_usd:
            raise ValueError("bad allocator sizing")
        if not 0 <= self.compare_margin < 1:
            raise ValueError("compare_margin must be in [0, 1)")


@dataclass(frozen=True)
class Config:
    owner: str
    token_ids: list[int] = field(default_factory=list)
    rpc_url: str = DEFAULT_RPCS[0]
    pools: list[str] = field(default_factory=list)  # pools whose gauges to scan for staked positions
    poll_seconds: float = 60.0
    reward_mode: str = "auto"
    key_file: str = ""  # optional path to a chmod-600 file holding the signing key (live mode only)
    state_path: str = "~/.aero-lp/state.json"
    gas_units_estimate: int = 2_700_000  # measured: full staked rebalance with two swaps ~2.6M gas
    l1_fee_usd_estimate: float = 0.005  # measured 2026-11-06: two txs paid 0.0000037 ETH in total incl. L1
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    execution: ExecConfig = field(default_factory=ExecConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    allocator: AllocatorConfig = field(default_factory=AllocatorConfig)

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
    alloc_raw = raw.pop("allocator", {})
    for k in ("allowed_tokens", "exclude_tokens"):
        if k in alloc_raw:
            alloc_raw[k] = tuple(alloc_raw[k])
    allocator = _pick(AllocatorConfig, alloc_raw)
    top_names = {f.name for f in fields(Config)} - {"strategy", "execution", "safety", "allocator"}
    unknown = set(raw) - top_names
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")
    return Config(strategy=strategy, execution=execution, safety=safety, allocator=allocator, **raw)
