# TradingView Advanced Charts: distilled reference for solmargintrader

Version: 1.0.0 (2026-11-07). Delta: first distillation of the `tradingview/` docs bundle.

This page distills the TradingView Advanced Charts (Charting Library) and Trading Platform documentation, its TypeScript definitions, and the agentskills.io Agent Skills format into one reference for this repository. It keeps the exact identifiers (method names, option keys, study names, `PineJS.Std` functions), the equations, and the contracts. It maps each part to the repo's components.

It is a reference, not an integration. Nothing in the repo renders TradingView charts today. The Charting Library is licensed by TradingView: request access before using it, and keep the library files out of this public repository (see [Licensing](#licensing-and-what-stays-out-of-git)).

## Sources

The owner placed the bundle in `tradingview/` (gitignored, local only). Every section cites its source:

| Citation | Local file | What it holds |
| --- | --- | --- |
| `ctx L<a>-<b>` | `tradingview/charting-library-context.txt` (66,434 lines) | The three `.d.ts` files (lines 13-35909), then 136 docs pages as Markdown (lines 35910-66434) |
| `d.ts L<n>` | `tradingview/charting_library.d.ts` | Widget, chart, study, drawing, `PineJS` types |
| `datafeed d.ts L<n>` | `tradingview/datafeed-api.d.ts` | `IBasicDataFeed`, `LibrarySymbolInfo`, `Bar`, marks |
| `broker d.ts L<n>` | `tradingview/broker-api.d.ts` | Trading Platform `IBrokerTerminal`, orders, positions |
| `agentskills L<n>` | `tradingview/agentskillsio-llms-full.txt` | Agent Skills spec from `https://agentskills.io/llms-full.txt` |
| `docs_map` | `tradingview/llms.txt`, `tradingview/docs_map.md` | Page index; docs last updated 2026-10-13 |

Every docs page is also online as Markdown: `https://www.tradingview.com/charting-library-docs/latest/<path>.md`. The `.d.ts` files are hosted next to the docs and always match the latest version.

## How to use this page

- To chart what the backtester computes, start with [Indicator parity](#indicator-parity-repo-vs-tradingview), then [Built-in indicators](#built-in-indicators) or [Custom indicators and PineJS](#custom-indicators-and-pinejs).
- To feed the repo's candles into a chart, read [Datafeed, symbology and streaming](#datafeed-symbology-and-streaming).
- To draw trades, forward-test calls, ladder rungs or LP ranges on a chart, read [Chart API, drawings and on-chart signals](#chart-api-drawings-and-on-chart-signals).
- To connect order entry, read [Trading Platform and Broker API](#trading-platform-and-broker-api) together with the extension non-negotiables in `CLAUDE.md`.
- To package any of this as an agent skill, read [Agent Skills format](#agent-skills-format-agentskillsio).

## Indicator parity: repo vs TradingView

`backtester/core/indicators.py` and the Compound 5m metrics (`backtester/core/scorecard.py`, `docs/COMPOUND-5M.md`) compute the same named indicators that TradingView ships. A chart is only useful as a check if both sides compute the same number. This table compares the repo's definitions (read from the code on 2026-11-07) with TradingView's built-in defaults. The TradingView docs do not state smoothing (RMA vs EMA), EMA seeding or the stdev convention for any built-in, so "expected same" rows still need an `exportData` check. A "differs" row means a TradingView chart will not match the backtest unless you change the study inputs or write a custom indicator.

| Indicator | Repo definition (`backtester/core/indicators.py`) | TradingView built-in (study name, default inputs from `StudyOverrides` in `charting_library.d.ts`) | Parity |
| --- | --- | --- | --- |
| SMA | `sma(values, window)`: mean of the last `window` values | `Moving Average`: `length`=9, `source`=close | Same formula; set `length` |
| EMA | `ema(values, span)`: `alpha = 2/(span+1)`, seeded by the SMA of the oldest retained window, recursion truncated to `12 * span` bars (`EMA_CAP_MULTIPLE`) | `Moving Average Exponential`: `length`=9 | Same to about 2.4e-13 relative after warm-up. Seeding is not documented by TradingView, so early bars can differ |
| RSI | Wilder: `wilder_smooth` (alpha `1/period`, SMA-seeded) of gains and losses; `RSI = 100 - 100/(1+RS)`; 50 without history | `Relative Strength Index`: `length`=14 (plus an optional `smoothing line`) | Expected same; the docs do not state the smoothing. Verify with `exportData` |
| MACD | EMA 12 - EMA 26; signal = EMA 9 of the line; histogram = line - signal | `MACD`: `fast length`=12, `slow length`=26, `signal length`=9, `oscillator ma type`=EMA, `signal line ma type`=EMA | Same |
| PPO | `100 * (EMA_fast - EMA_slow) / EMA_slow`, 12/26, signal EMA 9 | `Price Oscillator`: `shortlen`=10, `longlen`=21, no signal input | **Differs**: set 12/26; the signal line needs a custom indicator |
| Bollinger Bands | SMA 20 ± 2 × population stdev (`ddof=0`); `bandwidth = (upper - lower)/mid` | `Bollinger Bands`: `length`=20, `mult`=2; `Bollinger Bands Width` separate | Same inputs. `PineJS.Std.stdev` is documented as biased (population), matching `ddof=0` (d.ts L18919-18927); the built-in's own convention is not stated |
| Keltner | EMA 20 ± 2 × ATR 14 (strategy card `keltner`) | `Keltner Channels`: `length`=20, `mult`=**1**, `usetruerange`=true; one `length` for both | **Differs**: set `mult`=2; EMA 20 and ATR 14 cannot differ in the built-in |
| ATR | Wilder smoothing of true range `max(H-L, |H-prevC|, |L-prevC|)`, period 14 | `Average True Range`: `length`=14 | Same: `PineJS.Std.atr` is documented as the RMA of true range (d.ts L18560-18568) |
| Stochastic | Fast %K = `(C - LL_k)/(HH_k - LL_k) × 100`; %D = SMA 3 of %K; 50 on a zero range | `Stochastic`: `%k length`=14, `%k smoothing`=1, `%d smoothing`=3 | Same (raw %K at `%k smoothing`=1) |
| OBV | Cumulative `sign(ΔC) × volume` from 0 | `On Balance Volume` (plus optional smoothing line) | Same shape; level depends on the first loaded bar |
| VWAP | `rolling_vwap`: volume-weighted typical price `(H+L+C)/3` over the last 20 bars | `VWAP`: `source`=hlc3, `anchor period`=Session (Week, Month, ... options) | **Differs**: the built-in resets per anchor. `VWMA` (`len`=20) is a close-price proxy only. Compound 5m `vwap_side`/`vwap_reversion` use a UTC-session or 48-bar VWAP and scale the distance by its RMS over 288 bars, floored at ATR (`memory.md` v47): custom indicator |
| Z-score | `zscore`: sample stdev (`ddof=1`), window 20; 0 on zero dispersion | No built-in | Custom indicator. Note: the Compound 5m `zscore` metric uses `ddof=0`, unlike the strategy card |
| ADX / DMI | Wilder `+DI`, `-DI`, `ADX` (`directional_movement`) | `Directional Movement`: `di length`=14, `adx smoothing`=14 (plots `+di`, `-di`, `adx`, `dx`, `adxr`) | Same family; match both lengths |
| Ichimoku | Tenkan 9, Kijun 26, Senkou B 52, computed at the current bar | `Ichimoku Cloud`: 9 / 26 / 52, lagging 26, `leading shift periods`=26 | Same lines; the forward-plotted cloud is display only. Never read a value drawn at bar t as known at bar t |
| ROC | Decimal fraction over the window (Compound 5m `roc`: log return / (σ√n)) | `Rate Of Change`: `length`=9, percent | **Differs**: scale ×100 and vol scaling |
| Realised vol | Annualised log-return stdev (`ddof=1`, 365 periods/yr; 5m bars use `365 * 288`) | `Historical Volatility`: `length`=10 | Check annualisation and window |
| CCI, MFI, BOP, Donchian | Compound 5m `cci`, `money_flow` (candle proxy), `bop`, `donchian` | `Commodity Channel Index` 20; `Money Flow Index` 14; `Balance of Power`; `Donchian Channels` 20 | `money_flow` is a candle proxy, not MFI; others need input matching |
| Fibonacci | `fib_level = high - (high - low) × ratio` (up swing) | `fib_retracement` drawing | Same levels (0.382, 0.5, 0.618, 0.786) |

Check parity with `exportData` from the chart (see the Chart API section) against the backtester's arrays on the same cached bars. The repo's own guidance on matching TradingView (`skills/trading-and-investing/references/indicator-signal-implementation-and-backtesting.md:665`): use Wilder smoothing as `alpha = 1/n, adjust=False`, and require agreement to about 1e-8 after warm-up.

The per-strategy and per-metric study mapping is in [Built-in indicators → Use in solmargintrader](#use-in-solmargintrader).

## Licensing and what stays out of git

Read this before you build anything from this page. The terms decide which product the repo can use at all.

| Rule (TradingView docs) | Source | Consequence for this repo |
| --- | --- | --- |
| Advanced Charts is free only if the TradingView attribution stays visible and the deployment is public: "not for private use or behind a paywall". The licence agreement allows use "on public websites only". | ctx L47661-47823, L38895 | The Chrome extension and `soltui/` are private tools. They do not meet this condition. Do not embed Advanced Charts or Trading Platform in them without a licence from TradingView that covers private use. |
| The library is not redistributable. "Any part of the library" is prohibited in public repositories. | ctx L48065, L48340 | `mithudso/solmargintrader` is public. `tradingview/` (the docs bundle and the `.d.ts` files) is in `.gitignore`. A future vendored copy of the library (for example `extension/vendor/tradingview/`) must be gitignored too. |
| Download the library only from TradingView's private GitHub repos (`tradingview/charting_library`, `tradingview/trading_platform`) after an access request. Third-party copies are prohibited. | ctx L48032-48297 | Never fetch the library from a mirror or CDN. |
| Altering the library source is prohibited by the licence agreement. | ctx L50271-50344 | Customize only through options, overrides, featuresets, CSS themes and custom indicators. |
| Trading Platform is licensed to brokers and has its own fees. Order lines, position lines, execution shapes, multi-chart layouts, the Order Ticket, DOM and Account Manager are Trading Platform only (the three trading primitives since v29.0.0). | ctx L50345-50432, L49230-49313 | The [Trading Platform and Broker API](#trading-platform-and-broker-api) section is reference only. Each on-chart recipe below gives an Advanced Charts fallback with `createShape`. |
| Lightweight Charts is TradingView's free, open-source charting library (about 45 KB). You push data to it directly. It has no built-in indicators, no datafeed contract and no drawings API. | ctx L47984-48031 | This is the only TradingView product that fits a private, unpublished tool. It still conflicts with the extension's zero-runtime-dependency rule (`CLAUDE.md`, House style). Check its licence and attribution requirement in its repository before adding it. |

What the rest of this page is good for, given those terms:

- The **equations, indicator definitions and input defaults** are facts about how TradingView computes and labels indicators. They are useful as a parity target for the backtester even if the repo never embeds the library.
- The **datafeed, marks and drawings contracts** describe a clean design for exposing candles, signals and trades to any chart. The same shapes map onto Lightweight Charts (`createChart`, `addSeries`, markers, `createPriceLine`; see the migration map in [TradingView library: product, setup, versions](#tradingview-library-product-setup-versions)).
- The **Broker API concepts** (order state machine, brackets, reconcile-by-callback) are a checklist for the extension's own order code.

## Built-in indicators

Sources: docs `charting-library-context.txt` (cited as `ctx L<a>-<b>`) and type defs `charting_library.d.ts` (cited as `d.ts L<n>`). Docs say Advanced Charts and Trading Platform ship "more than 100" built-in indicators (ctx L65620-65640). Only the name list is in the docs; per-indicator input names and defaults come from the generated `StudyOverrides` interface in `d.ts` (L22397-27586), so inputs the types do not expose show as "none listed" (that does not prove the indicator has no such input in the UI).

### 1. Catalog of built-in indicators

- Name column = the exact string for `createStudy(name, ...)`. Docs say the name must match the Indicators dialog / drop-down (ctx L65654-65662); `widget.getStudiesList()` returns the exact supported names (d.ts L12550).
- Category is this fragment's own classification (trend / momentum / volatility / volume / other); the docs do not categorise.
- Inputs = UI input names (lowercase in overrides, e.g. `macd.fast length`) with defaults from `StudyOverrides`. `createStudy`'s `inputs` object is keyed by input **id** (e.g. `length`, `in_0`), which can differ from the UI name; get ids from `widget.getStudyInputs(name)` or `IStudyApi.getInputsInfo()`.
- `plots:` are plot names usable in overrides. Band/background plots (`upperlimit`, `lowerlimit`, `middlelimit`, `* background`) exist on oscillators and take `color`, `linestyle`, `linewidth`, `visible`, `value`, `zorder` (bands) or `color`, `transparency`, `visible` (background); omitted from rows below.
- Rows 1-108 = the docs "Indicators list" in order; the last 6 rows are names present in `d.ts` or elsewhere in the docs but absent from that list.

| Name (createStudy) | Category | Inputs and defaults | Notes |
| --- | --- | --- | --- |
| `52 Week High/Low` | other | `high source`=close [close, high]; `low source`=close [close, low] | (d.ts L22403) |
| `Accelerator Oscillator` | momentum | none listed | (plots: `plot`; d.ts L22411) |
| `Accumulation/Distribution` | volume | none listed | (plots: `plot`; d.ts L22425) |
| `Accumulative Swing Index` | trend | `limit move value`=10 | (plots: `asi`; d.ts L22439) |
| `Advance/Decline` | other | `length`=10 | (plots: `plot`; d.ts L22460) |
| `Arnaud Legoux Moving Average` | trend | `window size`=9; `offset`=0.85; `sigma`=6 | (plots: `plot`; d.ts L22644) |
| `Aroon` | trend | `length`=14 | (plots: `upper`, `lower`; d.ts L22679) |
| `Average Directional Index` | trend | `adx smoothing`=14; `di length`=14 | Plot adx only; inputs `adx smoothing` and `di length` are separate. (plots: `adx`; d.ts L22714) |
| `Average Price` | other | `other symbol` (symbol) | (plots: `plot`; d.ts L22742) |
| `Average True Range` | volatility | `length`=14 | (plots: `plot`; d.ts L22763) |
| `Awesome Oscillator` | momentum | none listed | (plots: `plot`; d.ts L22784) |
| `Balance of Power` | momentum | none listed | (plots: `plot`; d.ts L22798) |
| `Bollinger Bands` | volatility | `length`=20; `mult`=2; `other symbol` (symbol) | Docs: price indicator. Basis MA type and stdev convention not listed. (plots: `median`, `upper`, `lower`; d.ts L22812) |
| `Bollinger Bands %B` | volatility | `length`=20; `mult`=2 | (plots: `upperlimit`, `lowerlimit`, `plot`; d.ts L22881) |
| `Bollinger Bands Width` | volatility | `length`=20; `mult`=2 | (plots: `plot`; d.ts L22935) |
| `Chaikin Money Flow` | volume | `length`=20 | (plots: `zero`, `plot`; d.ts L22963) |
| `Chaikin Oscillator` | volume | `short`=3; `long`=10 | (plots: `zero`, `plot`; d.ts L22994) |
| `Chaikin Volatility` | volatility | `periods`=10; `rate of change lookback`=10 | (plots: `zero`, `plot`; d.ts L23032) |
| `Chande Kroll Stop` | volatility | `p`=10; `x`=1; `q`=9 | (plots: `long`, `short`; d.ts L23066) |
| `Chande Momentum Oscillator` | momentum | `length`=9 | (plots: `plot`; d.ts L23115) |
| `Chop Zone` | trend | none listed | (plots: `plot`; d.ts L23136) |
| `Choppiness Index` | trend | `length`=14 | (plots: `upperlimit`, `lowerlimit`, `plot`; d.ts L23150) |
| `Commodity Channel Index` | momentum | `length`=20; `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=20 | (plots: `upperlimit`, `lowerlimit`, `plot`, `smoothed ma`; d.ts L23197) |
| `Connors RSI` | momentum | `rsi length`=3; `updown length`=2; `roc length`=100 | (plots: `upperlimit`, `lowerlimit`, `crsi`; d.ts L23295) |
| `Coppock Curve` | momentum | `wma length`=10; `long roc length`=14; `short roc length`=11 | (plots: `plot`; d.ts L23353) |
| `Correlation Coefficient` | other | `sym` (symbol); `length`=20 | (plots: `plot`; d.ts L23419) |
| `Correlation - Log` | other | `instrument 1` (symbol); `instrument 2` (symbol); `periods`=25 | (plots: `plot`; d.ts L23388) |
| `Detrended Price Oscillator` | momentum | `period`=21; `iscentered`=false | (plots: `zero`, `dpo`; d.ts L23445) |
| `Directional Movement` | trend | `di length`=14; `adx smoothing`=14 | Plots +di, -di, adx, dx, adxr. (plots: `+di`, `-di`, `adx`, `dx`, `adxr`; d.ts L23481) |
| `Donchian Channels` | volatility | `length`=20; `offset`=0 | (plots: `lower`, `upper`, `basis`; d.ts L23565) |
| `Double EMA` | trend | `length`=9 | (plots: `plot`; d.ts L23627) |
| `Ease of Movement` | volume | `divisor`=10000; `length`=14 | (plots: `plot`; d.ts L23704) |
| `Elder's Force Index` | volume | `length`=13 | Docs list spells it `Elder's Force Index`; the volume blacklist example spells it `Elders Force Index`; verify with `getStudiesList()`. (plots: `zero`, `plot`; d.ts L23732) |
| `EMA Cross` | trend | `short:input`=9; `long:input`=26 | Same name collision as MA Cross for `short`/`long`. (plots: `short:plot`, `long:plot`, `crosses`; d.ts L23648) |
| `Envelopes` | volatility | `length`=20; `upper percentage`=10; `lower percentage`=10; `method`=Simple [Simple, Exponential, Weighted]; `source`=close (source) | (plots: `average`, `upper`, `lower`; d.ts L23763) |
| `Fisher Transform` | momentum | `length`=9 | (plots: `level:band`, `fisher`, `trigger`; d.ts L23842) |
| `Guppy Multiple Moving Average` | trend | `trader ema 1 length`=3; `trader ema 2 length`=5; `trader ema 3 length`=8; `trader ema 4 length`=10; `trader ema 5 length`=12; `trader ema 6 length`=15; `investor ema 1 length`=30; `investor ema 2 length`=35; `investor ema 3 length`=40; `investor ema 4 length`=45; `investor ema 5 length`=50; `investor ema 6 length`=60 | (plots: `trader ema 1`, `trader ema 2`, `trader ema 3`, `trader ema 4`, `trader ema 5`, `trader ema 6`, `investor ema 1`, `investor ema 2`, `investor ema 3`, `investor ema 4`, `investor ema 5`, `investor ema 6`; d.ts L23977) |
| `Historical Volatility` | volatility | `length`=10 | (plots: `plot`; d.ts L24229) |
| `Hull Moving Average` | trend | `length`=9 | (plots: `plot`; d.ts L24250) |
| `Ichimoku Cloud` | trend | `another symbol` (symbol); `conversion line periods`=9; `base line periods`=26; `leading span periods`=52; `lagging span periods`=26; `leading shift periods`=26 | Cloud displaced forward by `leading shift periods`. (plots: `conversion line`, `base line`, `lagging span`, `leading span a`, `leading span b`; d.ts L24271) |
| `Keltner Channels` | volatility | `usetruerange`=true; `length`=20; `mult`=1 | Single `length` input; default `mult` is 1. (plots: `upper`, `middle`, `lower`; d.ts L24389) |
| `Klinger Oscillator` | volume | none listed | (plots: `plot`, `signal`; d.ts L24456) |
| `Know Sure Thing` | momentum | `roclen1`=10; `roclen2`=15; `roclen3`=20; `roclen4`=30; `smalen1`=10; `smalen2`=10; `smalen3`=10; `smalen4`=15; `siglen`=9 | Inputs roclen1..4, smalen1..4, siglen. (plots: `zero`, `kst`, `signal`; d.ts L24484) |
| `Least Squares Moving Average` | trend | `length`=25; `offset`=0 | (plots: `plot`; d.ts L24585) |
| `Linear Regression Curve` | trend | `length`=9 | (plots: `plot`; d.ts L24613) |
| `Linear Regression Slope` | trend | `periods`=14 | (plots: `plot`; d.ts L24634) |
| `MA Cross` | trend | `short:input`=9; `long:input`=26 | Plots and inputs named `short`/`long` collide; use `short:input`, `long:input`, `short:plot` (docs example changes 9/26 to 12/24). (plots: `short:plot`, `long:plot`, `crosses`; d.ts L24654) |
| `MA with EMA Cross` | trend | `length ma`=10; `length ema`=10 | (plots: `ma`, `ema`, `crosses`; d.ts L24710) |
| `Mass Index` | volatility | `length`=10 | (plots: `plot`; d.ts L24874) |
| `McGinley Dynamic` | trend | `length`=14 | (plots: `plot`; d.ts L24895) |
| `Median Price` | other | none listed | (plots: `plot`; d.ts L24916) |
| `Momentum` | momentum | `length`=10; `source`=close (source) | (plots: `zero`, `mom`; d.ts L24930) |
| `Money Flow Index` | volume | `length`=14 | (plots: `upperlimit`, `lowerlimit`, `plot`; d.ts L24967) |
| `Moving Average` | trend | `other symbol` (symbol); `length`=9; `source`=close (source); `offset`=0; `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=9 | Docs: price indicator (placed on source pane). Has secondary smoothing MA (plot `smoothed ma`, display 0 by default per getStudyStyles sample). Average type not stated (SMA presumed). (plots: `plot`, `smoothed ma`; d.ts L25014) |
| `Moving Average Channel` | trend | `upper length`=20; `lower length`=20; `upper offset`=0; `lower offset`=0 | (plots: `upper`, `lower`; d.ts L25101) |
| `MACD` | momentum | `other symbol` (symbol); `fast length`=12; `slow length`=26; `source`=close (source); `signal length`=9; `oscillator ma type`=EMA [SMA, EMA, WMA]; `signal line ma type`=EMA [SMA, EMA, WMA] | Docs example inputs by id: `{in_0:14,in_1:30,in_3:'close',in_2:9}` (reads as fast, slow, source, signal; confirm with `getStudyInputs('MACD')`). (plots: `histogram`, `macd`, `signal`; d.ts L24766) |
| `Moving Average Exponential` | trend | `length`=9; `source`=close (source); `offset`=0; `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=9 | Docs example: `createStudy('Moving Average Exponential',false,false,{length:26})`. (plots: `plot`, `smoothed ma`; d.ts L25218) |
| `Moving Average Weighted` | trend | `length`=9; `source`=close (source); `offset`=0 | (plots: `plot`; d.ts L25499) |
| `Moving Average Double` | trend | `another symbol` (symbol); `1st period`=14; `2nd period`=21; `method`=Simple [Simple, Exponential, Weighted] | (plots: `plot 1`, `plot 2`; d.ts L25163) |
| `Moving Average Triple` | trend | `1st period`=14; `2nd period`=21; `3rd period`=35; `method`=Simple [Simple, Exponential, Weighted] | (plots: `plot 1`, `plot 2`, `plot 3`; d.ts L25430) |
| `Moving Average Adaptive` | trend | `period`=10 | (plots: `plot 1`; d.ts L25080) |
| `Moving Average Hamming` | trend | `period`=10 | (plots: `plot 1`; d.ts L25277) |
| `Moving Average Multiple` | trend | `1st period`=14; `2nd period`=21; `3rd period`=35; `4th period`=50; `5th period`=100; `6th period`=200; `method`=Simple [Simple, Exponential, Weighted] | Six plots; all six periods are always inputs. (plots: `plot 1`, `plot 2`, `plot 3`, `plot 4`, `plot 5`, `plot 6`; d.ts L25298) |
| `Majority Rule` | other | `rolling period`=14 | (plots: `majority rule`; d.ts L24854) |
| `Net Volume` | volume | none listed | (plots: `plot`; d.ts L25533) |
| `On Balance Volume` | volume | `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=9 | (plots: `plot`, `smoothed ma`; d.ts L25547) |
| `Parabolic SAR` | trend | `start`=0.02; `increment`=0.02; `maximum`=0.2; `other symbol` (symbol) | (plots: `plot`; d.ts L25598) |
| `Pivot Points Standard` | other | `type`=Traditional [Traditional, Fibonacci, Woodie, Classic, DeMark, Camarilla, Floor]; `number of pivots back`=15; `pivots timeframe`=Auto [Auto, Daily, Weekly, Monthly, Yearly]; `show historical pivots`=true | No plots keys in overrides; type options enumerated. (d.ts L25644) |
| `Price Channel` | volatility | `length`=20; `offset length`=0 | Docs examples use `createStudy('Price Channel',true,false,{in_0:26},...)` and `priceScale:'new-left'`. (plots: `highprice line`, `lowprice line`, `centerprice line`; d.ts L25664) |
| `Price Oscillator` | momentum | `shortlen`=10; `longlen`=21 | (plots: `plot`; d.ts L25720) |
| `Price Volume Trend` | volume | none listed | (plots: `pvt`; d.ts L25748) |
| `Rank Correlation Index` | momentum | `length`=12 | (plots: `zero line`, `rci`; d.ts L25762) |
| `Rate Of Change` | momentum | `length`=9 | (plots: `zero line`, `roc`; d.ts L25793) |
| `Ratio` | other | `source`=close [open, high, low, close, hl2, hlc3, ohlc4]; `symbol` (symbol) | (plots: `negativefill`, `positivefill`, `plot`, `baseline`; d.ts L25824) |
| `Relative Strength Index` | momentum | `length`=14; `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=14 | (plots: `upperlimit`, `middlelimit`, `lowerlimit`, `plot`, `smoothed ma`; d.ts L25922) |
| `Relative Vigor Index` | momentum | `length`=10 | (plots: `rvgi`, `signal`; d.ts L26010) |
| `Relative Volatility Index` | volatility | `length`=10 | (plots: `upperlimit`, `lowerlimit`, `plot`; d.ts L26045) |
| `Standard Error` | volatility | `length`=14 | (plots: `plot`; d.ts L26366) |
| `Standard Error Bands` | volatility | `periods`=21; `standard errors`=2; `method`=Simple [Simple, Exponential, Weighted]; `averaging periods`=3 | (plots: `plot 1`, `plot 2`, `plot 3`; d.ts L26386) |
| `SMI Ergodic Indicator/Oscillator` | momentum | `shortlen`=5; `longlen`=20; `siglen`=5 | (plots: `indicator`, `signal`, `oscillator`; d.ts L26092) |
| `Smoothed Moving Average` | trend | `length`=7; `source`=close (source) | (plots: `plot`; d.ts L26263) |
| `Standard Deviation` | volatility | `periods`=5; `deviations`=1 | (plots: `plot`; d.ts L26342) |
| `Stochastic` | momentum | `%k length`=14; `%k smoothing`=1; `%d smoothing`=3 | Docs: non-price (always 0-100). Docs example: `createStudy('Stochastic',false,false,{in_0:26},{"%d.color":"#FF0000"})`. (plots: `upperlimit`, `lowerlimit`, `%k`, `%d`; d.ts L26455) |
| `Stochastic RSI` | momentum | `lengthrsi`=14; `lengthstoch`=14; `smoothk`=3; `smoothd`=3 | Input ids lengthrsi/lengthstoch/smoothk/smoothd. (plots: `upperlimit`, `lowerlimit`, `%k`, `%d`; d.ts L26530) |
| `Session Volume Profile` | volume | `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `row size`=24; `volume`=Up/Down [Up/Down, Total, Delta]; `sessions`=All [All, Each (pre-market, market, post-market), Pre-market only, Market only, Post-market only, Custom]; `custom session`=0930-1600; `customsessiontz`=Exchange [Exchange, Etc/UTC, named tz]; `value area volume`=70; `extend poc right`=false; `extend vah right`=false; `extend val right`=false; `subscriberealtime`=true | Marked Trading Platform only in the docs list. See the Session Volume Profile section. (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L26155) |
| `SuperTrend` | trend | `length`=10; `factor`=3 | (plots: `supertrend`, `up arrow`, `down arrow`; d.ts L26612) |
| `Spread` | other | `source`=close [open, high, low, close, hl2, hlc3, ohlc4]; `symbol` (symbol) | (plots: `negative fill`, `positive fill`, `plot`, `baseline`; d.ts L26290) |
| `TRIX` | momentum | `length`=18 | (plots: `zero`, `trix`; d.ts L26672) |
| `Triple EMA` | trend | `length`=9 | (plots: `plot`; d.ts L26722) |
| `True Strength Indicator` | momentum | `long`=25; `short`=13; `siglen`=13 | d.ts override key is `true strength index` (name mismatch vs docs list); verify with `getStudiesList()`. (plots: `zero`, `true strength index`, `signal`; d.ts L26743) |
| `Trend Strength Index` | trend | `periods`=14 | (plots: `plot`; d.ts L26703) |
| `Typical Price` | other | none listed | (plots: `plot`; d.ts L26802) |
| `Ultimate Oscillator` | momentum | `length7`=7; `length14`=14; `length28`=28 | (plots: `uo`; d.ts L26816) |
| `Volatility Close-to-Close` | volatility | `periods`=10; `days per year`=252 | (plots: `plot`; d.ts L26898) |
| `Volatility Zero Trend Close-to-Close` | volatility | `periods`=10; `days per year`=252 | (plots: `plot`; d.ts L26986) |
| `Volatility O-H-L-C` | volatility | `periods`=10; `market closed percentage`=0; `days per year`=252 | (plots: `plot`; d.ts L26955) |
| `Volatility Index` | volatility | `periods`=10; `atr mult`=3; `method`=Wilder Smoothing [Exponential, Wilder Smoothing] | (plots: `plot`; d.ts L26925) |
| `VWAP` | volume | `source`=hlc3 (source); `anchor period`=Session [Session, Week, Month, Quarter, Year, Decade, Century] | Volume-based (in the docs volume blacklist). Anchor period input. (plots: `vwap`; d.ts L26851) |
| `VWMA` | trend | `len`=20 | (plots: `plot`; d.ts L26877) |
| `Volume Oscillator` | volume | `shortlen`=5; `longlen`=10 | (plots: `zero`, `plot`; d.ts L27098) |
| `Volume Profile Fixed Range` | volume | `first bar time`=0; `last bar time`=0; `row size`=24; `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `subscriberealtime`=true; `value area volume`=70; `volume`=Up/Down [Up/Down, Total, Delta] | Needs volume. Subject to `volume_profile.max_total_rows` (default 6000). (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L27136) |
| `Volume Profile Visible Range` | volume | `first visible bar time`=0; `last visible bar time`=0; `row size`=24; `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `value area volume`=70; `volume`=Up/Down [Up/Down, Total, Delta] | Needs volume. Single profile; errors if histogram exceeds `max_total_rows`. (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L27226) |
| `Vortex Indicator` | trend | `period`=14 | (plots: `vi +`, `vi -`; d.ts L27310) |
| `Volume` | volume | `show ma`=false; `volume ma:input`=SMA [SMA, EMA, WMA]; `ma length`=20; `color based on previous close`=false; `other symbol` (symbol); `smoothing line`=SMA [SMA, EMA, WMA]; `smoothing length`=9 | Added by default when the symbol has volume (`create_volume_indicator_by_default` featureset). Overrides example `volume.volume.color.0`. (plots: `volume`, `volume ma:plot`, `smoothed ma`; d.ts L27012) |
| `Williams %R` | momentum | `length`=14 | (plots: `upperlimit`, `lowerlimit`, `plot`; d.ts L27345) |
| `Williams Alligator` | trend | `jaw length`=21; `teeth length`=13; `lips length`=8; `jaw offset`=8; `teeth offset`=5; `lips offset`=3 | (plots: `jaw`, `teeth`, `lips`; d.ts L27392) |
| `Williams Fractal` | other | `periods`=2 | (plots: `down fractals`, `up fractals`; d.ts L27476) |
| `Zig Zag` | other | `deviation`=5; `depth`=10 | (plots: `plot`; d.ts L27503) |
| `Anchored VWAP` | volume | `start time`=0; `bands calculation mode`=Standard Deviation [Standard Deviation, Percentage]; `bands multiplier #1`=1; `bands multiplier #2`=2; `bands multiplier #3`=3; `source`=hlc3 (source) | Not in the Indicators list; present in d.ts (`AnchoredVWAPIndicatorOverrides`, `StudyOverrides`). UI display name not given; verify via `getStudiesList()`. (plots: `vwap`, `lower band #1`, `lower band #2`, `lower band #3`, `upper band #1`, `upper band #2`, `upper band #3`; d.ts L22481) |
| `Compare` | other | `source`=close [open, high, low, close, hl2, hlc3, ohlc4]; `symbol` (symbol) | Documented: `createStudy('Compare',false,false,{source:'open',symbol:'IBM'})`. No extend-time-scale or legend logos (docs). (plots: `plot`; d.ts L23269) |
| `Overlay` | other | `symbol` (symbol); `extendtimescale`=false | Documented: `createStudy('Overlay',true,false,{symbol:'IBM'})`. Supports Allow extend time scale; overrides `overlay.style`, `overlay.candleStyle.upColor`. (d.ts L25590) |
| `Fixed Range` | volume | `first bar time`=0; `last bar time`=0; `row size`=24; `rows layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `subscriberealtime`=true; `value area volume`=70; `volume`=Up/Down [Up/Down, Total, Delta] | Not in the Indicators list; d.ts `FixedRangeIndicatorOverrides`. Same inputs as Volume Profile Fixed Range; relationship not documented. (plots: `developing poc`, `developing va high`, `developing va low`; d.ts L23887) |
| `Regression Trend` | other | `first bar time`=0; `last bar time`=0; `lower deviation`=-2; `source`=close (source); `upper deviation`=2; `use lower deviation`=true; `use upper deviation`=true | Not in the Indicators list; d.ts `RegressionTrendIndicatorOverrides` (generic key map). Also a drawing tool `regression_trend`. (d.ts L25882) |
| `Sessions` | other | none listed | Not in the Indicators list; d.ts `SessionsIndicatorOverrides` is a generic key map. Inputs and plots: not listed. |

(ctx L65232-65497 names; d.ts L22397-27586 inputs/plots/defaults; d.ts L12550 `getStudiesList`.)

Docs-stated price vs non-price split: *Moving Average* and *Bollinger Bands* are price indicators (placed on the source pane, same price scale); *Stochastic* is non-price (new pane, new scale). Docs name no other built-in's group (ctx L65507-65519).

Volume-dependent indicators (docs blacklist example, ctx L65717-65732): Accumulation/Distribution, Chaikin Money Flow, Ease of Movement, Elders Force Index (sic), Klinger Oscillator, Money Flow Index, Net Volume, On Balance Volume, Price Volume Trend, VWAP, Volume Oscillator. Volume Profile indicators also need volume (ctx L54222-54230).

### Standard equations

Standard definitions, not from TradingView docs. TradingView's exact smoothing/seed/stdev convention for each built-in is **not documented** here; treat as the reference formula, not a guarantee of identical output.

```text
Moving averages
SMA(x,n)   = mean(x[t-n+1..t])
EMA(x,n)   = a*x + (1-a)*EMA_prev,  a = 2/(n+1)          (seed: first value or SMA(n); varies by implementation)
RMA/Wilder = a*x + (1-a)*RMA_prev,  a = 1/n               (a.k.a. SMMA, "Smoothed Moving Average")
WMA(x,n)   = sum(i*x[t-n+i], i=1..n) / (n(n+1)/2)
DEMA       = 2*EMA(x,n) - EMA(EMA(x,n),n)
TEMA       = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))
HMA(n)     = WMA( 2*WMA(x,n/2) - WMA(x,n), sqrt(n) )
VWMA(x,n)  = sum(x*V,n) / sum(V,n)
LSMA(n)    = endpoint of the least-squares line over n bars (+offset)
ALMA       = sum(w_i*x_i)/sum(w_i), w_i = exp(-(i-m)^2/(2*s^2)), m = offset*(n-1), s = n/sigma
McGinley   = MD_prev + (x - MD_prev) / (0.6 * n * (x/MD_prev)^4)

Momentum / oscillators
RSI        = 100 - 100/(1+RS),  RS = RMA(max(dC,0),n) / RMA(max(-dC,0),n)
MACD       = EMA(C,fast) - EMA(C,slow);  signal = EMA(MACD,sig);  hist = MACD - signal
PPO        = 100*(EMA(C,fast) - EMA(C,slow)) / EMA(C,slow)
Stochastic %K = 100*(C - LL(n)) / (HH(n) - LL(n));  slow %K = SMA(%K,ksmooth);  %D = SMA(%K,dsmooth)
StochRSI   = (RSI - min(RSI,n)) / (max(RSI,n) - min(RSI,n)), then smoothK, smoothD
Williams %R = -100*(HH(n) - C) / (HH(n) - LL(n))
CCI        = (TP - SMA(TP,n)) / (0.015 * meanabsdev(TP,n)),  TP = (H+L+C)/3
MFI        = 100 - 100/(1+MR),  MR = sum(TP*V on up bars,n) / sum(TP*V on down bars,n)
ROC        = 100*(C/C[n] - 1);   Momentum = C - C[n]
TRIX       = 100*(T/T[1] - 1),  T = EMA(EMA(EMA(C,n),n),n)
Ultimate   = 100*(4*A7 + 2*A14 + A28)/7,  A_k = sum(BP,k)/sum(TR,k),  BP = C - min(L,C[1])
Awesome    = SMA(hl2,5) - SMA(hl2,34);  Accelerator = AO - SMA(AO,5)
CMO        = 100*(Sup - Sdown)/(Sup + Sdown) over n
Coppock    = WMA( ROC(C,long) + ROC(C,short), wma )
TSI        = 100*EMA(EMA(dC,long),short) / EMA(EMA(|dC|,long),short)
BoP        = (C - O) / (H - L)
Aroon Up   = 100*(n - barsSinceHH(n)) / n;  Down analogous;  window = n+1 bars
Vortex     = VI+ = sum(|H - L[1]|,n)/sum(TR,n);  VI- = sum(|L - H[1]|,n)/sum(TR,n)

Trend systems
TR         = max(H-L, |H-C[1]|, |L-C[1]|);   ATR = RMA(TR,n)
+DM = (H-H[1]) if > (L[1]-L) and > 0 else 0;  -DM = (L[1]-L) if > (H-H[1]) and > 0 else 0
+DI = 100*RMA(+DM,n)/ATR;  -DI = 100*RMA(-DM,n)/ATR
DX  = 100*|+DI - -DI| / (+DI + -DI);   ADX = RMA(DX, adxsmooth)
Ichimoku   Tenkan = (HH9+LL9)/2; Kijun = (HH26+LL26)/2; SpanA = (Tenkan+Kijun)/2 shifted +26; SpanB = (HH52+LL52)/2 shifted +26; Chikou = C shifted -26
Parabolic SAR  SAR' = SAR + AF*(EP - SAR); AF starts at start, += increment on new EP, capped at maximum
SuperTrend upper = hl2 + f*ATR(n), lower = hl2 - f*ATR(n); band ratchets; trend flips when C crosses the active band
Chande Kroll Stop  highStop = HH(p) - x*ATR(p); lowStop = LL(p) + x*ATR(p); stopShort = HH(highStop,q); stopLong = LL(lowStop,q)

Volatility / channels
Bollinger  mid = SMA(C,n); upper/lower = mid +/- k*stdev(C,n)   (Bollinger specified population stdev)
%B = (C - lower)/(upper - lower);   BBW = (upper - lower)/mid
Keltner    mid = EMA(C,n); upper/lower = mid +/- m*ATR(n)  (or m*SMA(TR,n))
Donchian   upper = HH(n), lower = LL(n), basis = (upper+lower)/2
Price Channel  highprice = HH(n), lowprice = LL(n), center = mid
Envelopes  upper = MA*(1+p%), lower = MA*(1-p%)
Std Dev    stdev(C,n)*deviations;   Std Error = stdev/sqrt(n)
Historical Volatility = stdev(ln(C/C[1]),n)*sqrt(periods_per_year)*100
Chaikin Volatility = 100*(EMA(H-L,n)/EMA(H-L,n)[roc] - 1)
Mass Index = sum(EMA(H-L,9)/EMA(EMA(H-L,9),9), 25)

Volume
OBV  = OBV_prev + sign(C - C[1])*V
A/D  = A/D_prev + V*((C-L)-(H-C))/(H-L)
CMF  = sum(V*((C-L)-(H-C))/(H-L), n) / sum(V, n)
Chaikin Osc = EMA(A/D,3) - EMA(A/D,10)
Force Index = EMA((C - C[1])*V, 13)
PVT  = PVT_prev + V*(C - C[1])/C[1]
Volume Osc  = 100*(EMA(V,short) - EMA(V,long)) / EMA(V,long)
VWAP = cum(TP*V)/cum(V), reset at each anchor period (Session/Week/Month/...)

Price transforms / other
Typical = (H+L+C)/3;  Median = (H+L)/2;  Average = (O+H+L+C)/4
Pivot (Traditional) P = (H+L+C)/3, R1 = 2P - L, S1 = 2P - H, R2 = P + (H-L), S2 = P - (H-L)
Ratio = A/B;  Spread = A - B;  Correlation = Pearson(A,B,n)
Zig Zag: new pivot when price reverses >= deviation% from the running extreme (repaints)
```

Not given a formula (non-standard or not well specified in the sources): Klinger, SMI Ergodic, Chop Zone, Majority Rule, Trend Strength Index, Rank Correlation Index, Relative Vigor Index, Fisher Transform, Know Sure Thing details, Williams Alligator/Fractal, Guppy.

### 2. API: add, modify, remove

#### createStudy

```ts
createStudy(
  name: string,                           // Indicators-dialog name, e.g. 'Moving Average Exponential'
  forceOverlay?: boolean,                 // non-price indicators only: draw on the source pane
  lock?: boolean,                         // whether user may remove/change/hide it
  inputs?: Record<string, StudyInputValue>,   // string | number | boolean, keyed by input id
  overrides?: Partial<SingleIndicatorOverrides>, // style overrides, NO indicator name in keys
  options?: CreateStudyOptions
): Promise<EntityId | null>
// CreateStudyOptions { checkLimit?, priceScale?: 'new-left'|'new-right'|'no-scale'|'as-series',
//                      allowChangeCurrency?, allowChangeUnit?, disableUndo? }
```

(d.ts L11572, L6248-6264, L31393, L31423; ctx L65654-65672.) `checkLimit`: "show the indicator limit dialog if the limit is exceeded" (d.ts); what happens on `false` when over the limit is not documented. The `null` return case is not documented.

```js
const chart = widget.activeChart();            // after widget.onChartReady(...)
// docs examples (ctx L65660-65668)
chart.createStudy('MACD', false, false, { in_0: 14, in_1: 30, in_3: 'close', in_2: 9 });
chart.createStudy('Moving Average Exponential', false, false, { length: 26 });
chart.createStudy('Stochastic', false, false, { in_0: 26 }, { '%d.color': '#FF0000' });
chart.createStudy('Price Channel', true, false, { in_0: 26 }, null, { checkLimit: false, priceScale: 'new-left' });
// inspect names/inputs/styles first
widget.getStudiesList();                       // string[] of valid createStudy names
widget.getStudyInputs('MACD');                 // [{ id, name, type, localizedName }]
widget.getStudyStyles('Moving Average');       // metainfo; plot_0 internal id -> use UI plot name in overrides
```

(`getStudiesList` d.ts L12550; `getStudyInputs` L12563; `getStudyStyles` L12574; ctx L46976-47040.)

#### Manage existing studies

```js
const all = chart.getAllStudies();             // EntityInfo[] = [{ id, name }]   (d.ts L11413)
const id  = all.find(s => s.name === 'Volume').id;
const st  = chart.getStudyById(id);            // IStudyApi                      (d.ts L11584)
chart.removeEntity(id);                        // remove study (also drawings)   (d.ts L11677)
```

`IStudyApi` methods (d.ts L15040-15190): `isUserEditEnabled/setUserEditEnabled`, `getInputsInfo`, `getInputValues`, `setInputValues([{id,value}])`, `getStyleInfo`, `getStyleValues`, `mergeUp/mergeDown` (move to existing pane above/below), `unmergeUp/unmergeDown` (move to new pane; fails if it is the only source on its pane), `paneIndex`, `changePriceScale(StudyPriceScale | EntityId)`, `isVisible/setVisible`, `bringToFront/sendToBack`, `applyOverrides(overrides)`, `applyToEntireLayout()` (Trading Platform multi-chart), `onDataLoaded()`, `onStudyError()`.

```js
st.setInputValues([{ id: 'length', value: 50 }]);           // change input (id from getInputsInfo)
st.applyOverrides({ 'plot.color': '#FF6D00', 'plot.linewidth': 2 });
st.changePriceScale('new-left');                             // or another study's EntityId
st.unmergeDown();                                            // move to a new pane below
widget.subscribe('study_event', (id, type) => {});           // type: 'create'|'remove'|'price_scale_changed'|'paste_study' (d.ts L28290, L31385)
chart.getEntityValues();                                     // current data-window values of series + studies (d.ts L11248)
```

#### Placement

(ctx L65507-65592.) Price indicators attach to their source pane and price scale. Non-price indicators get a new pane and scale. Source = main series unless applied to another indicator.
- `forceOverlay=true` puts a **non-price** indicator on the source pane; it does **not** change the price scale. There is no creation-time way to put a price indicator on a separate pane: create it, then `unmergeUp/unmergeDown`.
- `options.priceScale`: `new-right`, `new-left`, `no-scale`, `as-series` (main series scale, else a new one). A pane holds at most 8 price scales; beyond that `new-*` degrades to `no-scale`.
- Programmatic move: `getStudyById(id).mergeUp()/mergeDown()/unmergeUp()/unmergeDown()`; scale: `changePriceScale(...)`; panes: `chart.getPanes()` returns `IPaneApi[]` (height, position, collapse, maximize).
- Custom studies: metainfo `is_price_study`, `linkedToSeries`, `priceScale` (`StudyTargetPriceScale` enum Right=0, Left=1, NoScale=2), `overlayScaleMargins` (d.ts L639-643).

#### Overrides syntax

(ctx L46757-47154.) Everything lowercase. Three call sites, two key shapes:

| Where | Key shape | Example |
| --- | --- | --- |
| `studies_overrides` (Widget constructor), `widget.applyStudiesOverrides(obj)` | `"<study name>.<plot>.<prop>"` or `"<study name>.<input>"` | `"bollinger bands.median.color": "#33FF88"` |
| `createStudy(..., overrides)`, `IStudyApi.applyOverrides(obj)` | same **without** the study name | `{ 'median.color': '#33FF88' }` |

- Constructor overrides set defaults for studies created **later**. `applyStudiesOverrides` affects only studies created after the call. `IStudyApi.applyOverrides` changes an existing study. `createStudy` overrides win over `studies_overrides`.
- Plot props: `linewidth`, `visible`, `plottype`, plus (d.ts) `display`, `linestyle`, `trackprice`, `transparency`, `color`. Color index: `<plot>.color.<i>` (`color.0` == `color`), e.g. Volume `volume.volume.color.1` = default-green bars.
- `plottype` values: `line`, `histogram`, `cross`, `area`, `columns`, `circles`, `line_with_breaks`, `area_with_breaks`, `step_line`, `step_line_with_breaks` (docs); d.ts `LineStudyPlotStyleName` adds `step_line_with_diamonds` (d.ts L31245).
- `display` is a bitmask of `StudyPlotDisplayTarget`: None=0, Pane=1, DataWindow=2, PriceScale=4, StatusLine=8, All=0xFFFFFFFF; the common default `15` = Pane+DataWindow+PriceScale+StatusLine; `0` hides (d.ts L610-617). `StudyPlotType` (d.ts L618-638: `line`, `colorer`, `bar_colorer`, `shapes`, `chars`, `arrows`, `ohlc_*`, ...) describes custom-study metainfo plot kinds, not override values.
- Input override: `"<study>.<input name>"`, e.g. `"moving average.length": 5`, `"volume.volume ma.visible"`. Precision: `"average true range.precision": 8`.
- Ambiguous names (same name as plot and input, e.g. MA Cross `short`/`long`): suffix `:plot`, `:input`, `:band`, `:area` before the dot: `"short:input": 12`, `"short:plot.linewidth": 3`, `"long:plot.display": 0`.
- Extra props allowed in `createStudy` overrides, "might not work" in `studies_overrides`: `showPriceLine`, `showLabelsOnPriceScale`, `showLegendValues` (booleans), `transparency` (number), `precision` (string).
- Colors: `#RRGGBB` only (no `#RGB`). Docs: transparency range 0-100 with "100 means fully opaque" (verify visually; this is the reverse of the usual convention). Line width: integer. Area-fill color/transparency customisation: not supported.
- Per-indicator override type lists: `StudyOverrides` (names included, for constructor/`applyStudiesOverrides`) and `SingleIndicatorOverrides` (union of per-indicator interfaces, names omitted, **style keys only; inputs are not in it**) (d.ts L31383).

```js
new TradingView.widget({ /*...*/,
  studies_overrides: { 'bollinger bands.median.color': '#33FF88', 'bollinger bands.upper.linewidth': 7,
                       'moving average.length': 5, 'volume.volume.transparency': 99 } });
widget.applyStudiesOverrides({ 'moving average.length': 5 });
chart.createStudy('Relative Strength Index', false, false, { length: 14 }, { 'lowerlimit.value': 30 });
```

#### Limits, access, defaults

- `study_count_limit` (widget option): max studies at once per layout; minimum value 2 (d.ts L5103; ctx L65737-65742).
- `studies_access: { type: 'black'|'white', tools: [{ name, grayed? }] }`: hide or gray-out indicators; names as in the Indicators dialog (d.ts L5083-5095, AccessList L713). Clicking a grayed one calls `onGrayedObjectClicked`.
- Volume indicator auto-added to symbols with volume; suppress with `disabled_features: ['create_volume_indicator_by_default']` (ctx L65733-65736).
- Spread operators in Compare: `enabled_features: ['show_spread_operators','compare_symbol_search_spread_operators']` (ctx L65692-65706).
- Docs: users cannot see or edit built-in indicator code; Pine Script is not supported; custom indicators are JavaScript Custom Studies (ctx L65620-65650).

#### Study templates

- Chart API: `const t = chart.createStudyTemplate({ saveSymbol?: boolean, saveInterval?: boolean })` returns an object; `chart.applyStudyTemplate(t)` applies it (d.ts L11726-11743).
- Persistence hooks on the save/load adapter: `getAllStudyTemplates()`, `saveStudyTemplate({ name, content })`, `removeStudyTemplate({ name })`, `getStudyTemplateContent({ name })` (d.ts L13579-13595).
- REST backend (`charts_storage_url/charts_storage_api_version/study_templates?client=<id>&user=<id>`): `GET` lists (`{status, data:[{name}]}`); `POST` body `{name, content}` saves; `GET ...&chart=<chart_id>&template=<name>` loads; `DELETE ...&template=<name>` deletes; each returns `status: ok|error` (ctx L50987-51054).

### 3. Session Volume Profile

(ctx L54151-54291; list entry marks it "Trading Platform only", ctx L65232-65497.)

- **What it computes:** one horizontal volume-at-price histogram per trading session, each with Point of Control (POC = row with max volume) and Value Area (price range holding `Value Area Volume` % of the session volume; VAH/VAL edges). Unlike Volume Profile Visible Range / Fixed Range (a single profile), it builds a separate profile per session. A bar spanning several rows spreads its volume across rows in proportion to price overlap (total preserved). Bars outside the selected session are excluded.
- **Forms:** chart type `SeriesType.SVP` = `20` (`widget.activeChart().setChartType(20)`; only profiles drawn, no price bars) or indicator `createStudy('Session Volume Profile', false)` drawn over the current chart type.
- **Inputs (defaults):** `Sessions`=All [All, Each (pre-market, market, post-market), Pre-market only, Market only, Post-market only, Custom]; `Custom session`=`0930-1600` (`HHMM-HHMM` or `HHMM-HHMM:days`); `Custom session timezone`=Exchange (indicator only; chart type uses the chart time zone); `Volume`=Up/Down [Up/Down, Total, Delta]; `Value Area Volume`=70 (0-100); `Rows Layout`=Number Of Rows [Number Of Rows, Ticks Per Row]; `Row Size`=24 (1-1000000); `Extend POC/VAH/VAL Right`=false. `All` = one profile per trading day; the per-phase values need a symbol with pre/post-market subsessions (otherwise every in-session bar counts as market hours); `Custom` = one profile per occurrence of the window.
- **Plots (indicator overrides, `SessionVolumeProfileIndicatorOverrides`, d.ts L21159):** `developing poc` (default `#f44336`), `developing va high`, `developing va low` (default `#2962ff`), all `step_line`, `display` default 0 (hidden). Chart-type customisation: `mainSeriesProperties.svpStyle.*` via `overrides` or `getSeries().setChartStyleProperties(20, { inputs: { profilesSessions: 'Each (pre-market, market, post-market)', rows: 48 }, poc: { visible: true, linewidth: 2 } })`.
- **Datafeed requirements:** bars must carry volume (else the indicator errors). Supported resolutions: intraday and `1D` (2D/weekly/monthly error). It may request a finer "detail" series through the normal `getBars`: if you implement `getVolumeProfileResolutionForPeriod` and return a finer resolution, that is used; otherwise it picks the advertised resolution closest to (not coarser than) its internal default, else the finest advertised resolution finer than the chart, else the chart's own bars. Advertised resolutions come from `LibrarySymbolInfo.supported_resolutions` (or datafeed config); `has_seconds`/`has_ticks` respected. Tick charts always use their own tick bars. Serve the detail resolution or reject it via `onErrorCallback`.
- **History/performance:** by default profiles cover only the history the chart has loaded. Widget option `volume_profile: { history_sessions: N, max_total_rows: M }`: `history_sessions` (1-500) prefetches that many sessions, needs `enabled_features: ['studies_extend_time_scale']` (extends the shared time scale for every source), contributes at most 200,000 bars to each series' `countBack`; `max_total_rows` (default 6000, values < 100 ignored) caps total rows across all profiles; past it the oldest profiles are dropped (SVP) or the indicator errors (Visible/Fixed Range, single profile). `max_total_rows` applies to all volume-profile indicators.

### 4. Gotchas from the docs

1. Names must match the Indicators dialog exactly (case and punctuation); the list uses `Elder's Force Index` and `True Strength Indicator`, while the volume-blacklist example writes `Elders Force Index` and `d.ts` overrides use `true strength index`. Validate against `widget.getStudiesList()` before hard-coding (ctx L65654-65662, L65717-65732; d.ts L12550).
2. `forceOverlay` only affects non-price indicators and never the price scale; price indicators cannot be created on their own pane, only moved afterwards (ctx L65520-65535).
3. Overrides key shape differs by call site: study name **included** for `studies_overrides`/`applyStudiesOverrides`, **omitted** for `createStudy`/`applyOverrides`. Use the UI plot name (`plot`), not the internal id from `getStudyStyles` (`plot_0`) (ctx L46917-47040).
4. `applyStudiesOverrides` and `studies_overrides` do not change studies already on the chart; use `IStudyApi.applyOverrides` (ctx L46793-46813).
5. `inputs` for `createStudy` are keyed by input id (`length`, `in_0`...), not always by the UI label; the docs MACD example uses positional ids. Read ids with `getStudyInputs`/`getInputsInfo` (ctx L65654-65672).
6. Ambiguous identifier errors (e.g. MA Cross `short`/`long`) need `:plot`/`:input`/`:band`/`:area` suffixes (ctx L47103-47154). The docs' own MA Cross example passes `false` as the `inputs` argument and puts input values in the overrides object; prefer `inputs` for inputs.
7. Colors accept `#RRGGBB` only; area-fill color/transparency not customisable; the stated transparency direction (100 = opaque) is unusual, so check visually (ctx L47089-47094).
8. A pane holds at most 8 price scales; `new-left/new-right` then silently become `no-scale` (ctx L65556-65560).
9. `unmerge*` does not work if the study is the only source on its pane; `merge*` needs the neighbouring pane to exist (d.ts L15078-15096).
10. Hide volume-based indicators explicitly when the datafeed has no volume; VWAP counts as volume-based (ctx L65717-65732).
11. `study_count_limit` minimum is 2 (d.ts L5098-5103).
12. Session Volume Profile: Trading Platform only per the list; needs volume; intraday or 1D only; the extra detail-resolution request goes through `getBars`; `history_sessions` has no effect without `studies_extend_time_scale` (ctx L54222-54291).
13. `Compare` lacks "Allow extend time scale" and legend logos; `Overlay` supports them (ctx L65674-65690).
14. Built-in `*IndicatorOverrides` interfaces contain style keys only; inputs are never settable through `overrides` (d.ts L20285 onward); use `inputs` or `setInputValues`.
15. TradingView docs do not specify smoothing (RMA vs EMA), seeding, or stdev convention (population vs sample) for any built-in; compare numerically before trusting equivalence.

### Use in solmargintrader

Repo facts are cited from `backtester/core/indicators.py` (`indicators.py`, used by the strategy cards in `backtester/strategy_cards/*.md`) and `backtester/core/scorecard.py` (`scorecard.py`, the Compound 5m metrics). TradingView facts come from the sections above; anything marked "(verify)" is a standard-definition assumption, not stated in the TV docs.

Chart setup that makes the display comparable: resolution `5` for Compound 5m (daily/hourly for the cards' presets), symbol timezone `Etc/UTC`, and the same OHLCV the backtester ingests (Coinbase, Hyperliquid and Jupiter-oracle bars have different volume semantics). Read indicator values from the **last closed bar**: the forming bar repaints, the backtester scores closed bars only.

#### Strategy card to TradingView study

| Repo strategy (defaults) | createStudy name | Input mapping | Differences to watch |
| --- | --- | --- | --- |
| `sma_regime` (SMA 200; presets 168/100/200) | `Moving Average` | `length`=window, `source`=close, `offset`=0 | TV default `length` is 9. Docs do not state the MA type of this study; SMA presumed (verify). Leave `smoothed ma` hidden (display 0 by default). |
| `ma_crossover` (SMA 20/50; presets 12/48, 50/200) | `MA Cross` or 2x `Moving Average` | `MA Cross`: `short:input`=fast, `long:input`=slow (TV defaults 9/26) | Ambiguous names, so use `:input`/`:plot` suffixes. `MA Cross` average type undocumented (verify SMA). Two `Moving Average` studies avoid the ambiguity. |
| `ema_crossover` (EMA 50/200; presets 10/30, 20/50) | `EMA Cross` or 2x `Moving Average Exponential` | `EMA Cross`: `short:input`, `long:input` (defaults 9/26); EMA: `length`, `source`=close, `offset`=0 | `indicators.ema` seeds with the SMA of the oldest window and caps the recursion at 12x span; `scorecard.ema` is pandas `ewm(adjust=False)` seeded by the first value. TV seed not documented; start-up differences decay over roughly 3x-12x span bars. |
| `ma_ribbon` (windows=5, base=10, so SMA 10/20/30/40/50) | `Moving Average Multiple` | `1st period`=10, `2nd period`=20, `3rd period`=30, `4th period`=40, `5th period`=50, `method`=Simple | TV always has 6 periods (defaults 14/21/35/50/100/200): set `6th period`=60 or hide `plot 6` with `'plot 6.display': 0`. The repo score (share of adjacent pairs ordered) is not drawn. |
| `macd` (12/26/9) | `MACD` | `fast length`=12, `slow length`=26, `source`=close, `signal length`=9, `oscillator ma type`=EMA, `signal line ma type`=EMA | Exact input match and defaults. Repo hist = MACD - signal, signal = EMA of the MACD series. `scorecard._c_macd` then divides by `0.25*ATR`; TV shows the raw histogram. Resolve input ids with `getStudyInputs('MACD')` before using `inputs`. |
| `ppo` (12/26/9) | `Price Oscillator` (partial) | `shortlen`=12, `longlen`=26 | TV defaults 10/21. Only two inputs are listed: no signal line (repo uses EMA9 of PPO) and no stated percent-vs-absolute mode (verify). A faithful display needs a custom study. |
| `rsi` (period 14, oversold 30, exit 50) | `Relative Strength Index` | `length`=14; bands via overrides `upperlimit.value`, `middlelimit.value`=50, `lowerlimit.value`=30 | Repo RSI is Wilder (alpha=1/n): SMA seed in `indicators.rsi`, pandas `ewm(alpha=1/n, adjust=False)` in `scorecard.rsi_series`. TV smoothing and `source` are not listed (RMA presumed, verify). Default bands 70/50/30 already match the card's 30/50 levels. Keep `smoothing line` (default SMA, 14) hidden. |
| `stochastic` (k 14, d 3; enter %K<20 and %K>%D, exit %K>80) | `Stochastic` | `%k length`=14, `%k smoothing`=1, `%d smoothing`=3 | Repo %K is raw and %D = SMA(3) of %K; `%k smoothing`=1 reproduces this (SMA %D presumed, verify). Default bands 80/20 equal the card levels. Long preset: `%k length`=40, `%d smoothing`=5. |
| `bb_reversion`, `bb_breakout` (window 20, k 2.0; long 60) | `Bollinger Bands` | `length`=20, `mult`=2 | Repo stdev is population (ddof=0) in both `indicators.bollinger` and `scorecard.rstd`, which is Bollinger's own convention; TV convention is not documented (verify). Basis MA type not listed. For the squeeze gate use `Bollinger Bands Width` with the same `length`/`mult` (verify it is (upper-lower)/basis, the repo's `bandwidth`). |
| `zscore` (window 20, entry -2, exit 0; ddof=1) | none built in. Use `Bollinger Bands %B` (`length`=window, `mult`=2) | z_pop = `mult` * (2*%B - 1); z_sample = z_pop * sqrt((n-1)/n) | **Convention clash inside the repo:** the card and `indicators.zscore` use sample stdev (ddof=1); `scorecard._c_zscore` uses `rstd` ddof=0 (population). BB-based z equals the Compound 5m z-score exactly; the card z-score is about 2.5% smaller at n=20. `Standard Deviation` (inputs `periods`=5, `deviations`=1) convention is not documented. |
| `breakout` (Donchian entry 20 / exit 10) | `Donchian Channels` x2 | `length`=20 (entry) and `length`=10 (exit), `offset`=0 | Repo channels EXCLUDE the current bar (`Upper_t = max(H_{t-n}..H_{t-1})`); the standard Donchian includes it (verify). Compare close with the previous bar's channel, or try `offset`=1 (offset direction is not documented; test on the chart). |
| `fib_retracement` (lookback 60; entry 0.382, invalid 0.786) | `Donchian Channels` for the swing + fib drawing | `length`=lookback (swing high = `upper`, swing low = `lower`) | No Fib built-in indicator. Level = high - (high-low)*r; draw with the `fib_retracement` drawing tool (in `SupportedLineTools`, d.ts L31429) or plot levels from a custom study. Donchian includes the current bar; the card's window ends at the bar (verify alignment). |
| `ichimoku_cloud` (9/26/52, displacement 26; long 18/52/104/52) | `Ichimoku Cloud` | `conversion line periods`=9, `base line periods`=26, `leading span periods`=52, `lagging span periods`=26, `leading shift periods`=26 | Direct mapping: tenkan, kijun, senkou_b, displacement. Both plot the cloud shifted forward; the repo compares today's close with the cloud computed `displacement` bars ago (no look-ahead). Long preset: 18/52/104 and shift 52. |
| `keltner` (EMA 20, ATR 14, mult 2.0) | `Keltner Channels` | `length`=20, `mult`=2, `usetruerange`=true | **TV default `mult` is 1, not 2.** Only one `length`: EMA span and ATR period cannot differ (card has 20 and 14). ATR smoothing and MA type not listed. Expect a different band width (verify). |
| `atr_position_sizing` (Wilder ATR 14, SMA 100 gate) | `Average True Range` + `Moving Average` | ATR `length`=14; MA `length`=100 | ATR smoothing not documented (Wilder/RMA expected, verify). Repo ATR: SMA-seeded Wilder (`indicators.atr`) or pandas Wilder (`scorecard.atr`). Sizing math is not displayable. |
| `adx_filtered_trend` (period 14, threshold 25) | `Directional Movement` (+DI, -DI, ADX) or `Average Directional Index` | `di length`=14, `adx smoothing`=14 | TV has two lengths; the repo uses one period for both (set equal). No threshold input: add a horizontal line drawing. Threshold: card 25, Compound `adx_dmi` 20. Smoothing method not documented (repo = Wilder). |
| `obv_trend` (OBV > SMA(20)) | `On Balance Volume` | `smoothing line`=SMA, `smoothing length`=20 | The `smoothed ma` plot is hidden by default; enable with `'smoothed ma.display': 15`. Absolute OBV differs by a constant (history start) but OBV minus SMA(OBV) is offset-invariant, so the crossover matches. |
| `vwap_reversion` (rolling VWAP 20 bars, 2% discount) | `VWAP` (session) or `VWMA` (rolling proxy) | `VWAP`: `source`=hlc3, `anchor period`=Session. `VWMA`: `len`=20 | `VWAP` has no rolling-window mode: it resets per anchor. Compound 5m `mode=0` resets at 00:00 UTC (`ts // 86400`); a TV 24x7 symbol with timezone `Etc/UTC` should reset there (verify against the symbol's `session`/`timezone`). `hlc3` default equals the repo typical price. `VWMA` weights the chosen source (close), not typical price, so it only approximates `rolling_vwap`. |
| `ts_momentum` (ROC 60 > 0; decimal return) | `Rate Of Change` (or `Momentum`) | `length`=60 | TV default 9. Standard ROC is a percent, 100x the repo's decimal (verify); the `zero line` is a plot. `Momentum` (`length`, `source`) is the absolute difference. |
| `voltarget`, `garch_vol_forecast`, `vol_regime_hmm` (realised vol window 20, 365 periods/yr, ddof=1; trend SMA 100) | `Historical Volatility` or `Volatility Close-to-Close`, plus `Moving Average` | HV: `length`=20. Close-to-close: `periods`=20, `days per year`=365 | TV defaults: HV `length` 10; close-to-close `days per year` 252 (repo crypto uses 365). TV output is a percent; repo `target_vol: 0.6` means 60. HV annualisation and stdev convention not documented. `garch_vol_forecast` (EWMA lambda 0.94) and `vol_regime_hmm` (trailing quantile of vol) have no built-in: custom study. |
| `swing_confluence` (breakout 20, SMA 50, MACD hist>0, RSI14>50, OBV>SMA20, exit 10) | `Donchian Channels`, `Moving Average`, `MACD`, `Relative Strength Index`, `On Balance Volume` | per the rows above | Four confirmations are separate studies; the vote count is not drawn. The Donchian current-bar caveat applies. |
| `hurst_regime_test`, `kalman_hedge_ratio`, `pairs_cointegration`, `avellaneda_stoikov_mm`, funding/OI/order-book strategies | not listed | no built-in | Not in the built-in list (`Correlation Coefficient`, `Ratio`, `Spread` exist but are not these models). |

(Names from ctx L65232-65497, defaults from d.ts L22397-27586; repo parameters from the strategy cards' `params:` blocks and `scorecard.py` COMPONENTS, L875-1100.)

#### Compound 5m scorecard metrics (SOL and ~10 coins, 5m bars)

Each metric is a -1..+1 score (mostly `tanh`/`clip` of ATR- or window-scaled distances). TradingView can draw the underlying study, not the scaled score.

| Compound metric id (defaults) | TV study for the underlying | Input mapping | Notes |
| --- | --- | --- | --- |
| `ema_cross` (fast 9, slow 21, scale 0.5, ATR 14) | `EMA Cross` | `short:input`=9, `long:input`=21 | TV defaults 9/26. Add `Average True Range` `length`=14 for the `tanh((EMA_f-EMA_s)/(0.5*ATR))` denominator. |
| `ema_trend` (span 50) | `Moving Average Exponential` | `length`=50 | |
| `macd` (12/26/9, scale 0.25) | `MACD` | TV defaults | Histogram shown raw. |
| `adx_dmi` (period 14, threshold 20) | `Directional Movement` | `di length`=14, `adx smoothing`=14 | Threshold line is manual. |
| `vwap_side`, `vwap_reversion` (mode 0 = UTC session; mode 1 = 48-bar rolling; distance scaled by RMS over 288 bars, floored at ATR) | `VWAP` | `source`=hlc3, `anchor period`=Session | Scaled distance and rolling mode are not available (see the `VWMA` caveat). |
| `ichimoku` (9/26/52; default-disabled) | `Ichimoku Cloud` | as above (`leading shift periods`=26) | Score 0.5 / 1.0 by cloud side and tenkan vs kijun. |
| `roc` (window 12, vol-scaled) | `Rate Of Change` | `length`=12 | Repo uses log return divided by sigma*sqrt(n); TV plots percent ROC (verify). |
| `rsi` (14, oversold 30, overbought 70) | `Relative Strength Index` | `length`=14 | Defaults match. |
| `stochastic` (k 14, d 3, oversold 20) | `Stochastic` | `%k length`=14, `%k smoothing`=1, `%d smoothing`=3 | |
| `cci` (period 20, extreme 150; default-disabled) | `Commodity Channel Index` | `length`=20; overrides `upperlimit.value`=150, `lowerlimit.value`=-150 | TV default bands +/-100; hide the `smoothed ma` (default SMA 20). Repo uses mean absolute deviation and 0.015 (standard; verify TV). |
| `bollinger` (20, k 2; score = clip(1 - 2*%B)) | `Bollinger Bands %B` | `length`=20, `mult`=2 | TV bands 0 and 1; population stdev. |
| `zscore` (window 48, entry 2) | `Bollinger Bands %B` (derive) | `length`=48, `mult`=2; z = 2*(2*%B - 1) | Population stdev (`rstd` ddof=0). |
| `donchian` (window 20, hold 3) | `Donchian Channels` | `length`=20 | Repo uses the prior-bar channel (`prior(...,1)`) and holds the signal 3 bars. |
| `squeeze` (BB 20/2, bandwidth percentile <= 20 over 288 bars, volume > 1.5x) | `Bollinger Bands Width` and `Volume` | `length`=20, `mult`=2; `Volume`: `show ma`=true, `ma length`=20 | Percentile rank and volume multiple are not built in. |
| `trend_continuation` (VWAP + EMA 9/21 + volume > 1.2x) | `VWAP`, `EMA Cross`, `Volume` | as above | Composite rule. |
| `liquidity_sweep` (lookback 24) | `Donchian Channels` shows the prior range | `length`=24 | Sweep logic not built in. |
| `zigzag` (pct 0.5, non-repainting) | `Zig Zag` | `deviation`=0.5, `depth`=10 | TV default deviation is 5, and the TV study repaints; the repo confirms a pivot only after the reversal and never moves it. |
| `fib_pullback` (swing 48, trend EMA 50, zone 0.382-0.618) | `Donchian Channels` (`length`=48) + `Moving Average Exponential` (`length`=50) + fib drawing | | Drawing tool for the zone. |
| `obv` (window 20) | `On Balance Volume` | `smoothing line`=SMA, `smoothing length`=20 | |
| `volume` (window 48) | `Volume` | `show ma`=true, `ma length`=48, `volume ma:input`=SMA | Repo compares with the prior-bar average volume. |
| `bop` (window 14) | `Balance of Power` | none listed | No smoothing input listed; the repo averages 14 bars. |
| `money_flow` (window 20) | `Chaikin Money Flow` | `length`=20 | |
| `htf_trend` (60m EMA 20 of completed HTF bars) | none; nearest is `Moving Average Exponential` | not listed (no resolution input in docs/types) | Needs a higher-timeframe chart or a custom study. |
| `persistence`, `funding`, `premium`, `oi_flow`, `book_imbalance`, `btc_lead`, `trend_lifecycle`, `cycle_phase`, `gate_*` | not listed | no built-in | Non-price data or custom logic. `Correlation Coefficient` (inputs `sym`, `length`=20) can show cross-asset correlation but not the lead metric. |

(scorecard.py L875-1100 for ids and defaults.)

#### Where TradingView defaults or smoothing could diverge from the Python implementation

1. **Wilder vs EMA smoothing.** Repo RSI, ATR and ADX/DMI use Wilder (alpha=1/n) (`indicators.wilder_smooth`, `scorecard.wilder`). TV docs expose `adx smoothing` for ADX but state no smoothing for RSI or ATR (RMA expected, verify).
2. **EMA seeding.** `indicators.ema`: SMA seed, recursion capped at 12x span. `scorecard.ema`: first-value seed with `min_periods=span`. TV undocumented. A chart with a few hundred bars shows small start-up differences that decay.
3. **Stdev convention.** Bollinger and `scorecard.rstd`: population (ddof=0). `indicators.zscore` and realised vol: sample (ddof=1). The card `zscore` is sample, the Compound `zscore` is population (they differ by sqrt(n/(n-1))). TV docs do not say which `Standard Deviation` / `Historical Volatility` use.
4. **Different TV defaults vs repo defaults.** Keltner `mult` 1 (repo 2); Price Oscillator 10/21 (repo 12/26); Moving Average `length` 9 (repo 200/50/20); EMA Cross and MA Cross 9/26 (repo 9/21 in Compound, 20/50 or 50/200 in cards); Historical Volatility `length` 10 (repo 20); Volatility Close-to-Close `days per year` 252 (repo 365); Zig Zag `deviation` 5 (repo 0.5). These match: Donchian `length` 20, Stochastic 14/1/3, MACD 12/26/9, RSI 14, Bollinger 20/2, Ichimoku 9/26/52/26/26, ADX 14, ATR 14.
5. **Units.** TV ROC and Historical Volatility are percent (standard definition, verify); the repo uses decimals (`target_vol: 0.6`, `roc` as a fraction).
6. **Bar inclusion and look-ahead.** Repo Donchian, breakout and sweep use the prior window (current bar excluded); the standard Donchian includes the current bar. TV's forward-shifted Ichimoku cloud and repainting Zig Zag are display-oriented; the repo deliberately avoids reading both at the current bar.
7. **VWAP reset.** Repo session VWAP resets at 00:00 UTC; TV resets per the symbol's session settings; there is no rolling-N VWAP built in.
8. **Single `length` limits.** Keltner exposes one `length` for both EMA and ATR in the listed inputs; the repo has separate `ema_span` and `atr_period`.
9. **Volume semantics.** OBV, CMF, VWAP and `Volume` depend on the datafeed's volume field (Coinbase base-asset vs Hyperliquid vs Jupiter). The chart matches the backtester only if both read the same bars.
10. **Intrabar vs closed bar.** TV recomputes on the forming bar; the backtester scores closed bars. Compare against `bar[1]`.
11. **Unlisted inputs.** RSI `source`, ATR smoothing, Bollinger basis MA type and Stochastic MA type are not listed in the docs/types. To pin them, call `widget.getStudyInputs(name)` at runtime and copy the ids into `inputs`.

#### Minimal repo chart preset (example, not run)

```js
widget.onChartReady(async () => {
  const c = widget.activeChart();
  await c.createStudy('Moving Average', false, false, { length: 200 });                         // sma_regime
  await c.createStudy('Bollinger Bands', false, false, { length: 20, mult: 2 });                // bb_* (confirm ids via getStudyInputs)
  await c.createStudy('Relative Strength Index', false, false, { length: 14 }, { 'lowerlimit.value': 30 });
  await c.createStudy('MACD', false, false);                                                    // 12/26/9 defaults
  await c.createStudy('Stochastic', false, false);                                              // 14/1/3 defaults
  await c.createStudy('Ichimoku Cloud', false, false);                                          // 9/26/52/26/26 defaults
  await c.createStudy('VWAP', false, false);                                                    // session anchor, hlc3
});
```

The input ids in `inputs` above (`length`, `mult`) follow the style of the docs' `Moving Average Exponential` example; confirm the ids per study first.

## Custom indicators and PineJS

Sources: `tradingview/charting-library-context.txt` (cited `ctx L<a>-<b>`) and `tradingview/charting_library.d.ts` (cited `d.ts L<n>`). Content is paraphrased; identifiers are exact. Pine Script is NOT supported in the library; indicators are plain JavaScript (ctx L43275-43279).

### 1. Architecture

**Registration.** `custom_indicators_getter: (PineJS) => Promise<readonly (CustomIndicator | StudyScript)[]>` is a widget-constructor option. The library calls it once and passes `PineJS` (object with `PineJS.Std`, the `PineJSStd` function library). Resolve an array of indicator objects (ctx L43281-43297; d.ts L5486-5498).

**Indicator object (`CustomIndicator`)** (ctx L43299-43322; d.ts L6494-6510):

| Field | Meaning |
|---|---|
| `name` | Internal unique name, not shown in UI. |
| `metainfo` | `StudyMetaInfo`: plots, inputs, styles, defaults, placement. Built once; cannot change after the chart is created (ctx L43706-43710). |
| `constructor` | ES5 constructor function (`function () { this.init = ...; this.main = ... }`). The library applies `new` to it (ctx L43183). Arrow functions and classes are not the documented form. |

**Lifecycle** (ctx L43185-43247; d.ts L16290-16316, L6504-6508):
1. After the instance is created, the library calls `init` (if defined) then `main` once each with an *empty context* to discover all variables (d.ts L6504-6508). Guard against NaN/undefined values on this call (the "Mondays" example returns `[NaN]` when `isNaN(context.symbol.time)`, ctx L41353-41355).
2. `init(ctx, inputCallback)` is optional. It runs when the indicator is calculated from scratch: added to chart, added to a new pane, symbol change, resolution change, extra history loaded (ctx L43194-43202). Use it for one-time setup such as `ctx.new_sym(...)` (ctx L43209-43215).
3. `main(ctx, inputCallback)` is required. The library calls it **once per bar of the main series, oldest to newest**. With extra symbols, it calls `main` for every bar of each additional series first, then for the main series (ctx L43219-43226). d.ts says `main` runs "for every bar of every symbol", so extra symbols raise the run count (d.ts L16305-16309).
4. `main` returns the values for the current bar (see "Output" below).

**Arguments.**
- `ctx` (`IContext`, d.ts L12979-13029): `ctx.symbol` (`ISymbolInstrument`: `time`, `open/high/low/close/volume`, `period`, `ticker`, `tickerid`, `index`, `minTick`, `isFirstBar`, `isLastBar`, `isNewBar`, `isBarClosed`, `updatetime`, `info`, `bartime()`, `isdwm()`; d.ts L15239-15296), `new_sym(tickerid, period, currencyCode?, unitId?, subsessionId?)`, `select_sym(i)` (0 = main series), `new_var(value?)`, `new_unlimited_var(value?)`, `new_ctx()`, `is_main_symbol(sym)`, `setMinimumAdditionalDepth(n)`.
- `inputCallback(i)` (conventionally stored as `this._input`): returns the i-th input value, index = position in `metainfo.inputs` (ctx L43188, L43610-43627). `type:'source'` inputs return a string such as `'close'`; resolve with `PineJS.Std[name](ctx)` (ctx L56536-56537).
- Convention: `this._context = ctx; this._input = inputCallback;` at the top of `init`/`main` (all docs examples).

**Series vs values.**
- Std OHLCV accessors (`Std.close(ctx)`, ...) return the *current bar's number*.
- Anything that needs history takes an `IPineSeries` made by `ctx.new_var(value)` (d.ts L12999-13007; L14215-14290). Pattern: `const s = ctx.new_var(Std.close(ctx)); const m = Std.sma(s, 20, ctx);` (ctx L56566-56578).
- `IPineSeries.get(n)`: n=0 current value, `get(1)` previous bar, `get(2)` two bars back (d.ts L14215-14228: "indices are opposite"). `set(value)` overwrites the current slot. `indexOf(time)` finds the bar index at a timestamp. `adopt(source, destination, mode)` maps values between time scales (see below).
- `new_var` keeps depth set by the first `.get(n)` call; `new_unlimited_var` keeps all history (d.ts L12998-13007). `Std.max_series_default_size = 10001` (d.ts L18285).
- "On each iteration you can get information about previous bars only ... the library does not provide future bars, and you should not use them" (ctx L43230-43232).

**Output of `main`** (ctx L43237-43247, L41867-41884):
- Return one number, or an array with **one element per entry of `metainfo.plots`, in plots order**. Colorer, OHLC and dataoffset plots are plots too and need their own element (e.g. `[value, colorIndex]`; `[o,h,l,c,colourBar,colourWick,colourBorder]`).
- Each element is a number, or `{ value, offset }` to display the value `offset` bars ahead/behind (`StudyResultValueWithOffset`, d.ts L27728-27739; ctx L43247). Offset is a display shift only.
- `NaN` = no value for that plot on that bar (hides a line point or a shape) (ctx L41360-41363). Return type `IPineStudyResult` = `StudyPrimitiveResult` (`(number|{value,offset})[]`) or composite / non-series results (d.ts L31193-31195, L31425).

**Timing, bar order, lookahead, realtime (critical for no-lookahead backtests).**
- Bars are processed in time order and only past data is exposed; future bars are not available (ctx L43230-43232).
- `Std.close(ctx)` is "the close of the current bar when it has closed, or the last traded price of a yet incomplete, realtime bar" (ctx L42358). So on the live bar the value changes tick to tick and `main` re-runs. Use `ctx.symbol.isBarClosed` / `isNewBar` / `isLastBar` (d.ts L15276-15283) to act only on closed bars.
- `Std.time(ctx)` returns UNIX time "according to the symbol timezone and not UTC" (d.ts L18337-18348). Verify unit (ms vs s) empirically before doing day arithmetic. `Bar.time` supplied by the datafeed is ms UTC (d.ts L1818-1826).
- A positive `offset` in the output paints a value on future bars. It is cosmetic and must never feed a signal.
- Extra-symbol data is mapped onto main-series times with `series.adopt(srcTimes, dstTimes, mode)`: mode 0 "continuous" (each destination time gets the source value, may repeat), mode 1 "precise" (each source value at most once; others NaN). Continuous uses the closest later main-series time (ctx L42963-43018; d.ts L14232-14290).

**Placement/format flags.** `is_price_study` (draw on the main pane vs own pane), `linkedToSeries`, `format`, `isCustomIndicator: true` (see Section 2). `Extending the time scale`: set `canExtendTimeScale: true` in metainfo and enable featureset `studies_extend_time_scale` so an indicator may have bars at times absent in the main series (ctx L43019-43150; featureset ctx L44670-44680).

**`setMinimumAdditionalDepth(n)`**: asks the datafeed for `n` extra bars before the visible range. Needed only for chained calculations (an MA of an MA) because the library cannot infer the lookback (ctx L56546-56556; d.ts L13017-13029).

(ctx L43163-43335, L56502-56864; d.ts L12979-13029, L14215-14290, L15239-15296, L16290-16316)

### 2. Metainfo schema

#### 2.1 Top-level fields (`RawStudyMetaInfoBase`, d.ts L20086-20152; ctx L43684-44128)

| Field | Type | Meaning |
|---|---|---|
| `_metainfoVersion` | number | Metadata version. Current = `53`, default `0`. Always set it. (Docs examples use 51 and 53.) |
| `id` | string | Required, unique, format `<name>@tv-basicstudies-1`. |
| `name` | string? | Internal name (optional; used in some examples). |
| `description` | string | Name in Indicators dialog and Object Tree; the `name` argument of `createStudy(...)` must equal it. |
| `shortDescription` | string | Name in Legend, Settings dialog, price-scale label. |
| `scriptIdPart` | string? | Seen as `''` in the OHLC example (ctx L41894); not documented. |
| `is_price_study` | boolean | `true` = draw on the main-series pane; `false` = own pane. |
| `isCustomIndicator` | boolean | Must be `true` for a custom indicator. |
| `is_hidden_study` | boolean | `true` hides it from the Indicators dialog (default `false`). |
| `linkedToSeries` | boolean | `true` = uses the main series' price scale and the series cannot be moved to another pane without it (hides "Move to"). |
| `priceScale` | `StudyTargetPriceScale` (`Right=0`, `Left=1`, `NoScale=2`) | Target price scale. |
| `overlayScaleMargins` | `{top, bottom}` fractions of pane height | When on the series pane, indicator has no visible scale and occupies the area per margins (like built-in Volume `{top:0.75,bottom:0}`). Negative or sum >= 1 is rejected with a console warning (ctx L44086-44105; d.ts L22385-22390). |
| `format` | `{type:'inherit'}` or `{type:'price'\|'volume'\|'percent', precision?}` | Price-scale/legend value type. `inherit` copies the source symbol (ctx L43780-43792; d.ts L27694-27703). |
| `precision` | number\|string | Deprecated; use `format`. |
| `inputs` | `StudyInputInfo[]` | Settings-dialog inputs (2.3). |
| `symbolSource` | `{type:'symbolInputSymbolSource', inputId}` | Use a symbol input as the data source (d.ts L28436-28442). |
| `plots` | `StudyPlotInfo[]` | Visual/data series (2.2). Order = order of `main` return array. |
| `styles` | `{[plotId]: StudyStylesInfo}` | Fixed, non-user-editable plot properties (below). |
| `ohlcPlots` | `{[ohlcPlotId]: StudyOhlcStylesInfo}` | OHLC meta-plots (2.2). |
| `defaults` | `StudyDefaults` | Defaults for inputs, styles, palettes, bands, filled areas, ohlcPlots, precision, graphics (2.4). |
| `palettes` | `{[paletteId]: {colors, valToIndex?, addDefaultColor?}}` | Palette definitions for colorer plots. |
| `bands` | `StudyBandInfo[]` | Horizontal lines the user cannot add/remove. |
| `filledAreas` | `StudyFilledAreaInfo[]` | Coloured area between two plots or two bands (not band-to-plot). |
| `canExtendTimeScale` | boolean | With featureset `studies_extend_time_scale`, allow bars outside main-series times. |
| `financialPeriod` | `FinancialPeriodOrAggregated` | Financial indicators only. |
| `groupingKey` | string | Groups indicators. |
| `behind_chart` | boolean | Series-level indicator (behind chart). |
| `graphics` | n/a | Not a typed metainfo field in `RawStudyMetaInfoBase`; only `defaults.graphics` (`horizlines`, `polygons`, `hhists`, `vertlines`, d.ts L22180-22190) exists. Used by Pine-script-style indicators. Gap: no custom-indicator `graphics` docs found. |

`StudyStylesInfo` (per plot id; d.ts L27915-27967): `title` (required, Styles-tab label and override path), `histogramBase`, `joinPoints` (Circles/Cross only), `isHidden`, `minHeight`/`maxHeight` (arrows), `size` (`PlotSymbolSize` or number: `auto|tiny|small|normal|large|huge`; chars/shapes), `char` (chars), `text` (chars/shapes), `showLast`, `zorder`, `format` (`Partial<StudyPlotValuePrecisionFormat>`), `forceOverlay`. The Mondays example also sets `location` inside `styles`.

`StudyBandInfo` (d.ts L21848-21869): `id?`, `name`, `isHidden?`, `zorder?`. Style/value/visibility of each band goes in `defaults.bands[i]` = `{color, linestyle, linewidth, value, visible}` (ctx L43347-43352, L43940-43962). Bands match `defaults.bands` by array index.

`StudyFilledAreaInfo` (d.ts L22083-22152): `id`, `objAId`, `objBId` (band ids or plot ids), `title`, `type` (`FilledAreaType`: `'plot_plot'` or `'hline_hline'`), `fillgaps?`, `zorder?`, `isHidden?`, `palette?`, `topValue?`, `bottomValue?`, `topColor?`, `bottomColor?`, `fillToIntersection?` (plot_plot only). Defaults in `defaults.filledAreasStyle[id]`: solid `{color, visible, transparency?(0-100)}` or gradient `{fillType:'gradient', visible, transparency?, topColor?, bottomColor?, topValue?, bottomValue?}` (d.ts L22056-22081, L22154-22176; ctx L43353-43356). Gradient fills can be driven by targeted plots via `targetField` in `StudyTargetedPlotInfo` (`topColor|bottomColor|topValue|bottomValue`, d.ts L27980-27991); the docs link a CodePen "Complex Filled Areas" but the context contains no code for it (gap).

`palettes` entry (d.ts L27648-27663): `colors` = `{[idx]: {name}}` or `[{name}, ...]`; `valToIndex` maps the numeric value returned by `main` to a colour index; `addDefaultColor` uses the default colour for colorer plots when the value is NaN/null. Defaults in `defaults.palettes[id].colors` = `[{color,style,width}, ...]` or `{[idx]: {color,style,width}}` (d.ts L27590-27637, L22002-22025).

#### 2.2 Plot types (`StudyPlotType`, d.ts L618-640; plot field reference ctx L41968-42119, defaults ctx L43368-43453)

Every plot needs `{id, type}`. Defaults for each plot id go under `defaults.styles[id]` (`ohlcPlots` for OHLC). All style defaults accept `visible`, `transparency` (1-100), `display` (bitmask of `StudyPlotDisplayTarget`: None 0, Pane 1, DataWindow 2, PriceScale 4, StatusLine 8, All 4294967295; d.ts L27678-27692, L600-617).

| `type` | Plot-info fields | Style fields (`defaults.styles[id]`) | Meaning |
|---|---|---|---|
| `line` | `id,type` | `plottype` (`LineStudyPlotStyle`: 0 Line, 1 Histogram, 3 Cross, 4 Area, 5 Columns, 6 Circles, 7 LineWithBreaks, 8 AreaWithBreaks, 9 StepLine, 10 StepLineWithDiamonds, 11 StepLineWithBreaks; d.ts L351-396), `color`, `linestyle` (`LineStyle` 0 Solid, 1 Dotted, 2 Dashed), `linewidth`, `trackPrice` (price line), `showLast?` | Numeric series. User can switch plot style in UI, so set `histogramBase`/`joinPoints` in `styles` too (ctx L57042). |
| `shapes` | `id,type` | `plottype` (`PlotShapeId`: `shape_arrow_down, shape_arrow_up, shape_circle, shape_cross, shape_xcross, shape_diamond, shape_flag, shape_square, shape_label_down, shape_label_up, shape_triangle_down, shape_triangle_up`; d.ts L31312), `location` (`MarkLocation`: `AboveBar, BelowBar, Top, Bottom, Right, Left, Absolute, AbsoluteUp, AbsoluteDown`; d.ts L404-415), `color`, `textColor`, `size` (`PlotSymbolSize`; controls height only, width follows bar width; ctx L43413-43417) | Marker on bars where the value is not NaN; value shown in legend (ctx L41360-41362). |
| `chars` | `id,type` | `char`, `location`, `color`, `textColor` | Single character marker. |
| `arrows` | `id,type` | `colorup`, `colordown`, `minHeight?`, `maxHeight?` | Up/down arrows sized by value (d.ts L21801-21822). |
| `colorer` | `id,type,palette,target` | via `defaults.palettes` | Per-point colour/style/width of the `target` plot. `main` returns the palette key/colour index in this plot's slot. |
| `bar_colorer` | `id,type,palette` | via palettes | Colours main-series bars (index via `valToIndex`). |
| `bg_colorer` | `id,type,palette` | via palettes | Colours pane background. |
| `text_colorer` | `id,type,palette,target` | via palettes | Colours text of `target`. |
| `ohlc_colorer` | `id,type,palette,target` | via palettes | Colours OHLC bar/candle body (`target` = ohlc plot id). |
| `wick_colorer` (`CandleWickColorer`) | `id,type,palette,target` | via palettes | Candle wick colour. |
| `border_colorer` (`CandleBorderColorer`) | `id,type,palette,target` | via palettes | Candle border colour. |
| `up_colorer`, `down_colorer` | `id,type,palette,target` | via palettes | Up/down candle colour (d.ts L22027-22031, L28048-28052). |
| `data` | `id,type,target,targetField?` | n/a | Non-visual data plot for a target (e.g. gradient values). |
| `dataoffset` | `id,type,target` | n/a | Per-point offset for the target plot (ctx L42030-42033). |
| `ohlc_open`/`ohlc_high`/`ohlc_low`/`ohlc_close` | `id,type,target` (= ohlcPlots key) | `defaults.ohlcPlots[target]`: `plottype` (`'ohlc_bars'` or `'ohlc_candles'`; `OhlcStudyPlotStyle`), `color`, `visible`, `display`; candles also `drawWick`, `drawBorder`, `wickColor`, `borderColor` | All four must be declared per OHLC plot; order in `main` return = order in `plots`. `ohlcPlots[target]` = `{title (required), isHidden, drawBorder, showLast, forceOverlay, format}` (ctx L41788-41964; d.ts L22319-22367). |

`rgba` colorer exists in d.ts (`StudyRgbaColorerPlotInfo`, type `colorer` with `target`, d.ts L27741) but is undocumented in the docs.

#### 2.3 Input types (`StudyInputType`, d.ts L595-609; interfaces d.ts L22196-22215, L21911-21935, L21975-21982, L22296-22309, L27704-27735, L27745-27753, L27793-27802, L27969-27978, L28019-28047)

Common fields (`StudyInputBaseInfo`): `id` (referenced by `defaults.inputs`), `name` (label), `type`, `defval`, `confirm?` (ask user to confirm before adding), `isHidden?`, `visible?` (string), `isAlwaysShownInLegend?`, `hideWhenPlotsHidden?: string[]` (plot ids whose hiding also hides this input in legend), `active?`, `group?` (header text shared by inputs with the same string; ctx L43532, L43629-43663).

| `type` | Extra properties | `defval` | Notes |
|---|---|---|---|
| `integer` | `min?`, `max?`, `step?` | number | Numeric. |
| `float` | `min?`, `max?`, `step?` | number | Numeric. |
| `price` | `min?`, `max?`, `step?` | number | Price-valued numeric. |
| `bool` | n/a | boolean | Checkbox. |
| `text` | `options?: string[]`, `optionsTitles?: {[option]: label}` | string | Drop-down when `options` given (e.g. `["SMA","EMA","WMA"]`). |
| `source` | `options?: (StudyPriceSource\|string)[]`, `optionsTitles?` | string | `StudyPriceSource` = `open|high|low|close|volume|hl2|hlc3|ohlc4|hlcc4` (d.ts L31424). Value used as `Std[value](ctx)`. |
| `symbol` | `optional?: boolean` | string | `''` = none; used with `new_sym` (ctx L43019-43150). |
| `resolution` | `options?`, `optionsTitles?`, `isMTFResolution?` | ResolutionString | Resolution picker. |
| `session` | `options?`, `optionsTitles?` | string | Session string. |
| `time` | `min`, `max` (required) | number | Timestamp input. |
| `bar_time` | `min`, `max` (required) | number | Bar-time input. |
| `color` | n/a | string | Colour picker. |
| `text_area` | n/a | string | Multi-line text. |

**Critical:** every input needs a value in `defaults.inputs` (`{[inputId]: value}`); "your custom indicator will not work unless you provide values in defaults for each input" (ctx L43574-43578). Input values arrive in `main` via `inputCallback(index)` in `inputs` order.

#### 2.4 `defaults` (`StudyDefaults`, d.ts L22002-22025; ctx L43338-43453)

| Key | Content |
|---|---|
| `inputs` | `{[inputId]: string\|number\|boolean}` (required if the indicator has inputs). |
| `styles` | `{[plotId]: style}` per plot type (2.2). |
| `ohlcPlots` | `{[ohlcPlotId]: {plottype, color, drawWick, drawBorder, wickColor, borderColor, visible, display}}`. |
| `palettes` | `{[paletteId]: {colors, valToIndex?, addDefaultColor?}}`; colour = `{color, style, width}`. |
| `bands` | array of `{color, linestyle, linewidth, value, visible}` (index-matched to `metainfo.bands`). |
| `filledAreasStyle` | `{[areaId]: {color, visible, transparency}}` or gradient form. |
| `areaBackground`, `bandsBackground` | `StudyBandBackgroundPreferences` (fill between bands). |
| `precision` | digits after the decimal separator of output values. |
| `graphics` | `horizlines/polygons/hhists/vertlines` defaults (Pine-style graphics). |

User-facing overrides for custom indicators use lowercased title paths such as `plot.color` (not `plot_0.color`); `getStudyStyles(name)` returns the metadata (ctx L46946-46990).

(ctx L40714-41782 examples, L41788-42119, L43338-44128; d.ts L20082-20152, L21801-22360, L27590-28047, L31312, L31388-31411)

### 3. PineJS Std function reference

`PineJS.Std` = `PineJSStd` (d.ts L18281-19167). **114 entries: 111 callables + 1 constant from the d.ts, plus 2 callables documented only in the docs (`wvap`, `timepart`) = 113 callables + 1 constant.** `ctx` = `IContext`. "Series" args are `IPineSeries` from `ctx.new_var(x)`. Doc text: ctx L42125-42960. There is no Std `vwap`, `cci`, `mfi`, `mom`, `supertrend`, `pivots`, `crossover`, `crossunder`, `bb`, `macd`, `tanh`; build them from the functions below (Section 4.2).

#### 3.1 Math, logic, comparison, utility

| Name | Signature | Returns |
|---|---|---|
| `max_series_default_size` | constant `10001` | Default max series depth. |
| `eps` | `eps()` | Machine epsilon (upper bound of float relative rounding error). |
| `na` | `na(n?)` | d.ts: `1` if NaN else `0` (`NaN` if undefined). Docs say boolean. |
| `nz` | `nz(x, y?)` | `x` if finite, else `y` (default 0). |
| `fixnan` | `fixnan(n_current, ctx)` | Replaces NaN with the last non-NaN value (stateful, needs ctx). |
| `iff` | `iff(condition, thenValue, elseValue)` | Functional ternary (slower than `?:`). |
| `and` | `and(n_0, n_1)` | `1` if both truthy else `0`. |
| `or` | `or(n_0, n_1)` | `1` if either truthy else `0`. |
| `not` | `not(n_0)` | `1` if falsy else `0`. |
| `max` | `max(...values)` | Greatest value (docs list up to 10 args). |
| `min` | `min(...values)` | Smallest value. |
| `avg` | `avg(...values)` | Mean of the given values. |
| `pow` | `pow(base, exponent)` | `base^exponent`. |
| `abs` | `abs(x)` | `x` if `x>=0` else `-x`. |
| `log` | `log(x)` | Natural log (x>0). |
| `log10` | `log10(x)` | Base-10 log. |
| `sqrt` | `sqrt(x)` | Square root (x>=0). |
| `sign` | `sign(x)` | 0, 1.0 or -1.0. |
| `exp` | `exp(x)` | `e^x`. |
| `sin` / `cos` / `tan` | `(x)` radians | Trig. |
| `asin` / `acos` / `atan` | `(x)` | Inverse trig; asin/acos return na outside [-1,1]. |
| `floor` | `floor(x)` | Largest integer <= x. |
| `ceil` | `ceil(x)` | Smallest integer >= x. |
| `round` | `round(x)` | Nearest integer, ties up (docs mention a precision arg; d.ts has none). |
| `isZero` | `isZero(v)` | d.ts type `number`: zero or almost zero (docs: boolean). |
| `toBool` | `toBool(v)` | `true` if finite and non-zero. |
| `eq` / `neq` | `(n1, n2)` | `1`/`0` equality / inequality. |
| `ge` / `le` | `(n1, n2)` | `1`/`0` for `>=` / `<=`. |
| `gt` / `lt` | `(n1, n2)` | `1`/`0` for `>` / `<`. |
| `equal` | `equal(n1, n2, eps?)` | boolean equality within epsilon. |
| `greater` / `less` | `(n1, n2, eps?)` | boolean `>` / `<` with epsilon. |
| `greaterOrEqual` / `lessOrEqual` | `(n1, n2, eps?)` | boolean `>=` / `<=` with epsilon. |
| `compare` | `compare(n1, n2, eps?)` | `-1`, `0` or `1`. |
| `error` | `error(message, title?)` | Throws an indicator error (`never`). |
| `n` | `n(ctx)` | Zero-based bar index of the current bar (0 = first historical bar). |

#### 3.2 Bar, time, session, symbol accessors

| Name | Signature | Returns |
|---|---|---|
| `open` / `high` / `low` / `close` | `(ctx)` | Current bar O/H/L/C (`close` = last price on an unfinished realtime bar). |
| `volume` | `volume(ctx)` | Current bar volume. |
| `hl2` | `hl2(ctx)` | `(high+low)/2`. |
| `hlc3` | `hlc3(ctx)` | `(high+low+close)/3`. |
| `ohlc4` | `ohlc4(ctx)` | `(open+high+low+close)/4`. |
| `time` | `time(ctx)`, `time(ctx, period)` | UNIX time of current bar (symbol timezone, not UTC; d.ts). |
| `period` | `period(ctx)` | Resolution string (`'60'`, `'D'`, `'W'`, `'M'`, `'5D'`, `'12M'`, `'3M'`). |
| `interval` | `interval(ctx)` | Numeric interval (e.g. `1` for `1D`). |
| `tickerid` | `tickerid(ctx)` | Full ticker id of the current symbol. |
| `ticker` | `ticker(ctx)` | Ticker without exchange prefix (e.g. `'MSFT'`). |
| `updatetime` | `updatetime(ctx)` | Symbol update time. |
| `currencyCode` | `currencyCode(ctx)` | Currency code or null. |
| `unitId` | `unitId(ctx)` | Unit id or null. |
| `year` / `month` / `weekofyear` / `dayofmonth` / `dayofweek` / `hour` / `minute` / `second` | `(ctx, time?)` | Component of the current (or given) bar time in the exchange timezone. `dayofweek`: Monday = 2 (ctx L41359). |
| `isdwm` | `isdwm(ctx)` | True if daily/weekly/monthly. |
| `isintraday` | `isintraday(ctx)` | True if minutes/seconds resolution. |
| `isdaily` / `isweekly` / `ismonthly` | `(ctx)` | Resolution-type tests. |
| `selectSessionBreaks` | `selectSessionBreaks(ctx, times: number[])` | Session breaks (intraday only). |
| `createNewSessionCheck` | `createNewSessionCheck(ctx)` | Returns `(time) => boolean` that tells if a new session starts. |
| `add_days_considering_dst` | `(timezone, utcTime: Date, daysCount)` | `Date` shifted by days, DST-aware. |
| `add_years_considering_dst` | `(timezone, utcTime: Date, yearsCount)` | `Date` shifted by years, DST-aware. |
| `timepart` (docs only) | `timepart(symbol, field, time)` | Not described (ctx L42954). |

#### 3.3 Series, moving averages, statistics, TA

| Name | Signature | Returns |
|---|---|---|
| `sum` | `sum(source, length, ctx)` | Sliding sum of last `length` values. |
| `sma` | `sma(source, length, ctx)` | Simple moving average. |
| `ema` | `ema(source, length, ctx)` | EMA, `alpha = 2/(length+1)`. |
| `rma` | `rma(source, length, ctx)` | Wilder/RMA EMA, `alpha = 1/length` (used in RSI/ATR). |
| `smma` | `smma(n_value, n_length, ctx)` | Smoothed MA of the next value (takes a number, not a series). |
| `wma` | `wma(source, length, ctx)` | Weighted MA, weights fall in arithmetic progression. |
| `vwma` | `vwma(source, length, ctx)` | Volume-weighted MA. |
| `swma` | `swma(source, ctx)` | 4-bar symmetric weighted MA, weights `[1/6,2/6,2/6,1/6]`. |
| `alma` | `alma(series, length, offset, sigma)` | Arnaud Legoux MA (Gaussian weights). No ctx argument. |
| `highest` | `highest(source, length, ctx)` | Highest value over `length` bars. |
| `lowest` | `lowest(source, length, ctx)` | Lowest value over `length` bars. |
| `highestbars` | `highestbars(source, length, ctx)` | Offset to the highest bar. |
| `lowestbars` | `lowestbars(source, length, ctx)` | Offset to the lowest bar. |
| `cum` | `cum(n_value, ctx)` | Running total; you pass the value to add each bar (d.ts). Docs show `cum(x, context)` with a series. |
| `change` | `change(source)` | `x - x[1]` (no length argument). |
| `roc` | `roc(source, length)` | Rate of change in percent. |
| `rising` | `rising(series, length)` | True if current value exceeds all previous values for `length` bars (d.ts returns number). |
| `falling` | `falling(series, length)` | True if current value is below all previous for `length` bars. |
| `cross` | `cross(n_0, n_1, ctx)` | boolean: the two values crossed (either direction). |
| `dev` | `dev(source, length, ctx)` | Mean absolute deviation about the SMA. |
| `stdev` | `stdev(source, length, ctx)` | Standard deviation, **biased** (population). |
| `variance` | `variance(source, length, ctx)` | Variance, **biased**. |
| `correlation` | `correlation(sourceA, sourceB, length, ctx)` | Correlation coefficient. |
| `percentrank` | `percentrank(source, length)` | Percent of previous values <= current. |
| `linreg` | `linreg(source, length, offset)` | Least-squares regression value at `offset`. |
| `tr` | `tr(n_handleNaN, ctx)` | True range; handleNaN truthy => first bar uses `high-low`. |
| `atr` | `atr(length, ctx)` | RMA of true range (uses `tr(true)`). |
| `rsi` | `rsi(upper, lower)` | RSI from upward and downward change values (pass their RMAs). |
| `stoch` | `stoch(source, high, low, length, ctx)` | Stochastic %K. |
| `tsi` | `tsi(source, shortLength, longLength, ctx)` | True strength index, value in `[-1, 1]` per docs. |
| `dmi` | `dmi(diLength, adxSmoothingLength, ctx)` | Tuple `[+DI, -DI, DX, ADX, ADXR]`. |
| `sar` | `sar(start, inc, max, ctx)` | Parabolic SAR. |
| `accdist` | `accdist(ctx)` | Accumulation/distribution index. |
| `zigzag` | `zigzag(n_deviation, n_depth, ctx)` | Zig-zag pivot points. |
| `zigzagbars` | `zigzagbars(n_deviation, n_depth, ctx)` | Zig-zag pivot points (bar form). |
| `wvap` (docs only) | `wvap(source, ctx)` | Listed without description (ctx L42956); likely a VWAP variant. Not in d.ts; do not rely on it. |

**Count check:** the three tables hold 93 rows (some rows group several names) covering 114 distinct names: all 112 d.ts names (111 callables + `max_series_default_size`) plus docs-only `wvap` and `timepart`.

**Doc vs d.ts discrepancies to respect.** The d.ts is the typed source: logic/compare helpers (`na`, `and`, `or`, `not`, `eq`, `ge`, ...) return `1/0` numbers, not booleans; `cum` takes a number; `cross` takes numbers; `rsi` takes two numbers (docs mislabel the second arg as "length"); `sar` args are all numbers; `year...second` take an optional `time`; `round` has no precision arg in the d.ts; the d.ts JSDoc for `le` says "greater or equal" (typo).

(d.ts L18281-19167; ctx L42125-42960)

### 4. Equations

#### 4.1 Stated by docs / JSDoc

| Function | Stated computation |
|---|---|
| `sma` | sum of last `length` values / `length` |
| `ema` | `EMA = alpha*x + (1-alpha)*EMA[1]`, `alpha = 2/(length+1)` |
| `rma` | EMA with `alpha = 1/length` |
| `vwma` | `sma(x*volume, length) / sma(volume, length)` |
| `swma` | weights `[1/6, 2/6, 2/6, 1/6]` over 4 bars |
| `tr` | `max(high-low, abs(high-close[1]), abs(low-close[1]))`; with `handleNaN`, first bar = `high-low` |
| `atr` | `rma(tr(true), length)` |
| `stoch` | `100*(close - lowest(low,length)) / (highest(high,length) - lowest(low,length))` |
| `roc` | `100*change(src,length)/src[length]` |
| `change` | `x - x[1]` |
| `linreg` | `intercept + slope*(length - 1 - offset)`, least squares over `length` bars |
| `stdev`, `variance` | biased estimate (divide by N, not N-1) |
| `variance` | expectation of squared deviation from the SMA |
| `dev` | difference measure between series and its SMA |
| `percentrank` | percent of previous `length` values that are <= current |
| `rsi(upper, lower)` | "based on rma's of upward and downward change" |
| `correlation` | degree to which two series deviate from their SMAs |
| `sign` | 0, +1.0, -1.0 |
| `round` | nearest integer, ties up |
| `rising` / `falling` | current value greater / less than any previous value over `length` bars |
| `cum` | cumulative total of all values |
| `iff` | `condition ? then : else` |
| `tsi` | uses moving averages of momentum; result in `[-1,1]` |

(d.ts L18281-19167; ctx L42125-42960)

#### 4.2 Standard definitions (not stated by docs; marked)

- `ema` seed: Pine seeds the first value with the SMA of the first `length` values (standard definition; the docs do not state the seed). Python `ewm(span, adjust=False, min_periods=span)` seeds with the first value, so early bars differ and converge as `(1-alpha)^k` decays.
- `rma(x,n)`: `rma = (rma[1]*(n-1) + x)/n`, same seed question (standard definition).
- `smma(x,n)`: `(smma[1]*(n-1) + x)/n` (standard definition).
- `wma(x,n)`: `sum_{i=0..n-1} (n-i)*x[i] / (n(n+1)/2)` (standard definition).
- `alma(x,n,off,sigma)`: `m = floor(off*(n-1)); s = n/sigma; w_i = exp(-(i-m)^2/(2*s^2)); alma = sum(w_i*x[n-1-i])/sum(w_i)` (standard definition).
- `highestbars` / `lowestbars`: offset of the extreme from the current bar; Pine returns 0 or negative offsets (standard definition).
- `stdev` = `sqrt(variance)`; `variance = mean(x^2) - mean(x)^2` over `length` (population; docs confirm "biased").
- `dev(x,n) = sma(abs(x - sma(x,n)), n)` (standard definition).
- `percentrank(x,n) = 100 * count(x[1..n] <= x) / n` (standard definition).
- `correlation(a,b,n) = cov(a,b)/(sd(a)*sd(b))` over `n` bars (standard definition).
- `rsi`: `up = rma(max(change,0), n)`, `down = rma(max(-change,0), n)`, `rsi = 100 - 100/(1 + up/down)`; `down==0 => 100`; `up==0 => 0` (standard definition). With the d.ts signature: `Std.rsi(Std.rma(upSeries,n,ctx), Std.rma(downSeries,n,ctx))`.
- `tsi(x,s,l) = 100*ema(ema(mom,l),s)/ema(ema(abs(mom),l),s)`, `mom = change(x)` (standard definition; docs say result is in `[-1,1]`, so a /100 scaling may apply; verify).
- `cross`: true when `(x>y) != (x[1]>y[1])`. `crossover = cross && x>y`; `crossunder = cross && x<y` (standard definition). Std has no crossover/crossunder.
- `dmi(di, adx)`: `up = high-high[1]; dn = low[1]-low; +DM = up>dn && up>0 ? up : 0; -DM = dn>up && dn>0 ? dn : 0; +DI = 100*rma(+DM,di)/rma(tr,di); -DI likewise; DX = 100*|+DI - -DI|/(+DI + -DI); ADX = rma(DX, adx); ADXR = (ADX + ADX[adx])/2` (standard definition, Wilder).
- `sar(start, inc, max)`: Wilder parabolic SAR with acceleration factor start, step `inc`, cap `max` (standard definition).
- `accdist`: `cum(((close-low)-(high-close))/(high-low) * volume)`, 0 when `high==low` (standard definition).
- `fixnan`: `x` if finite else previous output.
- `zigzag(dev, depth)`: pivot when price reverses by at least `dev` percent, with minimum `depth` bars between pivots (standard definition).
- Recipes for things Std lacks (all built from Std plus `Math`):
  - `cci(n) = (tp - sma(tp,n)) / (0.015*dev(tp,n))`, `tp = hlc3` (standard definition).
  - `mom(n) = x - x[n]` via `series.get(n)`.
  - `bb(n,k) = sma(x,n) +/- k*stdev(x,n)`; `%B = (x - lower)/(upper - lower)`.
  - `macd = ema(x,fast) - ema(x,slow)`; `signal = ema(macd,sig)`.
  - `mfi`: `100 - 100/(1 + posFlow/negFlow)` where flow = `hlc3*volume` split by sign of `change(hlc3)`, summed over `n`.
  - session `vwap`: `cum(hlc3*volume)/cum(volume)` reset on a new session/UTC day (`createNewSessionCheck(ctx)` or compute the day from `ctx.symbol.time`).
  - `supertrend`: bands `hl2 +/- mult*atr`, ratcheted with state kept in `new_var` series (standard definition).

(Sources for the stated parts: ctx L42125-42960; d.ts L18281-19167.)

### 5. Example indicators (9)

| # | Name (ctx lines) | What it plots and key technique |
|---|---|---|
| 1 | **Equity** - requesting data for another ticker (ctx L40714-40917) | One line (`plot_0`, `plottype: 2`, dark red, price line on) of a second symbol's close. `init`: `ctx.new_sym('#EQUITY', Std.period(ctx))`. `main`: `select_sym(0)`, `new_var(ctx.symbol.time)`; `select_sym(1)`, same for time and `new_var(Std.close(ctx))`; `alignedClose = secondaryClose.adopt(secondaryTime, mainTime, 1)`; `select_sym(0)`; return `[alignedClose]`. Server must resolve the new ticker and serve its bars. Basis for feeding backtest data (Section 7). |
| 2 | **Bar Colorer Demo** - colouring bars (ctx L40922-41103) | `bar_colorer` plot with `palette_0` (2 colours); `valToIndex: {100:0, 200:1}`; `main` returns 100 or 200 (random in demo). `is_price_study: true`. Technique: palette + `valToIndex` mapping to recolour main-series candles by signal. |
| 3 | **Custom Styles For Every Point** (ctx L41105-41291) | `line` plus `colorer` (`target:'plot_0'`, `palette:'paletteId1'`); palette colours carry `color`, `width`, `style`; `main` returns `[value, colorIndex]` so each point can have its own colour, width and dash style. |
| 4 | **Complex Filled Areas** (ctx L41293-41299) | Only a CodePen link in the docs context (no code). Feature: `filledAreas` between two plots or two bands (Section 2.1). |
| 5 | **Mondays** - advanced shapes use (ctx L41301-41444) | `shapes` plot, `shape_circle` at `Bottom` with text 'Monday'; `main` returns `[1]` when `Std.dayofweek(context) === 2` else `[NaN]`; guards `isNaN(context.symbol.time)`. Technique: boolean signal -> shape by returning a value vs NaN. |
| 6 | **Advanced Coloring Candles** (ctx L41446-41782) | A full candle OHLC plot (`ohlc_open/high/low/close`, target `plot_candle`) with three colorers (`ohlc_colorer` body, `wick_colorer`, `border_colorer`), each its own palette; `is_price_study:false`, `linkedToSeries:true`; returns `[o,h,l,c,col,col,col]` with `col` in {0,1}. Technique: repainting the price candles per signal. |
| 7 | **OHLC_sample** - OHLC plots (ctx L41788-41964) | Draws synthetic candles from four `ohlc_*` plots targeting `plotcandle_0`; `defaults.ohlcPlots.plotcandle_0.plottype` `'ohlc_candles'` (or `'ohlc_bars'`); `main` returns `[open, high, low, close]`. |
| 8 | **Custom Moving Average** - tutorial (ctx L56502-56864, L56951-57381) | Two lines: SMA(`length`, `source`) and a "Smoothing Line" (SMA/EMA/WMA of the SMA); inputs `length`, `source`, `offset`, `smoothingLine`, `smoothingLength`; `setMinimumAdditionalDepth(length+smoothingLength)`; chained `new_var(sma)`; returns `[{value, offset}, {value, offset}]`; `_metainfoVersion: 53`, `linkedToSeries: true`. |
| 9 | **Extend Time Scale Example** (ctx L43065-43150; code from L43072) | `symbol` input, `new_sym` in `init`, `select_sym(1)` in `main`, returns the other symbol's close; `canExtendTimeScale: true` and the `studies_extend_time_scale` featureset let it show bars where the main series has none. |

#### Minimal skeleton: value plot plus UP/DOWN shape signals (written from the documented API)

```js
// ESM, no deps. Register: custom_indicators_getter: (PineJS) => Promise.resolve([smtZ(PineJS)])
// Create:  chart.createStudy('SMT Z-Score Signal', false, false, { len: 20, entry: 0.5 })
export const smtZ = (PineJS) => ({
  name: 'SMT Z-Score Signal',
  metainfo: {
    _metainfoVersion: 53, id: 'SMTZScore@tv-basicstudies-1',
    description: 'SMT Z-Score Signal', shortDescription: 'SMT Z',
    is_price_study: false, isCustomIndicator: true, format: { type: 'price', precision: 3 },
    inputs: [{ id: 'len', name: 'Window', type: 'integer', defval: 20, min: 2, max: 500 },
             { id: 'entry', name: 'Entry |score|', type: 'float', defval: 0.5, min: 0, max: 1, step: 0.05 }],
    plots: [{ id: 'score', type: 'line' }, { id: 'up', type: 'shapes' }, { id: 'dn', type: 'shapes' }],
    styles: { score: { title: 'Score', histogramBase: 0 }, up: { title: 'UP', text: 'UP' }, dn: { title: 'DOWN', text: 'DN' } },
    defaults: {
      inputs: { len: 20, entry: 0.5 },
      styles: {
        score: { plottype: 0, linestyle: 0, linewidth: 1, trackPrice: false, visible: true, color: '#2196F3' },
        up: { plottype: 'shape_arrow_up', location: 'Absolute', color: '#26a69a', textColor: '#26a69a', visible: true },
        dn: { plottype: 'shape_arrow_down', location: 'Absolute', color: '#ef5350', textColor: '#ef5350', visible: true },
      },
    },
  },
  constructor: function () {
    this.main = function (ctx, inp) {
      const S = PineJS.Std, len = inp(0), entry = inp(1);
      const closes = ctx.new_var(S.close(ctx));                 // history for Std.* series args
      const mean = S.sma(closes, len, ctx), sd = S.stdev(closes, len, ctx);
      const z = sd > 0 ? (S.close(ctx) - mean) / sd : NaN;      // NaN while warming up / flat
      const score = Math.max(-1, Math.min(1, -z / 2));          // reversion: stretched low => +1
      const closed = ctx.symbol.isBarClosed !== false;          // ignore ticks on the live bar
      return [score, closed && score >= entry ? score : NaN, closed && score <= -entry ? score : NaN];
    };
  },
});
```
Notes: `location: 'Absolute'` is expected to draw the shape at the plotted value (Pine `location.absolute` semantics; docs list the value but do not define it, so verify visually). `Std.sma`/`stdev` are called unconditionally every bar (state is allocated per call site; see Section 6).

### 6. Gotchas from docs

1. **Defaults for every input or the indicator will not work** (ctx L43574-43578). Same ids in `inputs[].id` and `defaults.inputs`.
2. **`metainfo` is read once**; it cannot change after chart creation (ctx L43706-43710). Per-plot style defaults can be reset by the user via Apply Defaults.
3. **Constructor must be an ES5 function**; `init`/`main` live on `this` (ctx L43183). The library first runs `init` and `main` against an empty context (d.ts L6504-6508): guard against NaN `ctx.symbol.time` and zero/undefined values.
4. **Plots order = return array order**, including colorer/OHLC plots; mismatch silently mis-assigns values. A single plot may return a bare number (ctx L43240-43241).
5. **Return `NaN` to hide a point/shape**; null returns used to fail to plot (fixed in release 30.2, ctx L48879). Prefer NaN.
6. **Series arguments need `ctx.new_var(...)`**; passing the raw number from `Std.close(ctx)` to `Std.sma` is wrong. `cum`, `smma`, `cross`, `rsi` are the exceptions (number arguments).
7. **Chained calculations** (MA of MA) need `ctx.setMinimumAdditionalDepth(total)`; otherwise early visible bars are under-warmed (ctx L56546-56556).
8. **Extra symbols**: `main` runs for each bar of every series; always call `select_sym(0)` before returning; align with `adopt(...)` (mode 1 precise vs 0 continuous) (ctx L43222-43226, L42963-43018; d.ts L14232-14290). Extra-symbol bars need a datafeed-resolvable ticker.
9. **Biased `stdev`/`variance`** (population). Compare against sample-stdev code (ddof=1) and expect a `sqrt(n/(n-1))` ratio (ctx L42886-42906).
10. **Realtime bar**: `close` is the last price until the bar closes (ctx L42358). Use `ctx.symbol.isBarClosed` / `isNewBar` for signals; otherwise markers flicker/repaint on the live bar (d.ts L15276-15283).
11. **`plottype: 2`** appears in the "Equity" example (ctx L40758) but `LineStudyPlotStyle` has no value 2 (valid: 0,1,3-11; d.ts L351-396). Use 0 for a line.
12. **Shape `size`** controls height only; width follows bar width (ctx L43413-43417).
13. **Filled areas** can join two plots or two bands, never a band and a plot (ctx L43975).
14. **Colorers** need the palette in three places: `metainfo.palettes[id]` (names, `valToIndex`), `defaults.palettes[id]` (colours), and the plot's `palette: id`. Without `valToIndex`, the returned number is the palette index.
15. **OHLC plots** need all four `ohlc_*` plots per OHLC plot id and `target` pointing at the `ohlcPlots` key (ctx L41864-41865).
16. **Naming**: `id` must be unique and in the `<name>@tv-basicstudies-1` form; `description` is the name to pass to `createStudy` (ctx L43735-43752). `createStudy(name, forceOverlay?, lock?, inputs?, overrides?, options?)` returns `Promise<EntityId|null>` (d.ts L11572).
17. **Overrides for custom indicators** use lowercase title paths (`plot.color`, not `plot_0.color`); inspect with `getStudyStyles` (ctx L46946-46990).
18. **Time-scale extension** needs both `canExtendTimeScale: true` and featureset `studies_extend_time_scale` (off by default; ctx L44670-44680).
19. **`overlayScaleMargins`** is ignored when the indicator has its own pane or a visible scale; invalid values log a console warning (ctx L44086-44105; added in release 33.0.0, ctx L48383-48406).
20. **`group` on inputs** adds a header; `hideWhenPlotsHidden` hides input text in the legend when listed plots are hidden (ctx L48708, L49632).
21. **Release notes touching PineJS**: MIN/MAX_VALUE compare fix (ctx L49182), `highest` with negative numbers fix (ctx L50106), type fixes for Std functions (ctx L50022).
22. **Hard limits**: default series depth 10001 (`max_series_default_size`); use `new_unlimited_var` for deeper history (inferred from d.ts L18285, L12998-13007).
23. **Inferred, not stated by docs:** Std calls and `new_var` allocate per-call-site state, so call them every bar in the same order (no `if` around them) except branches selected by constant inputs, as the tutorial does (ctx L56592-56612).
24. **Pine Script not supported**; users cannot edit custom indicator code (ctx L43275-43279, L65650).

### Use in solmargintrader

Repo facts used (verified in the repo): the Compound 5m scorecard lives in `backtester/core/scorecard.py` (`evaluate`, `Evaluation.composite`, `.indication`, `.regime`, `.blocked`, `target_path`) and `backtester/core/compound.py` (`run_compound`, `forecast_stats` scores the call at bar t against `sign(close[t+1]-close[t])`). Components are the `_c_*` functions; gates are `_g_*`. The extension is ESM (`"type":"module"`, no dependencies, `node --test`) at `extension`. Compound doc: `docs/COMPOUND-5M.md`.

**A. Two ways to get a signal on the chart (recommend both, in this order)**

1. **Replay (authoritative, zero parity risk): serve the precomputed Python output as a pseudo-symbol and read it with `new_sym`.** This is the documented "Requesting data for another ticker" pattern (Example 1, ctx L40714-40820).
   - Datafeed: add a symbol such as `SMT:SOL_COMPOUND` whose `getBars` returns, per 5m bar, `time` in **ms** (Python `Bars.ts` is seconds; multiply by 1000; d.ts L1818-1826), and OHLCV used as a data bus: `close = composite` (-1..+1), `open = indication` (-1/0/+1), `high = coverage`, `low = regime code` (trend=1, range=2, squeeze=3, neutral=0), `volume = blocked` (0/1). Source: dump `Evaluation` arrays (`composite`, `indication`, `coverage`, `regime`, `blocked`) from `evaluate(bars, config)` to JSON/CSV, keyed by bar open time.
   - Indicator: `init`: `ctx.new_sym('SMT:SOL_COMPOUND', Std.period(ctx))`. `main`: `select_sym(0)`; `mainT = new_var(ctx.symbol.time)`; `select_sym(1)`; `secT = new_var(ctx.symbol.time)`; for each channel `ch = new_var(Std.close(ctx))`, `ch.adopt(secT, mainT, 1)` (precise mode, so a bar is not duplicated); same for `open`, `high`, `low`, `volume` via `Std.open/high/low/volume`; `select_sym(0)`; return `[composite, up ? composite : NaN, down ? composite : NaN, ...]`. Add `bands` at +entry/-entry (0.25 default) and 0, and a `bg_colorer` or `bar_colorer` plot for regime/blocked (FLAT) state.
   - Timing rule: the Python call at bar t uses data through the close of bar t and forecasts bar t+1. Draw the UP/DOWN shape on bar t (the signal bar). Never use a positive `offset` to place it on t+1 inside logic.
   - Indicator `main` runs for every bar of the extra symbol first, then the main series (ctx L43222-43226); keep `select_sym(0)` at the end.

2. **Live port (PineJS, visual cross-check and no-datafeed use):** port only components that map cleanly to `Std`; leave the adaptive Beta-weighting and tuning (`adaptive_counts`, `tune_component`) in Python because they are stateful over 4,032-bar windows and add parity risk for little chart value.

**B. Porting individual signals**

| Repo signal | Python definition (file) | PineJS port |
|---|---|---|
| Z-score reversion score | `_c_zscore`: `clip(-(close - sma(close,w)) / rstd(close,w) / entry)`, `rstd` = rolling std ddof=0 (`scorecard.py:519-521`) | `S.sma(closes,w,ctx)`, `S.stdev(closes,w,ctx)` (also biased, so identical), then `Math.max(-1, Math.min(1, -z/entry))`. The strategy-side `indicators.zscore` uses ddof=1 (`backtester/core/indicators.py:276-288`); port the one you compare against. The skeleton in Section 5 is this port. |
| VWAP distance / reversion | `_vwap_distance`: UTC-session VWAP from typical price x volume; `dist = close - vwap`; `spread = max(sqrt(rolling_mean(dist^2, spread_window)), atr(period))`; side score `tanh(dist/spread/scale)`; reversion score `clip(-dist/spread/stretch)` (`scorecard.py:211-225, 404-422, 524-526`) | No Std vwap. Keep `pv = ctx.new_var(S.hlc3(ctx)*S.volume(ctx))`, `v = ctx.new_var(S.volume(ctx))`; running sums reset when the UTC day changes (day from `ctx.symbol.time`, confirm ms vs s first, or `createNewSessionCheck(ctx)` if its session equals 00:00 UTC for the symbol). `dist2 = ctx.new_var(dist*dist)`, `S.sma(dist2, spread_window, ctx)`, `S.atr(period, ctx)`, `Math.tanh` (not in Std). |
| RSI score | `rsi_series` with Wilder `ewm(alpha=1/period, adjust=False, min_periods=period)` | `S.rsi(S.rma(upSeries,n,ctx), S.rma(downSeries,n,ctx))` with `upSeries = new_var(S.max(S.change(closes),0))`. Differences only in warm-up seeding. |
| ADX / regime | `dmi`, `classify_regime` (trend ADX >= 25, range <= 18, squeeze = Bollinger width rank <= 15%) | `S.dmi(14,14,ctx)[3]` = ADX; `S.percentrank(widthSeries, lookback)` for width rank (percentrank is "<= current", check definition against `pct_rank` in `scorecard.py:243`). |
| Compound score | weighted sum of component scores x regime multipliers, family de-dup, entry 0.25 / exit 0.10 hysteresis (`evaluate`, `target_path`, `scorecard.py:1508, 1615`) | Sum with weights as inputs; hysteresis needs state: `pos = ctx.new_var(); prev = pos.get(1)`; `pos.set(newPos)`. Gates (`_g_*`) fail closed: return NaN/FLAT if an input is NaN. |
| Strategy signals (rsi, macd, bb, keltner, ichimoku, vwap_reversion, zscore, stochastic, obv_trend, ppo, adx_filtered_trend, ema/ma crossover, swing_confluence, ...) | `backtester/core/strategies/*.py`, `on_bar(history) -> position` (0/1), stateful `_holding` | Use `Std.macd` recipes from Section 4.2, `Std.cross` for crossovers, `Std.stoch`, `Std.linreg`, `Std.accdist`; stateful entry/exit via `ctx.new_var` holding flag. Ichimoku, Keltner, OBV, PPO: compose from `highest/lowest`, `ema+atr`, `cum`, `ema` (no Std shortcuts). |

**C. Parity checks (Python vs PineJS), cheapest first**

1. **Pure-JS twin in the extension.** Put the numeric core as plain functions on arrays in `extension/src/core/` (zero-dep ESM) and have the PineJS wrapper only supply series and call them where possible. Add a `node --test` file (same style as `extension/test/soltui-parity.test.js`) that loads a fixture exported from Python (`ts, o, h, l, c, v` plus expected `score`, `composite`, `indication`) and asserts equality after warm-up, tolerance `1e-9` for SMA/stdev-based scores, `1e-6` for RMA/EMA-based ones.
2. **Warm-up exclusion rule.** Compare only bars `>= max(window, 5*period)`; EMA/RMA seeds differ (Python seeds with the first observation, Pine-style engines with an SMA), and the difference decays as `(1-alpha)^k`.
3. **Definitions that bite:** stdev ddof (0 in Std and `scorecard.rstd`; 1 in `indicators.zscore`); VWAP session reset (Python: 00:00 UTC, `scorecard.py:218-221`; chart `createNewSessionCheck` uses the symbol's session); `percentrank` strictness; `change(source)` has no length arg (use `.get(n)`); `highestbars` sign.
4. **In-chart check against the real PineJS runtime** (the only place real `Std` runs): add the study, call `chart.exportData({ includeTime: true, includeSeries: true, includedStudies: [studyId] })` (d.ts L11905-11931, L7705-7745; `from`/`to` in seconds) over the same window as the Python run, save as CSV, and diff `score`/`composite` columns to the Python CSV by bar time. `getEntityValues()` (d.ts L11243-11248) gives the latest values for spot checks.
5. **No-lookahead audit.** Truncation test: compute the indicator on bars `[0..k]` and on `[0..N]`; value at `k` must be identical (the repo already enforces prefix-invariance in the compound tests, see "prefix-invariance test" in `docs/COMPOUND-5M.md`). In the chart: confirm no shape appears on a bar before that bar's close time, and that `isBarClosed` gating removes repaint on the live bar.
6. **Report parity numerically:** max abs diff, share of bars with different `indication` sign, and count of UP/DOWN markers at identical bar times; accept only 100% match on signal bars after warm-up for the cheap components, and a documented tolerance for RMA/EMA components.

**D. What not to do:** do not port the adaptive learning/tuning into PineJS; do not trust a chart marker's hit rate as backtest evidence (the repo's forecast stats and OOS split are the evidence); do not use the `offset` output to shift signals; do not bundle the licensed Charting Library into the repo (it is loaded by the host page; only the indicator module and datafeed adapter belong in `extension/`).

## Datafeed, symbology and streaming

Sources: `ctx` = `tradingview/charting-library-context.txt`; `datafeed d.ts` = `tradingview/datafeed-api.d.ts` (1224 lines, generated by dts-bundle-generator 9.5.1). Where the d.ts and the prose docs disagree, the d.ts is treated as the type truth and the disagreement is listed in 8.2.

### 0. Orientation (read first)

- The library ships no market data. The datafeed object (assigned to the widget `datafeed` option) is the only bridge; the library calls its methods and you answer through callbacks. (ctx L38812-38832, L39116-39132)
- Time units: bar `time` and `HistoryMetadata.nextTime` are **milliseconds UTC**; `PeriodParams.from/to`, mark `time`, `getServerTime`, `expiration_date` are **seconds**; `getVolumeProfileResolutionForPeriod` `from/to` are **milliseconds**. UDF wire format is all seconds and the adapter converts `t`/`nextTime` to ms. (ctx L39162-39173; datafeed d.ts L19-24, L239-247)
- Every callback must be invoked **asynchronously** (a later macrotask, e.g. `setTimeout(() => cb(data), 0)`), otherwise `Uncaught RangeError: Maximum call stack size exceeded`. (ctx L39150-39158, L37843-37845)
- The library may mutate `Bar` objects you hand it: pass copies. The library caches history itself; do not build a second client cache for it. (ctx L37806-37808, L39160, L39452-39456)
- Licence note: the docs state the library may be used on **public websites only** and does not read local files; a file/CSV source needs a backend bridge (HTTP or WebSocket). The repo is access-restricted. Check the licence before wiring this into a private local tool or extension. (ctx L38892-38903, L62687-62690)
- Instance flavours: Advanced Charts needs only the chart methods; Trading Platform additionally needs quotes (`getQuotes`/`subscribeQuotes`/`unsubscribeQuotes`) and, for DOM, depth methods, plus a Broker API. (ctx L61429-61440, L39706-39723)

### 1. Datafeed contract: methods (IExternalDatafeed + IDatafeedChartApi + IDatafeedQuotesApi)

Type aliases (datafeed d.ts L1161-1220): `OnReadyCallback = (configuration: DatafeedConfiguration) => void`; `SearchSymbolsCallback = (items: SearchSymbolResultItem[]) => void`; `SearchSymbolsPaginatedCallback = (items, symbolsRemaining: number) => void`; `ResolveCallback = (symbolInfo: LibrarySymbolInfo) => void`; `DatafeedErrorCallback = (reason: string) => void`; `HistoryCallback = (bars: Bar[], meta?: HistoryMetadata) => void`; `SubscribeBarsCallback = (bar: Bar) => void`; `ServerTimeCallback = (serverTime: number) => void`; `GetMarksCallback<T> = (marks: T[]) => void`; `DOMCallback = (data: DOMData) => void`; `QuotesCallback = (data: QuoteData[]) => void`; `QuotesErrorCallback = (reason: string) => void`; `ResolutionString` is a nominal `string`.

| Method | Exact signature | Req? | When the library calls it | Required callback behaviour |
|---|---|---|---|---|
| `onReady` | `onReady(callback: OnReadyCallback): void` (d.ts L425) | Required | Once, at chart init, before anything else. | Call `callback(DatafeedConfiguration)` async (`setTimeout(() => callback(cfg))`). (ctx L39292-39324) |
| `searchSymbols` | `searchSymbols(userInput: string, exchange: string, symbolType: string, onResult: SearchSymbolsCallback, searchSource?: SearchInitiationPoint): void` (d.ts L298) | Required | User types in Symbol Search / Compare / Watchlist / indicator-symbol input. `SearchInitiationPoint` = `"symbolSearch" \| "watchlist" \| "compare" \| "indicatorInputs"` (d.ts L8-13). Frequency throttled by widget option `symbol_search_request_delay`. | Call `onResult(SearchSymbolResultItem[])`; empty array if no match. Empty `exchange`/`symbolType` = no filter. Tutorial caps at 200 results. (ctx L39326-39369, L60036-60059) |
| `searchSymbolsPaginated` | `searchSymbolsPaginated?(options: SymbolSearchPaginatedOptions, onResult: SearchSymbolsPaginatedCallback): void` (d.ts L311) | Optional | Replaces `searchSymbols` when defined; called as the user scrolls. | `options = {exchange, userInput, start?, symbolType, searchSource?}`. Use `start` as the offset (second page after 50 results has `start=50`). Pass `symbolsRemaining` = 0 when the server has no more. (d.ts L298-311, L1076-1097; ctx L38920-38955) |
| `resolveSymbol` | `resolveSymbol(symbolName: string, onResolve: ResolveCallback, onError: DatafeedErrorCallback, extension?: SymbolResolveExtension): void` (d.ts L320) | Required | When the library needs `LibrarySymbolInfo` for a name or ticker; again with `extension` on currency/unit/session change. | `onResolve(LibrarySymbolInfo)`. On failure `onError(msg)`; the literal `"unknown_symbol"` shows the ghost icon (unless `hide_image_invalid_symbol` featureset). If `name != ticker` the library resolves twice (entered name, then resolved ticker); if equal, once. (ctx L39371-39446) |
| `getBars` | `getBars(symbolInfo: LibrarySymbolInfo, resolution: ResolutionString, periodParams: PeriodParams, onResult: HistoryCallback, onError: DatafeedErrorCallback): void` (d.ts L330) | Required | Initial load, scroll-back, resolution/symbol change, indicator history needs, after `resetData`. Often **several calls per load**. | `onResult(bars, meta?)` with ascending bars; `meta = {noData?, nextTime?}`. See section 4. `onError` text: use `encodeURIComponent` if it contains special characters. (ctx L39448-39583) |
| `subscribeBars` | `subscribeBars(symbolInfo, resolution, onTick: SubscribeBarsCallback, listenerGuid: string, onResetCacheNeededCallback: () => void): void` (d.ts L341) | Required for live | When a dataset (symbol + resolution + currency + chart type) needs live updates. Not re-called if a subscription for the same dataset already exists. | Call `onTick(fullBar)` whenever the last bar changes or a newer bar starts. See section 5. (ctx L39185-39233, L39596-39633) |
| `unsubscribeBars` | `unsubscribeBars(listenerGuid: string): void` (d.ts L347) | Required for live | ~5 s after a subscription is no longer needed (switch symbol/resolution, chart closed). `listenerGuid` equals the `listenerGuid`/`subscriberUID` given to `subscribeBars`. | Stop pushing for that exact id; **keep pushing until this call arrives**. (ctx L39237-39250, L39635-39643) |
| `getMarks` | `getMarks?(symbolInfo, from: number, to: number, onDataCallback: GetMarksCallback<Mark>, resolution: ResolutionString): void` (d.ts L266) | Optional (`supports_marks`) | For the visible bar range; `from`/`to` are Unix **seconds**. | Call `onDataCallback(Mark[])` **once per call**. Max **10 marks per bar**. Mark `time` must equal a bar's time (e.g. bar times Jan 1/8/15 -> a mark at Jan 5 is invalid). (d.ts L252-266; ctx L38957-38969) |
| `getTimescaleMarks` | `getTimescaleMarks?(symbolInfo, from: number, to: number, onDataCallback: GetMarksCallback<TimescaleMark>, resolution: ResolutionString): void` (d.ts L279) | Optional (`supports_timescale_marks`) | Same range semantics as `getMarks`. | `onDataCallback(TimescaleMark[])` once per call. (d.ts L267-279; ctx L39001-39011) |
| `getServerTime` | `getServerTime?(callback: ServerTimeCallback): void` (d.ts L288) | Optional (`supports_time`) | When the chart needs server time; used for the price-scale bar-close countdown (intraday resolutions only; needs `mainSeriesProperties.showCountdown`). | Call `callback(unixSeconds)` exactly once, e.g. `1445324591`. (d.ts L280-288; ctx L39073-39088) |
| `getVolumeProfileResolutionForPeriod` | `getVolumeProfileResolutionForPeriod?(currentResolution: ResolutionString, from: number, to: number, symbolInfo: LibrarySymbolInfo): ResolutionString` (d.ts L390) | Optional | For Volume Profile Visible Range / Fixed Range / Session Volume Profile. `from`/`to` = **ms**. | Return a finer resolution to make the library request an extra series at it; return `currentResolution` (or do not implement) to build the profile from chart bars. (d.ts L364-390; ctx L39090-39102) |
| `subscribeDepth` | `subscribeDepth?(symbol: string, callback: DOMCallback): string` (d.ts L356) | TP/DOM only | Depth-of-Market widget; requires broker config flag `supportLevel2Data = true`. | Return a unique id; call `callback(DOMData)` per update. (ctx L39827-39833) |
| `unsubscribeDepth` | `unsubscribeDepth?(subscriberUID: string): void` (d.ts L363) | TP/DOM only | DOM widget stops. | Stop updates for the id returned by `subscribeDepth`. (ctx L39835-39837) |
| `getQuotes` | `getQuotes(symbols: string[], onDataCallback: QuotesCallback, onErrorCallback: QuotesErrorCallback): void` (d.ts L401) | TP only (mobile legend too) | Watchlist, Details, Order Ticket, DOM, Legend, Buy/Sell buttons, % change. | Call `onDataCallback(QuoteData[])` **once** with all symbols. Each item `n` must be **exactly** the requested symbol string. Required on mobile or the legend shows `NaN`. (ctx L39725-39800) |
| `subscribeQuotes` | `subscribeQuotes(symbols: string[], fastSymbols: string[], onRealtimeCallback: QuotesCallback, listenerGUID: string): void` (d.ts L410) | TP only | Live quote updates. `symbols` = update rarely (about once/minute, hidden watchlist rows); `fastSymbols` = at least every 10 s. | Call `onRealtimeCallback(QuoteData[])` per update; tutorial polls `getQuotes` every 5 s keyed by `listenerGUID`. (d.ts L402-410; ctx L39802-39813) |
| `unsubscribeQuotes` | `unsubscribeQuotes(listenerGUID: string): void` (d.ts L416) | TP only | Row removed or chart symbol changed. | Clear the listener. (ctx L39815-39825) |

Supporting types:

| Type | Fields (d.ts) |
|---|---|
| `PeriodParams` (L936-953) | `from: number` (s, leftmost requested bar); `to: number` (s, rightmost, **exclusive**); `countBack: number` (exact number of bars wanted; **higher priority than `from`** if supported); `firstDataRequest: boolean` (true on the first `getBars` of a load). |
| `HistoryMetadata` (L233-250) | `noData?: boolean` (no more history on the server); `nextTime?: number \| null` (ms; time of the nearest bar **before** the requested range; seconds still accepted with a console warning). |
| `SymbolResolveExtension` (L1056-1072) | `currencyCode?: string`; `unitId?: string`; `session?: string` (`"regular"` or `"extended"`). |
| `QuoteData` (L954-975, L1184) | `QuoteOkData {s:"ok", n:string, v:DatafeedQuoteValues}` or `QuoteErrorData {s:"error", n:string, v:object}`. |
| `DatafeedQuoteValues` (L154-214) | `ch, chp` (day change; required on mobile), `short_name, exchange, description, lp` (last price), `ask, bid, spread, open_price, high_price, low_price, prev_close_price, volume, original_name`, pre/post market `rtc, rtc_time (s), rch, rchp`, plus arbitrary `[valueName: string]: string\|number\|string[]\|number[]\|undefined`. Wrong types cause multi-second UI delays or missing quotes. |
| `SearchSymbolResultItem` (L991-1048) | `symbol` (short name), `description`, `exchange`, `ticker?`, `type` (`'stock'\|'futures'\|'forex'\|'index'`; docs also show `'crypto'`), `logo_urls?` (1 or 2 URLs), `exchange_logo?`. Provide `ticker` here **and** in `LibrarySymbolInfo`. |
| `DOMData` / `DOMLevel` (L50-70) | `{snapshot: boolean, asks: DOMLevel[], bids: DOMLevel[]}`, both sorted ascending by price; `DOMLevel {price, volume}`. `snapshot=false` = only changed levels. |

Sequence (first open): `onReady` -> `resolveSymbol` -> `getBars` (one or more) -> `subscribeBars`; on symbol switch: `resolveSymbol(new)` -> `getBars` -> `subscribeBars(new)` -> (~5 s later) `unsubscribeBars(old)`. (ctx L39645-39684, L39254-39258)

### 2. DatafeedConfiguration (`onReady` payload) (datafeed d.ts L75-143)

| Field | Type | Meaning / rules |
|---|---|---|
| `supported_resolutions` | `ResolutionString[]` | Resolutions the chart offers globally, e.g. `["1","15","240","D","6M"]`. `undefined` or `[]` = the dropdown shows the current symbol's `LibrarySymbolInfo.supported_resolutions`. Per-symbol list can disable entries. |
| `exchanges` | `Exchange[]` (`{value, name, desc}`) | Symbol Search exchange filter; `[]` hides the filter; `value:''` = all exchanges. `value` is passed to `searchSymbols`. |
| `symbols_types` | `DatafeedSymbolType[]` (`{name, value}`) | Symbol Search type filter; `value` passed as `symbolType`; `value:''` = all. Tutorial: `[{name:'crypto', value:'crypto'}]`. |
| `symbols_grouping` | `Record<string,string>` | Per symbol type, a regex string splitting name into root + expiration, to group contracts in Symbol Search. |
| `supports_marks` | boolean | Enables `getMarks`. |
| `supports_timescale_marks` | boolean | Enables `getTimescaleMarks`. (Prose docs say `supports_marks`; set both, see 8.2.) |
| `supports_time` | boolean | Enables `getServerTime` (countdown accuracy). |
| `currency_codes` | `(string \| CurrencyItem)[]` | Currencies for conversion; a string `"USD"` becomes `{id:"USD", code:"USD"}`. `CurrencyItem {id, code, logoUrl?, description?}`. |
| `units` | `Record<string, Unit[]>` | Unit groups for conversion, e.g. `{weight:[{id:'kg',name:'kg',description:'Kilograms'}]}`. `Unit {id,name,description}`. |

UDF `/config` adds `supports_search` and `supports_group_request` (one must be true). Defaults if `/config` is not implemented: `supported_resolutions ['1','5','15','30','60','1D','1W','1M']`, `supports_group_request true`, `supports_marks false`, `supports_search false`, `supports_timescale_marks false`. (ctx L38400-38428)

Tutorial config (Binance): `supports_timescale_marks, supports_marks, supports_time: true`, a `supported_resolutions` list, one exchange, `symbols_types:[{name:'crypto',value:'crypto'}]`. (ctx L59947-59956)

### 3. LibrarySymbolInfo (returned by `resolveSymbol`) (datafeed d.ts L451-871)

Symbol identity: `ticker` (if set) is what the library passes to all later datafeed calls; otherwise `name`. Neither should contain the exchange name; avoid `:` in `ticker` unless using the `EXCHANGE:SYMBOL` TradingView form. UI uppercases names unless the `uppercase_instrument_names` featureset is off. (ctx L38056-38087; d.ts L460-473)

| Field | Type / default | Meaning; crypto value |
|---|---|---|
| `name` (req) | string (L460) | Visible symbol name, not unique. `SOL-USD`. |
| `base_name` | string[] (L465) | Base symbols of a spread (`['NASDAQ:AAPL','NASDAQ:MSFT']`). Skip. |
| `ticker` | string (L473) | Unique id used in datafeed requests; not shown. `COINBASE:SOL-USD`. |
| `description` (req) | string (L478) | Legend text. `Solana / US Dollar`. |
| `long_description` | string (L484) | Longer text. |
| `type` (req) | string (L489) | Instrument type; `'crypto'` is used in the docs/tutorial. A perp has no expiry so `'crypto'` is the safe pick (the `SymbolType` list is outside the assigned ranges). |
| `session` (req) | string (L494) | Trading hours in the symbol `timezone`. Crypto: **`'24x7'`**. Do **not** use `0000-0000`: that means 00:00-00:00 Monday-Friday only. (ctx L40326-40337) |
| `session_display` | string (L498) | UI session text; defaults to `session`. |
| `session_holidays` | string (L507) | `YYYYMMDD` list `"20181105,20181107"` of non-trading days. Crypto: omit. |
| `corrections` | string (L520) | Per-day session overrides `SESSION:YYYYMMDD`, days newest first separated by `,`, corrections separated by `;`. Beats `session_holidays`. Crypto: omit. (ctx L38131-38150) |
| `exchange` (req) | string (L527) | Traded (proxy) exchange, shown in legend. `Coinbase` / `Hyperliquid`. |
| `listed_exchange` (req) | string (L534) | Real listed exchange, shown in legend. Same as `exchange`. |
| `timezone` (req) | `Timezone` (L539) | Exchange time zone, OlsonDB. Crypto: **`'Etc/UTC'`**. Governs session interpretation and bar alignment. |
| `format` (req) | `"price" \| "volume"` (L546) | `price` formats by `minmov/pricescale/minmove2/fractional/variableMinTick`; `volume` formats thousands/millions/billions. Crypto: `'price'`. |
| `pricescale` (req) | number (L558) | Decimal format: `10^n`, n = decimal places. Fractional format: `2^n`. |
| `minmov` (req) | number (L565) | Tick units; **tick size = `minmov / pricescale`**. |
| `fractional` | boolean (L592) | `true` only for `x'y` bond-style prices. Crypto: omit/false. |
| `minmove2` | number (L599) | Fraction-of-a-fraction (`x'y'z`); for forex/cfd `10` shows pips; `0`/omit otherwise. |
| `variable_tick_size` | string (L605) | e.g. `'0.01 10 0.02 25 0.05'` = tick 0.01 up to 10, 0.02 up to 25, 0.05 above. Still set `pricescale`/`minmov`. |
| `has_intraday` | boolean, default false (L613) | Datafeed has minute data. Must be true to enable minute resolutions, else "No data here". |
| `supported_resolutions` | `ResolutionString[]` (L636) | Per-symbol dropdown list. Availability: `isIntraday ? has_intraday && listed : listed`. `[]` disables all; `undefined` = all chart-supported + custom. |
| `intraday_multipliers` | string[] (L649) | Minute resolutions the datafeed **actually serves** from `getBars`, ascending (`["1","5"]`). Base set the library builds other minute/hour resolutions from. Default `[]` = datafeed can serve any requested minute resolution. Cannot build D/W/M. |
| `has_seconds` | boolean, default false (L657) | Enables seconds; needs `seconds_resolution` featureset. |
| `seconds_multipliers` | string[] (L674) | Seconds resolutions served, no letters (`["1","5"]`); library builds larger ones. |
| `has_ticks` | boolean, default false (L665) | Tick resolutions (`1T`); needs `tick_resolution` featureset. |
| `build_seconds_from_ticks` | boolean, default false (L685) | Trading Platform only; needs `has_seconds` and `has_ticks`. |
| `has_daily` | boolean, default **true** (L693) | Daily data present; also set `daily_multipliers`. |
| `daily_multipliers` | string[], default `["1"]` (L701) | Daily resolutions served, no letters. |
| `has_weekly_and_monthly` | boolean, default false (L711) | If false the library tries to build W/M from daily bars (many requests; may show "No data here"). |
| `weekly_multipliers` / `monthly_multipliers` | string[], default `['1']` (L719, L727) | Served weekly / monthly resolutions, no letters. |
| `has_empty_bars` | boolean, default false (L735) | Library fills gaps inside a session with empty bars. Unusable with `disable_resolution_rebuild`. |
| `visible_plots_set` | `"ohlcv"\|"ohlc"\|"c"\|"hlc"` default `'ohlcv'` (L744, L1220) | Values supported. `'c'` restricts to line styles (single-price series such as funding rate). |
| `volume_precision` | number (L751) | Typical volume decimals; `0` = integers. SOL: `2`-`3`. |
| `data_status` | `"streaming"\|"endofday"\|"delayed_streaming"` (L759) | Legend data-mode icon (needs `display_data_mode` featureset). `delayed_streaming` requires `delay`. |
| `delay` | number (L766) | `0` realtime, `-1` end of day, else seconds of delay. |
| `expired` / `expiration_date` | boolean / seconds (L771, L776) | Expired futures; library requests data up to that time. Perps: omit. |
| `sector`, `industry` | string (L777-780) | Stock Security Info. Omit. |
| `currency_code` | string (L785) | Trading or converted currency; shown on price axis. `'USD'`. |
| `original_currency_code` | string (L787) | Native trading currency. |
| `unit_id`, `original_unit_id`, `unit_conversion_types` | string, string, string[] (L792-800) | Unit conversion. Omit. |
| `subsession_id`, `subsessions` | string; `LibrarySubsessionInfo[]` (L805, L810) | Extended-session data. Not applicable to 24x7 crypto. `LibrarySubsessionInfo {description, id: "regular"\|"extended"\|"premarket"\|"postmarket"\|"24h"\|"night", session, "session-correction"?, "session-display"?}` (L427-450, L1165). |
| `price_source_id`, `price_sources` | string; `SymbolInfoPriceSource[]` `{id,name}` (L816, L826) | Legend price source ("Spot Price", "Bid"); needs `symbol_info_price_source` featureset. Optionally label "Coinbase last trade" vs "HL mark". |
| `logo_urls` | `[string] \| [string,string]` (L844) | Needs `show_symbol_logos`. |
| `exchange_logo` | string (L862) | Needs `show_exchange_logos`. |
| `library_custom_fields` | `Record<string, unknown>` (L870) | Opaque metadata the library ignores; readable later via `IChartWidgetApi.symbolExt`. Use for `{asset:'SOL', venue:'coinbase', kind:'spot'}` so `getMarks` knows which ledger to read. |

Not in the d.ts: the docs' `resolveSymbol` example also contains `pointvalue` (ctx L39508); it is not a declared `LibrarySymbolInfo` field, do not rely on it.

#### 3.1 pricescale / minmov math

- Decimal display: `pricescale = 10^d` where d = decimals shown. Tick size = `minmov / pricescale`. Price labels are rendered with d decimals. (ctx L38232-38243)
- Examples from the docs: tick 0.01 -> `minmov=1, pricescale=100`; tick 0.0125 -> `minmov=125, pricescale=10000`; tick 0.20 -> `minmov=20, pricescale=100`. (ctx L38241-38243)
- **SOL spot, tick 0.01:** `pricescale: 100, minmov: 1` -> tick = 1/100 = 0.01, labels like `142.37`. For a 3-decimal venue (tick 0.001): `pricescale: 1000, minmov: 1`.
- **Low-priced token, tick 1e-8** (e.g. quoted to 8 decimals): `pricescale: 100000000, minmov: 1` -> tick = 1/1e8 = 0.00000001. If the instrument moves in steps of 5e-8: `minmov: 5, pricescale: 100000000`.
- Derive from a venue tick string (tutorial): strip trailing zeros of `tickSize` (`"0.01000000"` -> `"0.01"`), `pricescale = 10 ** (digits after the dot)`, `1` if no dot; use `minmov: 1`. Works only when the tick is a power of ten; for ticks like `0.05`, use `minmov=5, pricescale=100`. (ctx L59972-59981)
- Variable tick: `variable_tick_size` overrides `pricescale`/`minmov` per price band but both must still be present. (ctx L38245-38258)
- Pick `pricescale` so that the **smallest price you will ever display** keeps significant digits; a too-small `pricescale` rounds low-priced tokens to `0.00`.

### 4. Bars, `getBars` paging, resolutions, alignment, time zones

#### 4.1 Bar object (datafeed d.ts L17-36)

```
{ time: number /* ms since epoch, UTC */, open, high, low, close: number, volume?: number }
```
- Intraday `time` = **start** of the bar, aligned to the symbol session. Example: 5-minute bars; every update between 10:00:00 and 10:04:59 must carry `time` = 10:00:00 UTC. (ctx L37868-37870, L40665-40667)
- Daily/weekly/monthly `time` = **00:00:00 UTC of the trading day** (monthly = first trading day of the month), never the session start; do not shift for time zone. (ctx L40653-40663, L38604-38605)
- Order: ascending, strictly increasing `time`. No two bars share a `time`. (ctx L39458-39462, L37847-37854)
- Single-price data: set `open=high=low=close=price`, or `visible_plots_set:'c'`. (ctx L39585-39594)
- Bars outside `session`: dropped on intraday resolutions; on D/W/M shifted forward to the next trading day and merged into that day's bar. Filter on the backend. (ctx L37865)

#### 4.2 `getBars` paging algorithm

1. Library computes how many bars it needs (`countBack`, includes indicator warm-up) and a `[from, to)` window (seconds; `to` exclusive). `firstDataRequest=true` for the first call of a load. (ctx L39464-39470)
2. **Return `countBack` bars ending just before `to`. `countBack` beats `from`.** If the window holds fewer than `countBack` bars, append **earlier** bars (before `from`) until the count is met. If the window holds more than `countBack`, return all of them (do not truncate). Return all existing bars in the window. Return at least 2 bars (one bar can break clicks). (ctx L39472-39483)
3. If you return fewer than requested, the library issues another `getBars` for the remainder, with `to` = earliest bar already received and `countBack` = remainder (doc example: 329 -> 157 received -> asks 172 -> 169 -> asks 3 -> 2 -> asks 2). This chain is normal but wasteful. (ctx L37752-37802)
4. Empty array and **no older data exists** -> `onResult([], {noData: true})`; otherwise the library asks forever ("infinite data requests"). UDF: `s: "no_data"`. (ctx L37824-37831, L39483)
5. Empty array but older data exists (market closed, holiday, weekend, venue outage) -> any one of: `[]` (library asks the next portion), `{nextTime: <ms of nearest earlier bar>}`, or ignore the dates and return `countBack` bars before `to`. (ctx L37814-37822, L38586-38599)
6. Do not include a bar at `to`: it was delivered in the previous response -> `Assertion failed: data must have unique times`. (ctx L37853)
7. First-call bookkeeping: on `firstDataRequest` remember the last bar returned; streaming must continue from it (tutorial `lastBarsCache`). (ctx L60273-60277)
8. Requested range may exceed the visible range (indicators). Requested range may fall in a closed market; that is expected. (ctx L37810-37822)

Sketch of correct `getBars` over a local sorted array (`bars`, ms) with `countBack`:
```js
const toMs = p.to * 1000, fromMs = p.from * 1000;
let hi = lowerBound(bars, toMs);                 // first index with time >= toMs  (exclusive end)
let lo = Math.min(lowerBound(bars, fromMs), Math.max(0, hi - p.countBack)); // widen to satisfy countBack
const out = bars.slice(lo, hi);
if (out.length === 0) return cb([], { noData: lo === 0 }); // nothing older => noData
cb(out.map(b => ({ ...b })));                    // copies, async via setTimeout
```

#### 4.3 What causes gaps, duplicates and shifted bars

| Symptom | Cause |
|---|---|
| Gap in chart | Datafeed returned no bar for that period. In-session no-trade minutes: `has_empty_bars:true` (or `inactivity_gaps` featureset to show whitespace). Closed days: `session_holidays`. (ctx L37960-37977) |
| `Assertion failed: data must have unique times` | A bar at `to` included, duplicate times across responses, or custom-indicator time mapping errors. (ctx L37847-37854) |
| `putToCacheNewBar: time violation` | A bar with `time` < last chart bar was pushed via `onTick`; historical bars cannot be updated via `subscribeBars`; or updates routed to the wrong subscriber. Fix history with `resetCache` then `resetData`. (ctx L37833-37841, L39604-39609) |
| Bar times differ from feed | Wrong `timezone`/`session`, ms vs s, update time not floored to bar start, or multi-day resolution alignment. Library shifts to the nearest expected bar start. (ctx L37856-37894) |
| Heikin-Ashi/Renko wrong, candles fine | Misaligned timestamps are shifted for standard styles but corrupt sequential styles; fix the feed. (ctx L37979-37993) |
| New bar missing right after close | Expected; a bar appears only on the first update for the new interval. (ctx L37953-37958) |

#### 4.4 Resolution strings and how unsupported ones are built

| Resolution | String | Notes |
|---|---|---|
| Ticks | `1T`, `5T`, `100T` | needs `has_ticks`, `tick_resolution` featureset; cannot be aggregated above seconds |
| Seconds | `1S` | needs `has_seconds`, `seconds_multipliers`, `seconds_resolution` featureset |
| Minutes | `1`, `5`, `15` | `has_intraday`, `intraday_multipliers` |
| Hours | minutes: `60`, `120`, `240` | via API use `120`, not `2h` (`setResolution('120')`) |
| Days | `1D` or `D`, `3D` | `has_daily`, `daily_multipliers` |
| Weeks | `1W` or `W` | `has_weekly_and_monthly`, `weekly_multipliers` |
| Months / years | `1M`, `3M`, `12M` (= 1 year) | `monthly_multipliers` |

(ctx L63850-63868, L63943-63947; datafeed d.ts L1195-1211)

- Library builds a resolution you list in `supported_resolutions` but do not serve, by combining smaller served bars listed in the `*_multipliers`. Doc example: `intraday_multipliers ["1","2"]`, `supported_resolutions ["1","2","5"]` -> `getBars` is called only with `'1'` and `'2'`; `5` is built from `1` (2 does not divide 5). Which base the library picks beyond that example is not stated in the assigned text. (ctx L40505-40511, L40571-40611)
- Cannot be built: daily/weekly/monthly from intraday; anything above seconds from ticks. (ctx L40514-40521)
- Every resolution listed in a `*_multipliers` array **must** be handled inside your `getBars` (`if (resolution === '1') ...`). (ctx L40567-40569)
- Switching to a symbol that lacks the current resolution flips the chart to its first supported resolution. (ctx L40503)
- `disable_resolution_rebuild` featureset: show bars exactly as the feed provides; then the library cannot build unsupported resolutions (no 5m from 1m). (ctx L63991-64001)

#### 4.5 Bar alignment, sessions, time

- Library aligns each bar to the start of its period. Multi-day/week/month periods count from the **beginning of the year**: days from Jan 1 (24x7: every calendar day counted), weeks from the first full week, months from January; counter restarts each year, so a period at year boundary can be short (`3D` after 2022-12-30 is 2023-01-01). Example: Aug 28 2025 is zero-based day 239, period start `floor(239/3)*3 = 237` -> Aug 26. (ctx L63949-63985)
- A session's last time is non-inclusive; the first bar starts at the session open and later bars are offset from it (session starting 09:15 with 1h bars -> 09:15, 10:15 ...). With `24x7` + `Etc/UTC`, 1m/5m/1h bars align on the UTC clock and daily bars are UTC days. (ctx L40307-40308, L40389-40391)
- Session string grammar: `24x7`; `0930-1600` (Mon-Fri); overnight when start > end or equal (`1600-0930`), `F`/`Fn` prefix for previous days (`1700F-2200`, n <= 6); times > 2400 span midnight (`0930-2730`); comma = multiple sessions per day; `:n` selects days (1 = Sunday ... 7 = Saturday); `|` separates per-day-set sessions; `1;...` / `...;6` sets first day of week; `SESSION#YYYYMMDD/SESSION` is past session history. (ctx L40326-40470)
- Extended sessions (pre/post-market) are for equities; they need `pre_post_market_sessions` featureset, `subsession_id`, `subsessions`, and a second `resolveSymbol` call with `extension.session`. Not needed for crypto. (ctx L39859-40256)
- Time-zone rules (symbol `timezone` and chart timezone):
  - `LibrarySymbolInfo.timezone` is of type `Timezone = "Etc/UTC" | CustomTimezones` where `CustomTimezones` is the 110-name union in d.ts L1160 (Africa/..., America/..., Asia/..., Atlantic/..., Australia/..., Europe/..., Pacific/..., `US/Mountain`). Always send an exact name from that set; crypto uses `Etc/UTC`.
  - The chart's display zone is separate: widget `timezone` option / `overrides: {timezone: 'America/New_York'}` / `applyOverrides({timezone})` / `activeChart().getTimezoneApi().setTimezone(...)`. Users can also switch in the bottom bar or Settings. Set it to `Etc/UTC` when your ledger is UTC epoch. (ctx L65899-65933)
  - `custom_timezones: [{id, alias, title}]` maps a custom id to a built-in zone or a GMT zone `Etc/GMT[+|-]H[:MM]`; the sign follows POSIX (reversed): `Etc/GMT+2` = 2 h **behind** GMT, `Etc/GMT-4` = 4 h **ahead**, `Etc/GMT+0` = `Etc/UTC`. GMT zones are valid only in `alias`. Alias DST must match the real zone. (ctx L66040-66097)
  - The docs list `Asia/Astana` where d.ts has `Asia/Almaty` (see 8.2).
  - The library handles DST itself; never pre-shift timestamps. (ctx L37872, L40657-40676)

### 5. Streaming

#### 5.1 `subscribeBars` contract

- A **dataset** = symbol + resolution + currency + chart type. Each dataset gets its own `listenerGuid`. A second chart on the same dataset reuses the subscription (no second `subscribeBars`). Several subscriptions overlap (old one lives ~5 s after a switch); route each tick to **every** matching callback and keep going until `unsubscribeBars(thatGuid)`. (ctx L39191-39250)
- `onTick(bar)` takes a **complete bar** (OHLCV state of the newest bar), not a tick or delta. (ctx L39228-39230)
- Two legal actions only: **update the last bar** (same `time`; library replaces the whole bar, every OHLCV field overwritten, no merge) or **append a newer bar** (`time` > last). Updating a bar older than the last, or sending a bar of another dataset, causes `putToCacheNewBar: time violation`. (ctx L39598-39633, L39231-39235)
- Because replacement is total, the datafeed must carry the **full bar state**. Example: last bar `{t, o10, h12, l9, c11}` + price 14 -> send `{t, o10, h14, l9, c14}`. (ctx L39611-39633)
- `onResetCacheNeededCallback()`: call it when already-delivered bar data has changed (e.g. after a socket reconnect that may have missed trades). It tells the library to drop cached bars; pair with `getBars` serving corrected data. Tutorial calls it for every handler on reconnect. (d.ts L339; ctx L60498, L60849-60851, L60867-60875)
- Changing history in place: `widget.resetCache()` then `activeChart().resetData()` (optionally `request_only_visible_range_on_reset` featureset). After connectivity loss the library does not recover; you must do this. (ctx L37896-37906, L39607)
- No new-bar event: the library has no "bar closed" callback. A new bar exists only after the first update for the next interval arrives. (ctx L37953-37958)

#### 5.2 Tutorial pattern: websocket -> bar

1. One shared socket for all subscriptions (`wss://stream.binance.com:9443/ws` in the tutorial); delay first connect ~100 ms to skip initial subscribe/unsubscribe churn. (ctx L60500-60560)
2. Reference-count streams by stream name: `SUBSCRIBE` for the first handler, `UNSUBSCRIBE` when the last leaves; map `subscriberUID -> streamName`. Handler = `{id, callback, onResetCacheNeededCallback, resolution, lastBar, isDirty}`. (ctx L60562-60699)
3. Two modes per resolution (`RESOLUTION_SPECS`: `interval`, `aggregate`, `streamType`, `streamInterval`): native resolutions forward server-built klines (`kline.t` is bar open ms); non-native resolutions (2, 4, 10, 90, 180 min in the tutorial) are rebuilt from the raw trade stream. (ctx L59784-59819, L60462-60467)
4. Throttle: store the latest bar per handler, mark `isDirty`, flush with `setInterval` every `UPDATE_FREQUENCY = 250` ms and only if dirty. (ctx L60831-60845)
5. Reconnect: on `close`, if streams remain, retry after `reconnectDelay` doubling from 1 s to `MAX_RECONNECT_DELAY = 30 s`; reset to 1 s on open; on re-open call `onResetCacheNeededCallback` (if it connected before) and re-send every `SUBSCRIBE`. Cancel timers once no subscribers remain. (ctx L60849-60923)
6. `subscribeBars` passes the last bar from `getBars` (`lastBarsCache`) into the stream so the live bar continues seamlessly. (ctx L60480-60490)
7. Helpers: `barStartTime(ms, res)` floors a timestamp to its bar open (intraday: `floor(ms / resMs) * resMs`; `1D`: UTC midnight; `1W`: Monday 00:00 UTC in the tutorial; `1M`: first of month); `getNextBarTime(barTime, res)` = `barTime + resMs` (month: +1 calendar month). (ctx L59854-59902)

#### 5.3 Aggregating trades/ticks into the current bar (equations)

Let `R` = resolution length in ms (`1`->60000, `5`->300000, `60`->3600000); a trade is `(t, p, q)` = (time ms, price, size); `B` = current bar `{time, open, high, low, close, volume}` or null.

```
start(t) = floor(t / R) * R                          # bar open containing t (24x7, UTC-aligned)

if B == null or start(t) > B.time:                   # new bar (equivalently t >= B.time + R)
    B = { time: start(t), open: p, high: p, low: p, close: p, volume: q }
elif start(t) == B.time:                             # same bar: update in place
    B.high   = max(B.high, p)
    B.low    = min(B.low,  p)
    B.close  = p                                     # open never changes
    B.volume = B.volume + q
else:                                                # start(t) < B.time: late trade for a closed bar
    ignore it (sending it as a bar = time violation); if it must count, fix history + resetCache/resetData
emit copy of B via onTick (throttled)
```
Higher-from-lower aggregation (history rebuild): group base bars by `start(base.time)`; `open` = first base open, `high` = max highs, `low` = min lows, `close` = last base close, `volume` = sum. (ctx L60189-60216)

Seeding rule: the first live bar must start from the bar `getBars` returned last (not from the first tick) or `open/high/low/volume` are wiped by replacement. Do not count a trade both in the REST-seeded bar and in the stream: de-duplicate by trade id or by a snapshot time cut-off.

Quote-vs-bar caution (derived): a mid, mark or index price stream is not a trade stream; label it as such (`price_sources`) and do not mix it with trade-based history bars.

### 6. UDF adapter (ctx L38299-38799)

Usage: `new Datafeeds.UDFCompatibleDatafeed(datafeedURL, updateFrequency = 10000 ms, limitedServerResponse?)`; `limitedServerResponse = {maxResponseLength: number, expectedOrder: "latestFirst" | "earliestFirst"}` for servers that chunk. No streaming out of the box (the adapter polls). All times in **seconds**; adapter converts `t`/`nextTime` to ms. (ctx L38346-38359, L38603)

"Response as a table": a column equal for all rows may be sent as a scalar, otherwise an array per column. (ctx L38361-38390)

| Endpoint | Query params | Response |
|---|---|---|
| `GET /config` | none | `DatafeedConfiguration` JSON **plus** `supports_search`, `supports_group_request` (one must be true). Defaults listed in section 2. |
| `GET /symbol_info?group=<name>` | `group` | Only when `supports_group_request`. 404 if group unknown. Table keys: `symbol`, `exchange_listed_name`, `description`, `minmovement`, `minmovement2`, `fractional`, `pricescale`, `has-intraday`, `has-daily`, `has-weekly-and-monthly`, `visible-plots-set`, `type`, `ticker`, `timezone`, `session-regular` (-> `session`), `session-holidays`, `corrections`, `supported-resolutions`, `intraday-multipliers`, `volume_precision`, `has-empty-bars`. Inefficient above ~100 symbols. |
| `GET /search` | `query`, `type`, `exchange`, `limit` | Array of `SearchSymbolResultItem`. Needs `supports_group_request:false` and `supports_search:true`. Example `/search?query=AA&type=stock&exchange=NYSE&limit=15`. |
| `GET /symbols` | `symbol` (name or `EXCHANGE:NAME`) | One `LibrarySymbolInfo` object. Same flags as `/search`. |
| `GET /history` | `symbol`, `from` (s, UTC), `to` (s, exclusive), `resolution`, `countback` (priority over `from`; if set ignore `from`) | Table: `s` (`ok`\|`error`\|`no_data`), `errmsg`, `t` (s, bar open), `c`, optional `o`,`h`,`l`,`v`, optional `nextTime` (s, with `no_data`). Prices are numbers not strings. Daily `t` = 00:00 UTC of the trading day; monthly = first trading day. Example OK: `{s:"ok", t:[...], c:[...], o:[...], h:[...], l:[...], v:[...]}`; holiday: `{s:"no_data", nextTime: 1428001140}`. Handle `countback` to avoid empty ranges. |
| `GET /marks` | `symbol`, `from`, `to` (s, visible range), `resolution` | Table: `id`, `time` (s), `color`, `text`, `label`, `labelFontColor`, `minSize`. Only first label character shown (2 with `two_character_bar_marks_labels`). Needs `supports_marks:true`. |
| `GET /timescale_marks` | same as `/marks` | **Array of objects** (not a table): `id`, `color`, `label`, `time` (s), `tooltip`, optional `shape` (`TimeScaleMarkShape`). The doc says it is gated by `supports_marks`; d.ts names `supports_timescale_marks` (set both). |
| `GET /time` | none | Plain number: server Unix seconds (`1445324591`). |
| `GET /quotes` | `symbols=<t1>,<t2>,...` (URL-encoded; `NYSE%3AAA%2CNYSE%3AF`) | `{s:"ok"\|"error", errmsg?, d: QuoteData[]}`, each `{s, n, v:{ch, chp, short_name, exchange, description, lp, ask, bid, open_price, high_price, low_price, prev_close_price, volume}}`. Trading Platform only. |

### 7. Marks and timescale marks (objects)

`Mark` (datafeed d.ts L872-926), returned by `getMarks`; drawn on a bar:

| Field | Type | Meaning |
|---|---|---|
| `id` | `string \| number` | Unique mark id. |
| `time` | number | Unix **seconds**; must equal a bar's time at the current resolution. |
| `color` | `MarkConstColors \| MarkCustomColor` | `"red"\|"green"\|"blue"\|"yellow"` or `{border: string, background: string}`. (Tutorial also passes `purple`/`orange`, outside the d.ts union; prefer `MarkCustomColor`.) |
| `text` | `string` | Popup text (d.ts). The doc examples pass `string[]`; follow d.ts and test. |
| `customTooltip?` | string | Trading Platform: opaque payload for your own `tv-custom-bar-mark` custom element (never parsed as HTML). |
| `label` | string | Letter in the mark circle; 1st char only unless `two_character_bar_marks_labels`. |
| `labelFontColor` | string | Letter colour. |
| `minSize` | number | Minimum circle size in px. |
| `borderWidth?` / `hoveredBorderWidth?` | number | Border width, normal / hover. |
| `imageUrl?` | string | Image inside the mark (square, any browser format, `data:` OK). |
| `showLabelWhenImageLoaded?` | boolean (default false) | Keep the letter when an image loaded. |

`TimescaleMark` (d.ts L1098-1151), returned by `getTimescaleMarks`; drawn on the time axis:

| Field | Type | Meaning |
|---|---|---|
| `id` | `string \| number` | Unique id. |
| `time` | number | Unix seconds. |
| `color` | `MarkConstColors \| string` | Mark colour (CSS string allowed). |
| `labelFontColor?` | `MarkConstColors \| string` | Label colour; defaults to `color`. |
| `label` | string | Letter. |
| `tooltip` | `string[]` | Popup lines (docs show light markdown such as `**bold**` and `_Note_`). |
| `customTooltip?` | string | Trading Platform custom element `tv-custom-timescale-mark`. |
| `shape?` | `"circle" \| "earningUp" \| "earningDown" \| "earning"` | Marker shape. |
| `imageUrl?`, `showLabelWhenImageLoaded?` | string, boolean | As above. |

Rules: both callbacks fire **once per request** and for the visible range in seconds; marks need `supports_marks` / `supports_timescale_marks`; a bar holds at most 10 marks; `customTooltip` is registered through `custom_js_urls` or `addCustomJSFile`. Out-of-section but useful: `activeChart().refreshMarks()` forces re-request of all marks; `clearMarks(ClearMarksMode.All=0 | BarMarks=1 | TimeScaleMarks=2)` removes them. (ctx L14378-14398, L3319-3326)

### 8. Common issues

#### 8.1 Symptom -> cause -> fix

1. `getBars` called many times -> returned fewer bars than `countBack` -> return earlier bars up to `countBack` (ctx L37752-37804).
2. Bars change after you handed them over -> library mutates `Bar` objects -> pass copies (ctx L37806-37808).
3. Requested range wider than visible -> indicators need warm-up history -> return what is asked (ctx L37810-37812).
4. Request for closed-market dates -> expected -> return `[]`, `nextTime` (ms), or the `countBack` bars before `to` (ctx L37814-37822).
5. Endless `getBars` -> end of history never signalled -> `{noData: true}` (UDF `s:"no_data"`) (ctx L37824-37831).
6. `putToCacheNewBar: time violation` -> bar older than last, historical bar updated, update sent to wrong subscriber, or D/W/M time not 00:00 UTC -> only update last or append newer, route by `listenerGuid`, floor to bar start (ctx L37833-37841).
7. `Maximum call stack size exceeded` -> synchronous callback -> `setTimeout(..., 0)` (ctx L37843-37845).
8. `Assertion failed: data must have unique times` -> bar at `to` or duplicate times -> exclude `to`, de-duplicate (ctx L37847-37854).
9. Chart bar times differ from feed -> wrong `timezone`/`session`, seconds not ms, update time not floored, multi-day alignment -> fix symbol info, floor to bar open (ctx L37856-37894).
10. Library offline / lost connection -> no auto-recovery -> `resetCache()` then `resetData()`; for offline apps resolve a fake symbol name to force a fresh `resolveSymbol` (ctx L37896-37925).
11. TP quotes not shown -> `n` not identical to requested symbol, wrong value types, zero bid/ask, extra fields -> fix `QuoteOkData` (ctx L37927-37938).
12. TP UI (Buy/Sell, Order Ticket, Account Manager, menus) ~10 s delay -> invalid quotes timeout -> fix `getQuotes`/`subscribeQuotes` (ctx L37940-37951).
13. New bar not drawn at close -> created only on first update of the new interval -> expected (ctx L37953-37958).
14. Gaps in chart -> no bars in period -> `has_empty_bars`, `inactivity_gaps`, `session_holidays` (ctx L37960-37977).
15. Japanese charts show wrong time -> misaligned feed timestamps -> fix the feed (ctx L37979-37993).
16. Indicator (VWAP, pivots) empty after resolution change -> needs more history than loaded; library does not prefetch -> scroll back (ctx L37995-38001).
17. Weekend/holiday bars merged into next day on D/W/M -> bars outside `session` -> filter backend or use correct `session` (ctx L37865).
18. Minute resolutions show "No data here" -> `has_intraday` false or missing `intraday_multipliers`; seconds -> `has_seconds`; ticks -> `has_ticks` (ctx L40537-40565; d.ts L613, L657, L665).
19. Weekly/monthly show "No data here" -> `has_weekly_and_monthly` false and daily build failed (d.ts L703-711).
20. Stale live bars after a socket reconnect -> missed trades while down -> call `onResetCacheNeededCallback` and refetch (ctx L60849-60851).
21. Only one bar returned -> click on chart errors -> return at least 2 bars (ctx L39479).
22. Symbol search by name gets resolved twice -> `name != ticker` -> make `resolveSymbol` accept both (ctx L39413-39423).
23. Wrong `unknown_symbol` icon missing -> `hide_image_invalid_symbol` featureset enabled (ctx L39442-39445).
24. Wrong session for 24/7 -> `0000-0000` is Mon-Fri -> use `24x7` (ctx L40326-40337).
25. `*_multipliers` entries with letters (`"1S"`, `"1D"`) -> multipliers must be bare numbers in ascending order (`["1","2"]`) (d.ts L667, L695).

#### 8.2 Gaps and inconsistencies in the supplied sources

- `Mark.text` is `string` in d.ts L883 but doc examples pass arrays (ctx L38983, L60311). `Mark.color` d.ts allows four names or `{border,background}`; tutorial uses `purple`/`orange` (ctx L60336-60346).
- `getTimescaleMarks` gating: prose says `supports_marks` (ctx L39005-39008, L38654), d.ts says `supports_timescale_marks` (L120, L271). Set both.
- `Asia/Astana` (ctx L65963) vs `Asia/Almaty` (d.ts L1160); `Asia/Kabul` ordering differs. Use d.ts names.
- `pointvalue` appears in an example (ctx L39508) but not in `LibrarySymbolInfo`.
- `getVolumeProfileResolutionForPeriod` `from`/`to` are ms (d.ts L385-386) while `PeriodParams` and mark times are seconds: easy to mix up (not an inconsistency, a trap).
- The assigned text does not define the `SymbolType` list, the `request_only_visible_range_on_reset` behaviour details, or how the library chooses among several multipliers when building a resolution.
- The tutorial `getBars` filters `[from,to)` and ignores `countBack`; it therefore relies on the "call again" chain. Prefer the algorithm in 4.2.

### Use in solmargintrader

Repo facts used (verified on disk): candle cache = CSV `timestamp,open,high,low,close,volume` with `timestamp` in epoch **seconds** (daily rows at 00:00 UTC): `data/SOL_1m.csv`, `SOL_5m_last30d.csv`, `SOL_15m_last30d.csv`, `SOL_1h.csv`, `SOL_1d.csv`, `SOL_funding_1h.csv`; Coinbase fetch writes these via `backtester/core/fetch.py` (row layout is `[time, low, high, open, close, volume]`, mapped explicitly). Backtest fills: default `fill_delay=1`, i.e. orders fill at the **open of a later bar** (`backtester/core/engine.py` L5-13, L68-70); trades carry `ts, side, price, units, reason` (`backtester/core/types.py` L248-264). Forward ledger rows: `~/.config/soltui/compound/forward/SOL.jsonl`, types `call` (`bar_ts`, `decided_at = bar_ts + 300`, `call` UP/DOWN/FLAT, `price`, `composite`, `regime`, `blocked_by`, `id`), `resolve` (`id`, `next_close`, `ret_bps`, `resolved_at`), `ctx`, `adopt`. A call is made at the close of 5m bar `bar_ts` and scored on the close of the next bar.

Verify before building: the `timestamp` column is the candle open (Coinbase bucket start) and `soltui` exposes the ledger as JSON (no exporter exists in the assigned docs; a read-only exporter script is needed because a browser page cannot read `~/.config`).

#### 9.1 Architecture (zero dependencies, ESM)

```
 browser page (chart host: local http server page or an extension page; NOT an MV3 service worker)
   TradingView widget --datafeed--> createDatafeed({ history, live, marks })
        history : fetch('/data/SOL_5m.csv' ...) -> parse -> cache arrays (ms)       [backtester cache]
        live    : WebSocket trades (Coinbase spot / Hyperliquid perp) -> applyTrade -> onTick
        marks   : fetch('/api/marks.json') <- exporter reads soltui forward JSONL + backtest trades (read-only)
```
- The widget must run on a page the library licence allows (see section 0). The datafeed holds the sockets in the page, because MV3 service workers are terminated when idle.
- Never write to the ledger from the datafeed; it is a read-only view. No order path exists or is added.
- `data/` has native 1m/1h/1d for SOL and only `last30d` for 5m/15m. For 5m and 15m beyond 30 days, aggregate from `SOL_1m.csv` in JS (group by `floor(t/R)*R`; open first, high max, low min, close last, volume sum) so the chart and the signal share the same grid.

#### 9.2 Datafeed skeleton (plain JS)

```js
// datafeed.js (ESM, no deps). Times: bars in ms, PeriodParams in s.
const RES_MS = { '1': 60e3, '5': 300e3, '15': 900e3, '60': 3600e3, '1D': 86400e3 };
const CONFIG = {
  supported_resolutions: ['1', '5', '15', '60', '240', '1D'],
  exchanges: [{ value: '', name: 'All', desc: '' }, { value: 'Coinbase', name: 'Coinbase', desc: 'Spot' },
              { value: 'Hyperliquid', name: 'Hyperliquid', desc: 'Perps' }],
  symbols_types: [{ name: 'crypto', value: 'crypto' }],
  supports_marks: true, supports_timescale_marks: true, supports_time: true,
};
const SYMBOLS = {            // see 9.3
  'COINBASE:SOL-USD': { /* LibrarySymbolInfo */ },
  'HYPERLIQUID:SOL-PERP': { /* LibrarySymbolInfo */ },
};
const later = (f) => setTimeout(f, 0);                    // callbacks must be async
const lowerBound = (a, t) => { let l = 0, h = a.length; while (l < h) { const m = (l + h) >> 1; a[m].time < t ? l = m + 1 : h = m; } return l; };

export function createDatafeed({ loadBars, live, loadMarks, loadTsMarks }) {
  const lastBar = new Map();       // `${ticker}|${res}` -> last bar seen by getBars
  const subs = new Map();          // listenerGuid -> {sym, res, bar, onTick, off}
  return {
    onReady: (cb) => later(() => cb(CONFIG)),
    searchSymbols: (q, ex, type, cb) => later(() => cb(Object.values(SYMBOLS)
      .filter(s => (!ex || s.exchange === ex) && (!type || s.type === type) && s.ticker.toLowerCase().includes(q.toLowerCase()))
      .map(s => ({ symbol: s.name, description: s.description, exchange: s.exchange, ticker: s.ticker, type: s.type })))),
    resolveSymbol: (name, ok, err) => {
      const key = Object.keys(SYMBOLS).find(k => k.toLowerCase() === name.toLowerCase() || SYMBOLS[k].name.toLowerCase() === name.toLowerCase());
      later(() => key ? ok({ ...SYMBOLS[key] }) : err('unknown_symbol'));
    },
    async getBars(si, res, p, ok, err) {
      try {
        const bars = await loadBars(si.ticker, res);                  // ascending, ms, deduped, only CLOSED + the forming bar
        const hi = lowerBound(bars, p.to * 1000);                     // exclusive end
        const lo = Math.min(lowerBound(bars, p.from * 1000), Math.max(0, hi - p.countBack)); // countBack wins
        const out = bars.slice(lo, hi).map(b => ({ ...b }));
        if (p.firstDataRequest && out.length) lastBar.set(`${si.ticker}|${res}`, { ...out[out.length - 1] });
        later(() => out.length ? ok(out, { noData: false }) : ok([], { noData: lo === 0 }));
      } catch (e) { later(() => err(String(e.message || e))); }
    },
    subscribeBars(si, res, onTick, guid, onReset) {
      const ms = RES_MS[res];
      const s = { sym: si.ticker, res, bar: lastBar.get(`${si.ticker}|${res}`) || null, onTick, dirty: false };
      s.off = live.onTrade(si.ticker, ({ t, p, q }) => {              // t ms, p price, q base size
        const start = Math.floor(t / ms) * ms, b = s.bar;
        if (!b || start > b.time) s.bar = { time: start, open: p, high: p, low: p, close: p, volume: q };
        else if (start === b.time) s.bar = { ...b, high: Math.max(b.high, p), low: Math.min(b.low, p), close: p, volume: b.volume + q };
        else return;                                                    // late trade for a closed bar: never send it
        s.dirty = true;
      });
      s.reconnect = live.onReconnect?.(() => onReset());               // tell the library cached bars may be stale
      s.timer = setInterval(() => { if (s.dirty && s.bar) { s.dirty = false; onTick({ ...s.bar }); } }, 250);
      subs.set(guid, s);
    },
    unsubscribeBars(guid) { const s = subs.get(guid); if (!s) return; clearInterval(s.timer); s.off?.(); s.reconnect?.(); subs.delete(guid); },
    getServerTime: (cb) => later(() => cb(Math.floor(Date.now() / 1000))),
    getMarks: async (si, from, to, cb, res) => cb(await loadMarks(si, from, to, res)),
    getTimescaleMarks: async (si, from, to, cb, res) => cb(await loadTsMarks(si, from, to, res)),
  };
}
```
`live.onTrade(ticker, fn)` returns an unsubscribe function; implement one shared socket per venue with reference counting and backoff as in 5.2. The Coinbase and Hyperliquid websocket message formats are **not** covered by the supplied docs: read the venue docs (Coinbase Exchange `matches`, Hyperliquid `trades`) when writing `live`. Seed `s.bar` from the REST candle of the current bucket when `lastBar` is empty so open/high/low/volume are not lost; drop stream trades with `t` <= the REST snapshot time (or trade id <= last seen id) to avoid double counting volume.

#### 9.3 LibrarySymbolInfo templates

```js
const base = {
  type: 'crypto', session: '24x7', timezone: 'Etc/UTC', format: 'price', minmov: 1,
  has_intraday: true, intraday_multipliers: ['1', '5', '15', '60'],
  has_daily: true, daily_multipliers: ['1'], has_weekly_and_monthly: false,
  has_seconds: false, has_ticks: false, visible_plots_set: 'ohlcv',
  supported_resolutions: ['1', '5', '15', '60', '240', '1D'],
  volume_precision: 2, data_status: 'streaming', delay: 0, currency_code: 'USD',
};
export const SOL_SPOT = { ...base, name: 'SOL-USD', ticker: 'COINBASE:SOL-USD',
  description: 'Solana / US Dollar (Coinbase spot)', exchange: 'Coinbase', listed_exchange: 'Coinbase',
  pricescale: 100 /* tick 0.01: verify against the venue product increment */,
  library_custom_fields: { asset: 'SOL', venue: 'coinbase', kind: 'spot' } };
export const SOL_PERP = { ...base, name: 'SOL-PERP', ticker: 'HYPERLIQUID:SOL-PERP',
  description: 'Solana perpetual (Hyperliquid)', exchange: 'Hyperliquid', listed_exchange: 'Hyperliquid',
  pricescale: 1000 /* verify: perp price precision is venue-defined and outside the supplied docs */,
  library_custom_fields: { asset: 'SOL', venue: 'hyperliquid', kind: 'perp' } };
// Funding as a line-only series: visible_plots_set 'c', pricescale 1e8 (tick 1e-8), has_daily false.
export const SOL_FUNDING = { ...base, name: 'SOL-FUNDING', ticker: 'HYPERLIQUID:SOL-FUNDING',
  description: 'SOL perp funding rate (hourly)', type: 'crypto', exchange: 'Hyperliquid', listed_exchange: 'Hyperliquid',
  visible_plots_set: 'c', pricescale: 100000000, has_daily: false, intraday_multipliers: ['60'],
  supported_resolutions: ['60'], data_status: 'endofday', delay: -1, volume_precision: 0 };
```
Notes:
- `name != ticker`, so `resolveSymbol` must resolve both (done above).
- Keep spot and perp as separate symbols; they have different venues, bases and volume semantics. Do not splice them.
- Tick values (`pricescale`) must come from the venue's own increment; the numbers above are placeholders for the display format, not facts from the supplied docs.
- Set the widget `timezone` to `Etc/UTC` so the on-screen clock matches ledger epochs.

#### 9.4 Resolutions to declare for 1m / 5m

- `supported_resolutions: ['1','5','15','60','240','1D']`, `intraday_multipliers: ['1','5','15','60']`. The first four are served natively by `getBars` (`resolution` strings `'1'`,`'5'`,`'15'`,`'60'`); `240` is then built by the library from 60; `1D` served from `SOL_1d.csv` (cannot be built from intraday). Omit `W`/`M` (`has_weekly_and_monthly:false` would force expensive daily rebuilds).
- Why native `5`: the "Compound 5m" signal uses closed Coinbase 5m candles. If the chart builds 5m from 1m, a minute with no trades is simply absent and the first/last minute of the bucket can differ from Coinbase's own 5m bar. Serving the same 5m grid keeps chart candles identical to the signal's inputs. If you only have 1m, aggregate it yourself with the formulas in 5.3 and still declare `'5'` in `intraday_multipliers`.
- Every resolution listed in `intraday_multipliers` must be handled in `getBars`; `getBars` must return `[]` + `noData` for any other string.
- Do not enable `disable_resolution_rebuild` unless every resolution is served natively.

#### 9.5 Publishing forward-test calls and backtest trades as marks

Mapping rules (`getMarks(si, from, to, cb, res)`; `from/to` seconds; `res` = chart resolution):

1. Source rows: `call` rows with their matching `resolve` row (join on `id`); skip `FLAT` unless a debug toggle is on (FLAT is most bars and would flood the 10-per-bar limit).
2. **Mark time = the entry bar, not the signal bar:** `time = decided_at` (= `bar_ts + 300`), floored to the displayed resolution: `floor(decided_at / resSec) * resSec`. The mark must equal an existing bar time, so for a `15` or `60` chart several 5m calls collapse onto one bar; cap at 10 and drop to `[]` above `60` min (a `1D` bar would hold up to 288 calls).
3. Fields: `id: row.id`; `label: 'U' | 'D'`; `labelFontColor: '#ffffff'`; `minSize: 14`; `color: { border: dirColour, background: outcomeColour }` where border = green (UP) / red (DOWN), background = gray while unresolved, green on hit, red on miss; hit = `sign(ret_bps) == direction`. `text`: `"UP @ 142.37 | composite +0.42 | regime range | bar_ts 12:35Z | ret +3.1 bps (resolved)"`. Plain string (per d.ts).
4. Backtest trades: `time = floor(trade.ts, res)` where `trade.ts` is the **fill** timestamp (engine fills at a later bar's open); `label: 'B'/'S'` from `Side`; `id: 'bt:<run>:<i>'`; include `price`, `fee`, `realized_pnl`, `reason` in `text`. Use a distinct colour family (blue/yellow) from forward calls.
5. Timescale marks (`getTimescaleMarks`, array of `TimescaleMark`): scheduled `events` from the compound config (`{ts, title}` -> `label 'E'`, `tooltip [title, utc string]`, `shape 'circle'`), config `adopt` rows (`label 'A'`), and regime/cycle phase changes (`label 'R'`). `time` seconds; align to bars as well (the bar-alignment rule is stated for bar marks, not explicitly for timescale marks).
6. Only return marks for symbols whose `library_custom_fields.asset === 'SOL'`. The signal is priced on Coinbase candles; when shown on SOL-PERP add `"basis: Coinbase signal"` to the text.
7. Refresh: forward rows resolve ~5 minutes after the call, so call `widget.activeChart().refreshMarks()` after each new `resolve`/`call` (or on a timer aligned to bar close). `onDataCallback` must be called exactly once per request; never leave a request unanswered.
8. Set `supports_marks: true` and `supports_timescale_marks: true` in `onReady`.

#### 9.6 No-lookahead caveats (non-negotiable)

- The forming bar is replaced in place on every `onTick`; its `close` is just the last price and **changes**. Any signal, mark, regime or composite computed from the forming bar is lookahead the moment it is later shown against the final bar. Compute only on **closed** bars (a bar is closed once a trade/clock time >= `bar.time + R`; the library never announces it, so detect it yourself from trade time or exchange time, not from the user machine clock alone; `getServerTime` helps countdown only).
- Never put a mark for the call of bar `t` on bar `t`. The call is decided at `t`'s close (`decided_at = bar_ts + 300`) and concerns bar `t+1`; mark bar `t+1` (its open equals `decided_at`). The mark may only be returned after the entry bar exists; during live trading it appears with the first tick of `t+1`.
- Never retro-fit marks: marks come from the **append-only** ledger as recorded (`recorded_at`, `config_hash`), not from re-running the current config over history. Backtest marks come from backtest `Trade.ts` (fill bar), shown in a separate colour from forward calls so backtest hindsight is never confused with forward evidence.
- A backtest signal on bar `t` must fill at the open of `t+1` or later (`fill_delay >= 1`). Plot the fill bar, not the signal bar. A `fill_delay=0` run fills at bar `t`'s close and is still a hindsight artefact on a chart that displays `t`'s full candle.
- When `getBars` is served from the cache, never include the currently forming bar from a stale CSV as if it were final; either exclude the current bucket (`time + R > now`) or take it from the live stream. Do not re-serve a bar to the library at a different `time` than previously sent (time violation).
- Coinbase candles omit empty minutes; the live aggregation counts only observed trades. After a reconnect gap, call `onResetCacheNeededCallback` and refetch the open bucket, otherwise the live bar silently lacks volume/high/low (a lookahead-adjacent distortion once the REST candle later replaces it).
- Do not label the forward-test hit-rate on the chart until >= ~100 resolved calls (project rule: below that it is noise; `skills/five-minute-signal/SKILL.md` L135).
- Chart is display only: no marks, quotes, `getQuotes` or Trading Platform broker API are used for trading; Advanced Charts needs none of the quote/depth methods.

## Chart API, drawings and on-chart signals

Source: TradingView Charting Library docs v33.0.0 (`ctx` = `tradingview/charting-library-context.txt`; `d.ts` = `tradingview/charting_library.d.ts`). Citations: `(ctx L..)`, `(d.ts L..)`. Paraphrased; identifiers exact. All timestamps are UNIX seconds (UTC). Mark/TimescaleMark/`getMarks` are datafeed-driven, not widget calls.

### 0. Edition gate (read first)

| Capability | Advanced Charts | Trading Platform (TP) | Source |
|---|---|---|---|
| `createOrderLine`, `createPositionLine`, `createExecutionShape` | NO (removed in v29) | yes | (ctx L51918-51932; d.ts L11745-11828) |
| Multiple-chart layouts (`setLayout`, `*Sync()`) | NO | yes (up to 8 charts) | (ctx L53274-53276; d.ts L12841) |
| `customTooltip` + `custom_js_urls` custom mark tooltips | NO (plain-text tooltips only) | yes | (ctx L57619-57632; d.ts L17093+) |
| Widget bar, watchlist, Account Manager, `onPlusClick` quick trading | NO | yes | (ctx L66236-66285, L63460-63476) |
| createShape / createMultipointShape / createAnchoredShape, marks, price/time scale APIs, exportData, watermark, snapshots | yes | yes | (ctx L62856-65231) |

Docs say the Advanced-Charts way to show executions is to emulate them with `createShape` (ctx L64929-64931). Check which edition the repo's `charting_library` bundle is before using any TP-only call.

### 1. IChartWidgetApi (get via `widget.activeChart()` or `widget.chart(index)`)

Obtain after `widget.onChartReady(cb)` / `await widget.chartReady()` (d.ts L12152-12156). Method list is in `IChartWidgetApi` (d.ts L11106-12139).

| Signature | Purpose | d.ts |
|---|---|---|
| `setSymbol(symbol: string, options?: SetSymbolOptions \| () => void): Promise<boolean>` | Change symbol; `options.dataReady`, `options.doNotActivateChart` (use `true` when setting several charts in a multi layout) | L11286 |
| `setResolution(resolution: ResolutionString, options?: SetResolutionOptions \| () => void): Promise<boolean>` | Change interval (e.g. `'5'`); same options | L11301 |
| `symbol(): string` | Current symbol id (use as the id for `customSymbolStatus().symbol()`) | L11838 |
| `symbolExt(): SymbolExt \| null` | Extended symbol info (`.name` etc.) | L11848 |
| `resolution(): ResolutionString` | Current interval | L11858 |
| `setVisibleRange(range: {from, to?}, options?: {applyDefaultRightMargin?, percentRightMargin?, rejectByTimeout?}): Promise<void>` | Show a time range; `to` is ignored when a right margin option is set (latest bar used); if the range will not fit, `to` wins over `from` | L11271, L21288; (ctx L64385-64392) |
| `getVisibleRange(): {from, to}` | Visible range, includes future bar times | L11868 |
| `getVisibleBarsRange(): {from, to} \| null` | Visible range of real bars only | L11874 |
| `setTimeFrame(timeFrame: {val: TimeFrameValue, res: ResolutionString}): void` | Same as clicking a bottom time-frame button (e.g. `{val:{type:'period-back',value:'12M'},res:'1W'}`) | L12107; (ctx L64484-64496) |
| `resetData(): void` | Reload data from datafeed | L11340 |
| `setChartType(type: SeriesType): Promise<void>`; `chartType(): SeriesType` | Chart style (`SeriesType` enum: Bars 0, Candles 1, Line 2, Area 3, HeikenAshi 8, ...) | L11316, L11890 |
| `createStudy(name, forceOverlay?, lock?, inputs?, overrides?, options?: {priceScale?, checkLimit?, disableUndo?, ...}): Promise<EntityId \| null>` | Add an indicator (e.g. `createStudy('Volume', false, false, undefined, undefined, {priceScale:'new-left'})`) | L11572; (ctx L63537-63550) |
| `getAllStudies(): {id, name}[]` | List indicators on chart | L11413 |
| `getStudyById(id): IStudyApi` | Control one indicator | L11584 |
| `removeEntity(id: EntityId, options?: UndoOptions): void` | Remove a drawing, indicator or trading primitive id | L11677; (ctx L65043-65050) |
| `removeAllShapes(): void`, `removeAllStudies(): void` | Bulk remove | L11687, L11697 |
| `createShape(point: ShapePoint, options: CreateShapeOptions): Promise<EntityId>` | One-point drawing (14 allowed names, see section 2) | L11610 |
| `createMultipointShape(points: ShapePoint[], options: CreateMultipointShapeOptions): Promise<EntityId>` | Multi-point drawing (any `SupportedLineTools` except cursor tools) | L11637 |
| `createAnchoredShape(position: {x, y}, options): Promise<EntityId>` | Screen-fixed drawing, x/y as fraction from top-left (`anchored_text`, `anchored_note`) | L11651; (ctx L64943-64962) |
| `getAllShapes(): {id, name}[]` | List drawings and ids | L11402 |
| `getShapeById(id): ILineDataSourceApi` | Control one drawing | L11665 |
| `createExecutionShape(): Promise<IExecutionLineAdapter>` | TP only. Buy/sell execution arrow | L11828 |
| `createOrderLine(): Promise<IOrderLineAdapter>` | TP only. Order line | L11772 |
| `createPositionLine(): Promise<IPositionLineAdapter>` | TP only. Position line | L11806 |
| `exportData(options?: Partial<ExportDataOptions>): Promise<ExportedData>` | Export series/indicator values as arrays | L11933 |
| `crossHairMoved(): ISubscription<(p: CrossHairMovedEventParams) => void>` | `{time, price, userTime?, entityValues?, offsetX?, offsetY?}`; main series key is `'_seriesId'` | L11228, L6302 |
| `getEntityValues(): EntityValuesResult` | Data-window values without moving crosshair (`atCrosshairPosition` flag) | L11248 |
| `onDataLoaded(): ISubscription<() => void>` | Fires when new history bars load (`subscribe(null, cb, true)` = once) | L11120 |
| `onSymbolChanged(): ISubscription<(s: LibrarySymbolInfo) => void>` | Fires on symbol resolve (also on resolution/currency change) | L11130 |
| `onIntervalChanged(): ISubscription<(interval, timeFrameParams) => void>` | Fires on interval change; set `timeFrameParams.timeframe` to change date range before load | L11161; (ctx L62944-62957) |
| `onVisibleRangeChanged(): ISubscription<(range) => void>` | Visible range changed | L11176 |
| `onChartTypeChanged()`, `onHoveredSourceChanged()` | Misc subscriptions | L11189, L11254 |
| `dataReady(): Promise<boolean>` | Resolves when data is loaded (callback overload deprecated) | L11207 |
| `executeActionById(actionId: ChartActionId): void` | Trigger a built-in UI action (list below) | L11356; (ctx L62993-63037) |
| `getCheckableActionState(actionId): boolean \| null` | State of toggle actions | L11370 |
| `refreshMarks(): void` | Re-request bar and timescale marks from datafeed | L11380 |
| `clearMarks(marksToClear?: ClearMarksMode): void` | `ClearMarksMode.All=0` (default), `BarMarks=1`, `TimeScaleMarks=2` | L11391, L312 |
| `priceFormatter(): INumberFormatter` | Formatter of current series; `.format(value)` | L11882 |
| `getPanes(): IPaneApi[]` | Panes (price scales via `getRightPriceScales()` etc.) | L11904 |
| `getSeries(): ISeriesApi` | Main series API (`changePriceScale`, `setVisible`, `entityId`) | L11595, L14831 |
| `getTimeScale(): ITimeScaleApi` | Time scale API | L12042 |
| `getTimezoneApi(): ITimezoneApi` | e.g. `.setTimezone('Etc/UTC')` | L11894; (ctx L65925-65933) |
| `applyOverrides(props: object): void` | Per-chart property overrides (does NOT change price-scale mode) | L12032; (ctx L62971-62991, L63600-63604) |
| `marketStatus(): IWatchedValueReadonly<MarketStatus \| null>` | Watch session status | L12090 |
| `inactivityGaps(): IWatchedValue<boolean>` | Show/hide gaps with no trades (needs `inactivity_gaps` featureset) | L12135; (ctx L62885-62938) |
| `selection(): ISelectionApi` | Select drawings/indicators | L11707 |
| `shapesGroupController(): IShapesGroupControllerApi` | Drawing groups (`createGroupFromSelection()`) | L12009; (ctx L65079-65137) |
| `getLineToolsState()` / `applyLineToolsState(state)` / `reloadLineToolsFromServer()` | Serialize / restore all drawings | L12113-12126 |
| `bringToFront / sendToBack / bringForward / sendBackward(ids)`, `availableZOrderOperations(ids)` | Z-order | L11515-11559 |
| `getAllPanesHeight()`, `setAllPanesHeight(h[])`, `maximizeChart()`, `restoreChart()`, `isMaximized()` | Pane layout | L11469-11504 |
| `getPriceToBarRatio()`, `setPriceToBarRatio(r)`, `isPriceToBarRatioLocked()`, `setPriceToBarRatioLocked(b)` | Aspect lock | L11424-11458 |
| `setZoomEnabled(b)`, `setScrollEnabled(b)`, `zoomOut()`, `canZoomOut()` | Interaction control | L11968-11998 |
| `barTimeToEndOfPeriod(t)`, `endOfPeriodToBarTime(t)` | Bar-time helpers | L12014-12019 |
| `requestSelectBar(): Promise<number>`, `cancelSelectBar()` | Let user click a bar, returns its time | L12070-12080 |
| `setDragExportEnabled(b)` | Drag-to-export (needs `chart_drag_export` featureset and a `dragstart` handler calling `params.setData`) | L11955; (ctx L63051-63074) |
| `loadChartTemplate(name)`, `createStudyTemplate(opts)`, `applyStudyTemplate(t)` | Templates | L12086, L11732-11743 |

Not present in the supplied docs/typing: `scrollToRealtime`, `getAllShapes` filters, `setSymbolAndResolution` (use the widget-level `setSymbol(symbol, interval, cb)`, d.ts L12252). To jump to the latest bar use `setVisibleRange({from}, {applyDefaultRightMargin:true})` (ctx L62959-62969) or `resetData()`.

Widget-level (`IChartingLibraryWidget`, d.ts L12141+): `onChartReady`, `chartReady`, `headerReady`, `chart(index?)`, `activeChart()`, `activeChartIndex()`, `setActiveChart(i)`, `chartsCount()`, `subscribe(event, cb)` / `unsubscribe`, `setSymbol(symbol, interval, cb)`, `symbolInterval()`, `applyOverrides`, `applyStudiesOverrides`, `onContextMenu(cb)`, `createButton`, `createDropdown`, `removeButton`, `showNoticeDialog`, `showConfirmDialog`, `closePopupsAndDialogs()` (L12260), `takeClientScreenshot(opts?)` (L12764), `watermark()` (L12929), `customSymbolStatus()` (L12938), `selectLineTool(tool, opts?)` / `selectedLineTool()` (L12267-12300), `save/load`, `addCustomCSSFile`, `addCustomJSFile`, `changeTheme`, `hideAllDrawingTools()`, `magnetEnabled()`, `remove()`.

`ChartActionId` values for `executeActionById` (d.ts L30599; ctx L62997-63036): `addPlusButton, chartProperties, compareOrAdd, scalesProperties, paneObjectTree, insertIndicator, symbolSearch, changeInterval, timeScaleReset, chartReset, seriesHide, studyHide, lineToggleLock, lineHide, scaleSeriesOnly, drawingToolbarAction, stayInDrawingModeAction, hideAllMarks, showCountdown, showSeriesLastValue, showSymbolLabelsAction, showStudyLastValue, showStudyPlotNamesAction, undo, redo, paneRemoveAllStudiesDrawingTools, showSymbolInfoDialog`.

`widget.subscribe(event, cb)` events (`SubscribeEventsMap`, d.ts L28157-28352): `toggle_sidebar, indicators_dialog, toggle_header, edit_object_dialog, chart_load_requested, chart_loaded, mouse_down, mouse_up, drawing, study, undo, redo, undo_redo_state_changed, reset_scales, compare_add, add_compare, load_study_template, onTick(bar), onAutoSaveNeeded, onScreenshotReady(url), onMarkClick(markId), onPlusClick, onTimescaleMarkClick(markId), onSelectedLineToolChanged, layout_about_to_be_changed, layout_changed, activeChartChanged(chartIndex), series_event, study_event, drawing_event(id, type), study_properties_changed, series_properties_changed, panes_height_changed, panes_order_changed, widgetbar_visibility_changed, study_dialog_save_defaults, timeframe_interval, dragstart, dragend, chart_theme_changed`.

### 2. Drawings

#### 2.1 Point types and creation rules

- `ShapePoint = StickedPoint | PricedPoint | TimePoint` (d.ts L31380).
  - `TimePoint {time}`; `PricedPoint {time, price}` (d.ts L19866); `StickedPoint {time, channel: 'open'|'high'|'low'|'close'}` snaps to that OHLC value of the bar (d.ts L21658). (ctx L64862-64871)
- `time` is snapped to the nearest existing bar; a 09:30 point on a 1h chart is drawn at 09:00 and does not move if you later switch to 30m (ctx L64873-64877). Align to the bar grid yourself (5m: `Math.floor(t/300)*300`).
- All three create methods return `Promise<EntityId>`; keep the id for `getShapeById`/`removeEntity` (ctx L65021-65050).
- Wrong point count for a multipoint tool throws `Error: Wrong points count for "<tool>". Required "<n>"` (ctx L64903-64905). Required point counts per tool are NOT tabulated in the docs.

#### 2.2 CreateShapeOptions (d.ts L6178, base L6192, multipoint L6169, anchored L6101)

| Field | Type | Meaning |
|---|---|---|
| `shape` | see lists below | Drawing name. `createShape` accepts only: `arrow_up`, `arrow_down`, `flag`, `vertical_line`, `horizontal_line`, `long_position`, `short_position`, `icon`, `emoji`, `sticker`, `text`, `anchored_text`, `note`, `anchored_note` (d.ts L6178-6183). `createMultipointShape` accepts any `SupportedLineTools` except `cursor, dot, arrow_cursor, eraser, measure, zoom` (L6169-6173). `createAnchoredShape` accepts `anchored_text`, `anchored_note` (L6101-6105) |
| `text` | string | Label text. Do NOT set for `long_position`/`short_position` (throws `Error: Value is undefined`) |
| `lock` | boolean | Lock against move/delete |
| `disableSelection` | boolean | User cannot select it |
| `disableSave` | boolean | Not stored in saved layouts |
| `disableUndo` | boolean | User cannot cancel creation; Undo button still works for prior actions |
| `overrides` | object | Per-drawing property overrides. Docs example uses bare name `{color:'green'}` (d.ts L11643); full property names are `linetool<name>.<prop>` (see 2.5) |
| `zOrder` | `'top'\|'bottom'` | Create in front of / behind all drawings |
| `showInObjectsTree` | boolean | Show in object tree |
| `ownerStudyId` | EntityId | Attach to an indicator; drawing follows its pane and is deleted with it (ctx L64965-65019) |
| `filled` | boolean | Fill if the tool supports it |
| `icon` | number | Hex number, not string (e.g. `0xf0da`), from the Icons list (ctx L64879-64895) |
| `emoji` | string | The emoji character itself, not a code point |

#### 2.3 Supported shape names (`SupportedLineTools`, d.ts L31429, 97 identifiers)

The Drawings List (ctx L64696-64840) groups tools by UI category; display names are listed first, then the typed identifiers that map to them by name. Point counts are not documented except where noted: every name in the `createShape` list is a 1-point drawing (ctx L64858-64860); `arrow` is shown with 2 points (ctx L64998-65012); `trend_line` is shown with 2 points (d.ts L11618-11630).

| Category (ctx) | Docs display names | Identifiers |
|---|---|---|
| Trend tools (L64702) | Trendline, Arrow, Ray, Info line, Extended line, Trend angle, Horizontal line, Horizontal ray, Vertical line, Crossline, Parallel channel, Regression trend, Flat top/bottom, Disjoint channel, Anchored VWAP | `trend_line, arrow, ray, info_line, extended, trend_angle, horizontal_line, horizontal_ray, vertical_line, cross_line, parallel_channel, regression_trend, flat_bottom, disjoint_angle, anchored_vwap` |
| Gann and Fibonacci (L64720) | Fib retracement, Trend-based fib extension, Pitchfork, Schiff pitchfork, Modified Schiff pitchfork, Inside pitchfork, Fib channel, Fib time zone, Gann box, Gann square fixed, Gann square, Gann fan, Fib speed resistance fan, Trend-based fib time, Fib circles, Pitchfan, Fib spiral, Fib speed resistance arcs, Fib wedge | `fib_retracement, fib_trend_ext, pitchfork, schiff_pitchfork, schiff_pitchfork_modified, inside_pitchfork, fib_channel, fib_timezone, gannbox, gannbox_fixed, gannbox_square, gannbox_fan, fib_speed_resist_fan, fib_trend_time, fib_circles, pitchfan, fib_spiral, fib_speed_resist_arcs, fib_wedge` |
| Geometric shapes (L64742) | Brush, Highlighter, Rectangle, Circle, Ellipse, Path, Curve, Polyline, Triangle, Rotated rectangle, Arc, Double curve | `brush, highlighter, rectangle, circle, ellipse, path, curve, polyline, triangle, rotated_rectangle, arc, double_curve` |
| Annotation (L64757) | Text, Note, Anchored note, Signpost, Callout, Comment, Price label, Price note, Arrow marker, Arrow mark left/right/up/down, Flag mark | `text, note, anchored_note, signpost, callout, comment, price_label, price_note, arrow_marker, arrow_left, arrow_right, arrow_up, arrow_down, flag` |
| Chart patterns (L64774) | XABCD, Cypher, ABCD, Triangle pattern, Three drives, Head and shoulders, Elliott impulse (12345), triangle (ABCDE), triple combo (WXYXZ), correction (ABC), double combo (WXY), Cyclic lines, Time cycles, Sine line | `xabcd_pattern, cypher_pattern, abcd_pattern, triangle_pattern, 3divers_pattern, head_and_shoulders, elliott_impulse_wave, elliott_triangle_wave, elliott_triple_combo, elliott_correction, elliott_double_combo, cyclic_lines, time_cycles, sine_line` |
| Prediction and measurement (L64791) | Long position, Short position, Position forecast, Date range, Price range, Date and price range, Bars pattern, Ghost feed, Sector, Fixed range volume profile | `long_position, short_position, forecast, date_range, price_range, date_and_price_range, bars_pattern, ghost_feed, fixed_range_volume_profile` (`projection` is typed; whether it is "Sector" is not stated) |
| Icons / Stickers / Emojis (L64804-64825) | Icon set (hex codes), sticker set, Twemoji v13.0 emojis | `icon` (+ `icon: 0x...`), `sticker`, `emoji` (+ `emoji: '...'`) |
| Typed but not in the Drawings List | - | `anchored_text, balloon, text_note, projection, table` |
| Cursor/tool modes (not creatable) | Measure, Zoom in, Magnets, Stay in drawing mode, Lock all, Hide all, Remove X drawings (L64826-64840) | `cursor, dot, arrow_cursor, eraser, measure, zoom` (use with `selectLineTool`) |

`DrawingToolIdentifier` (d.ts L31141, 89 internal `LineTool*` ids such as `LineToolRiskRewardLong`, `LineToolArrowMarkUp`, `LineToolHorzLine`, `LineToolVertLine`, `LineToolFlagMark`, `LineToolTrendLine`, `LineToolRectangle`) is the vocabulary of `drawings_access.drawingTools` (d.ts L7865; ctx L65180-65186). Do not pass these to `createShape`.

#### 2.4 ILineDataSourceApi (from `getShapeById`; d.ts L13688-13772)

`isSelectionEnabled()/setSelectionEnabled(b)`, `isSavingEnabled()/setSavingEnabled(b)`, `isShowInObjectsTreeEnabled()/setShowInObjectsTreeEnabled(b)`, `isUserEditEnabled()/setUserEditEnabled(b)`, `bringToFront()`, `sendToBack()`, `getProperties(target?, nopack?)`, `setProperties(props, saveDefaults?)` (partial object, same shape as `getProperties`; `saveDefaults=true` stores as default for new drawings), `getPoints(): PricedPoint[]`, `setPoints(points: ShapePoint[])` (must give ALL points), `getAnchoredPosition()`, `setAnchoredPosition({x,y})`.

#### 2.5 Drawing property overrides worth knowing (d.ts defaults)

| Tool (override prefix) | Properties and defaults |
|---|---|
| `arrow_up` (`linetoolarrowmarkup.`) | `arrowColor #089981, color #089981, fontsize 14, bold false, italic false, showLabel true` (d.ts L1666) |
| `arrow_down` (`linetoolarrowmarkdown.`) | `arrowColor #CC2F3C, color #CC2F3C, fontsize 14, showLabel true` (d.ts L1600) |
| `flag` (`linetoolflagmark.`) | `flagColor #2962FF` (d.ts L9048) |
| `horizontal_line` (`linetoolhorzline.`) | `linecolor #2962FF, linestyle 0, linewidth 2, showPrice true, textcolor #2962FF, fontsize 12, horzLabelsAlign center, vertLabelsAlign middle, bold, italic` (d.ts L10365) |
| `vertical_line` (`linetoolvertline.`) | `linecolor #2962FF, linestyle 0, linewidth 2, extendLine true, showTime true, textcolor, fontsize 14, textOrientation vertical, horzLabelsAlign center, vertLabelsAlign middle` (d.ts L29898) |
| `trend_line` (`linetooltrendline.`) | `linecolor, linestyle, linewidth, extendLeft, extendRight, leftEnd, rightEnd, showPriceRange, showPercentPriceRange, showPipsPriceRange, showBarsRange, showDateTimeRange, showDistance, showAngle, showMiddlePoint, showPriceLabels, alwaysShowStats, statsPosition, textcolor, fontsize, bold, italic` (d.ts L29583) |
| `text` (`linetooltext.`) | `color #2962FF, fontsize 14, bold, italic, backgroundColor rgba(41,98,255,0.25), backgroundTransparency 70, borderColor #707070, drawBorder false, fillBackground false, wordWrap false, wordWrapWidth 200, fixedSize true` (d.ts L28656) |
| `icon` (`linetoolicon.`) | `color #2962FF, size 40, angle 1.5707963...` (d.ts L15663) |
| `long_position` (`linetoolriskrewardlong.`) / `short_position` (`linetoolriskrewardshort.`) | `accountSize 1000, risk 25, riskDisplayMode percents, lotSize 1, currency NONE, compact false, showPriceLabels true, alwaysShowStats false, fontsize 12, textcolor #ffffff, linecolor #808080, linewidth 1, borderColor #667b8b, drawBorder false, fillBackground true, fillLabelBackground true, labelBackgroundColor #585858, profitBackground rgba(8,153,129,0.2), profitBackgroundTransparency 80, stopBackground rgba(242,54,69,0.2), stopBackgroundTransparency 80` (d.ts L20477-20519) |
| `rectangle` | No override interface in `DrawingOverrides` (d.ts L31140); overrides are unverified for this tool |

`DrawingOverrides` (d.ts L31140) lists the 79 tools that have typed override interfaces. Overrides use the full `linetool<name>.<prop>` form in widget `overrides` / `settings_overrides` (d.ts L5586); `createShape` examples in the docs use the bare property name after the prefix (`color`). Position tool `stopLevel`/`profitLevel` are not in the typed overrides (gap).

#### 2.6 Drawing events and groups

- `widget.subscribe('drawing', e => e.value)` fires when a drawing is added; `e.label`/`e.value` = tool name and id (d.ts L22371; ctx L65060-65068).
- `widget.subscribe('drawing_event', (id, type) => ...)` with `type: DrawingEventType = "click"|"move"|"remove"|"hide"|"show"|"create"|"properties_changed"|"points_changed"` (d.ts L31103; ctx L65070-65077). Trading-primitive `setVisible` also emits `drawing_event` (d.ts L13990).
- Groups (`shapesGroupController()`): a drawing can be in one group; same pane only; empty groups auto-removed; consecutive z-indexes; groups are per symbol. Featureset `keep_selected_group_on_tool_creation` auto-groups new shapes (ctx L65079-65137).
- Attach to indicator pane: `createStudy(...)` then `ownerStudyId` (ctx L64965-65019).

### 3. Trading primitives (TP only since v29; ctx L51918-52078)

Primitives are drawing-style visuals; no broker or backend needed (ctx L51920-51932). They are separate from the drawing toolbar visibility toggles. A primitive draws only if its own `setVisible` is true AND the chart property `tradingProperties.showOrders` / `showPositions` / `showExecutions` allows it; `getVisible()` returns only the per-primitive flag (ctx L52008-52031). Defaults via widget option `trading_customization`; snapshots include them only with featureset `snapshot_trading_drawings` (ctx L64176-64193, L52033-52036).

All setters return `this` (chainable). Inside a callback `this` is the adapter. Callback registrars are overloaded: `onX(cb)` or `onX(data, cb(data))`. A button (Modify/Cancel/Close/Reverse) is shown only if you registered its callback (ctx L52004-52006).

#### 3.1 `IExecutionLineAdapter` (d.ts L13416-13541)

`remove()`, `get/setPrice(number)`, `get/setTime(number)`, `get/setDirection('buy'|'sell')` (d.ts L31091), `get/setText(string)`, `get/setTooltip(string)`, `get/setArrowHeight(number)`, `get/setArrowSpacing(number)`, `get/setFont(string)`, `get/setTextColor(string)`, `get/setArrowColor(string)`, `get/setVisible(bool)`. Docs: users cannot move or edit execution shapes; arrow size cannot be changed (ctx L64919-64924) although `setArrowHeight` exists. Default style properties (`ExecutionLineToolOverrides`, d.ts L7644): `arrowBuyColor, arrowSellColor, arrowHeight, arrowSpacing, direction, fontBold, fontFamily, fontItalic, fontSize, text, textColor, textTransparency, tooltip` (prefix `linetoolexecution.`).

#### 3.2 `IOrderLineAdapter` (d.ts L13833-14172)

- Events: `onModify(cb)`, `onMove(cb)` (after a move), `onMoving(cb)` (while dragging), `onCancel(cb)`.
- Data: `get/setPrice(number)`, `get/setText(string)`, `get/setTooltip`, `get/setModifyTooltip`, `get/setCancelTooltip`, `get/setQuantity(string)`, `get/setEditable(bool)`, `get/setCancellable(bool)`, `get/setVisible(bool)`, `get/setExtendLeft(bool)`, `get/setLineLength(value, unit?: 'pixel'|'percentage')` (default `'percentage'`; negative pixels = from left edge), `get/setLineStyle(0|1|2)` (0 solid, 1 dotted, 2 dashed; ctx L52053-52060), `get/setLineWidth`, `remove()`.
- Style: `get/setBodyFont`, `QuantityFont` (format `"bold 12px Verdana"`; ctx L52049-52051), `LineColor`, `BodyBorderColor`, `BodyBackgroundColor`, `BodyTextColor`, `QuantityBorderColor`, `QuantityBackgroundColor`, `QuantityTextColor`, `CancelButtonBorderColor`, `CancelButtonBackgroundColor`, `CancelButtonIconColor`. Colors accept `#RGB`, `#RRGGBB`, `rgb()`, `rgba()` (ctx L52042-52048).
- Defaults (`OrderLineToolOverrides`, prefix `linetoolorder.`, d.ts L17848): separate buy/sell and active/inactive colors for line, body border, body text (also `...LimitColor`, `...StopColor`), cancel button, plus `extendLeft, lineLength, lineLengthUnit, lineStyle, lineWidth, modifyTooltip, cancelTooltip, bodyFont*`.

#### 3.3 `IPositionLineAdapter` (d.ts L14290-14623)

- Events: `onModify(cb)`, `onReverse(cb)`, `onClose(cb)` (no `onMove`).
- Data: `get/setPrice`, `get/setText`, `get/setTooltip`, `get/setProtectTooltip`, `get/setCloseTooltip`, `get/setReverseTooltip`, `get/setQuantity(string)`, `get/setVisible`, `get/setExtendLeft`, `get/setLineLength(value, unit?)`, `get/setLineStyle`, `get/setLineWidth`, `remove()`.
- Style: Body/Quantity font and colors as for orders, plus `ReverseButton{Border,Background,Icon}Color` and `CloseButton{Border,Background,Icon}Color`.
- Defaults: `PositionLineToolOverrides`, prefix `linetoolposition.` (d.ts L19589): `lineBuyColor/lineSellColor`, `bodyTextPositiveColor/NegativeColor/NeutralColor` (profit/loss text colors), `quantityBackgroundBuyColor/SellColor`, etc.

#### 3.4 How drag maps to order modification

The library never sends or changes an order. Dragging an order line fires `onMoving` repeatedly, then `onMove` when released; the adapter's `getPrice()` then holds the new price (inference from the callback descriptions, d.ts L13856-13880). Clicking the body/Modify button fires `onModify`; the x button fires `onCancel`; position Close/Reverse buttons fire `onClose`/`onReverse`. Your handler must (a) call your own broker/exchange code, then (b) update or `remove()` the line. Docs example (ctx L51985-52001) sets price/quantity/text inside `onModify`. With the Broker API (TP trading terminal) the library renders and moves broker orders itself via `modifyOrder`; that path is outside this section. For a read-only/dry-run UI, register no callbacks, call `setEditable(false)` and `setCancellable(false)` (flag semantics are inferred from names; verify visually).

### 4. Marks (bar marks and timescale marks)

Marks come from the datafeed, not from widget calls. In `onReady` config set `supports_marks: true` and/or `supports_timescale_marks: true` (d.ts L6764-6768); implement `getMarks(symbolInfo, from, to, onDataCallback, resolution)` and/or `getTimescaleMarks(...)` (d.ts L13233, L13246). Call `onDataCallback(array)` exactly once per request. Up to 10 marks per bar; each mark time must equal a bar time (d.ts L13220-13224). Update by changing your data and calling `chart.refreshMarks()`; remove with `clearMarks(mode)`. Click events: `widget.subscribe('onMarkClick', id => ...)`, `widget.subscribe('onTimescaleMarkClick', id => ...)` (d.ts L28250, L28260). Featuresets: `two_character_bar_marks_labels` (2-char label), `pin_bar_mark_tooltips_on_click` (click-to-pin tooltip, no hover) (ctx L63367-63377). Bar-mark tooltips are plain text only (no HTML) (ctx L63371-63373). `hideAllMarks` action toggles visibility.

| `Mark` field (d.ts L17093) | Type | Meaning |
|---|---|---|
| `id` | string \| number | Mark id (returned in click events) |
| `time` | number | Bar time, UNIX seconds |
| `color` | `'red'\|'green'\|'blue'\|'yellow'` or `{border, background}` | Circle color (`MarkConstColors` d.ts L31253; `MarkCustomColor`) |
| `text` | string | Tooltip text |
| `label` | string | Character in the circle (2 chars with featureset) |
| `labelFontColor` | string | Label color |
| `minSize` | number | Minimum circle size, px |
| `borderWidth?`, `hoveredBorderWidth?` | number | Border widths |
| `customTooltip?` | string | TP only. Payload for `tv-custom-bar-mark` element; falls back to `text` if element not registered |
| `imageUrl?`, `showLabelWhenImageLoaded?` | string, bool | Declared on the type; documented for timescale marks |

| `TimescaleMark` field (d.ts L28855) | Type | Meaning |
|---|---|---|
| `id`, `time` | string\|number, number | As above |
| `color` | `MarkConstColors \| string` | Figure color |
| `labelFontColor?` | string | Defaults to `color` |
| `label` | string | Character inside |
| `tooltip` | `string[]` | Plain-text lines of the popup |
| `customTooltip?` | string | TP only, `tv-custom-timescale-mark` payload |
| `shape?` | `'circle'\|'earningUp'\|'earningDown'\|'earning'` (d.ts L31484) | Figure shape |
| `imageUrl?`, `showLabelWhenImageLoaded?` | string, bool | Image inside the mark (url, `data:` ok; square preferred) |

Custom tooltips (TP only; ctx L57619-58069): define a Custom Element named `tv-custom-timescale-mark` or `tv-custom-bar-mark` (one module may register both), load it with widget option `custom_js_urls: [...]` or `widget.addCustomJSFile(url)`, set `customTooltip` to an opaque string (JSON typical). The library injects it as the element's text content (never parsed as HTML); read `this.textContent`, render into a shadow root, never modify light DOM, set `max-width:100%` (drawer layout under 420 px). Theme: library toggles class `theme-dark` on `<html>`. Treat custom JS as fully trusted (same origin); never use `innerHTML` with unsanitized data. Runnable demo in TP package: `custom_marks.html` (ctx L58061-58066).

### 5. Scales, legend, layout, UI

#### 5.1 Price scale (ctx L63405-63756)

- `IPriceScaleApi` (d.ts L14637-14723) from `chart.getPanes()[i].getRightPriceScales()[j]`, `getLeftPriceScales()`, `getMainSourcePriceScale()`, `getPriceScaleById(id)`: `getMode()/setMode(PriceScaleMode)`, `isInverted()/setInverted(b)`, `isLocked()/setLocked(b)`, `isAutoScale()/setAutoScale(b)`, `getVisiblePriceRange()/setVisiblePriceRange({from,to})`, `hasMainSeries()`, `getStudies()`, `currency()/setCurrency(code|null)`, `unit()/setUnit(u|null)`, `coordinateToPrice(y)`, `priceToCoordinate(price)`.
- `PriceScaleMode` (d.ts L522): `Normal = 0` (regular), `Log = 1`, `Percentage = 2`, `IndexedTo100 = 3`. Docs example `priceScale.setMode(2)` = percentage (ctx L63626-63635).
- Initial mode via widget `overrides`: `mainSeriesProperties.priceAxisProperties.percentage | .indexedTo100 | .log | .isInverted` (booleans, default false; d.ts L4199-4217). `applyOverrides` cannot change mode (ctx L63600-63604). Other: `priceScaleSelectionStrategyName: "left"|"right"|"auto"` (d.ts L3198), `scalesProperties.textColor`, `scalesProperties.fontSize`, `scalesProperties.showSymbolLabels`.
- Up to 8 price scales on a chart (1 on mobile). Move main series: `chart.getSeries().changePriceScale('new-left')`. Attach indicator: `createStudy(..., {priceScale:'new-left'})`.
- Formatting: `LibrarySymbolInfo.format` is `'price'` or `'volume'`; `pricescale` = `10^decimals` for decimal display (`100` -> `1.01`, `1000` -> `1.005`) or `2^n` for fractional; `minmov` = tick size in units of `1/pricescale`; `minmove2`, `fractional`, `variable_tick_size` (d.ts L16501) refine; custom via widget `custom_formatters.priceFormatterFactory(symbolInfo, minTick)` returning `{format(price, signPositive)}` or `null`; decimal sign via `numeric_formatting.decimal_sign` (ctx L63652-63734; d.ts L16439-16500).

#### 5.2 Time scale (ctx L64374-64524)

- `ITimeScaleApi` (d.ts L15313-15349): `coordinateToTime(x)`, `barSpacingChanged()`, `rightOffsetChanged()` (subscriptions), `setRightOffset(bars)`, `setBarSpacing(px)`, `barSpacing()`, `rightOffset()`, `width()`, `defaultRightOffset()`, `defaultRightOffsetPercentage()`, `usePercentageRightOffset()` (watched values). No `scrollToRealtime` exists in these docs.
- Widget option `time_scale: {min_bar_spacing: 0.01}` allows more bars on screen (costly; ctx L64405-64418).
- Time frame buttons default resolution: 5Y/1Y -> W, 6M -> 120, 3M -> 60, 1M -> 30, 5D -> 5, 1D -> 1 (ctx L64465-64476); customize with `time_frames`.
- Time zone: widget `timezone`, `getTimezoneApi().setTimezone('Etc/UTC')`; 98 built-in ids (ctx L65935-66037), custom ids via `custom_timezones: [{id, alias, title}]`, alias may be `Etc/GMT+N` (POSIX sign: `Etc/GMT+2` = 2 h behind GMT) (ctx L66040-66100). Symbol `timezone` also matters.

#### 5.3 Legend (ctx L63141-63358)

Top-left list; position fixed. Featuresets: `legend_widget` (hide), `edit_buttons_in_legend`, `show_hide_button_in_legend`, `format_button_in_legend`, `delete_button_in_legend`, `legend_context_menu`, `legend_inplace_edit`, `hide_resolution_in_legend`, `display_market_status`, `legend_last_day_change`, `show_last_price_and_change_only_in_series_legend`, `show_symbol_logos`, `show_symbol_logo_in_legend`, `display_data_mode`. Overrides: `paneProperties.legendProperties.showLegend`, `paneProperties.legendProperties.showLastDayChange`, `mainSeriesProperties.statusViewStyle.symbolTextSource` (e.g. `"ticker"`). Last-day-change needs quotes (`ch`, `chp` via `getQuotes`) and is TP-only; `NaN` in the legend means `getQuotes`/`subscribeQuotes` are missing.

#### 5.4 Market status, watermark, object tree, context menu, snapshots, toolbars

- Market status popup (ctx L65761-65862): uses `LibrarySymbolInfo` session in exchange time zone; add a custom section with `widget.customSymbolStatus().symbol('EXCHANGE:SYM').setVisible(true).setColor(c).setIcon(svg).setTooltip(t).setDropDownContent([{title, color?, content: string[], action?:{text, tooltip, onClick}}])`; text via `custom_translate_function`; hide with `display_market_status` in `disabled_features`. `chart.marketStatus()` is a watched value.
- Watermark (ctx L66287-66391): `const w = widget.watermark()`; `w.color().setValue('rgba(0,150,0,0.5)')`, `w.tickerVisibility()`, `w.descriptionVisibility()`, `w.intervalVisibility()`, `w.customVisibility()` (all `.setValue(bool)`), `w.setContentProvider(provider|null)` where provider receives `WatermarkContentData` and returns `WatermarkLine[]` (text, font size, line height, vertical offset). Initial state only: `settings_adapter.initialSettings.symbolWatermark = '{"visibility":"true","color":"rgba(244,67,54,0.25)"}'` (needs `setValue`/`removeValue` functions).
- Object tree (ctx L65864-65895): featureset `show_object_tree`; `undefined` text means `exchange`/`listed_exchange` missing in `LibrarySymbolInfo` (or enable `hide_object_tree_and_price_scale_exchange_label`).
- Context menu (ctx L64591-64694): widget `context_menu: {items_processor(items, actionsFactory, params: CreateContextMenuParams) => Promise<items>, renderer_factory}` (d.ts L31052), or `widget.onContextMenu((unixTime, price) => [{position:'top'|'bottom', text, click}, {text:'-'}, {text:'-Paste'}])` (`'-'` separator; `'-<name>'` removes a built-in item). `params.menuName` and `params.detail.type` (`series, study, shape, groupOfShapes, position, order, priceScale`, with ids) identify the menu (d.ts L6107).
- Snapshots (ctx L64072-64233): `snapshot_url` (your POST endpoint) enables Copy link / Open in new tab / Tweet; download/copy image always on; hide with `header_screenshot` in `disabled_features`; `const canvas = await widget.takeClientScreenshot({hideStudiesFromLegend:true})` returns an `HTMLCanvasElement`.
- Toolbars (ctx L64527-64590): custom buttons/dropdowns only in the top toolbar via `widget.createButton(...)` / `createDropdown(...)`. Symbol search: `executeActionById('symbolSearch')`, `widget.closePopupsAndDialogs()` (ctx L64258-64277).

#### 5.5 Multiple-chart layouts (TP only; ctx L53272-53570; d.ts L12683-12850)

- Layout ids: `'s'` single, `'<n>h'` row of n, `'<n>v'` column of n, `'<a>-<b>'` a top / b bottom, `'<n>'` n in two rows, `'<n>c'` two columns, `'<n>s'` one tall chart plus n-1 column. All 38 typed values (d.ts L31263): `2h 2v 3h 3v 3s 3r 2-1 1-2 4 4v 4h 4s 4s-l 1-3 3-1 2-2-l 2-2-r 2-2 1-4 5h 5v 5s 5s-l 2-3 3-2 4-1 2-3-l 2-3-r 6 6h 6v 6c 2-4 4-2 4-3 7h 7s 8 8c 8h 8v`. Charts are indexed from 0 (see diagrams ctx L53315-53513).
- API: `widget.setLayout('4')`, `widget.layout()`, `widget.chartsCount()`, `widget.chart(i)`, `widget.activeChart()`, `widget.setActiveChart(i)`, `widget.setLayoutSizes(sizes)`, `widget.resetLayoutSizes(disableUndo?)`, `widget.unloadUnusedCharts()` (call after `layout_changed`), events `layout_about_to_be_changed(newLayout)`, `layout_changed`, `activeChartChanged(i)`.
- Sync flags (TP; `IWatchedValue<boolean>`, `.value()`, `.setValue(b)`): `widget.symbolSync()`, `intervalSync()`, `crosshairSync()`, `timeSync()`, `dateRangeSync()` (d.ts L12801-12845). Charts can be synced by symbol, interval, crosshair, time and date range (ctx L53274-53276).
- Disable: put `header_layouttoggle` and `support_multicharts` in `disabled_features`.
- When changing several charts in code, pass `{doNotActivateChart: true}` to `setSymbol`/`setResolution` (d.ts L11286-11301).

### 6. Equations and definitions

| Item | Statement | Status |
|---|---|---|
| Decimal price display | `pricescale = 10^n` shows n decimals (`100` -> `1.01`) | Documented (d.ts L16446-16454; ctx L63652-63662) |
| Tick | tick size = `minmov / pricescale` | Documented (d.ts L16468) |
| Fractional price | `xx'yy'zz`; with `minmov=1, pricescale=128, minmove2=4`: `119'16'2` = `119 + 16.25/32` | Documented (d.ts L16460-16478) |
| Variable tick | string `'0.01 10 0.02 25 0.05'`: tick 0.01 below 10, 0.02 below 25, 0.05 from 25 up | Documented (d.ts L16497-16500) |
| Percentage mode | change vs. reference price: `(p - p0) / p0 * 100`, p0 = first visible bar | Standard definition; NOT stated in these docs |
| Indexed-to-100 | `p / p0 * 100` | Standard definition; NOT stated in these docs |
| Log mode | axis position proportional to `ln(p)` | Standard definition; NOT stated in these docs |
| Risk/reward (position tool) | `R:R = |target - entry| / |entry - stop|`; long/short tools expose `accountSize`, `risk` (percent or currency per `riskDisplayMode`), `lotSize` | Tool inputs documented in d.ts L20477; formula and stop/target level properties are NOT documented |
| Time frame vs resolution | clicking `1Y` switches to resolution `W` and rescales | Documented (ctx L64456-64476) |
| Timezone offsets | `Etc/GMT+2` is 2 h BEHIND GMT (POSIX sign inversion) | Documented (ctx L66072-66100) |

### Use in solmargintrader

Assumptions: 5-minute bars (300 s grid), times in UTC seconds, `chart = widget.activeChart()` after `chartReady()`. Never register `onModify`/`onMove`/`onCancel` handlers that call an exchange; the repo forbids guessed orders and runs the extension dry-run by default. Snap every time with `const bar = t => Math.floor(t / 300) * 300;`.

Which edition? Recipes A1 and A3-TP need Trading Platform; each has an Advanced-Charts fallback (`createShape`).

**A1. Backtest trades as execution shapes (TP)**

```js
const bar = t => Math.floor(t / 300) * 300, ids = [];
async function plotTrades(trades) {            // {strategy, side:'long'|'short', entryTs, entryPx, exitTs, exitPx, pnl}
  const chart = widget.activeChart();
  const exec = async (ts, px, dir, txt) => ids.push(
    (await chart.createExecutionShape()).setTime(bar(ts)).setPrice(px).setDirection(dir)
      .setText(txt).setTooltip(txt).setArrowColor(dir === 'buy' ? '#089981' : '#F23645'));
  for (const t of trades) {
    const open = t.side === 'long' ? 'buy' : 'sell', close = open === 'buy' ? 'sell' : 'buy';
    await exec(t.entryTs, t.entryPx, open, `${t.strategy} in @${t.entryPx}`);
    await exec(t.exitTs, t.exitPx, close, `${t.strategy} out @${t.exitPx} pnl ${t.pnl.toFixed(2)}`);
  }
}
const clearTrades = () => ids.splice(0).forEach(a => a.remove());
```

**A1b. Same, Advanced Charts fallback (arrows)**

```js
async function plotTradesAC(trades) {
  const chart = widget.activeChart(), mk = (ts, px, up, text) => chart.createShape(
    { time: bar(ts), price: px },
    { shape: up ? 'arrow_up' : 'arrow_down', text, lock: true, disableSelection: true,
      disableSave: true, disableUndo: true, overrides: { arrowColor: up ? '#089981' : '#F23645' } });
  for (const t of trades) {
    const long = t.side === 'long';
    await mk(t.entryTs, t.entryPx, long, `${t.strategy} in`);
    await mk(t.exitTs, t.exitPx, !long, `${t.strategy} out ${t.pnl.toFixed(2)}`);
  }
}   // bare override names (`arrowColor`) follow the docs' `{color:'green'}` pattern; verify once visually
```

**A2. Forward-test calls (Compound 5m) as marks with the score in the tooltip (datafeed marks; works in Advanced Charts)**

```js
// 1) onReady config: { supports_marks: true, ...rest }
const calls = [];                               // {id, time, call:'UP'|'DOWN'|'FLAT', score, outcome}
datafeed.getMarks = (sym, from, to, cb) => cb(calls
  .filter(c => c.call !== 'FLAT' && c.time >= from && c.time <= to)
  .map(c => ({ id: c.id, time: bar(c.time), color: c.call === 'UP' ? 'green' : 'red',
    label: c.call === 'UP' ? 'U' : 'D', labelFontColor: '#ffffff', minSize: 18,
    text: `${c.call} score=${c.score.toFixed(2)} ${c.outcome ?? 'pending'}` })));
function onLedgerUpdate(rows) { calls.splice(0, calls.length, ...rows); widget.activeChart().refreshMarks(); }
```

**A2b. Forward-test calls as arrow_up / arrow_down drawings (no datafeed change)**

```js
async function plotCalls(rows) {                 // {time, call, score, hit?}
  const chart = widget.activeChart();
  for (const r of rows.filter(x => x.call !== 'FLAT')) {
    await chart.createShape({ time: bar(r.time), channel: r.call === 'UP' ? 'low' : 'high' }, {  // StickedPoint
      shape: r.call === 'UP' ? 'arrow_up' : 'arrow_down', text: `${r.call} ${r.score.toFixed(2)}`,
      lock: true, disableSelection: true, disableSave: true, disableUndo: true,
      overrides: { arrowColor: r.hit === false ? '#787B86' : (r.call === 'UP' ? '#089981' : '#F23645') } });
  }
}   // marks (A2) are capped at 10 per bar and need bar-aligned times; shapes are not capped
```

**A3. Ladder-grid rungs, read-only (horizontal lines; works in Advanced Charts)**

```js
const rungIds = [];
async function drawRungs(rungs, t0) {            // [{px, side:'buy'|'sell', filled:boolean}] ; sell rung = entry + 1 step
  rungIds.splice(0).forEach(id => chart.removeEntity(id));
  for (const r of rungs) rungIds.push(await chart.createShape({ time: bar(t0), price: r.px }, {
    shape: 'horizontal_line', text: `${r.side.toUpperCase()} ${r.px}${r.filled ? ' (held)' : ''}`,
    lock: true, disableSelection: true, disableSave: true, disableUndo: true,
    overrides: { linecolor: r.side === 'buy' ? '#089981' : '#F23645', linestyle: r.filled ? 0 : 2, linewidth: 1 } }));
}   // `chart` = widget.activeChart(); linestyle 0 solid, 1 dotted, 2 dashed
```

**A3b. Same rungs as order lines, display only (TP)**

```js
async function orderLineView(r) {
  const ol = await chart.createOrderLine();
  return ol.setPrice(r.px).setQuantity(String(r.qty)).setText(`${r.side.toUpperCase()} ${r.px}`)
    .setTooltip('dry-run view only').setEditable(false).setCancellable(false)
    .setLineStyle(r.filled ? 0 : 2).setLineColor(r.side === 'buy' ? '#089981' : '#F23645');
}   // no onModify/onMove/onCancel registered: buttons stay hidden, nothing can place an order
```

**A4. Aero LP range on Base (two lines plus optional band)**

```js
async function drawLpRange({ lower, upper, current, t0, t1 }) {
  const edge = (px, label) => chart.createShape({ time: bar(t0), price: px }, { shape: 'horizontal_line',
    text: label, lock: true, disableSelection: true, disableSave: true, overrides: { linecolor: '#2962FF', linestyle: 2 } });
  const ids = [await edge(lower, `LP low ${lower}`), await edge(upper, `LP high ${upper}`)];
  ids.push(await chart.createMultipointShape([{ time: bar(t0), price: upper }, { time: bar(t1), price: lower }],
    { shape: 'rectangle', lock: true, disableSelection: true, disableSave: true, filled: true }));
  return ids;                                    // out-of-range: compare `current` to lower/upper in your code, not on the chart
}   // rectangle point count (2) and overrides are not documented in the supplied files; if it throws "Wrong points count", read the Required n in the error
```

**A5. Export chart data for parity checks against the Python backtester**

```js
async function exportBars(from, to) {
  const ex = await widget.activeChart().exportData({ from, to, includeTime: true, includeSeries: true, includedStudies: [] });
  const rowMajor = ex.data.length && ex.data[0].length === ex.schema.length;   // d.ts wording is ambiguous: detect orientation
  const col = i => rowMajor ? ex.data.map(r => r[i]) : Array.from(ex.data[i]);
  const idx = Object.fromEntries(ex.schema.map((f, i) => [f.type === 'time' ? 'time' : (f.plotTitle ?? '').toLowerCase(), i]));
  const time = col(idx.time);
  return time.map((t, k) => ({ t, o: col(idx.open)[k], h: col(idx.high)[k], l: col(idx.low)[k], c: col(idx.close)[k] }));
}   // then JSON.stringify and diff against the Python backtester's bars (same UTC-second bar-open times, same tolerance)
```

Parity notes: exported bars are what the chart's datafeed delivered, so this checks datafeed-to-chart fidelity, not the exchange. `includedStudies` is required (use `[]` for series only, `'all'` for everything). `ExportedData = {schema: FieldDescriptor[], data: Float64Array[], displayedData: string[][]}` (d.ts L7762); `FieldDescriptor` is `{type:'time'}`, `{type:'userTime'}`, `{type:'value', sourceType:'series', plotTitle, sourceTitle}` or `{type:'value', sourceType:'study', sourceId, sourceTitle, ...}` (d.ts L31150). Series `plotTitle` strings (open/high/low/close/volume) are not enumerated in the docs; the recipe lowercases them. Use `includeUserTime:true` only if you need exchange-local time; keep the chart on `Etc/UTC` (`getTimezoneApi().setTimezone('Etc/UTC')`) to avoid confusion. Use `includeDisplayedValues:true` to see rounding by `pricescale`.

### Gaps (not found in the supplied sources)

- Point counts per drawing tool; `rectangle` override keys; position-tool stop/profit level properties; exact `ExportedData.data` orientation; series `plotTitle` names.
- Percentage/indexed/log scale formulas (listed above as standard definitions only).
- `scrollToRealtime`: no such method in `IChartWidgetApi` or `ITimeScaleApi`.
- Which edition (Advanced Charts vs Trading Platform) the repo bundle is; this decides A1, A3b and layout/sync features.

## Widget, featuresets, customization and persistence

Source: `tradingview/charting-library-context.txt` (cited `ctx L<a>-<b>`) plus typings in `tradingview/charting_library.d.ts` (cited `d.ts`; used for types, defaults, and anything the docs tables omit). Docs snapshot references library build 31.2.0 (ctx L60985-60995); check yours with `TradingView.version()` (ctx L48155). Paraphrased; licensed material, do not republish.

Key page ranges in ctx: Widget Constructor L36620-37328, Accessibility L37329-37400, Events L37401-37493, Widget methods L37494-37741, Featuresets L44133-45845, Common issues L45846-45911, Precedence L45912-45966, Customization overview L45967-46156, Drawing overrides L46157-46298, Overrides L46299-46345, Chart overrides L46346-46756, CSS themes L47322-47466, Custom themes API L47467-47622, Theme L47633-47662, Low-level save/load L50574-50641, API handlers L50642-50767, REST API L50768-51225, Save drawings separately L51226-51631, Saving/loading overview L51632-51818, User settings L51819-51917, Custom button L56358-56501, Snapshot server L58125-58388, Debug mode L58389-58521, Set up the widget tutorial L60963-61179, Cross-origin L36133-36196, Shortcuts L36265-36619.

---

### 1. Widget constructor options

Entry point: `new TradingView.widget(options)` (global, from `charting_library.standalone.js`) or `import { widget } from '.../charting_library.esm.js'` (ctx L48120-48140, L61041). Type: `ChartingLibraryWidgetOptions` (d.ts L4890). Required in typings: `container`, `datafeed`, `interval`, `locale` (+ `library_path` in practice). Docs group the options into tables (ctx L36665-37328). "Default" is only filled where docs/typings state one; `-` means no stated default (undefined = library behaviour).

**Core / size / data**

| Option | Type | Default | Purpose |
|---|---|---|---|
| `container` | `HTMLElement \| string` | required | DOM element (or its id) that hosts the library iframe. |
| `library_path` | `string` | - | Path to the library `static` folder, with trailing `/`. Cross-origin hosting needs an absolute `http(s)://` URL and CORS (ctx L36133-36196). |
| `datafeed` | `IBasicDataFeed \| (IBasicDataFeed & IDatafeedQuotesApi)` | required | Your data object (`onReady`, `searchSymbols`, `resolveSymbol`, `getBars`, `subscribeBars`, `unsubscribeBars`). |
| `symbol` | `string` | - | Default chart symbol. Takes precedence over `load_last_chart`'s saved symbol. |
| `interval` | `ResolutionString` | required | Default resolution (e.g. `'5'`, `'1D'`). |
| `timeframe` | `TimeframeOption` (`string` like `'1D'`/`'3M'`, or `{from,to}` unix secs) | - | Default visible time frame. Range form still loads data up to now. |
| `time_frames` | `TimeFrameItem[]` (`{text,resolution,description?,title?}`) | - | Buttons in the bottom time-frame toolbar. `text` matches `\d+(y\|m\|d)`. |
| `timezone` | `"exchange" \| Timezone` | - | Default timescale time zone. |
| `custom_timezones` | `CustomAliasedTimezone[]` | - | Extra time zones for the picker. |
| `locale` | `LanguageCode` | required | UI language (>20 supported). |
| `fullscreen` | `boolean` | `false` | Use the whole window. |
| `autosize` | `boolean` | `false` | Fill the container and track its resizes. |
| `width` / `height` | `number` | - | Fixed pixel size. For full size use `fullscreen`/`autosize`, not `'100%'`. |
| `favorites` | `Favorites<ChartTypeFavorites>` | - | Default favorite chart types, drawings, indicators, resolutions. `localStorage` favorites win; `settings_adapter` favorites win over both. |
| `additional_symbol_info_fields` | `AdditionalSymbolInfoField[]` | - | Extra rows in the Security Info dialog. |
| `compare_symbols` | `CompareSymbol[]` | - | Preset symbols in the Compare dialog. |
| `symbol_search_request_delay` | `number` (ms) | - | Debounce for Symbol Search requests. |
| `symbol_search_complete` | `(input, item?) => Promise<{symbol,name}>` | - | Rewrite the Symbol Search result before it resolves (not called for watchlist adds). |
| `snapshot_url` | `string` | - | POST target for snapshots (`multipart/form-data`, field `preparedImage`, `image/png`); must reply with the public image URL. |

**Features / customization**

| Option | Type | Default | Purpose |
|---|---|---|---|
| `enabled_features` | `ChartingLibraryFeatureset[]` | - | Featuresets to force on (section 4). |
| `disabled_features` | `ChartingLibraryFeatureset[]` | - | Featuresets to force off. Disabling a complex set disables its children. |
| `overrides` | `Partial<ChartOverrides>` | - | Default chart/drawing properties (section 5). |
| `studies_overrides` | `Partial<StudyOverrides>` | - | Default indicator style/inputs, also Compare series. |
| `settings_overrides` | `Overrides` | - | Replaces matching values loaded from saved settings (localStorage or `settings_adapter`). |
| `theme` | `"light" \| "dark"` | `"light"` | Starting theme. |
| `custom_themes` | `CustomThemes` | - | Custom 7x19 colour palettes for light/dark. |
| `toolbar_bg` | `string` | - | Toolbar background colour. |
| `custom_css_url` | `string` | - | Extra CSS file (absolute or relative to `static`). Used to hide elements with no featureset and for `--tv-color-*` variables. |
| `custom_font_family` | `string` | - | CSS `font-family` for chart text, scales, legend. Add `@import`/font-face in the custom CSS. |
| `loading_screen` | `{foregroundColor?,backgroundColor?}` | - | Spinner colours only; spinner cannot be disabled. |
| `header_widget_buttons_mode` | `"fullsize" \| "compact" \| "adaptive"` | adaptive when omitted | Top-toolbar button style. |
| `context_menu` | `{items_processor?, renderer_factory?}` | - | Edit/replace context menu items. |
| `time_scale` | `TimeScaleOptions` (`min_bar_spacing`, ...) | - | Extra time-scale tuning (more bars on screen; costs CPU/memory). |
| `numeric_formatting` | `{decimal_sign: string}` | - | Decimal separator. |
| `custom_formatters` | `{timeFormatter?, dateFormatter?, tickMarkFormatter?, priceFormatterFactory?, studyFormatterFactory?}` | - | Replace time/date/price/study formatting. `tickMarkFormatter` must render UTC. |
| `custom_translate_function` | `(orig, singular, translated) => string \| null` | - | Rename UI strings. |
| `custom_chart_description_function` | `ChartDescriptorFunction` | - | Screen-reader chart description. |
| `studies_access` | `AccessList` | - | Allow/deny list of indicators in the UI. |
| `drawings_access` | `AccessList` | - | Allow/deny list of drawing tools. Font-icon drawings are one group, `"Font Icons"`. |
| `study_count_limit` | `number` (min 2) | - | Max indicators per layout. |
| `custom_indicators_getter` | `(PineJS) => Promise<(CustomIndicator \| StudyScript)[]>` | - | Supplies custom indicators. With `workers.enabled`, indicators must be pure (no globals/DOM). |
| `volume_profile` | `{max_total_rows?, history_sessions?}` | `max_total_rows` 6000 (values <100 ignored) | Volume-profile budgets; `history_sessions` needs `studies_extend_time_scale`. |
| `image_storage_adapter` | `IImageStorageAdapter` | - | EXPERIMENTAL; storage for the image drawing tool (default embeds images in the layout). |
| `workers` | `{enabled: boolean}` | - | Try a worker thread for chart/indicator calculation; falls back to main thread if it cannot start. |
| `nonce` | `string` | - | CSP nonce applied to `<script>`/`<style>` the library creates in its iframe. Auto-inferred from `window.__tvCspNonce` or any `<script nonce>` on the host page. Strict nonce `style-src` is unsupported (needs `'unsafe-inline'`). |
| `debug` | `boolean` | `false` | Datafeed API logs in the console (same as `charting_library_debug_mode` / `setDebugMode`). |

**Saving / loading** (ctx L36950-37100, L51632-51818)

| Option | Type | Default | Purpose |
|---|---|---|---|
| `save_load_adapter` | `IExternalSaveLoadAdapter` | - | API handlers (your own backend/storage) - section 6. |
| `charts_storage_url` | `string` | - | REST API base URL. Demo: `https://saveload.tradingview.com` (testing only; accepts only `localhost`/`tradingview.com` origins). |
| `charts_storage_api_version` | `"1.0" \| "1.1"` | - | Backend version; indicator templates need `"1.1"`. |
| `client_id` | `string` | - | User-group id sent as `client=`. |
| `user_id` | `string` | - | User id within a `client_id`, sent as `user=`. |
| `load_last_chart` | `boolean` | `false` (start empty) | Auto-load the user's last saved layout; needs REST or API handlers. Remove `symbol` or it wins. |
| `saved_data` | `object` | - | Layout object (from `widget.save()`) to initialise with (low-level API). |
| `saved_data_meta_info` | `{uid,name,description}` | - | Meta for `saved_data`. |
| `auto_save_delay` | `number` (seconds) | - | Debounce for the `onAutoSaveNeeded` event. |
| `settings_adapter` | `ISettingsAdapter` | - | Persist user settings elsewhere than localStorage. |

**Trading Platform only** (`TradingTerminalWidgetOptions`, d.ts L29022; ctx L37100-37140; not available in Advanced Charts): `broker_config` / `brokerConfig` (`SingleBrokerMetaInfo`), `restConfig`, `debug_broker` (`"all" \| "broker-only" \| "host-only" \| "normal"`), `custom_js_urls` (extra JS modules run inside the iframe; fully trusted code), `widgetbar`, `rss_news_feed`, `rss_news_title`, `news_provider`, `trading_customization` (order/position line styling; also `widget.applyTradingCustomization`). There is no `broker_factory` in these typings.

Count: 57 `ChartingLibraryWidgetOptions` members (d.ts) + 9 Trading-Platform-only extras.

Tutorial pattern (ctx L61050-61170): shared options builder returning `{symbol, interval, fullscreen:true, container, datafeed, library_path, locale, symbol_search_request_delay, theme, custom_css_url, custom_font_family, enabled_features, disabled_features, overrides}`; the quote/depth methods are stripped from the datafeed clone for Advanced Charts.

---

### 2. Widget methods (`IChartingLibraryWidget`, d.ts L12141; ctx L37494-37741)

Call anything except `headerReady()` only after `chartReady()` resolves (`onChartReady(cb)` is deprecated). The docs example calls `widget.getChartLanguage()`, but the typings name it `getLanguage()` - use the typings.

| Signature | Purpose |
|---|---|
| `headerReady(): Promise<void>` | Top toolbar ready; required before `createButton`/`createDropdown`. |
| `chartReady(): Promise<void>` | Chart + data ready. |
| `onChartReady(cb): void` | Deprecated callback form of `chartReady`. |
| `chart(index?): IChartWidgetApi` | API for chart `index` (multi-chart layouts). |
| `activeChart(): IChartWidgetApi` | API for the selected chart. |
| `activeChartIndex(): number` / `setActiveChart(i): void` | Get/set selected chart. |
| `chartsCount(): number` | Charts in layout. |
| `subscribe(event, cb)` / `unsubscribe(event, cb)` | Widget events (section 3). |
| `setSymbol(symbol, interval, cb): void` | Deprecated; use `activeChart().setSymbol()`. |
| `symbolInterval(): {symbol,interval}` | Active chart symbol and interval. |
| `getLanguage(): LanguageCode` | Configured locale. |
| `remove(): void` | Destroy the widget; unusable afterwards. |
| `applyOverrides(overrides): void` | Change chart/drawing overrides on all charts without reload (per chart: `chart(i).applyOverrides`). Cannot change price-scale mode. |
| `applyStudiesOverrides(overrides): void` | Change indicator defaults for indicators created afterwards; use `IStudyApi.applyOverrides` for existing ones. |
| `applyTradingCustomization(c): Promise<void>` | Style order/position lines. |
| `changeTheme(name, options?): Promise<void>` | Switch `"light"`/`"dark"`; await it before applying colour overrides. |
| `getTheme(): ThemeName` | Current theme. |
| `customThemes(): Promise<ICustomThemesApi>` | `applyCustomThemes(obj)`, `resetCustomThemes()`. Needs `library_custom_color_themes` on. |
| `setCSSCustomProperty(name, value)` / `getCSSCustomPropertyValue(name)` | Runtime `--tv-color-*` and own CSS variables. |
| `addCustomCSSFile(url)` | Load extra CSS. |
| `addCustomJSFile(url)` | Trading Platform only. |
| `createButton(options?): HTMLElement \| string` | Top-toolbar button (after `headerReady`). Default form returns an element. |
| `removeButton(idOrElement)` | Remove such a button. |
| `createDropdown(params): Promise<IDropdownApi>` | Top-toolbar dropdown (`{title, tooltip, items:[{title,onSelect}]}`). |
| `showNoticeDialog(params): Promise<void>` | OK dialog. |
| `showConfirmDialog(params): Promise<boolean>` | OK/Cancel dialog (docs example uses Yes/No wording). |
| `showLoadChartDialog()` / `showSaveAsChartDialog()` | Open built-in layout dialogs. |
| `save(options?): Promise<object>` / `save(cb, options?)` | Low-level: return layout state. `{includeDrawings:false}` omits drawings. |
| `load(state, extendedData?): Promise<void>` | Low-level: apply a layout state. |
| `getSavedCharts(): Promise<SaveLoadChartRecord[]>` | List server-saved layouts (`{id,name,image_url,modified_iso,short_symbol,interval}`). |
| `loadChartFromServer(record)` | Load one. |
| `saveChartToServer(options?)` | Save current layout (`{chartName?, defaultChartName?}`). Used for auto-save and drawings migration. |
| `removeChartFromServer(chartId)` | Delete a server layout. |
| `onContextMenu(cb: (unixTime, price) => ContextMenuItem[])` | Add context-menu items. |
| `onShortcut(keys, cb)` | Override/add shortcuts; non-modifier keys are numeric key codes (see section 7). |
| `setShortcutsEnabled(enabled, options?): Promise<void>` / `areShortcutsEnabled(): Promise<boolean>` | Master switch for built-in shortcuts. |
| `onGrayedObjectClicked(cb)` | Click on a greyed-out drawing/study. |
| `selectLineTool(tool, options?)` / `selectedLineTool()` | Select/read the active drawing tool or cursor. |
| `takeScreenshot(): void` | Snapshot and upload to `snapshot_url`; fires `onScreenshotReady`. |
| `takeClientScreenshot(options?): Promise<HTMLCanvasElement>` | Client-side snapshot as canvas (`toBlob`/`toDataURL`); no server. |
| `getIntervals(): string[]` | Supported resolutions. |
| `getStudiesList(): string[]` / `getStudyInputs(name)` / `getStudyStyles(name)` | Indicator catalogue and schema for `createStudy`. |
| `mainSeriesPriceFormatter(): INumberFormatter` | Format prices like the chart. |
| `setDebugMode(enabled)` | Toggle Datafeed API console logging. |
| `resetCache()` | Drop cached bars for all symbols. |
| `layout()` / `setLayout(type)` / `layoutName()` / `setLayoutSizes(sizes, disableUndo?)` / `resetLayoutSizes()` / `unloadUnusedCharts()` | Multi-chart layout control. |
| `lockAllDrawingTools()` / `hideAllDrawingTools()` / `magnetEnabled()` / `magnetMode()` / `drawOnAllChartsEnabled()` | `IWatchedValue` handles for toolbar toggles. |
| `symbolSync()` / `intervalSync()` / `crosshairSync()` / `timeSync()` / `dateRangeSync()` | Trading Platform only sync toggles. |
| `navigationButtonsVisibility()` / `paneButtonsVisibility()` / `currencyAndUnitVisibility()` | `IWatchedValue<VisibilityType>`. |
| `dateFormat()` / `timeHoursFormat()` | `IWatchedValue` for axis formats. |
| `undoRedoState()` / `clearUndoHistory()` | Undo stack. |
| `supportedChartTypes()` | Read-only watched list of `ChartStyle`. |
| `watermark()` / `customSymbolStatus()` | Watermark and custom status-item APIs. |
| `startFullscreen()` / `exitFullscreen()` | Fullscreen toggle. |
| `closePopupsAndDialogs()` | Close open dialogs/menus. |
| `watchList()` / `news()` / `widgetbar()` | Trading Platform only. |

Count: 85 methods. Useful `IChartWidgetApi` members for a dashboard (d.ts): `setSymbol`, `setResolution`, `setChartType`, `setVisibleRange`/`getVisibleRange`, `resetData`, `createStudy`, `getAllStudies`, `createShape`, `createMultipointShape`, `createAnchoredShape`, `getAllShapes`, `getShapeById`, `removeEntity`, `removeAllShapes`, `createOrderLine`, `createPositionLine`, `createExecutionShape`, `getSeries`, `exportData`, `createStudyTemplate`/`applyStudyTemplate`, `getLineToolsState`/`applyLineToolsState`/`reloadLineToolsFromServer`, `applyOverrides`, `executeActionById`, `onDataLoaded`, `onSymbolChanged`, `onIntervalChanged`, `onVisibleRangeChanged`, `onChartTypeChanged`, `crossHairMoved`, `onHoveredSourceChanged`, `dataReady`, `refreshMarks`/`clearMarks`.

---

### 3. Events

Three scopes (ctx L37401-37493): widget events via `widget.subscribe(name, cb)`; chart events via `IChartWidgetApi` methods returning `ISubscription` (`.subscribe(null, cb)`, `.unsubscribe`); component events (`IWatchListApi`, `ITimezoneApi`). The library does not move chart subscriptions when the active chart changes - resubscribe on `activeChartChanged`.

**Widget events (`SubscribeEventsMap`, d.ts L28157) - 37**

| Event | Callback payload | Fires when |
|---|---|---|
| `onAutoSaveNeeded` | none | User made an undoable change (debounced by `auto_save_delay`); call `saveChartToServer`. |
| `chart_load_requested` | `(savedData: object)` | A layout is about to load (hook for migrating drawings). |
| `chart_loaded` | none | Layout finished loading. |
| `onTick` | `(tick: Bar)` | Last bar updated. |
| `onScreenshotReady` | `(url: string)` | Server returned the snapshot URL. |
| `onMarkClick` | `(markId)` | Bar mark clicked. |
| `onTimescaleMarkClick` | `(markId)` | Timescale mark clicked. |
| `onPlusClick` | `({symbol: string\|null, price, clientX, clientY, pageX, pageY, screenX, screenY})` | Price-scale Plus (quick trade) button clicked. |
| `drawing` | `{label, value}` | Drawing added (`value` = tool name). |
| `study` | `{label, value}` | Indicator added (`value` = name). |
| `drawing_event` | `(sourceId, type)`; type in `click\|move\|remove\|hide\|show\|create\|properties_changed\|points_changed` | Drawing lifecycle. |
| `study_event` | `(entityId, type)`; type in `create\|remove\|price_scale_changed\|paste_study` | Indicator lifecycle. |
| `series_event` | `("price_scale_changed")` | Main series event. |
| `study_properties_changed` | `(id)` | Indicator properties changed. |
| `series_properties_changed` | `(id)` | Main series properties changed. |
| `study_dialog_save_defaults` | `(id)` | "Save as default" in indicator settings. |
| `load_study_template` | none | Indicator template loaded. |
| `edit_object_dialog` | `{objectType, scriptTitle}` | Properties dialog opened. |
| `indicators_dialog` | none | Indicators dialog opened. |
| `compare_add` / `add_compare` | none | Compare dialog shown / compare symbol added. |
| `toggle_sidebar` / `toggle_header` | `(isHidden)` | Drawing toolbar / header shown or hidden. |
| `widgetbar_visibility_changed` | `(isVisible)` | Widget bar toggled (Trading Platform). |
| `mouse_down` / `mouse_up` | `MouseEventParams` | Pointer events. |
| `dragstart` / `dragend` | `DragStartParams` / none | Drag-export gestures (`chart_drag_export`). |
| `undo_redo_state_changed` | `(state: UndoRedoState)` | Undo stack changed. |
| `reset_scales` | none | Reset-scales clicked. |
| `layout_about_to_be_changed` / `layout_changed` | `(newLayoutType)` / none | Multi-chart layout change. |
| `activeChartChanged` | `(chartIndex)` | Selected chart changed. |
| `panes_height_changed` / `panes_order_changed` | none | Pane resize / reorder. |
| `timeframe_interval` | `(range: {val,res})` | Time frame changed. |
| `chart_theme_changed` | `(themeName, isStandardTheme, onlyActiveChart)` | Theme updated. |

**Chart events (`IChartWidgetApi`, `ISubscription`)**

| Method | Fires when |
|---|---|
| `onDataLoaded()` | New history bars loaded. |
| `onSymbolChanged()` -> `(symbolInfo: LibrarySymbolInfo)` | Symbol changed. |
| `onIntervalChanged()` -> `(interval, timeFrameParameters)` | Resolution (or time frame) changed; callback may set `timeFrameParameters.timeframe`. |
| `onVisibleRangeChanged()` -> `(range)` | Visible range changed. |
| `onChartTypeChanged()` -> `(chartType)` | Series style changed. |
| `crossHairMoved()` -> `CrossHairMovedEventParams` | Crosshair moved (time, price, ...). |
| `onHoveredSourceChanged()` -> `(sourceId)` | Hover over series/indicator. |

---

### 4. Featuresets

Enable via `enabled_features: [...]`, disable via `disabled_features: [...]` (ctx L44133-44160). Disabling a complex featureset disables its nested children (indented below, written `> child`). Doc states 193 featuresets: 63 behaviour, 24 complex/visibility-controls, 1 placement, 43 Trading Platform, 62 visibility (counted from anchors). The d.ts type `ChartingLibraryFeatureset` (d.ts L30616) is a subset (Advanced Charts); the Trading Platform names live in `TradingTerminalFeatureset` (d.ts L31508). Caveat: the doc wording of the `hide_*` / `dont_show_*` sets is inverted ("Shows ..."); in the typings, enabling these sets HIDES the thing, default off. Default = state with no option given.

**4a. Behaviour (ctx L44245-44758)**

| Featureset | Default | Effect |
|---|---|---|
| `accessible_keyboard_shortcuts` | Off | Keyboard navigation starts with Tab instead of Alt+Z; chart switching becomes Shift+Left/Right. |
| `allow_arbitrary_symbol_search_input` | Off | Enter in Symbol Search uses the typed text as-is (passed to datafeed) instead of the top hit. |
| `aria_crosshair_price_description` | Off | Screen reader announces crosshair price (English only). |
| `aria_detailed_chart_descriptions` | Off | Detailed ARIA chart description on active-chart change (English; use `custom_chart_description_function` for others). |
| `auto_enable_symbol_labels` | On | Symbol-name label when comparing symbols. |
| `axis_pressed_mouse_move_scale` | On | Axis scaling with left button held. |
| `chart_drag_export` | Off | Chart drag-event handling for drag-to-export. |
| `chart_scroll` | On | Chart scrolling. |
| `chart_zoom` | On | Chart zooming. |
| `charting_library_debug_mode` | Off | Enable logs. |
| `confirm_overwrite_if_chart_layout_with_name_exists` | Off | Confirm before overwriting a same-named layout on save/rename/save-as. |
| `create_volume_indicator_by_default` | On | Add Volume at init. |
| `create_volume_indicator_by_default_once` | On | Do not re-add Volume on symbol/resolution change. |
| `constraint_dialogs_movement` | On | Keep dialogs inside the chart. |
| `cropped_tick_marks` | On | Show partially visible price labels. |
| `custom_resolutions` | Off | Allow datafeed-defined custom resolutions in the UI. |
| `datasource_copypaste` | On | Copy/paste of drawings and indicators. |
| `determine_first_data_request_size_using_visible_range` | Off | Size first data request from the visible bar count instead of a small fixed count. |
| `disable_legend_inplace_resolution_change` | Off | Block in-place resolution change in the legend. |
| `disable_legend_inplace_symbol_change` | Off | Block in-place symbol change in the legend. |
| `disable_pulse_animation` | Off | Disable pulse on Line chart type. |
| `disable_resolution_rebuild` | Off | Show bar times exactly as the datafeed gives them. |
| `end_of_period_timescale_marks` | Off | Timeline marks show bar end time. |
| `fix_left_edge` | Off | No scrolling left of the first bar. |
| `header_in_fullscreen_mode` | Off | Header present in fullscreen. |
| `hide_price_scale_if_all_sources_hidden` | Off | Hide a price scale when all its sources are hidden. |
| `horz_touch_drag_scroll` | On | Chart handles horizontal touch drag (page not scrolled). |
| `inactivity_gaps` | Off | Show inactivity gaps within sessions. |
| `iframe_loading_compatibility_mode` | Off | Load iframe from `about:blank` + `document.write` instead of a `blob:` URL (wallet webviews, CSP forbidding `blob:`); slower. |
| `iframe_loading_same_origin` | Off | Load iframe from `library_path + 'sameorigin.html'` (real same-origin URL, also `document.write`); `sameorigin.html` must be served; CSP nonce via `window.__tvCspNonce` there. |
| `insert_indicator_dialog_shortcut` | On | `/` opens Indicators. |
| `keep_selected_group_on_tool_creation` | Off | `createShape`/`createMultipointShape` inherit the selected drawing's group when no `zOrder` is passed. |
| `legend_bar_change_colors_based_on_value` | Off | Colour legend bar-change by value sign (OHLC types use series colours). |
| `library_custom_color_themes` | On | Enables the Custom themes API (v28+). |
| `lock_visible_time_range_on_resize` | Off | Keep visible range when the chart resizes. |
| `lock_visible_time_range_when_adjusting_percentage_right_margin` | Off | Keep range when editing percentage right margin. |
| `long_press_floating_tooltip` | On | Floating OHLC tooltip on long press. |
| `low_density_bars` | Off | Allow zooming to one bar in view. |
| `mouse_wheel_scale` | On | Wheel scales the series. |
| `mouse_wheel_scroll` | On | Horizontal wheel scrolls. |
| `no_min_chart_width` | Off | Remove minimum chart width. |
| `pin_bar_mark_tooltips_on_click` | Off | Bar-mark tooltips open on click and stay pinned. |
| `pinch_scale` | On | Pinch zoom (touch). |
| `pressed_mouse_move_scroll` | On | Left-button drag scrolls. |
| `pre_post_market_price_line` | Off | Pre/post-market price lines (v29.1+). |
| `request_only_visible_range_on_reset` | Off | On data reset re-request only the visible range. |
| `right_bar_stays_on_scroll` | On | Zoom behaviour: when disabled the bar under the cursor stays put. |
| `save_shortcut` | On | Ctrl/Cmd+S saves layout. |
| `saveload_separate_drawings_storage` | Off | Store drawings apart from the layout (section 6e). |
| `seconds_resolution` | Off | Resolutions in seconds. |
| `secondary_series_extend_time_scale` | Off | Extra series can extend the time scale. |
| `shift_visible_range_on_new_bar` | On | New bar scrolls the chart one point left; off = zoom out keeping first visible point. |
| `side_toolbar_in_fullscreen_mode` | Off | Drawings toolbar in fullscreen. |
| `studies_extend_time_scale` | Off | Custom indicators with `canExtendTimeScale` may extend the scale. |
| `study_templates` | Off | Header button for indicator templates. |
| `study_symbol_ticker_description` | Off | Apply ticker/description mode to indicator symbol inputs in the status line. |
| `study_overlay_compare_legend_option` | Off | Apply `mainSeriesProperties.statusViewStyle.symbolTextSource` to overlay/compare indicators. |
| `tick_resolution` | Off | Tick resolutions. |
| `two_character_bar_marks_labels` | Off | Up to two characters in bar marks. |
| `uppercase_instrument_names` | On | Disable to allow case-sensitive symbols. |
| `use_last_visible_bar_value_in_legend` | Off | Legend shows the rightmost visible bar, not the latest. |
| `vert_touch_drag_scroll` | On | Chart handles vertical touch drag. |
| `volume_force_overlay` | On | Volume on the main pane instead of its own pane. |

**4b. Complex featuresets / visibility of controls (ctx L44759-44977)**

| Featureset | Default | Effect |
|---|---|---|
| `context_menus` | On | Any right-click menu. |
| > `legend_context_menu` | On | Legend menu. |
| > `pane_context_menu` | On | Chart pane menu. |
| > `scales_context_menu` | On | Price/time scale menu. |
| `edit_buttons_in_legend` | On | Hide/Settings/Remove buttons for indicators and extra series (off: only ellipsis menu; main-series legend buttons disabled). |
| > `legend_inplace_edit` | On | In-place legend editing (off also hides legend Symbol Search). |
| > `delete_button_in_legend` | On | Remove button. |
| > `format_button_in_legend` | On | Settings button. |
| > `show_hide_button_in_legend` | On | Hide/Show button. |
| `header_widget` | On | Whole header panel and Symbol Search. |
| > `header_chart_type` | On | Chart type button. |
| > `header_compare` | On | Compare/Add Symbol. |
| > `header_fullscreen_button` | On | Fullscreen. |
| > `header_indicators` | On | Indicators. |
| > `header_resolutions` | On | Resolution button. |
| >> `show_interval_dialog_on_key_press` | On | Digits/comma open Change Interval. |
| > `header_screenshot` | On | Snapshot button. |
| > `header_settings` | On | Chart settings button. |
| > `header_symbol_search` | On | Symbol Search button. |
| > `header_undo_redo` | On | Undo/Redo. |
| > `header_quick_search` | On | Quick search. |
| > `symbol_search_hot_key` | On | Typing opens Symbol Search. |
| `use_localstorage_for_settings` | On | Persist chart properties/settings/favorites in `localStorage`. |
| > `save_chart_properties_to_local_storage` | On | Just chart properties in `localStorage`. |

**4c. Elements placement (ctx L44978-44992)**

| Featureset | Default | Effect |
|---|---|---|
| `move_logo_to_main_pane` | Off | TradingView logo on the main pane, not the bottom pane. |

**4d. Trading Platform only (ctx L44993-45344)** - not present in Advanced Charts; inert for the dashboard.

| Featureset | Default | Effect |
|---|---|---|
| `add_to_watchlist` | On | Add-symbol-to-watchlist menu item. |
| `always_pass_called_order_to_modify` | Off | Disables passing the parent order to `modifyOrder` for bracket edits. |
| `always_require_order_confirmation` | Off | Disables one-click trading. |
| `buy_sell_buttons` | On | Legend Buy/Sell buttons. |
| > `broker_button` | On | Legend Broker button. |
| `chart_crosshair_menu` | On | Price-scale Plus button (empty without Broker API). |
| `chart_hide_close_position_button` | Off | Hide position close button. |
| `chart_hide_close_order_button` | Off | Hide order close button. |
| `chart_property_page_trading` | On | Trading section in chart settings. |
| `chart_template_storage` | Off | Chart template save/load (needs API handlers). |
| `drawing_templates` | On | Drawing Templates on the drawing toolbar. |
| `dom_widget` | Off | Depth of Market widget. |
| `dom_raw_volume_values` | Off | Full (unsuffixed) DOM volumes. |
| `static_dom` | Off | DOM static price series mode. |
| `header_layouttoggle` | On | Select Layout button. |
| `hide_right_toolbar` | Off | Hide right toolbar at init. |
| `hide_right_toolbar_tabs` | Off | Hide right toolbar tabs. |
| `keep_object_tree_widget_in_right_toolbar` | Off | Object tree stays in right toolbar (needs `right_toolbar`). |
| `legend_last_day_change` | Off | "Last day change values" chart setting. |
| `multiple_watchlists` | On | Multiple watchlists. |
| `open_account_manager` | On | Account Manager opened by default. |
| `order_info` | On | Order info section in ticket. |
| `order_panel` | On | Order Ticket (off hides Trade button too). |
| `order_panel_close_button` | On | Close Order Ticket button. |
| `order_panel_undock` | On | Undock button. |
| `prefer_symbol_name_over_fullname` | On | Show symbol name, not `exchange:name` (v28+). |
| `right_toolbar` | On | Right toolbar. |
| `show_buy_sell_buttons_on_unsupported_resolution` | Off | Keep Buy/Sell on unsupported interval. |
| `show_dom_first_time` | Off | Show DOM on first open. |
| `show_last_price_and_change_only_in_series_legend` | Off | Main legend shows only last price and change. |
| `show_order_panel_on_start` | Off | Open Order Ticket on start. |
| `show_symbol_logo_in_account_manager` | On | Logos in Account Manager (needs `show_symbol_logos`). |
| `show_symbol_logo_in_close_position_dialog` | On | Logos in Close dialog (needs `show_symbol_logos`). |
| `show_symbol_logo_in_cancel_order_dialog` | On | Logos in Cancel dialog (needs `show_symbol_logos`). |
| `show_trading_notifications_history` | On | Notifications log tab. |
| `support_multicharts` | On | Multi-chart context actions (Select Layout button stays unless `header_layouttoggle` off). |
| `trading_account_manager` | On | Account Manager. |
| `trading_notifications` | On | Trading notifications on chart. |
| `watchlist_context_menu` | On | Watchlist context menu. |
| `watchlist_import_export` | On | Watchlist import/export. |
| `watchlist_sections` | On | Watchlist sections UI. |
| `prefer_quote_short_name` | On | `short_name` in Watchlist/Details. |
| `watchlist_cross_tab_sync` | On | Watchlist cross-tab sync (v29.2.0+). |

**4e. Visibility of other controls and visual elements (ctx L45345-45845)**

| Featureset | Default | Effect |
|---|---|---|
| `adaptive_logo` | On | "Chart by TradingView" text on small screens. |
| `always_show_legend_values_on_mobile` | Off | Legend values on mobile. |
| `border_around_the_chart` | On | 2px padding around chart. |
| `chart_style_hilo` | Off | High-Low chart style option. |
| `chart_style_hilo_last_price` | Off | Last price line/label for High-Low. |
| `chart_property_page_right_margin_editor` | On | Right margin field in Settings. |
| `chart_property_page_scales` | On | Scale overrides in settings (Price Scale). |
| `clear_price_scale_on_error_or_empty_bars` | On | Clear pane scales on series error/empty. |
| `compare_symbol_search_spread_operators` | Off | Spread operators in Compare (needs `show_spread_operators`). |
| `control_bar` | On | Zoom/scroll buttons at chart bottom. |
| `countdown` | On | "Countdown to bar close" scale option. |
| `display_data_mode` | Off | Data-delayed icon/section in legend. |
| `display_legend_on_all_charts` | Off | Legend on all charts regardless of crosshair sync. |
| `display_market_status` | On | Market status in legend. |
| `dont_show_boolean_study_arguments` | Off | Hide true/false indicator arguments when enabled (doc wording inverted). |
| `go_to_date` | On | "Go to" date jump. |
| `header_saveload` | On | Save/Load layout buttons (not part of `header_widget`). |
| `hide_image_invalid_symbol` | Off | Hide invalid-symbol illustration when enabled. |
| `hide_last_na_study_output` | Off | Hide last N/A indicator output when enabled. |
| `hide_left_toolbar_by_default` | Off | Left toolbar hidden on first open when enabled. |
| `hide_main_series_symbol_from_indicator_legend` | On | Hide "Main chart symbol" input from indicator legend. |
| `hide_price_scale_global_last_bar_value` | Off | Hide global last-price label when last bar is off-screen. |
| `hide_exponentiation_spread_operator` | Off | Hide `^` operator (doc wording inverted). |
| `hide_reciprocal_spread_operator` | Off | Hide `1/x` operator (doc wording inverted). |
| `hide_object_tree_and_price_scale_exchange_label` | Off | Hide exchange label. |
| `hide_resolution_in_legend` | Off | Hide interval (D, 2D, W...) in legend and data window. |
| `hide_unresolved_symbols_in_legend` | Off | Hide unresolved symbols in legend/data window. |
| `items_favoriting` | On | Add-to-favorites star on chart types, drawings, indicators, resolutions. |
| `left_toolbar` | On | Drawings toolbar. |
| `legend_widget` | On | Legend top-left. |
| `main_series_scale_menu` | On | Bottom-right Settings button. |
| `object_tree_legend_mode` | On | Object-tree button in narrow legend. |
| `pricescale_currency` | Off | Currency menu in Settings -> Scales. |
| `pricescale_unit` | Off | Unit menu in Settings -> Scales. |
| `pre_post_market_sessions` | Off | Pre/post-market session support. |
| `property_pages` | On | All Settings pages. |
| `popup_hints` | On | Pop-up shortcut/UI hints. |
| `remove_library_container_border` | On | Border 0, padding 1px. |
| `scales_date_format` | On | Date format selector. |
| `scales_time_hours_format` | On | Time hours format selector. |
| `show_chart_property_page` | On | Chart settings page. |
| `show_average_close_price_line_and_label` | Off | Average-close line/label visibility settings (doc "Shows", typings "Hide" - ambiguous). |
| `show_exchange_logos` | Off | Exchange logos in Symbol Search. |
| `show_right_widgets_panel_by_default` | On | Right widget bar open on first launch. |
| `show_symbol_logos` | Off | Symbol logos in Search/Watchlist/dialogs. |
| `show_symbol_logo_for_compare_studies` | On | Logos for compare studies (needs `show_symbol_logos`, `show_symbol_logo_in_legend`). |
| `show_symbol_logo_in_legend` | On | Main-symbol logo in legend (needs `show_symbol_logos`). |
| `show_object_tree` | On | Object tree button. |
| `show_percent_option_for_right_margin` | Off | Percentage right margin option. |
| `show_spread_operators` | Off | Spread operators in Symbol Search. |
| `show_zoom_and_move_buttons_on_touch` | Off | Touch zoom/move buttons (appear when time scale pressed). |
| `snapshot_trading_drawings` | Off | Orders/positions/executions in screenshots. |
| `source_selection_markers` | On | Selection markers on series and indicators. |
| `studies_symbol_search_spread_operators` | Off | Spread operators for indicator symbol inputs (needs `show_spread_operators`). |
| `symbol_info` | On | Symbol Info legend option. |
| `symbol_info_long_description` | Off | Long descriptions in legends if in symbol info. |
| `symbol_info_price_source` | Off | Price source in legends (needs `price_source_id`/`price_sources`). |
| `timeframes_toolbar` | On | Bottom time-frame toolbar. |
| `timezone_menu` | On | Time-zone dropdown. |
| `use_na_string_for_not_available_values` | Off | Show "N/A" instead of the empty-set glyph. |
| `use_symbol_name_for_header_toolbar` | Off | Use `name` rather than ticker in Symbol Search/header button. |
| `always_show_study_symbol_input_values_in_legend` | Off | Keep symbol-type indicator inputs in legend. |

**Recommended for a trading dashboard (SOL 5m, Advanced Charts)**

- Turn off: `header_symbol_search`, `header_compare`, `symbol_search_hot_key`, `header_screenshot` (needs a snapshot server), `header_fullscreen_button`, `header_saveload` (if you auto-save), `display_market_status` (24/7 crypto), `popup_hints`, `go_to_date`, `symbol_info`, `show_object_tree`, `border_around_the_chart`, `volume_force_overlay` (volume in its own pane, as the tutorial does, ctx L61100-61115), `use_localstorage_for_settings` + `save_chart_properties_to_local_storage` (route state through `settings_adapter` instead), `items_favoriting` (optional).
- Turn on: `saveload_separate_drawings_storage` (SOL levels follow the symbol across layouts; needs adapter methods), `lock_visible_time_range_on_resize` (dashboard panels resize), `determine_first_data_request_size_using_visible_range` (fewer startup requests), `use_na_string_for_not_available_values`, `custom_resolutions` only if you build non-native bars, `pre_post_market_sessions` stays off.
- Keep: `countdown` (set `mainSeriesProperties.showCountdown: true`, needs `getServerTime` on the datafeed; ctx L46655), `left_toolbar`, `header_resolutions`, `header_chart_type`, `header_indicators`, `timeframes_toolbar`, `control_bar`, `context_menus`, `property_pages`, `legend_widget`, `create_volume_indicator_by_default`, `shift_visible_range_on_new_bar`.
- CSP / MV3 candidates (section 8): `iframe_loading_same_origin`, `iframe_loading_compatibility_mode`.

---

### 5. Overrides, themes and CSS

**Syntax** (ctx L46299-46345). Dotted-path keys in `overrides`; apply at runtime with `widget.applyOverrides({...})` (all charts) or `widget.chart(i).applyOverrides({...})`. Keys are typed in `ChartPropertiesOverrides` (chart/pane/scales/series, d.ts L3195+) and `DrawingOverrides`. Drawing keys are `linetool<name>.<prop>`, e.g. `"linetoolhorzline.linecolor"`, `"linetoolhorzline.linestyle": 2`. Indicators use `studies_overrides` / `applyStudiesOverrides`, keys like `"bollinger bands.median.color"`, `"volume.volume.transparency"`, `"volume.show ma"`. Line style enum: 0 solid, 1 dotted, 2 dashed. `ChartStyle` enum: Bar 0, Candle 1, Line 2, Area 3, Renko 4, Kagi 5, PnF 6, LineBreak 7, HeikinAshi 8, HollowCandle 9, Baseline 10, HiLo 12, Column 13, LineWithMarkers 14, Stepline 15, HLCArea 16, VolCandle 19, SVP 20, HLCBars 21 (d.ts L285).

**Precedence (ctx L45912-46156, 1 = wins).**

| # | Mechanism | Note |
|---|---|---|
| 1 | `widget.applyOverrides` / `IChartWidgetApi.applyOverrides` | Runtime. |
| 2 | `widget.load(state)` | Layout content loaded at init/after. |
| 3 | `saved_data` | Layout passed to constructor. |
| 4 | `settings_overrides` | Replaces values read from settings storage. |
| 5 | `settings_adapter` | Your user-settings storage. |
| 6 | `localStorage` | On unless `use_localstorage_for_settings` is disabled. |
| 7 | `overrides` (constructor) | Defaults only; loses to user settings and saved layouts. |
| 8 | `custom_themes` | Palette; lowest. |

Consequences (ctx L45846-45911): a colour set in `overrides` can be silently replaced by a saved layout or stored user setting; theme is persisted in the layout, so after restoring a layout call `await widget.changeTheme('dark')` then re-apply colour overrides. Internal CSS classes/DOM are not stable API. Limits: toolbar icons cannot be customised, custom UI cannot be injected (build it outside the iframe), loading spinner cannot be disabled.

**Chart overrides: key properties (ctx L46346-46756).**

| Area | Keys |
|---|---|
| Pane background | `paneProperties.backgroundType` (`"solid"`/`"gradient"`; default solid, but the dark theme default is gradient), `paneProperties.background`, `paneProperties.backgroundGradientStartColor`, `paneProperties.backgroundGradientEndColor`. Light default `#ffffff` (d.ts). |
| Grid | `paneProperties.vertGridProperties.{color,style,visible}`, `paneProperties.horzGridProperties.{color,style,visible}` (dotted by default; style 0 = solid). |
| Separator / margins | `paneProperties.separatorColor`, `paneProperties.topMargin`, `paneProperties.bottomMargin` (% auto-scale margins). |
| Crosshair | `paneProperties.crossHairProperties.{color,style,width,transparency}` (transparency needs a hex colour). |
| Legend | `paneProperties.legendProperties.{showLastDayChange,showStudyArguments,showStudyTitles,showStudyValues,showSeriesTitle,showSeriesOHLC,showBarChange,showSeriesLegendCloseOnMobile,showVolume,showBackground,backgroundTransparency}`; `mainSeriesProperties.statusViewStyle.{showExchange,showInterval,symbolTextSource}`. |
| Scales | `scalesProperties.{lineColor,textColor,fontSize,axisHighlightColor,axisHoverHighlightColor}`, `priceScaleSelectionStrategyName` (`"left"\|"right"\|"auto"`; runtime: `getSeries().changePriceScale('new-left')`). |
| Scale labels | `scalesProperties.{showSeriesLastValue,showStudyLastValue,showSymbolLabels,showStudyPlotLabels,showBidAskLabels,showPrePostMarketPriceLabel,showPriceScaleCrosshairLabel,showTimeScaleCrosshairLabel,crosshairLabelBgColorLight,crosshairLabelBgColorDark,axisLineToolLabelBackgroundColorActive,axisLineToolLabelBackgroundColorCommon,seriesLastValueMode}`, `mainSeriesProperties.highLowAvgPrice.{highLowPriceLabelsVisible,averageClosePriceLabelVisible}`. |
| Scale mode | `mainSeriesProperties.priceAxisProperties.{percentage,indexedTo100,log,isInverted,alignLabels}`. Cannot be applied via `applyOverrides`; use `getPanes()[0].getRightPriceScales()[0].setMode(1)` (1 = log). |
| Series style | `mainSeriesProperties.style` (ChartStyle), plus per-style groups: `lineStyle`, `baselineStyle`, `steplineStyle`, `barStyle`, `candleStyle`, `volCandlesStyle`, `areaStyle`, `hlcAreaStyle`, `hlcBarsStyle`, `lineWithMarkersStyle`, `hollowCandleStyle`, `haStyle`, `columnStyle`, `hiloStyle`, `renkoStyle`, `pbStyle`, `kagiStyle`, `pnfStyle`, `svpStyle`. Runtime: `getSeries().setChartStyleProperties(1, {upColor, downColor, borderUpColor, borderDownColor})`. |
| Candle colours | `mainSeriesProperties.candleStyle.{upColor,downColor,drawWick,drawBorder,drawBody,borderColor,borderUpColor,borderDownColor,wickColor,wickUpColor,wickDownColor,barColorsOnPrevClose}`. Light defaults: up `#089981`, down `#F23645` (d.ts). |
| Lines / misc | `mainSeriesProperties.{visible,showPriceLine,priceLineWidth,priceLineColor,showCountdown,sessionId,showPrevClosePriceLine,minTick}`, `mainSeriesProperties.bidAsk.*`, `mainSeriesProperties.highLowAvgPrice.*`, `mainSeriesProperties.prevClosePrice.*`. `minTick`: `"default"` or `"priceScale,minMove,frac"`, e.g. `"10000,1,false"` (4 decimals). |
| Sessions | `backgrounds.{preMarket,postMarket}.{color,transparency,visible}`, `vertlines.sessBreaks.{color,style,width,visible}` (only symbols with subsessions). |
| Time zone | `timezone` via `applyOverrides({timezone:'Europe/Belgrade'})`. |
| Trading | `tradingProperties.*` (Trading Platform). |

**Drawing overrides (ctx L46157-46298).** Defaults: constructor `overrides: {"linetoolhorzline.linecolor": "rgba(48,164,22,0.8)", "linetoolhorzline.linestyle": 2}`; future drawings: `applyOverrides`; one drawing: `createShape(point, {shape:'horizontal_line', overrides:{linecolor:'#FF0000'}})`; existing drawing: `getShapeById(id).setProperties({...})`. Icons/stickers/emoji ignore `overrides`/`applyOverrides` and must be styled at creation (`shape:'icon'` with `icon: 0xf004, color, size`; `shape:'sticker'` with `sticker:'dislike'`; `shape:'emoji'` with the emoji character). Full list: `DrawingOverrides` in typings.

**Themes (ctx L47633-47662).** `theme: 'light'|'dark'` (default light); no built-in theme switch button; `widget.changeTheme('dark')` returns a promise; `widget.getTheme()`. A dark layout restored under a light theme keeps a dark background, so re-run `changeTheme`.

**Custom themes API (ctx L47467-47622).** `custom_themes: {light: CustomThemeColors, dark: CustomThemeColors}`. Each of `color1..color7` (blue, grey, red, green, orange, purple, yellow by default) is an array of 19 shades, lightest to darkest; plus `white` and `black` strings. Missing entries keep defaults. Runtime: `(await widget.customThemes()).applyCustomThemes(obj)` / `.resetCustomThemes()`. Only light and dark exist; cannot add a third theme. Not themable: Account Manager blue/red, Market Status green/orange/blue, Details green. Disabled with `library_custom_color_themes` (error: "The library_custom_color_themes feature must be enabled to use the Custom themes API"). Overrides sit above palette colours.

**CSS variables (legacy, ctx L47322-47466).** Load via `custom_css_url`; selectors `:root:not(.theme-dark)` (light) and `.theme-dark:root` (dark). Runtime: `setCSSCustomProperty`, `getCSSCustomPropertyValue`.

| Variable | Controls |
|---|---|
| `--tv-color-platform-background` | Page background behind all elements. |
| `--tv-color-pane-background` | Toolbar background. |
| `--tv-color-toolbar-button-background-hover` / `-expanded` / `-active` / `-active-hover` | Toolbar button states. |
| `--tv-color-toolbar-button-text` / `-hover` / `-active` / `-active-hover` | Toolbar button text/icon. |
| `--tv-color-item-active-text` | Toggle buttons (magnet, lock). |
| `--tv-color-toolbar-toggle-button-background-active` / `-active-hover` | Toggle fill. |
| `--tv-color-toolbar-divider-background` | Dividers. |
| `--tv-color-toolbar-save-layout-loader` | Save-layout loader. |
| `--tv-color-bar-mark-background-color` | Bar-mark tooltip background. |
| `--tv-color-popup-background` | Popup/context menu background. |
| `--tv-color-popup-element-text` / `-text-hover` / `-text-active` | Popup item text. |
| `--tv-color-popup-element-background-hover` / `-background-active` | Popup item background. |
| `--tv-color-popup-element-divider-background` | Popup dividers. |
| `--tv-color-popup-element-secondary-text` / `-hint-text` | Secondary/hint text. |
| `--tv-color-popup-element-toolbox-text` / `-text-hover` / `-text-active-hover` | Toolbox icon text. |
| `--tv-color-popup-element-toolbox-background-hover` / `-background-active-hover` | Toolbox icon background. |

---

### 6. Save / load

Approach matrix (ctx L51632-51818):

| Approach | Chart layout | Chart template | Drawing template | Indicator template | Notes |
|---|---|---|---|---|---|
| REST API (`charts_storage_url`) | yes | no | yes | yes | You host the endpoints. |
| API handlers (`save_load_adapter`) | yes | yes | yes | yes | Recommended; you control auth, errors. Chart/drawing templates are Trading Platform features. |
| Low-level (`widget.save()`/`load()`) | yes | no | no | yes (`createStudyTemplate`/`applyStudyTemplate`) | Your own UI; hide built-ins with `header_saveload`. |

Layout = drawings + indicators + chart settings (colours, styles); the visible time range is NOT stored. Indicator templates store all settings except precision. Auto-save recipe: set `auto_save_delay`, subscribe `onAutoSaveNeeded`, call `saveChartToServer()`. Restore last layout: low-level -> `saved_data`; high-level -> `load_last_chart: true` and drop `symbol`.

**6a. `IExternalSaveLoadAdapter` (d.ts L13552; ctx L50642-50767).** All methods return Promises.

| Method | Signature | Purpose |
|---|---|---|
| `getAllCharts` | `() => Promise<ChartMetaInfo[]>` (`{id,name,symbol,resolution,timestamp}`) | List layouts. |
| `saveChart` | `(chartData: ChartData) => Promise<string\|number>` (`{id?,name,symbol,resolution,content,timestamp}`) | Create/overwrite; return the id. |
| `getChartContent` | `(chartId) => Promise<string>` | Return stored `content`. |
| `removeChart` | `(id) => Promise<void>` | Delete. |
| `getAllStudyTemplates` | `() => Promise<{name}[]>` | List indicator templates. |
| `saveStudyTemplate` | `({name,content}) => Promise<void>` | Save one. |
| `getStudyTemplateContent` | `({name}) => Promise<string>` | Load one. |
| `removeStudyTemplate` | `({name}) => Promise<void>` | Delete. |
| `getDrawingTemplates` | `(toolName) => Promise<string[]>` | Template names for a tool. |
| `loadDrawingTemplate` | `(toolName, templateName) => Promise<string>` | Load. |
| `saveDrawingTemplate` | `(toolName, templateName, content) => Promise<void>` | Save. |
| `removeDrawingTemplate` | `(toolName, templateName) => Promise<void>` | Delete. |
| `getAllChartTemplates` | `() => Promise<string[]>` | Trading Platform chart templates (needs `chart_template_storage`). |
| `getChartTemplateContent` | `(name) => Promise<ChartTemplate>` | Load. |
| `saveChartTemplate` | `(newName, theme) => Promise<void>` | Save. |
| `removeChartTemplate` | `(name) => Promise<void>` | Delete. |
| `saveLineToolsAndGroups` | `(layoutId \| undefined, chartId, state: LineToolsAndGroupsState, context?: SaveLineToolsContext) => Promise<void>` | Separate drawings (6e). |
| `loadLineToolsAndGroups` | `(layoutId \| undefined, chartId, requestType, requestContext) => Promise<Partial<LineToolsAndGroupsState> \| null>` | Separate drawings (6e). |

Count: 18 methods. Docs ship CodePen examples for localStorage and in-memory adapters (ctx L50700-50725).

**6b. REST API (ctx L50768-51225).** Base `charts_storage_url/charts_storage_api_version/<resource>?client=<client_id>&user=<user_id>`; all JSON; responses carry `status: "ok"|"error"`. Implement save/load/delete/list. Reference server (Django + PostgreSQL, no auth, no separate-drawings endpoints): `github.com/tradingview/saveload_backend`.

| Resource | Method + extra query | Body | Response `data` |
|---|---|---|---|
| `charts` list | GET | - | entries with `{timestamp,symbol,resolution,id,name}` (docs call it a data object) |
| `charts` save | POST | `{name, content, symbol, resolution}` | `{status, id}` |
| `charts` save-as | POST `&chart=<id>` | same | `{status}` |
| `charts` load | GET `&chart=<id>` | - | `{content,timestamp,id,name}` |
| `charts` delete | DELETE `&chart=<id>` | - | `{status}` |
| `study_templates` list | GET | - | `[{name}]` |
| `study_templates` save | POST | `{name, content}` | `{status}` |
| `study_templates` load | GET `&template=<name>` (docs also show `&chart=`) | - | `{name, content}` |
| `study_templates` delete | DELETE `&template=<name>` | - | `{status}` |
| `drawings` save | POST `&chart=<id>&layout=<layoutId>` | `{state: LineToolsAndGroupsState}` | `{status}` |
| `drawings` load | GET `&chart=<id>&layout=<layoutId>&symbol=<symbol>` | - | `{data:{state}}` |
| `drawing_templates` list | GET `&tool=<toolName>` | - | `[{name}]` (Trading Platform) |
| `drawing_templates` save | POST `&tool=&name=` | `{content}` | `{status}` |
| `drawing_templates` load | GET `&chart=&tool=&name=` | - | `{content}` |
| `drawing_templates` delete | DELETE `&chart=&tool=&name=` | - | `{status}` |

Access model: `client_id` = user group (your site URL); `user_id` unique per user for private storage, same value for all for shared storage, or one shared id for anonymous users. Demo storage is wiped regularly and cross-origin only for `localhost`/`tradingview.com`.

**6c. Low-level API (ctx L50574-50641).** `widget.save().then(layout => store(layout))`, `widget.load(stored)`; `widget.activeChart().createStudyTemplate({saveSymbol:true, saveInterval:true})` and `.applyStudyTemplate(tpl)`. Output is JSON you store yourself. No chart templates.

**6d. User settings (`ISettingsAdapter`, ctx L51819-51917; d.ts L14876).** Settings kept independent of layouts: resolution, chart style, Order Ticket type/quantity, Settings -> Trading items, Account Manager summary row, right/bottom widget-bar views, watchlist.

| Member | Required | Purpose |
|---|---|---|
| `initialSettings?: InitialSettingsMap` | no | Key -> string value map applied at start (e.g. `symbolWatermark` JSON string). |
| `setValue(key: string, value: string): void` | yes | Persist a setting; required even if you never change settings. |
| `removeValue(key: string): void` | yes | Delete a setting. |

Default store is `localStorage`; disable with `use_localstorage_for_settings`. `settings_adapter` sits above `localStorage` in precedence, `settings_overrides` above the adapter.

**6e. Saving drawings separately (ctx L51226-51631).** Enable `saveload_separate_drawings_storage` and implement the matching hooks. Benefits: per-symbol drawings visible in any layout; smaller layout objects.

| Path | What to implement |
|---|---|
| Adapter | `saveLineToolsAndGroups` and `loadLineToolsAndGroups` on `IExternalSaveLoadAdapter`. |
| REST | `drawings` POST and GET endpoints (6b). |
| Low-level | `activeChart().getLineToolsState()`, `activeChart().applyLineToolsState(state)`, `activeChart().reloadLineToolsFromServer()`; call `widget.save(cb, {includeDrawings:false})` for the layout part. |
| Migration | Store a "migrated" flag per layout; on `chart_load_requested`, call `saveChartToServer()` to re-save in the new mode. Old combined layouts still load. |

Save context (`SaveLineToolsContext`): `sharingMode` (`NotShared` | `SharedInLayout` | `GloballyShared`), `requestId`, `symbol?`. A single user action may trigger several save calls; route each by `sharingMode` (global drawings go to a global bucket keyed by symbol).
Load context: `requestType` is `allLineTools` | `mainSeriesLineTools` (drawing `symbol` = request symbol and `ownerSource` = `seriesSourceId`) | `lineToolsWithoutSymbol` | `studiesLineTools` (`ownerSource` != `seriesSourceId`); `requestContext = {symbol, seriesSourceId, sharingMode?}`. Filter strictly or drawings from indicator panes get re-parented to the main pane.
`LineToolsAndGroupsState = {sources: Map<uuid, LineToolState|null>, groups: Map<uuid, uuid[]|null>}`; `null` is a tombstone = delete. Treat `LineToolState`/`LineToolsGroupState` as opaque.

---

### 7. Toolbar button, snapshots, debug, hosting, shortcuts, accessibility

**Custom top-toolbar button (ctx L56358-56501).** Always inside `widget.headerReady().then(...)`.
- Button: `const b = widget.createButton(); b.textContent = 'Show dialog'; b.addEventListener('click', ...)`; `widget.showConfirmDialog({title, body}).then(ok => ...)`.
- Dropdown: `widget.createDropdown({title:'Select symbol', tooltip:'...', items:[{title:'MSFT', onSelect:()=>widget.activeChart().setSymbol('MSFT')}]})`.
- Remove with `removeButton`. Toolbar icons and arbitrary UI injection are unsupported (ctx L46042-46075).

**Snapshots (ctx L58125-58388).** Built-in Copy link / Open in new tab / Tweet image POST a `multipart/form-data` PNG (field `preparedImage`) to `snapshot_url` and expect the public URL as the response body (docs show an Express + multer + cors server with `image/*` filter). `widget.takeClientScreenshot()` avoids a server and returns a canvas; hide the server-backed button with `header_screenshot` if no `snapshot_url` is set.

**Debug mode (ctx L58389-58521).** `debug: true` in the constructor or `widget.setDebugMode(true)` after ready (also `charting_library_debug_mode`); logs symbol resolve, requested vs received bar ranges (`FEED [SYMBOL|RES]: Requesting data ...`). Trading Platform: `debug_broker` = `all | broker-only | host-only | normal`.

**Cross-origin hosting (ctx L36133-36196).** Default expects library files same-origin as the page. For a different origin: load `charting_library.standalone.js` from that origin, set `library_path` to an absolute `http(s)://.../` ending in `/`, and serve CORS (`Access-Control-Allow-Origin`) for the page origin; otherwise blank chart or console errors. Hosted CDN alternative exists (`charting-library.tradingview-widget.com`, pinned via `/versions/<x.y.z>/`, ctx L56185-56225) - not usable under MV3 (remote code). Library file layout (ctx L48125-48140): `charting_library/{bundles/, charting_library.js (UMD), .cjs.js, .esm.js, .standalone.js (IIFE), .d.ts}`, `datafeeds/udf/`; `bundles/` is internal and changes without notice; all files except `charting_library.js` have content hashes in their names, so set a short cache expiry on `charting_library.js` only (ctx L50336-50345).

**CSP symptoms (ctx L56105-56120).** Errors such as `Refused to load the image ... "img-src 'self' blob data"` mean the page CSP blocks `blob:`/`data:` assets the library uses (screenshots, logos, emoji/icons). Fix the CSP or enable `iframe_loading_compatibility_mode`.

**Keyboard shortcuts (ctx L36265-36619).** Built-ins (Win/Linux; macOS swaps Ctrl->Cmd, Alt->Option): Ctrl+K quick search, `/` indicators, `.` load layout, Ctrl+S save layout, Ctrl+Z / Ctrl+Y undo/redo, type a symbol to search, digit or `,` for interval, arrows pan one bar, Ctrl+arrows zoom/pan further, Alt+G go to date, Alt+S snapshot link, Alt+R reset, Alt+I invert, Alt+L log, Alt+P percent, Alt+Z start keyboard navigation (Tab with `accessible_keyboard_shortcuts`), drawing hotkeys Alt+T/H/V/C/F/Shift+R, Ctrl+C/V copy-paste drawings, Ctrl+Alt+H hide drawings. Trading-only: Shift+B/S market orders, Alt+W watchlist. Custom: `widget.onShortcut(112, cb)` (F1), `widget.onShortcut(["alt", 81], cb)`, `["ctrl","shift",220]`; modifiers are lowercase strings, other keys are numeric `keyCode`s; printable strings like `"alt+q"` throw (removed after v30). Disable individual ones via featuresets (`insert_indicator_dialog_shortcut`, `save_shortcut`, `symbol_search_hot_key`, `show_interval_dialog_on_key_press`) or all via `setShortcutsEnabled(false)`.

**Accessibility (ctx L37329-37400).** Keyboard navigation of toolbars (Alt+Z), WCAG 2.2 AA colours, screen readers (VoiceOver, Narrator, JAWS, NVDA); extra descriptions via `aria_crosshair_price_description`, `aria_detailed_chart_descriptions` (English only).

**Set-up tutorial (ctx L60963-61179).** The runtime is kept out of source control under `vendor/tradingview/advanced_charts/`; `index.html` has a `<div id="tv_chart_container">` and `<script type="module" src="src/main.js">`; `main.js` does `import { widget as createWidget } from '/vendor/tradingview/advanced_charts/charting_library.esm.js'` then `new createWidget(options)` on `DOMContentLoaded`. Tutorial flags: enabled `custom_resolutions`, `allow_arbitrary_symbol_search_input`, `display_data_mode`, `use_symbol_name_for_header_toolbar`, `chart_drag_export`; disabled `use_localstorage_for_settings`, `save_chart_properties_to_local_storage`, `volume_force_overlay`.

---

### Use in solmargintrader

Context: zero-dependency ESM MV3 extension (`extension/manifest.json`, CSP `script-src 'self'; object-src 'self'; base-uri 'none'`, options page `src/ui/dashboard.html`), no build step, no remote code, plus the read-only macOS TUI (soltui, no browser so the widget does not apply there). The library is not zero-dependency and ships ~MBs of bundles; it must be copied locally and loaded through `library_path`. Everything below that depends on how the library behaves under the MV3 CSP is unverified: test it on the dashboard page first.

**Layout.** Copy the licensed package into `extension/vendor/tradingview/charting_library/` (gitignored, see licensing). Datafeed code is yours and lives in `extension/src/market/` (a new `tvDatafeed.js` implementing `onReady`, `searchSymbols`, `resolveSymbol`, `getBars`, `subscribeBars`, `unsubscribeBars`, and `getServerTime` for the countdown). Symbol info for SOL: `name/ticker/description 'SOL/USD'`, `type 'crypto'`, `session '24x7'`, `timezone 'Etc/UTC'`, `exchange/listed_exchange` your venue, `format 'price'`, `minmov 1`, `pricescale 100` (or 10000), `has_intraday true`, `supported_resolutions ['1','5','15','60','240','1D']`, `volume_precision 2`, `data_status 'streaming'` (field names from `LibrarySymbolInfo`, d.ts).

**Minimal widget config (dashboard page, ES module).**

```js
// extension/src/ui/view-chart.js   (module script loaded by dashboard.html; no inline script)
import { widget as TvWidget } from '../../vendor/tradingview/charting_library/charting_library.esm.js';
import { createTvDatafeed } from '../market/tvDatafeed.js';
import { createChartSaveLoadAdapter, createChartSettingsAdapter } from '../storage/tvAdapters.js';

export function mountSolChart(containerId = 'tv_chart_container') {
  const tv = new TvWidget({
    container: containerId,
    library_path: '../../vendor/tradingview/charting_library/', // relative to dashboard.html; or chrome.runtime.getURL(...) - test which resolves
    locale: 'en',
    datafeed: createTvDatafeed({ symbol: 'SOL/USD' }),
    symbol: 'SOL/USD',
    interval: '5',
    timezone: 'Etc/UTC',
    theme: 'dark',
    autosize: true,
    custom_font_family: 'ui-monospace, Menlo, monospace',
    debug: false,
    workers: { enabled: false },            // avoid blob workers until verified under CSP
    time_frames: [
      { text: '1d', resolution: '5',  description: '1 day, 5m',  title: '1D' },
      { text: '5d', resolution: '15', description: '5 days, 15m', title: '5D' },
    ],
    disabled_features: [
      'use_localstorage_for_settings', 'save_chart_properties_to_local_storage',
      'header_symbol_search', 'header_compare', 'symbol_search_hot_key',
      'header_screenshot', 'header_fullscreen_button', 'header_saveload',
      'display_market_status', 'popup_hints', 'go_to_date', 'symbol_info',
      'show_object_tree', 'border_around_the_chart', 'volume_force_overlay',
    ],
    enabled_features: [
      'saveload_separate_drawings_storage', 'lock_visible_time_range_on_resize',
      'determine_first_data_request_size_using_visible_range',
      'use_na_string_for_not_available_values',
      // CSP fallbacks - enable only if the default blob: iframe is blocked:
      // 'iframe_loading_same_origin',   // needs vendor/.../sameorigin.html
      // 'iframe_loading_compatibility_mode',
    ],
    overrides: {
      'paneProperties.backgroundType': 'solid',     // dark theme defaults to gradient
      'paneProperties.background': '#0b0e14',
      'paneProperties.vertGridProperties.color': 'rgba(255,255,255,0.04)',
      'paneProperties.horzGridProperties.color': 'rgba(255,255,255,0.04)',
      'scalesProperties.textColor': '#9aa4b2',
      'scalesProperties.lineColor': '#1f2530',
      'mainSeriesProperties.style': 1,              // candles
      'mainSeriesProperties.candleStyle.upColor': '#26a69a',
      'mainSeriesProperties.candleStyle.downColor': '#ef5350',
      'mainSeriesProperties.candleStyle.borderUpColor': '#26a69a',
      'mainSeriesProperties.candleStyle.borderDownColor': '#ef5350',
      'mainSeriesProperties.candleStyle.wickUpColor': '#26a69a',
      'mainSeriesProperties.candleStyle.wickDownColor': '#ef5350',
      'mainSeriesProperties.showCountdown': true,
      'paneProperties.legendProperties.showSeriesTitle': false,
    },
    studies_overrides: { 'volume.volume.transparency': 60, 'volume.show ma': false },
    save_load_adapter: createChartSaveLoadAdapter(chrome.storage.local),
    settings_adapter: createChartSettingsAdapter(chrome.storage.local),
    auto_save_delay: 5,
    load_last_chart: true,   // requires the adapter's getAllCharts/getChartContent; omit `symbol` if you want the saved symbol to win
  });

  tv.chartReady().then(async () => {
    await tv.changeTheme('dark');                    // re-assert theme after any restored layout
    tv.applyOverrides({ 'paneProperties.background': '#0b0e14', 'paneProperties.backgroundType': 'solid' });
    tv.subscribe('onAutoSaveNeeded', () => tv.saveChartToServer());
    tv.activeChart().onIntervalChanged().subscribe(null, (res) => {/* keep dashboard state in sync */});
    // grid levels / entries from core/grid.js: tv.activeChart().createOrderLine() / createShape({price}, {shape:'horizontal_line', ...})
  });
  return tv;
}
```

Notes on the snippet: with `load_last_chart: true` the constructor `symbol` wins over the saved layout's symbol (d.ts); `library_path` must end with `/`; overrides are the lowest-but-one tier, so the `chartReady` re-assert is deliberate (precedence table).

**`save_load_adapter` backed by `chrome.storage.local`** (new `extension/src/storage/tvAdapters.js`, no dependencies). Keep layouts under one key prefix, e.g. `tv:charts` (array of meta) and `tv:chart:<id>` (content), `tv:study_templates`, `tv:drawings:<layout|global>:<chartId>`, `tv:settings`:

```js
const K = { index: 'tv:charts', chart: id => `tv:chart:${id}`, tpl: 'tv:study_templates', draw: k => `tv:drawings:${k}` };
export function createChartSaveLoadAdapter(area) {
  const get = async k => (await area.get(k))[k];
  const set = (k, v) => area.set({ [k]: v });
  return {
    async getAllCharts() { return (await get(K.index)) ?? []; },                       // ChartMetaInfo[]
    async saveChart(d) {                                                               // ChartData -> id
      const id = d.id ?? crypto.randomUUID();
      const idx = ((await get(K.index)) ?? []).filter(c => String(c.id) !== String(id));
      idx.push({ id, name: d.name, symbol: d.symbol, resolution: d.resolution, timestamp: Math.floor(Date.now() / 1000) });
      await set(K.index, idx); await set(K.chart(id), d.content); return id;
    },
    async getChartContent(id) { return get(K.chart(id)); },                            // string
    async removeChart(id) { await area.remove(K.chart(id)); await set(K.index, ((await get(K.index)) ?? []).filter(c => String(c.id) !== String(id))); },
    async getAllStudyTemplates() { return ((await get(K.tpl)) ?? []).map(({ name }) => ({ name })); },
    async saveStudyTemplate(t) { const l = ((await get(K.tpl)) ?? []).filter(x => x.name !== t.name); l.push(t); await set(K.tpl, l); },
    async getStudyTemplateContent(t) { return ((await get(K.tpl)) ?? []).find(x => x.name === t.name)?.content; },
    async removeStudyTemplate(t) { await set(K.tpl, ((await get(K.tpl)) ?? []).filter(x => x.name !== t.name)); },
    // required by the interface; drawing/chart templates unused in Advanced Charts
    async getDrawingTemplates() { return []; }, async loadDrawingTemplate() { return ''; },
    async removeDrawingTemplate() {}, async saveDrawingTemplate() {},
    async getAllChartTemplates() { return []; }, async getChartTemplateContent() { return undefined; },
    async saveChartTemplate() {}, async removeChartTemplate() {},
    // separate drawings: null values are tombstones; Maps do not serialise -> store [id, state] entries
    async saveLineToolsAndGroups(layoutId, chartId, state, ctx) { /* bucket = ctx?.sharingMode === 'GloballyShared' ? 'global' : `${layoutId}/${chartId}`; merge state.sources / state.groups, delete on null */ },
    async loadLineToolsAndGroups(layoutId, chartId, requestType, requestContext) { /* filter by requestType using ownerSource vs requestContext.seriesSourceId; return {sources: Map, groups: Map} or null */ },
  };
}
export function createChartSettingsAdapter(area) {
  return {
    initialSettings: {},                       // hydrate from `await area.get('tv:settings')` before constructing the widget
    setValue: (k, v) => { area.get('tv:settings').then(r => area.set({ 'tv:settings': { ...(r['tv:settings'] ?? {}), [k]: v } })); },
    removeValue: k => { area.get('tv:settings').then(r => { const s = { ...(r['tv:settings'] ?? {}) }; delete s[k]; return area.set({ 'tv:settings': s }); }); },
  };
}
```

Caveats: `initialSettings` is read at construction, so `await` the stored map before `new TvWidget`. `chrome.storage.local` is capped at about 10 MB unless the manifest adds `unlimitedStorage`; the repo's `store.js` already keeps time series in IndexedDB and config in `chrome.storage.local` (comment at `extension/src/storage/store.js:5`), so keep chart layouts (small JSON) in `chrome.storage.local` and never put bars there. Adapter code runs in the dashboard page that constructs the widget, where `chrome.storage` is available.

**MV3 / CSP concerns (checklist).**

1. No remote code: do not use `charting-library.tradingview-widget.com`; ship the package inside the extension. The package contains hashed bundles under `bundles/`; keep the folder intact and unedited (ctx L48125-48150).
2. Current manifest CSP `script-src 'self'` allows module scripts from the extension; it forbids inline scripts and `eval`. Whether the library's iframe bootstrap needs inline script, `eval`, `new Function`, or `blob:` workers is NOT documented in the ctx; test by opening the dashboard with DevTools open and reading CSP violations.
3. By default the library builds its iframe from a `blob:` URL. If MV3 blocks it, try in order: `iframe_loading_same_origin` (serves `sameorigin.html` from `library_path`, real `chrome-extension://` URL, uses `document.write`, nonce via `window.__tvCspNonce` in that file), then `iframe_loading_compatibility_mode` (`about:blank` + `document.write`) (ctx L44475-44490). Both rely on `document.write` into a same-origin frame inheriting the page CSP; nonces are not valid in extension-page CSP, so inline `document.write` scripts may still be refused - in that case the fallback is a manifest `sandbox` page (relaxed CSP, no `chrome.*` access, talk to it via `postMessage`) hosting the widget. This fallback is general MV3 knowledge, not from the TradingView docs.
4. `base-uri 'none'` in the current CSP may break any `<base>` tag the library writes; relax to `'self'` only if a violation shows.
5. `img-src` must allow `blob:` and `data:` (screenshots, logos, emoji) - the extension-pages default does not restrict images, but do not add `img-src` that omits them (ctx L56105-56120).
6. `workers: {enabled: false}` until you confirm worker creation works under the CSP; custom indicators must stay pure if workers are on (d.ts).
7. `web_accessible_resources` is needed only if the chart is embedded in a web page via content script; for the extension dashboard page itself the iframe is same-origin with the extension, so it is not required (verify).
8. Network: the datafeed uses `fetch` inside the extension, so required hosts must be in `host_permissions` (the manifest already lists Jupiter/DefiLlama; add your OHLC source). The library itself should make no external calls with a local datafeed, but watch the Network panel for calls to `tradingview.com` hosts (telemetry/logo/snapshot endpoints) and block with CSP `connect-src` if any appear.
9. Size and load: library folder is several MB; lazy-load the module only when the chart view opens so the popup and service worker stay light. Service workers cannot host the widget (needs DOM); only the dashboard/options page can.
10. Build/test: repo has no build step, so keep `.esm.js` import paths static; node tests (`extension/test`) should import only the datafeed/adapters, never the vendor bundle. e2e (`extension/e2e`) can assert the container renders and `chartReady` resolves.

**Licensing / repo hygiene.**

- The Charting Library (Advanced Charts) is free but not open source: access is by licence agreement with TradingView (access-restricted GitHub package, ctx L60976-60995 "restricted"); the TradingView logo/attribution depends on your licence terms (ctx L46055-46060). The library files, the docs dump, and `charting_library.d.ts` are private/licensed and must not be committed or redistributed publicly.
- Finding: `tradingview/` is currently untracked and not in `.gitignore`, and the remote `mithudso/solmargintrader` is PUBLIC (gh repo view). Add `tradingview/` and `extension/vendor/tradingview/` to `.gitignore` before the next commit; ship builds of the extension only to yourself (a packaged .crx/.zip containing the library redistributes it).
- Keep the vendor copy out of CI artefacts; install it with a local script (the tutorial pattern is `npm run tv:install:ac -- <version>` from a private package, ctx L60985-60995) and record the pinned version in a non-secret file.
- Use `TradingView.version()` after load and compare with the docs build (31.2.0 in this snapshot).

**Open items to verify before building.** (a) blob/worker/inline-script behaviour under MV3 CSP (item 2-3); (b) `library_path` resolution for `chrome-extension://` pages (docs only specify absolute `http(s)` for cross-origin); (c) `volume.volume.color.0/.1` ordering for up/down volume colours (only `.0` appears in the typings example); (d) whether `load_last_chart` is reliable with a purely local adapter (docs describe REST/handlers).

## Trading Platform and Broker API

Sources: `ctx` = `tradingview/charting-library-context.txt`; `broker d.ts` = `tradingview/broker-api.d.ts` (2988 lines, dts-bundle-generator v9.5.1). Paraphrased; identifiers exact. "(docs)" = stated in the TradingView text; "(standard definition)" = textbook finance, not stated by TradingView; "(inferred)" = deduced from examples.

### 1. Licensing and product note

| Item | Fact | Source |
|---|---|---|
| Trading Platform (TP) | Standalone client-side product built on Advanced Charts; includes every Advanced Charts feature. Access is restricted (private repo `trading_platform`, request access). | ctx L55873-56037 |
| Migrating from Advanced Charts | Replace the `charting_library` folder with the one from the `trading_platform` repo. You then get extra chart types, multi-chart layout and an empty Account Manager. Watchlist, Details, Order Ticket, News and DOM additionally need the Datafeed quote methods plus featuresets or widget options. | ctx L55873-56037 |
| TP-only features | Broker API / chart trading (`broker_factory`, `broker_config`), Account Manager, Order Ticket, Buy/Sell buttons and bid/ask lines, Depth of Market, Watchlist, Details, News widgets, up to 8-chart synced layout, Renko / Point-and-Figure / Line Break / Kagi, Session Volume Profile, drawing templates, `build_seconds_from_ticks`. | ctx L55873-56037 |
| TP-only APIs | `trading_customization` (`brokerOrder`, `brokerPosition`, `order`, `position`), `tradingProperties.*` overrides, trading primitives `createOrderLine` / `createPositionLine` (TP-only since v29). | ctx L47155-47321 |
| Datafeed prerequisite | `getQuotes`, `subscribeQuotes`, `unsubscribeQuotes` must exist before the Broker API; without them: UI loading delays, missing data, `N/A` in the mobile legend. DOM additionally needs `subscribeDepth` / `unsubscribeDepth`. | ctx L55400-55441, L55873-56037, L53160-53271 |
| Not in TP | TradingView.com alerts are not included (tutorial builds a custom price-cross alert from chart primitives). | ctx L62162-62658 |
| Division of labour | The library keeps no trading state and has no login UI. Your backend does accounts, auth, order execution; the library displays what you push and calls your Broker API on user actions. | ctx L54292-54363, L59083-59606 |
| Three components | Broker API (`IBrokerTerminal`; library calls you), Trading Host (`IBrokerConnectionAdapterHost`; you call the library with unsolicited updates), Datafeed API (`IDatafeedQuotesApi`; quotes). | ctx L55442-55816 |
| Wiring | `broker_factory: (host) => new MyBroker(host, datafeed)`; flags in `broker_config: { configFlags, durations, customUI, tradedGroupConfig, customNotificationFields, orderRules }`. | ctx L55442-55816, L55817-55872; broker d.ts L2508-2559 |
| d.ts naming gap | The task text names `IBrokerWithoutRealtime`; this d.ts has no such interface. Equivalent surface = `IBrokerCommon` + `IBrokerAccountInfo` + `IBrokerTerminal` (`IBrokerTerminal extends IBrokerCommon, IBrokerAccountInfo`), with realtime via host `realtimeUpdate`. | broker d.ts L1129-1254, L1608 |

### 2. Core trading concepts

#### 2.1 Order types, sides, statuses (enums, numeric values exact)

| Enum | Members | Source |
|---|---|---|
| `OrderType` | `Limit=1`, `Market=2`, `Stop=3`, `StopLimit=4` | broker d.ts L130-135 |
| `Side` | `Buy=1`, `Sell=-1` | broker d.ts L145-148 |
| `OrderStatus` | `Canceled=1`, `Filled=2`, `Inactive=3`, `Placing=4`, `Rejected=5`, `Working=6` | broker d.ts L107-114 |
| `OrderStatusFilter` (History/Orders tabs) | `All=0` plus `Canceled=1`, `Filled=2`, `Inactive=3`, `Rejected=5`, `Working=6` (no `Placing`) | broker d.ts L115-122 |
| `ParentType` | `Order=1`, `Position=2`, `IndividualPosition=3` | broker d.ts L136-140 |
| `StopType` | `StopLoss=0`, `TrailingStop=1`, `GuaranteedStop=2` | broker d.ts L149-153 |
| `PriceType` | `Limit=1`, `Stop=2` | broker d.ts L141-144 |
| `ConnectionStatus` | `Connected=1`, `Connecting=2`, `Disconnected=3`, `Error=4` | broker d.ts L88-93 |
| `ConnectionType` | `Real=0`, `Demo=1` | broker d.ts L94-97 |
| `NotificationType` | `Error=0`, `Success=1` | broker d.ts L98-101 |
| `OrderOrPositionMessageType` | `"information"`, `"warning"`, `"error"` | broker d.ts L102-106 |
| `OrderTicketFocusControl` | `LimitPrice=1`, `StopPrice=2`, `TakeProfit=3`, `StopLoss=4`, `Quantity=5` | broker d.ts L123-129 |
| `DisconnectType` | `LogOut=0` `FailedRestoring=1` `Offline=2` `APIError=3` `TwoFactorRequired=4` `CancelAuthorization=5` `TimeOutForAuthorization=6` `OauthError=7` `BrokenConnection=8` `Reconnect=9` `FailedSignIn=10` | broker d.ts L27-39 |
| `DisconnectReason` | `SessionRestoreFailed=0` `ConnectionLost=1` `TokenExpired=2` `Inactivity=3` `UserLogOut=4` (analytics only) | broker d.ts L8-26 |
| `BottomWidgetBarMode` | `"minimized"`, `"normal"`, `"maximized"` | broker d.ts L75-79 |
| `CashTransactionType` | `"deposit"`, `"withdrawal"` | broker d.ts L80-83 |

Order types (docs): market = immediate, price not guaranteed; limit = price guaranteed, fill not; stop = becomes market at the trigger level; stop-limit = stop price plus limit price. Defaults: market, limit, stop on; stop-limit off. (ctx L54995-55019, L53750-53780). Market orders cannot be modified (ctx L59083-59606, broker d.ts L1633).

#### 2.2 Order status state machine

Documented rule: statuses split into transitional (`Placing`, `Working`, `Inactive`) and final (`Filled`, `Canceled`, `Rejected`); status moves only transitional to final, never back (ctx L55020-55057). Meanings (docs): `Placing` = broker registered the order, exchange has not confirmed; `Working` = approved by exchange, not executed; `Inactive` = in the system but not live, used for brackets.

| From | To | Trigger | Basis |
|---|---|---|---|
| (none) | `Working` | `placeOrder` then `orderUpdate` with `status: Working` within 10 s | docs, ctx L55593-55657 |
| (none) | `Inactive` | bracket child of a not-yet-filled parent order | docs, ctx L54437-54546 |
| (none) | `Working` | bracket added directly to an existing position | docs, ctx L54676-54782 |
| `Inactive` | `Working` | parent order becomes `Filled` (OSO, Order-Sends-Order); child's `parentId` / `parentType` re-pointed to the new position (`ParentType.Position`) | docs, ctx L54547-54655 |
| `Working` | `Filled` | execution; `executionUpdate` then `orderUpdate(Filled)` then `positionUpdate` | docs, ctx L55658-55719 |
| `Working` | `Canceled` | `cancelOrder` then `orderUpdate(Canceled)` | docs, ctx L59083-59606 |
| `Working` (bracket) | `Filled` | one bracket executes | docs, ctx L54783-54864 |
| sibling bracket | `Canceled` | OCO (One-Cancels-the-Other): the other bracket is cancelled; position `qty` goes to 0 via `positionUpdate` | docs, ctx L54783-54864 |
| `Working` / `Placing` | `Rejected` | exchange or broker refuses | docs (final status listed, no worked example), ctx L55020-55057 |
| `Placing` | `Working` or `Rejected` | exchange confirms or refuses | inferred from the status definitions |
| any final | any other | not allowed | docs rule |
| partial fill | none | no `PartiallyFilled` status exists; use `PlacedOrder.filledQty` / `avgPrice` while staying `Working` | inferred from broker d.ts L2375-2379 |

`Position` is created by a fill; positions have no status. Closing = `qty: 0` position update (see issues table).

#### 2.3 Time in force, durations

| Concept | Detail | Source |
|---|---|---|
| Enable | Provide `durations: OrderDurationMetaInfo[]` in `broker_config`; shows a "Time in force" menu (default for limit, stop, stop-limit; override per type with `supportedOrderTypes`). | ctx L53944-53988 |
| `OrderDurationMetaInfo` | `name` (title), `value` (id), `default?` (one only; also used by silent placement), `hasDatePicker?`, `hasTimePicker?`, `supportedOrderTypes?` (default `[Limit, Stop, StopLimit]`). | broker d.ts L2214-2231 |
| `OrderDuration` on orders | `{ type: string (= OrderDurationMetaInfo.value), datetime?: number }`. | broker d.ts L2202-2208 |
| Examples in docs | `DAY`, `GTC` (Good-Til-Canceled), `IOC`. | ctx L53944-53988, L61180-61408 |
| Per-symbol | `InstrumentInfo.allowedDurations`, `SymbolSpecificTradingOptions.allowedDurations`; modify an existing order's duration only if `supportModifyDuration`. | broker d.ts L2024, L2675-2680, L640-642 |
| Host | `setDurations(durations)` changes options at runtime. | broker d.ts L1338 |

#### 2.4 Brackets (take-profit / stop-loss), parent / child, trailing stop

| Rule | Detail | Source |
|---|---|---|
| Definition | Bracket orders protect a position: one stop-loss and one take-profit (limit) on the opposite side. Parent = the order or position bracketed. | ctx L54363-54436 |
| Link | Child carries `parentId` and `parentType`; child `qty` and `symbol` equal the parent's; child `side` is opposite. | ctx L54363-54436 |
| Child order shape | TP: `type: Limit`, `limitPrice = parent.takeProfit`. SL: `type: Stop`, `stopPrice = parent.stopLoss`. | ctx L54437-54546 |
| Place with brackets | `placeOrder(PreOrder)` where `PreOrder` has `takeProfit` / `stopLoss` (+ `limitPrice` for limit parents, `stopPrice` for stop parents). Backend then calls `orderUpdate` three times: parent (`Working`), TP child (`Inactive`), SL child (`Inactive`). Limit/stop parents must echo `limitPrice` / `stopPrice`. | ctx L54437-54546 |
| On parent fill | `orderUpdate` x3: parent `Filled`; each child `status: Working`, `parentId = position id`, `parentType = Position`. | ctx L54547-54655 |
| Position brackets | `editPositionBrackets(positionId, brackets, customFields?)` (or `editIndividualPositionBrackets`); backend must call `positionUpdate` (or `individualPositionUpdate`) within 10 s, plus `orderUpdate` for each new child (`Working`). | ctx L54656-54782 |
| Execution | A filled bracket cancels the other (OCO); position `qty` becomes 0. | ctx L54783-54864 |
| Cardinality | One SL + one TP per parent by default. `supportMultipleExitLevels` allows many; `supportUnpairedExitLevels` allows a level with only one leg; `maxExitLevelsCount` from `getOrderDialogOptions` caps levels. | ctx L54865-54955 |
| `exitLevels` | Array of `ExitLevel`, used only when more than one level exists; with one pair the root `takeProfit` / `stopLoss` fields are used (backward compatible). `BracketOrder.exitLevelId` ties a bracket to its level. | ctx L54865-54955 |
| Trailing stop | Fields `trailingStopPips`, `trailingStopPrice`, and `stopType = StopType.TrailingStop (1)` on `PlacedOrder` / `Position` / `IndividualPosition`; enabled by `supportTrailingStop`; editable by `supportModifyTrailingStop`. | broker d.ts L2357-2360, L485, L647 |
| Guaranteed stop | `guaranteedStop` price, `supportGuaranteedStop`. | broker d.ts L491 |
| Pair-only modes | `supportOnlyPairPositionBrackets`, `supportOnlyPairOrderBrackets` force SL+TP together. | broker d.ts L718-723 |
| Cancel semantics | `closePositionCancelsOrders`; `supportCancellingBothBracketsOnly` changes dialog text only, the library never cancels for you (implement `cancelOrder` / `cancelOrders`). | broker d.ts L713, L767 |
| Style overrides | `trading_customization.brokerOrder` / `brokerPosition` keys follow `{Side}.{State}.{Element}.{Property}` where Side in `buy`, `sell`, `takeProfit`, `stopLoss`; State in `normal`, `disabled`; Element in `close`, `qty`, `reverse`, `text`; Property in `activeColor`, `backgroundColor`, `borderBackgroundColor`, `borderColor`, `dividerColor`, `hintAreaColor`, `iconColor`, `lineColor`, `movingBackgroundColor`, `negativePlColor`, `pointBackgroundColor`, `pointShadowColor`, `positivePlColor`, `textColor`. Example: `widget.applyOverrides({"tradingProperties.bracketsPL.visibility": false})`. | ctx L47155-47321 |

#### 2.5 Positions: regular vs individual, netting vs hedging

| Concept | Detail | Source |
|---|---|---|
| Regular position | One aggregated position per symbol regardless of side; buys and sells raise or lower `qty`. Returned by `positions()`. Line drawn at `avgPrice`. | ctx L55058-55081, L55082-55104 |
| Individual position | Long and short tracked separately, one record per lot/trade (`IndividualPosition`: `id`, `date`, `price`, `qty`, `side`). Returned by `individualPositions()`. | ctx L55058-55081; broker d.ts L1927-1985 |
| Position netting | `supportPositionNetting: true` aggregates individual positions into one net position per symbol (example: long 100 plus short 50 = net long 50). Adds Account Manager pages "Individual Positions" and "Net Positions"; tab counter counts net positions only. Requires `positions` and `individualPositions`; updates via `positionUpdate` and `individualPositionUpdate`. Chart shows P&L for individual positions only. | ctx L55105-55137, L55291-55399 |
| Multiposition (hedging-like display) | `supportMultiposition: true` shows several positions for one symbol without aggregation; display-only, does not change calculation; same methods as regular positions. Disables default reversal (needs native) and the DOM "Flatten" button. | ctx L55138-55150; broker d.ts L569-577 |
| Brackets vs netting | If `supportPositionBrackets` is true, net positions take priority and individual lines are hidden on chart. To show individual lines use `supportPositionBrackets: false` and `supportIndividualPositionBrackets: true`. | ctx L54656-54675, L53109-53159 |
| FIFO closing | `requiresFIFOCloseIndividualPositions` enables closing individual positions in FIFO order. | broker d.ts L805-809 |
| Close | `supportClosePosition=false`: library sends an opposite-side market order via `placeOrder` with `PreOrder.isClose = true`. `true`: library calls `closePosition(positionId, amount?, confirmId?)`. Individual: `supportCloseIndividualPosition` + `closeIndividualPosition`. Partial close dialog: `supportPartialClosePosition` / `supportPartialCloseIndividualPosition`. | ctx L55165-55193; broker d.ts L525-537, L746-757 |
| Reverse (default) | Library calls `placeOrder` with `isClose: true`, opposite `side`, `qty = 2 x original qty` (long 100 becomes sell 200, ending short 100). Not usable with multiposition. | ctx L55194-55260 |
| Reverse (native) | `supportReversePosition` + `supportNativeReversePosition` then implement `reversePosition(positionId)`; must be followed by `positionUpdate`. | ctx L55233-55260; broker d.ts L589-602 |
| `Position.qty` | A positive number; `side` carries direction. Optional `longQty`, `shortQty`. | broker d.ts L2394-2410 |

#### 2.6 Executions

An `Execution` is a fill record: `id`, `symbol`, `price`, `qty`, `side`, `time` (ms), optional `commission`, `fee`, `netAmount`, `currencyRate`, `extra`. Loaded by `executions(symbol)` at start; new ones via host `executionUpdate`. Shown as chart marks when `supportExecutions` (default true). In a fill the documented order of host calls is `executionUpdate` then `orderUpdate(Filled)` then `positionUpdate` (ctx L55658-55719; broker d.ts L1026-1042, L794-799).

### 3. Broker API methods

Counts from grep of the d.ts: `IBrokerCommon` 16 + `IBrokerAccountInfo` 3 + `IBrokerTerminal` 19 = 38 broker methods; `IBrokerConnectionAdapterHost` 54 callable members (+ `factory` property).

#### 3.1 `IBrokerAccountInfo` (broker d.ts L1129-1151)

| Signature | Purpose | When called |
|---|---|---|
| `accountsMetainfo(): Promise<AccountMetainfo[]>` | List accounts (`id`, `name`, optional `type: "live"\|"demo"`, `currency`, `currencySign`). >1 element shows account drop-down. | Startup; after host `currentAccountUpdate` |
| `currentAccount(): AccountId` | Active account id. | Startup; after `currentAccountUpdate` |
| `setCurrentAccount?(id: AccountId): void` | Switch account; required when `accountsMetainfo` returns >1. | User picks account in drop-down |

#### 3.2 `IBrokerCommon` (broker d.ts L1152-1254)

| Signature | Purpose | When called |
|---|---|---|
| `chartContextMenuActions(context: TradeContext, options?: DefaultContextMenuActionsParams): Promise<ActionMetaInfo[]>` | Items for the chart context menu and the "Trade" entry; return `[]` to remove Trade. Typical: `host.defaultContextMenuActions(context)`. | Chart right-click |
| `isTradable(symbol: string): Promise<boolean \| IsTradableResult>` | Gate for Buy/Sell and ticket; `IsTradableResult` adds `reason`, `reasonHeading`, `solutions`, `shortReason`, `confirmButtonText`. | Symbol change; before ticket |
| `connectionStatus(): ConnectionStatus` | Must return `Connected (1)` or Account Manager spins forever (console: "Method connectionStatus is not properly implemented"). | Startup and after `connectionStatusUpdate` |
| `orders(): Promise<Order[]>` | Existing orders (`PlacedOrder \| BracketOrder`). | Chart load; after `ordersFullUpdate` |
| `ordersHistory?(): Promise<Order[]>` | Only final-status orders (rejected, filled, cancelled) for the History page. Required while `supportOrdersHistory` (default true) is on. | Opening History |
| `positions?(): Promise<Position[]>` | Net/regular positions. Required if `supportPositions`. | Chart load; after `positionsFullUpdate` |
| `individualPositions?(): Promise<IndividualPosition[]>` | Required if `supportPositionNetting`. | Chart load |
| `executions(symbol: string): Promise<Execution[]>` | Fills for a symbol. | Chart load / symbol change |
| `symbolInfo(symbol: string): Promise<InstrumentInfo>` | Quantity limits, pip/tick data, margin rate; needed for ticket, Buy/Sell price display and DOM. | Ticket / buttons / DOM |
| `accountManagerInfo(): AccountManagerInfo` | Build Account Manager (title, summary, columns, pages). Without it the AM is empty with a lone Trade button. | Startup |
| `formatter?(symbol: string, alignToMinMove: boolean): Promise<INumberFormatter>` | Custom price formatter. | Price display |
| `spreadFormatter?(symbol: string): Promise<INumberFormatter>` | Custom spread formatter. | Spread display |
| `quantityFormatter?(symbol: string): Promise<INumberFormatter>` | Custom quantity formatter. | Quantity display |
| `getOrderDialogOptions?(symbol: string): Promise<OrderDialogOptions \| undefined>` | Ticket custom fields (`customFields`), `showTotal`, `maxExitLevelsCount`. Field types: combobox, checkbox, text field, text field with checkbox. | Opening ticket |
| `getPositionDialogOptions?(symbol: string): Promise<PositionDialogOptions \| undefined>` | Position dialog custom fields. | Opening position dialog |
| `getSymbolSpecificTradingOptions?(symbol: string): Promise<SymbolSpecificTradingOptions \| undefined>` | Per-symbol overrides of flags (table in 4.3). | Per symbol |

#### 3.3 `IBrokerTerminal` (broker d.ts L1608-1762)

| Signature | Purpose | When called / must-follow |
|---|---|---|
| `placeOrder(order: PreOrder, confirmId?: string): Promise<PlaceOrderResult>` | Create order; return `{ orderId? }` (debug only). Must then push `orderUpdate(PlacedOrder)` with identical `id`, `symbol`, `side`, `qty` within 10 s. | Buy/Sell in ticket; also close (`isClose`) and default reverse |
| `previewOrder?(order: PreOrder): Promise<OrderPreviewResult>` | Estimated cost/commission/fees without placing; returns `sections`, `confirmId`, `warnings`, `errors`. | Click Buy/Modify when `supportPlaceOrderPreview` / `supportModifyOrderPreview`; missing impl logs "Order preview is not supported" |
| `modifyOrder(order: Order, confirmId?: string): Promise<void>` | Modify existing order; follow with `orderUpdate` within 10 s. Market orders cannot be modified. | Edit/drag order |
| `cancelOrder(orderId: string): Promise<void>` | Cancel; follow with `orderUpdate(Canceled)`. | Account Manager / chart close button |
| `cancelOrders?(symbol: string, side: Side \| undefined, ordersIds: string[]): Promise<void>` | Bulk cancel; only called from DOM "CXL all"; required for DOM. | DOM |
| `reversePosition?(positionId: string): Promise<void>` | Native reverse; follow with `positionUpdate`. | `supportNativeReversePosition` |
| `closePosition?(positionId: string, amount?: number, confirmId?: string): Promise<void>` | Close (partial if `amount`); follow with `positionUpdate` (`qty` 0 when fully closed). | `supportClosePosition` / `supportPartialClosePosition`; `confirmId` if `supportPreviewClosePosition` |
| `closeIndividualPosition?(individualPositionId: string, amount?: number, confirmId?: string): Promise<void>` | Same for a lot. | `supportCloseIndividualPosition` / partial |
| `editPositionBrackets?(positionId: string, brackets: Brackets, customFields?: CustomInputFieldsValues): Promise<void>` | Set SL/TP on a position. | `supportPositionBrackets` |
| `editIndividualPositionBrackets?(individualPositionId: string, brackets: Brackets): Promise<void>` | Same for a lot. | `supportIndividualPositionBrackets` |
| `leverageInfo?(p: LeverageInfoParams): Promise<LeverageInfo>` | Current/min/max/step leverage for a symbol+type+side. | `supportLeverage` |
| `setLeverage?(p: LeverageSetParams): Promise<LeverageSetResult>` | Send chosen leverage; broker validates/corrects and returns `{ leverage }`. | Leverage dialog |
| `previewLeverage?(p: LeverageSetParams): Promise<LeveragePreviewResult>` | `infos`, `warnings`, `errors` about chosen leverage. | Leverage dialog |
| `subscribeEquity?(): void` / `unsubscribeEquity?(): void` | Start/stop `equityUpdate` pushes; equity (Balance + P/L) drives Risk-in-percent. Needed with standard ticket + stop loss. | Ticket open/close |
| `subscribeMarginAvailable?(symbol: string): void` / `unsubscribeMarginAvailable?(symbol: string): void` | Start/stop `marginAvailableUpdate`; margin meter. | `supportMargin` |
| `subscribePipValue?(symbol: string): void` / `unsubscribePipValue?(symbol: string): void` | Dynamic pip value via `pipValueUpdate`; otherwise static `InstrumentInfo.pipValue`. | Ticket |

#### 3.4 Trading Host callbacks, `IBrokerConnectionAdapterHost` (broker d.ts L1275-1602)

| Group | Members | Notes |
|---|---|---|
| Factory | `factory.createDelegate()`, `factory.createWatchedValue(value?)`, `factory.createPriceFormatter(priceScale?, minMove?, fractional?, minMove2?, variableMinTick?)` | `priceScale` = 10^decimals; `minMove` = precision steps per tick |
| Connection | `connectionStatusUpdate(status, info?: DisconnectionInfo)` | re-invokes `connectionStatus()`; `DisconnectionInfo`: `message`, `heading`, `additionalInfo`, `disconnectType`, `reason` |
| Orders | `orderUpdate(order)`, `ordersFullUpdate()`, `orderPartialUpdate(id, changes)` | full update = drop cache and refetch via `orders()`; partial = only custom Account Manager fields changed |
| Positions | `positionUpdate(position, isHistoryUpdate?)`, `positionsFullUpdate()`, `positionPartialUpdate(id, changes)` | same pattern |
| Individual positions | `individualPositionUpdate(p, isHistoryUpdate?)`, `individualPositionsFullUpdate()`, `individualPositionPartialUpdate(id, changes)`, `individualPositionPLUpdate(id, pl)` | |
| Executions | `executionUpdate(execution)` | |
| Account | `currentAccountUpdate()` | terminal re-requests everything |
| Quotes | `realtimeUpdate(symbol, data: TradingQuotes)` | fields: `trade`, `size`, `bid`, `bid_size`, `ask`, `ask_size`, `spread`, `isDelayed`, `isHalted`, `isHardToBorrow`, `isNotShortable`, `lastSize` |
| P&L / money | `plUpdate(positionId, pl)`, `pipValueUpdate(symbol, { buyPipValue, sellPipValue })`, `equityUpdate(equity)`, `marginAvailableUpdate(n)`, `cryptoBalanceUpdate(symbol, CryptoBalance)` | `equityUpdate` is required by the standard ticket for risk math; send after the broker is built or wrap in `setTimeout` |
| DOM | `domUpdate(symbol, DOMData)` | |
| Quantity | `setQty(symbol, q)`, `getQty(symbol)`, `subscribeSuggestedQtyChange(symbol, cb)`, `unsubscribeSuggestedQtyChange(symbol, cb)` | user-chosen qty overrides `InstrumentInfo.qty.default`; `setQty` forces a value |
| Config | `patchConfig(Partial<BrokerConfigFlags>)`, `setDurations(OrderDurationMetaInfo[])` | flags can change at runtime |
| Visibility watched values | `sellBuyButtonsVisibility()`, `domPanelVisibility()`, `orderPanelVisibility()`, `tradedSourcesVisibility()`, `silentOrdersPlacement()` | `silentOrdersPlacement` = send orders without opening ticket; forced `false` when featureset `always_require_order_confirmation` is on |
| Menus | `defaultContextMenuActions(context, params?)`, `defaultDropdownMenuActions(options?: { tradingProperties?, restoreConfirmations? })` | the d.ts comment cites `setButtonDropdownActions`, but that method is NOT declared in this d.ts (gap) |
| Dialogs | `showOrderDialog?(order, focus?)`, `showNotification(title, text, type?: NotificationType)`, `showCancelOrderDialog(orderId, handler)`, `showCancelMultipleOrdersDialog(symbol, side, qty, handler)`, `showCancelBracketsDialog`, `showCancelMultipleBracketsDialog`, `showReversePositionDialog(position, handler)`, `showPositionBracketsDialog(position, brackets, focus)`, `showMessageDialog(title, text, textHasHTML?)`, `showConfirmDialog(...)`, `showSimpleConfirmDialog(...)`, `showTradingProperties()` | `showNotification` writes to toast and the Notifications log |
| Account Manager | `getAccountManagerVisibilityMode()`, `setAccountManagerVisibilityMode(mode)`, `activateBottomWidget()` (deprecated) | |
| Symbol | `getSymbolMinTick(symbol)`, `defaultFormatter(symbol, alignToMinMove)`, `numericFormatter(decimalPlaces)`, `quantityFormatter(decimalPlaces?)` | |
| Ticket settings | `getOrderTicketSetting(name)`, `setOrderTicketSetting(name, value)` | `OrderTicketSettings` keys in d.ts: `showRelativePriceControl`, `showOrderPreview` |

Minimal required set (tutorial, ctx L58522-59606): `connectionStatus`, `accountsMetainfo`, `currentAccount`, `accountManagerInfo`, `chartContextMenuActions`, `isTradable`, `symbolInfo`, `orders`, `positions`, `executions`, `placeOrder`, `modifyOrder`, `cancelOrder`; set `supportOrdersHistory: false` unless `ordersHistory` exists.

Timing contract: after `placeOrder` / `modifyOrder` / `cancelOrder` / `closePosition` / `reversePosition` / `editPositionBrackets`, the library waits 10 s for the matching `orderUpdate` / `positionUpdate`, else shows a timeout toast (ctx L52962-52995).

### 4. `BrokerConfigFlags`

#### 4.1 All 57 flags (broker d.ts L462-834)

| Flag | Default | Effect | Requires |
|---|---|---|---|
| `showQuantityInsteadOfAmount` | false | "Amount" label becomes "Quantity" | |
| `supportOrderBrackets` | false | TP/SL controls on new orders | |
| `supportStopLoss` | true | Stop-loss orders and ticket field; if false enable trailing or guaranteed | |
| `supportTrailingStop` | false | Trailing stop orders | |
| `supportGuaranteedStop` | false | Guaranteed stop orders | |
| `supportPositions` | true | Positions tab; false hides it | `positions()` |
| `supportPositionBrackets` | false | Edit button, "Edit position..." menu; takes precedence over individual lines on chart | `editPositionBrackets` |
| `supportIndividualPositionBrackets` | false | Same for individual positions (keep `supportPositionBrackets` false) | `editIndividualPositionBrackets` |
| `supportPositionNetting` | false | Individual + Net Positions tabs | `positions`, `individualPositions` |
| `supportClosePosition` | false | false = opposite market order via `placeOrder(isClose)`; true = `closePosition` | `closePosition` |
| `supportCloseIndividualPosition` | false | Close a lot | `closeIndividualPosition` |
| `supportModifyOrderPrice` | true | Price editing; with `supportEditAmount` and `supportModifyBrackets` all false, Modify button and chart drag-and-drop are removed | |
| `supportEditAmount` | true | Quantity editing in modify | |
| `supportModifyBrackets` | true | Bracket editing; false hides Modify in AM and chart | |
| `supportLevel2Data` | false | DOM Level 2 | Datafeed `subscribeDepth`/`unsubscribeDepth`, broker `cancelOrders` |
| `supportMultiposition` | false | Several positions per symbol; disables default reverse and DOM Flatten | native reverse |
| `supportPLUpdate` | true | You supply P&L; false = library computes from trade price vs avg price | `plUpdate` |
| `supportReversePosition` | false | Reverse button | |
| `supportNativeReversePosition` | false | Backend reverse | `reversePosition` |
| `supportMarketOrders` | true | Market type in ticket | |
| `supportLimitOrders` | true | Limit type | |
| `supportStopOrders` | true | Stop type | |
| `supportStopLimitOrders` | false | Stop-limit type | |
| `supportDemoLiveSwitcher` | true | Demo/live switch | |
| `supportMarketBrackets` | true | Brackets on market orders | |
| `supportSymbolSearch` | false | Symbol search | |
| `supportModifyDuration` | false | Change duration of existing order | `durations` |
| `supportModifyTrailingStop` | true | Edit trailing stops | |
| `supportMargin` | false | Margin meter | `subscribeMarginAvailable`, `marginAvailableUpdate`, `InstrumentInfo.marginRate` |
| `supportPlaceOrderPreview` | false | Confirmation dialog before placing | `previewOrder`, pass `confirmId` |
| `supportModifyOrderPreview` | false | Confirmation before modify | `previewOrder` |
| `supportLeverage` | false | Leverage trading | `leverageInfo` |
| `supportLeverageButton` | true | Leverage input in ticket (needs `supportLeverage`) | |
| `supportOrdersHistory` | true | History tab | `ordersHistory` (else AM breaks) |
| `supportAddBracketsToExistingOrder` | true | Add brackets to open order | |
| `supportBalances` | false | Crypto balances table (crypto only) | `cryptoBalanceUpdate` |
| `closePositionCancelsOrders` | false | Closing a position cancels its brackets | |
| `supportOnlyPairPositionBrackets` | false | SL+TP together only (position) | |
| `supportOnlyPairOrderBrackets` | false | SL+TP together only (order) | |
| `supportCryptoExchangeOrderTicket` | false | Crypto Exchange ticket mode (base or quote qty) | |
| `supportSymbolSpecificCryptoOrderTicket` | false | Auto-switch to exchange ticket when symbol type is `crypto` | |
| `positionPLInInstrumentCurrency` | false | P&L in instrument currency | |
| `showRiskInInstrumentCurrency` | false | Bracket risk in instrument currency | |
| `supportPartialClosePosition` | false | Partial close dialog | `closePosition(amount)` |
| `supportPartialCloseIndividualPosition` | false | Partial close of a lot | `closeIndividualPosition(amount)` |
| `supportCancellingBothBracketsOnly` | false | Dialog text only | `cancelOrder(s)` |
| `supportCryptoBrackets` | false | TP/SL entry in Money or % | |
| `showNotificationsLog` | true | Notifications log tab | |
| `supportStopOrdersInBothDirections` | false | Stop orders act as market-if-touched both ways; skips stop-direction check | |
| `supportStopLimitOrdersInBothDirections` | (none) | Same for stop-limit (limit-if-touched) | |
| `supportStrictCheckingLimitOrderPrice` | (none) | Reject limit prices on the wrong side of the market (would fill immediately) | |
| `supportExecutions` | true | Executions as chart marks | `executions()` |
| `supportModifyOrderType` | false | Change type of an existing order | |
| `requiresFIFOCloseIndividualPositions` | false | Individual positions close FIFO | |
| `supportMultipleExitLevels` | false | Several TP/SL levels ("Add level") | |
| `supportUnpairedExitLevels` | false | Level with a single leg | multiple levels |
| `supportCustomOrderInfo` | false | Broker-defined rows in Order info | |
| `supportPreviewClosePosition` | false | Close-position preview with `confirmId` | |

Not in this d.ts (do not rely on): `supportDOM` (DOM is gated by the `dom_widget` featureset plus `supportLevel2Data`), `supportCancelOrderForNonTradableSymbol`, `show_symbol_logos` (a featureset; the tutorial lists both inside `configFlags`, ctx L61180-61408).

Related featuresets (docs): `order_panel` (disables ticket and Trade button), `trading_account_manager`, `open_account_manager`, `dom_widget`, `show_dom_first_time`, `dom_raw_volume_values`, `show_symbol_logos`, `always_require_order_confirmation`.

#### 4.2 Other `broker_config` members (`SingleBrokerMetaInfo`, broker d.ts L2508-2559)

`configFlags`; `tradedGroupConfig: { supportAdaptiveLayout }`; `customNotificationFields: string[]`; `durations`; `orderRules: OrderRule[]` (`{ id, severity: "warning" \| "error" }`); `customUI` with `showOrderDialog`, `showPositionDialog`, `showCancelOrderDialog`, `showClosePositionDialog`, `showReversePositionDialog` (each returns `Promise<boolean>`).

#### 4.3 `SymbolSpecificTradingOptions` (broker d.ts L2675-2746)

`allowedDurations`, `allowedOrderTypes`, `supportOrderBrackets`, `supportBracketsInPips` (default true), `supportAddBracketsToExistingOrder`, `supportModifyBrackets`, `supportPositionBrackets`, `supportIndividualPositionBrackets`, `supportReversePosition`, `warningMessage`, `supportModifyPositionBrackets`, `supportModifyOrderBrackets`, `supportRiskControlsAndInfo`, `supportStopLoss`, `supportTrailingStop`, `supportGuaranteedStop`, `supportCryptoExchange`.

### 5. Data structures

#### 5.1 `PreOrder` (ticket output; broker d.ts L2462-2479, `OrderTemplateBase` L2285-2318)

| Field | Type | Notes |
|---|---|---|
| `symbol` | string | required |
| `type` | `OrderType` | required in `PreOrder` |
| `side` | `Side` | required |
| `qty` | number | required |
| `isClose` | boolean? | true when the order closes (or default-reverses) a position |
| `exitLevels` | `ExitLevel[]?` | multiple-exit mode |
| `stopType` | `StopType?` | |
| `currentQuotes` | `{ ask, bid }?` | quotes at ticket time |
| `stopPrice`, `limitPrice` | number? | per type |
| `takeProfit`, `stopLoss`, `guaranteedStop`, `trailingStopPips` | number? | brackets |
| `duration` | `OrderDuration?` | |
| `customFields` | `CustomInputFieldsValues?` | |

#### 5.2 `PlacedOrder` and `BracketOrder` (`Order = PlacedOrder \| BracketOrder`; broker d.ts L2339-2387, L439-446)

| Field | Type | Notes |
|---|---|---|
| `id` | string | unique; may later be reused as the position id |
| `symbol`, `type`, `side`, `qty`, `status` | | required |
| `stopLoss`, `takeProfit`, `guaranteedStop`, `trailingStopPips`, `trailingStopPrice`, `stopType` | number? / `StopType?` | stopType 1 = trailing |
| `exitLevels` | `ExitLevel[]?` | |
| `duration`, `customFields` | | |
| `filledQty`, `avgPrice` | number? | fill progress and average fill price |
| `updateTime` | number? | ms |
| `limitPrice`, `stopPrice` | number? | echo these for limit/stop parents |
| `message` | `{ type, text }?` | info/warning/error text shown on the order |
| `extra` | object? | custom fields; reference as `dataFields: [["extra","key"]]` |
| `BracketOrder.parentId` | string | parent order or position id |
| `BracketOrder.parentType` | `ParentType` | |
| `BracketOrder.exitLevelId` | string? | |

#### 5.3 `Position` / `PositionBase` (broker d.ts L2394-2450)

`id` (usually equals the broker symbol), `symbol`, `qty` (positive), `shortQty?`, `longQty?`, `side`, `avgPrice` (weighted average price; line drawn here; basis of library P&L), `updateTime?`, `lastPrice?`, `bidPrice?`, `askPrice?`, `unrealizedPl?`, `unrealizedPlPercent?`, `unrealizedPlQty?`, `marketValue?`, `stopLoss?`, `takeProfit?`, `guaranteedStop?`, `trailingStopPips?`, `trailingStopPrice?`, `stopType?`, `currency?`, `contractExpirationDate?`, `message?`, `exitLevels?`, `extra?` (docs: put monetary P&L in `extra.pl`, ctx L55291-55399).

`IndividualPosition` (broker d.ts L1927-1985) adds `date` (open ms), `price` (lot entry price), `canBeClosed?`, `pl?`, `visiblePL?` and drops `shortQty` / `longQty` / `contractExpirationDate`; also has `avgPrice?`, `unrealizedPl*`, `marketValue?`, brackets, `exitLevels?`, `extra?`.

#### 5.4 `Execution` (broker d.ts L1026-1051)

`id`, `symbol`, `price`, `qty`, `side`, `time` (ms) required; `commission?`, `fee?`, `netAmount?`, `currencyRate?` (account vs symbol currency), `extra?`.

#### 5.5 `InstrumentInfo` (returned by `symbolInfo`; broker d.ts L1986-2047)

| Field | Req | Meaning |
|---|---|---|
| `qty: QuantityMetainfo` | yes | `{ min, max, step, uiStep?, default? }` |
| `pipValue` | yes | value of one pip in account currency; 0 hides Order info and makes bracket P&L show 0 in Money mode |
| `pipSize` | yes | size of one pip (EURUSD 0.0001) |
| `minTick` | yes | smallest price change (EURUSD 0.00001) |
| `description` | yes | text for dialogs |
| `lotSize`, `type: SymbolType` (`forex` enables negative pips), `units` (quantity label), `brokerSymbol`, `currency`, `baseCurrency`, `quoteCurrency` (crypto) | no | |
| `leverage?: string`, `marginRate?: number` | no | 3% margin = 0.03 |
| `limitPriceStep`, `stopPriceStep` | no | override `minTick` per price field |
| `variableMinTick` | no | string like `0.01 10 0.02 25 0.05` (tick 0.01 below 10, 0.02 below 25, 0.05 from 25) |
| `allowedDurations`, `allowedOrderTypes` | no | |
| `bigPointValue` | no | value of a full point, used for Total value |
| `priceMagnifier` | no | price multiplier vs base unit |

#### 5.6 `LeverageInfo` and related (broker d.ts L2082-2162)

`LeverageInfo { title, leverage, min, max, step }`; `LeverageInfoParams { symbol, orderType, side, customFields? }`; `LeverageSetParams = LeverageInfoParams + leverage`; `LeverageSetResult { leverage }`; `LeveragePreviewResult { infos?, warnings?, errors? }`.

#### 5.7 Other

| Type | Fields |
|---|---|
| `Brackets` | `stopLoss?`, `guaranteedStop?`, `takeProfit?`, `trailingStopPips?`, `exitLevels?` |
| `ExitLevel` | `id`, `qty`, `takeProfit?`, `stopLoss?`, `guaranteedStop?`, `trailingStopPips?`, `isExisting?` (default true); `ExitLevelTemplate` adds `tpPips`, `slPips`, `tpRiskInPercent`, `slRiskInPercent`, `tpParentPricePercent`, `slParentPricePercent`, `tpRiskInCurrency`, `slRiskInCurrency` |
| `PlaceOrderResult` | `{ orderId? }` |
| `OrderPreviewResult` | `{ sections: {header?, rows: {title, value}[]}[], confirmId?, warnings?, errors? }` |
| `CryptoBalance` | `symbol`, `total`, `available`, `reserved?`, `value?`, `valueCurrency?`, `longName?`, `btcValue?` |
| `PipValues` | `buyPipValue`, `sellPipValue` |
| `TradeContext` | `symbol`, `displaySymbol`, `value`, `formattedValue`, `last` |
| `DOMData` / `DOMLevel` | see section 7.3 |
| `AccountMetainfo` | `id`, `name`, `type?`, `currency?`, `currencySign?` |

### 6. Equations

| # | Quantity | Formula | Label / source |
|---|---|---|---|
| 1 | P&L display modes | The user picks Money, Ticks or Percentage (Settings, Positions, Profit & loss). Money shows your `pl`/`plUpdate` value verbatim (must be monetary, not ticks or percent). Ticks and Percentage ignore your value and are computed by the library. | (docs) ctx L55347-55399 |
| 2 | P&L in Ticks | `((currentPrice - avgPrice) * sign) / tickSize`; `sign` = `side` (1 long, -1 short); `currentPrice` = bid/ask/last; `tickSize` = `pipSize` from `symbolInfo` if present, else `minTick`. | (docs) ctx L55347-55399 |
| 3 | P&L in Percentage | `((currentPrice - avgPrice) / avgPrice) * 100 * sign` | (docs) ctx L55347-55399 |
| 4 | P&L when `supportPLUpdate=false` | Library uses difference between current trade price and average position price; TradingView recommends your own calculation to avoid account vs position mismatches. | (docs) ctx L55291-55326; broker d.ts L578-588 |
| 5 | Unrealized P&L (monetary) | `(markPrice - avgPrice) * qty * sign * pointValue` (`pointValue` ~ `bigPointValue`; 1 for linear spot) | (standard definition); the tutorial uses `pointValue = 1` |
| 6 | Pip value | `pipValue = pipSize * pointValue * accountCurrencyRate` (tutorial's mock; `|| 1` fallback to avoid 0) | (docs) ctx L58522-58883 |
| 7 | Money P&L from pips (standard use of `pipValue`) | `pl = ((mark - avg) * sign / pipSize) * pipValue * qty` when `pipValue` is per unit | (standard definition); unit basis of `pipValue` is not stated in the docs |
| 8 | Average price on increase | `avgNew = (q1*p1 + q2*p2) / (q1 + q2)` for same-side adds; on partial reduce `avgPrice` is unchanged, realized P&L = `(exit - avg) * closedQty * sign`; fee excluded unless supplied | (standard definition); docs only say `avgPrice` is the weighted average of all positions for the symbol (broker d.ts L2408) |
| 9 | Net position from individual lots | `netQty = sum(sign_i * qty_i)`; example long 100 + short 50 = long 50 | (docs) ctx L55105-55137 |
| 10 | Default reverse | `placeOrder(side = opposite, qty = 2 * positionQty, isClose = true)`; long 100 becomes sell 200 and ends short 100 | (docs) ctx L55214-55232 |
| 11 | Margin rate | `marginRate` is a fraction (3% = 0.03); required margin = `notional * marginRate`; implied leverage = `1 / marginRate` | rate meaning (docs, ctx L53989-54060); the two derived formulas are (standard definition) |
| 12 | Margin meter | Shows how much of available margin an order will use; inputs: `marginRate`, `marginAvailableUpdate`. Exact share formula not documented; (standard definition) `orderNotional * marginRate / marginAvailable`. | (docs) + (standard definition) |
| 13 | Risk in percent / money (brackets, ticket) | Docs say only that equity (Balance + P/L, via `equityUpdate`) is used for "Risk in Percent" and that ticket settings exist for "Quantity in Money Risk" and "% Risk". Formula not given. (standard definition): `riskMoney = |entry - stop| / pipSize * pipValue * qty`, `riskPct = riskMoney / equity * 100`. | (docs) broker d.ts L1722-1727, ctx L53843-53911; formula (standard definition) |
| 14 | Bracket distance ticks to price | `price = entry + sign * ticks * minTick` for TP (opposite sign for SL), rounded to the tick grid. Price grid: `priceScale = 10^decimals`, `minMove` ticks per step; tick size = `minMove / priceScale` (tutorial uses `1 / priceScale` for `minMove = 1`). `variableMinTick` makes tick size depend on price band. Brackets can be entered in ticks/pips unless `supportBracketsInPips: false`. | tick size and `variableMinTick`: (docs) broker d.ts L1262-1266, L2026-2031, ctx L62162 (DOM tick); `price = entry + ...`: (standard definition) |
| 15 | Equity | `equity = balance + P/L` | (docs) broker d.ts L1725 |
| 16 | Total / trade value | Uses `bigPointValue` (value of one full price point); `showTotal` switches "Trade Value" to "Total" | (docs) broker d.ts L2041-2043, L2196-2200 |

### 7. Account Manager, formatters, DOM, watchlist, news

#### 7.1 Account Manager (ctx L52546-52778; broker d.ts L230-402)

| Item | Detail |
|---|---|
| `AccountManagerInfo` | `accountTitle`, `summary: AccountManagerSummaryField[]`, `customFormatters?`, `orderColumns`, `orderColumnsSorting?`, `historyColumns?`, `historyColumnsSorting?`, `positionColumns?`, `individualPositionColumns?`, `pages`, `possibleOrderStatuses?: OrderStatus[]` |
| `AccountManagerSummaryField` | `text`, `wValue` (a `WatchedValue`, created by `host.factory.createWatchedValue`, updated with `setValue`), `formatter?`, `isDefault?`, `informerMessage?` |
| `AccountManagerPage` | `id`, `title`, `tables`, `displayCounterInTab?` |
| `AccountManagerTable` | `id`, `title?`, `columns`, `initialSorting?`, `changeDelegate` (`fire(row)` pushes rows), `deleteDelegate?` (`fire(id)`), `flags?: { supportPagination }`, `getData(paginationLastId?)`; every row needs a unique string `id`; `isTotalRow` pins a row to the bottom |
| Column (`AccountManagerColumnBase`) | required `id`, `label`, `dataFields`; optional `formatter`, `alignment` (`left`/`right`), `sortProp`, `notSortable`, `help`, `highlightDiff`, `notHideable`, `hideByDefault`, `tooltipProperty`, `isCapitalize`, `showZeroValues`; order columns also `supportedStatusFilters` |
| `dataFields` | property names of the order/position object; nested custom data via `[["extra","key"]]`; a column re-renders only when its `dataFields` values change; `[]` = formatter receives the whole object and any change refreshes |
| Pages | Orders and Positions (via `orders()` / `positions()`), History (`ordersHistory`, final statuses only), Notifications log (`showNotificationsLog`; fed by `showNotification`), custom pages (`pages`) |
| Startup | `getAccountManagerVisibilityMode` / `setAccountManagerVisibilityMode`; featureset `open_account_manager` off hides on start; `trading_account_manager` off disables |
| Login flow | Library calls `accountsMetainfo` on start; after your login, call `currentAccountUpdate`; library re-calls `accountsMetainfo` and `currentAccount`. No login dialog is provided (ctx L54292-54362) |

#### 7.2 `StandardFormatterName` (29 values, broker d.ts L44-74; meaning per docs ctx L52283-52545)

| Value | Expected `dataFields` types / behavior |
|---|---|
| `"date"` / `"localDate"` | date |
| `"dateOrDateTime"` / `"localDateOrDateTime"` | `{ dateOrDateTime: number, hasTime: boolean }` |
| `"default"` | strings joined by spaces |
| `"empty"` | blank |
| `"fixed"` | number, 2 decimals (balance, equity) |
| `"fixedInCurrency"` | `[number, string]` adds currency |
| `"variablePrecision"` | number (qty) |
| `"formatQuantity"` | number with thousands spacing (`qty`, `filledQty`) |
| `"integerSeparated"` | integer with non-breaking-space groups |
| `"formatPrice"` | number (`limitPrice`, `stopPrice`, `avgPrice`) |
| `"formatPriceForexSup"` | price with last digit superscript, forex type only |
| `"formatPriceInCurrency"` | `[number, string]` |
| `"formatExitLevels"` | `[price, exitLevels, qty]` (`takeProfit` / `stopLoss`) |
| `"percentage"` | number as percent |
| `"coloredPercentage"` | percent, red if negative, orange under 5%, none at 5%+ |
| `"marginPercent"` | percent; under 0.01 raw plus `%`; non-finite shows `"> 200%"` |
| `"pips"` | number (`pipValue`) |
| `"profit"` | account-currency profit, `+` sign, thousands, red/green |
| `"profitInInstrumentCurrency"` | `[number, string]`, same styling |
| `"profitInInstrumentCurrencyFloored"`, `"profitInPercent"` | in the enum; not described in the docs |
| `"side"` | order side Buy/Sell |
| `"positionSide"` | Long/Short |
| `"status"` | order status text |
| `"symbol"` | `[brokerSymbol, symbol, message]`; click loads chart |
| `"text"` | string |
| `"type"` | `[type, parentId, stopType]` -> Limit/Stop/Stop-limit/Market |

Custom formatter (`customFormatters`): `name` (cast to `FormatterName`), `formatText` (required; used for export), `formatElement?` (HTML), `isPriceFormatterNeeded?` (ctx L52283-52320). Type mapping is in `StandardFormattersDependenciesMapping` (broker d.ts L2570-2655).

#### 7.3 DOM / Level 2 (ctx L53160-53271; ctx L61536-62161; broker d.ts L976-996)

| Item | Detail |
|---|---|
| Enable | featureset `dom_widget` + `supportLevel2Data: true` + `cancelOrders` implemented; Datafeed: `getQuotes`, `subscribeQuotes`, `unsubscribeQuotes`, `subscribeDepth`, `unsubscribeDepth`; optional featuresets `show_dom_first_time`, `dom_raw_volume_values` (drops K/M/B/T suffixes) |
| Mode | Static: price series fixed, last price moves within/above/below the range |
| `subscribeDepth(symbol, callback)` | returns a listener id string; call `callback({ snapshot, bids, asks })` |
| `unsubscribeDepth(listenerId)` | stop updates |
| `DOMData` | `{ snapshot: boolean, asks: DOMLevel[], bids: DOMLevel[] }`; `snapshot true` = full set, `false` = changed levels only; the d.ts says both arrays must be sorted ascending by `price` |
| `DOMLevel` | `{ price: number, volume: number }` |
| Push alternative | host `domUpdate(symbol, DOMData)` |
| Tutorial pattern | Binance `<symbol>@depth20@100ms`; normalise `[price, qty]` tuples to `{price, volume}`, drop non-finite or zero volume, cap 20 levels; push every 250 ms; synthetic ladder placeholder until live data (documented as demo-only) |
| Not in small viewports | DOM and Account Manager do not render in small iframes |

#### 7.4 Watchlist (ctx L52079-52250)

| Item | Detail |
|---|---|
| Enable | `widgetbar: { watchlist: true, watchlist_settings: { default_symbols: [...], readonly } }`; needs quote methods |
| API | `await widget.watchList()` returns `IWatchListApi`: `createList(title, symbols?)`, `getAllLists()`, `getActiveListId()`, `getList(id)`, `updateList(id, symbols)`, events `onListAdded`, `onListChanged`, `onListRemoved`, `onListRenamed` |
| Sections | list items starting with `###` are section dividers |
| Symbols | resolved one by one through `resolveSymbol`; prefer full `LibrarySymbolInfo` names (`NASDAQ:AAPL`) |
| Persistence | part of user settings; default `localStorage`, or `settings_adapter`; use list events to sync to your server |
| Logos | featureset `show_symbol_logos` + `logo_urls` in `LibrarySymbolInfo` |

#### 7.5 News (ctx L53584-53723)

| Item | Detail |
|---|---|
| Enable | `widgetbar: { news: true }`; needs quote methods |
| Sources | no built-in provider; `rss_news_feed: { default: { url, name }, <symbolType>: {...} }` (URL tags `{SYMBOL}`, `{TYPE}`, `{EXCHANGE}`) or `news_provider(symbol, callback)` returning `{ title, newsItems }`; if both given, `rss_news_feed` is ignored |
| `NewsItem` | `title`, `source`, `published` (ms), `shortDescription`, `fullDescription`, `link` (opens in pop-up; else full description shown) |
| Refresh | `(await widget.news()).refresh()` |
| CORS | tutorial proxies a CoinDesk RSS feed same-origin because the feed sends no CORS headers (ctx L62162-62658) |

#### 7.6 Order Ticket extras (ctx L53724-54150)

Open via Account Manager Trade button, price-scale plus button, legend Buy/Sell Market, or right-click Trade. Disable with featureset `order_panel`. Ellipsis settings: Show Order Price in Ticks, Show Quantity in Money Risk, Show Quantity in % Risk, Show TP/SL inputs in Money / %, Show order confirmation. Crypto brackets add Money and % entry (the Money/% TP/SL settings have no effect there). Custom ticket: `customUI.showOrderDialog`. Custom fields cannot be added to the "Order info" section; use the order preview dialog instead.

### 8. Common Broker API issues (symptom, cause, fix)

| # | Symptom | Cause | Fix | Source |
|---|---|---|---|---|
| 1 | "Failed to close position: Position closing timeout"; "Failed to modify order: timeout waiting for new order"; "Failed to reverse position: Position reversing timeout" | No matching `orderUpdate` / `positionUpdate` within 10 s, or the update is wrong | Always push the update after the request. For a close, send the same `id`, `qty: 0` and valid required fields; a non-zero qty or different id is treated as a different position and the library keeps waiting | ctx L52962-52995 |
| 2 | Account Manager spins forever; console "Method connectionStatus is not properly implemented" | `connectionStatus()` missing or not `Connected (1)` | Return `ConnectionStatus.Connected`; use `connectionStatusUpdate` for other states | ctx L58522-58883; broker d.ts L1172-1180 |
| 3 | Account Manager empty, only Trade button | `accountManagerInfo` not implemented | Implement it (or disable `trading_account_manager`) | ctx L58522-58883 |
| 4 | Account Manager breaks | `supportOrdersHistory` defaults true but `ordersHistory` missing | Implement `ordersHistory` or set the flag false | broker d.ts L1186-1189 |
| 5 | Buy/Sell buttons not visible | Not Trading Platform; or hidden in Settings, Trading, Buy/Sell buttons | Use TP; enable the setting | ctx L52996-53005 |
| 6 | Buy/Sell disabled / "Non-tradable symbol" | `isTradable` missing or false | Return true or `IsTradableResult` | ctx L52996-53005 |
| 7 | Buttons show no prices / "..." | `symbolInfo` missing | Implement it | ctx L52996-53005, L58522-58883 |
| 8 | Buttons do nothing, "order rejected" toast | `placeOrder` missing | Implement `placeOrder` | ctx L58522-58883 |
| 9 | Prices in buttons static | `getQuotes` / `subscribeQuotes` missing | Implement Datafeed quote methods | ctx L52996-53005, L55400-55441 |
| 10 | "Failed to modify order" toast | `modifyOrder` missing | Implement and call `orderUpdate` | ctx L59083-59606 |
| 11 | UI shows wrong data; cannot modify/cancel | Order or position id changed between submit and backend processing | `ordersFullUpdate()` / `positionsFullUpdate()` (rare cases only); normally use `orderUpdate` / `positionUpdate` | ctx L53006-53027 |
| 12 | Bracket inputs empty / not editable | Missing `LibrarySymbolInfo` or `InstrumentInfo` fields, quotes, pip value, or equity | Complete `resolveSymbol` and `symbolInfo`; supply quotes, `pipValueUpdate` (if `subscribePipValue`), `equityUpdate` (wrap early calls in `setTimeout`) | ctx L53028-53064 |
| 13 | Ticket quantity differs from your default | User-edited qty is persisted (local storage or `settings_adapter`); by design | `subscribeSuggestedQtyChange` plus `setQty` to force | ctx L53065-53099 |
| 14 | Bracket P&L shows 0 | `pipValue` is 0 (Money mode only) | Set non-zero `pipValue` | ctx L53100-53108 |
| 15 | Individual positions missing on chart with netting | `supportPositionBrackets` true takes precedence | `supportPositionBrackets: false`, `supportIndividualPositionBrackets: true` | ctx L53109-53159 |
| 16 | Console "Order preview is not supported" | preview flags on but `previewOrder` missing | Implement `previewOrder` | ctx L53781-53842 |
| 17 | "Cannot reverse position on multiposition account" | Default reverse cannot handle multiposition | Native reversal (`supportNativeReversePosition` + `reversePosition`) | ctx L55214-55260 |
| 18 | Watchlist / Details / News / DOM loading delays or missing data; mobile legend `N/A` | Quote methods absent | Implement `getQuotes`, `subscribeQuotes`, `unsubscribeQuotes` | ctx L55400-55441, L55873-56037 |
| 19 | Market order cannot be edited | By design | Cancel and re-place | ctx L59083-59606 |
| 20 | Trading UI missing, `globalThis.Brokers` undefined | BrokerDemo bundle absent in tutorial setup | Copy the sample bundle; code warns instead of crashing | ctx L61180-61408 |
| 21 | Stale net-position counts | Tab counter counts net positions only | Expected | ctx L55105-55137 |
| 22 | Slow watchlist load | Items resolved sequentially via `resolveSymbol` | Expected; no batch resolution | ctx L52079-52250 |

### Use in solmargintrader

Premise: the extension (`extension/src/`) can place real orders (Jupiter Trigger limits on Solana; Hyperliquid perps under consideration) but defaults to dry-run; rails are fail-closed in `core/risk.js`; one command registry in `core/commands.js`; the engine reconciles the venue order list before planning; ladder exits sit one rung above entry. TradingView Trading Platform is access-restricted, browser-hosted and keeps no state, so it can only be a viewer or an order-entry front end on top of those gates. Facts below cite the repo files read for this section.

#### A. Method routing: what must pass through `commands.js` and `risk.js`

Existing registry commands used (names from `COMMANDS` in `extension/src/core/commands.js`): `status`, `getConfig`, `getLimits`, `levels`, `capital`, `price`, `plan`, `pnl`, `data`, `exportCsv`, `venueInfo`, `holdings`, `overview`, `arm`, `disarm`, `kill`, `clearKill`, `tick`, `cancelOrder`, `resolveIntent`, `setLimits`. No command named `placeOrder` exists; a manual-order path would be a NEW command (proposal, not existing code).

| Broker API method | Class | Route |
|---|---|---|
| `connectionStatus`, `accountsMetainfo`, `currentAccount`, `accountManagerInfo`, `symbolInfo`, `executions`, `formatter` family | read-only | Derive from `status`, `getConfig`, `venueInfo`, `price`, `pnl`, `data`; no writes. Map kill-switch or venue-down to `Disconnected` via `connectionStatusUpdate` (fail-closed visuals) |
| `orders`, `positions`, `individualPositions`, `ordersHistory` | read-only | From the store's intents plus the last reconciled venue snapshot (the same data `plan` and `status` read) |
| `isTradable` | gate | Return `{ tradable: false, reason }` unless mode is armed, not killed, and `risk.normaliseState` accepts state; default `false` in dry-run |
| `chartContextMenuActions` | gate | Return `[]` initially (removes Trade menu entry) |
| `previewOrder` | pure | Call `risk.evaluate({ order, state, limits, openLots })` (or `admitBatch`) and render the verdict (`allow`/`block`) and the failed rail ids into `sections`/`errors`; never contacts the venue; supports `supportPlaceOrderPreview` |
| `placeOrder` | WRITE | Must NOT call the venue. It enqueues one intent through a registry command that (1) runs `risk.evaluate`, (2) writes the intent as `submitting` (write-ahead, as in `engine.js` before `venue.placeOrder`), (3) submits through the engine's single queue, (4) lands in `resting` or `unknown`. In dry-run it records a simulated intent only |
| `cancelOrder` | WRITE | Route to the existing `cancelOrder` command; on ambiguous outcome keep intent held (engine already logs "cancellation outcome unknown; intent held") |
| `cancelOrders` | WRITE | Leave unimplemented (DOM off). If ever added, loop the single `cancelOrder` command, not a venue bulk call |
| `modifyOrder` | WRITE | Not supported by a cancel-and-replace-less venue; leave unimplemented. A modify would be cancel + new intent = two risk-gated commands and a window with no resting order |
| `closePosition`, `closeIndividualPosition`, `reversePosition` | WRITE | Leave off; closing in this system is "place the paired exit" through the planner, not a market order |
| `editPositionBrackets`, `editIndividualPositionBrackets` | WRITE | Leave off (no stop-loss concept in the ladder) |
| `leverageInfo`, `setLeverage`, `previewLeverage` | WRITE/limit | Off for Jupiter spot (`maxLeverage` default 1 in `DEFAULT_LIMITS`). For Hyperliquid, `setLeverage` must go through `setLimits` (a risk-rail change, not a venue call) and `liquidation distance` rail |
| `subscribeEquity`, `subscribeMarginAvailable`, `subscribePipValue` | read-only | Feed from `capital`/`holdings`; if venue value is unknown, send nothing (never a guessed number) |

Rule: every host-side effect that can reach the venue is a registry command; the adapter holds no venue client.

#### B. Callbacks and "reconcile before plan"

- TradingView's flow is optimistic (`placeOrder` returns, then you push `orderUpdate(Working)`). The extension's flow is reconcile-first. Resolve the conflict by pushing to the host only after the tick's reconcile step: tick = fetch venue live orders, mark `resting` intents not found as `unknown`, promote matched `submitting` to `resting`, record fills, then plan, then `admitBatch`, then submit (engine behavior in `engine.js` around the `INTENT_STATUS` transitions). Emit `orderUpdate`/`positionUpdate`/`executionUpdate`/`plUpdate`/`equityUpdate` from the post-reconcile diff, never from the submit return value.
- Id stability: use `intentKey` as the TradingView order `id`. `venueOrderId` is only known after submit; using it would trigger the "Order and position IDs mismatch" failure (issues table #11). If ids must change, call `ordersFullUpdate()` once (docs call it rare-case only).
- 10-second contract: when submit outcome is ambiguous the extension must hold the intent as `unknown` and never retry. TradingView would show its timeout toast; that is acceptable and fail-closed. Better: push the order with status `Placing` and `message: { type: "warning", text: "unknown: not found on venue, needs review" }` so the Account Manager shows it, then resolve through the existing `resolveIntent` command.
- `executionUpdate` order for a fill: `executionUpdate`, then `orderUpdate(Filled)`, then `positionUpdate`, then `plUpdate`/`equityUpdate` (docs sequence).
- `realtimeUpdate`/quotes must come from the same price source the planner uses, not a second feed.
- Leave fee fields (`Execution.fee`, `commission`) undefined unless the venue reported them (repo rule: never guess a fee).

#### C. `BrokerConfigFlags` to keep off (or constrained) to avoid unintended orders

| Setting | Value | Reason |
|---|---|---|
| `supportModifyOrderPrice`, `supportEditAmount`, `supportModifyBrackets` | all `false` | Documented way to remove the Modify button and chart drag-to-modify (a drag edits a live order on release) |
| `supportMarketOrders` | `false` | Jupiter Trigger is limit-only; a market order bypasses the grid and slippage planning |
| `supportStopOrders`, `supportStopLimitOrders`, `supportStopOrdersInBothDirections`, `supportStopLimitOrdersInBothDirections` | `false` | Not part of the ladder |
| `supportOrderBrackets`, `supportPositionBrackets`, `supportIndividualPositionBrackets`, `supportMultipleExitLevels`, `supportUnpairedExitLevels`, `supportAddBracketsToExistingOrder`, `supportMarketBrackets`, `supportCryptoBrackets` | `false` | Brackets create child orders automatically (OSO/OCO); the repo derives exits itself |
| `supportTrailingStop`, `supportGuaranteedStop`, `supportModifyTrailingStop` | `false` (and `supportStopLoss` stays default only if unused) | No such order type on the venue |
| `supportClosePosition`, `supportCloseIndividualPosition`, `supportPartialClose*`, `closePositionCancelsOrders`, `supportReversePosition`, `supportNativeReversePosition`, `supportMultiposition` | `false` | One-click close/reverse = immediate market order; reverse is 2x qty |
| `supportModifyDuration`, `supportModifyOrderType` | `false` | In-place edits |
| `supportLeverage`, `supportLeverageButton`, `supportMargin` | `false` for Jupiter spot | Leverage is a rail (`maxLeverage`), not a UI toggle |
| `supportDemoLiveSwitcher` | `false` | Dry-run vs live is repo config (armed state), not a widget toggle |
| `supportCryptoExchangeOrderTicket`, `supportSymbolSpecificCryptoOrderTicket`, `supportBalances` | `false` initially | Exchange-style ticket changes qty semantics |
| `supportPlaceOrderPreview` | `true` (when ordering is ever enabled) | Gives a forced confirmation step that maps to `risk.evaluate` |
| `supportOrdersHistory` | `false` until `ordersHistory` exists | Else Account Manager breaks |
| Host `silentOrdersPlacement()` | keep `false`; keep featureset `always_require_order_confirmation` on | Otherwise Buy/Sell sends an order without opening the ticket |
| `order_panel` featureset off | for the read-only phase | Hides Trade button; also hide Buy/Sell via `sellBuyButtonsVisibility` |
| Trading primitives `createOrderLine`/`createPositionLine` | draw-only | Use for visualising ladder rungs; they place nothing |

Safe-on flags for a read-only viewer: `supportPositions`, `supportPositionNetting` (lots as individual positions), `supportPLUpdate: true`, `supportExecutions`, `showNotificationsLog`, `showQuantityInsteadOfAmount: true`.

#### D. Order status state machine vs intent states (`INTENT_STATUS` in `extension/src/storage/store.js`)

| Intent state | TradingView `OrderStatus` | Note |
|---|---|---|
| `submitting` (written before the network call) | `Placing (4)` | "registered, not confirmed" matches write-ahead |
| `resting` (confirmed live on venue) | `Working (6)` | |
| `filled` | `Filled (2)` | |
| `cancelled` | `Canceled (1)` | |
| `failed` (definitive rejection, `definitelyNotSubmitted`) | `Rejected (5)` | only definitive refusals; ambiguous ones are never `failed` |
| `unknown` (submitted but not found on venue; needs human review; never auto-retried) | none | TradingView assumes every request resolves in 10 s; map to `Placing` + warning `message` (section B) or omit and let timeout toast show. Never map to `Rejected` or `Canceled` (would invite a re-click) |
| (not used) | `Inactive (3)` | The ladder creates exit intents after the entry fills, so no waiting-child state is needed. A bracket child waiting for a parent is the only `Inactive` use in the docs |

Transition parity: TradingView forbids final-to-transitional; the engine does the same except `unknown` which is transitional and can only be left through `resolveIntent` (human) or a later reconcile that finds the order. Partial fills: no TradingView status; keep `resting` and report `filledQty`/`avgPrice`.

#### E. P&L: TradingView vs the repo's paired-lot / FIFO (`extension/src/core/pnl.js`)

| Topic | TradingView | Repo |
|---|---|---|
| Entry basis | One `avgPrice` per symbol (weighted average); library draws the line and derives Ticks/% P&L from it | Lots tracked individually; default mode PAIRED: a sell closes the lots named in `closesLots`; FIFO (`{ linkage: false }`) only for tax-style export and old fills without linkage |
| Realized P&L | No field; only `pl`/`unrealizedPl*` on open positions, plus executions | `matchFifo` returns `roundTrips`, `openLots`, `realizedGrossUsd`, `realizedFeeUsd`, `realizedNetUsd`, `unmatchedSellQty`; fees mandatory per fill, carry cost passed explicitly |
| Money mode | Shows your `pl` as given | Feed `plUpdate` from `pnl.js` net-of-fee figures; keep `supportPLUpdate: true` |
| Ticks / % mode | Library computes `((cur - avg) * sign) / tickSize` and `((cur - avg)/avg) * 100 * sign` from `avgPrice`, ignoring fees and ignoring which lot was sold | Will disagree with paired-lot residual when an upper rung exits before a lower one; use Money mode only, or compute `avgPrice` from the residual open lots so the displayed basis matches |
| Netting | `supportPositionNetting`: individual lots plus a net position | Map each open lot to an `IndividualPosition` (`id`, `date`, `price`, `qty`, `side`); net `Position.avgPrice` = quantity-weighted mean of the residual open lots (formula 8) |
| FIFO close flag | `requiresFIFOCloseIndividualPositions` | Keep `false`: paired attribution is deliberate (strict FIFO re-points a lot's exit one rung too low, per the file header) |
| Daily-loss rail | n/a | `risk.js` `dailyLossLimitUsd` reads realized P&L from the same paired pass; a TradingView-side P&L number must never feed the rail |

#### F. Recommendation

Build a read-only, dry-run broker adapter first.

1. Implement only the read surface: `connectionStatus`, `accountsMetainfo`, `currentAccount`, `accountManagerInfo` (Orders and Positions pages plus summary fields for equity, realized net, daily loss used), `orders`, `positions`, `individualPositions` (lots), `executions`, `symbolInfo` (`qty.step`/`minTick` from the venue, `pipValue` from venue data and non-zero), `isTradable` returning `{ tradable: false, reason: "read-only adapter" }`.
2. Flags: all write-capable flags in section C off; `supportOrdersHistory: false`; `chartContextMenuActions` returns `[]`; hide Buy/Sell and the order panel.
3. Push updates only after reconcile (section B), id = `intentKey`, `unknown` shown as `Placing` with a warning message.
4. Use trading primitives (`createOrderLine`) to draw ladder rungs and the `risk.js` caps as display only.
5. Only after that, add `previewOrder` (pure `risk.evaluate`) and a single new registry command for manual orders, still gated by dry-run default, kill switch, `admitBatch`, and the write-ahead intent journal. Keep `cancelOrder` on the existing command; leave modify, close, reverse, brackets, leverage unimplemented.

Gaps: the docs give no formula for Order Ticket risk or margin-meter share; `IBrokerWithoutRealtime` and host `setButtonDropdownActions` are absent from the supplied d.ts; `Placing` transitions are inferred; no worked `Rejected` example.

## TradingView library: product, setup, versions

Source bundle: `tradingview/charting-library-context.txt` (66,434 lines, documents version **33.0.0**, header L1-12, answering prompt L66393-66434). Index files: `llms.txt` and `docs_map.md`, both "Last updated: 2026-10-13 19:27:53 UTC" (docs_map). Latest library version in the bundle: **33.0.0, dated Tue Oct 13 2026** (ctx L48383-48443).

### 1. Product comparison

Capabilities and licence terms exactly as the docs state them. Where the docs are silent the cell says "not documented".

| Aspect | Lightweight Charts(TM) | Advanced Charts | Trading Platform | Widgets |
|---|---|---|---|---|
| What it is | Free, open-source, client-side library, 45 KB (ctx L47984-48031) | Standalone client-side charting; you host the files and connect your data (ctx L47661-47823, L50345-50432) | Everything in Advanced Charts plus trading; "standalone product that is licensed to brokers" (ctx L50345-50432) | Free standalone apps, copy-paste embed code, hosted on TradingView servers, show TradingView data (ctx L47984-48031) |
| How data arrives | You push data directly, no requests (ctx L47984-48031) | Library requests data from your Datafeed API or UDF server (ctx L47984-48031) | Same as Advanced Charts, plus quotes/depth/news feeds (ctx L47824-47983) | TradingView data only; you cannot connect your own (ctx L47984-48031) |
| Market data included | No; supply your own or a third party (ctx L47984-48031) | No (ctx L47661-47823 "Data source: you must provide your own") | No (same page) | Yes, TradingView's |
| Built-in indicators | None; implement your own (a Moving Average example is linked) | 100+; custom indicators in JavaScript | Same as Advanced Charts | Not documented (fewer customization options) |
| Pine Script | n/a | Not supported; use JavaScript custom indicators (ctx L50345-50432) | Not supported | n/a |
| Drawings / chart types | not documented | 110+ drawing tools; 14+ chart types | Same, plus exclusive Renko, Kagi, Point-and-Figure, Line Break, Session Volume Profile (v33) | not documented |
| Trading UI | none | none; `createOrderLine`, `createPositionLine`, `createExecutionShape` removed from Advanced Charts in v29.0.0 (ctx L49230-49313) | Multi-chart layouts, trading from chart + Account Manager, Watchlist/News/Details widgets, Advanced Order Ticket, Depth of Market (ctx L47661-47823) | none |
| Extras only in widgets | | | | Heatmaps, Hot lists, Screeners (not supported in the libraries) |
| Hosting | You bundle it | Your server must host the library files (ctx L47661-47823) | Same | TradingView hosts |
| Who may use it | Anyone (open source) | Free "provided that the TradingView attribution remains visible and the implementation environment is public (not for private use or behind a paywall)" (ctx L47661-47823); licence agreement: "public websites only" (ctx L38895) | Brokers; has "its own licensing fees" (amounts not documented) (ctx L50345-50432) | Anyone, free |
| How to get it | Public | Submit the access request form on the product landing page; on approval you get a GitHub invitation to a private repo (ctx L48032-48297) | Same flow, separate Trading Platform landing page/repo | Copy code |
| May it sit in a public GitHub repo? | Yes (open source) | **No**: "not redistributable. It is prohibited to use any part of the library in public repositories" (ctx L48032-48297, L48298-48366) | **No**, same rule | n/a |
| Where to download | Public | Only the official TradingView repos linked in the docs; third-party copies "strictly prohibited and may lead to legal consequences" (ctx L48032-48297) | Same | n/a |
| Logo | not documented | Visibility "depends on the terms of your license agreement"; ask your account manager (ctx L46057) | Same | not documented |
| Source edits | not documented | Altering library source is "strictly prohibited by the legal agreement you signed"; undocumented features may change without notice (ctx L50271-50344) | Same | n/a |
| User data / cookies | n/a | TradingView collects none; library sets no cookies (ctx L50345-50432) | Same | not documented |

Not supported in Advanced Charts or Trading Platform (client-server features of tradingview.com): Pine Script, Alerts, Strategy Tester, Bar Replay; Screener, Technical Analysis (Symbol Details) widget, Hot lists, Calendars, Heatmap; TradingView data, Range Bars, Chart Patterns; Chats (ctx L50345-50432).

Migration map, Lightweight Charts to Advanced Charts (ctx L47984-48031):

| Task | Lightweight Charts | Advanced Charts |
|---|---|---|
| Create chart | `createChart` | Widget Constructor |
| Add series of a style | `addSeries` | `overrides` property of the Widget Constructor (series styles) |
| Pixel coordinate | `timeToCoordinate` | No equivalent; use `ITimeScaleApi` |
| Price line | `createPriceLine` | `createShape` or `createOrderLine` (Trading Platform only) |

Switching Advanced Charts to Trading Platform is covered by a separate "How to migrate" topic not in the read ranges (ctx L50345-50432 only links it).

### 2. Get started

**Access (ctx L48032-48297).** Libraries live in a private GitHub repository: `tradingview/charting_library` (Advanced Charts) and `tradingview/trading_platform` (Trading Platform). Submit the landing-page form, receive a GitHub invitation. Approval criteria and fee for Advanced Charts are not documented in the bundle.

**Install, direct download.** Clone or download the ZIP. Copy `charting_library/` (core files) and `datafeeds/` (sample datafeed) into your project (ctx L48032-48297).

**Install, NPM.** Needs an authenticated Git client and an SSH key on your GitHub account. Dependency form: `"charting_library": "git@github.com:tradingview/charting_library.git#semver:32.0.0"` (the doc example still shows 32.0.0 while the bundle documents 33.0.0; pin what you actually test). Files in `node_modules/charting_library/` are not bundled by your build, so a `postinstall` script copies them to a static folder: `"copy-files": "cp -R node_modules/charting_library/ public"` (ctx L48032-48297).

**Package structure (ctx L48032-48297).**

| Path | Purpose |
|---|---|
| `charting_library/` | All library files, "DO NOT EDIT" |
| `charting_library/bundles/` | Internal resources, a "black box" that may change without notice |
| `charting_library.js` | UMD module, backward compatibility |
| `charting_library.d.ts` | TypeScript definitions for the widget |
| `charting_library.cjs.js` | CommonJS module |
| `charting_library.esm.js` | Native JS module for imports |
| `charting_library.standalone.js` | IIFE module (used in the quick start) |
| `datafeed-api.d.ts` | TypeScript definitions for the datafeed |
| `package.json` | package manifest |
| `datafeeds/udf/` | Sample UDF-compatible datafeed wrapper; editable; implements the Datafeed API |
| `index.html` | Basic example |
| `mobile_black.html`, `mobile_white.html` | Mobile customization examples (dark, light) |
| `test.html` | Comprehensive customization example |

**Minimal setup (ctx L48032-48297).**
1. Page head: `<script src="charting_library/charting_library.standalone.js">` and `<script src="datafeeds/udf/dist/bundle.js">`; body: `<div id="chartContainer">`.
2. `new TradingView.widget({ container: 'chartContainer', locale: 'en', library_path: 'charting_library/', datafeed: new Datafeeds.UDFCompatibleDatafeed("https://demo-feed-data.tradingview.com"), symbol: 'AAPL', interval: '1D', fullscreen: true, debug: true })`.
3. Serve statically on port 9090: `python -m http.server 9090`, or `npm install http-server -g` then `http-server -p 9090`, or an NGINX `server { listen 9090; location / { root <abs path>; } }`. Open `http://localhost:9090`; AAPL should render.
4. Check version in the browser console: `TradingView.version()`.
5. `library_path` is the URL prefix where the static `charting_library/` files are served. Pages and bundles on different origins need Cross-Origin hosting (`configuration/Hosting-Library-Cross-Origin`, outside the read ranges).

Next steps the docs name: Connecting data, Widget Constructor, Framework integrations, UI elements, Customization, Broker integration (Broker API) (ctx L48032-48297).

**Online playgrounds (ctx L56143-56235).** Starter templates exist for CodePen and JSFiddle (Advanced Charts, Trading Platform, Themed Advanced Charts). Hosted bases: `https://charting-library.tradingview-widget.com` (Advanced Charts), `https://trading-terminal.tradingview-widget.com` (Trading Platform). They always serve the latest `master`; pin a version with a `/versions/<x.y.z>/` path in both the script URL and `library_path`. The doc example uses `/versions/28.4.0` in the script tag but `/versions/29.0.0` in `library_path`; the two must be identical. The demo storage for layouts/templates only accepts `localhost` and `tradingview.com` origins. `custom_css_url` is relative to `library_path`.

**Framework integrations (ctx L56236-56355).** Any JS framework works; examples live under `https://github.com/tradingview/charting-library-examples/tree/master/<dir>`:

| Framework | `<dir>` | Note |
|---|---|---|
| React + JavaScript | `react-javascript` | |
| React + TypeScript | `react-typescript` | |
| Angular | `angular` | |
| Vue.js 2 / 3 | `vuejs` / `vuejs3` | |
| Next.js | `nextjs-javascript` (up to v13) / `nextjs` (v13+) | |
| Nuxt.js | `nuxtjs` (up to 2.x) / `nuxtjs3` (3.x+) | |
| SvelteKit | `sveltekit` | |
| Solid.js | `solidjs-typescript` | |
| Ruby on Rails | `ruby-on-rails` | |
| React Native | `react-native` | WebView |
| Android WebView | `android` | native SDK not provided |
| iOS WKWebView (Swift) | `ios-swift` | native SDK not provided |

Framework notes from elsewhere in the bundle: static files must be copied out of `node_modules` (see NPM above); on teardown call `remove()`, unsubscribe all data subscriptions, drop references (ctx L56036-56142); v24.001 added simple SSR support so the library can be imported in a Node context, which helps Remix (ctx L50123-50156); v28.0.0 changed `const enum` to `enum` so Vite and other `isolatedModules` setups can import enums (ctx L49423-49537); v31.1.0 added a CSP `nonce` option (ctx L48736-48764).

**Mobile (ctx L47824-47983).** Responsive layout hides or shrinks: right widget bar (Watchlist, Details, News, Data window), time-scale Marks, Account Manager (moved behind a Broker button in the legend; disable that with the `broker_button` featureset). Touch and multi-touch are supported. Legend shows close and % change only; OHLC and indicator values appear in tracking mode (long tap, tap to exit). Trading Platform must implement `getQuotes` and `subscribeQuotes` or the legend shows NaN. % change uses intraday quotes, not the previous bar. Only one price scale. Featuresets: `show_zoom_and_move_buttons_on_touch`, `horz_touch_drag_scroll`, `vert_touch_drag_scroll`, `pinch_scale`. Gestures: single tap drags chart and scales; long press opens scale menu and crosshair mode; double tap on a line enters move mode. No native iOS/Android wrappers; the library is "fully supported and guaranteed" inside a WebView; you build the native-to-JS bridge (`evaluateJavascript` on Android, `evaluateJavaScript` on iOS). Examples: Android, iOS Swift, React Native; no Flutter example (a bridge article is linked). Android WebView must support ES6; minimum Android 5.0 (Lollipop).

**Update the library (ctx L48298-48366).**
1. Run `TradingView.version()` in the console.
2. Read the release notes for every version between yours and the target; watch **breaking changes**.
3. Download the latest `master` of the Advanced Charts or Trading Platform repo (older versions: find the commit and reset to it). Only official repos; not redistributable.
4. Unzip into a **new** folder, do not overwrite the working copy.
5. Test with `npx serve <PATH>`; confirm `TradingView.version()`.
6. Adopt new features; test everything, since earlier work "should be compatible" but must be verified.

### 3. Release notes digest (newest first)

Kinds: **B** breaking, **D** deprecation, **N** new API/feature, **F** notable fix. "(TP)" means Trading Platform only. Dates are as printed; "n/d" means no date in the bundle. Whole section is ctx L48367-50270; per-version ranges are in the first column.

| Version (ctx range) | Date | Kind | Item |
|---|---|---|---|
| 33.0.0 (L48383-48443) | Oct 13 2026 | B | String key names in shortcuts removed (deprecated in v30): `onShortcut` with `'ctrl+shift+/'` or `['ctrl','shift','/']` now throws; use numeric codes `['ctrl','shift',191]`; modifiers stay strings |
| | | B | `paneProperties.gridLinesMode` override replaced by `paneProperties.vertGridProperties.visible` and `paneProperties.horzGridProperties.visible` (default `true`); grid lines now dotted and less transparent unless you set `style`/`color` |
| | | B (TP) | `CustomFields` interface replaced by `WithExtraData` on `PlacedOrder`, `Position`, `IndividualPosition`, `Execution`: custom properties go in `extra`; Account Manager `dataFields` becomes `['extra','balance']` |
| | | N | `volume_profile` widget option (`max_total_rows`, `history_sessions`); `overlayScaleMargins` in custom-indicator metainfo (e.g. `{ top: 0.75, bottom: 0 }`); `setShortcutsEnabled`; `scalesProperties.axisHoverHighlightColor`; `charting-library-datafeed` agent skill |
| | | N (TP) | Session Volume Profile (`SeriesType.SVP` = 20, `mainSeriesProperties.svpStyle`; needs volume, intraday and `1D`, may request finer `getBars`); featuresets `dom_raw_volume_values`, `always_require_order_confirmation` (disables one-click trading, also via saved settings or `silentOrdersPlacement`) |
| | | F | `nextTime` in **milliseconds** now honored (seconds still work with a console warning; UDF adapter converts for you); datafeed `supported_resolutions` honored with `workers` enabled; `changeTheme` no longer discards `overrides` |
| 32.2.0 (L48444-48528) | Sep 11 2026 | N | `getEntityValues` on the chart API (read series/indicator values any time); session-highlight props typed in `ChartPropertiesOverrides` (`backgrounds.preMarket`, `backgrounds.postMarket`, `vertlines.sessBreaks`) |
| | | N (TP) | `setVisible`/`getVisible` on order, position, execution adapters; ids of orders/positions/executions must be strings (clearer error now) |
| | | F | Bar countdown follows the symbol `session` close; stored chart colors no longer replaced by default theme at start |
| 32.1.0 (L48529-48631) | Aug 17 2026 | N | `pin_bar_mark_tooltips_on_click` featureset; custom mark tooltips (`customTooltip`, `custom_js_urls`, TP); `show_buy_sell_buttons_on_unsupported_resolution` (TP); `tradedSourcesVisibility` on the Trading Host (TP) |
| | | F | Market status uses synced `getServerTime` when implemented; `load` with undefined state no longer blanks series; VWAP anchors use trading day; unfinished drawings excluded from `save` |
| 32.0.0 (L48632-48701) | Jul 01 2026 | B | `dataReady()`, `setChartType()`, `saveChartToServer()` called without callbacks return Promises (`Promise<boolean>`, `Promise<void>`, `Promise<void>` rejecting with `SaveChartError`) |
| | | B | Drawing tool names changed in `custom_translate_function` and `drawings_access` (`"trendline"`, `"Trendline"`); Anchored Text tool removed (use Text with Anchor) |
| | | D | Callback overloads of `chartReady`, `save`, `getSavedCharts`, `saveChartToServer`, `removeChartFromServer`, `showNoticeDialog`, `showConfirmDialog`, `dataReady`, `setChartType`, and `widget.setSymbol(symbol, interval, callback)` deprecated; "will be removed in a future major release" |
| | | N | `workers.enabled` (indicator calculation in a worker, falls back to main thread); countdown for D/W/M bars; `keep_selected_group_on_tool_creation`; (TP) `supportUnpairedExitLevels` |
| | | docs | Datafeed tutorial rewritten on the **Binance REST API** (was CryptoCompare), plus a Trading Platform extension (quotes, DOM, news, save/load); margin meter guide (`supportMargin`, `subscribeMarginAvailable`, `marginRate`) |
| 31.2.0 (L48702-48735) | May 05 2026 | N | `group` on custom-indicator input metainfo; (TP) optional `listId` on watchlist `createList` |
| | | F | True Strength Index scaled to -100..+100 (was -1..+1) |
| 31.1.0 (L48736-48764) | Apr 08 2026 | N | `nonce` widget option for CSP (style-src still needs `'unsafe-inline'`); globally shared drawings; `saveLineToolsAndGroups(context)` gets `sharingMode`, `symbol`, `requestId` |
| 31.0.0 (L48765-48829) | Mar 06 2026 | N | Table view; (TP) multiple exit levels (`supportMultipleExitLevels`, `exitLevels`, `exitLevelId` on `BracketOrder`), `supportCryptoExchange` + `supportCryptoExchangeOrderTicket`, `supportAdaptiveLayout` |
| | | F | Symbols with no sessions for a whole week (holidays) can request data; Risk/Reward P&L uses `lotSize` and `pointValue` |
| 30.3.0 (L48830-48847) | Jan 21 2026 | N | `IChartWidgetApi.applyOverrides` (per chart); `legend_bar_change_colors_based_on_value` |
| 30.2.0 (L48848-48890) | Dec 22 2025 | N | Optional Datafeed method `searchSymbolsPaginated` (replaces `searchSymbols` when present); overlay updates behind main series; (TP) DOM dynamic mode restored (`static_dom` for static) |
| 30.1.0 (L48891-48946) | Nov 10 2025 | N | `getBars` may return bars and `noData: true` together; `getVisibleBarsRange`; `always_show_study_symbol_input_values_in_legend` |
| 30.0.0 (L48947-49041) | Sep 22 2025 | B | UDF properties `exchange-listed`, `exchange-traded` deprecated for `exchange_listed_name` (removal from v31); `inactivity_gaps` featureset replaces `intraday_inactivity_gaps` (now DWM too); scroll/resize no longer undoable; `showLabel` override ignored for line tools; iOS below 15 dropped (text says "above 16", inconsistent) |
| | | B (TP) | `supportOrdersHistory` default `true`: implement `ordersHistory` or set `false` |
| | | D | Letters/printable characters in shortcuts deprecated |
| | | N | Watermark API: `tickerVisibility`, `intervalVisibility`, `descriptionVisibility`; `chart_theme_changed` event; `setVisibleRange` returns a rejectable Promise; (TP) `applyTradingCustomization`, `canBeClosed`, `updateTime` |
| 29.6.0 / 29.5.0 (L49042-49070) | Aug 13 / Aug 05 2025 | N | `label` on `StudyOrDrawingAddedToChartEventParams`; (TP) `setLayoutSizes`; fix: `setMinimumAdditionalDepth` ignored by custom studies |
| 29.4.0 (L49071-49125) | Jun 25 2025 | N | (TP) multiple tick resolutions (no multipliers: datafeed must provide each, e.g. `10T`); `searchSource` arg on `searchSymbols`; snapshots rely solely on `snapshot_url` (you host the snapshot server); data-request throttling while scrolling; `intraday_inactivity_gaps` |
| 29.3.0 (L49126-49156) | May 08 2025 | N | HLC bars chart style; price-scale details in context-menu event |
| 29.2.0 (L49157-49199) | Apr 08 2025 | N | `resetCache` (clear all cached symbol/resolution data, then `resetData`); Trading Host `ordersFullUpdate`, `positionsFullUpdate`, `individualPositionsFullUpdate` |
| 29.1.0 (L49200-49229) | Mar 07 2025 | N | `onShortcut` can override default shortcuts; (TP) `pre_post_market_price_line` needs `rtc` in quotes |
| 29.0.0 (L49230-49313) | Feb 05 2025 | B | `createOrderLine`, `createPositionLine`, `createExecutionShape` removed from Advanced Charts (TP keeps them, now Promise-returning); `createShape`, `createMultipointShape`, `createAnchoredShape` return Promises resolving to the drawing id and reject on failure instead of returning `null` |
| | | B | Broker API: `IBrokerWithoutRealtime` merged into `IBrokerTerminal`; `subscribeDOM`/`unsubscribeDOM` removed (use `subscribeDepth`/`unsubscribeDepth`); `getPositionDialogOptions` async and takes a symbol; anchored note drawing removed; note renamed pin; MACD smoothing inputs; Volume Profile default colors |
| | | N (TP) | `trading_customization` supports `brokerOrder` and `brokerPosition` |
| 28.5.0 (L49314-49333) | Dec 18 2024 | N | `baselinePosition` for column series; "Another symbol" input on Moving Average Double |
| 28.4.0 (L49334-49361) | Nov 28 2024 | N | `includeOHLCValuesForSingleValuePlots` on data export; quote-event logging in debug mode |
| 28.3.0 (L49362-49376) | Oct 24 2024 | N | (TP) `DatafeedQuoteValues.short_name` shown in Watchlist/Details; `prefer_quote_short_name` featureset reverts |
| 28.2.0 (L49377-49392) | Oct 01 2024 | N | `build_seconds_from_ticks` symbol flag (needs `has_seconds`, `has_ticks`; `seconds_multipliers` empty or datafeed-provided); `timeframe_interval` event; Rank Correlation Index |
| 28.1.0 (L49393-49422) | Sep 04 2024 | D | `activateBottomWidget` deprecated for `setAccountManagerVisibilityMode`/`getAccountManagerVisibilityMode`; `iframe_loading_same_origin` featureset |
| 28.0.0 (L49423-49537) | Aug 14 2024 | B | `LibrarySymbolInfo.full_name` removed: library now sends `name` or `ticker` to `getBars`, `getQuotes`, `subscribeQuotes` (`prefer_symbol_name_over_fullname` reverts the UI) |
| | | B | `ErrorCallback` renamed `DatafeedErrorCallback`; `selectedCurrency` returns `null` not `"Mixed"`; Enter in Symbol Search picks the top result (`allow_arbitrary_symbol_search_input` restores old); `custom_translate_function` signature changed; DOM static mode (reverted in 30.2.0); Symbol Info dialog renamed Security Info |
| | | D | `createOrderLine`, `createPositionLine`, `createExecutionShape` deprecated for Advanced Charts; `brokerConfig` option deprecated for `broker_config` |
| | | B (TP) | `cancelOrders` optional; `calculatePLUsingLast` flag removed |
| | | N | Custom themes API; Volume Candles; `library_custom_fields` on `LibrarySymbolInfo`; `debug_broker` option; `symbolExt` returns `ticker`; Trading Host `getOrderTicketSetting`/`setOrderTicketSetting`/`connectionStatusUpdate` (TP) |
| 27.006 (L49538-49545) | May 21 2024 | F | Quotes are resolved with `ticker` (falls back to `name`) |
| 27.005-27.001 (L49546-49644) | May 07 - Feb 2 2024 | N/B | `study_event` types `widgetbar_visibility_changed` and `create`; `time` in `CrossHairMovedEventParams` back to UTC and new `userTime` (27.004); `resetLayoutSizes`, `unloadUnusedCharts` (TP); `hideWhenPlotsHidden` input option |
| 27 (L49645-49729) | Jan 17 2024 | B | Custom-study `text` style moved to `metainfo.styles.[plot id].text`; Ichimoku and Stochastic inputs renamed; `show_context_menu_in_crosshair_if_only_one_item` removed |
| | | B (TP) | Trade renamed IndividualPosition throughout: flags `supportTrades` to `supportPositionNetting`, `supportTradeBrackets` to `supportIndividualPositionBrackets`, `supportCloseTrade` to `supportCloseIndividualPosition`, `supportPartialCloseTrade` to `supportPartialCloseIndividualPosition`, `requiresFIFOCloseTrades` to `requiresFIFOCloseIndividualPositions`; `tradeUpdate` to `individualPositionUpdate`, `tradePartialUpdate` to `individualPositionPartialUpdate`, `tradePLUpdate` to `individualPositionPLUpdate`; `trades` to `individualPositions`; `closeTrade` to `closeIndividualPosition`; `editTradeBrackets` to `editIndividualPositionBrackets`; `tradesColumns` to `individualPositionColumns`; `positionDialogOptions` removed (use `getPositionDialogOptions`) |
| 26.004-26.001 (L49730-49831) | Nov 16 - Aug 08 2023 | N | Broker quantity getter/setter `getQty`, `setQty`, `subscribeSuggestedQtyChange`; VWAP `source` + `anchor`; keyboard navigation (`accessibility` featureset, Alt/Opt+Z); crosshair event carries series/study values; `onHoveredSourceChanged`; optional `variable_tick_size`; order-line `onMoving` |
| 26 (L49832-49863) | Jul 18 2023 | D | `customFormatters` (use `custom_formatters`); `brokerFactory` (use `broker_factory`) |
| 25.002-25.001 (L49864-49934) | Jul 12 / Jun 26 2023 | B | `price_sources` moved from datafeed configuration to symbol info |
| | | N | Symbol/exchange logos (`show_symbol_logos`, `show_exchange_logos`, `exchange_logo` from `resolveSymbol`); `marketStatus`; Watermark API; Custom Symbol Status API; `setTimeFrame`; anchored VWAP; first `getBars` after `resetData` no longer has countback 0 |
| 25 (L49935-49992) | May 22 2023 | B | Save/load adapter gains chart-template methods; `resetData` now requests only the visible range |
| 24.004-24.001 (L49993-50156) | Apr 24 - n/d 2023 | B/D | `SeriesStyle` renamed `SeriesType` (types only); `marginRate` deprecated for `supportLeverageButton`/`supportLeverage`; custom timezones; image marks; simple SSR support; `clearUndoHistory`; `symbol_search_complete` takes a result object and returns a friendly name |
| 24 (L50157-50187) | n/d | B | `preset` widget option removed; Mark tooltips no longer accept HTML; (TP) column description `id` required, `property` removed (use `dataFields`) |
| 23 (L50188-50191) | n/d | B | Average close price line hidden by default (`show_average_close_price_line_and_label`) |
| 22 (L50192-50230) | n/d | B/D | `getTimezone`/`setTimezone` deprecated (use `getTimezoneApi`); `snapshot_url` POST is `multipart/form-data` field `preparedImage` PNG; `createStudy` inputs become a named object (arrays still accepted); Moving Average first input is now the symbol so existing calls need `['', 9]`; `scrollPosition`/`defaultScrollPosition` deprecated for `rightOffset`/`defaultRightOffset`; `rest.html` and `datafeeds/rest` removed; (TP) `suggestedQty` removed from Trading Host, `dome_widget` deprecated for `dom_widget` |
| 21 (L50231-50270) | n/d | B | `holidays` renamed `session_holidays`; symbol type `bitcoin` renamed `crypto`; `show_dialog_on_snapshot_ready` removed; `changeTheme` returns a Promise; (TP) `placeOrder` returns `Promise<PlaceOrderResult>`, `supportExecutions` flag added, `supportReducePosition` removed, `supportModifyOrder` deprecated for `supportModifyOrderPrice`/`supportEditAmount`/`supportModifyBrackets` |

### 4. Best practices, FAQ, troubleshooting

Best practices (ctx L50271-50344):
- Keep chats, symbol lists, ads and similar outside the library; connect them through the API.
- Pick Datafeed API (JavaScript) or UDF (server in UDF format) deliberately; use WebSockets for fast streaming.
- Most library problems come from wrong data; give the right amount of data, and marks must match the requested range.
- Smallest meaningful chart size is 500x500 px; hide UI elements for smaller charts.
- Set `debug: true` in development, off in production for speed.
- First step on any issue: update the library, then enable debug mode and read Troubleshooting.
- Do not use undocumented features; they change without warning. Altering source is forbidden by the agreement.
- Do not use the demo datafeed in production (unstable, cannot take load).
- Serve over HTTP/2+ and TLS 1.3+; gzip or Brotli the library HTML; drop unused locales.
- Cloudflare Rocket Loader is not supported; avoid it.
- Give `charting_library.js` the minimum cache expiry: all other files carry hashes in their names, so a cached `charting_library.js` points at files that no longer exist after an update.

FAQ (ctx L50345-50432):
- Widgets vs Advanced Charts vs Trading Platform? Widgets use TradingView data and are pasted iframes; Advanced Charts is a free self-hosted chart on your data; Trading Platform is licensed to brokers with fees.
- Why does it differ from tradingview.com? Client-side only (no server features) and different release cadence.
- How do I connect data and add symbols? Connecting data, Datafeed API, UDF adapter, "Datafeed: common issues"; inspect the Demo Chart's network calls filtered by `demo-feed`.
- Data missing or wrong? Usually Symbology config or misaligned timestamps; enable debug mode.
- Which time unit? Unix timestamps in **seconds** unless stated; Datafeed bar times and `nextTime` are **milliseconds** (v33 note: `nextTime` in ms is now honored).
- Pine Script? Not supported; write JavaScript custom indicators.
- Does TradingView see user data or does the library set cookies? No to both.
- Where do I ask more? GitHub Issues (restricted access).

Troubleshooting (ctx L56036-56142, mobile FAQ ctx L47824-47983):
- Any problem → enable debug mode first; API-specific guides: "Common Datafeed API issues", "Common Broker API issues".
- Memory grows forever → call `remove()`, unsubscribe all data subscriptions, drop references to the widget/API.
- Memory grows with live data → throttle or batch real-time updates before sending.
- Still leaking → reproduce on an isolated blank page; if it persists, take a heap snapshot (DevTools Memory tab) and file a GitHub issue with it.
- CSP errors mentioning `blob` or `img-src` (screenshots, logos, emojis blocked) → allow the sources in your CSP; if impossible enable `iframe_loading_compatibility_mode` (uses `about:blank` + `document.write`). Nonce CSP: use the `nonce` option (v31.1.0), `style-src 'unsafe-inline'` is still required.
- Bug report must include: description, error messages, repro steps, library version, full debug logs, the symbol.
- Android sample shows a white screen → WebView lacks ES6; update WebView; minimum Android 5.0.
- Debug WebViews → Chrome DevTools remote debugging (Android), Safari Web Inspector (iOS).
- Native to JS data → `evaluateJavascript` (Android), `evaluateJavaScript` (iOS).
- Open links in the system browser on Android → `shouldOverrideUrlLoading` plus an `Intent` with `ACTION_VIEW`.
- Truncated price/time scales → only when emulating mobile in Chrome desktop; fine on real devices.
- Cannot type `-` in Android WebView number inputs → known Chromium issue; use a third-party keyboard.
- NaN in the mobile legend (Trading Platform) → implement `getQuotes` and `subscribeQuotes`.
- Playground chart fails to load → the host site's origin blocks CORS; use CodePen/JSFiddle templates or Cross-Origin hosting.
- Static files (`.csv`, `.txt`, `.xlsx`) cannot be read directly; the library fetches dynamically from a server (ctx L38895).

How-to guides (ctx L58068-58122): custom indicator (SMA plus Smoothing Line), custom page in Account Manager, custom top-toolbar button, snapshots server (Node.js), custom mark tooltips. Tutorials (ctx L62756-62806): Connect data (Datafeed API plus real-time streaming), Enable trading (Broker API), Enable debug mode. Interactive examples: `https://codepen.io/tradingview` (ctx L62807-62853).

### 5. Glossary (27 terms, ctx L50433-50571)

| Term | Meaning |
|---|---|
| Bracket order | Order bracketed by opposing stop-loss and take-profit orders to cap loss and lock profit |
| Execution | Completion of a buy or sell: buyer matched with seller, ownership transferred |
| Individual position | One singular holding in an instrument |
| Limit order | Buy or sell at the limit price or better; price guaranteed, fill not |
| Limit price | Max a buyer pays or min a seller accepts |
| Market order | Buy or sell at current market price; fill guaranteed, price not |
| Net position | Total open long minus total open short at a moment |
| Order | Request to buy or sell at a price and quantity; has limit price, stop price, duration; statuses include canceled, filled, placing, rejected |
| Order duration | How long an order stays active |
| Pip | Minimum price move for Forex symbols |
| Position | Amount of an instrument held |
| Position netting | Aggregating several individual positions in one symbol into one net position |
| Quotes | Real-time price info: latest bid/ask, open/close, change, other market data |
| Stop-loss order | Order that closes a position at a set price when it moves against you |
| Stop order | Order to buy or sell at market once a level is reached |
| Stop price | Trigger price at which an order becomes market or limit |
| Take-profit order | Limit order that closes a position at a set price to lock profit |
| Tick | Minimum price movement |
| Bar spacing | Pixels between data points; smaller shows more data |
| Datafeed | Middleware that requests data from a server and hands it to the library |
| Date range | Time period currently visible on the canvas; changes when the user scales |
| Featureset | Toggle that enables or disables a feature |
| Pane | Chart area where a series or indicator is shown |
| Plot | Line or area representing indicator values |
| Series | Collection of data points for a metric over time; style controls the look |
| Source symbol | Symbol an indicator takes its data from to compute its own values |
| Spread operators | Operators comparing an instrument with another instrument or a number; enabled in Search Symbol and Compare Symbol dialogs |

### 6. TradingView "Build with AI", "Agent skills", "Create AI library assistant"

**What TradingView publishes (ctx L35989-36061, L35908-35988).**

| Asset | What it is |
|---|---|
| `llms.txt` | Plain-text list of all documentation pages at the docs root (llmstxt.org convention); this copy is `tradingview/llms.txt` (234 lines), grouped as Overview, Build with AI, Configuration, Connecting data, UI elements, ... |
| `docs_map.md` | Same list plus each page's headings (nested bullets); `##`/`###` are doc groups, `- [title](url.md)` is a page; local copy 1,561 lines; ends with "Type Definitions" and "Full Context" sections (docs_map L1553-1561) |
| Per-page Markdown | Every page also at its URL plus `.md`; "Copy as Markdown" and "View as Markdown" controls under each title (added v32.1.0) |
| `.d.ts` hosting | `charting_library.d.ts`, `datafeed-api.d.ts`, `broker-api.d.ts` (Trading Platform only) hosted next to the docs, always the latest version; local copies sit in the same folder (1.17 MB, 67 KB, 133 KB) |
| `charting-library-context.txt` | Single-file bundle of all docs plus type definitions (see below) |
| Agent skill `charting-library-datafeed` | The only skill the docs name; shipped in the library repo (v33.0.0) |

**`charting-library-datafeed` skill (ctx L35908-35988).** Purpose: connect market data to the library; covers the Datafeed API, UDF adapter, symbology, trading sessions, resolutions, real-time updates and reconnects, quotes for Trading Platform, "Datafeed: common issues", saving/loading, customization precedence. Behavior rule: answer a datafeed question one of three ways: (1) name the existing feature, featureset or property; (2) state that the library does not support it and give a workaround; (3) find the broken datafeed rule, fix it, prove the fix with the checker. Checker: `scripts/check-datafeed.mjs` (Node 18+, no dependencies) calls your datafeed like the library does and reports each violation with the rule, the visible symptom, and the doc page:
```
node .agents/skills/charting-library-datafeed/scripts/check-datafeed.mjs --datafeed ./src/datafeed.js --symbol AAPL
node .agents/skills/charting-library-datafeed/scripts/check-datafeed.mjs --udf https://your-server.example.com --symbol AAPL
```
Browser-only datafeeds: wrap with `createCheckedDatafeed(datafeed)` from `scripts/datafeed-check/index.mjs`; it logs violations to the console without changing behavior; `--help` lists options. Install: `npx skills add tradingview/charting_library --skill charting-library-datafeed` (use `tradingview/trading_platform` for Trading Platform), or copy the folder to `.claude/skills/` or `.agents/skills/`. The skill lives in the **restricted** repo, is not in the npm package, and must be updated with the library.

**How `charting-library-context.txt` is meant to be used (ctx L36062-36130, header L1-12, prompt L66393-66434).** Structure: "Part 1: Documentation Content" (type definitions plus Markdown docs, each page opened by a `URL:` line) and "Part 2: Answering Guidelines (Prompt)". Upload it to an AI tool with a context window of one million tokens or more (file is several hundred thousand tokens; locally 2.9 MB). It is always for the latest version, so answers may not fit older installs. Prompt rules: (1) base all library facts only on the file; (2) if absent, answer that the information is not available in the provided documentation for version 33.0.0; (3) never invent APIs; (4) cite full absolute doc URLs; (5) else give a search link `https://www.tradingview.com/charting-library-docs/search/?q=<terms joined by +>`; (6) complete, commented code blocks with language; (7) answer directly or ask for clarification; (8) remind that it describes 33.0.0. Tips from the page: be specific, new chat per topic, newest model, low temperature, explicitly ask for code, verify via the linked docs. Disclaimers: docs site is the source of truth; you must test AI-generated code; models can hallucinate; no TradingView support for third-party LLM tools.

Working with the local bundle without loading it: `grep -n '^URL: ' charting-library-context.txt` lists page starts; `sed -n 'A,Bp'` the page. Anchors: Agent skills L35908; AI-friendly docs L35989; Build with AI L36032; Create AI assistant L36062; Introduction L47661; Mobile L47824; Product comparison L47984; Get started L48032; Update library L48298; Release notes L48367; Best practices L50271; FAQ L50345; Glossary L50433; Troubleshooting L56036; Online playgrounds L56143; Framework integrations L56236; How-to guides L58068; Tutorials L62756.

## Agent Skills format (agentskills.io)

Source `agentskillsio-llms-full.txt` (1,835 lines): Specification (agentskills L1563-1833), Overview (L347-406), Best practices (L408-681), Evaluating (L684-980), Optimizing descriptions (L983-1175), Quickstart (L1178-1257), Using scripts (L1260-1560), Adding skills support (L1-335), Client showcase (L337-345, list not included in the dump). The format was developed by Anthropic and released as an open standard (agentskills L391-395).

### 7. The SKILL.md specification

**Directory layout (agentskills L1568-1579).**

| Path | Status | Content |
|---|---|---|
| `skill-name/` | required | Directory; name must equal the `name` field |
| `SKILL.md` | required (exact filename) | YAML frontmatter + Markdown body |
| `scripts/` | optional | Executable code: self-contained or documented dependencies, helpful errors, graceful edge cases; language set depends on the client (Python, Bash, JavaScript common) (L1774-1782) |
| `references/` | optional | Docs loaded on demand: `REFERENCE.md` (technical detail), `FORMS.md` (templates/structured data), domain files like `finance.md`; keep each focused (L1784-1792) |
| `assets/` | optional | Templates, images, data files (lookup tables, schemas) (L1794-1800) |
| anything else | allowed | "Any additional files or directories"; these conventions are recommendations (L1772) |

**Frontmatter fields: 6 (agentskills L1587-1594, L1620-1756).**

| Field | Required | Constraints |
|---|---|---|
| `name` | yes | 1-64 chars; unicode lowercase alphanumerics (`a-z`, `0-9`) and `-` only; must not start or end with `-`; no consecutive `--`; must match the parent directory name. Valid: `pdf-processing`, `data-analysis`, `code-review`. Invalid: `PDF-Processing`, `-pdf`, `pdf--processing` |
| `description` | yes | 1-1024 chars, non-empty; say what it does and when to use it; include keywords that help agents match tasks. Good: "Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction." Poor: "Helps with PDFs." |
| `license` | no | License name or the name of a bundled license file; keep short (example: `Proprietary. LICENSE.txt has complete terms`) |
| `compatibility` | no | 1-500 chars if present; only for real environment needs (intended product, system packages, network access). Examples: `Designed for Claude Code (or similar products)`; `Requires git, docker, jq, and access to the internet`; `Requires Python 3.14+ and uv`. "Most skills do not need" it |
| `metadata` | no | Map from string keys to string values for client-specific extras; use reasonably unique key names. Example: `author: example-org`, `version: "1.0"` |
| `allowed-tools` | no | Space-separated string of pre-approved tools; **experimental**, support varies. Example: `Bash(git:*) Bash(jq:*) Read` |

Minimal frontmatter: `name` + `description`. The docs name no other top-level frontmatter fields. Whether `skills-ref validate` rejects unknown top-level keys is not stated (gap).

**Body (L1758-1768).** No format restrictions. Recommended: step-by-step instructions, input/output examples, common edge cases. The whole file loads on activation, so split long content into referenced files.

**Progressive disclosure and budgets (L1802-1823, L21-25, L379-385).**

| Tier | Loaded | Budget |
|---|---|---|
| 1 Metadata / catalog | `name` + `description` of every skill at startup | about 100 tokens per skill (spec); 50-100 tokens (host guide) |
| 2 Instructions | full `SKILL.md` body at activation | under 5,000 tokens recommended; keep `SKILL.md` under 500 lines |
| 3 Resources | `scripts/`, `references/`, `assets/` files, only when the instructions call for them | varies |

File references: relative paths from the skill root (`references/REFERENCE.md`, `scripts/extract.py`); keep them **one level deep** from `SKILL.md`, avoid nested chains (L1812-1823). Script paths in code blocks are relative to the skill root, because the agent runs commands from there (L1379-1381). Pin tool versions (`npx eslint@9.0.0`) and state prerequisites; use `compatibility` for runtime requirements (L1346-1347).

**Validation tooling (L1825-1833).** `skills-ref validate ./my-skill` from the `skills-ref` reference library (`github.com/agentskills/agentskills/tree/main/skills-ref`); "checks that your SKILL.md frontmatter is valid and follows all naming conventions." Skill-authoring helper: the `skill-creator` skill (github.com/anthropics/skills) automates evals, grading, benchmarking, and description optimization (L980, L1146).

**Quickstart sample (L1195-1216).** `.agents/skills/roll-dice/SKILL.md` with `name: roll-dice`, a `description:` that includes "Use when asked to ...", and a short body; the VS Code `/skills` command lists installed skills.

**Script design for agents (L1487-1560).** No interactive prompts (hard requirement; accept flags, env vars, stdin; on missing input print an error with usage); document with `--help` (short; it enters context); actionable error messages; structured output (JSON/CSV/TSV) on stdout, diagnostics on stderr; idempotency; closed input sets; `--dry-run` for destructive or stateful operations; distinct documented exit codes; safe defaults (`--confirm`/`--force` for destructive ops); bounded output (harnesses truncate around 10-30K characters; support `--offset` or an `--output` file). Self-contained deps: PEP 723 inline metadata with `uv run`, Deno `npm:`/`jsr:` imports, Bun auto-install, Ruby `bundler/inline`. One-off runners: `uvx`, `pipx run`, `npx`, `bunx`, `deno run`, `go run`.

### 8. Integration guidance for agent hosts (agentskills L1-335)

| Step | Guidance |
|---|---|
| 1 Discover | Scan project scope (`<project>/.<client>/skills/`, `<project>/.agents/skills/`) and user scope (`~/.<client>/skills/`, `~/.agents/skills/`). `.agents/skills/` is a widely adopted cross-client convention; the spec does not mandate locations. Some clients also scan `.claude/skills/`, ancestor dirs up to the git root, XDG dirs, user-configured paths. Look for subdirectories containing a file named exactly `SKILL.md`; skip `.git/`, `node_modules/`; bound depth (4-6 levels) and count (about 2,000 dirs). Collisions: project overrides user; within one scope pick first- or last-found consistently and warn |
| Trust | Project-level skills may come from an untrusted cloned repo: gate loading on a trust check so a repo cannot silently inject instructions |
| Cloud/sandbox | Project skills travel with the repo; user/org skills must be provisioned (config repo, URLs/packages, upload); built-ins ship as static assets |
| 2 Parse | Frontmatter between `---` markers, body after. Fallback for invalid YAML (for example an unquoted colon in `description`): quote or block-scalar and retry. Lenient validation: name/dir mismatch or name over 64 chars: warn, load; description missing/empty or YAML unparseable: skip and log. Store `name`, `description`, absolute `location` in a map keyed by `name` |
| 3 Disclose | Put a catalog (`name`, `description`, optional `location`; XML, JSON or list) in the system prompt or in an activation tool's description, with a short instruction on how to load. Hide filtered skills entirely (disabled by user, denied by permissions, or opted out of model invocation, for example `disable-model-invocation`). If no skills, omit the catalog and tool |
| 4 Activate | Model-driven: file-read of `SKILL.md`, or a dedicated tool (for example `activate_skill`) whose `name` parameter is an enum of valid skills. User-driven: `/skill-name` or `$skill-name`, autocomplete. Return full file or body-only; optionally wrap in `<skill_content name="...">` with the skill directory and a `<skill_resources>` list of bundled files, without reading them eagerly. Allowlist skill directories in the permission system so bundled resources do not trigger prompts |
| 5 Manage | Exempt skill content from context compaction/pruning; deduplicate re-activation; optional: run the skill in a subagent session that returns a summary |

Security notes the docs give: trust-gate project skills (above); allowlist only skill directories; scripts run in non-interactive shells, so they must not block on prompts; destructive scripts should be dry-run-capable with explicit confirm flags; `allowed-tools` is experimental pre-approval. The docs contain no dedicated sandboxing or script-signing section (gap).

### 9. Best practices for writing and evaluating skills (agentskills L408-1175)

Writing:
- Ground the skill in real expertise: extract it from a hands-on task (steps that worked, corrections you made, input/output formats, context you supplied) or synthesize from project artifacts (runbooks, API specs, code-review comments, VCS history, failure cases). Generic LLM-generated skills come out vague.
- Refine with real execution; read traces, not just outputs (vague instructions, inapplicable instructions, and menus of options cause wasted steps).
- Add what the agent lacks, omit what it knows; for each line ask "would the agent get this wrong without it?"
- Scope a skill as one coherent unit: not so narrow that several load per task, not so broad that activation is imprecise.
- Moderate detail; concise stepwise guidance with one working example beats exhaustive docs.
- Keep `SKILL.md` under 500 lines / 5,000 tokens; move detail to `references/` and say **when** to load each file ("Read `references/api-errors.md` if the API returns a non-200").
- Match specificity to fragility: freedom (with the why) for flexible tasks; exact commands for fragile ones.
- Provide defaults, not menus: one tool, one fallback.
- Favor procedures over declarations; the approach should generalize.
- Patterns: Gotchas section kept in `SKILL.md` (concrete corrections); output templates (inline or in `assets/`); checklists for multi-step flows; validation loops; plan-validate-execute for batch or destructive work; bundle scripts the agent keeps reinventing.

Descriptions (L983-1175): imperative phrasing ("Use this skill when..."); describe user intent, not mechanics; be a little pushy and list contexts including ones where the user does not name the domain; concise; hard limit 1,024 chars. Agents consult skills mostly for tasks beyond their built-in ability. Test with about 20 labelled queries (8-10 should-trigger, 8-10 should-not, realistic, near-miss negatives); run each 3 times, trigger rate threshold 0.5; split about 60% train / 40% validation, keep split fixed; revise from train failures only; avoid pasting keywords from failed queries; about 5 iterations; choose best by validation pass rate; recheck under 1,024 chars; verify with fresh queries.

Evaluating output (L684-980): test cases in `evals/evals.json` (`skill_name`, `evals[]` with `id`, `prompt`, `expected_output`, `files`, later `assertions`); start with 2-3 cases, vary phrasing, include edge cases, realistic context. Run each case with the skill and without it (or with the previous version snapshot), each from a clean context; workspace `<skill>-workspace/iteration-N/eval-<name>/{with_skill,without_skill}/{outputs,timing.json,grading.json}` plus `benchmark.json` (pass_rate, time_seconds, tokens as mean and stddev, plus delta) and `feedback.json`. `timing.json` has `total_tokens`, `duration_ms`. Assertions must be verifiable (not "output is good", not exact-phrase brittle); grade PASS/FAIL with quoted evidence; use scripts for mechanical checks; drop assertions that always pass or always fail in both configurations; investigate flaky ones; blind comparison between versions; human review of outputs. Iterate: give failed assertions, human feedback and transcripts plus the current SKILL.md to an LLM; generalize, stay lean, explain the why, bundle repeated work; stop when feedback is empty or gains plateau.

### 10. Use in solmargintrader

Repo facts checked (read-only): top-level `skills/` holds `five-minute-signal/` (SKILL.md only) and `trading-and-investing/` (SKILL.md, `manifest.yaml`, `SCHEDULED-RESEARCH.md`, `references/` with 57 files). `.claude/` has `agents/aero-pool-scout.md`, `settings.local.json`, `worktrees/`, and no `skills/` directory; no `.agents/` directory. `CLAUDE.md` says `extension/` and `liquidity/` can move real money, dry-run stays the default (`DEFAULT_CONFIG.mode` is `dry-run`, extension installs disarmed), and `backtester/` never gains live trading. `tradingview/` is untracked (not in `git ls-files`) and not git-ignored.

**Skill the repo could add: `tradingview-charting-reference`** (read-only lookup; no order path, consistent with the dry-run rule and with `five-minute-signal` which "never places an order").

Folder layout (references are slices of `docs/TRADINGVIEW-REFERENCE.md`, which does not exist yet, so the skill stays self-contained when copied to `.claude/skills/`, because spec paths are relative to the skill root and one level deep):
```
skills/tradingview-charting-reference/
  SKILL.md                                 # under 500 lines: when to use, routing table, gotchas, safety rules
  references/
    product-and-licensing.md               # from docs/TRADINGVIEW-REFERENCE.md "TradingView library: product, setup, versions" items 1-2
    release-notes-digest.md                # same section, item 3 (v33.0.0 breaking changes first)
    best-practices-faq-troubleshooting.md  # same section, items 4-5
    docs-bundle-navigation.md              # same section, item 6 (how to search charting-library-context.txt by URL: line)
    <datafeed / indicators / drawings / broker slices>   # from the other fragments of docs/TRADINGVIEW-REFERENCE.md; headings not known to this fragment
  assets/ and scripts/                     # none; do not vendor TradingView files
```
If the skill is only used inside this checkout, a pointer file with `Source: docs/TRADINGVIEW-REFERENCE.md#<heading>` is shorter, but then a copy installed elsewhere loses the content.

Compliant `SKILL.md` frontmatter (description 651 chars, under the 1,024 limit; `name` equals the folder; every `metadata` value is a string):
```yaml
---
name: tradingview-charting-reference
description: >-
  Look up how to embed and configure TradingView Advanced Charts (the Charting Library) in a web page: package layout and hosting (library_path), widget options, Datafeed API and UDF rules, custom indicators (PineJS metainfo), drawings, version 33 release-note breaking changes, and licence limits. Use when the user asks about TradingView Advanced Charts, Trading Platform, datafeed errors such as gaps or wrong bar times, or whether library files may be committed to a public repo. SKIP: Pine Script on tradingview.com, TradingView widgets, placing orders (no order path here; use the extension and its risk rails), backtests (use five-minute-signal).
license: Proprietary. Paraphrases TradingView documentation; the library itself is not redistributable.
compatibility: Reference only. Reads files under references/. No network, no scripts, no order placement.
metadata:
  version: "0.1.0"
  updated: "2026-11-07"
  docs-version: "33.0.0"
  safety: "read-only reference; never edits extension/ or liquidity/; dry-run stays default"
allowed-tools: Read Grep
---
```
`allowed-tools` is experimental, so drop it if a host rejects it. Body should open with the safety rules (below), then a table "question type to references/ file and when to load it", then a Gotchas list.

Gotchas to put in the body (all from this bundle): time properties are Unix seconds except Datafeed bar times and `nextTime`, which are milliseconds; `full_name` no longer exists (v28), the library sends `name` or `ticker`; quotes resolve with `ticker` then `name` (v27.006); Pine Script is unsupported, use JavaScript custom indicators; `createOrderLine`/`createPositionLine`/`createExecutionShape` exist only in Trading Platform (v29); `getBars` may return bars plus `noData: true` (v30.1); `library_path` and the script URL version must match; numeric key codes only in shortcuts (v33); wrap async widget methods in Promises (v32); gaps need `has_empty_bars` or `session_holidays`.

Safety rules to state in the skill: (1) answers explain and cite; they do not generate order-placing code paths, and any chart-side integration must keep `mode: 'dry-run'` as the default; (2) Trading Platform and its Broker API are for licensed brokers (fees apply), so do not propose them for the extension; (3) never copy files from the private TradingView repos (including `charting_library/`, the `charting-library-datafeed` skill, `datafeeds/`) into this repo, because "any part of the library" is barred from public repositories and the repo's visibility could not be checked here (`git remote` is `git@github.com:mithudso/solmargintrader.git`; `gh` could not resolve it). Keep `tradingview/` out of commits or confirm the repo is private first. The three `.d.ts` files and the context bundle are published by TradingView on the docs site, but the docs do not state a redistribution licence for them.

**Spec rules to check the existing repo skills against.**

| Rule (agentskills) | `five-minute-signal` | `trading-and-investing` |
|---|---|---|
| `name` 1-64 chars, lowercase/digits/hyphen, equals directory (L1620-1628) | passes | passes |
| `description` 1-1024 chars (L1660-1666) | 730 chars, passes | 998 chars, passes with 26 to spare; do not grow it |
| Only documented top-level fields: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` (L1587-1594) | has extra top-level `version`, `updated`; move into `metadata` as strings | extra top-level `version`, `updated`, `category`, `model`, `effort`, `tags`, `whenToUse`, `triggers`, `whenNotToUse`, `related_skills`; move or drop (unknown-key handling by `skills-ref` is not documented) |
| `metadata` is a string-to-string map (L1725-1731) | not used | `metadata.changelog` is a YAML list of strings, not a string value; serialize to one string or move the changelog out of frontmatter (it is already in `manifest.yaml`) |
| `SKILL.md` under 500 lines and under 5,000 tokens (L1810, L1807) | 135 lines, 8,032 bytes: passes | 362 lines passes, but 69,954 bytes is roughly 17k tokens (my 4-bytes-per-token estimate), far above the 5,000-token recommendation; move more into `references/` |
| References one level deep from `SKILL.md`, each focused (L1792, L1823) | no `references/` | 57 reference files, largest about 39 KB; check no reference links to another reference, and tell the agent when to load each |
| Description says what and when; imperative, intent-based (L1004-1007) | uses `TRIGGER:`/`SKIP:` keyword form; works, but not "Use this skill when ..." | same |
| Discoverable location (L44-57) | `skills/` is not a client scan path; link or copy into `.claude/skills/` or `.agents/skills/` for Claude Code and other hosts to find it | same |
| Evals present (`evals/evals.json`, trigger queries) (L699, L1013) | none found | none found (`manifest.yaml` and `SCHEDULED-RESEARCH.md` are extra files, allowed) |
| Script rules: non-interactive, `--dry-run`, exit codes (L1491-1560) | no `scripts/` | no `scripts/` |

Suggested validation command once the skills are in place: `skills-ref validate skills/tradingview-charting-reference` (install steps for `skills-ref` are not in the dump; see its repo).

## Repo findings from this distillation

The readers checked the repo while mapping the docs. These items are outside this page's scope and are recorded here, not fixed.

| Finding | Where | Why it matters |
| --- | --- | --- |
| The `zscore` strategy card uses the sample standard deviation (`ddof=1`, `backtester/core/indicators.py` `zscore`); the Compound 5m `zscore` metric uses the population standard deviation (`ddof=0`). | `backtester/core/indicators.py`, `backtester/core/scorecard.py` | The same name gives two numbers. A chart port must pick one. |
| `skills/trading-and-investing/SKILL.md` breaks the Agent Skills spec: `metadata.changelog` is a list (metadata must map strings to strings), it has 10 extra top-level frontmatter fields, and the body is about 70 KB (about 17k tokens; the spec recommends under 5,000 tokens). `skills/five-minute-signal/SKILL.md` has 2 extra top-level fields (`version`, `updated`). | `skills/` | Strict skill validators reject these files. |
| `skills/` is not a path that agent clients scan (`.claude/skills/` or `.agents/skills/`). | `skills/` | The repo's skills load only where they are copied or linked into a client path. |
| No exporter turns the forward ledger (`~/.config/soltui/compound/forward/<COIN>.jsonl`) or backtest trades into JSON for a chart. | `soltui/compound.py`, `backtester/core/types.py` | The marks and execution-shape recipes above assume a small read-only exporter. |
| Keltner, PPO, ROC and VWAP defaults differ between the repo and TradingView built-ins. | [Indicator parity](#indicator-parity-repo-vs-tradingview) | A chart with default inputs shows different values from the backtest. |

