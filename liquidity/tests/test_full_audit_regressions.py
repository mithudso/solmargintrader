"""Full-review counterexamples. Only mock HTTP, temporary state and a copied service launcher run."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from test_executor import ACCT, T0, TX, FakeEth, LaggingChain, journal_runner
from test_providers import POOL, SQRT, TOK, USDC, FakeChain, sample_doc, v3_answers
from test_safe_exit import WETH, ConvEngine, route
from web3 import Web3

from aero_lp import cli, providers, safe_exit
from aero_lp.executor import ExecConfig
from aero_lp.market import MarketData
from aero_lp.providers_report import render_report


def test_market_stablecoin_uses_observed_depeg_price():
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, json={"data": {"attributes": {"token_prices": {USDC: "0.72"}}}})

    market = MarketData(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert market.token_prices_usd([USDC]) == {USDC: 0.72}
    assert USDC in calls[0]


@pytest.mark.parametrize("bad", [None, "NaN", "Infinity", "-1", "0", True])
def test_market_never_invents_stablecoin_price_for_missing_or_invalid_quote(bad):
    market = MarketData(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"data": {"attributes": {"token_prices": {USDC: bad}}}})
            )
        )
    )
    assert USDC not in market.token_prices_usd([USDC])


def test_provider_stablecoin_uses_observed_depeg_price():
    coins = providers.Coins(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"coins": {"base:" + USDC: {"price": 0.72}}})
            )
        )
    )
    assert coins.current([USDC]) == {USDC: 0.72}


def test_live_runner_stops_before_signing_next_transaction_after_kill(tmp_path):
    kill = tmp_path / "KILL"

    def authorize():
        if kill.exists():
            raise RuntimeError("kill switch engaged")

    eth = FakeEth()
    signed = []
    acct = SimpleNamespace(
        address=ACCT.address, sign_transaction=lambda req: signed.append(req["nonce"]) or ACCT.sign_transaction(req)
    )
    original = eth.wait_for_transaction_receipt

    def receipt(*a, **kw):
        r = original(*a, **kw)
        kill.write_text("test stop")
        return r

    eth.wait_for_transaction_receipt = receipt
    runner = journal_runner(tmp_path, LaggingChain(eth, 0), acct, [T0], ExecConfig())
    runner.before_send = authorize
    try:
        with pytest.raises(RuntimeError, match="kill switch"):
            runner.execute([TX, TX])
        assert len(eth.sent) == 1 and signed == [0]
        assert len(runner.confirmed) == 1
        assert runner.journal.records()[0]["receipt"] is not None
    finally:
        runner.finish_submission()


def test_cli_live_run_checks_kill_before_chain_or_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path))
    (tmp_path / "KILL").write_text("archived")
    cfg = tmp_path / "config.toml"
    cfg.write_text('owner = "0x' + "ab" * 20 + '"\ntoken_ids = [42]\n')
    monkeypatch.setattr(cli, "_live_gate", lambda cfg: True)
    monkeypatch.setattr(cli, "Engine", lambda cfg: pytest.fail("KILL must refuse before chain construction"))
    assert cli.main(["run", "-c", str(cfg), "--live", "--once"]) == 3
    assert "kill switch" in capsys.readouterr().err.lower()


def test_slipstream_fallback_has_an_abi_for_every_requested_function():
    chain = FakeChain(v3_answers(slot0=(SQRT, -199000, 1, 300, 300, True)), TOK)
    chain.reject_seven_output_slot0 = True
    old = chain.multicall

    def strict(calls, block="latest"):
        for c in calls:
            Web3().eth.contract(abi=c.contract.abi).encode_abi(c.fn, args=list(c.args))
        return old(calls, block)

    chain.multicall = strict
    assert providers.read_v3_pool(chain, POOL).state.tick == -199000


def test_report_uses_the_same_apr_threshold_as_its_document():
    doc = sample_doc()
    doc["min_net_apr"] = 17.25
    text = render_report(doc)
    assert "17.25% APR" in text
    assert "The 5% bar" not in text and "reach\n5% APR" not in text


@pytest.mark.parametrize("bad", [float("inf"), True])
def test_conversion_rejects_nonfinite_or_boolean_market_prices(tmp_path, bad):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    step = safe_exit.plan_conversion(eng, WETH, 10**18, USDC, {WETH.lower(): bad, USDC.lower(): bad})
    assert step.refused and step.min_out_raw == 0


def service_copy(tmp_path):
    liq = tmp_path / "liquidity"
    scripts = liq / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "scripts/aero-lp-service"
    target = scripts / "aero-lp-service"
    shutil.copy2(source, target)
    binary = liq / ".venv/bin/aero-lp"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o700)
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    launcher = fakebin / "launchctl"
    launcher.write_text("#!/bin/sh\nexit 0\n")
    launcher.chmod(0o700)
    lp = tmp_path / "state"
    lp.mkdir()
    (lp / "config.toml").write_text("# synthetic config\n")
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home), "AERO_LP_HOME": str(lp), "PATH": str(fakebin) + ":/usr/bin:/bin"}
    return target, home / "Library/LaunchAgents/com.mithudso.aero-lp.plist", env


@pytest.mark.skipif(shutil.which("zsh") is None, reason="The retained macOS launcher requires zsh")
def test_service_install_defaults_to_unsigned_dry_run(tmp_path):
    target, plist, env = service_copy(tmp_path)
    r = subprocess.run(["/bin/zsh", str(target), "install"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "<string>--live</string>" not in plist.read_text()


@pytest.mark.skipif(shutil.which("zsh") is None, reason="The retained macOS launcher requires zsh")
def test_service_install_rejects_unknown_mode_before_service_action(tmp_path):
    target, plist, env = service_copy(tmp_path)
    r = subprocess.run(["/bin/zsh", str(target), "install", "--typo"], env=env, capture_output=True, text=True)
    assert r.returncode == 2
    assert not plist.exists()


@pytest.mark.parametrize("kind", ["income", "gas"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True])
def test_rebalance_decision_refuses_invalid_income_or_cost(kind, bad):
    from aero_lp.strategy import CostInputs, EarnInputs, Range, StrategyConfig, decide

    with pytest.raises(ValueError):
        cost = CostInputs(value_usd=1000, pool_fee=0.0005, gas_usd=bad if kind == "gas" else 0.1, swap_fraction=0.5)
        earn = EarnInputs(earn_usd_per_day_new=bad if kind == "income" else 50, earn_usd_per_day_current=0)
        decide(
            tick=1500,
            current=Range(-1000, 1000),
            spacing=100,
            sigma_daily=0.02,
            cfg=StrategyConfig(),
            cost=cost,
            earn=earn,
            consecutive_edge_checks=0,
            minutes_since_last_rebalance=None,
        )


@pytest.mark.parametrize("bad", [None, float("inf"), -1, 0, True])
def test_provider_omits_unavailable_or_invalid_stable_quote(bad):
    coins = providers.Coins(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"coins": {"base:" + USDC: {"price": bad}}})
            )
        )
    )
    assert coins.current([USDC]) == {}


def test_live_permission_is_checked_after_gas_estimation_before_signing(tmp_path):
    eth = FakeEth()
    killed = []
    signed = []

    def authorize():
        if killed:
            raise RuntimeError("kill switch engaged")

    def estimate(request):
        killed.append(True)
        return 100_000

    eth.estimate_gas = estimate
    account = SimpleNamespace(
        address=ACCT.address, sign_transaction=lambda request: signed.append(request) or ACCT.sign_transaction(request)
    )
    runner = journal_runner(tmp_path, LaggingChain(eth, 0), account, [T0], ExecConfig(), before_send=authorize)
    with pytest.raises(RuntimeError, match="kill switch"):
        runner.execute([TX])
    assert signed == [] and eth.sent == [] and runner.journal.records() == []


def test_kill_after_intent_persistence_retires_only_the_known_unsent_intent(tmp_path, monkeypatch):
    eth = FakeEth()
    killed = []

    def authorize():
        if killed:
            raise RuntimeError("kill switch engaged")

    runner = journal_runner(tmp_path, LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), before_send=authorize)
    original = runner.journal.before_submit

    def persist(*args, **kwargs):
        original(*args, **kwargs)
        killed.append(True)

    monkeypatch.setattr(runner.journal, "before_submit", persist)
    with pytest.raises(RuntimeError, match="kill switch"):
        runner.execute([TX])
    assert eth.sent == []
    (record,) = runner.journal.records()
    assert record["receipt"] is None and record["processed"]
    assert record["cancelled_before_broadcast"] is True
    assert record["hash"] == "0x" + "01" * 32 and record["intent"] == {"kind": "approve"}
    assert not runner._uncertain and runner.sent_hashes == [] and runner._next_nonce is None
    from aero_lp.submissions import SubmissionJournal

    restarted = SubmissionJournal(runner.journal.path, ACCT.address)
    for _ in range(2):
        restarted.reconcile(SimpleNamespace(), lambda *a: pytest.fail("unsent intent has no chain effects"))

    # Emergency withdrawal must pass the real reconciliation entry point after this cancellation.
    from test_engine import make_engine
    from test_engine_audit import setup_live

    from aero_lp import engine as engine_module
    from aero_lp.executor import RebalanceResult

    eng = make_engine(tmp_path)
    setup_live(eng, monkeypatch)
    eng.journal = restarted
    calls = []

    def withdraw(pos, mode):
        calls.append(mode)
        return RebalanceResult(None, False, ["remove"], [], {"remove": 100000})

    monkeypatch.setattr(engine_module, "Rebalancer", lambda *a: SimpleNamespace(withdraw=withdraw))
    eng.withdraw(42, True, object())
    assert calls == ["sim", "live"] and eth.sent == []


def test_daemon_and_engine_pass_their_permission_callback_to_live_runner(tmp_path, monkeypatch):
    from test_daemon import make_daemon
    from test_engine import make_engine

    from aero_lp import daemon as daemon_module
    from aero_lp import engine as engine_module

    daemon = make_daemon.__wrapped__(tmp_path, monkeypatch)(live_mode=True)
    callbacks = []
    monkeypatch.setattr(daemon_module, "LiveRunner", lambda *args, **kwargs: callbacks.append(kwargs["before_send"]))
    daemon.runner([T0], None)
    assert callbacks.pop() == daemon.assert_acting
    engine = make_engine(tmp_path)
    monkeypatch.setattr(engine_module, "LiveRunner", lambda *args, **kwargs: callbacks.append(kwargs["before_send"]))
    engine._live_runner(ACCT, [T0], POOL)
    assert callbacks.pop() == engine._gate


@pytest.mark.skipif(shutil.which("zsh") is None, reason="The retained macOS launcher requires zsh")
@pytest.mark.parametrize("mode", ["--live", "--dry-run"])
def test_service_explicit_modes_are_preserved(tmp_path, mode):
    target, plist, env = service_copy(tmp_path)
    result = subprocess.run(["/bin/zsh", str(target), "install", mode], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert ("<string>--live</string>" in plist.read_text()) == (mode == "--live")


def test_finite_inputs_cannot_overflow_into_an_admitted_rebalance():
    from aero_lp.strategy import CostInputs, EarnInputs, Range, StrategyConfig, decide

    with pytest.raises(ValueError, match="finite"):
        decide(
            tick=1500,
            current=Range(-1000, 1000),
            spacing=100,
            sigma_daily=0.02,
            cfg=StrategyConfig(),
            cost=CostInputs(1000, 0.0005, 0.1, 0.5),
            earn=EarnInputs(1e308, 0),
            consecutive_edge_checks=0,
            minutes_since_last_rebalance=None,
        )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "input_price,output_price,refused",
    [(100, 100, False), (100, 1, True), (1e308, 1e308, False), (1e308, 1e306, True), (1e-300, 1e-302, True)],
)
def test_conversion_market_ratio_survives_extreme_finite_quotes(
    monkeypatch, reverse, input_price, output_price, refused
):
    pool = SimpleNamespace(
        token0=SimpleNamespace(address=WETH, decimals=18),
        token1=SimpleNamespace(address=USDC, decimals=18),
        raw_price=1.0,
        fee=0.003,
        address=POOL,
    )
    monkeypatch.setattr(safe_exit, "best_direct_pool", lambda *a: pool)
    token_in, token_out = (USDC, WETH) if reverse else (WETH, USDC)
    eng = SimpleNamespace(cfg=SimpleNamespace(execution=ExecConfig(min_swap_usd=0)))
    step = safe_exit.plan_conversion(
        eng, token_in, 10**24, token_out, {token_in.lower(): input_price, token_out.lower(): output_price}
    )
    assert bool(step.refused) is refused
    if refused:
        assert "below market" in step.refused and step.min_out_raw == 0 and not step.route_pool
    else:
        assert step.route_pool == POOL and 0 < step.min_out_raw < step.expected_out_raw


def test_overflowing_exit_display_valuation_stays_unknown(tmp_path):
    from test_safe_exit import pos

    value = safe_exit._value_usd(pos(), {WETH.lower(): 1e308, USDC.lower(): 1e308}, (10**24, 0))
    assert value is None


def test_cancelled_intent_is_excluded_from_related_receipt_recovery(tmp_path):
    from aero_lp.submissions import SubmissionJournal

    journal = SubmissionJournal(tmp_path / "submissions.json", ACCT.address)
    confirmed, unsent = "0x" + "01" * 32, "0x" + "02" * 32
    journal.before_submit(confirmed, 0, TX, "one-operation", None, [T0])
    journal.receipt(confirmed, FakeEth().wait_for_transaction_receipt(confirmed, 1))
    journal.before_submit(unsent, 1, TX, "one-operation", None, [T0])
    journal.cancel_before_broadcast(unsent, "one-operation")
    effects = []

    def apply(record, group):
        assert all(r["receipt"] is not None for r in group)
        effects.append((record["hash"], [r["hash"] for r in group]))

    journal.reconcile(SimpleNamespace(), apply)
    assert effects == [(confirmed, [confirmed])]
    assert all(r["processed"] for r in journal.records())


def test_failed_cancellation_persistence_keeps_runner_and_journal_blocked(tmp_path, monkeypatch):
    killed = []

    def gate():
        if killed:
            raise RuntimeError("kill switch engaged")

    eth = FakeEth()
    runner = journal_runner(tmp_path, LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), before_send=gate)
    original = runner.journal.before_submit

    def persist(*a, **kw):
        original(*a, **kw)
        killed.append(True)

    def cannot_persist(*a):
        raise OSError("synthetic cancellation fsync failure")

    monkeypatch.setattr(runner.journal, "before_submit", persist)
    monkeypatch.setattr(runner.journal, "cancel_before_broadcast", cannot_persist)
    with pytest.raises(OSError, match="cancellation fsync"):
        runner.execute([TX])
    (record,) = runner.journal.records()
    assert record["receipt"] is None and not record["processed"] and runner._uncertain
    assert eth.sent == [] and runner._lease is None


def test_ambiguous_send_never_uses_prebroadcast_cancellation(tmp_path, monkeypatch):
    from aero_lp.submissions import PendingSubmission

    eth = FakeEth()
    attempts = []

    def send(raw):
        attempts.append(raw)
        raise TimeoutError("synthetic ambiguous broadcast")

    eth.send_raw_transaction = send
    runner = journal_runner(tmp_path, LaggingChain(eth, 0), ACCT, [T0], ExecConfig(), before_send=lambda: None)
    monkeypatch.setattr(
        runner.journal, "cancel_before_broadcast", lambda *a: pytest.fail("an attempted send is never cancellable")
    )
    with pytest.raises(TimeoutError, match="ambiguous broadcast"):
        runner.execute([TX])
    with pytest.raises(PendingSubmission, match="unresolved"):
        runner.execute([TX])
    (record,) = runner.journal.records()
    assert len(attempts) == 1 and runner._uncertain and not record["processed"]
    assert record["receipt"] is None and "cancelled_before_broadcast" not in record


@pytest.mark.parametrize("other_group,has_receipt", [(True, False), (False, True)])
def test_prebroadcast_cancellation_cannot_retire_another_operation_or_a_receipt(tmp_path, other_group, has_receipt):
    from aero_lp.submissions import PendingSubmission, SubmissionJournal

    journal = SubmissionJournal(tmp_path / "submissions.json", ACCT.address)
    tx_hash = "0x" + "01" * 32
    journal.before_submit(tx_hash, 0, TX, "original", None, [T0])
    if has_receipt:
        journal.receipt(tx_hash, FakeEth().wait_for_transaction_receipt(tx_hash, 1))
    before = journal.path.read_bytes()
    with pytest.raises(PendingSubmission, match="cannot cancel"):
        journal.cancel_before_broadcast(tx_hash, "other" if other_group else "original")
    assert journal.path.read_bytes() == before
