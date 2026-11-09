"""Offline regression coverage for reviewed safety boundaries."""

import copy
import json
import os
import stat
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from conftest import PRICES, QUOTE_SOL_USDC, FakeHttp, delta_native, delta_token, token_account, tx_json
from test_engine import AMOUNT, FEE, live_engine, swap
from test_rails import check, report
from test_txverify import econ_setup, run_econ

from executor import gates, ledger
from executor import txverify as tv
from executor.config import Config, fingerprint, load_config, public_view, validate
from executor.engine import realized_from_meta
from executor.errors import Ambiguous, ExecutorError, Refused, RpcError, SendRejected, WalletError
from executor.journal import Journal, require_clear
from executor.jupiter import Jupiter
from executor.quote import fetch_report
from executor.rpc import Rpc
from executor.signer import check_key_file_mode
from executor.tokens import USDC_MINT, WSOL_MINT, resolve


@pytest.mark.parametrize("change", ["kill", "age"])
def test_final_read_guards(cfg, chain, owner, monkeypatch, change):
    engine = live_engine(cfg, chain, owner)
    now = [1_800_000_000.0]
    engine.clock = lambda: now[0]
    balance, calls = chain.balance, []

    def final_balance(address):
        calls.append(address)
        if len(calls) == 2:
            if change == "kill":
                (engine.root / "KILL").write_text("stop")
            else:
                now[0] += cfg.rails.max_quote_age_s + 1
        return balance(address)

    monkeypatch.setattr(chain, "balance", final_balance)
    with pytest.raises(Refused, match="KILL|s old"):
        swap(engine, live=True, reason="synthetic guard check")
    assert chain.sent == [] and list(engine.journal.records()) == []


@pytest.mark.parametrize("reconcile", [False, True])
def test_failed_chain_fee(cfg, chain, owner, reconcile):
    engine = live_engine(cfg, chain, owner)
    error = {"InstructionError": [4, {"Custom": 6001}]}
    if reconcile:
        chain.default_status = None
        with pytest.raises(Ambiguous):
            swap(engine, live=True, reason="synthetic failed fee")
    chain.default_status = {"confirmationStatus": "confirmed", "err": error}
    chain.tx_meta["meta"].update(err=error, fee=200_000_000)
    if reconcile:
        assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"
    else:
        with pytest.raises(ExecutorError, match="failed on chain"):
            swap(engine, live=True, reason="synthetic failed fee")
    assert engine.journal.unresolved() == []
    state = next(iter(engine.journal.states().values()))
    out, intent = state["outcome"], state["intent"]
    assert out["fee_lamports"] == 200_000_000
    expected = Decimal("0.2") * Decimal(intent["sol_price_usd"])
    assert Decimal(out["fee_usd"]) == expected
    assert ledger.realized_pnl_usd(engine.journal.states(), ledger.utc_day(out["ts"]), intent["strategy"]) == -expected
    assert ledger.positions(engine.journal.states(), intent["strategy"]) == {}
    with pytest.raises(Refused, match="daily loss"):
        check(cfg, engine.root, report("buy"), journal=engine.journal, strategy=intent["strategy"], now=out["ts"])


@pytest.mark.parametrize("reconcile", [False, True])
def test_failed_missing_fee_stays_blocking(cfg, chain, owner, reconcile):
    engine = live_engine(cfg, chain, owner)
    if reconcile:
        chain.default_status = None
        with pytest.raises(Ambiguous):
            swap(engine, live=True, reason="synthetic missing fee")
    chain.default_status = {"confirmationStatus": "confirmed", "err": "InstructionError"}
    chain.tx_available = False
    if reconcile:
        assert engine.reconcile()["results"][0]["outcome"] == "still_unknown"
    else:
        with pytest.raises(Ambiguous, match="fee|accounting"):
            swap(engine, live=True, reason="synthetic missing fee")
    with pytest.raises(ExecutorError, match="unresolved"):
        require_clear(engine.journal)


