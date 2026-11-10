# Incremental code-quality audit — bootstrap 2026-11-10

Version: 1.0.1
Delta: v1.0.0 to v1.0.1; reconcile the performed audit with the generated receipt and preserve the failed intermediate run.

This is a **CAPPED** source review, not a repository-wide clean certificate. It reviews six explicitly prioritized availability files from 695 eligible source files; 689 remain unreviewed by the new ledger. The existing 2026-11-08 report remains historical evidence and its 13 residual findings were not re-certified or silently closed here. The default planner's initial 50-file queue and 645 further paths were inspected as inventory only. The six availability files were prioritized under the caller's scope; unvisited paths remain ready for another run in `.cdo/remaining-2026-11-10.json`.

The run uses code-deep-optimizer 1.17.1, standard severity, no feature or advisory phase. Repo-bootstrapper delegated this bounded code phase; no nested agents ran. Because the scope is capped and no clean exit is asserted, the blind exit gate is not claimed. Unit suites are must-pass regression checks, not a separate held-out eval/benchmark surface; empirical champion promotion did not engage and no durable champion was written.

## 1. Per-iteration severity

| Iteration | Critical | High | Medium | Low/Nit | Outcome |
| --- | ---: | ---: | ---: | --- | --- |
| Diagnose | 0 | 0 | 2 | Not pursued | Reader and startup-log FIFO counterexamples reproduced |
| Repair/recheck | 0 | 0 | 0 in the assigned scope | Not pursued | Five unsafe opens corrected; broader scope remains capped |

## 2. Findings

| Pass | File:line | Severity | Finding | Fix | Status |
| --- | --- | --- | --- | --- | --- |
| C1/C3/S2/S3/P2/T1 | `botmanager/src/botmanager/machine_health.py:35`, `botmanager/src/botmanager/suite_service.py:164`, `ecosystem/ui_service.py:152` | Medium | Bounded private readers called blocking O_RDONLY before checking the opened descriptor's regular-file type. A FIFO without a writer hangs before validation. | Add O_NONBLOCK while retaining O_NOFOLLOW, same-fd fstat ownership/type/size checks and bounded reads. | Fixed; three subprocess counterexamples turn timeout-red to green |
| C1/C3/S2/S3/P2/T1 | `botmanager/src/botmanager/suite.py:688`, `ecosystem/ui_service.py:355` | Medium | Startup log opens can block on a FIFO; the suite path also lacked regular-file validation, so a FIFO with an attached reader could reach process creation. | Open logs nonblocking; retain the UI identity check and add the suite's same-fd regular-file/owner/private-mode validation before spawning. | Fixed; both owners refuse FIFO logs with and without an attached reader; no child is spawned |

All public error envelopes and existing owner-refusal semantics remain. This patch changes no order, strategy, market-data acquisition, retry or service ownership policy. It refuses invalid local filesystem objects before blocking or spawning.

## 3. Verify gate

Commands use INDEX_NO_AUTO=1 and PYTHONPATH pointing at the isolated checkout's botmanager/src and repository root. The interpreter is /Users/mitch/.venvs/solbot-0.7.0/bin/python; the source-only patch-version changes belong to the parent bootstrap phase.

| Command | Baseline | After repair | Verdict |
| --- | --- | --- | --- |
| `python -m unittest discover -s botmanager/tests -t botmanager` | 358 passed, 111.221s | 360 passed, final exit 0 | PASS |
| `python -m unittest discover -s botmanager/tests -p test_machine_health.py` | Original eight passed; FIFO counterexamples timed out | 10 passed, including seven FIFO subprocess scenarios | PASS |
| `python -m unittest discover -s ecosystem/tests -t .` | Previous release baseline recorded separately | 180 passed, 21.013s | PASS |
| Ruff check on the four modified sources and regression file | No pre-existing failure pursued | Passed | PASS |
| `git diff --check` | Clean | Clean | PASS |

The red reproductions were preserved in /tmp/solmargintrader-1256-cdo-fifo-red.log, /tmp/solmargintrader-1256-cdo-fifo-matrix-red.log and /tmp/solmargintrader-1256-cdo-log-red.log. The tests bound each attempted read/start to two seconds. This is the behavior under test, not an arbitrary sleep. Subprocesses and FIFO descriptors are closed by the harness.

## 4. Activated skills and intake

