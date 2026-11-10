# M4 implementation checkpoint

Version: 1.1.0
Delta: 1.0.0 to 1.1.0 records the explicit source commit and complete owned-file manifest.
Delta: Replace the initial partial report with the implemented protocol, final focused checks, public setup/default-plan flow and scoped epoch ruling. This is a recoverable source checkpoint, not independent acceptance or delivery.
Task: TASK-1110 under EPIC-1106. Branch: agent-01a1c189-m4.
Base: a610868dbac61b46dba2a0047aa22d79b23cab34 (M3 PR188).
Worktree: /Users/mitch/dev/solmargintrader-wt-01a1c189-editing.
Source commit: e24ad7ca343a07910d04f3c3471494fcba763c75 (32 explicitly owned files).

## Stop and integration boundary

The parent relayed the user's request for a written plan of all remaining work.
Finish the currently discussed M4 authority/setup fixes, record and commit the
owned checkpoint, then stop. No M5+ work, installation, inference, indexing,
service/recorder startup, default/production/frozen experiment changes, keys,
arming, orders, push or merge were performed by this worker.

Parent retains root docs, CI, indexes, workflow records, Stele, installation,
independent review and delivery. Their dirty/staged files and .opencode/ remain
untouched. Parent's current planning branch starts at origin/master 21331e37,
which now includes PR189's ecosystem control room and PR190's approved 50bps
referral default. The checkpoint ecosystem 0.1.4 pin is OBSOLETE as a final release
number. Integration must preserve those newer behaviors and bump forward from
0.2.1, then recompute compatible package pins and review the combined source.
Do not install this pre-integration package matrix as the final release.

## Delivered source interfaces

All public manager actions remain in botmanager.registry.COMMANDS; CLI only parses,
dispatches and renders. Owner stdio invokes the existing soltui.commands registry's
single research.protocol action with an inert Context. It does not define another
execution registry, load default settings/keys, import Textual or start an owner.

Manager commands:
- research-setup: select installed interpreter/working-directory/config root,
  discover actual protocol/package/module identity with inert owner describe,
  reuse any existing canonical namespace binding and write a descriptor. Defaults
  use the current declared manager interpreter and its environment. Explicit
  --interpreter/--repository/--config-root/--authority-root/--authority-id and
  --output are available. An existing conflicting namespace refuses. Identical
  descriptor creation is idempotent; setup never initializes authority.
- research-register --owner FILE --accept-registered-roots-only, with explicit
  --initialize-first-authority only for the first namespace DB. Imports history
  and returns a public binding receipt. Repeated registration is idempotent.
- research-plan BOT [--output FILE]: at most two validated neighboring values for
  one supported unpinned strategy tunable, feature-aware horizon/warmup, ten
  blocks, bootstrap seed0/minimum10. Unsupported/all-pinned searches refuse. The
  response explicitly says current reference evidence/horizons are not final
  eligible. research uses this same default when --plan is omitted.
- backtest BOT --owner FILE --descriptor FILE: actual canonical costed replay;
  explicit reference/certification/independence limits, real completed exits,
  surviving open lots and pending targets. It records inspected dates first.
- research BOT --owner FILE --descriptor FILE [--plan FILE]: full frozen pipeline.
- research-status, research-cancel, research-recover and research-proposal use
  --owner and optional/required --run-id as their registry schemas specify.

Owner protocol2 request has exactly version, operation, authority, params and
expected_identity. Authority has exactly id/root/known_clients/inventory_complete;
known clients have exactly root/kind/active. Unknown nested fields refuse even on
inert status. Ordinary operations require the reviewed exact loaded identity.
Inert describe uses authority=null, expected_identity=null, params={} and returns
identity plus existing canonical id/root without creating any path/database.
Supported operations: describe/register/status/backtest/research/proposal/receipt/
cancel/recover. Client transport uses selected python -I -B, no PYTHONPATH, clean
PATH/LC_ALL/config environment, closed FDs, bounded 1MiB streams and 120s deadline.
Only an explicitly isolated registry override is forwarded. Failures are sanitized.
Status/proposal responses preserve stale proposal bodies with reconcilable=false
and reason; CLI research-proposal refuses reconciliation of stale proof.

The component READMEs document complete create -> research-setup -> register ->
prepare-input -> research-plan -> backtest/research commands. No hand-pasted Python
identity, manually written binding JSON or hand-authored plan is necessary. Source
selection/reference consent and first-DB initialization remain explicit because
neither can be inferred as permission to relabel data or create research history.
Existing prepare-input owns source/cost defaults; no second source algorithm added.

## One authority, migrations and coverage

