# soltui — SOL strategy console

A Textual TUI plus a macOS menu-bar indicator over the backtester. Its panes are grouped into five
destinations (Now, Signal, Research, Money, Library) plus Settings; see [Navigation](#navigation).
Structured like `~/dev/net-dns-monitor`: pure, tested logic modules with a thin
wiring shell.

> **No order path.** There is no order path in this package — no keys, no signing,
> no venue client, not even unreachable code. Every figure it shows is a
> historical simulation, a replay of one, or (Liquidity tab only) a figure read
> from the liquidity daemon's state files. See [Safety](#safety).

## Install and run

```bash
cd /Users/mitch.hudson/dev/solmargintrader
uv venv ~/.venvs/soltui -p 3.13
uv pip install -p ~/.venvs/soltui/bin/python -r backtester/requirements.txt -r soltui/requirements.txt
ln -sf "$PWD/soltui/bin/soltui" ~/.local/bin/soltui    # once; ~/.local/bin must be on PATH

soltui          # the console, from any directory (opens on Now)
soltui --classic  # the same console with the original tab bar
soltui app      # the macOS menu-bar indicator (needs rumps)
soltui serve    # the console in a browser window
```

### The menu-bar app bundle needs a framework Python

`soltui app` runs the indicator from the console venv. The double-clickable
`SolTUI.app` is different: it is a py2app alias bundle, and py2app's launcher can only
load a **framework build** of Python. uv's standalone CPython (what `~/.venvs/soltui`
uses) is not one, so build the bundle from a separate venv on Homebrew's python@3.13:

```bash
uv venv ~/.venvs/soltui-app -p /opt/homebrew/opt/python@3.13/bin/python3.13
uv pip install -p ~/.venvs/soltui-app/bin/python -r backtester/requirements.txt -r soltui/requirements.txt
~/.venvs/soltui-app/bin/python soltui/soltui-service build
```

The bundle records that framework through the stable `/opt/homebrew/opt` symlink, so
Homebrew patch upgrades do not break it. If the recorded framework disappears (the
python.org 3.13 install it was first built from did), the app dies with "A Python
runtime not could be located". `soltui-service build` now refuses a non-framework
interpreter and fails when the built bundle names no existing runtime;
`soltui-service status` reports the same check.

`soltui` is [`soltui/bin/soltui`](bin/soltui). It finds the repo through the
symlink, changes to the repo root and runs `python -m soltui.<module>` with
`$SOLTUI_PYTHON`, else `~/.venvs/soltui/bin/python`, else `python3`. Without the
launcher, `python3 -m soltui.tui` from the repo root still works.

The TUI needs price data. If a sweep reports "no data", fetch it:

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

## The menu-bar indicator

`status.build_title()` is a pure function, so what the bar shows is tested
without a macOS event loop. What you see, and why:

| State | Title | Why this and not something else |
|---|---|---|
| Idle | `◦ SOL: idle` | |
| Sweeping | `⟳ SOL: backtest 340/630` | While work is in flight, "how much is left" is the live question |
| Finished | `✓ SOL: last backtest +9.4%` | **"last backtest" is load-bearing** |
| Dry run open | `▷ SOL: paper +2.1% (12 fills)` | **"paper" is load-bearing** |
| Failed | `✕ SOL: error — no data` | Failures must be visible, not silent |

**Why every number carries a word.** A bare `+9.4%` in a menu bar reads, at a
glance, as *my money is up 9.4% right now*. There is no live account here. So the
source is always in the string, and a test asserts that exhaustively across every
phase rather than trusting review. If you add a phase that can show a percentage,
that test will fail until you label it.

Long titles clip from the **head**, never the tail, because the figure is at the
end — an earlier version clipped the tail and silently ate the number the
indicator exists to show. Its test is `test_clip_preserves_the_number_not_the_label`.

## Navigation

The console groups its panes by the question you bring, not as eighteen peer tabs. The design is in
`docs/design/soltui-v2/DESIGN.md`. The shell is `soltui/shell.py`.

| Key | Destination | Sub-views (the classic tab each one is) |
| --- | --- | --- |
| `1` | **Now** | Overview: Needs you (everything stale, failed or unseen, worst first), every coin, money tiles, activity, live prices |
| `2` | **Signal** | Call & metrics · Backtest · Forward test · All coins (the four Compound 5m sections) |
| `3` | **Research** | Backtest · Roster (Strategies) · Sweep (Queue) · Cumulative · Top 5 · Decide (Analyze) · Forward (Forwardtest) · Bots · Replay (Execute) · Dry run (Live Run) · Indicators (Signals) |
| `4` | **Money** | Aero LP (Liquidity) · P&L · Wallet, under a LIVE MONEY band |
| `5` | **Library** | Docs · Findings (Research) |
| `,` | **Settings** | Settings |

- `[` and `]` step through a destination's sub-views. Clicking a destination or a sub-view works too.
- `?` opens Explain for the focused field: the same text as F1, in a drawer that does not reflow the
  screen.
