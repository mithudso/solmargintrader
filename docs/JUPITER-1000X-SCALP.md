# Jupiter 1000x: 1s scalp window and exit guard

Version: 2.6.0. Delta: on the Perps page the window now opens positions and runs a take profit and stop loss for HYPE and ZEC, where Jupiter offers none; a mute button; extension 0.22.0, 2026-11-28.

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
   `/Users/mitch/dev/solmargintrader/extension` (version 0.19.0 or later), then
   reload the Jupiter tab.
2. On https://jup.ag/1000x?market=SOL&mode=classic the Indicators overlay has a
   new **1s scalp** button in its title bar. Press it.
3. A 980 by 940 window opens for that market: read-outs on the left, the order
   form on the right of the chart. Pressing the button again brings it forward.
   Opening it from another market replaces it.

Every tile, column title, field and button explains itself on hover. The window
itself carries no explanatory paragraphs.

The dropdown at the top left chooses the coin the window watches. Choosing
another reloads the window on that market, so read-outs and scores start again.
Long and Short work only while the Jupiter tab shows the same market, and the
dropdown is locked while a take profit, stop loss or entry is live.

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
| Call | A weighted vote of the sixteen readings (see [The weighted call](#the-weighted-call)). **UP** or **DOWN · strong** at a weighted score of 75% or more one way, **lean** from 37.5%, **MIXED** below. The line under it gives the vote count, the weighted score, the hit rate for that tier when the weighted call was replayed on the recording, the figure from the separate short live check with its error bar, and the typical 30 second move now. Hover the box for the full sentence. It stays in view on both tabs. |
| Chart | 1s candles for the last 150 seconds. Ahead of price: a thick **likely** line, the most likely price over the next 30 seconds, and the bands inside which 68% and 90% of recorded 30 second moves ended, scaled by the last 30 seconds' volatility. The likely line is the current price plus the average move that followed weighted calls of the current tier in the replay: +0.56 bp after 5 seconds and +0.90 bp after 30 for a strong call, +0.21 and +0.49 for a lean, so much of it arrives early and it is small next to the bands. With a mixed grid it is flat. Entry, bust, take profit and stop loss appear as price lines. |
| Strips | Top: the call made each second for the last 120 seconds. Bottom: whether that call was right 30 seconds later. |
| Trend grid | The sixteen readings. Green votes up, red votes down, grey is neutral, dashed is warming up. Every tile also carries an arrow and its value, a thin bar for its say in the call, and six small numbers: its own running hit rate, in percent, over the next 5 s, 10 s, 20 s, 30 s, 1 min and 5 min. A ★ and a double border mark a tile whose setting the Experiments tab switched in. |
| Slope ladder | Per window (5s, 10s, 20s, 30s, 1m, 5m): the fitted slope, the range it has moved in, its second derivative, that range, how long the slope has held its sign, the average and longest completed run this session, and a running accuracy gauge. |
| Session score | Calls settled in this window so far. Seconds overlap, so it is a rough guide. |

### The sixteen readings

Every reading is positive when price has been rising, and votes with its sign.
All are computed on closed 1s bars only.

These are the starting settings. The Experiments tab can switch another setting of the same reading in, and the tile then shows that setting's name.

| Tile | Definition | Warm-up |
| --- | --- | --- |
| Momentum 2s, Momentum 5s, Momentum 60s | Percent change over 2, 5 and 60 seconds, in basis points | 3, 6, 61 s |
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

### Running hit rate per reading

Under each tile, six cells score that setting alone. Its vote at one second is
checked against the move from that second's close to the close 5, 10, 20, 30, 60
and 300 seconds later. Each cell shows the share that matched: green at 52 or
more, red at 48 or less, a dot until ten calls have settled at that interval
(the 5 minute cell needs more than five minutes). Counts fade with a half-life
of two hours of ticks, so recent calls weigh most, and they are saved per coin,
so a new window carries on where the last one stopped. A neutral tile makes no
call, a flat outcome is not counted, and nothing is scored across a feed break.
Hover a cell for its count. Seconds overlap, so these are running reads and not
trade records.

### The weighted call

Each reading's say in the call is how far its hit rate over the next 30 seconds
is above 50%, as a share of all sixteen edges. A reading at or under 50% has no
say, unless inverse votes are turned on in the Experiments tab. The hit rate is the live one pulled toward the recorded one: the recording
counts as 300 calls, so a new window starts on the recorded rates and live
results take over within minutes. The weighted score is the sum of each
reading's say times its vote, from −100% to +100%.

On the recorded rates the two breakout readings carry 29% of the say between
them, because breakouts have the best record; MACD carries 2%.

Replayed without looking ahead on the last 40% of the base recording (rates
learned only from earlier seconds, starting rates from the first 60%):

| Call | Strong: right, share of seconds, average move | Lean | Mixed |
| --- | --- | --- | --- |
| One reading, one vote (the earlier call) | 53.3% ± 1.5, 34%, +0.77 bp | 50.7% ± 1.4 | 49.3% ± 1.9 |
| Weighted | 54.4% ± 2.0, 20%, +0.90 bp | 51.8% ± 1.4 | 50.0% ± 1.4 |
| Weighted, clear winners switched in (the cautious rule) | 54.4% ± 1.9, 23%, +0.86 bp | 51.8% ± 1.4 | 50.1% ± 1.5 |
| Weighted, highest hit rate switched in (the default) | 54.7% ± 1.9, 23%, +0.76 bp | 52.0% ± 1.4 | 49.6% ± 1.5 |
| Weighted, readings under 50% voting the other way | 54.6% ± 2.3, 15%, +0.70 bp | 51.5% ± 1.5 | 50.6% ± 1.3 |

Weighting gained about one point and calls "strong" less often. That gain is
within one standard error, and on the 43 minute live check there was no visible
difference (strong 53.8% ± 4.7 weighted against 54.3% ± 4.3 unweighted). Read
it as a small improvement in the read-out, not as an edge: the payout arithmetic
in [the study](../research/papers/SCALP-1S-STUDY.md) still needs a hit rate far
above these figures.

The replay and the window differ in ways that keep those figures a guide. The
replay's starting rates come from the first 60% of the recording; the window
ships rates from all of it. The replay starts each market with no record; the
window carries its record from one session to the next. The replay scores a
mixed score by its sign to report the mixed tier; the window shows no direction
for it. The replay skips recorded stretches shorter than ten minutes; the window
scores every second.

## The Experiments tab

The second tab keeps testing other settings of every reading, all the time the
window is open, on the same live ticks.

- **What is tested.** 380 settings of the sixteen readings. The readings with
  the most parameters have the most settings:

  | Reading | Settings | What is varied |
  |---|---|---|
  | MACD | 123 | 41 pairings of a fast average (3, 5, 8, 12, 16 or 20 s) with a slow one (10 to 90 s), each with a signal average of 5, 9 and 13 |
  | EMA cross | 51 | Fast 2 to 30 s against slow 5 to 120 s |
  | Parabolic SAR | 48 | Start and step each 0.005 to 0.05, cap 0.1, 0.2 or 0.4 |
  | Supertrend | 40 | Range of 5 to 60 s, multiplier 1 to 4 |
  | Momentum | 20 | 1 s to 5 min |
  | Breakout | 14 | 5 s to 10 min |
  | Slope, RSI, Z-score, range position, balance of power, ZigZag | 12 each | Windows of 2 s to 10 min; ZigZag 0.25 to 15 bp |
  | Efficiency | 11 | 5 s to 5 min |
  | Heikin-Ashi run | 1 | Has no setting |

  A MACD row reads fast / slow / signal, a SAR row start / step / cap.
- **At which intervals.** Each setting is scored at twelve: 3, 5, 10, 15, 20, 30,
  45, 60, 90 and 120 seconds, 3 and 5 minutes. These are not limited to the
  windows on the Live tab.
- **All settings.** One row per setting, one column per interval, each cell a
  hit rate in percent. A filled cell is a live result. A plain coloured number is
  the figure from the recording, shown until about two intervals' worth of live
  calls have settled. Rows are ranked at the interval chosen in **Rank by**, best
  current estimate first. ● marks a setting a tile uses. **Show** limits the
  table to one reading, for example the 123 MACD rows.
- **In use.** The sixteen tiles: the setting each one uses, its say in the call,
  its live and recorded hit rate at 30 seconds, and the best unused setting of
  the same kind with what the rule will do with it.
- **Switch settings.** Three choices, kept for the next window:
  - **Highest hit rate** (the default). Every 30 seconds each tile takes the
    unused setting of its kind with the highest current estimate over the next
    30 seconds, as soon as that is above the estimate of the setting it has.
    The estimate is the live hit rate, pulled toward the recorded one while
    live calls are few (the recording counts as 300 calls). There is no
    waiting and no margin, so a tile can change every 30 seconds, and any
    setting may be chosen, however many bars it needs.
  - **Only when clearly ahead.** The earlier rule. Both settings need at least
    40 independent calls' worth of settled 30 second calls (1,200 call-seconds,
    so at least 20 minutes); the challenger's cautious estimate (the lower end
    of a 90% Wilson interval) must be above the current setting's live rate;
    the challenger must be at least 52% right; the recording must not rank it
    below the current setting; and a tile that just changed is left alone for
    ten minutes.
  - **Never.** Tiles stay as they are.

  A setting never replaces another kind of reading, and no two tiles use the
  same one. Each switch is listed under **Switches**.
