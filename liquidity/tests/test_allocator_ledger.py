import time

import pytest

from aero_lp.allocator import gas_topup_needed, plan_allocation, plan_graduation, qualify
from aero_lp.config import AllocatorConfig
from aero_lp.ledger import Ledger

WETH = "0x4200000000000000000000000000000000000006"
WSTETH = "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452"
CBETH = "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
SCAM = "0x000000000000000000000000000000000000dead"


def row(pool, t0, t1, model, bt, edge=3.0, conf="high", tvl=1e6, pair="A/B"):
    return {
        "pool": pool,
        "pair": pair,
        "token0": t0,
        "token1": t1,
        "tick_spacing": 1,
        "expected_net_apr": model,
        "backtest_net_apr": bt,
        "edge_ratio": edge,
        "backtest_days": 7.0,
        "confidence": conf,
        "tvl_usd": tvl,
        "best_mode": "aero",
        "best_half_width_pct": 0.1,
    }


def test_both_estimates_must_clear_threshold():
    cfg = AllocatorConfig(min_net_apr=5)
    pools = [
        row("0x1", WETH, WSTETH, 12, 3, pair="model-only"),
        row("0x2", WETH, CBETH, 2, 20, pair="backtest-only"),
        row("0x3", WETH, USDC, 9, 8, pair="both"),
    ]
    cands, rejects = qualify(pools, cfg)
    assert [c.pair for c in cands] == ["both"]
    assert cands[0].score_apr == 8  # the smaller of the two
    assert any("backtest +3.0%" in r for r in rejects) and any("model +2.0%" in r for r in rejects)


@pytest.mark.parametrize(
    "override, needle",
    [
        ({"t1": SCAM}, "token not allowed"),
        ({"conf": "low"}, "confidence"),
        ({"tvl": 5e3}, "TVL"),
        ({"edge": 0.5}, "edge"),
    ],
)
def test_filters_reject_risky_pools(override, needle):
    args = dict(t0=WETH, t1=WSTETH, conf="high", tvl=1e6, edge=3.0)
    args.update(override)
    cands, rejects = qualify(
        [row("0x1", args["t0"], args["t1"], 20, 20, edge=args["edge"], conf=args["conf"], tvl=args["tvl"])],
        AllocatorConfig(),
    )
    assert not cands and needle in rejects[0]


def test_single_clear_winner_gets_everything_capped_per_position():
    cfg = AllocatorConfig(max_position_usd=50, max_total_deployed_usd=500)
    pools = [row("0x1", WETH, WSTETH, 30, 30, pair="best"), row("0x2", WETH, CBETH, 10, 10, pair="far")]
    plan = plan_allocation(pools, idle_usd=80, deployed_usd=0, cfg=cfg)
    assert not plan.experiment and len(plan.arms) == 1
    assert plan.arms[0].candidate.pair == "best" and plan.arms[0].usd == 50


def test_close_candidates_become_side_by_side_experiment():
    cfg = AllocatorConfig(compare_margin=0.3, max_arms=3, min_position_usd=10)
    pools = [
        row("0x1", WETH, WSTETH, 20, 20, pair="a"),
        row("0x2", WETH, CBETH, 16, 17, pair="b"),
        row("0x3", WETH, USDC, 15, 30, pair="c"),
        row("0x4", USDC, CBETH, 6, 6, pair="too-far"),
    ]
    plan = plan_allocation(pools, idle_usd=45, deployed_usd=0, cfg=cfg)
    assert plan.experiment and [a.candidate.pair for a in plan.arms] == ["a", "b", "c"]
    assert all(a.usd == pytest.approx(15) for a in plan.arms)


def test_experiment_shrinks_to_what_the_budget_can_fund():
    cfg = AllocatorConfig(compare_margin=0.5, min_position_usd=10)
    pools = [
        row("0x1", WETH, WSTETH, 20, 20, pair="a"),
        row("0x2", WETH, CBETH, 19, 19, pair="b"),
        row("0x3", WETH, USDC, 18, 18, pair="c"),
    ]
    plan = plan_allocation(pools, idle_usd=25, deployed_usd=0, cfg=cfg)
    assert len(plan.arms) == 2 and plan.arms[0].usd == pytest.approx(12.5)


