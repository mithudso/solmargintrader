# Streaming the profitable ZEC strategy configurations

Run from an existing Python environment with the repository's research,
backtester and Oracle dependencies. This is a foreground, read-only observer:

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py
```

The terminal refreshes every ten seconds until Ctrl-C. It shows all **908
configuration/timeframe/mode combinations** selected by **1,566 positive fee
rows** from the accepted expanded ZEC study. It includes 1m, 5m, 10m and 1h,
and keeps the 0.25% and 0.15% **per-fill** scenarios in separate return columns.
A configuration can be profitable at one fee and losing at the other; both
completed returns remain visible. No rank or claim of prospective reliability
is inferred from these one-day, in-sample winners.

The table identifies each strategy, full configuration ID, study mode, UP/FLAT
direction, current shape and range zone, historical returns and availability.
The timeframe summary gives the actual completed-bar close, target time and
contiguous history count. JSON output includes exact member parameters, ensemble
configuration, fee evidence, source clocks, bar-input hash and implementation
hashes. Every refresh preserves the signal's original bar close and expiry.

Useful filters and machine-readable output:

```sh
# Strategy passes without the research control modes; still includes every winner in those passes.
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --intervals 1m 5m 10m --modes baseline shape frequency

# Every selected row and exact parameter set, one complete JSON object per frame.
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --json --refresh 10

# Bounded read-only feed check; initial frames can still be loading candle history.
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oracle_winners.py --frames 5 --refresh 10 --limit 20
```

`--refresh` changes the display cadence from 0.2 through 300 seconds. It does
not change a tested strategy's bar interval or predict an arbitrary ten-second
move from minute evidence. Each directional hypothesis concerns the next bar
of that strategy's actual timeframe. `--limit` explicitly limits terminal rows;
the default and JSON output never truncate the selection. `--prices` selects
an existing shared-recorder directory without starting or changing a recorder.

## Sources and timing

The script polls the existing shared recorder's atomic `latest.json` for an
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

The initial history includes each selected strategy's warmup plus a 128-bar
seed, with at least 128 periods. Stateful strategies replay that full prefix
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
