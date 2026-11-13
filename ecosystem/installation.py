"""Isolated local installation and bounded installed-runtime health checks.

The bootstrap owns its dedicated virtual environment. No shell profile, global
package environment, remote installer, recorder or wallet is modified here.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import select
import signal
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path

PROJECTS = ("backtester", "oracle", "botmanager", "soltui", "ecosystem")
MODULES = ("backtester", "oracle", "botmanager", "soltui", "ecosystem")
RECEIPT_NAME = "ecosystem-install-receipt.json"
OWNER_NAME = "ecosystem-install-owner.json"
MAX_HEALTH_BYTES = 128_000
MAX_CONSTRAINT_BYTES = 128_000

HEALTH_SCRIPT = r"""
import asyncio
import importlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys
import tempfile

expected = json.loads(sys.argv[1])
prefix = Path(sys.prefix).resolve()
if sys.version_info < (3, 13) or sys.prefix == sys.base_prefix:
    raise RuntimeError("dedicated_python_required")
packages = {}
for item in expected:
    module = importlib.import_module(item["module"])
    path = Path(inspect.getfile(module)).resolve()
    if not path.is_relative_to(prefix):
        raise RuntimeError("installed_import_required")
    version = importlib.metadata.version(item["name"])
    if version != item["version"]:
        raise RuntimeError("package_version_mismatch")
    packages[item["name"]] = {"version": version, "module_path": str(path)}
for name in ("soltui.f5_batch", "soltui.forwardtest"):
    path = Path(inspect.getfile(importlib.import_module(name))).resolve()
    if not path.is_relative_to(prefix):
        raise RuntimeError("installed_import_required")
from backtester.core.strategies import REGISTRY
from oracle.strategies import StrategySet
if len(REGISTRY) != 34 or len(StrategySet().catalog()) != 14:
    raise RuntimeError("strategy_catalog_mismatch")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def check_mcp():
    with tempfile.TemporaryDirectory(prefix="ecosystem-mcp-health-") as root:
        archive = str(Path(root) / "health.sqlite3")
        parameters = StdioServerParameters(command=sys.executable, args=["-I", "-m", "oracle.server", "--archive", archive, "--instrument", "SOL/USDC"], env={"SOLTUI_CONFIG_DIR": str(Path(root) / "soltui")})
        async with stdio_client(parameters) as (reader, writer), ClientSession(reader, writer) as client:
            initialized = await client.initialize()
            tools = await client.list_tools()
            resources = await client.list_resources()
            market = await client.call_tool("oracle_market", {})
            if len(tools.tools) != 8 or len(resources.resources) != 3 or not initialized.capabilities.resources.subscribe:
                raise RuntimeError("mcp_contract_mismatch")
            if not market.structuredContent["ok"] or market.structuredContent["data"]["status"] != "unavailable":
                raise RuntimeError("mcp_abstention_failed")
            return {"tools": len(tools.tools), "resources": len(resources.resources), "subscriptions": True, "no_data_abstention": True, "stdio_closed": True}

