import copy
from decimal import Decimal

import pytest
from conftest import PRICES, QUOTE_SOL_USDC, FakeHttp, fixture

from executor import lifi
from executor.config import Config
from executor.errors import BadParams, Refused
from executor.jupiter import Jupiter, parse_quote
from executor.quote import evaluate, fetch_report
from executor.tokens import USDC_MINT, WSOL_MINT, resolve

SOL, USDC = resolve("SOL"), resolve("USDC")
PRICE_MAP = {WSOL_MINT: Decimal("90.0707"), USDC_MINT: Decimal("0.9997")}


def quote(**over):
    raw = copy.deepcopy(QUOTE_SOL_USDC)
    raw.update(over)
    return parse_quote(raw, WSOL_MINT, USDC_MINT, 10_000_000, 50)


def test_recorded_quote_parses_and_is_acceptable():
    rep = evaluate(Config(), quote(), SOL, USDC, PRICE_MAP)
    assert rep.ok, rep.problems
    d = rep.to_dict()
    assert d["route"][0]["label"] and d["min_out_raw"] <= d["out_raw"]
    assert d["reference"]["source"] == "jupiter-price-api"
    assert abs(d["deviation_bps"]) < 100


@pytest.mark.parametrize(
    "over",
    [
        {"inputMint": USDC_MINT},
        {"outAmount": "0"},
        {"otherAmountThreshold": "999999999999"},
        {"inAmount": "10000001"},
        {"swapMode": "ExactOut"},
        {"slippageBps": 51},
        {"platformFee": {"amount": "1", "feeBps": 10}},
        {"priceImpactPct": None},
        {"priceImpactPct": "-0.1"},
        {"priceImpactPct": "abc"},
        {"routePlan": []},
        {"routePlan": [{"swapInfo": {}}]},
        {"outAmount": None},
    ],
)
def test_malformed_quote_is_refused(over):
    with pytest.raises(Refused):
        quote(**over)


def test_price_impact_over_cap_is_a_problem():
    rep = evaluate(Config(), quote(priceImpactPct="0.01"), SOL, USDC, PRICE_MAP)  # 100 bps
    assert not rep.ok and any("price impact" in p for p in rep.problems)


def test_deviation_worse_and_better_than_reference_both_refused():
    worse = evaluate(Config(), quote(outAmount="880000", otherAmountThreshold="875600"), SOL, USDC, PRICE_MAP)
    better = evaluate(Config(), quote(outAmount="920000", otherAmountThreshold="915400"), SOL, USDC, PRICE_MAP)
    assert any("deviates" in p for p in worse.problems) and worse.deviation_bps > 0
    assert any("deviates" in p for p in better.problems) and better.deviation_bps < 0


def test_missing_price_refuses_rather_than_guessing():
    with pytest.raises(Refused, match="no independent price reference"):
        evaluate(Config(), quote(), SOL, USDC, {WSOL_MINT: Decimal(90)})


def test_prices_endpoint_drops_unusable_entries():
    http = FakeHttp()
    http.on("/price/v3", {WSOL_MINT: {"usdPrice": 0}, USDC_MINT: {"usdPrice": "0.99"}, "other": "x"})
    prices = Jupiter("https://lite-api.jup.ag", http, min_gap_s=0).prices([WSOL_MINT, USDC_MINT])
    assert WSOL_MINT not in prices and prices[USDC_MINT] == Decimal("0.99")


def test_fetch_report_enforces_allowlist_and_same_token():
    http = FakeHttp()
    cfg = Config()
    jup = Jupiter(cfg.jupiter_base_url, http, min_gap_s=0)
    with pytest.raises(Refused, match="same token"):
        fetch_report(cfg, jup, SOL, SOL, 1, 50)
    cfg.rails.allowed_mints = ["SOL"]
    with pytest.raises(Refused, match="not in rails.allowed_mints"):
        fetch_report(cfg, jup, SOL, USDC, 1, 50)
    assert http.calls == []  # refused before any network call