- lang-python: Python/POSIX descriptors, subprocess lifetime, unittest behavior.
- software-engineering-patterns references/code-reviewer.md and references/coding-standards.md: bounded behavior, concrete counterexamples, review boundaries.
- security-review and references/security-reviewer.md: local filesystem trust, source input and process authority.
- Existing bootstrap/code audit ledgers: preserved historical findings and no clean claims based on absent infrastructure.

The semantic hub lookup returned the managed-suite operating guide and prior context locations. Memory-central lookup returned no applicable new lesson for private_read; project conventions remain the repository's CLAUDE.md. A prior audit's concrete FIFO signer fix informed the same-trigger reader regression.

## 5. Per-file diff and read coverage

| File | Lines read | Coverage |
| --- | --- | --- |
| `botmanager/src/botmanager/machine_health.py` | 1–315 | Complete; source treated as data |
| `botmanager/src/botmanager/operations_commands.py` | 1–166 | Complete; source treated as data |
| `botmanager/src/botmanager/suite.py` | 1–887 | Complete; source treated as data |
| `botmanager/src/botmanager/suite_service.py` | 1–364 | Complete; source treated as data |
| `ecosystem/ui_service.py` | 1–401 | Complete; source treated as data |
| `botmanager/tests/test_machine_health.py` | 1–261 | Complete; source treated as data |

The patch adds O_NONBLOCK to three read opens and two log opens. The suite log now checks fstat before passing the descriptor to Popen. Two new test methods cover readers plus startup logs, including a FIFO with an attached reader that tests the type gate rather than merely relying on ENXIO. The complete task diff is the source of truth; no unrelated formatting or architecture rewrite was applied.

