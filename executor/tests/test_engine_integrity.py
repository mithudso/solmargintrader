"""Crash and incomplete-evidence regressions over a synthetic chain and temporary homes."""

from __future__ import annotations

import copy

import pytest
from conftest import tx_json
from test_engine import AMOUNT, FEE, OUT, live_engine, swap

from executor.engine import realized_from_meta
from executor.errors import Ambiguous, Refused
from executor.tokens import USDC_MINT, resolve


def pending_engine(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = None
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic timeout")
    chain.height = 1351
    return engine


@pytest.mark.parametrize("status", [{"confirmationStatus": "processed", "err": None}, {}, {"err": None}])
def test_present_nonterminal_status_never_clears_unknown(cfg, chain, owner, status):
    engine = pending_engine(cfg, chain, owner)
    chain.default_status = status
    result = engine.reconcile()
    assert result["results"][0]["outcome"] == "still_unknown"
    assert result["still_blocking"] == 1
    assert len(chain.sent) == 1


def test_processed_error_remains_unknown_until_confirmed(cfg, chain, owner):
    engine = pending_engine(cfg, chain, owner)
    chain.default_status = {"confirmationStatus": "processed", "err": {"InstructionError": [0, "failure"]}}
    assert engine.reconcile()["still_blocking"] == 1
    chain.default_status["confirmationStatus"] = "confirmed"
    assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"


def test_confirmation_waits_for_confirmed_error(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = {"confirmationStatus": "processed", "err": {"InstructionError": [0, "failure"]}}
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="processed status is not final")
    assert engine.journal.unresolved()
    assert len(chain.sent) == 1


@pytest.mark.parametrize("kind", ["intent", "sending"])
def test_kill_appearing_during_journal_flush_prevents_send(cfg, chain, owner, monkeypatch, kind):
    engine = live_engine(cfg, chain, owner)
    append = engine.journal.append

    def stop_after_write(event, iid, **fields):
        result = append(event, iid, **fields)
        if event == kind:
            (engine.root / "KILL").write_text("synthetic concurrent stop\n")
        return result

    monkeypatch.setattr(engine.journal, "append", stop_after_write)
    with pytest.raises(Refused, match="KILL"):
        swap(engine, live=True, reason="test stop during durable writes")
    assert chain.sent == []
    assert engine.journal.unresolved() == []


def test_reconcile_shares_swap_lock(cfg, chain, owner):
    engine = pending_engine(cfg, chain, owner)
    with engine._swap_lock(), pytest.raises(Refused, match="in progress"):
        engine.reconcile()
    assert engine.journal.unresolved()


@pytest.mark.parametrize("field", ["preTokenBalances", "postTokenBalances"])
@pytest.mark.parametrize("bad", [None, "missing", {}, "not an array"])
def test_missing_or_malformed_token_balance_arrays_are_not_zero(owner, field, bad):
    tx = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, OUT)})
    if bad == "missing":
        del tx["meta"][field]
    else:
        tx["meta"][field] = bad
    assert realized_from_meta(tx, owner, resolve("SOL"), resolve("USDC"), 0) is None


@pytest.mark.parametrize("amount", ["NaN", "-1", "1.5", "", True, None])
def test_malformed_token_amount_is_unreadable(owner, amount):
    tx = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, OUT)})
    tx["meta"]["postTokenBalances"][0]["uiTokenAmount"]["amount"] = amount
    assert realized_from_meta(tx, owner, resolve("SOL"), resolve("USDC"), 0) is None


def test_explicit_empty_opening_array_supports_new_token_account(owner):
    tx = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, OUT)})
    tx["meta"]["preTokenBalances"] = []
    result = realized_from_meta(tx, owner, resolve("SOL"), resolve("USDC"), 0)
    assert result["in_raw"] == AMOUNT and result["out_raw"] == OUT


