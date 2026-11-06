"""Minimal ABIs for the Aero Slipstream contracts the bot touches.

Signatures were copied from github.com/dromos-labs/metadex-slipstream-public (v1.1.0):
  contracts/periphery/interfaces/INonfungiblePositionManager.sol
  contracts/core/interfaces/pool/ICLPoolState.sol, ICLPoolConstants.sol
  contracts/gauge/interfaces/ICLGauge.sol, IGauge.sol, ICLGaugeFactory.sol
  contracts/periphery/interfaces/ISwapRouter.sol
  contracts/core/interfaces/IVoter.sol, ICLFactory.sol
"""

from __future__ import annotations

from typing import Any


def _p(spec: str) -> list[dict[str, Any]]:
    """Parse 'type name, type name' into ABI params. Tuples use the form tuple(type name,...) name."""
    out: list[dict[str, Any]] = []
    spec = spec.strip()
    if not spec:
        return out
    depth, cur = 0, ""
    parts: list[str] = []
    for ch in spec:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    for part in parts:
        if part.startswith("tuple("):
            close = part.rindex(")")
            inner, rest = part[6:close], part[close + 1 :].strip()
            suffix, _, name = rest.partition(" ") if rest.startswith("[") else ("", "", rest)
            out.append({"type": "tuple" + suffix, "name": name.strip(), "components": _p(inner)})
        else:
            typ, _, name = part.partition(" ")
            out.append({"type": typ, "name": name.strip()})
    return out


def fn(name: str, inputs: str = "", outputs: str = "", mut: str = "view") -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "inputs": _p(inputs),
        "outputs": _p(outputs),
        "stateMutability": mut,
    }


def ev(name: str, inputs: list[tuple[str, str, bool]]) -> dict[str, Any]:
    return {
        "type": "event",
        "name": name,
        "anonymous": False,
        "inputs": [{"type": t, "name": n, "indexed": i} for t, n, i in inputs],
    }


ERC20 = [
    fn("decimals", "", "uint8 "),
    fn("symbol", "", "string "),
    fn("balanceOf", "address owner", "uint256 "),
    fn("allowance", "address owner, address spender", "uint256 "),
    fn("approve", "address spender, uint256 amount", "bool ", "nonpayable"),
]

_MINT = (
    "tuple(address token0, address token1, int24 tickSpacing, int24 tickLower, int24 tickUpper, "
    "uint256 amount0Desired, uint256 amount1Desired, uint256 amount0Min, uint256 amount1Min, "
    "address recipient, uint256 deadline, uint160 sqrtPriceX96) params"
)
_DECREASE = "tuple(uint256 tokenId, uint128 liquidity, uint256 amount0Min, uint256 amount1Min, uint256 deadline) params"
_COLLECT = "tuple(uint256 tokenId, address recipient, uint128 amount0Max, uint128 amount1Max) params"

_INCREASE = (
    "tuple(uint256 tokenId, uint256 amount0Desired, uint256 amount1Desired, uint256 amount0Min, "
    "uint256 amount1Min, uint256 deadline) params"
)

NPM = [
    fn("increaseLiquidity", _INCREASE, "uint128 liquidity, uint256 amount0, uint256 amount1", "payable"),
    fn(
        "positions",
        "uint256 tokenId",
        "uint96 nonce, address operator, address token0, address token1, int24 tickSpacing, "
        "int24 tickLower, int24 tickUpper, uint128 liquidity, uint256 feeGrowthInside0LastX128, "
        "uint256 feeGrowthInside1LastX128, uint128 tokensOwed0, uint128 tokensOwed1",
    ),
    fn("factory", "", "address "),
    fn("ownerOf", "uint256 tokenId", "address "),
    fn("balanceOf", "address owner", "uint256 "),
    fn("tokenOfOwnerByIndex", "address owner, uint256 index", "uint256 "),
    fn("getApproved", "uint256 tokenId", "address "),
    fn("approve", "address to, uint256 tokenId", "", "nonpayable"),
    fn("mint", _MINT, "uint256 tokenId, uint128 liquidity, uint256 amount0, uint256 amount1", "payable"),
    fn("decreaseLiquidity", _DECREASE, "uint256 amount0, uint256 amount1", "payable"),
    fn("collect", _COLLECT, "uint256 amount0, uint256 amount1", "payable"),
    fn("burn", "uint256 tokenId", "", "payable"),
    fn("multicall", "bytes[] data", "bytes[] results", "payable"),
    ev(
        "Transfer",
        [("address", "from", True), ("address", "to", True), ("uint256", "tokenId", True)],
    ),
    ev(
        "IncreaseLiquidity",
        [
            ("uint256", "tokenId", True),
            ("uint128", "liquidity", False),
            ("uint256", "amount0", False),
            ("uint256", "amount1", False),
        ],
    ),
]

