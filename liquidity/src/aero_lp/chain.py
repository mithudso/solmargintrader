"""Read-only access to Aero Slipstream state on Base.

All multi-value reads go through Multicall3 in one eth_call pinned to one block, so a snapshot is
internally consistent and public RPC rate limits are respected.
"""

from __future__ import annotations

import contextlib
import math
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc.utils import ExceptionRetryConfiguration

from . import abi, addresses, clmath
from .validation import finite_number

ZERO = "0x0000000000000000000000000000000000000000"
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
MULTICALL3_ABI = [
    abi.fn(
        "aggregate3",
        "tuple(address target, bool allowFailure, bytes callData)[] calls",
        "tuple(bool success, bytes returnData)[] returnData",
        "payable",
    )
]
DEFAULT_RPCS = ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org"]
MAX_HEAD_LAG_S = 90


def _type_str(p: dict[str, Any]) -> str:
    t = p["type"]
    if t.startswith("tuple"):
        inner = ",".join(_type_str(c) for c in p["components"])
        return f"({inner}){t[5:]}"
    return t


MIN_BLOCK_READ_TRIES = 8
MIN_BLOCK_READ_DELAY_S = 1.5


class PositionGone(RuntimeError):
    pass


@dataclass(frozen=True)
class Call:
    contract: Contract
    fn: str
    args: tuple[Any, ...] = ()
    allow_failure: bool = False


@dataclass(frozen=True)
class Token:
    address: str
    symbol: str
    decimals: int


@dataclass
class PoolState:
    address: str
    token0: Token
    token1: Token
    tick_spacing: int
    fee_pips: int
    unstaked_fee_pips: int
    sqrt_price_x96: int
    tick: int
    liquidity: int
    staked_liquidity: int
    gauge: str
    gauge_alive: bool
    fee_growth_global0: int
    fee_growth_global1: int
    reward_growth_global: int
    block: int
    timestamp: int

    @property
    def raw_price(self) -> float:
        return clmath.sqrtx96_to_price(self.sqrt_price_x96)

    @property
    def price(self) -> float:
        """Human price: token1 per 1 token0."""
        return clmath.human_price(self.raw_price, self.token0.decimals, self.token1.decimals)

    @property
    def fee(self) -> float:
        return self.fee_pips / 1e6


@dataclass
class PositionState:
    token_id: int
    owner: str  # the economic owner (wallet), even when the NFT sits in the gauge
    staked: bool
    pool: PoolState
    tick_lower: int
    tick_upper: int
    liquidity: int
    amount0: int  # principal at current price, raw units
    amount1: int
    fees0: int  # uncollected fees, raw units (0 when staked: staked fees go to Token Operators)
    fees1: int
    earned_aero: int = 0  # unclaimed AERO (raw, 18 decimals) if staked
    deposit_block: int = 0
    penalty_min_blocks: int = 0
    penalty_rate: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def in_range(self) -> bool:
        return self.tick_lower <= self.pool.tick < self.tick_upper

    @property
    def penalty_blocks_left(self) -> int:
        if not self.staked or not self.deposit_block or not self.penalty_min_blocks:
            return 0
        return max(0, self.deposit_block + self.penalty_min_blocks - self.pool.block)

    def human_amounts(self) -> tuple[float, float]:
        d0, d1 = self.pool.token0.decimals, self.pool.token1.decimals
        return (self.amount0 + self.fees0) / 10**d0, (self.amount1 + self.fees1) / 10**d1

    def price_bounds(self) -> tuple[float, float]:
        d0, d1 = self.pool.token0.decimals, self.pool.token1.decimals
        return (
            clmath.human_price(clmath.price_from_tick(self.tick_lower), d0, d1),
            clmath.human_price(clmath.price_from_tick(self.tick_upper), d0, d1),
        )

    def value_in_token1(self) -> float:
        a0, a1 = self.human_amounts()
        return a0 * self.pool.price + a1


def make_web3(rpc_url: str) -> Web3:
    retry = ExceptionRetryConfiguration(
        errors=(requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout),
        retries=6,
        backoff_factor=0.8,
    )
    provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}, exception_retry_configuration=retry)
    w3 = Web3(provider)
    # The validation middleware issues eth_chainId before every call; we check the chain once instead.
    with contextlib.suppress(ValueError, KeyError):
        w3.middleware_onion.remove("validation")
    return w3


