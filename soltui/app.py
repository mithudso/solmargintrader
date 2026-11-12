"""macOS menu-bar shell. Thin by design.

    python3 -m soltui.app

Mirrors `netdnsmonitor/app.py`: every decision lives in already-tested modules
(`status`, `config`, `roster`, `runner`), and this file only wires them to a
`rumps.Timer` and a status-item title. The title itself comes from
`status.build_title`, which is a pure function with its own tests -- so the
indicator's behaviour is verified without a macOS event loop.

`rumps` is imported lazily. It is macOS-only and not needed to run the TUI or the
tests, so importing this module on Linux or in CI must not fail; `main()` reports
the install command instead.

## The indicator

While a sweep runs the title shows work remaining (`⟳ SOL: backtest 340/630`),
because that is the live question. Otherwise it shows the last completed
backtest's return, always with its source spelled out (`✓ SOL: last backtest
+9.4%`). A naked percentage in a menu bar reads as a live account balance, and
there is no live account here -- see `status.py`.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from . import serve as serve_mod
from .config import Settings, load_settings
from .roster import Roster
from .runner import SweepRunner
from .status import AppState, Phase, build_menu_summary, build_title

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "research" / "results"


class _ConsoleErrors:
    """Drain the owned child's pipe continuously, retaining only a bounded tail."""

    limit = 16_384

    def __init__(self, stream):
        self.tail = b""
        self._lock = threading.Lock()
        def drain():
            try:
                while chunk := stream.read(4096):
                    with self._lock:
                        self.tail = (self.tail + chunk)[-self.limit:]
            except (OSError, ValueError):
                with self._lock:
                    if not self.tail:
                        self.tail = b"Console error stream unavailable."
            finally:
                stream.close()
        self.thread = threading.Thread(target=drain, daemon=True, name="console-stderr")
        self.thread.start()

    def message(self):
        with self._lock:
            text = self.tail.decode("utf-8", errors="replace")
        return " ".join("".join(c for c in text if c.isprintable() or c.isspace()).split())[-200:]


def _wait_for_port(port: int, timeout: float = 8.0, host: str = "127.0.0.1") -> bool:
    """Block until something accepts on `port`, or `timeout` elapses.

    The browser is opened only after this returns True. Opening it first showed a
    connection error during the second the server takes to bind, which reads as
    "the console is broken" -- the exact impression this whole change exists to
    remove.
    """
    import socket
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.2)
    return False


def _rumps():
    """Import rumps on demand, or None when unavailable.

    Kept out of module scope so `import soltui.app` works anywhere -- the TUI and
    the whole test suite import fine on a machine with no rumps installed.
    """
    try:
        import rumps  # noqa: PLC0415 - optional, macOS-only

        return rumps
    except ImportError:
        return None