def test_nothing_deployed_below_minimum_or_over_total_cap_or_without_candidates():
    cfg = AllocatorConfig(min_position_usd=10, max_total_deployed_usd=100)
    good = [row("0x1", WETH, WSTETH, 20, 20)]
    assert not plan_allocation(good, 5, 0, cfg).arms
    assert not plan_allocation(good, 50, 95, cfg).arms  # only $5 left under the cap
    plan = plan_allocation([row("0x1", WETH, WSTETH, -3, -2, edge=0.2)], 50, 0, cfg)
    assert not plan.arms and "no pool worth it" in plan.reason


def test_pool_already_held_is_skipped():
    plan = plan_allocation([row("0xAbC", WETH, WSTETH, 20, 20)], 50, 0, AllocatorConfig(), held_pools={"0xabc"})
    assert not plan.arms


def test_gas_reserve_unwrap():
    cfg = AllocatorConfig(gas_reserve_eth=0.0003, unwrap_chunk_eth=0.0005)
    assert gas_topup_needed(0.001, 1.0, cfg) == 0
    assert gas_topup_needed(0.0001, 1.0, cfg) == 0.0005
    assert gas_topup_needed(0.0001, 0.0002, cfg) == 0.0002  # cannot unwrap more than held


def _ledger(tmp_path):
    return Ledger(tmp_path / "ledger.sqlite")


def test_ledger_pnl_counts_rewards_once_through_compounding(tmp_path):
    lg = _ledger(tmp_path)
    t0 = time.time() - 10 * 86400
    lg.open_slot("1", "0xp", "WETH/wstETH", WETH, WSTETH, 18, 18, 1, ts=t0)
    lg.flow("1", "deposit", 0.01, 0.01, 40.0, ts=t0)
    lg.event("claim", "1", gas_usd=0.01, reward_usd=2.0)  # AERO claimed...
    lg.flow("1", "topup", 0.0005, 0.0004, 2.0)  # ...and compounded back in
    lg.snapshot("1", 1, value_usd=42.5, hodl_usd=41.0)
    p = lg.pnl("1")
    assert p.deposited_usd == 42 and p.rewards_usd == 2 and p.gas_usd == pytest.approx(0.01)
    assert p.pnl_usd == pytest.approx(42.5 + 2 - 42 - 0.01)
    assert p.pnl_vs_hodl_usd == pytest.approx(42.5 + 2 - 41 - 0.01)
    assert p.apr_realized == pytest.approx(p.pnl_usd / 42 * 365 / 10 * 100, rel=1e-3)
    assert lg.deposited_amounts("1") == pytest.approx((0.0105, 0.0104))


def test_ledger_closed_slot_counts_withdrawal_not_value(tmp_path):
    lg = _ledger(tmp_path)
    lg.open_slot("2", "0xp", "A/B", WETH, USDC, 18, 6, 2)
    lg.flow("2", "deposit", 1, 1, 100.0)
    lg.snapshot("2", 2, 101.0, 100.5)
    lg.flow("2", "withdraw", 1, 1, 101.0)
    lg.close_slot("2")
    p = lg.pnl("2")
    assert p.value_usd == 0 and p.pnl_usd == pytest.approx(1.0)
    assert [r["slot"] for r in lg.open_slots()] == []


def _sample(lg, token, start_h_ago, end_h_ago, amount, now, every_min=10):
    """Wallet samples every `every_min` minutes between two points in the past."""
    t = now - start_h_ago * 3600
    while t <= now - end_h_ago * 3600:
        lg.wallet_snapshot({token: amount}, ts=t)
        t += every_min * 60


