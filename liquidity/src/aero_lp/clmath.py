"""Concentrated-liquidity math for Slipstream (Uniswap-v3-compatible tick math).

Integer functions are exact ports of TickMath / SqrtPriceMath / LiquidityAmounts.
Float helpers are for planning and reporting only, never for on-chain min-amount checks
without a slippage margin.
"""

from __future__ import annotations

import math

Q96 = 1 << 96
Q128 = 1 << 128
MIN_TICK = -887272
MAX_TICK = 887272
MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342
UINT128_MAX = (1 << 128) - 1
LOG_BASE = math.log(1.0001)


def get_sqrt_ratio_at_tick(tick: int) -> int:
    """Exact port of TickMath.getSqrtRatioAtTick. Returns sqrt(1.0001^tick) * 2^96."""
    if not MIN_TICK <= tick <= MAX_TICK:
        raise ValueError(f"tick {tick} out of range")
    abs_tick = abs(tick)
    ratio = 0xFFFCB933BD6FAD37AA2D162D1A594001 if abs_tick & 0x1 else 0x100000000000000000000000000000000
    for bit, mult in (
        (0x2, 0xFFF97272373D413259A46990580E213A),
        (0x4, 0xFFF2E50F5F656932EF12357CF3C7FDCC),
        (0x8, 0xFFE5CACA7E10E4E61C3624EAA0941CD0),
        (0x10, 0xFFCB9843D60F6159C9DB58835C926644),
        (0x20, 0xFF973B41FA98C081472E6896DFB254C0),
        (0x40, 0xFF2EA16466C96A3843EC78B326B52861),
        (0x80, 0xFE5DEE046A99A2A811C461F1969C3053),
        (0x100, 0xFCBE86C7900A88AEDCFFC83B479AA3A4),
        (0x200, 0xF987A7253AC413176F2B074CF7815E54),
        (0x400, 0xF3392B0822B70005940C7A398E4B70F3),
        (0x800, 0xE7159475A2C29B7443B29C7FA6E889D9),
        (0x1000, 0xD097F3BDFD2022B8845AD8F792AA5825),
        (0x2000, 0xA9F746462D870FDF8A65DC1F90E061E5),
        (0x4000, 0x70D869A156D2A1B890BB3DF62BAF32F7),
        (0x8000, 0x31BE135F97D08FD981231505542FCFA6),
        (0x10000, 0x9AA508B5B7A84E1C677DE54F3E99BC9),
        (0x20000, 0x5D6AF8DEDB81196699C329225EE604),
        (0x40000, 0x2216E584F5FA1EA926041BEDFE98),
        (0x80000, 0x48A170391F7DC42444E8FA2),
    ):
        if abs_tick & bit:
            ratio = (ratio * mult) >> 128
    if tick > 0:
        ratio = ((1 << 256) - 1) // ratio
    return (ratio >> 32) + (0 if ratio % (1 << 32) == 0 else 1)


def tick_from_price(price: float) -> float:
    """Raw (decimal-unadjusted) token1-per-token0 price -> fractional tick."""
    return math.log(price) / LOG_BASE


def price_from_tick(tick: float) -> float:
    """Raw token1-per-token0 price at a tick."""
    return math.exp(tick * LOG_BASE)


def human_price(raw_price: float, dec0: int, dec1: int) -> float:
    """Raw token1/token0 price -> human price (token1 units per 1 whole token0)."""
    return raw_price * 10 ** (dec0 - dec1)


def sqrtx96_to_price(sqrt_price_x96: int) -> float:
    ratio: float = sqrt_price_x96 / Q96
    return ratio * ratio


def floor_tick(tick: float, spacing: int) -> int:
    return int(math.floor(tick / spacing)) * spacing


def ceil_tick(tick: float, spacing: int) -> int:
    return int(math.ceil(tick / spacing)) * spacing


def usable_tick_bounds(spacing: int) -> tuple[int, int]:
    return ceil_tick(MIN_TICK, spacing), floor_tick(MAX_TICK, spacing)


# ---------------------------------------------------------------- LiquidityAmounts (exact ints)


def _mul_div(a: int, b: int, d: int) -> int:
    return a * b // d


def get_amount0_for_liquidity(sqrt_a: int, sqrt_b: int, liquidity: int) -> int:
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    return _mul_div(liquidity << 96, sqrt_b - sqrt_a, sqrt_b) // sqrt_a


def get_amount1_for_liquidity(sqrt_a: int, sqrt_b: int, liquidity: int) -> int:
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    return _mul_div(liquidity, sqrt_b - sqrt_a, Q96)


def get_amounts_for_liquidity(sqrt_p: int, sqrt_a: int, sqrt_b: int, liquidity: int) -> tuple[int, int]:
    """Token amounts a position of `liquidity` holds at price sqrt_p (rounded down)."""
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    if sqrt_p <= sqrt_a:
        return get_amount0_for_liquidity(sqrt_a, sqrt_b, liquidity), 0
    if sqrt_p < sqrt_b:
        return (
            get_amount0_for_liquidity(sqrt_p, sqrt_b, liquidity),
            get_amount1_for_liquidity(sqrt_a, sqrt_p, liquidity),
        )
    return 0, get_amount1_for_liquidity(sqrt_a, sqrt_b, liquidity)


