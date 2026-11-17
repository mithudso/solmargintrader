"""Optional, bounded advisory input; it never controls orders or risk limits."""

from __future__ import annotations

import json
import math
import os
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect refused")


class Advice:
    def __init__(self, *, enabled=False, max_calls=2, opener=None, environ=None):
        if (
            type(enabled) is not bool
            or type(max_calls) is not int
            or not 0 <= max_calls <= 2
        ):
            raise ValueError("Invalid advice budget")
        self.enabled = enabled
        self.remaining = max_calls
        self.opener = opener
        self.environ = environ

    def ask(self, facts):
        unavailable = {"status": "unavailable", "direction": None}
        if not self.enabled or not self.remaining:
            return unavailable
        if not isinstance(facts, dict) or set(facts) != {"price", "momentum"}:
            return unavailable
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v)
                for v in facts.values()
            )
            or facts["price"] <= 0
            or abs(facts["momentum"]) > 1
        ):
            return unavailable
        self.remaining -= 1
        key = (self.environ if self.environ is not None else os.environ).get(
            "ANTHROPIC_API_KEY"
        )
        if not isinstance(key, str) or not key or len(key) > 1024:
            return unavailable
        body = json.dumps(
            {
                "model": "claude-haiku-4-5",
                "max_tokens": 32,
                "messages": [
                    {
                        "role": "user",
                        "content": "Return only JSON with direction long, short, or neutral. Numeric source facts: "
                        + json.dumps(facts, allow_nan=False),
                    }
                ],
            }
        ).encode()
        request = Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            opener = self.opener or build_opener(_NoRedirect())
            with opener.open(request, timeout=3) as response:
                raw = response.read(8193)
            if len(raw) > 8192:
                return unavailable
            content = json.loads(raw)["content"]
            if (
                not isinstance(content, list)
                or len(content) != 1
                or content[0].get("type") != "text"
            ):
                return unavailable
            answer = json.loads(content[0]["text"])
            if (
                not isinstance(answer, dict)
                or set(answer) != {"direction"}
                or answer["direction"] not in ("long", "short", "neutral")
            ):
                return unavailable
            return {"status": "advisory", "direction": answer["direction"]}
        except Exception:  # noqa: BLE001 - never expose provider errors or response content
            return unavailable


class AsyncAdvice:
    """Never waits for an advisor on the feed or order-decision thread."""

    def __init__(self, advisor):
        import queue

        self.advisor = advisor
        self.results = queue.Queue(maxsize=2)
        self.pending = False
        self.closed = False
        self.thread = None

    def close(self):
        self.closed = True
        if self.thread is not None:
            self.thread.join(3.2)
            if self.thread.is_alive():
                raise RuntimeError("advice shutdown incomplete")

    def offer(self, facts, at):
        import threading

        if (
            self.closed
            or self.pending
            or not self.advisor.enabled
            or not self.advisor.remaining
        ):
            return
        self.pending = True

        def run():
            try:
                if self.closed:
                    return
                result = self.advisor.ask(facts)
                if not self.closed:
                    self.results.put_nowait(
                        {"result": result, "at": at, "reference_price": facts["price"]}
                    )
            finally:
                self.pending = False

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def poll(self):
        import queue

        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None
