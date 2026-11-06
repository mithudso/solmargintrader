# Repository bootstrap audit — 2026-11-06

Version: 1.1.0. Delta: integrated code safety references and verified metadata choices.

Scope: six-component repository at base `eebadbb`, isolated branch
`audit/bootstrap-cdo-20261106`. Existing untracked research/API files and the separate
session-key worktree remain outside this change. No previous bootstrap audit ledger
exists in this repository. Recalled tasks about other repositories are not evidence.

## Outcome

Corrected stale component, custody, setup, environment, CI and external-call descriptions.
Added missing contribution, requirements, cache, MCP-boundary and operational references.
Kept the existing execution architecture. The repository **does not pass the complete
mdb-tam five-standard operations contract**: its central operation registry, common error
schema, remediation maps and generated per-call cards are absent. Those gaps remain
explicit rather than being described as implemented or silently marked not applicable.

The paired code-deep-optimizer report owns code findings, regression evidence and its
convergence result. This report does not certify the whole codebase or live behavior.

## Standard-file manifest

| Artifact | Exists after pass | Review / action |
| --- | --- | --- |
| `CLAUDE.md` | Yes | Corrected six-component count, component Python rules, workflow records and missing semantic-indexer startup instruction |
| `AGENTS.md` | Yes | Linked real local scout definition; added workflow-record rule |
| `GEMINI.md` | Yes | Added liquidity boundary, shared workflow and component pytest exception |
| `.github/copilot-instructions.md` | Yes | Starts with execution strategy; current six-component architecture, verification and conventions |
| `prompts.md` | Yes | Parent task owns versioned verbatim request record |
| `memory.md` | Yes | Parent task owns resumable work/verification/remaining-step record |
| `docs/archive/`, `scripts/rotate-workflow-logs.mjs` | No | Deferred size-control helper; new workflow records are far below 200 KB; do not rotate active/swap files |
| `.editorconfig` | Yes | Existing UTF-8/LF/indent/final-newline rules match source style |
| `.gitignore` | Yes | Existing secrets/caches/worktrees protection retained; allow tracked VS Code launch config |
| `.gitattributes` | Yes | Existing LF/text/binary/generated classifications retained |
| `.nvmrc` | Yes | Node 22 matches verified CI runtime; package minimum is broader, not an exact pin |
| `.tool-versions` | No | Optional; no parallel toolchain authority added |
| `.env.example` | Yes | Names and blank secrets only; optional directory/key/interpreter overrides commented; explicit export, no automatic dotenv claim |
| `.vscode/settings.json` | Yes | Minimal editor rules; no dependency installation or auto-run configuration |
| `.vscode/extensions.json` | Yes | Python/debug/Ruff recommendations only |
| `.vscode/launch.json` | Yes | Existing Python CLI help and deterministic offline JS dry-run debug entries |
| `.vscode/mcp.json`, `.mcp.json` | No | No repo MCP server; machine-wide connectors are external; see `docs/MCP.md` |
| `.github/workflows/ci.yml` | Yes | Existing job behavior retained; actions pinned to resolved current tag commit SHAs |
| `.github/dependabot.yml` | Yes | Added existing mongo/liquidity Python manifests; no extension npm deps to update |
| `.github/CODEOWNERS` | Yes | Corrected stale handle to current repository owner; explicit money-moving and companion paths |
| `.github/PULL_REQUEST_TEMPLATE.md` | Yes | Added missing components, motivation, risk and rollback prompts |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Yes | Added mongo and liquidity component choices |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Yes | Existing scope/correctness questions retained |
| `.github/SECURITY.md` | Yes | Added Base key boundary and full threat-model link; retained honest absence of disclosure SLA |
| `LICENSE` | No | Owner decision needed for a repository-wide license; liquidity declares MIT but does not establish licensing for the whole tree |
| `CONTRIBUTING.md` | Yes | Source-derived scope, safety, validation and workflow-record guidance |
| `CODE_OF_CONDUCT.md` | Yes | Minimal conduct rules without invented moderation/SLA commitment |
| `README.md` | Yes | Added navigation; corrected six-component file-map description; research numbers untouched |
| `docs/ARCHITECTURE.md` | Yes | Six-component control/data boundaries and recorded existing design decisions |
| `docs/DEVELOPMENT.md` | Yes | Added real dependency/setup/commands and missing Python environment names; removed false dotenv behavior |
| `docs/COMPONENTS.md` | Yes | Explicit fetch modules and TUI KILL-file exception |
| `docs/SECURITY.md` | Yes | Liquidity custody, caps, simulation/receipt distinction and KILL controls |
| `docs/MCP.md` | Yes | No repo server or local MCP config; connector-independent retrieval commands |
| `docs/TESTING.md` | Yes | Existing counts left for parent final verification; added actual coverage/CI policy |
| `docs/codebase-overview.md` | Yes | Added current fetch, worker, liquidity safety and workflow references; no stale duplicated test totals |
| `docs/high_signal_file_index.json` | Yes | Parent regenerates with existing `scripts/build_doc_index.py` after new intended files are staged |
| `index/` | Yes | Existing exhaustive offline metadata/text/concept builders; parent regenerates after final code changes |
| `scripts/semantic_indexer.py`, `scripts/watch_and_index.sh` | No | Existing `index/build.py semantic` is the explicit optional embedding path; no redundant daemon created |
| `scripts/check-doc-indexes.mjs` equivalent | Yes | `scripts/check_docs.py` and `index/build.py --check` already run in CI |
| `docs/integrations-and-assumptions.md` | Yes | Added Base/GeckoTerminal/DefiLlama/Mongo/funding integrations; corrected macOS CI and explicit network-test boundary |
| `docs/known-issues.md` | Yes | Labelled historical cache observations; removed stale no-test/no-marker claims; retained unresolved live risks |
| `docs/onboarding.md` | Yes | Added missing components, offline-test boundaries and correct working-directory sequence |
| `docs/INSTALLATION.md` | Yes | Six setup stories; separate live service install; no test-count claims duplicated here |
| `docs/requirements.md` | Yes | Implemented functional, dependency and safety boundaries only |
| `docs/logging.md` | Yes | Existing component event sinks and remaining transport coverage limits |
| `docs/caching-and-optimization.md` | Yes | Cache owner/freshness, evidence rules and existing offline index regeneration |
| `docs/runbooks/incident.md` | Yes | Kill, preserve evidence, reconcile, escalate unknown state |
| `docs/runbooks/rollback.md` | Yes | Revert without losing journal/ledger or assuming source rollback undoes a trade |
| `docs/runbooks/handoff.md` | Yes | Resume from prompt, memory, Git and configured task state |
| `docs/external-calls.md` | Yes | Replaced four-call claim with HTTP/RPC/local-service/process/storage inventory and explicit coverage gaps |
| `server/src/lib/operations-registry.js` | No | No server package exists; creating one is a separate architecture change |
| `scripts/generate-ops-registry-doc.mjs` | No | No canonical operations registry to generate from |
| `docs/operations-registry.json`, `docs/tool-inventory.json` | No | No invented generated output; command parity already uses the extension registry |
| Repo context skill sidecars | No matching context files | Existing `docs/dso-skill/` is source material; no extra installed skills fabricated |

