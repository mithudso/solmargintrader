"""Put idle wallet coins to work, but only when a pool is worth it.

A pool qualifies only when **both** independent estimates clear `min_net_apr`:
  * the model:    income - LVR - rebalance cost at the optimized width (metrics.expected_net_apr);
  * the replay:   the best width on the pool's actual recent price path vs holding the pair
                  (metrics.backtest_net_apr).
It must also pass the edge-ratio, confidence, TVL and token allow-list filters. Its score is the
smaller of the two APRs.

When the best candidates are close (within `compare_margin` of the best score), the allocator does not
guess. It splits the capital into a side-by-side experiment of up to `max_arms` positions and tracks
each one's realized P&L in the ledger. After `experiment_days`, an arm that trails the winner by more
than `graduate_margin_apr` is closed. Its coins return to the wallet and become idle for the next
allocation.

`plan_allocation` and `plan_graduation` are pure, for testing. `Allocator.run` executes the plans.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from .config import AllocatorConfig
from .ledger import SlotPnl
from .metrics import KNOWN_TOKENS

CONF_RANK = {"high": 0, "medium": 1, "low": 2}
# A backtest on less history than this is "no replay" (metrics.backtest_best reports days == 0 for that), not 0% APR.
MIN_BACKTEST_DAYS = 0.9
# A pool is scored at one deposit size (gas is a fixed cost, so APR depends on it). A position much smaller than
# that size would earn less than the score says.
ARM_SIZE_FLOOR = 0.8


@dataclass
class Candidate:
    pool: str
    pair: str
    token0: str
    token1: str
    score_apr: float
    model_apr: float
    backtest_apr: float
    best_mode: str
    half_width_pct: float
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Arm:
    candidate: Candidate
    usd: float


@dataclass
class AllocationPlan:
    arms: list[Arm]
    experiment: bool
    reason: str


def _at_least(x: Any, floor: float) -> bool:
    """x >= floor, False for NaN, inf, None and non-numbers (a plain `x < floor` test passes NaN)."""
    return isinstance(x, int | float) and math.isfinite(x) and x >= floor


def _sym_ok(addr: str, cfg: AllocatorConfig) -> bool:
    sym = KNOWN_TOKENS.get(addr.lower())
    return sym is not None and sym in cfg.allowed_tokens and sym not in cfg.exclude_tokens


def qualify(pools: list[dict[str, Any]], cfg: AllocatorConfig) -> tuple[list[Candidate], list[str]]:
    """Filter scout rows to deployable candidates, best first. Also returns why the best rejects failed."""
    out: list[Candidate] = []
    rejects: list[str] = []
    for p in pools:
        why = []
        if not (_sym_ok(p["token0"], cfg) and _sym_ok(p["token1"], cfg)):
            why.append("token not allowed")
        if CONF_RANK.get(p.get("confidence", "low"), 2) > CONF_RANK[cfg.min_confidence]:
            why.append(f"confidence {p.get('confidence')}")
        if not _at_least(p.get("tvl_usd", 0), cfg.min_tvl_usd):
            why.append(f"TVL ${p.get('tvl_usd', 0):,.0f}")
        if not _at_least(p.get("edge_ratio", 0), cfg.min_edge_ratio):
            why.append(f"edge {p.get('edge_ratio', 0)}")
        # The replay at the width that would be deployed; older scout files only have the best-of-grid replay.
        model, bt = p.get("expected_net_apr", -1e9), p.get("backtest_deploy_apr", p.get("backtest_net_apr", -1e9))
        if not _at_least(model, cfg.min_net_apr):
            why.append(f"model {model:+.1f}%" if isinstance(model, int | float) else "model n/a")
            model = -1e9
        if not _at_least(bt, cfg.min_net_apr):
            why.append(f"backtest {bt:+.1f}%" if isinstance(bt, int | float) else "backtest n/a")
            bt = -1e9
        if not _at_least(p.get("backtest_days", 0), MIN_BACKTEST_DAYS):
            why.append("no price history to replay")
        if why:
            rejects.append(f"{p.get('pair')} CL{p.get('tick_spacing')}: " + ", ".join(why))
            continue
        out.append(
            Candidate(
                pool=p["pool"],
                pair=p["pair"],
                token0=p["token0"],
                token1=p["token1"],
                score_apr=min(model, bt),
                model_apr=model,
                backtest_apr=bt,
                best_mode=p.get("best_mode", "fees"),
                half_width_pct=p.get("best_half_width_pct", 1.0),
                raw=p,
            )
        )
    out.sort(key=lambda c: -c.score_apr)
    return out, rejects


def plan_allocation(
    pools: list[dict[str, Any]],
    idle_usd: float,
    deployed_usd: float,
    cfg: AllocatorConfig,
    held_pools: set[str] | None = None,
    scored_usd: float | None = None,
) -> AllocationPlan:
    """Decide where idle capital goes. `held_pools` are pools already holding a position (skipped).

    `scored_usd` is the deposit size the scout scored the pools at. Positions are not made much smaller than
    that: the arm count shrinks first, and with it the budget per arm grows.
    """
    budget = min(idle_usd, max(0.0, cfg.max_total_deployed_usd - deployed_usd))
    if not budget >= cfg.min_position_usd:  # also true for NaN
        return AllocationPlan([], False, f"deployable ${budget:.2f} < minimum position ${cfg.min_position_usd:.2f}")
    cands, rejects = qualify(pools, cfg)
    cands = [c for c in cands if c.pool.lower() not in {h.lower() for h in (held_pools or set())}]
    if not cands:
        top = "; ".join(rejects[:3]) if rejects else "no scout data"
        return AllocationPlan(
            [], False, f"no pool worth it (min {cfg.min_net_apr}% on model AND backtest). Best: {top}"
        )
    best = cands[0]
    close = [c for c in cands if c.score_apr >= best.score_apr * (1 - cfg.compare_margin)][: cfg.max_arms]
    k = max(1, min(len(close), int(budget // cfg.min_position_usd)))
    floor = ARM_SIZE_FLOOR * scored_usd if isinstance(scored_usd, int | float) and math.isfinite(scored_usd) else 0.0
    per = min(budget / k, cfg.max_position_usd)
    while k > 1 and per < floor:
        k -= 1
        per = min(budget / k, cfg.max_position_usd)
    if per < floor:
        return AllocationPlan(
            [], False, f"a position of ${per:.2f} is smaller than the ${scored_usd:,.2f} the pools were scored at"
        )
    arms = [Arm(c, per) for c in close[:k]]
    if len(arms) == 1:
        return AllocationPlan(
            arms,
            False,
            f"{best.pair}: score {best.score_apr:+.1f}% (model {best.model_apr:+.1f}%, "
            f"backtest {best.backtest_apr:+.1f}%)",
        )
    names = ", ".join(f"{a.candidate.pair} {a.candidate.score_apr:+.1f}%" for a in arms)
    return AllocationPlan(arms, True, f"candidates within {cfg.compare_margin:.0%}: side-by-side test of {names}")


def plan_graduation(
    experiment: dict[str, Any], arms: list[SlotPnl], cfg: AllocatorConfig, now: float | None = None
) -> tuple[str | None, list[str]]:
    """(winner slot, slots to close) for a running experiment; (None, []) while it is too early or too close."""
    t = now or time.time()
    if experiment.get("status") != "running" or t - experiment["started_at"] < cfg.experiment_days * 86400:
        return None, []
    live = [a for a in arms if a.closed_at is None]
    if len(live) < 2:
        return (live[0].slot if live else None), []
    ranked = sorted(live, key=lambda a: -a.apr_realized)
    winner = ranked[0]
    losers = [a.slot for a in ranked[1:] if winner.apr_realized - a.apr_realized >= cfg.graduate_margin_apr]
    return winner.slot, losers


def gas_topup_needed(eth_balance: float, weth_balance: float, cfg: AllocatorConfig) -> float:
    """WETH to unwrap to restore the native-ETH gas reserve (0 when not needed or not possible)."""
    if eth_balance >= cfg.gas_reserve_eth:
        return 0.0
    want = max(cfg.unwrap_chunk_eth, cfg.gas_reserve_eth - eth_balance)
    return min(want, weth_balance)
