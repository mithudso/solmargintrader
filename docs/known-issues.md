# Known issues

Active limitations, in descending order of how much damage they could do. Nothing here is
speculative — each item is either stated in the code or was reproduced.

Source markers are not an exhaustive issue list. The dated bootstrap and optimizer
reports record reviewed findings and residuals; this page records ongoing limitations.

---

## Extension — the money path

### No live order has ever been placed

The whole live path is unexercised against a real venue. Every test and the headless dry
run go through fakes. Do not present any live-path behaviour as working; read the
**Verification status** section of `extension/README.md` before extending it.

**Consequence:** the first real order is the first real test.

### Trigger contract has offline fixtures, not live acceptance

History pagination and cancellation paths are checked against current public documentation
and offline fixtures. No authenticated wallet response or live order has been accepted.
Incomplete execution valuation, costs or timing holds new planning. The bundled session
signer has no independent transaction-intent verifier, so automatic Trigger writes stay
blocked. See `docs/jupiter-trigger-contract.md`.

Unknown submissions retain their journal hold and are never automatically replayed.

### Fee attribution is unconfirmed

`src/jupiter/attribution.js` has never been checked against a real fill. Reported P&L may
attribute fees differently from the venue.

### Incomplete transport observability

Persistent intent/tick events do not replace per-request transport logs. Jupiter
request/outcome metadata and some failure paths remain outside a common sink.
`docs/logging.md` and the dated code-optimizer report distinguish verified changes from
remaining coverage. Do not infer a complete request history from a tick summary.

### The real-browser e2e covers loading and dry-run only

`npm run e2e` loads the unpacked extension in Chrome for Testing and checks install state, the
service worker, popup, dashboard, a dry-run plan and tick, the rails and secret handling. It never
arms or signs and stubs the network, so it is not evidence about live orders. The headless dry run
(`tools/dryrun.js --ticks 8 --osc 6 --offline 100`) remains the economics gate. Branded Chrome
cannot load an extension from the command line, so the e2e needs Chrome for Testing or Chromium.

---

## Backtester and research

### The cached data is a snapshot with no freshness contract

`data/` is gitignored and regenerable, and nothing in a CSV records when it was fetched.
`research/decide.py` prints the decision bar's age in bars and says `STALE` past two, which
is a mitigation, not a fix — the underlying cache still has to be refetched by hand.

A historical check found bars behind wall clock despite a current file mtime. That
snapshot is not a current freshness assertion; inspect timestamps/checksum in the
readout for the cache you are actually using.

### Historical `data/SOL_1h.csv` snapshot had two gaps larger than one bar

Reading that snapshot required the loader's `--allow-gaps`. The simulators now refuse
irregular cadence even with that loader flag: missing time is not measured carry or
annualization evidence. Use a complete cache before running a simulation.
The largest gap is 21,600s where 3,600s was expected, after epoch 1761404400. Any
statistic computed across that boundary spans a hole.

### `data/JLP_spot.csv` is not a bar series

One row, columns `timestamp,iso,mint,usd_price,source` — a Jupiter price snapshot from
`core/archive_price.py`, not OHLCV. Bar tools refuse it by naming the missing columns,
which is correct behaviour, but the filename invites the mistake.

### Coinbase is the primary bar and trade-tick source

Binance is geo-blocked from here. That means a single vendor's outage or history revision
affects refreshed price caches, and Coinbase's non-OHLCV row ordering has to be handled
on the way in. Signed funding history uses Hyperliquid with a shallow OKX cross-check;
that does not provide an independent bar history.

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

### Manual Jupiter V2 is preview-only

The manual path has structural transaction checks, but independent economic verification is
incomplete. Submit and quick-submit refuse before key loading, signing or sending. Unsigned
previews require a known input valuation; history and chain reconciliation remain available.
Historical unknown submissions stay blocked until chain proof resolves them. No elapsed-time
rule clears that uncertainty. This limitation does not change separately armed Coinbase orders.

### Legacy recorder Stop metadata

Recorder Stop uses a nonce bound to the active recorder lock and never sends a signal to a PID
from a file. A recorder started by an older version without this metadata cannot be stopped through
that fallback. The command reports the refusal instead of risking an unrelated process.

### The packaging paths have no tests

Unit tests cover signal derivation, state, rendering, launchers and service/plist helpers.
The installed py2app alias bundle and launchd behavior still require acceptance; `soltui/README.md` lists those
checks.

### It is an alias build, so it references this checkout

`setup_app.py` runs `py2app -A`, so the installed bundle points at
the checkout from which it was built. Move the repo and the app breaks — rebuild with
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

## Liquidity

Public RPC and market-data availability can prevent scoring or simulation. Provider
comparison is read-only and includes explicitly labelled quoted rows. A successful
simulation does not establish that a live transaction landed. Preserve partial-sequence
state and receipts before any retry. See `liquidity/README.md` and `liquidity/STATE_FILES.md`.

## Repo-level

### `docs/external-calls.md` is not machine-checked

`scripts/check_docs.py` validates test counts and index paths, but nothing diffs the
external-call inventory against the source. A new `fetch` call will not fail the build for
being undocumented.

### Captured artifacts are checked in

`build/`, `dist/`, `jup.ag/`, `jup.ag.zip`, `pagesource/` and `tradingskilllist` are
scratch and captured material. Nothing imports them. `.gitattributes` marks them vendored
or generated so they do not distort language statistics, but they still inflate the clone.
