# Testing

## Standalone bot manager

The `botmanager/` package has its own unittest suite and CI job. Install the four
regular local projects into an isolated Python 3.13 environment, then run from the
repository root:

```bash
python -m pip install ./backtester ./oracle ./soltui ./botmanager
python -m unittest discover -s botmanager/tests -t botmanager
```

The suite uses temporary `SOLBOT_HOME` directories. CLI reads must leave missing
storage absent; defaults, pinned configurations and separate bot identities must
survive a fresh process. Owner-integration fixtures exercise actual HTTP requests
without starting or changing production bots. Runtime tests also exercise separate
instances, crash-before/after commit, stale generations, stopped intent, dead/hung
workers, snapshot integrity and canonical simulator parity. launchctl fixture tests
do not establish installed service behavior; that remains an independent gate.
Current runtime and venue limits are listed in `botmanager/README.md`; tests do not
establish a profitable trading edge.

The targeted macOS CI job also installs the headless owners and runs the blind
judge tests on an actual supported operating-system sandbox. Linux refusal tests
do not establish macOS isolation. When changing the judge, run this focused suite
on macOS and independently verify its installed runtime/profile:

```bash
python -m unittest discover -s botmanager/tests -t botmanager -p test_blind.py
```

## Current managed-suite candidate gates

The coordinated source candidate uses manager 0.7.3, research-runtime 0.4.1 and
ecosystem 0.4.6. [Current operations](bot-manager-0.6-operations.md) keeps the package matrix
and remaining evidence gates separate from the historical M4 0.5.0 release.

New continuation states use a `config-v2` binding over configuration values and
intrabar observations. They reject older `repr`-bound checkpoints. Keep frozen
owner archives with their original pinned runtime; an audit candidate does not
migrate those records or authorize an owner restart.

Prospective research workers also refuse new evidence after their captured
production source changes. Run final checks in a fresh process after source
writers finish. A refusal during a concurrent edit does not establish a failed
strategy or grant permission to rewrite its saved provenance.

Run the separate browser-owner paper gate from the repository root:

```bash
node extension/tools/bot-manager-e2e.mjs
```

That gate uses test-owned profiles/native manifests, verifies actual Chrome storage
and native origin, and tests delegated paper start/stop, worker restart and offline
behavior. The ordinary e2e guard still forbids manager controls and arming. Neither
gate updates or certifies the everyday browser installation. Independent installed
acceptance and final-head CI remain separate release gates.

## Existing component suites

Oracle's forecast/archive/MCP and optional webhook boundaries use the installed
canonical package environment described in [development](DEVELOPMENT.md). From the
repository root, run its offline tests and Ruff gate with:

```bash
python3 -m unittest discover -s backtester/tests -t .   # 1196 tests
python3 -m unittest discover -s soltui/tests -t .       # 1694 tests (TUI dependencies required)
python3 -m unittest discover -s mongo/tests -t .        # 73 tests
cd extension && npm test                                # 555 tests
python3 scripts/check_docs.py                           # these counts, and the retrieval indexes
```

The full SolTUI suite is optional and is skipped by normal PR/push CI. Run it
locally with the command above, or manually dispatch CI with the boolean
`run_soltui_suite` enabled. The other CI jobs and test-discovery count check stay
enabled. The full local suite was run during the 2026-11-12 audit. Its source
binding and skipped tests are recorded in the audit report.

3518 tests total in the four counted suites: backtester, soltui, mongo and extension. Additional component gates are listed below. `liquidity/` additionally has its own pytest suite in its own virtualenv; see `liquidity/README.md`.

Every count on this page is checked by `scripts/check_docs.py`, which counts the suites by
discovery and fails on a stale figure. That exists because these numbers were wrong for
several commits — the docs claimed 250 backtester tests while the suite had grown to 454, and
nothing caught it.

## Extension — what the 555 tests cover

