"""Offline tests of the daemon with a stubbed chain, market, engine and rebalancer.

The stubs record every call, so the tests can prove what the daemon did and did not send: which runner kind
each rebalancer call received ("sim" or "live"), and that nothing signs in dry run or under the kill switch.
"""

from __future__ import annotations

import json
import math
import time
from types import SimpleNamespace

import pytest
from web3 import Web3

from aero_lp import addresses, clmath
from aero_lp import daemon as dmod
from aero_lp.allocator import Arm, Candidate
from aero_lp.chain import ZERO, PoolState, PositionGone, PositionState, Token
from aero_lp.config import AllocatorConfig, Config, SafetyConfig
from aero_lp.executor import RebalanceError, RebalanceResult
from aero_lp.metrics import KNOWN_TOKENS
from aero_lp.strategy import Action

OWNER = Web3.to_checksum_address("0x" + "ab" * 20)
WETH = Web3.to_checksum_address(addresses.WETH)
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
AERO = Web3.to_checksum_address(addresses.AERO_TOKEN)
WSTETH = Web3.to_checksum_address("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452")
GAUGE = Web3.to_checksum_address("0x" + "cc" * 20)
DEC = {WETH: 18, USDC: 6, AERO: 18, WSTETH: 18}
PRICES = {WETH.lower(): 2000.0, USDC.lower(): 1.0, AERO.lower(): 1.0, WSTETH.lower(): 2400.0}


def addr(n: int) -> str:
    return Web3.to_checksum_address("0x" + f"{n:02x}" * 20)


def tick_for(price: float) -> int:
    return int(round(math.log(price) / math.log(1.0001)))


def make_pool(t0: str, t1: str, tick: int, address: str | None = None, fee_pips: int = 500) -> PoolState:
    return PoolState(
        address=address or addr(0x11),
        token0=Token(t0, KNOWN_TOKENS[t0.lower()], DEC[t0]),
        token1=Token(t1, KNOWN_TOKENS[t1.lower()], DEC[t1]),
        tick_spacing=1,
        fee_pips=fee_pips,
        unstaked_fee_pips=0,
        sqrt_price_x96=clmath.get_sqrt_ratio_at_tick(tick),
        tick=tick,
        liquidity=10**18,
        staked_liquidity=0,
        gauge=GAUGE,
        gauge_alive=True,
        fee_growth_global0=0,
        fee_growth_global1=0,
        reward_growth_global=0,
        block=1,
        timestamp=1,
    )


# WETH (18) / USDC (6): raw price = USDC-raw per WETH-raw = 2000 * 1e6 / 1e18
MAIN_TICK = tick_for(2000 * 1e6 / 1e18)


def make_pos(
    token_id: int = 42,
    staked: bool = True,
    pool: PoolState | None = None,
    in_range: bool = True,
    earned_aero: int = 0,
    fees: tuple[int, int] = (0, 0),
) -> PositionState:
    pool = pool or make_pool(WETH, USDC, MAIN_TICK)
    tl, tu = (pool.tick - 100, pool.tick + 100) if in_range else (pool.tick + 100, pool.tick + 200)
    return PositionState(
        token_id, OWNER, staked, pool, tl, tu, 10**15, 10**15, 2 * 10**6, fees[0], fees[1], earned_aero
    )


def pos_worth(token_id: int, usd: float) -> PositionState:
    """A position holding half its value in WETH ($2000) and half in USDC."""
    pos = make_pos(token_id, staked=False)
    pos.amount0, pos.amount1 = int(usd / 2 / 2000 * 10**18), int(usd / 2 * 10**6)
    return pos


class FakeChain:
    def __init__(self):
        self.w3 = SimpleNamespace(eth=SimpleNamespace(get_balance=lambda a: 10**17))
        self.factory = SimpleNamespace(
            functions=SimpleNamespace(tickSpacings=lambda: SimpleNamespace(call=lambda: [1]))
        )
        self.routes: dict[frozenset[str], PoolState] = {}
        self.pools: dict[str, PoolState] = {}
        self.balances: dict[str, int] = {WETH: 0, USDC: 0, AERO: 0, WSTETH: 0}
        self.positions: dict[int, PositionState] = {}

    def add_pool(self, pool: PoolState) -> None:
        self.routes[frozenset({pool.token0.address.lower(), pool.token1.address.lower()})] = pool
        self.pools[pool.address.lower()] = pool

    def check_fresh(self):
        return 1

    def head(self):
        return 1, int(time.time())

    def gas_price_wei(self):
        return 10**6

    def pool_address(self, a, b, ts):
        p = self.routes.get(frozenset({a.lower(), b.lower()}))
        return p.address if p else ZERO

    def pool_state(self, address):
        return self.pools[address.lower()]

    def token(self, address):
        a = Web3.to_checksum_address(address)
        return Token(a, KNOWN_TOKENS[a.lower()], DEC.get(a, 18))

    def erc20_balances(self, owner, tokens, block="latest"):
        return [self.balances.get(Web3.to_checksum_address(t), 0) for t in tokens]

    def position(self, token_id, owner_hint=None):
        if token_id not in self.positions:
            raise PositionGone(token_id)
        return self.positions[token_id]


class FakeMarket:
    def __init__(self):
        self.down = False

    def token_prices_usd(self, tokens):
        if self.down:
            raise RuntimeError("price feed down")
        return {t.lower(): PRICES[t.lower()] for t in tokens if t.lower() in PRICES}


class FakeEngine:
    def __init__(self, cfg, chain=None, market=None):
        self.gate = None
        self.script: dict[int, object] = {}
        self.steps: list[tuple[int, bool, object]] = []
        self.withdraws: list[tuple[int, bool]] = []
        self.blocks: list[str] = []
        self.withdraw_result: object = None

    def step(self, configured_id, live, signer=None, force=False):
        self.steps.append((configured_id, live, signer))
        out = self.script[configured_id]
        if isinstance(out, Exception):
            raise out
        return out

    def pool_blocks(self, pool, live):
        return list(self.blocks)

    def withdraw(self, token_id, live, signer=None):
        self.withdraws.append((token_id, live))
        if isinstance(self.withdraw_result, Exception):
            raise self.withdraw_result
        return self.withdraw_result


