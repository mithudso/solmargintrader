from decimal import Decimal, getcontext

import pytest

from aero_lp import clmath


def test_sqrt_ratio_known_points():
    assert clmath.get_sqrt_ratio_at_tick(0) == 1 << 96
    assert clmath.get_sqrt_ratio_at_tick(clmath.MIN_TICK) == clmath.MIN_SQRT_RATIO
    assert clmath.get_sqrt_ratio_at_tick(clmath.MAX_TICK) == clmath.MAX_SQRT_RATIO
    with pytest.raises(ValueError):
        clmath.get_sqrt_ratio_at_tick(clmath.MAX_TICK + 1)


@pytest.mark.parametrize("tick", [-199211, -50, -1, 1, 50, 1000, 276324])
def test_sqrt_ratio_matches_high_precision_reference(tick):
    getcontext().prec = 60
    ref = (Decimal("1.0001") ** tick).sqrt() * (1 << 96)
    exact = clmath.get_sqrt_ratio_at_tick(tick)
    assert abs(Decimal(exact) - ref) / ref < Decimal("1e-15")


def test_sqrt_ratio_monotonic():
    vals = [clmath.get_sqrt_ratio_at_tick(t) for t in range(-500, 500, 7)]
    assert vals == sorted(vals)


def test_human_price_weth_usdc():
    # WETH (18 dec) / USDC (6 dec) around tick -199211 is ~2,232 USDC per WETH
    raw = clmath.price_from_tick(-199211)
    assert clmath.human_price(raw, 18, 6) == pytest.approx(2232.7, rel=1e-3)


def test_liquidity_amount_round_trip():
    sp = clmath.get_sqrt_ratio_at_tick(-199211)
    sa, sb = clmath.get_sqrt_ratio_at_tick(-199800), clmath.get_sqrt_ratio_at_tick(-198700)
    a0, a1 = 10**18, 2232 * 10**6
    liq = clmath.get_liquidity_for_amounts(sp, sa, sb, a0, a1)
    u0, u1 = clmath.get_amounts_for_liquidity(sp, sa, sb, liq)
    assert u0 <= a0 and u1 <= a1
    # one side is fully used (the binding constraint), within rounding
    assert max(u0 / a0, u1 / a1) == pytest.approx(1.0, rel=1e-6)


def test_amounts_single_sided_outside_range():
    sa, sb = clmath.get_sqrt_ratio_at_tick(100), clmath.get_sqrt_ratio_at_tick(200)
    below = clmath.get_amounts_for_liquidity(clmath.get_sqrt_ratio_at_tick(50), sa, sb, 10**18)
    above = clmath.get_amounts_for_liquidity(clmath.get_sqrt_ratio_at_tick(250), sa, sb, 10**18)
    assert below[1] == 0 and below[0] > 0
    assert above[0] == 0 and above[1] > 0


def test_fee_growth_inside_wraparound():
    mod = 1 << 256
    # current tick inside; outside values larger than global (wrapped) must still give a sane delta
    g0, g1 = 5, 7
    lo0, lo1, hi0, hi1 = mod - 10, mod - 10, 3, 4
    in0, in1 = clmath.fee_growth_inside(150, 100, 200, g0, g1, lo0, lo1, hi0, hi1)
    assert in0 == (g0 - lo0 - hi0) % mod
    assert in1 == (g1 - lo1 - hi1) % mod
    owed = clmath.fees_owed(1 << 128, in0, (in0 - 12) % mod)
    assert owed == 12


def test_value0_fraction_bounds():
    assert clmath.value0_fraction(0.5, 1.0, 2.0) == 1.0
    assert clmath.value0_fraction(3.0, 1.0, 2.0) == 0.0
    mid = clmath.value0_fraction(1.0, 1 / 1.1, 1.1)
    assert mid == pytest.approx(0.5, abs=1e-9)  # symmetric range in log space -> 50/50 by value


@pytest.mark.parametrize("bal0,bal1,target", [(10.0, 0.0, 0.5), (0.0, 1000.0, 0.3), (1.0, 50.0, 0.8)])
def test_swap_to_ratio_hits_target(bal0, bal1, target):
    price, fee = 100.0, 0.003
    direction, amt = clmath.swap_to_ratio(bal0, bal1, price, target, fee)
    if direction == 0:
        b0, b1 = bal0 - amt, bal1 + amt * price * (1 - fee)
    else:
        b0, b1 = bal0 + amt / price * (1 - fee), bal1 - amt
    assert b0 * price / (b0 * price + b1) == pytest.approx(target, abs=1e-9)


def test_impermanent_loss_zero_at_entry_and_negative_after_move():
    assert clmath.impermanent_loss_vs_hold(1.0, 1.0, 0.9, 1.1) == pytest.approx(0.0)
    assert clmath.impermanent_loss_vs_hold(1.0, 1.08, 0.9, 1.1) < 0
    assert clmath.impermanent_loss_vs_hold(1.0, 0.92, 0.9, 1.1) < 0
