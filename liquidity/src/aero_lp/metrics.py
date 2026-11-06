"""Every measure of a pool's likely profit or loss for a concentrated-liquidity deposit.

Income (what the deposit earns while in range), measured, not quoted:
  * fee income  - change in feeGrowthGlobal over the last day. CLPool.calculateFees credits it per
                  unit of *unstaked* in-range liquidity, net of the unstaked fee, so it already
                  reflects dynamic fees, router discounts and MEV capture.
  * AERO income - change in LeafVoter.projectedCumulativeRewardShare(gauge) over the last day,
                  shared by in-range *staked* liquidity.
Cost of being in the pool:
  * LVR         - loss-versus-rebalancing, sigma^2 / (8 * (1 - e^(-w/2))) of value per day for a
                  +/-w range, with sigma the daily vol of the pair's price ratio.
  * rebalancing - gas + swap fee + impact per rebalance, times sigma^2 / w^2 rebalances per day.
Context and risk:
  * TVL, 24h volume, turnover (volume / TVL), staked share, current dynamic fee, gauge status,
    unstaked-fee cut, token allow-list membership, history length behind each number.
Derived:
  * edge_ratio            - income / LVR. Both scale with concentration, so the ratio barely depends
                            on width; below 1 no width is profitable for a passive range.
  * expected_net_apr      - best width's income - LVR - rebalance cost, for the actual deposit size.
  * break_even_deposit    - smallest deposit whose income covers the rebalance costs at that width.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from . import addresses, backtest
from .chain import ZERO, AeroChain, PoolState, realized_vol_daily
from .executor import gas_cost_usd
from .market import (
    MarketData,
    PoolEconomics,
    earn_usd_per_day,
    fee_usd_per_liquidity_per_day,
    liquidity_for_usd,
    vol_from_closes,
)
from .strategy import StrategyConfig, best_width, lvr_fraction_per_day, rebalances_per_day, score_widths, target_range

REF_HALF_WIDTH = math.log1p(0.10)  # +/-10%: where the *_apr_ref figures are quoted
NO_DATA = -1e9  # stands in for a number that could not be computed (see PoolMetrics.to_json)

# Base tokens treated as known/liquid. Anything else is flagged, and the allocator ignores it by default.
KNOWN_TOKENS = {
    "0x4200000000000000000000000000000000000006": "WETH",
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": "USDbC",
    "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2": "USDT",
    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb": "DAI",
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf": "cbBTC",
    "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452": "wstETH",
    "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22": "cbETH",
    "0x04c0599ae5a44757c0af6f9ec3b93da8976c150a": "weETH",
    "0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c": "rETH",
    "0x3f5bf3edac59d650d8fdf9657a71f2f904a3a4ee": "AERO",
    "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42": "EURC",
}


@dataclass
class PoolMetrics:
    pool: str
    pair: str
    token0: str
    token1: str
    tick_spacing: int
    fee_pct: float
    tvl_usd: float
    volume_24h_usd: float
    turnover: float
    sigma_daily_pct: float | None
    sigma_source: str
    fee_apr_ref: float
    aero_apr_ref: float
    lvr_apr_ref: float
    edge_ratio: float
    best_mode: str
    best_half_width_pct: float
    expected_net_apr: float
    rebalances_per_week: float
    cost_per_rebalance_usd: float
    break_even_deposit_usd: float
    staked_share: float
    gauge_active: bool
    confidence: str
    flags: list[str] = field(default_factory=list)
    history_days: float = 0.0
    backtest_net_apr: float = 0.0  # best width replayed on the pool's actual price path, vs holding the pair
    backtest_half_width_pct: float = 0.0
    backtest_days: float = 0.0
    # Replay at the half-width that would actually be deployed (best_half_width_pct): what the allocator gates on.
    # backtest_net_apr is the best of a width grid and can come from a different width.
    backtest_deploy_apr: float = 0.0

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, float):
                # NaN / inf are not valid JSON (soltui's parser would reject the whole file). -1e9 is an obvious
                # "no data" value that fails every minimum the allocator checks.
                d[k] = round(v, 6) if math.isfinite(v) else NO_DATA
        return d


def pool_economics(chain: AeroChain, market: MarketData, pool: PoolState) -> tuple[PoolEconomics, dict[str, Any]]:
    """Build the earnings inputs for `pool` plus context (prices, TVL, volume, history length)."""
    t0, t1 = pool.token0, pool.token1
    prices = market.token_prices_usd([t0.address, t1.address, addresses.AERO_TOKEN, addresses.WETH])
    try:
        info = market.pool_info(pool.address)
    except Exception:  # noqa: BLE001 - GeckoTerminal is context, not a gate
        info = {"volume_24h_usd": 0.0, "reserve_usd": 0.0}
    econ = PoolEconomics(
        volume_usd_per_day=info.get("volume_24h_usd", 0.0),
        fee=pool.fee,
        unstaked_fee_share=pool.unstaked_fee_pips / 1e6,
        aero_per_day=chain.gauge_aero_per_day(pool.gauge, pool.block) if pool.gauge != ZERO else 0.0,
        aero_usd=prices.get(addresses.AERO_TOKEN.lower(), 0.0),
        active_liquidity=pool.liquidity,
        staked_liquidity=pool.staked_liquidity,
        price0_usd=prices.get(t0.address.lower(), 0.0),
        price1_usd=prices.get(t1.address.lower(), 0.0),
        dec0=t0.decimals,
        dec1=t1.decimals,
    )
    try:
        d0, d1, days = chain.fee_growth_delta(pool.address, pool.block)
    except Exception:  # noqa: BLE001 - fall back to volume x current fee
        d0 = d1 = 0
        days = 0.0
    if days > 0:
        econ = dataclasses.replace(econ, fee_usd_per_l_day=fee_usd_per_liquidity_per_day(d0, d1, days, econ))
    ctx = {
        "prices": prices,
        "eth_usd": prices.get(addresses.WETH.lower(), 0.0),
        "tvl_usd": info.get("reserve_usd", 0.0),
        "volume_24h_usd": info.get("volume_24h_usd", 0.0),
        "fee_history_days": days,
    }
    return econ, ctx


def pool_sigma(chain: AeroChain, market: MarketData, pool_address: str) -> tuple[float | None, str, float, list[float]]:
    """Daily vol of the pair's price ratio, its source, days of history, and the hourly closes used."""
    try:
        closes = market.hourly_closes(pool_address, 168)
        s = vol_from_closes(closes)
        if s:
            return s, f"geckoterminal {len(closes)}h hourly", len(closes) / 24, closes
    except Exception:  # noqa: BLE001
        pass
    ticks = chain.twap_tick_series(pool_address, hours=12, step_s=600)
    s = realized_vol_daily(ticks, step_s=600)
    return (s, "onchain 10-min TWAP", len(ticks) / 144, []) if s else (None, "none", 0.0, [])


