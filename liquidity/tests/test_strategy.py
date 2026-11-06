import math

import pytest

from aero_lp import strategy as st
from aero_lp.strategy import Action, CostInputs, EarnInputs, Range, StrategyConfig


def cost(**kw):
    base = dict(value_usd=1000.0, pool_fee=0.0005, gas_usd=0.1, swap_fraction=0.5)
    base.update(kw)
    return CostInputs(**base)


def decide(tick, current, *, cfg=None, earn=None, c=None, edge_checks=0, since=None, sigma=0.02, hw=None):
    return st.decide(
        tick=tick,
        current=current,
        spacing=100,
        sigma_daily=sigma,
        cfg=cfg or StrategyConfig(lvr_weight=0.0),
        cost=c or cost(),
        earn=earn or EarnInputs(earn_usd_per_day_new=5.0, earn_usd_per_day_current=0.0),
        consecutive_edge_checks=edge_checks,
        minutes_since_last_rebalance=since,
        half_width=hw,
    )


@pytest.mark.parametrize("tick", [-199211, -199200, 0, 57, -1])
@pytest.mark.parametrize("spacing", [1, 50, 100, 200])
def test_target_range_contains_tick_and_is_snapped(tick, spacing):
    r = st.target_range(tick, spacing, math.log1p(0.05))
    assert r.contains(tick)
    assert r.tick_lower % spacing == 0 and r.tick_upper % spacing == 0
    assert r.width_ticks >= spacing


def test_target_range_minimum_width():
    r = st.target_range(1234, 100, 1e-9)
    assert r.contains(1234) and r.width_ticks >= 100


def test_hold_when_centered():
    d = decide(0, Range(-1000, 1000))
    assert d.action == Action.HOLD


def test_rebalance_when_out_of_range_and_profitable():
    d = decide(1500, Range(-1000, 1000))
    assert d.action == Action.REBALANCE
    assert d.new_range is not None and d.new_range.contains(1500)


def test_cooldown_blocks():
    d = decide(1500, Range(-1000, 1000), since=5)
    assert d.action == Action.WAIT_COOLDOWN


def test_edge_needs_confirmation():
    cfg = StrategyConfig(lvr_weight=0.0, confirm_checks=2, edge_buffer=0.1)
    first = decide(950, Range(-1000, 1000), cfg=cfg, edge_checks=0)
    assert first.action == Action.WAIT_CONFIRM
    second = decide(950, Range(-1000, 1000), cfg=cfg, edge_checks=1)
    assert second.action == Action.REBALANCE


def test_unprofitable_when_costs_dominate():
    d = decide(
        1500,
        Range(-1000, 1000),
        earn=EarnInputs(earn_usd_per_day_new=0.01, earn_usd_per_day_current=0.0),
        c=cost(gas_usd=5.0),
    )
    assert d.action == Action.SKIP_UNPROFITABLE


def test_waits_out_gauge_penalty_when_cheaper():
    c = cost(unclaimed_aero_usd=50.0, penalty_rate=1.0, penalty_blocks_left=70)
    d = decide(1500, Range(-1000, 1000), c=c)
    assert d.action == Action.WAIT_PENALTY


def test_pays_penalty_when_waiting_costs_more():
    c = cost(unclaimed_aero_usd=0.01, penalty_rate=1.0, penalty_blocks_left=40_000)
    d = decide(1500, Range(-1000, 1000), c=c, earn=EarnInputs(earn_usd_per_day_new=50.0, earn_usd_per_day_current=0.0))
    assert d.action == Action.REBALANCE


def test_lvr_blocks_reentry_unless_disabled():
    earn = EarnInputs(earn_usd_per_day_new=1.0, earn_usd_per_day_current=0.0, lvr_usd_per_day_new=3.0)
    d = decide(1500, Range(-1000, 1000), cfg=StrategyConfig(lvr_weight=1.0), earn=earn)
    assert d.action == Action.SKIP_UNPROFITABLE and "LVR" in d.reason
    d0 = decide(1500, Range(-1000, 1000), cfg=StrategyConfig(lvr_weight=0.0), earn=earn)
    assert d0.action == Action.REBALANCE


def test_lvr_formula_limits():
    sigma = 0.03
    # very wide range -> v2 result sigma^2 / 8
    assert st.lvr_fraction_per_day(50.0, sigma) == pytest.approx(sigma**2 / 8, rel=1e-6)
    # narrower range -> more LVR per dollar
    assert st.lvr_fraction_per_day(0.01, sigma) > st.lvr_fraction_per_day(0.1, sigma)
    assert st.lvr_fraction_per_day(0.1, None) == 0.0


def test_best_width_prefers_narrow_when_edge_positive_and_wide_when_negative():
    cfg = StrategyConfig(min_half_width_pct=1, max_half_width_pct=40)
    sigma = 0.02
    v2_lvr = sigma**2 / 8

    def rich(w):  # income per unit liquidity far above LVR
        return 20 * v2_lvr / (1 - math.exp(-w / 2))

    def poor(w):  # income below LVR at every width
        return 0.5 * v2_lvr / (1 - math.exp(-w / 2))

    narrow = st.best_width(st.score_widths(rich, sigma, 0.0005, cfg))
    wide = st.best_width(st.score_widths(poor, sigma, 0.0005, cfg))
    assert narrow.half_width < wide.half_width
    assert narrow.net_frac_day > 0 > wide.net_frac_day
    assert wide.half_width == pytest.approx(math.log1p(0.40))


def test_in_range_probability_monotonic_in_width():
    p_narrow = st.in_range_probability(0.01, 0.03, 3)
    p_wide = st.in_range_probability(0.2, 0.03, 3)
    assert 0 <= p_narrow < p_wide <= 1


def test_config_validation():
    with pytest.raises(ValueError):
        StrategyConfig(width_mode="nope")
    with pytest.raises(ValueError):
        StrategyConfig(edge_buffer=0.6)
    with pytest.raises(ValueError):
        StrategyConfig(lvr_weight=-1)


def test_config_rejects_values_that_crash_or_disable_the_model():
    for bad in ({"horizon_days": 0}, {"vol_k": 0}, {"cooldown_minutes": -1}, {"benefit_cost_ratio": -1}):
        with pytest.raises(ValueError):
            StrategyConfig(**bad)
