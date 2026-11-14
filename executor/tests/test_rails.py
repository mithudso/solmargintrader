"""Every rail, one test each, plus the property that dry-run applies the same trade rails as live."""

import calendar
import time
from decimal import Decimal

import pytest
from conftest import PRICES, QUOTE_SOL_USDC

from executor import gates, rails
from executor.config import VALIDATION_STRATEGY, Config
from executor.errors import Refused
from executor.journal import Journal
from executor.jupiter import parse_quote
from executor.quote import evaluate
from executor.tokens import USDC_MINT, WSOL_MINT, resolve

SOL, USDC = resolve("SOL"), resolve("USDC")
PRICE_MAP = {
    WSOL_MINT: Decimal(str(PRICES[WSOL_MINT]["usdPrice"])),
    USDC_MINT: Decimal(str(PRICES[USDC_MINT]["usdPrice"])),
}
NOW = 1_800_000_000.0  # Fixed daytime UTC fixture; subtracting 100 seconds must stay on the same day.


def report(side="sell", usd=1.0, **over):
    """A QuoteReport worth ~`usd` dollars. sell = SOL->USDC, buy = USDC->SOL."""
    sol_price = float(PRICE_MAP[WSOL_MINT])
    if side == "sell":
        tin, tout = SOL, USDC
        in_raw = int(usd / sol_price * 1e9)
        out_raw = int(usd * 1e6 * 0.9997 / float(PRICE_MAP[USDC_MINT]) * float(PRICE_MAP[USDC_MINT]))
    else:
        tin, tout = USDC, SOL
        in_raw = int(usd * 1e6)
        out_raw = int(usd / sol_price * 1e9)
    raw = dict(QUOTE_SOL_USDC)
    raw.update(inputMint=tin.mint, outputMint=tout.mint, inAmount=str(in_raw), outAmount=str(out_raw),
               otherAmountThreshold=str(int(out_raw * 0.995)), priceImpactPct="0")  # fmt: skip
    raw.update(over)
    q = parse_quote(raw, tin.mint, tout.mint, in_raw, 50)
    return evaluate(Config(), q, tin, tout, PRICE_MAP)


def journal_with(tmp_path, trades):
    """trades: list of (strategy, side, base_raw, quote_usd, ts, fee_usd) written as confirmed outcomes."""
    j = Journal(tmp_path / "j.jsonl")
    for i, (strategy, side, base_raw, quote_usd, ts, fee_usd) in enumerate(trades):
        iid = f"t{i}"
        j.append("intent", iid, ts=ts, strategy=strategy, side=side, base_mint=WSOL_MINT, in_usd=str(quote_usd))
        j.append("sending", iid, ts=ts, signature=f"sig{i}")
        rec = j.append("result", iid, ts=ts, status="confirmed", signature=f"sig{i}", base_raw=base_raw,
                       quote_usd=str(quote_usd), fee_usd=str(fee_usd))  # fmt: skip
        assert rec
    return j


def check(cfg, tmp_path, rep, journal=None, **kw):
    kw.setdefault("strategy", "s1")
    kw.setdefault("live", False)
    kw.setdefault("exit_only", False)
    kw.setdefault("kill_present", False)
    kw.setdefault("native_lamports", 1_000_000_000)
    kw.setdefault("now", NOW)
    return rails.check_trade(cfg, tmp_path, journal or Journal(tmp_path / "j.jsonl"), rep, **kw)


def refused(cfg, tmp_path, rep, text, **kw):
    with pytest.raises(Refused) as ei:
        check(cfg, tmp_path, rep, **kw)
    assert any(text in p for p in ei.value.problems), ei.value.problems


def test_side_classification():
    assert rails.classify(report("buy")) == ("buy", WSOL_MINT)
    assert rails.classify(report("sell")) == ("sell", WSOL_MINT)


def test_max_trade_usd(tmp_path):
    cfg = Config()
    cfg.rails.max_trade_usd = 5
    check(cfg, tmp_path, report("buy", 5.0))
    refused(cfg, tmp_path, report("buy", 5.2), "max_trade_usd")


