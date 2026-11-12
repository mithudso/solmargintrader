"""Minimal HTTP seam so every network client can be tested with recorded fixtures and no live network."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

import httpx

from .errors import ExecutorError, HttpError

LOGGER = logging.getLogger(__name__)


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
            raise HttpError(f"HTTP {resp.status_code} from remote service", resp.status_code)
        if body is None:
            raise ExecutorError("non-JSON response from remote service")
        return body

    def _request(self, method, url, **kwargs):
        LOGGER.info(json.dumps({"event": "executor_http_request", "method": method}))
        status = None
        try:
            call = self._client.get if method == "GET" else self._client.post
            response = call(url, **kwargs)
            status = response.status_code
            result = self._json(response)
        except Exception as exc:  # Log only the class; a URL, body or exception message can contain credentials.
            LOGGER.warning(
                json.dumps(
                    {
                        "event": "executor_http_result",
                        "method": method,
                        "ok": False,
                        "status": status,
                        "error_type": type(exc).__name__,
                    }
                )
            )
            if isinstance(exc, httpx.HTTPError):
                raise ExecutorError(f"network error: {type(exc).__name__}") from None
            raise
        LOGGER.info(json.dumps({"event": "executor_http_result", "method": method, "ok": True, "status": status}))
        return result

    def get_json(self, url, params=None, headers=None):
        return self._request("GET", url, params=params, headers=headers)

    def post_json(self, url, body, headers=None):
        return self._request("POST", url, json=body, headers=headers)