| Area | Examples |
| --- | --- |
| Live prediction score | Shared Python/browser vectors bind all five grades, accuracy/sample floors, freshness and equal strategy weighting. Headless TUI and Chrome checks prove aligned immutable tick scores, leftward motion, automatic ten-second prediction refresh, error recovery, non-overlapping reads, coin-switch reset and obsolete-response/error suppression |
| Charts | the vendored Lightweight Charts file is the pinned 5.2.1 build (sha256), ships LICENSE and NOTICE; equity points map to ascending second-resolution line data (`test/charts.test.js`); `npm run e2e` draws it under the real extension CSP with the attribution link |
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
| **Signal Desk** | Real installed module/style identity, four routes, saved comparison compatibility, exact snapshot handoff without starting, pending/accuracy/return units, archived mutators, local search/dialog focus, mobile/compact layouts and light/dark contrast samples. The new workflow regression uses memory-only native writes |
| **Dashboard workspace** | All installed TUI commands are reachable through workflow groups; explicit false/clear values, structured tables, sortable/filterable results, CSV/JSON, sparse heatmaps, editor guards and confirmation resets have dedicated coverage. The real-browser gate uses a memory-only transport for write regressions; no real order or document write is sent |
| **soltui bridge** | `soltuiCall` returns the identical envelope through the extension message, the CLI and the API; a refusal, an unknown command and a missing host are the same clean envelope everywhere; the confirm flag is forwarded untouched; a running soltui command does not hold the engine lock; transports (port and child process) time out, ignore other ids and reject junk frames |
| **Market reads** | ABI decoding against the live `tickSpacings()` answer; non-read RPC methods refused; endpoint fallback; wrong-chain endpoint refused; low-confidence prices unused; unpriced unknown mints listed but not counted; Jupiter holdings first, RPC fallback; exact CL output inside the active range and refusal past it; Jupiter replies that do not match the request refused |
| **Alerts** | Only fresh, backtest-positive, medium/high-confidence, unflagged, gauged scout pools above break-even may say "act"; a stale or undated scout cannot; an active strategy with no Top 5 record has no baseline; today's all-negative scout raises nothing; idle capital counts Base stablecoins only; quoted leads are info and do not notify by default; first scan records leads silently, and an empty read still counts as the baseline; acks survive re-scans; scans and acks run one at a time |
| **Auto-reload gate** | First observation only stores the hash; no reload while a tick is queued or running (the change is retried, not forgotten); the reload runs inside the engine lock and holds it; an unreachable host never reloads and is logged once; a failed `reload()` restores the old hash |

The parity suite probes all 38 commands with a deliberately invalid argument, which proves the route
resolved **without executing the handler** — no side effects, no network calls.

## What is NOT covered

Read this before trusting anything with money.

1. **Offline tests do not establish live order acceptance.** Synthetic fixtures exercise the write
   path (auth → vault → deposit craft → sign → create). Installed venue acceptance remains a
   separate owner-authorized gate; the maintenance suites do not fund, sign or submit an order.
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
real service worker, popup and dashboard. It uses Node built-ins only. 24 checks (25 with the production soltui host):

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

From the repository root:

```bash
(cd extension && npm test)                             # unit + parity
(cd extension && node tools/dryrun.js --ticks 8 --osc 6 --offline 100 --assert-economics) # a round trip must close positive
(cd extension && npm run e2e)                          # real-browser load + dry-run checks (needs Chrome for Testing)
(cd extension && node tools/dryrun.js --ticks 4 --walk 5 --offline 100) # trending case: bids fill, no exits
(cd extension && node tools/verify-endpoints.js)        # live Jupiter reachability
(cd extension && find src tools test -name '*.js' -print0 | xargs -0 -n1 node --check)
```

The oscillating dry run is the meaningful one: it is the only check that closes a round trip and so
the only one that can detect a zero-spread regression.

## Backtester — 1196 tests

Correctness of the simulation is the priority, so the suite concentrates on the things that silently
inflate a result: **lookahead leaks**, cost application, and metric arithmetic. Any change touching
signal generation or fill timing needs a test that would catch a one-bar leak. See
`backtester/README.md`.

`test_scorecard.py` holds that test for the compound five-minute scorecard: every historical
component, the composite, the regime label and the target path must give the same value at bar t
whether or not the bars after t exist (prefix invariance), and a deliberately leaky component is
shown to fail the check. `test_compound_backtest.py` covers the 5m loader (traded-minute
aggregation, gaps split into segments, stale funding refused), the engine fill at bar t+1's open,
and that fees reach the P&L. The same prefix-invariance check runs with adaptive weighting on and with tuning forced to move, so a learned weight or an adopted setting at bar t never uses the outcome of bar t.
`test_fetch_minutes_alt.py` runs the other-venue minute fetcher against canned replies: KuCoin and
WhiteBIT's `[t, open, close, high, low]` rows land in OHLC order, OKX's unconfirmed candle is
dropped, a page with swapped columns stops the fetch before anything is written, and a resumed
fetch neither repeats nor skips minutes.

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

