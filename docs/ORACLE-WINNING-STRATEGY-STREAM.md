# Oracle winning-strategy TUI

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
| Chart | Display 48, 96, 192 or 300 completed bars; this does not reseed the strategy or change its warmup. |
| Signal refresh | Enter 0.2–300 seconds and Apply, or use minus/plus. The quote heartbeat remains independent at one second. |
| Choose strategies | Search names, parameters or IDs. Space/Enter toggles a row; Select/Clear visible affects only the current search. Apply preserves choices in other windows. |
| Edit focused | Edit the focused row's JSON parameters/ensemble; Apply validates before changing the working variant. |
| Reset focused | Restore the immutable original configuration and its original evidence. |
| Save view | Persist windows, chart length, cadence, manual selections and edited variants privately. |

Keys: **S** opens strategies, **E** edits the focused row, **R** requests a
refresh, **Ctrl-S** saves the view, **Q** quits. Escape cancels a modal without
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

The chart uses the selected number of completed trade candles. The shape panel
shows the detected range/trend/V/bowl/cap/compression, range zone, observed shape
episode age and fitted-turn phase where available. Its marker locates the **live
quote in the preceding48-bar observed range**; the last completed close is used
when no fresh quote exists. A quote outside that range can show below0% or
above100%. This is observed range position, **not future pattern completion**.

The right panel shows RSI14, balance of power, MACD line/signal/histogram,
Bollinger bands and%B, ADX/DI, stochastic, ATR, EMA20/50, z-score and ROC.
Selected configurations add their actual RSI periods and custom Bollinger,
MACD and stochastic parameter readings. Numbers use the active bar window,
reset at gaps and retain their bar-close timestamp. Balance of power is
`(close-open)/(high-low)` for the completed candle; a zero range is unavailable.
ROC is displayed in percent. BOP is requested market context, not a newly
backtested winning strategy. None of these numbers is a profit probability.

Quote age and completed-bar expiry are checked against the current screen
clock, even with a long signal refresh. Retained indicator values are explicitly
marked stale; failed source/calculation windows clear dependent numbers and
charts. Refreshes preserve cursor position so the right panel can be read while
prices update. A configuration/window change cannot install an older worker's
response. One coalescing calculation worker and one quote worker keep the event
loop responsive; page fetches check cancellation between bounded requests.

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
