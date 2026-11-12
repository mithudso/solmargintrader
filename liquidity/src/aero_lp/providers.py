"""Liquidity-provider comparison: which AMMs on a chain pay a small passive LP, and how sure are we?

The Aero scout judges Slipstream pools only. This module widens the same judgement to every provider
DefiLlama lists on the chain, in two tiers:

  Tier 1, *measured* (on chain). Uniswap v3, PancakeSwap v3, SushiSwap v3, Alien Base v3, Aero Slipstream, any
      other pool that answers the Uniswap-v3 interface, and Uniswap v4 (through StateView). Income is the 24h
      change in feeGrowthGlobal0/1X128 per unit of active liquidity. The pool then goes through the same
      `metrics.score_pool` as an Aero pool (LVR, width optimizer, price-path replay, break-even deposit).
  Tier 2, *quoted*. Constant-product (v2, Aerodrome v1), stableswap (Curve, Fluid), weighted (Balancer) and ALM
      vaults (Beefy, Stake DAO). Income is DefiLlama's `apyBase`. That is a quote, not a measurement. Quoted
      APYs overstated realized income about 5x on Aero, so every Tier 2 row is labelled and capped at medium
      confidence. LVR comes from the closed forms below, with sigma from DefiLlama hourly coin prices.

Incentive APR (DefiLlama `apyReward`, for example Merkl) is a separate column. It is never added to income.
The module is read-only: it signs nothing and sends nothing.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx
from web3 import Web3

from . import abi, addresses
from .chain import ZERO, AeroChain, Call, PoolState, Token
from .diagnostics import safe_error
from .market import MarketData, vol_from_closes
from .metrics import KNOWN_TOKENS, NO_DATA, PoolMetrics, ScoreDetail, economics_from, evaluate_pool_detail, score_pool
from .state import atomic_write_json, home
from .strategy import StrategyConfig, half_width_log, lvr_fraction_per_day

SCHEMA = "aero-lp-providers/1"
LLAMA_POOLS_URL = "https://yields.llama.fi/pools"
LLAMA_COINS = "https://coins.llama.fi"
GT = "https://api.geckoterminal.com/api/v2"
LLAMA_TTL_S = 6 * 3600
NATIVE = {ZERO, "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}
CHAIN_LABELS = {"base": "Base"}  # DefiLlama chain names. Tier 1 reads only Base.
BLOCKS_PER_DAY = 43_200  # Base: 2 s blocks
CHART_MAX_POINTS = 500  # DefiLlama's chart endpoint rejects a request for more data points than this
CONF_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------- AMM types and the venue registry


class AmmType(StrEnum):
    CONCENTRATED = "concentrated"  # Uniswap-v3-compatible, tick based
    UNISWAP_V4 = "uniswap-v4"
    CONSTANT_PRODUCT = "constant-product"
    STABLESWAP = "stableswap"
    WEIGHTED = "weighted"
    ALM_VAULT = "alm-vault"
    LENDING = "lending"  # not an LP: excluded
    OTHER = "other"  # no model for it: excluded


_C, _V4, _CP, _SS, _W, _ALM, _L = (
    AmmType.CONCENTRATED,
    AmmType.UNISWAP_V4,
    AmmType.CONSTANT_PRODUCT,
    AmmType.STABLESWAP,
    AmmType.WEIGHTED,
    AmmType.ALM_VAULT,
    AmmType.LENDING,
)
PROJECT_TYPES: dict[str, AmmType] = {
    # tick-based concentrated liquidity, Uniswap v3 compatible
    "uniswap-v3": _C,
    "pancakeswap-amm-v3": _C,
    "sushiswap-v3": _C,
    "alien-base-v3": _C,
    "aerodrome-slipstream": _C,
    "velodrome-v3": _C,
    "dackieswap-v3": _C,
    "baseswap-v3": _C,
    "swapbased-v3": _C,
    "squadswap-v3": _C,
    "camelot-v3": _C,
    "kyberswap-elastic": _C,
    "nest-cl": _C,
    # Uniswap v4 and v4 hooks
    "uniswap-v4": _V4,
    "kyberswap-fairflow": _V4,
    "pancakeswap-infinity": _V4,
    # constant product (Aerodrome v1 is split into volatile and stable pairs by `classify`)
    "uniswap-v2": _CP,
    "sushiswap": _CP,
    "pancakeswap-amm": _CP,
    "aerodrome-v1": _CP,
    "velodrome-v2": _CP,
    "baseswap": _CP,
    "dackieswap-v2": _CP,
    "swapbased": _CP,
    "alien-base-v2": _CP,
    "camelot-v2": _CP,
    # stableswap family
    "curve-dex": _SS,
    "fluid-dex": _SS,
    # weighted
    "balancer-v2": _W,
    "balancer-v3": _W,
    # ALM / auto-compounding vaults over an AMM position
    "beefy": _ALM,
    "stake-dao-yield": _ALM,
    "gamma": _ALM,
    "steer-protocol": _ALM,
    "arrakis-finance": _ALM,
    "ichi": _ALM,
    # not an LP
    "morpho-blue": _L,
    "morpho-v1": _L,
    "aave-v3": _L,
    "aave-v4": _L,
    "compound-v3": _L,
    "fluid-lending": _L,
    "moonwell-lending": _L,
    "euler-v2": _L,
    "exactly": _L,
    "seamless-protocol": _L,
    "40-acres": _L,
    "d2-finance": _L,
    "clipper": AmmType.OTHER,
}
# Types whose DefiLlama row carries a trading volume. A row below the volume minimum is dropped; vaults have none.
NEEDS_VOLUME = {_C, _V4, _CP, _SS, _W}


@dataclass(frozen=True)
class Venue:
    """A DEX we can read on chain. Every address here has two sources: the DEX's own docs or deployment repo,
    and an on-chain check (`verify_registry`): the contract has code, the position manager's factory() is the
    factory, and for v4 the StateView and PositionManager name the same PoolManager."""

    id: str
    name: str
    llama_project: str
    amm_type: AmmType
    factory: str | None  # v3 factory, or the v4 PoolManager
    position_manager: str | None
    fee_tiers: tuple[int, ...] = ()  # fee pips tried when DefiLlama gives no fee
    gt_dex: str | None = None
    state_view: str | None = None  # v4 only
    sources: tuple[str, ...] = ()


UNISWAP_V4_POOL_MANAGER = addresses.UNISWAP_V4_POOL_MANAGER
UNISWAP_V4_STATE_VIEW = addresses.UNISWAP_V4_STATE_VIEW
UNISWAP_V4_POSITION_MANAGER = addresses.UNISWAP_V4_POSITION_MANAGER

REGISTRY: tuple[Venue, ...] = (
    Venue(
        "uniswap-v3",
        "Uniswap v3",
        "uniswap-v3",
        _C,
        addresses.UNISWAP_V3_FACTORY,
        addresses.UNISWAP_V3_NPM,
        (100, 500, 3000, 10000),
        "uniswap-v3-base",
        sources=(
            "https://docs.uniswap.org/contracts/v3/reference/deployments/base-deployments",
            "on-chain: NPM.factory() == factory; pool.factory() == factory",
        ),
    ),
    Venue(
        "pancakeswap-v3",
        "PancakeSwap v3",
        "pancakeswap-amm-v3",
        _C,
        addresses.PANCAKE_V3_FACTORY,
        addresses.PANCAKE_V3_NPM,
        (100, 500, 2500, 10000),
        "pancakeswap-v3-base",
        sources=(
            "https://developer.pancakeswap.finance/contracts/v3/addresses",
            "on-chain: NPM.factory() == factory; pool.factory() == factory",
        ),
    ),
    Venue(
        "sushiswap-v3",
        "SushiSwap v3",
        "sushiswap-v3",
        _C,
        addresses.SUSHI_V3_FACTORY,
        addresses.SUSHI_V3_NPM,
        (100, 500, 3000, 10000),
        "sushiswap-v3-base",
        sources=(
            "https://github.com/sushiswap/v3-periphery/blob/master/deployments/base/NonfungiblePositionManager.json",
            "on-chain: NPM.factory() == factory; pool.factory() == factory",
        ),
    ),
    Venue(
        "alien-base-v3",
        "Alien Base v3",
        "alien-base-v3",
        _C,
        addresses.ALIEN_V3_FACTORY,
        addresses.ALIEN_V3_NPM,
        (100, 200, 300, 500, 3000, 10000),
        "alien-base-v3",
        sources=(
            "https://docs.alienbase.xyz/contracts",
            "on-chain: NPM.factory() == factory; pool.factory() == factory",
        ),
    ),
    Venue(
        "aerodrome-slipstream",
        "Aero Slipstream",
        "aerodrome-slipstream",
        _C,
        addresses.CL_FACTORY,
        addresses.NONFUNGIBLE_POSITION_MANAGER,
        (),
        "aero-slipstream-base",
        sources=("https://aero.xyz/docs/security", "https://github.com/dromos-labs/metadex-slipstream-public"),
    ),
    Venue(
        "uniswap-v4",
        "Uniswap v4",
        "uniswap-v4",
        _V4,
        UNISWAP_V4_POOL_MANAGER,
        UNISWAP_V4_POSITION_MANAGER,
        (),
        "uniswap-v4-base",
        state_view=UNISWAP_V4_STATE_VIEW,
        sources=(
            "https://docs.uniswap.org/contracts/v4/deployments",
            "on-chain: StateView.poolManager() == PositionManager.poolManager() == PoolManager",
        ),
    ),
)
VENUES = {v.id: v for v in REGISTRY}
BY_PROJECT = {v.llama_project: v for v in REGISTRY}
# GeckoTerminal dex ids that look like Uniswap-v3 forks but are not in the registry. Their pools are probed with the
# v3 interface; a pool that answers is scored as Tier 1 with an "unregistered factory" flag and capped at medium.
PROBE_DEXES = (
    "baseswap-v3",
    "swapbased-v3",
    "dackieswap-v3-base",
    "squadswap-v3-base",
    "synthswap-v3",
    "9mm-v3-base",
    "omni-exchange-v3-base",
    "throne-v3-base",
    "kim-v4-base",
    "solidly-v3-base",
)


def classify(project: str, pool_meta: str | None, tokens: list[str] | None = None) -> AmmType:
    """AMM type of a DefiLlama row. Aerodrome v1 pairs that are pegged are stableswap, the rest constant product."""
    t = PROJECT_TYPES.get(project, AmmType.OTHER)
    if project == "aerodrome-v1" and tokens and len(tokens) == 2 and _pegged_pair(tokens):
        return AmmType.STABLESWAP
    if project == "stake-dao-yield" and (pool_meta or "").lower() == "curve":
        return AmmType.ALM_VAULT
    return t


def _pegged_pair(tokens: list[str]) -> bool:
    from .scout import CORRELATED_PAIRS

    sym = {KNOWN_TOKENS.get(norm_token(t)) for t in tokens}
    if None in sym:
        return False
    return any(sym == {a, b} for a, b in CORRELATED_PAIRS)


def norm_token(addr: str) -> str:
    a = addr.lower()
    return addresses.WETH.lower() if a in NATIVE else a


def verify_registry(chain: AeroChain) -> list[str]:
    """On-chain half of the two-source rule: returns problems, empty when every registry address checks out."""
    problems: list[str] = []
    w3 = chain.w3
    for v in REGISTRY:
        for label, addr in (
            ("factory", v.factory),
            ("position_manager", v.position_manager),
            ("state_view", v.state_view),
        ):
            if addr and len(w3.eth.get_code(Web3.to_checksum_address(addr))) == 0:
                problems.append(f"{v.id} {label} {addr}: no contract code")
        if v.amm_type is _V4:
            pm = w3.eth.contract(address=Web3.to_checksum_address(v.position_manager), abi=abi.V4_POSITION_MANAGER)
            sv = w3.eth.contract(address=Web3.to_checksum_address(v.state_view), abi=abi.V4_STATE_VIEW)
            a, b = chain.multicall([Call(pm, "poolManager"), Call(sv, "poolManager")])
            if a.lower() != v.factory.lower() or b.lower() != v.factory.lower():
                problems.append(f"{v.id}: PositionManager/StateView poolManager() = {a}/{b}, expected {v.factory}")
        elif v.id != "aerodrome-slipstream":
            npm = w3.eth.contract(address=Web3.to_checksum_address(v.position_manager), abi=abi.NPM)
            got = chain.multicall([Call(npm, "factory")])[0]
            if got.lower() != v.factory.lower():
                problems.append(f"{v.id}: NPM.factory() = {got}, expected {v.factory}")
    return problems


# ---------------------------------------------------------------------------- DefiLlama pools


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


@dataclass(frozen=True)
class LlamaPool:
    id: str
    project: str
    symbol: str
    chain: str
    tvl_usd: float
    apy_base: float | None
    apy_reward: float | None
    apy_total: float | None
    volume_1d: float | None
    volume_7d: float | None
    pool_meta: str | None
    tokens: tuple[str, ...]  # lower case, native normalized to WETH
    stablecoin: bool
    exposure: str
    outlier: bool
    il_risk: str

    @classmethod
    def from_raw(cls, r: dict[str, Any]) -> LlamaPool:
        toks = tuple(norm_token(t) for t in (r.get("underlyingTokens") or []) if isinstance(t, str))
        return cls(
            id=str(r.get("pool", "")),
            project=str(r.get("project", "")),
            symbol=str(r.get("symbol", "")),
            chain=str(r.get("chain", "")),
            tvl_usd=_f(r.get("tvlUsd")) or 0.0,
            apy_base=_f(r.get("apyBase")),
            apy_reward=_f(r.get("apyReward")),
            apy_total=_f(r.get("apy")),
            volume_1d=_f(r.get("volumeUsd1d")),
            volume_7d=_f(r.get("volumeUsd7d")),
            pool_meta=r.get("poolMeta"),
            tokens=toks,
            stablecoin=bool(r.get("stablecoin")),
            exposure=str(r.get("exposure", "")),
            outlier=bool(r.get("outlier")),
            il_risk=str(r.get("ilRisk", "")),
        )

    @property
    def fee_pips(self) -> int | None:
        """Swap fee in pips parsed from poolMeta ("0.3%", "CL100 - 0.015%"). None when absent."""
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", self.pool_meta or "")
        return round(float(m.group(1)) * 10_000) if m else None

    @property
    def tick_spacing(self) -> int | None:
        m = re.search(r"\bCL(\d+)\b", self.pool_meta or "")
        return int(m.group(1)) if m else None

    @property
    def quoted_base_apy(self) -> float | None:
        """DefiLlama's base APY. Vaults publish only a total, so take the total less the reward part."""
        if self.apy_base is not None:
            return self.apy_base
        if self.apy_total is not None:
            return self.apy_total - (self.apy_reward or 0.0)
        return None


