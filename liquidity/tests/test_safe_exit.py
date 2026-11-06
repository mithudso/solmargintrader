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
    assert rep.positions[0].status == "blocked" and "feed down" in rep.positions[0].reason


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
    eng._live_runner = lambda *a: type("LiveRunner", (), {})()
    rep = run(eng, tmp_path, live=True, convert_to="USDC")
    step = rep.positions[0].converts[0]
    assert [s[0] for s in sent] == ["SimRunner", "LiveRunner"] and sent[0][1] == sent[1][1] == 10**18
    assert step.tx_hashes == ["0xbb"] and step.out_raw == 1990 * 10**6 and eng.gated == 1


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