- **Warm-up.** The grid is ready 78 seconds after opening or after a feed
  break, whatever is switched in. A chosen setting that needs more bars than
  the window has (MACD 20 / 90 needs 270) leaves its tile on the starting
  setting until it has them; **In use** says which setting is waiting.
- **Readings under 50%.** **Sit out** (the default): a reading whose hit rate
  is at or under 50% has no say in the call. **Vote the other way**: its vote
  is turned round and counts by how far under 50% it is. A tile counted that
  way is marked ⇄.
- **Inverse-vote experiment.** Both versions of the call are made every second
  from the same sixteen readings, whichever is in use, and each is scored
  against the price 30 seconds later. The table shows the live hit rate of
  each one's strong calls and of its strong and lean calls together on this
  coin, beside what the replay of the recording gave. ● marks the one in use.
  The line under it names the readings that are under 50% at that moment.
- **Starting settings** puts every tile back; with **Highest hit rate** chosen
  they are picked again within 30 seconds, so choose **Never** first to stay
  on them. **Forget results** (two presses) throws away what was learned for
  this coin, including the inverse-vote record.

Switching and inverse votes change only the read-outs. They never touch the
order panel, an armed level or a press on the Jupiter page.

What was learned by an earlier version of the grid is kept: a saved record is
carried over setting by setting, and the new settings start from their recorded
rates.

