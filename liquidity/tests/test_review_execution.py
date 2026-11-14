"""Boundary regressions use inert accounts, fake RPCs and disposable files only."""

from __future__ import annotations

import json
import math
import os
import plistlib
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from hexbytes import HexBytes
from test_engine import make_engine, make_ev
from test_engine_audit import setup_live
from test_executor import T0, T1, FakeChain, WalletRunner, make_position
from test_metrics import POOL, PRICES, StubChain, StubMarket, make_pool, wobble
from test_safe_exit import ConvEngine, route, run
from web3 import Web3

from aero_lp import addresses, backtest, chain, cli, clmath, engine, gates, market, metrics, providers, safe_exit, scout
from aero_lp.config import Config, ExecConfig
from aero_lp.executor import LiveRunner, PlannedTx, RebalanceError, Rebalancer, RebalanceResult, SimRunner
from aero_lp.ledger import Ledger, SlotPnl
from aero_lp.service import render
from aero_lp.strategy import StrategyConfig


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, 10**1000])
@pytest.mark.parametrize("field", ["eth_usd", "value_usd", "gas_usd", "twap_deviation_bps", "pool_price"])
def test_live_safety_rejects_invalid_numeric_measurements(tmp_path, field, value):
    ev = make_ev()
    if field == "pool_price":
        ev.econ.price0_usd = value
    else:
        setattr(ev, field, value)
    assert make_engine(tmp_path).safety_blocks(ev, live=True)


def test_provider_errors_are_redacted_in_progress_and_persisted_artifacts(tmp_path, monkeypatch):
    from test_providers import coins_transport, raw_pool

    rows = [raw_pool("uniswap-v2", "WETH-USDC")]

    def handler(request):
        if request.url.host == "yields.llama.fi":
            return httpx.Response(200, json={"data": rows})
        return coins_transport().handle_request(request)

    def fail(*args, **kwargs):
        raise TimeoutError("https://fixture.invalid/rpc?api_key=private-fixture-token Bearer secret-fixture")

    monkeypatch.setattr(providers, "evaluate_quoted", fail)
    progress = []
    output = tmp_path / "providers.json"
    report = tmp_path / "report.md"
    doc = providers.run_providers(
        None,
        market.MarketData(client=httpx.Client(transport=httpx.MockTransport(handler))),
        50,
        cache_dir=tmp_path,
        now=1_800_000_000,
        out_json=output,
        out_report=report,
        progress=progress.append,
    )
    assert doc["errors"] and "TimeoutError" in doc["errors"][0]["error"]
    observable = output.read_text() + report.read_text() + " ".join(progress)
    assert "private-fixture-token" not in observable and "secret-fixture" not in observable
    assert "fixture.invalid" not in observable


@pytest.mark.parametrize("phase", ["estimate", "journal", "first_send"])
def test_live_permission_is_rechecked_before_each_sign_and_broadcast(phase):
    observed = {"killed": False, "sign": 0, "send": 0, "cancel": 0, "receipt": 0}
    owner = Web3.to_checksum_address("0x" + "ab" * 20)

    def guard():
        if observed["killed"]:
            raise RuntimeError("KILL")

    def sign(request):
        observed["sign"] += 1
        return SimpleNamespace(hash=HexBytes(b"\x01" * 32), raw_transaction=b"inert fixture bytes")

    def prepare(*args, **kwargs):
        if phase == "journal":
            observed["killed"] = True

    def send(raw):
        assert raw == b"inert fixture bytes"
        observed["send"] += 1
        if phase == "first_send":
            observed["killed"] = True

    def receipt(*args, **kwargs):
        observed["receipt"] += 1
        return {"status": 1, "gasUsed": 21000, "effectiveGasPrice": 1, "blockNumber": 1, "logs": []}

    def cancel(*args):
        observed["cancel"] += 1

    journal = SimpleNamespace(
        owner=owner,
        acquire=lambda: SimpleNamespace(close=lambda: None),
        before_submit=prepare,
        receipt=lambda *a: None,
        cancel_before_broadcast=cancel,
    )
    fake_chain = SimpleNamespace(
        w3=SimpleNamespace(eth=SimpleNamespace(send_raw_transaction=send, wait_for_transaction_receipt=receipt))
    )
    runner = LiveRunner(
        fake_chain,
        SimpleNamespace(address=owner, sign_transaction=sign),
        [],
        ExecConfig(),
        journal=journal,
        before_send=guard,
    )
    runner._fees = lambda: (1, 1)
    runner._nonce = lambda: 0

    def estimate(request):
        if phase == "estimate":
            observed["killed"] = True
        return 21000

    runner._estimate_gas = estimate
    tx = PlannedTx("approve fixture", T0, "0x")
    with pytest.raises(RuntimeError, match="KILL"):
        runner.execute([tx, tx])
    assert observed["sign"] == (0 if phase == "estimate" else 1)
    assert observed["send"] == (1 if phase == "first_send" else 0)
    assert observed["receipt"] == observed["send"]
    assert observed["cancel"] == (1 if phase == "journal" else 0)
    assert len(runner.sent_hashes) == observed["send"]


