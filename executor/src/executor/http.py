"""Minimal HTTP seam so every network client can be tested with recorded fixtures and no live network."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from .errors import ExecutorError, HttpError


class Http(Protocol):
    def get_json(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any: ...

    def post_json(self, url: str, body: Any, headers: dict[str, str] | None = None) -> Any: ...


class HttpxHttp:
    """The live implementation. One short timeout; no automatic retries here (callers decide)."""

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(timeout=timeout, follow_redirects=False)

    def _json(self, resp: httpx.Response) -> Any:
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code >= 400:
            detail = ""
            if isinstance(body, dict):
                detail = str(body.get("error") or body.get("message") or "")[:200]
            raise HttpError(f"HTTP {resp.status_code} from {resp.request.url.host}: {detail}".strip(), resp.status_code)
        if body is None:
            raise ExecutorError(f"non-JSON response from {resp.request.url.host}")
        return body

    def get_json(self, url, params=None, headers=None):
        try:
            return self._json(self._client.get(url, params=params, headers=headers))
        except httpx.HTTPError as exc:
            raise ExecutorError(f"network error: {type(exc).__name__}") from None

    def post_json(self, url, body, headers=None):
        try:
            return self._json(self._client.post(url, json=body, headers=headers))
        except httpx.HTTPError as exc:
            raise ExecutorError(f"network error: {type(exc).__name__}") from None