def test_max_position_usd_is_per_strategy(tmp_path):
    cfg = Config()
    cfg.rails.max_trade_usd = 10
    j = journal_with(tmp_path, [("s1", "buy", 222_000_000, 20, NOW - 10, 0)])
    check(cfg, tmp_path, report("buy", 5.0), j)  # $20 + $5 = $25 is at the cap
    refused(cfg, tmp_path, report("buy", 5.5), "max_position_usd", journal=j)
    check(cfg, tmp_path, report("buy", 9.0), j, strategy="s2")  # another strategy has its own $25


def test_position_cap_default_is_the_owners_25(tmp_path):
    assert Config().rails.max_position_usd == 25 and Config().rails.daily_loss_stop_usd == 10


def test_long_or_flat_no_shorts(tmp_path):
    cfg = Config()
    j = journal_with(tmp_path, [("s1", "buy", 50_000_000, 5, NOW - 10, 0)])
    check(cfg, tmp_path, report("sell", 1.0), j)  # selling part of what it holds is fine
    sold_too_much = report("sell", 1.0)
    object.__setattr__(sold_too_much.quote, "in_raw", 60_000_000)  # more than the 50,000,000 held
    refused(cfg, tmp_path, sold_too_much, "long or flat", journal=j)
    refused(cfg, tmp_path, report("sell", 1.0), "long or flat", strategy="s-empty")


def test_strategy_trades_must_be_usdc_against_a_base(tmp_path):
    cfg = Config()
    cfg.rails.allowed_mints = ["SOL", "USDC", "USDT"]
    tin, tout = resolve("USDC"), resolve("USDT")
    raw = dict(QUOTE_SOL_USDC)
    raw.update(
        inputMint=tin.mint, outputMint=tout.mint, inAmount="1000000", outAmount="999000", otherAmountThreshold="994000"
    )
    q = parse_quote(raw, tin.mint, tout.mint, 1_000_000, 50)
    rep = evaluate(cfg, q, tin, tout, {USDC_MINT: Decimal(1), tout.mint: Decimal(1)})
    refused(cfg, tmp_path, rep, "USDC <-> base only")


def test_daily_loss_stop_blocks_buys_but_not_sells_or_exits(tmp_path):
    cfg = Config()
    today = NOW - 100
    # Buy 1 SOL-worth for $20, sell it for $9: a realized loss of $11, over the $10 stop.
    j = journal_with(
        tmp_path, [("s1", "buy", 1_000_000_000, 20, today, 0), ("s1", "sell", 1_000_000_000, 9, today + 1, 0)]
    )
    refused(cfg, tmp_path, report("buy", 1.0), "daily_loss_stop_usd", journal=j)
    # A different strategy is unaffected.
    check(cfg, tmp_path, report("buy", 1.0), j, strategy="s2")
    # A sell/exit reduces risk and is never stopped by it.
    (tmp_path / "x").mkdir()
    j2 = journal_with(tmp_path / "x", [("s1", "buy", 1_000_000_000, 20, today, 10.5)])
    refused(cfg, tmp_path, report("buy", 1.0), "daily_loss_stop_usd", journal=j2)
    check(cfg, tmp_path, report("sell", 1.0), j2, exit_only=True)


def test_loss_resets_on_the_next_utc_day(tmp_path):
    cfg = Config()
    yesterday = NOW - 2 * 86400
    j = journal_with(
        tmp_path, [("s1", "buy", 1_000_000_000, 20, yesterday, 0), ("s1", "sell", 1_000_000_000, 9, yesterday + 1, 0)]
    )
    check(cfg, tmp_path, report("buy", 1.0), j)


def test_fees_count_toward_the_daily_loss(tmp_path):
    cfg = Config()
    j = journal_with(tmp_path, [("s1", "buy", 1_000_000_000, 5, NOW - 5, 10.5)])
    refused(cfg, tmp_path, report("buy", 1.0), "daily_loss_stop_usd", journal=j)


def test_unrealized_loss_on_the_open_position_counts(tmp_path):
    cfg = Config()
    # 0.1 SOL bought for $20 is worth ~$9 at the reference price: ~$11 unrealized loss.
    j = journal_with(tmp_path, [("s1", "buy", 100_000_000, 20, NOW - 5, 0)])
    refused(cfg, tmp_path, report("buy", 1.0), "daily_loss_stop_usd", journal=j)


