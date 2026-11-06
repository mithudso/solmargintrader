"""Live Base checks. Run with:  pytest -m network

They read public chain state and run eth_simulateV1. Nothing is signed or broadcast.
"""

from __future__ import annotations

import pytest
from web3 import Web3

from aero_lp import addresses
from aero_lp.chain import AeroChain, PositionGone
from aero_lp.executor import ExecConfig, Rebalancer, SimRunner, runner_tokens
from aero_lp.strategy import target_range

pytestmark = pytest.mark.network

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


@pytest.fixture(scope="module")
def chain() -> AeroChain:
    return AeroChain()


def test_deployment_verifies(chain):
    assert chain.verify_deployment() == []


def test_weth_usdc_pool_state(chain):
    addr = chain.pool_address(addresses.WETH, USDC, 100)
    p = chain.pool_state(addr)
    assert p.token0.symbol == "WETH" and p.token1.symbol == "USDC"
    assert 100 < p.price < 100_000
    assert p.gauge_alive and p.staked_liquidity > 0
    assert chain.gauge_aero_per_day(p.gauge, p.block) > 0


def _find_staked_position(chain: AeroChain, gauge: str):
    head = chain.head()[0]
    topic = "0x" + Web3.keccak(text="Deposit(address,address,uint256,uint128)").hex().removeprefix("0x")
    for start in range(head - 9_000, head - 200_000, -20_000):
        logs = chain.w3.eth.get_logs(
            {"address": gauge, "fromBlock": start, "toBlock": start + 8_999, "topics": [topic]}
        )
        for lg in logs:
            user = Web3.to_checksum_address("0x" + lg["topics"][2].hex()[-40:])
            tid = int(lg["topics"][3].hex(), 16)
            try:
                pos = chain.position(tid, owner_hint=user)
            except PositionGone:
                continue
            if pos.staked and pos.liquidity > 0:
                return pos
    return None


def test_full_rebalance_simulates_on_a_real_staked_position(chain):
    pool = chain.pool_state(chain.pool_address(addresses.WETH, USDC, 100))
    pos = _find_staked_position(chain, pool.gauge)
    if pos is None:
        pytest.skip("no live staked position found in the scanned window")
    new = target_range(pos.pool.tick, pos.pool.tick_spacing, 0.05)
    runner = SimRunner(
        chain, pos.owner, runner_tokens(pos.pool.token0.address, pos.pool.token1.address), pos.pool.address
    )
    res = Rebalancer(chain, pos.owner, ExecConfig()).rebalance(pos, new, True, runner, 2000.0, 1.0)
    assert res.stages[:2] == ["unstake", "remove"] and res.stages[-2:] == ["mint", "stake"]
    assert res.new_token_id and res.staked
    assert 500_000 < sum(res.gas_used.values()) < 5_000_000