def test_legacy_failed_needs_accounting(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    j = engine.journal
    j.append("intent", "legacy", strategy="s", side="buy", base_mint=WSOL_MINT, sol_price_usd="100")
    j.append("sending", "legacy", signature="legacy-signature")
    j.append("result", "legacy", status="failed", error="InstructionError")
    with pytest.raises(ExecutorError, match="unresolved"):
        require_clear(j)
    chain.default_status = {"confirmationStatus": "confirmed", "err": "InstructionError"}
    chain.tx_meta["meta"]["err"] = "InstructionError"
    assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"
    assert j.unresolved() == [] and j.states()["legacy"]["outcome"]["fee_lamports"] == FEE


@pytest.mark.parametrize("direction", ["input", "output"])
def test_existing_wsol_cannot_hide_loss(owner, direction):
    rent, old = tv.TOKEN_ACCOUNT_RENT_LAMPORTS, 50_000_000
    if direction == "input":
        chain, facts, exp, info = econ_setup(owner)
        native, usdc = -AMOUNT - facts.fee_lamports + rent, 900_000
    else:
        chain, facts, exp, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
        native, usdc = old + rent + 1 - facts.fee_lamports, -1_000_000
    wsol = tv.ata_address(owner, WSOL_MINT)
    chain.state[wsol] = token_account(WSOL_MINT, owner, old, old + rent)
    chain.mods[wsol] = lambda _: None
    chain.mods[owner] = delta_native(native)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(usdc, USDC_MINT, owner)
    assert run_econ(chain, facts, exp, info)[0], "old WSOL cannot mask economic loss"


@pytest.mark.parametrize("old", [0, 50_000_000])
@pytest.mark.parametrize("direction", ["input", "output"])
def test_legitimate_wsol_closure_actual_amount(owner, old, direction):
    rent = tv.TOKEN_ACCOUNT_RENT_LAMPORTS
    if direction == "input":
        chain, facts, exp, info = econ_setup(owner)
        native, usdc = -AMOUNT - facts.fee_lamports + rent + old, 900_000
        expected = (AMOUNT, usdc)
    else:
        chain, facts, exp, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
        native, usdc = old + rent + 11_100_000 - facts.fee_lamports, -1_000_000
        expected = (1_000_000, 11_100_000)
    wsol = tv.ata_address(owner, WSOL_MINT)
    chain.state[wsol] = token_account(WSOL_MINT, owner, old, old + rent)
    chain.mods[wsol] = lambda _: None
    chain.mods[owner] = delta_native(native)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(usdc, USDC_MINT, owner)
    assert run_econ(chain, facts, exp, info)[0] == []
    tx = tx_json(owner, native, facts.fee_lamports, {USDC_MINT: (100_000_000, 100_000_000 + usdc)})
    tx["transaction"]["message"]["accountKeys"].append(wsol)
    tx["meta"]["preBalances"].append(old + rent)
    tx["meta"]["postBalances"].append(0)
    tx["meta"]["preTokenBalances"].append(
        {"accountIndex": 2, "mint": WSOL_MINT, "owner": owner, "uiTokenAmount": {"amount": str(old)}}
    )
    actual = realized_from_meta(tx, owner, resolve(exp.mint_in), resolve(exp.mint_out), 0)
    assert (actual["in_raw"], actual["out_raw"]) == expected


def test_journal_short_write(tmp_path, monkeypatch):
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "s")
    write, calls = os.write, []

    def short_write(fd, data):
        calls.append(len(data))
        return write(fd, data[:7])

    monkeypatch.setattr(os, "write", short_write)
    j.append("sending", "s", signature="synthetic")
    assert len(calls) > 1 and j.states()["s"]["state"] == "sending"
    assert j.corrupt_lines() == 0 and len(j.unresolved()) == 1


def test_journal_zero_write(tmp_path, monkeypatch):
    journal = Journal(tmp_path / "j.jsonl")
    journal.append("intent", "s")
    monkeypatch.setattr(os, "write", lambda *_: 0)
    with pytest.raises(ExecutorError, match="write|progress"):
        journal.append("sending", "s", signature="synthetic")
    assert journal.states()["s"]["state"] == "intent"


def test_replenishing_buy(tmp_path):
    assert check(Config(), tmp_path, report("buy"), native_lamports=4_000_000).side == "buy"


def test_public_rpc_host():
    cfg = validate(Config(rpc_url="https://audit-user:audit-password@rpc.example.invalid:8899/mainnet?key=private"))
    assert public_view(cfg)["rpc_host"] == "rpc.example.invalid:8899"


