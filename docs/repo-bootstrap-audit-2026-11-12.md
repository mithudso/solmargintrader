# Repository bootstrap audit — 2026-11-12

Version: 1.0.0. Delta: whole-repository maintenance intake, source-backed metadata
refresh, bounded operations assessment and explicit final-delivery gates.

Task: TASK-1541, the repository bootstrap and code-maintenance task under the
all-repository maintenance effort. Intake baseline:
`5914d2268b770079e54078e4479d166e9c75c90e`.

**Status: CAPPED; final source/documentation drift checks and delivery pending.**
This report records completed work and captured checks. It does not establish
complete five-standard compliance, complete deep review, live execution readiness,
a profitable strategy or delivery to the remote default branch. The existing
bounded optimizer workflow continues; this report creates no new invocation or
independent-gate allowance.

## Prior decisions retained

The November 6, 8, 10 and 11 bootstrap reports were read before this refresh. The
repository-wide license and workflow rotation gaps from November 6 were addressed
in later work; they are not new unresolved findings. The November 8 operations
registry N/A conclusion does not establish five-standard compliance. The November
10 and 11 reports correctly retain the missing operations infrastructure and
coverage limits. Historical counts, installed-runtime receipts and partial audits
remain dated evidence rather than present-day certification.

The workspace has ten documented local components and the separate hosted
`website/` package. Simulation, read-only forecast/MCP, tenant accounts, paper
owners and separately authorized signing paths retain distinct trust boundaries.
See [component contracts](COMPONENTS.md), [security](SECURITY.md) and the
[existing wiki](ECOSYSTEM-WIKI.md).

## Scope and review accounting

The intake inventory contains **771 maintained source paths** across 19 component
and support groups: 631 Python files, 120 JavaScript files, 11 JavaScript modules,
four `.sh` files and five extensionless scripts. No Swift path appears in that
maintained-source inventory. Tests and helpers were included; there was no silent
50-file limit. Seven source-shaped vendor/archive artifacts were excluded as
shown below.

All 771 initial per-file receipts were collected. Their preserved initial
classification is **712 valid receipts and 59 partial or invalid receipts**.
The 712 consist of 167 fresh read-only CLI contexts and 545 fresh supplemental
per-file contexts. These figures describe the initial receipts, not final
unchanged-source or changed-source deep completion. Partial files, changed files
and newly added maintenance tests require their separately recorded continuation
and final coverage accounting.

The companion navigation dossier enumerated 3,367 paths, including 2,588
non-maintained-source records classified by path, size, hash and role. That
navigation census is explicitly shallow: it reports zero deep-read bodies. Its
380 entry points, 1,343 option rows, 239 environment-read sites and 88 literal
environment names are static navigation evidence. Dynamic invocation, option and
environment domains remain unknown where the source does not resolve them. No
research, transcript, customer, cache or generated-data bodies are reproduced in
this report.

The repository-scope passes covered architecture/configuration, canonical library
reuse, dependencies, CI and test parallelization. Exact Python duplication scans,
targeted JavaScript checks and concurrency eligibility are bounded evidence;
semantic clone freedom and measured parallel speedup were not established.
Configuration remains owned by each component's authority boundary. Pure
simulation packages do not acquire a generic settings service or dashboard.

### Hashed intake exclusions

These are provenance records, not deep-review claims. The five `.ts` paths contain
archived GitHub HTML rather than maintained TypeScript. Their archive contents
and the pinned third-party chart bytes were preserved.