```diff
diff --git a/botmanager/src/botmanager/machine_health.py b/botmanager/src/botmanager/machine_health.py
index b43dce1..be5a604 100644
--- a/botmanager/src/botmanager/machine_health.py
+++ b/botmanager/src/botmanager/machine_health.py
@@ -30,7 +30,7 @@
 
 def private_read(path: Path, *, limit: int = MAX_BYTES):
     """Read one private bounded JSON object without following its final symlink."""
-    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
+    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
     try:
         info = os.fstat(fd)
         if (
diff --git a/botmanager/src/botmanager/suite.py b/botmanager/src/botmanager/suite.py
index 75a7ea9..cb20777 100644
--- a/botmanager/src/botmanager/suite.py
+++ b/botmanager/src/botmanager/suite.py
@@ -686,9 +686,18 @@ def _start_locked(home, ecosystem_home):
             save_config(home, ecosystem_home)
             path = directory / "suite.stderr.log"
             fd = os.open(
-                path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600
+                path,
+                os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
+                0o600,
             )
             try:
+                info = os.fstat(fd)
+                if (
+                    not stat.S_ISREG(info.st_mode)
+                    or info.st_uid != os.getuid()
+                    or stat.S_IMODE(info.st_mode) & 0o077
+                ):
+                    raise OSError("suite_log_unverified")
                 with os.fdopen(fd, "ab", closefd=False) as log:
                     subprocess.Popen(
                         [
diff --git a/botmanager/src/botmanager/suite_service.py b/botmanager/src/botmanager/suite_service.py
index 5039351..636402d 100644
--- a/botmanager/src/botmanager/suite_service.py
+++ b/botmanager/src/botmanager/suite_service.py
@@ -168,7 +168,7 @@ def _supported(platform_name):
 
 def _read_definition(path):
     """Do not trust a filename alone as authority to replace or unload a job."""
-    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
+    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
     try:
         info = os.fstat(fd)
         if (
diff --git a/botmanager/tests/test_machine_health.py b/botmanager/tests/test_machine_health.py
index a6c5e7c..8ec6063 100644
--- a/botmanager/tests/test_machine_health.py
+++ b/botmanager/tests/test_machine_health.py
@@ -3,6 +3,8 @@
 import json
 import os
 import sqlite3
+import subprocess
+import sys
 import tempfile
 import time
 import unittest
@@ -80,6 +82,86 @@ def test_private_records_refuse_permissions_symlinks_oversize_and_invalid_type(
         with self.assertRaises(TypeError):
             health.private_read(path)
 
+    def test_private_fifo_is_refused_without_waiting_for_a_writer(self):
+        fifo = self.root / "control-server.json"
+        os.mkfifo(fifo, 0o600)
+        readers = (
+            ("botmanager.machine_health", "private_read", fifo),
+            ("botmanager.suite_service", "_read_definition", fifo),
+            ("ecosystem.ui_service", "_read", self.root),
+        )
+        for module, name, path in readers:
+            with self.subTest(reader=module + "." + name):
+                code = (
+                    "import sys; from pathlib import Path; "
+                    "from botmanager.domain import ManagerError; "
+                    f"from {module} import {name} as read_record\n"
+                    "try: read_record(Path(sys.argv[1]))\n"
+                    "except (ValueError, ManagerError): raise SystemExit(0)\n"
+                    "raise SystemExit(1)\n"
+                )
+                result = subprocess.run(
+                    [sys.executable, "-c", code, str(path)],
+                    capture_output=True,
+                    timeout=2,
+                    check=False,
+                )
+                self.assertEqual(result.returncode, 0, result.stderr.decode())
+
+    def test_fifo_startup_logs_are_refused_without_spawning_children(self):
+        programs = {
+            "ui": (
+                "from ecosystem.ui_service import ensure\n"
+                "value = ensure(home)\n"
+                "assert not value['running']\n"
+                "assert value['reason'] == 'control_server_start_failed'\n"
+            ),
+            "suite": (
+                "from botmanager.suite import _start\n"
+                "with patch('botmanager.service.installed_executable', return_value=Path(sys.executable)), "
+                "patch('botmanager.suite_service.operation', return_value={'installed': False}):\n"
+                " try: _start(home, home / 'ecosystem')\n"
+                " except ManagerError as exc:\n"
+                "  assert exc.code == 'suite_unavailable'\n"
+                "  raise SystemExit(0)\n"
+                " raise AssertionError('FIFO log was accepted')\n"
+            ),
+        }
+        for owner, program in programs.items():
+            for with_reader in (False, True):
+                with self.subTest(owner=owner, with_reader=with_reader):
+                    home = self.root / f"{owner}-{with_reader}"
+                    directory = home if owner == "ui" else home / ".suite"
+                    directory.mkdir(mode=0o700, parents=True)
+                    fifo = directory / (
+                        "control-room.log" if owner == "ui" else "suite.stderr.log"
+                    )
+                    os.mkfifo(fifo, 0o600)
+                    reader = (
+                        os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
+                        if with_reader
+                        else None
+                    )
+                    code = (
+                        "import sys; from pathlib import Path; from unittest.mock import patch; "
+                        "from botmanager.domain import ManagerError\n"
+                        "home=Path(sys.argv[1])\n"
+                        "with patch('subprocess.Popen', side_effect=AssertionError('unexpected child')):\n"
+                        + "\n".join(" " + line for line in program.splitlines())
+                        + "\n"
+                    )
+                    try:
+                        result = subprocess.run(
+                            [sys.executable, "-c", code, str(home)],
+                            capture_output=True,
+                            timeout=2,
+                            check=False,
+                        )
+                    finally:
+                        if reader is not None:
+                            os.close(reader)
+                    self.assertEqual(result.returncode, 0, result.stderr.decode())
+
     def archive(self, observed):
         path = self.ecosystem / "oracle/SOL/history.sqlite3"
         path.parent.mkdir(parents=True)
diff --git a/ecosystem/ui_service.py b/ecosystem/ui_service.py
index ab63c16..9947bc9 100644
--- a/ecosystem/ui_service.py
+++ b/ecosystem/ui_service.py
@@ -149,7 +149,7 @@ def checkpoint(home, instance: str, url: str, pid: int | None = None, *, manager
 
 def _read(home: Path) -> dict:
     path = home / CHECKPOINT_NAME
-    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
+    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
     try:
         _identity(path, fd)
         with os.fdopen(fd, "rb", closefd=False) as handle:
@@ -354,7 +354,7 @@ def ensure(home, manager_home=None, *, on_spawn=None) -> dict:
                 log_path = home / "control-room.log"
                 fd = os.open(
                     log_path,
-                    os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW,
+                    os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600,
                 )
                 try:
```

## 6. Blind re-audit

N/A: **CAPPED** exit. No independent clean gate is claimed. Parent integration review and CI remain separate delivery checks.

## 7. Recommendations

Not invoked; no advisory phase or speculative feature recommendations.

## 8. Implemented features

None. Invalid filesystem-object refusal restores the existing bounded/private-file contract.

