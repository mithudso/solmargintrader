"""Synthetic receipt groups and isolated ledgers; no chain or keys."""

from types import SimpleNamespace

import pytest
from test_daemon import AERO, GAUGE, MAIN_TICK, OWNER, USDC, WETH, make_pool, make_pos, tick_for
from test_executor import increase_log, transfer_log

from aero_lp import addresses
from aero_lp.config import Config
from aero_lp.ledger import Ledger
from aero_lp.recovery import LedgerRecovery
from aero_lp.submissions import PendingSubmission, SubmissionJournal


def receipt(h, logs=(), status=1):
    return {
        "transactionHash": h,
        "status": status,
        "blockNumber": 101,
        "gasUsed": 90000,
        "effectiveGasPrice": 10**6,
        "logs": list(logs),
    }


def record(kind, h, pool, logs=(), status=1, **intent):
    return {"hash": h, "pool": pool.address, "intent": {"kind": kind, **intent}, "receipt": receipt(h, logs, status)}


@pytest.mark.parametrize("token", [WETH, USDC])
@pytest.mark.parametrize("bad_price", [None, 0.0, -1.0, float("nan"), float("inf"), True])
def test_registration_refuses_missing_or_invalid_basis_then_recovers(tmp_path, token, bad_price):
    from aero_lp.daemon import Daemon

    ledger = Ledger(tmp_path / "ledger.sqlite")
    pool = make_pool(WETH, USDC, MAIN_TICK)
    position = SimpleNamespace(owner=OWNER, pool=pool, human_amounts=lambda: (0.5, 1000.0))
    prices = {WETH.lower(): 2000.0, USDC.lower(): 1.0}
    if bad_price is None:
        prices.pop(token.lower())
    else:
        prices[token.lower()] = bad_price
    daemon = Daemon.__new__(Daemon)
    daemon.cfg, daemon.ledger = Config(OWNER), ledger
    daemon.chain = SimpleNamespace(position=lambda *a, **kw: position)
    daemon.prices = lambda: prices
    daemon.log = lambda *a: None
    try:
        with pytest.raises((ValueError, RuntimeError)):
            daemon._register(1)
        assert ledger.slot_row("1") is None
        prices.update({WETH.lower(): 2000.0, USDC.lower(): 1.0})
        daemon._register(1)
        assert ledger.pnl("1").deposited_usd == 2000.0
        ledger.snapshot("1", 1, 2000.0, 2000.0, 0.0)
        assert ledger.pnl("1").pnl_usd == 0.0
    finally:
        ledger.db.close()


def test_reconciliation_checks_ledger_binding_before_callback(tmp_path):
    from test_executor import TX

    path = tmp_path / "submissions.json"
    first = SubmissionJournal(path, OWNER, ledger_path=tmp_path / "A.sqlite")
    h = "0x" + "11" * 32
    first.before_submit(h, 0, TX, "test", None, [])
    first.receipt(h, receipt(h))
    other = SubmissionJournal(path, OWNER, ledger_path=tmp_path / "B.sqlite")
    callbacks = []
    with pytest.raises(PendingSubmission, match="ledger"):
        other.reconcile(SimpleNamespace(), lambda *a: callbacks.append(a))
    assert callbacks == [] and not first.records()[0]["processed"]
    first.reconcile(SimpleNamespace(), lambda *a: callbacks.append(a))
    assert len(callbacks) == 1


def test_runner_persists_explicit_slot_and_wallet_scopes_before_send(tmp_path):
    from test_executor import ACCT, T0, TX, FakeEth, LaggingChain

    from aero_lp.executor import ExecConfig, LiveRunner

    for scope in ({"scope": "slot", "slot": "strategy"}, {"scope": "wallet"}):
        journal = SubmissionJournal(tmp_path / f"{scope['scope']}.json", OWNER)
        eth = FakeEth()
        original = eth.send_raw_transaction

        def send(raw, saved_journal=journal, saved_scope=scope, original_send=original):
            assert saved_journal.records()[0]["accounting"] == saved_scope
            return original_send(raw)

        eth.send_raw_transaction = send
        runner = LiveRunner(LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), journal=journal, accounting=scope)
        runner.execute([TX])
        runner.finish_submission()