| Repository path | Intake SHA-256 | Exclusion |
| --- | --- | --- |
| `ecosystem/web/vendor/lightweight-charts-5.2.1.mjs` | `1bb1ee79f9d4dd17261b53d930f7a8995748276f80e7ba0e24412b5068062f5f` | Pinned third-party chart |
| `extension/vendor/lightweight-charts/lightweight-charts.standalone.production.mjs` | `1bb1ee79f9d4dd17261b53d930f7a8995748276f80e7ba0e24412b5068062f5f` | Same pinned third-party chart |
| `scripts/referral_scripts/claim-all-fees.ts` | `ad2a8f99dc5314ae830c08d636031114cdb919047002ad25d587058a61c992bf` | Archived HTML snapshot |
| `scripts/referral_scripts/create-referral-token-account.ts` | `73847da918d34d04cc8b88c04697e41d29dc6805fa67c4478dda680a81fa5d4e` | Archived HTML snapshot |
| `scripts/referral_scripts/create-referral-account.ts` | `a59c50a7b40266c72299a237d5cc2f03e0b3d228cac81ab000cb9a2b2b92b33a` | Archived HTML snapshot |
| `scripts/referral_scripts/get-referral-token-account.ts` | `052f815d3d52f2c957f76cfcece0e6d26a8c0f2a5625cd0f4d0ee85753a7810b` | Archived HTML snapshot |
| `scripts/referral_scripts/get-referral-account.ts` | `3bbccdc0aa664544354f273cedc0000fdd5a230f9736e9ef3df13c9df420d1c9` | Archived HTML snapshot |

## Metadata and repository standards

The refresh preserves working repository equivalents and updates factual drift.
Presence of a standard file does not prove every paragraph or behavior it names.

| Area | Recorded work and applicability |
| --- | --- |
| Workflow and agent instructions | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and `.github/copilot-instructions.md` reflect actual components, safe retrieval, existing agent definitions and task-completion delivery. Root owns the versioned request and continuation records. |
| Workflow size control | The guarded rotation moved 27 older memory sections into `docs/archive/memory-2026-11-12.md`, retained 20 recent sections and preserved section/STOP-marker accounting. Workflow versions remain separate from package versions. |
| Repository hygiene | Existing editor, line-ending, Node and ignore conventions remain. `.gitignore` and safe environment-name documentation were updated where applicable. No credential values were added. |
| Contribution and ownership | Existing license, conduct, owner and issue conventions remain. PR/security/bug-report guidance now covers the actual component and execution boundaries. No disclosure SLA was invented. |
| CI and dependencies | Website path filters include its upstream research, backtester and Oracle inputs. Offline maintenance regressions and disposable Mongo fixture gates are represented in CI. Dependabot includes the separate website npm package. Private supervisor source is pinned in `soltui/requirements.txt`; public advisory results do not certify that private implementation. |
| Architecture and operations | `docs/ARCHITECTURE.md`, `COMPONENTS.md`, `SECURITY.md`, `OPERATIONS.md`, installation, development, requirements, onboarding, logging and caching guides correct component/owner and execution descriptions. CLI examples retain their owning working directory. |
| Tests | `docs/TESTING.md` distinguishes the legacy count-gated subtotal from additional packages, offline fixtures from live gates, and a historical skip from the current delivery's result. Final count refresh is pending. |
| Existing wiki | `docs/ECOSYSTEM-WIKI.md` adds hosted-website navigation while retaining the packaged wiki. Its generator/consumer fixes preserve exact content hashes, retained provenance and byte bounds. Final snapshot regeneration is pending. |
| Static retrieval | `docs/codebase-overview.md` and existing index/generator tools are the maintained paths. Final high-signal, metadata/text/concept and LLM-family regeneration/checks remain pending. Existing source receipts are not replaced with a hash-only review claim. |

Captured dependency audits reported zero known advisory entries for 104 public
third-party Python distributions, 15 in the executor lock, 49 in the liquidity
lock and 91 website dependencies. Seven first-party distributions in the combined
Python inventory and each locked local package were explicitly skipped by public
package lookup. These are captured-inventory results, not complete private-source,
license, latest-release or future-vulnerability clearance.

## Five-standard external-call assessment