class FakeRB:
    """Records (method, runner kind) for every call; results are scripted by the test."""

    def __init__(self, chain, owner, cfg):
        self.calls: list[tuple] = []
        self.claimed = 3 * 10**18
        self.collected = (0, 0)
        self.swap_out = 777
        self.on_claim = None
        self.topup_error: Exception | None = None
        self.deploy_error: Exception | None = None
        self.new_token_id = 555

    @staticmethod
    def _kind(runner):
        return runner[0]

    def claim(self, pos, runner):
        self.calls.append(("claim", self._kind(runner)))
        if self.on_claim:
            self.on_claim()
        return RebalanceResult(
            pos.token_id, True, ["claim"], ["0xc1"], {"claim": 100000}, aero_claimed=self.claimed, fee_wei=10**12
        )

    def collect(self, pos, runner):
        self.calls.append(("collect", self._kind(runner)))
        return RebalanceResult(
            pos.token_id, False, ["collect"], ["0xc2"], {"collect": 100000}, amounts_in_position=self.collected
        )

    def topup(self, pos, a0, a1, runner, u0, u1, *, include_unstake_proceeds=True):
        self.calls.append(("topup", self._kind(runner), a0, a1))
        if self.topup_error and runner[0] == "live":  # the preflight simulation passes; the live send fails
            raise self.topup_error
        return RebalanceResult(
            pos.token_id, pos.staked, ["increase"], ["0xt"], {"increase": 100000}, amounts_in_position=(a0, a1)
        )

    def swap_exact(self, pool, token_in, amount, runner, min_out):
        self.calls.append(("swap_exact", self._kind(runner), token_in, amount, min_out, runner[1][2], runner[1][3]))
        return RebalanceResult(None, False, ["swap"], ["0xs"], {"swap": 100000}, amount_out=self.swap_out)

    def deploy(self, pool, rng, stake, a0, a1, runner, u0, u1, on_stage=None):
        self.calls.append(("deploy", self._kind(runner), a0, a1, stake))
        live = runner[0] == "live"
        if self.deploy_error and live:
            partial = self.deploy_error.partial
            if on_stage and partial.new_token_id:  # the real sequence calls the hook when the mint lands
                on_stage("mint", partial)
            raise self.deploy_error
        res = RebalanceResult(
            self.new_token_id,
            stake,
            ["swap", "mint"],
            ["0xd"],
            {"mint": 100000},
            amounts_in_position=(a0, a1),
            fee_wei=10**12,
        )
        if on_stage and live:
            on_stage("mint", res)
        return res

    def unwrap_weth(self, amount, runner):
        self.calls.append(("unwrap_weth", self._kind(runner), amount))
        return RebalanceResult(None, False, ["unwrap"], ["0xu"], {"unwrap": 100000})

    swap_to_eth_error: Exception | None = None

    def swap_to_eth(self, pool, token_in, amount_in, min_eth_out, runner):
        self.calls.append(("swap_to_eth", self._kind(runner), token_in, amount_in, min_eth_out))
        if self.swap_to_eth_error:
            raise self.swap_to_eth_error
        return RebalanceResult(None, False, ["swap_to_eth"], ["0xe"], {"swap_to_eth": 100000})


@pytest.fixture
def make_daemon(tmp_path, monkeypatch):
    chain, market = FakeChain(), FakeMarket()
    constructed: list[tuple] = []

    def sim(chain_, owner, tokens, pool=None):
        constructed.append(("sim", chain_, owner, tokens, pool))
        return ("sim", (chain_, owner, tokens, pool))

    def live(chain_, signer, tokens, cfg, pool=None, *, journal=None):
        constructed.append(("live", chain_, signer, tokens, pool))
        return ("live", (chain_, signer, tokens, pool))

    monkeypatch.setattr(dmod, "AeroChain", lambda url: chain)
    monkeypatch.setattr(dmod, "MarketData", lambda: market)
    monkeypatch.setattr(dmod, "Engine", FakeEngine)
    monkeypatch.setattr(dmod, "Rebalancer", FakeRB)
    monkeypatch.setattr(dmod, "SimRunner", sim)
    monkeypatch.setattr(dmod, "LiveRunner", live)
    monkeypatch.setattr(dmod, "run_scout", lambda *a, **k: None)

    count = []

    def build(
        live_mode: bool = False, killed: bool = False, safety: SafetyConfig | None = None, **alloc
    ) -> dmod.Daemon:
        root = tmp_path / f"home{len(count)}"  # one state directory per daemon: KILL files must not leak between them
        count.append(root)
        cfg = Config(
            owner=OWNER,
            state_path=str(root / "state.json"),
            allocator=AllocatorConfig(**alloc),
            safety=safety or SafetyConfig(),
        )
        d = dmod.Daemon(cfg, live_mode, signer=object() if live_mode else None, root=root)
        d.test = SimpleNamespace(chain=chain, market=market, constructed=constructed)
        if killed:
            (root / "KILL").write_text("")
        return d

    return build


def events(d, kind=None):
    rows = d.ledger.db.execute("SELECT * FROM events ORDER BY id").fetchall()
    return [r for r in rows if kind is None or r["kind"] == kind]


def decision_ev(pos, value_usd=40.0, gas_usd=0.01, action=Action.HOLD):
    return SimpleNamespace(
        pos=pos, decision=SimpleNamespace(reason="test", action=action), value_usd=value_usd, gas_usd=gas_usd
    )


def open_slot(d, slot="42", pool=None, token_id=42, experiment=None, ts=None, deposit=40.0):
    pool = pool or make_pool(WETH, USDC, MAIN_TICK)
    d.ledger.open_slot(
        slot,
        pool.address,
        "WETH/USDC",
        WETH,
        USDC,
        18,
        6,
        token_id,
        experiment=experiment,
        ts=ts,
    )
    d.ledger.flow(slot, "deposit", 0.01, 20.0, deposit, ts=ts)


# ---------------------------------------------------------------- the kill switch and dry run


def test_acting_needs_live_and_no_kill_file(make_daemon):
    assert not make_daemon(live_mode=False).acting()
    assert not make_daemon(live_mode=False, killed=True).acting()
    assert not make_daemon(live_mode=True, killed=True).acting()
    d = make_daemon(live_mode=True)
    assert d.acting()
    (d.root / "KILL").write_text("")
    assert not d.acting()  # the file is checked on every call, not cached


def test_runner_is_simulation_unless_live_and_refused_under_kill(make_daemon):
    assert make_daemon(live_mode=False).runner([WETH], None)[0] == "sim"
    d = make_daemon(live_mode=False, killed=True)
    assert d.runner([WETH], None)[0] == "sim"  # a dry run never has a signer to refuse
    live = make_daemon(live_mode=True)
    assert live.runner([WETH], None)[0] == "live"
    (live.root / "KILL").write_text("")
    with pytest.raises(dmod.KillSwitchEngaged):
        live.runner([WETH], None)
    with pytest.raises(dmod.KillSwitchEngaged):
        live.assert_acting()  # the engine's pre-broadcast gate
    assert [c[0] for c in live.test.constructed].count("live") == 1


def test_live_daemon_without_signer_is_refused(make_daemon, tmp_path):
    with pytest.raises(ValueError, match="signer"):
        dmod.Daemon(Config(owner=OWNER), True, None, root=tmp_path)


def _prepare_every_action(d, tmp_path):
    """Everything that could sign is armed: a staked position with a big reward, a WETH gas shortfall with
    idle coins and a qualifying pool, and a mature experiment with a clear loser."""
    chain = d.test.chain
    pos = make_pos(staked=True, earned_aero=500 * 10**18)
    d.decisions["42"] = {"_pos": pos, "_ev": decision_ev(pos), "value_usd": 40.0, "pool": pos.pool.address}
    pool = make_pool(WETH, USDC, MAIN_TICK)
    chain.add_pool(pool)
    chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22)))
    chain.positions[42] = pos
    open_slot(d, "42", pool, 42)
    start = time.time() - 9 * 86400
    d.ledger.start_experiment("e1", ts=start)
    for slot, val in (("a", 50.0), ("b", 30.0)):
        d.ledger.open_slot(slot, "0x" + slot, slot, WETH, USDC, 18, 6, int(ord(slot)), experiment="e1", ts=start)
        d.ledger.flow(slot, "deposit", 1, 1, 40.0, ts=start)
        d.ledger.snapshot(slot, int(ord(slot)), val, 40.0)
    chain.positions[ord("a")] = pos_worth(ord("a"), 50.0)
    chain.positions[ord("b")] = pos_worth(ord("b"), 30.0)
    _scout_doc(d, pool)
    return _idle_weth_wallet(d)


