"""Resolver boundary and OS-enforced, bounded deterministic judge process."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .blind_judge import MAX_PACKET, decide, digest


def verify(packet, verdict):
    # Recompute the deterministic result as well as integrity bindings. A digest
    # alone authenticates neither candidate membership nor selection policy.
    if verdict != decide(packet):
        raise ValueError("fabricated or stale verdict")
    return verdict


def resolve_tie(verdict, incumbent):
    tied = verdict["tied_ids"]
    if incumbent in tied:
        return incumbent
    # An anonymous tie between challengers has no evidence-based ordering.
    return tied[0] if len(tied) == 1 else None


def _runtime():
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise ValueError("isolation_unavailable: deny-default macOS sandbox required")
    base = Path(sys.base_prefix).resolve()
    executable = base / "Resources/Python.app/Contents/MacOS/Python"
    if not executable.is_file():
        executable = Path(sys.executable).resolve()
    return base, executable.resolve()


def _profile(workspace):
    base, executable = _runtime()
    runtime = [Path("/System/Library"), Path("/usr/lib"), base]
    read_rules = " ".join("(subpath " + json.dumps(str(p)) + ")" for p in runtime)
    ancestors = {p for path in [*runtime, workspace] for p in path.parents}
    metadata_rules = " ".join(
        "(literal " + json.dumps(str(p)) + ")" for p in sorted(ancestors)
    )
    # dyld/CPython aborts before stderr without access to the root directory
    # itself. literal '/' grants no descendant file or directory contents.
    profile = "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(allow file-read-metadata {metadata_rules})",
            '(allow file-read-data (literal "/"))',
            f'(allow file-read* {read_rules} (subpath {json.dumps(str(workspace))}) (literal "/dev/urandom") (literal "/dev/random") (literal "/dev/null"))',
            f"(allow file-map-executable {read_rules})",
            f"(allow process-exec (literal {json.dumps(str(executable))}))",
            "(allow sysctl-read)",
            "(allow process-info* (target self))",
        ]
    )
    return profile, executable


def bounded_process(argv, payload, *, cwd, env, timeout=15, limit=MAX_PACKET):
    """Bound both pipes while running; communicate() alone buffers unbounded output."""
    if len(payload) > limit:
        raise ValueError("process input limit exceeded")
    with tempfile.TemporaryFile() as stdin:
        stdin.write(payload)
        stdin.seek(0)
        process = subprocess.Popen(
            argv,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        streams = {process.stdout: bytearray(), process.stderr: bytearray()}
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as selector:
                for stream in streams:
                    selector.register(stream, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise ValueError("process deadline exceeded")
                    for key, _ in selector.select(
                        min(0.1, max(0, deadline - time.monotonic()))
                    ):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            streams[key.fileobj].extend(chunk)
                            if len(streams[key.fileobj]) > limit:
                                raise ValueError("process output limit exceeded")
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            return (
                process.returncode,
                bytes(streams[process.stdout]),
                bytes(streams[process.stderr]),
            )
        finally:
            if process.poll() is None:
                import signal

                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            process.stdout.close()
            process.stderr.close()


def _isolated(code, payload=b""):
    with tempfile.TemporaryDirectory(prefix="solbot-judge-") as directory:
        workspace = Path(directory).resolve()
        script = workspace / "judge.py"
        script.write_text(code)
        profile, executable = _profile(workspace)
        status, stdout, _stderr = bounded_process(
            [
                "/usr/bin/sandbox-exec",
                "-p",
                profile,
                str(executable),
                "-I",
                "-S",
                "-B",
                str(script),
            ],
            payload,
            cwd=workspace,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            timeout=10,
        )
        if status != 0:
            raise ValueError(f"isolation_unavailable: judge process exit {status}")
        return json.loads(stdout), digest(profile)


def probe_isolation(paths):
    """Run real denial probes using the same profile/runtime as the judge."""
    code = """import json, os, socket, subprocess
reads=[]
metadata=[]
for path in PATHS:
    try:
        with open(path, 'rb') as f: f.read(1)
        reads.append(False)
    except PermissionError: reads.append(True)
    try:
        os.stat(path); metadata.append(False)
    except PermissionError: metadata.append(True)
network=False
try:
    s=socket.socket(); s.connect(('127.0.0.1', 9))
except PermissionError: network=True
finally:
    try: s.close()
    except NameError: pass
process=False
try: subprocess.run(['/bin/echo', 'escape'], check=True, capture_output=True)
except PermissionError: process=True
print(json.dumps(dict(available=True, reads_denied=reads, metadata_denied=metadata, network_denied=network, process_denied=process)))
""".replace("PATHS", repr([str(Path(p).resolve()) for p in paths]))
    try:
        result, profile_digest = _isolated(code)
        return {**result, "profile_digest": profile_digest}
    except (OSError, ValueError):
        return {"available": False, "reason": "isolation_unavailable"}


def run_judge(packet):
    decide(packet)  # Fail before starting a process for malformed metadata.
    source = Path(__file__).with_name("blind_judge.py").read_text()
    verdict, _ = _isolated(source, json.dumps(packet, allow_nan=False).encode())
    return verify(packet, verdict)
