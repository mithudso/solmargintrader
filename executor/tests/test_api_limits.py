"""Loopback-only disposable HTTP fixtures: no registry side effects or owner token."""

import contextlib
import http.client
import json
import socket
import threading

import pytest

from executor import api, registry

TOKEN = "synthetic-api-token"


@contextlib.contextmanager
def running_server():
    server = api.create_server(0, TOKEN)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(1)
        assert not thread.is_alive()


def raw_request(server, headers, payload=b""):
    with socket.create_connection(server.server_address, timeout=0.5) as client:
        client.settimeout(0.5)
        request = (
            f"POST /v1/status HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {TOKEN}\r\n" + headers + "\r\n"
        ).encode("ascii") + payload
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        return client.recv(4096)


@pytest.mark.parametrize(
    "headers,payload",
    [
        ("Content-Length: -1\r\n", b"{}"),
        ("Content-Length: 2\r\nContent-Length: 2\r\n", b"{}"),
        ("Transfer-Encoding: chunked\r\n", b"0\r\n\r\n"),
    ],
)
def test_invalid_framing_is_refused_before_dispatch(monkeypatch, headers, payload):
    calls = []
    monkeypatch.setattr(registry, "dispatch", lambda *a, **k: calls.append(a) or registry.ok_envelope("status", {}))
    with running_server() as server:
        response = raw_request(server, headers, payload)
    assert response.startswith(b"HTTP/1.1 400 ")
    assert calls == []


def test_oversize_body_is_refused_without_waiting_for_body(monkeypatch):
    calls = []
    monkeypatch.setattr(registry, "dispatch", lambda *a, **k: calls.append(a))
    with running_server() as server, socket.create_connection(server.server_address, timeout=0.5) as client:
        client.settimeout(0.5)
        client.sendall(
            (
                "POST /v1/status HTTP/1.1\r\nHost: localhost\r\n"
                f"Authorization: Bearer {TOKEN}\r\nContent-Length: {api.MAX_BODY_BYTES + 1}\r\n\r\n"
            ).encode()
        )
        assert client.recv(4096).startswith(b"HTTP/1.1 413 ")
    assert calls == []


def test_idle_headers_have_a_read_deadline(monkeypatch):
    monkeypatch.setattr(api, "REQUEST_TIMEOUT_S", 0.1, raising=False)
    with running_server() as server, socket.create_connection(server.server_address, timeout=0.5) as client:
        client.settimeout(0.5)
        client.sendall(b"GET /v1/health HTTP/1.1\r\nHost:")
        assert client.recv(1) == b""


def test_connection_admission_is_bounded_before_thread_creation(monkeypatch):
    monkeypatch.setattr(api, "MAX_CONNECTIONS", 2, raising=False)
    lock = threading.Lock()
    first_two = threading.Event()
    third = threading.Event()
    release = threading.Event()
    counts = {"active": 0}

    class CountingHandler:
        def __init__(self, request, address, server):
            with lock:
                counts["active"] += 1
                if counts["active"] == 2:
                    first_two.set()
                if counts["active"] > 2:
                    third.set()
            try:
                release.wait(1)
            finally:
                with lock:
                    counts["active"] -= 1

    monkeypatch.setattr(api, "make_handler", lambda token: CountingHandler)
    clients = []
    with running_server() as server:
        try:
            clients.extend(socket.create_connection(server.server_address, timeout=0.5) for _ in range(2))
            assert first_two.wait(0.5)
            clients.append(socket.create_connection(server.server_address, timeout=0.5))
            assert not third.wait(0.1)
        finally:
            release.set()
            for client in clients:
                client.close()


def test_json_surrogates_preserve_response_envelope_and_surface_parity(monkeypatch):
    result = {"note": "\ud800", "valid": "café"}
    monkeypatch.setattr(registry, "dispatch", lambda *a, **k: registry.ok_envelope("status", result))
    with running_server() as server:
        connection = http.client.HTTPConnection(*server.server_address, timeout=0.5)
        try:
            connection.request("GET", "/v1/status", headers={"Authorization": f"Bearer {TOKEN}"})
            response = connection.getresponse()
            raw = response.read()
            assert response.status == 200
        finally:
            connection.close()
    assert raw == registry.dumps(registry.ok_envelope("status", result)).encode("utf-8")
    assert json.loads(raw)["result"] == result
