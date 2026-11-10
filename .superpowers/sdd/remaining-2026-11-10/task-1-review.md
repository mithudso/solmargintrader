# Independent M4 review

Version: 1.0.1
Delta: 1.0.0 -> 1.0.1; independently re-reviewed sole P2 correction cb1ddab49e2df2a938a6be1907c9e3a4c6c5cb0f. Original review covers frozen task-1-review-package.diff and relevant integrated source through d7aa933.

## Verdicts

**Spec compliance: PASS for reviewed source, conditional on outstanding delivery acceptance.** The source preserves the M4 research constraints. This verdict does not establish installed acceptance, final-head CI, remote delivery, or profitable/certified current evidence.

**Code quality: PASS.** The sole P2 error-normalization defect is resolved in cb1ddab49e2df2a938a6be1907c9e3a4c6c5cb0f. No remaining important findings in the reviewed M4 source scope.

## Findings (severity order; resolved)

### RESOLVED P2 — Closed child pipes let deadline exceptions escape the public owner refusal path

Locations: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/blind.py:104 and /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/research_owner.py:90.

If the child closes stdout and stderr before exiting, the selector loop completes. The subsequent process.wait(timeout=...) raises subprocess.TimeoutExpired when the child remains alive. The ordinary deadline branch raises ValueError, but this branch does not normalize the exception. OwnerClient.call does not catch TimeoutExpired. As a result, the owner-protocol failure can escape the documented ManagerError research_unavailable path instead of returning a structured refusal. The finally block still kills and reaps the child, so the process bound itself holds.

Focused reproduction, executed successfully during this review (no installation or persistent home mutation): PYTHONPATH=botmanager/src python3 imported bounded_process and invoked the current interpreter with -I -S -c 'import os,time; os.close(1); os.close(2); time.sleep(2)', payload b'', env={}, a temporary cwd and timeout=.05. Observed exception: TimeoutExpired, with approximately .039 seconds remaining in the final wait. This is a new targeted reproduction, not a rerun of previously completed suites.

Fix: normalize subprocess.TimeoutExpired inside bounded_process to the same ValueError deadline refusal used by its selector loop, retaining cleanup. Add a focused test covering EOF on both pipes while the child is still running. Alternatively normalize it at all consumers, but the shared helper is the more consistent boundary.

## Specification evidence reviewed

- /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/research.py:21 freezes chronological 50/25/25 partitions with horizon separation. Candidate enumeration admits at most 32 configurations; execute checks the normal/stressed allocation against 1,000 cells before creating an attempt.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/blind_judge.py:12 fixes at least 30 completed trades, drawdown at most .2 and median(net_return - .5 * drawdown), followed by lower median turnover. Resolver ties retain the incumbent and refuse arbitrary challenger ties.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/research.py:171 requires at least 10 decided blocks, positive median improvement and the shared alpha_k=.05/(k*(k+1)). Current public backtest evidence explicitly remains uncertified with unsupported position independence; the public owner does not accept an evaluator injection. The injected certified evaluator is an in-process test seam, not a wire operation.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/manager_evidence.py:446 validates anonymous training/validation evidence, freezes exactly one challenger, persists mapping-access audit and permanently spends the final before holdout evaluation. Interrupted finals cannot be replayed. Ordinals aggregate related SOL strategies and imported attempts.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/research_admission.py:449 requires explicit first initialization, stores an owner-clock epoch and marks unknown earlier history unavailable. Existing registration prevents a new authority identity/root and refuses recreation of a missing registered database. Native participating work refuses another local ledger.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/research_owner.py:266 retains stale proposal bodies while refusing reconciliation after changed required participation, registry roster or scoped imported prior exposure. /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/manager_evidence.py:626 excludes ordinary later reads from retrospective invalidation and includes historical overlapping imports and relevant gaps. Reviewed fixture assertions cover these distinctions.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/soltui/research_admission.py:29 provides the shared nonblocking optimizer lease. Participating bg/F5/forward/native callers reuse the existing owner and acquire that lease; no second optimizer was added.
- /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/blind.py:32 refuses unsupported hosts before process launch. The fixed trusted bootstrap applies deny-default Seatbelt before loading judge source/input. Absolute resolver/repository access, metadata, sockets, fork, exact Python re-exec and external execution have real denial tests. Judge input/output have 1 MiB bounds and the judge sets a 5-second CPU limit, with launcher wall-clock termination. No unrestricted substitute exists.

## Evidence limits and cross-milestone observations

I trusted the implementer test reports as permitted and inspected the actual reasoning and assertions. I did not rerun full suites, install packages, modify production configuration/history, or perform live actions. Earlier failed sandbox startup probes must remain preserved in controller-held evidence; the source report explicitly does not claim those missing raw artifacts are present here.

The frozen review package excludes registry/package/documentation integration. Current source also includes Task 5 learning-owner integration outside the frozen M4 package; no new blocking interaction was established in this review. Final identity/source parity must use the complete final integrated installation, since learning modules participate in the current owner identity. The forward-compatible package matrix, complete manager regression result, regular installations, public outside-checkout setup/register/backtest/research/owner tests, actual OS-denial acceptance and final-head delivery remain controller gates.

No product files were changed by this reviewer. Only this review artifact was written.

## Independent correction re-review

Reviewed the exact cb1ddab49e2df2a938a6be1907c9e3a4c6c5cb0f diff in /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/blind.py, /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/tests/test_blind.py and /Users/mitch/dev/solmargintrader-wt-01a1c447/.superpowers/sdd/remaining-2026-11-10/task-1-report.md. The new subprocess.TimeoutExpired handler wraps the final wait and normalizes it to ValueError("process deadline exceeded") before the unchanged finally block kills/reaps and closes both pipes. This addresses the reproduced trigger and restores OwnerClient.call's existing refusal normalization.

The regression starts a real child, closes file descriptors 1 and 2, sleeps beyond the deadline, requires the exact normalized ValueError, checks pipe closure and verifies that os.waitpid raises ChildProcessError after reaping. The reported focused 18 blind/research tests and changed-file checks completed successfully. I inspected the test reasoning and accepted those completed results without redundant reruns. No additional source regression or required correction was identified.

Specification and quality verdicts now pass for M4 source. The original installed/delivery limitations and separate Task 5 integration review boundary remain in force.