What to expect from the default rule: many switches and no better call.
Replayed on the later part of the base recording it changed a tile's setting
1,994 times in 26 market-hours, about five times per tile per hour, and strong
calls were right 54.7% ± 1.9 of the time against 54.4% ± 2.0 with no switching.
On the two short live recordings it was 53.9% against 53.8%, and 47.6% against
49.6%. None of those differences is larger than its error. Settings of one
reading differ by a point or two over 30 seconds (MACD 12 / 26 / 9 was right
50.5% of the time on the recording and the best of the 123 MACD settings
51.6%), and a hit rate measured over two hours of ticks is uncertain by more
than that, so the highest of many rates is partly the luckiest. The setting a
tile shows is the one that has done best lately, not one known to be better.

What to expect from inverse votes: nothing to gain so far. Over 30 seconds no
setting was reliably wrong. On the first 60% of the recording 26 of the 380
were under 50%, the lowest at 48.9%, and betting against those on the rest was
right 49.7% ± 0.9 of the time. Inside the call, turning under-50% readings
round made strong calls 54.6% ± 2.3 on 15% of seconds against 54.4% ± 2.0 on
20%; on the first live recording 49.7% ± 5.4 against 53.8% ± 4.7. With the
default switch rule there is seldom a reading under 50% to turn round, because
each tile already holds the best setting of its kind. The live table is there
to show if that changes.

Processing: reading all 380 settings takes about one millisecond per second of
ticks in the window, and the whole study replays in about a minute on one
machine. No second machine is needed for a grid this size or one several times
larger.

What the intervals show on the recording: every reading is right more often
over a few seconds than over 30. The median setting was right 53.4% of the time
over 3 seconds, 50.8% over 30 seconds and 50.4% over 5 minutes; the best
breakout 63% over 3 seconds and 54% over 30. A higher hit rate over a shorter
interval is not a better trade: the move in 3 seconds is a fraction of a basis
point, positions cannot be closed before 15 seconds, and the 1000x payout pays
nothing on wins under 0.2 bp. The call therefore stays on 30 seconds; the tab
shows the other intervals so they can be judged.

Results are kept in the browser's local storage, one record per coin. Two
windows on one coin each save their own results and the last one to save wins.
A stored record that does not fit this version's grid, or holds counts larger
than a live record can reach, is ignored.

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

