# Jupiter 1000x: 1s scalp window and exit guard

Version: 2.0.0. Delta: Long and Short entry buttons with size presets, levels in basis points, order form beside the chart, hover descriptions and a slope accuracy gauge; extension 0.18.0, 2026-11-27.

## What it is

A separate Chrome window for https://jup.ag/1000x . It does three things.

1. **Reads the next 30 seconds from one-second bars.** Sixteen trend readings on
   1s oracle bars vote up or down. The window shows the vote, a chart with the
   expected 30 second range drawn ahead of price, a slope ladder with a running
   accuracy gauge, and a score of its own calls.
2. **Opens a position from the window.** Long and Short press the Jupiter
   page's own order form: its size button, then its Long or Short button, at the
   leverage the page shows. They are locked until you unlock them.
3. **Adds the take profit and stop loss the page lacks.** You set either or both,
   as distances from entry or as prices. A position opened from the window gets
   them armed from its real entry as soon as it is listed. When the oracle price
   reaches a level, the window alerts you, or presses that position's own
   **Close** button on the Jupiter page.

It never builds or signs a transaction and holds no key. Jupiter builds each
trade and your wallet signs it.

The read-out is a lean, not a signal that pays. The study behind it found that a
one-sided grid was right about 53% of the time over the next 30 seconds, and
that the 1000x payout needs far more than that. Read
[the study](../research/papers/SCALP-1S-STUDY.md) before trading on it.

## Open it

1. Load or reload the unpacked extension from
   `/Users/mitch/dev/solmargintrader/extension` (version 0.18.0 or later), then
   reload the Jupiter tab.
2. On https://jup.ag/1000x?market=SOL&mode=classic the Indicators overlay has a
   new **1s scalp** button in its title bar. Press it.
3. A 980 by 940 window opens for that market: read-outs on the left, the order
   form on the right of the chart. Pressing the button again brings it forward.
   Opening it from another market replaces it.

Every tile, column title, field and button explains itself on hover. The window
itself carries no explanatory paragraphs.

The window closes when its Jupiter tab closes. It stays open when the tab
reloads, so an armed guard can report that it lost the page.

## The read-out

One-second bars come only from the live stream: Jupiter's history service has no
resolution below one minute. The stream publishes about twice a second. A second
with no update repeats the last price; more than three silent seconds discard
the bars and start again. The grid therefore needs about 80 seconds after
opening, and after any gap.

| Part | What it shows |
| --- | --- |
| Call | **UP** or **DOWN · strong** when at least 12 of 16 readings net one way, **lean** from 6, **MIXED** below. The line under it gives the vote count, the hit rate for that tier on the recording the grid was chosen from, the figure from the separate short live check with its error bar, and the typical 30 second move now. Hover the box for the full sentence. |
| Chart | 1s candles for the last 150 seconds. Ahead of price: a dashed centre line and the bands inside which 68% and 90% of recorded 30 second moves ended, scaled by the last 30 seconds' volatility. Entry, bust, take profit and stop loss appear as price lines. |
| Strips | Top: the call made each second for the last 120 seconds. Bottom: whether that call was right 30 seconds later. |
| Trend grid | The sixteen readings. Green votes up, red votes down, grey is neutral, dashed is warming up. Every tile also carries an arrow and its value. |
| Slope ladder | Per window (5s, 10s, 20s, 30s, 1m, 5m): the fitted slope, the range it has moved in, its second derivative, that range, how long the slope has held its sign, the average and longest completed run this session, and a running accuracy gauge. |
| Session score | Calls settled in this window so far. Seconds overlap, so it is a rough guide. |

### The sixteen readings

Every reading is positive when price has been rising, and votes with its sign.
All are computed on closed 1s bars only.

