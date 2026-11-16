"""Backend for explicit TUI actions; the forward worker never calls this executor."""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import stat
import tempfile
import time
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from oracle_leverage.store import Store, default_home

VENUES = ("jupiter-cli-10x", "jupiter-sdk-1000x")
CONSOLE_ERRORS = (
    ValueError,
    RuntimeError,
    OSError,
    TypeError,
    ArithmeticError,
    ImportError,
    KeyError,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected RPC redirect")


def valid_signature(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[1-9A-HJ-NP-Za-km-z]{64,100}", value
    ):
        return False
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for char in value:
        number = number * 58 + alphabet.index(char)
    return (
        number > 0
        and len(value) - len(value.lstrip("1")) + (number.bit_length() + 7) // 8 == 64
    )


class Console:
    def __init__(self, home=None, *, cli=None, sdk=None, clock=time.time):
        self.store = Store(home or default_home())
        self.home = self.store.home
        self.clock = clock
        self._cli = cli
        self._sdk = sdk
        self._wallet_checked_at = float("-inf")
        self._wallet_identity = {}

    @property
    def cli(self):
        if self._cli is None:
            from oracle_leverage.cli import JupiterCLI

            self._cli = JupiterCLI()
        return self._cli

    @property
    def sdk(self):
        if self._sdk is None:
            from oracle_leverage.sdkbridge import SDKBridge

            self._sdk = SDKBridge()
        return self._sdk

    def config(self):
        path = self.home / "config.json"
        if not path.exists() and not path.is_symlink():
            return {"armed": False, "max_collateral_usd": 10, "sdk": {}}
        info = path.lstat()
        if (
            info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or not stat.S_ISREG(info.st_mode)
        ):
            raise ValueError("Trading config must be an owner-only regular file")
        cfg = json.loads(path.read_text())
        if not isinstance(cfg, dict) or type(cfg.get("armed", False)) is not bool:
            raise ValueError("Invalid private trading config")
        return cfg

    def set_venue_armed(self, venue, enabled, collateral_usd):
        """Explicit operator action; no order, signing, or intent mutation."""
        lock = None
        try:
            if venue not in VENUES or type(enabled) is not bool:
                raise ValueError("Invalid venue or arm state")
            amount = (
                self.request("BTC", venue, "long", collateral_usd)["collateral_usd"]
                if enabled
                else None
            )
            lock = self._lock()
            cfg = self.config()
            if "enabled_venues" in cfg:
                enabled_venues = cfg["enabled_venues"]
                if not isinstance(enabled_venues, list) or any(
                    v not in VENUES for v in enabled_venues
                ):
                    raise ValueError("Invalid enabled venues")
                enabled_venues = list(dict.fromkeys(enabled_venues))
            else:
                enabled_venues = list(VENUES) if cfg.get("armed") is True else []
                if (
                    cfg.get("sdk", {}).get("enabled") is not True
                    and VENUES[1] in enabled_venues
                ):
                    enabled_venues.remove(VENUES[1])
            if enabled:
                wallet = self.cli.wallet()
                address, name = wallet.get("address"), wallet.get("name")
                if (
                    not isinstance(address, str)
                    or not address
                    or not isinstance(name, str)
                    or not name
                ):
                    raise ValueError("Active CLI public wallet is unavailable")
                if enabled_venues and cfg.get("wallet_address") != address:
                    raise ValueError("Active CLI wallet differs from configured wallet")
                cfg["wallet_address"] = address
                cfg["wallet_name"] = name
                if venue not in enabled_venues:
                    enabled_venues.append(venue)
                caps = cfg.get("venue_collateral_caps", {})
                if not isinstance(caps, dict):
                    raise TypeError("Invalid venue collateral caps")
                cfg["venue_collateral_caps"] = {**caps, venue: amount}
                if venue == VENUES[1]:
                    sdk = cfg.get("sdk", {})
                    if not isinstance(sdk, dict):
                        raise ValueError("Invalid SDK configuration")
                    cfg["sdk"] = {**sdk, "enabled": True}
            elif venue in enabled_venues:
                enabled_venues.remove(venue)
            cfg["enabled_venues"] = enabled_venues
            cfg["armed"] = bool(enabled_venues)
            fd, temporary = tempfile.mkstemp(prefix=".config-", dir=self.home)
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump(cfg, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.home / "config.json")
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return {
                "status": "armed" if enabled else "disarmed",
                "venue": venue,
                "message": (
                    f"Wallet {cfg.get('wallet_address')} ({cfg.get('wallet_name')}); cap {amount} USD. No order sent."
                    if enabled
                    else "New submissions blocked for this venue; submitted transactions remain in progress."
                ),
            }
        except CONSOLE_ERRORS as exc:
            return {"status": "blocked", "message": str(exc)[:400]}
        finally:
            if lock:
                lock.close()

    @staticmethod
    def request(asset, venue, side, collateral_usd):
        if (
            asset not in ("ZEC", "BTC")
            or venue not in VENUES
            or side not in ("long", "short")
        ):
            raise ValueError("Unsupported asset, venue or side")
        try:
            amount = Decimal(str(collateral_usd))
        except InvalidOperation as exc:
            raise ValueError("Invalid collateral") from exc
        minimum = 10 if venue == VENUES[0] else 5
        if (
            not amount.is_finite()
            or amount < minimum
            or amount > 100000
            or amount.as_tuple().exponent < -6
        ):
            raise ValueError(
                f"Collateral must be finite, at least{minimum} and have at most6decimals"
            )
        return {
            "asset": asset,
            "venue": venue,
            "side": side,
            "collateral_usd": str(amount),
            "leverage": 10 if venue == VENUES[0] else 1000,
        }

    def snapshot(self):
        cfg = self.config()
        if cfg.get("armed") is True and cfg.get("wallet_address"):
            self.reconcile()
        heartbeat = self.store.meta("heartbeat", {})
        now = self.clock()
        selection = self.store.meta("selection", {})
        wallet = self.public_wallet(cfg)
        predictions = self.store.predictions()
        totals = self.store.performance()
        performance = {
            "settled": totals["n"],
            "open": totals["open"],
            "correct": totals["correct"],
            "hit_rate": totals["correct"] / totals["n"] if totals["n"] else None,
            "mean_net_bps": totals["mean_net_bps"],
            "by_asset": totals["by_asset"],
            "mode": "paper only;16bps cost scenario, no venue fills",
        }
        open_counts = {asset: 0 for asset in ("ZEC", "BTC")}
        for prediction in self.store.predictions("open"):
            if prediction.get("asset") in open_counts:
                open_counts[prediction["asset"]] += 1
        performance["by_asset"] = {}
        for asset in ("ZEC", "BTC"):
            row = totals["by_asset"].get(asset, {})
            n = row.get("n", 0)
            correct = row.get("correct", 0)
            performance["by_asset"][asset] = {
                "settled": n,
                "open": open_counts[asset],
                "correct": correct,
                "hit_rate": correct / n if n else None,
                "mean_net_bps": row.get("mean_net_bps"),
            }
        stale = now - heartbeat.get("at", 0) > 45
        service_status = heartbeat.get("status", "not-started")
        if service_status == "running" and stale:
            service_status = "stale"
        if service_status == "running" and any(
            v.get("error")
            for v in heartbeat.get("assets", {}).values()
            if isinstance(v, dict)
        ):
            service_status = "degraded"
        capabilities = [
            {
                "asset": "BTC",
                "venue": VENUES[0],
                "status": "available",
                "message": "Official CLI0.10.1;10x; explicit private arming required",
            },
            {
                "asset": "ZEC",
                "venue": VENUES[0],
                "status": "blocked",
                "message": "Standard Jupiter CLI supports BTC/SOL/ETH; no ZEC market",
            },
            *[
                {
                    "asset": a,
                    "venue": VENUES[1],
                    "status": "available",
                    "message": "Official 1000x service with SDK checks; JupUSD collateral; explicit private arming required",
                }
                for a in ("ZEC", "BTC")
            ],
        ]
        live_positions = self.store.meta("venue_positions", [])
        return {
            "status": "paper-forward-" + service_status,
            "updated_at": heartbeat.get("at"),
            "armed": cfg.get("armed", False),
            "enabled_venues": cfg.get(
                "enabled_venues",
                [
                    v
                    for v in VENUES
                    if cfg.get("armed") is True
                    and (v != VENUES[1] or cfg.get("sdk", {}).get("enabled") is True)
                ],
            ),
            "mtf_forward": self.store.meta("mtf_forward", {}),
            "wallet": wallet,
            "price_comparison": self.price_comparison(),
            "assets": capabilities,
            "strategies": [
                {**r, "shape": r.get("shape_group", "all")}
                for r in selection.get("rules", [])
            ],
            "performance": performance,
            "positions": live_positions,
            "events": [
                {
                    "id": p["id"],
                    "asset": p["asset"],
                    "interval_minutes": (p["target_end"] - p["target_start"]) // 60,
                    "direction": p["direction"],
                    "status": p["status"],
                    "target_end": p["target_end"],
                    "message": f"{p['asset']} {p['direction']} {p['status']} → {p['target_end']}",
                }
                for p in predictions[:30]
            ],
            "heartbeat": heartbeat,
            "intents": self.store.intents(),
            "message": (
                "Waiting for a newly observed matching setup"
                if not predictions
                else "Future-only paper ledger; historical and live venues differ"
            ),
            "source_errors": {
                asset: value.get("error")
                for asset, value in heartbeat.get("assets", {}).items()
                if isinstance(value, dict) and value.get("error")
            },
        }

    def public_wallet(self, cfg=None):
        """Display the same full public CLI identity used by both trading paths."""
        cfg = self.config() if cfg is None else cfg
        now = self.clock()
        if now - self._wallet_checked_at >= 15:
            try:
                identity = self.cli.wallet()
                self._wallet_identity = {
                    "address": identity["address"],
                    "name": identity["name"],
                    "status": "ready",
                }
            except CONSOLE_ERRORS:
                self._wallet_identity = {
                    "address": None,
                    "name": None,
                    "status": "unavailable",
                }
            self._wallet_checked_at = now
        wallet = {
            **self._wallet_identity,
            "checked_at": self._wallet_checked_at,
            "configured_address": cfg.get("wallet_address"),
            "armed": cfg.get("armed", False),
        }
        wallet["message"] = (
            "CLI public identity unavailable; no transaction wallet is inferred"
            if wallet["status"] != "ready"
            else "Active named Jupiter CLI wallet; both trading paths bind this identity again before submission"
        )
        if (
            wallet["address"]
            and wallet["configured_address"]
            and wallet["address"] != wallet["configured_address"]
        ):
            wallet["status"] = "mismatch"
            wallet["message"] = (
                "Active CLI and configured wallet differ; submission is blocked"
            )
        return wallet

    def price_comparison(self):
        """Recheck stream freshness at read time and compare synchronous USD prices."""
        data = self.store.meta("dual_quotes", {})
        if not isinstance(data, dict):
            data = {}
        now = self.clock()
        at = data.get("at")
        heartbeat_fresh = (
            type(at) in (int, float)
            and math.isfinite(at)
            and 0 <= now - at <= 2
            and data.get("status") != "stopped"
        )
        feeds = {}
        for source, limit in (("jupiter", 1), ("coinbase", 3)):
            feeds[source] = {}
            original = data.get("feeds", {}).get(source, {})
            for asset in ("BTC", "ZEC"):
                quote = original.get(asset, {}) if isinstance(original, dict) else {}
                if not isinstance(quote, dict):
                    quote = {}
                valid = all(
                    type(quote.get(k)) in (int, float)
                    and math.isfinite(quote[k])
                    and quote[k] > 0
                    for k in ("price", "exchange_at", "received_at")
                )
                fresh = (
                    valid
                    and heartbeat_fresh
                    and data.get("connected", {}).get(source) is True
                    and all(
                        0 <= now - quote[k] <= limit
                        for k in ("exchange_at", "received_at")
                    )
                )
                feeds[source][asset] = {**quote, "fresh": fresh}
        pairs = {}
        for asset in ("BTC", "ZEC"):
            jupiter, coinbase = feeds["jupiter"][asset], feeds["coinbase"][asset]
            skew = (
                abs(jupiter["exchange_at"] - coinbase["exchange_at"])
                if jupiter.get("fresh") and coinbase.get("fresh")
                else None
            )
            comparable = skew is not None and skew <= 1
            pairs[asset] = {
                "comparable": comparable,
                "timestamp_skew_seconds": skew,
                "basis_bps": (jupiter["price"] / coinbase["price"] - 1) * 10000
                if comparable
                else None,
                "difference_usd": jupiter["price"] - coinbase["price"]
                if comparable
                else None,
                "primary_1000x_source": "jupiter",
                "primary_1000x_price": jupiter.get("price")
                if jupiter.get("fresh")
                else None,
            }
        return {
            **data,
            "feeds": feeds,
            "pairs": pairs,
            "checked_at": now,
            "status": data.get("status", "not-started")
            if heartbeat_fresh
            else "stale"
            if data
            else "not-started",
            "message": "Jupiter oracle is the1000x display source; Coinbase synced-book midpoint is a comparison. Positive basis means Jupiter is higher. No feed substitution.",
        }

    def _signature_statuses(self, signatures, cfg):
        url = cfg.get("rpc_url", "https://api.mainnet-beta.solana.com")
        parsed = urlparse(url)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http"
            and parsed.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("RPC endpoint must use HTTPS")
        request = Request(
            url,
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [signatures, {"searchTransactionHistory": True}],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            body = response.read(65537)
            if len(body) > 65536 or response.status != 200:
                raise ValueError("RPC status response unavailable")
        result = json.loads(body).get("result", {}).get("value")
        if not isinstance(result, list) or len(result) != len(signatures):
            raise ValueError("RPC status response is incomplete")
        return result

    def reconcile(self):
        """Only reads venue/chain state. Unknown outcomes remain quarantined."""
        if self.clock() - self.store.meta("venue_reconciled_at", 0) < 15:
            return
        cfg = self.config()
        if cfg.get("armed") is not True or not cfg.get("wallet_address"):
            return
        try:
            wallet = self.cli.wallet()
            if wallet["address"] != cfg["wallet_address"]:
                raise ValueError("Active CLI wallet changed")
            self._read_positions(wallet["name"])
            if cfg.get("sdk", {}).get("enabled") is True:
                self._read_sdk_positions(wallet["address"])
            submitted = [
                i
                for i in self.store.unresolved_intents()
                if valid_signature(json.loads(i["response_json"]).get("signature"))
            ]
            signatures = [
                json.loads(i["response_json"])["signature"] for i in submitted
            ]
            if signatures:
                states = self._signature_statuses(signatures, cfg)
                for intent, state in zip(submitted, states, strict=True):
                    if state is not None and (
                        not isinstance(state, dict)
                        or "err" not in state
                        or "confirmationStatus" not in state
                        or (
                            state["err"] is not None
                            and not (
                                (isinstance(state["err"], str) and bool(state["err"]))
                                or (
                                    isinstance(state["err"], dict)
                                    and bool(state["err"])
                                )
                            )
                        )
                    ):
                        raise ValueError("RPC signature state is incomplete")
                    if state and state.get("confirmationStatus") in (
                        "confirmed",
                        "finalized",
                    ):
                        self.store.put_intent(
                            intent["id"],
                            intent["kind"],
                            "failed" if state["err"] is not None else "confirmed",
                            json.loads(intent["request_json"]),
                            json.loads(intent["response_json"]),
                        )
            self.store.put_meta("venue_error", None)
        except CONSOLE_ERRORS:
            self.store.put_meta(
                "venue_error",
                "Venue or chain reconciliation unavailable; new submissions remain guarded",
            )
        self.store.put_meta("venue_reconciled_at", self.clock())

    def preview(self, asset, venue, side, collateral_usd):
        try:
            request = self.request(asset, venue, side, collateral_usd)
            if venue == VENUES[0]:
                if asset != "BTC":
                    return {
                        "status": "blocked",
                        "message": "ZEC is unsupported by the standard Jupiter Perps CLI",
                    }
                wallet = self.cli.wallet()
                response = self.cli.preview(
                    asset, side, request["collateral_usd"], key_name=wallet["name"]
                )
                if self.cli.wallet() != wallet:
                    raise ValueError("CLI wallet changed while building the preview")
                request["wallet_address"], request["key_name"] = (
                    wallet["address"],
                    wallet["name"],
                )
                size = float(response.get("sizeUsd", math.nan))
                if (
                    not math.isfinite(size)
                    or not 0 < size <= float(request["collateral_usd"]) * 10.2
                ):
                    raise ValueError("CLI preview has no usable bounded position size")
                for field in ("entryPriceUsd", "liquidationPriceUsd", "openFeeUsd"):
                    value = float(response.get(field, math.nan))
                    if (
                        not math.isfinite(value)
                        or value < 0
                        or (field != "openFeeUsd" and value == 0)
                    ):
                        raise ValueError(
                            "CLI preview has unavailable price, liquidation or fee evidence"
                        )
                message = (
                    f"Unsigned CLI simulation: {asset} {side}, 10x, "
                    f"{request['collateral_usd']} USDC collateral, {size:g} USD position. "
                    f"Entry ${float(response['entryPriceUsd']):g}; liquidation ${float(response['liquidationPriceUsd']):g}; "
                    f"opening fee ${float(response['openFeeUsd']):g}. "
                    f"Wallet {wallet['address']}. Submit is a separate action."
                )
            else:
                wallet = self.cli.wallet()
                service_request = {
                    "action": "service-build-open",
                    "owner": wallet["address"],
                    "asset": asset,
                    "side": side,
                    "margin": str(int(Decimal(request["collateral_usd"]) * 1000000)),
                    "leverage": 1000,
                }
                try:
                    response = self.sdk.call(service_request)
                except CONSOLE_ERRORS as error:
                    if getattr(error, "code", None) not in (
                        "service_keeper_mismatch",
                        "service_keeper_or_pause_mismatch",
                        "unexpected_service_instruction",
                    ):
                        raise
                    response = self.sdk.call(
                        {**service_request, "action": "service-inspect-open"}
                    )
                if response.get("status") == "inspection":
                    checked = response.get("checked", {})
                    simulation = response.get("simulation", {})
                    if (
                        not isinstance(checked, dict)
                        or not isinstance(simulation, dict)
                        or any(
                            checked.get(key) != value
                            for key, value in {
                                "program": "yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA",
                                "owner": wallet["address"],
                                "asset": asset,
                                "side": side,
                                "margin": service_request["margin"],
                                "leverage": 1000,
                            }.items()
                        )
                        or simulation.get("status") != "passed"
                    ):
                        raise ValueError(
                            "SDK inspection does not match the requested trade"
                        )
                    if self.cli.wallet() != wallet:
                        raise ValueError(
                            "CLI wallet changed while inspecting the preview"
                        )
                    fees = response.get("fees", {})
                    message = (
                        f"Unsigned simulation passed: {asset} {side}, {request['collateral_usd']} JupUSD margin, {Decimal(request['collateral_usd']) * 1000} USD notional. "
                        f"Close fee {fees.get('closeFeePpm', 'unavailable')} ppm; win fee {fees.get('winFeePpm', 'unavailable')} ppm. "
                        "Inspection only: Submit is unavailable until the service keeper and current transaction layout can be verified for execution. No order was signed or submitted."
                    )
                    return {"status": "inspection", **request, "message": message}
                if response.get("status") in ("blocked", "error"):
                    return response
                checked = response.get("checked", {})
                if (
                    response.get("status") != "ready"
                    or checked.get("program")
                    != "yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA"
                    or checked.get("owner") != wallet["address"]
                    or checked.get("asset") != asset
                    or checked.get("side") != side
                    or checked.get("margin")
                    != str(int(Decimal(request["collateral_usd"]) * 1000000))
                    or checked.get("leverage") != 1000
                    or not response.get("build", {}).get("serializedTxBase64")
                ):
                    raise ValueError(
                        "SDK service transaction does not match the requested trade"
                    )
                if self.cli.wallet() != wallet:
                    raise ValueError("CLI wallet changed while building the preview")
                request["wallet_address"], request["key_name"] = (
                    wallet["address"],
                    wallet["name"],
                )
                fees = response.get("fees", {})
                message = (
                    f"Unsigned official 1000x build: {asset} {side}, {request['collateral_usd']} JupUSD margin, "
                    f"{Decimal(request['collateral_usd']) * 1000} USD notional. "
                    f"Close fee {fees.get('closeFeePpm', 'unavailable')} ppm of notional; "
                    f"win fee {fees.get('winFeePpm', 'unavailable')} ppm of profit. "
                    f"Owner {wallet['address']}; position {checked.get('position')}. "
                    "Entry price is set by the oracle at execution. SDK verified direction, margin, accounts and signers. Submit builds a fresh matching transaction, checks it, then signs and sends it to Jupiter's keeper."
                )
            identity = uuid.uuid4().hex
            self.store.put_intent(identity, "preview", "ready", request, response)
            return {
                "status": "ready",
                "preview_id": identity,
                **request,
                "request": request,
                "preview": response,
                "message": message,
            }
        except CONSOLE_ERRORS as exc:
            messages = {
                "jupiter_insufficient_funds": "The 10x CLI simulation requires sufficient USDC collateral and SOL network balance. No order was signed or submitted.",
                "service_400_insufficient_balance": "The 1000x build requires sufficient JupUSD collateral and SOL network balance. No order was signed or submitted.",
                "service_keeper_mismatch": "The unsigned 1000x build names a keeper signer that differs from the live on-chain configuration. Preview is blocked while the service transaction is verified; no order was signed or submitted.",
                "service_keeper_or_pause_mismatch": "The unsigned 1000x build failed the on-chain keeper or pause check. Preview is blocked; no order was signed or submitted.",
                "service_program_paused": "The 1000x on-chain program reports that trading is paused. Preview is blocked; no order was signed or submitted.",
                "service_owner_is_keeper": "The wallet matches the on-chain keeper, which is not allowed for this build. Preview is blocked; no order was signed or submitted.",
                "service_market_unavailable": "The 1000x market is paused, closed or close-only. Preview is blocked; no order was signed or submitted.",
                "unexpected_service_instruction": "The unsigned 1000x transaction contains an instruction the current verifier does not recognize. Preview is blocked; no order was signed or submitted.",
                "process_timeout": "The preview service timed out. No order was signed or submitted; retry after checking the connection.",
                "process_nonzero_exit": "The preview process failed without a recognized safe diagnostic. Check the private process receipt; no order was signed or submitted.",
                "invalid_process_json": "The preview service returned an invalid response. No order was signed or submitted.",
            }
            message = messages.get(getattr(exc, "code", None), str(exc)[:400])
            return {"status": "error", "message": message}

    def _lock(self):
        lock = (self.home / "execution.lock").open("a")
        os.chmod(self.home / "execution.lock", 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise ValueError("Another explicit trading operation is running") from None
        return lock

    def _read_positions(self, key_name):
        result = self.cli.positions(key_name=key_name)
        if isinstance(result, dict) and "positions" not in result:
            raise ValueError("Venue positions field is unavailable")
        rows = result.get("positions", []) if isinstance(result, dict) else result
        if not isinstance(rows, list) or any(
            not isinstance(r, dict) or not r.get("positionPubkey") for r in rows
        ):
            raise ValueError("Venue position reconciliation is unavailable")
        sdk_rows = [
            r
            for r in self.store.meta("venue_positions", [])
            if r.get("venue") == VENUES[1]
        ]
        self.store.put_meta(
            "venue_positions",
            sdk_rows
            + [
                {
                    **r,
                    "id": r.get("positionPubkey"),
                    "venue": VENUES[0],
                    "status": "open",
                }
                for r in rows
            ],
        )
        return rows

    def _read_sdk_positions(self, owner):
        result = self.sdk.call({"action": "service-positions", "owner": owner})
        rows = result.get("positions")
        if (
            result.get("status") != "ready"
            or not isinstance(rows, list)
            or any(
                not isinstance(r, dict)
                or r.get("owner") != owner
                or not r.get("address")
                for r in rows
            )
        ):
            raise ValueError("1000x venue positions are unavailable")
        cli_rows = [
            r
            for r in self.store.meta("venue_positions", [])
            if r.get("venue") == VENUES[0]
        ]
        self.store.put_meta(
            "venue_positions",
            cli_rows
            + [
                {
                    **r,
                    "id": "1000x:" + r["address"],
                    "venue": VENUES[1],
                    "status": "open",
                    "side": "long" if r["isLong"] else "short",
                    "sizeUsd": str(Decimal(r["notional"]) / 1000000),
                }
                for r in rows
            ],
        )
        self.store.put_meta(
            "sdk_profit_queue",
            {"queued": result.get("queued"), "claims": result.get("claims", [])},
        )
        return rows

    def _submit_sdk(self, identity, kind, request, preview, wallet):
        """Sign checked bytes, journal their signature, then transmit exactly once."""
        signed = self.cli.sign_transaction(
            preview["build"]["serializedTxBase64"], key_name=wallet["name"]
        )
        if self.cli.wallet() != wallet:
            raise ValueError("Active CLI wallet changed before transmission")
        payload = {
            "owner": wallet["address"],
            "preview": preview,
            "serializedTxBase64": signed["signedTransaction"],
        }
        verified = self.sdk.call({**payload, "action": "service-signed"})
        signature = verified.get("signature")
        if verified.get("status") != "ready" or not valid_signature(signature):
            raise ValueError("SDK rejected the signed transaction")
        # Store the owner signature before the keeper can receive anything.
        evidence = {"signature": signature, "venue": VENUES[1]}
        self.store.put_intent(identity, kind, "submitting", request, evidence)
        try:
            response = self.sdk.call({**payload, "action": "service-execute"})
            if response.get("signature") != signature or response.get("status") not in (
                "submitted",
                "failed",
            ):
                raise ValueError("1000x keeper response is incomplete")
        except CONSOLE_ERRORS:
            self.store.put_intent(identity, kind, "unknown", request, evidence)
            return {
                "status": "unknown",
                "signature": signature,
                "message": "Keeper outcome requires chain/venue reconciliation; no automatic retry",
            }
        self.store.put_intent(identity, kind, response["status"], request, response)
        return {
            **response,
            "message": "Keeper accepted the signed request; chain and venue reconciliation determine the final outcome"
            if response["status"] == "submitted"
            else "Keeper reported execution failed; inspect the recorded request",
        }

    def _reconcile_before_submit(self, key_name):
        self.reconcile()
        unresolved = self.store.unresolved_intents()
        if unresolved:
            raise ValueError(
                "Prior submission needs venue/chain reconciliation; automatic resubmission is blocked"
            )
        return self._read_positions(key_name)

    def execute(self, preview_id):
        lock = None
        try:
            lock = self._lock()
            intent = self.store.intent(preview_id)
            if not intent or intent["kind"] != "preview" or intent["status"] != "ready":
                raise ValueError("Preview is missing, used or not ready")
            if self.clock() - intent["created_at"] > 30:
                raise ValueError("Preview expired; request a fresh preview")
            request = json.loads(intent["request_json"])
            cfg = self.config()
            if cfg.get("armed") is not True:
                raise ValueError(
                    "Trading is disarmed; the live-data forward test is paper only"
                )
            if "enabled_venues" in cfg and (
                not isinstance(cfg["enabled_venues"], list)
                or request["venue"] not in cfg["enabled_venues"]
            ):
                raise ValueError("Trading is disarmed for the selected venue")
            wallet = self.cli.wallet()
            if (
                not cfg.get("wallet_address")
                or wallet["address"] != cfg["wallet_address"]
                or wallet["address"] != request.get("wallet_address")
                or wallet["name"] != request.get("key_name")
            ):
                raise ValueError(
                    "Active CLI wallet differs from the explicit configured/preview wallet"
                )
            caps = cfg.get("venue_collateral_caps", {})
            if not isinstance(caps, dict):
                raise TypeError("Invalid venue collateral caps")
            cap = Decimal(
                str(caps.get(request["venue"], cfg.get("max_collateral_usd", "0")))
            )
            if (
                not cap.is_finite()
                or cap <= 0
                or Decimal(request["collateral_usd"]) > cap
            ):
                raise ValueError("Collateral exceeds the private configured cap")
            self._reconcile_before_submit(wallet["name"])
            if request["venue"] == VENUES[1]:
                if cfg.get("sdk", {}).get("enabled") is not True:
                    raise ValueError(
                        "1000x trading requires sdk.enabled in the private armed configuration"
                    )
                self._read_sdk_positions(wallet["address"])
                # The service's execution window starts at build time. Refresh
                # the same economic intent after the explicit Submit action.
                preview = self.sdk.call(
                    {
                        "action": "service-build-open",
                        "owner": wallet["address"],
                        "asset": request["asset"],
                        "side": request["side"],
                        "leverage": 1000,
                        "margin": str(
                            int(Decimal(request["collateral_usd"]) * 1000000)
                        ),
                    }
                )
                checked = preview.get("checked", {})
                if preview.get("status") != "ready" or any(
                    checked.get(k) != v
                    for k, v in {
                        "owner": wallet["address"],
                        "asset": request["asset"],
                        "side": request["side"],
                        "leverage": 1000,
                        "margin": str(
                            int(Decimal(request["collateral_usd"]) * 1000000)
                        ),
                    }.items()
                ):
                    raise ValueError(
                        "Fresh SDK build differs from the reviewed trade intent"
                    )
                return self._submit_sdk(preview_id, "preview", request, preview, wallet)
            self.store.put_intent(preview_id, "preview", "submitting", request, {})
            try:
                response = self.cli.execute(
                    request["asset"],
                    request["side"],
                    request["collateral_usd"],
                    key_name=request["key_name"],
                )
                signature = response.get("signature") or response.get("txid")
                if not valid_signature(signature):
                    raise RuntimeError(
                        "CLI returned no transaction signature; outcome is unknown"
                    )
            except CONSOLE_ERRORS as exc:
                self.store.put_intent(
                    preview_id,
                    "preview",
                    "unknown",
                    request,
                    {"message": str(exc)[:400]},
                )
                return {
                    "status": "unknown",
                    "message": "Submission outcome needs reconciliation; never automatically retry",
                    "preview_id": preview_id,
                }
            self.store.put_intent(
                preview_id, "preview", "submitted", request, {"signature": signature}
            )
            return {
                "status": "submitted",
                "message": "Submitted; final chain confirmation is not yet established",
                "signature": signature,
            }
        except CONSOLE_ERRORS as exc:
            return {"status": "blocked", "message": str(exc)[:400]}
        finally:
            if lock:
                lock.close()

    def close(self, position_id):
        lock = None
        try:
            lock = self._lock()
            if self.config().get("armed") is not True:
                raise ValueError("Trading is disarmed")
            wallet = self.cli.wallet()
            if wallet["address"] != self.config().get("wallet_address"):
                raise ValueError(
                    "Active CLI wallet differs from the explicit configured wallet"
                )
            if position_id.startswith("1000x:"):
                if self.config().get("sdk", {}).get("enabled") is not True:
                    raise ValueError(
                        "1000x trading is disabled in the private configuration"
                    )
                self._reconcile_before_submit(wallet["name"])
                address = position_id.removeprefix("1000x:")
                rows = self._read_sdk_positions(wallet["address"])
                position = next((r for r in rows if r["address"] == address), None)
                if not position:
                    raise ValueError("1000x position is absent from the current wallet")
                preview = self.sdk.call(
                    {
                        "action": "service-build-close",
                        "owner": wallet["address"],
                        "asset": position["asset"],
                        "position": address,
                    }
                )
                if preview.get("status") != "ready":
                    raise ValueError("1000x close preview is unavailable")
                request = {
                    "position_id": position_id,
                    "venue": VENUES[1],
                    "wallet_address": wallet["address"],
                }
                return self._submit_sdk(
                    uuid.uuid4().hex, "close", request, preview, wallet
                )
            rows = self._reconcile_before_submit(wallet["name"])
            if not any(r.get("positionPubkey") == position_id for r in rows):
                raise ValueError(
                    "Position is not present in the current CLI wallet's venue response"
                )
            identity = uuid.uuid4().hex
            request = {"position_id": position_id, "venue": VENUES[0]}
            self.store.put_intent(identity, "close", "submitting", request, {})
            try:
                response = self.cli.close(position_id, key_name=wallet["name"])
                signature = response.get("signature") or response.get("txid")
                if not valid_signature(signature):
                    raise RuntimeError("Missing close signature")
            except CONSOLE_ERRORS:
                self.store.put_intent(identity, "close", "unknown", request, {})
                return {
                    "status": "unknown",
                    "message": "Close outcome needs reconciliation; never automatically retry",
                }
            self.store.put_intent(
                identity, "close", "submitted", request, {"signature": signature}
            )
            return {
                "status": "submitted",
                "signature": signature,
                "message": "Close submitted; confirm against chain and venue",
            }
        except CONSOLE_ERRORS as exc:
            return {"status": "blocked", "message": str(exc)[:400]}
        finally:
            if lock:
                lock.close()
