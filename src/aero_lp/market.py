"""Off-chain market data (GeckoTerminal public API) and the earnings model.

GeckoTerminal lists Aero Slipstream on Base as dex id `aero-slipstream-base`. The free API allows
about 30 requests/minute, so responses are cached for `ttl` seconds.
"""

from __future__ import annotations

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


def vol_from_closes(closes: list[float], step_hours: float = 1.0) -> float | None:
    """Daily log-return vol from a price series."""
    pts = [c for c in closes if c > 0]
    if len(pts) < 12:
        return None
    rets = [math.log(pts[i + 1] / pts[i]) for i in range(len(pts) - 1)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(24 / step_hours)


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
    denom = e.active_liquidity + (0 if already_counted else liquidity)
    return e.volume_usd_per_day * e.fee * (1 - e.unstaked_fee_share) * liquidity / max(1, denom)
