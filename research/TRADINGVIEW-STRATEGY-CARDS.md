# Saved TradingView strategy publications

Version: 1.0.0 (2026-11-08). Delta: first complete purpose-and-rule interpretation of this directory's strategy-labelled publications.

Every one of the 742 saved HTML publications was checked for its native script type. Exactly 21 are marked `strategy`; the other 666 studies and 55 libraries are outside this interpretation pass. Full author descriptions for all 21 were read (92,770 raw Unicode characters).

The type label is a platform execution category, not proof of a trading hypothesis. Nine cards describe directional/trading models; the others explain sizing, exits, execution shells, reporting or evaluation. Thirteen retain the existing canonical card identities; eight companion tool cards stay outside the executable strategy loader.

Each card explains the idea, objective, mechanism, documented rules, disclosed settings, failure modes and missing information. The saved script source fields are empty, including publications labelled open-source. No unrecorded formula, default, profitable result or live implementation is inferred. Short author descriptions remain explicit gaps.

## Publication-to-card index

| Publication | Classification | Idea and objective |
| --- | --- | --- |
| [Ultimate Strategy Template](tradingview-strategy-tools/tv_2lgyzykc_ultimate_strategy_template.md) | strategy-template | Separate a trading signal from its execution and risk-management shell, so different indicators can be evaluated through the same strategy template. |
| [inwCoin Martingale Strategy ( for Bitcoin )](../backtester/strategy_cards/tv_8os1nbr8_inwcoin_martingale_strategy_for_bitcoin.md) | trading-strategy | Demonstrate how long-only averaging down can produce repeated recoveries while accumulating a ruinous tail exposure; the author presents it as a martingale failure experiment. |
| [How to use Leverage and Margin in PineScript](tradingview-strategy-tools/tv_9iwinz7i_how_to_use_leverage_and_margin_in_pinescript.md) | leverage-example | Explain how the publication configures notional exposure and simulated margin constraints; it supplies no forecasting or entry edge. |
| [Stop loss and Take Profit in $$ example](tradingview-strategy-tools/tv_ihvpg6ts_stop_loss_and_take_profit_in_example.md) | exit-example | Illustrate expressing stop-loss and take-profit amounts in the traded symbol's currency, rather than establish a trading signal. |
| [Oscillator Evaluator (Analysis tool)](tradingview-strategy-tools/tv_m9taaikp_oscillator_evaluator_analysis_tool.md) | evaluation-tool | Compare how different oscillators behave under several common signal interpretations, holding the evaluation framework conceptually constant. |
| [3Commas Bot](../backtester/strategy_cards/tv_mvlwazsg_3commas_bot.md) | execution-template-with-demo | Provide a modifiable trading and alert-execution shell with predefined risk controls, using a moving-average crossover as the initial demonstration signal. |
| [Trading Report Generator from CSV](tradingview-strategy-tools/tv_otfw8b2a_trading_report_generator_from_csv.md) | reporting-tool | Reconstruct a strategy-tester performance report from an existing transaction log; it evaluates executed decisions rather than generate new ones. |
| [TASC 2026.08 An Ag Selling Model](../backtester/strategy_cards/tv_vfzck3hx_tasc_2026_08_an_ag_selling_model.md) | trading-strategy | Help an agricultural producer obtain an above-average selling price by staging short futures sales into seasonal strength, then covering at harvest. |
| [Grover Llorens Activator Strategy Analysis](../backtester/strategy_cards/tv_vuym89tw_grover_llorens_activator_strategy_analysis.md) | trading-strategy | Test whether a price-converging trailing activator can identify reversals early enough to trade trends, while examining the false reversals created by that same convergence. |
| [Built-in Kelly ratio for dynamic position sizing](../backtester/strategy_cards/tv_bfxf4ixh_built_in_kelly_ratio_for_dynamic_position_sizing.md) | sizing-overlay | Demonstrate adapting position size from the strategy's own completed-trade performance using a Kelly ratio, with a Keltner-channel strategy as the host. |
| [Gap Filling Strategy ](../backtester/strategy_cards/tv_ghocsiv7_gap_filling_strategy.md) | trading-strategy | Trade the return to a significant opening gap's prior reference level, while offering an inverted mode that instead trades gap continuation. |
| [Сalculation a position size based on risk](../backtester/strategy_cards/tv_hocpm5uy_alculation_a_position_size_based_on_risk.md) | sizing-example | Show how a chosen risk budget and stop-loss distance can determine position size; it is a risk overlay rather than a market forecast. |
| [LUBE](../backtester/strategy_cards/tv_i9tjotjl_lube.md) | trading-strategy | Look for price entering a recently under-visited zone where it may move with less congestion, then trade the near-term trend until congestion returns. |
| [Stepped trailing strategy example](../backtester/strategy_cards/tv_jjhuhcje_stepped_trailing_strategy_example.md) | exit-example | Protect progressively more of a favorable move by advancing a stop at three profit milestones, without defining the entry signal. |
| [Monthly Returns in PineScript Strategies](tradingview-strategy-tools/tv_kzp8e4x3_monthly_returns_in_pinescript_strategies.md) | reporting-tool | Add monthly and yearly return tables to an existing strategy so a trader can inspect when its performance changes. |
| [TrendMaster Pro 2.3 with Alerts](../backtester/strategy_cards/tv_mvkdf8qh_trendmaster_pro_2_3_with_alerts.md) | trading-strategy | Trade moving-average trend changes only when configurable momentum, trend-strength, volatility and session constraints also agree, with a defined risk budget. |
| [Template Trailing Strategy (Backtester)](tradingview-strategy-tools/tv_n8bgynwl_template_trailing_strategy_backtester.md) | strategy-template | Keep the trading hypothesis separate from order handling, position sizing and event alerts, so the same signal can be tested with different execution mechanics. |
| [TASC 2026.03 One Percent A Week](../backtester/strategy_cards/tv_nvecqiqx_tasc_2026_03_one_percent_a_week.md) | trading-strategy | Seek a small weekly snapback in TQQQ after a dip from Monday's open, with limited trade frequency and a Friday deadline. |
| [Grid Like Strategy](../backtester/strategy_cards/tv_oxvr5vmy_grid_like_strategy.md) | trading-strategy | Use a symmetric step-through-price process to demonstrate the apparent recovery benefits and real capital/friction problems of martingale and anti-martingale sizing. |
| [Bjorgum Double Tap](../backtester/strategy_cards/tv_rlkjr2sq_bjorgum_double_tap.md) | trading-strategy | Recognize a failed retest of a high or low, then trade the neckline breakout as a double-top or double-bottom reversal/breakout pattern. |
| [How To Set Backtest Time Ranges](tradingview-strategy-tools/tv_xaeg4zjg_how_to_set_backtest_time_ranges.md) | backtest-utility | Restrict an existing strategy's experiment to chosen time/date windows, including entry and exit eligibility, without supplying its trading hypothesis. |

## How to read the cards

`Documented rules` reports what the author actually disclosed. Failure modes and missing-information sections add our interpretation and implementation concerns. In particular, a break-even limit is not a loss cap; an indicator does not define an order policy; a sizing overlay does not create an entry edge; a reporting script replays or summarizes other decisions.

Article settings, screenshot examples and complete defaults are distinguished. The one-percent position target in the TQQQ card is not a one-percent account-return guarantee. The sequential reversing grid is not the repository's simultaneous resting-order ladder.

## Provenance and validation

The manifest `research/tradingview-strategy-understanding.json` records the entire 742-page metadata inventory, all 21 card paths/hashes, full-description read status, source/description hashes and 55 exact raw-description passages with Unicode-codepoint offsets. Raw captures remain outside Git.

```bash
python3 scripts/check_tradingview_strategy_profiles.py
python3 scripts/check_tradingview_strategy_profiles.py --source-root /Users/mitch/dev/solmargintrader/tradingview/www.tradingview.com/www.tradingview.com/script
python3 -m unittest backtester.tests.test_strategy_cards
```

The first command checks the committed artifacts offline. The second also verifies every original HTML hash, native type, strategy subset and cited passage against the local capture. Neither command executes Pine, places orders, or measures profitability.
