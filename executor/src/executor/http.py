"""Bounded HTTP seam; provider data and credentials never enter diagnostics."""

from __future__ import annotations

import json
import logging
import threading
import zlib
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic
from typing import Any, Protocol

import httpx

from .errors import ExecutorError, HttpError

LOGGER = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_PRIVATE_DIAGNOSTICS = ContextVar("executor_private_http_diagnostics", default=False)
_FACTORY_LOCK = threading.Lock()


@contextmanager
def _private_diagnostics():
    """Redact dependency records before any handler sees them, only in this call.

    HTTPX has no per-client logger. Its httpcore children also log independently,
    so a parent-logger filter does not cover their records. Preserve the existing
    record factory and unrelated clients; do not change logger levels/handlers.
    """
    with _FACTORY_LOCK:
        previous = logging.getLogRecordFactory()
        if getattr(previous, "_executor_context", None) is not _PRIVATE_DIAGNOSTICS:

            def factory(*args, **kwargs):
                record = previous(*args, **kwargs)
                if _PRIVATE_DIAGNOSTICS.get() and record.name.partition(".")[0] in {"httpx", "httpcore"}:
                    record.msg = "executor HTTP dependency diagnostic (private details withheld)"
                    record.args = ()
                    record.exc_info = record.exc_text = record.stack_info = None
                return record

            factory._executor_context = _PRIVATE_DIAGNOSTICS
            logging.setLogRecordFactory(factory)
    token = _PRIVATE_DIAGNOSTICS.set(True)
    try:
        yield
    finally:
        _PRIVATE_DIAGNOSTICS.reset(token)


class Http(Protocol):
    def get_json(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any: ...

    def post_json(self, url: str, body: Any, headers: dict[str, str] | None = None) -> Any: ...


class HttpxHttp:
    """Bounded streaming; no automatic retries here, especially for submits."""

    def __init__(self, timeout: float = 20.0):
        self._timeout = timeout
        self._client = httpx.Client(
            timeout=timeout, follow_redirects=False, headers={"Accept-Encoding": "gzip, deflate"}
        )

    @staticmethod
    def _remaining(deadline):
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ExecutorError("remote response deadline exceeded")
        return remaining

    def _json(self, resp: httpx.Response, deadline: float) -> Any:
        if resp.status_code >= 400:
            # A status is enough for bounded caller retry policy; never parse its body.
            raise HttpError(f"HTTP {resp.status_code} from remote service", resp.status_code)
        length = resp.headers.get("content-length", "")
        if length.isascii() and length.isdecimal() and (len(length) > 12 or int(length) > MAX_RESPONSE_BYTES):
            raise ExecutorError("remote response is too large")
        encoding = resp.headers.get("content-encoding", "identity").strip().lower()
        if encoding in ("", "identity"):
            decoder = None
        elif encoding in ("gzip", "deflate"):
            decoder = zlib.decompressobj(31 if encoding == "gzip" else 15)
        else:
            raise ExecutorError("unsupported remote content encoding")
        # Mock/custom transports may return an already decoded, cached response.
        # The network path stays streaming; cap cached decoded bytes as well.
        if resp.is_stream_consumed:
            if len(resp.content) > MAX_RESPONSE_BYTES:
                raise ExecutorError("remote response is too large")
            chunks = (resp.content,)
            decoder = None
        else:
            chunks = resp.iter_raw()
        payload = bytearray()
        raw_bytes = 0
        for chunk in chunks:
            self._remaining(deadline)
            raw_bytes += len(chunk)
            if raw_bytes > MAX_RESPONSE_BYTES:
                raise ExecutorError("remote response is too large")
            remaining = MAX_RESPONSE_BYTES - len(payload)
            try:
                # HTTPX iter_bytes decodes before yielding, which can allocate an
                # entire compressed bomb. Bound decoding itself, not just copies.
                decoded = decoder.decompress(chunk, remaining + 1) if decoder else chunk
            except zlib.error:
                raise ExecutorError("invalid compressed response from remote service") from None
            if len(decoded) > remaining:
                raise ExecutorError("remote response is too large")
            payload.extend(decoded)
        self._remaining(deadline)
        if decoder and (not decoder.eof or decoder.unused_data):
            raise ExecutorError("invalid compressed response from remote service")
        try:
            body = json.loads(payload)
        except (ValueError, UnicodeError):
            raise ExecutorError("non-JSON response from remote service") from None
        self._remaining(deadline)
        if body is None:
            raise ExecutorError("non-JSON response from remote service")
        return body

    def _request(self, method, url, **kwargs):
        LOGGER.info(json.dumps({"event": "executor_http_request", "method": method}))
        status = None
        deadline = monotonic() + getattr(self, "_timeout", 20.0)
        try:
            with (
                _private_diagnostics(),
                self._client.stream(method, url, timeout=self._remaining(deadline), **kwargs) as response,
            ):
                status = response.status_code
                self._remaining(deadline)
                result = self._json(response, deadline)
        except Exception as exc:  # Only the class: URLs, bodies and exception messages can contain credentials.
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