| Tile | Definition | Warm-up |
| --- | --- | --- |
| Impulse 2s, Momentum 5s, Momentum 60s | Percent change over 2, 5 and 60 seconds, in basis points | 3, 6, 61 s |
| Breakout 20s, Breakout 60s | +1 when the close exceeds the high of the previous 20 or 60 seconds, −1 below their low, else neutral | 21, 61 s |
| Heikin-Ashi run | Signed count of consecutive Heikin-Ashi bars of one colour, capped at 20 | 60 s |
| Balance of power | Mean of (close − open) / (high − low) over 5 seconds; a zero-range second counts as 0 | 5 s |
| ZigZag leg | Direction of the current swing after a 1 basis point close-only reversal | 60 s |
| Range position | Position of the close in the last 60 seconds' range, −0.5 to +0.5 | 60 s |
| Efficiency | Net change over 60 seconds divided by the distance travelled | 61 s |
| Slope 60s | t-statistic of a straight-line fit through the last 60 closes | 60 s |
| RSI 7 | Wilder RSI over 7 seconds, centred to −1…+1 | 60 s |
| Z-score 20 | Close against the mean of the last 20 closes, in sample standard deviations | 20 s |
| MACD hist | MACD(12,26,9) histogram on 1s closes, in basis points of price | 78 s |
| Parabolic SAR | +1 while the stop trails below price (start and step 0.02, cap 0.2) | 60 s |
| Supertrend | Direction from a 10 second mean true range, multiplier 3 | 60 s |

RSI and the Z-score are read as trend here, not as overbought or oversold: in
the recording, fading an extreme lost. The repository's two-bar reversal rule,
Keltner position and directional movement failed the selection rule and have no
tile. A 3/10 EMA cross passed narrowly and was left out as a near-duplicate of
the momentum tiles.

### Slope ladder and reversal timing

For each window the slope is the least-squares slope of the closes, in basis
points of price per second. **Change** is the second derivative of a
least-squares parabola through the same window, in basis points per second
squared. A positive change means the slope is increasing. When slope and change
share a sign the move is steepening; when they differ it is fading.

**Held** counts the seconds since the slope last changed sign. **Avg / max** are
the mean and longest completed runs between sign changes in this session. A run
is timed only when both of its ends were seen: the run in progress when the
window opened, or when the feed broke, is left out. Hover a row for the recorded
baseline. In the recording a window's slope kept its sign for about the length
of the window on average (5.9 s for the 5s slope, 287 s for the 5m slope), which
is what a random walk produces. The longest runs were 72 s and 1,616 s.

### Slope accuracy gauge

The **Hit** column scores each window's slope as a call. Every second on which
the slope points up or down is checked 30 seconds later against the move from
that second's close. The gauge shows the share that matched over the calls
settled in the last ten minutes, as a bar centred on 50%, with the count. A flat
slope makes no call, and calls open when the feed breaks are dropped. Seconds
overlap, so the gauge is a running read and not a trade record. In the recording
the 5 second slope matched 51.6% of the time and the 5 minute slope about 50%.

## Opening a position

| Step | What happens |
| --- | --- |
| Unlock | Tick **Unlock**. Long and Short are disabled until you do, in every window: Unlock, Confirm and the size are never remembered, so each window starts locked, confirming and at a quarter. Hover a disabled button to see why it is disabled. |
| Size | Choose ¼, ½, ¾ or All of the funds available for the pay token selected on the Jupiter page. A quarter, half and all press the page's own **25%**, **Half** and **Max**. Three quarters has no page button: the window presses **Max**, reads the amount, types three quarters of it and waits for the page's own line under the amount to change. In every case the amount the page then shows must be within 85% to 100% of that share of the balance it shows, or nothing is pressed. |
| Levels | Leave **as** on *bp from entry* and type a take profit and a stop loss in basis points, or press **No TP**, **No SL** or **No TP/SL**. A stop loss at or beyond the bust distance (9.8 bp at 1,000×) is refused before anything is sent. |
| Press | With **Confirm** ticked, the first press turns the button into *Confirm long ½* for four seconds and a second press at least 0.6 seconds later sends. A double-click does not confirm. Untick it for one-press entries. |
| Send | The window asks the Jupiter tab once. The tab checks that it is on this window's market and in Classic mode, sets the size, waits for the page to accept it and presses the page's own Long or Short button. The page uses the leverage it shows. |
| Arm | When exactly one new position for that market, side and leverage is listed, the window selects it and arms the levels from its real entry price, in the mode chosen under **At a level**. If price has already passed a level by then, the guard arms anyway and acts on the next quote. If arming fails, it says the position is open without its levels, with a notification and tone. |

