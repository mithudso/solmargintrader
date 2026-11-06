"""Off-chain market data (GeckoTerminal public API) and the earnings model.

GeckoTerminal lists Aero Slipstream on Base as dex id `aero-slipstream-base`. The free API allows
about 30 requests/minute, so responses are cached for `ttl` seconds.
"""

from __future__ import annotations

import dataclasses
import math
import time
from dataclasses import dataclass
from typing import Any

import httpx

from . import clmath

GT = "https://api.geckoterminal.com/api/v2"
STABLES = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC (native)
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",  # USDbC
    "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2",  # USDT
    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",  # DAI
}


class MarketData:
    def __init__(self, ttl: float = 120.0, client: httpx.Client | None = None):
        self.ttl = ttl
        self.http = client or httpx.Client(timeout=20, headers={"accept": "application/json"})
        self._cache: dict[str, tuple[float, Any]] = {}

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        key = url + repr(sorted((params or {}).items()))
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < self.ttl:
            return hit[1]
        for attempt in range(4):
            r = self.http.get(url, params=params)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1) ** 2)
                continue
            r.raise_for_status()
            data = r.json()
            self._cache[key] = (time.time(), data)
            return data
        raise RuntimeError(f"rate limited by {url}")

    def token_prices_usd(self, addresses: list[str]) -> dict[str, float]:
        addrs = [a.lower() for a in addresses]
        out = {a: 1.0 for a in addrs if a in STABLES}
        need = [a for a in addrs if a not in out]
        if need:
            data = self._get(f"{GT}/simple/networks/base/token_price/{','.join(need)}")
            for a, v in (data.get("data", {}).get("attributes", {}).get("token_prices") or {}).items():
                if v is not None:
                    out[a.lower()] = float(v)
        return out

    def pool_info(self, pool: str) -> dict[str, float]:
        a = self._get(f"{GT}/networks/base/pools/{pool.lower()}")["data"]["attributes"]
        vol = a.get("volume_usd") or {}
        return {
            "reserve_usd": float(a.get("reserve_in_usd") or 0),
            "volume_24h_usd": float(vol.get("h24") or 0),
            "volume_6h_usd": float(vol.get("h6") or 0),
        }

    def hourly_closes(self, pool: str, hours: int = 72) -> list[float]:
        """Hourly close prices (base token in quote token units), oldest first."""
        data = self._get(
            f"{GT}/networks/base/pools/{pool.lower()}/ohlcv/hour",
            {"aggregate": 1, "limit": min(hours, 1000), "currency": "token"},
        )
        rows = data["data"]["attributes"]["ohlcv_list"]  # newest first: [ts, o, h, l, c, v]
        return [float(r[4]) for r in reversed(rows) if r[4]]

    def top_pools(self, page: int = 1) -> list[dict[str, Any]]:
        data = self._get(f"{GT}/networks/base/dexes/aero-slipstream-base/pools", {"page": page})
        out = []
        for p in data.get("data", []):
            a = p["attributes"]
            out.append(
                {
                    "address": a["address"],
                    "name": a["name"],
                    "reserve_usd": float(a.get("reserve_in_usd") or 0),
                    "volume_24h_usd": float((a.get("volume_usd") or {}).get("h24") or 0),
                }
            )
        return out


def vol_from_closes(closes: list[float], step_hours: float = 1.0, horizon_hours: float = 24.0) -> float | None:
    """Daily log-return vol from a price series.

    Uses overlapping `horizon_hours` returns when there are at least three horizons of data. Trade prices
    bounce between bid and ask inside a tick; that noise is mean-reverting, so it inflates the variance of
    short returns but cancels out over a day. Scaling hourly variance by 24 would count the bounce 24
    times, which for pegged pairs (LST/ETH, stable/stable) overstates daily vol, and therefore LVR, several
    fold. Falls back to one-step returns for short histories.
    """
    pts = [c for c in closes if c > 0]
    if len(pts) < 12:
        return None
    k = max(1, round(horizon_hours / step_hours))
    if len(pts) < 3 * k + 1:
        k = 1
    rets = [math.log(pts[i + k] / pts[i]) for i in range(len(pts) - k)]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var / k) * math.sqrt(24 / step_hours)