def _scout_doc(d, pool):
    (d.root / "scout.json").write_text(
        json.dumps(
            {
                "schema": "aero-lp-scout/1",
                "generated_at": time.time(),
                "pools": [
                    {
                        "pool": pool.address,
                        "pair": "WETH/USDC",
                        "tick_spacing": 1,
                        "token0": WETH,
                        "token1": USDC,
                        "expected_net_apr": 50,
                        "backtest_net_apr": 50,
                        "backtest_days": 7,
                        "edge_ratio": 5,
                        "confidence": "high",
                        "tvl_usd": 1e6,
                        "best_mode": "aero",
                        "best_half_width_pct": 1.0,
                    }
                ],
            }
        )
    )


def _idle_weth_wallet(d):
    wallet = {
        "eth": 0.0,
        "tokens": [
            {"symbol": "WETH", "address": WETH, "amount": 1.0, "usd": 2000.0, "raw": 10**18, "decimals": 18},
        ],
        "human": {WETH: 1.0},
    }
    now = time.time()
    for k in range(0, 49 * 2):  # a sample every 30 minutes for 49 hours: the wallet is observed throughout
        d.ledger.wallet_snapshot({WETH: 1.0}, ts=now - k * 1800)
    return wallet


@pytest.mark.parametrize("live_mode, killed", [(False, False), (False, True), (True, True)])
def test_no_action_method_signs_when_not_acting(make_daemon, tmp_path, live_mode, killed):
    d = make_daemon(live_mode=live_mode, killed=killed, min_position_usd=10)
    wallet = _prepare_every_action(d, tmp_path)
    d.engine.withdraw_result = RuntimeError("must not be reached")
    d.compound_slot("42")
    d.allocate(wallet)
    d.graduate()
    assert [c for c in d.rb.calls if c[1] == "live"] == []
    assert not [c for c in d.rb.calls if c[0] in ("claim", "collect", "topup", "unwrap_weth")]
    assert d.engine.withdraws == []
    assert [c for c in d.test.constructed if c[0] == "live"] == []
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind IN ('topup','withdraw')").fetchone()[0] == 0
    assert d.ledger.db.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 3  # nothing opened or closed
    assert d.ledger.experiments()[0]["status"] == "running"
    if not live_mode:
        # dry run simulates the deployment instead of sending it
        assert all(c[1] == "sim" for c in d.rb.calls)


def test_manage_slot_reads_the_kill_switch_once_for_flag_and_signer(make_daemon):
    d = make_daemon(live_mode=True)
    pos = make_pos()
    d.engine.script[42] = (decision_ev(pos), None)
    d.ledger.open_slot("42", pos.pool.address, "WETH/USDC", WETH, USDC, 18, 6, 42)
    d.manage_slot("42", time.time())
    assert d.engine.steps[-1][1] is True and d.engine.steps[-1][2] is d.signer
    (d.root / "KILL").write_text("")
    d.manage_slot("42", time.time())
    assert d.engine.steps[-1][1] is False and d.engine.steps[-1][2] is None


def test_kill_switch_created_between_claim_and_swap_stops_the_compound(make_daemon):
    d = make_daemon(live_mode=True)
    chain = d.test.chain
    pos = make_pos(staked=True, earned_aero=500 * 10**18)
    chain.add_pool(pos.pool)
    chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22)))
    chain.positions[42] = pos
    open_slot(d)
    d.decisions["42"] = {"_pos": pos, "_ev": decision_ev(pos)}
    d.rb.on_claim = lambda: (d.root / "KILL").write_text("")
    with pytest.raises(dmod.KillSwitchEngaged):
        d.compound_slot("42")
    kinds = [c[0] for c in d.rb.calls]
    assert kinds == ["claim"]  # no swap, no topup: the claimed AERO stays in the wallet
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='topup'").fetchone()[0] == 0


# ---------------------------------------------------------------- _convert_into


@pytest.mark.parametrize(
    "token, route_tokens, route_price, gets_token0",
    [
        # AERO is the route's token0: selling token0 -> output = amount * raw_price
        (AERO, (AERO, WETH), 1 / 2000, True),
        # wstETH is the route's token1: selling token1 -> output = amount / raw_price
        (WSTETH, (WETH, WSTETH), 2000 / 2400, True),
    ],
)
def test_convert_into_min_out_direction_and_measured_output(make_daemon, token, route_tokens, route_price, gets_token0):
    d = make_daemon(live_mode=False)
    route = make_pool(*route_tokens, tick_for(route_price), address=addr(0x33))
    d.test.chain.add_pool(route)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    amount = 10 * 10**18
    d.rb.swap_out = 123456
    a0, a1 = d._convert_into(pool, token, amount, None)
    call = d.rb.calls[-1]
    fwd = token == route.token0.address
    expected = amount * route.raw_price * (1 - route.fee) if fwd else amount / route.raw_price * (1 - route.fee)
    assert call[0] == "swap_exact" and call[1] == "sim"
    assert call[4] == int(expected * (1 - 50 / 1e4))  # min_out is in the OUTPUT token's units
    # output is the measured swap result (not min_out), routed to the pool's token0 slot (WETH)
    assert (a0, a1) == (123456, 0)
    # the runner tracks the pool's tokens, AERO (for rewards) and the converted token; its pool is the route
    tokens, runner_pool = call[5], call[6]
    assert set(tokens) >= {WETH, USDC, AERO, token} and runner_pool == route.address


def test_convert_into_output_goes_to_token1_slot_when_the_route_ends_in_token1(make_daemon):
    d = make_daemon(live_mode=False)
    d.test.chain.add_pool(make_pool(AERO, USDC, tick_for(1.0 * 1e6 / 1e18), address=addr(0x44)))
    d.rb.swap_out = 5_000_000
    pool = make_pool(WETH, USDC, MAIN_TICK)
    # WETH/USDC pool, AERO has no AERO/WETH route here, only AERO/USDC: lands in token1
    assert d._convert_into(pool, AERO, 5 * 10**18, None) == (0, 5_000_000)


def test_token_that_is_already_a_pool_token_is_not_swapped(make_daemon):
    d = make_daemon()
    pool = make_pool(WETH, USDC, MAIN_TICK)
    assert d._convert_into(pool, WETH, 5, None) == (5, 0)
    assert d._convert_into(pool, USDC.lower(), 7, None) == (0, 7)
    assert d.rb.calls == []


def test_conversion_is_refused_when_the_pool_pays_far_below_market(make_daemon):
    d = make_daemon(live_mode=False)
    # the pool prices AERO at half of its market value (a pushed pool; the min_out would be built from it)
    d.test.chain.add_pool(make_pool(AERO, WETH, tick_for(0.00025), address=addr(0x33)))
    pool = make_pool(WETH, USDC, MAIN_TICK)
    assert d._convert_into(pool, AERO, 10**18, None) == (0, 0)
    assert d.rb.calls == []
    assert "conversion refused" in events(d, "skip")[-1]["detail"]


def test_conversion_without_a_route_or_a_price_leaves_the_coins(make_daemon):
    d = make_daemon(live_mode=False)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    assert d._convert_into(pool, AERO, 10**18, None) == (0, 0)
    assert "no direct pool" in events(d, "skip")[-1]["detail"]
    d.test.chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x33)))
    d.test.market.down = True
    with pytest.raises(RuntimeError, match="price feed down"):  # sizing needs a fresh price: fail, don't guess
        d._convert_into(pool, AERO, 10**18, None)
    assert d.rb.calls == []


# ---------------------------------------------------------------- deploy_arm


