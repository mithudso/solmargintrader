"""Make sure a LOCAL ollama server is reachable, starting it if it is not.

    python3 index/ollama_ensure.py            # check, start if needed, report the model
    python3 index/ollama_ensure.py --pull     # also pull the embedding model if absent

Used by `search.py` (semantic and hybrid), `build.py semantic` and `idle.py`, so the
three share one definition of "ollama is ready". Standard library only.

**Localhost only.** `AGENTS.md` and `CLAUDE.md` keep the engine off the network and this
tooling talks to the machine's own ollama and nothing else. A non-local base URL is
refused before any request is made, and a server is only ever started for a local one.

**Starting the server.** On macOS the Ollama desktop app is the supported way to run it
(it owns the menu-bar process and the model store), so `open -g -a Ollama` is tried first;
otherwise `ollama serve` is launched detached. Either way the call then polls `/api/tags`
until the server answers or `wait` seconds pass, and reports what happened instead of
raising: a search that cannot reach ollama should degrade to keyword search and say so.

**Pulling is opt-in.** The embedding model is ~670 MB. It is never downloaded as a side
effect of a search; `--pull` (or `pull=True`) does it deliberately.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# This repository's semantic index defaults to Mxbai; other stores choose their
# own model (the hub file corpus uses Nomic). Ollama treats `mxbai-embed-large`
# and `mxbai-embed-large:latest` as the same model; the tag makes the manifest clear.
EMBED_MODEL = "mxbai-embed-large:latest"
OLLAMA_BASE = "http://localhost:11434"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
MAC_APP = Path("/Applications/Ollama.app")


@dataclass
class Status:
    """What `ensure` found and did."""

    ok: bool                 # reachable AND the model is present
    reachable: bool
    started: bool            # we launched the server during this call
    model_present: bool | None  # None when the server was unreachable
    message: str


def base_of(endpoint: str) -> str:
    """`http://localhost:11434/api/embed` -> `http://localhost:11434`."""
    p = urllib.parse.urlparse(endpoint)
    return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else OLLAMA_BASE


def is_local(base: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(base)
        return parsed.scheme in {"http", "https"} and parsed.hostname in LOCAL_HOSTS
    except ValueError:
        return False


def _get_json(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 - local only, checked by caller
        return json.loads(r.read())


def installed_models(base: str = OLLAMA_BASE, timeout: float = 3.0) -> list[str] | None:
    """Model names the server has, or None when it is unreachable."""
    if not is_local(base):
        return None
    try:
        data = _get_json(f"{base}/api/tags", timeout)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    models = data.get("models", [])
    if not isinstance(models, list) or any(not isinstance(m, dict) or not isinstance(m.get("name"), str) for m in models):
        return None
    return [m["name"] for m in models]


def reachable(base: str = OLLAMA_BASE, timeout: float = 3.0) -> bool:
    return installed_models(base, timeout) is not None


def model_matches(installed: list[str], model: str) -> bool:
    """`name` and `name:latest` are the same model to ollama."""
    want = model if ":" in model else f"{model}:latest"
    return any((n if ":" in n else f"{n}:latest") == want for n in installed)


def start_server(popen: Callable[..., object] = subprocess.Popen) -> str:
    """Launch a local server detached; returns how, or '' when nothing could be launched."""
    if sys.platform == "darwin" and MAC_APP.exists():
        popen(["open", "-g", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "the Ollama app"
    binary = shutil.which("ollama")
    if binary:
        popen([binary, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              stdin=subprocess.DEVNULL, start_new_session=True)
        return "`ollama serve`"
    return ""


def pull_model(model: str, base: str = OLLAMA_BASE, timeout: float = 3600.0) -> bool:
    if not is_local(base):
        return False
    body = json.dumps({"model": model, "stream": False}).encode()
    req = urllib.request.Request(f"{base}/api/pull", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - local only
            result = json.loads(r.read())
            return isinstance(result, dict) and result.get("status") == "success"
    except (urllib.error.URLError, OSError, ValueError):
        return False


def ensure(model: str = EMBED_MODEL, base: str = OLLAMA_BASE, *, start: bool = True,
           wait: float = 45.0, pull: bool = False,
           sleep: Callable[[float], None] = time.sleep,
           popen: Callable[..., object] = subprocess.Popen) -> Status:
    """Reach ollama (starting it if allowed) and check the model is installed."""
    if not is_local(base):
        return Status(False, False, False, None,
                      "refusing endpoint: this tooling requires a local HTTP(S) ollama")
    started = False
    names = installed_models(base)
    if names is None and start:
        try:
            how = start_server(popen)
        except OSError:
            return Status(False, False, False, None, "ollama is unavailable; the local server could not be launched")
        if not how:
            return Status(False, False, False, None,
                          "ollama is not running and no Ollama app or `ollama` binary was found")
        started = True
        deadline = time.monotonic() + wait
        while names is None and time.monotonic() < deadline:
            sleep(1.0)
            names = installed_models(base)
        if names is None:
            return Status(False, False, True, None,
                          f"started {how} but it did not answer within {wait:.0f}s")
    if names is None:
        return Status(False, False, False, None, f"ollama is not reachable at {base}")
    present = model_matches(names, model)
    if not present and pull:
        present = pull_model(model, base) and model_matches(installed_models(base) or [], model)
    if not present:
        return Status(False, True, started, False,
                      f"ollama is up but `{model}` is not installed: ollama pull {model}")
    return Status(True, True, started, True,
                  ("started ollama; " if started else "") + f"`{model}` ready")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=EMBED_MODEL)
    ap.add_argument("--base", default=OLLAMA_BASE)
    ap.add_argument("--no-start", action="store_true", help="check only; never launch a server")
    ap.add_argument("--pull", action="store_true", help="download the model if it is missing")
    args = ap.parse_args(argv)
    status = ensure(args.model, args.base, start=not args.no_start, pull=args.pull)
    print(("ok: " if status.ok else "not ready: ") + status.message)
    return 0 if status.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
