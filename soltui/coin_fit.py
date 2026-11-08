"""Single/bulk coin suitability, quick ranking and a fixed-configuration audit.

All market data comes from explicit local caches. No order path, automatic
configuration adoption, recorder startup, or background fetching exists here.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from backtester.core.coinfit import simulate
from backtester.core.data import CsvLoader
from backtester.core.dcasim import DcaConfig, capital_required_usd, safety_sizes_usd
from backtester.core.types import CostConfig, validate_bar_arrays

from . import bots

VERSION = "1.0.0"
TEMPLATE_FIELDS = (
    "venue_pair",
    "as_of",
    "intended_order_notional",
    "round_trip_cost",
    "spacing_cost_ratio",
    "completed_net_cycles",
    "efficiency_ratio",
    "future_band_occupancy",
    "downside_escape_duration",
    "full_required_reserve",
    "exit_hit_by_horizon",
    "recovery_duration",
    "adverse_excursion",
    "investment_thesis",
    "cash_flow_schedule",
    "total_equity_return",
    "max_equity_drawdown",
    "time_underwater",
    "oos_rank_stability",
    "joint_reserve_shortfall",
    "cash_flow_return_convention",
    "benchmark_cash_flow_match",
)
MAX_DAYS = 730
MIN_WINDOW_BARS = 24
POLICY = {
    "version": 1,
    "max_drawdown": 0.25,
    "min_cycles": 3,
    "min_spacing_cost_ratio": 3.0,
    "min_positive_window_fraction": 0.60,
    "min_exit_hit_rate": 0.70,
    "score_drawdown_penalty": 0.5,
}


def _iso(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")


def _finite(value: Any, name: str, minimum: float = 0) -> float:
    if isinstance(value, bool):
        raise bots.BotError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise bots.BotError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or result < minimum:
        raise bots.BotError(f"{name} must be finite and at least {minimum}")
    return result


def _stamp(value: Any) -> int:
    if isinstance(value, bool):
        raise bots.BotError("timestamp must not be boolean")
    try:
        numeric = float(value)
    except (ValueError, TypeError):
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise bots.BotError("start must be a UTC date or epoch seconds") from exc
        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
        numeric = dt.timestamp()
    if not math.isfinite(numeric) or numeric < 0 or numeric % 3600:
        raise bots.BotError(
            "window timestamps must be positive whole-hour UTC boundaries"
        )
    return int(numeric)


def _coins(coins: Any, settings: Any) -> list[str]:
    if isinstance(coins, str):
        coins = coins.replace(",", " ").upper().split()
    if coins is None:
        coins = [str(getattr(settings, "asset", "SOL")).upper()]
    if not isinstance(coins, (list, tuple)) or not all(
        isinstance(c, str) for c in coins
    ):
        raise bots.BotError("coins must be a list of symbols or ALL")
    names = [c.upper().removesuffix("-USD") for c in coins]
    if names == ["ALL"]:
        names = bots.available_coins(settings)
    if len(names) > 1000:
        raise bots.BotError("screen at most1000explicit coins per job")
    if len(set(names)) != len(names):
        raise bots.BotError("duplicate coins are not allowed in a ranking")
    return names


def _cache_dir(settings: Any) -> Path:
    """An explicit missing cache must not silently substitute another dataset."""
    raw = getattr(settings, "data_dir", None)
    if raw:
        path = Path(raw).expanduser().resolve()
        if not path.is_dir():
            raise bots.BotError(
                f"Explicit data_dir is unavailable: {path}; no fallback dataset is used"
            )
        return path
    path = bots.data_dir(None).resolve()
    if not path.is_dir():
        raise bots.BotError(f"No default candle cache available: {path}")
    return path


def load_coin(coin: str, settings: Any) -> dict[str, Any]:
    """Strict native1h input, or complete sixty-minute buckets; never bridge gaps."""
    if not re.fullmatch(r"[A-Z0-9]{1,24}", coin):
        raise bots.BotError("coin identifiers must be uppercase asset symbols")
    base = _cache_dir(settings)
    native, minutes = base / f"{coin}_1h.csv", base / f"{coin}_1m.csv"
    path = native if native.is_file() else minutes
    interval = "1h" if path == native else "1m"
    frame = CsvLoader(path, allow_gaps=True).load(coin, None, None, interval)
    if interval == "1m":
        if (frame["timestamp"] % 60 != 0).any():
            raise bots.BotError(
                f"{coin}: minute candles must align to whole UTC minutes; row counts cannot prove coverage"
            )
        frame["hour"] = (frame["timestamp"] // 3600) * 3600
        frame = (
            frame.groupby("hour")
            .agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "last"),
                volume=("volume", "sum"),
                count=("open", "size"),
            )
            .reset_index()
            .rename(columns={"hour": "timestamp"})
        )
        frame = frame[frame["count"] == 60]
    if frame.empty:
        raise bots.BotError(f"{coin}: no complete cached hourly bars")
    arrays = {
        "ts": frame["timestamp"].to_numpy(dtype="int64"),
        **{
            k: frame[k].to_numpy(dtype="float64")
            for k in ("open", "high", "low", "close", "volume")
        },
    }
    return {**arrays, "source": str(path), "resampled": interval == "1m"}


def _slice(data: dict[str, Any], start: int, end: int) -> dict[str, np.ndarray]:
    indices = (data["ts"] >= start) & (data["ts"] < end)
    result = {
        k: np.asarray(data[k])[indices].copy()
        for k in ("ts", "open", "high", "low", "close", "volume")
    }
    expected = (end - start) // 3600
    if len(result["ts"]) != expected or expected < MIN_WINDOW_BARS:
        raise bots.BotError(
            f"incomplete common window {_iso(start)} to {_iso(end)}: "
            f"{len(result['ts'])}/{expected} hourly bars; no gap filling"
        )
    if int(result["ts"][0]) != start or int(result["ts"][-1]) + 3600 != end:
        raise bots.BotError("cache does not cover the exact common window")
    validate_bar_arrays(result, "1h")
    return result


def _hash(data: dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for key in ("ts", "open", "high", "low", "close", "volume"):
        h.update(key.encode())
        h.update(np.asarray(data[key], dtype="<f8").tobytes())
    return h.hexdigest()


def _features(
    data: dict[str, np.ndarray], bot: str, cfg: dict[str, Any]
) -> dict[str, Any]:
    prices = data["close"]
    changes = np.diff(np.log(prices))
    traveled = float(np.sum(np.abs(changes)))
    ratio = abs(float(np.sum(changes))) / traveled if traveled else None
    out = {"efficiency_ratio": ratio, "price_return": float(prices[-1] / prices[0] - 1)}
    if bot == "grid":
        lower, upper = (
            prices[0] * (1 - cfg["range_pct"] / 100),
            prices[0] * (1 + cfg["range_pct"] / 100),
        )
        longest = current = 0
        for price in prices[1:]:
            current = current + 1 if price < lower else 0
            longest = max(longest, current)
        out.update(
            {
                "band_lower": float(lower),
                "band_upper": float(upper),
                "band_occupancy": float(
                    np.mean((prices[1:] >= lower) & (prices[1:] <= upper))
                ),
                "downside_escape_days": longest / 24,
                "ongoing_downside_escape": bool(current),
            }
        )
    return out


def _field(
    name: str,
    value: Any = None,
    state: str = "unknown",
    reason: str = "Not established by historical candles",
    basis: str = "unavailable",
) -> dict[str, Any]:
    return {
        "metric": name,
        "value": value,
        "state": state,
        "reason": reason,
        "basis": basis,
    }


def _template(
    bot: str,
    cfg: dict[str, Any],
    metrics: dict[str, Any],
    features: dict[str, Any],
    costs: CostConfig,
    capital: float,
    windows: list[dict[str, Any]],
    mode: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    fields = {name: _field(name) for name in TEMPLATE_FIELDS}

    def put(
        name: str,
        value: Any,
        reason: str,
        basis: str = "simulated",
        state: str = "measured",
    ) -> None:
        fields[name] = _field(name, value, state, reason, basis)

    put(
        "venue_pair",
        "USD candle cache; provider unverified",
        "File provenance alone does not establish current venue availability or historical listing lifecycle",
        "cache",
        "unknown",
    )
    primary = next(
        (w for w in windows if w["role"] == "continuous" and not w["stress"]),
        windows[0],
    )
    put(
        "as_of",
        primary["end"],
        "End of the reported metrics window; the reserved holdout/common period are recorded separately",
        "cache",
    )
    put(
        "round_trip_cost",
        2 * (costs.fee_bps + costs.slippage_bps),
        "Per-fill bps on both sides; historical spread/depth not observed",
        "configured assumption",
    )
    put(
        "efficiency_ratio",
        features["efficiency_ratio"],
        "Net close-price drift / traveled log-price path; not standalone predictive evidence",
        "descriptive",
    )
    put(
        "total_equity_return",
        metrics["total_return"],
        "Whole funded account, idle reserve included, terminal inventory liquidated with costs",
    )
    put(
        "max_equity_drawdown",
        metrics["max_drawdown"],
        "Full marked-equity curve before display downsampling; negative fraction",
    )
    put(
        "time_underwater",
        metrics["time_underwater_days"],
        "Days below prior account peak; ongoing episodes retained",
    )
    put(
        "cash_flow_return_convention",
        "simple return; prefunded",
        "No external contributions; purchases move assets within the funded account",
    )
    put(
        "benchmark_cash_flow_match",
        metrics["hold_return"],
        "Same capital, next-open entry and terminal fee/slippage; cash baseline0%",
    )
    put(
        "joint_reserve_shortfall",
        None,
        "Independent per-coin accounts; no shared-budget portfolio stress performed",
        "not a portfolio allocation",
        "not_applicable",
    )
    base = [
        w
        for w in windows
        if w["role"] in ("development_fold", "reserved_holdout") and not w["stress"]
    ]
    put(
        "oos_rank_stability",
        {
            "positive_windows": sum(w["metrics"]["total_return"] > 0 for w in base),
            "windows": len(base),
        },
        "Fixed-config window robustness; not proof of complete point-in-time ranking-rule generalization",
        "diagnostic" if mode == "audit" else "not tested",
        "measured" if mode == "audit" else "unknown",
    )
    if bot == "grid":
        put(
            "intended_order_notional",
            capital / cfg["rungs"],
            "Funded notional per rung; historical visible depth unknown",
            "configured",
        )
        rt = 2 * (costs.fee_bps + costs.slippage_bps)
        put(
            "spacing_cost_ratio",
            metrics["spacing_bps"] / rt,
            "Proposed3x cushion; not an empirically optimal cutoff",
            "heuristic",
        )
        put(
            "completed_net_cycles",
            metrics["cycles"],
            "Paired simulator round trips; forced terminal exits are not counted as cycles",
        )
        put(
            "future_band_occupancy",
            features["band_occupancy"],
            "Post-initialization closes inside the range fixed from the initial close",
            "descriptive",
        )
        put(
            "downside_escape_duration",
            features["downside_escape_days"],
            "Close-based escape duration includes ongoing final episode",
            "descriptive",
        )
        for key in (
            "full_required_reserve",
            "exit_hit_by_horizon",
            "recovery_duration",
            "adverse_excursion",
            "investment_thesis",
            "cash_flow_schedule",
        ):
            put(
                key,
                None,
                "Not a basket or accumulation strategy",
                "not_applicable",
                "not_applicable",
            )
    elif bot == "dca":
        dcfg = DcaConfig(**cfg)
        put(
            "intended_order_notional",
            max([dcfg.base_order_usd, *safety_sizes_usd(dcfg)]),
            "Largest planned order; historical execution depth unknown",
            "configured",
        )
        put(
            "full_required_reserve",
            capital_required_usd(dcfg) * (1 + costs.fee_bps / 10000),
            "All base/safety orders plus buy fees, not just the base order",
            "derived",
        )
        put(
            "exit_hit_by_horizon",
            metrics["exit_hit_rate"],
            "Completed / (completed + stopped + unfinished); unfinished deals are not discarded",
        )
        put(
            "recovery_duration",
            metrics["recovery_p95_days"],
            "95th percentile among completed deals only; not a censored population estimate",
        )
        put(
            "adverse_excursion",
            metrics["max_drawdown"],
            "Full-account path loss, not the base order alone",
        )
        for key in (
            "spacing_cost_ratio",
            "completed_net_cycles",
            "future_band_occupancy",
            "downside_escape_duration",
            "investment_thesis",
            "cash_flow_schedule",
        ):
            put(
                key,
                None,
                "Not applicable to this safety-order basket",
                "not_applicable",
                "not_applicable",
            )
    else:
        put(
            "intended_order_notional",
            metrics["contribution_budget"],
            "Equal funded purchase budget; fee included",
            "configured",
        )
        put(
            "cash_flow_schedule",
            {
                "count": metrics["contributions"],
                "hours": cfg["interval_hours"],
                "funding": "prefunded",
            },
            "Equal cash portions scheduled before execution; future income is not assumed",
        )
        thesis = context.get("investment_thesis")
        if (
            isinstance(thesis, dict)
            and type(thesis.get("approved")) is bool
            and thesis.get("reason")
            and thesis.get("source")
        ):
            put(
                "investment_thesis",
                thesis,
                "Supplied ownership thesis, not inferred from candles",
                "provided",
                "pass" if thesis["approved"] else "fail",
            )
        for key in (
            "spacing_cost_ratio",
            "completed_net_cycles",
            "future_band_occupancy",
            "downside_escape_duration",
            "full_required_reserve",
            "exit_hit_by_horizon",
            "recovery_duration",
            "adverse_excursion",
        ):
            put(
                key,
                None,
                "Not applicable to fixed-schedule accumulation",
                "not_applicable",
                "not_applicable",
            )
    return list(fields.values())


def _row(
    coin: str,
    bot: str,
    cfg: dict[str, Any],
    data: dict[str, Any],
    start: int,
    end: int,
    costs: CostConfig,
    capital: float,
    mode: str,
    cancel: Callable[[], bool],
    progress: Callable[[float, str], None],
    context: dict[str, Any],
    policy: dict[str, Any],
    expected_data_sha256: str | None = None,
) -> dict[str, Any]:
    # Bind the complete observed input for later audit, but do not make quick
    # eligibility depend on the held-out prices or their future completeness.
    indices = (data["ts"] >= start) & (data["ts"] < end)
    full = {
        k: np.asarray(data[k])[indices].copy()
        for k in ("ts", "open", "high", "low", "close", "volume")
    }
    if mode == "audit":
        full = _slice(data, start, end)
    data_hash = _hash(full)
    if expected_data_sha256 and data_hash != expected_data_sha256:
        raise bots.BotError(
            "cached history changed since quick ranking; rank again before auditing"
        )
    total_hours = (end - start) // 3600
    hold_hours = min(720, max(24, total_hours // 4))
    split = end - hold_hours * 3600
    quick_start = max(start, split - 2160 * 3600)
    windows = []
    if mode == "quick":
        specs = [("quick development", quick_start, split, "quick", False)]
    else:
        span = (split - start) // 3600
        if span < 3 * MIN_WINDOW_BARS:
            raise bots.BotError(
                "audit needs at least3complete development windows plus the holdout"
            )
        edges = [start + (span * i // 3) * 3600 for i in range(4)]
        baseline_specs = [
            (
                f"development fold{i + 1}",
                edges[i],
                edges[i + 1],
                "development_fold",
                False,
            )
            for i in range(3)
        ]
        baseline_specs += [
            ("reserved newest holdout", split, end, "reserved_holdout", False),
            ("continuous full account", start, end, "continuous", False),
        ]
        specs = baseline_specs + [
            (f"{name} (2x costs)", a, b, role, True)
            for name, a, b, role, _ in baseline_specs
        ]
    for index, (label, a, b, role, stress) in enumerate(specs):
        if cancel():
            return {
                "coin": coin,
                "fit": "CANCELLED",
                "status": "cancelled",
                "reason": "Cancelled between bounded simulation windows",
                "windows": windows,
            }
        progress(index / len(specs), f"{coin}: {label}")
        multiplier = 2 if stress else 1
        scenario_costs = CostConfig(
            fee_bps=costs.fee_bps * multiplier,
            slippage_bps=costs.slippage_bps * multiplier,
        )
        run = simulate(
            bot,
            cfg,
            _slice(data, a, b),
            capital=capital,
            costs=scenario_costs,
            include_fills=mode == "audit",
        )
        windows.append(
            {
                "label": label,
                "start": a,
                "end": b,
                "role": role,
                "stress": stress,
                "fee_bps": scenario_costs.fee_bps,
                "slippage_bps": scenario_costs.slippage_bps,
                **run,
            }
        )
    primary = (
        windows[0]
        if mode == "quick"
        else next(w for w in windows if w["role"] == "continuous" and not w["stress"])
    )
    measured = _slice(data, primary["start"], primary["end"])
    metrics = primary["metrics"]
    features = _features(measured, bot, cfg)
    reasons, failures = [], []

    def gate(ok: bool, text: str) -> None:
        (reasons if ok else failures).append(text)

    gate(
        metrics["total_return"] > 0,
        f"Full-account net return {metrics['total_return']:+.2%} after costs and terminal liquidation",
    )
    gate(
        abs(metrics["max_drawdown"]) <= policy["max_drawdown"],
        f"Full-account drawdown {metrics['max_drawdown']:.2%}; proposed limit{policy['max_drawdown']:.0%}",
    )
    if bot != "scheduled_dca":
        gate(
            metrics["cycles"] >= policy["min_cycles"],
            f"Completed cycles/deals {metrics['cycles']}; proposed minimum{policy['min_cycles']:g}",
        )
    if bot == "grid":
        ratio = metrics["spacing_bps"] / (2 * (costs.fee_bps + costs.slippage_bps))
        gate(
            ratio >= policy["min_spacing_cost_ratio"],
            f"Spacing/cost ratio {ratio:.2f}; proposed minimum{policy['min_spacing_cost_ratio']:g}",
        )
    elif bot == "dca":
        required = capital_required_usd(DcaConfig(**cfg)) * (
            1 + 2 * costs.fee_bps / 10000
        )
        base_required = capital_required_usd(DcaConfig(**cfg)) * (
            1 + costs.fee_bps / 10000
        )
        gate(
            capital >= (required if mode == "audit" else base_required),
            f"Funded cash {capital:.2f}; full-ladder reserve at stress fees {required:.2f}",
        )
        rate = metrics["exit_hit_rate"]
        gate(
            rate is not None and rate >= policy["min_exit_hit_rate"],
            f"Exit hit rate {rate!r}, including unfinished deals; proposed minimum{policy['min_exit_hit_rate']:.2f}",
        )
    robust = [
        w
        for w in windows
        if w["role"] in ("development_fold", "reserved_holdout") and not w["stress"]
    ]
    if mode == "audit":
        fraction = sum(w["metrics"]["total_return"] > 0 for w in robust) / len(robust)
        gate(
            fraction >= policy["min_positive_window_fraction"],
            f"Positive fixed-config windows {fraction:.0%}; proposed minimum{policy['min_positive_window_fraction']:.0%}",
        )
        hold = next(
            w for w in windows if w["role"] == "reserved_holdout" and not w["stress"]
        )
        stress_hold = next(
            w for w in windows if w["role"] == "reserved_holdout" and w["stress"]
        )
        gate(
            hold["metrics"]["total_return"] > 0,
            f"Newest reserved holdout net return {hold['metrics']['total_return']:+.2%}",
        )
        gate(
            stress_hold["metrics"]["total_return"] > 0,
            f"Newest holdout at 2x fees/slippage {stress_hold['metrics']['total_return']:+.2%}",
        )
        worst = min(w["metrics"]["max_drawdown"] for w in windows)
        gate(
            abs(worst) <= policy["max_drawdown"],
            f"Worst scenario drawdown {worst:.2%}; proposed limit{policy['max_drawdown']:.0%}",
        )
    else:
        worst = metrics["max_drawdown"]
    base_returns = (
        [w["metrics"]["total_return"] for w in robust]
        if robust
        else [metrics["total_return"]]
    )
    median = float(np.median(base_returns))
    score = 100 * (median - policy["score_drawdown_penalty"] * abs(worst))
    fit = (
        "POOR_FIT"
        if failures
        else ("PROVISIONAL_FIT" if mode == "quick" else "GOOD_FIT")
    )
    missing = [
        "Current executable order-book depth and actual venue eligibility",
        "Point-in-time universe/listing/delisting continuity",
        "Joint portfolio reserve stress",
        "Historical depth/fill evidence beyond the candle execution model",
    ]
    if bot == "scheduled_dca":
        thesis = context.get("investment_thesis")
        if (
            not isinstance(thesis, dict)
            or type(thesis.get("approved")) is not bool
            or not thesis.get("reason")
            or not thesis.get("source")
        ):
            missing.append(
                "Evidenced long-term ownership thesis; price appreciation is insufficient"
            )
            if not failures:
                fit = "INSUFFICIENT_DATA"
        elif thesis["approved"] is False:
            failures.append("Supplied ownership thesis fails")
            fit = "POOR_FIT"
    template = _template(
        bot, cfg, metrics, features, costs, capital, windows, mode, context
    )
    return {
        "coin": coin,
        "fit": fit,
        "status": "complete",
        "score": score,
        "fit_scope": "historical simulation under the stated heuristic policy; not live due-diligence approval",
        "reason": "; ".join(failures or reasons),
        "reasons": reasons,
        "failures": failures,
        "missing_evidence": missing,
        "metrics": metrics,
        "features": features,
        "windows": windows,
        "equity": primary["equity"],
        "template": template,
        "data_sha256": data_hash,
        "data_source": data["source"],
        "quick_start": quick_start,
        "quick_end": split,
        "holdout_start": split,
        "holdout_end": end,
        "median_window_return": median,
        "worst_scenario_drawdown": worst,
    }


def rank_coins(
    bot: str,
    coins: Any,
    settings: Any = None,
    *,
    mode: str = "quick",
    start: Any = None,
    days: Any = None,
    progress: Callable[[float, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    reference_end: Any = None,
    config: dict[str, Any] | None = None,
    fee_bps: float | None = None,
    slippage_bps: float | None = None,
    selection_id: str | None = None,
    expected_data_sha256: str | None = None,
    context: dict[str, dict[str, Any]] | None = None,
    capital: float | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank a common cached window; quick never scores its newest holdout prices.

    The audit uses fixed parameters and reset-window diagnostics plus a continuous
    account. It does not call that a calibrated predictive ranking strategy.
    """
    if policy is not None and (
        not isinstance(policy, dict) or set(policy) - set(POLICY)
    ):
        raise bots.BotError("policy contains unknown or immutable keys")
    if (
        policy is not None
        and "version" in policy
        and (
            type(policy["version"]) is not int or policy["version"] != POLICY["version"]
        )
    ):
        raise bots.BotError("policy version must match the implemented policy")
    policy = {**POLICY, **(policy or {})}
    for key, value in policy.items():
        if key != "version":
            policy[key] = _finite(value, key)
            if policy[key] > 1000000:
                raise bots.BotError("policy values must be <=1000000")
    for key in ("max_drawdown", "min_exit_hit_rate", "min_positive_window_fraction"):
        if policy[key] > 1:
            raise bots.BotError(f"policy.{key} must be a fraction0..1")
    if policy["min_cycles"] != int(policy["min_cycles"]):
        raise bots.BotError("policy.min_cycles must be an integer")
    if bot not in ("grid", "dca", "scheduled_dca") or mode not in ("quick", "audit"):
        raise bots.BotError(
            "coin fit supports grid, dca or scheduled_dca; mode quick or audit"
        )
    if bot == "scheduled_dca":
        cfg = copy.deepcopy(config or {"interval_hours": 168})
        if (
            set(cfg) != {"interval_hours"}
            or type(cfg["interval_hours"]) is not int
            or cfg["interval_hours"] < 1
        ):
            raise bots.BotError(
                "scheduled DCA needs only a positive integer interval_hours"
            )
    else:
        cfg = (
            bots.validate(bot, copy.deepcopy(config))
            if config is not None
            else copy.deepcopy(bots.get_config(bot))
        )
    if bot == "grid" and cfg["rungs"] > 100:
        raise bots.BotError(
            "interactive coin screening is bounded to100rungs; use the manual engine for larger ladders"
        )
    fee = _finite(
        getattr(settings, "fee_bps", 6.0) if fee_bps is None else fee_bps, "fee_bps"
    )
    slip = _finite(
        getattr(settings, "slippage_bps", 2.0)
        if slippage_bps is None
        else slippage_bps,
        "slippage_bps",
    )
    if fee + slip <= 0 or max(fee, slip) >= 5000:
        raise bots.BotError(
            "screening requires explicit positive total costs, each below5000bps for2xstress"
        )
    costs = CostConfig(fee_bps=fee, slippage_bps=slip)
    amount = (
        _finite(capital, "capital", 1e-9)
        if capital is not None
        else (
            float(cfg["capital_usd"])
            if bot == "grid"
            else capital_required_usd(DcaConfig(**cfg)) * (1 + 2 * fee / 10000)
            if bot == "dca"
            else _finite(getattr(settings, "capital", 10000), "capital", 1e-9)
        )
    )
    if bot == "grid":
        cfg["capital_usd"] = amount
    callback, cancel = progress or (lambda *_: None), cancelled or (lambda: False)
    captured = SimpleNamespace(
        data_dir=str(_cache_dir(settings)), asset=getattr(settings, "asset", "SOL")
    )
    names = _coins(coins, captured)
    if not names:
        raise bots.BotError(
            "No cached coins; fetch hourly data from the Data tab or explicit fetch CLI first"
        )
    context = context or {}
    if not isinstance(context, dict) or not all(
        isinstance(k, str) and isinstance(v, dict) for k, v in context.items()
    ):
        raise bots.BotError(
            "context must be keyed by coin symbol with an object for each coin"
        )
    try:
        json.dumps(context, allow_nan=False, sort_keys=True)
    except (ValueError, TypeError) as exc:
        raise bots.BotError(
            "context must contain finite, JSON-serializable evidence"
        ) from exc
    loaded, rows, errors = {}, [], {}
    now = int(time.time() // 3600) * 3600
    for i, coin in enumerate(names):
        if cancel():
            break
        callback(0.10 * i / len(names), f"Loading {coin} ({i + 1}/{len(names)})")
        try:
            loaded[coin] = load_coin(coin, captured)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            errors[coin] = str(exc)
    end = (
        _stamp(reference_end)
        if reference_end is not None
        else min(
            now, max((int(d["ts"][-1]) + 3600 for d in loaded.values()), default=now)
        )
    )
    if end > now:
        raise bots.BotError("reference_end must not include future or forming hours")
    duration = _finite(days if days not in (None, "") else 180, "days", 7)
    if duration > MAX_DAYS or duration * 24 != int(duration * 24):
        raise bots.BotError(f"days must describe whole hours, between7and{MAX_DAYS}")
    beginning = (
        _stamp(start) if start not in (None, "") else end - int(duration * 86400)
    )
    if start not in (None, "") and days not in (None, ""):
        requested_end = beginning + int(duration * 86400)
        if requested_end > end:
            raise bots.BotError(
                "requested start/days exceeds available complete history"
            )
        end = requested_end
    if not 7 * 86400 <= end - beginning <= MAX_DAYS * 86400:
        raise bots.BotError("analysis window must be between7and730days")
    for i, coin in enumerate(names):
        if cancel():
            break
        if coin not in loaded:
            continue
        try:
            row = _row(
                coin,
                bot,
                cfg,
                loaded[coin],
                beginning,
                end,
                costs,
                amount,
                mode,
                cancel,
                lambda f, msg, i=i: callback(0.10 + 0.90 * (i + f) / len(names), msg),
                context.get(coin, {}),
                policy,
                expected_data_sha256,
            )
            rows.append(row)
        except (ValueError, OSError, KeyError, TypeError, FloatingPointError) as exc:
            errors[coin] = str(exc)
    present = {r["coin"] for r in rows}
    for coin in names:
        if coin not in present:
            previously_failed = coin in errors
            error = errors.get(
                coin,
                "Cancelled before this coin was tested"
                if cancel()
                else "Coin did not complete",
            )
            errors[coin] = error
            rows.append(
                {
                    "coin": coin,
                    "fit": "CANCELLED"
                    if cancel() and not previously_failed
                    else "INSUFFICIENT_DATA",
                    "status": "error",
                    "score": None,
                    "reason": error,
                    "reasons": [],
                    "missing_evidence": [error],
                    "metrics": {},
                    "windows": [],
                    "equity": [],
                    "template": [],
                }
            )
    priority = {
        "GOOD_FIT": 0,
        "PROVISIONAL_FIT": 0,
        "POOR_FIT": 1,
        "INSUFFICIENT_DATA": 2,
        "CANCELLED": 3,
    }
    rows.sort(
        key=lambda r: (
            priority.get(r["fit"], 4),
            -(r.get("score") if r.get("score") is not None else -math.inf),
            r["coin"],
        )
    )
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    identity = hashlib.sha256(
        json.dumps(
            {
                "bot": bot,
                "config": cfg,
                "capital": amount,
                "start": beginning,
                "end": end,
                "fees": fee,
                "slippage": slip,
                "coins": sorted(names),
                "policy": policy,
                "mode": mode,
                "context": context,
                "data_hashes": {r["coin"]: r.get("data_sha256") for r in rows},
            },
            sort_keys=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    callback(1, "Cancelled" if cancel() else "Coin ranking complete")
    return {
        "schema": "coin-fit/v1",
        "version": VERSION,
        "bot": bot,
        "mode": mode,
        "at": time.time(),
        "config": cfg,
        "capital_usd": amount,
        "fee_bps": fee,
        "slippage_bps": slip,
        "common_start": beginning,
        "common_end": end,
        "rows": rows,
        "errors": errors,
        "cancelled": bool(cancel()),
        "selection_id": selection_id or identity,
        "context_sha256": identity,
        "policy": policy,
        "score_formula": f"100*(median base-window net return -{policy['score_drawdown_penalty']:g}*absolute worst scenario drawdown)",
        "notes": [
            "Research heuristic; thresholds and score weights are not empirically optimal.",
            "All rows use the same USD capital, bot settings and UTC window; errors stay visible.",
            "Quick uses at most90development days and reserves the newest quarter (at most30days).",
            "Audit reports3development folds, the reserved holdout, a continuous full account, and2xfee/slippage scenarios.",
            "Audit windows restart accounts; the continuous run separately retains path/inventory effects.",
            "The holdout is reserved by this quick screen only; earlier research may already have viewed it.",
            "Current cache membership is not a point-in-time historical universe; no live depth or fundamental validation is implied.",
            "Forced terminal exits include costs and disclose pre-exit inventory; scheduled DCA is prefunded with zero cash interest.",
            "Equity drawdown uses hourly closing marks; unknown intrabar equity paths and historical visible depth are not reconstructed.",
            "No bot configuration is adopted, no recorder or fetch starts, and no order is placed.",
        ],
    }


def _pct(value: Any) -> str:
    return "—" if value is None else f"{float(value):+.2%}"


def render_report(reports: list[dict[str, Any]], fmt: str = "markdown") -> str:
    """The CLI and skill share the exact backend results used by the Bots tab."""
    if fmt == "json":
        return (
            json.dumps(
                {"schema": "coin-fit-cli/v1", "runs": reports},
                indent=2,
                allow_nan=False,
            )
            + "\n"
        )
    headers = [
        "bot",
        "mode",
        "rank",
        "coin",
        "fit",
        "score",
        "net_return",
        "hold_return",
        "max_drawdown",
        "cycles",
        "costs_usd",
        "open_inventory_before_exit",
        "unfinished_deals",
        "analysis_start",
        "analysis_end",
        "metric_start",
        "metric_end",
        "capital_usd",
        "fee_bps",
        "slippage_bps",
        "data_sha256",
        "fit_scope",
        "reason",
    ]
    table = []
    for report in reports:
        for row in report["rows"]:
            m = row.get("metrics", {})
            primary = next(
                (
                    w
                    for w in row.get("windows", [])
                    if w["role"] == "continuous" and not w["stress"]
                ),
                next(iter(row.get("windows", [])), {}),
            )
            table.append(
                [
                    report["bot"],
                    report["mode"],
                    row["rank"],
                    row["coin"],
                    row["fit"],
                    row.get("score"),
                    m.get("total_return"),
                    m.get("hold_return"),
                    m.get("max_drawdown"),
                    m.get("cycles"),
                    m.get("costs_usd"),
                    m.get("open_inventory_before_exit"),
                    m.get("unfinished_deals"),
                    _iso(report["common_start"]),
                    _iso(report["common_end"]),
                    _iso(primary["start"]) if primary else None,
                    _iso(primary["end"]) if primary else None,
                    report["capital_usd"],
                    report["fee_bps"],
                    report["slippage_bps"],
                    row.get("data_sha256"),
                    row.get("fit_scope"),
                    row["reason"],
                ]
            )
    if fmt == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(table)
        return output.getvalue()
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "# Coin strategy fit",
        "",
        (
            "Historical simulation screen only. Quick fits are provisional; "
            "a positive audit does not establish future profitability or live execution suitability."
        ),
        "",
    ]
    for report in reports:
        lines += [
            f"## {report['bot']} — {report['mode']}",
            "",
            f"Common period: {_iso(report['common_start'])} to {_iso(report['common_end'])} (end exclusive).",
            (
                f"Capital per coin: ${report['capital_usd']:,.2f}; per-fill fees {report['fee_bps']:g} bps, "
                f"slippage {report['slippage_bps']:g} bps. Accounts are independent; no shared budget is implied."
            ),
            "",
            "| Rank | Coin | Fit | Score | Net return | Hold | Max DD | Cycles | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in report["rows"]:
            m = row.get("metrics", {})
            cells = [
                row["rank"],
                row["coin"],
                row["fit"],
                "—" if row.get("score") is None else f"{row['score']:.3f}",
                _pct(m.get("total_return")),
                _pct(m.get("hold_return")),
                _pct(m.get("max_drawdown")),
                m.get("cycles", "—"),
                row["reason"],
            ]
            lines.append("| " + " | ".join(escape(c) for c in cells) + " |")
        lines += [
            "",
            "Costs and terminal inventory (before the modeled forced exit):",
            "",
            "| Coin | Fees + slippage USD | Pre-exit coin quantity | Unfinished DCA deals |",
            "| --- | --- | --- | --- |",
        ]
        for row in report["rows"]:
            m = row.get("metrics", {})
            costs = "—" if m.get("costs_usd") is None else f"{m['costs_usd']:.6f}"
            cells = [
                row["coin"],
                costs,
                m.get("open_inventory_before_exit", "—"),
                m.get("unfinished_deals", "not applicable"),
            ]
            lines.append("| " + " | ".join(escape(c) for c in cells) + " |")
        if len(report["rows"]) == 1:
            row = report["rows"][0]
            lines += ["", "### Reasoning", ""] + [
                "- " + reason
                for reason in row.get("reasons", []) + row.get("failures", [])
            ]
            lines += [
                "",
                "### Backtest windows",
                "",
                "| Window | Costs stressed | Return | Max DD | Cycles |",
                "| --- | --- | --- | --- | --- |",
            ]
            for window in row.get("windows", []):
                m = window["metrics"]
                lines.append(
                    f"| {escape(window['label'])} | {window['stress']} | {_pct(m['total_return'])} | {_pct(m['max_drawdown'])} | {m['cycles']} |"
                )
            lines += [
                "",
                "### Template evidence",
                "",
                "| Field | State | Value | Reason |",
                "| --- | --- | --- | --- |",
            ]
            for field in row.get("template", []):
                lines.append(
                    "| "
                    + " | ".join(
                        escape(field[k]) for k in ("metric", "state", "value", "reason")
                    )
                    + " |"
                )
        lines += ["", "Missing due diligence:", ""]
        for reason in sorted(
            {v for row in report["rows"] for v in row.get("missing_evidence", [])}
        ):
            lines.append("- " + reason)
        lines += ["", "Score: " + report["score_formula"], ""] + [
            "- " + note for note in report["notes"]
        ]
    return "\n".join(lines) + "\n"


def demo_data(directory: Path, days: int = 180) -> None:
    """Deterministic synthetic data. Names deliberately cannot imply real coin history."""
    count = days * 24 + 1
    steps = np.arange(count)
    stamp = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
    paths = {
        "RANGE": 100 + 8 * np.sin(steps / 12),
        "RALLY": 100 * np.exp(steps * 0.00015),
        "FALL": 100 * np.exp(-steps * 0.00025),
    }
    for coin, closes in paths.items():
        opens = np.r_[closes[0], closes[:-1]]
        with (directory / f"{coin}_1h.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            writer.writerows(
                (
                    stamp + int(i) * 3600,
                    float(opens[i]),
                    float(max(opens[i], closes[i]) * 1.001),
                    float(min(opens[i], closes[i]) * 0.999),
                    float(closes[i]),
                    1000,
                )
                for i in steps
            )


def _json_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    def reject(token: str) -> None:
        raise bots.BotError(f"non-finite JSON constant{token}")

    value = json.loads(path.read_text(), parse_constant=reject)
    if not isinstance(value, dict):
        raise bots.BotError(f"{path} must contain a JSON object")
    return value


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Single/bulk coin-fit screen with quick and audit spot backtests; never places orders."
    )
    parser.add_argument("--coin", help="One asset or USD pair, e.g. SOL or SOL-USD")
    parser.add_argument(
        "--coins", nargs="+", help="Several assets, or ALL cached coins"
    )
    parser.add_argument(
        "--bot", choices=("grid", "dca", "scheduled_dca", "all"), default="grid"
    )
    parser.add_argument("--mode", choices=("quick", "audit"), default="quick")
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Local hourly/minute CSV cache; no automatic network fetch",
    )
    parser.add_argument("--start", help="UTC date or whole-hour epoch seconds")
    parser.add_argument(
        "--days",
        type=float,
        default=180,
        help="Common analysis period, including reserved newest holdout (default180)",
    )
    parser.add_argument(
        "--fee-bps",
        type=float,
        default=6,
        help="Per-fill modeled fee (default6); use your venue fee tier",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=2,
        help="Per-fill modeled adverse slippage (default2)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        help="Whole funded account; default grid config or full DCA ladder with stress-fee reserve",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Fixed bot config object; with --bot all, keyed by bot",
    )
    parser.add_argument(
        "--context",
        type=Path,
        help="Optional coin-keyed ownership thesis for scheduled DCA",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        help="JSON overrides for the documented heuristic score/risk thresholds",
    )
    parser.add_argument(
        "--format", choices=("markdown", "json", "csv"), default="markdown"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write report; JSON includes audit fills/equity and all22template fields",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Explicit synthetic RANGE/RALLY/FALL fixtures; no real market claim",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    temporary = None
    try:
        if args.coin and args.coins:
            raise bots.BotError("choose --coin or --coins")
        if not args.demo and not (args.coin or args.coins):
            raise bots.BotError("supply --coin, --coins or --demo")
        if args.output and any(
            args.output.resolve() == path.resolve()
            for path in (args.config, args.context, args.policy)
            if path
        ):
            raise bots.BotError("output must not overwrite a config or context input")
        configs, context, policy = (
            _json_file(args.config),
            _json_file(args.context),
            _json_file(args.policy),
        )
        if args.bot == "all" and set(configs) - {"grid", "dca", "scheduled_dca"}:
            raise bots.BotError(
                "--bot all config must be keyed only by known bot names"
            )
        names = args.coins or ([args.coin] if args.coin else ["RANGE", "RALLY", "FALL"])
        data_dir = args.data_dir
        if args.demo:
            if args.data_dir or args.start:
                raise bots.BotError(
                    "--demo cannot use a real data directory or requested start"
                )
            duration = _finite(args.days, "days", 7)
            if duration > MAX_DAYS:
                raise bots.BotError("demo is limited to730days")
            temporary = tempfile.TemporaryDirectory(prefix="coin-fit-demo-")
            data_dir = Path(temporary.name)
            demo_data(data_dir, math.ceil(duration))
        settings = SimpleNamespace(
            data_dir=str(data_dir) if data_dir else "",
            asset="SOL",
            capital=args.capital or 10000,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        )
        selected = (
            ("grid", "dca", "scheduled_dca") if args.bot == "all" else (args.bot,)
        )
        reports = []
        for bot in selected:
            cfg = configs.get(bot) if args.bot == "all" else (configs or None)
            report = rank_coins(
                bot,
                names,
                settings,
                mode=args.mode,
                start=args.start,
                days=args.days,
                config=cfg,
                context=context,
                capital=args.capital,
                policy=policy,
            )
            report["synthetic"] = args.demo
            reports.append(report)
        text = render_report(reports, args.format)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
        else:
            print(text, end="")
        return 1 if any(r["errors"] for r in reports) else 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
        parser.exit(2, f"coin-fit: {exc}\n")
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(cli_main())