ExperimentStore remains the temporal/attempt owner. Additive tables:
manager_attempts, manager_budgets, manager_trials, manager_artifacts,
manager_clients, manager_imports, manager_exposures, manager_final_dates,
manager_history_gaps. Existing protocol1 runs/cells/holdouts/exposures and legacy
retry/adoption/partition behavior retain their meaning. Manager-import migration
adds admitted_at/historical with conservative defaults for older rows. Gap migration
adds nullable cutoff; older unbounded gaps stay unbounded. ManagerStore schema2
adds only immutable research_proposals receipts, never another exposure ledger.

Canonical namespace default is the account-home suffix
.local/share/solbot-research/authority.json. It is independent of both manager home
and owner configuration root. The record binds authority UUID/root, enrolled
config roots, known-client inventory, namespace hash, isolation mode and immutable
initialization epoch. Per-config research-authority.json is only a binding receipt.
New owner roots must enroll against the same namespace; new homes/UUIDs cannot
reset dates, attempts or alpha. Explicit SOLTUI_RESEARCH_REGISTRY uses controlled
isolated inventory; its namespace/isolation label is bound into receipts and
production_eligible remains false.

Registration lock order is namespace flock -> shared optimizer flock -> SQL.
Registration imports the actual authority and selected/default native roots,
pre-ledger bots/optimize*.json even without experiments/, preserved cutoff files,
default F5/bg/forward roots, both documented ecosystem batch roots, any explicit
ecosystem-home, and recognized selected Oracle archive context. A caller omission
cannot erase known roots. Unknown source context creates a history gap. A prior
observed store disappearing becomes unavailable, not newly fresh checked absence.
A registered root cannot silently change kind. F5 source bounds are recovered only
from matching frozen file SHA256 before/after the same-FD CSV read, including its
recorded contiguous selection. Attempts include failed/interrupted variants;
missing/changed bounds, partial stores and prospective unknown history refuse
fresh-final certification. Imports are immutable/idempotent and never delete old
exposure. Budget counts are deliberately conservative across SOL strategy families,
timeframes, source/cost/dataset fingerprints and execution aliases.

First initialization creates the first DB through ExperimentStore only when no
namespace binding exists. It records an owner-clock epoch with an immutable gap
for earlier dates. That cutoff cannot be changed by re-registration or consent.
Historical windows remain unavailable; genuinely post-epoch final intervals can
qualify after required owners/relevant history are verified. Existing counters
never reset. This does NOT claim reconstruction of unknown pre-epoch attempts or
machine-wide lifetime alpha history; scoped proof binds the epoch and the retained
canonical attempt context. Other unknown source/participation gaps remain explicit
and may be unbounded. The public status exposes gap scope as affects_dates_before.

Coverage is registered_roots_only, never fleet-wide completeness. Active root
locks are read-only probes, not process intervention. Declarations never prove
loaded participation. Known active unaware clients remain blockers. Participating
F5/bg/forward use explicit SOLTUI_RESEARCH_AUTHORITY, one optimizer lease and
pre-read admission; nested F5->forward calls use process-safe reentrant lease
context. Native preview/run acquire that lease when opted in, protect capture
before loading bars, and refuse another native ledger instead of pretending its
receipts are canonical. Unbound legacy behavior remains unmanaged. Existing
immutable installed F5 environments remain untouched; no coordinator rewrite was
needed. Actual deployment requires consciously enrolling/cooperating owners.

## Frozen search, costs and anonymous judgment

Static range generation receives only spec/ranges, never validation/final arrays.
Freeze input snapshot/hash, actual engine identity, loaded owner identity, baseline
spec/pins, cost inputs, search/objective/confidence and chronological geometry.
50/25/25 partitions have purge/embargo and 10–15 nonoverlapping blocks. Feature
warmup/horizon must cover every candidate window/slow-period. Maximum32 total
configurations and1000 consumed cells, including normal and 2x fee/slippage/carry
stress. Allocation checks planned work before evaluation. Failed/dropped trials
are consumed transactionally before evaluation and cannot be retried as fresh.

Current canonical research replay preserves end-cell inventory; completed trade
counts use actual round trips/deals/stopped deals/real non-final engine exits.
No artificial end-cell close, deleted inventory or trade relabeling. Reference
backtest output explicitly marks certification=false and unsupported position
independence due to unbounded horizons. Feature purge alone does not establish
position independence. Current real inputs therefore cannot produce a certified
winner. Full accepted/losing/error paths are demonstrated on explicitly controlled
fixture evaluator injection, which is not exposed by the wire protocol.

Judge packets allow only protocol version, exact policy, random opaque32hex IDs,
aligned integer chronological blocks and finite metrics/coverage/certification/
cost-stress fields. Nested unknown metadata rejects. No names, market, paths,
parameters, seed, incumbent flags, labels or free text. Policy: >=30 completed
trades, max20% drawdown, certified comparable coverage and nonnegative stressed
return; maximize median(net_return -0.5*drawdown), lower median turnover tie-break.
Return tied ID set; resolver retains tied incumbent; multiple tied challengers
cause no selection. Verify recomputed packet/policy/verdict digests and membership.
Validation pair freezes before final; persist verdict before mapping access audit.