def get_liquidity_for_amount0(sqrt_a: int, sqrt_b: int, amount0: int) -> int:
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    intermediate = _mul_div(sqrt_a, sqrt_b, Q96)
    return _mul_div(amount0, intermediate, sqrt_b - sqrt_a)


def get_liquidity_for_amount1(sqrt_a: int, sqrt_b: int, amount1: int) -> int:
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    return _mul_div(amount1, Q96, sqrt_b - sqrt_a)


def get_liquidity_for_amounts(sqrt_p: int, sqrt_a: int, sqrt_b: int, amount0: int, amount1: int) -> int:
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    if sqrt_p <= sqrt_a:
        return get_liquidity_for_amount0(sqrt_a, sqrt_b, amount0)
    if sqrt_p < sqrt_b:
        return min(
            get_liquidity_for_amount0(sqrt_p, sqrt_b, amount0),
            get_liquidity_for_amount1(sqrt_a, sqrt_p, amount1),
        )
    return get_liquidity_for_amount1(sqrt_a, sqrt_b, amount1)


# ---------------------------------------------------------------- fees owed (PositionValue.fees)


def fee_growth_inside(
    tick_current: int,
    tick_lower: int,
    tick_upper: int,
    global0: int,
    global1: int,
    lower_out0: int,
    lower_out1: int,
    upper_out0: int,
    upper_out1: int,
) -> tuple[int, int]:
    """Port of Tick.getFeeGrowthInside with uint256 wraparound."""
    mod = 1 << 256
    if tick_current >= tick_lower:
        below0, below1 = lower_out0, lower_out1
    else:
        below0, below1 = (global0 - lower_out0) % mod, (global1 - lower_out1) % mod
    if tick_current < tick_upper:
        above0, above1 = upper_out0, upper_out1
    else:
        above0, above1 = (global0 - upper_out0) % mod, (global1 - upper_out1) % mod
    return (global0 - below0 - above0) % mod, (global1 - below1 - above1) % mod


def fees_owed(liquidity: int, inside_now: int, inside_last: int) -> int:
    return liquidity * ((inside_now - inside_last) % (1 << 256)) // Q128


# ---------------------------------------------------------------- planning helpers (floats)


def value0_fraction(price: float, price_lower: float, price_upper: float) -> float:
    """Share of a fresh position's value that must be token0 at `price` (raw token1/token0 prices).

    Per unit liquidity: amount0 = 1/sqrtP - 1/sqrtB, amount1 = sqrtP - sqrtA.
    """
    if price <= price_lower:
        return 1.0
    if price >= price_upper:
        return 0.0
    sp, sa, sb = math.sqrt(price), math.sqrt(price_lower), math.sqrt(price_upper)
    v0 = (1 / sp - 1 / sb) * price
    v1 = sp - sa
    return v0 / (v0 + v1)


def swap_to_ratio(bal0: float, bal1: float, price: float, target_frac0: float, fee: float) -> tuple[int, float]:
    """Amount to sell so the post-swap value split matches `target_frac0`.

    Returns (direction, amount_in): direction 0 = sell token0 for token1, 1 = sell token1 for token0,
    amount_in in raw units of the sold token. `fee` is the pool fee as a fraction (0.0005 = 5 bps).
    Price impact is ignored; the executor re-reads balances after the swap and the position
    manager refunds the unused remainder.
    """
    v0, v1 = bal0 * price, bal1
    total = v0 + v1
    if total <= 0:
        return 0, 0.0
    target_v0 = target_frac0 * total
    if v0 > target_v0:
        # sell x token0: (bal0 - x)*P = r * ((bal0 - x)*P + bal1 + x*P*(1-f))
        r = target_frac0
        x = (v0 - r * total) / (price * (1 - r * fee))
        return 0, max(0.0, min(x, bal0))
    # sell y token1: (bal0*P + y*(1-f)) = r * (bal0*P + y*(1-f) + bal1 - y)
    r = target_frac0
    y = (r * total - v0) / ((1 - fee) * (1 - r) + r)
    return 1, max(0.0, min(y, bal1))


def position_value_in_token1(amount0: float, amount1: float, price: float) -> float:
    return amount0 * price + amount1


def impermanent_loss_vs_hold(price_entry: float, price_now: float, price_lower: float, price_upper: float) -> float:
    """Value of a CL position relative to holding the entry token mix (negative = loss), as a fraction.

    Uses unit liquidity; independent of position size.
    """

    def amounts(p: float) -> tuple[float, float]:
        sa, sb = math.sqrt(price_lower), math.sqrt(price_upper)
        sp = min(max(math.sqrt(p), sa), sb)
        return 1 / sp - 1 / sb, sp - sa

    a0, a1 = amounts(price_entry)
    hold = a0 * price_now + a1
    b0, b1 = amounts(price_now)
    lp = b0 * price_now + b1
    return lp / hold - 1 if hold > 0 else 0.0
