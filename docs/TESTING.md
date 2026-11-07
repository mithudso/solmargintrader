# Testing

```bash
python3 -m unittest discover -s backtester/tests -t .   # 681 tests
python3 -m unittest discover -s soltui/tests -t .       # 408 tests (~300s)
python3 -m unittest discover -s mongo/tests -t .        # 33 tests
cd extension && npm test                                # 303 tests
python3 scripts/check_docs.py                           # these counts, and the retrieval indexes
```

1466 tests total across the unittest and `node:test` suites. `liquidity/` additionally has its own pytest suite in its own virtualenv; see `liquidity/README.md`.

Every count on this page is checked by `scripts/check_docs.py`, which counts the suites by
discovery and fails on a stale figure. That exists because these numbers were wrong for
several commits — the docs claimed 250 backtester tests while the suite had grown to 454, and
nothing caught it.

## Extension — what the 303 tests cover

| Area | Examples |
| --- | --- |
| Grid math | Arithmetic and geometric ladders against hand-computed values; endpoint pinning; degenerate configs rejected |
| **Round-trip economics** | An exit rests one rung above its lot, never at the same level; `gross === notional × rungWidth` |
| Planning | Lot aggregation (two lots on one rung produce **one** order, not a duplicate key); venue minimum; deadband; already-resting suppression |
| Risk rails | Each rail fires on its own breach; a batch cannot collectively breach a cap each member passes; rails **fail closed** on missing or NaN state; unusable orders blocked |
| P&L | FIFO across lots; partial closes realizing a proportional share of entry fees; carry subtracted; fees turning a gross win into a net loss; unmatched sells surfaced |
| Reconciliation | A venue echoing fewer decimals is matched, **not duplicated**; a missing order is orphaned and never auto-retried; unknown live orders adopted; two near-identical orders do not bind to one intent |
| Tick guards | Unusable price aborts before P&L; the daily counter measures today, not lifetime; a short grid on a spot venue says so |
| Wallet | base58 against real mints and the all-zero pubkey; shortvec boundaries; signature insertion into the correct slot; non-signer refused |
| Crypto | Sealed-seed round trip; wrong passphrase fails closed; fresh salt and IV per seal; Ed25519 signing |
| **Surface parity** | Every command routable over the API; `GET` restricted to read-only; CLI help lists all commands and every argument; UI messages all map to real commands |
| **soltui bridge** | `soltuiCall` returns the identical envelope through the extension message, the CLI and the API; a refusal, an unknown command and a missing host are the same clean envelope everywhere; the confirm flag is forwarded untouched; a running soltui command does not hold the engine lock; transports (port and child process) time out, ignore other ids and reject junk frames |
| **Auto-reload gate** | First observation only stores the hash; no reload while a tick is queued or running (the change is retried, not forgotten); the reload runs inside the engine lock and holds it; an unreachable host never reloads and is logged once; a failed `reload()` restores the old hash |

The parity suite probes all 25 commands with a deliberately invalid argument, which proves the route
resolved **without executing the handler** — no side effects, no network calls.

## What is NOT covered

Read this before trusting anything with money.

1. **No live order has ever been placed.** The write path (auth → vault → deposit craft → sign →
   create) matches the documented shapes but has never executed. It needs an API key and a funded
   wallet. Test with one rung at the $10 minimum.
2. **The Trigger contract has offline fixtures, not live acceptance.** History pagination and
   cancellation were checked against current public documentation. Wallet-specific responses,
   execution USD valuation and semantic transaction verification still need verified fixtures.
3. **Fee attribution is unconfirmed.** Unknown costs remain flagged for inspection and hold new
   admission. Uncertain execution price, quantity or timing also holds planning.
4. **Signature insertion is tested against synthetic transactions**, not a real Jupiter deposit.
5. **The e2e covers loading and dry-run only.** `npm run e2e` loads the unpacked extension in
   Chrome for Testing and checks install state, service worker, popup, dashboard, a dry-run plan
   and tick, rails and secrets. It never arms or signs and stubs the network, so it says nothing
   about live orders. Needs Chrome for Testing; it is not part of `npm test`.
6. **The Chrome alarm floor is assumed to be 30s.** The engine logs the real wake delta — watch it
   before trusting a sub-minute tick.