## Actual OS boundary

Final macOS deny-default sandbox profile was executed, not merely detected.
The previous parent Python SIGABRT6 preflights are preserved. Diagnosis: Python
startup needs read-data of the literal root directory '/' (not descendants), and
framework Python.app executable avoids launcher's reexec. Runtime reads are only
System/Library, usr/lib, resolved Python base prefix and isolated child workspace,
plus random/null devices. Metadata is limited to runtime/workspace ancestor
literals; no general repository/home access. Network and other process execution
remain denied. Child python -I -S -B uses copied self-contained judge code in a
temporary workspace outside resolver/mapping paths, clean env/FDs, bounded streams,
10s sandbox wall deadline, 5s CPU, 1MiB file-size and32 FD resource limits.

m4-sandbox-final-proof.json v1.0 records actual final-profile reads_denied=[true,true],
metadata_denied=[true,true], network_denied=true, process_denied=true, available=true,
profile digest and source SHA256. Real mapping file and repository source were
probed; the proof artifact includes a redacted-workspace profile template because
actual temp paths change each launch. The full manager suite executes this proof
and an actual accepted anonymous judge packet. Unsupported platforms return
isolation_unavailable; Linux CI must prove explicit refusal rather than claim a
working sandbox. No Linux runtime was exercised locally.

## Final spend, statistical and receipt semantics

One shared conservative ordinal spans all related SOL scopes. Late imported
attempts increment the existing budget rather than resetting it. Freeze external
attempt count at preparation; changed external count before unseal refuses until
re-prepared. alpha_k=0.05/(k*(k+1)). Native exposure/final rows fence manager finals;
manager/imported dates fence native finals. Pair selection requires actual immutable
trial reports, not merely a fabricated valid-looking packet. Concurrent ordinal
allocation and final reservation have transactional tests.

Final admission durably spends dates BEFORE the first final cell. Failure, kill,
timeout or cancellation keeps spent history and retained incumbent. Recover closes
an interrupted attempt only after acquiring the optimizer lease. No rerun reopens
spent dates. >=10 decided blocks, positive median paired improvement, frozen
block-bootstrap policy seed0/10000 resamples/minimum10 are required. Sign p-value
is descriptive for the wire policy; independent-sign calculations exist only for
explicit helper fixtures. Too-small alpha resolution refuses. No caller boolean
can establish independence or certification.

Accepted fixture finals create immutable pending_shadow proposals, with authority
namespace/epoch/roster revision, relevant final-history revision, frozen attempt/
alpha context, baseline revision/hash, manual pins, changes and evidence digest.
History revision includes overlapping possibly-prior exposure, relevant gaps and
required participation; unrelated future dates and ordinary reads after final
admission do not invalidate a pending shadow. Newly imported conflicting prior
exposure or changed required roster invalidates reconciliation while preserving
historical evidence. No automatic configuration change occurs in M4.

Manager CAS writes an idempotent proposal receipt under the existing mutation lock;
owner mirrors it afterward. Retry recovers the exact own receipt after a crash
between databases. A fresh request after manual baseline/pin changes refuses;
replay of its own prior receipt remains attributable. This is not cross-database
atomicity. M6 must enforce >=7calendar days AND>=30 prospective-paper trades plus
fresh scope/pin checks before actual automatic promotion.

## Verification receipts (completed exits)

Working directory for all source checks: the worktree printed above.

RED evidence:
- Initial blind discovery exit1 (missing module), then5 tests exit0.
- Initial manager-owner API tests exit1 (missing methods), then5 tests exit0.
- Initial research discovery exit1 (missing module), later canonical fixtures green.
- Final authority regressions: unknown nested client accepted on status and missing
  prior store called verified:2 failures, exit1; focused owner/evidence25 exit0.
- Participating native mismatch/capture tests:2 errors reaching the loader instead
  of refusing, exit1; final complete owner/legacy group subsequently green.
- Public setup/default plan:1 unknown-command failure and1 missing-function error,
  exit1; research module10 tests exit0 after implementation.
- Epoch test:missing cutoff API TypeError exit1; then owner/evidence26 exit0,
  including old-window refusal, future admission, immutable cutoff and ordinal.

Final GREEN:
1. PYTHONPATH=botmanager/src /Users/mitch/.venvs/solbot/bin/python -m unittest discover
   -s botmanager/tests -t botmanager -q
   187 tests,32.443s, exit0. Complete manager suite, actual macOS OS judge.
