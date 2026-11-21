"""Exercise the Volty journal-to-history accounting boundary with an inert venue."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from oracle.gum_orders import GumError
from oracle.gum_webhook_orders import VENUE, client_order_id
from oracle.tests.test_gum_orders import ACCOUNT, OWNER
from oracle.webhook_orders import database
from oracle.zec_volty import LivePolicy, VoltyVenue
from oracle.zec_volty_performance import performance_snapshot

NOW = 1_800_000_000


class VoltyPerformanceTests(unittest.TestCase):
    def setUp(self):
        state = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.inbox = state / "live.sqlite3"
        self.policy = LivePolicy(
            owner=OWNER, trading_account=ACCOUNT, subaccount_id=2, key_file=state / "never-read",
            allocation="50", allocation_basis="collateral", max_slippage_bps=10,
            max_order_notional_usdc="20",
        )
        self.venue = VoltyVenue(self.policy, self.inbox, call=self.call)
        self.venue.verify_binding()
        self.order_rows, self.entries, self.position_offsets = [], [], []

    def call(self, method, path, owner, body):
        self.assertEqual((method, owner, body), ("GET", OWNER, None))
        route = urlsplit(path)
        query = parse_qs(route.query)
        if route.path == "/tradingAccount":
            return {"exists": True, "accounts": [
                {"pubkey": ACCOUNT, "subaccountId": 2, "isolated": False, "market": None},
            ]}
        self.assertEqual(query["symbol"], ["ZEC"])
        offset, limit = int(query["offset"][0]), int(query["limit"][0])
        if route.path == f"/tradingAccount/{ACCOUNT}/orderHistory":
            return {"orders": self.order_rows[offset:offset + limit]}
        self.assertEqual(route.path, f"/tradingAccount/{ACCOUNT}/positionHistory")
        self.position_offsets.append(offset)
        return {"entries": self.entries[offset:offset + limit]}

    def fill(self, event_id, side, action, at, price, *, binding=None, status="complete"):
        retired = binding is not None
        binding = binding or self.venue.binding
        order_id = str(len(self.order_rows) + 1)
        client_id = client_order_id(binding, event_id, 0)
        identity = {"symbol": "ZEC", "owner": OWNER, "account_id": ACCOUNT, "subaccount_id": 2,
                    "side": side, "reduce_only": action == "close"}
        plan = {"action": action, "binding": binding, "quantity": "0.02", **identity}
        receipt = {**identity, "order_id": order_id, "client_order_id": client_id, "status": "filled",
                   "settled": True, "isolated": True, "filled_quantity": "0.02", "actual_fee_usdc": "0.01",
                   "transactions": [
                       {"type": "fill", "signature": f"fixture-{order_id}", "timestamp": at,
                        "size": "0.02", "fee": "0.01", "price": price},
                   ]}
        legs = [{"state": "filled", "client_order_id": client_id, "plan": plan, "receipt": receipt}]
        if status in {"expired", "refused"}:
            legs.append({"state": status, "receipt": None})
        with database(self.inbox) as db, db:
            db.execute(
                "INSERT INTO signals "
                "(event_id,digest,symbol,side,timestamp,status,mode,portfolio_id,plan) "
                "VALUES (?,'fixture','ZEC',?,?,?,'live',?,?)",
                (event_id, side, at, status, binding, json.dumps({"binding": binding, "venue": VENUE, "legs": legs})),
            )
            if retired:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS volty_retired_events (event_id TEXT PRIMARY KEY, binding TEXT NOT NULL)"
                )
                db.execute("INSERT INTO volty_retired_events VALUES (?,?)", (event_id, binding))
        self.order_rows.append({"symbol": "ZEC", "orderId": order_id, "clientOrderId": client_id, "filledSize": "0.02"})

    def trade(self, event, side, at, entry, exit_price, realized, funding, net, *, binding=None, status="complete"):
        close_at = at + 3
        self.fill(f"{event}:open", side, "open", at, entry, binding=binding)
        close_side = "sell" if side == "buy" else "buy"
        self.fill(f"{event}:close", close_side, "close", close_at, exit_price, binding=binding, status=status)
        self.entries.insert(0, {
            "symbol": "ZEC", "isolated": True, "closeReason": "trade", "side": "Bid" if side == "buy" else "Ask",
            "openedAt": at, "closedAt": close_at, "closedSize": "0.02", "realizedPnl": realized,
            "fees": "0.02", "funding": funding, "netPnl": net,
        })

    def test_signed_funding_and_net_wins_include_settled_retired_and_failed_reversals(self):
        retired = VoltyVenue(replace(self.policy, allocation="20"), self.inbox).binding
        self.trade("old", "buy", NOW - 80, "600", "610", "0.20", "-0.19", "-0.01",
                   binding=retired, status="expired")
        self.trade("new-short", "sell", NOW - 60, "650", "645", "0.10", "0.03", "0.11", status="refused")
        self.trade("even", "buy", NOW - 40, "645", "646", "0.02", "0", "0")
        self.fill("current", "buy", "open", NOW - 20, "660")
        durable = self.inbox.read_bytes()
        with patch("oracle.zec_volty_performance.PAGE_SIZE", 2):
            self.assertEqual(performance_snapshot(self.venue, now=NOW), {
                "schema": 1, "updated_at": NOW, "gross_pnl_usdc": 0.32, "net_pnl_usdc": 0.10,
                "closed_trades": 3, "profitable_trades": 1,
            })
        self.assertEqual(self.position_offsets, [0, 2])
        self.assertEqual(self.inbox.read_bytes(), durable)

    def test_refuses_partial_duplicate_or_unbalanced_venue_history(self):
        self.trade("trade", "buy", NOW - 10, "600", "610", "0.20", "0", "0.18")
        entry = self.entries[0]
        for entries, error in (
            ([], "volty_performance_incomplete_history"),
            ([entry, entry], "volty_performance_unmatched_position"),
            ([{**entry, "funding": "-0.19"}], "volty_performance_unmatched_position"),
            ([{**entry, "closedAt": entry["closedAt"] - 1}], "volty_performance_unmatched_position"),
        ):
            with self.subTest(error=error, entries=len(entries)):
                self.entries = entries
                with self.assertRaisesRegex(GumError, error):
                    performance_snapshot(self.venue, now=NOW)
        self.entries = [entry]
        with (
            patch("oracle.zec_volty_performance.PAGE_SIZE", 1),
            patch("oracle.zec_volty_performance.MAX_PAGES", 1),
            self.assertRaisesRegex(GumError, "volty_performance_incomplete_pagination"),
        ):
            performance_snapshot(self.venue, now=NOW)

    def test_open_position_is_not_a_realized_trade_and_extra_filled_order_refuses(self):
        self.fill("open", "sell", "open", NOW - 10, "600")
        self.assertEqual(performance_snapshot(self.venue, now=NOW), {
            "schema": 1, "updated_at": NOW, "gross_pnl_usdc": 0.0, "net_pnl_usdc": 0.0,
            "closed_trades": 0, "profitable_trades": 0,
        })
        self.order_rows.append({"symbol": "ZEC", "orderId": "999", "clientOrderId": "888", "filledSize": "0.02"})
        with self.assertRaisesRegex(GumError, "volty_performance_unverified_order_history"):
            performance_snapshot(self.venue, now=NOW)