@pytest.mark.parametrize("field", ["rpc_url", "jupiter_base_url", "lifi_base_url"])
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1.evil.example.invalid",
        "http://127.0.0.1@evil.example.invalid",
        "https:///rpc",
        "https://rpc.invalid:bad",
    ],
)
def test_parsed_endpoint_validation(field, url):
    cfg = Config()
    setattr(cfg, field, url)
    with pytest.raises(ExecutorError):
        validate(cfg)


def test_existing_config_parent_permissions(tmp_path):
    parent = tmp_path / "shared"
    parent.mkdir(mode=0o755)
    before = stat.S_IMODE(parent.stat().st_mode)
    load_config(parent / "config.toml")
    assert stat.S_IMODE(parent.stat().st_mode) == before


@pytest.mark.parametrize("slip", [10, 50])
def test_quote_minimum_threshold(slip):
    http = FakeHttp()
    raw = copy.deepcopy(QUOTE_SOL_USDC)
    raw.update(slippageBps=slip, otherAmountThreshold="1")
    http.on("/quote", raw)
    http.on("/price/v3", PRICES)
    jup = Jupiter(Config().jupiter_base_url, http, min_gap_s=0)

    def fetch():
        return fetch_report(Config(), jup, resolve("SOL"), resolve("USDC"), 10_000_000, slip)

    rep = fetch()
    assert not rep.ok and any("threshold" in p or "minimum" in p for p in rep.problems)
    raw["otherAmountThreshold"] = str(int(raw["outAmount"]) * (10_000 - slip) // 10_000)
    assert fetch().ok


@pytest.mark.parametrize(
    "error",
    [
        {"code": -32603, "message": "internal error"},
        {"code": -32002, "message": "failed"},
        {"code": -999, "message": "unknown"},
        "malformed",
        {},
    ],
)
def test_rpc_error_ambiguity(error):
    http = FakeHttp()
    http.on("/rpc", {"jsonrpc": "2.0", "id": 1, "error": error})
    with pytest.raises(RpcError) as exc:
        Rpc("http://127.0.0.1/rpc", http).send_transaction("synthetic")
    assert not isinstance(exc.value, SendRejected) and len(http.calls) == 1


def test_rpc_known_preflight_rejection():
    http = FakeHttp()
    http.on(
        "/rpc",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32002,
                "message": "simulation failed",
                "data": {"err": {"InstructionError": [1, "failure"]}, "logs": []},
            },
        },
    )
    with pytest.raises(SendRejected):
        Rpc("http://127.0.0.1/rpc", http).send_transaction("synthetic")


@pytest.mark.parametrize(
    "field,value",
    [
        ("accumulated_s", "NaN"),
        ("accumulated_s", float("inf")),
        ("dry_runs", True),
        ("dry_runs", 5.5),
        ("last_tick_at", float("nan")),
    ],
)
def test_bad_soak(field, value, tmp_path):
    cfg = Config()
    cur = {
        "fingerprint": fingerprint(cfg, "s"),
        "started_at": 0,
        "last_tick_at": 100_000,
        "accumulated_s": 100_000,
        "dry_runs": 5,
        "resets": [],
    }
    cur[field] = value
    (tmp_path / "soak.json").write_text(json.dumps({"schema": gates.SOAK_SCHEMA, "strategies": {"s": cur}}))
    assert gates.soak_status(tmp_path, cfg, "s")[0] is False


@pytest.mark.parametrize("stamp", [float("nan"), float("inf"), -1, True])
def test_bad_research_timestamp(tmp_path, stamp):
    doc = {
        "schema": gates.RESEARCH_SCHEMA,
        "results": [
            {"strategy": "s", "result": "pass", "checked_at": stamp, "source": "old"},
            {"strategy": "s", "result": "fail", "checked_at": 2, "source": "new"},
        ],
    }
    (tmp_path / "research-gate.json").write_text(json.dumps(doc))
    assert gates.research_status(tmp_path, Config(), "s")[0] is False


def test_nonfinite_gate_write(tmp_path):
    with pytest.raises((ValueError, ExecutorError)):
        gates.record_research_result(tmp_path, Config(), "s", "pass", "synthetic", now=float("nan"))