2. PYTHONPATH=botmanager/src /Users/mitch/.venvs/solbot/bin/python -m unittest
   soltui.tests.test_experiments soltui.tests.test_experiment_runner
   soltui.tests.test_manager_evidence soltui.tests.test_research_owner
   soltui.tests.test_f5_batch soltui.tests.test_bgworker
   soltui.tests.test_bgworker_audit -q
   150 tests,6.269s, exit0. Complete required legacy modules and current owner fixes.
3. PYTHONPATH=botmanager/src /Users/mitch/.venvs/soltui/bin/python -m unittest
   soltui.tests.test_bridge_parity soltui.tests.test_bridge_surfaces
   soltui.tests.test_bridge_buttons -q
   42 tests,24.910s, exit0. No new command-registry action added after this check;
   describe/setup/default-plan additions reuse research.protocol.
4. Earlier unchanged relevant forwardtest + forwardtest_concurrency:31 tests exit0
   in the existing soltui UI environment. Earlier ecosystem backtests/runner/recovery:
   23 tests exit0. No broad unchanged M3 suite rerun beyond required manager suite.
5. Ruff full check+format on21 manager/new-owner/new-test files exit0. Legacy-owner
   touched-file diagnostics match baseline51 existing findings; fatal rules exit0.
   New test_experiment_runner additions pass full Ruff. git diff --check exit0.
6. Actual final-profile proof script exit0; denial booleans above.

Test environment corrections are not feature results: a mistaken executable path
solbot-manager did not exist (127); a nonexistent test_bridge selector and using
the UI environment without headless distribution metadata failed (exit1). Correct
headless source tests use solbot, UI bridge tests use soltui. No installation was
performed. Portable SolTUI fixtures use .research_fixtures, not another project's
generic tests package. Source package identity and installed distribution metadata
are reported separately; these are source tests, not an installed-M4 receipt.
Short synthetic timelines produce preexisting annualization overflow warnings;
all reported checks completed with their exact successful exits. Some legacy
manager fixtures emit sqlite ResourceWarnings; they did not fail these checks.

## Remaining gates for the parent's all-remaining-work plan

- Independently review the source and conditional statistical/authority contracts.
  In particular review initialization epoch scope/unknown pre-epoch alpha limits,
  immutable client participation and missing-history refusal, OS allowlist, and
  receipt validity across later paper admissions. No independent M4 acceptance yet.
- Integrate current upstream PR189/PR190 without regressing control-room/referral
  behavior. Replace obsolete ecosystem0.1.4 release plan with a forward bump from
  0.2.1; verify combined headless package dependency matrix.
- Parent refreshes canonical offline indexes after the final staged source set and
  runs required canonical/index gates; this worker did not index.
- Build/install combined reviewed wheels into isolated acceptance environments;
  verify loaded paths/hashes/versions from a temporary cwd, public research-setup ->
  first registration -> actual CLI backtest/research/default-plan flow, identity
  refusal, headless imports, cancellation/recovery and exact receipt reconciliation.
  Current user installations remain accepted M3, not M4.
- CI must include actual macOS sandbox proof and explicit unsupported Linux refusal,
  normal owner/test discovery and relevant bootstrap/F5 regression after integration.
- Real deployment requires verified known owner enrollment and honest history
  coverage. Existing active immutable unaware F5 installations remain blockers;
  do not stop/rewrite them or silently create another authority.
- Current Coinbase SOL/USD reference input and indicative Jupiter quotes cannot
  certify fills/network/priority/rent/fee coverage or bounded independence. Acquire
  certified comparable evidence through the proper future work before real strict
  final eligibility. No fixture proves profitable edge or real final freshness.
- M5 reports/attribution, M6 shadow-gated auto promotion, M7 natural-language/LLM
  boundaries and M8 final integration remain parent milestones. No work started.
- Push/PR/required CI/merge/remote verification are parent delivery gates after the
  requested planning checkpoint resumes. This report makes no delivery claim.

## Complete owned-file manifest

- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/README.md
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/pyproject.toml
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/__init__.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/blind.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/blind_judge.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/registry.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/research.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/research_owner.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/store.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/strategies/__init__.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/strategies/base.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/src/botmanager/strategies/grid.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/tests/test_blind.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/botmanager/tests/test_research.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/ecosystem/__init__.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/ecosystem/pyproject.toml
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/README.md
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/bgworker.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/commands.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/experiment_runner.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/experiments.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/f5_batch.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/forwardtest.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/manager_evidence.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/pyproject.toml
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/research_admission.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/research_owner.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/tests/bridge_support.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/tests/research_fixtures.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/tests/test_experiment_runner.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/tests/test_manager_evidence.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/soltui/tests/test_research_owner.py
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/.superpowers/sdd/2026-11-09-bot-manager/task-m4-report.md
- /Users/mitch/dev/solmargintrader-wt-01a1c189-editing/.superpowers/sdd/2026-11-09-bot-manager/m4-sandbox-final-proof.json