# ---------------------------------------------------------------------------- earnings model


@dataclass(frozen=True)
class PoolEconomics:
    """Inputs for a per-position earnings estimate, all in USD per day unless noted."""

    volume_usd_per_day: float
    fee: float  # current dynamic fee as fraction
    unstaked_fee_share: float  # share of an unstaked LP's fees diverted (unstakedFee / 1e6)
    aero_per_day: float  # AERO emitted to the gauge per day
    aero_usd: float
    active_liquidity: int  # pool.liquidity()
    staked_liquidity: int  # pool.stakedLiquidity() (in range)
    price0_usd: float
    price1_usd: float
    dec0: int
    dec1: int
    # Realized fee income per unit of unstaked in-range liquidity per day, in USD, measured from the
    # change in feeGrowthGlobal over the last day. CLPool.calculateFees credits feeGrowthGlobal per unit of
    # *unstaked* liquidity, already net of the unstaked fee, so this captures dynamic fees and MEV capture.
    # 0 = not measured; fall back to volume * current fee.
    fee_usd_per_l_day: float = 0.0


def fee_usd_per_liquidity_per_day(d_growth0_x128: int, d_growth1_x128: int, days: float, e: PoolEconomics) -> float:
    """Convert feeGrowthGlobal deltas (Q128 per unit liquidity) into USD per unit liquidity per day."""
    if days <= 0:
        return 0.0
    q128 = 1 << 128
    usd = d_growth0_x128 / q128 / 10**e.dec0 * e.price0_usd + d_growth1_x128 / q128 / 10**e.dec1 * e.price1_usd
    return usd / days


def liquidity_for_usd(value_usd: float, sqrt_p: int, tick_lower: int, tick_upper: int, e: PoolEconomics) -> int:
    """Liquidity a fresh, correctly-ratioed deposit of `value_usd` gets on [tick_lower, tick_upper)."""
    unit = 10**18
    sa, sb = clmath.get_sqrt_ratio_at_tick(tick_lower), clmath.get_sqrt_ratio_at_tick(tick_upper)
    a0, a1 = clmath.get_amounts_for_liquidity(sqrt_p, sa, sb, unit)
    usd_per_unit = a0 / 10**e.dec0 * e.price0_usd + a1 / 10**e.dec1 * e.price1_usd
    if usd_per_unit <= 0:
        return 0
    return int(value_usd / usd_per_unit * unit)


def earn_usd_per_day(liquidity: int, staked: bool, in_range: bool, e: PoolEconomics, already_counted: bool) -> float:
    """Expected USD/day for a deposit with `liquidity` while in range.

    `already_counted`: True when this liquidity is already part of the pool totals (an existing deposit),
    False for a hypothetical new deposit (added to the denominator).
    """
    if not in_range or liquidity <= 0:
        return 0.0
    if staked:
        denom = e.staked_liquidity + (0 if already_counted else liquidity)
        return e.aero_per_day * e.aero_usd * liquidity / max(1, denom)
    if e.fee_usd_per_l_day > 0:
        # Measured per-unit growth; a new deposit dilutes it by its share of unstaked in-range liquidity.
        unstaked = max(0, e.active_liquidity - e.staked_liquidity)
        dilution = 1.0 if already_counted else unstaked / max(1, unstaked + liquidity)
        return e.fee_usd_per_l_day * liquidity * dilution
    denom = e.active_liquidity + (0 if already_counted else liquidity)
    return e.volume_usd_per_day * e.fee * (1 - e.unstaked_fee_share) * liquidity / max(1, denom)


def with_realized_fees(chain: Any, pool: str, head: int, e: PoolEconomics) -> PoolEconomics:
    """Return `e` with fee_usd_per_l_day measured on chain (unchanged if history is unavailable)."""
    try:
        d0, d1, days = chain.fee_growth_delta(pool, head)
    except Exception:  # noqa: BLE001
        return e
    if days <= 0:
        return e
    return dataclasses.replace(e, fee_usd_per_l_day=fee_usd_per_liquidity_per_day(d0, d1, days, e))