def test_first_signal_notification_failure_cannot_interrupt_sequence(monkeypatch):
    stopped, completed = [], []
    original = signal.getsignal(signal.SIGINT)
    with engine.defer_sigint(stopped.append):
        monkeypatch.setattr("builtins.print", lambda *a, **k: (_ for _ in ()).throw(BrokenPipeError()))
        signal.raise_signal(signal.SIGINT)
        completed.append(True)
    assert completed == [True] and stopped == [signal.SIGINT]
    assert signal.getsignal(signal.SIGINT) == original


def test_withdraw_rechecks_fresh_manipulation_guard(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch)
    calls = []
    monkeypatch.setattr(
        engine,
        "Rebalancer",
        lambda *a: SimpleNamespace(
            withdraw=lambda p, r: (calls.append(r), RebalanceResult(None, False, ["remove"], [], {"remove": 100000}))[1]
        ),
    )
    eng.pool_blocks = lambda pool, live: ["TWAP moved after planning"]
    with pytest.raises(RuntimeError, match="TWAP moved"):
        eng.withdraw(42, True, object())
    assert calls == ["sim"]


@pytest.mark.parametrize("minimum", [0, -1, True, 1.5, 2**256])
def test_public_swaps_require_positive_exact_output_minimum(minimum):
    pos = make_position(False)
    runner = WalletRunner(pos, pos.pool.sqrt_price_x96)
    rb = Rebalancer(FakeChain(), "0x" + "ab" * 20, ExecConfig())
    with pytest.raises(ValueError):
        rb.swap_exact(pos.pool, T0, 10**15, runner, minimum)
    with pytest.raises(ValueError):
        rb.swap_to_eth(pos.pool, T1, 10**6, minimum, runner)
    assert runner.txs == []


def test_failed_simulation_probe_is_never_balance_evidence():
    w3 = Web3()
    w3.eth.get_block = lambda block: {"timestamp": 1800000000}
    w3.provider.make_request = lambda *a: {
        "result": [
            {"calls": [{"status": "0x1", "gasUsed": "0x5208", "logs": []}, {"status": "0x0", "returnData": "0x01"}]}
        ]
    }
    sim = SimRunner(SimpleNamespace(w3=w3, head=lambda: (100, 1800000000)), "0x" + "ab" * 20, [T0])
    with pytest.raises(RuntimeError, match="probe"):
        sim.execute([PlannedTx("approve", T0, "0x")])
    assert sim.history == [] and sim.confirmed == []
    assert sim.gas_used == {}


@pytest.mark.parametrize("probe", [None, "0x01", "0x" + "00" * 33])
def test_simulation_requires_complete_exact_abi_evidence_without_partial_state(probe):
    w3 = Web3()
    w3.eth.get_block = lambda block: {"timestamp": 1800000000}
    calls = [{"status": "0x1", "gasUsed": "0x5208", "logs": []}]
    if probe is not None:
        calls.append({"status": "0x1", "returnData": probe})
    w3.provider.make_request = lambda *a: {"result": [{"calls": calls}]}
    sim = SimRunner(SimpleNamespace(w3=w3, head=lambda: (100, 1800000000)), "0x" + "ab" * 20, [T0])
    with pytest.raises(RuntimeError, match="probe"):
        sim.execute([PlannedTx("approve", T0, "0x")])
    assert sim.history == [] and sim.confirmed == [] and sim.logs == [] and sim.gas_used == {}


