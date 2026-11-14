"""Provider comparison (offline): DefiLlama parsing, AMM mapping, Tier 2 LVR, the generic v3 and v4 readers against
a fake chain, ranking, and the report. HTTP goes through httpx.MockTransport; no network, no chain."""

from __future__ import annotations

import json
import math
import time
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from web3 import Web3

from aero_lp import abi, addresses, clmath, metrics, providers
from aero_lp.chain import ZERO, Token
from aero_lp.market import MarketData, vol_from_closes
from aero_lp.metrics import NO_DATA, PoolMetrics
from aero_lp.providers import (
    AmmType,
    Coins,
    Env,
    LlamaPool,
    ProviderRow,
    classify,
    evaluate_quoted,
    load_llama,
    rank_rows,
    select_pools,
)
from aero_lp.providers_report import render_report
from aero_lp.strategy import StrategyConfig, lvr_fraction_per_day

WETH = addresses.WETH
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
USDT = "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2"
CBBTC = "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf"
POOL = Web3.to_checksum_address("0x" + "11" * 20)


def raw_pool(project="uniswap-v2", symbol="WETH-USDC", tokens=(WETH, USDC), **kw) -> dict[str, Any]:
    base: dict[str, Any] = {
        "chain": "Base",
        "project": project,
        "symbol": symbol,
        "tvlUsd": 2_000_000.0,
        "apyBase": 12.0,
        "apyReward": None,
        "apy": 12.0,
        "pool": f"{project}-{symbol}",
        "exposure": "multi",
        "poolMeta": None,
        "underlyingTokens": list(tokens),
        "volumeUsd1d": 500_000.0,
        "volumeUsd7d": 3_000_000.0,
        "stablecoin": False,
        "outlier": False,
        "il7d": None,
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------- DefiLlama parsing


def test_llama_pool_parses_fee_tick_spacing_and_native_tokens():
    p = LlamaPool.from_raw(raw_pool("uniswap-v3", poolMeta="0.3%"))
    assert p.fee_pips == 3000 and p.tick_spacing is None
    assert LlamaPool.from_raw(raw_pool(poolMeta="0.05%")).fee_pips == 500
    assert LlamaPool.from_raw(raw_pool(poolMeta="0.01%")).fee_pips == 100
    assert LlamaPool.from_raw(raw_pool(poolMeta="0.25%")).fee_pips == 2500
    aero = LlamaPool.from_raw(raw_pool("aerodrome-slipstream", poolMeta="CL100 - 0.015%"))
    assert aero.fee_pips == 150 and aero.tick_spacing == 100
    assert LlamaPool.from_raw(raw_pool(poolMeta=None)).fee_pips is None
    native = LlamaPool.from_raw(raw_pool(tokens=(ZERO, USDC)))
    assert native.tokens == (WETH.lower(), USDC)  # native ETH is priced as WETH
    assert LlamaPool.from_raw(raw_pool(tokens=("0x" + "ee" * 20, USDC))).tokens[0] == WETH.lower()


def test_llama_pool_tolerates_missing_and_null_numbers():
    p = LlamaPool.from_raw({"project": "x", "tvlUsd": None, "apyBase": "bad", "underlyingTokens": None})
    assert p.tvl_usd == 0.0 and p.apy_base is None and p.tokens == () and p.quoted_base_apy is None


def test_quoted_base_apy_falls_back_to_the_total_less_rewards_for_vaults():
    vault = LlamaPool.from_raw(raw_pool("beefy", apyBase=None, apy=40.0, apyReward=None))
    assert vault.quoted_base_apy == 40.0
    mixed = LlamaPool.from_raw(raw_pool("beefy", apyBase=None, apy=40.0, apyReward=10.0))
    assert mixed.quoted_base_apy == 30.0
    assert LlamaPool.from_raw(raw_pool(apyBase=7.0)).quoted_base_apy == 7.0


@pytest.mark.parametrize(
    ("project", "expected"),
    [
        ("uniswap-v3", AmmType.CONCENTRATED),
        ("pancakeswap-amm-v3", AmmType.CONCENTRATED),
        ("sushiswap-v3", AmmType.CONCENTRATED),
        ("alien-base-v3", AmmType.CONCENTRATED),
        ("aerodrome-slipstream", AmmType.CONCENTRATED),
        ("uniswap-v4", AmmType.UNISWAP_V4),
        ("kyberswap-fairflow", AmmType.UNISWAP_V4),
        ("uniswap-v2", AmmType.CONSTANT_PRODUCT),
        ("sushiswap", AmmType.CONSTANT_PRODUCT),
        ("pancakeswap-amm", AmmType.CONSTANT_PRODUCT),
        ("aerodrome-v1", AmmType.CONSTANT_PRODUCT),
        ("curve-dex", AmmType.STABLESWAP),
        ("fluid-dex", AmmType.STABLESWAP),
        ("balancer-v2", AmmType.WEIGHTED),
        ("balancer-v3", AmmType.WEIGHTED),
        ("beefy", AmmType.ALM_VAULT),
        ("stake-dao-yield", AmmType.ALM_VAULT),
        ("morpho-blue", AmmType.LENDING),
        ("aave-v3", AmmType.LENDING),
        ("clipper", AmmType.OTHER),
        ("some-unknown-dex", AmmType.OTHER),
    ],
)
def test_amm_type_mapping(project, expected):
    assert classify(project, None) is expected


def test_aerodrome_v1_pegged_pairs_are_stableswap_and_the_rest_constant_product():
    assert classify("aerodrome-v1", None, [USDC, USDT]) is AmmType.STABLESWAP
    assert classify("aerodrome-v1", None, [WETH, "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452"]) is AmmType.STABLESWAP
    assert classify("aerodrome-v1", None, [WETH, USDC]) is AmmType.CONSTANT_PRODUCT
    assert classify("aerodrome-v1", None, [WETH, "0x" + "ab" * 20]) is AmmType.CONSTANT_PRODUCT
    assert classify("uniswap-v2", None, [USDC, USDT]) is AmmType.CONSTANT_PRODUCT


def test_every_registry_venue_has_an_amm_type_the_project_map_agrees_with():
    for v in providers.REGISTRY:
        assert PROJECT_TYPES_OF(v.llama_project) is v.amm_type
        assert v.sources and v.factory and Web3.is_checksum_address(v.factory)
        assert Web3.is_checksum_address(v.position_manager)


def PROJECT_TYPES_OF(project: str) -> AmmType:
    return providers.PROJECT_TYPES[project]


def test_select_pools_applies_every_filter_and_counts_what_it_drops():
    raw = [
        raw_pool("uniswap-v2", "A-B"),
        raw_pool("uniswap-v2", "LOW-TVL", tvlUsd=50_000.0),
        raw_pool("uniswap-v2", "LOW-VOL", volumeUsd1d=100.0),
        raw_pool("uniswap-v2", "NO-VOL", volumeUsd1d=None),
        raw_pool("morpho-blue", "LEND", exposure="single"),
        raw_pool("aave-v3", "LEND2"),
        raw_pool("clipper", "RFQ"),
        raw_pool("beefy", "VAULT", volumeUsd1d=None, apyBase=None, apy=30.0),
    ]
    sel = select_pools(raw, min_tvl_usd=100_000.0, min_volume_usd=10_000.0)
    assert sorted(p.symbol for p, _ in sel.kept) == ["A-B", "VAULT"]  # a vault has no volume and needs none
    reasons = {(e["project"], e["reason"]): e["count"] for e in sel.excluded}
    assert reasons[("uniswap-v2", "24h volume below $10,000")] == 2
    assert reasons[("morpho-blue", "single-asset exposure")] == 1
    assert reasons[("aave-v3", "lending, not an LP")] == 1
    assert reasons[("clipper", "no model for this project")] == 1
    assert sel.total == len(raw)  # the low-TVL row is dropped silently: it never was a candidate


# ---------------------------------------------------------------------------- DefiLlama HTTP


def llama_transport(rows: list[dict[str, Any]], calls: list[str] | None = None):
    def handler(req: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(req.url))
        if req.url.host == "yields.llama.fi":
            other = raw_pool(chain="Ethereum", symbol="ELSEWHERE")
            return httpx.Response(200, json={"status": "success", "data": [*rows, other]})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_load_llama_filters_the_chain_caches_on_disk_and_honours_the_ttl(tmp_path):
    calls: list[str] = []
    http = httpx.Client(transport=llama_transport([raw_pool(), raw_pool("uniswap-v3", "X-Y")], calls))
    rows, info = load_llama(tmp_path, http, "base", ttl_s=3600, now=1000.0)
    assert len(rows) == 2 and info["from_cache"] is False and len(calls) == 1
    assert (tmp_path / "llama-pools-base.json").exists()
    rows2, info2 = load_llama(tmp_path, http, "base", ttl_s=3600, now=1500.0)  # inside the TTL: no request
    assert rows2 == rows and info2["from_cache"] is True and len(calls) == 1
    load_llama(tmp_path, http, "base", ttl_s=3600, now=1000.0 + 3601)  # expired
    assert len(calls) == 2
    load_llama(tmp_path, http, "base", ttl_s=3600, now=1000.0 + 3602, force=True)  # forced
    assert len(calls) == 3


def test_load_llama_ignores_a_corrupt_cache(tmp_path):
    (tmp_path / "llama-pools-base.json").write_text("{not json")
    http = httpx.Client(transport=llama_transport([raw_pool()]))
    rows, info = load_llama(tmp_path, http, "base", now=5.0)
    assert len(rows) == 1 and info["from_cache"] is False


def series_response(coin_ids: list[str], n: int = 168, drift: dict[str, float] | None = None) -> dict[str, Any]:
    coins = {}
    for i, cid in enumerate(coin_ids):
        t = cid.split(":", 1)[1]
        pts = []
        for h in range(n):
            wob = 1 + 0.01 * math.sin(h / (3 + i)) + (drift or {}).get(t, 0.0) * h
            pts.append(
                {"timestamp": 1_700_000_000 + h * 3600 + (h % 3) * 7, "price": (1.0 if t == USDC else 2000.0) * wob}
            )
        coins[cid] = {"symbol": "X", "decimals": 18, "prices": pts}
    return {"coins": coins}


def coins_transport(missing: set[str] | None = None, requests_seen: list[str] | None = None):
    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        ids = path.rsplit("/", 1)[1].split(",")
        if requests_seen is not None:
            requests_seen.append(str(req.url))
        ids = [i for i in ids if i.split(":", 1)[1] not in (missing or set())]
        if "/chart/" in path:
            span = int(req.url.params["span"])
            if span * len(ids) > 500:  # DefiLlama's real limit
                return httpx.Response(400, json={"message": "exceeds the maximum of 500"})
            return httpx.Response(200, json=series_response(ids, span))
        if "/prices/current/" in path:
            return httpx.Response(
                200,
                json={"coins": {i: {"price": 2000.0 if WETH.lower() in i else 1.0 if USDC in i else 3.0} for i in ids}},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_coins_hourly_respects_the_500_point_limit_and_aligns_a_ratio():
    seen: list[str] = []
    c = Coins(httpx.Client(transport=coins_transport(requests_seen=seen)))
    closes = c.ratio_closes(WETH, USDC)
    assert len(closes) == 168 and all(x > 0 for x in closes)
    assert vol_from_closes(closes) is not None
    c.hourly([WETH, USDC, CBBTC, USDT])  # four more tokens, two already fetched
    assert all(len(u.rsplit("/", 1)[1].split("?")[0].split(",")) <= 2 for u in seen)
    n = len(seen)
    c.hourly([WETH, USDC])  # cached: no request
    assert len(seen) == n


def test_coins_remembers_a_token_without_a_chart_and_returns_no_ratio():
    seen: list[str] = []
    c = Coins(httpx.Client(transport=coins_transport(missing={CBBTC}, requests_seen=seen)))
    assert c.ratio_closes(WETH, CBBTC) == []
    n = len(seen)
    assert c.ratio_closes(CBBTC, USDC) == []
    assert not any(CBBTC in u for u in seen[n:])  # the missing token is not asked for again


def test_coins_current_fetches_stable_quotes_and_maps_native_as_weth():
    c = Coins(httpx.Client(transport=coins_transport()))
    px = c.current([ZERO, USDC, CBBTC])
    assert px[USDC] == 0.97 and px[WETH.lower()] == 2000.0 and px[CBBTC] == 3.0


# ---------------------------------------------------------------------------- Tier 2 LVR formulas


def test_constant_product_lvr_is_sigma_squared_over_eight_per_day():
    assert providers.lvr_apr_constant_product(0.04) == pytest.approx(0.04**2 / 8 * 36500)
    assert providers.lvr_apr_constant_product(0.0) == 0.0


def test_weighted_lvr_is_sigma_squared_w_one_minus_w_over_two():
    s = 0.03
    assert providers.lvr_apr_weighted(s, 0.8) == pytest.approx(s**2 * 0.8 * 0.2 / 2 * 36500)
    assert providers.lvr_apr_weighted(s, 0.5) == pytest.approx(providers.lvr_apr_constant_product(s))
    assert providers.lvr_apr_weighted(s, 0.8) == pytest.approx(providers.lvr_apr_weighted(s, 0.2))
    assert providers.lvr_apr_weighted(s, 0.8) < providers.lvr_apr_weighted(s, 0.5)


def test_stableswap_lvr_is_the_constant_product_upper_bound():
    assert providers.lvr_apr_stableswap(0.002) == providers.lvr_apr_constant_product(0.002)


def test_alm_lvr_uses_the_volatility_range_and_exceeds_the_full_range_value():
    cfg = StrategyConfig()
    lvr, half_pct = providers.lvr_apr_alm(0.03, cfg)
    w = math.log1p(half_pct / 100)
    assert lvr == pytest.approx(lvr_fraction_per_day(w, 0.03) * 36500)
    assert lvr > providers.lvr_apr_constant_product(0.03)  # a range concentrates the loss


def test_weights_from_meta():
    assert providers.weights_from_meta("50OLAS-50USDC") == [0.5, 0.5]
    assert providers.weights_from_meta("80WETH-20USDC") == pytest.approx([0.8, 0.2])
    assert providers.weights_from_meta(None) is None
    assert providers.weights_from_meta("Curve") is None


# ---------------------------------------------------------------------------- Tier 2 rows


def quoted(project="uniswap-v2", amm=AmmType.CONSTANT_PRODUCT, sigma=0.03, hist=7.0, **raw_kw) -> ProviderRow | None:
    p = LlamaPool.from_raw(raw_pool(project, **raw_kw))
    return evaluate_quoted(p, amm, sigma, "test", hist, 5.0)


def test_constant_product_row_is_quoted_income_minus_closed_form_lvr_and_labelled():
    r = quoted(apyBase=12.0, apyReward=3.0)
    assert r is not None
    lvr = 0.03**2 / 8 * 36500
    assert r.tier == "quoted" and r.income_apr == 12.0 and r.quoted_apy_base == 12.0
    assert r.lvr_apr == pytest.approx(lvr) and r.expected_net_apr == pytest.approx(12.0 - lvr)
    assert r.edge_ratio == pytest.approx(12.0 / lvr)
    # incentives sit in their own column and never enter income or the headline net
    assert r.incentive_apr == 3.0 and r.net_apr_with_incentives == pytest.approx(r.expected_net_apr + 3.0)
    assert "quote" in r.income_source and r.confidence == "medium"
    assert r.clears_bar is False and r.actionable is False and r.replay_net_apr is None


def test_a_quoted_row_never_clears_the_bar_whatever_it_claims():
    r = quoted(apyBase=900.0, tvlUsd=50_000_000.0)
    assert r is not None and r.expected_net_apr > 100 and r.clears_bar is False


def test_weighted_row_uses_the_pool_weights_and_flags_unknown_ones():
    r = quoted("balancer-v2", AmmType.WEIGHTED, poolMeta="80WETH-20USDC", symbol="WETH-USDC")
    assert r is not None and r.lvr_apr == pytest.approx(providers.lvr_apr_weighted(0.03, 0.8))
    r2 = quoted("balancer-v3", AmmType.WEIGHTED, poolMeta=None)
    assert r2 is not None and r2.lvr_apr == pytest.approx(providers.lvr_apr_constant_product(0.03))
    assert any("weights unknown" in f for f in r2.flags)


def test_stableswap_row_is_marked_approximate_and_pegged_only():
    r = quoted(
        "curve-dex", AmmType.STABLESWAP, sigma=0.002, tokens=(WETH, "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22")
    )
    assert r is not None and any("approximate" in f and "pegged" in f for f in r.flags) and r.confidence == "low"
    unpegged = quoted("curve-dex", AmmType.STABLESWAP, sigma=0.05)
    assert unpegged is not None and any("not pegged" in f for f in unpegged.flags)


def test_alm_vault_notes_net_of_rebalancing_and_still_charges_lvr():
    r = quoted("beefy", AmmType.ALM_VAULT, apyBase=None, apy=60.0, poolMeta="Uniswap", volumeUsd1d=None)
    assert r is not None and r.income_apr == 60.0
    assert any("net of its own rebalancing" in f for f in r.flags) and r.lvr_apr > 0
    assert r.rebalance_cost_apr == 0.0 and r.best_half_width_pct and r.confidence == "low"
    curve = quoted("stake-dao-yield", AmmType.ALM_VAULT, apyBase=None, apy=3.0, poolMeta="Curve")
    assert curve is not None and any("Curve vault" in f for f in curve.flags)


def test_a_pool_with_no_base_apy_counts_income_as_zero_and_keeps_rewards_separate():
    r = quoted("aerodrome-v1", AmmType.CONSTANT_PRODUCT, apyBase=None, apy=40.0, apyReward=40.0)
    assert r is not None and r.income_apr == 0.0 and r.incentive_apr == 40.0
    assert r.expected_net_apr < 0 < r.net_apr_with_incentives + 50 and r.confidence == "low"


def test_no_sigma_means_no_row_and_outliers_and_unlisted_tokens_are_low():
    assert quoted(sigma=None) is None
    assert quoted(outlier=True).confidence == "low"  # type: ignore[union-attr]
    unlisted = quoted(tokens=(WETH, "0x" + "ab" * 20))
    assert unlisted is not None and unlisted.confidence == "low" and "unlisted token" in unlisted.flags
    short = quoted(hist=2.0)
    assert short is not None and short.confidence == "low"


# ---------------------------------------------------------------------------- the generic readers, on a fake chain


class FakeChain:
    """The part of AeroChain the providers module uses. `answers` maps (contract address, function) to a value or to
    a callable(block, args)."""

    def __init__(self, answers: dict[tuple[str, str], Any], tokens: dict[str, Token] | None = None):
        self.answers = {(a.lower(), f): v for (a, f), v in answers.items()}
        self.toks = tokens or {}
        self.w3 = SimpleNamespace(
            eth=SimpleNamespace(
                contract=lambda address, abi: SimpleNamespace(address=address, abi=abi),
                get_block=lambda n: {"number": n, "timestamp": 1_800_000_000},
            )
        )
        self.reject_seven_output_slot0 = False
        self.calls: list[tuple[str, str, Any]] = []

    def head(self):
        return 5_000_000, 1_800_000_000

    def token(self, address: str) -> Token:
        return self.toks[address.lower()]

    def gas_price_wei(self) -> int:
        return 10**7

    def multicall(self, calls, block="latest"):
        out = []
        for c in calls:
            self.calls.append((c.contract.address.lower(), c.fn, block))
            if self.reject_seven_output_slot0 and c.fn == "slot0" and c.contract.abi is abi.V3_POOL:
                raise ValueError("cannot decode 7 outputs from 6 words")
            key = (c.contract.address.lower(), c.fn)
            if key not in self.answers:
                if c.allow_failure:
                    out.append(None)
                    continue
                raise RuntimeError(f"multicall {c.fn} on {c.contract.address} failed")
            v = self.answers[key]
            out.append(v(block, c.args) if callable(v) else v)
        return out


TOK = {
    WETH.lower(): Token(Web3.to_checksum_address(WETH), "WETH", 18),
    USDC: Token(Web3.to_checksum_address(USDC), "USDC", 6),
}
SQRT = clmath.get_sqrt_ratio_at_tick(-199_000)


def v3_answers(pool: str = POOL, **over) -> dict[tuple[str, str], Any]:
    a = {
        "slot0": (SQRT, -199_000, 1, 300, 300, 0, True),
        "token0": WETH,
        "token1": USDC,
        "tickSpacing": 10,
        "fee": 500,
        "liquidity": 10**18,
        "feeGrowthGlobal0X128": 5 * 2**128,
        "feeGrowthGlobal1X128": 7 * 2**128,
        "factory": providers.VENUES["uniswap-v3"].factory,
    }
    a.update(over)
    return {(pool, k): v for k, v in a.items()}


def test_generic_v3_reader_reads_a_uniswap_pool_without_aero_fields():
    chain = FakeChain(v3_answers(), TOK)
    rd = providers.read_v3_pool(chain, POOL)  # type: ignore[arg-type]
    s = rd.state
    assert (s.tick, s.tick_spacing, s.fee_pips, s.liquidity) == (-199_000, 10, 500, 10**18)
    assert s.sqrt_price_x96 == SQRT and s.fee == pytest.approx(0.0005)
    assert s.gauge == ZERO and s.gauge_alive is False and s.staked_liquidity == 0 and s.unstaked_fee_pips == 0
    assert (s.token0.symbol, s.token1.symbol) == ("WETH", "USDC")
    assert rd.factory.lower() == providers.VENUES["uniswap-v3"].factory.lower() and rd.has_gauge is False
    assert s.fee_growth_global0 == 5 * 2**128 and s.block == 5_000_000 and s.timestamp == 1_800_000_000


def test_generic_v3_reader_marks_the_aero_only_calls_allow_failure():
    chain = FakeChain(v3_answers(), TOK)
    seen = []
    orig = chain.multicall

    def spy(calls, block="latest"):
        seen.extend((c.fn, c.allow_failure) for c in calls)
        return orig(calls, block)

    chain.multicall = spy  # type: ignore[method-assign]
    providers.read_v3_pool(chain, POOL)  # type: ignore[arg-type]
    flags = dict(seen)
    assert all(flags[f] for f in ("factory", "unstakedFee", "stakedLiquidity", "gauge"))
    assert not any(flags[f] for f in ("slot0", "token0", "token1", "tickSpacing", "fee", "liquidity"))
    assert not flags["feeGrowthGlobal0X128"] and not flags["feeGrowthGlobal1X128"]


def test_generic_v3_reader_retries_with_slipstreams_six_output_slot0():
    chain = FakeChain(v3_answers(slot0=(SQRT, -199_000, 1, 300, 300, True)), TOK)
    chain.reject_seven_output_slot0 = True
    rd = providers.read_v3_pool(chain, POOL)  # type: ignore[arg-type]
    assert rd.state.tick == -199_000


def test_generic_v3_reader_flags_a_pool_that_has_a_gauge_but_scores_it_without_one():
    gauge = Web3.to_checksum_address("0x" + "cc" * 20)
    chain = FakeChain(v3_answers(gauge=gauge, stakedLiquidity=10**17, unstakedFee=100000), TOK)
    rd = providers.read_v3_pool(chain, POOL)  # type: ignore[arg-type]
    assert rd.has_gauge is True and rd.state.gauge == ZERO and rd.state.staked_liquidity == 0


def test_generic_v3_reader_fails_when_a_required_call_is_missing():
    answers = v3_answers()
    del answers[(POOL, "liquidity")]
    with pytest.raises(RuntimeError, match="liquidity"):
        providers.read_v3_pool(FakeChain(answers, TOK), POOL)  # type: ignore[arg-type]


def test_find_v3_pools_reads_factory_get_pool_and_tries_every_tier_without_a_fee():
    v = providers.VENUES["uniswap-v3"]
    a, b = WETH.lower(), USDC
    p500 = Web3.to_checksum_address("0x" + "aa" * 20)
    p3000 = Web3.to_checksum_address("0x" + "bb" * 20)

    def get_pool(block, args):
        _, _, fee = args
        return {500: p500, 3000: p3000}.get(fee, ZERO)

    chain = FakeChain({(v.factory, "getPool"): get_pool})
    got = providers.find_v3_pools(chain, v, [(a, b, 500), (a, b, 3000), (a, b, 10000), (a, b, None)])  # type: ignore[arg-type]
    assert got[(a, b, 500)] == p500 and got[(a, b, 3000)] == p3000
    assert got[(a, b, 10000)] is None  # the factory has no such pool: nothing is invented
    assert got[(a, b, None)] == p500  # first existing tier in the venue's list (100, 500, ...)


def test_growth_delta_walks_back_to_a_shorter_window_when_history_is_missing():
    def read(block: int) -> tuple[int, int]:
        if block < 1_000_000 - 43_200 // 4:  # no state older than 6 h
            raise RuntimeError("missing trie node")
        return (100 + (block - 900_000) * 10, 200)

    d0, d1, days = providers._growth_delta(read, 1_000_000)
    assert days == pytest.approx(0.25) and d1 == 0 and d0 == 10 * (43_200 // 4)
    d0, d1, days = providers._growth_delta(
        lambda b: (_ for _ in ()).throw(RuntimeError("x")) if b < 1_000_000 else (1, 1), 1_000_000
    )
    assert (d0, d1, days) == (0, 0, 0.0)


def test_growth_delta_handles_counter_wrap():
    mod = 1 << 256
    d0, _, days = providers._growth_delta(lambda b: (5 if b == 100_000 else mod - 3, 0), 100_000)
    assert d0 == (5 - (mod - 3)) % mod == 8 and days == 1.0


def v4_chain(pool_id: str, hooks: str = ZERO, fee: int = 3000, key_present: bool = True) -> FakeChain:
    v = providers.VENUES["uniswap-v4"]
    pid = bytes.fromhex(pool_id[2:])
    key = (USDC, USDT, fee, 1, hooks) if key_present else (ZERO, ZERO, 0, 0, ZERO)

    def growth(block, args):
        assert args[0] == pid
        return (10_000 * 2**128 + (block - 5_000_000) * 2**100, 20_000 * 2**128)

    chain = FakeChain(
        {
            (v.position_manager, "poolKeys"): lambda block, args: (
                (_ for _ in ()).throw(AssertionError) if args[0] != pid[:25] else key
            ),
            (v.state_view, "getSlot0"): (SQRT, -199_000, 0, 100),
            (v.state_view, "getLiquidity"): 10**15,
            (v.state_view, "getFeeGrowthGlobals"): growth,
        },
        {**TOK, USDT: Token(Web3.to_checksum_address(USDT), "USDT", 6)},
    )
    return chain


def test_v4_reader_uses_state_view_for_state_and_the_position_manager_for_the_key():
    pool_id = "0x" + "ab" * 32
    rd = providers.read_v4_pool(v4_chain(pool_id, fee=3000), pool_id)  # type: ignore[arg-type]
    assert rd is not None
    s = rd.state
    assert s.address == pool_id and s.tick_spacing == 1 and s.liquidity == 10**15
    assert s.fee_pips == 100  # the live lpFee from slot0, not the key's static fee
    assert (s.token0.symbol, s.token1.symbol) == ("USDC", "USDT") and s.gauge == ZERO
    assert rd.hooks == ZERO and rd.dynamic_fee is False
    d0, d1, days = rd.fee_delta
    assert days == 1.0 and d1 == 0 and d0 == 43_200 * 2**100  # growth at head minus growth a day back


def test_v4_reader_detects_dynamic_fee_hooks_and_native_currency():
    pool_id = "0x" + "cd" * 32
    hook = Web3.to_checksum_address("0x" + "dd" * 20)
    rd = providers.read_v4_pool(v4_chain(pool_id, hooks=hook, fee=0x800000), pool_id)  # type: ignore[arg-type]
    assert rd is not None and rd.dynamic_fee is True and rd.hooks == hook

    v = providers.VENUES["uniswap-v4"]
    chain = v4_chain(pool_id)
    chain.answers[(v.position_manager.lower(), "poolKeys")] = (ZERO, USDC, 500, 10, ZERO)
    rd = providers.read_v4_pool(chain, pool_id)  # type: ignore[arg-type]
    assert (
        rd is not None and rd.state.token0.symbol == "ETH" and rd.state.token0.address == Web3.to_checksum_address(WETH)
    )


def test_v4_reader_returns_none_for_an_unknown_key_or_a_bad_id():
    pool_id = "0x" + "ab" * 32
    assert providers.read_v4_pool(v4_chain(pool_id, key_present=False), pool_id) is None  # type: ignore[arg-type]
    assert providers.read_v4_pool(v4_chain(pool_id), "0x1234") is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- scoring a pool end to end (offline)


def gt_transport(closes: list[float]):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "api.geckoterminal.com" and "/ohlcv/" in req.url.path:
            rows = [[i, c, c, c, c, 1.0] for i, c in reversed(list(enumerate(closes)))]
            return httpx.Response(200, json={"data": {"attributes": {"ohlcv_list": rows}}})
        if "coins.llama.fi" in req.url.host:
            return coins_transport().handle_request(req)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def make_env(chain, closes) -> Env:
    http = httpx.Client(transport=gt_transport(closes))
    market = MarketData(client=http)
    return Env(chain, market, Coins(http), 50.0, StrategyConfig(), 5.0, gas_price_wei=10**6)  # type: ignore[arg-type]


def wobble(n=168) -> list[float]:
    return [0.0005 * (1 + 0.004 * math.sin(i / 3)) for i in range(n)]


class FeeChain(FakeChain):
    def fee_growth_delta(self, pool: str, head: int):
        return 3 * 2**128 // 10**9, 2 * 2**128 // 10**9, 1.0


def test_score_v3_runs_a_uniswap_pool_through_the_shared_scoring_and_labels_it_measured():
    chain = FeeChain(v3_answers(), TOK)
    env = make_env(chain, wobble())
    row = providers.score_v3(env, "uniswap-v3", "uniswap-v3", POOL, 3_000_000.0, 4_000_000.0, None)
    assert row.tier == "measured" and row.venue == "uniswap-v3" and row.amm_type == "concentrated"
    assert row.venue_info["factory"] == providers.VENUES["uniswap-v3"].factory
    assert row.venue_info["position_manager"] == providers.VENUES["uniswap-v3"].position_manager
    assert row.venue_info["pool"] == POOL and row.actionable is True
    assert "measured" in row.income_source and "feeGrowthGlobal" in row.income_source
    assert all(isinstance(x, float) and math.isfinite(x) for x in (row.expected_net_apr, row.lvr_apr, row.income_apr))
    assert row.sigma_source.startswith("geckoterminal") and row.replay_net_apr is not None
    json.dumps(row.to_json(), allow_nan=False)


def test_score_v3_matches_evaluate_pool_for_the_same_pool_without_a_gauge():
    """The venue-neutral path and the Aero path share `score_pool`: with no gauge the numbers are identical."""
    chain = FeeChain(v3_answers(), TOK)
    env = make_env(chain, wobble())
    rd = providers.read_v3_pool(chain, POOL)  # type: ignore[arg-type]
    m1, d1 = providers.score_onchain(env, rd.state, chain.fee_growth_delta(POOL, 1), 3e6, 4e6, True)
    prices = env.prices_for([WETH, USDC])
    econ = metrics.economics_from(rd.state, prices, {"volume_24h_usd": 4e6}, 0.0, chain.fee_growth_delta(POOL, 1))
    ctx = {
        "prices": prices,
        "eth_usd": prices[WETH.lower()],
        "tvl_usd": 3e6,
        "volume_24h_usd": 4e6,
        "fee_history_days": 1.0,
    }
    m2, d2 = metrics.score_pool(
        rd.state, econ, ctx, vol_from_closes(wobble()), m1.sigma_source, 7.0, wobble(), 50.0, env.cfg, 10**6
    )
    assert m1.to_json() == m2.to_json() and d1 == d2
    assert m1.best_mode == "fees" and d1.net_gauge_apr is None and m1.gauge_active is False


def test_score_v3_refuses_a_pool_whose_factory_is_not_the_registered_one():
    other = Web3.to_checksum_address("0x" + "99" * 20)
    env = make_env(FeeChain(v3_answers(factory=other), TOK), wobble())
    with pytest.raises(RuntimeError, match="not the registered"):
        providers.score_v3(env, "uniswap-v3", "uniswap-v3", POOL, 3e6, 4e6, None)


def test_score_v3_for_an_unregistered_fork_is_capped_at_medium_and_not_marked_actionable_by_registry():
    chain = FeeChain(v3_answers(factory=Web3.to_checksum_address("0x" + "77" * 20)), TOK)
    row = providers.score_v3(make_env(chain, wobble()), "baseswap-v3", "baseswap-v3", POOL, 3e6, 4e6, None)
    assert row.confidence in ("medium", "low") and any("not in the registry" in f for f in row.flags)
    assert row.actionable is False and row.venue_info["pool"] == POOL


def test_score_v3_without_fee_growth_history_falls_back_and_drops_to_low_confidence():
    class NoHistory(FeeChain):
        def fee_growth_delta(self, pool, head):
            raise RuntimeError("no state history")

    row = providers.score_v3(
        make_env(NoHistory(v3_answers(), TOK), wobble()), "uniswap-v3", "uniswap-v3", POOL, 3e6, 4e6, None
    )
    assert row.confidence == "low" and any("income not measured" in f for f in row.flags)
    assert "estimate" in row.income_source and row.clears_bar is False


def test_score_v3_rejects_a_pool_with_no_liquidity():
    env = make_env(FeeChain(v3_answers(liquidity=0), TOK), wobble())
    with pytest.raises(RuntimeError, match="no active liquidity"):
        providers.score_v3(env, "uniswap-v3", "uniswap-v3", POOL, 3e6, 4e6, None)


def test_score_v4_marks_hooked_pools_and_caps_their_confidence():
    pool_id = "0x" + "ee" * 32
    hook = Web3.to_checksum_address("0x" + "dd" * 20)
    env = make_env(v4_chain(pool_id, hooks=hook), wobble())
    row = providers.score_v4(env, pool_id, 3e6, 4e6, None)
    assert row.venue == "uniswap-v4" and row.amm_type == "uniswap-v4" and row.venue_info["hooks"] == hook
    assert row.confidence in ("medium", "low") and any("hook" in f for f in row.flags)
    assert row.venue_info["state_view"] == providers.UNISWAP_V4_STATE_VIEW


def test_score_v4_raises_for_an_unknown_pool_key():
    pool_id = "0x" + "ee" * 32
    env = make_env(v4_chain(pool_id, key_present=False), wobble())
    with pytest.raises(RuntimeError, match="pool key"):
        providers.score_v4(env, pool_id, 3e6, 4e6, None)


def test_pair_sigma_falls_back_to_defillama_when_geckoterminal_fails():
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "api.geckoterminal.com":
            return httpx.Response(404)
        return coins_transport().handle_request(req)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    env = Env(None, MarketData(client=http), Coins(http), 50.0, StrategyConfig(), 5.0)
    s, src, days, closes = providers.pair_sigma(env, POOL, WETH, USDC, False)
    assert s is not None and src.startswith("defillama") and days == pytest.approx(7.0) and len(closes) == 168


# ---------------------------------------------------------------------------- rows, ranking, the bar


def metrics_fixture(**kw) -> PoolMetrics:
    base = dict(
        pool=POOL, pair="WETH/USDC", token0=WETH, token1=USDC, tick_spacing=10, fee_pct=0.05, tvl_usd=3e6,
        volume_24h_usd=4e6, turnover=1.3, sigma_daily_pct=2.0, sigma_source="t", fee_apr_ref=30.0, aero_apr_ref=0.0,
        lvr_apr_ref=10.0, edge_ratio=3.0, best_mode="fees", best_half_width_pct=5.0, expected_net_apr=12.0,
        rebalances_per_week=1.0, cost_per_rebalance_usd=0.1, break_even_deposit_usd=20.0, staked_share=0.0,
        gauge_active=False, confidence="high", flags=[], history_days=3.0, backtest_net_apr=9.0,
        backtest_half_width_pct=5.0, backtest_days=7.0, backtest_deploy_apr=8.0,
    )  # fmt: skip
    base.update(kw)
    return PoolMetrics(**base)


def detail(**kw) -> metrics.ScoreDetail:
    base = dict(
        income_apr=25.0, lvr_apr=10.0, rebalance_cost_apr=3.0, net_fees_only_apr=12.0, net_gauge_apr=None,
        income_measured=True, fee_history_days=1.0,
    )  # fmt: skip
    base.update(kw)
    return metrics.ScoreDetail(**base)


def row_for(m: PoolMetrics, d: metrics.ScoreDetail, llama: LlamaPool | None = None, **kw) -> ProviderRow:
    return providers.row_from_metrics(m, d, "uniswap-v3", "uniswap-v3", AmmType.CONCENTRATED, llama, 5.0, {}, **kw)


def test_incentives_stay_in_their_own_column_and_never_enter_income_or_net():
    llama = LlamaPool.from_raw(raw_pool("uniswap-v3", apyBase=40.0, apyReward=20.0, poolMeta="0.05%"))
    r = row_for(metrics_fixture(), detail(), llama)
    assert r.income_apr == 25.0 and r.expected_net_apr == 12.0
    assert r.incentive_apr == 20.0 and r.net_apr_with_incentives == 32.0
    assert r.quoted_apy_base == 40.0  # the quote is kept beside the measurement, labelled
    assert r.clears_bar is True  # model 12 and replay 8 are both >= 5, edge 3, high confidence, measured


def test_an_aero_row_counting_gauge_emissions_gets_no_extra_incentive():
    llama = LlamaPool.from_raw(raw_pool("aerodrome-slipstream", apyBase=3.0, apyReward=30.0))
    r = row_for(metrics_fixture(best_mode="aero", gauge_active=True), detail(net_gauge_apr=12.0), llama)
    assert r.incentive_apr is None and r.net_apr_with_incentives == r.expected_net_apr
    assert "gauge" in r.income_source


@pytest.mark.parametrize(
    ("kw", "clears"),
    [
        ({}, True),
        ({"backtest_deploy_apr": 4.0}, False),  # replay below the bar
        ({"expected_net_apr": 4.0}, False),  # model below the bar
        ({"edge_ratio": 1.1}, False),  # edge below 1.2
        ({"confidence": "low"}, False),
        ({"backtest_days": 0.0}, False),  # no replay at all
        ({"confidence": "medium"}, True),
    ],
)
def test_clears_bar_needs_model_replay_edge_and_confidence(kw, clears):
    assert row_for(metrics_fixture(**kw), detail()).clears_bar is clears


def test_unmeasured_income_and_no_data_values_become_none_not_garbage():
    r = row_for(metrics_fixture(expected_net_apr=NO_DATA, backtest_deploy_apr=NO_DATA, edge_ratio=1e9), detail())
    assert r.expected_net_apr is None and r.replay_net_apr is None and r.edge_ratio is None
    assert r.net_apr_with_incentives is None and r.clears_bar is False
    json.dumps(r.to_json(), allow_nan=False)


def mini(net, conf="high", tier="measured", venue="x") -> ProviderRow:
    return ProviderRow(
        venue, venue, "concentrated", tier, "p", "A/B", None, 1e6, None, "s", 1.0, None, 1.0, 0.0, 1.0, net, net,
        None, None, None, None, "t", conf, False,
    )  # fmt: skip


def test_ranking_puts_low_confidence_last_whatever_its_apr_and_orders_by_net():
    rows = [
        mini(500.0, "low", "quoted", "a"),
        mini(-3.0, "high", "measured", "b"),
        mini(8.0, "medium", "quoted", "c"),
        mini(2.0, "high", "measured", "d"),
        mini(None, "high", "measured", "e"),
        mini(900.0, "low", "measured", "f"),
        mini(NO_DATA, "medium", "measured", "g"),
    ]
    order = [r.venue for r in rank_rows(rows)]
    assert order[:3] == ["c", "d", "b"]  # non-low, by net
    assert set(order[3:5]) == {"e", "g"}  # no usable net: below the usable ones of their band
    assert order[5:] == ["f", "a"]  # low confidence last, still ordered by net


def test_ranking_breaks_a_tie_in_favour_of_the_measured_row():
    order = [r.tier for r in rank_rows([mini(5.0, "medium", "quoted"), mini(5.0, "medium", "measured")])]
    assert order == ["measured", "quoted"]


def test_summarize_counts_discovered_measured_and_quoted_and_picks_the_best_ranked_pool():
    sel = select_pools([raw_pool("uniswap-v2", f"P{i}", apyBase=float(i)) for i in (2, 4, 6)], 1e5, 1e4)
    rows = rank_rows([mini(3.0, "medium", "quoted", "uniswap-v2"), mini(7.0, "high", "measured", "uniswap-v2")])
    s = providers.summarize(rows, sel)
    assert len(s) == 1
    u = s[0]
    assert u["provider"] == "uniswap-v2" and u["pools_discovered"] == 3
    assert (u["pools_measured"], u["pools_quoted"]) == (1, 1)
    assert u["median_quoted_apy"] == 4.0 and u["median_measured_edge"] == 1.0
    assert u["best_pool"]["tier"] == "measured" and u["best_pool"]["expected_net_apr"] == 7.0


# ---------------------------------------------------------------------------- report


def sample_doc() -> dict[str, Any]:
    sel = select_pools([raw_pool("uniswap-v2", "WETH-USDC")], 1e5, 1e4)
    rows = rank_rows([
        row_for(metrics_fixture(), detail()),
        mini(-1.0, "medium", "quoted", "uniswap-v2"),
        mini(300.0, "low", "quoted", "beefy"),
    ])  # fmt: skip
    return {
        "schema": providers.SCHEMA, "generated_at": time.time(), "chain": "base", "deposit_usd": 50.0,
        "min_net_apr": 5.0, "params": {"elapsed_s": 12.0}, "providers": providers.summarize(rows, sel),
        "pools": [r.to_json() for r in rows],
        "excluded": [{"project": "morpho-blue", "reason": "lending, not an LP", "count": 4}],
        "unscored": [{"reason": "beefy: no price history for the pair", "count": 2}],
        "errors": [{"pool": "uniswap-v3 X", "error": "factory has no such pool"}],
        "registry": [{"id": "uniswap-v3", "name": "Uniswap v3", "factory": "0xF", "position_manager": "0xP",
                      "state_view": None, "sources": ["https://docs.uniswap.org", "on-chain check"]}],
    }  # fmt: skip


def test_report_has_the_three_sections_labels_quoted_figures_and_states_the_bar():
    text = render_report(sample_doc())
    assert text.index("## 1. Provider summary") < text.index("## 2. Top") < text.index("## 3. How to read this")
    assert "(quoted)" in text and "quoted" in text and "measured" in text
    assert "5% APR" in text and "edge ratio" in text and "below 1" in text
    assert "Incentive APR (separate)" in text and "never added to income" in text
    assert "morpho-blue" in text and "factory has no such pool" in text and "https://docs.uniswap.org" in text


def test_report_lists_low_confidence_rows_last_and_marks_the_tier_per_row():
    lines = {
        int(ln.split("|")[1]): ln for ln in render_report(sample_doc()).splitlines() if ln[:3] in ("| 1", "| 2", "| 3")
    }
    assert " measured " in lines[1] and "| high |" in lines[1]
    assert " quoted " in lines[2] and "| medium |" in lines[2]
    assert " quoted " in lines[3] and "| low |" in lines[3] and "beefy" in lines[3]


def test_report_survives_missing_values_and_pipes_in_text():
    doc = sample_doc()
    doc["pools"][0]["expected_net_apr"] = None
    doc["pools"][0]["pair"] = "A|B"
    doc["providers"][0]["best_pool"] = None
    text = render_report(doc, top=1)
    assert "n/a" in text and "A/B" in text and "A|B" not in text


# ---------------------------------------------------------------------------- the whole run, Tier 2 only


def test_run_providers_without_a_chain_scores_quoted_rows_and_writes_both_files(tmp_path):
    rows = [
        raw_pool("uniswap-v2", "WETH-USDC", apyBase=12.0, apyReward=2.0),
        raw_pool("balancer-v2", "WETH-USDC", poolMeta="80WETH-20USDC", apyBase=5.0, pool="bal"),
        raw_pool("curve-dex", "USDC-USDT", tokens=(USDC, USDT), apyBase=1.0, pool="crv"),
        raw_pool("beefy", "WETH-USDC", apyBase=None, apy=30.0, volumeUsd1d=None, poolMeta="Uniswap", pool="bf"),
        raw_pool("uniswap-v3", "WETH-USDC", poolMeta="0.05%", apyBase=60.0, pool="v3"),
        raw_pool("morpho-blue", "LEND", exposure="single", pool="m"),
        raw_pool("uniswap-v2", "NOCHART-USDC", tokens=("0x" + "ab" * 20, USDC), pool="nc"),
    ]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "yields.llama.fi":
            return httpx.Response(200, json={"data": rows})
        return coins_transport(missing={"0x" + "ab" * 20}).handle_request(req)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    out_json, out_md = tmp_path / "providers.json", tmp_path / "providers-report.md"
    doc = providers.run_providers(
        None,
        MarketData(client=http),
        50.0,
        cache_dir=tmp_path,
        out_json=out_json,
        out_report=out_md,
        now=1_800_000_000.0,
    )
    assert doc["schema"] == "aero-lp-providers/1" and doc["params"]["tier1_enabled"] is False
    on_disk = json.loads(out_json.read_text())
    assert on_disk["pools"] == doc["pools"] and out_md.read_text().startswith("# Liquidity provider comparison")
    by_proj = {p["project"]: p for p in doc["pools"]}
    assert set(by_proj) == {"uniswap-v2", "balancer-v2", "curve-dex", "beefy", "uniswap-v3"}
    assert all(p["tier"] == "quoted" for p in doc["pools"])
    assert by_proj["beefy"]["amm_type"] == "alm-vault" and by_proj["curve-dex"]["amm_type"] == "stableswap"
    assert by_proj["uniswap-v2"]["incentive_apr"] == 2.0 and by_proj["uniswap-v2"]["income_apr"] == 12.0
    assert {"project": "morpho-blue", "reason": "single-asset exposure", "count": 1} in doc["excluded"]
    assert any("no price history" in u["reason"] for u in doc["unscored"])
    assert doc["pools"][0]["confidence"] != "low" or all(p["confidence"] == "low" for p in doc["pools"])
    json.dumps(doc, allow_nan=False)


def test_run_providers_reuses_the_cached_defillama_file(tmp_path):
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.host)
        if req.url.host == "yields.llama.fi":
            return httpx.Response(200, json={"data": [raw_pool()]})
        return coins_transport().handle_request(req)

    market = MarketData(client=httpx.Client(transport=httpx.MockTransport(handler)))
    providers.run_providers(None, market, 50.0, cache_dir=tmp_path, now=1000.0)
    providers.run_providers(None, market, 50.0, cache_dir=tmp_path, now=1100.0)
    assert calls.count("yields.llama.fi") == 1
    providers.run_providers(None, market, 50.0, cache_dir=tmp_path, now=1200.0, refresh=True)
    assert calls.count("yields.llama.fi") == 2


# ---------------------------------------------------------------------------- the registry's on-chain check


def test_verify_registry_reports_a_factory_mismatch_and_missing_code():
    reg = providers.REGISTRY
    answers: dict[tuple[str, str], Any] = {}
    for v in reg:
        if v.amm_type is AmmType.UNISWAP_V4:
            answers[(v.position_manager, "poolManager")] = v.factory
            answers[(v.state_view, "poolManager")] = v.factory
        elif v.id != "aerodrome-slipstream":
            answers[(v.position_manager, "factory")] = v.factory
    chain = FakeChain(answers)
    chain.w3.eth.get_code = lambda a: b"\x01"  # type: ignore[attr-defined]
    assert providers.verify_registry(chain) == []  # type: ignore[arg-type]
    answers[(providers.VENUES["pancakeswap-v3"].position_manager.lower(), "factory")] = "0x" + "00" * 19 + "01"
    chain = FakeChain({**{(a.lower(), f): v for (a, f), v in answers.items()}})
    chain.w3.eth.get_code = lambda a: (
        b"" if a == Web3.to_checksum_address(providers.VENUES["alien-base-v3"].factory) else b"\x01"
    )  # type: ignore[attr-defined]
    problems = providers.verify_registry(chain)  # type: ignore[arg-type]
    assert any("alien-base-v3 factory" in p and "no contract code" in p for p in problems)
    assert any("pancakeswap-v3: NPM.factory()" in p for p in problems)


# ---------------------------------------------------------------------------- single-sided, incentive-only, dead fields


def single_raw(project, symbol, token, base, reward=None, tvl=5_000_000.0, il="no", expo="single") -> dict[str, Any]:
    return raw_pool(
        project,
        symbol,
        tokens=(token,),
        apyBase=base,
        apyReward=reward,
        tvlUsd=tvl,
        ilRisk=il,
        exposure=expo,
        pool=symbol,
    )


def test_single_sided_picks_the_best_base_apy_per_token_and_keeps_rewards_separate():
    cbeth = "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22"
    raw = [
        single_raw("aave-v3", "USDC", USDC, 4.0),
        single_raw("morpho-blue", "STEAKUSDC", USDC, 6.5, reward=1.5),
        single_raw("moonwell-lending", "USDC", USDC, 0.0),  # zero base APY: dropped
        single_raw("aave-v3", "WETH", WETH, 2.0),
        single_raw("lido", "CBETH", cbeth, 2.9),
        single_raw("aave-v3", "CBBTC", CBBTC, 0.5, tvl=50_000.0),  # below the TVL minimum
        single_raw("morpho-blue", "RISKY", USDC, 20.0, il="yes"),  # impermanent-loss risk: not single-sided "no-IL"
        single_raw("morpho-blue", "MULTI", USDC, 30.0, expo="multi"),
    ]
    s = providers.select_single_sided(raw, 1e6)
    assert [r["project"] for r in s["USDC"]] == ["morpho-blue", "aave-v3"]
    top = s["USDC"][0]
    assert top["apy_base"] == 6.5 and top["apy_reward"] == 1.5 and top["excess_over_holding_apr"] == 6.5
    assert top["kind"] == "lending supply" and "bad debt" in top["risks"]
    assert {r["kind"] for r in s["WETH"]} == {"lending supply", "LST/LRT staking"}  # the LST is listed under WETH
    lst = next(r for r in s["WETH"] if r["kind"] == "LST/LRT staking")
    assert "depeg" in lst["risks"] and lst["apy_base"] == 2.9
    assert s["cbBTC"] == [] and s["AERO"] == []


def test_comparison_sets_best_lp_beside_best_single_sided_per_token():
    lp = mini(8.0, "high", "measured", "uniswap-v3")
    lp.pair = "WETH/USDC"
    lp.clears_bar = True
    one = {"asset": "X", "kind": "lending supply"}
    single = {
        "WETH": [{"project": "aave-v3", "apy_base": 2.0, **one}],
        "USDC": [{"project": "morpho-blue", "apy_base": 6.5, **one}],
    }
    cmp = {c["token"]: c for c in providers.compare_lp_and_single([lp], single, 5.0)}
    assert cmp["WETH"]["best_lp"]["expected_net_apr"] == 8.0 and cmp["WETH"]["best_single"]["clears_bar"] is False
    assert cmp["USDC"]["best_single"]["clears_bar"] is True and cmp["USDC"]["best_lp"]["pair"] == "WETH/USDC"
    assert cmp["cbBTC"]["best_lp"] is None and cmp["AERO"]["best_single"] is None


def test_tier_two_scores_only_pools_with_a_positive_base_apy_and_lists_reward_only_ones(tmp_path):
    rows = [
        raw_pool("uniswap-v2", "WETH-USDC", apyBase=12.0, pool="ok"),
        raw_pool("aerodrome-v1", "WETH-AERO", apyBase=None, apyReward=300.0, apy=300.0, pool="reward"),
        raw_pool("uniswap-v2", "ZERO-USDC", apyBase=0.0, apyReward=None, pool="zero"),
    ]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "yields.llama.fi":
            return httpx.Response(200, json={"data": rows})
        return coins_transport().handle_request(req)

    market = MarketData(client=httpx.Client(transport=httpx.MockTransport(handler)))
    doc = providers.run_providers(None, market, 50.0, cache_dir=tmp_path, now=1.0)
    assert {p["pair"] for p in doc["pools"]} == {"WETH-USDC"}
    assert [i["pair"] for i in doc["incentive_only"]] == ["WETH-AERO"]
    assert doc["incentive_only"][0]["label"] == "incentive-only" and doc["incentive_only"][0]["apy_reward"] == 300.0
    assert "single_sided" in doc and len(doc["comparison"]) == 4


def test_dead_defillama_fields_are_not_parsed_or_shown(tmp_path):
    p = LlamaPool.from_raw(raw_pool(il7d=5.0, apyBase7d=3.0, apyBaseInception=2.0))
    assert not any(hasattr(p, f) for f in ("il7d", "apy_base_7d", "apy_base_inception"))
    text = render_report(sample_doc())
    assert "il7d" not in text and "apyBase7d" not in text


def test_report_has_the_single_sided_section_and_the_aero_price_line():
    doc = sample_doc()
    doc["single_sided"] = {
        "USDC": [{"project": "morpho-blue", "asset": "X", "kind": "lending supply", "apy_base": 6.5, "apy_reward": 1.0,
                  "tvl_usd": 5e6, "clears_bar": True, "risks": "bad debt"}],
        "AERO": [],
    }  # fmt: skip
    doc["comparison"] = providers.compare_lp_and_single([], doc["single_sided"], 5.0)
    doc["incentive_only"] = [{"project": "aerodrome-v1", "pair": "A-B", "tvl_usd": 1e6, "apy_reward": 90.0}]
    text = render_report(doc)
    assert "## 4. Single-sided yield on Base (comparison only)" in text and "## 5. Coverage and caveats" in text
    assert "AERO income is valued at the spot price and does not account for emission dilution." in text
    assert "morpho-blue" in text and "bad debt" in text and "Incentive-only LP pools" in text
    assert "No single-sided pool" in text