def test_sol_reserve(tmp_path):
    cfg = Config()
    refused(
        cfg,
        tmp_path,
        report("sell", 1.0),
        "min_sol_reserve_lamports",
        strategy=None,
        native_lamports=5_000_000 + 10_000_000,
    )
    check(cfg, tmp_path, report("sell", 1.0), strategy=None, native_lamports=5_000_000 + 12_000_000)


def test_live_needs_mode_live_and_a_strategy(tmp_path):
    cfg = Config()
    refused(cfg, tmp_path, report("buy"), 'config mode is not "live"', live=True)
    cfg.mode = "live"
    refused(cfg, tmp_path, report("buy"), "needs a strategy id", live=True, strategy=None)


def test_kill_blocks_live_but_not_dry_run_or_exit(tmp_path):
    cfg = Config()
    cfg.mode = "live"
    cfg.gates.allow_failed_research_gate = True
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 0, 0
    rep = report("buy")
    refused(cfg, tmp_path, rep, "KILL file", live=True, kill_present=True)
    check(cfg, tmp_path, rep, live=False, kill_present=True)  # dry-run is not live
    j = journal_with(tmp_path, [("s1", "buy", 100_000_000, 5, NOW - 5, 0)])
    check(cfg, tmp_path, report("sell"), j, live=True, kill_present=True, exit_only=True)


def test_unresolved_send_blocks_live(tmp_path):
    cfg = Config()
    cfg.mode = "live"
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 0, 0
    cfg.gates.allow_failed_research_gate = True
    j = Journal(tmp_path / "j.jsonl")
    j.append("intent", "x1", strategy="s1")
    j.append("sending", "x1", signature="abc")
    refused(cfg, tmp_path, report("buy"), "unresolved send", live=True, journal=j)
    check(cfg, tmp_path, report("buy"), journal=j, live=False)  # a dry-run is unaffected


def test_exit_requires_a_sell_and_skips_the_trade_cap(tmp_path):
    cfg = Config()
    cfg.rails.max_trade_usd = 1
    j = journal_with(tmp_path, [("s1", "buy", 1_000_000_000, 20, NOW - 5, 0)])
    check(cfg, tmp_path, report("sell", 15.0), j, exit_only=True)
    refused(cfg, tmp_path, report("buy", 0.5), "reduce-only", exit_only=True)
    refused(cfg, tmp_path, report("sell", 1.0), "needs the strategy", exit_only=True, strategy=None)


def test_quote_problems_are_rail_problems(tmp_path):
    cfg = Config()
    refused(cfg, tmp_path, report("buy", priceImpactPct="0.05"), "price impact")


# -- gates -----------------------------------------------------------------------------------------------------


def live_cfg():
    cfg = Config()
    cfg.mode = "live"
    return cfg


def test_live_refused_without_research_and_soak(tmp_path):
    cfg = live_cfg()
    with pytest.raises(Refused) as ei:
        check(cfg, tmp_path, report("buy"), live=True)
    text = " ".join(ei.value.problems)
    assert "soak gate" in text and "research gate" in text


def test_live_allowed_with_pass_and_soak(tmp_path):
    cfg = live_cfg()
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 1, 2
    t0 = NOW - 7200
    for i in range(4):
        gates.record_dry_run(tmp_path, cfg, "s1", t0 + i * 1500)
    gates.record_research_result(tmp_path, cfg, "s1", "pass", "backtest-run-1", now=NOW - 60)
    d = check(cfg, tmp_path, report("buy"), live=True)
    assert any("research gate passed" in n for n in d.notes)


def test_failed_research_result_blocks_and_latest_wins(tmp_path):
    cfg = live_cfg()
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 0, 0
    gates.record_research_result(tmp_path, cfg, "s1", "pass", "old", now=NOW - 500)
    gates.record_research_result(tmp_path, cfg, "s1", "fail", "newer", now=NOW - 100)
    refused(cfg, tmp_path, report("buy"), "research gate", live=True)


def test_override_flag_is_logged_on_every_use(tmp_path):
    cfg = live_cfg()
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 0, 0
    gates.record_dry_run(tmp_path, cfg, "s1", NOW - 10)
    cfg.gates.allow_failed_research_gate = True
    for _ in range(2):
        d = check(cfg, tmp_path, report("buy"), live=True)
        assert any("OVERRIDDEN" in n for n in d.notes)
    lines = (tmp_path / "gate-overrides.jsonl").read_text().splitlines()
    assert len(lines) == 2 and '"strategy": "s1"' in lines[0]


