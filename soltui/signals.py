"""Editable signal parameters: the tunables behind the Signals tab.

## The model, because it needs to be unambiguous

A *signal* is an indicator with a period or threshold (RSI's period, Bollinger's
width, MACD's spans). A *strategy* is a rule built on one or more signals. The
same signal is shared by several strategies -- `rsi` and any composite containing
it both read the RSI period.

So editing a signal here sets a **default**, and it flows one way:

    signal defaults  ->  strategy constructor kwargs  ->  explicit per-entry params win

`params_for("rsi")` returns `{"period": 14, ...}` from the defaults. If a roster
entry was added as `rsi period=7`, that explicit value wins. Defaults fill only
what the user did not pin, which is what makes the Signals tab useful without
silently overwriting a deliberate choice in the Strategies tab.

Every default is validated against the same rule the strategy constructor
enforces, so a bad value fails in the Signals form rather than at sweep time.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


class SignalError(ValueError):
    """Raised when a signal parameter would be invalid."""


@dataclass
class SignalDefaults:
    """Tunable parameters per signal, with the values the backtester ships."""

    # Moving averages / trend
    sma_fast: int = 20
    sma_slow: int = 50
    regime_window: int = 100
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # Oscillators
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_exit: float = 50.0
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_oversold: float = 20.0
    stoch_exit: float = 80.0
    # Bands / channels
    bollinger_window: int = 20
    bollinger_std: float = 2.0
    keltner_ema: int = 20
    keltner_atr: int = 14
    keltner_mult: float = 2.0
    donchian_entry: int = 20
    donchian_exit: int = 10
    # Flow / statistical
    obv_ma: int = 20
    vwap_window: int = 20
    vwap_discount: float = 0.02
    zscore_window: int = 20
    zscore_entry: float = -2.0
    roc_window: int = 60
    # Risk overlay
    vol_window: int = 20
    vol_target: float = 0.60
    trend_window: int = 100
    # Grid
    grid_anchor: int = 50
    grid_levels: int = 4
    grid_step: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        """Serialisable form."""
        return asdict(self)


# Which defaults map to which strategy constructor kwargs. Explicit rather than
# inferred from names: the mapping is the contract between this tab and the
# strategy registry, and guessing it would break silently when either side is
# renamed.
STRATEGY_PARAM_MAP: dict[str, dict[str, str]] = {
    "ma_crossover": {"fast": "sma_fast", "slow": "sma_slow"},
    "macd": {"fast": "macd_fast", "slow": "macd_slow", "signal": "macd_signal"},
    "rsi": {"period": "rsi_period", "oversold": "rsi_oversold", "exit_level": "rsi_exit"},
    "stochastic": {
        "k_period": "stoch_k", "d_period": "stoch_d",
        "oversold": "stoch_oversold", "exit_level": "stoch_exit",
    },
    "bb_reversion": {"window": "bollinger_window", "num_std": "bollinger_std"},
    "bb_breakout": {"window": "bollinger_window", "num_std": "bollinger_std"},
    "keltner": {
        "ema_span": "keltner_ema", "atr_period": "keltner_atr", "mult": "keltner_mult",
    },
    "breakout": {"entry_lookback": "donchian_entry", "exit_lookback": "donchian_exit"},
    "obv_trend": {"ma_window": "obv_ma"},
    "vwap_reversion": {"window": "vwap_window", "entry_discount": "vwap_discount"},
    "zscore": {"window": "zscore_window", "entry_z": "zscore_entry"},
    "ts_momentum": {"window": "roc_window"},
    "sma_regime": {"window": "regime_window"},
    "voltarget": {
        "trend_window": "trend_window", "vol_window": "vol_window",
        "target_vol": "vol_target",
    },
    "grid": {
        "anchor_window": "grid_anchor", "levels": "grid_levels", "step": "grid_step",
    },
    "buy_and_hold": {},
}

# Human-facing grouping and units for the Signals tab, so the form reads as a
# signal editor rather than a flat dump of forty fields.
SIGNAL_GROUPS: list[tuple[str, list[str]]] = [
    ("Moving averages", ["sma_fast", "sma_slow", "regime_window", "trend_window"]),
    ("MACD", ["macd_fast", "macd_slow", "macd_signal"]),
    ("RSI", ["rsi_period", "rsi_oversold", "rsi_exit"]),
    ("Stochastic", ["stoch_k", "stoch_d", "stoch_oversold", "stoch_exit"]),
    ("Bollinger", ["bollinger_window", "bollinger_std"]),
    ("Keltner / ATR", ["keltner_ema", "keltner_atr", "keltner_mult"]),
    ("Donchian", ["donchian_entry", "donchian_exit"]),
    ("Volume / VWAP", ["obv_ma", "vwap_window", "vwap_discount"]),
    ("Z-score / ROC", ["zscore_window", "zscore_entry", "roc_window"]),
    ("Volatility target", ["vol_window", "vol_target"]),
    ("Grid", ["grid_anchor", "grid_levels", "grid_step"]),
]


def validate(defaults: SignalDefaults) -> SignalDefaults:
    """Return `defaults` if every value is usable, else raise SignalError.

    Checks the same relationships the strategy constructors enforce, so the
    Signals form is the place a bad value is caught.
    """
    d = defaults
    positive_ints = [
        "sma_fast", "sma_slow", "regime_window", "macd_fast", "macd_slow",
        "macd_signal", "rsi_period", "stoch_k", "stoch_d", "bollinger_window",
        "keltner_ema", "keltner_atr", "donchian_entry", "donchian_exit", "obv_ma",
        "vwap_window", "zscore_window", "roc_window", "vol_window", "trend_window",
        "grid_anchor", "grid_levels",
    ]
    for name in positive_ints:
        if int(getattr(d, name)) < 1:
            raise SignalError(f"{name} must be at least 1")

    if d.sma_fast >= d.sma_slow:
        raise SignalError("sma_fast must be shorter than sma_slow")
    if d.macd_fast >= d.macd_slow:
        raise SignalError("macd_fast must be shorter than macd_slow")
    if d.rsi_period < 2:
        raise SignalError("rsi_period must be at least 2")
    if not 0 < d.rsi_oversold < d.rsi_exit <= 100:
        raise SignalError("require 0 < rsi_oversold < rsi_exit <= 100")
    if not 0 < d.stoch_oversold < d.stoch_exit <= 100:
        raise SignalError("require 0 < stoch_oversold < stoch_exit <= 100")
    if d.bollinger_std <= 0:
        raise SignalError("bollinger_std must be positive")
    if d.keltner_mult <= 0:
        raise SignalError("keltner_mult must be positive")
    if d.zscore_entry >= 0:
        raise SignalError(
            "zscore_entry must be negative — it is the oversold threshold a long "
            "reversion enters at"
        )
    if not 0 < d.vwap_discount < 1:
        raise SignalError("vwap_discount must be a fraction between 0 and 1")
    if d.vol_target <= 0:
        raise SignalError("vol_target must be positive")
    if not 0 < d.grid_step < 1:
        raise SignalError("grid_step must be a fraction between 0 and 1")
    return d


def params_for(strategy: str, defaults: SignalDefaults) -> dict[str, Any]:
    """Constructor kwargs for `strategy`, taken from the signal defaults.

    Returns {} for a strategy with no tunables (buy_and_hold) or one not in the
    map, so an unmapped strategy still constructs with its own defaults rather
    than failing.
    """
    mapping = STRATEGY_PARAM_MAP.get(strategy)
    if not mapping:
        return {}
    return {kwarg: getattr(defaults, field) for kwarg, field in mapping.items()}


def merged_params(
    strategy: str, defaults: SignalDefaults, explicit: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Signal defaults with any explicit per-entry params layered on top.

    Explicit wins. That direction matters: the Signals tab must not silently
    overwrite a value the user deliberately pinned in the Strategies tab.
    """
    params = params_for(strategy, defaults)
    params.update(explicit or {})
    return params


def field_names() -> list[str]:
    """Every tunable field name, in declaration order."""
    return [f.name for f in fields(SignalDefaults)]


def coerce(name: str, raw: str, defaults: SignalDefaults) -> Any:
    """Parse a form string into the declared type of field `name`.

    Uses the dataclass's own annotation rather than guessing from the text, so
    '20' stays an int for a window and becomes a float for a threshold.
    """
    current = getattr(defaults, name)
    text = raw.strip()
    if not text:
        return current
    try:
        return int(text) if isinstance(current, int) else float(text)
    except ValueError as exc:
        raise SignalError(f"{name}: {raw!r} is not a number") from exc


def from_dict(raw: dict[str, Any]) -> SignalDefaults:
    """Rebuild from `to_dict()`, ignoring unknown keys and validating the result."""
    known = set(field_names())
    return validate(SignalDefaults(**{k: v for k, v in (raw or {}).items() if k in known}))


def mapped_strategies() -> list[str]:
    """Strategies whose parameters this tab can drive."""
    return sorted(k for k, v in STRATEGY_PARAM_MAP.items() if v)