## On the Jupiter Perps page

The **Perps paper** overlay on a Perps market (`https://jup.ag/perps/long/USDC-HYPE`
and the other SOL, ETH, BTC, ZEC and HYPE routes) has the same **1s scalp**
button. It opens this window for that market with every read-out: the call, the
chart with its projection, the trend grid, the slope ladder and the Experiments
tab. The price is the same public oracle stream, which covers all five markets.

What the order panel does there depends on the market.

### HYPE and ZEC: entries and a window-run take profit and stop loss

Jupiter offers no take profit or stop loss on these two beta markets. The page's
own code renders the positions row's TP / SL cell as `-- / --` with the text
"Take Profit / Stop Loss is not available for HYPE" (or ZEC), and the venue's
public market terms at `https://api.gum.ag/app/perps/markets` list market,
limit and post-only orders only. So on these markets the window runs the take
profit and stop loss itself, as it does on 1000x.

| Step | What the window presses on the Jupiter page |
| --- | --- |
| Long or Short | The side switch if it is on the other side, a leverage preset if you chose one, **HALF** or **MAX**, then the form's own **Long/Buy** or **Short/Sell** button, once |
| A level is reached (Press Close mode) | That position's own **Quick close** button, once, then **Confirm** if the page asks "Close Entire Position?" |

- **Size** is half or all of the USDC the page shows as available. A quarter and
  three quarters are not offered: the page has no button for them, and the
  window never types an amount on this page, because nothing on it would prove
  the page took a typed figure.
- **Leverage** is Page (whatever the form shows) or two of the page's presets:
  10× and 25× on HYPE, 25× and 50× on ZEC.
- **Stop loss** must sit inside the liquidation price, which the window reads
  from the position's row. Before a position exists, the "¼ liq." chips and the
  notes use an estimate: 1 / leverage less the first maintenance tier (200 bp on
  HYPE, 100 bp on ZEC). At 25× on ZEC that is 300 bp.
- **Estimated result** is the leveraged move less both taker fees (3.5 bp of
  position size each way).
- **Which price.** Levels are judged on the oracle price the window watches,
  not on the page's own mark price. The window shows how far apart the two are,
  refuses to arm when they differ by more than 25 bp or when the page has not
  been read in the last few seconds, requires a stop to sit at least 25 bp
  inside the liquidation price, and sounds its "not protecting" alarm if the
  two drift further apart than that while a level is armed.
- **One position per market.** This venue keeps one net position per market,
  so while a position in the window's market is listed, Long and Short are
  off: a second order would add to, shrink or flip it.
- **Leverage "Page".** The leverage the form shows when you press must still be
  there at the submit press, or nothing is pressed.
- The order form must be on its **Market** tab and the **Positions** tab must be
  showing.

The same rails as on 1000x apply: Long and Short are locked in every new window,
alert-only is the default, only real clicks count, one request is never
repeated, the extension never signs, and "Close All" is never pressed. A close
request finds its position by market, side and entry price; it selects the
Positions tab if another tab is showing; it confirms only a "Close Entire
Position?" question that names the same market and that its own press caused;
and a window opened on one venue is refused by the other venue's page.

**The window must stay open.** The take profit and stop loss exist only while
this window and the Jupiter tab are open and the price stream is fresh. A close
is a market order and the wallet may still ask for approval; until it is
approved nothing closes. At 25× to 50× that is a real limit: treat the stop as
a helper, not as a guarantee.

**Not verified on the real page.** The order form's controls were read on the
live HYPE page on 2026-11-28. No position was open, so the position row and the
close steps were taken from the page's code alone, and neither an open nor a
close has been exercised. The first real use is the first live test of each
press. Start in alert-only mode with a small balance, and check that the
listed position, its entry and its liquidation price read correctly in the
window before relying on Press Close. If the page's markup differs, the bridge
refuses and says why; it does not guess.

### SOL, ETH and BTC: read-outs only

There the window presses nothing and its order panel is replaced by a note.
These markets have Jupiter's own **Add TP / SL** in the positions list, which
Jupiter runs without any window staying open (seen in the page's code; not
exercised). Pressing that control from the window is not built.

The read-out's figures were measured on the 1000x oracle price, not on the
Perps mark price, and the average move after a strong call (under 1 bp) is
smaller than the fees to open and close a Perps position: about 7 bp of
position size on HYPE and ZEC, more on SOL, ETH and BTC.

