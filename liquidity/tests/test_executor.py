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


def test_missing_aero_on_unstake_is_flagged():
    pos = make_position(staked=True)
    pos.earned_aero = 3 * 10**18

    class NoAeroRunner(FakeRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if any(t.label == "gauge.withdraw" for t in txs):
                self.bal[AERO] -= 5 * 10**18  # undo the fake payout: reward deferred / forfeited
                r = StageResult(r.logs, dict(self.bal), sqrt_price_x96=self.sqrt_p)
            return r

    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(
        pos, Range(-199700, -198700), True, NoAeroRunner(pos, pos.pool.sqrt_price_x96), 2232, 1
    )
    assert res.aero_claimed == 0 and any("deferredEmissions" in n for n in res.notes)


def test_withdraw_staked_position_unstakes_removes_and_reports_received_amounts():
    pos = make_position(staked=True)
    runner = FakeRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).withdraw(pos, runner)
    assert res.stages == ["unstake", "remove"]
    assert [t.label for t in runner.txs] == ["gauge.withdraw", "remove liquidity + collect + burn"]
    assert res.amounts_in_position == (pos.amount0, pos.amount1)
    assert res.aero_claimed == 5 * 10**18 and res.new_token_id is None


def test_withdraw_unstaked_position_has_no_gauge_step():
    pos = make_position(staked=False)
    runner = FakeRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).withdraw(pos, runner)
    assert res.stages == ["remove"] and len(runner.txs) == 1


def test_withdraw_failure_is_wrapped_with_partial_result():
    from aero_lp.executor import RebalanceError

    pos = make_position(staked=True)

    class FailRemove(FakeRunner):
        def execute(self, txs):
            if any(t.label.startswith("remove") for t in txs):
                raise RuntimeError("reverted: PSC")
            return super().execute(txs)

    try:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).withdraw(pos, FailRemove(pos, pos.pool.sqrt_price_x96))
    except RebalanceError as e:
        assert e.partial.stages == ["unstake"] and "withdraw failed" in str(e)
    else:
        raise AssertionError("expected RebalanceError")


# ---------------------------------------------------------------- deploy, topup, claim, collect, swap_exact, unwrap


FEES1 = 3 * 10**5  # fees the unstake collects, in token1 raw units
CLAIM = 2 * 10**18


class WalletRunner(FakeRunner):
    """FakeRunner plus the labels the new operations send; every executed tx adds a fixed fee."""

    fee_wei = 0

    def __init__(self, *a):
        super().__init__(*a)
        self.increased: dict = {}
        self.fail_on: str | None = None
        self.fail_always: set[str] = set()
        self.unstake_fees1 = 0

    def execute(self, txs):
        logs = []
        for tx in txs:
            if tx.label in self.fail_always or tx.label == self.fail_on:
                self.fail_on = None
                raise RuntimeError(f"tx '{tx.label}' reverted")
            self.fee_wei += 1_000
            if tx.label == "gauge.claimEmissions":
                self.txs.append(tx)
                self.bal[AERO] += CLAIM
            elif tx.label == "collect":
                self.txs.append(tx)
                self.bal[T0] += 10**15
                self.bal[T1] += 7
            elif tx.label == "increaseLiquidity":
                self.txs.append(tx)
                self.increased = self_npm().decode_function_input(tx.data)[1]["params"]
                self.bal[T0] -= self.increased["amount0Desired"]
                self.bal[T1] -= self.increased["amount1Desired"]
            elif tx.label == "weth.withdraw":
                self.txs.append(tx)
            else:
                logs += super().execute([tx]).logs
                if tx.label == "gauge.withdraw":
                    self.bal[T1] += self.unstake_fees1
        return StageResult(logs, dict(self.bal), sqrt_price_x96=self.sqrt_p)


