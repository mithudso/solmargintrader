"""Transaction-scoped accounting and receipt-recovery regressions."""

from __future__ import annotations

import pytest
from test_executor import HUGE, OWNER, T1, FakeChain, FakeRunner, WalletRunner, journal_runner, make_position

from aero_lp import clmath
from aero_lp.executor import ExecConfig, RebalanceError, Rebalancer, StageResult
from aero_lp.strategy import Range


def test_topup_drift_aborts_before_swapping_and_restakes():
    pos = make_position(True, tick=-199700)

    class Drift(WalletRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label == "gauge.withdraw":
                self.sqrt_p = clmath.get_sqrt_ratio_at_tick(pos.pool.tick + 200)
                r.sqrt_price_x96 = self.sqrt_p
            return r

    runner = Drift(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="spot moved") as exc:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 50 * 10**6, runner, 2232, 1)
    assert exc.value.partial.staked
    assert not any(t.label.startswith("swap") for t in runner.txs)


def test_incoming_transfer_during_remove_never_enters_rebalance_budget():
    pos = make_position(False)

    class Incoming(FakeRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label.startswith("remove"):
                self.bal[T1] += 10**9
                return StageResult(r.logs, dict(self.bal), sqrt_price_x96=self.sqrt_p)
            return r

    runner = Incoming(pos, pos.pool.sqrt_price_x96)
    Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(
        pos, Range(pos.tick_lower, pos.tick_upper), False, runner, 2232, 1
    )
    assert runner.minted["amount1Desired"] == pos.amount1
    assert runner.bal[T1] >= HUGE + 10**9


def test_increase_receipt_survives_failed_state_read():
    pos = make_position(True)

    class FailRead(WalletRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label == "increaseLiquidity":
                raise RuntimeError("RPC could not serve state at block 101")
            return r

    runner = FailRead(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError) as exc:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232, 1)
    assert exc.value.partial.stages == ["unstake", "increase", "stake"]
    assert exc.value.partial.amounts_in_position == (0, 10**6)


def test_missing_remove_transfer_evidence_aborts_before_spending():
    pos = make_position(False)

    class Missing(FakeRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label.startswith("remove"):
                r.logs = []
            return r

    runner = Missing(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="no token proceeds"):
        Rebalancer(FakeChain(), OWNER, ExecConfig()).rebalance(
            pos, Range(pos.tick_lower, pos.tick_upper), False, runner, 2232, 1
        )
    assert not any(t.label.startswith(("swap", "mint")) for t in runner.txs)


def test_actual_mint_amounts_come_from_confirmed_increase_receipt():
    pos = make_position(False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).deploy(
        pos.pool, Range(-199700, -198700), False, 3 * 10**15, 0, runner, 2232, 1
    )
    assert res.amounts_in_position == tuple(int(runner.minted[f"amount{i}Desired"] * 0.999) for i in (0, 1))


def test_unrelated_incoming_transfer_during_topup_unstake_stays_out_of_budget():
    pos = make_position(True)

    class Incoming(WalletRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label == "gauge.withdraw":
                self.bal[T1] += 10**9
                r.balances[T1] += 10**9
            return r

    runner = Incoming(pos, pos.pool.sqrt_price_x96)
    runner.unstake_fees1 = 100_000
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(pos, 0, 10**6, runner, 2232, 1)
    assert runner.increased["amount1Desired"] == 1_100_000
    assert res.amounts_in_position == (0, 1_100_000)


def test_mint_without_increase_evidence_stops_but_preserves_new_nft():
    pos = make_position(False)

    class Missing(WalletRunner):
        def execute(self, txs):
            r = super().execute(txs)
            if txs and txs[-1].label.startswith("mint"):
                r.logs = [lg for lg in r.logs if len(lg["topics"]) != 2]
                self.confirmed[-1].logs = r.logs
            return r

    runner = Missing(pos, pos.pool.sqrt_price_x96)
    with pytest.raises(RebalanceError, match="IncreaseLiquidity receipt missing") as exc:
        Rebalancer(FakeChain(), OWNER, ExecConfig()).deploy(
            pos.pool, Range(-199700, -198700), True, 3 * 10**15, 0, runner, 2232, 1
        )
    assert exc.value.partial.new_token_id == 777
    assert any("amounts unknown" in note for note in exc.value.partial.notes)
    assert not any(t.label == "gauge.deposit" for t in runner.txs)


def test_live_increase_receipt_is_kept_before_failed_postreceipt_read(monkeypatch, tmp_path):
    from test_executor import ACCT, T0, FakeEth, LaggingChain, increase_log

    from aero_lp.executor import LiveRunner, PlannedTx, RebalanceResult

    class Eth(FakeEth):
        def wait_for_transaction_receipt(self, h, timeout):
            receipt = super().wait_for_transaction_receipt(h, timeout)
            receipt["logs"] = [increase_log(42, 100, 200)]
            return receipt

    monkeypatch.setattr(LiveRunner, "READ_RETRY_DELAY_S", 0)
    runner = journal_runner(tmp_path, LaggingChain(Eth(), 10**6), ACCT, [T0, T1], ExecConfig())
    rb = Rebalancer(FakeChain(), OWNER, ExecConfig())
    tx = PlannedTx(
        "increaseLiquidity",
        rb.npm.address,
        rb.npm.encode_abi("increaseLiquidity", args=[(42, 100, 200, 0, 0, 1800000000)]),
    )
    with pytest.raises(RebalanceError, match="could not serve state") as exc:
        rb._wrap("topup", RebalanceResult(42, False, [], [], {}), runner, lambda: runner.execute([tx]))
    assert exc.value.partial.stages == ["increase"]
    assert exc.value.partial.amounts_in_position == (100, 200)
    assert exc.value.partial.tx_hashes == runner.sent_hashes


def test_repeated_transaction_labels_preserve_total_gas(tmp_path):
    from test_executor import ACCT, T0, TX, FakeEth, LaggingChain

    runner = journal_runner(tmp_path, LaggingChain(FakeEth(), 0), ACCT, [T0], ExecConfig())
    runner.execute([TX, TX])
    assert sum(runner.gas_used.values()) == 180_000


def test_capped_topup_leaves_unstake_proceeds_in_wallet():
    pos = make_position(True)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    runner.unstake_fees1 = 300_000
    res = Rebalancer(FakeChain(), OWNER, ExecConfig()).topup(
        pos, 0, 1_000_000, runner, 2232, 1, include_unstake_proceeds=False
    )
    assert runner.increased["amount1Desired"] == 1_000_000
    assert res.amounts_in_position == (0, 1_000_000)
    assert runner.bal[T1] == HUGE - 1_000_000 + 300_000