## Opening a position

In short, on the Jupiter 1000x tab (not the Perps page):

1. Put the Jupiter page on the market you want, in **Classic** mode, with its **Positions** tab showing, and connect your wallet there.
2. Press **1s scalp** on the overlay. The window must be opened this way; a window opened by its address alone cannot reach the page.
3. In the window choose **Size** and **Leverage**, and type a take profit and stop loss if you want them (or press **No TP/SL**).
4. Tick **Unlock**. Until then Long and Short stay off.
5. Press **Long** or **Short**. With **Confirm** ticked the first press arms the button and a second press within four seconds sends it.
6. Approve in your wallet if it asks. When the position is listed, the levels you typed are armed from its real entry.

The line under the buttons always says why they are off ("Long and Short are off: …") or that they are ready. The badge beside **Order** is only the take profit and stop loss watch: **TP/SL off** means no level is being watched and does not block an entry. **Arm** is for a position that is already listed; it is off while none is.

| Step | What happens |
| --- | --- |
| Unlock | Tick **Unlock**. Long and Short are disabled until you do, in every window: Unlock, Confirm and the size are never remembered, so each window starts locked, confirming and at a quarter. Hover a disabled button to see why it is disabled. |
| Size | Choose ¼, ½, ¾ or All of the funds available for the pay token selected on the Jupiter page. A quarter, half and all press the page's own **25%**, **Half** and **Max**. Three quarters has no page button: the window presses **Max**, reads the amount, types three quarters of it and waits for the page's own line under the amount to change. In every case the amount the page then shows must be within 85% to 100% of that share of the balance it shows, or nothing is pressed. |
| Leverage | **Page** uses whatever the Jupiter page's order form shows. **500×** or **1,000×** presses that preset on the page before the size is set, and refuses if the page does not switch. The choice is never remembered: each window starts on Page. |
| Levels | Leave **as** on *bp from entry* and type a take profit and a stop loss in basis points, or press **No TP**, **No SL** or **No TP/SL**. A stop loss at or beyond the bust distance (9.8 bp at 1,000×, 19.8 bp at 500×) is refused before anything is sent. |
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
  amount back. The leverage is the page's own: either what it shows, or its
  500× or 1,000× preset pressed for you.
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
- **A price typed as a distance is refused.** The two fields show their unit.
  In *bp from entry*, a number within 3% of the coin's price (71.90 with SOL at
  71.70) is refused with a prompt to switch **as** to *price*: read as a
  distance it would put the level about 0.7% away.
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
- **It cannot set an entry price.** An open fills at the oracle price recorded
  about two seconds after submission. A level in basis points is measured from
  that real entry. Leverage is limited to the page's own 500× and 1,000× presets
  or whatever the page already shows.
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

`npm test` includes the Python parity of all sixteen readings and all 380
experiment settings, the slope ladder and the payout arithmetic on recorded
oracle bars, the scoring, weighting, both switch rules and the inverse-vote call of the Experiments tab, the guard state machine, the
page bridge and the window ownership rules. `npm run e2e:scalp` loads the
extension into Chrome for Testing against a local stand-in for the Jupiter page
and a loopback oracle stream. It checks that the window opens on a real click
only, that the order form sits beside the chart and every tile and column has
hover text, that alert mode presses nothing, that close mode presses the row's
own Close exactly once after the hold lock clears and never "Close all", that a
stale price shows the unprotected warning, that Long and Short stay locked until
unlocked and need the confirming press, that a confirmed Long presses the page's
Max, types three quarters, presses Long once and arms the levels from the new
entry, that the slope gauge fills in, and that the Experiments tab lists 380
settings at 12 intervals with live results, filters them by reading and shows
the inverse-vote experiment while the call and the order panel stay on screen, that the window opened from a SOL, ETH or BTC Perps route shows the
read-outs with no order control, that on a ZEC Perps stand-in a confirmed Long
presses the page's side, preset, HALF and submit buttons once with nothing typed,
the levels are armed from the listed entry, and a stop presses Quick close once
and Confirm once, and that the mute button is kept. `--full` also waits out the warm-up.
It never visits the real site and connects no wallet.

Sources:

https://jup.ag/1000x?market=SOL&mode=classic

https://docs.jup.ag/user-docs/trade/1000x/trading.md

https://developer.chrome.com/docs/extensions/reference/api/tabs#method-sendMessage
