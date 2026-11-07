"""Keyboard-accessible, scrollable counterpart of the hover help."""

from __future__ import annotations

from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from .help import HEADER_GLOSSARY, SETTING_HELP, SIGNAL_HELP, TAB_HELP, TERMS


class HelpScreen(ModalScreen):
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    #help-dialog { width: 90%; max-width: 110; height: 90%; border: thick $accent;
                   background: $surface; padding: 1 2; }
    #help-heading { height: auto; margin-bottom: 1; }
    #help-search { margin-bottom: 1; }
    #help-scroll { height: 1fr; }
    #help-body { height: auto; }
    """
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "dismiss", "Close help"), ("f1", "dismiss", "Close help")
    ]

    def __init__(self, context: str = "") -> None:
        super().__init__()
        self.context = context

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("Help — hover for a definition, or search and scroll here.\n"
                         "Tab moves between search and text; Page Up/Down scroll; Esc closes.",
                         id="help-heading", markup=False)
            yield Input(placeholder="Search a term, for example Sharpe, grid, APR or fees",
                        id="help-search")
            with VerticalScroll(id="help-scroll", can_focus=True):
                yield Static("", id="help-body", markup=False)

    def on_mount(self) -> None:
        self._render_help("")
        self.query_one("#help-search", Input).focus()

    @on(Input.Changed, "#help-search")
    def _search(self, event: Input.Changed) -> None:
        self._render_help(event.value)

    def _render_help(self, query: str) -> None:
        words = query.casefold().split()
        sections = [("Current control / column", self.context)] if self.context else []
        sections += [(term, text) for term, text in TERMS.items()]
        sections += [("Table column: " + term, text) for term, text in HEADER_GLOSSARY.items()]
        sections += [("Setting: " + term.replace("_", " "), text)
                     for term, text in SETTING_HELP.items()]
        sections += [("Signal setting: " + term.replace("_", " "), text)
                     for term, text in SIGNAL_HELP.items()]
        sections += [("Tab: " + term.removeprefix("tab-").replace("liverun", "Live Run"), text)
                     for term, text in TAB_HELP.items()]
        matches = [(title, text) for title, text in sections
                   if all(word in (title + " " + text).casefold() for word in words)]
        body = "\n\n".join(f"{title}\n{text}" for title, text in matches)
        self.query_one("#help-body", Static).update(body or "No matching term. Try a shorter word.")
        self.query_one("#help-scroll", VerticalScroll).scroll_home(animate=False)