BACKTEST_WIDTHS_PCT = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0)


def backtest_best(
    closes: list[float],
    yield_fn: Any,
    deposit_usd: float,
    gas_usd: float,
    pool_fee: float,
    tick_spacing: int,
    cfg: StrategyConfig,
) -> tuple[float, float, float]:
    """Replay the pool's actual hourly price path at a grid of widths (snapped to the tick spacing).

    Returns (best net APR % vs holding the pair, its half-width %, days replayed). Unlike the LVR
    formula, this sees mean reversion: a pegged pair that wobbles inside the range and comes back
    costs nothing here, while the formula charges every wobble as informed flow.

    Fewer than 24 closes or a zero deposit return (0, 0, 0): `days == 0` is how callers tell "no replay"
    from "a replay that earned 0%". A replay whose every width gives NaN or inf also reports no replay.
    """
    if len(closes) < 24 or not deposit_usd > 0:
        return 0.0, 0.0, 0.0
    days = (len(closes) - 1) / 24
    min_w = tick_spacing * math.log(1.0001)
    best = (-math.inf, 0.0)
    for pct in BACKTEST_WIDTHS_PCT:
        hw = max(math.log1p(pct / 100), min_w)
        r = backtest.run(closes, hw, yield_fn, start_value=deposit_usd, gas_cost=gas_usd, pool_fee=pool_fee, cfg=cfg)
        apr = r.pnl_vs_hodl / deposit_usd * 365 / days * 100
        if math.isfinite(apr) and apr > best[0]:
            best = (apr, (math.exp(hw) - 1) * 100)
    if not math.isfinite(best[0]):
        return 0.0, 0.0, 0.0
    return best[0], best[1], days


