"""One registry, two surfaces: the CLI and the HTTP API return byte-identical envelopes, with the same access model
as extension/tools/api-server.js and the same logging."""

import http.client
import io
import json
import os
import stat
import threading
from contextlib import redirect_stdout
from email.message import Message
from unittest import mock

import pytest
from conftest import (
    delta_native,
    delta_token,
    jup_http_for,
    make_engine,
    tx_json,
)

from executor import api, cli, registry, txverify
from executor.config import VALIDATION_STRATEGY
from executor.errors import ExecutorError
from executor.tokens import USDC_MINT, WSOL_MINT

AMOUNT, FEE, OUT = 10_000_000, 10_000, 900_000


@pytest.fixture
def wired(cfg, chain, owner, ctx_factory):
    chain.mods[owner] = delta_native(-(AMOUNT + FEE))
    chain.mods[txverify.ata_address(owner, USDC_MINT)] = delta_token(OUT, USDC_MINT, owner)
    chain.tx_meta = tx_json(owner, -(AMOUNT + FEE), FEE, {USDC_MINT: (100_000_000, 100_000_000 + OUT)})
    http = jup_http_for(owner, WSOL_MINT, USDC_MINT, AMOUNT)
    http.on("li.quest", {"estimate": {}})
    engine = make_engine(cfg, chain, http)
    ctx_factory(cfg, engine)
    return engine


def run_cli(*argv) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue().rstrip("\n")


