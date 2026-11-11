"""Serializable causal ZEC ensemble policies shared by research and paper workers.

This module only computes exposures. It has no network or order-submission path.
Member policies use the canonical registry. Stateful members are advanced from
all prior bars, including before the ensemble's longest warmup completes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

import numpy as np

from . import indicators as ind
from .strategies import build as build_strategy
from .types import BarWindow, periods_per_year

MODES = {
    "single",
    "all",
    "any",
    "mean",
    "majority",
    "supermajority",
    "gate",
    "switch",
    "weighted",
}


def canonical_config(config: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(config, allow_nan=False))
    if value.get("schema_version", 1) != 1 or value.get("interval") not in {"1m", "1h"}:
        raise ValueError("ensemble requires schema_version 1 and interval 1m or 1h")
    value.setdefault("schema_version", 1)
    if value.get("mode") not in MODES or not value.get("members"):
        raise ValueError("ensemble mode and members are required")
    value.setdefault("persistence", 1)
    value.setdefault("rebalance_threshold", 0.0)
    if type(value["persistence"]) is not int or not 1 <= value["persistence"] <= 60:
        raise ValueError("persistence must be an integer in [1, 60]")
    if not 0 <= value["rebalance_threshold"] < 1:
        raise ValueError("rebalance threshold must be in [0,1)")
    for spec in [
        *value["members"],
        *([value["gate"]] if "gate" in value else []),
        *([value["fallback"]] if "fallback" in value else []),
    ]:
        build_strategy(spec["strategy"], **spec.get("params", {}))
    if value["mode"] in {"gate", "switch"} and "gate" not in value:
        raise ValueError("gated policies require gate")
    if value["mode"] == "switch" and "fallback" not in value:
        raise ValueError("switch policies require fallback")
    if value["mode"] == "weighted":
        weights = value.get("weights", [])
        if (
            len(weights) != len(value["members"])
            or any(not math.isfinite(x) or x < 0 for x in weights)
            or sum(weights) <= 0
        ):
            raise ValueError("weights must be finite nonnegative and match members")
        value["weights"] = [x / sum(weights) for x in weights]
    return value


def candidate_id(config: dict[str, Any]) -> str:
    raw = json.dumps(canonical_config(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def spec_id(spec: dict[str, Any]) -> str:
    return json.dumps(spec, sort_keys=True, separators=(",", ":"))


class _TrustedWindow(BarWindow):
    """Bounded causal views used only with audited built-in registry policies.

    Generic engine windows keep their owned-copy guard. The research cache and
    shared paper policy use prefix-only views internally, avoiding quadratic
    copies. All finite indicators cap their recursions at 12 times a window;
    this retains twice that plus a guard. Full-prefix RSI/EWMA/OBV carry exact
    recurrences separately. Unknown external strategies never enter this path.
    """

    __slots__ = ("limit",)

    def __init__(self, ts, open_, high, low, close, volume, i, limit=10000):
        super().__init__(ts, open_, high, low, close, volume, i)
        self.limit = limit

    def _series(self, name, source):
        value = source[max(0, self._i + 1 - self.limit) : self._i + 1].view()
        value.setflags(write=False)
        return value


class _Member:
    def __init__(self, spec: dict[str, Any], interval: str = "1h"):
        self.spec = copy.deepcopy(spec)
        self.strategy = build_strategy(spec["strategy"], **spec.get("params", {}))
        if spec["strategy"] in {"voltarget", "garch_voltarget"}:
            self.strategy.target_vol *= math.sqrt(365 / periods_per_year(interval))
            self.strategy.params["target_vol"] = self.strategy.target_vol
        self.ewma_var = None
        self.obv = 0.0
        self.obv_tail = []
        self.limit = (
            max(
                [int(x) for x in self.strategy.params.values() if type(x) is int]
                + [250]
            )
            * 24
            + 512
        )
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None

    def step(self, history: BarWindow) -> float:
        strategy = self.strategy
        history = _TrustedWindow(
            history._ts,
            history._open,
            history._high,
            history._low,
            history._close,
            history._volume,
            history.i,
            self.limit,
        )
        kind = self.spec["strategy"]
        i = history.i
        if kind in {"obv_trend", "swing_confluence"}:
            if i:
                delta = float(history.closes[-1] - history.closes[-2])
                self.obv += float(np.sign(delta)) * float(history.volumes[-1])
            self.obv_tail.append(self.obv)
            self.obv_tail = self.obv_tail[
                -max(getattr(strategy, "ma_window", 20), 20) :
            ]
            if i < strategy.warmup_bars():
                return 0.0
            if kind == "obv_trend":
                return float(self.obv > np.mean(self.obv_tail[-strategy.ma_window :]))
            close = float(history.closes[-1])
            if strategy._holding:
                if close < float(
                    np.min(history.lows[-strategy.exit_lookback - 1 : -1])
                ):
                    strategy._holding = False
            elif close > float(np.max(history.highs[-strategy.breakout - 1 : -1])):
                confirms = int(close > ind.sma(history.closes, strategy.ma_window))
                confirms += int(ind.macd(history.closes)[2] > 0)
                confirms += int(ind.rsi(history.closes) > 50)
                confirms += int(
                    len(self.obv_tail) >= 20 and self.obv > np.mean(self.obv_tail[-20:])
                )
                strategy._holding = confirms >= strategy.min_confirms
            return float(strategy._holding)
        if kind == "garch_voltarget":
            if i:
                r = float(np.log(history.closes[-1]) - np.log(history.closes[-2]))
                self.ewma_var = (
                    r * r
                    if i == 1
                    else (1 - strategy.lam) * r * r + strategy.lam * self.ewma_var
                )
            if i < strategy.warmup_bars() or history.closes[-1] <= ind.sma(
                history.closes, strategy.trend_window
            ):
                return 0.0
            sigma = math.sqrt(max(self.ewma_var, 0)) * math.sqrt(365)
            return min(1.0, strategy.target_vol / sigma) if sigma > 0 else 0.0
        # Canonical RSI recomputes Wilder's recursion from the entire prefix.
        # Carrying the same seed and recurrence avoids quadratic replay without
        # truncating history or changing its numerical definition.
        if self.spec["strategy"] == "rsi":
            i = history.i
            period = strategy.period
            closes = history.closes
            if i == period:
                delta = np.diff(closes)
                self.avg_gain = float(np.maximum(delta, 0).mean())
                self.avg_loss = float(np.maximum(-delta, 0).mean())
            elif i > period:
                delta = float(closes[-1] - closes[-2])
                self.avg_gain = (self.avg_gain * (period - 1) + max(delta, 0)) / period
                self.avg_loss = (self.avg_loss * (period - 1) + max(-delta, 0)) / period
            if i < strategy.warmup_bars():
                return 0.0
            rsi = (
                (100.0 if self.avg_gain > 0 else 50.0)
                if self.avg_loss <= 1e-15
                else 100 - 100 / (1 + self.avg_gain / self.avg_loss)
            )
            if not strategy._holding and rsi < strategy.oversold:
                strategy._holding = True
            elif strategy._holding and rsi > strategy.exit_level:
                strategy._holding = False
            return float(strategy._holding)
        if history.i < strategy.warmup_bars():
            return 0.0
        result = float(strategy.on_bar(history))
        if not math.isfinite(result):
            raise ValueError("member returned nonfinite exposure")
        return min(1.0, max(0.0, result))


def combine(
    config: dict[str, Any],
    member_values: list[float],
    gate: float = 0.0,
    fallback: float = 0.0,
) -> float:
    mode = config["mode"]
    if mode == "single":
        return member_values[0]
    if mode == "all":
        return min(member_values)
    if mode == "any":
        return max(member_values)
    if mode in {"mean", "gate", "switch"}:
        mean = sum(member_values) / len(member_values)
        return (
            mean
            if mode == "mean" or gate > 0
            else (fallback if mode == "switch" else 0.0)
        )
    if mode == "majority":
        return float(sum(x > 0 for x in member_values) * 2 > len(member_values))
    if mode == "supermajority":
        return float(sum(x > 0 for x in member_values) * 3 >= 2 * len(member_values))
    return sum(w * x for w, x in zip(config["weights"], member_values))


def persist(raw: float, state: dict[str, Any], count: int) -> float:
    active = raw > 0
    if active == state["pending"]:
        state["count"] += 1
    else:
        state["pending"], state["count"] = active, 1
    if state["count"] >= count:
        state["active"] = active
    state["last"] = (
        raw
        if state["active"] and active
        else (state["last"] if state["active"] else 0.0)
    )
    return state["last"]


class ZecEnsemble:
    def __init__(self, config: dict[str, Any]):
        self.params = canonical_config(config)
        self.name = "zec_ensemble_" + candidate_id(self.params)
        specs = [
            *self.params["members"],
            *([self.params["gate"]] if "gate" in self.params else []),
            *([self.params["fallback"]] if "fallback" in self.params else []),
        ]
        self.members = {
            spec_id(spec): _Member(spec, self.params["interval"]) for spec in specs
        }
        self.last_ts: int | None = None
        self.origin_ts: int | None = None
        self.persistence = {"pending": False, "count": 0, "active": False, "last": 0.0}

    def warmup_bars(self) -> int:
        return max(m.strategy.warmup_bars() for m in self.members.values())

    def on_bar(self, history: BarWindow) -> float:
        end = history.i + 1
        arrays = [
            source[:end]
            for source in (
                history._ts,
                history._open,
                history._high,
                history._low,
                history._close,
                history._volume,
            )
        ]
        if self.origin_ts is not None and int(arrays[0][0]) != self.origin_ts:
            raise ValueError(
                "ensemble history origin changed; replay full observed history"
            )
        if self.origin_ts is None:
            self.origin_ts = int(arrays[0][0])
        start = (
            0
            if self.last_ts is None
            else int(np.searchsorted(arrays[0], self.last_ts, side="right"))
        )
        for i in range(start, len(history)):
            window = _TrustedWindow(*arrays, i)
            values = {key: member.step(window) for key, member in self.members.items()}
            if i >= self.warmup_bars():
                raw = combine(
                    self.params,
                    [values[spec_id(s)] for s in self.params["members"]],
                    values.get(spec_id(self.params.get("gate", {})), 0.0),
                    values.get(spec_id(self.params.get("fallback", {})), 0.0),
                )
                persist(raw, self.persistence, self.params["persistence"])
            self.last_ts = int(arrays[0][i])
        return float(self.persistence["last"])

    def checkpoint_state(self) -> dict[str, Any]:
        return copy.deepcopy(
            {
                "last_ts": self.last_ts,
                "origin_ts": self.origin_ts,
                "persistence": self.persistence,
                "members": {
                    k: {
                        "strategy": m.strategy.__dict__,
                        "avg_gain": m.avg_gain,
                        "avg_loss": m.avg_loss,
                        "ewma_var": m.ewma_var,
                        "obv": m.obv,
                        "obv_tail": m.obv_tail,
                    }
                    for k, m in self.members.items()
                },
            }
        )

    def restore_state(self, state: dict[str, Any]) -> None:
        self.last_ts, self.origin_ts = state["last_ts"], state["origin_ts"]
        self.persistence = copy.deepcopy(state["persistence"])
        if set(state["members"]) != set(self.members):
            raise ValueError("ensemble member state changed")
        for key, saved in state["members"].items():
            member = self.members[key]
            member.strategy.__dict__.update(copy.deepcopy(saved["strategy"]))
            member.avg_gain, member.avg_loss = saved["avg_gain"], saved["avg_loss"]
            member.ewma_var, member.obv, member.obv_tail = (
                saved.get("ewma_var"),
                saved.get("obv", 0.0),
                saved.get("obv_tail", []),
            )


def build_ensemble(config: dict[str, Any]) -> ZecEnsemble:
    return ZecEnsemble(config)


def build(config: dict[str, Any], bars_per_year: float | None = None) -> ZecEnsemble:
    return build_ensemble(config)


def component_signal_series(
    spec: dict[str, Any], arrays: dict[str, np.ndarray], interval: str = "1h"
) -> np.ndarray:
    member = _Member(spec, interval)
    out = np.empty(len(arrays["ts"]), dtype="float64")
    for i in range(len(out)):
        out[i] = member.step(
            _TrustedWindow(
                arrays["ts"],
                arrays["open"],
                arrays["high"],
                arrays["low"],
                arrays["close"],
                arrays["volume"],
                i,
            )
        )
    return out


def signal_series(config: dict[str, Any], arrays: dict[str, np.ndarray]) -> np.ndarray:
    strategy = build_ensemble(config)
    out = np.zeros(len(arrays["ts"]), dtype="float64")
    for i in range(len(out)):
        out[i] = strategy.on_bar(
            BarWindow(
                arrays["ts"],
                arrays["open"],
                arrays["high"],
                arrays["low"],
                arrays["close"],
                arrays["volume"],
                i,
            )
        )
    return out


def latest_exposure(config: dict[str, Any], arrays: dict[str, np.ndarray]) -> float:
    strategy = build_ensemble(config)
    i = len(arrays["ts"]) - 1
    return strategy.on_bar(
        BarWindow(
            arrays["ts"],
            arrays["open"],
            arrays["high"],
            arrays["low"],
            arrays["close"],
            arrays["volume"],
            i,
        )
    )
