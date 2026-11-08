# Saved native-strategy source cards

Version: 1.2.0. Delta: distinguish source disclosure from standalone coin-test qualification.

**All21 cards are incomplete as standalone coin tests and are stored in the incomplete directory.** The historical source review below identifies10 disclosed principal calculations and11 partial descriptions; that distinction does not qualify any complete coin test.

The21 native-strategy descriptions were read in full (92,770 characters). Their accepted card contents remain unchanged. Ten disclose a principal calculation; eleven have partial computational definitions. All21 remain coin-test-incomplete. Indicator or procedure usability does not certify the entire published trading system, repository integration or profitability.

The wider742-publication task includes indicators and financial libraries; its expanded review is separate. All saved `script.content` fields are empty, so description snippets do not establish complete Pine source.

## Publication cards

| Publication | Classification | Principal-output readiness |
| --- | --- | --- |
| [Ultimate Strategy Template](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_2lgyzykc_ultimate_strategy_template.md) | strategy-template | usable-specification |
| [inwCoin Martingale Strategy ( for Bitcoin )](../backtester/strategy_cards/incomplete/tv_8os1nbr8_inwcoin_martingale_strategy_for_bitcoin.md) | trading-strategy | usable-specification |
| [How to use Leverage and Margin in PineScript](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_9iwinz7i_how_to_use_leverage_and_margin_in_pinescript.md) | leverage-example | usable-specification |
| [Stop loss and Take Profit in $$ example](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_ihvpg6ts_stop_loss_and_take_profit_in_example.md) | exit-example | incomplete |
| [Oscillator Evaluator (Analysis tool)](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_m9taaikp_oscillator_evaluator_analysis_tool.md) | evaluation-tool | usable-specification |
| [3Commas Bot](../backtester/strategy_cards/incomplete/tv_mvlwazsg_3commas_bot.md) | execution-template-with-demo | usable-specification |
| [Trading Report Generator from CSV](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_otfw8b2a_trading_report_generator_from_csv.md) | reporting-tool | usable-specification |
| [TASC 2026.08 An Ag Selling Model](../backtester/strategy_cards/incomplete/tv_vfzck3hx_tasc_2026_08_an_ag_selling_model.md) | trading-strategy | usable-specification |
| [Grover Llorens Activator Strategy Analysis](../backtester/strategy_cards/incomplete/tv_vuym89tw_grover_llorens_activator_strategy_analysis.md) | trading-strategy | incomplete |
| [Built-in Kelly ratio for dynamic position sizing](../backtester/strategy_cards/incomplete/tv_bfxf4ixh_built_in_kelly_ratio_for_dynamic_position_sizing.md) | sizing-overlay | incomplete |
| [Gap Filling Strategy ](../backtester/strategy_cards/incomplete/tv_ghocsiv7_gap_filling_strategy.md) | trading-strategy | incomplete |
| [Сalculation a position size based on risk](../backtester/strategy_cards/incomplete/tv_hocpm5uy_alculation_a_position_size_based_on_risk.md) | sizing-example | incomplete |
| [LUBE](../backtester/strategy_cards/incomplete/tv_i9tjotjl_lube.md) | trading-strategy | incomplete |
| [Stepped trailing strategy example](../backtester/strategy_cards/incomplete/tv_jjhuhcje_stepped_trailing_strategy_example.md) | exit-example | usable-specification |
| [Monthly Returns in PineScript Strategies](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_kzp8e4x3_monthly_returns_in_pinescript_strategies.md) | reporting-tool | incomplete |
| [TrendMaster Pro 2.3 with Alerts](../backtester/strategy_cards/incomplete/tv_mvkdf8qh_trendmaster_pro_2_3_with_alerts.md) | trading-strategy | incomplete |
| [Template Trailing Strategy (Backtester)](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_n8bgynwl_template_trailing_strategy_backtester.md) | strategy-template | incomplete |
| [TASC 2026.03 One Percent A Week](../backtester/strategy_cards/incomplete/tv_nvecqiqx_tasc_2026_03_one_percent_a_week.md) | trading-strategy | usable-specification |
| [Grid Like Strategy](../backtester/strategy_cards/incomplete/tv_oxvr5vmy_grid_like_strategy.md) | trading-strategy | usable-specification |
| [Bjorgum Double Tap](../backtester/strategy_cards/incomplete/tv_rlkjr2sq_bjorgum_double_tap.md) | trading-strategy | incomplete |
| [How To Set Backtest Time Ranges](../backtester/strategy_cards/incomplete/native-strategy-profiles/tv_xaeg4zjg_how_to_set_backtest_time_ranges.md) | backtest-utility | incomplete |

## Exact usability scopes and gaps

### Ultimate Strategy Template

Usable scope: the complete 10/100 SMA-default crossover connector calculation and +1/-1/0 output. The execution shell is not certified; its order/risk configuration is only listed.

### inwCoin Martingale Strategy ( for Bitcoin )

Usable scope: geometric martingale stake sizing from a supplied initial stake and losing-streak index, explicitly first stake times 2^(n-1). The averaging-down trading system is not certified: MACD/channel definitions and conflicting profit-exit prose remain unresolved.

### How to use Leverage and Margin in PineScript

Usable scope: allocation percentage multiplied by leverage to obtain notional percentage, plus the explicitly printed historical margin-parameter arithmetic. This does not certify broker liquidation behavior or current Pine semantics.

