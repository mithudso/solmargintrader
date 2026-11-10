# Experiment fixture teardown repair

Version: 1.0.0
Delta: Initial bounded reaper completion repair and repeated lifecycle verification.

The 219-test affected-source run failed with OSError66 Directory not empty at temporary config/experiments cleanup. The detached experiment-reap thread then logged no such table: runs. Popen.returncode is set before that reaper finishes its journal reconciliation.

The controller could not spawn the textual-job-lifecycle-specialist because all concurrency slots were occupied. The controller read /Users/mitch/.claude/agents/textual-job-lifecycle-specialist.md and applied its workflow inline. It did not claim that a specialist ran.

The test fixture now joins only its own run-named reaper threads with a five-second bound before deleting its temporary store. An unfinished thread fails the check. The stdout-success case also waits for an actual failed/interrupted journal state; printed success remains diagnostic. Production job behavior is unchanged. One existing local import separation was corrected for Ruff.

Ten full JobLifecycle repetitions passed: seven tests per repetition, 70 completed tests, exit0. Log: /Users/mitch/.local/state/solbot/releases/0.6.0/textual-teardown-repeat.log. A full affected selection remains a controller integration gate after learning changes freeze. No personal state, producer, service or installed environment changed.