def test_concurrent_research_writes(tmp_path, monkeypatch):
    original = gates._atomic_write
    ready, release, started, done = (threading.Event() for _ in range(4))

    def delayed(path, doc):
        if doc["results"][-1]["result"] == "pass":
            ready.set()
            assert release.wait(3)
        original(path, doc)

    monkeypatch.setattr(gates, "_atomic_write", delayed)

    def fail():
        started.set()
        result = gates.record_research_result(tmp_path, Config(), "s", "fail", "new", now=2)
        done.set()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(gates.record_research_result, tmp_path, Config(), "s", "pass", "old", now=1)
        assert ready.wait(3)
        second = pool.submit(fail)
        assert started.wait(3)
        done.wait(0.15)
        release.set()
        first.result(timeout=3)
        second.result(timeout=3)
    assert len(json.loads((tmp_path / "research-gate.json").read_text())["results"]) == 2
    assert gates.research_status(tmp_path, Config(), "s")[0] is False


def test_fifo_key_refusal(tmp_path):
    path = tmp_path / "fifo"
    os.mkfifo(path, 0o600)
    done, errors = threading.Event(), []

    def check_fifo():
        try:
            check_key_file_mode(path)
        except WalletError as exc:
            errors.append(str(exc))
        finally:
            done.set()

    worker = threading.Thread(target=check_fifo, daemon=True)
    worker.start()
    finished = done.wait(0.15)
    if not finished:
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
    worker.join(2)
    assert finished, "FIFO blocked before validation"
    assert errors and "not a regular file" in errors[0]


@pytest.mark.parametrize("reconcile", [False, True])
@pytest.mark.parametrize("old", [0, 50_000_000])
def test_engine_accounts_actual_closed_wsol_rent(cfg, chain, owner, reconcile, old):
    engine = live_engine(cfg, chain, owner)
    rent = tv.TOKEN_ACCOUNT_RENT_LAMPORTS
    wsol = tv.ata_address(owner, WSOL_MINT)
    chain.state[wsol] = token_account(WSOL_MINT, owner, old, old + rent)
    chain.mods[wsol] = lambda _: None
    native = -AMOUNT - FEE + old + rent
    chain.mods[owner] = delta_native(native)
    tx = tx_json(owner, native, FEE, {USDC_MINT: (100_000_000, 100_900_000)})
    tx["transaction"]["message"]["accountKeys"].append(wsol)
    tx["meta"]["preBalances"].append(old + rent)
    tx["meta"]["postBalances"].append(0)
    tx["meta"]["preTokenBalances"].append(
        {"accountIndex": 2, "mint": WSOL_MINT, "owner": owner, "uiTokenAmount": {"amount": str(old)}}
    )
    chain.tx_meta = tx
    if reconcile:
        chain.default_status = None
        with pytest.raises(Ambiguous):
            swap(engine, live=True, reason="synthetic closed WSOL")
        chain.default_status = {"confirmationStatus": "finalized", "err": None}
        assert engine.reconcile()["results"][0]["post_verify_ok"]
    else:
        assert swap(engine, live=True, reason="synthetic closed WSOL")["post_verify_ok"]
    outcome = next(iter(engine.journal.states().values()))["outcome"]
    assert outcome["in_raw"] == AMOUNT and outcome["base_raw"] == AMOUNT
    assert not (engine.root / "KILL").exists()


@pytest.mark.parametrize("old", [0, 50_000_000])
def test_retained_funded_wsol_is_conserved(owner, old):
    rent = tv.TOKEN_ACCOUNT_RENT_LAMPORTS
    received = 11_100_000
    chain, facts, exp, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
    wsol = tv.ata_address(owner, WSOL_MINT)
    chain.state[wsol] = token_account(WSOL_MINT, owner, old, old + rent) if old else None
    chain.mods[wsol] = lambda _: token_account(WSOL_MINT, owner, old + received, rent + old + received)
    native = -facts.fee_lamports - (0 if old else rent)
    chain.mods[owner] = delta_native(native)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    assert run_econ(chain, facts, exp, info)[0] == []
    tx = tx_json(owner, native, facts.fee_lamports, {USDC_MINT: (100_000_000, 99_000_000)})
    tx["transaction"]["message"]["accountKeys"].append(wsol)
    tx["meta"]["preBalances"].append(old + rent if old else 0)
    tx["meta"]["postBalances"].append(old + rent + received)
    if old:
        tx["meta"]["preTokenBalances"].append(
            {"accountIndex": 2, "mint": WSOL_MINT, "owner": owner, "uiTokenAmount": {"amount": str(old)}}
        )
    tx["meta"]["postTokenBalances"].append(
        {"accountIndex": 2, "mint": WSOL_MINT, "owner": owner, "uiTokenAmount": {"amount": str(old + received)}}
    )
    realized = realized_from_meta(tx, owner, resolve("USDC"), resolve("SOL"), rent)
    assert (realized["in_raw"], realized["out_raw"]) == (1_000_000, received)