## soltui — 1694 tests

The suite includes real Textual render cycles, subprocess lifecycle checks and offline strategy integration.
Run all tests with
`python3 -m unittest discover -s soltui/tests -t .`.

soltui keeps research simulations separate from explicitly confirmed manual Coinbase orders. Its tests cover
display correctness, not money. `test_compound.py` covers the Compound 5m tab end to end
(toggle, edit, refused values, a stubbed live signal) plus the forward ledger with stub venues:
the still-forming bar is dropped, a call is recorded once per bar and resolved by the next close,
and an enabled news gate blocks when its feeds are unreachable. `test_launcher.py` drives the `soltui` shell command
(`soltui/bin/soltui`) through a symlink with a fake interpreter, so it checks the repo
lookup, the module choice and argument pass-through without starting Textual. The
packaging paths — the py2app alias bundle and the launchd agent — are **not** covered by
any test; see `soltui/README.md` for the manual checks that stand in for them.

The optimization workbench has dedicated foundation, native runner and interface suites:
`test_experiments.py`, `test_experiment_runner.py` and `test_experiment_interface.py`.
They cover immutable cells, typed budgets, observed sparse maps, CSV units/provenance,
spent/explored temporal reservations, legacy fences, historical mutation, cooperative controls,
process termination/recovery, baseline comparison, adoption crash receipts and the headless UI.
Fixtures isolate configuration/data; tests stub the live order path and do not submit real orders.

## mongo — 73 tests

Pure helpers need no server. Native integration tests **skip unless
`SOLMARGINTRADER_MONGO_TEST_URI` is explicitly set to a bare loopback URI** for a
disposable test server. They use unique database names and reject credentials, URI paths,
queries and non-loopback hosts. An explicitly configured but unreachable server fails the
test. An ordinary local MongoDB listener does not opt the suite in.

The load fixture asserts *idempotency*: two loads of its synthetic three-collection subset
must leave identical counts. A time series collection accepts no unique index, so the
assertion detects duplicate appends. The fixture uses a unique disposable database and
removes only that database.

The rest guard the store's honesty: every document carries provenance, the server refuses
one that does not (strict validation, proven by an insert that must raise), NaN never
reaches the store, and the card counts track the registry — 49 cards with `registry_key`
set on exactly 25, every key real.

## Adding tests

- Extension: `extension/test/*.test.js`, `node:test` + `node:assert/strict`. Assert behaviour and
  observable effects, not line execution.
- Backtester: `backtester/tests/`, `unittest`, including older research modules
  (`test_decide.py`, `test_cpcv.py`, `test_interpret.py`). Causal shape/cycle studies
  also use `research/tests/`. The top50 study installs its research-only dependencies
  from `research/coinbase50-requirements.txt` and runs
  `python3 -m unittest research.tests.test_coinbase50_study -v`; CI runs that gate.
- soltui: `soltui/tests/`, `unittest`.
- mongo: `mongo/tests/`, `unittest`. Use the guarded disposable Mongo fixture for server-dependent tests;
  never infer permission from a listening local MongoDB server.
- A new command needs no new parity test — the registry-driven suite picks it up automatically. If it
  takes an argument that changes money, add a behavioural test for that argument.


## Coverage target and CI gates

The coverage target is meaningful assertions on important and changed paths, including
failure modes, state transitions and emitted logs. This repository does not configure a
numeric line-coverage threshold. A blanket 100% line target is not an existing CI gate.

`.github/workflows/ci.yml` runs extension unit/parity/syntax/manifest/offline-dry-run
and isolated real-browser checks, backtester/research tests, Oracle and installed paper
ecosystem tests, manager lifecycle checks, bounded SolTUI checks on macOS, MongoDB and
raw-capture integration tests with a service container, documentation/index drift checks,
and executor/liquidity offline pytest and lint gates. The separate
`.github/workflows/website.yml` runs Node tests/syntax, Python adapter tests and public
research export freshness when its configured source paths change.
The default liquidity pytest selection excludes the `network` marker. Public Jupiter
reachability is informational and runs on workflow dispatch, not on each PR.

A green suite does not prove that the installed Chrome extension, macOS bundle, live
liquidity daemon, or venue envelope matches the tested source. Record those acceptance
gaps separately. Installed-service tests must not be replaced by process-liveness alone.

