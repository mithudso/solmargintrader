# Optimization workbench execution log

Version: 2
Delta: v1 to v2; record concurrent strategy-browser delivery reconciliation.

## Work log

Goal: implement all six accepted comparison recommendations.
Scope: native simulated optimization and read-only external evidence in SolTUI.
Done-condition: usable shared-registry features, verified evidence/control boundaries and remote delivery.

The implementation plan is `docs/optimization-workbench-plan.md` v5. Plan A contracts were satisfied before implementation; foundation, runner and interface owners implemented against them. A bounded continuity follow-up permits sealed final periods as later training history, while preserving permanent final-test spend and active-reservation protection. An independent reviewer reproduced three issues and verified their fixes: unbound CSV rows, lost launch controls and inconsistent drawdown signs. Loaded acceptance exercised actual native simulation and subprocesses with isolated synthetic configuration/data. No owner data, order path, paused job or running service was changed.

## Project

Project key: `git@github.com:mithudso/solmargintrader.git`. Existing registry entry reused. Stele epic TASK-952, contract task TASK-953, implementation task TASK-961 and final verification/delivery task TASK-962 provide the canonical lifecycle receipts.

## Context found

- `soltui/bots.py`: existing adaptive candidates, simulator adapters and significance gates.
- `soltui/bgqueue.py`: prior durable whole-job queue and evidence limitations.
- `soltui/commands.py`: shared CLI/API/UI registry.
- `soltui/bots_screens.py`: existing candidate/progress modal.
- `research/perturb.py`: existing one-at-a-time sensitivity differs from observed joint maps.
- Project registry: existing `solmargintrader` record; no duplicate registration.

## Existing artifacts

Existing simulators, command bridge, Bots UI and root llms family were reused. The upstream optimizer dossier/index was already delivered by PR 95 and was not rebuilt or modified by this work.

## Plan

1. Foundation: immutable specifications/cells, typed budgets, sparse maps and reported imports.
2. Native runner: frozen evidence, checkpoints, spent-date guards and safe adoption.
3. Interface/lifecycle: registry endpoints, detached worker controls and the workbench.
4. Independent review and correction of concrete boundary failures.
5. Loaded CLI/worker/headless UI acceptance on isolated real simulation fixtures.
6. Documentation, generated retrieval metadata and remote delivery; final receipts are in TASK-962.

## Open questions

No unresolved product decision. Installation synchronization is separate from code acceptance: the installed wrapper points to a shared checkout held by other active sessions. That checkout and running services remain unchanged until synchronization is safe. Local freshness cannot establish absence of external/manual inspection of dates.

## Agents

| Owner | Work | Result |
| --- | --- | --- |
| foundation | Store, spaces, maps, imports | complete; focused regressions pass |
| runner | Native frozen evaluation and promotion | complete; 27 runner regressions pass |
| textual-job-lifecycle-specialist | Process lifecycle and interactive workbench | complete; focused interface/foundation and parity checks pass |
| independent reviewer | Reproductions and fix verification | all three findings cleared |
| live-acceptance-verifier | Actual loaded source, CLI, processes and UI | core and workbench acceptance pass; final wiring receipt recorded in TASK-962 |

Agents inherited the native model. Claude-specific model labels in the planning skill are unavailable in this harness. Ownership was explicit; the orchestrator did not edit application/test source. The final delivery follows the user's standing Git authorization, which takes precedence over the planning skill's Git prohibition.

## Artifacts written

New core modules: `soltui/experiments.py`, `soltui/experiment_runner.py`, `soltui/experiment_jobs.py`, `soltui/experiment_screens.py`. Three new dedicated regression suites accompany them. Existing Bots, registry, TUI, help and parity fixtures were integrated narrowly. The guide, versioned plan, workflow records, context bundle and sourced llms additions preserve continuation context. Generated repository indexes are rebuilt offline; no semantic inference service was started.

## Stage log

| Stage | Outcome | Evidence |
| --- | --- | --- |
| Resolve | complete | p helper run 20261108-063425 |
| Recall | complete | source, existing registry, scoped graph and current architecture |
| Register | reused | existing solmargintrader record |
| Plan | complete | versioned plan before source changes |
| Research | skipped | max-research=0; existing source and current Textual docs sufficient |
| Bundle | complete | p helper wrote context-bundle.json |
| Helpers | none | no reusable helper required |
| Dispatch | complete | explicit owners and returned artifacts |
| Compile | complete | p helper backed up and appended 7 sourced facts plus routing entry |
| Self-check | 8/8 | deterministic helper, no invalid artifacts |

A complete SolTUI run passed 947 tests in 721.036 seconds, with two expected skips, before the bounded sealed-history refinement. The final focused gate passed 79 tests; six new continuity regressions bring current discovery to 953. Actual CLI/worker/workbench acceptance was rerun with stable final source hashes. New Python modules/tests pass Ruff; documentation counts, offline index hashes, card coverage and 11 HTML converter tests pass. Required final-commit CI, merge and installation-boundary receipts are maintained in TASK-962 rather than inferred from this pre-merge document. The shared checkout's unrelated work is preserved.

The initial final CI passed all eight checks, including 953 SolTUI cases with 14 expected optional-dependency skips. Concurrent PR 99 then advanced the default branch and caused a merge conflict. The delivery phase preserved its Strategies browser, combined both workflow histories and regenerated derived indexes. The only source correction was the shared handler-count test: both independent changes added one button, so the combined count is 68. Forty-five targeted cases, the incoming Strategies UI and actual combined Bots/workbench preview/dismissal pass. Final combined-tip CI and installed parity remain bound to TASK-962.
