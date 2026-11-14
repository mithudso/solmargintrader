"""Run an explicit backtester tool in its own repository-local environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import venv
from pathlib import Path

TOOLS = {name: f"backtester.core.{name}" for name in (
    "fetch", "fetch_minutes", "fetch_minutes_alt", "archive_price", "history_store", "run_archive", "kucoin_history", "funding", "universe", "ticks", "strategy_cards",
)}
TOOLS.update({"backtest": "backtester.cli", "grid": "backtester.gridcli", "pair": "backtester.paircli",
              "bot": "backtester.botcli", "volty": "backtester.voltycli"})
OWNER = "oraclebot-backtester-tools/v1"
REQUIRED_MODULES = ("numpy", "pandas")


class PrerequisiteError(RuntimeError):
    """A fixed, actionable setup failure without subprocess output or secrets."""


def _python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _repair_command(project: Path, python: Path, requirements: tuple[str, ...] | None = None) -> str:
    wanted = ["-e", str(project)] if requirements is None else list(requirements)
    return shlex.join([str(python), "-m", "pip", "install", *wanted])


def _missing_modules(python: Path, modules: tuple[str, ...] = REQUIRED_MODULES) -> list[str]:
    code = f"import importlib.util,json; print(json.dumps([m for m in {modules!r} if importlib.util.find_spec(m) is None]))"
    result = subprocess.run([str(python), "-I", "-c", code], capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise PrerequisiteError("private Python prerequisite check failed; recreate the tool environment after inspecting it")
    try:
        missing = json.loads(result.stdout)
    except ValueError as exc:
        raise PrerequisiteError("private Python prerequisite check returned invalid metadata") from exc
    if not isinstance(missing, list) or any(m not in modules for m in missing):
        raise PrerequisiteError("private Python prerequisite check returned invalid module names")
    return missing


def ensure_environment(project: Path, *, requirements: tuple[str, ...] | None = None,
                       required_modules: tuple[str, ...] = REQUIRED_MODULES,
                       owner: str = OWNER, entrypoint: Path | None = None) -> Path:
    """Provision only a marked private environment; never system Python.

    By default install this backtester project. A standalone tool can instead
    declare packages, required module names and its own stable owner string.
    Example: ``ensure_environment(tool_dir, requirements=("textual==8.2.8",),
    required_modules=("textual",), owner="oraclebot-design-prototype/v1")``.
    """
    if (requirements is not None and (not isinstance(requirements, (tuple, list)) or not requirements or any(
            not isinstance(value, str) or not value.strip() or value.startswith("-")
            or "\n" in value or "\r" in value for value in requirements))):
        raise PrerequisiteError("tool requirements must be explicit package specifications")
    if (not owner or not isinstance(owner, str) or not isinstance(required_modules, (tuple, list)) or not required_modules or any(
            not isinstance(value, str) or not value.replace("_", "").replace(".", "").isalnum()
            for value in required_modules)):
        raise PrerequisiteError("tool owner and required Python module names must be explicit")
    requirements = tuple(requirements) if requirements is not None else None
    required_modules = tuple(required_modules)
    if sys.version_info < (3, 13):
        retry = shlex.join(["python3.13", str(entrypoint or Path(__file__).resolve()), "--help"])
        raise PrerequisiteError(f"Python 3.13 or newer is required. Retry with the required interpreter: {retry}")
    project = project.resolve()
    tools = project / ".tools"
    if tools.is_symlink():
        raise PrerequisiteError("tool setup directory must not be a symlink")
    tools.mkdir(mode=0o700, exist_ok=True)
    lock = tools / "bootstrap.lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise PrerequisiteError(f"tool setup is owned or interrupted; inspect {lock} before removing it") from exc
    try:
        environment = tools / ".venv"
        marker = environment / ".oraclebot-tools.json"
        identity = {"owner": owner, "project": str(project)}
        if environment.is_symlink():
            raise PrerequisiteError("tool environment must not be a symlink")
        if marker.is_symlink():
            raise PrerequisiteError("tool ownership marker must not be a symlink")
        if environment.exists():
            try:
                saved = json.loads(marker.read_text())
            except (OSError, ValueError) as exc:
                raise PrerequisiteError("existing tool environment has no valid ownership marker; refusing to change it") from exc
            if not isinstance(saved, dict) or any(saved.get(key) != value for key, value in identity.items()):
                raise PrerequisiteError("existing tool environment belongs to another source; refusing to change it")
        else:
            environment.mkdir(mode=0o700)
            marker.write_text(json.dumps(identity))
            saved = identity
        python = _python(environment)
        if not python.is_file():
            try:
                venv.EnvBuilder(with_pip=True).create(environment)
            except (OSError, subprocess.SubprocessError) as exc:
                raise PrerequisiteError("Python venv/ensurepip is unavailable; repair this Python installation's venv support") from exc
        manifest = ((project / "pyproject.toml").read_bytes() if requirements is None else
                    json.dumps({"requirements": requirements, "modules": required_modules}, sort_keys=True).encode())
        wanted = hashlib.sha256(manifest).hexdigest()
        missing = _missing_modules(python, required_modules)
        if saved.get("project_sha256") != wanted or missing:
            uv = shutil.which("uv")
            packages = ["-e", str(project)] if requirements is None else list(requirements)
            command = ([uv, "pip", "install", "--python", str(python), *packages] if uv else
                       [str(python), "-m", "pip", "install", *packages])
            result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
            if result.returncode:
                raise PrerequisiteError(f"declared tool dependencies could not be installed into the private environment. Repair: {_repair_command(project, python, requirements)}")
            missing = _missing_modules(python, required_modules)
            if missing:
                raise PrerequisiteError(f"missing Python module(s): {', '.join(missing)}. Repair: {_repair_command(project, python, requirements)}")
            marker.write_text(json.dumps({**identity, "project_sha256": wanted}))
        return python
    finally:
        lock.rmdir()


def main(argv: list[str] | None = None) -> int:
    project = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        f"Example: python3 {project / 'run.py'} fetch --help\n"
        "The selected tool runs in .tools/.venv. Setup never changes system Python or starts services."
    ))
    parser.add_argument("tool", choices=sorted(TOOLS), nargs="?", help="explicit tool; use TOOL --help for its arguments")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.tool is None:
        parser.print_help()
        return 0
    try:
        python = ensure_environment(project)
    except (PrerequisiteError, OSError, subprocess.SubprocessError) as exc:
        message = str(exc) if isinstance(exc, PrerequisiteError) else f"private environment setup failed ({type(exc).__name__})"
        print(f"error: {message}", file=sys.stderr)
        return 3
    try:
        return subprocess.run([str(python), "-m", TOOLS[args.tool], *args.arguments], cwd=project.parent, check=False).returncode
    except OSError as exc:
        print(f"error: selected tool could not start ({type(exc).__name__})", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