Normal PR and push CI runs a bounded SolTUI bridge smoke gate plus modules mapped to changed areas. Unknown paths retain the smoke gate. This is not full-suite coverage. The four-shard full suite requires manual dispatch with `run_soltui_suite=true`.


## Managed availability and native Chrome recovery

Run the manager lifecycle and machine-health tests with the source package on the
import path. The ecosystem suite exercises actual loopback health routes, scoped
UI ownership and wiki provenance. Use INDEX_NO_AUTO=1 for all these checks.

```bash
INDEX_NO_AUTO=1 PYTHONPATH=botmanager/src:. python3 -m unittest discover -s botmanager/tests -t botmanager
INDEX_NO_AUTO=1 PYTHONPATH=botmanager/src:. python3 -m unittest discover -s ecosystem/tests -t .
```

The separate `extension/tools/control-room-e2e.mjs` gate requires a compatible
regular installed runtime selected by SOLBOT_TEST_PYTHON and
SOLBOT_TEST_INSTALLED=1. It uses short isolated private homes and a temporary
Chrome profile to verify fixed native startup, actual UI opening, owned UI crash
recovery, health reads, helper failure semantics and disarmed defaults. The
ordinary `extension/tools/e2e.mjs` gate retains its stronger no-start restrictions.
CI runs both. These checks do not prove physical reboot or everyday-profile
installation; actual installed acceptance is a separate recorded gate.

## JavaScript correctness and gradual type checking

The root package defines a pinned development toolchain and a reproducible lockfile.
Run its checks from the repository root:

```bash
npm ci --ignore-scripts
npm run check:js
```

ESLint checks extension, website and ecosystem JavaScript for undefined bindings,
unsafe execution, unreachable control flow and related correctness failures. Its
configuration avoids a style rewrite. The atomic file-store cleanup has one
documented local exception because it must reject when private temporary data
cannot be removed.

Strict `checkJs` currently covers the forecast-expiry helper and its public JSDoc
contract. The compile-time callers include valid inputs and expected errors for
invalid directions, expiry values and evaluation clocks. This is incremental
checked-interface coverage; the rest of the JavaScript has behavioral and lint
checks. Type checking emits no runtime files. The JavaScript quality workflow
runs the same locked toolchain in CI.

## Hosted website source and deployment gates

The website uses Node’s `node:test` runner with SQLite-backed account fixtures.
Its tests cover Ed25519 signatures, one-use challenge expiry/replay, secure
sessions, tenant isolation, subscription gating, signed Stripe webhooks,
Checkout/deletion races and the D1 cascade-deletion return contract. OAuth/MCP
fixtures exercise actual synthetic Ed25519 login and policy signatures, PKCE,
resource/redirect binding, replay, scopes, two-wallet status isolation, immediate
revocation and missing-executor refusal. Atomic race tests cover plan invalidation,
budget reservations, duplicate submissions and account deletion. Unknown outcomes
retain budget. Active-grant history remains reachable for revocation. The pure
browser evidence helper withholds expired directions.

```bash
npm --prefix website test
npm --prefix website run check
npm --prefix website run test:browser
node --test website/test/mcp-integration.test.js
python3 -m unittest website.engine.test_server website.engine.test_research
python3 -m website.scripts.export_research --check
ruff check website/engine website/scripts/export_research.py
```

The Python fixtures check canonical costed-engine parity, data gaps, bounds,
read-only archive access and research-export provenance. They never acquire
market history, run a trading worker or submit an order. Install the existing
backtester/Oracle dependencies in an isolated Python environment first.
`.github/workflows/website.yml` runs Node and Python source gates on relevant PRs.

The browser command runs the original workspace suite and agent-consent suite
in isolated Chrome with local account/wallet fixtures. Held callbacks verify
sign-out invalidation, serialized transitions and frozen policy controls. Trading
consent signs once per finite grant; no test adds a per-trade wallet prompt.
Successful customer-adapter fixtures are mocks. They do not verify real wallet
delegation, provider signing, venue reconciliation or an order.

Deployed acceptance is separate: verify exact loaded asset bytes, desktop/mobile
flows, actual hosted wallet signature/session/deletion, OAuth discovery/consent/
PKCE/token/status/revocation, Stripe Checkout and cancellation
when configured, and hosted analysis with its real inputs. Running
`node website/scripts/smoke.mjs https://oraclebot.io` explicitly creates and
deletes a throwaway account. The smoke verifies authentication and unpaid-access
denial; it does not prove a successful subscription, backtest or live trade.