**Result: CAPPED.** The preserved static census scanned every initial maintained
source path: 631 Python AST parses, 131 JavaScript lexical scans and nine script
lexical scans. It recorded 3,106 boundary observations in 293 files and bounded
contract inspection for 16 logical families. The observations include 1,193
fixture/test shapes, 62 nonfixture constructors, 362 unresolved wrappers or
injections, 16 nonfixture inbound shapes and 1,473 other nonfixture I/O shapes.
They are not production request totals or a complete semantic call graph.

The census was source-bound at capture time. Repairs changed source afterward;
its original hash validation must not be described as final-head freshness.
Filename-associated tests, dynamic targets, injected transports, SDK requests and
unresolved reachability remain labelled unknown. The public
[external-call guide](external-calls.md) adds concrete executor, hosted-website and
raw-capture boundaries without claiming a generated exhaustive registry.

| Required standard | Current supported assessment |
| --- | --- |
| Named CLI/MCP trigger and registry | Component CLIs, the extension command registry, manager commands and Oracle MCP exist. They do not constitute one complete per-call operations registry. |
| Centralized per-attempt errors | Component journals, sanitized errors and logs exist. A common structured sink covering every attempt across all surfaces is absent or unproven. |
| Per-code remediation | Existing retry/reconciliation rules are component-specific. A complete safe/escalate map for every emitted error code is absent or unproven. |
| Generated per-call cards | Status panes and control views exist. Complete registry-generated status/log/path/documentation/resync/history cards are absent. |
| Datastore-landed verification | Applicable persisted writes need evidence at their owning store. A mock response, local journal or acknowledged batch is not universal proof of remote read-back. Nonpersisting reads/reports/quotes require no invented write or `DATASTORE_VERIFY_FAILED` branch. |

The generic `server/src/lib/operations-registry.js` path does not fit this
multi-package workspace. That path is adapted; the missing cross-component
operations contract remains a real gap. The project already has an Oracle stdio
MCP server, loopback control surfaces and a separate hosted website; no fictional
server runtime was added. Client-local authenticated MCP registration remains
host-specific rather than a committed credential-bearing `.mcp.json`.

The optional derived MongoDB store was tested only with offline mocks and explicit
disposable integration harnesses. No real owner database was used. Read-only
simulation/forecast operations do not gain a datastore dependency merely to meet a
template. Generic automatic retries were not added to ambiguous signed sends,
manual orders or uncertain upload outcomes.

## Captured verification and pending final checks

Commands below describe the relevant package checks. Repair checks use synthetic
data and disposable homes/stores with sanitized credentials/Git settings. The
recorded isolation failures below prevent a universal isolation claim for every
intake or harness run. Captured repair results are separate from required
checks on the final pushed commit. Later source edits can require a focused
repeat; the table does not assert a finished final-head matrix.

