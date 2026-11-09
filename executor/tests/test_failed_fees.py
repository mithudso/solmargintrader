"""Failed on-chain attempts incur measured fees even though they create no position."""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest
from test_engine import FEE, live_engine, swap
from test_rails import check, report

from executor import gates, ledger
from executor.config import VALIDATION_STRATEGY, Config
from executor.errors import Ambiguous, ExecutorError, Refused
from executor.journal import Journal
from executor.tokens import WSOL_MINT

NOW = 1_800_000_000.0
DAY = ledger.utc_day(NOW)
MISSING = object()


def failed_attempt(journal, *, strategy="regular", fee="1.25", ts=NOW, iid="failed"):
    journal.append("intent", iid, ts=ts, strategy=strategy, side="buy", base_mint=WSOL_MINT, in_usd="1")
    journal.append("sending", iid, ts=ts, signature=f"sig-{iid}")
    fields = {} if fee is MISSING else {"fee_usd": fee}
    journal.append("result", iid, ts=ts, status="failed", signature=f"sig-{iid}", **fields)
    return journal.states()


def test_failed_fee_is_a_loss_without_any_trade_or_position(tmp_path):
    states = failed_attempt(Journal(tmp_path / "journal.jsonl"))
    assert ledger.realized_pnl_usd(states, DAY, "regular") == Decimal("-1.25")
    assert ledger.realized_pnl_usd(states, DAY) == Decimal("-1.25")
    assert ledger.positions(states, "regular") == {}


def test_failed_fees_reach_daily_stop_for_regular_live_buy(tmp_path, monkeypatch):
    cfg = Config(mode="live")
    journal = Journal(tmp_path / "journal.jsonl")
    failed_attempt(journal, fee="4", iid="first")
    failed_attempt(journal, fee="6", iid="second")
    monkeypatch.setattr(gates, "check_live_allowed", lambda *args: ([], []))
    with pytest.raises(Refused, match="daily_loss_stop_usd"):
        check(cfg, tmp_path, report("buy", 1), journal, strategy="regular", live=True, now=NOW)
    assert check(cfg, tmp_path, report("buy", 1), journal, strategy="unrelated", live=True, now=NOW)


def test_failed_fees_are_scoped_to_the_requested_strategy_and_utc_day(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    failed_attempt(journal, strategy="regular", fee="2", iid="today")
    failed_attempt(journal, strategy="other", fee="3", iid="other")
    failed_attempt(journal, strategy="regular", fee="5", ts=NOW - 86400, iid="yesterday")
    assert ledger.realized_pnl_usd(journal.states(), DAY, "regular") == Decimal("-2")
    assert ledger.realized_pnl_usd(journal.states(), DAY, "other") == Decimal("-3")
    assert ledger.realized_pnl_usd(journal.states(), DAY) == Decimal("-5")
    assert ledger.realized_pnl_usd(journal.states(), ledger.utc_day(NOW - 86400), "regular") == Decimal("-5")


@pytest.mark.parametrize(
    "fee", [MISSING, None, "NaN", "Infinity", "-Infinity", "-0.001", "bad-fee-sensitive", True, {}, []]
)
def test_missing_or_invalid_failed_fee_refuses_without_exposing_values(tmp_path, fee):
    states = failed_attempt(Journal(tmp_path / "journal.jsonl"), fee=fee)
    with pytest.raises(Refused, match="fee") as exc:
        ledger.realized_pnl_usd(states, DAY, "regular")
    assert "bad-fee-sensitive" not in str(exc.value)
    assert ledger.positions(states, "regular") == {}
    assert ledger.realized_pnl_usd(states, DAY, "other") == 0
    assert ledger.realized_pnl_usd(states, ledger.utc_day(NOW - 86400), "regular") == 0


def test_explicit_zero_failed_fee_is_not_missing_evidence(tmp_path):
    states = failed_attempt(Journal(tmp_path / "journal.jsonl"), fee="0")
    assert ledger.realized_pnl_usd(states, DAY, "regular") == 0


def test_missing_failed_fee_does_not_block_a_proven_reduce_only_exit(tmp_path):
    journal = Journal(tmp_path / "journal.jsonl")
    journal.append("intent", "buy", ts=NOW - 50, strategy="regular", side="buy", base_mint=WSOL_MINT, in_usd="9")
    journal.append("sending", "buy", ts=NOW - 50, signature="buy-sig")
    journal.append(
        "result",
        "buy",
        ts=NOW - 50,
        status="confirmed",
        signature="buy-sig",
        base_raw=100_000_000,
        quote_usd="9",
        fee_usd="0",
    )
    states = failed_attempt(journal, fee=MISSING)
    assert ledger.positions(states, "regular")[WSOL_MINT].qty_raw == 100_000_000
    decision = check(
        Config(mode="live"),
        tmp_path,
        report("sell", 1),
        journal,
        strategy="regular",
        live=True,
        exit_only=True,
        now=NOW,
    )
    assert decision.exit is True


def failed_status():
    return {"confirmationStatus": "confirmed", "err": {"InstructionError": [0, "synthetic failure"]}}


def test_engine_measures_and_records_failed_on_chain_fee(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = failed_status()
    with pytest.raises(ExecutorError, match="failed on chain"):
        swap(engine, live=True, reason="synthetic failed-chain fee")
    state = next(iter(engine.journal.states().values()))
    out = state["outcome"]
    expected = Decimal(FEE) / Decimal(1_000_000_000) * Decimal(state["intent"]["sol_price_usd"])
    assert out["fee_lamports"] == FEE
    assert Decimal(out["fee_usd"]) == expected
    assert ledger.realized_pnl_usd(engine.journal.states(), ledger.utc_day(out["ts"]), VALIDATION_STRATEGY) == -expected
    assert ledger.positions(engine.journal.states(), VALIDATION_STRATEGY) == {}
    assert len(chain.sent) == 1


@pytest.mark.parametrize("fee", ["missing", None, "10000", -1, True])
def test_failed_fee_unreadable_holds_until_reconcile_measures_it(cfg, chain, owner, fee):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = failed_status()
    complete = copy.deepcopy(chain.tx_meta)
    if fee == "missing":
        del chain.tx_meta["meta"]["fee"]
    else:
        chain.tx_meta["meta"]["fee"] = fee
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic unreadable failed fee")
    assert engine.journal.unresolved()
    assert engine.reconcile()["still_blocking"] == 1
    chain.tx_meta = complete
    result = engine.reconcile()
    assert result["still_blocking"] == 0
    assert result["results"][0]["outcome"] == "failed_on_chain"
    out = next(iter(engine.journal.states().values()))["outcome"]
    assert out["fee_lamports"] == FEE
    assert Decimal(out["fee_usd"]) > 0
    assert len(chain.sent) == 1


def test_reconcile_records_failed_fee_after_initial_confirmation_timeout(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = None
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic delayed failure")
    chain.default_status = failed_status()
    assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"
    out = next(iter(engine.journal.states().values()))["outcome"]
    assert out["fee_lamports"] == FEE
    assert Decimal(out["fee_usd"]) > 0
    assert not engine.journal.unresolved()
    assert len(chain.sent) == 1
