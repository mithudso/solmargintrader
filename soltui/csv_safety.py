"""Keep exported display strings literal when opened by spreadsheet software.

Call ``spreadsheet_safe_text(cell)`` before passing cells to ``csv.writer``.
Formula-like strings receive an apostrophe. Signed numeric values, including
grouped numbers, scientific notation and percentages, keep their numeric text.
This helper has no UI dependency, so headless reports can share the same policy.
"""
from __future__ import annotations

import re

_NUMBER = re.compile(r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?")


def spreadsheet_safe_text(value: object) -> str:
    """Return a literal cell without turning negative numeric results into text."""
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) and not _NUMBER.fullmatch(text.strip()):
        return "'" + text
    return text
