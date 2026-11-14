# Oracle winning-strategy TUI

Version: 1.1.0
Delta: add a genuine foreground trade stream, provisional indicator overlays, full refresh and completed two-bar context.

Start the interactive, read-only workbench:

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py
```

It opens a focused **1m / baseline / six-strategy** watchlist, with a price and
shape chart on the left and numeric indicators on the right. The complete
**908 configuration/timeframe/mode groups** from **1,566 positive fee rows**
remain available through the strategy picker. The existing SolTUI environment
already provides Textual; this entry point does not install or start a service.

## Controls

| Control | What changes |
| --- | --- |
| Bar window | Select 1m, 5m, 10m or 1h; calls concern the next bar of this actual timeframe. |
| Study mode | Baseline, shape, frequency, named controls, or all modes in the chosen window. |
| Chart | Display up to48,96,192 or300 timestamp-aligned points, including the labelled developing point when available; this does not reseed strategies or change their warmup. |
| Refresh now [R] | Request fresh completed-candle overlap, quote, trade snapshot and indicator calculation for the displayed window; provider error backoff stays enforced. |
| Click / Enter on indicator | Toggle that indicator on the chart; repeat to clear. EMA/Bollinger price levels share the USD axis; oscillators use an explicitly labelled independent right scale. |
| Maximum signal refresh | Enter0.2–300seconds and Apply, or use minus/plus. New settled bar boundaries also refresh closed inputs so streaming indicators keep advancing. The quote heartbeat stays independent at1second. |
| Choose strategies | Search names, parameters or IDs. Space/Enter toggles a row; Select/Clear visible affects only the current search. Apply preserves choices in other windows. |
| Edit focused | Edit the focused row's JSON parameters/ensemble; Apply validates before changing the working variant. |
| Reset focused | Restore the immutable original configuration and its original evidence. |
| Save view | Persist windows, chart length, cadence, manual selections and edited variants privately. |
| Shape guide [H] | Explain the detected shape, show its actual 48-bar price trace and an illustrative sketch, and describe what to watch or what would challenge the interpretation. |

Keys: **S** opens strategies, **E** edits the focused row, **R** requests the same full displayed-data refresh as the button, **H** opens the shape guide, **Ctrl-S** saves the view, **Q** quits. Escape cancels a modal without
changing its selection or configuration. Arrow/Page keys navigate the tables.
On narrow terminals the indicator panel stacks below the watchlist; scroll or
Tab to it. Wide terminals show it on the right. Tables can scroll horizontally.

The historical columns retain **0.25% and 0.15% per-fill** scenarios. An edited
row shows **UNTESTED**, has a pencil marker and inherits neither original P&L
nor a winning label. Applying an edit changes only this display's working
hypothesis. Save view makes it survive a restart. Original parameters, accepted
CSV/plan, archived forecasts and running producer settings stay unchanged.

The JSON editor validates supported members with the canonical strategy factory
and ensemble contract. It also permits structurally valid reference-policy edits;
these remain N/A without a directional adapter. Invalid JSON or parameters keep
the previous working configuration. Longer windows can require additional
warmup. Editing a strategy does not establish a new profitable backtest.

Default preferences are stored in
`/Users/mitch/.config/solmargintrader/oracle-winners-tui.json` (or under
`XDG_CONFIG_HOME`). Use `--settings /absolute/private/view.json` for another
profile. Saving is atomic with mode0600; corrupt/incompatible saved preferences
are reported and preserved while the original defaults load. No save occurs
until Save view is chosen.

## Shape and indicator panels

The chart plots actual observed prices on the selected timeframe. Streaming mode can append a clearly labelled developing candle, keeping the selected total point limit. Closed strategy calls and the48-bar shape still use only completed candles. The shape panel
shows the detected range/trend/V/bowl/cap/compression, range zone, observed shape
episode age and fitted-turn phase where available. Its marker locates the **live
quote in the preceding48-bar observed range**; the last completed close is used
when no fresh quote exists. A quote outside that range can show below0% or
above100%. This is observed range position, **not future pattern completion**.

The inline panel explains the label in plain language and shows a small teaching
sketch. **Shape guide [H]** opens a scrollable explanation with the actual last
48 contiguous completed closes, a dot at the last completed close, price scale
and timestamps. The illustrative sketch is separate from that observed trace;
neither extends into a predicted future path. Live quote range position and the
last completed close have separate labels. Chart lookback does not change this
48-bar shape window.

Each label explains its geometric meaning, a conditional continuation or reversal
to watch, and what would challenge that interpretation. A V describes a decline
and recovery; it does not establish that the recovery will continue. Compression
describes narrowing fitted high/low boundaries and leaves breakout direction
open. Bowl/cap explanations label a fitted historical turn and describe R² as
past fit quality. These observations do not become new strategy triggers or
forecast probabilities. The guide includes a gallery for all detector labels.

Label age counts consecutive rolling windows with the same label. It is not the
age or completion percentage of the full pattern. Retained data is marked stale;
source failures clear the open guide, and insufficient contiguous history shows
an unavailable trace. Use Page/arrow keys to scroll and Escape or Close guide to
return to the watchlist.

The right panel shows RSI14, balance of power, MACD line/signal/histogram,
Bollinger bands and%B, ADX/DI, stochastic, ATR, EMA20/50, z-score and ROC.
Selected configurations add their actual RSI periods and custom Bollinger,
MACD and stochastic parameter readings. Indicator histories use the canonical
trailing functions at each timestamp, with warmup values left unavailable and
real gaps breaking history. Balance of power is `(close-open)/(high-low)`;
a zero range is unavailable. ROC is percent. These are market context, not new
backtested winners or profit probabilities.

### Streaming readings and clickable overlays

The TUI owns one foreground, memory-only public Coinbase Exchange subscription
for `ZEC-USD` on `matches` and `heartbeat`. It reuses the existing stdlib
WebSocket transport. It never starts, replaces or writes to the shared recorder,
installs a service or opens an account connection. The first `last_match` is a
historical subscription snapshot and is not added to live volume. Unique actual
matches provide open/high/low/close and the sum of observed trade sizes.

The first candle after attachment or reconnect is **partial since attachment**:
the stream does not know the earlier open, high, low or volume. The label changes
to a developing full-period observation only after a clean boundary. Trade-ID
and heartbeat gap candidates, disconnects and old trade/receipt timestamps
withhold the live point; no price or volume is filled in. Clean later boundaries
can recover. In a quiet market, unchanged values are honest; the display does
not animate invented changes. UI polling occurs four times per second, separately
from the chosen maximum completed-signal refresh interval. Closed history also advances at each newly settled bar boundary, even when the maximum interval is longer than that bar.

Live scalar readings add the current trade candle to the contiguous completed
indicator history only when its timestamp is the immediately adjacent current
bucket. They remain **provisional**. They do not change strategy signals,
historical P&L, cycle training, shape classification or fixed forecast targets.
The three-second settlement period may briefly withhold the live point until
the previous completed candle is available. Unavailable streaming data leaves
explicitly labelled completed readings rather than simulated ticks.

Click an indicator row, or focus it and press Enter, to draw its actual historical
values on the price graph. Repeat to remove it. The selection marker, numeric
legend and units identify the plotted measure. Price levels such as EMA20 or
Bollinger bands share the USD scale. RSI, volume, MACD changes and other
oscillators use a separately labelled right scale; their apparent vertical
position is not a dollar price or future target. Missing/warmup points do not
produce invented lines. The drawing stops at the latest observed candle.

### Completed two-bar reversal check

The separate panel checks the last two contiguous **completed** candle bodies
for UU or DD and distinguishes the first two candles of a new streak from a
rolling pair inside a longer streak. Mixed, flat or missing bars show no valid
same-color condition. The signal and next-bar target timestamps stay fixed;
expired context is marked stale rather than given a fresh target on every paint.

Historical fractions come from the immutable November12–13 one-day study,
verified by its retained results hash. At ten minutes, rolling UU preceded D
in19/24 cases (79.2%); rolling DD preceded U in16/29 (55.2%), with one flat.
New-streak definitions instead give14/19 (73.7%) and6/13 (46.2%). These are
**one-day historical counts, not live odds**, use the captured receipt clock
rather than this live exchange-time feed, and do not establish profitable trades.
Hourly samples are explicitly tiny. Full definitions and qualifications appear
in the panel tooltip and the paper:
https://oraclebot.io/#research/zec-two-bar-reversal-8b2f7af3

### Refresh, backoff and teardown

Refresh now coalesces a request for fresh completed-candle overlap and a fresh
recorder read, wakes a disconnected trade subscriber, and recalculates displayed
indicators. It preserves the fixed starting history, cycle fits, parameters,
watchlist and user settings. Repeated clicks cannot bypass the15-second retry
backoff after provider errors, rate limits or incomplete responses. Refresh
means all data in the displayed window; it does not redownload the complete
historical matrix or evaluate every hidden strategy.

Completed evaluation, recorder reads, indicator calculations and the trade
subscription each have an owned background lifecycle. Results carry view/source
generations so late output cannot replace a new timeframe or edited configuration.
Closed indicator history is cached; live ticks calculate only the newest point.
The UI never does network I/O. Quit/exit/unmount stop timers and request bounded
worker/socket shutdown without replacing Textual's own lifecycle fields. Existing
services, capture archives and signing settings remain unchanged.

## Plain and machine-readable compatibility

The former whole-universe table remains available with **--plain**. **--json**
and bounded **--frames** requests retain the previous noninteractive contract:

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --plain --intervals 1m --modes baseline --refresh 10
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --json --frames 5 --refresh 10
```

