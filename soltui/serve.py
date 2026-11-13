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

## Safety

Binds **127.0.0.1** only and accepts browser WebSockets only from that exact local
origin. The console includes separately armed manual Coinbase controls. Browser
framing is disabled, and a wider bind is unavailable. Other local processes can
still reach the loopback endpoint; the console belongs on a trusted local account.
"""

from __future__ import annotations

import argparse
import inspect
import shlex
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
    return shlex.join([sys.executable, "-m", "soltui.tui"])


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
        from aiohttp import web
        from textual_serve.server import Server
    except ImportError:
        interpreter = shlex.quote(str(REPO / ".venv" / "bin" / "python"))
        print(
            "textual-serve is not installed, so the browser window is unavailable.\n"
            f"  uv venv {shlex.quote(str(REPO / '.venv'))}\n"
            f"  uv pip install --python {interpreter} "
            f"-r {shlex.quote(str(REPO / 'soltui' / 'requirements.txt'))}\n"
            "Alternatively run the console in a terminal:\n"
            f"  {shlex.quote(sys.executable)} -m soltui.tui",
            file=sys.stderr,
        )
        return 2

    # This factory is the integration boundary where the guard must be installed
    # before any app process or WebSocket starts. Refuse incompatible SDKs.
    if not inspect.iscoroutinefunction(getattr(Server, "_make_app", None)):
        print("textual-serve lacks the guarded application factory; browser console unavailable.",
              file=sys.stderr)
        return 2

    if port is not None and not 1 <= port <= 65535:
        print("Port must be between 1 and 65535.", file=sys.stderr)
        return 3

    chosen = port if port is not None else find_port()
    if chosen is None:
        print(f"No free port in {DEFAULT_PORT}..{DEFAULT_PORT + 19}.", file=sys.stderr)
        return 3
    if port is not None and not port_is_free(port):
        print(f"Port {port} is already in use. Is the console already open at "
              f"{url_for(port)}?", file=sys.stderr)
        return 4

    target = url_for(chosen)
    allowed_hosts = {f"{HOST}:{chosen}"}
    allowed_origins = {target}
    if chosen == 80:
        allowed_hosts.add(HOST)
        allowed_origins.add(f"http://{HOST}")

    @web.middleware
    async def local_browser_only(request, handler):
        origin = request.headers.get("Origin")
        if (request.headers.get("Host") not in allowed_hosts
                or (origin is not None and origin not in allowed_origins)
                or (request.path == "/ws" and origin not in allowed_origins)):
            raise web.HTTPForbidden(text="Local console origin required.")
        response = await handler(request)
        response.headers["X-Frame-Options"] = "DENY"
        # An additional CSP intersects with an existing SDK policy.
        response.headers.add("Content-Security-Policy", "frame-ancestors 'none'")
        return response

    class LocalServer(Server):
        async def _make_app(self):
            application = await super()._make_app()
            application.middlewares.insert(0, local_browser_only)
            return application

    print(f"soltui console -> {target}   (Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(target)

    server = LocalServer(app_command(), host=HOST, port=chosen, title="soltui console",
                         public_url=target)
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
