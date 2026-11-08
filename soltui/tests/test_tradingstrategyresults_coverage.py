"""Every strategy and indicator in `tradingstrategyresults.json` is represented in soltui.

That file is a catalogue of strategies and indicators from public trading guides. The
question this test answers is the one the catalogue raises: for each name, is there a
strategy card, and is it where soltui can use it?

A name is covered when:
  * a strategy card exists for it, AND
  * if the card is buildable, the strategy is in the registry, tunable on the Signals
    tab (`STRATEGY_PARAM_MAP`), constructible from the Signals defaults, and present in
    the background queue; or
  * if the card is spec-only, it is NOT queued (a queued spec-only card is an
    identical error row per job) and it lists the data it needs.

The map below is the contract. If the catalogue file is present in the repo root, the
test also checks the map against its names, so a new entry in the catalogue fails here
until someone maps it.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from backtester.core.strategies import REGISTRY, build
from backtester.core.strategy_cards import load_all
from soltui import bgqueue, reference, signals

REPO = Path(__file__).resolve().parent.parent.parent
CATALOGUE = REPO / "tradingstrategyresults.json"

# catalogue name -> card ids that represent it (any one is enough; all listed must exist).
STRATEGIES = {
    "HODLing": ["buy_and_hold"],
    "Dollar-cost averaging (DCA)": ["dca"],
    "Day trading": ["day_trading"],
    "Swing trading": ["swing_confluence"],
    "Trend trading": ["ma_crossover", "ema_crossover"],
    "Scalping": ["scalping"],
    "Arbitrage": ["triangular_arbitrage", "dex_cex_dislocation"],
    "Event-driven trading": ["event_driven"],
}
# Not in the catalogue file: added by the owner's request as another item to consider.
EXTRA_CARDS = ["prediction_markets"]
INDICATORS = {
    "Simple moving average (SMA)": ["ma_crossover", "sma_regime"],
    "Exponential moving average (EMA)": ["ema_crossover"],
    "Moving-average crossover / golden cross": ["ma_crossover", "ema_crossover"],
    "Relative Strength Index (RSI)": ["rsi"],
    "Moving Average Convergence Divergence (MACD)": ["macd"],
    "Bollinger Bands": ["bb_reversion", "bb_breakout"],
    "Stochastic oscillator": ["stochastic"],
    "On-Balance Volume (OBV)": ["obv_trend"],
    "Fibonacci retracement": ["fib_retracement"],
    "Average True Range (ATR)": ["atr_position_sizing"],
    "Percentage Price Oscillator (PPO)": ["ppo"],
    "Ichimoku Cloud": ["ichimoku_cloud"],
    "VWAP": ["vwap_reversion"],
}
# catalogue indicator -> prefix of the label it carries on the soltui Signals reference table.
REFERENCE_LABEL = {
    "Simple moving average (SMA)": "SMA",
    "Exponential moving average (EMA)": "EMA",
    "Relative Strength Index (RSI)": "RSI",
    "Moving Average Convergence Divergence (MACD)": "MACD",
    "Bollinger Bands": "Bollinger",
    "Stochastic oscillator": "Stochastic",
    "On-Balance Volume (OBV)": "OBV",
    "Fibonacci retracement": "Fibonacci",
    "Average True Range (ATR)": "ATR",
    "Percentage Price Oscillator (PPO)": "PPO",
    "Ichimoku Cloud": "Ichimoku",
    "VWAP": "VWAP",
}


def _all_card_ids() -> list[str]:
    ids: list[str] = []
    for table in (STRATEGIES, INDICATORS):
        for cards in table.values():
            ids.extend(cards)
    return sorted(set(ids) | set(EXTRA_CARDS))


class TestCatalogueCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards = load_all()
        cls.queued = {j.strategy for j in bgqueue.build_queue("SOL", max_tier=0)}

    def test_every_catalogue_name_has_a_card(self) -> None:
        for table in (STRATEGIES, INDICATORS):
            for name, ids in table.items():
                for cid in ids:
                    with self.subTest(name=name, card=cid):
                        self.assertIn(cid, self.cards)

    def test_every_buildable_card_is_tunable_constructible_and_queued(self) -> None:
        defaults = signals.SignalDefaults()
        for cid in _all_card_ids():
            card = self.cards[cid]
            if not card.buildable:
                continue
            key = card.registry_key
            with self.subTest(card=cid):
                self.assertIn(key, REGISTRY)
                self.assertIn(key, signals.STRATEGY_PARAM_MAP, "Signals tab would ignore it")
                build(key, **signals.merged_params(key, defaults))
                if card.data_available:
                    self.assertIn(key, self.queued, "buildable card missing from the sweep queue")

    def test_every_spec_only_card_is_kept_out_of_the_queue_and_says_what_it_needs(self) -> None:
        for cid in _all_card_ids():
            card = self.cards[cid]
            if card.status != "spec-only":
                continue
            with self.subTest(card=cid):
                self.assertNotIn(cid, self.queued)
                self.assertTrue(card.data_required, "a spec-only card must say what it needs")

    def test_new_cards_reach_every_horizon_of_the_queue(self) -> None:
        # The sweep ordering reads the cards, so a new card needs a preset per horizon
        # to be evaluated at every interval, not just the default.
        for cid in ("dca", "ema_crossover", "ppo", "fib_retracement", "swing_confluence"):
            with self.subTest(card=cid):
                jobs = [j for j in bgqueue.build_queue("SOL", max_tier=0) if j.strategy == cid]
                self.assertTrue(jobs)
                self.assertIn("1h", {j.interval for j in jobs}, "short horizon should run hourly")

    def test_every_catalogue_indicator_is_on_the_signals_reference(self) -> None:
        labels = [row[0] for row in reference.SIGNAL_REFERENCE]
        for name, prefix in REFERENCE_LABEL.items():
            with self.subTest(indicator=name):
                self.assertTrue(any(lbl.startswith(prefix) for lbl in labels), labels)

    def test_the_map_matches_the_catalogue_file_when_it_is_present(self) -> None:
        if not CATALOGUE.exists():
            self.skipTest("tradingstrategyresults.json is not in this checkout")
        data = json.loads(CATALOGUE.read_text())
        self.assertEqual({s["name"] for s in data["strategies"]}, set(STRATEGIES))
        self.assertEqual({i["name"] for i in data["indicators_and_signals"]}, set(INDICATORS))


if __name__ == "__main__":
    unittest.main()