def test_measured_zero_fees_remain_zero_despite_positive_volume():
    pool = make_pool()
    econ = metrics.economics_from(pool, PRICES, {"volume_24h_usd": 1e6}, 0, (0, 0, 1))
    assert econ.fee_usd_per_l_day == 0
    assert market.earn_usd_per_day(10**18, False, True, econ, False) == 0
    missing = replace(econ, fee_usd_per_l_day=None)
    assert market.earn_usd_per_day(10**18, False, True, missing, False) > 0


def test_fee_transport_outage_does_not_turn_into_estimated_income():
    broken = StubChain()
    broken.fee_growth_delta = lambda *a: (_ for _ in ()).throw(TimeoutError("https://rpc.invalid/private-key"))
    with pytest.raises(RuntimeError, match="provider unavailable") as failure:
        metrics.pool_economics(broken, StubMarket(), make_pool())
    assert "private-key" not in str(failure.value)


def test_replay_uses_supplied_impact_and_returns_causal_deployed_width(monkeypatch):
    calls = []
    real = backtest.run

    def record(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append((args[1], kwargs["impact_bps"], result.pnl_vs_hodl))
        return result

    monkeypatch.setattr(backtest, "run", record)
    m, _ = metrics.evaluate_pool_detail(
        StubChain(), StubMarket(closes=wobble()), POOL, 50, StrategyConfig(), impact_bps=100
    )
    assert calls and all(impact == 100 for _, impact, _ in calls)
    width, _, pnl = calls[-1]
    assert math.isclose((math.exp(width) - 1) * 100, m.best_half_width_pct)
    assert m.backtest_deploy_apr == pytest.approx(pnl / 50 * 365 / ((len(wobble()) - 1) / 24) * 100)
    assert "local estimate" in m.break_even_basis and "not a solved" in m.break_even_basis


def test_partial_withdrawal_does_not_invent_hodl_profit():
    row = SlotPnl("1", "A/B", "pool", 1, None, 1, None, 100, 40, 0, 0, 60, 60, 0)
    assert row.pnl_usd == 0 and row.pnl_vs_hodl_usd == 0
    assert replace(row, value_usd=72, hodl_usd=72).pnl_vs_hodl_usd == 0
    assert replace(row, value_usd=70, hodl_usd=72).pnl_vs_hodl_usd == -2


def test_optional_conversion_failure_does_not_prevent_withdrawals(tmp_path, monkeypatch):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    monkeypatch.setattr(safe_exit, "best_direct_pool", lambda *a: (_ for _ in ()).throw(TimeoutError("route down")))
    rep = run(eng, tmp_path, ids=(1, 2), live=True, convert_to="USDC")
    assert [p.status for p in rep.positions] == ["exited", "exited"]
    assert all(p.converts[0].refused for p in rep.positions)


@pytest.mark.parametrize("price", [float("nan"), float("inf"), 0, -1])
def test_conversion_invalid_price_has_no_executable_route(tmp_path, price):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    step = safe_exit.plan_conversion(eng, T0, 10**18, T1, {T0.lower(): 2000, T1.lower(): price})
    assert step.refused and not step.route_pool and step.min_out_raw == 0


def test_partial_conversion_retains_hashes_and_never_claims_skipped(tmp_path, monkeypatch):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    partial = RebalanceResult(None, False, ["swap"], ["0xfixture"], {}, amount_out=123)
    monkeypatch.setattr(
        safe_exit, "_convert_live", lambda *a: (_ for _ in ()).throw(RebalanceError("unknown", partial))
    )
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    step = rep.positions[0].converts[0]
    assert not rep.ok and step.tx_hashes == ["0xfixture"] and step.out_raw == 123
    assert step.status == "unknown" and "SKIPPED" not in safe_exit.format_plan(rep)


def test_plist_serializer_preserves_paths_and_defaults_to_dry_run():
    body = render("/synthetic/a&b/bin", "/synthetic/state<one>", "fixture.label")
    doc = plistlib.loads(body)
    assert "--live" not in doc["ProgramArguments"]
    assert doc["ProgramArguments"][0] == "/synthetic/a&b/bin"
    assert doc["EnvironmentVariables"]["AERO_LP_HOME"] == "/synthetic/state<one>"
    assert "--live" in plistlib.loads(render("bin", "state", "label", live=True))["ProgramArguments"]


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, float("nan"), 2**256])
def test_token_ids_fail_at_config_boundary(bad):
    with pytest.raises(ValueError):
        Config("0x" + "ab" * 20, [bad])