def test_confirmed_incomplete_metadata_preserves_hold_until_recovered(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    complete = copy.deepcopy(chain.tx_meta)
    del chain.tx_meta["meta"]["preTokenBalances"]
    with pytest.raises(Ambiguous, match="balances could not be read"):
        swap(engine, live=True, reason="missing opening balances")
    assert engine.journal.unresolved()
    assert engine.reconcile()["still_blocking"] == 1
    chain.tx_meta = complete
    assert engine.reconcile()["still_blocking"] == 0
    assert len(chain.sent) == 1


def test_unexpected_confirmation_error_is_ambiguous_and_does_not_leak_values(cfg, chain, owner, monkeypatch):
    engine = live_engine(cfg, chain, owner)

    def broken_status(*args):
        raise RuntimeError("sensitive remote response")

    monkeypatch.setattr(chain, "signature_statuses", broken_status)
    with pytest.raises(Ambiguous) as exc:
        swap(engine, live=True, reason="synthetic reader failure")
    assert "sensitive remote response" not in str(exc.value)
    assert engine.journal.unresolved()[0]["state"] == "unknown"
    assert len(chain.sent) == 1


def test_failed_auto_kill_write_keeps_send_unresolved(cfg, chain, owner, monkeypatch):
    from pathlib import Path

    engine = live_engine(cfg, chain, owner)
    chain.tx_meta = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, 10)})
    write_text = Path.write_text

    def disk_error(path, *args, **kwargs):
        if path.name == "KILL":
            raise OSError("synthetic disk failure")
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", disk_error)
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="post-trade mismatch with failed stop persistence")
    assert engine.journal.unresolved()
    assert len(chain.sent) == 1


@pytest.mark.parametrize("elapsed", [21.0, -1.0, float("nan")])
def test_quote_expiring_or_clock_changing_during_journal_flush_prevents_send(cfg, chain, owner, monkeypatch, elapsed):
    engine = live_engine(cfg, chain, owner)
    clock = {"now": 1_800_000_000.0}
    engine.clock = lambda: clock["now"]
    append = engine.journal.append

    def delayed_write(kind, iid, **fields):
        record = append(kind, iid, **fields)
        if kind == "sending":
            clock["now"] += elapsed
        return record

    monkeypatch.setattr(engine.journal, "append", delayed_write)
    with pytest.raises(Refused, match="quote"):
        swap(engine, live=True, reason="synthetic journal delay or clock change")
    assert chain.sent == []
    assert engine.journal.unresolved() == []


def test_journal_and_response_preserve_final_gate_decision(cfg, chain, owner, monkeypatch):
    from dataclasses import replace

    from executor import rails

    engine = live_engine(cfg, chain, owner)
    check_trade = rails.check_trade
    checks = []
    warning = "WARNING final gate state differs from the initial read"

    def changed_gate(*args, **kwargs):
        decision = check_trade(*args, **kwargs)
        checks.append(decision)
        return replace(decision, notes=(warning,)) if len(checks) == 2 else decision

    monkeypatch.setattr(rails, "check_trade", changed_gate)
    result = swap(engine, live=True, reason="synthetic gate update during preparation")
    intent = next(record for record in engine.journal.records() if record["kind"] == "intent")
    assert intent["gate_notes"] == [warning]
    assert intent["evidence"]["decision"]["notes"] == result["decision"]["notes"] == [warning]
    assert len(chain.sent) == 1


@pytest.mark.parametrize("index", [None, True, -1, 2, "1", "duplicate"])
def test_invalid_or_duplicate_token_account_indices_are_unreadable(owner, index):
    tx = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (OUT, OUT)})
    entry = tx["meta"]["postTokenBalances"][0]
    if index is None:
        del entry["accountIndex"]
    elif index == "duplicate":
        tx["meta"]["postTokenBalances"].append(copy.deepcopy(entry))
    else:
        entry["accountIndex"] = index
    assert realized_from_meta(tx, owner, resolve("SOL"), resolve("USDC"), 0) is None