def test_daemon_runner_supplies_known_slot_or_explicit_wallet_context(tmp_path, monkeypatch):
    from test_daemon import make_daemon

    from aero_lp import daemon as daemon_module

    daemon = make_daemon.__wrapped__(tmp_path, monkeypatch)(live_mode=True)
    contexts = []
    monkeypatch.setattr(daemon_module, "LiveRunner", lambda *a, **kw: contexts.append(kw["accounting"]))
    daemon.runner([WETH], None, slot="strategy")
    daemon.runner([WETH], None, wallet=True)
    assert contexts == [{"scope": "slot", "slot": "strategy"}, {"scope": "wallet"}]


def test_legacy_unattributed_journal_refuses_without_consuming_receipt(tmp_path):
    from test_executor import TX

    ledger = Ledger(tmp_path / "ledger.sqlite")
    journal = SubmissionJournal(tmp_path / "submissions.json", OWNER, ledger_path=ledger.path)
    h = "0x" + "44" * 32
    journal.before_submit(h, 0, TX, "legacy", None, [])
    journal.receipt(h, receipt(h))
    recovery = LedgerRecovery(Config(OWNER), SimpleNamespace(min_block=None), ledger, lambda: {WETH.lower(): 2000})
    with pytest.raises(PendingSubmission, match="attribution"):
        journal.reconcile(recovery.chain, recovery.apply)
    assert not journal.records()[0]["processed"]
    assert ledger.db.execute("SELECT COUNT(*) FROM transaction_effects").fetchone()[0] == 0
    ledger.db.close()


@pytest.mark.parametrize("removed", [False, True])
def test_aero_reward_counted_once_after_failed_or_successful_removal(tmp_path, removed):
    pool = make_pool(AERO, USDC, tick_for(1e6 / 1e18))
    ledger = Ledger(tmp_path / "ledger.sqlite")
    ledger.open_slot("strategy", pool.address, "AERO/USDC", AERO, USDC, 18, 6, 42)
    ledger.flow("strategy", "deposit", 0, 100, 100)
    unstake = record("unstake", "0xunstake", pool, [transfer_log(AERO, GAUGE, OWNER, 10**18)], token_id=42)
    remove = record(
        "remove",
        "0xremove",
        pool,
        [transfer_log(USDC, pool.address, OWNER, 100 * 10**6)] if removed else [],
        status=int(removed),
        token_id=42,
    )
    group = [unstake, remove]
    recovery = LedgerRecovery(
        Config(OWNER),
        SimpleNamespace(pool_state=lambda _: pool),
        ledger,
        lambda: {WETH.lower(): 2000, AERO.lower(): 1, USDC.lower(): 1},
    )
    for _ in range(2):
        for r in group:
            recovery.apply(r, group)
    pnl = ledger.pnl("strategy")
    assert pnl.rewards_usd == (0 if removed else 1)
    assert pnl.withdrawn_usd == (101 if removed else 0)
    assert pnl.pnl_usd == pytest.approx(1 - pnl.gas_usd)
    ledger.db.close()


