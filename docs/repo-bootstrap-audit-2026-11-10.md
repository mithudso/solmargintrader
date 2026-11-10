# Repository bootstrap audit — 2026-11-10

Version: 1.0.0
Delta: Refresh the ten-component workspace, maintained wiki, bounded availability fix and retrieval evidence.
Task: TASK-1256. Baseline: 70ac8b74527281a9e49a4be22992b4ee44e8805e.

## Outcome

This is a completed bounded bootstrap pass, not full five-standard compliance or a whole-repository code-quality certificate. Historical audit records remain intact. The Nov8 operations N/A conclusion does not establish compliance: the central registry, common error/remediation infrastructure and generated per-call cards remain absent, as the Nov6 audit and KNOW-750 record.

Reused the existing packaged ecosystem wiki. Its navigation now covers commands, reference material, scripts, strategy and maintenance without creating another wiki backend. Corrected ten-component architecture, Oracle MCP, managed health/security/logging, archived liquidity and separately armed SolTUI manual-order boundaries. Added current environment-variable names without secret values. Refreshed source-bound LLM navigation and current package/readme metadata.

The bounded CDO pass reproduced FIFO hangs before regular-file validation. Five opens in four availability modules now open nonblocking before type/owner validation. Seven subprocess cases cover reads and startup logs, including a FIFO with an attached reader. Manager source is patch candidate0.7.1 and ecosystem0.4.1; bootstrap selects a new0.4.1 environment. Existing installed0.7.0/0.4.0 environments and all live services/producers remain untouched.

The existing guarded rotation archived178 older memory sections, retaining20; memory.md fell from about325KB to81KB. Workflow versions remain independent of package versions. No semantic embeddings or inference were generated.

## Standard manifest

| Artifact | Present | Assessment |
| --- | --- | --- |
| `.github/copilot-instructions.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `AGENTS.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `CLAUDE.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `GEMINI.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `memory.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `prompts.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `scripts/rotate-workflow-logs.mjs` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.editorconfig` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.gitignore` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.gitattributes` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.nvmrc` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.env.example` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.vscode/settings.json` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.vscode/extensions.json` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.vscode/launch.json` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.vscode/mcp.json` | no | Optional host client registration; do not copy credentials or invent archive selection. |
| `.mcp.json` | no | Optional host client registration; do not copy credentials or invent archive selection. |
| `.github/workflows/ci.yml` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/dependabot.yml` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/CODEOWNERS` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/PULL_REQUEST_TEMPLATE.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/ISSUE_TEMPLATE/bug_report.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/ISSUE_TEMPLATE/feature_request.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `.github/SECURITY.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `LICENSE` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `CONTRIBUTING.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `CODE_OF_CONDUCT.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `README.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/ARCHITECTURE.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/DEVELOPMENT.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/COMPONENTS.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/SECURITY.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/MCP.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/TESTING.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/ECOSYSTEM-WIKI.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/codebase-overview.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/high_signal_file_index.json` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/integrations-and-assumptions.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/known-issues.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/onboarding.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/INSTALLATION.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/requirements.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/logging.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/caching-and-optimization.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/external-calls.md` | yes | Existing artifact reviewed; source-derived updates where needed. |
| `docs/operations-registry.json` | no | Major architectural backlog; no full-standard pass. |
| `docs/tool-inventory.json` | no | Major architectural backlog; no full-standard pass. |

## Existing equivalents and scope

Existing index/build.py, index/search.py and scripts/check_docs.py provide offline metadata/text/concept retrieval and CI path/hash checks. No redundant semantic daemon, server/src package or empty npm lockfile was created. Agent inventory matches both real repository agents. No offscreen extension document is present. The zero-dependency extension does not require an invented dependency lock.

## Verification and convergence

1. Source audit identified stale component/MCP/security/wiki descriptions and the historical standards discrepancy.
2. Remediation corrected corroborated metadata, FIFO opens, package environment defaults and workflow-log size. Generator component classification now includes all ten components.
3. Verification checked links, source paths, package imports, bounded FIFO regressions, wiki/keyword artifacts and final CI. Any remaining architectural and coverage gaps stay explicit below; they were not relabeled clean.

Completed local results: manager360, ecosystem180, health10 with7 subprocess scenarios; Ruff and diff checks passed. Documentation count discovery reports1003 backtester,434 extension,46 mongo and1466 SolTUI tests, total2949. See the independent code-review result and private candidate installation receipt for their separate evidence; final-head CI and remote delivery receipt are recorded outside the repository after delivery to avoid self-invalidating generated artifacts.

## Residual gaps

- Major: full five-standard operations infrastructure remains absent. No central operation registry, common error schema, complete remediation maps or generated per-call dashboard cards exist. Generic automatic retry is unsafe for ambiguous money-moving writes. A separately scoped design is required.
- Medium: external-call documentation now covers ten additional logical transport boundaries, but it is not an exhaustive per-call-site inventory.
- Medium: Dependabot does not cover every Python component; coupled first-party version pins need deliberate release maintenance. No current vulnerability clearance is claimed. Endor tooling is unavailable for unchanged mcp1.30.0.
- CDO is CAPPED:6/695 eligible files reviewed,689 explicitly unreviewed. The pass receipt and exclusions are in docs/code-deep-optimizer-2026-11-10-bootstrap.md and .cdo/. Historical unresolved findings were not reasserted as current without reproduction.
- The external LLM dossier records a full shallow census and nine fully read manifest/parser inputs. Its executable inventory is explicitly partial; dynamic CLI flags, complete config/env-call graphs and deep per-file semantics are not claimed complete.
- No fresh whole-repository customer-data body scan, hosted-wiki access audit, native Linux boot, physical reboot or everyday Chrome loading check was performed by this bootstrap pass. Existing installed acceptance receipts remain separate historical evidence.

## Continuation and preservation

Authoritative current navigation: docs/ECOSYSTEM-WIKI.md, docs/bot-manager-managed-suite.md and llms.txt. External dossier: /Users/mitch/.research/distillations/solmargintrader-bootstrap-1256.repo. Private verification/delivery evidence: /Users/mitch/.local/state/solbot/bootstrap-1256/. Unrelated primary files and the locked SolTUI worktree are preserved. Do not restart archived liquidity, frozen research producers or the installed suite to verify a documentation change.
