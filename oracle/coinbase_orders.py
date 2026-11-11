"""Exact Coinbase spot sizing and one-shot official CLI order transport.

Credentials remain in the official CLI's configured credential store. This
adapter neither reads credentials nor retries an order submission.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

MAX_PAGES = 100
MAX_OUTPUT = 1024 * 1024
PAIR = re.compile(r"[A-Z0-9]{1,20}-[A-Z0-9]{1,20}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}\Z")
PLAIN_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
ORDER_FIELDS = (
    "order_id",
    "client_order_id",
    "product_id",
    "side",
    "status",
    "order_configuration",
    "created_time",
    "last_fill_time",
    "completion_percentage",
    "filled_size",
    "average_filled_price",
    "total_fees",
    "total_value_after_fees",
    "number_of_fills",
)


class CoinbaseError(RuntimeError):
    """A sanitized failure before submission or during a read."""


class CoinbaseAmbiguous(CoinbaseError):
    """An order may have been accepted. Reconcile; never submit again."""


def _decimal(value: Any, *, zero: bool = False) -> Decimal:
    if (
        not isinstance(value, str)
        or len(value) > 128
        or not PLAIN_DECIMAL.fullmatch(value)
    ):
        raise CoinbaseError("coinbase_invalid_decimal")
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or (not zero and result == 0):
            raise CoinbaseError("coinbase_invalid_decimal")
    except InvalidOperation:
        raise CoinbaseError("coinbase_invalid_decimal") from None
    return result


def _identity(value: Any) -> str:
    if not isinstance(value, str) or not IDENTITY.fullmatch(value):
        raise CoinbaseError("coinbase_invalid_identity")
    return value


def product_id(symbol: str) -> str:
    """Map a chart ticker to its exact Coinbase pair; preserve quote currency."""
    if not isinstance(symbol, str):
        raise CoinbaseError("coinbase_invalid_symbol")
    value = symbol.upper()
    if ":" in value:
        exchange, value = value.split(":", 1)
        if not re.fullmatch(r"[A-Z0-9_]+", exchange):
            raise CoinbaseError("coinbase_invalid_exchange_prefix")
    value = value.replace("/", "-")
    if "-" not in value:
        # Longest suffix first makes SOLUSDC unambiguously SOL-USDC.
        quote = next(
            (
                q
                for q in ("USDC", "USDT", "USD", "EUR", "GBP", "BTC", "ETH")
                if value.endswith(q)
            ),
            None,
        )
        if quote is None:
            raise CoinbaseError("coinbase_ambiguous_symbol")
        value = value[: -len(quote)] + "-" + quote
    if not PAIR.fullmatch(value):
        raise CoinbaseError("coinbase_invalid_symbol")
    base, quote = value.split("-")
    if base == quote:
        raise CoinbaseError("coinbase_invalid_symbol")
    return value


class CoinbaseOrders:
    """The daemon's explicit Coinbase transport. Construction places no order."""

    def __init__(
        self,
        command: str | None = None,
        *,
        call: Callable[[list[str]], dict[str, Any]] | None = None,
        timeout: float = 30,
    ):
        self.command = command or shutil.which("coinbase")
        self.call = call
        self.timeout = timeout

    def _invoke(self, args: list[str]) -> dict[str, Any]:
        try:
            if self.call is not None:
                result = self.call(args)
            else:
                if not self.command:
                    raise CoinbaseError("coinbase_cli_unavailable")
                # Disk-backed capture bounds in-memory output. Provider stderr
                # is discarded because it can contain account or auth details.
                with tempfile.TemporaryFile() as output:
                    process = subprocess.run(
                        [self.command, *args],
                        stdout=output,
                        stderr=subprocess.DEVNULL,
                        timeout=self.timeout,
                        check=False,
                    )
                    if process.returncode or output.tell() > MAX_OUTPUT:
                        raise CoinbaseError("coinbase_cli_failed")
                    output.seek(0)
                    result = json.load(output)
            if not isinstance(result, dict) or any(
                result.get(k) for k in ("error", "errorType", "errs")
            ):
                raise CoinbaseError("coinbase_invalid_response")
            return result
        except Exception:  # noqa: BLE001 - sanitize every external transport error
            raise CoinbaseError("coinbase_operation_failed") from None

    def balances(self, portfolio_id: str) -> list[dict[str, Any]]:
        portfolio_id = _identity(portfolio_id)
        accounts: list[dict[str, Any]] = []
        cursor = ""
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            args = ["balance", "limit==250", "portfolio_id==" + portfolio_id]
            if cursor:
                args.append("cursor==" + cursor)
            page = self._invoke(args)
            rows = page.get("accounts")
            if page.get("portfolio_id") != portfolio_id or not isinstance(rows, list):
                raise CoinbaseError("coinbase_invalid_balance_page")
            if any(not isinstance(row, dict) for row in rows):
                raise CoinbaseError("coinbase_invalid_balance_page")
            has_next = page.get("has_next")
            if (
                has_next is None
                and not page.get("cursor")
                and type(page.get("size")) is int
                and page["size"] == len(rows)
            ):
                has_next = False  # Official CLI omits false on the final page.
            if type(has_next) is not bool:
                raise CoinbaseError("coinbase_incomplete_balances")
            accounts.extend(rows)
            if not has_next:
                return accounts
            cursor = page.get("cursor")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise CoinbaseError("coinbase_balance_pagination_stalled")
            seen.add(cursor)
        raise CoinbaseError("coinbase_balance_page_limit")

    def plan(self, symbol: str, side: str, portfolio_id: str) -> dict[str, Any]:
        pair = product_id(symbol)
        portfolio_id = _identity(portfolio_id)
        if not isinstance(side, str) or side.upper() not in ("BUY", "SELL"):
            raise CoinbaseError("coinbase_invalid_side")
        side = side.upper()
        base, quote = pair.split("-")
        product = self._invoke(["products", "get", pair, "product_type==SPOT"])
        if (
            product.get("product_id") != pair
            or product.get("product_type") != "SPOT"
            or product.get("base_currency_id") != base
            or product.get("quote_currency_id") != quote
            or str(product.get("status", "")).lower() != "online"
        ):
            raise CoinbaseError("coinbase_spot_product_unavailable")
        currency = quote if side == "BUY" else base
        matches = [
            row
            for row in self.balances(portfolio_id)
            if row.get("currency") == currency
        ]
        if len(matches) != 1:
            raise CoinbaseError("coinbase_available_balance_unavailable")
        account = matches[0]
        available = account.get("available_balance")
        if (
            account.get("active") is not True
            or account.get("ready") is not True
            or not isinstance(available, dict)
            or available.get("currency") != currency
        ):
            raise CoinbaseError("coinbase_available_balance_unavailable")
        balance = _decimal(available.get("value"), zero=True)
        unit = "quote" if side == "BUY" else "base"
        increment = _decimal(product.get(unit + "_increment"))
        minimum = _decimal(product.get(unit + "_min_size"))
        maximum = _decimal(product.get(unit + "_max_size"))
        with localcontext() as context:
            context.prec = 256
            size = ((balance * Decimal("0.75")) // increment) * increment
        if minimum > maximum or not minimum <= size <= maximum:
            raise CoinbaseError("coinbase_size_outside_market_limits")
        return {
            "product_id": pair,
            "portfolio_id": portfolio_id,
            "side": side,
            "size_field": unit + "_size",
            "size": format(size, "f"),
            "available": format(balance, "f"),
            "available_currency": currency,
            "balance_percentage": "75",
            "product_type": "SPOT",
            "type": "market",
        }

    def submit(self, plan: dict[str, Any], client_order_id: str) -> dict[str, Any]:
        try:
            client_order_id = str(uuid.UUID(client_order_id))
        except (ValueError, TypeError, AttributeError):
            raise CoinbaseError("coinbase_invalid_client_order_id") from None
        pair = product_id(plan.get("product_id"))
        portfolio = _identity(plan.get("portfolio_id"))
        side = plan.get("side")
        field = "quote_size" if side == "BUY" else "base_size"
        if side not in ("BUY", "SELL") or plan.get("size_field") != field:
            raise CoinbaseError("coinbase_invalid_plan")
        _decimal(plan.get("size"))
        args = [
            "orders",
            "create",
            "product_id=" + pair,
            "side=" + side,
            "type=market",
            field + "=" + plan["size"],
            "product_type=SPOT",
            "portfolio_id=" + portfolio,
            "client_order_id=" + client_order_id,
        ]
        try:
            result = self._invoke(args)  # Exactly one write attempt.
            _identity(result.get("order_id"))
            if (
                result.get("product_id") != pair
                or result.get("side") != side
                or result.get("client_order_id", client_order_id) != client_order_id
            ):
                raise CoinbaseError("coinbase_order_identity_mismatch")
        except Exception:  # noqa: BLE001 - every failed write may have landed
            raise CoinbaseAmbiguous("coinbase_submission_unknown") from None
        return {key: result[key] for key in ORDER_FIELDS if key in result}

    def get(self, order_id: str) -> dict[str, Any]:
        result = self._invoke(
            ["orders", "get", _identity(order_id), "product_type==SPOT"]
        )
        if result.get("order_id") != order_id:
            raise CoinbaseError("coinbase_order_identity_mismatch")
        return {key: result[key] for key in ORDER_FIELDS if key in result}

    def find(
        self, client_order_id: str, product_id: str, portfolio_id: str | None = None
    ) -> dict[str, Any] | None:
        """Find only a provably matching caller ID; an empty result proves no absence.

        Some CLI versions omit client_order_id even from get. Those responses
        cannot resolve an interrupted submission and remain unknown.
        """
        _identity(client_order_id)
        if not PAIR.fullmatch(product_id):
            raise CoinbaseError("coinbase_invalid_product")
        cursor = ""
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            args = [
                "orders",
                "list",
                "product_type==SPOT",
                "product_ids==" + product_id,
                "limit==250",
            ]
            if portfolio_id is not None:
                args.append("portfolio_id==" + _identity(portfolio_id))
            if cursor:
                args.append("cursor==" + cursor)
            page = self._invoke(args)
            rows = page.get("orders")
            if not isinstance(rows, list):
                raise CoinbaseError("coinbase_invalid_order_page")
            for row in rows:
                if not isinstance(row, dict):
                    raise CoinbaseError("coinbase_invalid_order_page")
                order = row
                if row.get("client_order_id") is None:
                    order = self.get(_identity(row.get("order_id")))
                if order.get("client_order_id") == client_order_id:
                    if order.get("product_id") != product_id:
                        raise CoinbaseError("coinbase_order_identity_mismatch")
                    return {key: order[key] for key in ORDER_FIELDS if key in order}
            more = page.get("has_next")
            next_cursor = page.get("cursor")
            if more is False or (more is None and not next_cursor):
                return None
            if (
                more is not True
                or not isinstance(next_cursor, str)
                or not next_cursor
                or next_cursor in seen
            ):
                raise CoinbaseError("coinbase_order_pagination_stalled")
            seen.add(next_cursor)
            cursor = next_cursor
        raise CoinbaseError("coinbase_order_page_limit")