def test_uint128_liquidity_refuses_overflow():
    assert clmath._liquidity_uint128(2**128 - 1) == 2**128 - 1
    with pytest.raises(ValueError, match="uint128"):
        clmath._liquidity_uint128(2**128)
    sa, sb = clmath.get_sqrt_ratio_at_tick(0), clmath.get_sqrt_ratio_at_tick(1)
    with pytest.raises(ValueError, match="uint128"):
        clmath.get_liquidity_for_amount0(sa, sb, 1 << 256)
    with pytest.raises(ValueError, match="uint128"):
        clmath.get_liquidity_for_amount1(sa, sb, 1 << 256)


def test_oracle_outage_is_distinct_from_short_history():
    c = object.__new__(chain.AeroChain)
    failure = [TimeoutError("https://credential.invalid/secret")]
    c._c = lambda *a: SimpleNamespace(
        functions=SimpleNamespace(observe=lambda *a: SimpleNamespace(call=lambda: (_ for _ in ()).throw(failure[0])))
    )
    with pytest.raises(RuntimeError, match="provider unavailable") as error:
        c.twap_tick_series(T0)
    assert "credential" not in str(error.value)
    failure[0] = ValueError("execution reverted: OLD")
    assert c.twap_tick_series(T0) == []


@pytest.mark.parametrize("bad", ["--widths=-100", "--widths=nan", "--value=0", "--hours=0"])
def test_backtest_cli_refuses_before_external_construction(monkeypatch, bad):
    monkeypatch.setattr(cli, "AeroChain", lambda *a: pytest.fail("external construction"))
    with pytest.raises(SystemExit) as error:
        cli.main(["backtest", "--pool", T0, bad])
    assert error.value.code == 2


def test_once_failure_returns_nonzero(monkeypatch):
    monkeypatch.setattr(cli, "load", lambda *a: Config("0x" + "ab" * 20, [1]))
    monkeypatch.setattr(
        cli,
        "Engine",
        lambda *a: SimpleNamespace(step=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fixture failure"))),
    )
    assert cli.main(["run", "--once"]) != 0


@pytest.mark.parametrize("phase", ["discovery", "evaluation"])
def test_scout_bounds_discovery_and_one_evaluation(monkeypatch, phase):
    original = signal.getsignal(signal.SIGALRM)

    def slow(*args, **kwargs):
        time.sleep(1)
        pytest.fail("deadline was swallowed")

    monkeypatch.setattr(scout, "candidate_pools", slow if phase == "discovery" else lambda *a: [T0])
    monkeypatch.setattr(scout, "evaluate_pool", slow)
    report = scout.run_scout(object(), object(), 50, max_seconds=0.02)
    assert report["budget_exhausted"] and not report["complete"]
    assert signal.getsignal(signal.SIGALRM) == original


def test_scout_errors_do_not_persist_credentials(monkeypatch):
    monkeypatch.setattr(
        scout,
        "evaluate_pool",
        lambda *a, **k: (_ for _ in ()).throw(
            TimeoutError("https://user:fixture-password@rpc.invalid/private-api-key?token=fixture-token")
        ),
    )
    doc = scout.run_scout(object(), object(), 50, pools=[T0])
    text = json.dumps(doc)
    assert "fixture-password" not in text and "private-api-key" not in text and "fixture-token" not in text


def test_market_cache_expires_and_stable_peg_is_observed(monkeypatch):
    now, calls = [100.0], []

    def reply(request):
        calls.append(request)
        return httpx.Response(
            200, json={"data": {"attributes": {"token_prices": {T1.lower(): "0.97" if len(calls) == 1 else "0.94"}}}}
        )

    monkeypatch.setattr(market.time, "time", lambda: now[0])
    m = market.MarketData(ttl=60, client=httpx.Client(transport=httpx.MockTransport(reply)))
    assert m.token_prices_usd([T1])[T1.lower()] == 0.97
    assert m.token_prices_usd([T1])[T1.lower()] == 0.97
    now[0] += 61
    assert m.token_prices_usd([T1])[T1.lower()] == 0.94 and len(calls) == 2


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "0", "-1", True])
def test_invalid_observed_market_prices_are_refused(raw):
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"data": {"attributes": {"token_prices": {T1.lower(): raw}}}})
    )
    m = market.MarketData(client=httpx.Client(transport=transport))
    assert T1.lower() not in m.token_prices_usd([T1])


