# M4 source recovery report

Version: 1.0.1
Delta: 1.0.0 -> 1.0.1; normalized closed-pipe deadline failures after independent P2 review. Initial recovery: recovered checkpoint e24ad7ca343a07910d04f3c3471494fcba763c75 onto current master integration; tightened receipt participation and sandbox execution.

## Scope and changes

Recovered 21 owned M4 source/test paths. Existing recovered files have byte-identical e24 parent and current HEAD bases. An initial recovery also replaced the newer generalized catalogue coverage test; restored that exact path to HEAD before commit. registry.py M4 additions were recovered but ownership returned to controller for later command integration; registry.py is excluded from this source commit. Package versions, strategy implementation, documentation, prompt and memory records remain controller/other-agent work.

Preserved canonical research setup/default bounded plan, explicit authority enrollment/immutable epoch, append-only shared history, public owner protocol, descriptive costed replay, frozen 50/25/25 geometry with horizon purge/embargo, 32-configuration/1000-cell budgets, 30 trades, 20% drawdown rail, median(return - 0.5 drawdown) score/turnover/incumbent tie rules, frozen challenger, 10 decided blocks and shared alpha_k=0.05/(k*(k+1)). Current reference/independence gaps refuse strict certification.

Added fail-closed proposal and receipt checks when requested known-client requirements differ from registered participation. Stale bodies remain inspectable. Regression tests cover later harmless paper imports, training imports, newly imported historical final overlap, unregistered newly required participant and public registration of that participant. Registry overrides remain non-production.

## Actual sandbox proof and failed attempts

The original deny-default sandbox-exec profile permitted the exact CPython binary for initial startup. Real os.execv of that same binary succeeded and printed 123. External /bin/echo was already denied. A nested sandbox_init tightening attempt inside the existing sandbox failed with result -1 and error Operation not permitted. These failed attempts are retained here and must not be described as successful isolation.

Replaced the exec allow-list with a fixed trusted bootstrap that starts CPython, loads only ctypes, then applies deny-default Seatbelt using sandbox_init before loading judge source or reading the input packet. There is no process-exec permission. A failed initialization refuses; unsupported hosts never launch bounded_process or an unrestricted judge. Existing earliest checkpoint Python startup failures are not available as raw artifacts in this worktree; preserve any controller-held earlier evidence rather than inventing it.

Real current macOS proof: available=true; absolute resolver/repository reads denied; metadata denied; network denied; fork denied; exact CPython re-exec denied; external process denied. Allowed judge startup and actual winner selection pass through the same launcher. Profile digest is workspace-dependent because each temporary workspace is literal-bound.

## Verification

- Focused manager research/blind suite: 17 tests, exit 0 (includes real Seatbelt and unsupported-host no-process regression).
- Owner/evidence/experiment/catalogue suite: 70 tests, exit 0, one skip (missing optional UI dependency in solbot environment).
- Affected bgworker/audit/F5/policy/forward/concurrency/native/paper/interface suite in existing soltui environment: 137 tests, exit 0.
- Ruff over new M4 modules, manager store and M4 tests: exit 0.
- Broad legacy touched-file Ruff: 51 existing diagnostics; HEAD and worktree have identical counts per code, zero new diagnostics. Broad lint is not claimed clean.
- Full manager discovery with absolute PYTHONPATH: 198 tests, six failures in checkpoint numeric equality while concurrent accounting/strategy changes were in progress. Controller notified for final freeze/rerun. Earlier relative PYTHONPATH/discovery attempts failed to import tests or locate worker code; those are command failures, not passing checks.
- git diff --check over owned changes: exit 0.

## Remaining delivery gates

Controller must complete fresh independent review, final integrated manager test run, regular candidate installation from reviewed source, outside-checkout public setup/register/backtest/research/owner and OS-denial acceptance, asset/source parity, final-head CI and delivery. This report establishes source readiness only. No production home or actual research history was changed; no environment was installed or mutated by this worker.

## Independent review P2 correction

The independent review reproduced subprocess.TimeoutExpired when a child closed both output pipes but remained alive past bounded_process's final wait. The helper now normalizes this exception to ValueError("process deadline exceeded") inside the existing cleanup boundary. OwnerClient.call therefore retains its structured research_unavailable refusal path. Process-group termination, reaping and pipe closure remain unchanged.

The real subprocess regression closes file descriptors 1 and 2, sleeps past a 0.1-second deadline, asserts the normalized ValueError, checks closed pipes and proves the child was reaped with os.waitpid raising ChildProcessError. Focused tests.test_blind plus tests.test_research completed: 18 tests, exit 0. Changed-file Ruff and whitespace checks passed. No broader suites, installations or production state changes were performed for this narrow correction.