def backtest_at_width(
    closes: list[float],
    yield_fn: Any,
    deposit_usd: float,
    gas_usd: float,
    pool_fee: float,
    tick_spacing: int,
    cfg: StrategyConfig,
    half_width: float,
) -> float:
    """Net APR % vs holding when the replay uses exactly `half_width` (log). 0 without a replay (no data),
    NO_DATA when the result is not a number."""
    if len(closes) < 24 or not deposit_usd > 0:
        return 0.0
    hw = max(half_width, tick_spacing * math.log(1.0001))
    r = backtest.run(closes, hw, yield_fn, start_value=deposit_usd, gas_cost=gas_usd, pool_fee=pool_fee, cfg=cfg)
    apr = r.pnl_vs_hodl / deposit_usd * 365 / ((len(closes) - 1) / 24) * 100
    return apr if math.isfinite(apr) else NO_DATA


def evaluate_pool(
    chain: AeroChain,
    market: MarketData,
    pool_address: str,
    deposit_usd: float,
    cfg: StrategyConfig | None = None,
    gas_units: int = 2_700_000,
    l1_fee_usd: float = 0.005,
    impact_bps: float = 5.0,
) -> PoolMetrics:
    cfg = cfg or StrategyConfig()
    pool = chain.pool_state(pool_address)
    econ, ctx = pool_economics(chain, market, pool)
    sigma, sigma_src, hist_days, closes = pool_sigma(chain, market, pool.address)
    flags: list[str] = []

    def yield_curve(staked: bool):
        def f(w: float) -> float:
            if deposit_usd <= 0 or (staked and not pool.gauge_alive):
                return 0.0
            r = target_range(pool.tick, pool.tick_spacing, w)
            liq = liquidity_for_usd(deposit_usd, pool.sqrt_price_x96, r.tick_lower, r.tick_upper, econ)
            return earn_usd_per_day(liq, staked, True, econ, already_counted=False) / deposit_usd

        return f

    gas_usd = gas_cost_usd(gas_units, chain.gas_price_wei(), ctx["eth_usd"], l1_fee_usd)
    cost_per_rebalance = gas_usd + 0.5 * deposit_usd * (pool.fee + impact_bps / 1e4)
    cost_frac = cost_per_rebalance / deposit_usd if deposit_usd > 0 else 1.0

    fee_ref = yield_curve(False)(REF_HALF_WIDTH)
    aero_ref = yield_curve(True)(REF_HALF_WIDTH)
    lvr_ref = lvr_fraction_per_day(REF_HALF_WIDTH, sigma)
    income_ref = max(fee_ref, aero_ref)
    edge = income_ref / lvr_ref if lvr_ref > 0 else (math.inf if income_ref > 0 else 0.0)

    best = {}
    for mode, staked in (("aero", True), ("fees", False)):
        best[mode] = best_width(score_widths(yield_curve(staked), sigma, cost_frac, cfg))
    mode = "aero" if best["aero"].net_frac_day >= best["fees"].net_frac_day and pool.gauge_alive else "fees"
    chosen = best[mode]
    rb_day = rebalances_per_day(chosen.half_width, sigma)
    # Break-even deposit: income/$ at that width covers gas (the size-dependent part of the cost).
    inc_day = chosen.yield_frac_day - chosen.lvr_frac_day - rb_day * 0.5 * (pool.fee + impact_bps / 1e4)
    break_even = (rb_day * gas_usd / inc_day) if inc_day > 0 else math.inf

    bt_apr, bt_w, bt_days = backtest_best(
        closes, yield_curve(mode == "aero"), deposit_usd, gas_usd, pool.fee, pool.tick_spacing, cfg
    )
    bt_deploy = backtest_at_width(
        closes, yield_curve(mode == "aero"), deposit_usd, gas_usd, pool.fee, pool.tick_spacing, cfg, chosen.half_width
    )
    tvl = ctx["tvl_usd"]
    vol = ctx["volume_24h_usd"]
    staked_share = pool.staked_liquidity / pool.liquidity if pool.liquidity else 0.0
    for t in (pool.token0, pool.token1):
        if t.address.lower() not in KNOWN_TOKENS:
            flags.append(f"unlisted token {t.symbol}")
    if tvl < 50_000:
        flags.append("TVL < $50k")
    if not pool.gauge_alive:
        flags.append("gauge inactive (no AERO)")
    if ctx["fee_history_days"] < 1:
        flags.append("fee history < 1 day")
    if hist_days < 2:
        flags.append("volatility history < 2 days")
    if tvl > 0 and vol / tvl > 50:
        flags.append("turnover > 50x/day")
    if edge < 1:
        flags.append("income below LVR at every width")
    if not ctx["eth_usd"]:
        flags.append("ETH price unavailable: gas cost understated")
    if not (econ.price0_usd and econ.price1_usd):
        flags.append("missing USD price for a pool token")
    net_apr = chosen.net_frac_day * 36500
    if not math.isfinite(net_apr):
        net_apr = NO_DATA
        flags.append("net APR not computable")
    confidence = "high"
    if hist_days < 2 or ctx["fee_history_days"] < 1 or tvl < 50_000:
        confidence = "medium"
    # Without the ETH price the gas leg of every cost is ~0, and without a token price every USD figure is wrong:
    # either would let a pool look better than it is.
    if (
        sigma is None
        or any(f.startswith("unlisted") for f in flags)
        or tvl < 10_000
        or not ctx["eth_usd"]
        or not (econ.price0_usd and econ.price1_usd)
    ):
        confidence = "low"

    return PoolMetrics(
        pool=pool.address,
        pair=f"{pool.token0.symbol}/{pool.token1.symbol}",
        token0=pool.token0.address,
        token1=pool.token1.address,
        tick_spacing=pool.tick_spacing,
        fee_pct=pool.fee * 100,
        tvl_usd=tvl,
        volume_24h_usd=vol,
        turnover=vol / tvl if tvl > 0 else 0.0,
        sigma_daily_pct=sigma * 100 if sigma else None,
        sigma_source=sigma_src,
        fee_apr_ref=fee_ref * 36500,
        aero_apr_ref=aero_ref * 36500,
        lvr_apr_ref=lvr_ref * 36500,
        edge_ratio=edge if math.isfinite(edge) else 1e9,
        best_mode=mode,
        best_half_width_pct=(math.exp(chosen.half_width) - 1) * 100,
        expected_net_apr=net_apr,
        rebalances_per_week=rb_day * 7,
        cost_per_rebalance_usd=cost_per_rebalance,
        break_even_deposit_usd=break_even if math.isfinite(break_even) else 1e12,
        staked_share=staked_share,
        gauge_active=pool.gauge_alive,
        confidence=confidence,
        flags=flags,
        history_days=min(hist_days, ctx["fee_history_days"] or hist_days),
        backtest_net_apr=bt_apr,
        backtest_half_width_pct=bt_w,
        backtest_days=bt_days,
        backtest_deploy_apr=bt_deploy,
    )
