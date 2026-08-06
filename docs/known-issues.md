# Known issues

Active limitations, in descending order of how much damage they could do. Nothing here is
speculative — each item is either stated in the code or was reproduced.

There are no `TODO`, `FIXME`, `XXX` or `HACK` markers anywhere in
`backtester/`, `research/`, `extension/` or `soltui/`. This page is the substitute for
grepping for them.

---

## Extension — the money path

### No live order has ever been placed

The whole live path is unexercised against a real venue. Every test and the headless dry
run go through fakes. Do not present any live-path behaviour as working; read the
**Verification status** section of `extension/README.md` before extending it.

**Consequence:** the first real order is the first real test.

### The Trigger order-list response envelope is guessed

Reconciliation reads the venue's live order list at the top of every tick and treats it as
the source of truth. The shape of that response was inferred from documentation, not
observed. If the real envelope differs, reconciliation is wrong in the most consequential
place in the system — and because neither Jupiter call logs its request or outcome
(`docs/logging.md`, gap 1), the failure would be hard to diagnose after the fact.

**Mitigation in place:** an intent that was submitted but is not found live becomes
`unknown` and is **never** auto-retried. That converts a mis-parsed envelope into a stalled
rung rather than a double-fire.

### Fee attribution is unconfirmed

`src/jupiter/attribution.js` has never been checked against a real fill. Reported P&L may
attribute fees differently from the venue.

### Unlogged paths

Four, listed with evidence in `docs/logging.md`: every Jupiter call, per-rail risk
rejections, the `unknown` intent transition, and a thrown tick (which goes to
`console.error` and does not survive service-worker eviction). Fixing these is
`code-deep-optimizer` pass S5 work.

### Loading unpacked cannot be automated

`chrome://extensions` needs a human, so the MV3 load path is never covered by CI. The
headless dry run (`tools/dryrun.js --ticks 8 --osc 6 --offline 100`) stands in for it and
is the integration gate.

---

## Backtester and research

### The cached data is a snapshot with no freshness contract

`data/` is gitignored and regenerable, and nothing in a CSV records when it was fetched.
`research/decide.py` prints the decision bar's age in bars and says `STALE` past two, which
is a mitigation, not a fix — the underlying cache still has to be refetched by hand.

As of the last check, `data/SOL_1h.csv` ended 40 hourly bars behind wall clock while
`SOL_1d.csv` was 1.7 daily bars behind. Both were "current" by file mtime.

### `data/SOL_1h.csv` has two gaps larger than one bar

Reading it requires `--allow-gaps`, which is a knowing acceptance of an incomplete series.
The largest gap is 21,600s where 3,600s was expected, after epoch 1761404400. Any
statistic computed across that boundary spans a hole.

### `data/JLP_spot.csv` is not a bar series

One row, columns `timestamp,iso,mint,usd_price,source` — a Jupiter price snapshot from
`core/archive_price.py`, not OHLCV. Bar tools refuse it by naming the missing columns,
which is correct behaviour, but the filename invites the mistake.

### Coinbase is the only market-data source

Binance is geo-blocked from here. That means a single vendor's outage or history revision
moves every backtest, and Coinbase's non-OHLCV row ordering has to be handled on the way
in.

### No registry default emits a short

Every registered strategy's default parameters are long-or-flat; only
`ma_crossover(short_when_below=True)` can go short, and nothing constructs it that way.
So `research/decide.py --allow-short` widens the stated exposure bound and changes nothing
else, and `HOLD-SHORT` is unreachable through that CLI. A test asserts this, so a future
shorting default will fail rather than quietly make the help text wrong.

### The full readout is slow on hourly data

Every strategy is replayed over the whole series, so cost is bars × strategies: about 18
seconds for 25 strategies over 8,823 hourly bars. It announces itself on stderr rather than
looking hung. Not a bug — the price of engine parity.

---

## soltui

### The packaging paths have no tests

The 95 tests cover signal derivation, status/roster state and rendering. The py2app alias
build and the launchd agent are verified by hand only; `soltui/README.md` lists those
checks.

### It is an alias build, so it references this checkout

`setup_app.py` runs `py2app -A`, so the installed bundle points at
`/Users/mitch.hudson/dev/solmargintrader`. Move the repo and the app breaks — rebuild with
`soltui-service build`. A full freeze would have to embed pandas and numpy.

### Never install a bundle built from a worktree

`.claude/worktrees/` gets deleted, and login startup then fails silently.
`soltui-service install` refuses a worktree target and warns on a worktree source.

### Quit does not stop it

`KeepAlive` necessarily overrides the menu-bar Quit item. The real off switch is removing
`~/Library/Application Support/soltui/supervise.enabled`, which is what
`soltui-service stop` does.

### A py2app launch-error dialog keeps the process alive

So a liveness check alone will report a healthy agent while the app is showing an error
dialog and doing nothing. Check the log, not just the process.

---

## Repo-level

### `docs/external-calls.md` is not machine-checked

`scripts/check_docs.py` validates test counts and index paths, but nothing diffs the
external-call inventory against the source. A new `fetch` call will not fail the build for
being undocumented.

### Captured artifacts are checked in

`build/`, `dist/`, `jup.ag/`, `jup.ag.zip`, `pagesource/` and `tradingskilllist` are
scratch and captured material. Nothing imports them. `.gitattributes` marks them vendored
or generated so they do not distort language statistics, but they still inflate the clone.