def test_idle_amount_requires_full_window_and_takes_minimum(tmp_path):
    lg = _ledger(tmp_path)
    now = time.time()
    assert lg.idle_amount(WETH, 1.0, 86400, now) == 0  # no history yet: not proven idle
    _sample(lg, WETH, 30, 10.01, 1.0, now)
    _sample(lg, WETH, 10, 1.01, 0.4, now)  # owner used some
    _sample(lg, WETH, 1, 0, 1.5, now)  # owner just received more
    assert lg.idle_amount(WETH, 1.5, 86400, now) == pytest.approx(0.4)
    assert lg.idle_amount(WETH, 0.2, 86400, now) == pytest.approx(0.2)  # never more than held now


def test_idle_amount_counts_the_balance_that_was_in_force_when_the_window_began(tmp_path):
    lg = _ledger(tmp_path)
    now = time.time()
    _sample(lg, WETH, 25, 24.2, 0.3, now)  # the last sample before the window says 0.3
    _sample(lg, WETH, 23.9, 0, 1.0, now)
    assert lg.idle_amount(WETH, 1.0, 86400, now) == pytest.approx(0.3)


def test_a_gap_in_the_samples_means_not_proven_idle(tmp_path):
    lg = _ledger(tmp_path)
    now = time.time()
    # the daemon was down from 20 h ago until 5 minutes ago; a coin could have come and gone, or arrived, meanwhile
    _sample(lg, WETH, 40, 20, 1.0, now)
    lg.wallet_snapshot({WETH: 1.0}, ts=now - 300)
    assert lg.idle_amount(WETH, 1.0, 86400, now) == 0.0
    # the same history without the outage is idle
    lg2 = Ledger(tmp_path / "other.sqlite")
    _sample(lg2, WETH, 40, 0, 1.0, now)
    assert lg2.idle_amount(WETH, 1.0, 86400, now) == pytest.approx(1.0)
    # sampling that stopped an hour and a half ago is not current either
    lg3 = Ledger(tmp_path / "third.sqlite")
    _sample(lg3, WETH, 40, 1.5, 1.0, now)
    assert lg3.idle_amount(WETH, 1.0, 86400, now) == 0.0


def test_graduation_waits_then_closes_clear_losers_only(tmp_path):
    lg = _ledger(tmp_path)
    cfg = AllocatorConfig(experiment_days=7, graduate_margin_apr=5)
    start = time.time() - 8 * 86400
    lg.start_experiment("e1", ts=start)
    for slot, val in (("a", 41.0), ("b", 40.1), ("c", 40.0)):
        lg.open_slot(slot, "0x" + slot, slot, WETH, WSTETH, 18, 18, 1, experiment="e1", ts=start)
        lg.flow(slot, "deposit", 1, 1, 40.0, ts=start)
        lg.snapshot(slot, 1, val, 40.0)
    exp = lg.experiments()[0]
    arms = [lg.pnl(s) for s in exp["arms"]]
    winner, losers = plan_graduation(exp, arms, cfg)
    assert winner == "a" and set(losers) == {"b", "c"}  # a: ~+11%/yr; b ~+1%, c 0%
    early = dict(exp, started_at=time.time() - 86400)
    assert plan_graduation(early, arms, cfg) == (None, [])


# ---------------------------------------------------------------- numeric edge cases and config validation


@pytest.mark.parametrize(
    "field, bad",
    [
        ("expected_net_apr", float("nan")),
        ("backtest_net_apr", float("nan")),
        ("expected_net_apr", float("inf")),
        ("backtest_net_apr", float("inf")),
        ("edge_ratio", float("nan")),
        ("edge_ratio", float("inf")),
        ("tvl_usd", float("nan")),
        ("tvl_usd", float("inf")),
        ("expected_net_apr", None),
        ("backtest_net_apr", "12"),
    ],
)
def test_non_finite_or_malformed_numbers_never_qualify(field, bad):
    p = row("0x1", WETH, WSTETH, 20, 20)
    p[field] = bad
    cands, rejects = qualify([p], AllocatorConfig())
    assert cands == [] and rejects  # a NaN passes every plain `x < floor` test; it must not pass this one