@pytest.fixture
def server(wired):
    srv = api.create_server(0, token="t0ken")
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def request(server, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    h = {"Authorization": "Bearer t0ken", **(headers or {})}
    if body is not None:
        h["Content-Type"] = "application/json"
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    return resp.status, data


# -- the registry ----------------------------------------------------------------------------------------------


def test_every_command_is_declared_the_same_way():
    names = set(registry.COMMANDS)
    assert {
        "quote",
        "swap",
        "status",
        "journal",
        "kill",
        "resume",
        "gates",
        "reconcile",
        "gates.record_research",
    } <= names
    for cmd in registry.COMMANDS.values():
        d = cmd.to_dict()
        assert set(d) == {"name", "describe", "params", "read_only", "long_running", "requires_confirm"}
        assert all(p["type"] in registry.PARAM_TYPES for p in d["params"])
    assert registry.COMMANDS["swap"].read_only is False and registry.COMMANDS["quote"].read_only is True
    assert registry.COMMANDS["resume"].requires_confirm is True
    assert registry.COMMANDS["kill"].requires_confirm is False


def test_envelope_shape_ok_and_error(wired):
    ok = registry.dispatch("gates", {"strategy": "s1"})
    assert set(ok) == {"ok", "command", "result", "error"} and ok["ok"] is True and ok["error"] is None
    bad = registry.dispatch("nope", {})
    assert bad == {
        "ok": False,
        "command": "nope",
        "result": None,
        "error": {"code": "unknown_command", "message": 'unknown command "nope"'},
    }


@pytest.mark.parametrize(
    "name,params,code",
    [
        ("quote", {"from": "SOL"}, "bad_params"),
        ("quote", {"from": "SOL", "to": "USDC", "amount": "1", "wat": 1}, "bad_params"),
        ("quote", {"from": "SOL", "to": "USDC", "amount": 1.5}, "bad_params"),
        ("quote", {"from": "SOL", "to": "BONK", "amount": "1"}, "refused"),
        ("journal", {"limit": 0}, "bad_params"),
        ("journal", {"limit": 10**1000}, "bad_params"),
        ("resume", {}, "forbidden"),
        ("resume", {"confirm": "yes"}, "bad_params"),
        ("resume", {"confirm": False}, "forbidden"),
    ],
)
def test_error_codes(wired, name, params, code):
    env = registry.dispatch(name, params)
    assert env["ok"] is False and env["error"]["code"] == code


def test_resume_removes_kill_only_with_confirm(wired):
    registry.dispatch("kill", {"reason": "test"})
    assert (wired.root / "KILL").exists()
    assert registry.dispatch("resume", {})["ok"] is False and (wired.root / "KILL").exists()
    env = registry.dispatch("resume", {"confirm": True})
    assert env["ok"] and env["result"]["was_present"] is True and not (wired.root / "KILL").exists()


def test_unexpected_exceptions_become_failed_envelopes_without_details(wired, monkeypatch):
    def boom(ctx, p):
        raise KeyError("secret-looking-detail")

    monkeypatch.setitem(registry.COMMANDS, "gates", registry.Command("gates", "x", boom, ()))
    env = registry.dispatch("gates", {})
    assert env["error"] == {"code": "failed", "message": "internal error: KeyError"}


def test_the_swap_command_defaults_to_dry_run(wired, cfg):
    cfg.validation.enabled = True
    env = registry.dispatch("swap", {"from": "SOL", "to": "USDC", "amount": "0.01", "strategy": VALIDATION_STRATEGY})
    assert env["ok"] and env["result"]["mode"] == "dry-run" and wired.rpc.sent == []


def test_status_reports_without_secrets(wired, cfg):
    env = registry.dispatch("status", {})
    assert env["ok"]
    res = env["result"]
    assert res["mode"] == "dry-run" and res["kill"] is False and res["key_file_ok"] is True
    assert res["balances"]["SOL"] == "1.000000000" and res["balances"]["USDC"] == "100.000000"
    text = json.dumps(env)
    assert cfg.key_file not in text and "key.json" not in text


def test_status_flags_a_key_file_with_loose_permissions(wired, cfg):
    os.chmod(cfg.key_file, 0o644)
    res = registry.dispatch("status", {})["result"]
    assert res["key_file_ok"] is False and "mode 600" in res["key_file_problem"]


# -- CLI <-> API parity ----------------------------------------------------------------------------------------


READ_ONLY_CALLS = [
    ("status", {}, ["status"]),
    ("gates", {"strategy": "s1"}, ["gates", "--strategy", "s1"]),
    ("journal", {"limit": 5}, ["journal", "--limit", "5"]),
    (
        "quote",
        {"from": "SOL", "to": "USDC", "amount": "0.01"},
        ["quote", "--from", "SOL", "--to", "USDC", "--amount", "0.01"],
    ),
]


@pytest.mark.parametrize("name,params,argv", READ_ONLY_CALLS)
def test_cli_and_api_return_byte_identical_envelopes(wired, server, name, params, argv):
    code, cli_out = run_cli(*argv)
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    status, api_out = request(server, "GET", f"/v1/{name}" + (f"?{qs}" if qs else ""))
    assert status == 200 and code == 0
    assert cli_out == api_out
    assert json.loads(cli_out)["ok"] is True


def test_post_and_cli_parity_for_a_state_changing_command(wired, server, cfg):
    cfg.validation.enabled = True
    params = {"from": "SOL", "to": "USDC", "amount": "0.01", "strategy": VALIDATION_STRATEGY}
    status, api_out = request(server, "POST", "/v1/swap", params)
    code, cli_out = run_cli(
        "swap", "--from", "SOL", "--to", "USDC", "--amount", "0.01", "--strategy", VALIDATION_STRATEGY
    )
    assert status == 200 and code == 0 and cli_out == api_out
    assert json.loads(cli_out)["result"]["mode"] == "dry-run"


def test_errors_are_byte_identical_too(wired, server):
    code, cli_out = run_cli("quote", "--from", "SOL", "--to", "BONK", "--amount", "1")
    status, api_out = request(server, "POST", "/v1/quote", {"from": "SOL", "to": "BONK", "amount": "1"})
    assert code == 1 and status == 422 and cli_out == api_out
    assert json.loads(cli_out)["error"]["code"] == "refused"


def test_list_is_identical_and_complete(wired, server):
    code, cli_out = run_cli("list")
    status, api_out = request(server, "GET", "/v1/commands")
    assert code == 0 and status == 200 and cli_out == api_out
    assert {c["name"] for c in json.loads(cli_out)["result"]} == set(registry.COMMANDS)


def test_cli_call_is_generic_and_resume_needs_confirm(wired):
    code, out = run_cli("call", "gates", "--json", '{"strategy":"s1"}')
    assert code == 0 and json.loads(out)["command"] == "gates"
    code, out = run_cli("resume")
    assert code == 1 and json.loads(out)["error"]["code"] == "forbidden"
    code, out = run_cli("resume", "--confirm")
    assert code == 0
    code, out = run_cli("call", "x", "--json", "{oops")
    assert code == 1 and json.loads(out)["error"]["code"] == "bad_params"


def test_cli_gates_record_research_uses_the_registry(wired):
    code, out = run_cli("gates", "record-research", "--strategy", "s1", "--result", "pass", "--source", "run-1")
    assert code == 0 and json.loads(out)["command"] == "gates.record_research"
    code, out = run_cli("gates", "status", "--strategy", "s1")
    assert json.loads(out)["result"]["research_ok"] is True


def test_cli_preserves_an_explicit_ephemeral_api_port(monkeypatch):
    main = mock.Mock(return_value=0)
    monkeypatch.setattr(api, "main", main)
    assert cli.main(["api", "--port", "0"]) == 0
    main.assert_called_once_with(["--port", "0"])


@pytest.mark.parametrize(
    "value,arguments", [("not-a-port", []), ("8789", ["--port", "-1"]), ("8789", ["--port", "65536"])]
)
def test_api_cli_invalid_port_reports_usage_before_binding(monkeypatch, capsys, value, arguments):
    monkeypatch.setenv("EXECUTOR_API_PORT", value)
    create = mock.Mock()
    monkeypatch.setattr(api, "create_server", create)
    with pytest.raises(SystemExit) as error:
        api.main(arguments)
    assert error.value.code == 2
    assert "--port" in capsys.readouterr().err
    create.assert_not_called()


def test_entrypoint_help_gives_a_safe_example(capsys):
    assert "Example:" in cli._parser().format_help()
    with pytest.raises(SystemExit) as error:
        api.main(["--help"])
    assert error.value.code == 0
    assert "Example:" in capsys.readouterr().out


# -- HTTP access model -----------------------------------------------------------------------------------------


def test_api_binds_loopback_only(server):
    assert server.server_address[0] == "127.0.0.1"


def test_health_needs_no_token(server):
    status, body = request(server, "GET", "/v1/health", headers={"Authorization": ""})
    assert status == 200 and json.loads(body)["service"] == "executor"


def test_missing_and_wrong_bearer_are_refused(server, caplog):
    with caplog.at_level("INFO", logger="executor.api"):
        for h in ({"Authorization": ""}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic t0ken"}):
            status, body = request(server, "GET", "/v1/status", headers=h)
            assert status == 401 and json.loads(body)["error"]["code"] == "forbidden"
    events = [json.loads(record.message) for record in caplog.records if record.name == "executor.api"]
    assert len(events) == 3 and all(event["status"] == 401 for event in events)
    assert all(event["event"] == "executor_api_response" for event in events)
    assert "t0ken" not in caplog.text and "wrong" not in caplog.text


@pytest.mark.parametrize("header", [{"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}])
def test_browser_originated_requests_are_refused_even_with_the_token(server, header):
    status, body = request(server, "GET", "/v1/status", headers=header)
    assert status == 403 and "browser-originated" in json.loads(body)["error"]["message"]
    status, _ = request(server, "POST", "/v1/kill", {}, headers=header)
    assert status == 403


def test_get_cannot_reach_state_changing_commands(server, wired):
    for name in ("swap", "kill", "resume", "reconcile", "gates.record_research"):
        status, _ = request(server, "GET", f"/v1/{name}")
        assert status == 405
    assert not (wired.root / "KILL").exists()


def test_unknown_route_and_methods(server):
    assert request(server, "GET", "/v1/nope")[0] == 404
    assert request(server, "GET", "/elsewhere")[0] == 404
    assert request(server, "PUT", "/v1/status")[0] == 405


def test_bad_bodies(server):
    status, body = request(server, "POST", "/v1/quote", [1, 2])
    assert status == 400
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    conn.request("POST", "/v1/quote", body="{nope", headers={"Authorization": "Bearer t0ken"})
    assert conn.getresponse().status == 400


@pytest.mark.parametrize("length", ["-1", str(api.MAX_BODY_BYTES + 1)])
def test_invalid_body_length_is_rejected_without_reading(length):
    handler = object.__new__(api.make_handler("test"))
    handler.headers = Message()
    handler.headers["Content-Length"] = length
    handler.rfile = mock.Mock()
    with pytest.raises(ExecutorError):
        handler._read_json()
    handler.rfile.read.assert_not_called()
    assert handler.close_connection is True


@pytest.mark.parametrize(
    "headers", [[("Transfer-Encoding", "chunked")], [("Content-Length", "0"), ("Content-Length", "1")]]
)
def test_ambiguous_body_framing_is_refused_before_reading(headers):
    handler = object.__new__(api.make_handler("test"))
    handler.headers = Message()
    for key, value in headers:
        handler.headers[key] = value
    handler.rfile = mock.Mock()
    with pytest.raises(ExecutorError):
        handler._read_json()
    handler.rfile.read.assert_not_called()
    assert handler.close_connection is True


def test_malformed_http_target_returns_a_bounded_error(server):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    try:
        conn.putrequest("GET", "http://[broken", skip_host=True)
        conn.putheader("Authorization", "Bearer t0ken")
        conn.endheaders()
        response = conn.getresponse()
        assert response.status == 400
        assert json.loads(response.read())["error"]["code"] == "bad_params"
    finally:
        conn.close()


def test_http_connection_has_a_read_deadline(monkeypatch):
    handler_type = api.make_handler("test")
    handler = object.__new__(handler_type)
    handler.connection = mock.Mock()
    monkeypatch.setattr(api.BaseHTTPRequestHandler, "setup", lambda self: None)
    handler.setup()
    handler.connection.settimeout.assert_called_once_with(5)


def test_no_cors_headers_are_ever_sent(server):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    conn.request("GET", "/v1/status", headers={"Authorization": "Bearer t0ken"})
    resp = conn.getresponse()
    resp.read()
    assert not [h for h, _ in resp.getheaders() if h.lower().startswith("access-control")]
    assert resp.getheader("cache-control") == "no-store"


def test_token_file_is_created_mode_600_and_reused(tmp_path):
    p = tmp_path / "t" / "api-token"
    t1 = api.load_token(p)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600 and len(t1) >= 32
    os.chmod(p, 0o644)
    assert api.load_token(p) == t1 and stat.S_IMODE(os.stat(p).st_mode) == 0o600


def test_token_comparison():
    assert api.token_matches("abc", "abc")
    assert (
        not api.token_matches("abd", "abc") and not api.token_matches("", "abc") and not api.token_matches("abc", " ")
    )


# -- logging ---------------------------------------------------------------------------------------------------


def test_one_log_line_per_call_with_keys_only(wired, server, tmp_path):
    run_cli("quote", "--from", "SOL", "--to", "USDC", "--amount", "0.0123456")
    request(server, "POST", "/v1/quote", {"from": "SOL", "to": "USDC", "amount": "0.0123456"})
    request(server, "GET", "/v1/status")
    lines = [json.loads(x) for x in (tmp_path / "logs" / "calls.jsonl").read_text().splitlines()]
    assert [(r["surface"], r["command"]) for r in lines] == [("cli", "quote"), ("api", "quote"), ("api", "status")]
    assert lines[0]["params_keys"] == ["amount", "from", "to"]
    raw = (tmp_path / "logs" / "calls.jsonl").read_text()
    assert "0.0123456" not in raw and "SOL" not in raw and "t0ken" not in raw
    assert set(lines[0]) == {"ts", "surface", "command", "ok", "error_code", "ms", "params_keys"}
    assert stat.S_IMODE(os.stat(tmp_path / "logs" / "calls.jsonl").st_mode) == 0o600


def test_failed_calls_are_logged_with_their_code(wired, tmp_path):
    registry.dispatch("resume", {}, surface="cli")
    registry.dispatch("nope", {}, surface="api")
    lines = [json.loads(x) for x in (tmp_path / "logs" / "calls.jsonl").read_text().splitlines()]
    assert [(r["command"], r["ok"], r["error_code"]) for r in lines] == [
        ("resume", False, "forbidden"),
        ("nope", False, "unknown_command"),
    ]


def test_log_rotates_at_5mb(wired, tmp_path):
    log = tmp_path / "logs" / "calls.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("x" * (registry.LOG_ROTATE_BYTES + 1))
    registry.dispatch("gates", {"strategy": "s"})
    assert (tmp_path / "logs" / "calls.jsonl.1").exists() and log.stat().st_size < 1000


def test_cross_chain_quote_through_the_registry_is_quote_only(wired):
    from conftest import fixture

    wired.http.on("li.quest", fixture("lifi_quote_usdc_base.json"))
    env = registry.dispatch("quote", {"from": "USDC", "to": "USDC", "amount": "5", "to_chain": "base"})
    assert env["ok"] and env["result"]["executable"] is False and env["result"]["mode"] == "quote-only"