- `ctrl+p` opens the palette. It lists every view, the app's actions and all registry commands by
  name. A read-only command with no required parameters runs from the palette and shows a one-line
  result. Any other command (every write, including the LP Kill and Resume) opens the view that owns
  its button and focuses it, so confirm steps stay where they are.
- The strip under the top bar shows every background process: sweep, trainers, autopilot, LP daemon,
  price recorder, forward test and wallet scan. It refreshes every 5 s.

Every classic pane is still a pane of the one `#main-tabs` TabbedContent. A tab added later is filed
under Research automatically (`shell.with_extra_views`). `soltui --classic` shows the original tab bar.
The pre-v2 console is also preserved as the git tag `soltui-ui-v1` (branch `backup/soltui-ui-v1`).

## The tabs

Hover any field, button, table heading or table value for plain-language help.
The definitions explain the unit, give an example and name the main limitation.
This includes the Queue and Liquidity tables, signal parameters and public-wallet
settings. Indicator and strategy rows also explain their trading hypothesis.

The shared editor sits under every tab below an orange bar. Drag the bar to resize the
editor (ctrl+up / ctrl+down from the keyboard), double-click it for the default size, and
click **x close** at its right end to hide the editor; click the bar, drag it up or press
ctrl+e to bring it back. The size and open state are remembered in
`~/.config/soltui/tui.json`.

Press **F1** anywhere, including inside an input or the source editor, to open
the searchable glossary with help for the current control or selected column.
Search for terms such as **grid**, **Sharpe**, **CPCV**, **bps**, **APR** or **LVR**.
Use Tab to move to the help text, Page Up/Page Down or the mouse wheel to scroll,
and Esc to close it and return to the same control. Long explanations remain
available here even when a hover tooltip is clipped by a small terminal.

The glossary distinguishes the registered `grid` exposure staircase from the
extension's resting-order ladder. Closed winning grid cycles can coexist with
larger open losses; read total net account equity as well as realized P&L.