`--intervals` and `--modes` in TUI mode choose the initial focused window/mode;
use its controls to switch thereafter. Noninteractive mode retains its original
multi-window filters. UI preferences and untested variants are never inserted
into the original plain/JSON stream or backtest selection.

## Sources and timing

The application polls the existing shared recorder's atomic `latest.json` for an
exact **ZEC-USD** bid/ask midpoint. These are streaming quote snapshots, not a
promise of every exchange tick or an executable fill. The upstream exchange
event age is not certified by this snapshot source. It requires both fresh
snapshot and quote clocks; an old quote clears the current direction and
retains `last_direction` only as explicitly stale context.

Strategy input is **completed Coinbase Exchange trade OHLCV**, fetched separately
through public `GET /products/ZEC-USD/candles`. This avoids fabricating volume
from the quote snapshots. REST history is paginated below the 300-candle limit,
validated and filtered to completed buckets with a three-second settlement
delay. Successful data refreshes occur once per bar boundary, not on every
display tick; incomplete latest candles and failures retry no sooner than
fifteen seconds. A recent three-candle overlap lets late internal candles
recover without filling genuine gaps. This is a live
quote display with completed-bar signals, not a tick-driven strategy rewrite.

Coinbase offers 60, 300 and 3,600-second bars used here. Ten-minute bars are
aggregated only when **both** constituent five-minute bars exist. Empty periods
remain missing. A missing candle resets strategy history and makes a 48-bar
shape unavailable until enough contiguous history exists. Volume is the actual
reported base-asset trade volume. No interpolation, zero-volume gap filling or
USD/USDT/USDC substitution occurs.

