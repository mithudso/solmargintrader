"""Exact ZEC isolated-perpetual orders through the official GUM JTX Action API.

Order messages are constructed locally from checked economics. This module never
signs a server-supplied transaction, creates an account, deposits, or retries a
write. The optional signer signs bytes and returns 64 Ed25519 signature bytes.
The binary layout follows jupnet/gum-perp-sdk 0.2.0 action.rs/request.rs.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import time
import urllib.error
import urllib.request
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any

BASE_URL = "https://api.gum.ag/perps"
PROGRAM_ID = "jtxQHH3ysuWRETjaynai3jowPztq2LBJApVFcEv4Wmg"
MARKET_ID = "9pWk9ibcH33PWj9wg7qC1hqVkJnMtSwMwcA3SXfvzEav"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
U64_MAX = (1 << 64) - 1
MAX_RESPONSE = 2 * 1024 * 1024
TERMINAL = {"filled", "cancelled", "partially_filled_cancelled", "expired"}


class GumError(RuntimeError):
    """A sanitized read failure or refusal before an order POST starts.

    submit_leg wraps every exception after invoking the POST as GumAmbiguous.
    No error includes a request signature or key.
    """


class GumAmbiguous(GumError):
    """The order may have been accepted; only read-only reconciliation is safe."""


def b58encode(value: bytes) -> str:
    zeros = len(value) - len(value.lstrip(b"\0"))
    number, result = int.from_bytes(value, "big"), ""
    while number:
        number, digit = divmod(number, 58)
        result = ALPHABET[digit] + result
    return "1" * zeros + result


def b58decode(value: str, length: int = 32) -> bytes:
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        raise GumError("gum_invalid_public_identity")
    number = 0
    try:
        for char in value:
            number = number * 58 + ALPHABET.index(char)
    except ValueError:
        raise GumError("gum_invalid_public_identity") from None
    raw = b"\0" * (len(value) - len(value.lstrip("1")))
    raw += number.to_bytes((number.bit_length() + 7) // 8, "big")
    if len(raw) != length or b58encode(raw) != value:
        raise GumError("gum_invalid_public_identity")
    return raw


def _decimal(value: Any, *, zero=False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise GumError("gum_invalid_number")
    try:
        if len(str(value)) > 128:
            raise ValueError
        result = Decimal(str(value))
        if (
            not result.is_finite()
            or result.as_tuple().exponent < -128
            or result < 0
            or result > Decimal("1e18")
            or (not zero and result == 0)
        ):
            raise ValueError
        return result
    except (InvalidOperation, ValueError):
        raise GumError("gum_invalid_number") from None


def _integer(value, *, zero=False, maximum=U64_MAX):
    if type(value) is not int or not (0 if zero else 1) <= value <= maximum:
        raise GumError("gum_invalid_integer")
    return value


def _text(value: Decimal) -> str:
    return format(_decimal(value, zero=True), "f")


def _symbol(symbol):
    if not isinstance(symbol, str):
        raise GumError("gum_zec_only")
    ticker = symbol.split(":")[-1]
    if ticker not in {
        "ZEC",
        "ZECUSD",
        "ZECUSDC",
        "ZEC/USD",
        "ZEC/USDC",
        "ZEC-USD",
        "ZEC-USDC",
        "ZEC-PERP",
    }:
        raise GumError("gum_zec_only")
    return "ZEC"


def _short(value: int) -> bytes:
    result = bytearray()
    while True:
        byte, value = value & 127, value >> 7
        result.append(byte | (128 if value else 0))
        if not value:
            return bytes(result)


def action_message(
    owner: str,
    blockhash: str,
    *,
    subaccount_id: int,
    price_lots: int,
    base_lots: int,
    side: str,
    reduce_only: bool,
    collateral_native: int,
    client_order_id: str,
) -> bytes:
    """The SDK's PlaceOrderIsolated + market/FOK Action; no arbitrary program/data."""
    _integer(subaccount_id, zero=True, maximum=199)
    _integer(price_lots)
    _integer(base_lots)
    _integer(collateral_native, zero=True)
    if side not in ("buy", "sell") or type(reduce_only) is not bool:
        raise GumError("gum_invalid_order")
    if reduce_only and collateral_native:
        raise GumError("gum_reduce_cannot_draw_collateral")
    if (
        not isinstance(client_order_id, str)
        or not 1 <= len(client_order_id) <= 20
        or not client_order_id.isascii()
        or not client_order_id.isdecimal()
    ):
        raise GumError("gum_invalid_client_id")
    client = int(client_order_id)
    _integer(client)
    if str(client) != client_order_id:
        raise GumError("gum_invalid_client_id")
    # tag30, collateral u64, subaccount u8, Borsh String, price/base u64,
    # Side(Bid=0,Ask=1), OrderType(Market=1), bool, TIF(FOK=2), Option<u64>.
    data = struct.pack("<BQB", 30, collateral_native, subaccount_id)
    data += struct.pack("<I", 3) + b"ZEC"
    data += struct.pack(
        "<QQBBBBBQ", price_lots, base_lots, side == "sell", 1, reduce_only, 2, 1, client
    )
    return (
        b58decode(blockhash)
        + b58decode(PROGRAM_ID)
        + b"\x01"
        + b58decode(owner)
        + _short(len(data))
        + data
    )