@dataclass
class Selection:
    kept: list[tuple[LlamaPool, AmmType]]
    excluded: list[dict[str, Any]]  # {"project", "reason", "count"}
    total: int  # rows on the chain before any filter


def load_llama(
    cache_dir: Path,
    http: httpx.Client,
    chain: str = "base",
    ttl_s: float = LLAMA_TTL_S,
    force: bool = False,
    now: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """DefiLlama yields for one chain, cached on disk. Returns (raw rows, source info)."""
    now = time.time() if now is None else now
    label = CHAIN_LABELS.get(chain, chain.capitalize())
    path = cache_dir / f"llama-pools-{chain}.json"
    if not force:
        try:
            doc = json.loads(path.read_text())
            if isinstance(doc, dict) and now - float(doc["fetched_at"]) < ttl_s:
                return doc["pools"], {
                    "fetched_at": doc["fetched_at"],
                    "from_cache": True,
                    "pools_on_chain": len(doc["pools"]),
                }
        except (OSError, ValueError, KeyError, TypeError):
            pass
    r = http.get(LLAMA_POOLS_URL, timeout=120)
    r.raise_for_status()
    rows = [p for p in r.json().get("data", []) if p.get("chain") == label]
    atomic_write_json(path, {"fetched_at": now, "chain": label, "pools": rows})
    return rows, {"fetched_at": now, "from_cache": False, "pools_on_chain": len(rows)}


def select_pools(raw: list[dict[str, Any]], min_tvl_usd: float, min_volume_usd: float) -> Selection:
    """Multi-asset LP rows above the TVL and volume minimums, each with its AMM type. Lending and unmodelled
    projects are counted under `excluded`, not silently dropped."""
    kept: list[tuple[LlamaPool, AmmType]] = []
    dropped: Counter[tuple[str, str]] = Counter()
    for r in raw:
        p = LlamaPool.from_raw(r)
        if p.exposure != "multi":
            dropped[(p.project, "single-asset exposure")] += 1
            continue
        if p.tvl_usd < min_tvl_usd:
            continue
        amm = classify(p.project, p.pool_meta, list(p.tokens))
        if amm is AmmType.LENDING:
            dropped[(p.project, "lending, not an LP")] += 1
        elif amm is AmmType.OTHER:
            dropped[(p.project, "no model for this project")] += 1
        elif amm in NEEDS_VOLUME and (p.volume_1d is None or p.volume_1d < min_volume_usd):
            dropped[(p.project, f"24h volume below ${min_volume_usd:,.0f}")] += 1
        else:
            kept.append((p, amm))
    excl = [{"project": k[0], "reason": k[1], "count": n} for k, n in sorted(dropped.items())]
    return Selection(kept, excl, len(raw))


# ---------------------------------------------------------------------------- single-sided yield (comparison only)

# Tokens the owner holds, then the main stables. Addresses come from KNOWN_TOKENS (the symbol table in metrics.py).
SINGLE_TOKENS = ("WETH", "USDC", "cbBTC", "AERO", "USDT", "DAI", "EURC")
LST_SYMBOLS = {"WSTETH", "CBETH", "WEETH", "RETH", "STETH", "EZETH", "RSETH", "SUPEROETHB", "OETH"}
LENDING_PROJECTS = {p for p, t in PROJECT_TYPES.items() if t is AmmType.LENDING}
RISK_LENDING = "bad debt, oracle failure, contract risk; high utilisation can delay withdrawals"
RISK_LST = "depeg against ETH, slashing, contract risk; excess is the staking yield over holding ETH"
RISK_OTHER = "contract risk; strategy and counterparty risk of the vault are not in the number"


def select_single_sided(raw: list[dict[str, Any]], min_tvl_usd: float, per_token: int = 5) -> dict[str, Any]:
    """Single-asset pools with no impermanent-loss risk (lending supply, LST staking), best `apyBase` first, per
    token. The excess over just holding the token is the supply APY (lending) or the staking yield (LST).
    `apyReward` is kept in its own field. Comparison only: nothing acts on these rows."""
    by_token: dict[str, list[dict[str, Any]]] = {t: [] for t in SINGLE_TOKENS}
    for r in raw:
        p = LlamaPool.from_raw(r)
        if p.exposure != "single" or p.il_risk != "no" or p.tvl_usd < min_tvl_usd:
            continue
        if not (p.apy_base and p.apy_base > 0) or len(p.tokens) != 1:
            continue
        tok = p.tokens[0]
        sym = KNOWN_TOKENS.get(tok)
        lst = (
            (sym or "").upper() in LST_SYMBOLS
            or p.symbol.upper() in LST_SYMBOLS
            or any(x in p.symbol.upper() for x in LST_SYMBOLS)
        )
        if p.project in LENDING_PROJECTS:
            kind, risk = "lending supply", RISK_LENDING
        elif lst:
            kind, risk = "LST/LRT staking", RISK_LST
        else:
            kind, risk = "vault / other", RISK_OTHER
        # An LST or LRT earns on top of ETH, so it is listed under WETH; a lending pool is listed under its token.
        target = "WETH" if kind == "LST/LRT staking" else sym
        if target not in by_token:
            continue
        by_token[target].append(
            {
                "token": target,
                "asset": p.symbol,
                "project": p.project,
                "kind": kind,
                "apy_base": p.apy_base,
                "apy_reward": p.apy_reward,
                "tvl_usd": p.tvl_usd,
                "excess_over_holding_apr": p.apy_base,
                "clears_bar": None,  # filled by the caller against min_net_apr
                "risks": risk,
            }
        )
    return {t: sorted(v, key=lambda x: -x["apy_base"])[:per_token] for t, v in by_token.items()}


def compare_lp_and_single(
    ranked: list[ProviderRow], single: dict[str, list[dict[str, Any]]], min_net_apr: float
) -> list[dict[str, Any]]:
    """Best LP net APR beside best single-sided APR for each token the owner holds. The LP figure is for a pair that
    contains the token, so it is not a like-for-like holding of that token alone."""
    out = []
    for tok in ("WETH", "USDC", "cbBTC", "AERO"):
        lps = [
            r
            for r in ranked
            if r.expected_net_apr is not None and tok.lower() in {x.lower() for x in re.split(r"[/-]", r.pair)}
        ]
        # ranked puts low confidence last, so the first row is the best one the ranking trusts most.
        best_lp = lps[0] if lps else None
        singles = single.get(tok, [])
        best_single = singles[0] if singles else None
        out.append(
            {
                "token": tok,
                "best_lp": (
                    {
                        "venue": best_lp.venue,
                        "pair": best_lp.pair,
                        "tier": best_lp.tier,
                        "confidence": best_lp.confidence,
                        "expected_net_apr": best_lp.expected_net_apr,
                        "clears_bar": best_lp.clears_bar,
                    }
                    if best_lp
                    else None
                ),
                "best_single": (
                    {
                        "project": best_single["project"],
                        "asset": best_single["asset"],
                        "kind": best_single["kind"],
                        "apy_base": best_single["apy_base"],
                        "clears_bar": best_single["apy_base"] >= min_net_apr,
                    }
                    if best_single
                    else None
                ),
            }
        )
    return out


def incentive_only(raw_kept: list[tuple[LlamaPool, AmmType]]) -> list[dict[str, Any]]:
    """LP rows that quote rewards but no base fee APY. They are not scored: the income is an emission, not a fee."""
    out = []
    for p, amm in raw_kept:
        base = p.quoted_base_apy if amm is AmmType.ALM_VAULT else p.apy_base
        if not (base and base > 0) and p.apy_reward and p.apy_reward > 0:
            out.append(
                {
                    "project": p.project,
                    "pair": p.symbol,
                    "tvl_usd": p.tvl_usd,
                    "apy_reward": p.apy_reward,
                    "label": "incentive-only",
                }
            )
    return sorted(out, key=lambda x: -x["tvl_usd"])


# ---------------------------------------------------------------------------- DefiLlama coin prices


class Coins:
    """DefiLlama coin prices (current and hourly) for Base tokens, cached in memory."""

    def __init__(self, http: httpx.Client, chain: str = "base"):
        self.http = http
        self.chain = chain
        self._now: dict[str, float] = {}
        self._hourly: dict[str, dict[int, float]] = {}
        self._missing_hourly: set[str] = set()

    def _coin_ids(self, toks: list[str]) -> str:
        return ",".join(f"{self.chain}:{t}" for t in toks)

    def current(self, tokens: list[str]) -> dict[str, float]:
        toks = sorted({norm_token(t) for t in tokens})
        need = [t for t in toks if t not in self._now]
        for i in range(0, len(need), 40):
            batch = need[i : i + 40]
            try:
                r = self.http.get(f"{LLAMA_COINS}/prices/current/{self._coin_ids(batch)}", timeout=30)
                r.raise_for_status()
                for k, v in (r.json().get("coins") or {}).items():
                    price = _f(v.get("price"))
                    if price is not None and price > 0:
                        self._now[k.split(":", 1)[1].lower()] = price
            except (httpx.HTTPError, ValueError):
                continue
        return {t: self._now[t] for t in toks if t in self._now}

    def hourly(self, tokens: list[str], span: int = 168) -> None:
        """Fetch hourly prices for any token not fetched yet. Tokens DefiLlama has no chart for are remembered.
        The chart endpoint caps a request at 500 data points, so it takes 500 // span tokens at a time (2 for a
        week of hours); the requests run on a few threads."""
        need = sorted({norm_token(t) for t in tokens} - set(self._hourly) - self._missing_hourly)
        per = max(1, CHART_MAX_POINTS // span)
        batches = [need[i : i + per] for i in range(0, len(need), per)]

        def fetch(batch: list[str]) -> dict[str, Any] | None:
            try:
                r = self.http.get(
                    f"{LLAMA_COINS}/chart/{self._coin_ids(batch)}", params={"span": span, "period": "1h"}, timeout=40
                )
                r.raise_for_status()
                return r.json().get("coins") or {}
            except (httpx.HTTPError, ValueError):
                return None

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(fetch, batches))
        for batch, coins in zip(batches, results, strict=True):
            if coins is None:
                continue  # A failed request is not evidence that a token has no chart.
            for k, v in coins.items():
                series = {}
                for pt in v.get("prices") or []:
                    price = _f(pt.get("price"))
                    if price and price > 0 and pt.get("timestamp"):
                        series[int(pt["timestamp"]) // 3600] = price
                if series:
                    self._hourly[k.split(":", 1)[1].lower()] = series
            self._missing_hourly.update(t for t in batch if t not in self._hourly)

    def ratio_closes(self, a: str, b: str) -> list[float]:
        """Hourly price of token a in units of token b, oldest first. Empty when either chart is missing."""
        self.hourly([a, b])
        sa, sb = self._hourly.get(norm_token(a)), self._hourly.get(norm_token(b))
        if not sa or not sb:
            return []
        hours = sorted(set(sa) & set(sb))
        longest: list[int] = []
        current: list[int] = []
        for hour in hours:
            current = current + [hour] if current and hour == current[-1] + 1 else [hour]
            if len(current) >= len(longest):
                longest = current
        return [sa[h] / sb[h] for h in longest]


# ---------------------------------------------------------------------------- Tier 2: closed-form LVR


def lvr_apr_constant_product(sigma_daily: float) -> float:
    """LVR of a 50/50 constant-product pool, % per year of pool value: sigma^2 / 8 per day."""
    return sigma_daily**2 / 8 * 36500


def lvr_apr_weighted(sigma_daily: float, weight: float) -> float:
    """LVR of a two-asset weighted pool (Balancer), % per year: sigma^2 * w * (1 - w) / 2 per day.
    w = 0.5 gives sigma^2 / 8, the constant-product value."""
    return sigma_daily**2 * weight * (1 - weight) / 2 * 36500


def lvr_apr_stableswap(sigma_daily: float) -> float:
    """Approximation for a stableswap pool: the constant-product value. It is an upper bound for a pair that
    stays near its peg. It does not hold for a pair that is not pegged (the curve there is not constant product)."""
    return lvr_apr_constant_product(sigma_daily)


def lvr_apr_alm(sigma_daily: float, cfg: StrategyConfig) -> tuple[float, float]:
    """LVR of a vault that holds a concentrated range. The vault's range is not published, so assume the width
    the strategy's volatility rule would pick (k * sigma * sqrt(horizon)). Returns (% per year, half-width %)."""
    w = half_width_log(cfg, sigma_daily)
    return lvr_fraction_per_day(w, sigma_daily) * 36500, (math.exp(w) - 1) * 100


def weights_from_meta(pool_meta: str | None) -> list[float] | None:
    """Balancer weights from poolMeta, for example "50OLAS-50USDC" -> [0.5, 0.5]."""
    nums = re.findall(r"(\d+(?:\.\d+)?)(?=[A-Za-z])", pool_meta or "")
    if len(nums) < 2:
        return None
    vals = [float(n) for n in nums]
    total = sum(vals)
    return [v / total for v in vals] if total > 0 else None


# ---------------------------------------------------------------------------- result rows


@dataclass
class ProviderRow:
    venue: str  # registry id, or the DefiLlama project / GeckoTerminal dex id when not in the registry
    project: str
    amm_type: str
    tier: str  # "measured" (on chain) or "quoted" (DefiLlama)
    pool: str  # pool address, v4 poolId, or DefiLlama pool id
    pair: str
    fee_pct: float | None
    tvl_usd: float
    volume_24h_usd: float | None
    income_source: str
    income_apr: float | None  # % per year at the modelled width, before LVR. Excludes incentives.
    incentive_apr: float | None  # DefiLlama apyReward. Separate; never part of income_apr.
    lvr_apr: float | None
    rebalance_cost_apr: float | None
    edge_ratio: float | None  # income / LVR
    expected_net_apr: float | None  # income - LVR - rebalance cost. Excludes incentives.
    net_apr_with_incentives: float | None
    replay_net_apr: float | None  # Tier 1 only: price-path replay at the deployed width
    best_half_width_pct: float | None
    break_even_deposit_usd: float | None
    sigma_daily_pct: float | None
    sigma_source: str
    confidence: str
    clears_bar: bool
    quoted_apy_base: float | None = None  # DefiLlama apyBase, labelled quoted wherever shown
    flags: list[str] = field(default_factory=list)
    venue_info: dict[str, Any] = field(default_factory=dict)  # what a later change needs to act on the row
    actionable: bool = False  # Tier 1, on a registered venue, nothing blocking

    def to_json(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        for k, v in list(d.items()):
            if isinstance(v, float):
                d[k] = round(v, 6) if math.isfinite(v) else None
        return d


def cap_confidence(conf: str, cap: str) -> str:
    return conf if CONF_ORDER[conf] >= CONF_ORDER[cap] else cap


def rank_rows(rows: list[ProviderRow]) -> list[ProviderRow]:
    """Low-confidence rows last, then by expected net APR. A row with no usable net APR goes below the rest of its
    confidence band. Quoted figures never outrank a measured one of equal confidence: they are capped at medium
    and the tier breaks ties."""

    def key(r: ProviderRow) -> tuple[int, int, float, int]:
        net = r.expected_net_apr
        usable = net is not None and net > NO_DATA / 2
        return (
            r.confidence == "low",
            0 if usable else 1,
            -(net if usable and net is not None else 0.0),
            r.tier != "measured",
        )

    return sorted(rows, key=key)


def _bar(net: float | None, replay: float | None, edge: float | None, conf: str, tier: str, min_net_apr: float) -> bool:
    """Would the Aero allocator deploy here? Measured, model and replay at or above the bar, edge >= 1.2,
    confidence at least medium. Quoted rows never clear it."""
    return (
        tier == "measured"
        and net is not None
        and replay is not None
        and edge is not None
        and net >= min_net_apr
        and replay >= min_net_apr
        and edge >= 1.2
        and CONF_ORDER[conf] <= CONF_ORDER["medium"]
    )


def row_from_metrics(
    m: PoolMetrics,
    d: ScoreDetail,
    venue: str,
    project: str,
    amm_type: AmmType,
    llama: LlamaPool | None,
    min_net_apr: float,
    venue_info: dict[str, Any],
    registered: bool = True,
    extra_flags: list[str] | None = None,
    cap: str | None = None,
) -> ProviderRow:
    flags = list(m.flags) + (extra_flags or [])
    flags.append("break-even deposit: " + m.break_even_basis)
    conf = m.confidence
    if not d.income_measured:
        flags.append("income not measured (24h fee growth unavailable): volume x fee used")
        conf = cap_confidence(conf, "low")
    if not registered:
        flags.append("factory not in the registry: pool recognised by interface only")
        conf = cap_confidence(conf, "medium")
    if cap:
        conf = cap_confidence(conf, cap)
    gauge = m.best_mode == "aero"
    venue_info = {
        **venue_info,
        "tokens": [norm_token(m.token0), norm_token(m.token1)],
        "tick_spacing": m.tick_spacing,
    }
    reward = None if gauge else (llama.apy_reward if llama else None)
    net = m.expected_net_apr if m.expected_net_apr > NO_DATA / 2 else None
    replay = m.backtest_deploy_apr if m.backtest_days > 0 and m.backtest_deploy_apr > NO_DATA / 2 else None
    edge = m.edge_ratio if m.edge_ratio < 1e9 else None
    return ProviderRow(
        venue=venue,
        project=project,
        amm_type=amm_type.value,
        tier="measured",
        pool=m.pool,
        pair=m.pair,
        fee_pct=m.fee_pct,
        tvl_usd=m.tvl_usd,
        volume_24h_usd=m.volume_24h_usd,
        income_source=(
            "24h feeGrowthGlobal change + AERO gauge emissions (measured)"
            if gauge
            else "24h feeGrowthGlobal change per unit of active liquidity (measured)"
            if d.income_measured
            else "volume x current fee (estimate)"
        ),
        income_apr=d.income_apr,
        incentive_apr=reward,
        lvr_apr=d.lvr_apr,
        rebalance_cost_apr=d.rebalance_cost_apr,
        edge_ratio=edge,
        expected_net_apr=net,
        net_apr_with_incentives=(net + (reward or 0.0)) if net is not None else None,
        replay_net_apr=replay,
        best_half_width_pct=m.best_half_width_pct,
        break_even_deposit_usd=m.break_even_deposit_usd if m.break_even_deposit_usd < 1e11 else None,
        sigma_daily_pct=m.sigma_daily_pct,
        sigma_source=m.sigma_source,
        confidence=conf,
        clears_bar=_bar(net, replay, edge, conf, "measured", min_net_apr),
        quoted_apy_base=llama.quoted_base_apy if llama else None,
        flags=flags,
        venue_info=venue_info,
        actionable=registered and CONF_ORDER[conf] <= CONF_ORDER["medium"],
    )


def _venue_info(v: Venue | None, pool: str, chain_id: int = addresses.BASE_CHAIN_ID, **extra: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"chain_id": chain_id, "pool": pool}
    if v:
        info.update({"factory": v.factory, "position_manager": v.position_manager, "kind": v.amm_type.value})
        if v.state_view:
            info["state_view"] = v.state_view
    info.update(extra)
    return info


def evaluate_quoted(
    p: LlamaPool,
    amm: AmmType,
    sigma: float | None,
    sigma_source: str,
    hist_days: float,
    min_net_apr: float,
    cfg: StrategyConfig | None = None,
    min_tvl_for_medium: float = 250_000.0,
) -> ProviderRow | None:
    """Tier 2 row: income is DefiLlama's quoted base APY, LVR is a closed form. None without a volatility."""
    cfg = cfg or StrategyConfig()
    if sigma is None:
        return None
    flags = ["income is a DefiLlama quote, not measured"]
    income = p.quoted_base_apy
    no_base = p.apy_base is None and amm is not AmmType.ALM_VAULT
    if no_base:
        flags.append("no base fee APY quoted: income taken as 0 (rewards are in the incentive column)")
        income = 0.0
    if income is None:
        return None
    half_w: float | None = None
    if amm is AmmType.CONSTANT_PRODUCT:
        lvr = lvr_apr_constant_product(sigma)
    elif amm is AmmType.STABLESWAP:
        lvr = lvr_apr_stableswap(sigma)
        flags.append("stableswap LVR is approximate (constant-product upper bound), valid only while pegged")
        if sigma > 0.01:
            flags.append("pair is not pegged: stableswap LVR formula does not apply")
    elif amm is AmmType.WEIGHTED:
        ws = weights_from_meta(p.pool_meta)
        w = ws[0] if ws and len(ws) == 2 else 0.5
        if not ws or len(ws) != 2:
            flags.append("pool weights unknown: assumed 50/50")
        lvr = lvr_apr_weighted(sigma, w)
    elif amm is AmmType.ALM_VAULT:
        if (p.pool_meta or "").lower() == "curve":
            lvr = lvr_apr_stableswap(sigma)
            flags.append("Curve vault: LVR approximated as constant product")
        else:
            lvr, half_w = lvr_apr_alm(sigma, cfg)
            flags.append(f"vault range unknown: LVR assumes a +/-{half_w:.1f}% range")
        flags.append("vault APY is already net of its own rebalancing cost; LVR is still borne by the vault")
    else:  # concentrated or v4 without an on-chain reading
        lvr = lvr_apr_constant_product(sigma)
        flags.append("quoted APY is per pool TVL and LVR is the full-range lower bound: both are optimistic")
    net = income - lvr
    reward = p.apy_reward
    edge = income / lvr if lvr > 0 else None
    conf = "medium" if amm in (AmmType.CONSTANT_PRODUCT, AmmType.WEIGHTED) else "low"
    if p.tvl_usd < min_tvl_for_medium or hist_days < 5 or p.outlier or no_base:
        conf = "low"
    if p.outlier:
        flags.append("DefiLlama marks the APY an outlier")
    if any(t not in KNOWN_TOKENS for t in p.tokens):
        flags.append("unlisted token")
        conf = "low"
    return ProviderRow(
        venue=BY_PROJECT[p.project].id if p.project in BY_PROJECT else p.project,
        project=p.project,
        amm_type=amm.value,
        tier="quoted",
        pool=p.id,
        pair=p.symbol,
        fee_pct=p.fee_pips / 10_000 if p.fee_pips is not None else None,
        tvl_usd=p.tvl_usd,
        volume_24h_usd=p.volume_1d,
        income_source="DefiLlama apyBase (quoted)" if p.apy_base is not None else "DefiLlama vault APY (quoted)",
        income_apr=income,
        incentive_apr=reward,
        lvr_apr=lvr,
        rebalance_cost_apr=0.0,
        edge_ratio=edge,
        expected_net_apr=net,
        net_apr_with_incentives=net + (reward or 0.0),
        replay_net_apr=None,
        best_half_width_pct=half_w,
        break_even_deposit_usd=None,
        sigma_daily_pct=sigma * 100,
        sigma_source=sigma_source,
        confidence=conf,
        clears_bar=False,
        quoted_apy_base=p.quoted_base_apy,
        flags=flags,
        venue_info={
            "chain_id": addresses.BASE_CHAIN_ID if p.chain.lower() == "base" else None,
            "chain": p.chain,
            "kind": amm.value,
            "llama_pool": p.id,
        },
        actionable=False,
    )


# ---------------------------------------------------------------------------- Tier 1: generic v3 and v4 readers


@dataclass
class V3Read:
    state: PoolState
    factory: str | None
    has_gauge: bool


def read_v3_pool(chain: AeroChain, address: str, block: int | None = None) -> V3Read:
    """Read any Uniswap-v3-compatible pool at one block. Aero-only members (unstakedFee, stakedLiquidity, gauge) and
    factory() are read with allow_failure: a Uniswap pool lacks the Aero ones. A pool is treated as plain v3 (no
    gauge income) whatever it answers. Raises if slot0, the tokens, tick spacing, fee, liquidity or fee growth fail."""
    bn = block if block is not None else chain.head()[0]
    addr = Web3.to_checksum_address(address)

    def calls(c: Any) -> list[Call]:
        return [
            Call(c, "slot0"),
            Call(c, "token0"),
            Call(c, "token1"),
            Call(c, "tickSpacing"),
            Call(c, "fee"),
            Call(c, "liquidity"),
            Call(c, "feeGrowthGlobal0X128"),
            Call(c, "feeGrowthGlobal1X128"),
            Call(c, "factory", allow_failure=True),
            Call(c, "unstakedFee", allow_failure=True),
            Call(c, "stakedLiquidity", allow_failure=True),
            Call(c, "gauge", allow_failure=True),
        ]

    try:
        res = chain.multicall(calls(chain.w3.eth.contract(address=addr, abi=abi.V3_POOL)), block=bn)
    except Exception:  # noqa: BLE001 - Slipstream's slot0 has 6 outputs: the 7-output decode fails, so retry with theirs
        res = chain.multicall(calls(chain.w3.eth.contract(address=addr, abi=abi.CL_POOL)), block=bn)
    s0, t0, t1, ts, fee, liq, fg0, fg1, factory, _ufee, _sliq, gauge = res
    ts_block = int(chain.w3.eth.get_block(bn)["timestamp"])
    state = PoolState(
        address=addr,
        token0=chain.token(t0),
        token1=chain.token(t1),
        tick_spacing=int(ts),
        fee_pips=int(fee),
        unstaked_fee_pips=0,
        sqrt_price_x96=int(s0[0]),
        tick=int(s0[1]),
        liquidity=int(liq),
        staked_liquidity=0,
        gauge=ZERO,
        gauge_alive=False,
        fee_growth_global0=int(fg0),
        fee_growth_global1=int(fg1),
        reward_growth_global=0,
        block=bn,
        timestamp=ts_block,
    )
    return V3Read(state, factory, bool(gauge and gauge.lower() != ZERO))


def find_v3_pools(
    chain: AeroChain, venue: Venue, wanted: list[tuple[str, str, int | None]]
) -> dict[tuple[str, str, int | None], str | None]:
    """Pool addresses from the venue's factory.getPool(tokenA, tokenB, fee) for (tokenA, tokenB, fee pips) triples.
    A missing fee tries every tier in the venue's list and keeps the first pool that exists. The answer is read
    from the chain: nothing is guessed."""
    assert venue.factory
    fac = chain.w3.eth.contract(address=Web3.to_checksum_address(venue.factory), abi=abi.V3_FACTORY)
    asks: list[tuple[tuple[str, str, int | None], int]] = []
    for key in wanted:
        a, b, fee = key
        for f in [fee] if fee else list(venue.fee_tiers):
            asks.append((key, f))
    out: dict[tuple[str, str, int | None], str | None] = dict.fromkeys(wanted)
    for i in range(0, len(asks), 150):
        chunk = asks[i : i + 150]
        res = chain.multicall(
            [
                Call(fac, "getPool", (Web3.to_checksum_address(k[0]), Web3.to_checksum_address(k[1]), f), True)
                for k, f in chunk
            ]
        )
        for (key, _), pool in zip(chunk, res, strict=True):
            if pool and pool.lower() != ZERO and out[key] is None:
                out[key] = Web3.to_checksum_address(pool)
    return out


def _growth_delta(
    read: Callable[[int], tuple[int, int]], head: int, blocks_per_day: int = BLOCKS_PER_DAY
) -> tuple[int, int, float]:
    """Same windowing as AeroChain.fee_growth_delta for sources that are not a pool: a day back, then 6 h, then 1 h."""
    mod = 1 << 256
    now0, now1 = read(head)
    for back in (blocks_per_day, blocks_per_day // 4, 1800):
        try:
            then0, then1 = read(head - back)
        except Exception:  # noqa: BLE001 - RPC without enough state history, or a pool younger than the window
            continue
        return (now0 - then0) % mod, (now1 - then1) % mod, back / blocks_per_day
    return 0, 0, 0.0


@dataclass
class V4Read:
    state: PoolState
    pool_id: str
    hooks: str
    dynamic_fee: bool
    fee_delta: tuple[int, int, float]


def read_v4_pool(chain: AeroChain, pool_id: str) -> V4Read | None:
    """A Uniswap v4 pool through StateView and PositionManager.poolKeys. None when the pool key is not known to the
    PositionManager (the tick spacing is then unknown, so the pool is not scored on chain)."""
    v = VENUES["uniswap-v4"]
    sv = chain.w3.eth.contract(address=Web3.to_checksum_address(v.state_view), abi=abi.V4_STATE_VIEW)
    posm = chain.w3.eth.contract(address=Web3.to_checksum_address(v.position_manager), abi=abi.V4_POSITION_MANAGER)
    pid = bytes.fromhex(pool_id.removeprefix("0x"))
    if len(pid) != 32:
        return None
    key = chain.multicall([Call(posm, "poolKeys", (pid[:25],), True)])[0]
    if not key or key[0] == ZERO and key[1] == ZERO and key[3] == 0:
        return None
    c0, c1, key_fee, spacing, hooks = key
    bn = chain.head()[0]
    s0, liq = chain.multicall([Call(sv, "getSlot0", (pid,)), Call(sv, "getLiquidity", (pid,))], block=bn)
    sqrt_p, tick, _protocol_fee, lp_fee = s0
    if sqrt_p == 0:
        return None

    def growth(block: int) -> tuple[int, int]:
        g = chain.multicall([Call(sv, "getFeeGrowthGlobals", (pid,))], block=block)[0]
        return int(g[0]), int(g[1])

    delta = _growth_delta(growth, bn)

    def tok(c: str) -> Token:
        if c.lower() == ZERO:
            return Token(Web3.to_checksum_address(addresses.WETH), "ETH", 18)
        return chain.token(c)

    g0, g1 = growth(bn)
    state = PoolState(
        address=pool_id,
        token0=tok(c0),
        token1=tok(c1),
        tick_spacing=int(spacing),
        fee_pips=int(lp_fee),
        unstaked_fee_pips=0,
        sqrt_price_x96=int(sqrt_p),
        tick=int(tick),
        liquidity=int(liq),
        staked_liquidity=0,
        gauge=ZERO,
        gauge_alive=False,
        fee_growth_global0=g0,
        fee_growth_global1=g1,
        reward_growth_global=0,
        block=bn,
        timestamp=int(chain.w3.eth.get_block(bn)["timestamp"]),
    )
    return V4Read(state, pool_id, hooks, bool(int(key_fee) & 0x800000), delta)


# ---------------------------------------------------------------------------- GeckoTerminal listings


def gt_dex_pools(market: MarketData, dex: str, page: int = 1) -> list[dict[str, Any]]:
    """Top pools of one GeckoTerminal dex by 24h volume: address (or v4 poolId), name, TVL, volume."""
    data = market._get(f"{GT}/networks/base/dexes/{dex}/pools", {"page": page, "sort": "h24_volume_usd_desc"})
    out = []
    for p in data.get("data", []):
        a = p["attributes"]
        out.append(
            {
                "address": a["address"],
                "name": a.get("name", ""),
                "tvl_usd": float(a.get("reserve_in_usd") or 0),
                "volume_24h_usd": float((a.get("volume_usd") or {}).get("h24") or 0),
            }
        )
    return out


# ---------------------------------------------------------------------------- the run


@dataclass
class Env:
    chain: AeroChain | None
    market: MarketData
    coins: Coins
    deposit_usd: float
    cfg: StrategyConfig
    min_net_apr: float
    gas_price_wei: int = 0

    def prices_for(self, tokens: list[str]) -> dict[str, float]:
        return self.coins.current([*tokens, addresses.WETH])


def pair_sigma(
    env: Env, pool_addr: str, t0: str, t1: str, onchain_ok: bool
) -> tuple[float | None, str, float, list[float]]:
    """Daily vol of the pair's price ratio. GeckoTerminal pool OHLCV first (as the Aero scout does), then DefiLlama
    coin charts, then the pool's own 10-minute TWAP (v3 pools only). Returns (sigma, source, days, hourly closes)."""
    try:
        closes = env.market.hourly_closes(pool_addr, 168)
        s = vol_from_closes(closes)
        if s:
            return s, f"geckoterminal {len(closes)}h hourly", len(closes) / 24, closes
    except Exception:  # noqa: BLE001 - rate limit, unknown pool, young pool
        pass
    closes = env.coins.ratio_closes(t0, t1)
    s = vol_from_closes(closes)
    if s:
        return s, f"defillama coins {len(closes)}h hourly", len(closes) / 24, closes
    if onchain_ok and env.chain is not None:
        from .chain import realized_vol_daily

        ticks = env.chain.twap_tick_series(pool_addr, hours=12, step_s=600)
        s = realized_vol_daily(ticks, step_s=600)
        if s:
            return s, "onchain 10-min TWAP", len(ticks) / 144, []
    return None, "none", 0.0, []


def score_onchain(
    env: Env,
    pool: PoolState,
    fee_delta: tuple[int, int, float],
    tvl_usd: float,
    volume_usd: float,
    onchain_sigma_ok: bool,
) -> tuple[PoolMetrics, ScoreDetail]:
    prices = env.prices_for([pool.token0.address, pool.token1.address])
    info = {"volume_24h_usd": volume_usd, "reserve_usd": tvl_usd}
    econ = economics_from(pool, prices, info, 0.0, fee_delta)
    ctx = {
        "prices": prices,
        "eth_usd": prices.get(addresses.WETH.lower(), 0.0),
        "tvl_usd": tvl_usd,
        "volume_24h_usd": volume_usd,
        "fee_history_days": fee_delta[2],
    }
    sigma, src, hist_days, closes = pair_sigma(
        env, pool.address, pool.token0.address, pool.token1.address, onchain_sigma_ok
    )
    return score_pool(
        pool, econ, ctx, sigma, src, hist_days, closes, env.deposit_usd, env.cfg, env.gas_price_wei or 10**7
    )


def score_v3(
    env: Env, venue_id: str, project: str, address: str, tvl: float, vol: float, llama: LlamaPool | None
) -> ProviderRow:
    """Tier 1 for one Uniswap-v3-compatible pool."""
    assert env.chain is not None
    reg = VENUES.get(venue_id)
    rd = read_v3_pool(env.chain, address)
    if rd.state.liquidity <= 0:
        raise RuntimeError("no active liquidity")
    try:
        delta = env.chain.fee_growth_delta(rd.state.address, rd.state.block)
    except Exception:  # noqa: BLE001
        delta = (0, 0, 0.0)
    m, d = score_onchain(env, rd.state, delta, tvl, vol, True)
    extra: list[str] = []
    registered = reg is not None
    if registered and not rd.factory:
        raise RuntimeError("registered pool factory verification unavailable")
    if registered and reg is not None and rd.factory and rd.factory.lower() != (reg.factory or "").lower():
        raise RuntimeError(f"pool.factory() {rd.factory} is not the registered {venue_id} factory {reg.factory}")
    if rd.has_gauge:
        extra.append("pool has a gauge: scored on fees only (no gauge income)")
    info = _venue_info(reg, rd.state.address, factory_seen=rd.factory)
    return row_from_metrics(
        m, d, venue_id, project, AmmType.CONCENTRATED, llama, env.min_net_apr, info, registered, extra
    )


def score_v4(env: Env, pool_id: str, tvl: float, vol: float, llama: LlamaPool | None) -> ProviderRow:
    assert env.chain is not None
    rd = read_v4_pool(env.chain, pool_id)
    if rd is None:
        raise RuntimeError("pool key not known to the v4 PositionManager (tick spacing unknown)")
    if rd.state.liquidity <= 0:
        raise RuntimeError("no active liquidity")
    m, d = score_onchain(env, rd.state, rd.fee_delta, tvl, vol, False)
    extra = []
    cap = None
    if rd.hooks.lower() != ZERO:
        extra.append(f"pool has a hook ({rd.hooks[:10]}...): it can redirect fees or change the swap path")
        cap = "medium"
    if rd.dynamic_fee:
        extra.append("dynamic fee")
    reg = VENUES["uniswap-v4"]
    info = _venue_info(reg, pool_id, hooks=rd.hooks, tick_spacing=rd.state.tick_spacing)
    return row_from_metrics(
        m, d, "uniswap-v4", "uniswap-v4", AmmType.UNISWAP_V4, llama, env.min_net_apr, info, True, extra, cap
    )


def score_aero(env: Env, address: str) -> ProviderRow:
    assert env.chain is not None
    m, d = evaluate_pool_detail(env.chain, env.market, address, env.deposit_usd, env.cfg)
    reg = VENUES["aerodrome-slipstream"]
    row = row_from_metrics(
        m, d, reg.id, reg.llama_project, AmmType.CONCENTRATED, None, env.min_net_apr, _venue_info(reg, m.pool)
    )
    if d.net_gauge_apr is not None:
        row.flags.append(
            f"net APR with AERO gauge emissions (staked) {d.net_gauge_apr:+.1f}%, fees only {d.net_fees_only_apr:+.1f}%"
        )
    return row


@dataclass
class Job:
    provider: str
    label: str
    run: Callable[[], ProviderRow]
    llama_id: str | None = None


def _median(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def _pick_candidates(pools: list[LlamaPool], n: int) -> list[LlamaPool]:
    """Half by 24h volume, half by turnover (volume / TVL): the busiest pools and the ones that earn most per dollar."""
    if n <= 0:
        return []
    by_vol = sorted(pools, key=lambda p: -(p.volume_1d or 0))
    by_turn = sorted(pools, key=lambda p: -((p.volume_1d or 0) / p.tvl_usd if p.tvl_usd else 0))
    out: list[LlamaPool] = []
    for src, take in ((by_vol, math.ceil(n / 2)), (by_turn, n)):
        for p in src:
            if len(out) >= n or take <= 0:
                break
            if p not in out:
                out.append(p)
                take -= 1
    return out


def run_providers(
    chain: AeroChain | None,
    market: MarketData,
    deposit_usd: float,
    *,
    chain_name: str = "base",
    cache_dir: Path | None = None,
    min_tvl_usd: float = 100_000.0,
    min_volume_usd: float = 10_000.0,
    max_pools: int = 60,
    aero_pools: int = 12,
    probe: bool = True,
    max_seconds: float | None = 1500.0,
    cfg: StrategyConfig | None = None,
    min_net_apr: float = 5.0,
    refresh: bool = False,
    progress: Callable[[str], None] | None = None,
    out_json: Path | None = None,
    out_report: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Discover, score and rank the providers; write providers.json and providers-report.md when paths are given."""
    say = progress or (lambda _m: None)
    started = time.monotonic()
    cfg = cfg or StrategyConfig()
    cache_dir = cache_dir or home()
    raw, src = load_llama(cache_dir, market.http, chain_name, force=refresh, now=now)
    sel = select_pools(raw, min_tvl_usd, min_volume_usd)
    say(f"DefiLlama: {len(raw)} pools on {chain_name}, {len(sel.kept)} multi-asset LPs after filters")
    onchain = chain is not None and chain_name == "base"
    coins = Coins(market.http, chain_name)
    env = Env(chain, market, coins, deposit_usd, cfg, min_net_apr)
    errors: list[dict[str, str]] = []
    rows: list[ProviderRow] = []
    measured_llama: set[str] = set()
    registry_problems: list[str] = []

    jobs: dict[str, list[Job]] = {}
    if onchain and chain is not None:
        registry_problems = verify_registry(chain)
        for pr in registry_problems:
            errors.append({"pool": "registry", "error": pr})
        env.gas_price_wei = chain.gas_price_wei()
        bad = {p.split(" ")[0].rstrip(":") for p in registry_problems}
        by_proj: dict[str, list[LlamaPool]] = {}
        for p, amm in sel.kept:
            if amm is AmmType.CONCENTRATED:
                by_proj.setdefault(p.project, []).append(p)
        # Uniswap-v3-compatible venues with a registry factory: find each candidate pool with factory.getPool.
        n_v3 = [v for v in REGISTRY if v.amm_type is AmmType.CONCENTRATED and v.id != "aerodrome-slipstream"]
        per_venue = max(1, max_pools // (len(n_v3) + 1))
        for v in n_v3:
            if v.id in bad:
                continue
            cands = _pick_candidates([p for p in by_proj.get(v.llama_project, []) if len(p.tokens) == 2], per_venue)
            wanted = [(p.tokens[0], p.tokens[1], p.fee_pips) for p in cands]
            try:
                found = find_v3_pools(chain, v, wanted) if wanted else {}
            except Exception as e:  # noqa: BLE001
                errors.append({"pool": v.id, "error": "getPool lookup failed: " + safe_error(e)})
                continue
            for p, key in zip(cands, wanted, strict=True):
                addr = found.get(key)
                if not addr:
                    errors.append({"pool": f"{v.id} {p.symbol} {p.pool_meta}", "error": "factory has no such pool"})
                    continue
                jobs.setdefault(v.id, []).append(
                    Job(
                        v.id,
                        f"{v.id} {p.symbol} {p.pool_meta or ''}".strip(),
                        lambda v=v, p=p, addr=addr: score_v3(
                            env, v.id, v.llama_project, addr, p.tvl_usd, p.volume_1d or 0.0, p
                        ),
                        p.id,
                    )
                )
        # Uniswap v4: pool ids from GeckoTerminal's listing, state from StateView.
        if "uniswap-v4" not in bad:
            try:
                listing = [x for x in gt_dex_pools(market, "uniswap-v4-base") if x["tvl_usd"] >= min_tvl_usd]
                listing = [x for x in listing if x["volume_24h_usd"] >= min_volume_usd][:per_venue]
            except Exception as e:  # noqa: BLE001
                listing = []
                errors.append({"pool": "uniswap-v4", "error": f"GeckoTerminal listing failed: {type(e).__name__}"})
            for x in listing:
                jobs.setdefault("uniswap-v4", []).append(
                    Job(
                        "uniswap-v4",
                        f"uniswap-v4 {x['name']}",
                        lambda x=x: score_v4(env, x["address"], x["tvl_usd"], x["volume_24h_usd"], None),
                    )
                )
        # Aero Slipstream: the scout's own candidate list, scored with evaluate_pool.
        if aero_pools > 0:
            from .scout import candidate_pools

            try:
                for addr in candidate_pools(chain, market, aero_pools)[: aero_pools + 8]:
                    jobs.setdefault("aerodrome-slipstream", []).append(
                        Job("aerodrome-slipstream", f"aero {addr}", lambda addr=addr: score_aero(env, addr))
                    )
            except Exception as e:  # noqa: BLE001
                errors.append({"pool": "aerodrome-slipstream", "error": f"candidate list failed: {type(e).__name__}"})

    # Round-robin over providers, so a time budget cuts every provider evenly rather than the last ones whole.
    def budget_left() -> bool:
        return max_seconds is None or time.monotonic() - started < max_seconds

    total_jobs = sum(len(q) for q in jobs.values())
    done = 0
    non_aero_done = 0
    aero_done = 0
    queues = {k: list(q) for k, q in jobs.items()}
    while queues and budget_left():
        for k in list(queues):
            if not queues[k]:
                del queues[k]
                continue
            if not budget_left():
                break
            if k == "aerodrome-slipstream" and aero_done >= aero_pools:
                del queues[k]
                continue
            if k != "aerodrome-slipstream" and non_aero_done >= max_pools:
                del queues[k]
                continue
            job = queues[k].pop(0)
            done += 1
            try:
                row = job.run()
            except Exception as e:  # noqa: BLE001 - one bad pool must not end the run
                errors.append({"pool": job.label, "error": safe_error(e)})
                say(f"[{done}/{total_jobs}] {job.label}: error {safe_error(e)}")
                continue
            rows.append(row)
            if k == "aerodrome-slipstream":
                aero_done += 1
            else:
                non_aero_done += 1
            if job.llama_id:
                measured_llama.add(job.llama_id)
            net = row.expected_net_apr or 0.0
            fee = row.fee_pct or 0.0
            say(f"[{done}/{total_jobs}] {row.venue} {row.pair} {fee:.3g}%: net {net:+.1f}% ({row.confidence})")
    skipped = sum(len(q) for q in queues.values())
    if skipped:
        errors.append(
            {"pool": "budget", "error": f"time budget used up: {skipped} Tier 1 pools not scored (quoted instead)"}
        )
        say(f"time budget of {max_seconds:.0f}s used up: {skipped} Tier 1 pools left unscored")

    # Unregistered Uniswap-v3 forks, found by interface.
    if onchain and chain is not None and probe:
        for dex in PROBE_DEXES:
            if not budget_left():
                break
            try:
                listing = [x for x in gt_dex_pools(market, dex) if x["tvl_usd"] >= min_tvl_usd][:3]
            except Exception as e:  # noqa: BLE001 - the dex may not exist on GeckoTerminal any more
                errors.append({"pool": f"probe:{dex}", "error": f"listing failed: {type(e).__name__}"})
                continue
            for x in listing:
                if not budget_left():
                    break
                try:
                    row = score_v3(env, dex, dex, x["address"], x["tvl_usd"], x["volume_24h_usd"], None)
                    rows.append(row)
                    say(f"probe {dex} {row.pair}: net {row.expected_net_apr or 0:+.1f}% ({row.confidence})")
                except Exception as e:  # noqa: BLE001
                    errors.append({"pool": f"probe:{dex} {x['address']}", "error": safe_error(e)})

    # Tier 2: every remaining DefiLlama row, scored from quotes.
    measured_rows: dict[str, list[ProviderRow]] = {}
    for r in rows:
        measured_rows.setdefault(r.project, []).append(r)
    rest = [
        (p, a)
        for p, a in sel.kept
        if p.id not in measured_llama and not (a in COVERABLE and _covered(p, measured_rows.get(p.project, [])))
    ]
    inc_only = incentive_only(rest)
    # Score a quoted pool only when it quotes a positive base fee APY (a vault publishes only a total: that total less
    # its rewards stands in for apyBase).
    rest = [(p, a) for p, a in rest if ((p.quoted_base_apy if a is AmmType.ALM_VAULT else p.apy_base) or 0) > 0]
    coins.hourly([t for p, _a in rest if len(p.tokens) == 2 for t in p.tokens])
    unscored: Counter[str] = Counter()
    for p, amm in rest:
        if len(p.tokens) != 2:
            unscored[f"{p.project}: not a two-token pool"] += 1
            continue
        closes = coins.ratio_closes(p.tokens[0], p.tokens[1])
        sigma = vol_from_closes(closes)
        if sigma is None:
            unscored[f"{p.project}: no price history for the pair"] += 1
            continue
        try:
            row = evaluate_quoted(
                p, amm, sigma, f"defillama coins {len(closes)}h hourly", len(closes) / 24, min_net_apr, cfg
            )
        except Exception as error:  # noqa: BLE001 -- retain independently scored pools
            errors.append({"pool": p.id, "error": safe_error(error)})
            say(f"quoted {p.id}: error {safe_error(error)}")
            continue
        if row is None:
            unscored[f"{p.project}: no quoted base APY"] += 1
        else:
            rows.append(row)
    say(f"Tier 2: {sum(1 for r in rows if r.tier == 'quoted')} quoted rows, {sum(unscored.values())} unscored")

    attach_llama(rows, sel)
    ranked = rank_rows(rows)
    single = select_single_sided(raw, min_tvl_usd)
    for lst in single.values():
        for x in lst:
            x["clears_bar"] = x["apy_base"] >= min_net_apr
    doc = {
        "schema": SCHEMA,
        "generated_at": time.time() if now is None else now,
        "chain": chain_name,
        "deposit_usd": deposit_usd,
        "min_net_apr": min_net_apr,
        "params": {
            "min_tvl_usd": min_tvl_usd,
            "min_volume_usd": min_volume_usd,
            "max_pools": max_pools,
            "aero_pools": aero_pools,
            "probe": probe,
            "tier1_enabled": onchain,
            "elapsed_s": round(time.monotonic() - started, 1),
        },
        "sources": {"defillama_pools": src, "defillama_total_rows": sel.total},
        "registry": [
            {
                "id": v.id,
                "name": v.name,
                "factory": v.factory,
                "position_manager": v.position_manager,
                "state_view": v.state_view,
                "sources": list(v.sources),
            }
            for v in REGISTRY
        ],
        "providers": summarize(ranked, sel),
        "pools": [r.to_json() for r in ranked],
        "excluded": sel.excluded,
        "incentive_only": inc_only,
        "single_sided": single,
        "comparison": compare_lp_and_single(ranked, single, min_net_apr),
        "unscored": [{"reason": k, "count": n} for k, n in sorted(unscored.items())],
        "errors": errors,
    }
    if out_json is not None:
        atomic_write_json(out_json, doc)
    if out_report is not None:
        from .providers_report import render_report

        out_report.parent.mkdir(parents=True, exist_ok=True)
        out_report.write_text(render_report(doc))
    return doc


COVERABLE = {AmmType.CONCENTRATED, AmmType.UNISWAP_V4}


def _covered(p: LlamaPool, measured: list[ProviderRow]) -> bool:
    """True when a measured row already covers this DefiLlama row: same project, same token pair, and the same tick
    spacing (Aero's poolMeta says "CL100 - 0.015%") or the same fee."""
    for r in measured:
        if r.tier != "measured" or frozenset(r.venue_info.get("tokens", ())) != frozenset(p.tokens):
            continue
        if p.tick_spacing is not None and r.venue_info.get("tick_spacing") == p.tick_spacing:
            return True
        if p.fee_pips is not None and r.fee_pct is not None and round(r.fee_pct * 10_000) == p.fee_pips:
            return True
    return False


def attach_llama(rows: list[ProviderRow], sel: Selection) -> None:
    """Give a measured row the DefiLlama figures for the same pool: the quoted base APY (to set beside the measured
    income) and the incentive APR. An Aero row that already counts its measured AERO emissions gets no incentive."""
    by_project: dict[str, list[LlamaPool]] = {}
    for p, _a in sel.kept:
        by_project.setdefault(p.project, []).append(p)
    for r in rows:
        if r.tier != "measured" or r.quoted_apy_base is not None:
            continue
        toks = frozenset(r.venue_info.get("tokens", ()))
        match = [
            p
            for p in by_project.get(r.project, [])
            if frozenset(p.tokens) == toks
            and (
                (p.tick_spacing is not None and p.tick_spacing == r.venue_info.get("tick_spacing"))
                or (p.fee_pips is not None and r.fee_pct is not None and round(r.fee_pct * 10_000) == p.fee_pips)
            )
        ]
        if not match:
            continue
        p = max(match, key=lambda x: x.tvl_usd)
        r.quoted_apy_base = p.quoted_base_apy
        if r.incentive_apr is None and "gauge" not in r.income_source and p.apy_reward:
            r.incentive_apr = p.apy_reward
            if r.expected_net_apr is not None:
                r.net_apr_with_incentives = r.expected_net_apr + p.apy_reward


def summarize(ranked: list[ProviderRow], sel: Selection) -> list[dict[str, Any]]:
    """One row per provider: discovered vs scored, TVL, median quoted APY, median measured edge, best pool."""
    discovered: dict[str, list[LlamaPool]] = {}
    amm_of: dict[str, str] = {}
    for p, amm in sel.kept:
        discovered.setdefault(p.project, []).append(p)
        amm_of.setdefault(p.project, amm.value)
    by_project: dict[str, list[ProviderRow]] = {}
    for r in ranked:
        by_project.setdefault(r.project, []).append(r)
        amm_of.setdefault(r.project, r.amm_type)
    out = []
    for project in sorted(set(discovered) | set(by_project)):
        pools = discovered.get(project, [])
        rs = by_project.get(project, [])
        measured = [r for r in rs if r.tier == "measured"]
        quoted = [r for r in rs if r.tier == "quoted"]
        best = rs[0] if rs else None  # rows arrive ranked: the first is the best by the ranking rule
        out.append(
            {
                "provider": project,
                "venue": (BY_PROJECT[project].id if project in BY_PROJECT else project),
                "amm_type": amm_of.get(project, "other"),
                "pools_discovered": len(pools),
                "pools_measured": len(measured),
                "pools_quoted": len(quoted),
                "tvl_usd": sum(p.tvl_usd for p in pools) or sum(r.tvl_usd for r in rs),
                "median_quoted_apy": _median([p.quoted_base_apy for p in pools if p.quoted_base_apy is not None]),
                "median_measured_edge": _median([r.edge_ratio for r in measured if r.edge_ratio is not None]),
                "pools_clearing_bar": sum(1 for r in rs if r.clears_bar),
                "best_pool": (
                    {
                        "pair": best.pair,
                        "fee_pct": best.fee_pct,
                        "tier": best.tier,
                        "confidence": best.confidence,
                        "expected_net_apr": best.expected_net_apr,
                        "pool": best.pool,
                    }
                    if best
                    else None
                ),
            }
        )
    out.sort(key=lambda s: (s["best_pool"] is None, -((s["best_pool"] or {}).get("expected_net_apr") or -1e9)))
    return out