The request is never repeated. If the tab does not answer, the window says the
outcome is unknown, keeps the entry blocked and keeps watching for the position.
If no new position is listed within 60 seconds it says so; one listed within
the next ten minutes (a wallet prompt answered late) is still adopted and its
levels armed. The tab refuses a second entry while one is in progress or within
five seconds of the last, and gives up instead of pressing if the form takes
more than six seconds to settle, as it can in a hidden tab. Entries are refused
while a guard is live on another position, and while the positions list cannot
be read in full: the new position is found by comparing the list before and
after. Chrome asks before closing the window while an entry is out.

## The exit guard

| Step | What happens |
| --- | --- |
| Read | Once a second the window asks the Jupiter tab for the rows of its positions table: market, side, leverage, entry, mark, bust and the state of the row's button. |
| Set | Type a take profit, a stop loss, or both. **as** chooses how the fields are read: *bp from entry* (distance in basis points from the position's entry) or *price*. The quick buttons fill a level from a distance or from the way to bust, and **No TP**, **No SL** and **No TP/SL** clear them. Each level shows its price or distance and the page formula's estimated result. |
| Arm | Choose **Alert me only** (the default) or **Press Close on the Jupiter page**, then press Arm. Arming needs a real click. |
| Watch | Each oracle quote is compared with the levels. A quote older than two seconds is ignored. When no fresh price arrives, or the Jupiter page cannot be read, the panel says **ARMED BUT NOT PROTECTED**, and after four seconds it notifies you and sounds a tone, repeating every 30 seconds. A price stream that gave up is started again every 15 seconds. |
| Act | At a level the window notifies you and sounds a tone. In close mode it asks the tab to press Close for that one row. If the page still shows the 15 second hold countdown it retries every 250 ms for up to 30 seconds. |
| Confirm | After the press, the guard waits for the row to leave the list and then reports **Closed**. The row counts as gone only after three complete reads in a row miss it; a read with a row still opening or unreadable proves nothing. If the row is still listed after 25 seconds, or the page stopped answering, it reports **Not confirmed** and does not press again. |

### Rails, in code

- **Alert only is the default, and entries are locked.** A fresh install presses
  nothing: Long and Short need the Unlock tick, a real click and, by default, a
  confirming second press.
- **Entries use the page's own controls.** The window presses the page's size
  button and its Long or Short button. It types an amount only for three
  quarters, from the page's own Max, and refuses if the page does not show that
  amount back. The leverage is whatever the page shows; the window never sets it.
- **One entry request, never repeated**, and none within five seconds of the last.
- **Right market, right mode.** The tab refuses an entry when it shows another
  market than the window's, or a mode other than Classic.
- **One position, exact match.** The bridge presses only when exactly one listed
  row matches the armed market, side, leverage and entry text. Two identical
  rows cannot be armed, and are refused as ambiguous at the press.
- **Only the row's own button, only when it says exactly "Close" and is
  enabled.** "Close all", "Close position" and locked modes are never pressed.
- **No second press** for the same row within ten seconds, and never after a
  press the page did not confirm.
- **No guessed numbers.** Levels are plain decimals you typed. An entry or bust
  price the page shows in another format is refused. An entry more than 20% from
  the live price counts as misread.
- **Levels must make sense.** Take profit on the winning side of the current
  price; stop loss on the losing side and inside the bust price. A stop loss is
  refused when the page's bust price cannot be read.
- **A request that is out cannot be withdrawn.** Disarm works only while the
  guard is armed and waiting. A press that lands after the 30 second wait ran
  out is still recorded as a press.
- **The window is not closed under a live guard.** Opening the scalp window for
  another market is refused until you disarm. If the Jupiter tab itself closes,
  the window stays open and reports that it lost the page.
- **Only the extension's own worker** can reach the page bridge, and only the
  window that worker opened for that tab can ask for a close.
- **Failures are loud.** Every refusal ends in a visible **COULD NOT CLOSE**
  state with the reason, a notification and a tone.

Source: `extension/src/1000x/exit-guard.js`, `extension/src/1000x/entry-plan.js`,
`extension/src/1000x/page-bridge.js`,
`extension/src/bg/jupiter-scalp-window.js` and the `jupiterScalpWindow` command
in `extension/src/core/commands.js`. The guard is separate from the grid engine:
it has its own arm switch and the grid's kill switch does not affect it.

### What it cannot do

- **It cannot sign.** Each open and each close needs your wallet's signature.
  If the wallet asks, nothing happens until you approve. Keep the Jupiter tab
  and the wallet reachable.
- **It cannot set an entry price or the leverage.** An open fills at the oracle
  price recorded about two seconds after submission, at the page's leverage. A
  level in basis points is measured from that real entry.
- **Large sizes may stop at a page dialog.** The page can ask for a message
  before opening a large position. The window then reports that no new position
  was listed; finish on the Jupiter tab.
- **It cannot set a fill price.** Jupiter's documentation says a close fills at
  the oracle price recorded about two seconds after submission, with no price
  limit. A stop loss near the bust price can still be liquidated first.
- **It cannot close inside the first 15 seconds** of a position.
- **It stops when its window closes** and when Chrome quits. Chrome asks before
  closing a window with a live guard. With the Jupiter tab closed it can only
  alert. Keep the window open; it may sit behind other windows. In a hidden
  window Chrome slows timers to about once a second, which delays retries and
  confirmation but not the trigger, which runs on each arriving quote.
- **It reads the English desktop table.** On a narrow window (card layout) or
  another language it reports that it cannot read positions.
- **One guard at a time**, for one position of the window's market.
- **No trailing stop, no partial close, no time stop.** The product closes whole
  positions only.

## Evidence and limits

The positions table and the close flow were read from the public bundle
`https://jup.ag/assets/1000x-Bz57naGJ.js` in the local archive at
`/Users/mitch/.local/state/jup1000x-overlay-2348/public-site/` : a `table` with
the headers Position, Value / PnL, Entry / Mark price, Bust price, Size,
Collateral, Held and Status; one `tr` per position; a button in the last cell
that reads "Close", "Close in Ns" or "Closing…". On 2026-11-27 the live page
showed the same headers with no rows, because no position was open. These are
portal internals with no compatibility promise. If Jupiter changes the table,
the bridge refuses rather than guesses.

The order form was read from the same bundle: a `form` labelled "Degen market
order" holding the amount input `#degen-amount`, buttons reading "25%", "Half"
and "Max", an available-balance button, leverage buttons, and the two submit
buttons marked `data-side="long"` and `data-side="short"`.

**Not verified:** an open or a close on the real page. No position was opened
for this work, and the three-quarter amount in particular has only been typed
into a stand-in for the page's input. The first real use is the first live test
of each press, the wallet prompt and the confirmation. Start with a quarter, in
alert-only mode.

## Verification

```sh
cd /Users/mitch/dev/solmargintrader/extension
npm test
npm run e2e:scalp -- --evidence /tmp/smt-scalp
npm run e2e:scalp -- --full --evidence /tmp/smt-scalp-full
```

`npm test` includes the Python parity of all sixteen readings, the slope ladder
and the payout arithmetic on recorded oracle bars, the guard state machine, the
page bridge and the window ownership rules. `npm run e2e:scalp` loads the
extension into Chrome for Testing against a local stand-in for the Jupiter page
and a loopback oracle stream. It checks that the window opens on a real click
only, that the order form sits beside the chart and every tile and column has
hover text, that alert mode presses nothing, that close mode presses the row's
own Close exactly once after the hold lock clears and never "Close all", that a
stale price shows the unprotected warning, that Long and Short stay locked until
unlocked and need the confirming press, that a confirmed Long presses the page's
Max, types three quarters, presses Long once and arms the levels from the new
entry, and that the slope gauge fills in. `--full` also waits out the warm-up.
It never visits the real site and connects no wallet.

Sources:

https://jup.ag/1000x?market=SOL&mode=classic

https://docs.jup.ag/user-docs/trade/1000x/trading.md

https://developer.chrome.com/docs/extensions/reference/api/tabs#method-sendMessage
