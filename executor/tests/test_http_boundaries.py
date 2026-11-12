"""Real HTTPX mock transports exercise privacy and bounded stream consumption."""

from __future__ import annotations

import gzip
import json
import logging
import zlib
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from conftest import QUOTE_SOL_USDC

from executor import http as transport_module
from executor import registry
from executor.config import Config
from executor.engine import Engine
from executor.errors import ExecutorError, HttpError, Refused
from executor.http import HttpxHttp
from executor.jupiter import Jupiter, parse_quote
from executor.tokens import USDC_MINT, WSOL_MINT

SECRET = "SYNTHETIC_HTTP_BOUNDARY_SECRET"


class TrackedStream(httpx.SyncByteStream):
    def __init__(self, chunks, before_chunk=None):
        self.chunks = chunks
        self.before_chunk = before_chunk
        self.bytes = 0
        self.pulls = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            if self.before_chunk:
                self.before_chunk()
            self.pulls += 1
            self.bytes += len(chunk)
            yield chunk

    def close(self):
        self.closed = True


def client(callback):
    transport = object.__new__(HttpxHttp)
    transport._client = httpx.Client(transport=httpx.MockTransport(callback), timeout=20, trust_env=False)
    return transport


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_actual_httpx_and_httpcore_records_omit_private_request_details(method, caplog):
    def respond(request):
        for logger_name in ("httpcore.synthetic_transport", "httpx.synthetic_transport"):
            logging.getLogger(logger_name).debug("request headers=%r body=%r", dict(request.headers), request.content)
        return httpx.Response(200, json={"ok": True})

    transport = client(respond)
    try:
        with caplog.at_level(logging.DEBUG):
            url = f"https://user:{SECRET}@rpc.invalid/{SECRET}?api_key={SECRET}"
            if method == "GET":
                assert transport.get_json(url, headers={"Authorization": SECRET}) == {"ok": True}
            else:
                assert transport.post_json(url, {"private": SECRET}, headers={"Authorization": SECRET}) == {"ok": True}
        assert SECRET not in caplog.text
        assert all(SECRET not in str(record.__dict__) for record in caplog.records)
        assert any(record.name == "httpx" for record in caplog.records)
        assert any(record.name.startswith("httpcore.") for record in caplog.records)
        with caplog.at_level(logging.INFO, logger="httpx"):
            logging.getLogger("httpx").info("unrelated-client-diagnostic")
        assert "unrelated-client-diagnostic" in caplog.text
    finally:
        transport._client.close()


@pytest.mark.parametrize("field", ["outAmount", "inAmount", "swapMode", "otherAmountThreshold", "slippageBps"])
def test_actual_quote_registry_envelope_omits_malformed_provider_value(field, monkeypatch):
    raw = {**QUOTE_SOL_USDC, "inAmount": "1000000", field: {"authorization": SECRET, "body": "raw-body-marker"}}
    transport = client(lambda request: httpx.Response(200, json=raw))
    cfg = Config()
    engine = object.__new__(Engine)
    engine.cfg = cfg
    engine.jup = Jupiter(cfg.jupiter_base_url, transport, api_key="", min_gap_s=0)
    monkeypatch.setattr(registry, "CONTEXT_FACTORY", lambda: registry.Context(cfg, engine))
    try:
        envelope = registry.dispatch("quote", {"from": "SOL", "to": "USDC", "amount": "0.001"})
        assert envelope["ok"] is False and envelope["error"]["code"] == "refused"
        encoded = registry.dumps(envelope)
        assert SECRET not in encoded and "raw-body-marker" not in encoded
    finally:
        transport._client.close()


def test_swap_simulation_refusal_does_not_echo_provider_body():
    transport = client(
        lambda request: httpx.Response(
            200,
            json={"swapTransaction": "AA==", "lastValidBlockHeight": 1, "simulationError": {"authorization": SECRET}},
        )
    )
    try:
        quote = parse_quote(QUOTE_SOL_USDC, WSOL_MINT, USDC_MINT, 10_000_000, 50)
        with pytest.raises(Refused, match="simulation failed") as error:
            Jupiter("https://provider.invalid", transport, api_key="", min_gap_s=0).build_swap(quote, "owner", 10)
        assert SECRET not in str(error.value)
    finally:
        transport._client.close()


