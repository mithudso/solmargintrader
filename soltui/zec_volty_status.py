"""Read the local Volty owner's public status snapshot without taking control."""

import json
import os
import re
import stat
import time
from decimal import Decimal
from pathlib import Path

_MAX_BYTES = 256 * 1024
_MAX_ORDERS = 16
_MAX_FILLS = 32
_MAX_ACTIVITY = 6
_WINDOW_SECONDS = 300
_LEARNING_HORIZONS = (60, 300, 600, 900, 1200, 3600)
_MODES = {"observe", "live"}
_STATES = {"watching", "armed", "paused", "data-unavailable", "checking", "blocked", "stopped"}
_ORDER_STATES = {"submitting", "acknowledged", "pending", "filled", "cancelled", "refused", "unknown"}
_SIDES = {"buy", "sell"}
_OUTCOMES = {
    "already_held", "cancelled", "complete", "evaluating", "expired", "owner_preflight_refused",
    "pending", "preceding_order_unresolved", "refused", "unknown",
}
_MAX_TIMESTAMP = 253402300799


def _member(value, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError
    return value


def _identifier(value, pattern):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError
    return value


def _timestamp(value, latest):
    if type(value) not in (float, int) or not 0 < value <= min(_MAX_TIMESTAMP, latest):
        raise ValueError
    return value


def _price(value):
    if type(value) not in (float, int) or not 0 < value <= 1e12:
        raise ValueError
    return value


def _quantity(value, *, zero=False):
    text = _identifier(value, r"[0-9]{1,18}(?:\.[0-9]{1,18})?")
    if not zero and not Decimal(text):
        raise ValueError
    return text


def _signal(signal, latest):
    return {
        "event_id": _identifier(signal["event_id"], r"[A-Za-z0-9_.:-]{1,96}"),
        "side": _member(signal["side"], _SIDES),
        "at": _timestamp(signal["at"], latest),
        "mark": _price(signal["mark"]),
        "upper": _price(signal["upper"]),
        "lower": _price(signal["lower"]),
    }


def _fill(fill, latest):
    return {
        "signature": _identifier(fill["signature"], r"[!-~]{1,128}"),
        "price": _quantity(fill["price"]),
        "size": _quantity(fill["size"]),
        "fee": _quantity(fill["fee"], zero=True),
        "timestamp": _timestamp(fill["timestamp"], latest),
    }


def _order(order, observed_at):
    requested = _quantity(order["requested_quantity"])
    quantity = order["filled_quantity"]
    filled = None if quantity is None else _quantity(quantity, zero=True)
    if filled is not None and Decimal(filled) > Decimal(requested):
        raise ValueError
    order_id = order["order_id"]
    order_id = None if order_id is None else _identifier(order_id, r"[0-9]{1,32}")
    fills = order["fills"]
    state = _member(order["state"], _ORDER_STATES)
    if not isinstance(fills, list) or (fills and (order_id is None or not filled or not Decimal(filled))):
        raise ValueError
    if state == "filled" and (not fills or Decimal(filled) != Decimal(requested)):
        raise ValueError
    leg = _member(order["leg"], {"open", "close"})
    settling = (
        order.get("settlement_pending") is True and leg == "close" and state == "pending"
        and bool(fills) and Decimal(filled) == Decimal(requested)
    )
    return {
        "event_id": _identifier(order["event_id"], r"[A-Za-z0-9_.:-]{1,96}"),
        "client_order_id": _identifier(order["client_order_id"], r"[1-9][0-9]{0,19}"),
        "side": _member(order["side"], _SIDES),
        "leg": leg,
        "state": state,
        "order_id": order_id,
        "requested_quantity": requested,
        "filled_quantity": filled,
        "updated_at": _timestamp(order["updated_at"], observed_at + 5),
        # GUM accepts venue clocks up to 30 seconds ahead of the host.
        "fills": [_fill(fill, observed_at + 30) for fill in fills[:_MAX_FILLS]],
        **({"settlement_pending": True} if settling else {}),
    }


def _telemetry(row, updated_at):
    if not isinstance(row, dict):
        raise ValueError
    market = row["market"]
    if market is not None:
        started = _timestamp(market["window_start"], updated_at)
        mark_at = _timestamp(market["mark_at"], updated_at)
        lower, upper = _price(market["lower"]), _price(market["upper"])
        if started % _WINDOW_SECONDS or not started <= mark_at < started + _WINDOW_SECONDS or lower >= upper:
            raise ValueError
        market = {"window_start": started, "mark_at": mark_at, "mark": _price(market["mark"]),
                  "lower": lower, "upper": upper}
    activity = row["activity"]
    if activity is not None:
        if not isinstance(activity, list):
            raise ValueError
        activity = [{"at": _timestamp(event["at"], updated_at + 5), "side": _member(event["side"], _SIDES),
                     "mark": _price(event["mark"]), "outcome": _member(event["outcome"], _OUTCOMES)}
                    for event in activity[:_MAX_ACTIVITY]]
    capture = row.get("capture")
    return {"market": market, "activity": activity,
            **({"capture": capture} if capture in ("waiting", "recording", "unavailable") else {})}


def _bounded_json(path):
    # The writer atomically replaces the file. Read only the inode opened here.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
            raise ValueError
        data = stream.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise ValueError
    return json.loads(data)


def _learning(path):
    try:
        row = _bounded_json(path)
        if type(row["schema"]) is not int or row["schema"] != 1 or row["mode"] != "shadow":
            raise ValueError
        state = _member(row["state"], {"waiting", "warming", "learning", "stale", "unavailable"})
        updated_at = _timestamp(row["updated_at"], time.time() + 5)
        ticks = row["ticks"]
        if type(ticks) is not int or not 0 <= ticks <= 10**12:
            raise ValueError
        last = _timestamp(row["last_tick_at"], updated_at) if ticks else None
        horizons = row["horizons"]
        if not isinstance(horizons, list) or len(horizons) != (len(_LEARNING_HORIZONS) if ticks else 0):
            raise ValueError
        summary = []
        for seconds, horizon in zip(_LEARNING_HORIZONS, horizons):
            if horizon["seconds"] != seconds:
                raise ValueError
            counts = {key: horizon[key] for key in ("trained", "pending", "expired", "capacity_drops")}
            if any(type(value) is not int or not 0 <= value <= ticks for value in counts.values()):
                raise ValueError
            scores = {key: horizon[key] for key in ("candidate_brier", "frequency_brier")}
            if counts["trained"]:
                if any(type(value) not in (int, float) or not 0 <= value <= 2 for value in scores.values()):
                    raise ValueError
            elif any(value is not None for value in scores.values()):
                raise ValueError
            summary.append({"seconds": seconds, **counts, **scores})
        return {"mode": "shadow", "state": state, "updated_at": updated_at,
                "last_tick_at": last, "ticks": ticks, "horizons": summary}
    except (OSError, KeyError, TypeError, ValueError, RecursionError):
        return None


def read_status():
    # The test/profile config override keeps the native bridge isolated from the owner.
    config = Path(os.environ.get("SOLTUI_CONFIG_DIR") or Path.home() / ".soltui")
    path = config / "zec-volty" / "status.json"
    try:
        row = _bounded_json(path)
        if not isinstance(row, dict) or type(row.get("schema")) is not int or row["schema"] != 1:
            return None
        mode = _member(row["mode"], _MODES)
        state = _member(row["state"], _STATES)
        updated_at = _timestamp(row["updated_at"], time.time() + 5)
        orders = row["orders"]
        if not isinstance(orders, list):
            return None
        signal = row["signal"]
        result = {
            "schema": 1,
            "mode": mode,
            "state": state,
            "updated_at": updated_at,
            "signal": None if signal is None else _signal(signal, updated_at + 5),
            "orders": [_order(order, updated_at) for order in orders[:_MAX_ORDERS]],
        }
        if "telemetry" in row:
            try:
                result["telemetry"] = _telemetry(row["telemetry"], updated_at)
            except (KeyError, TypeError, ValueError):
                # An unsupported optional extension must not hide valid receipts.
                pass
        learner = _learning(path.with_name("learning-status.json"))
        if learner is not None:
            result["learning"] = learner
        return result
    except (OSError, KeyError, TypeError, ValueError, RecursionError):
        return None
