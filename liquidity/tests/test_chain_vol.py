import math
import random

from aero_lp import clmath
from aero_lp.chain import realized_vol_daily


def _window_average_ticks(sigma_daily: float, n: int, step_s: int, sub: int = 30) -> list[float]:
    """Per-window average tick of a driftless Brownian log-price, as the pool oracle reports it."""
    rng = random.Random(7)
    sd = sigma_daily * math.sqrt(step_s / 86400 / sub)
    x, out = 0.0, []
    for _ in range(n):
        acc = 0.0
        for _ in range(sub):
            x += rng.gauss(0, sd)
            acc += x
        out.append(acc / sub / clmath.LOG_BASE)
    return out


def test_twap_window_vol_is_unbiased():
    # Differencing window averages smooths the path (raw estimate ~0.82x sigma); the estimator corrects that.
    est = realized_vol_daily(_window_average_ticks(0.04, 2500, 600), step_s=600)
    assert est is not None and abs(est / 0.04 - 1) < 0.06


def test_vol_needs_enough_points():
    assert realized_vol_daily([0.0] * 5) is None


def test_twap_series_spans_the_requested_hours_not_a_window_count():
    from types import SimpleNamespace

    from aero_lp.chain import AeroChain

    seen = {}

    def observe(agos):
        seen["agos"] = agos
        return SimpleNamespace(call=lambda: ([0] * len(agos), []))

    chain = AeroChain.__new__(AeroChain)
    chain._c = lambda a, b: SimpleNamespace(functions=SimpleNamespace(observe=observe))
    chain.twap_tick_series("0x" + "11" * 20, hours=12, step_s=600)
    assert max(seen["agos"]) == 12 * 3600 and len(seen["agos"]) == 73