@pytest.mark.parametrize("reconcile", [False, True])
def test_actual_rent_can_differ_from_simulated_retained_rent(cfg, chain, owner, reconcile):
    engine = live_engine(cfg, chain, owner)
    usdc = tv.ata_address(owner, USDC_MINT)
    chain.state[usdc] = None
    rent = tv.TOKEN_ACCOUNT_RENT_LAMPORTS
    chain.mods[owner] = delta_native(-AMOUNT - FEE - rent)
    chain.mods[usdc] = lambda _: token_account(USDC_MINT, owner, 900_000, rent)
    # Actual execution retained a different measured rent amount from the simulation.
    actual_rent = rent + 1
    tx = tx_json(owner, -AMOUNT - FEE - actual_rent, FEE, {})
    tx["transaction"]["message"]["accountKeys"][1] = usdc
    tx["meta"]["preBalances"][1] = 0
    tx["meta"]["postBalances"][1] = actual_rent
    tx["meta"]["postTokenBalances"] = [
        {"accountIndex": 1, "mint": USDC_MINT, "owner": owner, "uiTokenAmount": {"amount": "900000"}}
    ]
    chain.tx_meta = tx
    if reconcile:
        chain.default_status = None
        with pytest.raises(Ambiguous):
            swap(engine, live=True, reason="synthetic actual rent")
        chain.default_status = {"confirmationStatus": "finalized", "err": None}
        assert engine.reconcile()["results"][0]["post_verify_ok"]
    else:
        assert swap(engine, live=True, reason="synthetic actual rent")["post_verify_ok"]


def test_status_envelope_redacts_rpc_userinfo(cfg, chain, owner, monkeypatch):
    from executor import registry

    engine = live_engine(cfg, chain, owner)
    cfg.rpc_url = "https://audit-user:audit-password@rpc.invalid:8899/rpc?key=private"
    monkeypatch.setattr(registry, "CONTEXT_FACTORY", lambda: registry.Context(cfg, engine))
    result = registry.dispatch("status", {})
    encoded = json.dumps(result)
    assert "audit-user" not in encoded and "audit-password" not in encoded and "key=private" not in encoded
    assert "rpc.invalid:8899" in encoded


@pytest.mark.parametrize(
    "bad", [[], [1], {"fee": None, "err": "failed"}, {"fee": True, "err": "failed"}, {"fee": -1, "err": "failed"}]
)
def test_malformed_failed_fee_metadata_remains_blocking(cfg, chain, owner, bad):
    engine = live_engine(cfg, chain, owner)
    chain.default_status = {"confirmationStatus": "confirmed", "err": "failed"}
    chain.tx_meta["meta"] = bad
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic malformed failed fee")
    assert engine.journal.unresolved()


def test_gate_records_with_unknown_shape_are_unsatisfied(tmp_path):
    for value in ["bad", 3, [], {"fingerprint": "bad"}]:
        (tmp_path / "soak.json").write_text(json.dumps({"schema": gates.SOAK_SCHEMA, "strategies": {"s": value}}))
        assert not gates.soak_status(tmp_path, Config(), "s")[0]
    for row in [None, "bad", {}, {"strategy": "s", "result": "pass", "checked_at": 10**500, "source": "bad"}]:
        (tmp_path / "research-gate.json").write_text(
            json.dumps(
                {
                    "schema": gates.RESEARCH_SCHEMA,
                    "results": [{"strategy": "s", "result": "pass", "checked_at": 1, "source": "old"}, row],
                }
            )
        )
        assert not gates.research_status(tmp_path, Config(), "s")[0]


def test_gate_override_cannot_write_nonfinite_timestamp(tmp_path):
    with pytest.raises((ValueError, ExecutorError)):
        gates.log_override(tmp_path, "s", "synthetic", now=float("nan"))