## Extension — real-browser e2e

`npm run e2e` (`extension/tools/e2e.mjs`, helpers in `extension/e2e/`) launches Chrome for Testing
headless, loads `extension/` with `Extensions.loadUnpacked` over the DevTools pipe, and drives the
real service worker, popup and dashboard. It uses Node built-ins only. 20 checks (21 with the production soltui host):

| Check | What it proves |
| --- | --- |
| Service worker starts | The manifest entry point loads as an MV3 worker |
| Installs disarmed in dry-run | `runtime.armed` and `killSwitch` are false and `config.mode` equals `DEFAULT_CONFIG.mode` after a real `onInstalled` |
| Install event and alarm | The journal holds the `installed` event; the tick alarm is scheduled |
| Popup and dashboard | Both render from the worker's `status`; dry-run and disarmed are shown |
| Registry parity | The worker's command list equals `COMMAND_NAMES`; unknown messages are refused |
| Plan and tick | `plan` is priced by the stubbed read and returns intents; a disarmed `tick` is skipped as `not-armed` and journals nothing |
| Rails fail closed | Missing, NaN or malformed state and limits block, run in the browser |
| Secrets | A canary API key appears in no DOM, no response and no `chrome.storage.sync` |
| Network audit | Chrome-level interception saw only keyless GET price reads; every other request was blocked |
| soltui bridge | The real extension talks to the soltui native messaging host (a host manifest is written into the throwaway profile's `NativeMessagingHosts`). `soltuiCommands` and a read-only `soltuiCall` return the same envelope as the extension CLI, and with the production host as `soltui list` / `soltui call`, byte for byte. An unknown command and a missing host are clean failed envelopes. The dashboard SolTUI panel lists the registry and shows the result as text. The 1-minute build probe alarm exists. The run says which host it used: the production host when soltui is installed, a protocol-identical fixture (`e2e/fixtures/`) where it is not, for example the Linux CI runner. `SOLTUI_E2E_HOST=real` fails the run if the production host cannot start |
| Disarmed at the end | The run never changed `armed` or the kill switch |

Safety is structural: `e2e/lib/guard.mjs` allowlists the messages the harness may send and
`test/e2e-harness.test.js` (part of `npm test`) fails when a new registry command is not classified.
Install a browser with `npx @puppeteer/browsers install chrome@stable` (branded Chrome ignores
command-line extension loading); set `CHROME` for another build and `E2E_NO_SANDBOX=1` in containers.

## Verification commands

```bash
cd extension

npm test                                              # unit + parity
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must close positive
npm run e2e                                           # real-browser load + dry-run checks (needs Chrome for Testing)
node tools/dryrun.js --ticks 4 --walk 5 --offline 100 # trending case: bids fill, no exits
node tools/verify-endpoints.js                        # live Jupiter reachability
find src tools test -name '*.js' -print0 | xargs -0 -n1 node --check
```

The oscillating dry run is the meaningful one: it is the only check that closes a round trip and so
the only one that can detect a zero-spread regression.

## Backtester — 681 tests

Correctness of the simulation is the priority, so the suite concentrates on the things that silently
inflate a result: **lookahead leaks**, cost application, and metric arithmetic. Any change touching
signal generation or fill timing needs a test that would catch a one-bar leak. See
`backtester/README.md`.

32 of those cover the ladder-grid simulator (`core/gridsim.py`), and they exist because that module
has to agree with `extension/src/core/grid.js` about what a round trip earns. Three groups matter
most: the **round-trip invariant** (gross `== notional × rung width`, plus rung width asserted
against the JavaScript implementation's own figures), the **no-lookahead group** (nothing fills on
bar 0; a bar spanning both legs books only the entry), and the **failure modes** (a one-way
downtrend fills every bid and loses; an unfundable rung is skipped rather than overdrawn; a forced
end-of-run exit is never counted as a captured rung).

36 of them cover the **strategy cards** (`core/strategy_cards.py`). Those tests exist because a card's
frontmatter supplies numbers to a backtest, so the machine-readable half is checked against the code
rather than trusted: registry drift is asserted in **both** directions (every registered strategy has
a card, every card's `registry_key` still exists), every declared default is compared against its
constructor's actual default, `warmup_bars` and `family` against the code, and every card's presets
against `research/sweep.py` so a card documents the same experiment the sweep runs. Every buildable
card is also constructed and run through a full backtest. Prose in a card can still be wrong — no
test catches that — but a number cannot.

31 more cover the **nine strategies implemented from spec-only cards**
(`core/strategies/advanced.py`). Each test targets what that mechanism could get
*wrong* rather than that it runs: the excluded window in dual momentum, the strength
gate in ADX, and above all the **displacement trap in Ichimoku** — the cloud sitting
at the current bar was computed 26 bars ago, so reading it as current reads 26 bars of
future data. That test asserts the value used equals the cloud computed from the
truncated slice *and* differs from the full-history cloud, so the distinction is
verified rather than assumed.

63 cover the **per-bar rule readout** (`research/decide.py`), and the one that matters
asserts *engine parity*: a recording wrapper captures every `on_bar` return
`run_backtest` asks for, and the readout's replay must reproduce that index sequence and
those values exactly for all 25 strategies. The rest guard the two ways the readout can
lie — a truncated-history test that fails if the replay is ever "optimised" into a single
call on the last bar, and a constructed series where that shortcut gives the *opposite*
answer, so the first test is known to be load-bearing rather than vacuously true.

## soltui — 408 tests

Slower than the others (~70s) because the TUI tests drive real render cycles. Three
files: `test_signals.py` (signal derivation), `test_status_roster.py` (status and roster
state) and `test_tui.py` (rendering). Run them with
`python3 -m unittest discover -s soltui/tests -t .`.

soltui is read-only over the research side and places no orders, so its tests are about
display correctness, not money. `test_launcher.py` drives the `soltui` shell command
(`soltui/bin/soltui`) through a symlink with a fake interpreter, so it checks the repo
lookup, the module choice and argument pass-through without starting Textual. The
packaging paths — the py2app alias bundle and the launchd agent — are **not** covered by
any test; see `soltui/README.md` for the manual checks that stand in for them.

## mongo — 33 tests

Split between pure helpers that need nothing and integration tests that **skip cleanly
when no mongod is listening**, so a checkout without a database runs the suite green
rather than red.

The one that earns its keep asserts *idempotency*. `load.py` drops before it writes, and
two consecutive loads must leave identical counts — a time series collection accepts no
unique index, so nothing else would catch a second load silently doubling all 18,381
bars. It runs over a three-collection subset to stay fast; the mechanism is the same for
every collection.

The rest guard the store's honesty: every document carries provenance, the server refuses
one that does not (strict validation, proven by an insert that must raise), NaN never
reaches the store, and the card counts track the registry — 45 cards with `registry_key`
set on exactly 25, every key real.

## Adding tests

- Extension: `extension/test/*.test.js`, `node:test` + `node:assert/strict`. Assert behaviour and
  observable effects, not line execution.
- Backtester and research: `backtester/tests/`, `unittest`. `research/` has no test directory of
  its own; its modules are tested from there (`test_decide.py`, `test_cpcv.py`, `test_interpret.py`).
- soltui: `soltui/tests/`, `unittest`.
- mongo: `mongo/tests/`, `unittest`. Guard anything server-dependent with the module's
  `needs_server` decorator so a checkout without mongod still passes.
- A new command needs no new parity test — the registry-driven suite picks it up automatically. If it
  takes an argument that changes money, add a behavioural test for that argument.


## Coverage target and CI gates

The coverage target is meaningful assertions on important and changed paths, including
failure modes, state transitions and emitted logs. This repository does not configure a
numeric line-coverage threshold. A blanket 100% line target is not an existing CI gate.

`.github/workflows/ci.yml` runs extension unit/parity/syntax/manifest/offline-dry-run
checks, backtester tests/imports, soltui tests on macOS, MongoDB integration tests with
a service container, documentation/index drift checks, and liquidity Ruff/format/pytest.
The default liquidity pytest selection excludes the `network` marker. Public Jupiter
reachability is informational and runs on workflow dispatch, not on each PR.

A green suite does not prove that the installed Chrome extension, macOS bundle, live
liquidity daemon, or venue envelope matches the tested source. Record those acceptance
gaps separately. Installed-service tests must not be replaced by process-liveness alone.
