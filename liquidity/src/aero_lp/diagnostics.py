"""Bounded diagnostics: provider endpoints and credential-shaped material stay private."""

from __future__ import annotations

import re


def safe_text(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    text = re.sub(r"https?://[^\s\"'<>]+", "[redacted endpoint]", text)
    text = re.sub(
        r"(?i)(?:bearer\s+|(?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+", "[redacted credential]", text
    )
    text = re.sub(r"(?i)\b(?:0x)?[0-9a-f]{64}\b", "[redacted value]", text)
    return text[:240]


def safe_error(error: BaseException) -> str:
    # Upstream messages can contain arbitrary credentials without recognizable syntax.
    # The caller supplies operation context; only the exception class is public.
    if type(error).__name__ == "PendingSubmission" and str(error) in {
        "submission journal owner or version does not match",
        "submission journal is bound to a different ledger",
    }:
        return str(error)  # exact local literals; no interpolated or upstream content
    return type(error).__name__