mcp = asyncio.run(asyncio.wait_for(check_mcp(), timeout=30))
print(json.dumps({"schema_version": 1, "status": "complete", "python_version": list(sys.version_info[:3]), "python_prefix": str(prefix), "packages": packages, "backtest_strategies": len(REGISTRY), "oracle_strategies": len(StrategySet().catalog()), "mcp": mcp}, allow_nan=False))
"""


def _failure(reason: str) -> dict:
    return {"schema_version": 1, "status": "failed", "reason": reason}


def _manifests(repo: Path) -> list[dict[str, str]]:
    result = []
    for directory, module in zip(PROJECTS, MODULES, strict=True):
        with (repo / directory / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
        name, version = project["name"], project["version"]
        if not isinstance(name, str) or not isinstance(version, str):
            raise TypeError("invalid_local_project")
        result.append({"name": name, "version": version, "module": module})
    return result


def source_fingerprint(repo: Path) -> str:
    """Hash local package code, strategy cards, and shipped web assets."""
    digest = hashlib.sha256()
    for name in PROJECTS:
        root = repo / name
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(
                part.startswith(".")
                or part in ("tests", "__pycache__", "build", "dist")
                or part.endswith(".egg-info")
                for part in relative.parts
            ):
                continue
            if path.is_symlink():
                raise ValueError("source_symlink_refused")
            if path.is_file() and path.suffix in (
                ".py",
                ".toml",
                ".md",
                ".txt",
                ".html",
                ".css",
                ".js",
                ".mjs",
                ".json",
            ):
                digest.update(f"{name}/{relative}".encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
    return digest.hexdigest()


def _environment(temp: Path | None = None) -> dict[str, str]:
    allowed = (
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "SYSTEMROOT",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_TRUSTED_HOST",
        "PIP_CERT",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
    )
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    if temp is not None:
        env["SOLTUI_CONFIG_DIR"] = str(temp / "soltui")
        env["SOLBOT_HOME"] = str(temp / "manager")
    return env


def _terminate(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def _run(
    command: list[str], *, cwd: Path, timeout: float, output: bool = False
) -> tuple[int, str]:
    """Bound the complete subprocess group and never emit installer logs."""
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=_environment(cwd),
        stdout=subprocess.PIPE if output else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if not output:
            return process.wait(timeout=timeout), ""
        assert process.stdout is not None
        deadline = time.monotonic() + timeout
        data = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            readable, _, _ = select.select(
                [process.stdout], [], [], min(0.1, remaining)
            )
            if not readable:
                continue
            chunk = os.read(
                process.stdout.fileno(), min(65536, MAX_HEALTH_BYTES + 1 - len(data))
            )
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_HEALTH_BYTES:
                _terminate(process)
                return 125, ""
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        return code, data.decode("utf-8")
    except subprocess.TimeoutExpired:
        _terminate(process)
        return 124, ""
    finally:
        if process.poll() is None:
            _terminate(process)
        if process.stdout is not None:
            process.stdout.close()


def verify_environment(python: Path, repo: Path) -> dict:
    """Prove imports and an actual MCP handshake using installed code from temp cwd."""
    try:
        python = Path(python).expanduser().absolute()
        expected = _manifests(Path(repo).expanduser().resolve())
        if not python.is_file():
            return _failure("environment_python_missing")
        with tempfile.TemporaryDirectory(prefix="ecosystem-health-") as temporary:
            code, output = _run(
                [str(python), "-I", "-c", HEALTH_SCRIPT, json.dumps(expected)],
                cwd=Path(temporary),
                timeout=60,
                output=True,
            )
        if code == 124:
            return _failure("environment_health_timeout")
        if code != 0:
            return _failure("environment_health_failed")
        result = json.loads(output)
        if (
            not isinstance(result, dict)
            or result.get("status") != "complete"
            or result.get("schema_version") != 1
            or result.get("backtest_strategies") != 34
            or result.get("oracle_strategies") != 14
        ):
            return _failure("environment_health_invalid")
        prefix = python.parent.parent.resolve()
        if result.get("python_prefix") != str(prefix):
            return _failure("environment_health_invalid")
        versions = result.get("python_version")
        if (
            not isinstance(versions, list)
            or len(versions) != 3
            or any(type(value) is not int for value in versions)
            or tuple(versions) < (3, 13, 0)
        ):
            return _failure("environment_health_invalid")
        packages = result.get("packages")
        if not isinstance(packages, dict) or set(packages) != {
            item["name"] for item in expected
        }:
            return _failure("environment_health_invalid")
        for item in expected:
            package = packages[item["name"]]
            if (
                not isinstance(package, dict)
                or package.get("version") != item["version"]
                or not isinstance(package.get("module_path"), str)
                or not Path(package["module_path"]).resolve().is_relative_to(prefix)
            ):
                return _failure("environment_health_invalid")
        mcp = result.get("mcp")
        if (
            not isinstance(mcp, dict)
            or mcp.get("tools") != 8
            or mcp.get("resources") != 3
            or any(
                mcp.get(key) is not True
                for key in ("subscriptions", "no_data_abstention", "stdio_closed")
            )
        ):
            return _failure("environment_health_invalid")
        return {
            "schema_version": 1,
            "status": "complete",
            "python": str(python),
            "python_prefix": str(prefix),
            "python_version": versions,
            "packages": packages,
            "backtest_strategies": 34,
            "oracle_strategies": 14,
            "mcp": mcp,
        }
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        UnicodeError,
        subprocess.SubprocessError,
    ):
        return _failure("environment_health_unavailable")


def _read_receipt(path: Path) -> dict:
    if path.is_symlink() or path.stat().st_size > MAX_HEALTH_BYTES:
        raise ValueError("invalid_installation_receipt")
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid_installation_receipt")
    return value


def _write_receipt(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(value, handle, allow_nan=False, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())


def _constraints_hash(path: Path) -> str:
    """Read a bounded regular file without following a replacement symlink."""
    if path.is_symlink():
        raise ValueError("constraints_symlink_refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CONSTRAINT_BYTES:
            raise ValueError("invalid_constraints_file")
        contents = handle.read(MAX_CONSTRAINT_BYTES + 1)
        if len(contents) > MAX_CONSTRAINT_BYTES:
            raise ValueError("invalid_constraints_file")
    return hashlib.sha256(contents).hexdigest()


def _constraints_unchanged(path: Path | None, expected: str | None) -> bool:
    if path is None:
        return True
    try:
        return _constraints_hash(path) == expected
    except (OSError, ValueError):
        return False


def _intent_mismatch(saved: dict, expected: dict) -> dict:
    if saved.get("constraints_sha256") != expected.get("constraints_sha256"):
        return _failure("environment_constraints_changed_use_new_venv")
    return _failure("environment_source_changed_use_new_venv")


@contextmanager
def _installation_lock(directory: Path):
    fd = os.open(directory / ".ecosystem-install.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def install_environment(repo: Path, venv_dir: Path, *, constraints_file: Path | None = None) -> dict:
    """Install local projects once; reuse only an exact verified source receipt.

    An ownership marker permits a failed first install to resume. A completed
    environment is immutable for this source identity so active workers cannot
    have their imports replaced by an implicit upgrade.

    Explicit constraints add their content hash to ownership and completion
    receipts. Reuse requires the same explicit constraint intent. Receipts never
    retain constraint contents or repository credentials from those contents.
    """
    if sys.version_info < (3, 13):
        return _failure("python_313_required")
    try:
        repo = Path(repo).expanduser().resolve()
        venv_dir = Path(venv_dir).expanduser().absolute()
        constraints = None
        constraints_sha256 = None
        if constraints_file is not None:
            try:
                constraints = Path(constraints_file).expanduser().absolute()
                constraints_sha256 = _constraints_hash(constraints)
            except (OSError, ValueError, TypeError):
                return _failure("constraints_file_unavailable")
        expected = _manifests(repo)
        fingerprint = source_fingerprint(repo)
        python = venv_dir / "bin" / "python"
        receipt_path = venv_dir / RECEIPT_NAME
        owner_path = venv_dir / OWNER_NAME
        receipt = {
            "schema_version": 1,
            "source_fingerprint": fingerprint,
            "projects": expected,
        }
        if constraints_sha256 is not None:
            receipt["constraints_sha256"] = constraints_sha256
        constraint_result = ({"constraints_sha256": constraints_sha256}
                             if constraints_sha256 is not None else {})
        if venv_dir.is_symlink():
            return _failure("environment_symlink_refused")
        if venv_dir.exists():
            if receipt_path.exists():
                saved = _read_receipt(receipt_path)
                if saved != receipt:
                    return _intent_mismatch(saved, receipt)
                health = verify_environment(python, repo)
                if health.get("status") != "complete":
                    return health
                if source_fingerprint(repo) != fingerprint:
                    return _failure("source_changed_during_install")
                if not _constraints_unchanged(constraints, constraints_sha256):
                    return _failure("constraints_changed_during_install")
                return {
                    "schema_version": 1,
                    "status": "complete",
                    "python": str(python),
                    "source_fingerprint": fingerprint,
                    "reused": True,
                    "health": health,
                    **constraint_result,
                }
            if not owner_path.exists():
                return _failure("environment_receipt_missing_use_new_venv")
            saved = _read_receipt(owner_path)
            if saved != receipt:
                return _intent_mismatch(saved, receipt)
        else:
            venv_dir.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            venv_dir.mkdir(mode=0o700)
            _write_receipt(owner_path, receipt)
        with (
            _installation_lock(venv_dir),
            tempfile.TemporaryDirectory(prefix="ecosystem-install-") as temporary,
        ):
            cwd = Path(temporary)
            if not (venv_dir / "pyvenv.cfg").is_file():
                code, _ = _run(
                    [sys.executable, "-m", "venv", str(venv_dir)], cwd=cwd, timeout=120
                )
                if code != 0:
                    return _failure("environment_creation_failed")
            if not _constraints_unchanged(constraints, constraints_sha256):
                return _failure("constraints_changed_during_install")
            code, _ = _run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    *(["--constraint", str(constraints)] if constraints is not None else []),
                    *[str(repo / name) for name in PROJECTS],
                ],
                cwd=cwd,
                timeout=600,
            )
            if code == 124:
                return _failure("package_install_timeout")
            if code != 0:
                return _failure("package_install_failed")
            health = verify_environment(python, repo)
            if health.get("status") != "complete":
                return health
            if source_fingerprint(repo) != fingerprint:
                return _failure("source_changed_during_install")
            if not _constraints_unchanged(constraints, constraints_sha256):
                return _failure("constraints_changed_during_install")
            _write_receipt(receipt_path, receipt)
        return {
            "schema_version": 1,
            "status": "complete",
            "python": str(python),
            "source_fingerprint": fingerprint,
            "reused": False,
            "health": health,
            **constraint_result,
        }
    except BlockingIOError:
        return _failure("environment_install_running")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        UnicodeError,
        subprocess.SubprocessError,
    ):
        return _failure("installation_unavailable")
