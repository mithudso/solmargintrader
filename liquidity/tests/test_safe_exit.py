"""exit-to-safe with a stubbed engine: dry run signs nothing, live sets KILL, every check fails closed."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from web3 import Web3

from aero_lp import addresses, cli, safe_exit
from aero_lp.config import Config, SafetyConfig
from aero_lp.executor import RebalanceError, RebalanceResult
from aero_lp.metrics import KNOWN_TOKENS

OWNER = "0x" + "ab" * 20
WETH = Web3.to_checksum_address(addresses.WETH)
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
PRICES = {WETH.lower(): 2000.0, USDC.lower(): 1.0}


def token(addr, sym, dec):
    return SimpleNamespace(address=addr, symbol=sym, decimals=dec)


POOL = SimpleNamespace(
    address="0x" + "11" * 20, token0=token(WETH, "WETH", 18), token1=token(USDC, "USDC", 6), tick_spacing=100
)


def pos(tid=1):
    return SimpleNamespace(token_id=tid, pool=POOL, staked=True)


def result(stages=("unstake", "remove", "collect", "burn"), amounts=(10**18, 2000 * 10**6), hashes=("0xaa",)):
    return RebalanceResult(None, False, list(stages), list(hashes), {}, tuple(amounts), 0)


class StubEngine:
    def __init__(self, tmp_path, *, gas=0.1, blocks=(), fail_live=None, **safety):
        self.cfg = Config(OWNER, [7], state_path=str(tmp_path / "state.json"), safety=SafetyConfig(**safety))
        self.calls: list[tuple[int, bool]] = []
        self.gas, self.blocks, self.fail_live = gas, list(blocks), fail_live
        self.market = SimpleNamespace(token_prices_usd=lambda a: PRICES)
        self.state = SimpleNamespace(slot=lambda t: SimpleNamespace(current_token_id=t + 100))
        self.gated = 0

    def withdraw(self, tid, live, signer=None):
        self.calls.append((tid, live))
        if live and self.fail_live:
            raise self.fail_live
        return pos(tid), result(), self.gas

    def pool_blocks(self, pool, live):
        return self.blocks

    def _gate(self):
        self.gated += 1

    def reconcile_submissions(self):
        pass


def run(eng, tmp_path, ids=(1,), live=False, **kw):
    return safe_exit.run_exit(eng, list(ids), live=live, signer=object() if live else None, root=tmp_path, **kw)


def test_dry_run_is_the_default_signs_nothing_and_does_not_kill(tmp_path):
    eng = StubEngine(tmp_path)
    rep = run(eng, tmp_path)
    assert eng.calls == [(1, False)] and not (tmp_path / "KILL").exists()
    assert rep.ok and rep.positions[0].status == "ready" and rep.positions[0].value_usd == pytest.approx(4000.0)
    text = safe_exit.format_plan(rep)
    assert "DRY RUN" in text and "unstake -> remove -> collect -> burn" in text and "1 WETH" in text


def test_live_sets_kill_first_then_withdraws_every_position(tmp_path):
    eng = StubEngine(tmp_path)
    seen = []
    orig = eng.withdraw
    eng.withdraw = lambda t, live, s=None: (seen.append((t, live, (tmp_path / "KILL").exists())), orig(t, live, s))[1]
    rep = run(eng, tmp_path, ids=(1, 2), live=True)
    assert [s for s in seen if s[1]] == [(1, True, True), (2, True, True)]  # KILL existed before each live send
    assert rep.ok and rep.killed_by_exit and [p.status for p in rep.positions] == ["exited"] * 2
    assert "set by exit-to-safe" in (tmp_path / "KILL").read_text()
    path = safe_exit.write_report(tmp_path, rep)
    assert json.loads(path.read_text())["ok"] is True


def test_existing_kill_file_is_left_untouched(tmp_path):
    (tmp_path / "KILL").write_text("killed from soltui")
    rep = run(StubEngine(tmp_path), tmp_path, live=True)
    assert not rep.killed_by_exit and (tmp_path / "KILL").read_text() == "killed from soltui"


@pytest.mark.parametrize(
    "kw, text",
    [
        ({"blocks": ["spot is 90 bps from the 10-min TWAP"]}, "TWAP"),
        ({"gas": 5.0}, "max_gas_usd"),
        ({"gas": float("nan")}, "max_gas_usd"),
    ],
)
def test_price_and_gas_checks_block_the_position_in_dry_run_and_live(tmp_path, kw, text):
    for live in (False, True):
        eng = StubEngine(tmp_path, **kw)
        rep = run(eng, tmp_path, live=live)
        assert rep.positions[0].status == "blocked" and text in rep.positions[0].reason and not rep.ok
        assert all(not lv for _, lv in eng.calls)  # never sent


def test_missing_prices_block_sizing(tmp_path):
    eng = StubEngine(tmp_path)

    def boom(_):
        raise RuntimeError("feed down")

    rep = run(eng, tmp_path, prices_fn=boom)
    assert rep.positions[0].status == "blocked" and "USD prices unavailable" in rep.positions[0].reason
    assert "RuntimeError" in rep.positions[0].reason and "feed down" not in rep.positions[0].reason


def test_position_larger_than_max_position_usd_can_still_exit(tmp_path):
    rep = run(StubEngine(tmp_path, max_position_usd=10.0), tmp_path, live=True)
    assert rep.positions[0].status == "exited"


def test_live_failure_stops_and_reports_the_partial_result(tmp_path):
    partial = result(stages=("unstake",), hashes=("0xdead",))
    eng = StubEngine(tmp_path, fail_live=RebalanceError("withdraw failed after stage 'unstake'", partial))
    rep = run(eng, tmp_path, ids=(1, 2), live=True)
    assert [p.status for p in rep.positions] == ["failed", "ready"] and rep.positions[0].tx_hashes == ["0xdead"]
    assert [c for c in eng.calls if c[1]] == [(1, True)] and not rep.ok


def test_live_needs_a_signer(tmp_path):
    with pytest.raises(ValueError):
        safe_exit.run_exit(StubEngine(tmp_path), [1], live=True, root=tmp_path)


def test_managed_ids_union_config_slots_and_ledger_deduplicated(tmp_path):
    eng = StubEngine(tmp_path)
    assert safe_exit.managed_token_ids(eng.cfg, eng, [5, 107, 5], None) == [107, 5]
    assert safe_exit.managed_token_ids(eng.cfg, eng, [5], [9, 9]) == [9]


# ----- conversion (off by default)


class ConvEngine(StubEngine):
    def __init__(self, tmp_path, route, **kw):
        super().__init__(tmp_path, **kw)
        self.route = route
        self.chain = SimpleNamespace(
            factory=SimpleNamespace(
                functions=SimpleNamespace(tickSpacings=lambda: SimpleNamespace(call=lambda: [100]))
            ),
            pool_address=lambda a, b, ts: "0x" + "22" * 20 if route else safe_exit.ZERO,
            pool_state=lambda addr: self.route,
        )


def route(price_raw, liquidity=10**18):
    # token0 WETH (18) / token1 USDC (6): raw price = USDC raw per WETH raw
    return SimpleNamespace(
        address="0x" + "22" * 20,
        token0=token(WETH, "WETH", 18),
        token1=token(USDC, "USDC", 6),
        raw_price=price_raw,
        fee=0.0005,
        liquidity=liquidity,
    )


def test_conversion_is_off_by_default(tmp_path):
    rep = run(ConvEngine(tmp_path, route(2000 * 1e-12)), tmp_path)
    assert rep.positions[0].converts == [] and "no conversion" in safe_exit.format_plan(rep)


def test_conversion_plan_uses_a_direct_pool_with_slippage_floor(tmp_path):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    rep = run(eng, tmp_path, convert_to="USDC")
    (step,) = rep.positions[0].converts  # only WETH: the USDC leg is already the target
    assert step.token == "WETH" and not step.refused and step.min_out_raw < step.expected_out_raw
    assert 0 < step.min_out_raw == int(step.expected_out_raw * (1 - eng.cfg.execution.max_slippage_bps / 1e4))
    assert step.expected_out_raw == pytest.approx(1999 * 10**6, rel=1e-3)


def test_conversion_refused_when_pool_price_is_far_below_market(tmp_path):
    rep = run(ConvEngine(tmp_path, route(1500 * 1e-12)), tmp_path, convert_to="USDC")
    assert "below market" in rep.positions[0].converts[0].refused


def test_conversion_refused_without_a_direct_pool(tmp_path):
    rep = run(ConvEngine(tmp_path, None), tmp_path, convert_to="USDC")
    assert "no direct pool" in rep.positions[0].converts[0].refused


def test_conversion_refused_when_a_price_is_missing(tmp_path):
    rep = run(
        ConvEngine(tmp_path, route(2000 * 1e-12)),
        tmp_path,
        convert_to="USDC",
        prices_fn=lambda a: {WETH.lower(): 2000.0},
    )
    assert "no USD price" in rep.positions[0].converts[0].refused


def test_live_conversion_simulates_then_sends_only_the_withdrawn_amount(tmp_path, monkeypatch):
    sent = []

    class FakeRB:
        def __init__(self, *a):
            pass

        def swap_exact(self, route_, tok, amount, runner, min_out):
            sent.append((type(runner).__name__, amount, min_out))
            r = RebalanceResult(None, False, ["swap"], ["0xbb"], {"x": 100_000})
            r.amount_out = 1990 * 10**6
            return r

    monkeypatch.setattr("aero_lp.executor.Rebalancer", FakeRB)
    monkeypatch.setattr(safe_exit, "SimRunner", lambda *a, **k: type("SimRunner", (), {})())
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    eng.chain.gas_price_wei = lambda: 10**6
    eng._live_runner = lambda *a, **kw: type("LiveRunner", (), {})()
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    step = rep.positions[0].converts[0]
    assert [s[0] for s in sent] == ["SimRunner", "LiveRunner"] and sent[0][1] == sent[1][1] == 10**18
    assert step.tx_hashes == ["0xbb"] and step.out_raw == 1990 * 10**6 and eng.gated == 1


def test_actual_withdrawal_replaces_dry_conversion_budget_not_wallet_balance(tmp_path, monkeypatch):
    sent = []

    class FakeRB:
        def __init__(self, *a):
            pass

        def swap_exact(self, _route, _token, amount, runner, _minimum):
            sent.append((type(runner).__name__, amount))
            return RebalanceResult(None, False, ["swap"], [], {"swap": 100_000})

    monkeypatch.setattr("aero_lp.executor.Rebalancer", FakeRB)
    monkeypatch.setattr(safe_exit, "SimRunner", lambda *a, **kw: type("SimRunner", (), {})())
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    eng.chain.gas_price_wei = lambda: 10**6
    eng.chain.erc20_balances = lambda *a, **kw: [100 * 10**18, 50_000 * 10**6]
    eng._live_runner = lambda *a, **kw: type("LiveRunner", (), {})()
    eng.withdraw = lambda tid, live, signer=None: (
        pos(tid),
        result(amounts=(5 * 10**17, 1000 * 10**6)) if live else result(),
        0.1,
    )
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    step = rep.positions[0].converts[0]
    assert not step.refused
    assert step.amount_raw == 5 * 10**17
    assert sent == [("SimRunner", 5 * 10**17), ("LiveRunner", 5 * 10**17)]


@pytest.mark.parametrize("aero_in_pool", [False, True])
def test_actual_non_pool_reward_is_a_separate_budget_without_double_count(tmp_path, monkeypatch, aero_in_pool):
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    current = pos()
    if aero_in_pool:
        current.pool = SimpleNamespace(**{**vars(POOL), "token0": token(addresses.AERO_TOKEN, "AERO", 18)})
    dry = result()
    dry.aero_claimed = 99 * 10**18
    actual = result(amounts=(3 * 10**18, 5 * 10**6))
    actual.aero_claimed = 2 * 10**18
    eng.withdraw = lambda tid, live, signer=None: (current, actual if live else dry, 0.1)
    calls = []
    monkeypatch.setattr(
        safe_exit,
        "plan_conversion",
        lambda _eng, tok, amount, target, prices: safe_exit.ConvertStep(KNOWN_TOKENS[tok.lower()], tok, amount),
    )
    monkeypatch.setattr(
        safe_exit, "_convert_live", lambda _eng, plan, step, *a: calls.append((step.token, step.amount_raw))
    )
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    expected = [("AERO", 3 * 10**18)] if aero_in_pool else [("WETH", 3 * 10**18), ("AERO", 2 * 10**18)]
    assert calls == expected
    assert [(s.token, s.amount_raw) for s in rep.positions[0].converts] == expected


@pytest.mark.parametrize("binding", ["correct", "owner", "ledger"])
def test_conversion_accounts_confirmed_withdrawal_through_bound_journal(tmp_path, monkeypatch, binding):
    from test_daemon import make_pos
    from test_executor import TX, FakeChain, transfer_log

    from aero_lp.engine import Engine
    from aero_lp.executor import Rebalancer
    from aero_lp.ledger import Ledger
    from aero_lp.recovery import LedgerRecovery
    from aero_lp.state import State
    from aero_lp.submissions import SubmissionJournal

    current = make_pos(1, staked=False)
    ledger = Ledger(tmp_path / "ledger.sqlite")
    ledger.open_slot("1", current.pool.address, "WETH/USDC", WETH, USDC, 18, 6, 1)
    ledger.flow("1", "deposit", 0.5, 1000, 2000)
    journal = SubmissionJournal(tmp_path / "submissions.json", OWNER, ledger_path=ledger.path)
    tx = Rebalancer(FakeChain(), OWNER, Config(OWNER).execution).remove_calls(current, 12345, 0.003)
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    eng.state = State(eng.cfg.state_file)
    eng.state.slot(1)
    eng.chain.gas_price_wei = lambda: 10**6
    eng.chain.pool_state = lambda address: current.pool if address == current.pool.address else eng.route
    eng.recovery_handler = LedgerRecovery(eng.cfg, eng.chain, ledger, lambda: PRICES).apply
    eng.recover_submission = lambda record, group: Engine.recover_submission(eng, record, group)
    bound = journal
    if binding == "owner":
        bound = SubmissionJournal(journal.path, "0x" + "cd" * 20, ledger_path=ledger.path)
    elif binding == "ledger":
        bound = SubmissionJournal(journal.path, OWNER, ledger_path=tmp_path / "other.sqlite")
    eng.submission_journal = lambda: bound
    eng.reconcile_submissions = lambda: Engine.reconcile_submissions(eng)
    withdraw_hash, convert_hash = "0x" + "01" * 32, "0x" + "02" * 32

    def receipt(h, logs=()):
        return {
            "transactionHash": h,
            "status": 1,
            "blockNumber": 101,
            "gasUsed": 90_000,
            "effectiveGasPrice": 10**6,
            "logs": list(logs),
        }

    def withdraw(tid, live, signer=None):
        if live:
            journal.before_submit(
                withdraw_hash,
                0,
                tx,
                "withdraw",
                current.pool.address,
                [WETH, USDC],
                accounting={"scope": "slot", "slot": "1"},
            )
            journal.receipt(
                withdraw_hash,
                receipt(
                    withdraw_hash,
                    [
                        transfer_log(WETH, current.pool.address, OWNER, 5 * 10**17),
                        transfer_log(USDC, current.pool.address, OWNER, 1000 * 10**6),
                    ],
                ),
            )
        return current, result(amounts=(5 * 10**17, 1000 * 10**6), hashes=[withdraw_hash]), 0.1

    eng.withdraw = withdraw
    conversions = []

    class FakeRB:
        def __init__(self, *a):
            pass

        def swap_exact(self, _route, _token, _amount, runner, _minimum):
            assert journal.records()[0]["processed"]
            assert ledger.pnl("1").withdrawn_usd == 2000
            assert ledger.slot_row("1")["closed_at"] is not None
            conversions.append(type(runner).__name__)
            return RebalanceResult(None, False, ["swap"], [convert_hash], {"swap": 100_000})

    monkeypatch.setattr("aero_lp.executor.Rebalancer", FakeRB)
    monkeypatch.setattr(safe_exit, "SimRunner", lambda *a, **kw: type("SimRunner", (), {})())

    def live_runner(*a, **kw):
        assert kw["wallet"]
        journal.before_submit(
            convert_hash, 1, TX, "conversion", eng.route.address, [WETH, USDC], accounting={"scope": "wallet"}
        )
        journal.receipt(convert_hash, receipt(convert_hash))
        return type("LiveRunner", (), {})()

    eng._live_runner = live_runner
    try:
        rep = run(eng, tmp_path, live=True, convert_to="USDC")
        step = rep.positions[0].converts[0]
        if binding == "correct":
            assert not step.refused
            assert conversions == ["SimRunner", "LiveRunner"]
            eng.reconcile_submissions()
            assert all(r["processed"] for r in journal.records())
            assert ledger.pnl("1").withdrawn_usd == 2000
        else:
            assert binding in step.refused
            assert conversions == []
            assert not journal.records()[0]["processed"]
            assert ledger.pnl("1").withdrawn_usd == 0
    finally:
        ledger.db.close()


def test_live_conversion_blocked_by_gas_cap_leaves_coins_in_wallet(tmp_path, monkeypatch):
    class FakeRB:
        def __init__(self, *a):
            pass

        def swap_exact(self, *a):
            return RebalanceResult(None, False, [], [], {"x": 10**9})

    monkeypatch.setattr("aero_lp.executor.Rebalancer", FakeRB)
    monkeypatch.setattr(safe_exit, "SimRunner", lambda *a, **k: object())
    eng = ConvEngine(tmp_path, route(2000 * 1e-12))
    eng.chain.gas_price_wei = lambda: 10**10
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    assert rep.positions[0].status == "exited" and "max_gas_usd" in rep.positions[0].converts[0].refused


# ----- CLI


def test_cli_exit_to_safe_defaults_to_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path))
    cfgfile = tmp_path / "c.toml"
    cfgfile.write_text(f'owner = "{OWNER}"\ntoken_ids = [7]\nstate_path = "{tmp_path / "state.json"}"\n')
    eng = StubEngine(tmp_path)
    monkeypatch.setattr(cli, "_engine", lambda a: (eng.cfg, eng))
    monkeypatch.setattr("aero_lp.wallet.load_signer", lambda *a, **k: pytest.fail("dry run must not load the signer"))
    assert cli.main(["exit-to-safe", "-c", str(cfgfile)]) == 0
    assert eng.calls == [(107, False)] and "DRY RUN" in capsys.readouterr().out and not (tmp_path / "KILL").exists()


def test_exit_is_not_blocked_by_the_live_gates(tmp_path, monkeypatch):
    """No soak record and no research result: live daemon is refused, exit-to-safe is not."""
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path))
    c = Config(OWNER)
    with pytest.raises(Exception, match="refusing live mode"):
        from aero_lp import gates

        gates.check_live_allowed(tmp_path, c)
    eng = StubEngine(tmp_path)
    assert run(eng, tmp_path, live=True).ok


def test_known_tokens_cover_every_exit_target():
    assert set(safe_exit.SYMBOL_TO_ADDRESS) >= {"USDC", "USDT", "DAI"}
    assert "USDC" in KNOWN_TOKENS.values()