def test_override_does_not_bypass_the_soak(tmp_path):
    cfg = live_cfg()
    cfg.gates.allow_failed_research_gate = True
    refused(cfg, tmp_path, report("buy"), "soak gate", live=True)


def test_soak_resets_when_rails_change(tmp_path):
    cfg = live_cfg()
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 0.5, 1
    gates.record_dry_run(tmp_path, cfg, "s1", NOW - 7200)
    gates.record_dry_run(tmp_path, cfg, "s1", NOW - 5800)
    gates.record_dry_run(tmp_path, cfg, "s1", NOW - 4400)
    assert gates.soak_status(tmp_path, cfg, "s1")[0] is True
    cfg.rails.max_position_usd = 24
    ok, why = gates.soak_status(tmp_path, cfg, "s1")
    assert ok is False and "changed" in why
    gates.record_dry_run(tmp_path, cfg, "s1", NOW)
    assert gates.soak_status(tmp_path, cfg, "s1")[0] is False  # restarted from zero


def test_a_stopped_runner_cannot_bank_downtime(tmp_path):
    cfg = live_cfg()
    cfg.gates.soak_hours, cfg.gates.min_dry_runs = 1, 1
    gates.record_dry_run(tmp_path, cfg, "s1", NOW - 90000)
    gates.record_dry_run(tmp_path, cfg, "s1", NOW)  # a day later: one gap credits at most MAX_TICK_GAP_S
    assert gates.soak_status(tmp_path, cfg, "s1")[0] is False


def test_unreadable_gate_records_fail_closed(tmp_path):
    cfg = live_cfg()
    (tmp_path / "soak.json").write_text("{not json")
    (tmp_path / "research-gate.json").write_text("[]")
    assert gates.soak_status(tmp_path, cfg, "s1")[0] is False
    assert gates.research_status(tmp_path, cfg, "s1")[0] is False


def test_record_research_validates(tmp_path):
    cfg = Config()
    from executor.errors import BadParams

    with pytest.raises(BadParams):
        gates.record_research_result(tmp_path, cfg, "s1", "maybe", "x")
    with pytest.raises(BadParams):
        gates.record_research_result(tmp_path, cfg, "s1", "pass", " ")


# -- reserved validation strategy ------------------------------------------------------------------------------


def test_validation_strategy_is_off_by_default(tmp_path):
    cfg = live_cfg()
    refused(cfg, tmp_path, report("sell", 1.0), "needs [validation].enabled", strategy=VALIDATION_STRATEGY, live=True)


def test_validation_strategy_skips_gates_but_is_capped_in_code(tmp_path):
    cfg = live_cfg()
    cfg.validation.enabled = True
    cfg.rails.max_trade_usd = 10  # config cannot loosen the code cap
    d = check(cfg, tmp_path, report("sell", 1.0), strategy=VALIDATION_STRATEGY, live=True)
    assert d.gates_exempt and any("gates skipped" in n for n in d.notes)
    refused(cfg, tmp_path, report("sell", 2.5), "capped at $2", strategy=VALIDATION_STRATEGY, live=True)


def test_validation_strategy_daily_cap(tmp_path):
    cfg = live_cfg()
    cfg.validation.enabled = True
    j = Journal(tmp_path / "j.jsonl")
    for i in range(2):
        j.append("intent", f"v{i}", strategy=VALIDATION_STRATEGY, in_usd="1.9")
        j.append("sending", f"v{i}", signature=f"s{i}")
    j.append("result", "v0", status="confirmed", signature="s0", base_raw=1, quote_usd="1.9", fee_usd="0")
    j.append("result", "v1", status="confirmed", signature="s1", base_raw=1, quote_usd="1.9", fee_usd="0")
    refused(
        cfg,
        tmp_path,
        report("sell", 1.0),
        "per rolling 24 h",
        strategy=VALIDATION_STRATEGY,
        live=True,
        journal=j,
        now=time.time(),
    )


def test_validation_exemption_applies_only_to_the_reserved_id(tmp_path):
    cfg = live_cfg()
    cfg.validation.enabled = True
    refused(cfg, tmp_path, report("sell", 1.0), "soak gate", strategy="path-validation-2", live=True)
