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

import subprocess
import sys
import webbrowser
from pathlib import Path

from .config import Settings, load_settings
from .roster import Roster
from .runner import SweepRunner
from .status import AppState, Phase, build_menu_summary, build_title

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "research" / "results"


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
                [{"name": n} for n in cfg.enabled_strategies]
            )
            if len(self.roster) == 0:
                self.roster = Roster.default()
            self.runner = SweepRunner(self.state)
            self.menu = [
                "Open TUI",
                "Run backtest",
                "Cancel sweep",
                None,
                "Open results folder",
                None,
                "Status",
            ]
            self.timer = rumps.Timer(self.tick, cfg.poll_interval_seconds)
            self.timer.start()

        def tick(self, _sender) -> None:
            """Refresh the title and the status submenu from live state."""
            self.title = build_title(self.state)
            summary = build_menu_summary(self.state)
            item = self.menu.get("Status")
            if item is not None:
                item.title = summary[0] if summary else "Status"

        @rumps.clicked("Open TUI")
        def open_tui(self, _sender) -> None:
            """Launch the Textual console in a new Terminal window.

            The TUI needs a TTY, which a menu-bar process does not have, so it is
            opened in Terminal rather than run in-process.
            """
            script = (
                f'tell application "Terminal" to do script '
                f'"cd {REPO} && python3 -m soltui.tui"'
            )
            subprocess.run(["osascript", "-e", script], check=False)

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

        @rumps.clicked("Status")
        def show_status(self, _sender) -> None:
            """Full status detail, including the no-live-account notice."""
            rumps.alert(
                title="soltui status",
                message="\n".join(build_menu_summary(self.state)),
            )

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