class AeroChain:
    def __init__(
        self,
        rpc_url: str = DEFAULT_RPCS[0],
        *,
        w3: Web3 | None = None,
        expected_chain_id: int = addresses.BASE_CHAIN_ID,
    ):
        self.w3 = w3 or make_web3(rpc_url)
        chain_id = self.w3.eth.chain_id
        if chain_id != expected_chain_id:
            raise RuntimeError(f"RPC chain id {chain_id} != expected {expected_chain_id} (Base)")
        self.npm = self._c(addresses.NONFUNGIBLE_POSITION_MANAGER, abi.NPM)
        self.factory = self._c(addresses.CL_FACTORY, abi.CL_FACTORY)
        self.voter = self._c(addresses.LEAF_VOTER, abi.LEAF_VOTER)
        self.gauge_factory = self._c(addresses.CL_GAUGE_FACTORY, abi.CL_GAUGE_FACTORY)
        self.mc = self._c(MULTICALL3, MULTICALL3_ABI)
        self._tokens: dict[str, Token] = {}
        # Highest block in which this process mined a transaction (set by LiveRunner). Balance reads that ask for
        # "latest" are served at a block no older than this, so a load-balanced RPC node that is one block behind
        # cannot return pre-transaction balances for the next operation's "before" snapshot.
        self.min_block: int | None = None

    def _c(self, address: str, contract_abi: list[dict[str, Any]]) -> Contract:
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=contract_abi)

    # ------------------------------------------------------------------ batching

    def multicall(self, calls: list[Call], block: int | str = "latest") -> list[Any]:
        """Run calls in one Multicall3 eth_call. Failed allow_failure calls return None."""
        payload = []
        out_types: list[list[str]] = []
        for c in calls:
            fn_abi = next(f for f in c.contract.abi if f.get("name") == c.fn and f["type"] == "function")
            in_types = [_type_str(i) for i in fn_abi["inputs"]]
            data = Web3.keccak(text=f"{c.fn}({','.join(in_types)})")[:4] + self.w3.codec.encode(in_types, list(c.args))
            payload.append((c.contract.address, c.allow_failure, data))
            out_types.append([_type_str(o) for o in fn_abi["outputs"]])
        results = self.mc.functions.aggregate3(payload).call(block_identifier=block)
        decoded: list[Any] = []
        for (ok, ret), types, c in zip(results, out_types, calls, strict=True):
            if not ok:
                if not c.allow_failure:
                    raise RuntimeError(f"multicall {c.fn} on {c.contract.address} failed")
                decoded.append(None)
                continue
            vals = self.w3.codec.decode(types, ret)
            decoded.append(vals[0] if len(vals) == 1 else vals)
        return decoded

    # ------------------------------------------------------------------ safety

    def head(self) -> tuple[int, int]:
        blk = self.w3.eth.get_block("latest")
        minimum = getattr(self, "min_block", None)
        if minimum is not None and int(blk["number"]) < minimum:
            last: Exception | None = None
            for attempt in range(MIN_BLOCK_READ_TRIES):
                try:
                    blk = self.w3.eth.get_block(minimum)
                    if int(blk["number"]) < minimum:
                        raise RuntimeError("RPC returned a block older than the receipt")
                    break
                except Exception as error:  # noqa: BLE001 - load-balanced node has not imported the receipt yet
                    last = error
                    if attempt + 1 < MIN_BLOCK_READ_TRIES:
                        time.sleep(MIN_BLOCK_READ_DELAY_S)
            else:
                raise RuntimeError(f"RPC could not serve head at or after block {minimum}: {last}") from last
        return int(blk["number"]), int(blk["timestamp"])

    def check_fresh(self, max_lag_s: int = MAX_HEAD_LAG_S) -> int:
        """Refuse a stale RPC node (some public endpoints lag hours). Returns head block."""
        number, ts = self.head()
        lag = time.time() - ts
        if lag > max_lag_s:
            raise RuntimeError(f"RPC head block {number} is {lag:.0f}s old (> {max_lag_s}s); node is stale")
        return number

    def verify_deployment(self) -> list[str]:
        """Return a list of problems; empty means the hard-coded addresses look right on this RPC."""
        problems = []
        for name, addr in {**addresses.ALL_CONTRACTS, "Multicall3": MULTICALL3}.items():
            code = self.w3.eth.get_code(Web3.to_checksum_address(addr))
            if len(code) == 0:
                problems.append(f"{name} {addr}: no contract code")
        try:
            fac = self.npm.functions.factory().call()
            if fac.lower() != addresses.CL_FACTORY.lower():
                problems.append(f"NPM.factory() = {fac}, expected {addresses.CL_FACTORY}")
        except Exception as e:  # noqa: BLE001
            problems.append(f"NPM.factory() call failed: {e}")
        try:
            self.check_fresh()
        except RuntimeError as e:
            problems.append(str(e))
        return problems

    # ------------------------------------------------------------------ tokens / pools

    def token(self, address: str) -> Token:
        key = address.lower()
        if key not in self._tokens:
            c = self._c(address, abi.ERC20)
            sym, dec = self.multicall([Call(c, "symbol", allow_failure=True), Call(c, "decimals")])
            self._tokens[key] = Token(Web3.to_checksum_address(address), sym or address[:8], int(dec))
        return self._tokens[key]

    def pool_address(self, token0: str, token1: str, tick_spacing: int) -> str:
        fn = self.factory.get_function_by_signature("getPool(address,address,int24)")
        return fn(Web3.to_checksum_address(token0), Web3.to_checksum_address(token1), tick_spacing).call()

    def pool_state(self, pool_address: str, block: int | None = None) -> PoolState:
        bn = block if block is not None else self.head()[0]
        p = self._c(pool_address, abi.CL_POOL)
        (s0, t0, t1, ts, fee, ufee, liq, sliq, gauge, fg0, fg1, rg) = self.multicall(
            [
                Call(p, "slot0"),
                Call(p, "token0"),
                Call(p, "token1"),
                Call(p, "tickSpacing"),
                Call(p, "fee"),
                Call(p, "unstakedFee"),
                Call(p, "liquidity"),
                Call(p, "stakedLiquidity"),
                Call(p, "gauge"),
                Call(p, "feeGrowthGlobal0X128"),
                Call(p, "feeGrowthGlobal1X128"),
                Call(p, "rewardGrowthGlobalX128", allow_failure=True),
            ],
            block=bn,
        )
        alive = False
        if gauge != ZERO:
            alive = bool(self.multicall([Call(self.voter, "isActivated", (gauge,), True)], block=bn)[0])
        ts_block = int(self.w3.eth.get_block(bn)["timestamp"])
        return PoolState(
            address=Web3.to_checksum_address(pool_address),
            token0=self.token(t0),
            token1=self.token(t1),
            tick_spacing=int(ts),
            fee_pips=int(fee),
            unstaked_fee_pips=int(ufee),
            sqrt_price_x96=int(s0[0]),
            tick=int(s0[1]),
            liquidity=int(liq),
            staked_liquidity=int(sliq),
            gauge=Web3.to_checksum_address(gauge),
            gauge_alive=alive,
            fee_growth_global0=int(fg0),
            fee_growth_global1=int(fg1),
            reward_growth_global=int(rg or 0),
            block=bn,
            timestamp=ts_block,
        )

    def twap_tick_series(self, pool_address: str, hours: int = 48, step_s: int = 3600) -> list[float]:
        """Average tick per `step_s` window over the last `hours` hours, oldest first. Empty if history is short."""
        p = self._c(pool_address, abi.CL_POOL)
        for h in (hours, hours // 2, hours // 4, 6):
            agos = [i * step_s for i in range(h * 3600 // step_s, -1, -1)]
            try:
                cums, _ = p.functions.observe(agos).call()
            except Exception:  # noqa: BLE001 - 'OLD' revert when oracle cardinality is too small
                continue
            return [(cums[i + 1] - cums[i]) / step_s for i in range(len(cums) - 1)]
        return []

    # ------------------------------------------------------------------ positions

    def gauge_contract(self, gauge: str) -> Contract:
        return self._c(gauge, abi.CL_GAUGE)

    def position(self, token_id: int, owner_hint: str | None = None) -> PositionState:
        head = self.head()[0]
        pos, nft_owner = self.multicall(
            [Call(self.npm, "positions", (token_id,), True), Call(self.npm, "ownerOf", (token_id,), True)], block=head
        )
        if pos is None or nft_owner is None:
            raise PositionGone(
                f"Slipstream position #{token_id} does not exist (burned or never minted). If it was rebalanced "
                "outside this bot, put the new token id in the config."
            )
        (_, _, t0, t1, spacing, tl, tu, liq, fgi0_last, fgi1_last, owed0, owed1) = pos
        pool = self.pool_state(self.pool_address(t0, t1, spacing), block=head)
        staked = pool.gauge != ZERO and nft_owner.lower() == pool.gauge.lower()
        owner = nft_owner
        if staked and owner_hint:
            hinted = Web3.to_checksum_address(owner_hint)
            membership = self.multicall(
                [Call(self.gauge_contract(pool.gauge), "stakedContains", (hinted, token_id))], block=head
            )[0]
            if membership is not True:
                raise RuntimeError(f"position #{token_id} is not staked by {hinted} (ownership evidence: {membership})")
            owner = hinted

        sa, sb = clmath.get_sqrt_ratio_at_tick(tl), clmath.get_sqrt_ratio_at_tick(tu)
        a0, a1 = clmath.get_amounts_for_liquidity(pool.sqrt_price_x96, sa, sb, liq)
        pc = self._c(pool.address, abi.CL_POOL)
        lo, hi = self.multicall([Call(pc, "ticks", (tl,)), Call(pc, "ticks", (tu,))], block=head)
        in0, in1 = clmath.fee_growth_inside(
            pool.tick, tl, tu, pool.fee_growth_global0, pool.fee_growth_global1, lo[3], lo[4], hi[3], hi[4]
        )
        fees0 = owed0 + clmath.fees_owed(liq, in0, fgi0_last)
        fees1 = owed1 + clmath.fees_owed(liq, in1, fgi1_last)
        st = PositionState(token_id, owner, staked, pool, tl, tu, liq, a0, a1, fees0, fees1)

        if staked:
            g = self.gauge_contract(pool.gauge)
            calls = [
                Call(g, "depositBlock", (token_id,)),
                Call(self.gauge_factory, "effectivePenaltyConfig", (pool.gauge,)),
                Call(self.gauge_factory, "MAX_PIPS"),
            ]
            if owner_hint:
                calls.append(Call(g, "earned", (owner, [token_id])))
                # AERO whose mint reverted during an earlier withdraw/claim is parked here, not paid out.
                calls.append(Call(g, "deferredEmissions", (owner,), True))
            res = self.multicall(calls, block=head)
            st.fees0 = st.fees1 = 0
            st.deposit_block = int(res[0])
            try:
                if not isinstance(res[1], tuple | list) or len(res[1]) != 2:
                    raise ValueError("penalty configuration missing")
                minimum_blocks, rate = res[1]
                finite_number(minimum_blocks, "minStakeBlocks", integer=True)
                finite_number(rate, "penaltyRate", integer=True)
                finite_number(res[2], "MAX_PIPS", positive=True, integer=True)
                if rate > res[2]:
                    raise ValueError("penaltyRate exceeds MAX_PIPS")
            except ValueError as error:
                raise RuntimeError(f"position #{token_id}: penalty data unavailable or invalid: {error}") from error
            st.penalty_min_blocks, st.penalty_rate = minimum_blocks, rate / res[2]
            if owner_hint:
                try:
                    finite_number(res[3], "accrued AERO reward", integer=True)
                except ValueError as error:
                    raise RuntimeError(f"position #{token_id}: reward data unavailable or invalid: {error}") from error
                st.earned_aero = res[3]
                st.extra["deferred_aero"] = int(res[4] or 0)
        return st

    def positions_of(self, owner: str, pools: list[str] | None = None) -> list[int]:
        """Token ids the owner holds directly plus those staked in the gauges of `pools`."""
        owner = Web3.to_checksum_address(owner)
        n = int(self.npm.functions.balanceOf(owner).call())
        ids: list[int] = []
        if n:
            ids = list(self.multicall([Call(self.npm, "tokenOfOwnerByIndex", (owner, i)) for i in range(n)]))
        for pool_addr in pools or []:
            ps = self.pool_state(pool_addr)
            if ps.gauge != ZERO:
                ids.extend(self.gauge_contract(ps.gauge).functions.stakedValues(owner).call())
        return sorted({int(i) for i in ids})

    def erc20_balances(self, owner: str, tokens: list[str], block: int | str = "latest") -> list[int]:
        calls = [Call(self._c(t, abi.ERC20), "balanceOf", (Web3.to_checksum_address(owner),)) for t in tokens]
        if block != "latest" or not self.min_block:
            return [int(x) for x in self.multicall(calls, block=block)]
        last: Exception | None = None
        for attempt in range(MIN_BLOCK_READ_TRIES):
            try:
                pinned = max(self.min_block, int(self.w3.eth.block_number))
                return [int(x) for x in self.multicall(calls, block=pinned)]
            except Exception as e:  # noqa: BLE001 - the node has not imported our last block yet: wait and retry
                last = e
                if attempt + 1 < MIN_BLOCK_READ_TRIES:
                    time.sleep(MIN_BLOCK_READ_DELAY_S)
        raise RuntimeError(f"RPC could not serve balances at or after block {self.min_block}: {last}") from last

    def gauge_aero_per_day(self, gauge: str, head: int, blocks_per_day: int = 43_200) -> float:
        """AERO emitted to `gauge` per day, from LeafVoter.projectedCumulativeRewardShare over the last day.

        The reward share is the cumulative AERO (18 decimals) credited to the gauge. Falls back to shorter
        windows when the RPC lacks state history.
        """
        if gauge == ZERO:
            return 0.0
        fn = self.voter.functions.projectedCumulativeRewardShare(gauge)
        now = fn.call(block_identifier=head)
        for back in (blocks_per_day, blocks_per_day // 4, 1800):
            try:
                then = fn.call(block_identifier=head - back)
            except Exception:  # noqa: BLE001 - RPC without enough history
                continue
            return (now - then) / 1e18 * blocks_per_day / back
        return 0.0

    def fee_growth_delta(self, pool_address: str, head: int, blocks_per_day: int = 43_200) -> tuple[int, int, float]:
        """(d feeGrowthGlobal0X128, d feeGrowthGlobal1X128, days) over the last day, shorter if history is
        missing. Returns zeros when no historical state is available."""
        p = self._c(pool_address, abi.CL_POOL)
        mod = 1 << 256
        now0, now1 = self.multicall([Call(p, "feeGrowthGlobal0X128"), Call(p, "feeGrowthGlobal1X128")], block=head)
        for back in (blocks_per_day, blocks_per_day // 4, 1800):
            try:
                then0, then1 = self.multicall(
                    [Call(p, "feeGrowthGlobal0X128"), Call(p, "feeGrowthGlobal1X128")], block=head - back
                )
            except Exception:  # noqa: BLE001 - RPC without enough history, or pool younger than the window
                continue
            return (now0 - then0) % mod, (now1 - then1) % mod, back / blocks_per_day
        return 0, 0, 0.0

    def gas_price_wei(self) -> int:
        return int(self.w3.eth.gas_price)


# Differences of consecutive window-average ticks have variance (2/3) * sigma^2 * step for Brownian motion
# (the averaging smooths the path), so the raw estimate is low by sqrt(2/3).
TWAP_DIFF_VOL_BIAS = math.sqrt(1.5)


def realized_vol_daily(ticks: list[float], step_s: int = 3600) -> float | None:
    """Daily log-return volatility from a series of per-window *average* ticks (None if too few points).

    The series comes from pool-oracle cumulative ticks, so each point is a window average, not a closing
    price; `TWAP_DIFF_VOL_BIAS` corrects the smoothing so the result matches close-to-close volatility.
    """
    if len(ticks) < 6:
        return None
    rets = [(ticks[i + 1] - ticks[i]) * clmath.LOG_BASE for i in range(len(ticks) - 1)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(86400 / step_s) * TWAP_DIFF_VOL_BIAS
