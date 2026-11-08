"""The Bots tab's two pop-up windows: the coin picker and the auto-optimize window.

Presentation only, like `help_screen.py`. Neither window runs a command itself: the coin picker
returns the chosen coins to the tab, and the auto-optimize window shows what the tab's worker
reports (`bots.progress` while it runs, the `bots.optimize` result when it ends). Their buttons
close or confirm the window; no button here is an action, so none needs a registry command.
"""

from __future__ import annotations

from typing import Any, Callable, ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, SelectionList, Static


def _pct(value: Any) -> str:
    return "-" if value is None else f"{100 * float(value):+.2f}%"


def _changes_text(changes: dict[str, Any]) -> str:
    return " ".join(f"{k}={v}" for k, v in changes.items()) or "(current settings)"


class CoinPickerScreen(ModalScreen[list[str] | None]):
    """Tick the coins a backtest runs on. Returns the ticked coins, or None when cancelled."""

    DEFAULT_CSS = """
    CoinPickerScreen { align: center middle; }
    #coins-dialog { width: 60; height: 80%; border: thick $accent; background: $surface; padding: 1 2; }
    #coins-list { height: 1fr; }
    #coins-buttons { height: 3; }
    """
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "cancel", "Cancel")]

    def __init__(self, coins: list[str], selected: list[str]) -> None:
        super().__init__()
        self.coins = coins
        self.selected = set(selected)

    def compose(self) -> ComposeResult:
        with Vertical(id="coins-dialog"):
            yield Static("Coins to backtest: Space or click ticks a coin; OK runs on every ticked coin.",
                         markup=False)
            yield SelectionList[str](*[(c, c, c in self.selected) for c in self.coins], id="coins-list")
            with Horizontal(id="coins-buttons"):
                yield Button("All", id="coins-all")
                yield Button("None", id="coins-none")
                yield Button("OK", variant="primary", id="coins-ok")
                yield Button("Cancel", id="coins-cancel")

    def on_mount(self) -> None:
        tips = {"coins-all": "Tick every coin with cached data.", "coins-none": "Untick every coin.",
                "coins-ok": "Use the ticked coins for the next backtest.", "coins-cancel": "Keep the previous choice.",
                "coins-list": "Every coin with cached bars. A backtest runs once per ticked coin and lists each."}
        for wid, tip in tips.items():
            self.query_one(f"#{wid}").tooltip = tip

    @on(Button.Pressed, "#coins-all")
    def _all(self) -> None:
        self.query_one(SelectionList).select_all()

    @on(Button.Pressed, "#coins-none")
    def _none(self) -> None:
        self.query_one(SelectionList).deselect_all()

    @on(Button.Pressed, "#coins-ok")
    def _ok(self) -> None:
        chosen = list(self.query_one(SelectionList).selected)
        self.dismiss([c for c in self.coins if c in chosen])

    @on(Button.Pressed, "#coins-cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)


class OptimizeScreen(ModalScreen[None]):
    """Auto-optimize, live: the configurations under test, progress, then exactly what changed.

    `poll` returns the bot's `bots.progress` record (or None); the window polls it twice a second
    until `show_result` is called with the finished `bots.optimize` report. Closing the window
    does not stop the run; the Auto-optimize section of the tab shows the same report.
    """

    DEFAULT_CSS = """
    OptimizeScreen { align: center middle; }
    #opt-dialog { width: 95%; height: 92%; border: thick $warning; background: $surface; padding: 1 2; }
    #opt-head { height: auto; }
    #opt-progress { height: auto; color: $accent; }
    #opt-result { height: auto; padding: 1; border: round $success; display: none; }
    #opt-scroll { height: 1fr; }
    #opt-candidates { height: 14; }
    #opt-coins { height: 16; }
    #opt-buttons { height: 3; }
    """
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "close", "Close")]

    def __init__(self, label: str, poll: Callable[[], dict[str, Any] | None],
                 table_cls: type[DataTable] = DataTable) -> None:
        super().__init__()
        self.label = label
        self.poll = poll
        self.table_cls = table_cls
        self.result: dict[str, Any] | None = None
        self._shown_candidates = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="opt-dialog"):
            yield Static(Text(f"Auto-optimize: {self.label}. Starting…"), id="opt-head")
            yield Static("", id="opt-progress")
            with VerticalScroll(id="opt-scroll"):
                yield Static("", id="opt-result")
                yield Static("Configurations under test (the first row is your current settings):",
                             classes="table-title")
                yield self.table_cls(id="opt-candidates")
                yield Static("Per coin, filled in when the run ends: the windows it ran and the pick against "
                             "your current settings out of sample.", classes="table-title")
                yield self.table_cls(id="opt-coins")
            with Horizontal(id="opt-buttons"):
                yield Button("Close", variant="primary", id="opt-close")

    def _ensure_columns(self) -> None:
        """Idempotent: a fast run can finish before this window has mounted."""
        cand = self.query_one("#opt-candidates", DataTable)
        if not cand.columns:
            cand.add_columns("candidate", "config change")
        coins = self.query_one("#opt-coins", DataTable)
        if not coins.columns:
            coins.add_columns("coin", "history", "windows", "current test median", "pick test median",
                              "pick wins", "pick losses")

    def on_mount(self) -> None:
        self._ensure_columns()
        self.query_one("#opt-close").tooltip = ("Close this window. A run still in progress keeps going; its "
                                                "report also appears in the tab's Auto-optimize section.")
        self.set_interval(0.5, self.refresh_progress)
        self.refresh_progress()

    def refresh_progress(self) -> None:
        if self.result is not None:
            return
        prog = self.poll() or {}
        if not prog:
            return
        cands = prog.get("candidates") or []
        self.query_one("#opt-head", Static).update(Text(
            f"Auto-optimize: {self.label}, run {prog.get('run', '?')}: testing {len(cands)} configurations on "
            "every cached coin. Older windows pick a candidate; newer windows decide whether it is adopted."))
        self.query_one("#opt-progress", Static).update(Text(
            f"{100 * float(prog.get('fraction') or 0):.0f}% · {prog.get('message', '')}"))
        if len(cands) != self._shown_candidates:
            table = self.query_one("#opt-candidates", DataTable)
            table.clear()
            for row in cands:
                table.add_row(str(row["index"]), _changes_text(row["changes"]))
            self._shown_candidates = len(cands)

    def show_result(self, r: dict[str, Any] | None, error: str = "") -> None:
        """The popup part: what was decided, which settings changed, and whether they were saved."""
        self.result = r or {}
        self._ensure_columns()
        box = self.query_one("#opt-result", Static)
        box.display = True
        if error or not r:
            box.update(Text(f"Auto-optimize failed: {error or 'no result'}\nNo settings were changed."))
            return
        v = r["verdict"]
        if isinstance(r.get("reports"), dict):
            lines = ["Independent coin-specific results; global defaults were not changed."]
            for coin, report in r["reports"].items():
                verdict = report.get("verdict") or {}
                changes = ", ".join(f"{c['setting']} {c['before']} -> {c['after']}"
                                    for c in verdict.get("changes") or [])
                decision = "saved " + (changes or "coin settings") if verdict.get("saved") else "not saved"
                lines.append(f"  {coin}: {decision}. {verdict.get('reason', '')}")
        elif v.get("saved"):
            lines = [f"SAVED. Run {r['run']} adopted new settings for this bot ({v.get('saved_to', '')}):"]
            lines += [f"  {c['setting']}: {c['before']} -> {c['after']}" for c in v.get("changes") or []]
        else:
            lines = [f"NOT SAVED. Run {r['run']} kept your current settings unchanged."]
            if v.get("changes_not_saved"):
                lines.append("  It would have changed (adopt was off): " + ", ".join(
                    f"{c['setting']} {c['before']} -> {c['after']}" for c in v["changes_not_saved"]))
        lines.append(f"Why: {v.get('reason', '-')}")
        used, skipped = r.get("coins_used") or [], r.get("skipped") or {}
        skipped_text = ("; ".join(f"{k} ({m})" for k, m in skipped.items()) if isinstance(skipped, dict)
                        else ", ".join(skipped))
        lines.append(f"Ran on {len(used)} coin(s): {', '.join(used) or '-'}"
                     + (f"; skipped {len(skipped)}: {skipped_text}" if skipped else ""))
        lines.append(f"{r['candidates']} configurations, {r['train_cells']} train and {r['test_cells']} test "
                     f"cells, {r['seconds']} s. Run it again to search wider.")
        box.update(Text("\n".join(lines)))
        self.query_one("#opt-head", Static).update(Text(f"Auto-optimize: {self.label}, run {r['run']}: finished."))
        self.query_one("#opt-progress", Static).update("100%")
        coins = self.query_one("#opt-coins", DataTable)
        coins.clear()
        for row in r.get("per_coin") or []:
            coins.add_row(row["coin"], row.get("data_source") or "-",
                          f"{row['train_windows']} train / {row['test_windows']} test",
                          _pct(row["current_test_median"]), _pct(row["pick_test_median"]),
                          str(row["pick_wins"]), str(row["pick_losses"]))

    @on(Button.Pressed, "#opt-close")
    def action_close(self) -> None:
        self.dismiss(None)