def test_jupiter_retries_429_a_bounded_number_of_times():
    from executor.errors import HttpError

    calls = {"n": 0}

    def flaky(_):
        calls["n"] += 1
        raise HttpError("HTTP 429", 429)

    http = FakeHttp()
    http.on("/price/v3", flaky)
    jup = Jupiter("https://lite-api.jup.ag", http, min_gap_s=0, sleep=lambda s: None)
    with pytest.raises(HttpError):
        jup.prices([WSOL_MINT])
    assert calls["n"] == Jupiter.RETRIES_429 + 1


def test_build_swap_refuses_a_failed_jupiter_simulation_and_missing_fields():
    jup_http = FakeHttp()
    jup = Jupiter("https://lite-api.jup.ag", jup_http, min_gap_s=0)
    q = quote()
    jup_http.on(
        "/swap/v1/swap", {"swapTransaction": "AA==", "lastValidBlockHeight": 5, "simulationError": {"error": "x"}}
    )
    with pytest.raises(Refused, match="simulation failed"):
        jup.build_swap(q, "owner", 1000)
    jup_http.on("/swap/v1/swap", {"lastValidBlockHeight": 5})
    with pytest.raises(Refused, match="no swapTransaction"):
        jup.build_swap(q, "owner", 1000)
    jup_http.on("/swap/v1/swap", {"swapTransaction": "AA=="})
    with pytest.raises(Refused, match="lastValidBlockHeight"):
        jup.build_swap(q, "owner", 1000)


def test_swap_request_carries_the_priority_fee_cap_and_no_platform_fee():
    http = FakeHttp()
    seen = {}

    def swap(body):
        seen.update(body)
        return {"swapTransaction": "AA==", "lastValidBlockHeight": 5, "simulationError": None}

    http.on("/swap/v1/swap", swap)
    Jupiter("https://lite-api.jup.ag", http, min_gap_s=0).build_swap(quote(), "owner", 123_456)
    assert seen["prioritizationFeeLamports"]["priorityLevelWithMaxLamports"]["maxLamports"] == 123_456
    assert "feeAccount" not in seen and seen["wrapAndUnwrapSol"] is True


# -- cross-chain (quote only) ----------------------------------------------------------------------------------


def lifi_http():
    http = FakeHttp()
    http.on("/v1/quote", fixture("lifi_quote_usdc_base.json"))
    return http


def test_cross_chain_quote_is_quote_only_and_recorded():
    out = lifi.quote_cross_chain(Config(), lifi_http(), "owner", USDC, 5_000_000, "base", "USDC")
    assert out["mode"] == "quote-only" and out["executable"] is False
    assert "transactionRequest" not in out and "not implemented" in out["gap"]
    assert out["to_chain"] == "base" and Decimal(out["out_amount"]) > 0
    assert out["acceptable"] is True


def test_cross_chain_cost_over_cap_is_refused_flagged():
    cfg = Config()
    cfg.bridge.max_cost_bps = 1
    out = lifi.quote_cross_chain(cfg, lifi_http(), "owner", USDC, 5_000_000, "base", "USDC")
    assert out["acceptable"] is False and "bridge.max_cost_bps" in out["problems"][0]


def test_cross_chain_missing_numbers_refuse():
    http = FakeHttp()
    bad = fixture("lifi_quote_usdc_base.json")
    bad["estimate"].pop("toAmountUSD")
    http.on("/v1/quote", bad)
    with pytest.raises(Refused):
        lifi.quote_cross_chain(Config(), http, "owner", USDC, 5_000_000, "base", "USDC")


def test_cross_chain_unsupported_inputs():
    with pytest.raises(BadParams):
        lifi.quote_cross_chain(Config(), lifi_http(), "o", USDC, 1, "narnia", "USDC")
    with pytest.raises(BadParams):
        lifi.quote_cross_chain(Config(), lifi_http(), "o", USDC, 1, "base", "PEPE")


def test_prices_fixture_is_what_the_tests_assume():
    assert WSOL_MINT in PRICES and USDC_MINT in PRICES
