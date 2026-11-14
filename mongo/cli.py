"""CLI-only prerequisite messages; importing the research libraries stays unchanged."""
from __future__ import annotations

from pathlib import Path
import shlex
import sys
from typing import Callable


def run_cli(main: Callable[[], int], repo: Path) -> int:
    """Report known missing packages without installing anything or starting services."""
    try:
        return main()
    except ModuleNotFoundError as error:
        module = (error.name or "").split(".")[0]
        packages = {"pymongo": "pymongo", "dotenv": "python-dotenv", "numpy": "numpy", "pandas": "pandas"}
        if module not in packages:
            raise
        python = repo / ".venv" / "bin" / "python"
        print(f"error: missing Python package {packages[module]} (module {module}).", file=sys.stderr)
        if not python.is_file():
            print(shlex.join(["uv", "venv", str(repo / ".venv"), "--python", "3.13"]), file=sys.stderr)
        install = ["uv", "pip", "install", "--python", str(python),
                   "-r", str(repo / "mongo" / "requirements.txt"), "-e", str(repo / "backtester")]
        if module == "dotenv":
            install.append("python-dotenv")
        print("Install into the isolated repository environment:", file=sys.stderr)
        print(shlex.join(install), file=sys.stderr)
        return 3
    except Exception as error:
        # Driver exceptions can contain host details. Emit only a fixed message.
        if type(error).__name__ != "ServerSelectionTimeoutError" or type(error).__module__ != "pymongo.errors":
            raise
        print("error: the configured MongoDB server is unavailable.", file=sys.stderr)
        if sys.platform == "darwin":
            print("For the default local server: brew services start mongodb-community", file=sys.stderr)
        print("Verify the server selected by --uri, then retry. This command starts no services.", file=sys.stderr)
        return 3