def build_app(settings: Settings | None = None):
    """Construct the menu-bar app class, bound to a live rumps import.

    The class is defined inside the function because it must subclass
    `rumps.App`, which may not exist. Returning an instance keeps the import
    guard in one place.
    """
    rumps = _rumps()
    if rumps is None:
        raise RuntimeError(
            "rumps is not installed. It is macOS-only:\n"
            "    pip install -r soltui/requirements.txt"
        )

    cfg = settings or load_settings()

    class SolMenuBarApp(rumps.App):
        """Status-item shell over the sweep runner."""

        def __init__(self) -> None:
            state = AppState()
            super().__init__(name="soltui", title=build_title(state))
            self.state = state
            self.settings = cfg
            self.roster = Roster.from_list(
                cfg.roster or [{"name": n} for n in cfg.enabled_strategies]
            )
            if len(self.roster) == 0 and cfg.enabled_strategies:
                self.roster = Roster.default()
            self.runner = SweepRunner(self.state)
            # The served console, if one has been opened. Tracked so a second
            # click focuses the existing window rather than binding another port
            # and leaving orphaned servers behind.
            self.serve_proc: subprocess.Popen | None = None
            self.serve_port: int | None = None
            self.serve_errors: _ConsoleErrors | None = None
            # One-line "a balance changed" notice from the portfolio snapshots, re-read at most once a minute.
            self.portfolio_line: str | None = None
            self._portfolio_checked = 0.0
            self.menu = [
                "Open console",
                "Open console in Terminal",
                None,
                "Run backtest",
                "Cancel sweep",
                None,
                "Open results folder",
                None,
                "Status",
            ]
            self.timer = rumps.Timer(self.tick, cfg.poll_interval_seconds)
            self.timer.start()
            # Auto-open the console on launch. Without this the app is a bare
            # menu-bar icon until someone clicks "Open console" -- reads as
            # having no interface at all (see open_console's docstring).
            self.open_console(None)

        def tick(self, _sender) -> None:
            """Refresh the title and the status submenu from live state."""
            self.title = build_title(self.state)
            summary = build_menu_summary(self.state)
            self._refresh_portfolio_line()
            if self.portfolio_line:
                summary = [self.portfolio_line, *summary]
            item = self.menu.get("Status")
            if item is not None:
                item.title = summary[0] if summary else "Status"

        @rumps.clicked("Open console")
        def open_console(self, _sender) -> None:
            """Open the console as a real window, via a loopback HTTP server.

            This is the default because the Terminal route below fails *silently*
            when Terminal automation is not permitted — the default on a fresh
            macOS install. The result was a menu-bar app that appeared to have no
            interface at all, when in fact it has had five tabs all along.

            `soltui.serve` needs no TTY, which is the constraint that forced the
            Terminal detour in the first place.
            """
            if self.serve_proc is not None:
                if self.serve_proc.poll() is None and _wait_for_port(self.serve_port, timeout=1.0):
                    webbrowser.open(serve_mod.url_for(self.serve_port))
                    return
                if not self._discard_console():
                    rumps.notification("soltui", "Console is still stopping",
                                       "The previous console child has not exited; retry after it stops.")
                    return
            port = serve_mod.find_port()
            if port is None:
                rumps.notification("soltui", "Could not open the console",
                                   "No free port near 8899.")
                return
            try:
                self.serve_proc = subprocess.Popen(
                    [sys.executable, "-m", "soltui.serve",
                     "--port", str(port), "--no-open"],
                    cwd=str(REPO),
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
            except OSError as exc:
                rumps.notification("soltui", "Could not open the console", str(exc))
                return
            self.serve_port = port
            self.serve_errors = _ConsoleErrors(self.serve_proc.stderr)
            # The server needs a moment to bind. Opening the browser first would
            # show a connection error the user would read as "it is broken".
            if not _wait_for_port(port, timeout=8.0):
                errors = self.serve_errors
                self._discard_console()
                err = errors.message() if errors else ""
                rumps.notification(
                    "soltui", "Console did not start",
                    err or "Is textual-serve installed? "
                           "python3 -m pip install textual-serve")
                return
            webbrowser.open(serve_mod.url_for(port))

        def _discard_console(self) -> bool:
            """Reap only the failed child this app launched, with bounded waits."""
            child, errors = self.serve_proc, self.serve_errors
            try:
                if child is not None and child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                # Retain this ownership handle; another click must not start a
                # duplicate while an unresponsive child still holds its port.
                return False
            self.serve_proc = self.serve_port = self.serve_errors = None
            if errors:
                errors.thread.join(timeout=1)
            return True

        @rumps.clicked("Open console in Terminal")
        def open_tui(self, _sender) -> None:
            """Fallback: launch the console in a new Terminal window.

            Kept because it needs no extra dependency, but it is no longer the
            default and it no longer fails quietly: `osascript` returning non-zero
            almost always means Terminal automation was denied, which the user must
            grant in System Settings > Privacy & Security > Automation.
            """
            command = f"cd {shlex.quote(str(REPO))} && {shlex.quote(sys.executable)} -m soltui.tui"
            script = f'tell application "Terminal" to do script {json.dumps(command, ensure_ascii=False)}'
            result = subprocess.run(["osascript", "-e", script],
                                    capture_output=True, text=True, check=False)
            if result.returncode != 0:
                rumps.notification(
                    "soltui", "Could not open Terminal",
                    (result.stderr or "").strip()[:160]
                    or "Grant Terminal automation in System Settings > Privacy & "
                       "Security > Automation.")

        @rumps.clicked("Run backtest")
        def run_backtest(self, _sender) -> None:
            """Start a CPCV sweep over the saved roster."""
            if self.runner.running:
                rumps.notification("soltui", "", "A sweep is already running.")
                return
            try:
                self.runner.start(self.roster, self.settings)
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                self.state.phase = Phase.ERROR
                self.state.error = str(exc)[:60]
                rumps.notification("soltui", "Could not start sweep", str(exc))

        @rumps.clicked("Cancel sweep")
        def cancel_sweep(self, _sender) -> None:
            """Ask the worker to stop at the next configuration boundary."""
            self.runner.cancel()

        @rumps.clicked("Open results folder")
        def open_results(self, _sender) -> None:
            """Reveal the sweep output directory."""
            if RESULTS_DIR.exists():
                webbrowser.open(RESULTS_DIR.as_uri())
            else:
                rumps.notification(
                    "soltui", "", "No results yet — run a backtest first."
                )

        def _refresh_portfolio_line(self, force: bool = False) -> None:
            if not force and time.monotonic() - self._portfolio_checked < 60:
                return
            self._portfolio_checked = time.monotonic()
            try:
                # Imported here, not at the top: the registry pulls in pandas, and a bundle without it
                # must still show its menu. The notice is an extra, never a reason for the app not to start.
                from . import commands  # noqa: PLC0415

                env = commands.dispatch("portfolio.notice", {}, surface="menubar", quiet=True)
                self.portfolio_line = env["result"]["line"] if env["ok"] else None
            except Exception:  # noqa: BLE001
                self.portfolio_line = None

        @rumps.clicked("Status")
        def show_status(self, _sender) -> None:
            """Full status detail, including the no-live-account notice."""
            self._refresh_portfolio_line(force=True)
            lines = build_menu_summary(self.state)
            if self.portfolio_line:
                lines = [self.portfolio_line, *lines]
            rumps.alert(title="soltui status", message="\n".join(lines))
            # Opening the detail counts as having looked at the wallet.
            try:
                from . import commands  # noqa: PLC0415

                commands.dispatch("portfolio.notice", {"mark_seen": True}, surface="menubar", quiet=True)
            except Exception:  # noqa: BLE001
                pass
            self.portfolio_line = None

    return SolMenuBarApp()


def main(argv: list[str] | None = None) -> int:
    """Entry point. Reports the install command when rumps is missing."""
    try:
        build_app().run()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
