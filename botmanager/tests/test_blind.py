from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

from botmanager import blind


def packet():
    return {
        "version": 2,
        "policy": {
            "minimum_trades": 30,
            "maximum_drawdown": 0.2,
            "drawdown_weight": 0.5,
        },
        "candidates": [
            {
                "id": c * 32,
                "cells": [
                    {
                        "block": i,
                        "net_return": ret,
                        "drawdown": 0.01,
                        "turnover": 1.0,
                        "trades": 3,
                        "uncertainty": 0.01,
                        "coverage": True,
                        "certified": True,
                        "cost_stress": True,
                    }
                    for i in range(10)
                ],
            }
            for c, ret in [("a", 0.02), ("b", 0.03)]
        ],
    }


class BlindTests(unittest.TestCase):
    def test_unknown_metadata_at_every_level_refused(self):
        for location in ["packet", "policy", "candidate", "cell"]:
            p = packet()
            target = {
                "packet": p,
                "policy": p["policy"],
                "candidate": p["candidates"][0],
                "cell": p["candidates"][0]["cells"][0],
            }[location]
            target["strategy"] = "/private/mapping.json"
            with self.assertRaises(ValueError):
                blind.decide(p)

    def test_relabel_row_order_and_exact_tie(self):
        p = packet()
        a = blind.decide(p)
        self.assertEqual(a["tied_ids"], ["b" * 32])
        p["candidates"].reverse()
        for c in p["candidates"]:
            c["cells"].reverse()
        self.assertEqual(a["tied_ids"], blind.decide(p)["tied_ids"])
        p["candidates"][0]["id"] = "c" * 32
        self.assertEqual(blind.decide(p)["tied_ids"], ["c" * 32])
        p["candidates"][0]["cells"] = copy.deepcopy(p["candidates"][1]["cells"])
        self.assertEqual(set(blind.decide(p)["tied_ids"]), {"a" * 32, "c" * 32})
        self.assertEqual(blind.resolve_tie(blind.decide(p), "a" * 32), "a" * 32)

    def test_fabricated_or_stale_verdict_refused(self):
        p = packet()
        v = blind.decide(p)
        for field, value in [
            ("tied_ids", ["f" * 32]),
            ("packet_digest", "0" * 64),
            ("policy_digest", "0" * 64),
        ]:
            bad = {**v, field: value}
            with self.assertRaises(ValueError):
                blind.verify(p, bad)

    def test_missing_cells_costs_trades_and_drawdown(self):
        p = packet()
        p["candidates"][1]["cells"].pop()
        with self.assertRaises(ValueError):
            blind.decide(p)
        for field, value in [
            ("trades", 0),
            ("drawdown", 0.21),
            ("certified", False),
            ("cost_stress", False),
        ]:
            p = packet()
            for c in p["candidates"]:
                for cell in c["cells"]:
                    cell[field] = value
            self.assertEqual(blind.decide(p)["tied_ids"], [])

    def test_actual_isolation_denies_private_repo_network_and_process(self):
        with tempfile.TemporaryDirectory() as d:
            secret = Path(d) / "mapping.json"
            secret.write_text("private parameters")
            proof = blind.probe_isolation([secret, Path(__file__).resolve()])
            if sys.platform == "darwin":
                self.assertTrue(proof["available"], proof)
            if proof["available"]:
                self.assertEqual(proof["reads_denied"], [True, True])
                self.assertEqual(proof["metadata_denied"], [True, True])
                self.assertTrue(proof["network_denied"])
                self.assertTrue(proof["process_denied"])
                self.assertTrue(proof["fork_denied"])
                self.assertTrue(proof["exec_denied"])
                self.assertEqual(blind.run_judge(packet())["tied_ids"], ["b" * 32])
            else:
                with self.assertRaisesRegex(ValueError, "isolation_unavailable"):
                    blind.run_judge(packet())

    def test_unsupported_host_never_starts_unrestricted_judge(self):
        from unittest.mock import patch

        with (
            patch.object(blind.sys, "platform", "unsupported"),
            patch.object(blind, "bounded_process") as process,
        ):
            self.assertFalse(blind.probe_isolation([])["available"])
            with self.assertRaisesRegex(ValueError, "isolation_unavailable"):
                blind.run_judge(packet())
            process.assert_not_called()

    def test_process_output_and_deadline_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "output limit"):
                blind.bounded_process(
                    [sys.executable, "-I", "-S", "-c", 'print("x"*10000)'],
                    b"",
                    cwd=d,
                    env={},
                    limit=100,
                )
            with self.assertRaisesRegex(ValueError, "deadline"):
                blind.bounded_process(
                    [sys.executable, "-I", "-S", "-c", "import time; time.sleep(5)"],
                    b"",
                    cwd=d,
                    env={},
                    timeout=0.05,
                )

    def test_closed_pipes_do_not_escape_deadline_refusal_and_child_is_reaped(self):
        import os
        from unittest.mock import patch

        children = []
        popen = blind.subprocess.Popen

        def start(*args, **kwargs):
            process = popen(*args, **kwargs)
            children.append(process)
            return process

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(blind.subprocess, "Popen", side_effect=start),
            self.assertRaisesRegex(ValueError, "^process deadline exceeded$"),
        ):
            blind.bounded_process(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-c",
                    "import os,time; os.close(1); os.close(2); time.sleep(5)",
                ],
                b"",
                cwd=directory,
                env={},
                timeout=0.1,
            )
        child = children[0]
        self.assertIsNotNone(child.poll())
        self.assertTrue(child.stdout.closed)
        self.assertTrue(child.stderr.closed)
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)

    def test_exited_child_group_signal_denial_preserves_output_refusal(self):
        import os
        from unittest.mock import patch

        children = []
        popen = blind.subprocess.Popen
        killpg = os.killpg

        def cleanup(child):
            try:
                child.kill()
            finally:
                try:
                    child.wait(timeout=1)
                finally:
                    child.stdout.close()
                    child.stderr.close()

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            self.addCleanup(cleanup, child)
            return child

        def signal_group(pid, sig):
            if group_signal.call_count == 1:
                # Force the hosted-macOS exit race: no live child remains to
                # signal, but killpg reports EPERM rather than ESRCH.
                children[0].wait(timeout=1)
                raise PermissionError("exited group")
            return killpg(pid, sig)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(blind.subprocess, "Popen", side_effect=start),
            patch.object(blind.os, "killpg", side_effect=signal_group) as group_signal,
            self.assertRaisesRegex(ValueError, "^process output limit exceeded$"),
        ):
            blind.bounded_process(
                # Exceed the reader's limit without filling even a minimum
                # POSIX pipe, so the child can exit before the mocked wait.
                [sys.executable, "-I", "-S", "-c", 'print("x"*200)'],
                b"",
                cwd=directory,
                env={},
                limit=100,
            )
        child = children[0]
        self.assertEqual(group_signal.call_count, 2)
        self.assertEqual(group_signal.call_args.args, (child.pid, 0))
        self.assertEqual(child.returncode, 0)
        self.assertTrue(child.stdout.closed)
        self.assertTrue(child.stderr.closed)
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)

    def test_denied_live_group_still_reaps_child_and_preserves_deadline(self):
        import os
        import signal
        from unittest.mock import patch

        children = []
        popen = blind.subprocess.Popen
        killpg = os.killpg

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            return child

        def signal_group(pid, sig):
            if group_signal.call_count == 1:
                self.assertIsNone(children[0].poll())
                raise PermissionError("group signal denied")
            return killpg(pid, sig)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(blind.subprocess, "Popen", side_effect=start),
            patch.object(blind.os, "killpg", side_effect=signal_group) as group_signal,
            self.assertRaisesRegex(ValueError, "^process deadline exceeded$"),
        ):
            blind.bounded_process(
                [sys.executable, "-I", "-S", "-c", "import time; time.sleep(10)"],
                b"",
                cwd=directory,
                env={},
                timeout=0.1,
            )
        child = children[0]
        self.assertEqual(child.returncode, -signal.SIGKILL)
        self.assertEqual(group_signal.call_args.args, (child.pid, 0))
        self.assertTrue(child.stdout.closed)
        self.assertTrue(child.stderr.closed)
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)

    def test_group_still_present_after_denied_signal_never_reports_success(self):
        import os
        import signal
        from unittest.mock import patch

        children = []
        popen = blind.subprocess.Popen

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            return child

        for probe_error in (None, PermissionError("group probe denied")):
            with (
                self.subTest(probe_error=probe_error),
                tempfile.TemporaryDirectory() as directory,
                patch.object(blind.subprocess, "Popen", side_effect=start),
                patch.object(
                    blind.os,
                    "killpg",
                    side_effect=[PermissionError("group signal denied"), probe_error],
                ) as group_signal,
                self.assertRaises(PermissionError),
            ):
                blind.bounded_process(
                    [sys.executable, "-I", "-S", "-c", "print('done')"],
                    b"",
                    cwd=directory,
                    env={},
                )
            child = children[-1]
            self.assertEqual(
                group_signal.call_args_list[0].args, (child.pid, signal.SIGKILL)
            )
            self.assertEqual(group_signal.call_args.args, (child.pid, 0))
            self.assertEqual(child.returncode, 0)
            self.assertTrue(child.stdout.closed)
            self.assertTrue(child.stderr.closed)
            with self.assertRaises(ChildProcessError):
                os.waitpid(child.pid, os.WNOHANG)

    def test_denied_descendant_group_is_refused_and_fixture_cleans_it_up(self):
        import os
        import signal
        import time
        from unittest.mock import patch

        children = []
        popen = blind.subprocess.Popen
        killpg = os.killpg

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            return child

        def signal_group(pid, sig):
            if group_signal.call_count == 1:
                raise PermissionError("group signal denied")
            return killpg(pid, sig)

        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / "heartbeat"
            child_code = f"import time,pathlib\np=pathlib.Path({str(heartbeat)!r})\nwhile True:\n p.write_text(str(time.monotonic_ns()))\n time.sleep(0.01)"
            parent_code = f'import subprocess,sys\nsubprocess.Popen([sys.executable,"-I","-S","-c",{child_code!r}])'
            try:
                with (
                    patch.object(blind.subprocess, "Popen", side_effect=start),
                    patch.object(
                        blind.os, "killpg", side_effect=signal_group
                    ) as group_signal,
                    self.assertRaisesRegex(PermissionError, "group signal denied"),
                ):
                    blind.bounded_process(
                        [sys.executable, "-I", "-S", "-c", parent_code],
                        b"",
                        cwd=directory,
                        env={},
                        timeout=0.3,
                    )
                child = children[0]
                self.assertEqual(child.returncode, 0)
                self.assertTrue(child.stdout.closed)
                self.assertTrue(child.stderr.closed)
                self.assertEqual(group_signal.call_count, 2)
                self.assertEqual(group_signal.call_args.args, (child.pid, 0))
                self.assertTrue(heartbeat.is_file())
                with self.assertRaises(ChildProcessError):
                    os.waitpid(child.pid, os.WNOHANG)
            finally:
                for child in children:
                    try:
                        killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            time.sleep(0.05)
            stopped_at = heartbeat.read_text()
            time.sleep(0.08)
            self.assertEqual(heartbeat.read_text(), stopped_at)

    def test_exited_parent_does_not_leave_its_descendant_running_after_timeout(self):
        import os
        import signal
        import time
        from unittest.mock import patch

        started = []
        popen = blind.subprocess.Popen

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            started.append(child)
            return child

        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / "heartbeat"
            child_code = f"import time,pathlib\np=pathlib.Path({str(heartbeat)!r})\nwhile True:\n p.write_text(str(time.monotonic_ns()))\n time.sleep(0.01)"
            parent_code = f'import subprocess,sys\nsubprocess.Popen([sys.executable,"-I","-S","-c",{child_code!r}])'
            try:
                with (
                    patch.object(blind.subprocess, "Popen", side_effect=start),
                    self.assertRaisesRegex(ValueError, "deadline"),
                ):
                    blind.bounded_process(
                        [sys.executable, "-I", "-S", "-c", parent_code],
                        b"",
                        cwd=directory,
                        env={},
                        timeout=0.3,
                    )
                self.assertEqual(
                    started[0].returncode,
                    0,
                    "direct child finished while its descendant held the pipes",
                )
                self.assertTrue(heartbeat.is_file())
                time.sleep(0.05)
                stopped_at = heartbeat.read_text()
                time.sleep(0.08)
                self.assertEqual(
                    heartbeat.read_text(),
                    stopped_at,
                    "descendant must stop even when its parent already exited",
                )
            finally:
                for child in started:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