def _arm(pool, usd, mode="fees"):
    c = Candidate(pool.address, "WETH/USDC", WETH, USDC, 40, 40, 40, mode, 1.0)
    return Arm(c, usd)


def _idle(addr_, human, usd, decimals):
    return {
        "address": addr_,
        "idle_amount": human,
        "idle_raw": int(human * 10**decimals),
        "idle_usd": usd,
        "usd": usd,
        "amount": human,
        "raw": int(human * 10**decimals),
    }


def test_deploy_arm_uses_pool_tokens_first_and_never_counts_a_conversion_twice(make_daemon):
    d = make_daemon(live_mode=True)
    chain = d.test.chain
    pool = make_pool(WETH, USDC, MAIN_TICK)
    chain.add_pool(pool)
    chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22)))
    idle = [
        _idle(AERO, 5.0, 5.0, 18),
        _idle(USDC, 10.0, 10.0, 6),
        _idle(WETH, 0.005, 10.0, 18),
    ]
    d.rb.swap_out = 2 * 10**15  # the AERO -> WETH swap returns this much WETH
    d.deploy_arm(_arm(pool, 25.0), idle, None)
    kinds = [(c[0], c[1]) for c in d.rb.calls]
    # only AERO was converted (the pool's own tokens need no swap); the deposit is simulated, then sent
    assert kinds == [("swap_exact", "sim"), ("swap_exact", "live"), ("deploy", "sim"), ("deploy", "live")]
    swap = d.rb.calls[0]
    assert swap[2] == AERO and swap[3] == 5 * 10**18
    deploy = next(c for c in d.rb.calls if c[:2] == ("deploy", "live"))
    assert deploy[1] == "live"
    assert deploy[2] == 5 * 10**15 + 2 * 10**15  # idle WETH + the swap's output, each counted once
    assert deploy[3] == 10 * 10**6
    assert idle[0]["idle_usd"] == pytest.approx(0) and idle[1]["idle_usd"] == pytest.approx(0)
    slot = d.ledger.open_slots()[0]
    assert slot["slot"] == "555" and d.ledger.pnl("555").deposited_usd == pytest.approx(7e-3 * 2000 + 10)


def test_deploy_arm_proportional_amounts_for_a_partly_used_token(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    idle = [_idle(USDC, 40.0, 40.0, 6)]
    d.deploy_arm(_arm(pool, 10.0), idle, None)
    deploy = d.rb.calls[-1]
    assert deploy[1] == "live" and deploy[3] == 10 * 10**6  # $10 of a $40 balance is a quarter of the raw amount
    assert idle[0]["idle_usd"] == pytest.approx(30.0) and idle[0]["idle_raw"] == 30 * 10**6


def test_dry_run_deploy_leaves_no_slot_and_no_experiment(make_daemon):
    d = make_daemon(live_mode=False)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    d.test.chain.balances[USDC] = 10 * 10**6
    d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], "exp-x", "note")
    assert d.rb.calls == [("deploy", "sim", 0, 10 * 10**6, False)]
    assert d.ledger.experiments() == [] and d.ledger.open_slots() == []
    assert "would deploy" in events(d, "skip")[-1]["detail"]


def test_dry_run_deploy_that_needs_a_conversion_does_not_fake_a_revert(make_daemon):
    d = make_daemon(live_mode=False)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    d.test.chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22)))
    # the wallet holds no WETH, so the simulated swap's output cannot be deposited in a simulation
    d.deploy_arm(_arm(pool, 5.0), [_idle(AERO, 5.0, 5.0, 18)], None)
    assert [c[0] for c in d.rb.calls] == ["swap_exact"]
    assert "would convert and deploy" in events(d, "skip")[-1]["detail"]


def test_experiment_row_exists_only_after_an_arm_is_really_opened(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    d.rb.deploy_error = RebalanceError("boom", RebalanceResult(None, False, ["swap"], [], {}))
    with pytest.raises(RebalanceError):
        d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], "exp-1", "note")
    assert d.ledger.experiments() == []
    d.rb.deploy_error = None
    d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], "exp-1", "note")
    assert [e["id"] for e in d.ledger.experiments()] == ["exp-1"] and d.ledger.experiments()[0]["arms"] == ["555"]


def test_minted_but_unstaked_deploy_is_tracked_not_orphaned(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    partial = RebalanceResult(
        901, False, ["swap", "mint"], ["0xm"], {}, amounts_in_position=(0, 10 * 10**6), fee_wei=10**12
    )
    d.rb.deploy_error = RebalanceError("stake failed", partial)
    d.test.chain.balances[USDC] = 10**7
    with pytest.raises(RebalanceError):
        d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], None)
    assert [s["slot"] for s in d.ledger.open_slots()] == ["901"]
    assert d.ledger.pnl("901").deposited_usd == pytest.approx(10.0)


def test_deploy_is_not_sent_when_the_manipulation_guard_blocks_or_gas_is_too_high(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    d.engine.blocks = ["spot is 300 bps from the 10-min TWAP"]
    d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], None)
    assert d.rb.calls == [] and "TWAP" in events(d, "skip")[-1]["detail"]
    d2 = make_daemon(live_mode=True, safety=SafetyConfig(max_gas_usd=0.0))
    d2.test.chain.add_pool(pool)
    d2.rb.deploy = lambda *a, **k: RebalanceResult(1, False, ["mint"], [], {"mint": 5_000_000})
    d2.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], None)
    assert d2.ledger.open_slots() == [] and "max_gas_usd" in events(d2, "skip")[-1]["detail"]


# ---------------------------------------------------------------- allocate


def test_deployed_and_held_come_from_the_ledger_not_from_stale_decisions(make_daemon, monkeypatch):
    d = make_daemon(live_mode=False, min_position_usd=10, max_total_deployed_usd=50)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    _scout_doc(d, pool)
    wallet = _idle_weth_wallet(d)
    # slot "42" is open in the ledger and holds $40 but its evaluation failed this tick (no decision);
    # a closed arm's decision lingers in memory and must not count
    open_slot(d, "42", pool, 42)
    d.ledger.snapshot("42", 42, 40.0, 40.0)
    d.decisions["gone"] = {"value_usd": 999.0, "pool": "0xdead"}
    seen = []
    monkeypatch.setattr(d, "deploy_arm", lambda arm, idle, exp, note="": seen.append(arm.usd))
    d.allocate(wallet)
    assert seen == []  # the open slot already holds the scout's only pool
    d.ledger.db.execute("UPDATE slots SET pool='0xother' WHERE slot='42'")
    d.allocate(wallet)
    assert seen == [pytest.approx(10.0)]  # $50 cap - $40 already deployed, even without a fresh decision


def test_stale_scout_data_is_not_used(make_daemon, monkeypatch):
    d = make_daemon(live_mode=False, min_position_usd=10)
    wallet = _prepare_every_action(d, None)
    doc = json.loads((d.root / "scout.json").read_text())
    doc["generated_at"] = time.time() - 4 * 6 * 3600  # older than 3 scout intervals
    (d.root / "scout.json").write_text(json.dumps(doc))
    seen = []
    monkeypatch.setattr(d, "deploy_arm", lambda *a, **k: seen.append(1))
    d.allocate(wallet)
    assert seen == [] and "old" in events(d, "skip")[-1]["detail"]


