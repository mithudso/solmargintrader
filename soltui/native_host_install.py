"""Install, remove or inspect the native-messaging host registration.

    python -m soltui.native_host_install install [--python P] [--repo R] [--extra-id ID ...] [--dir D ...]
    python -m soltui.native_host_install uninstall
    python -m soltui.native_host_install status

`install` writes an executable wrapper (absolute paths, no arguments, which is what Chrome requires of a
manifest `path`) that runs the console venv's interpreter on `soltui.native_host` from the repo root, and
one host manifest into the NativeMessagingHosts directory of each installed Chromium browser. The
manifest's `allowed_origins` is the owner's extension plus any ids in `SOLTUI_EXTRA_EXTENSION_IDS`
(comma separated) or `--extra-id`; Chrome enforces access with that list.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .native_host import HOST_NAME

EXTENSION_ID = "pnokcppamfghgaimmmghoegjllhonhbh"
DEFAULT_PYTHON = Path.home() / ".venvs" / "soltui" / "bin" / "python"
REPO = Path(__file__).resolve().parent.parent

# Browser user-data directories under ~/Library/Application Support that take a NativeMessagingHosts dir.
BROWSERS = (
    "Google/Chrome", "Google/Chrome Beta", "Google/Chrome Canary", "Chromium",
    "Google/Chrome for Testing", "BraveSoftware/Brave-Browser", "Microsoft Edge",
)


def support_root() -> Path:
    return Path(os.environ.get("SOLTUI_APP_SUPPORT_ROOT") or Path.home() / "Library" / "Application Support")


def wrapper_path() -> Path:
    base = Path(os.environ.get("SOLTUI_SUPPORT_DIR") or support_root() / "soltui")
    return base / "native-host" / "soltui-native-host"


def browser_host_dirs(root: Path | None = None) -> list[Path]:
    """NativeMessagingHosts dirs of the browsers whose profile directory exists."""
    root = root or support_root()
    return [root / b / "NativeMessagingHosts" for b in BROWSERS if (root / b).is_dir()]


def allowed_origins(extra: list[str] | None = None) -> list[str]:
    ids = [EXTENSION_ID]
    env = [i.strip() for i in os.environ.get("SOLTUI_EXTRA_EXTENSION_IDS", "").split(",")]
    for i in env + list(extra or []):
        if i and i not in ids:
            ids.append(i)
    return [f"chrome-extension://{i}/" for i in ids]


def wrapper_text(repo: Path, python: Path) -> str:
    return f'#!/bin/sh\ncd "{repo}" || exit 1\nexec "{python}" -m soltui.native_host\n'


def manifest(wrapper: Path, extra: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": HOST_NAME,
        "description": "soltui command bridge (manual Coinbase orders require explicit confirmation)",
        "path": str(wrapper),
        "type": "stdio",
        "allowed_origins": allowed_origins(extra),
    }


def install(repo: Path = REPO, python: Path = DEFAULT_PYTHON, extra_ids: list[str] | None = None,
            dirs: list[Path] | None = None, wrapper: Path | None = None) -> dict[str, Any]:
    wrapper = wrapper or wrapper_path()
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(wrapper_text(repo.resolve(), python))
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    targets = list(dirs) if dirs else browser_host_dirs()
    written = []
    for d in targets:
        d.mkdir(parents=True, exist_ok=True)
        target = d / f"{HOST_NAME}.json"
        target.write_text(json.dumps(manifest(wrapper, extra_ids), indent=2) + "\n")
        written.append(str(target))
    return {"wrapper": str(wrapper), "manifests": written, "python": str(python),
            "allowed_origins": allowed_origins(extra_ids)}


def uninstall(dirs: list[Path] | None = None, wrapper: Path | None = None) -> dict[str, Any]:
    wrapper = wrapper or wrapper_path()
    removed = []
    for d in (list(dirs) if dirs else browser_host_dirs()):
        target = d / f"{HOST_NAME}.json"
        if target.exists():
            target.unlink()
            removed.append(str(target))
    if wrapper.exists():
        wrapper.unlink()
        removed.append(str(wrapper))
    return {"removed": removed}


def status(dirs: list[Path] | None = None, wrapper: Path | None = None) -> dict[str, Any]:
    wrapper = wrapper or wrapper_path()
    out: dict[str, Any] = {"wrapper": str(wrapper), "wrapper_exists": wrapper.exists(),
                           "wrapper_executable": os.access(wrapper, os.X_OK) if wrapper.exists() else False,
                           "wrapper_text": wrapper.read_text() if wrapper.exists() else None,
                           "manifests": []}
    for d in (list(dirs) if dirs else browser_host_dirs()):
        target = d / f"{HOST_NAME}.json"
        entry: dict[str, Any] = {"path": str(target), "exists": target.exists()}
        if target.exists():
            try:
                data = json.loads(target.read_text())
                entry["points_at_wrapper"] = data.get("path") == str(wrapper)
                entry["allowed_origins"] = data.get("allowed_origins")
            except ValueError:
                entry["error"] = "not valid JSON"
        out["manifests"].append(entry)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soltui host-install")
    parser.add_argument("verb", choices=("install", "uninstall", "status"))
    parser.add_argument("--python", default=os.environ.get("SOLTUI_PYTHON") or str(DEFAULT_PYTHON))
    parser.add_argument("--repo", default=str(REPO))
    parser.add_argument("--extra-id", action="append", default=[])
    parser.add_argument("--dir", action="append", default=[], help="extra NativeMessagingHosts dir")
    a = parser.parse_args(argv)
    dirs = None
    if a.dir:
        dirs = browser_host_dirs() + [Path(d) for d in a.dir]
    if a.verb == "install":
        result = install(Path(a.repo), Path(a.python), a.extra_id, dirs)
    elif a.verb == "uninstall":
        result = uninstall(dirs)
    else:
        result = status(dirs)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