@pytest.mark.parametrize("status", [200, 500])
@pytest.mark.parametrize("length", [None, "1", "8388622"])
@pytest.mark.parametrize("encoding", ["identity", "gzip", "deflate"])
def test_body_budget_applies_to_status_length_and_decoded_content(status, length, encoding, monkeypatch):
    monkeypatch.setattr(transport_module, "MAX_RESPONSE_BYTES", 1024, raising=False)
    payload = json.dumps({"padding": "x" * 8192}).encode()
    if encoding == "gzip":
        payload = gzip.compress(payload)
    elif encoding == "deflate":
        payload = zlib.compress(payload)
    stream = TrackedStream(payload[i : i + 128] for i in range(0, len(payload), 128))
    headers = {"Content-Encoding": encoding}
    if length is not None:
        headers["Content-Length"] = length
    transport = client(lambda request: httpx.Response(status, headers=headers, stream=stream))
    try:
        with pytest.raises(ExecutorError) as error:
            transport.get_json("https://provider.invalid/result")
        if status == 500:
            assert isinstance(error.value, HttpError) and error.value.status == 500
            assert stream.bytes == 0
        else:
            assert "too large" in str(error.value)
            if encoding == "identity":
                assert stream.bytes <= 1024 + 128
        assert stream.closed
    finally:
        transport._client.close()


@pytest.mark.parametrize("encoding", ["identity", "gzip", "deflate"])
def test_small_valid_encoded_json_is_accepted_and_closed(encoding):
    payload = b'{"ok":true}'
    if encoding == "gzip":
        payload = gzip.compress(payload)
    elif encoding == "deflate":
        payload = zlib.compress(payload)
    stream = TrackedStream([payload])
    transport = client(lambda request: httpx.Response(200, headers={"Content-Encoding": encoding}, stream=stream))
    try:
        assert transport.get_json("https://provider.invalid/result") == {"ok": True}
        assert stream.closed
    finally:
        transport._client.close()


def test_trickled_stream_hits_total_budget_without_sleep_or_retry(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(transport_module, "monotonic", lambda: clock[0], raising=False)

    def advance():
        clock[0] += 0.4

    stream = TrackedStream([b'{"ok":', *([b" "] * 10), b"true}"], before_chunk=advance)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, stream=stream)

    transport = client(respond)
    transport._timeout = 1.0
    try:
        with pytest.raises(ExecutorError, match="deadline"):
            transport.get_json("https://provider.invalid/result")
        assert len(requests) == 1 and stream.pulls <= 3
        assert stream.closed
    finally:
        transport._client.close()


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_midstream_transport_failure_closes_once_and_never_retries(method, caplog):
    def chunks():
        yield b'{"incomplete":'
        raise httpx.ReadTimeout(SECRET)

    stream = TrackedStream(chunks())
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, stream=stream)

    transport = client(respond)
    try:
        with caplog.at_level(logging.DEBUG), pytest.raises(ExecutorError) as error:
            if method == "GET":
                transport.get_json("https://provider.invalid/result")
            else:
                transport.post_json("https://provider.invalid/result", {"signed": SECRET})
        assert SECRET not in str(error.value) and SECRET not in caplog.text
        assert len(requests) == 1 and stream.closed
    finally:
        transport._client.close()


def test_unknown_content_encoding_refuses_without_consuming_body():
    stream = TrackedStream([b"private provider body"])
    transport = client(lambda request: httpx.Response(200, headers={"Content-Encoding": "unsupported"}, stream=stream))
    try:
        with pytest.raises(ExecutorError, match="unsupported remote content encoding"):
            transport.get_json("https://provider.invalid/result")
        assert stream.bytes == 0 and stream.closed
    finally:
        transport._client.close()


def test_malformed_gzip_is_fixed_error_and_closed():
    stream = TrackedStream([SECRET.encode()])
    transport = client(lambda request: httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=stream))
    try:
        with pytest.raises(ExecutorError, match="invalid compressed response") as error:
            transport.get_json("https://provider.invalid/result")
        assert SECRET not in str(error.value) and stream.closed
    finally:
        transport._client.close()


def test_transport_privacy_guard_does_not_mute_concurrent_unrelated_clients(caplog):
    def respond(request):
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(logging.getLogger("httpx").info, "concurrent-client-diagnostic").result(timeout=2)
        return httpx.Response(200, json={"ok": True})

    transport = client(respond)
    try:
        with caplog.at_level(logging.INFO):
            assert transport.get_json(f"https://provider.invalid/{SECRET}") == {"ok": True}
        assert SECRET not in caplog.text
        assert "concurrent-client-diagnostic" in caplog.text
    finally:
        transport._client.close()


@pytest.mark.parametrize("status", [200, 500])
def test_default_limit_stops_the_original_eight_megabyte_probe(status):
    stream = TrackedStream(iter([b'{"padding":"', *([b"x" * 65536] * 128), b'"}']))
    transport = client(lambda request: httpx.Response(status, stream=stream))
    try:
        with pytest.raises(ExecutorError):
            transport.get_json("https://provider.invalid/result")
        assert stream.closed
        assert stream.bytes <= transport_module.MAX_RESPONSE_BYTES + 65536
        assert stream.bytes < 8 * 1024 * 1024
        if status == 500:
            assert stream.bytes == 0
    finally:
        transport._client.close()