## Corroborated drift and changes

1. The old external-call page claimed four calls and no research/soltui network path.
   Source includes minute/tick/funding/product fetches, Base RPC and simulation/broadcast,
   GeckoTerminal/DefiLlama, MongoDB, explicit TUI fetch subprocesses, and optional index
   Ollama calls. The replacement states each boundary, timeout/retry/log/test limits.
2. Installation/onboarding and agent pointers omitted liquidity or MongoDB. They now
   distinguish dependency setup, offline tests, optional service install and live action.
3. The old development page said only extension tools read environment variables and
   implied `.env` auto-loading. Python source reads research cache, liquidity home/key,
   launcher and worker handoff variables. Examples now name them without storing values.
4. The old integration page said soltui had no CI gate. The existing workflow runs its
   suite on macOS, omitting a private supervisor dependency. Docs preserve that limit.
5. Root Python guidance incorrectly generalized backtester's unittest/dependency rules
   to liquidity. Component-specific pytest/Ruff/web3 rules now remain explicit.
6. CODEOWNERS named a stale handle. It now uses `@mithudso`, matching current GitHub
   repository ownership. Existing action versions are unchanged and immutable-pinned.
7. The top agent rule named nonexistent semantic-indexer scripts and demanded startup.
   It now uses configured semantic search with local keyword/source fallback and explicit
   optional embeddings. Startup does not implicitly start inference or indexing.

