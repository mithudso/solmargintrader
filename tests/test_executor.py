"""Offline tests of the rebalance sequence with a fake chain and a fake runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from hexbytes import HexBytes
from web3 import Web3

from aero_lp import abi, addresses, clmath
from aero_lp.chain import PoolState, PositionState, Token
from aero_lp.executor import ExecConfig, LiveRunner, PlannedTx, RebalanceError, Rebalancer, StageResult
from aero_lp.strategy import Range

W3 = Web3()
OWNER = Web3.to_checksum_address("0x" + "ab" * 20)
GAUGE = Web3.to_checksum_address("0x" + "ga".replace("g", "c") * 20)
T0 = Web3.to_checksum_address(addresses.WETH)
T1 = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
AERO = Web3.to_checksum_address(addresses.AERO_TOKEN)
HUGE = 10**30  # pre-existing wallet balance the bot must never touch


class FakeChain:
    def __init__(self):
        self.w3 = W3
        self.npm = W3.eth.contract(address=addresses.NONFUNGIBLE_POSITION_MANAGER, abi=abi.NPM)

    def _c(self, address, contract_abi):
        return W3.eth.contract(address=Web3.to_checksum_address(address), abi=contract_abi)

    def gauge_contract(self, gauge):
        return self._c(gauge, abi.CL_GAUGE)

    def erc20_balances(self, owner, tokens):
        return [HUGE for _ in tokens]


class FakeRunner:
    """Emulates token flows per tx label; records every planned tx."""

    def __init__(self, pos: PositionState, sqrt_p: int):
        self.bal = {T0: HUGE, T1: HUGE, AERO: HUGE}
        self.pos, self.sqrt_p = pos, sqrt_p
        self.txs: list[PlannedTx] = []
        self.minted: dict = {}

    def block_timestamp(self) -> int:
        return 1_800_000_000

    def execute(self, txs):
        logs = []
        for tx in txs:
            self.txs.append(tx)
            if tx.label == "gauge.withdraw":
                self.bal[AERO] += 5 * 10**18
            elif tx.label.startswith("remove"):
                self.bal[T0] += self.pos.amount0
                self.bal[T1] += self.pos.amount1
            elif tx.label.startswith("swap"):
                _, args = W3.eth.contract(abi=abi.SWAP_ROUTER).decode_function_input(tx.data)
                p = args["params"]
                price = clmath.sqrtx96_to_price(self.sqrt_p)
                out = p["amountIn"] * price * 0.999 if p["tokenIn"] == T0 else p["amountIn"] / price * 0.999
                self.bal[p["tokenIn"]] -= p["amountIn"]
                self.bal[p["tokenOut"]] += int(out)
            elif tx.label.startswith("mint"):
                _, args = self_npm().decode_function_input(tx.data)
                m = args["params"]
                self.bal[T0] -= int(m["amount0Desired"] * 0.999)
                self.bal[T1] -= int(m["amount1Desired"] * 0.999)
                self.minted = m
                topic0 = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().removeprefix("0x")
                logs.append(
                    {
                        "address": addresses.NONFUNGIBLE_POSITION_MANAGER,
                        "topics": [topic0, "0x" + "0" * 64, "0x" + "0" * 24 + OWNER[2:].lower(), hex(777)],
                        "data": "0x",
                    }
                )
        return StageResult(logs, dict(self.bal), sqrt_price_x96=self.sqrt_p)


def self_npm():
    return W3.eth.contract(address=addresses.NONFUNGIBLE_POSITION_MANAGER, abi=abi.NPM)


def make_position(staked: bool, tick: int = -199211) -> PositionState:
    sp = clmath.get_sqrt_ratio_at_tick(tick)
    pool = PoolState(
        address=Web3.to_checksum_address("0x" + "11" * 20),
        token0=Token(T0, "WETH", 18),
        token1=Token(T1, "USDC", 6),
        tick_spacing=100,
        fee_pips=500,
        unstaked_fee_pips=50_000,
        sqrt_price_x96=sp,
        tick=tick,
        liquidity=10**18,
        staked_liquidity=10**18,
        gauge=GAUGE,
        gauge_alive=True,
        fee_growth_global0=0,
        fee_growth_global1=0,
        reward_growth_global=0,
        block=1,
        timestamp=1,
    )
    tl, tu = -200100, -199300  # price is above the range -> position is all token1
    liq = 10**15
    a0, a1 = clmath.get_amounts_for_liquidity(
        sp, clmath.get_sqrt_ratio_at_tick(tl), clmath.get_sqrt_ratio_at_tick(tu), liq
    )
    return PositionState(42, OWNER, staked, pool, tl, tu, liq, a0, a1, 0, 0)


def test_staked_rebalance_sequence_and_uses_only_position_funds():
    pos = make_position(staked=True)
    assert not pos.in_range and pos.amount0 == 0 and pos.amount1 > 0
    runner = FakeRunner(pos, pos.pool.sqrt_price_x96)
    new = Range(-199700, -198700)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, new, True, runner, 2232.0, 1.0)

    assert res.stages[0] == "unstake" and res.stages[1] == "remove"
    assert "swap" in res.stages and res.stages[-2:] == ["mint", "stake"]
    assert res.new_token_id == 777 and res.staked
    assert res.aero_claimed == 5 * 10**18
    labels = [t.label for t in runner.txs]
    assert labels[0] == "gauge.withdraw" and labels[-1] == "gauge.deposit"
    m = runner.minted
    # never more than what came out of the position (+ swap proceeds); pre-existing HUGE balance untouched
    assert m["amount1Desired"] <= pos.amount1
    assert m["amount0Desired"] > 0  # swapped into token0 for the new two-sided range
    assert m["tickLower"] == new.tick_lower and m["tickUpper"] == new.tick_upper
    assert m["recipient"] == OWNER and m["sqrtPriceX96"] == 0
    assert m["amount0Min"] < m["amount0Desired"] and m["amount1Min"] < m["amount1Desired"]


def test_unstaked_rebalance_skips_gauge_and_can_stay_unstaked():
    pos = make_position(staked=False)
    runner = FakeRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, Range(-199700, -198700), False, runner, 2232, 1)
    assert res.stages[0] == "remove" and "unstake" not in res.stages and "stake" not in res.stages
    assert not res.staked


def test_remove_call_has_slippage_mins_and_burns():
    pos = make_position(staked=False, tick=-199700)  # inside -> both tokens
    pos.tick_lower, pos.tick_upper = -200100, -199300
    sa, sb = clmath.get_sqrt_ratio_at_tick(-200100), clmath.get_sqrt_ratio_at_tick(-199300)
    pos.amount0, pos.amount1 = clmath.get_amounts_for_liquidity(pos.pool.sqrt_price_x96, sa, sb, pos.liquidity)
    tx = Rebalancer(FakeChain(), OWNER, ExecConfig(max_slippage_bps=100)).remove_calls(pos, 123, 0.01)
    _, args = self_npm().decode_function_input(tx.data)
    inner = args["data"]
    assert len(inner) == 3  # decreaseLiquidity, collect, burn
    fn, dec = self_npm().decode_function_input(inner[0])
    assert fn.fn_name == "decreaseLiquidity"
    p = dec["params"]
    assert p["liquidity"] == pos.liquidity and p["deadline"] == 123
    assert p["amount0Min"] == int(pos.amount0 * 0.99) and p["amount1Min"] == int(pos.amount1 * 0.99)
    assert self_npm().decode_function_input(inner[2])[0].fn_name == "burn"


# ---------------------------------------------------------------- partial failure, deadlines, live reads


class StakeFailsRunner(FakeRunner):
    """Everything works until the stake stage, which reverts."""

    def execute(self, txs):
        if txs[-1].label == "gauge.deposit":
            raise RuntimeError("tx 'gauge.deposit' reverted")
        return super().execute(txs)


def test_failed_stake_after_mint_reports_new_token_id_instead_of_losing_it():
    pos = make_position(staked=True)
    runner = StakeFailsRunner(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="after stage 'mint'") as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, Range(-199700, -198700), True, runner, 2232.0, 1.0)
    partial = e.value.partial
    assert partial.new_token_id == 777 and not partial.staked
    assert partial.stages[-1] == "mint" and "stake" not in partial.stages


class ClockRunner(FakeRunner):
    """Each stage takes 100 s of chain time."""

    def __init__(self, *a):
        super().__init__(*a)
        self.now = 1_800_000_000

    def block_timestamp(self) -> int:
        self.now += 100
        return self.now


def test_every_stage_gets_a_fresh_deadline():
    pos = make_position(staked=False)
    runner = ClockRunner(pos, pos.pool.sqrt_price_x96)
    Rebalancer(FakeChain(), OWNER, ExecConfig(deadline_s=600)).rebalance(
        pos, Range(-199700, -198700), False, runner, 2232, 1
    )
    deadlines = []
    for tx in runner.txs:
        if tx.label.startswith("remove"):
            inner = self_npm().decode_function_input(tx.data)[1]["data"]
            deadlines.append(self_npm().decode_function_input(inner[0])[1]["params"]["deadline"])
        elif tx.label.startswith("swap"):
            p = W3.eth.contract(abi=abi.SWAP_ROUTER).decode_function_input(tx.data)[1]["params"]
            deadlines.append(p["deadline"])
        elif tx.label.startswith("mint"):
            deadlines.append(self_npm().decode_function_input(tx.data)[1]["params"]["deadline"])
    assert len(deadlines) >= 3
    assert deadlines == sorted(deadlines) and len(set(deadlines)) == len(deadlines)


class SpentElsewhereRunner(FakeRunner):
    """The wallet balance drops during the remove stage (e.g. a concurrent outgoing transfer)."""

    def execute(self, txs):
        r = super().execute(txs)
        if txs[0].label.startswith("remove"):
            self.bal[T0] -= 10**20
            self.bal[T1] -= 10**20
            r = StageResult(r.logs, dict(self.bal), sqrt_price_x96=self.sqrt_p)
        return r


def test_negative_balance_delta_is_clamped_and_nothing_is_minted():
    pos = make_position(staked=False)
    runner = SpentElsewhereRunner(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="nothing to mint"):
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, Range(-199700, -198700), False, runner, 2232, 1)
    assert not any(t.label.startswith(("mint", "swap", "approve")) for t in runner.txs)


def test_exec_config_rejects_unprotected_values():
    for bad in (
        {"max_slippage_bps": 10_000},
        {"max_slippage_bps": -1},
        {"deadline_s": 0},
        {"max_priority_fee_gwei": -0.1},
    ):
        with pytest.raises(ValueError):
            ExecConfig(**bad)


class FakeEth:
    max_priority_fee = 10**5

    def __init__(self):
        self.nonce, self.block_no, self.sent = 0, 100, []

    def get_block(self, tag):
        return {"timestamp": 1_800_000_000, "baseFeePerGas": 10**6}

    def get_transaction_count(self, addr, tag):
        return self.nonce

    def estimate_gas(self, req):
        return 100_000

    send_error: Exception | None = None
    known: bool = False

    def send_raw_transaction(self, raw):
        if self.send_error:
            raise self.send_error
        self.nonce += 1
        self.sent.append(raw)
        return HexBytes(b"\x01" * 32)

    def get_transaction(self, h):
        if not self.known:
            raise ValueError("transaction not found")
        return {"hash": h}

    def wait_for_transaction_receipt(self, h, timeout):
        self.block_no += 1
        return {"status": 1, "gasUsed": 90_000, "blockNumber": self.block_no, "logs": []}


class LaggingChain:
    """erc20_balances / slot0 only succeed once the node has imported the requested block."""

    def __init__(self, eth: FakeEth, ready_after_calls: int):
        self.w3 = SimpleNamespace(eth=eth)
        self.eth, self.ready_after, self.calls = eth, ready_after_calls, []

    def _gate(self, block):
        self.calls.append(block)
        if len(self.calls) <= self.ready_after:
            raise ValueError("header not found")

    def erc20_balances(self, owner, tokens, block="latest"):
        self._gate(block)
        return [5 for _ in tokens]

    def _c(self, address, contract_abi):
        outer = self

        class _Slot0:
            def call(self, block_identifier="latest"):
                outer._gate(block_identifier)
                return [123]

        return SimpleNamespace(functions=SimpleNamespace(slot0=lambda: _Slot0()))


ACCT = SimpleNamespace(
    address=OWNER,
    sign_transaction=lambda req: SimpleNamespace(raw_transaction=b"raw", hash=HexBytes(b"\x01" * 32)),
)
TX = PlannedTx("approve", T0, "0x")


def test_live_runner_reads_state_at_the_receipt_block_and_waits_for_a_lagging_node(monkeypatch):
    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    eth = FakeEth()
    chain = LaggingChain(eth, ready_after_calls=2)
    runner = LiveRunner(chain, ACCT, [T0, T1], ExecConfig(), pool=Web3.to_checksum_address("0x" + "11" * 20))
    res = runner.execute([TX])
    assert res.balances == {T0: 5, T1: 5} and res.sqrt_price_x96 == 123
    assert set(chain.calls) == {101}  # never "latest": always the receipt's block
    assert len(chain.calls) == 4  # 2 failed + 1 ok balance read, then the slot0 read
    assert runner.sent_hashes == ["0x" + "01" * 32]


def test_live_runner_fails_loudly_if_the_node_never_catches_up(monkeypatch):
    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    runner = LiveRunner(LaggingChain(FakeEth(), 10**6), ACCT, [T0], ExecConfig())
    with pytest.raises(RuntimeError, match="could not serve state at block 101"):
        runner.execute([TX])
    assert runner.sent_hashes  # the broadcast hash is still on record


def test_send_error_after_node_accepted_the_tx_carries_on_to_the_receipt():
    eth = FakeEth()
    eth.send_error, eth.known = ValueError("already known"), True  # a transport retry hit the same tx twice
    res = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig()).execute([TX])
    assert res.tx_hashes == ["0x" + "01" * 32]


def test_send_error_for_an_unknown_tx_is_raised_but_the_hash_stays_on_record():
    eth = FakeEth()
    eth.send_error = ValueError("insufficient funds")
    runner = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig())
    with pytest.raises(ValueError, match="insufficient funds"):
        runner.execute([TX])
    assert runner.sent_hashes == ["0x" + "01" * 32]


def test_nonce_never_goes_backwards_on_a_lagging_node(monkeypatch):
    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    eth = FakeEth()
    eth.get_transaction_count = lambda addr, tag: 5  # stale: ignores our first transaction
    nonces = []
    acct = SimpleNamespace(
        address=OWNER,
        sign_transaction=lambda req: (
            nonces.append(req["nonce"]) or SimpleNamespace(raw_transaction=b"raw", hash=HexBytes(b"\x01" * 32))
        ),
    )
    LiveRunner(LaggingChain(eth, 0), acct, [T0], ExecConfig()).execute([TX, TX])
    assert nonces == [5, 6]


def test_estimate_gas_is_retried_for_a_lagging_node(monkeypatch):
    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    eth, calls = FakeEth(), []

    def flaky(req):
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("execution reverted")
        return 100_000

    eth.estimate_gas = flaky
    LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig()).execute([TX])
    assert len(calls) == 3


class DriftingRunner(FakeRunner):
    """Moves the pool price by `drift` ticks during the remove stage (a sandwich-style push)."""

    def __init__(self, pos, sqrt_p, drift_ticks):
        super().__init__(pos, sqrt_p)
        self.drift_ticks = drift_ticks

    def execute(self, txs):
        r = super().execute(txs)
        if any(t.label.startswith("remove") for t in txs):
            self.sqrt_p = clmath.get_sqrt_ratio_at_tick(self.pos.pool.tick + self.drift_ticks)
            r = StageResult(r.logs, r.balances, sqrt_price_x96=self.sqrt_p)
        return r


def test_price_drift_after_remove_aborts_before_any_swap():
    from aero_lp.executor import RebalanceError

    pos = make_position(staked=False)
    runner = DriftingRunner(pos, pos.pool.sqrt_price_x96, drift_ticks=250)
    try:
        Rebalancer(FakeChain(), OWNER, ExecConfig(max_stage_drift_bps=100)).rebalance(
            pos, Range(-199700, -198700), False, runner, 2232, 1
        )
    except RebalanceError as e:
        assert "moved" in str(e) and e.partial.stages == ["remove"]
    else:
        raise AssertionError("expected RebalanceError")
    assert not any(t.label.startswith("swap") for t in runner.txs)


def test_small_drift_is_tolerated_and_stage_hook_sees_every_stage():
    pos = make_position(staked=True)
    runner = DriftingRunner(pos, pos.pool.sqrt_price_x96, drift_ticks=20)
    seen: list[tuple[str, int | None]] = []
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(
        pos, Range(-199700, -198700), True, runner, 2232, 1, on_stage=lambda st, r: seen.append((st, r.new_token_id))
    )
    assert [s for s, _ in seen] == res.stages
    assert ("mint", 777) in seen  # the hook sees the new id before the stake stage runs


def test_hook_exception_aborts_with_partial_result():
    from aero_lp.executor import RebalanceError

    pos = make_position(staked=True)
    runner = FakeRunner(pos, pos.pool.sqrt_price_x96)

    def hook(stage, r):
        if stage == "remove":
            raise RuntimeError("operator abort")

    try:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(
            pos, Range(-199700, -198700), True, runner, 2232, 1, hook
        )
    except RebalanceError as e:
        assert e.partial.stages == ["unstake", "remove"]
    else:
        raise AssertionError("expected RebalanceError")