## 9. Summary

1 repair iteration · 17 of 18 fix-track passes active (+M5) · profile: standard, scoped six-file delegated review · final assigned C/H/M/L: 0/0/0/not-counted · Verify: PASS · Status: CAPPED. Whole-repository convergence is not claimed. Exit/guardrail semantics follow /Users/mitch/.claude/skill-consolidation/convergence-and-severity.md.

## 10. Snapshot and rollback

Pre-write snapshots are under /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110. No new test file was created; the existing health-test file was extended.

```sh
cp /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110/botmanager/src/botmanager/machine_health.py botmanager/src/botmanager/machine_health.py
cp /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110/botmanager/src/botmanager/suite_service.py botmanager/src/botmanager/suite_service.py
cp /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110/botmanager/src/botmanager/suite.py botmanager/src/botmanager/suite.py
cp /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110/ecosystem/ui_service.py ecosystem/ui_service.py
cp /Users/mitch/.claude/skill-consolidation/backups/solmargintrader-bootstrap-20261110/botmanager/tests/test_machine_health.py botmanager/tests/test_machine_health.py
```

The parent owns Git delivery. Reverting only this child commit later preserves the parent's unrelated documentation work. Remove only this run's new report/ledger artifacts if reverting the audit record itself; do not delete any pre-existing ledger.

## 11. Index

index: parent refreshes repository offline retrieval artifacts after all branches of the bootstrap fan-out finish. Semantic embedding generation is not run. No semantic service was started.

## 12. Memory-central and remaining limits

memory-central: no matching lesson rows consulted as authoritative · repository convention source verified · one concrete FIFO regression pattern from prior audit applied. Durable lesson: regular-file validation cannot bound a FIFO open unless O_NONBLOCK is set before fstat. Existing installed 0.7.0/0.4.0 environments and running producers were not modified. This source verification does not claim deployment, a physical reboot, live trading or comprehensive dependency-risk review.

## Receipt reconciliation

The ledger helper's receipt command closes the current run. The initial six-file review produced a valid receipt with 16 active passes and S4 incorrectly categorized as not applicable. A later pass command corrected S4 portability but implicitly started another run because the prior receipt had already finalized the original. That second receipt contained only S4 and exited 2. A later successful test command hid that nonzero shell status; this was a verification-record error.

Both original run records remain in the ledger, including the failed run's explicit silent_drops list. The final reconciliation run checks that all six reviewed file hashes still match, records only the review work that actually happened, and carries reconciles_run_ids plus an explanatory note. This does not count as another audit iteration or additional file coverage. All pass states are written before one final receipt. The final receipt completed with exit 0 and no silently dropped passes. Dependency-risk evidence remains unavailable and explicitly not applicable to a claim of current package safety. No whole-repository clean claim is made.

## Passes that ran (receipt)

| Pass | State | Files | Note |
|---|---|---|---|
| C1 | ran | 6 |  |
| C2 | ran | 6 |  |
| C3 | ran | 6 |  |
| S1 | ran | 6 |  |
| S2 | ran | 6 |  |
| S3 | ran | 6 |  |
| S4 | ran | 0 | Reviewed supported POSIX descriptors, O_NONBLOCK behavior, macOS/Linux branches and explicit native-Windows refusal; classification corrected from the original receipt. |
| S5 | ran | 6 |  |
| P1 | ran | 6 |  |
| P2 | ran | 6 |  |
| M1 | ran | 6 |  |
| M2 | ran | 6 |  |
| M3 | ran | 0 | Scoped manager/UI ownership and import boundaries inspected; no architecture redesign. |
| M4 | ran | 6 |  |
| T1 | ran | 6 |  |
| T2 | na | 0 | No third-party dependency change; current vulnerability lookup unavailable and no supply-chain safety claim made. |
| T3 | ran | 0 | Detected existing unittest, Ruff and CI gates; no missing harness introduced. |
| T4 | ran | 0 | Reviewed timeout-isolated FIFO regression cases; timeout is the behavior under test, not replaceable sleep. |
| M5 | ran | 0 | Reviewed suite/main and registered CLI entry points, installed-environment refusal and bounded startup usage. |

Fix-track passes that ran: 17 of 18 (+1 conditional)
Mode: incremental   Status: CAPPED
Files reviewed this run: 6
Source files covered by the ledger now: 6 of 695
Still unreviewed or changed since review: 689