## Extended checks

- **Agent inventory:** one tracked local definition, `.claude/agents/aero-pool-scout.md`.
  Its sonnet model/tools/read-only remit is recorded; no global agents copied into repo.
- **Stack/skill coverage:** Python/NumPy/pandas, Textual/macOS, pymongo, ESM/MV3/WebCrypto,
  web3/httpx/SQLite/Ruff/pytest all have installed language/platform/domain coverage.
  Availability does not prove that each module received a code review; see optimizer scope.
- **Auth surfaces:** Jupiter key and encrypted session-key vault, local HTTP bearer token,
  separate liquidity key file/Keychain/legacy env fallback. Docs state custody and failure
  boundaries. No credential was read, copied or added by this pass.
- **MCP/native host/offscreen:** no repository MCP server, native-host tree or offscreen
  document implementation found. No fake health test or native manifest was added.
- **Concept tree:** repo uses `index/CONCEPT-INDEX.json`, built by `index/build.py`;
  no `concept-tree/tree.json` standard is imposed on this existing implementation.
- **Dependencies:** extension declares zero runtime/dev dependencies, so no npm lock/audit
  was invented. Liquidity has a committed uv lock. Mongo/liquidity bot coverage was missing
  and added. Liquidity uses the `uv` ecosystem for its pyproject and lock, per the
  [GitHub ecosystem reference](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories).
  Current vulnerability/outdated-package conclusions require a separate live
  advisory lookup; this pass does not claim one.
- **Data in VCS:** research result CSVs are intentional evidence. Existing captured/scratch
  artifacts and tracked `.remember` history were preserved, not deleted or republished.
  This filename/source audit is not a complete credential or PII scan.
- **Historical records:** preserved dated research, captured docs and audit context. No
  claimed research figure or held-out result was changed during this bootstrap pass.

## Validation and remaining work

Editor JSON files parse with Python's stdlib JSON parser. Action tags were resolved with
`git ls-remote` to their existing release commits on 2026-11-06; annotated setup-uv tag
was peeled to its commit. No action-version upgrade occurred.

The shell-default `python3 scripts/check_docs.py` refused to count because 20 test modules
could not import their dependencies. This is an interpreter/setup gap, not evidence that
document counts are wrong. No dependency installation ran in this pass. The parent audit
uses the validated suite environment for final checks and owns final index regeneration,
test totals, code-optimizer findings, commit and CI receipts.

Remaining gaps:

- Repository-wide license choice requires the owner. Do not infer it from one component.
- Five-standard operation-level error/remediation/card/read-back infrastructure remains
  absent or partial, as each inventory row states. It needs a scoped architecture design;
  generic auto-retry on money-moving operations is unsafe.
- Workflow-log rotation helper is deferred until size control is needed. Preserve swap
  refusal and version boundaries when implementing it.
- External-call inventory is manual; current doc/index gates do not prove call coverage.
- Live extension envelope/fee attribution, installed Chrome/app/service acceptance and
  real operation outcomes remain separate from offline tests.

The paired optimizer report records integrated verification and delivery. Its result remains
BLIND-AUDIT-DISSENT; focused repairs do not imply repository-wide or live acceptance.

Final local gate: 681 backtester tests pass; 402 TUI tests run with one skip; 33 Mongo
tests run with 17 driver/server skips; 237 extension tests pass; liquidity 427 pass
with six network tests deselected. Ruff check/format, module syntax, deterministic
offline round trip, documentation counts and offline index checks pass. CI supplies
the service-backed MongoDB and independent runner receipt before merge.
