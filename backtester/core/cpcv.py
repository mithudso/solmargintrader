"""Combinatorial purged cross-validation, adapted honestly for fixed-parameter strategies.

## What this borrows from Lopez de Prado, and what it does not

Classic CPCV (Lopez de Prado 2018, Ch. 12) targets ML pipelines: you FIT a model
on training folds and score held-out folds. *Purging* drops training
observations whose label windows overlap the test fold; *embargo* drops the
observations immediately following it. Both exist to stop test-period
information leaking into fitted parameters.

**The strategies here fit nothing.** Their parameters (MA 20/50, RSI 14, ...) are
fixed a priori, so there is no training set, and purge/embargo are **degenerate** --
there are no fitted parameters to protect. Claiming otherwise would borrow the
vocabulary without the mechanism.

What CPCV *does* buy, and the reason this module exists:

1. **A distribution of out-of-sample paths instead of one arbitrary split.** A
   single 70/30 split on SOL lands almost exactly on the price top, so one
   number conflates "strategy quality" with "which regime landed in the test
   set". C(N,k) paths sample many regime mixes.
2. **Probability of Backtest Overfitting.** With many splits the CSCV procedure
   of Bailey et al. (2014) becomes computable: how often does the configuration
   that looks best in-sample rank below median out-of-sample?

The leakage vector that *is* real for fixed-parameter strategies is **warm-up**:
a block whose indicators warm up inside the block wastes its first `warmup` bars,
while warming from the bars immediately preceding the block uses genuine past
history and is not look-ahead. `evaluate_block` does the latter and measures only
the in-block region. That substitution is the honest analogue of purging here,
and it is the only one claimed.

Path returns are built by **concatenating per-bar returns** from the selected
blocks in chronological order, because blocks are generally non-adjacent and
equity *levels* cannot be spliced across a gap.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .engine import EngineConfig, run_backtest
from .metrics import simple_returns
from .types import periods_per_year


@dataclass
class BlockResult:
    """One contiguous evaluation block."""

    index: int
    start: int
    end: int
    returns: np.ndarray
    trades: int
    usable: bool
    reason: str = ""


@dataclass
class CpcvResult:
    """Distribution of out-of-sample paths for one configuration."""

    label: str
    n_groups: int
    k_test: int
    n_paths: int
    path_sharpes: np.ndarray
    path_returns: np.ndarray
    block_sharpes: np.ndarray
    total_trades: int
    usable_blocks: int
    insufficient: bool = False
    reason: str = ""
    blocks: list[BlockResult] = field(default_factory=list)

    @property
    def median_sharpe(self) -> float:
        """Median path Sharpe -- the headline robust statistic."""
        return float(np.median(self.path_sharpes)) if self.path_sharpes.size else float("nan")

    @property
    def q1_sharpe(self) -> float:
        """25th percentile: the conservative read Lopez de Prado recommends."""
        return float(np.quantile(self.path_sharpes, 0.25)) if self.path_sharpes.size else float("nan")

    @property
    def q3_sharpe(self) -> float:
        """75th percentile of path Sharpe."""
        return float(np.quantile(self.path_sharpes, 0.75)) if self.path_sharpes.size else float("nan")

    @property
    def frac_positive(self) -> float:
        """Fraction of paths with positive Sharpe -- the stability measure."""
        return float((self.path_sharpes > 0).mean()) if self.path_sharpes.size else float("nan")

    @property
    def spread(self) -> float:
        """Interquartile spread. Large spread means the result is split-dependent."""
        return self.q3_sharpe - self.q1_sharpe

    @property
    def median_return(self) -> float:
        """Median compounded path return."""
        return float(np.median(self.path_returns)) if self.path_returns.size else float("nan")


def make_groups(n_bars: int, n_groups: int) -> list[tuple[int, int]]:
    """Partition [0, n_bars) into `n_groups` contiguous (start, end) blocks.

    Remainder bars go to the earliest groups so sizes differ by at most one;
    leaving a short tail group would make the final path systematically noisier
    than the rest.
    """
    if n_groups < 2:
        raise ValueError("n_groups must be >= 2")
    if n_bars < n_groups:
        raise ValueError(f"cannot split {n_bars} bars into {n_groups} groups")
    base, extra = divmod(n_bars, n_groups)
    bounds: list[tuple[int, int]] = []
    cursor = 0
    for g in range(n_groups):
        size = base + (1 if g < extra else 0)
        bounds.append((cursor, cursor + size))
        cursor += size
    return bounds


def evaluate_block(
    make_strategy: Callable[[], object],
    arrays: dict[str, np.ndarray],
    start: int,
    end: int,
    cfg: EngineConfig,
) -> BlockResult:
    """Per-bar returns for bars [start, end), warmed up from preceding bars.

    A fresh strategy instance is built so no position or `_holding` state leaks
    across blocks. Warm-up comes from the bars immediately BEFORE `start`
    (legitimate past history, not look-ahead); if too few precede the block, it
    is marked unusable rather than run on a partially-defined indicator, which
    would silently mix a warm and a cold signal in one measurement.
    """
    strat = make_strategy()
    warm = int(strat.warmup_bars())
    lead = start - warm
    if lead < 0:
        return BlockResult(
            index=-1, start=start, end=end, returns=np.zeros(0), trades=0,
            usable=False,
            reason=f"needs {warm} warm-up bars, only {start} precede this block",
        )
    if end - start < 3:
        return BlockResult(
            index=-1, start=start, end=end, returns=np.zeros(0), trades=0,
            usable=False, reason="block shorter than 3 bars",
        )

    sub = {key: v[lead:end] for key, v in arrays.items()}
    res = run_backtest(make_strategy(), sub, cfg)
    equity = res.equity[warm:]
    if equity.size < 3:
        return BlockResult(
            index=-1, start=start, end=end, returns=np.zeros(0), trades=0,
            usable=False, reason="fewer than 3 measurable bars after warm-up",
        )
    trades = sum(1 for t in res.trades if t.bar_index >= warm)
    return BlockResult(
        index=-1, start=start, end=end,
        returns=simple_returns(equity), trades=trades, usable=True,
    )


def _sharpe(r: np.ndarray, ppy: float) -> float:
    """Annualised Sharpe of a (possibly concatenated) return series."""
    if r.size < 2:
        return float("nan")
    sd = float(np.std(r, ddof=1))
    if sd <= 1e-15:
        return 0.0
    return float(np.mean(r) / sd * np.sqrt(ppy))


def cpcv_evaluate(
    label: str,
    make_strategy: Callable[[], object],
    arrays: dict[str, np.ndarray],
    cfg: EngineConfig,
    n_groups: int = 8,
    k_test: int = 2,
    min_total_trades: int = 10,
) -> CpcvResult:
    """Evaluate one configuration across all C(n_groups, k_test) paths.

    Each block is run ONCE and cached; a path is the concatenation of its
    blocks' per-bar returns. So the cost is O(n_groups) engine runs rather than
    O(C(n_groups, k_test)).
    """
    n = len(arrays["close"])
    ppy = periods_per_year(cfg.interval)

    try:
        bounds = make_groups(n, n_groups)
    except ValueError as exc:
        return CpcvResult(
            label=label, n_groups=n_groups, k_test=k_test, n_paths=0,
            path_sharpes=np.zeros(0), path_returns=np.zeros(0),
            block_sharpes=np.zeros(0), total_trades=0, usable_blocks=0,
            insufficient=True, reason=str(exc),
        )

    blocks: list[BlockResult] = []
    for i, (s, e) in enumerate(bounds):
        b = evaluate_block(make_strategy, arrays, s, e, cfg)
        b.index = i
        blocks.append(b)

    usable = [b for b in blocks if b.usable]
    if len(usable) < k_test:
        first_reason = next((b.reason for b in blocks if not b.usable), "unknown")
        return CpcvResult(
            label=label, n_groups=n_groups, k_test=k_test, n_paths=0,
            path_sharpes=np.zeros(0), path_returns=np.zeros(0),
            block_sharpes=np.zeros(0),
            total_trades=sum(b.trades for b in blocks),
            usable_blocks=len(usable), insufficient=True,
            reason=f"only {len(usable)}/{n_groups} blocks usable ({first_reason})",
            blocks=blocks,
        )

    block_sharpes = np.array([_sharpe(b.returns, ppy) for b in usable], dtype="float64")

    path_sharpes: list[float] = []
    path_returns: list[float] = []
    for combo in itertools.combinations(range(len(usable)), k_test):
        cat = np.concatenate([usable[i].returns for i in sorted(combo)])
        path_sharpes.append(_sharpe(cat, ppy))
        path_returns.append(float(np.prod(1.0 + cat) - 1.0))

    total_trades = sum(b.trades for b in usable)
    return CpcvResult(
        label=label, n_groups=n_groups, k_test=k_test, n_paths=len(path_sharpes),
        path_sharpes=np.array(path_sharpes, dtype="float64"),
        path_returns=np.array(path_returns, dtype="float64"),
        block_sharpes=block_sharpes, total_trades=total_trades,
        usable_blocks=len(usable),
        insufficient=total_trades < min_total_trades,
        reason=(
            f"only {total_trades} trades across all blocks (floor {min_total_trades})"
            if total_trades < min_total_trades else ""
        ),
        blocks=blocks,
    )


def pbo_cscv(
    block_returns: dict[str, list[np.ndarray]], max_splits: int = 200
) -> dict[str, float]:
    """Probability of Backtest Overfitting via CSCV (Bailey et al. 2014).

    For every split of the blocks into a train half and a test half: pick the
    configuration with the best TRAIN Sharpe, then find its percentile rank
    among all configurations on TEST. **PBO is the fraction of splits where the
    train-winner lands below the median out-of-sample.**

    Interpretation: PBO near 0 means in-sample winners generalise. PBO at or
    above 0.5 means selecting on in-sample performance is no better than
    choosing at random, i.e. the "best" backtest is an overfit artifact.

    `max_splits` caps the enumeration -- C(16,8) is 12,870 and the estimate is
    stable long before that. The cap SAMPLES EVENLY across the combination space
    rather than taking the first N: `itertools.combinations` emits in
    lexicographic order, so the first N all share low-index blocks and would
    systematically under-represent the later ones. Sampling is by fixed stride,
    so the result is still fully deterministic and reproducible.
    """
    labels = list(block_returns)
    if len(labels) < 2:
        return {"pbo": float("nan"), "n_splits": 0.0, "n_configs": float(len(labels))}
    n_blocks = len(block_returns[labels[0]])
    if any(len(block_returns[l]) != n_blocks for l in labels):
        raise ValueError("all configurations must expose the same block count")
    if n_blocks < 4:
        return {"pbo": float("nan"), "n_splits": 0.0, "n_configs": float(len(labels))}

    half = n_blocks // 2

    def raw_sharpe(parts: list[np.ndarray]) -> float:
        """Un-annualised Sharpe; annualisation cancels in a ranking."""
        cat = np.concatenate(parts) if parts else np.zeros(0)
        if cat.size < 2:
            return float("nan")
        sd = float(np.std(cat, ddof=1))
        return 0.0 if sd <= 1e-15 else float(np.mean(cat) / sd)

    # Even sampling: walk the whole space but keep every `stride`-th combination,
    # so a capped run still spans early and late block groupings.
    total_splits = math.comb(n_blocks, half)
    stride = max(1, total_splits // max_splits) if max_splits > 0 else 1

    below_median = 0
    splits = 0
    for position, train_idx in enumerate(itertools.combinations(range(n_blocks), half)):
        if position % stride:
            continue
        if splits >= max_splits:
            break
        test_idx = [i for i in range(n_blocks) if i not in train_idx]
        train_s = {l: raw_sharpe([block_returns[l][i] for i in train_idx]) for l in labels}
        test_s = {l: raw_sharpe([block_returns[l][i] for i in test_idx]) for l in labels}
        valid = [l for l in labels if np.isfinite(train_s[l]) and np.isfinite(test_s[l])]
        if len(valid) < 2:
            continue
        winner = max(valid, key=lambda l: train_s[l])
        ranked = sorted(valid, key=lambda l: test_s[l])
        rank = ranked.index(winner) / (len(ranked) - 1)
        if rank < 0.5:
            below_median += 1
        splits += 1

    return {
        "pbo": (below_median / splits) if splits else float("nan"),
        "n_splits": float(splits),
        "n_configs": float(len(labels)),
    }
