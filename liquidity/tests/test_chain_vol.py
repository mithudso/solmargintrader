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


def test_latest_balance_reads_are_pinned_to_a_block_no_older_than_our_last_transaction(monkeypatch):
    from types import SimpleNamespace

    from aero_lp import chain as chain_mod
    from aero_lp.chain import AeroChain

    monkeypatch.setattr(chain_mod, "MIN_BLOCK_READ_DELAY_S", 0)
    c = object.__new__(AeroChain)
    c.min_block = 120
    c.w3 = SimpleNamespace(eth=SimpleNamespace(block_number=118))  # the node answering is behind our receipt
    c._c = lambda address, contract_abi: SimpleNamespace(abi=contract_abi, address=address)
    asked = []

    def multicall(calls, block="latest"):
        asked.append(block)
        if len(asked) < 3:
            raise ValueError("header not found")  # the node has not imported block 120 yet
        return [5 for _ in calls]

    c.multicall = multicall
    owner = "0x" + "ab" * 20
    token = "0x4200000000000000000000000000000000000006"
    assert c.erc20_balances(owner, [token]) == [5]
    assert asked == [120, 120, 120]  # never "latest", never a block before ours
    asked.clear()
    c.w3.eth.block_number = 130
    c.multicall = lambda calls, block="latest": (asked.append(block), [7])[1]
    assert c.erc20_balances(owner, [token]) == [7] and asked == [130]
    asked.clear()
    c.min_block = None  # nothing mined by this process: plain "latest", unchanged behaviour
    assert c.erc20_balances(owner, [token]) == [7] and asked == ["latest"]
    c.min_block = 120
    assert c.erc20_balances(owner, [token], block=99) == [7] and asked[-1] == 99  # explicit blocks are respected
