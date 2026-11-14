"""Exercise the real HTTP adapter with an in-memory transport, never a socket."""

import copy
import logging

import httpx
import pytest
from conftest import FakeHttp, fixture

from executor.config import Config
from executor.errors import ExecutorError, HttpError, Refused
from executor.http import HttpxHttp
from executor.lifi import quote_cross_chain
from executor.tokens import resolve

USDC = resolve("USDC")


@pytest.fixture
def transport_client():
    clients = []

    def make(handler):
        client = HttpxHttp()
        client._client.close()
        client._client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
        clients.append(client)
        return client

    yield make
    for client in clients:
        client._client.close()


@pytest.mark.parametrize("method", ["get", "post"])
def test_adapter_logs_one_safe_request_and_outcome_without_credentials(method, transport_client, caplog):
    canary = "SYNTHETIC-PRIVATE-CANARY"
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"value": 7, "private": canary})

    client = transport_client(handler)
    with caplog.at_level(logging.INFO):
        if method == "get":
            result = client.get_json(
                f"https://user:{canary}@fixture.invalid/{canary}", {"key": canary}, {"Authorization": canary}
            )
        else:
            result = client.post_json(
                f"https://fixture.invalid/?key={canary}", {"secret": canary}, {"Authorization": canary}
            )
    assert result["value"] == 7 and len(calls) == 1
    own = [r for r in caplog.records if r.name == "executor.http"]
    assert sum("http_request" in r.getMessage() for r in own) == 1
    assert sum("http_result" in r.getMessage() for r in own) == 1
    assert canary not in caplog.text
    assert all(canary not in repr(r.args) for r in caplog.records)


@pytest.mark.parametrize("status", [302, 429, 503])
def test_non_success_status_is_typed_and_does_not_expose_provider_text(status, transport_client, caplog):
    canary = "SYNTHETIC-PRIVATE-CANARY"
    client = transport_client(
        lambda request: httpx.Response(status, json={"error": canary}, headers={"Location": "https://remote.invalid"})
    )
    with caplog.at_level(logging.INFO), pytest.raises(HttpError) as error:
        client.get_json("https://fixture.invalid/")
    assert error.value.status == status
    assert canary not in str(error.value) + caplog.text


def test_invalid_json_fails_with_a_safe_outcome(transport_client, caplog):
    client = transport_client(lambda request: httpx.Response(200, content=b"PRIVATE-SYNTHETIC-CANARY"))
    with caplog.at_level(logging.INFO), pytest.raises(ExecutorError, match="non-JSON"):
        client.get_json("https://fixture.invalid/")
    assert "http_result" in caplog.text and "ExecutorError" in caplog.text
    assert "PRIVATE-SYNTHETIC-CANARY" not in caplog.text


def test_post_timeout_never_retries_or_logs_exception_text(transport_client, caplog):
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("PRIVATE-SYNTHETIC-CANARY", request=request)

    client = transport_client(timeout)
    with caplog.at_level(logging.INFO), pytest.raises(ExecutorError) as error:
        client.post_json("https://fixture.invalid", {})
    assert len(calls) == 1
    assert "ReadTimeout" in str(error.value)
    assert "http_result" in caplog.text
    assert "PRIVATE-SYNTHETIC-CANARY" not in caplog.text + str(error.value)


def quote_raw(raw, cap=100):
    http = FakeHttp()
    http.on("/v1/quote", raw)
    cfg = Config()
    cfg.bridge.max_cost_bps = cap
    return quote_cross_chain(cfg, http, "synthetic-owner", USDC, 5_000_000, "base", "USDC")


def test_cross_chain_cost_includes_separate_gas_without_double_counting_included_fees(caplog):
    raw = copy.deepcopy(fixture("lifi_quote_usdc_base.json"))
    raw["estimate"].update(fromAmountUSD="5", toAmountUSD="4.99")
    raw["estimate"]["gasCosts"] = [{"amountUSD": "0.05"}]
    raw["estimate"]["feeCosts"] = [
        {"name": "included", "amountUSD": "0.1", "included": True},
        {"name": "extra", "amountUSD": "0.02", "included": False},
    ]
    with caplog.at_level(logging.INFO):
        result = quote_raw(raw)
    assert result["cost_bps"] == 160 and not result["acceptable"]
    assert "lifi_quote_outcome" in caplog.text
    assert "synthetic-owner" not in caplog.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("gasCosts", None),
        ("gasCosts", [{"amountUSD": "NaN"}]),
        ("feeCosts", [{"amountUSD": "0.01"}]),
        ("feeCosts", [{"amountUSD": "0.01", "included": "false"}]),
    ],
)
def test_cross_chain_unknown_cost_evidence_refuses(field, value):
    raw = copy.deepcopy(fixture("lifi_quote_usdc_base.json"))
    raw["estimate"][field] = value
    with pytest.raises(Refused):
        quote_raw(raw)
