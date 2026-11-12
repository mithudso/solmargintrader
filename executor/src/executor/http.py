"""Minimal HTTP seam so every network client can be tested without live network."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import httpx

from .errors import ExecutorError, HttpError

log = logging.getLogger(__name__)


class _SafeHttpxLog(logging.Filter):
    """HTTPX INFO normally includes credential-bearing URLs. Keep only typed metadata."""

    def filter(self, record):
        if record.msg == 'HTTP Request: %s %s "%s %d %s"' and isinstance(record.args, tuple) and len(record.args) == 5:
            method, url, _, status, _ = record.args
            host = url.host if isinstance(url, httpx.URL) else "redacted"
            record.msg, record.args = "HTTP Request: %s host=%s status=%s", (method, host, status)
        else:
            record.msg, record.args = "HTTPX diagnostic redacted", ()
        record.exc_info = record.exc_text = record.stack_info = None
        return True


class Http(Protocol):
    def get_json(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any: ...

    def post_json(self, url: str, body: Any, headers: dict[str, str] | None = None) -> Any: ...


class HttpxHttp:
    """One bounded timeout and one attempt. Callers decide whether a read can retry."""

    def __init__(self, timeout: float = 20.0):
        logger = logging.getLogger("httpx")
        if not any(isinstance(f, _SafeHttpxLog) for f in logger.filters):
            logger.addFilter(_SafeHttpxLog())
        self._client = httpx.Client(timeout=timeout, follow_redirects=False)

    def _json(self, resp: httpx.Response) -> Any:
        if not 200 <= resp.status_code < 300:
            raise HttpError(f"HTTP {resp.status_code} from {resp.request.url.host}", resp.status_code)
        try:
            return resp.json()
        except ValueError:
            raise ExecutorError(f"non-JSON response from {resp.request.url.host}") from None

    def _request(self, method, url, **kwargs):
        host = httpx.URL(url).host
        started = time.monotonic()
        status, outcome = None, "transport_error"
        log.info("http_request method=%s host=%s", method, host)
        try:
            resp = self._client.request(method, url, **kwargs)
            status = resp.status_code
            outcome = "http_error" if not 200 <= status < 300 else "invalid_json"
            value = self._json(resp)
            outcome = "ok"
            return value
        except httpx.HTTPError as exc:
            outcome = type(exc).__name__
            raise ExecutorError(f"network error: {outcome}") from None
        finally:
            log.info(
                "http_outcome method=%s host=%s status=%s outcome=%s seconds=%.3f",
                method,
                host,
                status,
                outcome,
                time.monotonic() - started,
            )

    def get_json(self, url, params=None, headers=None):
        return self._request("GET", url, params=params, headers=headers)

    def post_json(self, url, body, headers=None):
        return self._request("POST", url, json=body, headers=headers)