def test_unwrap_is_capped_by_the_balance_and_the_wallet_is_reread_before_idle_is_computed(make_daemon, monkeypatch):
    d = make_daemon(live_mode=True, min_position_usd=10)
    raw = 123_456_789_012_345  # less than the unwrap chunk: the whole balance is unwrapped
    d.test.chain.balances[WETH] = raw
    wallet = {
        "eth": 0.0,
        "tokens": [{"symbol": "WETH", "address": WETH, "amount": raw / 1e18, "usd": 1.0, "raw": raw, "decimals": 18}],
        "human": {WETH: raw / 1e18},
    }
    reads = []
    real = d.read_wallet
    monkeypatch.setattr(d, "read_wallet", lambda: (reads.append(1), real())[1])
    d.allocate(wallet)
    unwrap = [c for c in d.rb.calls if c[:2] == ("unwrap_weth", "live")][0]
    assert unwrap[1] == "live" and unwrap[2] == raw
    assert reads == [1]  # idle amounts are computed from the wallet as it is after the unwrap


# ---------------------------------------------------------------- compounding and its ledger entries


def _armed_compound(d, staked, fees=(0, 0), earned=500 * 10**18):
    chain = d.test.chain
    pos = make_pos(staked=staked, earned_aero=earned, fees=fees)
    chain.add_pool(pos.pool)
    chain.add_pool(make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22)))
    chain.positions[42] = pos
    open_slot(d)
    d.decisions["42"] = {"_pos": pos, "_ev": decision_ev(pos)}
    return pos


def test_staked_compound_books_the_claim_once_and_the_topup_as_a_flow(make_daemon):
    d = make_daemon(live_mode=True)
    _armed_compound(d, staked=True)
    d.rb.swap_out = 10**15
    d.compound_slot("42")
    assert [(c[0], c[1]) for c in d.rb.calls] == [
        ("claim", "sim"),
        ("claim", "live"),
        ("swap_exact", "sim"),
        ("swap_exact", "live"),
        ("topup", "sim"),  # the preflight simulation
        ("topup", "live"),
    ]
    claim = events(d, "claim")[0]
    assert claim["reward_usd"] == pytest.approx(3.0)  # 3 AERO at $1, counted here and nowhere else
    assert events(d, "compound")[0]["reward_usd"] == 0
    flows = d.ledger.db.execute("SELECT * FROM flows WHERE kind='topup'").fetchall()
    assert len(flows) == 1 and flows[0]["usd"] == pytest.approx(10**15 / 1e18 * 2000)
    assert claim["gas_usd"] == pytest.approx(10**12 / 1e18 * 2000)


def test_unstaked_compound_books_measured_fees_not_the_estimate(make_daemon):
    d = make_daemon(live_mode=True)
    _armed_compound(d, staked=False, fees=(10**15, 5 * 10**6))  # estimate: $2 + $5
    d.rb.collected = (10**15, 0)  # what actually arrived: only the WETH, $2
    d.compound_slot("42")
    assert events(d, "collect")[0]["reward_usd"] == pytest.approx(2.0)
    assert d.rb.calls[-1][:2] == ("topup", "live") and d.rb.calls[-1][2:] == (10**15, 0)


def test_compound_waits_when_the_guard_blocks_or_the_price_left_the_range(make_daemon):
    d = make_daemon(live_mode=True)
    pos = _armed_compound(d, staked=True)
    d.engine.blocks = ["TWAP"]
    d.compound_slot("42")
    assert d.rb.calls == []  # not even the claim
    d.engine.blocks = []
    d.test.chain.positions[42] = make_pos(staked=True, in_range=False, pool=pos.pool)
    d.rb.swap_out = 10**15
    d.compound_slot("42")
    assert [(c[0], c[1]) for c in d.rb.calls] == [
        ("claim", "sim"),
        ("claim", "live"),
        ("swap_exact", "sim"),
        ("swap_exact", "live"),
    ]  # both writes were preflighted; the refreshed out-of-range position was not topped up
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='topup'").fetchone()[0] == 0


def test_failed_restake_after_the_increase_still_books_the_added_liquidity(make_daemon):
    d = make_daemon(live_mode=True)
    _armed_compound(d, staked=True)
    d.rb.swap_out = 10**15
    d.rb.topup_error = RebalanceError(
        "restake failed", RebalanceResult(42, False, ["unstake", "increase"], [], {}, amounts_in_position=(10**15, 0))
    )
    with pytest.raises(RebalanceError):
        d.compound_slot("42")
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='topup'").fetchone()[0] == 1
    d.rb.topup_error = RebalanceError("revert", RebalanceResult(42, False, ["unstake"], [], {}))
    # A later tick must refresh the position before another compound after a partial live outcome.
    pos = d.test.chain.position(42)
    d.decisions["42"] = {"_pos": pos, "_ev": decision_ev(pos)}
    with pytest.raises(RebalanceError):
        d.compound_slot("42")
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='topup'").fetchone()[0] == 1  # nothing added


# ---------------------------------------------------------------- rebalance bookkeeping


def _rebalance_result(new_id=900, aero=2 * 10**18):
    return RebalanceResult(
        new_id, True, ["unstake", "remove", "mint", "stake"], ["0xr"], {}, aero_claimed=aero, fee_wei=10**12
    )


def test_rebalance_is_booked_even_if_the_price_feed_dies_afterwards(make_daemon):
    d = make_daemon(live_mode=True)
    pos = make_pos()
    d.test.chain.positions[42] = pos
    open_slot(d)
    d.prices()  # last good prices are on record
    d.engine.script[42] = (decision_ev(pos, action=Action.REBALANCE), _rebalance_result())
    d.test.market.down = True
    d.manage_slot("42", time.time())
    row = d.ledger.slot_row("42")
    assert row["token_id"] == 900
    ev = events(d, "rebalance")[0]
    assert ev["reward_usd"] == pytest.approx(2.0) and ev["gas_usd"] == pytest.approx(10**12 / 1e18 * 2000)
    # the entry describes a burned NFT: compounding must wait for the next evaluation
    assert d.decisions["42"]["_stale"] and d.decisions["42"]["token_id"] == 900
    d.compound_slot("42")
    assert d.rb.calls == []


