"""Serve the Textual console as a real window, without needing a TTY.

    python3 -m soltui.serve                 # then open the printed URL
    python3 -m soltui.serve --port 8899 --no-open

## Why this exists

The console has had five tabs, buttons and settings since it was written — but the
only way to reach them was `app.py`'s "Open TUI" menu item, which does:

    tell application "Terminal" to do script "cd <repo> && python3 -m soltui.tui"

That is a `subprocess.run(..., check=False)`, so if Terminal automation is not
permitted — the default on a fresh macOS install, and a silent denial — **nothing
happens at all**. From the menu bar the app looks like it has no interface. It was
a reachability bug, not a missing UI.

A menu-bar process has no controlling terminal, which is the constraint that forced
the Terminal detour. `textual-serve` removes it: the same `App` runs behind a local
HTTP server and renders in a browser window, so there is a real window with the
existing controls and no TTY anywhere in the path.

## What this does not change

The app. `SolTuiApp` is untouched, its pure modules are untouched, and the 95 tests
still cover the logic without driving a terminal *or* a browser. This module is a
transport.

## Safety

Binds **127.0.0.1** only. `textual-serve` runs the app as a subprocess and streams
its output to the browser, which means anything that can reach the port can drive
the console; on a shared machine a wider bind would hand over the Execute tab. That
tab is dry-run only (see `paper.py`) so the exposure is bounded, but loopback is
still the right default and there is no flag to widen it.
"""

from __future__ import annotations

import argparse
import socket
import sys
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DEFAULT_PORT = 8899
HOST = "127.0.0.1"

# The command textual-serve runs as a subprocess. Absolute interpreter and an
# explicit `-m` so it does not depend on the parent's cwd or PATH -- a menu-bar
# process inherits neither reliably.
def app_command() -> str:
    return f"{sys.executable} -m soltui.tui"


def port_is_free(port: int, host: str = HOST) -> bool:
    """True when nothing is listening on `port`.

    Checked before starting rather than after failing, because the failure mode is
    otherwise a traceback in a process the user cannot see -- the menu bar starts
    this detached.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) != 0


def find_port(preferred: int = DEFAULT_PORT, tries: int = 20) -> int | None:
    """First free port at or above `preferred`, or None if all are taken."""
    for p in range(preferred, preferred + tries):
        if port_is_free(p):
            return p
    return None


def url_for(port: int) -> str:
    return f"http://{HOST}:{port}"


def serve(port: int | None = None, open_browser: bool = True) -> int:
    """Run the console behind a loopback HTTP server. Blocks until interrupted.

    Returns a process exit code rather than raising, because the menu bar launches
    this detached and a traceback would go nowhere a user can read.
    """
    try:
        from textual_serve.server import Server
    except ImportError:
        print(
            "textual-serve is not installed, so the browser window is unavailable.\n"
            "  python3 -m pip install textual-serve\n"
            "Alternatively run the console in a terminal:\n"
            "  python3 -m soltui.tui",
            file=sys.stderr,
        )
        return 2

    chosen = port if port is not None else find_port()
    if chosen is None:
        print(f"No free port in {DEFAULT_PORT}..{DEFAULT_PORT + 19}.", file=sys.stderr)
        return 3
    if port is not None and not port_is_free(port):
        print(f"Port {port} is already in use. Is the console already open at "
              f"{url_for(port)}?", file=sys.stderr)
        return 4

    target = url_for(chosen)
    print(f"soltui console -> {target}   (Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(target)

    server = Server(app_command(), host=HOST, port=chosen, title="soltui console")
    try:
        server.serve()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=None,
                    help=f"port to bind on {HOST} (default: first free from {DEFAULT_PORT})")
    ap.add_argument("--no-open", action="store_true",
                    help="do not open a browser window")
    args = ap.parse_args(argv)
    return serve(port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
