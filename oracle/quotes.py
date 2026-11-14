"""Explicit opt-in Swap v1 evidence owned by the existing shared Oracle archive.

This module never builds transactions, signs, retries, or starts a collector.
Quoted outputs and cost assumptions remain distinct from observed execution.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

from .store import canonical

ENDPOINT = "https://api.jup.ag/swap/v1/quote"
MINT = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
MAX_RESPONSE = 262144
ROUTE_POLICY = "direct_single_leg_100pct_v1"
QUOTE_BUDGET_PATH = (
    Path.home() / ".local/share/solmargintrader/oracle/quote-budget.sqlite3"
)


class QuoteError(ValueError):
    """Sanitized symbolic data-quality failure; no provider body or key."""


def _hash(body):
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def _raw(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,24}", value):
        return int(value)
    raise QuoteError("invalid_raw_amount")


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {
        "inputMint",
        "outputMint",
        "amount",
        "slippageBps",
    }:
        raise QuoteError("invalid_quote_request")
    if (
        any(
            not isinstance(request[k], str) or not MINT.fullmatch(request[k])
            for k in ("inputMint", "outputMint")
        )
        or request["inputMint"] == request["outputMint"]
    ):
        raise QuoteError("invalid_quote_mints")
    if (
        type(request["amount"]) is not int
        or not 0 < request["amount"] < 2**64
        or type(request["slippageBps"]) is not int
        or not 0 <= request["slippageBps"] < 10000
    ):
        raise QuoteError("invalid_quote_size_or_slippage")
    return dict(request)


def capture_quote(
    request, response, *, requested_at, received_at, expires_at, max_latency_s
):
    request = validate_request(request)
    try:
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v)
                for v in (requested_at, received_at, expires_at, max_latency_s)
            )
            or not 0 < requested_at <= received_at < expires_at
            or not 0 < max_latency_s <= 30
            or received_at - requested_at > max_latency_s
            or expires_at - received_at > 30
        ):
            raise QuoteError("quote_clock_or_latency_invalid")
        if (
            not isinstance(response, dict)
            or any(
                response[k] != request[k]
                for k in ("inputMint", "outputMint", "slippageBps")
            )
            or response["swapMode"] != "ExactIn"
            or _raw(response["inAmount"]) != request["amount"]
        ):
            raise QuoteError("quote_request_mismatch")
        out, minimum = (
            _raw(response["outAmount"]),
            _raw(response["otherAmountThreshold"]),
        )
        if (
            not 0 < minimum <= out
            or type(response["contextSlot"]) is not int
            or response["contextSlot"] <= 0
        ):
            raise QuoteError("quote_output_or_slot_missing")
        plan = response["routePlan"]
        if not isinstance(plan, list) or not 1 <= len(plan) <= 32:
            raise QuoteError("quote_route_missing")
        # The current capture contract can independently reconcile one direct
        # leg. Split/multihop flow and nonzero platform fees need separate
        # amount accounting; syntactic validity must never imply support.
        if len(plan) != 1:
            raise QuoteError("quote_route_topology_unsupported")
        routes = []
        for leg in plan:
            info = leg["swapInfo"]
            if any(
                not isinstance(info[k], str) or not MINT.fullmatch(info[k])
                for k in ("ammKey", "inputMint", "outputMint", "feeMint")
            ):
                raise QuoteError("quote_route_identity_invalid")
            if type(leg["percent"]) is not int or not 0 < leg["percent"] <= 100:
                raise QuoteError("quote_route_allocation_invalid")
            if leg["percent"] != 100 or (
                "bps" in leg and (type(leg["bps"]) is not int or leg["bps"] != 10000)
            ):
                raise QuoteError("quote_route_allocation_invalid")
            route_in, route_out = _raw(info["inAmount"]), _raw(info["outAmount"])
            if (
                info["inputMint"] != request["inputMint"]
                or info["outputMint"] != request["outputMint"]
                or route_in <= 0
                or route_out <= 0
                or route_in != request["amount"]
                or route_out != out
            ):
                raise QuoteError("quote_route_envelope_mismatch")
            if info["feeMint"] not in (info["inputMint"], info["outputMint"]):
                raise QuoteError("quote_route_fee_currency_unsupported")
            routes.append(
                {
                    "percent": leg["percent"],
                    "swapInfo": {
                        **{
                            k: info[k]
                            for k in ("ammKey", "inputMint", "outputMint", "feeMint")
                        },
                        **{
                            k: str(_raw(info[k]))
                            for k in ("inAmount", "outAmount", "feeAmount")
                        },
                    },
                }
            )
        platform = response.get("platformFee")
        if platform is not None:
            if (
                not isinstance(platform, dict)
                or type(platform["feeBps"]) is not int
                or not 0 <= platform["feeBps"] < 10000
            ):
                raise QuoteError("quote_platform_fee_invalid")
            platform = {
                "amount": str(_raw(platform["amount"])),
                "feeBps": platform["feeBps"],
            }
            if _raw(platform["amount"]) != 0 or platform["feeBps"] != 0:
                raise QuoteError("quote_platform_fee_topology_unsupported")
        # Swap v1's misleading Pct suffix denotes a decimal fraction, not
        # percentage points. Keep the exact decimal string, avoiding binary
        # rounding, and distinguish missing evidence from an observed zero.
        impact = response.get("priceImpactPct")
        if impact is not None and (
            not isinstance(impact, str)
            or len(impact) > 128
            or re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", impact) is None
            or not Decimal(0) <= Decimal(impact) <= Decimal(1)
        ):
            raise QuoteError("quote_price_impact_invalid")
        sanitized = {
            **{
                k: response[k]
                for k in (
                    "inputMint",
                    "outputMint",
                    "swapMode",
                    "slippageBps",
                    "contextSlot",
                )
            },
            "inAmount": str(request["amount"]),
            "outAmount": str(out),
            "otherAmountThreshold": str(minimum),
            "routePlan": routes,
            "platformFee": platform,
            "priceImpactPct": impact,
        }
        result = {
            "schema_version": 1,
            "source": "jupiter_swap_v1",
            "api_version": "swap/v1/quote",
            "request": request,
            "route_policy": ROUTE_POLICY,
            "response": sanitized,
            "price_impact": {
                "value": impact,
                "unit": "fraction",
                "state": "observed" if impact is not None else "unavailable",
                "reason": None if impact is not None else "price_impact_unavailable",
            },
            "requested_at": requested_at,
            "received_at": received_at,
            "expires_at": expires_at,
            "max_latency_s": max_latency_s,
            "latency_s": received_at - requested_at,
            "fee_complete": False,
            "costs": None,
            "certified": False,
            "certification_reasons": [
                "network_priority_rent_costs_unavailable",
                "fill_not_observed",
                "quote_not_execution",
            ],
            "fill_assumption": "minimum_output_only_no_fill_guarantee",
        }
        if impact is None:
            result["certification_reasons"].append("price_impact_unavailable")
        result["observation_id"] = _hash(result)
        return result
    except QuoteError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise QuoteError("invalid_quote_response") from exc


def validate_observation(observation):
    try:
        expected = capture_quote(
            observation["request"],
            observation["response"],
            requested_at=observation["requested_at"],
            received_at=observation["received_at"],
            expires_at=observation["expires_at"],
            max_latency_s=observation["max_latency_s"],
        )
        if canonical(expected) != canonical(observation):
            raise QuoteError("quote_observation_integrity_invalid")
        return expected
    except (KeyError, TypeError) as exc:
        raise QuoteError("invalid_quote_observation") from exc


def _connection(path, *, write=False):
    path = Path(path)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise QuoteError("shared_archive_absent")
    db = sqlite3.connect(
        path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=1
    )
    try:
        if not write:
            db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        if (
            db.execute("PRAGMA application_id").fetchone()[0] != 0x4F52434C
            or db.execute("PRAGMA user_version").fetchone()[0] not in (1, 2)
        ):
            raise QuoteError("shared_archive_incompatible")
        if write:
            row = db.execute(
                "SELECT body FROM metadata WHERE key='quote_schema'"
            ).fetchone()
            if row and row[0] != "1":
                raise QuoteError("quote_schema_incompatible")
            db.execute("INSERT OR IGNORE INTO metadata VALUES('quote_schema','1')")
            db.execute(
                "CREATE TABLE IF NOT EXISTS quote_observations (sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, body TEXT NOT NULL)"
            )
            for op in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER IF NOT EXISTS immutable_quotes_{op} BEFORE {op} ON quote_observations BEGIN SELECT RAISE(ABORT,'immutable_quotes'); END"
                )
        return db
    except Exception:
        db.close()
        raise


def import_quote(archive_path, observation):
    q = validate_observation(observation)
    db = None
    try:
        db = _connection(archive_path, write=True)
        db.execute(
            "INSERT OR IGNORE INTO quote_observations(id,body) VALUES(?,?)",
            (q["observation_id"], canonical(q)),
        )
        db.commit()
        return q
    except sqlite3.Error as exc:
        raise QuoteError("shared_quote_archive_unavailable") from exc
    finally:
        if db is not None:
            db.close()


def read_quote_page(archive_path, *, after=0, limit=1000):
    if (
        type(after) is not int
        or after < 0
        or type(limit) is not int
        or not 1 <= limit <= 1000
    ):
        raise QuoteError("invalid_quote_page")
    db = None
    try:
        db = _connection(archive_path)
        version = db.execute(
            "SELECT body FROM metadata WHERE key='quote_schema'"
        ).fetchone()
        if version is None:
            return {
                "schema_version": 1,
                "items": [],
                "next_after": after,
                "has_more": False,
            }
        if version[0] != "1":
            raise QuoteError("quote_schema_incompatible")
        rows = db.execute(
            "SELECT sequence,body FROM quote_observations WHERE sequence>? ORDER BY sequence LIMIT ?",
            (after, limit + 1),
        ).fetchall()
        items = [
            {"sequence": r[0], "observation": validate_observation(json.loads(r[1]))}
            for r in rows[:limit]
        ]
        return {
            "schema_version": 1,
            "items": items,
            "next_after": items[-1]["sequence"] if items else after,
            "has_more": len(rows) > limit,
        }
    except (sqlite3.Error, ValueError) as exc:
        if isinstance(exc, QuoteError):
            raise
        raise QuoteError("shared_quote_archive_unavailable") from exc
    finally:
        if db is not None:
            db.close()


def read_quotes(archive_path, *, after=0, limit=1000):
    """Compatibility list projection; new consumers use sequence-bearing pages."""
    return [
        item["observation"]
        for item in read_quote_page(archive_path, after=after, limit=limit)["items"]
    ]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise QuoteError("quote_redirect_refused")


def _read_body(response, deadline):
    data = bytearray()
    while len(data) <= MAX_RESPONSE:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise QuoteError("quote_deadline_exceeded")
        # CPython's HTTPResponse exposes the transport beneath its buffered file.
        # read1 performs one socket receive, so progress cannot reset the budget.
        transport = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
        if transport is not None:
            transport.settimeout(remaining)
        chunk = response.read1(min(65536, MAX_RESPONSE + 1 - len(data)))
        if time.monotonic() >= deadline:
            raise QuoteError("quote_deadline_exceeded")
        if not chunk:
            return bytes(data)
        data.extend(chunk)
    raise QuoteError("quote_response_too_large")


def collect_quote(
    archive_path,
    request,
    *,
    enabled=False,
    api_key=None,
    endpoint=ENDPOINT,
    _test_endpoint=False,
    timeout=5.0,
    max_latency_s=2.0,
    _test_budget_path=None,
):
    """One authenticated GET, one shared 60/minute budget; never retry a request."""
    if enabled is not True:
        raise QuoteError("quote_collection_not_enabled")
    request = validate_request(request)
    if (
        not isinstance(api_key, str)
        or not api_key
        or "\n" in api_key
        or "\r" in api_key
    ):
        raise QuoteError("credentials_unavailable")
    parsed = urllib.parse.urlsplit(endpoint)
    test_ok = (
        _test_endpoint is True
        and parsed.scheme == "http"
        and parsed.hostname in ("127.0.0.1", "localhost", "::1")
    )
    if (
        (endpoint != ENDPOINT and not test_ok)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise QuoteError("quote_endpoint_refused")
    if (
        type(timeout) not in (int, float)
        or not math.isfinite(timeout)
        or not 0 < timeout <= 30
    ):
        raise QuoteError("invalid_quote_timeout")
    if _test_budget_path is not None and not test_ok:
        raise QuoteError("quote_budget_override_refused")
    budget_path = (
        Path(_test_budget_path) if _test_budget_path is not None else QUOTE_BUDGET_PATH
    )
    # Validate the selected existing producer archive before creating any budget.
    archive_db = _connection(archive_path)
    archive_db.close()
    budget_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if budget_path.is_symlink():
        raise QuoteError("quote_budget_symlink_refused")
    db = None
    try:
        db = sqlite3.connect(budget_path, timeout=1)
        db.execute("BEGIN IMMEDIATE")
        application = db.execute("PRAGMA application_id").fetchone()[0]
        version = db.execute("PRAGMA user_version").fetchone()[0]
        tables = db.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        if (
            application not in (0, 0x4F525142)
            or version not in (0, 1)
            or tables
            and application != 0x4F525142
        ):
            raise QuoteError("quote_budget_incompatible")
        db.execute(
            "CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, at REAL NOT NULL)"
        )
        db.execute("PRAGMA application_id=1330794818")
        db.execute("PRAGMA user_version=1")
        now = time.time()
        if (
            db.execute(
                "SELECT count(*) FROM requests WHERE at>?", (now - 60,)
            ).fetchone()[0]
            >= 60
        ):
            raise QuoteError("aggregate_rate_budget_exhausted")
        db.execute("DELETE FROM requests WHERE at<=?", (now - 60,))
        db.execute("INSERT INTO requests(at) VALUES(?)", (now,))
        db.commit()
        budget_path.chmod(0o600)
    except sqlite3.Error as exc:
        raise QuoteError("shared_quote_budget_unavailable") from exc
    finally:
        if db is not None:
            db.close()
    query = {**request, "swapMode": "ExactIn", "onlyDirectRoutes": "true"}
    req = urllib.request.Request(
        endpoint + "?" + urllib.parse.urlencode(query),
        headers={"x-api-key": api_key, "Accept": "application/json"},
    )
    requested = time.time()
    deadline = time.monotonic() + timeout
    try:
        with urllib.request.build_opener(_NoRedirect).open(
            req, timeout=timeout
        ) as response:
            if (
                response.status != 200
                or response.headers.get_content_type() != "application/json"
            ):
                raise QuoteError("quote_http_response_invalid")
            raw = _read_body(response, deadline)
        received = time.time()
        body = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise QuoteError(
            "quote_rate_limited" if exc.code == 429 else "quote_http_error"
        ) from None
    except (OSError, ValueError) as exc:
        if isinstance(exc, QuoteError):
            raise
        raise QuoteError("quote_transport_or_body_invalid") from None
    observation = capture_quote(
        request,
        body,
        requested_at=requested,
        received_at=received,
        expires_at=received + 5,
        max_latency_s=max_latency_s,
    )
    return import_quote(archive_path, observation)