def _http(method, path, owner, body=None):
    if not path.startswith("/") or ".." in path or "#" in path:
        raise GumError("gum_invalid_path")
    headers = {"X-PUBKEY": owner, "Accept": "application/json"}
    payload = None
    if body is not None:
        payload = json.dumps(body, allow_nan=False, separators=(",", ":")).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE_URL + path, data=payload, method=method, headers=headers
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            raise GumError("gum_redirect_refused")

    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(request, timeout=15) as response:
            raw = response.read(MAX_RESPONSE + 1)
            if response.url != BASE_URL + path or len(raw) > MAX_RESPONSE:
                raise GumError("gum_invalid_response")
        return json.loads(raw)
    except (OSError, ValueError, urllib.error.HTTPError):
        if method != "GET":
            raise GumAmbiguous("gum_submission_requires_reconciliation") from None
        raise GumError("gum_read_unavailable") from None


def discover(owner: str, *, call=None) -> dict:
    """Read public owner-scoped state without requiring a funded trading account."""
    b58decode(owner)
    invoke = call or _http
    result = {"venue": "jupiter-gum", "owner": owner}
    for key, path in (
        ("market", "/market/ZEC"),
        ("health", "/health"),
        ("accounts", "/tradingAccount"),
    ):
        result[key] = invoke("GET", path, owner, None)
    if (
        not isinstance(result["accounts"], dict)
        or type(result["accounts"].get("exists")) is not bool
        or not isinstance(result["accounts"].get("accounts"), list)
    ):
        raise GumError("gum_invalid_accounts")
    _market(result["market"])
    return result


def _market(data: dict) -> dict:
    if (
        not isinstance(data, dict)
        or data.get("symbol") != "ZEC"
        or data.get("pubkey") != MARKET_ID
    ):
        raise GumError("gum_market_identity_changed")
    if (
        data.get("baseDecimals"),
        data.get("baseLotSize"),
        data.get("quoteLotSize"),
    ) != (6, 1000, 10):
        raise GumError("gum_market_lot_identity_changed")
    if _decimal(data.get("tickSize")) != Decimal("0.01") or _decimal(
        data.get("stepSize")
    ) != Decimal("0.001"):
        raise GumError("gum_invalid_market_units")
    for key in (
        "markPrice",
        "indexPrice",
        "bestBid",
        "bestAsk",
        "maxAccountPositionNotional",
    ):
        _decimal(data.get(key))
    if _decimal(data["bestBid"]) > _decimal(data["bestAsk"]):
        raise GumError("gum_crossed_market")
    fee = _decimal(data.get("takerFeeBps"), zero=True)
    if fee >= 10000:
        raise GumError("gum_invalid_fee")
    _integer(data.get("maxLeverage"), maximum=255)
    if (
        type(data.get("timestamp")) is not int
        or abs(time.time() - data["timestamp"]) > 5
    ):
        raise GumError("gum_stale_market")
    if _decimal(data.get("lastUpdatedMs"), zero=True) > 5000:
        raise GumError("gum_stale_market")
    if not isinstance(data.get("riskTiers"), list) or not data["riskTiers"]:
        raise GumError("gum_missing_risk_tiers")
    limits = data.get("orderLimitConfig", {}).get("market")
    if not isinstance(limits, dict):
        raise GumError("gum_missing_order_limits")
    for key in (
        "minOrderQty",
        "minOrderNotional",
        "maxOpenOrderQty",
        "maxCloseOrderQty",
        "maxOpenOrderNotional",
        "maxCloseOrderNotional",
    ):
        _decimal(limits.get(key))
    return data


