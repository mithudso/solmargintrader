"""Live Base reads for the provider comparison. Run with:  pytest -m network

Reads public chain state, GeckoTerminal and DefiLlama. Nothing is signed or broadcast.
"""

from __future__ import annotations

import math

import pytest

from aero_lp import addresses, providers
from aero_lp.chain import AeroChain
from aero_lp.market import MarketData
from aero_lp.providers import Coins, Env
from aero_lp.strategy import StrategyConfig

pytestmark = pytest.mark.network

USDC = "0x833589fCD6eDb6E08f4C7C32D4f71b54bdA02913"
# A Uniswap v4 USDC/USDT pool on Base (poolId is the hash of its key, so it never changes).
V4_USDC_USDT = "0xfba2c4592d32a4e2e6393b8898f9110b4e272983f4bd416b38f81672a17fe3dc"


@pytest.fixture(scope="module")
def chain() -> AeroChain:
    return AeroChain()


def test_registry_addresses_verify_on_chain(chain):
    assert providers.verify_registry(chain) == []


def test_a_real_uniswap_v3_weth_usdc_pool_scores_with_finite_measured_numbers(chain):
    venue = providers.VENUES["uniswap-v3"]
    found = providers.find_v3_pools(chain, venue, [(addresses.WETH.lower(), USDC.lower(), 500)])
    pool = found[(addresses.WETH.lower(), USDC.lower(), 500)]
    assert pool, "Uniswap v3 factory has no WETH/USDC 0.05% pool on Base"

    market = MarketData(min_interval=2.2)
    env = Env(chain, market, Coins(market.http), 50.0, StrategyConfig(), 5.0, gas_price_wei=chain.gas_price_wei())
    info = market.pool_info(pool)
    row = providers.score_v3(env, "uniswap-v3", "uniswap-v3", pool, info["reserve_usd"], info["volume_24h_usd"], None)

    assert row.tier == "measured" and row.venue == "uniswap-v3" and row.fee_pct == pytest.approx(0.05)
    assert "feeGrowthGlobal" in row.income_source, "income must come from the 24h fee-growth change"
    for name in ("income_apr", "lvr_apr", "expected_net_apr", "sigma_daily_pct", "edge_ratio", "tvl_usd"):
        v = getattr(row, name)
        assert v is not None and math.isfinite(v), name
    assert row.income_apr > 0 and row.lvr_apr > 0 and 0 < row.sigma_daily_pct < 30
    assert row.tvl_usd > 100_000 and row.venue_info["pool"].lower() == pool.lower()
    assert row.confidence in ("high", "medium")


def test_a_real_uniswap_v4_pool_reads_through_state_view(chain):
    rd = providers.read_v4_pool(chain, V4_USDC_USDT)
    assert rd is not None, "PositionManager does not know this pool key"
    s = rd.state
    assert {s.token0.symbol, s.token1.symbol} == {"USDC", "USDT"} and s.tick_spacing > 0 and s.sqrt_price_x96 > 0
    d0, d1, days = rd.fee_delta
    assert days > 0 and d0 >= 0 and d1 >= 0