def test_swap_exact_reports_the_measured_output_and_checks_its_arguments():
    pos = make_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    amount = 10**15
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_exact(pos.pool, T0, amount, runner, 123)
    price = clmath.sqrtx96_to_price(pos.pool.sqrt_price_x96)
    assert res.amount_out == int(amount * price * 0.999) and res.stages == ["swap"]
    params = W3.eth.contract(abi=abi.SWAP_ROUTER).decode_function_input(runner.txs[-1].data)[1]["params"]
    assert (params["tokenIn"], params["tokenOut"], params["amountIn"], params["amountOutMinimum"]) == (
        T0,
        T1,
        amount,
        123,
    )
    # the other direction sells token1 for token0
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_exact(pos.pool, T1, 10**6, runner, 1)
    assert res.amount_out == int(10**6 / price * 0.999)
    with pytest.raises(ValueError, match="not a token of pool"):
        Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_exact(pos.pool, AERO, 1, runner, 0)
    with pytest.raises(ValueError, match="amount_in"):
        Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_exact(pos.pool, T0, 0, runner, 0)


def test_swap_exact_failure_carries_the_gas_already_paid():
    pos = make_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.fail_always = {f"swap {10**15}"}
    with pytest.raises(RebalanceError) as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_exact(pos.pool, T0, 10**15, runner, 1)
    assert e.value.partial.fee_wei == 1_000  # the approve went through


def test_claim_reports_only_the_aero_that_arrived():
    pos = make_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).claim(pos, runner)
    assert res.aero_claimed == CLAIM and res.stages == ["claim"] and res.fee_wei == 1_000
    _, args = W3.eth.contract(abi=abi.CL_GAUGE).decode_function_input(runner.txs[0].data)
    assert args["_account"] == OWNER and args["_recipient"] == OWNER and args["_tokenIds"] == [42]


def test_collect_reports_the_fees_that_arrived_and_never_touches_liquidity():
    pos = make_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).collect(pos, runner)
    assert res.amounts_in_position == (10**15, 7)
    fn, args = self_npm().decode_function_input(runner.txs[0].data)
    assert fn.fn_name == "collect" and args["params"]["recipient"] == OWNER


def test_unwrap_weth_sends_one_withdraw_for_the_amount():
    pos = make_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).unwrap_weth(5 * 10**14, runner)
    fn, args = W3.eth.contract(abi=abi.WETH).decode_function_input(runner.txs[0].data)
    assert fn.fn_name == "withdraw" and args["wad"] == 5 * 10**14 and res.stages == ["unwrap"]
    assert runner.txs[0].to == Web3.to_checksum_address(addresses.WETH)


def test_deploy_spends_only_the_designated_amounts_and_stakes():
    pos = make_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    pool = pos.pool
    new = Range(-199700, -198700)
    designated = 3 * 10**15  # token0 only; the wallet holds 1e30 of everything
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).deploy(pool, new, True, designated, 0, runner, 2232.0, 1.0)
    assert res.stages == ["swap", "mint", "stake"] and res.new_token_id == 777 and res.staked
    m = runner.minted
    swapped_out = runner.bal[T1] - HUGE + m["amount1Desired"] * 0.999
    assert m["amount0Desired"] <= designated
    assert m["amount0Desired"] + m["amount1Desired"] > 0
    assert m["amount1Desired"] <= int(swapped_out) + 1  # token1 can only come from our own swap
    assert m["tickLower"] == new.tick_lower and m["recipient"] == OWNER


def test_deploy_without_gauge_leaves_the_nft_unstaked_with_a_note():
    pos = make_position(staked=False)
    pos.pool.gauge_alive = False
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).deploy(
        pos.pool, Range(-199700, -198700), True, 3 * 10**15, 0, runner, 2232.0, 1.0
    )
    assert not res.staked and any("gauge not activated" in n for n in res.notes)


def _one_sided_topup_position(staked: bool):
    """The price sits above the range, so the position takes token1 only and no swap is needed."""
    return make_position(staked=staked)


