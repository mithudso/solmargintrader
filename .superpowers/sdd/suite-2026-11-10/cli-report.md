Version: 1
Delta: Initial completed CLI, ordered walkthrough, UI discovery and platform-guide implementation.
Task: TASK-1247
Owner: /root/cli_workflow

Implemented in the shared isolated worktree /Users/mitch/dev/solmargintrader-wt-1247-suite:

- Registered stack, ui, health-check, metrics and component-alerts through CommandSpec.
- Kept CLI application logic in registry handlers. Metrics renders plain Prometheus only on success; errors retain sanitized JSON and established exit-code categories.
- Replaced the three-command root epilog with 18 ordered stages and 118 complete solbot command examples. The same stages are available in structured help. Parser tests cover all 57 commands and all stack, ui, service, browser-control, prepare-input mode and report-format choices.
- Included genuine source/research/learning prerequisites, default/immutable/CAS editing, independent reference families, separate prospective/historical descriptors, source-issued IDs, report pagination, browser observation guards/receipts, optional owner-produced executor request artifacts, backup/new-home restore and guarded recovery alternatives. No example arms a wallet or invents source certification or elapsed shadow evidence.
- UI status reads verified owner/checkpoint/HTTP identity without starting a process or guessing a port. Explicit start/open uses the suite, and browser launch failure preserves the actual verified URL. Missing optional ecosystem package produces a structured capability refusal.
- Added a macOS/Linux/Windows comparison, fresh headless Linux install recipe, systemd linger limitations, native-helper setup and WSL2/Windows Chrome bridge limits. The suite starts manager/UI availability and observes existing reference freshness; acquisition, F5 and recorder owners remain independent.

Verification completed successfully:

1. `PYTHONPATH=botmanager/src:botmanager/tests:. INDEX_NO_AUTO=1 /Users/mitch/.venvs/solbot-0.6.0/bin/python -m unittest test_cli test_operations test_walkthrough -v` — 21 tests, exit 0.
2. Ruff check of the four owned modules and three owned test files — exit 0.
3. POSIX shell syntax validation of all walkthrough setup/command/capture snippets — included in passing tests; parse-only, no component startup.
4. Exact parser validation of 118 published solbot examples against the actual 57-command registry — included in passing tests.
5. Explicit --help/bare help/structured help and missing-home health/UI tests verify no home creation and no secret-canary output.
6. git diff --check of owned source/test/guide paths — exit 0.

Integration remaining with parent:

- Independent combined source review and full component checks.
- Regular installed-package acceptance from outside the checkout.
- Migration of the exact verified old manager service, installation/enablement of the suite and native helper, and loaded extension/UI acceptance.
- Actual Linux/Windows installation and physical reboot were not performed by this scoped worker. The guide does not claim they were.
- Parent owns prompt/memory versions, release matrix, final CI/PR merge and remote-content proof.