def test_transient_chart_failure_is_not_cached_as_missing():
    calls = []

    def reply(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(
            200, json={"coins": {"base:" + T0.lower(): {"prices": [{"timestamp": 3600, "price": 10}]}}}
        )

    c = providers.Coins(httpx.Client(transport=httpx.MockTransport(reply)))
    c.hourly([T0])
    assert T0.lower() not in c._missing_hourly
    c.hourly([T0])
    assert c._hourly[T0.lower()] == {1: 10} and len(calls) == 2


def test_ratio_preserves_direction_alignment_and_contiguous_hour_spacing(monkeypatch):
    c = providers.Coins(httpx.Client(transport=httpx.MockTransport(lambda req: pytest.fail("network"))))
    monkeypatch.setattr(c, "hourly", lambda tokens: None)
    c._hourly = {T0.lower(): {1: 20, 2: 66, 3: 81, 5: 100}, T1.lower(): {0: 99, 1: 2, 2: 3, 4: 4, 5: 2}}
    assert c.ratio_closes(T0, T1) == [10, 22]
    assert c.ratio_closes(T1, T0) == pytest.approx([0.1, 1 / 22])


def test_non_base_quoted_rows_do_not_advertise_base_identity():
    from test_providers import raw_pool

    p = providers.LlamaPool.from_raw(raw_pool(chain="Ethereum"))
    row = providers.evaluate_quoted(p, providers.AmmType.CONSTANT_PRODUCT, 0.02, "fixture", 7, 5)
    assert row is not None and not row.actionable
    assert row.venue_info["chain"] == "Ethereum" and row.venue_info["chain_id"] is None


def test_registered_factory_unavailable_is_a_refusal(monkeypatch):
    assert "uniswap-v3" in providers.VENUES
    monkeypatch.setattr(
        providers, "read_v3_pool", lambda *a: SimpleNamespace(state=make_pool(), factory=None, has_gauge=False)
    )
    monkeypatch.setattr(providers, "score_onchain", lambda *a: (None, None))
    with pytest.raises(RuntimeError, match="factory verification unavailable"):
        providers.score_v3(SimpleNamespace(chain=StubChain()), "uniswap-v3", "uniswap-v3", T0, 1e6, 1e6, None)


def test_ownership_enumeration_uses_one_block_snapshot():
    seen = []
    c = object.__new__(chain.AeroChain)
    c.head = lambda: (100, 1800000000)

    def read(label, value):
        def call(**kwargs):
            seen.append((label, kwargs["block_identifier"]))
            return value

        return SimpleNamespace(call=call)

    c.npm = SimpleNamespace(functions=SimpleNamespace(balanceOf=lambda owner: read("balance", 1)))
    c.multicall = lambda calls, block="latest": (seen.append(("indices", block)), [7])[1]
    c.pool_state = lambda address, block=None: (seen.append(("pool", block)), SimpleNamespace(gauge=T1))[1]
    c.gauge_contract = lambda address: SimpleNamespace(
        functions=SimpleNamespace(stakedValues=lambda owner: read("staked", [8]))
    )
    assert c.positions_of("0x" + "ab" * 20, [T0]) == [7, 8]
    assert seen == [("balance", 100), ("indices", 100), ("pool", 100), ("staked", 100)]


def test_recovery_bookkeeping_uses_cached_prices_without_authorizing_new_sizing(tmp_path, monkeypatch):
    from test_daemon import WETH
    from test_daemon import make_daemon as daemon_fixture

    from aero_lp import daemon

    d = daemon_fixture.__wrapped__(tmp_path, monkeypatch)(live_mode=True)
    assert d.prices()[WETH.lower()] == 2000
    d.test.market.down = True
    seen = []

    def recover(cfg, chain_, ledger, prices, decisions):
        return SimpleNamespace(apply=lambda record, group: seen.append(prices()[WETH.lower()]))

    monkeypatch.setattr(daemon, "LedgerRecovery", recover)
    d._apply_submission({}, [])
    assert seen == [2000]
    with pytest.raises(RuntimeError, match="feed down"):
        d.prices()  # cached prices remain forbidden for new trade sizing


def test_burned_nft_does_not_block_historical_receipt_bookkeeping(tmp_path):
    from test_executor import OWNER
    from test_submission_audit import late_mint_receipt, mint_transaction

    from aero_lp.recovery import LedgerRecovery
    from aero_lp.submissions import SubmissionJournal

    ledger = Ledger(tmp_path / "ledger.sqlite")
    journal = SubmissionJournal(tmp_path / "submissions.json", OWNER, ledger_path=ledger.path)
    tx_hash = "0x" + "01" * 32
    journal.before_submit(tx_hash, 0, mint_transaction(), "group", make_position(False).pool.address, [T0, T1])
    journal.receipt(tx_hash, late_mint_receipt())
    record = journal.records()[0]
    c = SimpleNamespace(
        pool_state=lambda *a: make_position(False).pool,
        position=lambda *a, **k: (_ for _ in ()).throw(chain.PositionGone("burned")),
    )
    prices = {T0.lower(): 2000, T1.lower(): 1, addresses.WETH.lower(): 2000}
    recover = LedgerRecovery(Config(OWNER), c, ledger, lambda: prices)
    try:
        recover.apply(record, [record])
        recover.apply(record, [record])
        assert ledger.slot_row("777")["token_id"] == 777
        assert ledger.open_slots() == []
        assert ledger.db.execute("SELECT COUNT(*) FROM flows WHERE slot='777'").fetchone()[0] == 1
    finally:
        ledger.db.close()


@pytest.mark.parametrize(
    "result",
    [
        None,
        {},
        {"strategy": "aero-slipstream-lp"},
        {"strategy": "aero-slipstream-lp", "result": "pass", "checked_at": float("nan"), "source": "fixture"},
    ],
)
def test_nested_research_records_are_checked_after_valid_schema(tmp_path, result):
    path = tmp_path / "research-gate.json"
    path.write_text(json.dumps({"schema": gates.RESEARCH_SCHEMA, "results": [result]}))
    with pytest.raises(ValueError):
        gates._research_document(path)


def test_missing_eth_gate_is_independent_of_pool_token_prices():
    pool = make_pool()
    pool.token0 = replace(pool.token0, address=T1, symbol="USDC", decimals=6)
    econ = metrics.economics_from(
        pool, {T1.lower(): 1, pool.token1.address.lower(): 2400}, {"volume_24h_usd": 1e6}, 0, (0, 0, 1)
    )
    context = {"prices": {}, "eth_usd": 0, "tvl_usd": 1e6, "volume_24h_usd": 1e6, "fee_history_days": 1}
    result, _ = metrics.score_pool(pool, econ, context, 0.02, "fixture", 7, wobble(), 50, StrategyConfig(), 10**6)
    assert econ.price0_usd > 0 and econ.price1_usd > 0
    assert result.confidence == "low" and any("ETH price" in value for value in result.flags)


def test_negative_qualifying_scores_still_retain_the_best_pool():
    from test_allocator_ledger import WETH, WSTETH, row

    from aero_lp.allocator import plan_allocation
    from aero_lp.config import AllocatorConfig

    cfg = AllocatorConfig(min_net_apr=-50, min_edge_ratio=0, compare_margin=0.3)
    rows = [
        row("best", WETH, WSTETH, -3, -3),
        row("close", WETH, WSTETH, -3.5, -3.5),
        row("distant", WETH, WSTETH, -5, -5),
    ]
    plan = plan_allocation(rows, 80, 0, cfg)
    assert [arm.candidate.pool for arm in plan.arms] == ["best", "close"]


def test_key_file_policy_binds_the_consumed_descriptor(tmp_path, monkeypatch):
    from aero_lp import wallet

    path = tmp_path / "synthetic-input"
    path.write_text("first synthetic input")
    path.chmod(0o600)
    real_stat = os.stat

    def replace_after_path_stat(candidate, *args, **kwargs):
        result = real_stat(candidate, *args, **kwargs)
        if os.fspath(candidate) == str(path):
            path.unlink()
            path.write_text("replacement synthetic input")
            path.chmod(0o644)
        return result

    monkeypatch.setattr(wallet.os, "stat", replace_after_path_stat)
    assert wallet._from_file(str(path)) == "first synthetic input"


def _service_fixture(tmp_path, broken_python=False):
    repository = tmp_path / "repo"
    scripts, binaries, stubs = repository / "scripts", repository / ".venv" / "bin", tmp_path / "stubs"
    for directory in (scripts, binaries, stubs):
        directory.mkdir(parents=True)
    script = scripts / "aero-lp-service"
    script.write_bytes((Path(__file__).parents[1] / "scripts" / "aero-lp-service").read_bytes())
    binary = binaries / "aero-lp"
    binary.write_text("#!/bin/sh\nexit 91\n")  # Installation must never execute the daemon.
    binary.chmod(0o700)
    python = binaries / "python"
    if broken_python:
        python.write_text("#!/bin/sh\nexit 1\n")
        python.chmod(0o700)
    else:
        python.symlink_to(sys.executable)
    launchctl = stubs / "launchctl"
    launchctl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SERVICE_TRACE"\n')
    launchctl.chmod(0o700)
    directory = tmp_path / "state&<paper>"
    directory.mkdir()
    (directory / "config.toml").write_text("# inert fixture, never loaded\n")
    (directory / "KILL").write_text("preserve fixture stop")
    environment = {
        "AERO_LP_LAUNCHAGENTS_DIR": str(tmp_path / "agents"),
        "AERO_LP_HOME": str(directory),
        "PATH": str(stubs) + os.pathsep + os.defpath,
        "SERVICE_TRACE": str(tmp_path / "calls"),
        "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
    }
    assert shutil.which("launchctl", path=environment["PATH"]) == str(launchctl)
    return script, directory, environment


@pytest.mark.parametrize("flags, live", [([], False), (["--dry-run"], False), (["--live"], True)])
def test_service_install_has_explicit_validated_live_opt_in(tmp_path, flags, live):
    script, directory, environment = _service_fixture(tmp_path)
    result = subprocess.run(
        ["/bin/zsh", str(script), "install", *flags], env=environment, capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, result.stderr
    files = list(Path(environment["AERO_LP_LAUNCHAGENTS_DIR"]).glob("*.plist"))
    assert len(files) == 1
    doc = plistlib.loads(files[0].read_bytes())
    assert ("--live" in doc["ProgramArguments"]) is live
    assert doc["EnvironmentVariables"]["AERO_LP_HOME"] == str(directory)
    assert (directory / "KILL").read_text() == "preserve fixture stop"
    assert [line.split()[0] for line in Path(environment["SERVICE_TRACE"]).read_text().splitlines()] == [
        "bootout",
        "bootstrap",
    ]


@pytest.mark.parametrize("flags", [["--dryrun"], ["--live", "extra"]])
def test_invalid_service_install_arguments_never_replace_or_reload(tmp_path, flags):
    script, _, environment = _service_fixture(tmp_path)
    result = subprocess.run(
        ["/bin/zsh", str(script), "install", *flags], env=environment, capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 2
    assert not Path(environment["SERVICE_TRACE"]).exists()
    assert not Path(environment["AERO_LP_LAUNCHAGENTS_DIR"]).exists()


def test_failed_plist_generation_preserves_existing_service_file(tmp_path):
    script, _, environment = _service_fixture(tmp_path, broken_python=True)
    target = Path(environment["AERO_LP_LAUNCHAGENTS_DIR"]) / "com.mithudso.aero-lp.plist"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old disposable fixture")
    result = subprocess.run(
        ["/bin/zsh", str(script), "install"], env=environment, capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0 and target.read_bytes() == b"old disposable fixture"
    assert not Path(environment["SERVICE_TRACE"]).exists()
    assert list(target.parent.iterdir()) == [target]