# Serialized economic fields must bind the builder response independently of simulation.
def _route_payload(
    *, shared=False, step=b"\x30\x64\x00\x01", amount=10_000_000, quoted=901_607, slippage=50, fee=0, count=1
):
    disc = "c1209b3341d69c81" if shared else "e517cb977ae3ad2a"
    return (
        bytes.fromhex(disc)
        + (b"\x00" if shared else b"")
        + struct.pack("<I", count)
        + step
        + struct.pack("<QQHB", amount, quoted, slippage, fee)
    )


def _recorded_route_check(data):
    from test_txverify import REAL_OWNER, exp, real_tx_and_tables

    tx, tables = real_tx_and_tables()
    facts = tv.inspect_tx(tx, tables)
    for instruction in facts.instructions:
        if instruction.program == tv.JUPITER_V6:
            instruction.data = data
    return tv.check_static(facts, exp(REAL_OWNER))


@pytest.mark.parametrize("shared", [False, True])
def test_serialized_route_binds_input_and_minimum(shared):
    for fields in (
        {"amount": 10_000_001},
        {"quoted": 1, "slippage": 0},
        {"quoted": 901_607, "slippage": 100},
        {"fee": 1},
        {"slippage": 10_001},
        {"amount": 0},
        {"quoted": 0},
    ):
        problems, _ = _recorded_route_check(_route_payload(shared=shared, **fields))
        assert problems, fields


@pytest.mark.parametrize("shared", [False, True])
def test_serialized_route_rejects_malformed_and_appended_fields(shared):
    valid = _route_payload(shared=shared)
    bad = [
        valid + b"\x00",
        valid + struct.pack("<QQHB", 10_000_000, 901_607, 50, 0),
        valid[:-1],
        _route_payload(shared=shared, count=0),
        _route_payload(shared=shared, count=2),
        _route_payload(shared=shared, count=0xFFFFFFFF),
        _route_payload(shared=shared, step=b"\xff\x64\x00\x01"),
        _route_payload(shared=shared, step=b"\x08\x02\x64\x00\x01"),
        _route_payload(shared=shared, step=b"\x0c\x02\x64\x00\x01"),
        _route_payload(shared=shared, step=b"\x2f\x01\x02\x64\x00\x01"),
        _route_payload(shared=shared, step=b"\x2f\x01\x01\xff\xff\xff\xff\x64\x00\x01"),
        _route_payload(shared=shared, step=b"\x4b\x01\x00\x00\x00\x09\x01\x64\x00\x01"),
    ]
    for payload in bad:
        problems, _ = _recorded_route_check(payload)
        assert problems, payload.hex()


@pytest.mark.parametrize("shared", [False, True])
def test_serialized_route_uses_consumed_schema_for_economic_fields(shared):
    swaps = [
        b"\x30",
        b"\x08\x01",
        b"\x0c\x01",
        b"\x1d" + struct.pack("<QQ", 1, 2),
        b"\x21" + struct.pack("<I", 7),
        b"\x2f\x01\x00",
        b"\x2f\x01\x01" + struct.pack("<I", 1) + b"\x06\x02",
        b"\x4b" + struct.pack("<I", 1) + b"\x08\x02",
        b"\x57" + struct.pack("<Q", 100) + b"\x01",
    ]
    for variant in swaps:
        valid = _route_payload(shared=shared, step=variant + b"\x64\x00\x01")
        problems, info = _recorded_route_check(valid)
        assert problems == [], (variant.hex(), problems)
        assert info["jupiter_route"]["amount_in"] == 10_000_000
        assert info["jupiter_route"]["minimum_out"] >= 896_771
        weak = _route_payload(shared=shared, step=variant + b"\x64\x00\x01", quoted=1, slippage=0)
        assert _recorded_route_check(weak)[0]