CL_POOL = [
    fn(
        "slot0",
        "",
        "uint160 sqrtPriceX96, int24 tick, uint16 observationIndex, uint16 observationCardinality, "
        "uint16 observationCardinalityNext, bool unlocked",
    ),
    fn("token0", "", "address "),
    fn("token1", "", "address "),
    fn("tickSpacing", "", "int24 "),
    fn("fee", "", "uint24 "),
    fn("unstakedFee", "", "uint24 "),
    fn("liquidity", "", "uint128 "),
    fn("stakedLiquidity", "", "uint128 "),
    fn("gauge", "", "address "),
    fn("feeGrowthGlobal0X128", "", "uint256 "),
    fn("feeGrowthGlobal1X128", "", "uint256 "),
    fn("rewardGrowthGlobalX128", "", "uint256 "),
    fn(
        "ticks",
        "int24 tick",
        "uint128 liquidityGross, int128 liquidityNet, int128 stakedLiquidityNet, "
        "uint256 feeGrowthOutside0X128, uint256 feeGrowthOutside1X128, uint256 rewardGrowthOutsideX128, "
        "int56 tickCumulativeOutside, uint160 secondsPerLiquidityOutsideX128, uint32 secondsOutside, "
        "bool initialized",
    ),
    fn("observe", "uint32[] secondsAgos", "int56[] tickCumulatives, uint160[] secondsPerLiquidityCumulativeX128s"),
]

CL_GAUGE = [
    fn("deposit", "uint256 _lp", "", "nonpayable"),
    fn("withdraw", "uint256 _lp", "", "nonpayable"),
    fn("claimEmissions", "address _account, address _recipient, uint256[] _tokenIds", "", "nonpayable"),
    fn("earned", "address _account, uint256[] _tokenIds", "uint256 "),
    fn("depositBlock", "uint256 _tokenId", "uint256 "),
    fn("stakedValues", "address _depositor", "uint256[] "),
    fn("stakedContains", "address _depositor, uint256 _tokenId", "bool "),
    fn("gaugeFactory", "", "address "),
    fn("pool", "", "address "),
    fn("deferredEmissions", "address _account", "uint256 "),
]

CL_GAUGE_FACTORY = [
    fn("effectivePenaltyConfig", "address _gauge", "tuple(uint256 minStakeBlocks, uint256 penaltyRate) "),
    fn("MAX_PIPS", "", "uint256 "),
]

LEAF_VOTER = [
    fn("isActivated", "address _gauge", "bool "),
    fn("projectedCumulativeRewardShare", "address _gauge", "uint256 "),
]

CL_FACTORY = [
    {
        **fn("getPool", "address tokenA, address tokenB, int24 tickSpacing", "address pool"),
    },
    fn("tickSpacings", "", "int24[] "),
    fn("tickSpacingToFee", "int24 tickSpacing", "uint24 fee"),
]

_EXACT_IN = (
    "tuple(address tokenIn, address tokenOut, int24 tickSpacing, address recipient, uint256 deadline, "
    "uint256 amountIn, uint256 amountOutMinimum, uint160 sqrtPriceLimitX96) params"
)
SWAP_ROUTER = [
    fn("exactInputSingle", _EXACT_IN, "uint256 amountOut", "payable"),
]

WETH = [
    fn("withdraw", "uint256 wad", "", "nonpayable"),
    fn("deposit", "", "", "payable"),
]
