"""Editable display state and causal market details; no trading or UI imports."""

from __future__ import annotations

import copy
import gzip
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core import indicators as ind
from backtester.core.strategies import build
from backtester.core.zec_ensemble import canonical_config
from research import zec_live as live
from research.shape_study import detect_shapes
from research.zec_expanded import key as config_key

CONFIG_KEYS = {
    "members",
    "mode",
    "persistence",
    "rebalance_threshold",
    "gate",
    "fallback",
    "weights",
    "weighting",
}
LOOKBACKS = (48, 96, 192, 300)


def row_key(row):
    return ":".join(
        (
            row["interval"],
            row.get("baseline_candidate_id", row["candidate_id"]),
            row["mode"],
        )
    )


def label(row):
    cfg = row.get("config")
    if not cfg:
        return row["family"] + " · " + row["candidate_id"]
    members = cfg["members"]
    if len(members) == 1:
        member = members[0]
        params = ", ".join(f"{k}={v}" for k, v in member.get("params", {}).items())
        return f"{member['strategy']}({params})"
    return cfg["mode"] + "[" + "+".join(s["strategy"] for s in members) + "]"


def finite_tree(value, depth=0):
    if depth > 10:
        raise ValueError("Configuration is too deeply nested")
    if isinstance(value, dict):
        for item in value.values():
            finite_tree(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item, depth + 1)
    elif type(value) in (int, float) and (
        not math.isfinite(value) or abs(value) > 1_000_000
    ):
        raise ValueError("Use finite numeric values within one million")


def validate_config(value):
    if not isinstance(value, dict) or set(value) - CONFIG_KEYS:
        raise ValueError("Use only the existing ensemble configuration fields")
    finite_tree(value)
    if (
        not isinstance(value.get("members"), list)
        or not 1 <= len(value["members"]) <= 16
    ):
        raise ValueError("Use between one and sixteen strategy members")
    cfg = copy.deepcopy(value)
    for spec in live.specs(cfg):
        if not isinstance(spec, dict) or set(spec) - {"strategy", "params"}:
            raise TypeError("A member needs a strategy and parameter object")
        if not isinstance(spec.get("params", {}), dict):
            raise TypeError("Strategy parameters must be an object")
        strategy = build(spec["strategy"], **spec.get("params", {}))
        if strategy.warmup_bars() > 10_000:
            raise ValueError("The live editor supports at most 10,000 warmup bars")
        spec["params"] = dict(strategy.params)
    if "weighting" in cfg and cfg["weighting"] != "inverse-absolute-correlation":
        raise ValueError("Unsupported weighting method")
    result = canonical_config({**cfg, "interval": "1m", "schema_version": 1})
    result.pop("interval")
    result.pop("schema_version")
    return result


def default_path():
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        / "solmargintrader"
        / "oracle-winners-tui.json"
    )


def validate_reference(value, baseline):
    if not isinstance(value, dict) or set(value) != set(baseline):
        raise ValueError("Keep the reference policy's existing fields")
    finite_tree(value)
    for name, initial in baseline.items():
        current = value[name]
        if isinstance(initial, dict):
            validate_reference(current, initial)
        elif isinstance(initial, str):
            if current != initial:
                raise ValueError("Reference policy types cannot change")
        elif (
            type(current) not in (int, float)
            or current < 0
            or (initial > 0 and current == 0)
            or (type(initial) is int and type(current) is not int)
        ):
            raise ValueError(
                "Reference values must preserve integer fields and valid signs"
            )