| Component/check | Intake or captured result | Later repair evidence / final status |
| --- | --- | --- |
| Backtester unittest discovery | 1,005 tests; 9 failures and 2 errors, exit 1 | Owned numeric-module selection: 1,007 tests passed. Full integrated final discovery pending. |
| Research unittest discovery | Initial `-t .` invocation failed to import the un-packaged test directory; corrected discovery passed 75 tests | `python -m unittest discover -s research/tests -q`: 141 tests passed. Final integrated receipt pending. |
| Oracle offline unittest suite | 187 tests passed | Focused transport/protocol fixes have receipts; final complete package result pending. |
| Manager unittest suite | 363 tests passed | Full `python -m unittest discover -s tests -v` in `botmanager/`: 386 passed after stable-source reconciliation. |
| Ecosystem unittest suite | 236 tests passed | Full `python -m unittest discover -s ecosystem/tests -t . -v`: 269 passed. |
| Executor locked pytest/Ruff/format | Intake checks passed | Final repair checks: 557 passed, 5 network tests deselected; Ruff and format passed. |
| Archived liquidity offline pytest/Ruff | Intake checks passed | 690 passed, 6 network tests deselected; Ruff, scoped formatting and service-script syntax passed. This did not reactivate liquidity. |
| Mongo and capture | Offline baseline passed | Mongo: 53 tests, 3 skipped; capture: 22 tests, 1 skipped. Read-only query fixtures and scoped lint passed. Live-store cases remain separate. |
| Extension unit and browser fixtures | Unit, offline dry-run and 25 browser checks passed at intake | 509 unit tests passed; 26 DOM/browser regressions passed; isolated extension e2e 25/25 passed. Final commit gates pending. |
| Website Node/Python/export | Intake Node tests: 32 passed; syntax, Python adapter and export checks exit 0 | Final coupled-source checks pending. An export freshness check is distinct from generating or publishing new research. |
| SolTUI | Full serial baseline timed out after 3,600 seconds; no full pass | Evidence modules: 82 passed; recovery/wallet/service batch: 37 passed; latest changed-source regressions: 21 passed. Experiment modules: 51 passed plus 6 latest focused tests. Remaining mounted-UI/full-suite and final integration status pending. |
| Private service dependency | Not installed in the isolated environment | Twelve existing service/render parity tests skipped. New service failure/rollback tests use an inert renderer and disposable bundles; actual service activation is unverified. |
| Lint, syntax and documentation | Headless/locked baseline lint checks passed | Scoped repair lint/syntax receipts include passes and explicit unchanged legacy debt. Repository-wide final policy, count/link checks and generated-index freshness remain pending. |

Some repair-time checks failed before correction, including source-fingerprint
mismatches during concurrent edits, stale expected-contract assertions and UI
lifecycle cases. Their receipts remain preserved. Subsequent targeted or stable
passes do not erase those failures, certify all unrelated modules, or turn a
partial suite into a full pass.

## Test-harness incident and operational limits

A test-discovery mistake imported a `TestCase` directly and unintentionally ran
original service tests outside the intended sentinel. The escaped path reached
`portfolio_agent.uninstall` and a `launchctl bootout` attempt for its fixed label.
**No pre-incident loaded-state observation was captured.** A later read-only
observation found the label unloaded; that observation cannot establish whether
the test caused the state. No restoration was attempted, and no service was
started or stopped to remediate the observation.

The fixture was corrected to use a module alias, retain mocks through cleanup and
bind temporary paths. Git fixtures now use explicit empty templates, stripped
inherited `GIT_*` variables and null global/system Git configuration. Other
recorded inherited-hook incidents and their continuation evidence were preserved.
These events prevent a blanket claim that owner runtimes were unchanged.

The authorized maintenance scope did not include arming, signing, submitting,
funding, changing strategy parameters, running research searches, resetting paper
cohorts, reactivating retired liquidity, modifying wallet/key material or
regenerating semantic vectors. Fixture/service installer tests are not installed
runtime acceptance. Existing live/paper owners, STOP markers and other tasks'
branches and claims remain independent operational authority.

## Finalization pending

Root must fill the remaining delivery evidence after source stabilizes and the
merge is verified:

1. Record the third/final bootstrap drift result within the existing three-pass
   cap, reconcile accepted findings and partial/changed/new source coverage, and
   retain an honest capped residual status where coverage remains incomplete.
2. Regenerate/check the intended packaged wiki, high-signal index, static
   metadata/text/concept artifacts and applicable LLM navigation from final
   public source. Keep semantic embeddings, inference and owner services paused.
3. Record final package, documentation, syntax and required PR check results on
   the final pushed commit; resolve material failures before delivery.
4. Record the merged PR, merge SHA and remote default-branch content verification.
   Synchronize or clean only task-owned work when active consumers and checkout
   state make that safe. A queued merge or open PR is not completed delivery.

The report remains **CAPPED with finalization pending** until those receipts are
recorded. Missing operations infrastructure, unresolved static/dynamic coverage
and explicitly skipped runtime acceptance remain disclosed afterward.