def test_a_pool_with_no_price_history_to_replay_never_qualifies_even_at_a_zero_threshold():
    p = row("0x1", WETH, WSTETH, 20, 0.0)
    p["backtest_days"] = 0.0  # metrics.backtest_best reports "no replay" as days == 0, not as a 0% APR
    cfg = AllocatorConfig(min_net_apr=0)
    cands, rejects = qualify([p], cfg)
    assert cands == [] and "no price history" in rejects[0]
    del p["backtest_days"]
    assert qualify([p], cfg)[0] == []


def test_nan_idle_budget_deploys_nothing():
    plan = plan_allocation([row("0x1", WETH, WSTETH, 20, 20)], float("nan"), 0, AllocatorConfig())
    assert plan.arms == []
    assert plan_allocation([row("0x1", WETH, WSTETH, 20, 20)], 50, float("nan"), AllocatorConfig()).arms == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_net_apr": float("nan")},
        {"idle_window_hours": float("inf")},
        {"graduate_margin_apr": -1},  # would close every arm, near-ties included
        {"experiment_days": -1},
        {"max_total_deployed_usd": -1},
        {"idle_window_hours": -1},
        {"compound_interval_h": 0},
        {"allocate_interval_h": -1},
        {"scout_interval_h": 0},
        {"snapshot_interval_min": 0},
        {"compound_gas_multiple": -1},
        {"gas_reserve_eth": -0.1},
    ],
)
def test_allocator_config_rejects_values_that_would_act_unsafely(kwargs):
    with pytest.raises(ValueError):
        AllocatorConfig(**kwargs)


def test_default_and_example_allocator_config_are_valid():
    cfg = AllocatorConfig()
    assert cfg.min_net_apr == 5 and cfg.idle_window_hours == 24


def test_pnl_of_a_fresh_slot_without_a_snapshot_is_flat_not_a_total_loss(tmp_path):
    lg = _ledger(tmp_path)
    lg.open_slot("3", "0xp", "A/B", WETH, USDC, 18, 6, 3)
    lg.flow("3", "deposit", 1, 1, 40.0)
    p = lg.pnl("3")
    assert p.value_usd == 40.0 and p.pnl_usd == pytest.approx(0.0)
    lg.flow("3", "withdraw", 0.5, 0.5, 15.0)  # partly withdrawn, still open, no snapshot yet
    assert lg.pnl("3").value_usd == pytest.approx(25.0)


def test_arm_count_shrinks_before_positions_fall_below_the_scored_size():
    cfg = AllocatorConfig(compare_margin=0.5, min_position_usd=10, max_arms=3)
    pools = [row("0x1", WETH, WSTETH, 20, 20, pair="a"), row("0x2", WETH, CBETH, 19, 19, pair="b")]
    free = plan_allocation(pools, idle_usd=40, deployed_usd=0, cfg=cfg)
    assert len(free.arms) == 2 and free.arms[0].usd == pytest.approx(20)
    sized = plan_allocation(pools, idle_usd=40, deployed_usd=0, cfg=cfg, scored_usd=35)
    assert len(sized.arms) == 1 and sized.arms[0].usd == pytest.approx(40)  # one arm of $40, not two of $20
    none = plan_allocation(pools, idle_usd=20, deployed_usd=0, cfg=cfg, scored_usd=35)
    assert none.arms == [] and "scored at" in none.reason
    assert plan_allocation(pools, 20, 0, cfg, scored_usd=float("nan")).arms  # a bad value does not block


def test_qualify_gates_on_the_replay_at_the_deployed_width_when_the_scout_has_it():
    p = row("0x1", WETH, WSTETH, 20, 20)
    p["backtest_deploy_apr"] = 2.0  # the best grid width looks fine; the width we would deploy does not
    cands, rejects = qualify([p], AllocatorConfig(min_net_apr=5))
    assert cands == [] and "backtest +2.0%" in rejects[0]
    p["backtest_deploy_apr"] = 9.0
    [c] = qualify([p], AllocatorConfig(min_net_apr=5))[0]
    assert c.backtest_apr == 9.0 and c.score_apr == 9.0