class WorkingSet:
    def __init__(self, winners=None):
        winners = live.load_winners() if winners is None else winners
        self.originals = {row_key(w): copy.deepcopy(w) for w in winners}
        self.interval, self.mode, self.refresh, self.lookback = (
            "1m",
            "baseline",
            10.0,
            96,
        )
        self.overrides = {}
        self.selected = set()
        for interval in live.STEPS:
            choices = [
                w
                for w in winners
                if w["interval"] == interval and w["mode"] == "baseline"
            ]
            choices.sort(
                key=lambda w: max(x["return_pct"] for x in w["historical"].values()),
                reverse=True,
            )
            self.selected.update(row_key(w) for w in choices[:6])
        self.references = {}
        if winners and all(w["config"] is not None for w in winners):
            return
        plan = json.loads(gzip.decompress((live.STUDY / "plan.json.gz").read_bytes()))
        self.references = {config_key(cfg): cfg for cfg in plan["lifecycle_configs"]}

    def choices(self):
        rows = [
            w
            for w in self.originals.values()
            if w["interval"] == self.interval
            and (self.mode == "all" or w["mode"] == self.mode)
        ]
        return sorted(
            rows,
            key=lambda w: (
                -max(h["return_pct"] for h in w["historical"].values()),
                label(w),
                row_key(w),
            ),
        )

    def effective(self, identity):
        row = copy.deepcopy(self.originals[identity])
        if identity in self.overrides:
            original_id = row["candidate_id"]
            config = copy.deepcopy(self.overrides[identity])
            row.update(
                baseline_candidate_id=original_id,
                candidate_id="edited-" + config_key(config),
                historical={},
                winning_fee_bps=[],
                edited=True,
            )
            if row["market"] == "spot_reference":
                row["config"] = config
            else:
                row["reference_config"] = config
        return row

    def visible(self):
        return [
            self.effective(row_key(w))
            for w in self.choices()
            if row_key(w) in self.selected
        ]

    def editor_config(self, identity):
        if identity in self.overrides:
            return copy.deepcopy(self.overrides[identity])
        row = self.originals[identity]
        if row["config"] is not None:
            return copy.deepcopy(row["config"])
        if row["candidate_id"].startswith("volty-"):
            _, length, multiple = row["candidate_id"].split("-")
            return {"length": int(length), "atr_mult": float(multiple)}
        return copy.deepcopy(self.references[row["candidate_id"]])

    def edit(self, identity, text):
        if len(text) > 32_768:
            raise ValueError("Configuration exceeds 32 KiB")
        value = json.loads(text)
        original = self.originals[identity]
        if original["market"] == "spot_reference":
            value = validate_config(value)
            baseline = validate_config(original["config"])
        else:
            baseline = self.editor_config_original(identity)
            validate_reference(value, baseline)
        if value == baseline:
            self.overrides.pop(identity, None)
        else:
            self.overrides[identity] = value

    def editor_config_original(self, identity):
        override = self.overrides.pop(identity, None)
        try:
            return self.editor_config(identity)
        finally:
            if override is not None:
                self.overrides[identity] = override

    def save(self, path):
        path = Path(path)
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("Preferences path must not use symlinks")
        path.parent.mkdir(parents=True, exist_ok=True)
        body = live.canonical(
            {
                "version": 1,
                "study_csv_sha256": live.CSV_HASH,
                "interval": self.interval,
                "mode": self.mode,
                "refresh": self.refresh,
                "lookback": self.lookback,
                "selected": sorted(self.selected),
                "overrides": self.overrides,
            }
        )
        if len(body.encode()) > 1_048_576:
            raise ValueError("Preferences exceed 1 MiB")
        descriptor, temporary = tempfile.mkstemp(
            prefix=".oracle-winners-", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(body + "\n")
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def load(self, path):
        path = Path(path)
        if not path.exists():
            return
        if path.is_symlink() or path.stat().st_size > 1_048_576:
            raise ValueError("Invalid preferences file")
        data = json.loads(path.read_text())
        if data.get("version") != 1 or data.get("study_csv_sha256") != live.CSV_HASH:
            raise ValueError("Preferences belong to a different study")
        if data.get("interval") not in live.STEPS or data.get("mode") not in (
            *live.MODES,
            "all",
        ):
            raise ValueError("Invalid saved window")
        refresh = float(data["refresh"])
        if (
            not math.isfinite(refresh)
            or not 0.2 <= refresh <= 300
            or data.get("lookback") not in LOOKBACKS
        ):
            raise ValueError("Invalid saved refresh or lookback")
        selected = set(data["selected"])
        if not selected <= self.originals.keys() or not isinstance(
            data.get("overrides"), dict
        ):
            raise ValueError("Unknown saved strategy")
        candidate = WorkingSet(list(self.originals.values()))
        for identity, config in data["overrides"].items():
            if identity not in self.originals:
                raise ValueError("Unknown saved configuration")
            candidate.edit(identity, live.canonical(config))
        self.interval, self.mode, self.refresh, self.lookback = (
            data["interval"],
            data["mode"],
            refresh,
            data["lookback"],
        )
        self.selected, self.overrides = selected, candidate.overrides


def market_details(rows, interval, end, lookback=96, configs=()):
    bars, valid = live.arrays_for(rows, live.STEPS[interval], end)
    gaps = np.flatnonzero(~valid)
    start = int(gaps[-1]) + 1 if len(gaps) else 0
    clean = {k: v[start:] for k, v in bars.items()}
    close, high, low = (clean[k] for k in ("close", "high", "low"))
    n = len(close)
    result = {
        "asof": end,
        "contiguous_bars": n,
        "chart": close[-lookback:].tolist(),
        "chart_start": int(clean["ts"][-min(n, lookback)]) if n else None,
        "shape": live.latest_shape(bars, valid, live.STEPS[interval]),
        "indicators": [],
    }
    result["indicators"] = market_indicators(clean, configs)
    if n >= 48:
        frame = pd.DataFrame(
            {"timestamp": clean["ts"], "close": close, "high": high, "low": low}
        )
        tag = detect_shapes(frame, window=48).iloc[-1]
        result["shape"].update(
            episode_age_bars=int(tag.episode_age_bars),
            turn_phase=str(tag.turn_phase),
            range_low=float(np.min(low[-48:])),
            range_high=float(np.max(high[-48:])),
            trace=close[-48:].tolist(),
            trace_start=int(clean["ts"][-48]),
            trace_end=int(clean["ts"][-1]),
            fitted_turn_bars_ago=(
                float(tag.fitted_turn_bars_ago)
                if np.isfinite(tag.fitted_turn_bars_ago)
                else None
            ),
        )
    return result


def market_indicators(clean, configs=()):
    """Canonical trailing scalar readings; callers control completed/live inputs."""
    close, high, low = (clean[k] for k in ("close", "high", "low"))
    n = len(close)
    values = []

    def add(name, value, ready=True):
        values.append(
            {
                "name": name,
                "value": float(value) if ready and np.isfinite(value) else None,
            }
        )

    if n:
        spread = high[-1] - low[-1]
        add(
            "Balance of power",
            (close[-1] - clean["open"][-1]) / spread if spread else np.nan,
        )
        add("Volume (ZEC)", clean["volume"][-1])
    rsi_periods = {14}
    for cfg in configs:
        if cfg:
            rsi_periods.update(
                s.get("params", {}).get("period", 14)
                for s in live.specs(cfg)
                if s["strategy"] == "rsi"
            )
    for period in sorted(rsi_periods):
        add(f"RSI {period}", ind.rsi(close, period), n >= period + 1)
    macd = ind.macd(close)
    for name, value in zip(("MACD 12/26", "MACD signal 9", "MACD histogram"), macd):
        add(name, value)
    mid, upper, lower, _ = ind.bollinger(close)
    for name, value in (
        ("BB20 middle", mid),
        ("BB20 upper 2σ", upper),
        ("BB20 lower 2σ", lower),
    ):
        add(name, value)
    add(
        "BB20 %B",
        (close[-1] - lower) / (upper - lower) * 100 if n and upper > lower else np.nan,
    )
    plus, minus, adx = ind.directional_movement(high, low, close)
    for name, value in (("ADX14", adx), ("+DI14", plus), ("−DI14", minus)):
        add(name, value)
    k, d = ind.stochastic(high, low, close)
    add("Stochastic %K14", k)
    add("Stochastic %D3", d)
    add("ATR14", ind.atr(high, low, close))
    add("EMA20", ind.ema(close, 20), n >= 20)
    add("EMA50", ind.ema(close, 50), n >= 50)
    add("Z-score20", ind.zscore(close))
    add("ROC20 %", ind.roc(close) * 100, n >= 21)
    # Keep edited/selected parameter readings separate from the standard panel.
    # A Bollinger45 hypothesis must not be explained with a Bollinger20 value.
    selected_specs = {
        live.canonical(s): s for cfg in configs if cfg for s in live.specs(cfg)
    }
    for spec in sorted(selected_specs.values(), key=live.canonical):
        params, kind = spec.get("params", {}), spec["strategy"]
        if kind in {"bb_reversion", "bb_breakout"}:
            window, width = params.get("window", 20), params.get("num_std", 2.0)
            if (window, width) != (20, 2.0):
                middle, top, bottom, _ = ind.bollinger(close, window, width)
                for part, value in (("mid", middle), ("upper", top), ("lower", bottom)):
                    name = f"BB {window}/{width:g}σ {part}"
                    if not any(r["name"] == name for r in values):
                        add(name, value)
        elif kind == "macd":
            fast, slow, signal = (
                params.get("fast", 12),
                params.get("slow", 26),
                params.get("signal", 9),
            )
            if (fast, slow, signal) != (12, 26, 9):
                _, _, histogram = ind.macd(close, fast, slow, signal)
                add(f"MACD {fast}/{slow}/{signal} hist", histogram)
        elif kind == "stochastic":
            k_period, d_period = params.get("k_period", 14), params.get("d_period", 3)
            if (k_period, d_period) != (14, 3):
                k_value, d_value = ind.stochastic(high, low, close, k_period, d_period)
                add(f"Stoch K{k_period}/D{d_period} %K", k_value)
                add(f"Stoch K{k_period}/D{d_period} %D", d_value)
    # Multiple strategies can share the same indicator parameters.
    return list({r["name"]: r for r in values}.values())