def test_claimed_aero_is_not_a_reward_when_it_is_redeposited_into_an_aero_pool(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(AERO, WETH, tick_for(0.0005), address=addr(0x22))
    pos = make_pos(pool=pool)
    open_slot(d, pool=pool)
    d.engine.script[42] = (decision_ev(pos, action=Action.REBALANCE), _rebalance_result())
    d.manage_slot("42", time.time())
    assert events(d, "rebalance")[0]["reward_usd"] == 0  # its value is already in the new position


def test_failed_rebalance_that_minted_follows_the_new_nft_and_marks_the_decision_stale(make_daemon):
    d = make_daemon(live_mode=True)
    pos = make_pos()
    open_slot(d)
    d.decisions["42"] = {"_pos": pos, "_ev": decision_ev(pos)}
    partial = RebalanceResult(777, False, ["unstake", "remove", "mint"], ["0xr"], {}, fee_wei=10**12)
    d.engine.script[42] = RebalanceError("stake failed", partial)
    d.manage_slot("42", time.time())
    assert d.ledger.slot_row("42")["token_id"] == 777 and d.decisions["42"]["_stale"]
    err = events(d, "error")[0]
    assert err["gas_usd"] > 0  # the gas of the failed attempt is booked


def test_position_gone_books_its_last_value_as_withdrawn_instead_of_a_total_loss(make_daemon):
    d = make_daemon(live_mode=True)
    open_slot(d)
    d.ledger.snapshot("42", 42, 41.5, 40.0)
    d.engine.script[42] = PositionGone(42)
    d.manage_slot("42", time.time())
    p = d.ledger.pnl("42")
    assert p.closed_at is not None and p.withdrawn_usd == pytest.approx(41.5) and p.pnl_usd == pytest.approx(1.5)


def test_no_snapshot_is_taken_without_both_prices(make_daemon):
    d = make_daemon(live_mode=False)
    open_slot(d)
    pos = make_pos()
    d.test.market.down = True  # nothing was ever priced either
    d.engine.script[42] = (decision_ev(pos), None)
    d.manage_slot("42", time.time())
    assert d.ledger.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0
    assert d.ledger.pnl("42").pnl_usd == pytest.approx(0.0)  # not -100%


def test_log_never_loses_an_event_to_a_price_outage(make_daemon):
    d = make_daemon(live_mode=True)
    d.test.market.down = True
    d.log("error", "partial", "1", RebalanceResult(None, False, [], ["0xh"], {}, fee_wei=10**15))
    row = events(d, "error")[0]
    assert row["gas_usd"] == 0 and json.loads(row["tx"]) == ["0xh"]


# ---------------------------------------------------------------- graduation


def _experiment(d, slots=("a", "b"), values=(50.0, 30.0)):
    start = time.time() - 9 * 86400
    d.ledger.start_experiment("e1", ts=start)
    for slot, val in zip(slots, values, strict=True):
        tid = ord(slot)
        d.ledger.open_slot(slot, "0x" + slot, slot, WETH, USDC, 18, 6, tid, experiment="e1", ts=start)
        d.ledger.flow(slot, "deposit", 1, 1, 40.0, ts=start)
        d.ledger.snapshot(slot, tid, val, 40.0)
        d.test.chain.positions[tid] = pos_worth(tid, val)


def _withdraw_result():
    pos = make_pos(ord("b"))
    res = RebalanceResult(None, False, ["unstake", "remove"], ["0xw"], {}, amounts_in_position=(10**16, 5 * 10**6))
    res.aero_claimed = 10**18
    res.fee_wei = 10**12
    return pos, res, 0.01


def test_graduation_closes_the_loser_books_the_withdrawal_and_the_final_claim(make_daemon):
    d = make_daemon(live_mode=True)
    _experiment(d)
    d.engine.withdraw_result = _withdraw_result()
    d.graduate()
    assert d.engine.withdraws == [(ord("b"), True)]
    p = d.ledger.pnl("b")
    assert p.closed_at is not None and p.withdrawn_usd == pytest.approx(0.01 * 2000 + 5)
    w = events(d, "withdraw")[0]
    assert w["reward_usd"] == pytest.approx(1.0) and w["gas_usd"] > 0  # AERO paid out by the unstake + gas
    assert d.ledger.experiments()[0]["status"] == "graduated"


def test_failed_withdrawal_keeps_the_experiment_open_and_does_not_stop_the_loop(make_daemon):
    d = make_daemon(live_mode=True)
    _experiment(d, slots=("a", "b", "c"), values=(50.0, 30.0, 30.0))
    d.engine.withdraw_result = RebalanceError(
        "remove reverted", RebalanceResult(None, False, ["unstake"], ["0xw"], {}, fee_wei=10**12)
    )
    d.graduate()
    assert len(d.engine.withdraws) == 2  # the second loser was still tried
    assert d.ledger.experiments()[0]["status"] == "running"
    assert len(events(d, "error")) == 2 and all(e["gas_usd"] > 0 for e in events(d, "error"))


def test_graduation_waits_when_an_arm_cannot_be_valued(make_daemon):
    d = make_daemon(live_mode=True)
    _experiment(d)
    d.test.market.down = True
    d.graduate()
    assert d.engine.withdraws == [] and d.ledger.experiments()[0]["status"] == "running"


def test_graduation_refreshes_arm_values_before_ranking(make_daemon):
    d = make_daemon(live_mode=False)
    _experiment(d, values=(30.0, 30.0))  # stale snapshots say they are tied
    d.graduate()
    n = d.ledger.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert n == 4  # one fresh snapshot per arm on top of the two stored ones


# ---------------------------------------------------------------- the loop


def test_one_failing_slot_or_step_does_not_stop_the_tick(make_daemon, monkeypatch):
    d = make_daemon(live_mode=False)
    for slot in ("1", "2"):
        d.ledger.open_slot(slot, addr(0x11), "WETH/USDC", WETH, USDC, 18, 6, int(slot))
    handled, called = [], []

    def manage(slot, now):
        handled.append(slot)
        if slot == "1":
            raise RuntimeError("rpc blip")

    monkeypatch.setattr(d, "manage_slot", manage)
    monkeypatch.setattr(d, "compound_slot", lambda s: (_ for _ in ()).throw(RuntimeError("compound boom")))
    monkeypatch.setattr(d, "allocate", lambda w: (_ for _ in ()).throw(RuntimeError("alloc boom")))
    monkeypatch.setattr(d, "graduate", lambda: called.append("graduate"))
    d.tick()
    assert handled == ["1", "2"] and called == ["graduate"]
    assert (d.root / "status.json").exists()
    assert sum(1 for e in events(d, "error")) >= 3


def test_price_feed_outage_does_not_stop_wallet_reads_or_status(make_daemon):
    d = make_daemon(live_mode=False)
    d.test.chain.balances[USDC] = 5 * 10**6
    d.test.market.down = True
    w = d.read_wallet()
    assert [t["usd"] for t in w["tokens"]] == [0.0] * len(w["tokens"])
    assert d.idle_tokens(w) == []  # nothing is allocated without prices
    d.write_status(w)
    assert json.loads((d.root / "status.json").read_text())["schema"] == dmod.STATUS_SCHEMA


def test_config_position_that_cannot_be_read_does_not_block_the_others(make_daemon):
    d = make_daemon(live_mode=False)
    d.cfg = Config(owner=OWNER, token_ids=[7, 42])
    good = make_pos(42, staked=False)
    d.test.chain.positions[42] = good

    def position(token_id, owner_hint=None):
        if token_id == 7:
            raise RuntimeError("bad ABI response")
        return good

    d.chain.position = position
    d.register_config_positions()
    assert [s["slot"] for s in d.ledger.open_slots()] == ["42"]
    assert "cannot track position #7" in events(d, "error")[0]["detail"]


def test_dry_run_tick_end_to_end_writes_a_valid_status_and_signs_nothing(make_daemon):
    d = make_daemon(live_mode=False)
    pos = make_pos(staked=False)
    d.test.chain.positions[42] = pos
    d.test.chain.balances[USDC] = 12 * 10**6
    open_slot(d)
    sim = RebalanceResult(901, True, ["unstake", "remove", "swap", "mint", "stake"], [], {})
    d.engine.script[42] = (decision_ev(pos, action=Action.REBALANCE), sim)
    d.tick()
    doc = json.loads((d.root / "status.json").read_text())
    assert doc["mode"] == "dry-run" and doc["killed"] is False
    p = doc["positions"][0]
    assert p["slot"] == "42" and p["decision"] == "rebalance" and p["simulated"].startswith("unstake")
    assert "_pos" not in p and "_stale" not in p
    assert d.engine.steps == [(42, False, None)]
    assert d.ledger.slot_row("42")["token_id"] == 42  # the simulated mint is not adopted
    assert [c for c in d.test.constructed if c[0] == "live"] == []
    assert events(d, "rebalance") == []
    assert doc["wallet"]["tokens"]


def test_status_shows_the_kill_switch(make_daemon):
    d = make_daemon(live_mode=True, killed=True)
    d.write_status(d.read_wallet())
    doc = json.loads((d.root / "status.json").read_text())
    assert doc["killed"] is True and doc["mode"] == "live"


def test_bookkeeping_does_not_hammer_a_failing_price_feed(make_daemon):
    d = make_daemon(live_mode=False)
    calls = []
    real = d.test.market.token_prices_usd

    def counted(tokens):
        calls.append(1)
        return real(tokens)

    d.test.market.token_prices_usd = counted
    d.prices()  # a good set is on record
    d.test.market.down = True
    d.test.market.token_prices_usd = lambda t: (calls.append(1), (_ for _ in ()).throw(RuntimeError("429")))[1]
    assert d.known_prices() == d._last_prices and len(calls) == 2
    d.known_prices()
    d.eth_usd()
    assert len(calls) == 2  # one failure, then the last good prices until the retry interval has passed


# ---------------------------------------------------------------- exact amounts, slot tracking, sizing, signals


def test_a_fully_idle_balance_is_used_as_the_exact_integer_not_a_float_round_trip(make_daemon):
    d = make_daemon(live_mode=False)
    raw = 19_379_600_000_000_003  # int(raw * 1.0) == 19_379_600_000_000_004: one wei more than the wallet holds
    assert int(raw * 1.0) > raw
    d.ledger.wallet_snapshot({WETH: raw / 1e18}, ts=time.time() - 1)
    now = time.time()
    for k in range(0, 49 * 2):
        d.ledger.wallet_snapshot({WETH: raw / 1e18}, ts=now - k * 1800)
    wallet = {
        "eth": 1.0,
        "tokens": [{"symbol": "WETH", "address": WETH, "amount": raw / 1e18, "usd": 38.0, "raw": raw, "decimals": 18}],
        "human": {WETH: raw / 1e18},
    }
    [t] = d.idle_tokens(wallet)
    assert t["idle_raw"] == raw
    # and deploy_arm takes exactly that when it takes all of it
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    d.test.chain.balances[WETH] = raw
    d.deploy_arm(_arm(pool, 1000.0), [t], None)
    assert d.rb.calls[-1][2] == raw


def test_a_mint_is_tracked_the_moment_it_lands_not_when_the_sequence_ends(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    seen_during = []
    real = d.rb.deploy

    def deploy(*a, on_stage=None, **k):
        res = real(*a, on_stage=on_stage, **k)
        return res

    # open slots as seen from inside the hook, i.e. before deploy() has returned
    orig_open = d._open_slot

    def spy(*a, **k):
        out = orig_open(*a, **k)
        seen_during.append([s["slot"] for s in d.ledger.open_slots()])
        return out

    d._open_slot = spy
    d.rb.deploy = deploy
    d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], None)
    assert seen_during == [["555"]]
    flows = d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE slot='555' AND kind='deposit'").fetchone()[0]
    assert flows == 1  # opened once, by the hook, not again after the sequence returned


