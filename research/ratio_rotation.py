"""Numeraire-switching rotation: hold whichever coin is cheapest against its peers.

    python3 research/ratio_rotation.py --self-test
    python3 research/ratio_rotation.py --turnover-table
    python3 research/ratio_rotation.py --demo-chain
    python3 research/ratio_rotation.py --sweep
    python3 research/ratio_rotation.py --sweep --assets BTC,ETH,SOL,DOGE,ZEC,XRP

This answers a question the single-asset engine cannot be asked. `run_backtest`
takes one asset's arrays and a strategy returning exposure in [-1, 1] on *that*
asset; "which of five coins do I hold right now" has no expression in that
interface. So this is a standalone portfolio simulator, in the same spirit as
`research/leverage_economics.py`: it borrows the project's cost model, block
splits and deflated-Sharpe machinery, and implements only the part that is
genuinely missing.

## The idea being tested, and the one it is NOT

The premise is the folk strategy of *chaining discounts*: ETH/BTC looks cheap so
buy ETH, later SOL/ETH looks cheap so spend that ETH on SOL, and so on around the
board, compounding a discount at every hop.

**The chain is arithmetic fiction, and `--demo-chain` measures the damage.** All
series here are USD-quoted, so every cross rate is a quotient of two USD closes
and the triangle closes exactly:

    (ETH/BTC) * (SOL/ETH) = SOL/BTC        identically, to floating point

Therefore BTC -> ETH -> SOL and BTC -> SOL end in the same quantity of SOL, except
the chained route paid two fee-and-slippage legs instead of one. Chaining cannot
add return; it can only subtract cost. What survives the observation is not a
chain at all but a *selection*: at each rebalance, which single asset do I want to
be denominated in. That is what this module backtests.

The genuinely different strategy -- exploiting real, separately-quoted cross pairs
whose product departs from one -- is triangular arbitrage, and
`backtester/strategy_cards/triangular_arbitrage.md` already explains at length why
this project's data cannot evaluate it and why measuring it here would manufacture
a spurious equity curve out of timestamp misalignment. Nothing in this module
should be read as evidence about that card's subject.

## Why the identity check in `--self-test` is not a finding

`test_cross_rate_identity` asserts the triangle closes. It will always pass on
correct code, because on USD-quoted series it is true by construction. It is a
**quote-convention guard**, not a result: it fails only when a leg has been
inverted, which `triangular_arbitrage.md` names as the most common implementation
bug in this family. Reporting its success as evidence of anything would be the
exact error the card warns about.

## Signal

For each asset `i` at bar `t`, over a trailing `window`:

    x_i(t)     = log P_i(t)
    rel_i(t)   = x_i(t) - mean_j x_j(t)          cross-sectional log-price level
    score_i(t) = -zscore(rel_i, window)          "reversion": cheap vs peers ranks high
                 +zscore(rel_i, window)          "momentum":  strong vs peers ranks high

Ranking on `rel` demeaned across assets is what makes this a *relative* statement
rather than a directional one: adding a constant to every log price leaves every
score unchanged. `top_k` assets are held at equal weight; `top_k=1` is literal
numeraire switching, the user-facing version of the idea.

The `momentum` direction is included because it is the honest control. Buying the
relative loser and buying the relative winner are the same machine with one sign
flipped, and a family in which *both* signs look profitable is measuring something
other than the signal.

## Costs are the entire question, so they are charged first

Turnover cost is `sum_i |W(t,i) - W(t-1,i)| * (fee_bps + slippage_bps) / 1e4`. A
complete rotation between two assets moves 2.0 of weight and therefore pays twice
the one-way cost. At this project's `CostConfig` defaults (6 bps fee, 2 bps
slippage) that is 16 bps per rotation, and `--turnover-table` prints what that
compounds to at each holding period. Read it before tuning anything: it rules out
short lookbacks on economics alone, and every configuration not run is one fewer
trial the deflated Sharpe has to be corrected for.

## Timing convention, and how it is enforced

Weights at bar `t` are computed from closes through `t` inclusive, charged their
turnover at `t`, and earn the close-to-close return of bar `t+1`. That is the
standard one-bar convention: it assumes execution at the close you just observed.
`--fill-delay` inserts additional whole bars between signal and exposure; if a
result survives at delay 0 but dies at delay 1, it was reading the fill.

The convention is enforced rather than asserted. `test_no_lookahead` recomputes
the weights after overwriting all data strictly after bar `t` with garbage and
requires the first `t+1` rows to be bit-identical. A one-bar leak fails it.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import make_groups, pbo_cscv  # noqa: E402
from backtester.core.data import CsvLoader, frame_to_arrays  # noqa: E402
from backtester.core.deflated_sharpe import (  # noqa: E402
    deannualise,
    deflated_sharpe_ratio,
    effective_trials,
    trial_sharpe_variance,
)
from backtester.core.metrics import max_drawdown, sharpe_ratio  # noqa: E402
from backtester.core.perps import hourly_borrow_rate  # noqa: E402
from backtester.core.types import CostConfig, Side, hours_per_bar, periods_per_year  # noqa: E402

OUT_DIR = REPO / "research" / "results"

# The universe that survives the intersection test in `describe_universes()`.
# Rotation needs EVERY asset present at bar t -- unlike the per-asset sweeps, it
# cannot run each coin on its own window -- so the study length is set by the
# shortest member, and adding a young coin is paid for in years of history.
PRIMARY_ASSETS = ("BTC", "ETH", "SOL", "DOGE", "ZEC")

# Adding XRP costs 40% of the bars. Reported as a secondary universe rather than
# folded into the primary, because a result that only appears in one of them is
# a result about the window, not about breadth.
SECONDARY_ASSETS = ("BTC", "ETH", "SOL", "DOGE", "ZEC", "XRP")

# Assets deliberately excluded, and the number that decides it. BNB and HYPE are
# not judged on quality: intersecting either one collapses the study to under a
# year, which is below any evidence floor this project accepts.
EXCLUDED_ASSETS: dict[str, str] = {
    "BNB": "listed 2025-10-22; intersecting it truncates the 5-coin study from 1,875 bars to 287",
    "HYPE": "listed 2026-02-05; intersecting it truncates the study to 181 bars",
    "TRX": "not listed on Coinbase at all (see backtester/core/universe.py)",
}

# A row needs this many rebalances out-of-sample before it is ranked rather than
# merely listed, matching research/sweep.py's MIN_OOS_TRADES rationale.
MIN_OOS_ROTATIONS = 10

# Walk-forward in-sample fraction, matching research/sweep.py's SPLIT.
SPLIT = 0.70

# Lookbacks are pruned on economics, not taste: see `turnover_table()`. Windows
# below ~20 daily bars rotate fast enough that the cost line dominates any
# plausible edge, so they are not searched. Not searching them is not a courtesy
# to the strategy -- it lowers the trial count that the deflated Sharpe deflates by.
SWEEP_WINDOWS = (20, 30, 45, 60, 90, 120)
SWEEP_TOP_K = (1, 2)
SWEEP_DIRECTIONS = ("reversion", "momentum")

# Rebalance only when the score ranking actually changes AND the incoming asset's
# score beats the incumbent's by this margin. A pure argmax rotates on noise.
SWEEP_MARGINS = (0.0, 0.25, 0.5)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Panel:
    """Aligned close prices for a set of assets on their common timestamps.

    Alignment is by exact timestamp intersection with no forward-fill, following
    `backtester.core.pairs.align_peer`'s reasoning: a filled bar is an invented
    price, and in a cross-sectional strategy an invented price does not merely add
    noise, it can be *selected* -- the asset whose stale close makes it look
    cheapest is exactly the one the rule buys.
    """

    assets: tuple[str, ...]
    timestamps: np.ndarray  # (T,) int64 epoch seconds
    closes: np.ndarray  # (T, N) float64
    interval: str

    @property
    def n_bars(self) -> int:
        return int(self.closes.shape[0])

    @property
    def n_assets(self) -> int:
        return int(self.closes.shape[1])

    def returns(self) -> np.ndarray:
        """(T, N) simple close-to-close returns; row 0 is zero by construction."""
        out = np.zeros_like(self.closes)
        out[1:] = self.closes[1:] / self.closes[:-1] - 1.0
        return out

    def span(self) -> str:
        lo = pd.to_datetime(int(self.timestamps[0]), unit="s").date()
        hi = pd.to_datetime(int(self.timestamps[-1]), unit="s").date()
        return f"{lo}..{hi}"

    def describe(self) -> str:
        return f"{'+'.join(self.assets)} {self.n_bars} bars {self.span()}"


def load_panel(
    assets: Sequence[str],
    interval: str = "1d",
    data_dir: Path | None = None,
    allow_gaps: bool = True,
) -> Panel:
    """Load `assets` and intersect them onto their common timestamps.

    `allow_gaps` defaults to True here and False in the backtester CLI, and the
    difference is deliberate. A gap in ONE member of a rotation panel is not
    silently concatenated the way it is in a single-asset series: the intersection
    below drops any timestamp not present in every asset, so a hole in one coin
    removes those bars from the study for all of them. That is visible in the bar
    count this function reports, which is the number the reader is asked to judge.
    """
    data_dir = data_dir or (REPO / "data")
    frames: dict[str, pd.DataFrame] = {}
    for asset in assets:
        path = data_dir / f"{asset}_{interval}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} missing. data/ is gitignored and refetched; run:\n"
                f"  python3 -m backtester.core.universe --assets {','.join(assets)} "
                f"--interval {interval} --allow-partial --allow-gaps"
            )
        frames[asset] = CsvLoader(path, allow_gaps=allow_gaps).load(asset, None, None, interval)

    common: set[int] | None = None
    for asset, frame in frames.items():
        ts = set(int(v) for v in frame["timestamp"].to_numpy())
        common = ts if common is None else (common & ts)
    assert common is not None
    if len(common) < 2:
        raise ValueError(f"{'+'.join(assets)} share only {len(common)} timestamps; not a panel")

    ordered = np.array(sorted(common), dtype=np.int64)
    closes = np.empty((ordered.size, len(assets)), dtype=np.float64)
    for j, asset in enumerate(assets):
        frame = frames[asset]
        keep = frame["timestamp"].astype("int64").isin(ordered)
        sub = frame.loc[keep].sort_values("timestamp")
        closes[:, j] = sub["close"].to_numpy(dtype=np.float64)

    return Panel(tuple(assets), ordered, closes, interval)


def describe_universes(interval: str = "1d", data_dir: Path | None = None) -> pd.DataFrame:
    """Intersection length of each candidate universe, longest-first.

    This is the evidence behind `PRIMARY_ASSETS` and exists so the choice can be
    re-derived rather than trusted. "Use all the coins" is a reasonable instruction
    that this table answers with a number: the 8-asset intersection is 181 bars.
    """
    data_dir = data_dir or (REPO / "data")
    available = sorted(p.name.split("_")[0] for p in data_dir.glob(f"*_{interval}.csv"))
    rows: list[dict[str, Any]] = []
    for size in range(2, len(available) + 1):
        best: tuple[int, tuple[str, ...]] | None = None
        for combo in itertools.combinations(available, size):
            try:
                panel = load_panel(combo, interval, data_dir)
            except (ValueError, FileNotFoundError):
                continue
            if best is None or panel.n_bars > best[0]:
                best = (panel.n_bars, combo)
        if best is not None:
            panel = load_panel(best[1], interval, data_dir)
            rows.append(
                {"n_assets": size, "assets": "+".join(best[1]), "bars": best[0], "span": panel.span()}
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Signal
# --------------------------------------------------------------------------


def rolling_zscore_of_relative_log_price(
    closes: np.ndarray, window: int
) -> np.ndarray:
    """(T, N) z-score of each asset's log price relative to the cross-sectional mean.

    Returns NaN for the first `window` rows, which callers must treat as "no
    position" rather than "zero score" -- a zero score is a rank, and ranking on
    warm-up rows would put an arbitrary asset in the portfolio before any evidence
    about it exists.

    Every value at row `t` is computed from rows `<= t`. That is the whole
    look-ahead surface of this module and `test_no_lookahead` is what checks it.
    """
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}")
    # Both guards are needed and neither implies the other: `NaN <= 0` is False,
    # so a NaN price would slip past the positivity check, become a NaN z-score,
    # and then be coerced to 0.0 below -- ranking a missing price as exactly
    # average and making it selectable. `load_panel` already rejects non-finite
    # closes upstream, but this function is public and must not be the weak link.
    if not np.all(np.isfinite(closes)):
        raise ValueError("non-finite close in panel; log price undefined")
    if np.any(closes <= 0):
        raise ValueError("non-positive close in panel; log price undefined")

    logp = np.log(closes)
    relative = logp - logp.mean(axis=1, keepdims=True)

    T, N = relative.shape
    out = np.full((T, N), np.nan, dtype=np.float64)
    if T <= window:
        return out

    # Trailing mean and standard deviation of each asset's own relative series.
    # Computed with an explicit loop rather than a cumulative-sum trick: the
    # cumsum form loses precision on long series of similar magnitudes, and this
    # runs once per configuration on <2,000 bars.
    for t in range(window, T):
        block = relative[t - window + 1 : t + 1]
        mu = block.mean(axis=0)
        sd = block.std(axis=0, ddof=1)
        # A dead-flat window has no dispersion and therefore no opinion. Emitting
        # 0.0 would rank it as exactly average, which is the right abstention.
        safe = np.where(sd > 1e-12, sd, np.nan)
        z = (relative[t] - mu) / safe
        out[t] = np.where(np.isfinite(z), z, 0.0)
    return out


def target_weights(
    closes: np.ndarray,
    window: int,
    top_k: int = 1,
    direction: str = "reversion",
    margin: float = 0.0,
) -> np.ndarray:
    """(T, N) target weights, row `t` computed from closes through `t` inclusive.

    `margin` is hysteresis, not a tuning knob added for performance: a bare argmax
    over noisy scores rotates whenever two assets cross, and at 16 bps a rotation
    that is a coin-flip is a guaranteed loss. An incumbent is displaced only when
    the challenger's score exceeds it by `margin`.
    """
    if direction not in ("reversion", "momentum"):
        raise ValueError(f"direction must be 'reversion' or 'momentum', got {direction!r}")
    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")
    if margin < 0:
        raise ValueError(f"margin must be >= 0, got {margin}")

    z = rolling_zscore_of_relative_log_price(closes, window)
    sign = -1.0 if direction == "reversion" else 1.0
    scores = sign * z

    T, N = scores.shape
    k = min(top_k, N)
    weights = np.zeros((T, N), dtype=np.float64)
    held: np.ndarray | None = None

    for t in range(T):
        row = scores[t]
        if not np.all(np.isfinite(row)):
            held = None  # still in warm-up: hold nothing, not something arbitrary
            continue
        ranked = np.argsort(-row, kind="stable")[:k]
        if held is not None and margin > 0.0:
            incumbent_worst = float(np.min(row[held]))
            challengers = [i for i in ranked if i not in set(held.tolist())]
            # Keep the incumbent set unless a challenger clears it by `margin`.
            if challengers and float(np.max(row[challengers])) < incumbent_worst + margin:
                ranked = held
        held = np.asarray(ranked, dtype=int)
        weights[t, held] = 1.0 / held.size
    return weights


# --------------------------------------------------------------------------
# Portfolio simulation
# --------------------------------------------------------------------------


@dataclass
class RotationResult:
    """One evaluated configuration on one panel slice."""

    label: str
    params: dict[str, Any]
    timestamps: np.ndarray
    equity: np.ndarray
    net_returns: np.ndarray
    gross_returns: np.ndarray
    turnover: np.ndarray
    interval: str
    borrow_cost_total: float = 0.0
    ruin_index: int | None = None

    @property
    def ruined(self) -> bool:
        """True if equity reached the zero floor. Everything after is not a path."""
        return self.ruin_index is not None

    @property
    def live_returns(self) -> np.ndarray:
        """Net returns up to ruin.

        Metrics must be computed on this, not on `net_returns`. Once equity hits
        the floor the simulator keeps producing return numbers for bars the
        account could not have traded, and a Sharpe computed across them describes
        a counterfactual portfolio that still had money. The first version of this
        module reported Sharpe 1.19 for a path that had already gone to zero.
        """
        if self.ruin_index is None:
            return self.net_returns
        return self.net_returns[: self.ruin_index + 1]

    @property
    def n_rotations(self) -> int:
        """Rebalances where any weight actually moved."""
        return int(np.count_nonzero(self.turnover > 1e-12))

    @property
    def total_cost(self) -> float:
        """Terminal gross wealth minus terminal net wealth, as a multiple of stake.

        Informational only. On a ruined or heavily levered path the net product
        runs through bars the account could not have traded, so read this column
        as a cost indicator rather than an accounting figure; `live_returns`
        explains why those bars are fictional.
        """
        gross = float(np.prod(1.0 + self.gross_returns))
        net = float(np.prod(1.0 + self.net_returns))
        return gross - net

    def sharpe(self) -> float:
        """Sharpe on the live path.

        Note a property that makes this column near-useless for comparing
        leverages: when every term scales linearly with leverage -- the return,
        the turnover cost and the borrow fee all do -- mean and standard
        deviation scale together and the ratio is unchanged. A leverage sweep
        therefore prints a constant Sharpe by arithmetic, and `monthly_pct` and
        `max_drawdown` are the columns that carry the information.
        """
        live = self.live_returns
        if live.size < 2:
            return float("nan")
        return float(sharpe_ratio(live, periods_per_year(self.interval)))

    def gross_sharpe(self) -> float:
        return float(sharpe_ratio(self.gross_returns, periods_per_year(self.interval)))

    def total_return(self) -> float:
        return float(self.equity[-1] / self.equity[0] - 1.0)

    def monthly_pct(self) -> float:
        """Mean return per 30 days, the unit research/SWEEP-9COIN.md reports in."""
        ppy = periods_per_year(self.interval)
        years = len(self.net_returns) / ppy
        if years <= 0:
            return 0.0
        return float(((self.equity[-1] / self.equity[0]) ** (1.0 / (years * 12.0)) - 1.0) * 100.0)

    def max_drawdown(self) -> float:
        return float(max_drawdown(self.equity, self.timestamps).max_drawdown)

    def summary(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "bars": len(self.net_returns),
            "rotations": self.n_rotations,
            "total_return": self.total_return(),
            "monthly_pct": self.monthly_pct(),
            "sharpe": self.sharpe(),
            "gross_sharpe": self.gross_sharpe(),
            "max_drawdown": self.max_drawdown(),
            "cost_drag": self.total_cost,
            **self.params,
        }


def simulate(
    panel: Panel,
    weights: np.ndarray,
    costs: CostConfig | None = None,
    label: str = "rotation",
    params: dict[str, Any] | None = None,
    fill_delay: int = 0,
    leverage: float = 1.0,
    borrow_utilization: float | None = None,
    accrue_borrow: bool | None = None,
) -> RotationResult:
    """Run `weights` over `panel` and charge turnover.

    Timing: `weights[t]` is charged its turnover at bar `t` and earns bar `t+1`'s
    return. `fill_delay` shifts exposure that many further bars into the future
    while leaving the cost where the decision was made, which is the conservative
    direction -- a delayed fill should not also get a delayed bill.

    `leverage` scales exposure. `accrue_borrow` decides whether the perp borrow
    fee from `backtester.core.perps` is charged, and defaults to `leverage > 1.0`
    -- read that default as "unlevered means spot, levered means perp" rather
    than as a property of leverage itself. It is stated as its own argument
    because tying it to `leverage > 1.0` implicitly puts a cliff at exactly 1.0,
    where 1.0x pays nothing and 1.0001x pays the fee on the *entire* notional.
    The cliff is real in the sense that spot and perp are different venues; it is
    an artifact if a reader takes the leverage curve as continuous.

    The fee is charged on full notional, not on the borrowed increment, because
    that is how the perp venues this project targets actually bill. Note what
    that models: a borrow fee BOTH sides pay, floored at zero -- not a funding
    rate that changes sign. It is a cost sensitivity, not a carry strategy; see
    RATIO-ROTATION.md.
    """
    costs = costs or CostConfig()
    if fill_delay < 0:
        raise ValueError(f"fill_delay must be >= 0, got {fill_delay}")
    if leverage <= 0:
        raise ValueError(f"leverage must be > 0, got {leverage}")

    rets = panel.returns()
    T = panel.n_bars
    cost_rate = (costs.fee_bps + costs.slippage_bps) / 1e4

    prev = np.zeros(panel.n_assets, dtype=np.float64)
    net = np.zeros(T, dtype=np.float64)
    gross = np.zeros(T, dtype=np.float64)
    turn = np.zeros(T, dtype=np.float64)
    borrow_total = 0.0

    hours = hours_per_bar(panel.interval)
    borrow_rate = 0.0
    if accrue_borrow if accrue_borrow is not None else leverage > 1.0:
        util = borrow_utilization if borrow_utilization is not None else costs.utilization
        borrow_rate = hourly_borrow_rate(costs, Side.LONG, util)

    for t in range(T - 1):
        w = weights[t]
        # Turnover is billed against the leveraged notional, because that is the
        # size actually traded. Charging it on the unlevered weight would make
        # leverage look free, which is the error `leverage_economics.py` exists
        # to prevent.
        moved = float(np.abs(w - prev).sum()) * leverage
        turn[t] = moved
        prev = w

        src = t - fill_delay
        exposure = weights[src] if src >= 0 else np.zeros(panel.n_assets)
        gross_ret = float(np.dot(exposure, rets[t + 1])) * leverage

        borrow = 0.0
        if borrow_rate > 0.0:
            notional = float(np.abs(exposure).sum()) * leverage
            borrow = notional * borrow_rate * hours
            borrow_total += borrow

        gross[t + 1] = gross_ret
        net[t + 1] = gross_ret - moved * cost_rate - borrow

    equity = np.empty(T, dtype=np.float64)
    equity[0] = 1.0
    # Floor at zero: a levered path can be wiped out, and letting equity go
    # negative would silently produce a "recovery" from below zero. Record WHERE
    # that happened, because every return after it is fictional -- the account
    # had nothing left to earn it with.
    ruin_index: int | None = None
    for t in range(1, T):
        equity[t] = max(equity[t - 1] * (1.0 + net[t]), 0.0)
        if ruin_index is None and equity[t] <= 0.0:
            ruin_index = t

    return RotationResult(
        label=label,
        params=params or {},
        timestamps=panel.timestamps,
        equity=equity,
        net_returns=net,
        gross_returns=gross,
        turnover=turn,
        interval=panel.interval,
        borrow_cost_total=borrow_total,
        ruin_index=ruin_index,
    )


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------


def control_weights(
    panel: Panel, kind: str, seed: int = 0, window: int = 60, top_k: int = 1, hold_bars: int | None = None
) -> np.ndarray:
    """Benchmark weight paths.

    `random` is the control that matters and the one most often omitted. A
    rotation rule that cannot beat *rotating at random among the same assets at
    the same frequency* has demonstrated only that the assets went up. The 9-coin
    sweep found exactly this for trend: the random baseline exceeded the
    walk-forward result, meaning selection destroyed value.

    `hold_bars` sets how often the random control re-draws. It must be matched to
    the rule under test: a control that rotates at a different frequency is
    comparing turnover costs, not selection skill.
    """
    T, N = panel.closes.shape
    weights = np.zeros((T, N), dtype=np.float64)

    if kind == "equal_weight":
        weights[window:] = 1.0 / N
        return weights

    if kind.startswith("hold_"):
        asset = kind[len("hold_") :]
        if asset not in panel.assets:
            raise ValueError(f"{asset} not in panel {panel.assets}")
        weights[window:, panel.assets.index(asset)] = 1.0
        return weights

    if kind == "random":
        rng = np.random.default_rng(seed)
        k = min(top_k, N)
        # Match the *frequency* of the rule it controls for, not just its assets:
        # a control that rotates every bar would be beaten by anything.
        every = max(int(hold_bars if hold_bars is not None else window), 1)
        held = rng.choice(N, size=k, replace=False)
        for t in range(window, T):
            if (t - window) % every == 0:
                held = rng.choice(N, size=k, replace=False)
            weights[t, held] = 1.0 / k
        return weights

    raise ValueError(f"unknown control {kind!r}")


def evaluate_controls(
    panel: Panel,
    costs: CostConfig | None = None,
    split: float = SPLIT,
    match_hold_bars: int = 30,
    match_top_k: int = 1,
    random_seeds: int = 50,
) -> pd.DataFrame:
    """Controls measured on the SAME out-of-sample slice the sweep rows report.

    This function exists because of a bug worth recording rather than quietly
    fixing: the first run of this module ranked strategy rows on the last 30% of
    the panel while printing controls over all 1,875 bars. The strategy's
    +12.9%/month then sat beside buy-and-hold's +0.54%/month, and the gap was
    almost entirely the difference between two time windows. Any control not
    evaluated on the identical slice is decoration.

    The random control is run over `random_seeds` draws and reported as a
    distribution, not a single path. One seed of a random rotation is a single
    sample from a wide distribution -- the first version of this drew -79.5% and
    would have made the strategy look far better than the median draw justifies.

    `match_top_k` matters for the same reason `match_hold_bars` does. A `top_k=2`
    rule compared against a 1-asset random control gets credit for diversification
    it did not earn: two assets have lower variance than one by construction, so
    part of any Sharpe edge would be breadth rather than selection skill. Both
    knobs exist so the control differs from the rule in exactly one respect --
    *which* assets it picks -- and in no other.
    """
    costs = costs or CostConfig()
    cut = int(panel.n_bars * split)
    oos = slice_panel(panel, cut, panel.n_bars)
    rows: list[dict[str, Any]] = []

    for kind in ["equal_weight"] + [f"hold_{a}" for a in panel.assets]:
        w = control_weights(panel, kind, window=0)
        res = simulate(oos, w[cut:], costs, kind, {"control": kind})
        rows.append(res.summary())

    draws = []
    for seed in range(random_seeds):
        w = control_weights(
            panel, "random", seed=seed, window=0, top_k=match_top_k, hold_bars=match_hold_bars
        )
        draws.append(simulate(oos, w[cut:], costs, "random", {}))
    for label, pick in (
        ("random_p50", float(np.median([d.monthly_pct() for d in draws]))),
        ("random_p90", float(np.percentile([d.monthly_pct() for d in draws], 90))),
    ):
        rows.append(
            {
                "label": f"{label} (n={random_seeds}, hold={match_hold_bars}, k={match_top_k})",
                "bars": oos.n_bars,
                "rotations": int(np.median([d.n_rotations for d in draws])),
                "total_return": float("nan"),
                "monthly_pct": pick,
                "sharpe": float(np.median([d.sharpe() for d in draws]))
                if label.endswith("p50")
                else float(np.percentile([d.sharpe() for d in draws], 90)),
                "max_drawdown": float("nan"),
            }
        )

    return pd.DataFrame(rows)


def best_single_asset_ex_post(panel: Panel, costs: CostConfig | None = None) -> RotationResult:
    """The best buy-and-hold in hindsight -- an upper bound nobody could have picked.

    Included because it is the number that makes a rotation result interpretable
    in the other direction. Beating buy-and-hold BTC is easy in a sample where
    another coin tripled; beating the ex-post best is the bar for "the selection
    rule found something", and essentially nothing clears it.
    """
    best: RotationResult | None = None
    for asset in panel.assets:
        res = simulate(
            panel,
            control_weights(panel, f"hold_{asset}", window=0),
            costs=costs,
            label=f"hold_{asset}",
            params={"control": f"hold_{asset}"},
        )
        if best is None or res.total_return() > best.total_return():
            best = res
    assert best is not None
    return best


# --------------------------------------------------------------------------
# The chain demonstration
# --------------------------------------------------------------------------


def demo_chain(panel: Panel, costs: CostConfig | None = None) -> pd.DataFrame:
    """Measure the cost of routing BTC->ETH->SOL versus BTC->SOL directly.

    This is the empirical form of the module's central claim. Both routes end
    holding SOL; the only difference is how many fee legs were paid. The table
    reports the terminal SOL quantity per route so the reader can see that the
    gross quantities are identical to floating point and the net ones differ by
    exactly the extra leg.
    """
    costs = costs or CostConfig()
    leg = (costs.fee_bps + costs.slippage_bps) / 1e4
    needed = ("BTC", "ETH", "SOL")
    missing = [a for a in needed if a not in panel.assets]
    if missing:
        raise ValueError(f"demo_chain needs {needed}; panel lacks {missing}")

    i_btc, i_eth, i_sol = (panel.assets.index(a) for a in needed)
    p = panel.closes[-1]
    start_btc = 1.0

    # Cross rates, derived from USD closes. This IS the identity under test.
    r_btc_eth = p[i_btc] / p[i_eth]  # ETH per BTC
    r_eth_sol = p[i_eth] / p[i_sol]  # SOL per ETH
    r_btc_sol = p[i_btc] / p[i_sol]  # SOL per BTC

    chained_gross = start_btc * r_btc_eth * r_eth_sol
    direct_gross = start_btc * r_btc_sol
    chained_net = start_btc * r_btc_eth * (1 - leg) * r_eth_sol * (1 - leg)
    direct_net = start_btc * r_btc_sol * (1 - leg)

    return pd.DataFrame(
        [
            {
                "route": "BTC->ETH->SOL (chained)",
                "legs": 2,
                "sol_gross": chained_gross,
                "sol_net": chained_net,
                "cost_bps": (1 - chained_net / chained_gross) * 1e4,
            },
            {
                "route": "BTC->SOL (direct)",
                "legs": 1,
                "sol_gross": direct_gross,
                "sol_net": direct_net,
                "cost_bps": (1 - direct_net / direct_gross) * 1e4,
            },
        ]
    )


def carry_table(
    panel: Panel,
    window: int,
    top_k: int,
    direction: str,
    margin: float,
    costs: CostConfig | None = None,
    split: float = SPLIT,
    leverages: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
) -> pd.DataFrame:
    """Leverage-cost sensitivity of one configuration on the out-of-sample slice.

    **Read the label carefully: this is a borrow-fee cost curve, not a carry
    strategy.** `backtester/core/perps.py` models a fee that BOTH sides pay and
    that is floored at zero (see its docstring). A funding rate -- the thing an
    actual basis-carry trade harvests -- changes sign with the long/short
    imbalance, and receiving it when it is negative is the entire trade. This
    module cannot express that, because no funding-rate history is cached in this
    repository.

    So what this table answers is the narrow question: how fast does the
    financing cost eat this rotation as leverage rises. What it cannot answer --
    whether a funding-basis carry strategy across these pairs is profitable --
    needs data the project does not have, and is written up as a spec-only
    question in RATIO-ROTATION.md rather than guessed at here.
    """
    costs = costs or CostConfig()
    weights = target_weights(panel.closes, window, top_k, direction, margin)
    cut = int(panel.n_bars * split)
    oos = slice_panel(panel, cut, panel.n_bars)

    rows: list[dict[str, Any]] = []
    for lev in leverages:
        res = simulate(
            oos, weights[cut:], costs, f"lev{lev:g}", {"leverage": lev}, leverage=lev
        )
        unlevered = simulate(oos, weights[cut:], costs, "base", {}, leverage=1.0)
        rows.append(
            {
                "leverage": lev,
                "monthly_pct": res.monthly_pct(),
                "sharpe": res.sharpe(),
                "max_drawdown": res.max_drawdown(),
                "ruined": res.ruined,
                "borrow_cost_frac": res.borrow_cost_total,
                # What leverage SHOULD have produced if financing were free, so the
                # gap between the two columns is exactly the cost of the money.
                "naive_scaled_monthly_pct": unlevered.monthly_pct() * lev,
            }
        )
    return pd.DataFrame(rows)


def turnover_table(costs: CostConfig | None = None, interval: str = "1d") -> pd.DataFrame:
    """Annual cost drag as a function of average holding period.

    The point of printing this before any backtest: it is a pure arithmetic
    statement about the cost model that no amount of parameter search can argue
    with, and it prunes the grid on economics rather than on results.
    """
    costs = costs or CostConfig()
    one_way = (costs.fee_bps + costs.slippage_bps) / 1e4
    per_rotation = 2.0 * one_way  # out of one asset and into another
    ppy = periods_per_year(interval)
    rows = []
    for hold in (1, 2, 3, 5, 10, 20, 30, 60, 90):
        rotations = ppy / hold
        rows.append(
            {
                "avg_hold_bars": hold,
                "rotations_per_year": round(rotations, 1),
                "cost_bps_per_rotation": per_rotation * 1e4,
                "annual_drag_pct": (1.0 - (1.0 - per_rotation) ** rotations) * 100.0,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------


def slice_panel(panel: Panel, start: int, end: int) -> Panel:
    return Panel(panel.assets, panel.timestamps[start:end], panel.closes[start:end], panel.interval)


def walk_forward(
    panel: Panel,
    window: int,
    top_k: int,
    direction: str,
    margin: float,
    costs: CostConfig | None = None,
    split: float = SPLIT,
) -> tuple[RotationResult, RotationResult]:
    """In-sample and out-of-sample halves of one configuration.

    The weights are computed on the FULL panel once and then sliced, not refitted
    per half. That is correct here and worth stating because it looks wrong: the
    signal has no fitted parameters -- `window`, `top_k`, `direction` and `margin`
    are chosen by the sweep, not estimated from data -- so the only thing a
    per-half recomputation would change is how many warm-up bars the OOS half
    burns. Slicing after the fact keeps the OOS half fully invested from its first
    bar while still using no information from it.
    """
    weights = target_weights(panel.closes, window, top_k, direction, margin)
    cut = int(panel.n_bars * split)
    params = {"window": window, "top_k": top_k, "direction": direction, "margin": margin}

    # Each slice starts flat (`prev = zeros` inside `simulate`), so the first
    # out-of-sample bar re-enters the position carried across the split and books
    # one entry cost that a continuously-held path would not pay. Left in
    # deliberately -- it is uniform across every configuration and control, and it
    # errs toward charging too much rather than too little. The one place it is
    # not harmless: it inflates `oos_rotations` by one, so a configuration with
    # nine genuine rotations can clear MIN_OOS_ROTATIONS on the artifact.
    is_panel = slice_panel(panel, 0, cut)
    oos_panel = slice_panel(panel, cut, panel.n_bars)
    is_res = simulate(is_panel, weights[:cut], costs, "in_sample", params)
    oos_res = simulate(oos_panel, weights[cut:], costs, "out_of_sample", params)
    return is_res, oos_res


def block_returns(
    panel: Panel,
    window: int,
    top_k: int,
    direction: str,
    margin: float,
    costs: CostConfig | None = None,
    n_groups: int = 8,
) -> list[np.ndarray]:
    """Per-block net returns, for `pbo_cscv` and for a spread across regimes.

    Reuses `cpcv.make_groups` for the boundaries. `cpcv_evaluate` itself is not
    reusable here -- it takes single-asset arrays and calls `run_backtest`
    internally -- so this is the minimum re-implementation, not a parallel one.
    """
    weights = target_weights(panel.closes, window, top_k, direction, margin)
    out: list[np.ndarray] = []
    for start, end in make_groups(panel.n_bars, n_groups):
        sub = slice_panel(panel, start, end)
        if sub.n_bars < 3:
            continue
        res = simulate(sub, weights[start:end], costs, f"block_{start}", {})
        out.append(res.net_returns[1:])
    return out


def sweep(
    panel: Panel,
    costs: CostConfig | None = None,
    windows: Sequence[int] = SWEEP_WINDOWS,
    top_ks: Sequence[int] = SWEEP_TOP_K,
    directions: Sequence[str] = SWEEP_DIRECTIONS,
    margins: Sequence[float] = SWEEP_MARGINS,
    split: float = SPLIT,
) -> pd.DataFrame:
    """Every configuration, in-sample beside out-of-sample, with the count printed.

    The denominator is the point. `research/sweep.py`'s house rule is that a top
    row is uninterpretable without the number of configurations it won against,
    and the deflated Sharpe below consumes exactly that count.
    """
    rows: list[dict[str, Any]] = []
    for window, top_k, direction, margin in itertools.product(windows, top_ks, directions, margins):
        try:
            is_res, oos_res = walk_forward(panel, window, top_k, direction, margin, costs, split)
        except ValueError:
            continue
        rows.append(
            {
                "window": window,
                "top_k": top_k,
                "direction": direction,
                "margin": margin,
                "is_sharpe": is_res.sharpe(),
                "is_monthly_pct": is_res.monthly_pct(),
                "oos_sharpe": oos_res.sharpe(),
                "oos_monthly_pct": oos_res.monthly_pct(),
                "oos_gross_sharpe": oos_res.gross_sharpe(),
                "oos_rotations": oos_res.n_rotations,
                "oos_max_dd": oos_res.max_drawdown(),
                "decay_sharpe": is_res.sharpe() - oos_res.sharpe(),
                "rankable": oos_res.n_rotations >= MIN_OOS_ROTATIONS,
            }
        )
    return pd.DataFrame(rows)


def holding_attribution(
    panel: Panel, window: int, top_k: int, direction: str, margin: float, split: float = SPLIT
) -> pd.DataFrame:
    """Fraction of out-of-sample bars spent holding each asset.

    The decisive diagnostic for any rotation result, and the one that turns a
    headline Sharpe into an explanation. A selection rule that spends most of its
    time in the single asset that happened to run is not selecting; it is a
    momentum filter with extra steps, and its return belongs to that asset rather
    than to the rule. Compare each row against the same asset's standalone
    buy-and-hold on this slice before crediting the strategy with anything.
    """
    weights = target_weights(panel.closes, window, top_k, direction, margin)
    cut = int(panel.n_bars * split)
    oos_w = weights[cut:]
    invested = oos_w[np.any(oos_w != 0.0, axis=1)]
    if invested.size == 0:
        return pd.DataFrame([{"asset": a, "share_of_invested_bars": 0.0} for a in panel.assets])
    share = invested.sum(axis=0) / invested.shape[0]
    return pd.DataFrame(
        [{"asset": a, "share_of_invested_bars": float(s)} for a, s in zip(panel.assets, share)]
    ).sort_values("share_of_invested_bars", ascending=False)


def oos_bars_per_rotation(frame: pd.DataFrame, panel: Panel, split: float = SPLIT) -> float:
    """Average bars between rotations for the best out-of-sample row.

    Used to match the random control's turnover to the rule it controls for. A
    random control that trades at a different frequency measures the cost model,
    not the selection rule.
    """
    rankable = frame[frame["rankable"]]
    if rankable.empty:
        return 30.0
    best = rankable.sort_values("oos_sharpe", ascending=False).iloc[0]
    oos_bars = panel.n_bars - int(panel.n_bars * split)
    rotations = max(int(best["oos_rotations"]), 1)
    return oos_bars / rotations


def deflate(frame: pd.DataFrame, panel: Panel, split: float = SPLIT) -> dict[str, Any]:
    """Deflated Sharpe for the best out-of-sample row against the trial count.

    Uses the same machinery as the rest of the project so the number is
    comparable to `research/SWEEP-9COIN.md`'s funnel.
    """
    rankable = frame[frame["rankable"]]
    if rankable.empty:
        return {"insufficient": True, "reason": "no configuration cleared MIN_OOS_ROTATIONS"}

    best = rankable.sort_values("oos_sharpe", ascending=False).iloc[0]
    sharpes = rankable["oos_sharpe"].to_numpy(dtype=float)
    ppy = periods_per_year(panel.interval)
    n_obs = int(panel.n_bars * (1.0 - split))

    variance = float(trial_sharpe_variance(sharpes))
    n_trials = float(effective_trials(len(sharpes)))
    if n_trials < 2 or variance <= 0:
        return {"insufficient": True, "reason": f"n_trials={n_trials}, variance={variance}"}

    result = deflated_sharpe_ratio(
        sharpe=deannualise(float(best["oos_sharpe"]), ppy),
        n_obs=n_obs,
        n_trials=n_trials,
        trial_variance=variance / (ppy or 1.0),
    )
    return {
        "insufficient": False,
        "best_config": {k: best[k] for k in ("window", "top_k", "direction", "margin")},
        "best_oos_sharpe": float(best["oos_sharpe"]),
        "n_configs": int(len(frame)),
        "n_rankable": int(len(sharpes)),
        **result.to_dict(),
    }


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------


def _synthetic_panel(T: int = 400, N: int = 4, seed: int = 7) -> Panel:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.03, size=(T, N))
    closes = 100.0 * np.exp(np.cumsum(steps, axis=0))
    ts = np.arange(T, dtype=np.int64) * 86400 + 1_600_000_000
    return Panel(tuple(f"A{i}" for i in range(N)), ts, closes, "1d")


def self_test() -> int:
    """Gate the module. Every check is one the docstring makes a claim about."""
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  -- ' + detail if detail and not ok else ''}")
        if not ok:
            failures.append(name)

    panel = _synthetic_panel()

    # 1. Quote-convention guard. Not evidence -- see the module docstring.
    p = panel.closes[-1]
    chained = (p[0] / p[1]) * (p[1] / p[2])
    direct = p[0] / p[2]
    check(
        "cross_rate_identity (quote-convention guard, true by construction)",
        np.isclose(chained, direct, rtol=1e-12),
        f"{chained} vs {direct}",
    )

    # 2. No look-ahead. Corrupt everything after bar t; earlier weights must not move.
    t = 200
    full = target_weights(panel.closes, window=30, top_k=1)
    corrupted = panel.closes.copy()
    rng = np.random.default_rng(99)
    corrupted[t + 1 :] = corrupted[t + 1 :] * rng.uniform(2.0, 5.0, size=corrupted[t + 1 :].shape)
    partial = target_weights(corrupted, window=30, top_k=1)
    check(
        "no_lookahead (weights[:t+1] invariant to future data)",
        np.array_equal(full[: t + 1], partial[: t + 1]),
        f"first mismatch at {int(np.argmax(np.any(full[: t + 1] != partial[: t + 1], axis=1)))}",
    )

    # 3. Warm-up rows hold nothing rather than something arbitrary.
    check("warmup_is_flat", bool(np.all(full[:30] == 0.0)))

    # 4. Weights are a portfolio: each active row sums to 1.
    active = full[np.any(full != 0.0, axis=1)]
    check("weights_sum_to_one", bool(np.allclose(active.sum(axis=1), 1.0)))

    # 5. Costs are never zero when the strategy trades, and always reduce return.
    w = target_weights(panel.closes, window=30, top_k=1)
    res = simulate(panel, w, label="t")
    check("strategy_traded", res.n_rotations > 0, f"{res.n_rotations} rotations")
    check(
        "costs_reduce_return",
        float(np.prod(1 + res.net_returns)) < float(np.prod(1 + res.gross_returns)),
    )

    # 6. Zero-cost config reproduces the gross path -- proves the cost path is the
    #    ONLY difference between the two, so `gross` is a valid counterfactual.
    free = simulate(panel, w, costs=CostConfig(fee_bps=0.0, slippage_bps=0.0), label="free")
    check("zero_cost_equals_gross", bool(np.allclose(free.net_returns, free.gross_returns)))

    # 7. Higher costs never help.
    dear = simulate(panel, w, costs=CostConfig(fee_bps=50.0, slippage_bps=20.0), label="dear")
    check("cost_monotonic", dear.total_return() < res.total_return())

    # 8. Hysteresis cannot increase turnover.
    lo = simulate(panel, target_weights(panel.closes, 30, 1, "reversion", 0.0)).n_rotations
    hi = simulate(panel, target_weights(panel.closes, 30, 1, "reversion", 1.0)).n_rotations
    check("margin_reduces_turnover", hi <= lo, f"margin=0 -> {lo}, margin=1 -> {hi}")

    # 9. A one-asset panel's rotation IS buy-and-hold: no selection is possible.
    solo = Panel(("A0",), panel.timestamps, panel.closes[:, :1], "1d")
    solo_rot = simulate(solo, target_weights(solo.closes, 30, 1), label="solo")
    solo_hold = simulate(solo, control_weights(solo, "hold_A0", window=30), label="hold")
    check(
        "single_asset_rotation_is_buy_and_hold",
        np.allclose(solo_rot.equity, solo_hold.equity),
    )

    # 10. fill_delay shifts exposure and cannot silently improve the result by
    #     changing what is charged.
    delayed = simulate(panel, w, label="d", fill_delay=1)
    check("fill_delay_changes_path", not np.allclose(delayed.net_returns, res.net_returns))
    check("fill_delay_keeps_turnover", np.allclose(delayed.turnover, res.turnover))

    # 11. Row 0 has no prior bar, so its return must be zero rather than garbage.
    check("panel_returns_row0_zero", bool(np.all(panel.returns()[0] == 0.0)))

    # 11b. A missing or non-finite price must raise rather than rank as average.
    for bad_value in (np.nan, np.inf, 0.0, -1.0):
        broken = panel.closes.copy()
        broken[50, 0] = bad_value
        try:
            target_weights(broken, 30, 1)
            check(f"rejects_bad_price_{bad_value}", False, "no exception raised")
        except ValueError:
            check(f"rejects_bad_price_{bad_value}", True)

    # 12. Leverage accrues borrow fee and it is a cost, never a credit.
    lev = simulate(panel, w, label="lev", leverage=3.0)
    check("borrow_fee_is_a_cost", lev.borrow_cost_total > 0.0)

    # 13. The borrow accrual is controlled explicitly, not implied by leverage,
    #     so the cliff at leverage==1.0 can be turned off and inspected.
    lev_nofee = simulate(panel, w, label="nofee", leverage=3.0, accrue_borrow=False)
    check("borrow_is_explicitly_controllable", lev_nofee.borrow_cost_total == 0.0)
    check("borrow_reduces_return", lev.total_return() < lev_nofee.total_return())

    # 14. A ruined path is flagged, and its metrics stop at ruin rather than
    #     describing bars the account could not have traded.
    doomed_prices = panel.closes.copy()
    doomed_prices[100:] = doomed_prices[100:] * np.linspace(1.0, 0.01, doomed_prices[100:].shape[0])[:, None]
    doomed_panel = Panel(panel.assets, panel.timestamps, doomed_prices, "1d")
    doomed = simulate(
        doomed_panel, target_weights(doomed_prices, 30, 1), label="doomed", leverage=20.0
    )
    if doomed.ruined:
        check("ruin_truncates_metrics", doomed.live_returns.size <= doomed.ruin_index + 1)
        check("ruin_equity_stays_floored", bool(np.all(doomed.equity[doomed.ruin_index :] == 0.0)))
    else:
        check("ruin_path_constructed", False, "synthetic doom path did not ruin; check the fixture")

    # 15. Sharpe is scale-invariant when every cost term scales with leverage.
    #     Asserted rather than merely noted, because a future change that breaks
    #     it would mean a cost stopped scaling -- which is a real bug.
    a = simulate(panel, w, label="a", leverage=2.0, accrue_borrow=True)
    b = simulate(panel, w, label="b", leverage=4.0, accrue_borrow=True)
    if not (a.ruined or b.ruined):
        check("sharpe_scale_invariant_under_leverage", np.isclose(a.sharpe(), b.sharpe(), rtol=1e-9))

    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _print_frame(frame: pd.DataFrame, floatfmt: str = "%.4f") -> None:
    with pd.option_context("display.width", 200, "display.max_columns", 40, "display.float_format", lambda v: floatfmt % v):
        print(frame.to_string(index=False))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Numeraire-switching rotation across a coin panel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--self-test", action="store_true", help="run the gate and exit")
    ap.add_argument("--universes", action="store_true", help="print intersection lengths and exit")
    ap.add_argument("--turnover-table", action="store_true", help="print the cost arithmetic and exit")
    ap.add_argument("--demo-chain", action="store_true", help="measure chained vs direct routing")
    ap.add_argument("--sweep", action="store_true", help="run the configuration sweep")
    ap.add_argument(
        "--carry",
        action="store_true",
        help="borrow-fee sensitivity of the best config (a cost curve, NOT a carry strategy)",
    )
    ap.add_argument("--assets", default=",".join(PRIMARY_ASSETS))
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--leverage", type=float, default=1.0, help=">1 accrues the perp borrow fee")
    ap.add_argument("--fill-delay", type=int, default=0)
    ap.add_argument("--out", default=None, help="CSV filename written into research/results/")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.turnover_table:
        print("Cost drag by holding period (CostConfig defaults, 1d bars).")
        print("A rotation moves 2.0 of weight and pays two one-way legs.\n")
        _print_frame(turnover_table(interval=args.interval), "%.2f")
        return 0

    if args.universes:
        print("Longest intersection at each universe size. Rotation needs every")
        print("asset present at bar t, so the study length is the shortest member.\n")
        _print_frame(describe_universes(args.interval), "%.0f")
        print("\nExcluded by construction:")
        for asset, why in EXCLUDED_ASSETS.items():
            print(f"  {asset:<5} {why}")
        return 0

    assets = tuple(a.strip().upper() for a in args.assets.split(",") if a.strip())
    panel = load_panel(assets, args.interval)
    print(f"Panel: {panel.describe()}\n", file=sys.stderr)

    if args.demo_chain:
        print("Chained vs direct routing to the same terminal asset.")
        print("Gross quantities are identical by construction; only cost differs.\n")
        _print_frame(demo_chain(panel), "%.8f")
        return 0

    if args.carry:
        frame = sweep(panel, split=SPLIT)
        rankable = frame[frame["rankable"]]
        if rankable.empty:
            print(
                f"No configuration cleared MIN_OOS_ROTATIONS={MIN_OOS_ROTATIONS}, so there is "
                "no best row to measure leverage sensitivity on.",
                file=sys.stderr,
            )
            return 1
        best = rankable.sort_values("oos_sharpe", ascending=False).iloc[0]
        print("Borrow-fee sensitivity on the out-of-sample slice.")
        print("perps.py models a BORROW FEE (both sides pay, floored at zero),")
        print("NOT a funding rate that changes sign. This is a cost curve.\n")
        _print_frame(
            carry_table(
                panel,
                int(best["window"]),
                int(best["top_k"]),
                str(best["direction"]),
                float(best["margin"]),
            )
        )
        return 0

    if args.sweep:
        frame = sweep(panel, split=SPLIT)
        n = len(frame)
        rankable = frame[frame["rankable"]]
        print(f"{n} configurations evaluated; {len(rankable)} cleared "
              f"MIN_OOS_ROTATIONS={MIN_OOS_ROTATIONS}.\n")
        _print_frame(frame.sort_values("oos_sharpe", ascending=False).head(15))

        best_row = frame.sort_values("oos_sharpe", ascending=False).iloc[0]
        hold_bars = max(int(round(oos_bars_per_rotation(frame, panel))), 1)
        print(f"\n--- controls, SAME out-of-sample slice (last {1 - SPLIT:.0%}), "
              f"random matched at {hold_bars}-bar holds ---")
        controls = evaluate_controls(
            panel, split=SPLIT, match_hold_bars=hold_bars, match_top_k=int(best_row["top_k"])
        )
        _print_frame(controls[
            ["label", "bars", "rotations", "total_return", "monthly_pct", "sharpe", "max_drawdown"]
        ])
        print(f"\nbest sweep row for comparison: {dict(best_row[['window','top_k','direction','margin']])}"
              f" -> {best_row['oos_monthly_pct']:.4f}%/mo, sharpe {best_row['oos_sharpe']:.4f}")

        print("\n--- where the best row actually spent its out-of-sample time ---")
        _print_frame(
            holding_attribution(
                panel,
                int(best_row["window"]),
                int(best_row["top_k"]),
                str(best_row["direction"]),
                float(best_row["margin"]),
            )
        )

        print("\n--- deflated sharpe on the best out-of-sample row ---")
        print(json.dumps(deflate(frame, panel), indent=2, default=float))

        print("\n--- probability of backtest overfitting (CSCV) ---")
        blocks: dict[str, list[np.ndarray]] = {}
        for _, row in frame.iterrows():
            key = f"w{int(row['window'])}_k{int(row['top_k'])}_{row['direction']}_m{row['margin']}"
            blocks[key] = block_returns(
                panel, int(row["window"]), int(row["top_k"]), str(row["direction"]), float(row["margin"])
            )
        print(json.dumps(pbo_cscv(blocks), indent=2, default=float))

        if args.out:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = OUT_DIR / Path(args.out).name
            frame.to_csv(path, index=False)
            print(f"\nwrote {path}", file=sys.stderr)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