### Stop loss and Take Profit in $$ example

The sole sentence states an educational currency-denominated exit purpose without its principal computation.

- No conversion from currency amount to stop/target price or position quantity is defined.

### Oscillator Evaluator (Analysis tool)

Usable scope: mode 3 maps a supplied oscillator crossing above zero to long and crossing below zero to short. It is an independently specified signal mode; the other five modes and performance accounting are not certified.

### 3Commas Bot

Usable scope: directional MA-cross signal using user-selected MA types and lengths, upward for long and downward for short. It is the explicit primary signal; stop-anchor, sizing and trailing-order parity are not certified.

### Trading Report Generator from CSV

Usable scope: parse the stated CSV trade fields, chronologically sort, select the chart instrument and map next-bar transactions to limit orders at logged fill prices. This is a disclosed replay procedure, not certified realized-P&L accounting or broker execution.

### TASC 2026.08 An Ag Selling Model

Usable scope: agricultural selling level from a source SMA plus a user-supplied factor times ATR, with lengths and factor supplied as parameters. Exact harvest-day execution and futures contract parity are outside this level-calculation scope.

### Grover Llorens Activator Strategy Analysis

Crossing rules depend on a custom activator whose principal numerical series is not defined in the description. Performance-statistic formulas are ancillary and do not define that series.

- Grover Llorens Activator recurrence, acceleration/convergence calculation and initialization are absent.

### Built-in Kelly ratio for dynamic position sizing

Naming Kelly and Keltner does not disclose the adaptive sizing computation.

- Kelly estimator/formula and its trade-performance inputs are not defined; neither initial-history behavior nor size transformation is supplied.

### Gap Filling Strategy

The trade trigger depends on an unresolved non-fill confirmation and an undefined exact fill/reference level; generic gap arithmetic alone is not the principal strategy.

- The phrase bar following the gap does not define the confirmation bar.
- The red gap-fill price is not explicitly calculated or anchored, so the confirmation/exit predicate is not reproducible without a choice.

### Сalculation a position size based on risk

The entire description names risk and stop loss without defining their transformation into size.

- No position-sizing equation, units or risk-to-stop-distance conversion is supplied.

### LUBE

The normalized friction signal and directional series determine the principal trade output, but their exact computation is absent.

- Visit-count price inclusion and friction normalization/baseline equation are not fully defined.
- The fir weighted-average length and directional comparison are undisclosed.

### Stepped trailing strategy example

Usable scope: parameterized exit state machine with supplied initial stop and three profit prices: TP1 moves stop to entry, TP2 moves stop to TP1, TP3 exits. Level values are inputs to this procedure, not a missing entry strategy. Intrabar execution parity is not certified.

### Monthly Returns in PineScript Strategies

A monthly/yearly performance table is promised without its principal return calculation.

- Return numerator/denominator, equity sampling and compounding/reset calculation are absent.

### TrendMaster Pro 2.3 with Alerts

The primary crossover candidates must pass multiple confirmation layers before becoming the stated output. Undisclosed gates prevent reproducing the principal filtered signal.

- Bollinger width pass threshold, stochastic pass conditions and Band Power calculation are absent.
- Exact combination/enablement of confirmation layers and higher-timeframe alignment predicate are not supplied.

### Template Trailing Strategy (Backtester)

The orchestration framework requires an opaque encoded deal-condition convention and unspecified execution/sizing transformations. Interface examples and generic trailing definitions do not disclose its principal computation.

- getSignal/DealConditions numeric encoding and decoding are delegated to an unspecified library version.
- Entry/exit/trailing/quantity module formulas and order-priority transitions are not disclosed.

### TASC 2026.03 One Percent A Week

Usable scope: normal-week order/level procedure: Monday open minus 1% buy limit, next-day fill plus 1% target, 0.5% drawdown triggers entry-price limit, Friday close ends position, one trade/week and 10% equity. Holiday policy and exact drawdown-reference implementation remain outside this scoped procedure.

### Grid Like Strategy

Usable scope: supplied equally spaced grid levels and base size drive the explicit long-state transition: upward cross opens long with adjacent stop/target; winning exit opens next long, losing exit opens short with adjacent levels. Loss/win-conditioned multiplicative sizing is specified. Grid anchoring, complete mirrored short recurrence and resets are not certified.

### Bjorgum Double Tap

Target-height arithmetic depends on identifying the double pattern and pivots, whose decisive numerical recognition criteria remain undefined. The target alone is an intermediate calculation with hidden core inputs.

- Exact zig-zag direction-change/confirmation predicate and significant-point rule are absent.
- Double-test tolerance and admissible pivot arrangement/spacing are not defined.

### How To Set Backtest Time Ranges

The description promises time/date filtering but does not disclose its principal inclusion predicate.

- Window boundary/timezone, cross-midnight/day matching and date-range Boolean logic are absent.

## Verification

`python3 scripts/check_tradingview_strategy_profiles.py` checks the frozen semantic receipt, unchanged card bytes and reviewed final locations. Add `--source-root` pointing to the saved `/script` HTML directory to verify all742 capture hashes and exact raw evidence.

Source/card evidence: `research/tradingview-strategy-understanding.json`; independent semantic receipt: `research/tradingview-strategy-understanding-audit.json`; completeness and locations: `research/tradingview-strategy-card-locations.json`.