def test_minted_but_unstaked_deploy_books_one_deposit_only(make_daemon):
    d = make_daemon(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    partial = RebalanceResult(901, False, ["swap", "mint"], [], {}, amounts_in_position=(0, 10 * 10**6))
    d.rb.deploy_error = RebalanceError("stake failed", partial)
    with pytest.raises(RebalanceError):
        d.deploy_arm(_arm(pool, 10.0), [_idle(USDC, 10.0, 10.0, 6)], None)
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE slot='901'").fetchone()[0] == 1


def _engine_state(d, token_id, rebalanced):
    from aero_lp.state import SlotState, State

    st = State.__new__(State)
    st.slots = {"42": SlotState(current_token_id=token_id, last_rebalance_ts=time.time() if rebalanced else None)}
    d.engine.state = st
    return st


def test_ledger_follows_the_engine_when_the_process_stopped_right_after_the_mint(make_daemon):
    d = make_daemon(live_mode=True)
    open_slot(d)  # the ledger still says NFT 42, which the rebalance burned
    # the engine's persist hook saved the new id at the mint and nothing else: no rebalance timestamp, no history
    _engine_state(d, 900, rebalanced=False)
    d.test.chain.positions[900] = make_pos(900)
    d.engine.script[42] = (decision_ev(make_pos(900)), None)
    d.manage_slot("42", time.time())
    assert d.ledger.slot_row("42")["token_id"] == 900
    assert d.ledger.slot_row("42")["closed_at"] is None


def test_engine_follows_the_ledger_when_its_state_file_was_lost(make_daemon):
    d = make_daemon(live_mode=True)
    open_slot(d, token_id=900)  # the ledger knows the slot moved to NFT 900 after a rebalance
    st = _engine_state(d, 42, rebalanced=False)  # a fresh state file points at the original, burned NFT
    d.test.chain.positions[900] = make_pos(900)
    d.engine.script[42] = (decision_ev(make_pos(900)), None)
    d.manage_slot("42", time.time())
    assert st.slots["42"].current_token_id == 900 and d.ledger.slot_row("42")["token_id"] == 900


@pytest.mark.parametrize("alive", [(42, 900), ()])
def test_disagreeing_ids_are_left_alone_when_the_chain_cannot_say_which_is_right(make_daemon, alive):
    d = make_daemon(live_mode=True)
    open_slot(d, token_id=900)
    st = _engine_state(d, 42, rebalanced=True)
    for tid in alive:
        d.test.chain.positions[tid] = make_pos(tid)
    d._align_token_id("42", create=True)
    assert st.slots["42"].current_token_id == 42 and d.ledger.slot_row("42")["token_id"] == 900


def test_graduation_uses_the_engines_current_nft_for_the_withdrawal(make_daemon):
    d = make_daemon(live_mode=True)
    _experiment(d)
    from aero_lp.state import SlotState, State

    st = State.__new__(State)
    st.slots = {"b": SlotState(current_token_id=777)}
    d.engine.state = st
    d.test.chain.positions.pop(ord("b"))  # the old NFT is burned
    d.test.chain.positions[777] = pos_worth(777, 30.0)
    d.engine.withdraw_result = _withdraw_result()
    d.graduate()
    assert d.engine.withdraws == [(777, True)]


def test_a_stop_signal_during_a_sequence_is_flagged_and_the_result_is_kept(make_daemon):
    import os
    import signal

    d = make_daemon(live_mode=True)
    done = []

    def sequence():
        os.kill(os.getpid(), signal.SIGTERM)  # `launchctl bootout` in the middle of a sequence
        done.append("stake")  # still runs
        return "result"

    assert d._send(sequence) == "result"  # returned, so the caller can book it
    assert done == ["stake"] and d._stop_signal == signal.SIGTERM
    with pytest.raises(SystemExit) as e:
        d._check_stop()  # the next safe point exits
    assert e.value.code == 128 + signal.SIGTERM


def test_a_rebalance_finished_while_a_stop_was_requested_is_booked_before_the_daemon_exits(make_daemon):
    import signal

    d = make_daemon(live_mode=True)
    pos = make_pos()
    open_slot(d)
    d.test.chain.positions[42] = pos

    class StopDuringStep(FakeEngine):
        def step(self, configured_id, live, signer=None, force=False):
            d._request_stop(signal.SIGTERM)  # the signal arrives mid-sequence
            return decision_ev(pos, action=Action.REBALANCE), _rebalance_result()

    d.engine.__class__ = StopDuringStep
    with pytest.raises(SystemExit):
        d.tick()
    assert d.ledger.slot_row("42")["token_id"] == 900
    assert events(d, "rebalance")[0]["gas_usd"] > 0  # booked, with its gas and reward
    assert [e["kind"] for e in events(d)].count("scout") == 0  # and nothing further was started


def test_run_stops_between_ticks_without_waiting_for_the_poll_interval(make_daemon, monkeypatch):
    import signal

    d = make_daemon(live_mode=False)
    before = signal.getsignal(signal.SIGTERM)
    ticks = []
    monkeypatch.setattr(d, "tick", lambda: (ticks.append(1), d._request_stop(signal.SIGTERM)))
    with pytest.raises(SystemExit):
        d.run()
    assert ticks == [1] and signal.getsignal(signal.SIGTERM) == before  # handlers restored


def test_pools_are_scored_at_the_size_one_arm_would_get(make_daemon):
    d = make_daemon(live_mode=False, min_position_usd=10, max_position_usd=200, max_arms=3)
    wallet = lambda usd: {"tokens": [{"usd": usd}]}  # noqa: E731
    assert d.scout_deposit_usd(wallet(90.0)) == pytest.approx(30.0)  # a third of the wallet
    assert d.scout_deposit_usd(wallet(12.0)) == 10.0  # never below the minimum position
    assert d.scout_deposit_usd(wallet(9000.0)) == 200.0  # nor above the cap


def test_allocation_refuses_positions_much_smaller_than_the_size_the_pools_were_scored_at(make_daemon, monkeypatch):
    d = make_daemon(live_mode=False, min_position_usd=10, max_total_deployed_usd=500)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    _scout_doc(d, pool)
    doc = json.loads((d.root / "scout.json").read_text())
    doc["deposit_usd"] = 100.0
    (d.root / "scout.json").write_text(json.dumps(doc))
    wallet = _idle_weth_wallet(d)
    wallet["tokens"][0].update(amount=0.005, usd=10.0, raw=5 * 10**15)  # only $10 idle: a tenth of the scored size
    seen = []
    monkeypatch.setattr(d, "deploy_arm", lambda *a, **k: seen.append(1))
    d.allocate(wallet)
    assert seen == [] and "scored at" in events(d, "skip")[-1]["detail"]


def test_a_second_signal_while_idle_leaves_at_once(make_daemon):
    import signal

    d = make_daemon(live_mode=False)
    d._on_signal(signal.SIGTERM, None)  # first: asks for a stop at the next safe point
    assert d._stop_signal == signal.SIGTERM
    with pytest.raises(KeyboardInterrupt):
        d._on_signal(signal.SIGINT, None)  # second: the operator insists


def test_a_stop_request_ends_a_long_scout_between_pools(make_daemon, monkeypatch):
    import signal

    d = make_daemon(live_mode=False)
    d.test.chain.balances[USDC] = 12 * 10**6

    def scout(*a, progress=None, **k):
        d._request_stop(signal.SIGTERM)
        progress("[1/20] pool scored")  # the daemon's callback checks for the stop request here

    monkeypatch.setattr(dmod, "run_scout", scout)
    with pytest.raises(SystemExit):
        d.tick()


# ---------------------------------------------------------------- gas top-up for smart accounts (EIP-7702)


def _low_gas_wallet(usdc_raw=5_000_000, weth_raw=10**16):
    return {
        "eth": 0.00005,
        "tokens": [
            {
                "symbol": "WETH",
                "address": WETH,
                "amount": weth_raw / 1e18,
                "usd": weth_raw / 1e18 * 2000,
                "raw": weth_raw,
                "decimals": 18,
            },
            {
                "symbol": "USDC",
                "address": USDC,
                "amount": usdc_raw / 1e6,
                "usd": usdc_raw / 1e6,
                "raw": usdc_raw,
                "decimals": 6,
            },
        ],
        "human": {WETH: weth_raw / 1e18, USDC: usdc_raw / 1e6},
    }


def test_smart_account_tops_up_gas_by_swapping_a_stable_not_unwrapping_weth(make_daemon):
    d = make_daemon(live_mode=True, gas_reserve_eth=0.0003, unwrap_chunk_eth=0.0005)
    d.test.chain.w3.eth.get_code = lambda a: bytes.fromhex("ef0100") + bytes(20)  # EIP-7702 delegation
    # USDC/WETH pool at 2000 USDC per WETH (token0 = WETH since 0x42.. < 0x83..)
    d.test.chain.add_pool(make_pool(WETH, USDC, tick_for(2000 * 10**6 / 10**18), address=addr(0x33)))
    d._gas_topup(_low_gas_wallet())
    assert not [c for c in d.rb.calls if c[0] == "unwrap_weth"]
    swap = [c for c in d.rb.calls if c[:2] == ("swap_to_eth", "live")][0]
    assert swap[1] == "live" and swap[2] == USDC
    assert 1_000_000 < swap[3] < 1_100_000  # ~0.0005 ETH x $2000 x 1.03 of USDC (6 decimals)
    assert 0.0005e18 < swap[4] < 0.00055e18  # ~0.0005 ETH bought with a 3% buffer, minus fee and slippage
    assert events(d, "unwrap")[-1]["detail"].startswith("swapped")


def test_plain_eoa_still_unwraps_weth(make_daemon):
    d = make_daemon(live_mode=True, gas_reserve_eth=0.0003, unwrap_chunk_eth=0.0005)
    d.test.chain.w3.eth.get_code = lambda a: b""
    d._gas_topup(_low_gas_wallet())
    assert [(c[0], c[1]) for c in d.rb.calls] == [("unwrap_weth", "sim"), ("unwrap_weth", "live")]


def test_failed_gas_topup_is_logged_and_does_not_raise(make_daemon):
    d = make_daemon(live_mode=True, gas_reserve_eth=0.0003)
    d.test.chain.w3.eth.get_code = lambda a: bytes.fromhex("ef0100") + bytes(20)
    d.test.chain.add_pool(make_pool(WETH, USDC, tick_for(2000 * 10**6 / 10**18), address=addr(0x33)))
    d.rb.swap_to_eth_error = RuntimeError("execution reverted")
    wallet = _low_gas_wallet()
    assert d._gas_topup(wallet) is wallet  # unchanged; allocation goes on with its own per-send ETH checks
    assert "gas top-up failed" in events(d, "error")[-1]["detail"]


def test_gas_topup_is_planned_not_sent_when_dry_run_or_killed(make_daemon):
    for d in (make_daemon(live_mode=False), make_daemon(live_mode=True, killed=True)):
        d.test.chain.w3.eth.get_code = lambda a: bytes.fromhex("ef0100") + bytes(20)
        d._gas_topup(_low_gas_wallet())
        assert not d.rb.calls


def test_dry_run_tick_credits_the_soak_gate_and_status_shows_it(make_daemon):
    d = make_daemon(live_mode=False)
    d.tick()
    d.tick()
    soak = json.loads((d.root / "soak.json").read_text())
    assert soak["schema"] == "aero-lp-soak/1" and soak["accumulated_s"] >= 0
    status = json.loads((d.root / "status.json").read_text())
    assert status["gates"]["soak_ok"] is False and status["gates"]["research_ok"] is False


def test_live_tick_does_not_write_a_soak_record(make_daemon):
    d = make_daemon(live_mode=True)
    d.tick()
    assert not (d.root / "soak.json").exists()