def test_reinvested_aero_is_not_double_counted_on_recovered_mint(tmp_path):
    from test_executor import W3

    pool = make_pool(AERO, USDC, tick_for(1e6 / 1e18))
    ledger = Ledger(tmp_path / "ledger.sqlite")
    ledger.open_slot("strategy", pool.address, "AERO/USDC", AERO, USDC, 18, 6, 42)
    ledger.flow("strategy", "deposit", 0, 100, 100)
    unstake = record("unstake", "0xu", pool, [transfer_log(AERO, GAUGE, OWNER, 10**18)], token_id=42)
    remove = record("remove", "0xr", pool, token_id=42)
    nft = {
        "address": addresses.NONFUNGIBLE_POSITION_MANAGER,
        "topics": [
            W3.keccak(text="Transfer(address,address,uint256)"),
            "0x" + "0" * 64,
            "0x" + "0" * 24 + OWNER[2:].lower(),
            hex(777),
        ],
        "data": "0x",
    }
    mint = record("mint", "0xm", pool, [nft, increase_log(777, 10**18, 100 * 10**6)])
    group = [unstake, remove, mint]
    pos = make_pos(777, pool=pool)
    recovery = LedgerRecovery(
        Config(OWNER),
        SimpleNamespace(pool_state=lambda _: pool, position=lambda *a, **k: pos),
        ledger,
        lambda: {WETH.lower(): 2000, AERO.lower(): 1, USDC.lower(): 1},
    )
    for _ in range(2):
        for r in group:
            recovery.apply(r, group)
    ledger.snapshot("strategy", 777, 101, 100, 0)
    pnl = ledger.pnl("strategy")
    assert pnl.rewards_usd == 0 and pnl.deposited_usd == 100 and pnl.withdrawn_usd == 0
    assert pnl.pnl_usd == pytest.approx(1 - pnl.gas_usd)
    ledger.db.close()


def test_new_wallet_funded_mint_binds_approval_fees_to_proven_nft(tmp_path):
    from test_executor import W3

    pool = make_pool(WETH, USDC, MAIN_TICK)
    ledger = Ledger(tmp_path / "ledger.sqlite")
    approve = record("approve", "0xapprove", pool)
    nft = {
        "address": addresses.NONFUNGIBLE_POSITION_MANAGER,
        "topics": [
            W3.keccak(text="Transfer(address,address,uint256)"),
            "0x" + "0" * 64,
            "0x" + "0" * 24 + OWNER[2:].lower(),
            hex(777),
        ],
        "data": "0x",
    }
    mint = record("mint", "0xmint", pool, [nft, increase_log(777, 0, 10**6)])
    for r in (approve, mint):
        r["accounting"] = {"scope": "wallet"}
    pos = make_pos(777, pool=pool)
    recovery = LedgerRecovery(
        Config(OWNER),
        SimpleNamespace(pool_state=lambda _: pool, position=lambda *a, **k: pos),
        ledger,
        lambda: {WETH.lower(): 2000, USDC.lower(): 1},
    )
    for _ in range(2):
        recovery.apply(approve, [approve, mint])
        recovery.apply(mint, [approve, mint])
    assert ledger.pnl("777").gas_usd == pytest.approx(0.00036)
    assert ledger.pnl("777").deposited_usd == 1
    ledger.db.close()


@pytest.mark.parametrize("scope", ["legacy", "slot", "wallet"])
def test_conversion_fee_context_is_required_and_idempotent(tmp_path, scope):
    pool = make_pool(WETH, USDC, MAIN_TICK)
    ledger = Ledger(tmp_path / "ledger.sqlite")
    ledger.open_slot("strategy", pool.address, "WETH/USDC", WETH, USDC, 18, 6, 42)
    r = record("swap", "0xswap", pool, token_in=WETH, token_out=USDC)
    if scope != "legacy":
        r["accounting"] = {"scope": scope, **({"slot": "strategy"} if scope == "slot" else {})}
    recovery = LedgerRecovery(
        Config(OWNER), SimpleNamespace(pool_state=lambda _: pool), ledger, lambda: {WETH.lower(): 2000, USDC.lower(): 1}
    )
    if scope == "legacy":
        with pytest.raises(PendingSubmission, match="attribution"):
            recovery.apply(r, [r])
        assert ledger.db.execute("SELECT COUNT(*) FROM transaction_effects").fetchone()[0] == 0
    else:
        recovery.apply(r, [r])
        recovery.apply(r, [r])
        assert ledger.pnl("strategy").gas_usd == pytest.approx(0.00018 if scope == "slot" else 0)
        assert ledger.db.execute("SELECT SUM(gas_usd) FROM events").fetchone()[0] == pytest.approx(0.00018)
    ledger.db.close()