@pytest.mark.parametrize("via_reconcile", [False, True])
def test_integrated_auto_kill_precedes_terminal_result(cfg, chain, owner, monkeypatch, via_reconcile):
    engine = live_engine(cfg, chain, owner)
    if via_reconcile:
        chain.default_status = None
        with pytest.raises(Ambiguous):
            swap(engine, live=True, reason="synthetic delayed mismatch")
    chain.default_status = {"confirmationStatus": "confirmed", "err": None}
    chain.tx_meta = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, 10)})
    append = engine.journal.append
    terminal_checks = []

    def guarded_terminal(kind, iid, **fields):
        if kind in ("result", "reconciled") and fields.get("status") == "confirmed":
            terminal_checks.append((engine.root / "KILL").is_file())
        return append(kind, iid, **fields)

    monkeypatch.setattr(engine.journal, "append", guarded_terminal)
    if via_reconcile:
        assert engine.reconcile()["results"][0]["post_verify_ok"] is False
    else:
        assert swap(engine, live=True, reason="synthetic immediate mismatch")["post_verify_ok"] is False
    assert terminal_checks == [True]
    assert engine.journal.unresolved() == []
    assert len(chain.sent) == 1


def test_integrated_reconcile_kill_failure_retains_unresolved_send(cfg, chain, owner, monkeypatch):
    from pathlib import Path

    engine = live_engine(cfg, chain, owner)
    chain.default_status = None
    with pytest.raises(Ambiguous):
        swap(engine, live=True, reason="synthetic delayed mismatch")
    chain.default_status = {"confirmationStatus": "confirmed", "err": None}
    chain.tx_meta = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (0, 10)})
    write_text = Path.write_text

    def failed_stop(path, *args, **kwargs):
        if path.name == "KILL":
            raise OSError("synthetic stop persistence failure")
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failed_stop)
    with pytest.raises(OSError, match="stop persistence"):
        engine.reconcile()
    assert engine.journal.unresolved()[0]["state"] == "unknown"
    with pytest.raises(ExecutorError, match="unresolved"):
        require_clear(engine.journal)
    assert len(chain.sent) == 1


def _integrated_tracked_exit(engine, *, tracked=True, unknown=False):
    journal = engine.journal
    strategy = "tracked"
    if tracked:
        journal.append("intent", "prior-buy", strategy=strategy, side="buy", base_mint=WSOL_MINT, in_usd="0.9")
        journal.append("sending", "prior-buy", signature="buy-signature")
        journal.append(
            "result",
            "prior-buy",
            status="confirmed",
            signature="buy-signature",
            base_raw=AMOUNT,
            quote_usd="0.9",
            fee_usd="0",
        )
    journal.append("intent", "legacy-fee", strategy=strategy, side="sell", base_mint=WSOL_MINT, in_usd="0.1")
    journal.append("sending", "legacy-fee", signature="failed-signature")
    journal.append("result", "legacy-fee", status="failed", signature="failed-signature")
    if unknown:
        journal.append("intent", "pending-send", strategy=strategy, side="sell", base_mint=WSOL_MINT, in_usd="0.1")
        journal.append("sending", "pending-send", signature="unknown-signature")
        journal.append("unknown", "pending-send", signature="unknown-signature")
    return journal


def test_integrated_engine_allows_only_proven_exit_past_terminal_fee_hold(cfg, chain, owner):
    engine = live_engine(cfg, chain, owner)
    journal = _integrated_tracked_exit(engine)
    (engine.root / "KILL").write_text("synthetic stop")
    with pytest.raises(ExecutorError, match="unresolved"):
        require_clear(journal)
    result = engine.swap(
        "SOL",
        "USDC",
        "0.01",
        strategy="tracked",
        live=True,
        exit_only=True,
        reason="reduce measured position despite terminal fee-only hold",
    )
    assert result["sent"] is True and result["post_verify_ok"] is True
    assert ledger.positions(journal.states(), "tracked")[WSOL_MINT].qty_raw == 0
    assert [state["id"] for state in journal.unresolved()] == ["legacy-fee"]
    with pytest.raises(ExecutorError, match="unresolved"):
        require_clear(journal)
    assert len(chain.sent) == 1


@pytest.mark.parametrize(
    "strategy,tracked,unknown", [("tracked", True, True), ("tracked", False, False), ("path-validation", True, False)]
)
def test_integrated_fee_exit_exception_never_admits_unknown_or_wallet_sell(
    cfg, chain, owner, strategy, tracked, unknown
):
    engine = live_engine(cfg, chain, owner)
    _integrated_tracked_exit(engine, tracked=tracked, unknown=unknown)
    with pytest.raises(Refused, match="unresolved"):
        engine.swap(
            "SOL", "USDC", "0.01", strategy=strategy, live=True, exit_only=True, reason="must retain unresolved barrier"
        )
    assert chain.sent == []