def test_staked_topup_includes_the_fees_the_unstake_collected_even_without_a_swap():
    pos = _one_sided_topup_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.unstake_fees1 = FEES1
    designated = 10**6
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, designated, runner, 2232.0, 1.0)
    assert res.stages == ["unstake", "increase", "stake"] and res.staked
    # designated amount + fees collected by the unstake, and nothing from the 1e30 wallet balance
    assert runner.increased["amount1Desired"] == designated + FEES1
    assert runner.increased["amount0Desired"] == 0
    labels = [t.label for t in runner.txs]
    assert labels[0] == "gauge.withdraw" and labels[-2:] == ["npm.approve(gauge)", "gauge.deposit"]


def test_unstaked_topup_uses_exactly_the_designated_amounts():
    pos = _one_sided_topup_position(staked=False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232.0, 1.0)
    assert res.stages == ["increase"] and runner.increased["amount1Desired"] == 10**6
    assert not any(t.label.startswith("gauge") for t in runner.txs)


def test_topup_with_a_swap_still_stays_inside_the_designated_amounts():
    pos = make_position(staked=False, tick=-199700)  # in range: the deposit needs both tokens
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    designated = 5 * 10**6
    Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, designated, runner, 2232.0, 1.0)
    inc = runner.increased
    swap_out0 = runner.bal[T0] - HUGE + inc["amount0Desired"]
    assert inc["amount0Desired"] > 0 and inc["amount0Desired"] <= swap_out0
    assert inc["amount1Desired"] <= designated


def test_failed_increase_puts_the_unstaked_nft_back_in_the_gauge():
    pos = _one_sided_topup_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.fail_on = "increaseLiquidity"
    with pytest.raises(RebalanceError, match="topup failed") as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232.0, 1.0)
    assert [t.label for t in runner.txs][-2:] == ["npm.approve(gauge)", "gauge.deposit"]
    assert e.value.partial.staked and any("restaked" in n for n in e.value.partial.notes)


def test_failed_restake_is_reported_with_the_increase_already_done():
    pos = _one_sided_topup_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.fail_always = {"gauge.deposit"}
    with pytest.raises(RebalanceError) as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232.0, 1.0)
    partial = e.value.partial
    assert "increase" in partial.stages and partial.amounts_in_position[1] > 0 and not partial.staked
    assert any("restake also failed" in n for n in partial.notes)


def test_failure_before_the_unstake_does_not_attempt_a_restake():
    pos = _one_sided_topup_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.fail_always = {"gauge.withdraw"}
    with pytest.raises(RebalanceError):
        Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232.0, 1.0)
    assert runner.txs == []


def test_gas_paid_before_a_failure_is_carried_by_rebalance_and_withdraw_results():
    pos = make_position(staked=True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.fail_always = {"npm.approve(gauge)"}  # fails after unstake, remove, swap, mint all succeeded
    with pytest.raises(RebalanceError) as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, Range(-199700, -198700), True, runner, 2232.0, 1.0)
    assert e.value.partial.fee_wei == runner.fee_wei > 0
    ok = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).withdraw(pos, ok)
    assert res.fee_wei == ok.fee_wei == 2_000
    bad = WalletRunner(pos, pos.pool.sqrt_price_x96)
    bad.fail_always = {"remove liquidity + collect + burn"}
    with pytest.raises(RebalanceError) as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).withdraw(pos, bad)
    assert e.value.partial.fee_wei == 1_000  # the unstake was paid for


def test_receipt_fee_covers_execution_and_l1_data_fee_in_any_encoding():
    from aero_lp.executor import receipt_fee_wei

    base = {"gasUsed": 100, "effectiveGasPrice": 7}
    assert receipt_fee_wei(base) == 700
    assert receipt_fee_wei({**base, "l1Fee": "0x10"}) == 716
    assert receipt_fee_wei({**base, "l1Fee": 5}) == 705
    assert receipt_fee_wei({**base, "l1Fee": None, "effectiveGasPrice": None}) == 0
    assert receipt_fee_wei({"gasUsed": 3}) == 0