def _quote_fresh(market, received_at):
    _market(market)
    elapsed = time.monotonic() - received_at
    if (
        elapsed < 0
        or _decimal(market["lastUpdatedMs"], zero=True) + Decimal(str(elapsed)) * 1000
        > 5000
    ):
        raise GumError("gum_stale_market")


def _enabled(enabled, deadline):
    if not enabled() or (deadline is not None and time.time() > deadline):
        raise GumError("gum_disarmed_or_expired")


class GumOrders:
    def __init__(
        self,
        owner: str,
        trading_account: str | None = None,
        subaccount_id: int = 0,
        *,
        leverage,
        allocation="75",
        allocation_basis="collateral",
        max_slippage_bps=50,
        signer=None,
        call=None,
    ):
        b58decode(owner)
        if trading_account is not None:
            b58decode(trading_account)
        _integer(subaccount_id, zero=True, maximum=199)
        self.owner, self.account_id, self.subaccount_id = (
            owner,
            trading_account,
            subaccount_id,
        )
        self.leverage, self.allocation = _decimal(leverage), _decimal(allocation)
        if self.leverage < 1 or self.leverage > 50 or self.allocation > 75:
            raise GumError("gum_invalid_allocation_or_leverage")
        if allocation_basis not in ("collateral", "notional"):
            raise GumError("gum_invalid_allocation_basis")
        _integer(max_slippage_bps, maximum=1000)
        self.allocation_basis, self.max_slippage_bps = (
            allocation_basis,
            max_slippage_bps,
        )
        self.signer, self.call = signer, call or _http

    @property
    def binding(self):
        if not self.account_id:
            raise GumError("gum_account_required")
        value = [
            "jupiter-gum",
            "ZEC-PERP",
            self.owner,
            self.account_id,
            self.subaccount_id,
            _text(self.leverage),
            _text(self.allocation),
            self.allocation_basis,
            self.max_slippage_bps,
        ]
        return hashlib.sha256(
            json.dumps(value, separators=(",", ":")).encode()
        ).hexdigest()

    def _get(self, path):
        return self.call("GET", path, self.owner, None)

    def accounts(self):
        data = self._get("/tradingAccount")
        if (
            not isinstance(data, dict)
            or type(data.get("exists")) is not bool
            or not isinstance(data.get("accounts"), list)
        ):
            raise GumError("gum_invalid_accounts")
        rows = data["accounts"]
        if data["exists"] != bool(rows):
            raise GumError("gum_invalid_accounts")
        for row in rows:
            if not isinstance(row, dict) or type(row.get("isolated")) is not bool:
                raise GumError("gum_invalid_account")
            b58decode(row.get("pubkey"))
            _integer(row.get("subaccountId"), zero=True, maximum=255)
        return rows

    def _account(self, account_id=None):
        if account_id is not None and account_id != self.account_id:
            raise GumError("gum_account_changed")
        rows = self.accounts()
        matches = [row for row in rows if row["pubkey"] == self.account_id]
        if (
            len(matches) != 1
            or matches[0]["isolated"]
            or matches[0]["subaccountId"] != self.subaccount_id
            or matches[0].get("market") is not None
        ):
            raise GumError("gum_account_missing_or_not_owned")
        return rows

    def _positions(self, rows):
        positions = self._get(f"/tradingAccount/{self.account_id}/positions")
        if not isinstance(positions, list):
            raise GumError("gum_invalid_positions")
        isolated = [
            row
            for row in rows
            if row["isolated"] and row["subaccountId"] == self.subaccount_id
        ]
        # Aggregated API reads may omit a missing isolated snapshot. Direct reads
        # of every known isolated account must succeed before declaring flat.
        direct = []
        for account in isolated:
            current = self._get(f"/tradingAccount/{account['pubkey']}/positions")
            if not isinstance(current, list):
                raise GumError("gum_invalid_positions")
            direct.extend(current)
        aggregated = [
            p for p in positions if isinstance(p, dict) and p.get("isolated") is True
        ]

        def identity(p):
            if not isinstance(p, dict):
                raise GumError("gum_invalid_positions")
            return json.dumps(
                {k: p.get(k) for k in ("symbol", "side", "size", "isolated")},
                sort_keys=True,
            )

        if sorted(identity(p) for p in direct) != sorted(
            identity(p) for p in aggregated
        ):
            raise GumError("gum_inconsistent_isolated_snapshot")
        if len(positions) > 1:
            raise GumError("gum_account_not_dedicated")
        if not positions:
            return {"side": None, "size": "0", "isolated": True}
        row = positions[0]
        if (
            not isinstance(row, dict)
            or row.get("symbol") != "ZEC"
            or row.get("isolated") is not True
            or row.get("side") not in ("Bid", "Ask")
        ):
            raise GumError("gum_foreign_or_cross_position")
        size = _decimal(row.get("size"))
        if size % Decimal("0.001"):
            raise GumError("gum_invalid_position_lots")
        _decimal(row.get("collateral"))
        return {
            "side": "buy" if row["side"] == "Bid" else "sell",
            "size": _text(size),
            "isolated": True,
        }

    def get_net_position(self, account_id=None):
        rows = self._account(account_id)
        for row in rows:
            if row["subaccountId"] == self.subaccount_id:
                orders = self._get(f"/tradingAccount/{row['pubkey']}/orders")
                if not isinstance(orders, list) or orders:
                    raise GumError("gum_open_orders_or_unavailable")
        return self._positions(rows)

    def preflight(self):
        rows = self._account()
        health = self._get("/health")
        if not isinstance(health, dict) or health.get("trading_available") is not True:
            raise GumError("gum_trading_unavailable")
        market = _market(self._get("/market/ZEC"))
        received_at = time.time()
        received_monotonic = time.monotonic()
        if self.leverage > _decimal(market["maxLeverage"]):
            raise GumError("gum_leverage_unavailable")
        position = self._positions(rows)
        account_ids = [self.account_id] + [
            r["pubkey"]
            for r in rows
            if r["isolated"] and r["subaccountId"] == self.subaccount_id
        ]
        for account_id in account_ids:
            orders = self._get(f"/tradingAccount/{account_id}/orders")
            if not isinstance(orders, list) or orders:
                raise GumError("gum_open_orders_or_unavailable")
        preferences = self._get(f"/tradingAccount/{self.account_id}/leverage")
        if not isinstance(preferences, list):
            raise GumError("gum_invalid_leverage_preferences")
        selected = []
        for preference in preferences:
            if (
                not isinstance(preference, dict)
                or type(preference.get("isolated")) is not bool
            ):
                raise GumError("gum_invalid_leverage_preferences")
            if preference.get("symbol") == "ZEC" and preference["isolated"]:
                selected.append(_integer(preference.get("leverage"), maximum=50))
        if len(selected) > 1:
            raise GumError("gum_ambiguous_leverage_preference")
        balance = self._get(f"/tradingAccount/{self.account_id}/balances")
        if not isinstance(balance, dict):
            raise GumError("gum_invalid_balance")
        free = _decimal(balance.get("freeBalance"), zero=True)
        _decimal(balance.get("availableToTrade"), zero=True)
        _integer(balance.get("tokenBalance"), zero=True)
        residual = Decimal(0)
        for row in rows:
            if row["isolated"] and row["subaccountId"] == self.subaccount_id:
                if row.get("market") != "ZEC":
                    raise GumError("gum_account_not_dedicated")
                data = self._get(f"/tradingAccount/{row['pubkey']}/balances")
                residual += max(
                    _decimal(data.get("freeBalance"), zero=True),
                    Decimal(_integer(data.get("tokenBalance"), zero=True)) / 1000000,
                )
        _quote_fresh(market, received_monotonic)
        return {
            "venue": "jupiter-gum",
            "owner": self.owner,
            "account_id": self.account_id,
            "binding": self.binding,
            "market": market,
            "position": position,
            "free_usdc": _text(free),
            "idle_isolated_usdc": _text(residual),
            "selected_leverage": selected[0] if selected else None,
            "observed_at": received_at,
            "quote_monotonic_at": received_monotonic,
        }

    def plan(self, symbol, side, account_id=None):
        _symbol(symbol)
        if side not in ("buy", "sell"):
            raise GumError("gum_invalid_side")
        if account_id is not None and account_id != self.account_id:
            raise GumError("gum_account_changed")
        state = self.preflight()
        market, position = state["market"], state["position"]
        action = (
            "noop"
            if position["side"] == side
            else "close"
            if position["side"]
            else "open"
        )
        leg_side = (
            ("sell" if position["side"] == "buy" else "buy")
            if action == "close"
            else side
        )
        plan = {
            "venue": "jupiter-gum",
            "product_id": "ZEC-PERP",
            "symbol": "ZEC",
            "owner": self.owner,
            "account_id": self.account_id,
            "subaccount_id": self.subaccount_id,
            "binding": self.binding,
            "action": action,
            "target_side": side,
            "side": leg_side,
            "leverage": _text(self.leverage),
            "allocation": _text(self.allocation),
            "allocation_basis": self.allocation_basis,
            "max_slippage_bps": self.max_slippage_bps,
            "isolated": True,
            "reduce_only": action == "close",
            "free_usdc_before": state["free_usdc"],
            "market_timestamp": market["timestamp"],
            "market_last_updated_ms": market["lastUpdatedMs"],
            "quote_monotonic_at": state["quote_monotonic_at"],
            "position_before": position,
            "observed_at": state["observed_at"],
        }
        if action == "noop":
            return plan
        tick, step = Decimal("0.01"), Decimal("0.001")
        slip = Decimal(self.max_slippage_bps) / 10000
        cap = (
            (_decimal(market["bestAsk"]) * (1 + slip) / tick).to_integral_value(
                rounding=ROUND_FLOOR
            )
            * tick
            if leg_side == "buy"
            else (_decimal(market["bestBid"]) * (1 - slip) / tick).to_integral_value(
                rounding=ROUND_CEILING
            )
            * tick
        )
        risk_price = max(
            cap, *(_decimal(market[k]) for k in ("markPrice", "bestBid", "bestAsk"))
        )
        adverse_price = (
            max(
                Decimal(0),
                cap - min(_decimal(market["markPrice"]), _decimal(market["bestBid"])),
            )
            if leg_side == "buy"
            else risk_price - cap
        )
        fee = _decimal(market["takerFeeBps"], zero=True) / 10000
        collateral_native = 0
        if action == "close":
            quantity = _decimal(position["size"])
        else:
            if _decimal(state["idle_isolated_usdc"], zero=True):
                raise GumError("gum_idle_isolated_collateral_requires_reconciliation")
            allocated = _decimal(state["free_usdc"], zero=True) * self.allocation / 100
            collateral = (
                allocated
                if self.allocation_basis == "collateral"
                else allocated / self.leverage
            )
            collateral_native = int(
                (collateral * 1000000).to_integral_value(rounding=ROUND_FLOOR)
            )
            collateral = Decimal(collateral_native) / 1000000
            # Reserve both fees and adverse execution loss against current mark.
            # This is a quote-time bound; subsequent price movement changes leverage.
            unit_budget = risk_price / self.leverage + fee * risk_price + adverse_price
            quantity = (collateral / unit_budget / step).to_integral_value(
                rounding=ROUND_FLOOR
            ) * step
            plan["unit_margin_budget_usdc"] = _text(unit_budget)
        if quantity <= 0:
            raise GumError("gum_insufficient_collateral")
        limits = market["orderLimitConfig"]["market"]
        suffix = "Close" if action == "close" else "Open"
        notional = quantity * risk_price
        if quantity < _decimal(limits["minOrderQty"]) or notional < _decimal(
            limits["minOrderNotional"]
        ):
            raise GumError("gum_below_minimum_order")
        if (
            quantity > _decimal(limits[f"max{suffix}OrderQty"])
            or notional > _decimal(limits[f"max{suffix}OrderNotional"])
            or notional > _decimal(market["maxAccountPositionNotional"])
        ):
            raise GumError("gum_order_limit_exceeded")
        tiers = market["riskTiers"]
        previous_cap = Decimal(0)
        chosen = None
        for tier in tiers:
            ceiling = _decimal(tier.get("notionalCap"))
            maximum = _integer(tier.get("maxLeverage"), maximum=50)
            if ceiling <= previous_cap:
                raise GumError("gum_invalid_risk_tiers")
            previous_cap = ceiling
            if chosen is None and notional < ceiling:
                chosen = maximum
        if action == "open":
            preference = state["selected_leverage"]
            # With no explicit preference, the API admits the first tier's max
            # leverage and corresponding cap (REST API Set Leverage section).
            admitted = (
                preference
                if preference is not None
                else _integer(tiers[0]["maxLeverage"], maximum=50)
            )
            if chosen is None or self.leverage > chosen or admitted > chosen:
                raise GumError("gum_explicit_risk_tier_configuration_required")
            if self.leverage > admitted:
                raise GumError("gum_leverage_preference_too_low")
        plan.update(
            quantity=_text(quantity),
            base_lots=int(quantity / step),
            price_cap=_text(cap),
            price_lots=int(cap / tick),
            collateral_native=collateral_native,
            notional_cap=_text(notional),
            estimated_open_fee_usdc=_text(notional * fee),
            taker_fee_bps=_text(_decimal(market["takerFeeBps"], zero=True)),
            reduce_only=action == "close",
        )
        return plan

    def submit_leg(self, plan, client_order_id, *, enabled=lambda: True, deadline=None):
        _enabled(enabled, deadline)
        if self.signer is None:
            raise GumError("gum_signer_unavailable")
        if (
            not isinstance(plan, dict)
            or plan.get("binding") != self.binding
            or plan.get("action") not in ("open", "close")
        ):
            raise GumError("gum_invalid_plan")
        if (
            not isinstance(plan.get("observed_at"), (int, float))
            or not 0 <= time.time() - plan["observed_at"] <= 5
        ):
            raise GumError("gum_plan_expired")
        # Rebuild economics against fresh account/market state. A changed quote
        # can improve the bound; it cannot widen the already-persisted cap.
        fresh = self.plan("ZEC", plan.get("target_side"), self.account_id)
        for key in (
            "venue",
            "product_id",
            "symbol",
            "owner",
            "account_id",
            "subaccount_id",
            "action",
            "side",
            "position_before",
            "reduce_only",
            "isolated",
            "leverage",
            "allocation",
            "allocation_basis",
            "max_slippage_bps",
        ):
            if fresh.get(key) != plan.get(key):
                raise GumError("gum_plan_state_changed")
        quantity_dec = _decimal(plan.get("quantity"))
        if quantity_dec * 1000 != _integer(plan.get("base_lots")):
            raise GumError("gum_plan_lots_changed")
        collateral_native = _integer(plan.get("collateral_native"), zero=True)
        if plan["action"] == "close":
            if quantity_dec != _decimal(fresh["quantity"]) or collateral_native:
                raise GumError("gum_plan_state_changed")
        elif (
            collateral_native > fresh["collateral_native"]
            or collateral_native == 0
            or quantity_dec
            > Decimal(collateral_native)
            / 1000000
            / Decimal(fresh["unit_margin_budget_usdc"])
        ):
            raise GumError("gum_plan_budget_changed")
        price_lots = _integer(plan.get("price_lots"))
        if _decimal(plan.get("price_cap")) != Decimal(price_lots) / 100:
            raise GumError("gum_price_lots_changed")
        if (plan["side"] == "buy" and price_lots > fresh["price_lots"]) or (
            plan["side"] == "sell" and price_lots < fresh["price_lots"]
        ):
            raise GumError("gum_price_cap_widened")
        price, quantity = float(plan["price_cap"]), float(plan["quantity"])
        # Match the SDK/API f64 lot conversion before signing. This bounded ZEC
        # subset has integral decimal lots; refuse any conversion discrepancy.
        if (
            not math.isfinite(price)
            or not math.isfinite(quantity)
            or round(price * 1000) // 10 != price_lots
            or round(quantity * 1000) != plan["base_lots"]
        ):
            raise GumError("gum_wire_lot_mismatch")
        block = self._get("/blockhash")
        if not isinstance(block, dict):
            raise GumError("gum_invalid_blockhash")
        blockhash = block.get("blockhash")
        message = action_message(
            self.owner,
            blockhash,
            subaccount_id=self.subaccount_id,
            price_lots=price_lots,
            base_lots=plan["base_lots"],
            side=plan["side"],
            reduce_only=plan["reduce_only"],
            collateral_native=plan["collateral_native"],
            client_order_id=client_order_id,
        )

        def fresh_and_enabled():
            _enabled(enabled, deadline)
            elapsed = time.monotonic() - fresh["quote_monotonic_at"]
            if (
                elapsed < 0
                or abs(time.time() - fresh["market_timestamp"]) > 5
                or Decimal(str(fresh["market_last_updated_ms"]))
                + Decimal(str(elapsed)) * 1000
                > 5000
            ):
                raise GumError("gum_stale_market")

        fresh_and_enabled()
        signature = self.signer(message)
        if not isinstance(signature, bytes) or len(signature) != 64:
            raise GumError("gum_invalid_signature")
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
        except ImportError:
            raise GumError("gum_signing_extra_unavailable") from None
        try:
            Ed25519PublicKey.from_public_bytes(b58decode(self.owner)).verify(
                signature, message
            )
        except (InvalidSignature, TypeError, ValueError):
            raise GumError("gum_signature_owner_mismatch") from None
        body = {
            "subaccountId": self.subaccount_id,
            "symbol": "ZEC",
            "side": "Bid" if plan["side"] == "buy" else "Ask",
            "orderType": "market",
            "price": price,
            "quantity": quantity,
            "reduceOnly": plan["reduce_only"],
            "timeInForce": "FillOrKill",
            "clientOrderId": client_order_id,
            "isIsolated": True,
            "collateralAmount": plan["collateral_native"],
            "tradingAccount": self.account_id,
            "recentBlockhash": blockhash,
            "signature": "0:" + b58encode(signature),
        }
        fresh_and_enabled()
        try:
            result = self.call("POST", "/order/create", self.owner, body)
            if (
                not isinstance(result, dict)
                or result.get("symbol") != "ZEC"
                or result.get("clientOrderId") != client_order_id
            ):
                raise GumAmbiguous("gum_unverified_submission_identity")
        except Exception:  # noqa: BLE001 - every failure after POST starts is ambiguous
            raise GumAmbiguous("gum_submission_requires_reconciliation") from None
        return {
            "client_order_id": client_order_id,
            "account_id": self.account_id,
            "owner": self.owner,
            "subaccount_id": self.subaccount_id,
            "symbol": "ZEC",
            "side": plan["side"],
            "status": "pending",
        }

    def reconcile(self, plan, client_order_id):
        if not isinstance(plan, dict) or plan.get("binding") != self.binding:
            raise GumError("gum_invalid_plan")
        matches = []
        for offset in range(0, 50000, 500):
            data = self._get(
                f"/tradingAccount/{self.account_id}/orderHistory?symbol=ZEC&limit=500&offset={offset}"
            )
            if not isinstance(data, dict) or not isinstance(data.get("orders"), list):
                raise GumError("gum_invalid_order_history")
            entries = data["orders"]
            matches.extend(
                row
                for row in entries
                if isinstance(row, dict) and row.get("clientOrderId") == client_order_id
            )
            if len(entries) < 500:
                break
        else:
            raise GumError("gum_history_pagination_incomplete")
        if not matches:
            return {"status": "unknown", "client_order_id": client_order_id}
        if len(matches) != 1:
            raise GumError("gum_duplicate_client_id")
        order = matches[0]
        if (
            order.get("symbol") != "ZEC"
            or order.get("side") != ("Bid" if plan["side"] == "buy" else "Ask")
            or order.get("isolated") is not True
            or order.get("reduceOnly") != plan["reduce_only"]
            or _decimal(order.get("originalSize")) != _decimal(plan["quantity"])
            or order.get("orderType") != "market"
            or order.get("timeInForce") != "fok"
            or not isinstance(order.get("orderId"), str)
            or not order["orderId"].isdigit()
        ):
            raise GumError("gum_order_identity_mismatch")
        if (
            not plan["reduce_only"]
            and _decimal(order.get("initialCollateral"), zero=True) * 1000000
            != plan["collateral_native"]
        ):
            raise GumError("gum_collateral_receipt_mismatch")
        filled = _decimal(order.get("filledSize"), zero=True)
        original = _decimal(order["originalSize"])
        if filled > original:
            raise GumError("gum_invalid_fill")
        trail = order.get("transactions")
        if not isinstance(trail, list):
            raise GumError("gum_invalid_fill_trail")
        transactions = []
        fill_quantity, actual_fee = Decimal(0), Decimal(0)
        for transaction in trail:
            if not isinstance(transaction, dict):
                raise GumError("gum_invalid_fill_trail")
            kind, signature, timestamp = (
                transaction.get(k) for k in ("type", "signature", "timestamp")
            )
            if (
                kind not in ("submit", "fill", "cancel")
                or not isinstance(signature, str)
                or not 1 <= len(signature) <= 128
                or not signature.isascii()
                or not signature.isprintable()
                or any(c.isspace() for c in signature)
                or type(timestamp) is not int
                or not 0 < timestamp <= time.time() + 30
            ):
                raise GumError("gum_invalid_fill_trail")
            entry = {"type": kind, "signature": signature, "timestamp": timestamp}
            if kind == "fill":
                if any(
                    not isinstance(transaction.get(k), str)
                    for k in ("price", "size", "fee")
                ):
                    raise GumError("gum_invalid_fill_economics")
                price, size = (
                    _decimal(transaction["price"]),
                    _decimal(transaction["size"]),
                )
                fee = _decimal(transaction["fee"], zero=True)
                if (
                    size % Decimal("0.001")
                    or (plan["side"] == "buy" and price > Decimal(plan["price_cap"]))
                    or (plan["side"] == "sell" and price < Decimal(plan["price_cap"]))
                ):
                    raise GumError("gum_fill_exceeds_plan")
                maximum_fee = price * size * _decimal(
                    plan["taker_fee_bps"], zero=True
                ) / 10000 + Decimal("0.000001")
                if fee > maximum_fee:
                    raise GumError("gum_fill_fee_exceeds_quote")
                role = transaction.get("role")
                if role is not None and role not in ("maker", "taker"):
                    raise GumError("gum_invalid_fill_role")
                entry.update(price=_text(price), size=_text(size), fee=_text(fee))
                if role is not None:
                    entry["role"] = role
                fill_quantity += size
                actual_fee += fee
            transactions.append(entry)
        if fill_quantity != filled:
            raise GumError("gum_fill_trail_quantity_mismatch")
        state = order.get("status")
        if state == "filled" and filled == original:
            status = "filled"
        elif state in TERMINAL:
            status = "cancelled"
        elif state in ("open", "partially_filled"):
            status = "pending"
        else:
            status = "unknown"
        position = self.get_net_position()
        settled = False
        if plan["reduce_only"] and status == "filled" and position["side"] is None:
            # An isolated close settles equity back to its parent (SDK REST API,
            # executedCollateral). Wait for actual balance settlement, not just
            # indexed fills, before sizing the next opening leg.
            executed = order.get("executedCollateral")
            try:
                returned = -Decimal(executed)
                if not returned.is_finite() or returned < 0:
                    raise ValueError
                state = self.preflight()
                settled = (
                    Decimal(state["idle_isolated_usdc"]) == 0
                    and Decimal(state["free_usdc"])
                    >= Decimal(plan["free_usdc_before"]) + returned
                )
            except (InvalidOperation, TypeError, ValueError):
                settled = False
        return {
            "status": status,
            "filled_quantity": _text(filled),
            "original_quantity": _text(original),
            "client_order_id": client_order_id,
            "order_id": order["orderId"],
            "account_id": self.account_id,
            "owner": self.owner,
            "subaccount_id": self.subaccount_id,
            "symbol": "ZEC",
            "side": plan["side"],
            "reduce_only": plan["reduce_only"],
            "isolated": True,
            "position": position,
            "settled": settled,
            "transactions": transactions,
            "actual_fee_usdc": _text(actual_fee),
        }
