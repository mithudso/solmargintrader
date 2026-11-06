"""Ambiguous broadcasts stay blocked until durable receipt and ownership reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from test_engine import make_engine, make_ev
from test_engine_audit import setup_live
from test_executor import T0, TX
from web3 import Web3

from aero_lp import engine as engine_module
from aero_lp.executor import RebalanceResult, SimRunner


@pytest.mark.parametrize("gas", [None, "0x0", "broken"])
def test_simrunner_requires_positive_measured_gas(gas):
    w3 = Web3()
    w3.eth.get_block = lambda block: {"timestamp": 1800000000}
    response = {"status": "0x1", "returnData": "0x"}
    if gas is not None:
        response["gasUsed"] = gas
    w3.provider.make_request = lambda *a: {"result": [{"calls": [response, {"returnData": "0x01"}]}]}
    runner = SimRunner(SimpleNamespace(w3=w3, head=lambda: (100, 1800000000)), "0x" + "ab" * 20, [T0])
    with pytest.raises(RuntimeError, match="gas"):
        runner.execute([TX])
    assert runner.history == []


@pytest.mark.parametrize("gas", [{}, {"tx": 0}, {"tx": -1}, {"tx": True}])
@pytest.mark.parametrize("operation", ["rebalance", "withdraw"])
def test_engine_rejects_unknown_sequence_gas(tmp_path, monkeypatch, gas, operation):
    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch)
    calls = []

    def run(*args, **kwargs):
        runner = args[3] if operation == "rebalance" else args[1]
        calls.append(runner)
        return RebalanceResult(None, False, [], [], gas)

    monkeypatch.setattr(engine_module, "Rebalancer", lambda *a: SimpleNamespace(**{operation: run}))
    with pytest.raises(RuntimeError, match="gas"):
        if operation == "rebalance":
            eng.rebalance(make_ev(), True, object())
        else:
            eng.withdraw(42, True, object())
    assert calls == ["sim"]


def test_live_runner_refuses_to_broadcast_without_durable_journal():
    from test_executor import ACCT, FakeEth, LaggingChain

    from aero_lp.executor import ExecConfig, LiveRunner

    eth = FakeEth()
    runner = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig())
    with pytest.raises(RuntimeError, match="journal"):
        runner.execute([TX])
    assert eth.sent == []


def mint_transaction():
    from test_executor import OWNER, T1, self_npm

    from aero_lp.executor import PlannedTx

    params = (T0, T1, 100, -199700, -198700, 0, 1_000_000, 0, 0, OWNER, 1800000000, 0)
    npm = self_npm()
    return PlannedTx("mint [-199700,-198700)", npm.address, npm.encode_abi("mint", args=[params]))


def late_mint_receipt():
    from hexbytes import HexBytes
    from test_executor import FakeEthWithLogs, increase_log

    receipt = FakeEthWithLogs().wait_for_transaction_receipt(HexBytes(b"\x01" * 32), 1)
    receipt["logs"].append(increase_log(777, 0, 1_000_000))
    return receipt


def test_journal_is_durable_before_send_and_blocks_another_runner(tmp_path):
    import json

    from test_executor import ACCT, OWNER, FakeEth, LaggingChain

    from aero_lp.executor import ExecConfig, LiveRunner
    from aero_lp.submissions import PendingSubmission, SubmissionJournal

    journal = SubmissionJournal(tmp_path / "submissions.json", OWNER)
    eth = FakeEth()
    original_send = eth.send_raw_transaction

    def send(raw):
        stored = json.loads(journal.path.read_text())
        assert len(stored["transactions"]) == 1
        entry = next(iter(stored["transactions"].values()))
        assert "data" not in entry and "raw_transaction" not in entry
        assert entry["receipt"] is None and entry["intent"]["kind"] == "mint"
        return original_send(raw)

    eth.send_raw_transaction = send
    eth.wait_for_transaction_receipt = lambda *a, **kw: (_ for _ in ()).throw(TimeoutError("receipt timeout"))
    runner = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), journal=journal)
    with pytest.raises(TimeoutError):
        runner.execute([mint_transaction()])
    restarted = SubmissionJournal(journal.path, OWNER)
    assert len(restarted.records()) == 1 and not restarted.records()[0]["processed"]
    other = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), journal=restarted)
    with pytest.raises(PendingSubmission, match="unresolved"):
        other.execute([TX])
    assert len(eth.sent) == 1
    with pytest.raises(PendingSubmission, match="unresolved"):
        runner.execute([TX])  # even emergency recovery cannot sign over its own ambiguous outcome


def test_late_mint_is_tracked_across_daemon_restart_before_retry(tmp_path, monkeypatch):
    from hexbytes import HexBytes
    from test_daemon import MAIN_TICK, USDC, WETH, _arm, _idle, make_pool, make_pos
    from test_daemon import make_daemon as daemon_fixture
    from test_executor import ACCT, OWNER, FakeChain, FakeEthWithLogs, LaggingChain

    from aero_lp import daemon as daemon_module
    from aero_lp.executor import ExecConfig, LiveRunner, RebalanceError, Rebalancer
    from aero_lp.submissions import PendingSubmission

    build = daemon_fixture.__wrapped__(tmp_path, monkeypatch)
    d = build(live_mode=True)
    pool = make_pool(WETH, USDC, MAIN_TICK)
    d.test.chain.add_pool(pool)
    eth = FakeEthWithLogs()
    eth.wait_for_transaction_receipt = lambda *a, **kw: (_ for _ in ()).throw(TimeoutError("receipt timeout"))
    rb = Rebalancer(FakeChain(), OWNER, ExecConfig())
    original = d.rb.deploy

    def deploy(pool, rng, stake, a0, a1, runner, u0, u1, on_stage=None):
        if runner[0] == "sim":
            return original(pool, rng, stake, a0, a1, runner, u0, u1, on_stage=on_stage)
        d.rb.calls.append(("deploy", "live", a0, a1, stake))
        real = LiveRunner(LaggingChain(eth, 0), ACCT, [T0, USDC], ExecConfig(), pool.address, journal=d.journal)
        return rb._wrap(
            "deploy", RebalanceResult(None, False, [], [], {}), real, lambda: real.execute([mint_transaction()])
        )

    monkeypatch.setattr(d.rb, "deploy", deploy)
    with pytest.raises(RebalanceError, match="receipt timeout"):
        d.deploy_arm(_arm(pool, 10), [_idle(USDC, 10, 10, 6)], None)
    assert len(eth.sent) == 1 and d.ledger.open_slots() == []

    def missing(_hash):
        raise RuntimeError("transaction receipt not found")

    d.test.chain.w3.eth.get_transaction_receipt = missing
    restarted = daemon_module.Daemon(d.cfg, True, signer=object(), root=d.root)
    with pytest.raises(PendingSubmission, match="unresolved"):
        restarted.deploy_arm(_arm(pool, 10), [_idle(USDC, 10, 10, 6)], None)
    assert restarted.rb.calls == [] and len(eth.sent) == 1
    receipt = late_mint_receipt()
    d.test.chain.w3.eth.get_transaction_receipt = lambda h: receipt
    pos = make_pos(777, staked=False, pool=pool)
    pos.amount0, pos.amount1 = 0, 1_000_000
    d.test.chain.positions[777] = pos
    restarted.deploy_arm(_arm(pool, 10), [_idle(USDC, 10, 10, 6)], None)
    assert [row["token_id"] for row in restarted.ledger.open_slots()] == [777]
    assert restarted.rb.calls == []  # the stale plan cannot create a second position in this pool
    assert restarted.ledger.pnl("777").deposited_usd == 1
    assert all(r["processed"] for r in restarted.journal.records())
    # Crash after SQLite commit but before journal completion: replay is financially idempotent.
    with restarted.journal._edit() as doc:
        doc["transactions"][HexBytes(b"\x01" * 32).to_0x_hex()]["processed"] = False
    again = daemon_module.Daemon(d.cfg, True, signer=object(), root=d.root)
    again._reconcile_submissions()
    assert again.ledger.pnl("777").deposited_usd == 1
    assert again.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='deposit'").fetchone()[0] == 1
    assert again.ledger.db.execute("SELECT COUNT(*) FROM transaction_effects WHERE effect='fee'").fetchone()[0] == 1


def proven_receipt(tx_hash, logs):
    return {
        "transactionHash": tx_hash,
        "status": 1,
        "blockNumber": 101,
        "gasUsed": 90000,
        "effectiveGasPrice": 10**6,
        "logs": logs,
    }


def test_late_rebalance_mint_recovers_engine_state_and_existing_slot(tmp_path, monkeypatch):
    from hexbytes import HexBytes
    from test_daemon import make_daemon as daemon_fixture
    from test_daemon import make_pos, open_slot
    from test_executor import OWNER, FakeChain, make_position

    from aero_lp.engine import Engine
    from aero_lp.executor import ExecConfig, Rebalancer
    from aero_lp.state import State

    d = daemon_fixture.__wrapped__(tmp_path, monkeypatch)(live_mode=True)
    pos = make_pos()
    d.test.chain.add_pool(pos.pool)
    open_slot(d)
    new = make_pos(777, staked=False, pool=pos.pool)
    d.test.chain.positions[777] = new
    eng = Engine.__new__(Engine)
    eng.cfg, eng.chain, eng.state = d.cfg, d.chain, State(d.cfg.state_file)
    eng.state.slot(42)
    eng.journal, eng.recovery_handler = d.journal, d._apply_submission
    remove = Rebalancer(FakeChain(), OWNER, ExecConfig()).remove_calls(make_position(True), 1800000000, 0.005)
    h0, h1 = HexBytes(b"\x02" * 32).to_0x_hex(), HexBytes(b"\x01" * 32).to_0x_hex()
    d.journal.before_submit(h0, 0, remove, "rebalance", pos.pool.address, [T0])
    d.journal.receipt(h0, proven_receipt(h0, []))
    d.journal.before_submit(h1, 1, mint_transaction(), "rebalance", pos.pool.address, [T0])
    d.journal.receipt(h1, late_mint_receipt())
    eng.reconcile_submissions()
    assert State(d.cfg.state_file).slot(42).current_token_id == 777
    assert d.ledger.slot_row("42")["token_id"] == 777
    assert d.ledger.pnl("42").deposited_usd == 40
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind='withdraw'").fetchone()[0] == 0


@pytest.mark.parametrize("kind", ["increase", "remove"])
def test_recovered_position_flows_are_idempotent(tmp_path, monkeypatch, kind):
    from hexbytes import HexBytes
    from test_daemon import make_daemon as daemon_fixture
    from test_daemon import make_pos, open_slot
    from test_executor import OWNER, T1, FakeChain, increase_log, make_position, self_npm, transfer_log

    from aero_lp.executor import ExecConfig, PlannedTx, Rebalancer

    d = daemon_fixture.__wrapped__(tmp_path, monkeypatch)(live_mode=True)
    pos = make_pos(staked=False)
    d.test.chain.add_pool(pos.pool)
    d.test.chain.positions[42] = pos
    open_slot(d)
    h = HexBytes(b"\x03" * 32).to_0x_hex()
    if kind == "increase":
        npm = self_npm()
        tx = PlannedTx(
            "increaseLiquidity",
            npm.address,
            npm.encode_abi("increaseLiquidity", args=[(42, 0, 1_000_000, 0, 0, 1800000000)]),
        )
        logs = [increase_log(42, 0, 1_000_000)]
    else:
        tx = Rebalancer(FakeChain(), OWNER, ExecConfig()).remove_calls(make_position(False), 1800000000, 0.005)
        logs = [transfer_log(T1, pos.pool.address, OWNER, 2_000_000)]
        del d.test.chain.positions[42]
    d.journal.before_submit(h, 0, tx, "one-operation", pos.pool.address, [T0, T1])
    d.journal.receipt(h, proven_receipt(h, logs))
    d._reconcile_submissions()
    with d.journal._edit() as doc:
        doc["transactions"][h]["processed"] = False
    d._reconcile_submissions()
    flow_kind = "topup" if kind == "increase" else "withdraw"
    assert d.ledger.db.execute("SELECT COUNT(*) FROM flows WHERE kind=?", (flow_kind,)).fetchone()[0] == 1
    assert d.ledger.pnl("42").withdrawn_usd == (2 if kind == "remove" else 0)
    assert d.ledger.pnl("42").deposited_usd == (41 if kind == "increase" else 40)


def test_every_known_rebalancer_intent_can_be_journaled():
    from test_executor import OWNER, T1, FakeChain, WalletRunner, make_position

    from aero_lp.executor import ExecConfig, Rebalancer
    from aero_lp.submissions import transaction_intent

    pos = make_position(False)
    rb = Rebalancer(FakeChain(), OWNER, ExecConfig())
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    rb.collect(pos, runner)
    rb.claim(pos, runner)
    rb.unwrap_weth(100, runner)
    rb.swap_to_eth(pos.pool, T1, 1_000_000, 1, runner)
    kinds = {transaction_intent(tx)["kind"] for tx in runner.txs}
    assert {"collect", "claim", "unwrap", "gas_swap", "approve"} <= kinds


def test_cli_recovery_cannot_consume_receipts_without_ledger_accounting(tmp_path, monkeypatch):
    from hexbytes import HexBytes
    from test_daemon import FakeMarket, make_pos
    from test_executor import OWNER

    from aero_lp.ledger import Ledger
    from aero_lp.state import State
    from aero_lp.submissions import SubmissionJournal

    eng = make_engine(tmp_path)
    eng.market = FakeMarket()
    pos = make_pos(777, staked=False)
    eng.chain = SimpleNamespace(min_block=None, position=lambda *a, **kw: pos, pool_state=lambda a: pos.pool)
    eng.journal = SubmissionJournal(tmp_path / "submissions.json", OWNER)
    h = HexBytes(b"\x01" * 32).to_0x_hex()
    eng.journal.before_submit(h, 0, mint_transaction(), "cli", pos.pool.address, [T0])
    eng.journal.receipt(h, late_mint_receipt())
    eng.reconcile_submissions()
    ledger = Ledger(tmp_path / "ledger.sqlite")
    assert ledger.slot_row("777")["token_id"] == 777
    assert ledger.pnl("777").deposited_usd == 1
    assert all(r["processed"] for r in eng.journal.records())
    assert State(eng.cfg.state_file).slots == {}  # allocation NFT is tracked by the ledger before management starts


def test_active_sequence_cannot_be_reconciled_or_interleaved(tmp_path):
    from test_executor import ACCT, OWNER, FakeEth, LaggingChain

    from aero_lp.executor import ExecConfig, LiveRunner
    from aero_lp.submissions import PendingSubmission, SubmissionJournal

    journal = SubmissionJournal(tmp_path / "submissions.json", OWNER)
    runner = LiveRunner(LaggingChain(FakeEth(), 0), ACCT, [T0], ExecConfig(), journal=journal)
    runner.execute([TX])
    with pytest.raises(PendingSubmission, match="still active"):
        journal.reconcile(runner.chain, lambda *a: None)
    runner.finish_submission()
    journal.reconcile(runner.chain, lambda *a: None)
    assert all(r["processed"] for r in journal.records())


def test_recovery_fee_keeps_closed_slot_after_crash_before_event(tmp_path, monkeypatch):
    from test_daemon import MAIN_TICK, OWNER, USDC, WETH, make_pool
    from test_executor import transfer_log

    from aero_lp import addresses
    from aero_lp.config import Config
    from aero_lp.ledger import Ledger
    from aero_lp.recovery import LedgerRecovery

    pool = make_pool(WETH, USDC, MAIN_TICK)
    cfg = Config(OWNER, state_path=str(tmp_path / "state.json"))
    ledger = Ledger(tmp_path / "ledger.sqlite")
    ledger.open_slot("strategy", pool.address, "WETH/USDC", WETH, USDC, 18, 6, 42)
    ledger.flow("strategy", "deposit", 0, 2, 2)
    record = {
        "hash": "0x" + "11" * 32,
        "pool": pool.address,
        "intent": {"kind": "remove", "token_id": 42},
        "receipt": proven_receipt("0x" + "11" * 32, [transfer_log(USDC, pool.address, OWNER, 2_000_000)]),
    }
    recovery = LedgerRecovery(
        cfg,
        SimpleNamespace(pool_state=lambda address: pool),
        ledger,
        lambda: {WETH.lower(): 2000, USDC.lower(): 1, addresses.AERO_TOKEN.lower(): 1},
    )
    original = ledger.event
    monkeypatch.setattr(ledger, "event", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("crash after close")))
    with pytest.raises(RuntimeError, match="crash after close"):
        recovery.apply(record, [record])
    assert ledger.slot_row("strategy")["closed_at"] is not None
    monkeypatch.setattr(ledger, "event", original)
    recovery.apply(record, [record])
    recovery.apply(record, [record])
    assert ledger.pnl("strategy").gas_usd == pytest.approx(0.00018)
    assert ledger.pnl("strategy").withdrawn_usd == 2
    assert ledger.db.execute("SELECT COUNT(*) FROM events WHERE slot IS NULL").fetchone()[0] == 0


def test_recovery_group_keeps_historical_nft_slot_for_approval(tmp_path):
    from test_daemon import MAIN_TICK, OWNER, USDC, WETH, make_pool

    from aero_lp.config import Config
    from aero_lp.ledger import Ledger
    from aero_lp.recovery import LedgerRecovery

    pool = make_pool(WETH, USDC, MAIN_TICK)
    ledger_path = tmp_path / "ledger.sqlite"
    ledger = Ledger(ledger_path)
    ledger.open_slot("strategy", pool.address, "WETH/USDC", WETH, USDC, 18, 6, 42)
    ledger.set_token_id("strategy", 777)
    ledger.db.close()
    ledger = Ledger(ledger_path)
    approval = {
        "hash": "0x" + "22" * 32,
        "pool": pool.address,
        "intent": {"kind": "approve"},
        "receipt": proven_receipt("0x" + "22" * 32, []),
    }
    unstake = {
        "hash": "0x" + "33" * 32,
        "pool": pool.address,
        "intent": {"kind": "unstake", "token_id": 42},
        "receipt": proven_receipt("0x" + "33" * 32, []),
    }
    recovery = LedgerRecovery(
        Config(OWNER),
        SimpleNamespace(pool_state=lambda address: pool),
        ledger,
        lambda: {WETH.lower(): 2000, USDC.lower(): 1},
    )
    recovery.apply(approval, [approval, unstake])
    recovery.apply(unstake, [approval, unstake])
    assert ledger.pnl("strategy").gas_usd == pytest.approx(0.00036)
    assert ledger.db.execute("SELECT COUNT(*) FROM events WHERE slot IS NULL").fetchone()[0] == 0