class MintReadFails(WalletRunner):
    """The mint receipt arrives (its Transfer log is recorded) but the follow-up state read then fails."""

    def __init__(self, *a):
        super().__init__(*a)
        self.logs: list = []

    def execute(self, txs):
        if any(t.label.startswith("mint") for t in txs):
            r = super().execute(txs)
            self.logs.extend(r.logs)
            raise RuntimeError("RPC could not serve state at block 101")
        return super().execute(txs)


def test_a_minted_nft_is_recovered_from_the_logs_when_the_post_receipt_read_fails():
    pos = make_position(staked=False)
    runner = MintReadFails(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="could not serve state") as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).deploy(
            pos.pool, Range(-199700, -198700), True, 3 * 10**15, 0, runner, 2232.0, 1.0
        )
    p = e.value.partial
    assert p.new_token_id == 777 and any("was minted" in n for n in p.notes)
    assert sum(p.amounts_in_position) > 0  # so the caller can book the deposit


def test_a_rebalance_whose_mint_read_fails_still_reports_the_new_nft():
    pos = make_position(staked=True)
    runner = MintReadFails(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError) as e:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(pos, Range(-199700, -198700), True, runner, 2232.0, 1.0)
    assert e.value.partial.new_token_id == 777


class FakeEthWithLogs(FakeEth):
    mint_topic0 = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().removeprefix("0x")
    status = 1

    def wait_for_transaction_receipt(self, h, timeout):
        self.block_no += 1
        log = {
            "address": addresses.NONFUNGIBLE_POSITION_MANAGER,
            "topics": [
                HexBytes(self.mint_topic0),
                HexBytes("0x" + "0" * 64),
                HexBytes("0x" + "0" * 24 + OWNER[2:].lower()),
                HexBytes(hex(777)),
            ],
            "data": b"",
        }
        return {
            "status": self.status,
            "gasUsed": 90_000,
            "effectiveGasPrice": 10**6,
            "l1Fee": "0x10",
            "blockNumber": self.block_no,
            "logs": [log],
        }


def test_live_runner_keeps_receipt_logs_when_the_state_read_after_them_fails(monkeypatch):
    from aero_lp.executor import minted_token_id

    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    runner = LiveRunner(LaggingChain(FakeEthWithLogs(), 10**6), ACCT, [T0], ExecConfig())
    with pytest.raises(RuntimeError, match="could not serve state"):
        runner.execute([TX])
    assert minted_token_id(runner.logs, addresses.NONFUNGIBLE_POSITION_MANAGER, OWNER) == 777
    assert runner.chain.min_block == 101  # later balance reads are pinned to at least this block


def test_live_runner_books_the_gas_of_a_reverted_transaction():
    eth = FakeEthWithLogs()
    eth.status = 0
    runner = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig())
    with pytest.raises(RuntimeError, match="reverted"):
        runner.execute([TX])
    assert runner.fee_wei == 90_000 * 10**6 + 16


def test_swap_to_eth_keeps_weth_in_the_router_then_unwraps_to_the_owner():
    pool = make_position(staked=False).pool  # WETH/USDC
    runner = FakeRunner(make_position(staked=False), pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).swap_to_eth(pool, T1, 1_000_000, 4 * 10**14, runner)
    assert res.stages == ["swap_to_eth"]
    tx = runner.txs[-1]
    router = W3.eth.contract(address=addresses.SWAP_ROUTER, abi=abi.SWAP_ROUTER)
    fn, args = router.decode_function_input(tx.data)
    assert fn.fn_name == "multicall" and len(args["data"]) == 2
    f1, a1 = router.decode_function_input(args["data"][0])
    f2, a2 = router.decode_function_input(args["data"][1])
    assert f1.fn_name == "exactInputSingle" and f2.fn_name == "unwrapWETH9"
    p = a1["params"]
    assert p["tokenIn"] == T1 and p["tokenOut"] == T0 and p["amountIn"] == 1_000_000
    assert p["recipient"] == "0x0000000000000000000000000000000000000000"  # router holds the WETH mid-transaction
    assert a2["amountMinimum"] == 4 * 10**14 and a2["recipient"] == OWNER