The noninteractive stream seeds each selected strategy's warmup plus128 bars.
The TUI uses a fixed512-bar seed per timeframe, preserving its starting point
when chart lookback or manual selection changes. Stateful strategies replay that full prefix
and retain its fixed starting point as new completed bars arrive. This seed
window is not the original capture's starting history. The JSON reports
`input_start_at`, `contiguous_bars` and `input_sha256`; two differently seeded
live sessions must not be claimed to have identical state. History is bounded
at 100,000 periods; capacity exhaustion reports unavailable. No input files or
forecast archives are written by the script.

Provider errors, missing history, stale quotes and expired predictions show
explicit reasons. A fast quote cannot make an expired completed-bar prediction
fresh. The script does not relabel a past call with a new target on each refresh.

## Direction, shape and frequency semantics

The exposure sign follows Oracle's convention: positive → **UP**, zero →
**FLAT**, negative → **DOWN**. The expanded study's spot policies are long/flat
and therefore produce **UP or FLAT**. A long exit is not automatically a bearish
forecast. This is a source-bound, provisional exposure hypothesis, not calibrated
next-bar price accuracy, P&L or trading permission. It does not replace the
native Oracle's separate 14-card archive or qualification.

The original member and ensemble adapters preserve state, persistence, gating,
warmup and volatility scaling. The graph shape uses only the last **48 contiguous
completed bars**, through the accepted detector with its full contiguous input
suffix so the preceding return is preserved: range, trend up/down, V rebound,
inverted V, bowl, cap or compression. Shape-filtered rows apply their original
fixed family rule. Baseline rows display shape as context without silently
adding a filter.

Frequency rows retain the 64-observation training search and frozen 16-period
decision block, anchored to this process's initial history. The current output
never fits on its future evaluation block. A cached period and coefficients,
including an unavailable fit, stay frozen through the block even when the
provider later revises its training candles. Frequency controls, linear controls
and shape controls remain explicitly named research benchmarks. No null tests,
backtests, paid research or embeddings run in the display. **None of the
original study's cycle tests survived multiple-testing correction**; the live
cycle filter carries `qualified: false`.

The **59** profitable grid/DCA and synthetic Volty configuration/mode groups
remain listed with `lifecycle_policy_has_no_directional_adapter`. Their
path-dependent orders, stop crossings and holdings cannot be converted into an
honest standalone UP/DOWN/FLAT call from a completed-candle exposure adapter.
They stay **N/A**, rather than being silently omitted or assigned an invented
prediction. Other strategies can remain warming when the real venue history
has gaps. Having a profitable backtest does not make missing inputs available.

## Frozen selection and verification

The script verifies the exact accepted CSV and compressed plan hashes before
loading any winner. It joins configurations to the frozen inventory rather
than regenerating the current catalog. The original study and all its outputs
remain unchanged:

- [Expanded findings](../research/ZEC-EXPANDED-STRATEGIES.md)
- [Complete evidence index](../research/zec-expanded-20261113.llms/llms.txt)
- [Current default-card Oracle display](ORACLE-LIVE-FORECAST.md)

Provider contract:
https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles

Tests exercise real loopback HTTP pagination and rate limits, frozen winner
completeness, future-price poisoning, missing candles, exact frozen-cycle
agreement, stale quotes and expired calls. The historical matrix is not rerun.

```sh
cd /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/soltui/bin/python -m unittest research.tests.test_zec_live -v
```

Live acceptance must independently inspect a running complete frame after
bootstrap, source timestamps, actual strategy directions, shape availability
and preservation of the existing recorder. Unit tests alone do not establish
current venue availability. The script never opens a wallet, loads credentials,
signs, submits orders, installs a service or changes the existing Oracle policy.