| Tab | What it does |
|---|---|
| **Settings** | Asset, interval, date range, capital, fees, fill delay, CPCV geometry, and the wallets to watch: public Solana, Base and Ethereum addresses, and extended **public** keys (`btc_xpub`, `ltc_xpub`, `doge_xpub`) for Bitcoin, Litecoin and Dogecoin. Each is validated (Base58Check and version bytes for an xpub); an `xprv`, a WIF key, a raw 64-hex string or a Solana secret-key array is refused with a message that private keys do not belong in settings, and the message never repeats the value. An xpub is shown as a short prefix everywhere (`settings.get`, the TUI, the API) and the config file is mode 600. A read-only *signing key source* row shows whether `~/.ssh/wallet.private` (the EVM, Ethereum/Base, key) and `~/.ssh/solana.private` (the Solana key) exist and are mode 600, by `stat` alone. **There is no field that accepts a private key.** Saved to `~/.config/soltui/`. Validation refuses look-ahead (`fill_delay < 0`), a `k >= blocks` split, and any non-dry-run mode. |
| **Strategies** | Every registered strategy on the left, your roster on the right. Add with params (`fast=20 slow=50`). Validation happens **on add** — an unknown name fails with the valid list, bad params fail at the form, not mid-sweep. The left table also shows each strategy's **test history** from the background sweep's results file: tested yes/no/n/a, times tested (distinct configurations), when last tested, and the card-preset result (median Sharpe, net return, trades) — never the best of many variations. Three buttons start the background worker at each card's own parameters: **Backtest selected**, **Backtest all untested**, **Backtest all**. Already-recorded configurations are skipped, and only one background sweep runs at a time. Results written before dates were recorded read `date not recorded`. |
| **Signals** | Read-only reference: each indicator's actual equation as implemented in `backtester/core/indicators.py`, plus what each family is for and *when it fails*. |
| **Forwardtest** | Paper-test every strategy, the roster or custom combinations. Forecast 1, 5, 10 and 30 minutes separately; inspect accuracy, unresolved calls and settings changes. |
| **Compound 5m** | Four sections: **Call & metrics**, **Backtest** (a *What is tested* paragraph, readable row names, buy & hold, net bps 1h/24h, and a **Frontier** button that tests every metric's strongest 2% of readings held 1 h-24 h), **Forward test**, **All coins**. Scores every metric from `5minleveragestrategies.json` (and the ones it lacked: higher timeframe, funding/premium/OI, order book, BTC lead, trend lifecycle, market-cycle phase) for the **next 5-minute bar**, -1 down to +1 up; families vote once, the regime reweights trend vs reversion styles, and cost / liquidation / shock / thin-market / event / news gates force FLAT. Double-click a metric to switch it on or off (or select it and press Space); a single click selects it and shows its full detail (formula, parameters, evidence, adoptions) in the editor below, as do coin, backtest and forward rows; **Autopilot** (on by default) runs tuning, adopts tuned settings per coin by itself and keeps every coin training (with `python -m soltui.compound_agent install` for a LaunchAgent); **Toggle on/off**, edit `weight=` and parameters, and aggregate settings (`entry`, `exit`, `leverage`, `fee_bps`…). **Signal now** scores the latest closed bar from public data; **Backtest selected** runs the compound and each enabled metric alone on cached 5m data (OOS hit rate, z, oracle net bps, engine return after fees); **Forward tick** / **Auto-forward** record a call per closed bar and resolve it when the next bar closes; **Start unattended training** runs that in a detached background process that keeps going after the console closes. Calls are sized to the Settings Solana wallet (`wallet (live)`), and a status line under the buttons summarises each backtest run in plain words. No order path. See `docs/COMPOUND-5M.md`. |
| **Bots** | The **grid bot** (the resting ladder the extension trades, `backtester/core/gridsim.py`), the **triangle arbitrage bot** (three-leg USD cycles through Coinbase cross pairs, `core/trianglesim.py`) and the **DCA bot** (base order, deeper safety orders, one take-profit above the average entry, `core/dcasim.py`). **Backtest** starts the selected bot on one or several ticked **Coins** (default: from the beginning of the cached data) and shows a per-coin table, what it set from the price at the start (ladder levels, safety orders, watched triangles) and what it made, beside buy-and-hold. **Start forward test** runs it in dry-run from now on the live recorded price stream; **Auto-optimize (all coins)** opens a window listing the configurations under test with live progress, runs them on every cached coin, adopts one only if it beats the current settings out of sample by a sign test, and then says exactly which settings changed and whether they were saved, with per-coin results. Each re-run searches wider. A **Live prices** section shows every streamed market's bid, ask and spread; prices record automatically. All simulation; no order path. See [The Bots tab](#the-bots-tab-and-the-price-stream). |
| **Backtest** | **Strategy to backtest** picks the whole roster or one roster strategy (the roster is the right-hand list on the Strategies tab, shown on the line beside the picker); **Run backtest** runs that pick through CPCV on a worker thread. Shows median path Sharpe, **IQR**, **% paths positive**, **backtest median net %**, trades. Cancellable. **Backtest untested + little-tested** starts the background worker at once on every strategy never tested or with fewer than three recorded configurations (card parameters plus near variations, every horizon); its progress shows under the buttons and on the Queue tab. |
| **Top 5** | The five recommended configurations with their evidence and off-asset transfer tests. |
| **Live Run** | Launches the extension's dry-run tool. A Top 5 preset list fills the strategy; the result shows `dry-run net %`. |
| **Execute** | Dry-run replay. Step a simulation bar by bar and see the fills a strategy *would* have made. A Top 5 preset list selects a configuration (its composite replays on the series it was fitted on); every figure says `paper net %`. |
| **Analyze** | What every strategy would decide for one coin at one moment. A Top 5 preset judges only that configuration with its parameters. The headline carries the asset's `backtest data price change`. |
| **Wallet** | Read-only discovery of what the two Settings addresses hold: native SOL/ETH, SPL tokens (Token and Token-2022), stake accounts, ERC-20 balances, LP position NFTs, and the contract or account each holding lives in, with explorer links. Per-chain and total USD, every figure `wallet (live)`. Airdrop-looking tokens are flagged and excluded from totals. See [The Wallet tab](#the-wallet-tab). |
| **P&L** | Profit and loss over 24h, 7d, 30d, 90d, YTD, all or a custom start/end. One section per source (`backtest`, `paper`, `dry-run`, `dry-run LP`, `live LP`, and the separate `wallet (live)` value-change section) with net and gross P&L, fees, slippage, borrow/funding, realized vs unrealized, win rate, expectancy, daily series with cumulative curve, max drawdown and recovery, best and worst day/week/month, and a by-strategy / by-asset attribution. See [The P&L tab](#the-pl-tab). |
| **Queue** | Starts and reads the low-priority background sweep. Start/Stop/Refresh, a live status line, a ranked table and a below-the-floor table. |
| **Liquidity** | Read-only view of the Aero (aero.xyz) liquidity daemon's state files (`$AERO_LP_HOME`, default `~/.aero-lp/`): mode badge (LIVE is red, dry-run is yellow), kill-switch banner ("Kill switch ON — bot paused"), idle vs deployed USD, totals; Positions, Scout (top pools by modelled net APR), Experiments (arms side by side, winner marked) and Recent actions (newest first, basescan tx links) tables. Refresh / Kill / Resume buttons (`F5` refresh, `F8` kill-resume toggle while the tab is open); re-reads every 15 s. |

### Strategy roster and Forwardtest

On **Strategies**, focus a row in the left table and press **Space** to add it or remove its
matching roster configuration. With multiple custom versions, use the right table and press
**Space** on the version to remove. **Add all to roster** fills in missing
strategies with the Signal defaults and keeps custom entries.

On **Forwardtest**, choose **All strategies**, **Roster only**, or **Combinations only**. Enter
a combination such as `rsi,macd; breakout,obv_trend` and select its rule. Each group separated
by a semicolon is a separate trial. Use exact roster labels to distinguish custom versions.
**All four** forecasts 1, 5, 10 and 30 minutes; choose a single duration to issue only that
forecast. Start uses the asset and round-trip fee/slippage threshold from Settings. Edits take
effect after stopping and starting again. Press Ctrl+E to make more room for the results
when the shared editor is open.

Each trial reads closed Coinbase one-minute candles and records UP, DOWN or FLAT before
the next unopened minute. It scores that window from its first open to its last close,
marks moves within the cost threshold FLAT, and waits if any candle is missing. For each
horizon, only one window is predicted at a time. Accuracy is a directional classification
score. A rule that always stays flat or always holds can serve as a comparison.

Each strategy or combination and horizon has its own active settings. When it misses, the
trainer considers nearby settings that made the correct call at the same time. It uses the
Compound Beta comparison: at least 300 paired observations, probability above 95%, and a
two-day cooldown after each change. Parameters without a usable alternative stay unchanged.
Learning only changes that paper trial's future calls.

The app checks prices while the session is running, including when another tab is open.
Stop or close the console to stop checking. The SQLite file in the local SolTUI configuration
directory retains predictions, shadow calls, outcomes and adoptions. Restarting with the same
trial and evaluation code resumes that record. Old pending calls can settle only if their exact
candles are still available. No wallet or order is involved.

### The Bots tab and the price stream

**The price stream.** `soltui/pricefeed.py` is a standard-library WebSocket client (RFC 6455; no
new dependency) on Coinbase Exchange's public feed, `wss://ws-feed.exchange.coinbase.com`. It
subscribes to every USD market of the cached coins that Coinbase lists plus every cross pair
among them (24 markets on 2026-11-08), on two keyless channels: `level2_batch`, from which it keeps
each market's book and so its true best bid and ask with sizes, and `ticker`, for the last trade.
The ticker's own bid/ask changes only on a trade; on 2026-11-08 the SOL-BTC ticker quote was 89
minutes old while the book had moved, which is why books are used where they exist. Once a second
it writes a snapshot of every market to `~/.config/soltui/prices/YYYY-MM-DD.jsonl.gz` (one gzip member
per flush, so a crash loses at most ten seconds) and replaces `prices/latest.json`.

**Recording is always on**, because the recording is what the bots backtest and train on. The
console, at start and then every minute, makes sure of it (`prices.ensure`): it installs the
LaunchAgent `com.mitchhudson.soltui.pricefeed` (`RunAtLoad`, `KeepAlive`, from the main checkout)
if it is missing, so recording survives a closed console, a crash and a reboot; where it cannot
(a git worktree, no `launchctl`) it starts a detached `python -m soltui.pricefeed record`. There is
no Stop button. One `flock` on `prices/recorder.lock` keeps it to one recorder; the agent's process
waits on that lock (`--wait-lock`) instead of exiting, so it never thrashes. By hand:
`python -m soltui.pricefeed status | install | uninstall | ensure`. About 50-200 KB/s of public market data, and
about 15 MB a day on disk (measured 2026-11-08; nothing prunes it).

**Backtest = "had I started it then".** At the chosen start the bot reads the price at that
bar's close and sets itself up from it; the simulator then runs it over the following hourly
bars with the backtester's pessimistic rules (nothing fills on the bar that placed it, buys
before sells, adverse slippage, fees on every fill). With no start it begins at **the beginning
of the data**: several 1m caches reach back to 2019 while the 1h files start in 2023, so the
minutes resampled to hours (an hour needs 30 of its minutes) are used before the 1h file starts
and native hours after. Gaps of up to 48 missing hours are bridged with flat bars at the last
close and counted (nothing fills during them); a longer gap ends the run, and with no start the
backtest begins after the last such gap and says so (only ZEC's early history has them). Tick
several **Coins** to run the same bot and start on each; the per-coin table lists every one,
including the coins that could not run and why. The triangle bot backtests on recorded bid/ask snapshots; for a time
before the recording it falls back to a **candle proxy** (Coinbase 1m closes with an assumed
half-spread, labelled `candle-proxy`, executed a minute later), which bounds noise rather than
measuring an opportunity.

**Forward test = the same bot on the future, in dry-run.** It starts now on the current
settings and, on every refresh, replays what the recorder captured since (incrementally: only
new gzip members are read). Grid and DCA run on one-minute mid-price bars built from the
snapshots; a gap of up to two minutes is bridged with flat bars, and a longer one ends the
coverage at the gap because what the market did unseen is unknown.

**Auto-optimize.** Pressing it opens a window listing every configuration under test, with live
progress. Run 1 tests a fixed, small grid of settings per bot (12 grid, 36 DCA, 12 triangle
configurations plus the current one); **each later run tests 12 more configurations than the first,
skips every configuration an earlier run tried, adds the one-setting neighbours of the current
settings and samples further from them** (the reach grows with the run number until it spans each
setting's whole range; the sampler is seeded by bot and run, so a run is reproducible). They run on
every cached coin over six 30-day windows of hourly bars (every recorded triangle over hour windows,
for the triangle bot). The older three windows rank the candidates; the newer three decide. The
train winner is adopted only when it beats the current settings in significantly more test cells
than it loses (one-sided sign test, p < 0.05, at least ten decided cells) with a positive median
gain. When the run ends the window says **SAVED** with every changed setting (`before -> after`)
and the file it was saved to, or **NOT SAVED** and why, and lists per coin the windows it ran and
the pick against the current settings; a toast says the same. The run history is in
`~/.config/soltui/bots/optimize-history-<bot>.json`. On 2026-11-08, over 23
coins, neither the grid (p = 0.78) nor the DCA bot (p = 0.45) had a reliable winner, so both kept
their defaults. That is the expected answer in this repo (Stele KNOW-561, KNOW-871).

### Searching the repo from the Docs tab

The Docs tab lists every file in the committed index. Its search box queries that index three ways:
**keyword** (BM25: exact terms, offline), **semantic** (meaning, using `mxbai-embed-large:latest` through the
local Ollama) and **hybrid** (both, rank-fused). Press Enter or **Search**; it never searches per keystroke.
An empty box and Search restores the file list.

Nothing is loaded until the first search: the keyword postings, the embedding matrix and the ~670 MB model
all stay out of memory until then. **Free search memory** drops them and asks Ollama to unload the model
immediately. A semantic or hybrid search starts Ollama if it is not running, and if it cannot, falls back to
keyword and says why. The model is never downloaded for you: `ollama pull mxbai-embed-large:latest`.

Each search also runs the idle index check (`index/idle.py`), which rebuilds an out-of-date semantic index in the
background when the machine is idle, writing only gitignored files. See `index/README.md`. The same search is
the registry command `docs.search`, so the CLI, API and extension get it too.

### Top 5 presets and net %

`top5.presets` (one registry command, so the TUI, CLI, API and extension see the same list) turns each Top 5 row
into a preset: label, member signals with the SOL-tuned parameters read from `research/sweep.py` `HORIZONS`
(never copied), the series it was fitted on and its evidence. Clicking one in Analyze, Live Run or Execute only
fills that tab's fields; running still goes through the tab's own button.

Net % is `final / initial - 1` everywhere (`soltui/netpct.py`). Every text form names its source:
`backtest median net +9.4%`, `paper net +2.1%`, `dry-run net +0.7%`, `live LP net +1.2%`. A figure with no base
(no capital, no deposit) is a dash, never `0%`. `test_tui_presets_pnl.py` walks every table in the app and fails
on a percentage with no source word.

### The P&L tab

`pnl.summary`, `pnl.series` and `pnl.breakdown` take `window` (24h, 7d, 30d default, 90d, ytd, all), `start` /
`end` (custom, UTC; a date `end` includes that whole day) and `source`. Window edges are inclusive. The days of a
series add up to the window's net P&L because the first day is measured against the equity before the window.

* **Sources.** `backtest`: one full-history run per roster strategy, each on the Settings capital (a section adds
  independent equal-capital runs, so its net % is total net over total capital). `paper`: the open Execute replay
  up to its cursor. `dry-run`: the extension's journal (`~/.solmargintrader/journal.json`, override with
  `SOLTUI_JOURNAL`), FIFO round trips net of fees and carry; it records no capital, so no %. `dry-run LP` /
  `live LP`: the liquidity daemon's `ledger.sqlite` snapshots (opened read-only) when they exist, else the
  cumulative `status.json` figure, which is marked *not windowed* because it cannot be cut by date.
* **Simulated and real money are never summed.** Each source is its own section; the report has no total. The
  daemon's own mode picks `live LP` (real) or `dry-run LP` (simulated); an unknown mode is `reported LP`, filed
  under neither.
* **Definitions.** Gross = net + fees + slippage + borrow paid in the window. Realized = net result of fills that
  closed risk in the window; unrealized = the rest. Win rate and expectancy are over those closes. Contribution is
  percentage points of the section's net %; a section's rows sum to it exactly.
* **A backtest has historical dates.** A `30d` window ending today finds no backtest data when the cached series
  ended earlier; the section says where its data is (`its data covers ... to ...`) instead of showing zeros.

### The Wallet tab

`portfolio.scan` (`chain`, `tokens`, `record`) reads the public addresses in Settings. SolTUI never
loads a private key, signs a transaction or stores API credentials. For Base discovery it can invoke the
already configured Coinbase Developer Platform CLI (`cdp`); that separate CLI manages its own API authentication.
The same scan powers the Wallet tab, CLI and HTTP API.

* **Solana.** `getBalance`; `getTokenAccountsByOwner` under both Token programs; stake accounts via
  `getProgramAccounts`; names and USD prices from Jupiter's keyless APIs.
* **Base.** `eth_getBalance(address, "latest")` reads native ETH. The configured `cdp data evm token-balances`
  command discovers native and ERC-20 balances, following every `nextPageToken` (100 rows per page, at most
  25 pages). SolTUI finds `cdp` on PATH or in Homebrew's standard locations. No separate SolTUI credential
  setup is needed on a machine where CDP already works. See [the balance query recipe](../docs/BASE-WALLET-QUERIES.md).
  If CDP is unavailable, the scanner tries Blockscout, including its continuation pages. Built-in tokens,
  daemon tokens and explicitly requested `tokens=[...]` are checked by `eth_call` to `balanceOf`; current
  RPC balances win over indexed balances. Other contracts are never called. Indexed balances remain
  labelled as indexed when an RPC read fails. USD prices come from DefiLlama (confidence at least 0.5),
  then DexScreener. NFT position managers and daemon position values retain their existing checks.
* **Honest limits.** If CDP and Blockscout fail, only available pages and known/requested tokens can be
  checked. Errors appear in the Wallet summary, mark the scan partial, and mark its total incomplete.
  Missing or malformed replies never become a zero balance. A later page failure retains earlier pages.
  Requests, CLI subprocesses and pagination have deadlines/limits; CLI stderr is never displayed.
* **Airdrops.** Unrecognized indexed tokens are displayed with a flag and excluded from totals until
  explicitly requested or trusted by the built-in/daemon lists. Spam wording still flags requested tokens.
  SolTUI reads their indexed metadata and never calls their contracts or visits their sites.

* **Ethereum.** `eth_address` is read on mainnet: `eth_getBalance` plus `balanceOf` for 12 well-known tokens
  (no indexer, so a token outside the list is not found; the scan says so). Prices come from Coinbase's public
  spot endpoint.
* **Bitcoin, Litecoin, Dogecoin from an xpub** (`soltui/hdwallet.py`, `soltui/utxo_scan.py`). Addresses are derived
  on this machine by BIP32 public derivation (stdlib only; chain 0 receive and chain 1 change, gap limit 20) and
  only addresses are sent to the explorers: mempool.space then blockstream.info for Bitcoin, litecoinspace.org for
  Litecoin, BlockCypher for Dogecoin (20 addresses a request). A plain `xpub` does not say which address style the
  wallet used, so Bitcoin and Litecoin try P2PKH, P2SH-P2WPKH and P2WPKH and keep each style that has history; a
  `ypub`/`zpub` tries only its own; Dogecoin is P2PKH. Results carry per-chain balances, the script types found
  and the number of addresses derived, never the addresses. A failed explorer call stops that branch and the
  result is `partial` (the balance is then a lower bound). A balance with no USD price is unknown, not zero: it
  stays out of the total and `unpriced` names it.
* **History and monitoring.** `portfolio.snapshot` (and an all-chain `portfolio.scan`) appends one timestamped
  per-chain snapshot to `~/Library/Application Support/soltui/portfolio/snapshots.jsonl` (mode 600; balances by
  symbol, prices and USD, no addresses or xpubs). `portfolio.changes` reports balance changes between snapshots (a
  chain that read partially or failed in either one is skipped, because a failed read looks like a balance falling
  to zero). The hourly LaunchAgent `com.mitchhudson.soltui.portfolio` runs `portfolio.snapshot`
  (`python -m soltui.portfolio_agent install|uninstall|status`; the plist lives in `~/Library/LaunchAgents`, where
  the automation watchdog finds it). The TUI and the menu bar show one line when a balance changed since the
  wallet was last viewed (`portfolio.notice`). The P&L tab shows the snapshots as a separate `wallet (live)`
  section: the *change in wallet value between complete snapshots of the same set of wallets*, which includes
  deposits, withdrawals and price moves and is not a trading P&L (gross, realized and unrealized are blank for it).
  It is never combined with a simulated figure.
* **Extension.** `wallet.addresses` returns the public Solana and EVM addresses only; the extension dashboard's
  "Use soltui Solana address" button fills the Wallet pubkey field from it and the owner still clicks Save.

Tests use recorded replies (`soltui/tests/fixtures/wallet/`), never the network.

### The Liquidity tab — a window onto a daemon, not a controller

`liquidity/` (the `aero-lp` daemon) manages the positions and writes
`status.json` (`aero-lp-status/1`) and `scout.json` (`aero-lp-scout/1`); the
contract is `liquidity/STATE_FILES.md`. `soltui/liquidity.py` is the pure reader
and formatter. A missing, corrupt or unknown-schema file shows "no data" and never
raises. If `generated_at` is older than three minutes the summary says the daemon
may be down.

Same labelling rule as the menu bar: P&L and APR columns say `live` or `dry-run`
(whichever the daemon reports; an unknown mode is `reported`, never guessed
`live`), and scout figures say `modelled`, because they are estimates, not results.
`test_every_percentage_column_carries_a_source_word` enforces it.

### The Queue tab — a sweep you interrupt, not one you finish

`python3 -m soltui.bgworker --asset SOL` grinds through parameter space in a
separate process at background QoS (`taskpolicy -b`, nice 19), so it can run
while you use the machine. The TUI only *reads* what it writes — the sweep keeps
going with the console closed. Resume requires a matching proof sidecar for the
settings, date range, CSV bytes and relevant Python source. Legacy or changed evidence
refuses before appending results; it never silently mixes runs or replaces old history.
Use an explicit fresh `--results-path /absolute/path/results.jsonl` for a new CLI run.
The Queue pane reads the default results path; it does not discover custom CLI paths.
Stop sends a nonce-bound request to the current worker's private control socket. It
never signals a PID taken from an old PID file. The worker consumes requests between jobs.

Because it is always interrupted rather than completed, the **order** is the
design, not the extent: every strategy card's own published preset is evaluated
before any variation of one, then near variations (0.75x/1.5x), then far
(0.5x/2x). Presets and the promise ordering come from the cards themselves
(`success_likelihood`, per-horizon presets), never a copy.

Two tables, and the split is the point. Ranking is out-of-sample CPCV median
Sharpe; anything under the 10-trade evidence floor is **listed but never
ranked**, because a Sharpe from three trades sorted descending is a ranking of
luck. The status line reports how many rows are *rankable*, not how many were
evaluated — the second number flatters the sweep.

```bash
python3 -m soltui.bgworker --plan --asset SOL      # what it would run, in order
python3 -m soltui.bgworker --asset SOL --max-tier 0  # presets only
```

**Missing price data is reported before the sweep, not during it.** The queue
interleaves 1h and 1d jobs by promise, so an absent `data/SOL_1h.csv` would
otherwise surface minutes in — with the whole short horizon quietly absent from
the results while the pane still said "running". The tab names each missing
series and the exact `backtester.core.fetch` command, and **Fetch missing data**
runs those commands for you.

That button is the only network action in this package, and it stays the
separate explicit step `CLAUDE.md` requires: it runs `backtester.core.fetch`,
writes a local cache, and does **not** start a sweep as a side effect. A sweep
missing one interval still runs every job at the intervals it does have, and
says so rather than reporting a clean "done". Note the hourly series is refused
by the loader unless `--allow-gaps` is passed (it has disclosed gaps). Even with that
loader flag, the simulation engine refuses irregular intervals rather than guessing
carry cost or annualization. Use a complete cache for simulation. When a fetch leaves
a series missing, the tab points at `~/.config/soltui/bg/fetch.log`.

Inspect it while it runs: `~/.config/soltui/bg/` holds `results.jsonl` (one JSON
object per job), `state.json` (progress) and `worker.log`.

### Read the Backtest tab correctly

Median Sharpe alone is not the answer. A median of `+0.5` with an IQR of `1.4`
straddles zero heavily, and `% paths positive` below ~70% means the sign of the
result depends on which regime you happened to sample. Both columns are shown for
that reason. The measured PBO for this strategy set is 0.43–0.46 against a 0.500
pure-noise control — so treat *ordering* as weakly informative at best, and read
the distribution.

## The command bridge: one registry, four surfaces

Every action in the console is a command in `soltui/commands.py` (`soltui list` prints them all).
The TUI, the CLI, the HTTP API and the Chrome extension's native-messaging host all call
`dispatch(name, params, surface)`, so one call returns one envelope, byte for byte, wherever it came from:

```
{"ok": true,  "command": "roster.list", "result": {...}, "error": null}
{"ok": false, "command": "...", "result": null, "error": {"code": "bad_params|unknown_command|forbidden|failed|timeout", "message": "..."}}
```

```bash
soltui list                                         # every command with its parameters
soltui call roster.list
soltui call roster.add --param name=rsi --json '{"params": {"period": 9}}'
soltui call liquidity.resume --param confirm=true   # see the confirm gate below
soltui api --port 8788                              # http://127.0.0.1:8788/v1/<command>
soltui host-install install                         # register the Chrome native host
```

- **Confirm gate.** `liquidity.resume` deletes the aero-lp `KILL` file, which removes a safety stop on a
  real-money daemon. It refuses with `forbidden` unless `confirm` is the boolean `true`, on every surface;
  the TUI's Resume button asks you to press it twice within 10 seconds. `liquidity.kill` only adds the stop
  and needs no confirm. No command moves funds: soltui has no keys, signer or venue client.
- **API access.** Binds `127.0.0.1` only. Every route except `GET /v1/health` needs
  `Authorization: Bearer <token>`; the token is in `~/Library/Application Support/soltui/api-token`
  (mode 600, created on first run). A request with an `Origin` or `Sec-Fetch-Site` header is refused, since a
  web page can post to localhost. `GET` runs read-only commands only; `POST` takes a JSON object of params.
- **Native host** `com.mitchhudson.soltui` (`soltui/native_host.py`): Chrome's 4-byte little-endian framing,
  ops `ping`, `list`, `call`, `buildHash`. `buildHash` hashes the extension's manifest and `src/` so the
  extension can reload itself when its source changes. A reply over Chrome's 1 MB limit comes back as a
  `failed` envelope that points at the CLI or API. `soltui host-install install|uninstall|status` writes the
  wrapper script (`~/Library/Application Support/soltui/native-host/soltui-native-host`, running
  `~/.venvs/soltui/bin/python -m soltui.native_host`) and a manifest in each installed Chromium browser,
  allowing extension `pnokcppamfghgaimmmghoegjllhonhbh` plus any ids in `SOLTUI_EXTRA_EXTENSION_IDS`.
  Chrome loads host manifests at launch, so restart it after the first install.
- **Call log.** `dispatch` appends one line per call to `~/Library/Logs/soltui/calls.jsonl`:
  `{ts, surface, command, ok, error_code, ms, params_keys}`. Parameter *keys* only, never values; rotated at
  5 MB. The TUI's timer-driven refreshes are not logged, calls anyone asked for are.
- **State.** Mutating commands persist (roster with its params, signal defaults, settings), so a roster built
  through the API is the roster the TUI shows. The dry-run replay (`paper.*`) and the sweep live in the
  running process: use them through the TUI, the API server or the native host, or give `paper.start` a
  `bars` parameter for a one-shot CLI replay.

`soltui/tests/test_bridge_parity.py` walks the registry and proves byte-identical envelopes across the four
surfaces for every command; `test_bridge_buttons.py` fails when a TUI button is not a registry command.

## Safety

`CLAUDE.md` for this repo states: dry-run is the default, the extension installs
disarmed, and *"never change a default so that a fresh install can place an
order."* This package holds to that:

- **No order path exists.** Not stubbed, not disabled — absent. `grep` the package
  for a venue client and you will find none.
- **`config.MODES` contains only `dry-run`.** A config selecting `live` is refused
  by `validate()` with an explanatory error.
- **`armed` cannot be inherited.** Setting it requires an explicit second
  acknowledgement flag, so an old config file cannot silently arm a future build.
  Nothing in this build reads `armed` for anything.
- **The Execute tab is a replay, not a live loop.** Stepping bars and computing
  fills would create a *second* order-execution path alongside
  `backtester/core/engine.py`, outside the coverage of the engine's known-answer
  tests, and the two could diverge into wrong money. Instead `paper.py` runs the
  tested engine once and exposes a cursor over the result.
- `summary()["live_orders_placed"]` is structurally always `0`, and a test asserts
  it so a regression is loud.
- **The Bots tab simulates.** Its grid, triangle and DCA bots run the backtester's simulators
  over cached bars or the recorded stream; `test_bots.py` and `test_pricefeed.py` assert that
  neither module names a key file, a signer or an order call. The price recorder reads public
  Coinbase market data only and writes only under `~/.config/soltui/prices/`; the bots write only
  under `~/.config/soltui/bots/` (settings, results, forward-test state, optimize reports, and the
  candle-proxy cache).

Adding live execution later means routing through
`extension/src/core/commands.js` and its risk rails as separate, explicit work —
not extending this package.

## Tests

```bash
python3 -m unittest discover -s soltui/tests -t .        # see docs/DEVELOPMENT.md for the current count
python3 -m unittest discover -s backtester/tests -t .    # 119 tests
```

The TUI tests mount the real app through Textual's `run_test()` headless harness
and click real buttons, so a crash-on-mount is caught rather than shipped. Two
genuine bugs were found this way: a timer that queried a widget during teardown
and took the app down with it, and the title-clipping bug above.

## Layout

```
soltui/
  status.py    pure: AppState, build_title(), build_menu_summary()
  config.py    pure: Settings, validate(), load/save
  roster.py    pure: Roster add/remove, validated against the strategy registry
  paper.py     pure: PaperSession replay cursor over one backtest
  runner.py    worker thread: roster -> CPCV rows, progress for the indicator
  tui.py       Textual app, one tab per pane (presentation only)
  bgqueue.py   background sweep: job list, ordering, file contract, leaderboard
  bgworker.py  the background sweep process itself (python3 -m soltui.bgworker)
  bgcontrol.py spawn/stop the worker; the liveness lock
  liquidity.py pure: read/validate/format the liquidity daemon's state files; KILL toggle
  bots.py      the Bots tab: grid / triangle / DCA bot configs, backtest, forward test, auto-optimize
  bots_screens.py the Bots tab's coin picker and auto-optimize window (presentation only)
  pricefeed.py the streaming price recorder: stdlib WebSocket, Coinbase level2_batch + ticker, gzip JSONL
  app.py       rumps menu-bar shell (wiring only, lazy rumps import)
  commands.py  the command registry: dispatch, envelope, confirm gate, call log (every action lives here)
  reference.py static Research/Signals tab content, served by research.get / signals.reference
  cli.py       `soltui call` / `soltui list`
  api.py       `soltui api`: loopback HTTP, bearer token, browser requests refused
  native_host.py, native_host_install.py   Chrome native-messaging host and its installer
```

Anything that makes a decision lives in the pure modules. `tui.py` and `app.py` are
deliberately dumb, which is what lets the logic be tested without a terminal or a
macOS event loop.
