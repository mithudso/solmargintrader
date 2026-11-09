"""Explain a saved current call without substituting a new quote or future winners."""
from __future__ import annotations

import hashlib
import json
import math
import time
from contextlib import closing

import numpy as np
from backtester.core import indicators

from . import config, forwardtest, live_score, live_tools


def _rule(member):
    name, p = member.get("name"), member.get("params", {})
    if name == "ma_crossover":
        return f"Compare trailing fast SMA({p.get('fast', 20)}) with slow SMA({p.get('slow', 50)}); long above, otherwise flat or the explicitly enabled short branch."
    if name == "sma_regime":
        return f"Compare close with trailing SMA({p.get('window', 200)}); long above, otherwise flat."
    if name == "rsi":
        return f"Wilder RSI({p.get('period', 14)}): enter below {p.get('oversold', 30)}, hold until RSI exceeds {p.get('exit_level', 50)}. The stored vote includes holding state."
    if name == "buy_and_hold":
        return "Always emits long after warm-up; its eligible current vote still needs the accuracy, sample and expiry floors."
    return f"Saved strategy {name}, parameters {json.dumps(p, sort_keys=True)}. Exact indicator/state diagnostics were not recorded with this call."


def _chart(db, asset, call):
    members = call["members"]
    exact = call["recorded_signal_basis"].get("features_available", False)
    periods = []
    if exact and len(members) == 1:
        member, p = members[0], members[0].get("params", {})
        periods = [int(p.get("fast", 20)), int(p.get("slow", 50))] if member["name"] == "ma_crossover" else [int(p.get("window", 200))]
    count = min(900, 300 + max(periods, default=0))
    rows = db.execute("SELECT ts,open,high,low,close,volume FROM candle WHERE asset=? AND ts<=? ORDER BY ts DESC LIMIT ?",
                      (asset, call["bar"], count)).fetchall()[::-1]
    rows = [r for r in rows if all(isinstance(v, (int, float)) and math.isfinite(v) for v in r)
            and min(r[1:5]) > 0 and r[2] >= max(r[1], r[4]) and r[3] <= min(r[1], r[4]) and r[5] >= 0]
    candles = [dict(zip(("time", "open", "high", "low", "close", "volume"), row)) for row in rows[-300:]]
    series = []
    for period in dict.fromkeys(periods):
        points = []
        for index in range(period - 1, len(rows)):
            window = rows[index - period + 1:index + 1]
            if candles and rows[index][0] >= candles[0]["time"] and all(b[0] - a[0] == 60 for a, b in zip(window, window[1:])):
                points.append({"time": rows[index][0], "value": float(indicators.sma(np.asarray([r[4] for r in window]), period))})
        if points:
            series.append({"name": f"SMA({period})", "type": "line", "pane": "price", "data": points})
    direction = call["direction"]
    marker = {"time": call["bar"], "direction": direction, "text": f"Saved {direction} · {call['horizon_minutes']}m",
              "issued_at": call["issued_at"], "expires_at": call["expires_at"], "trial_id": call["trial_id"]}
    origin_present = any(c["time"] == call["bar"] for c in candles)
    missing = [] if series else [call["recorded_signal_basis"]["reason"]]
    if not origin_present:
        missing.append("The recorded origin candle is unavailable; no marker is placed on a guessed candle.")
    return {"candles": candles, "series": series, "markers": [marker] if origin_present else [],
            "source": "Retained closed Coinbase 1m candles, strictly at or before the saved call's origin bar; gaps remain gaps.",
            "proof": {"trial_id": call["trial_id"], "bar": call["bar"], "input_sha256": call["recorded_signal_basis"].get("input_sha256"),
                      "origin_indicator_verified": exact},
            "missing": missing,
            "note": "SMA series use the backend indicator math on retained trailing windows. The origin value is verified against the saved call; earlier chart points are reconstructions, not logged indicator readings."}


def explain(asset, label, *, now=None, min_accuracy=60., min_resolved=20):
    now = time.time() if now is None else now
    if not isinstance(label, str) or not label or len(label) > 256:
        raise ValueError("Choose one saved strategy label")
    path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    base = {"asset": asset, "label": label, "observed_at": now, "available": False, "calls": [],
            "eligible_horizons": [], "chart_suggestions": [], "message": "No saved call for this strategy."}
    if not path.exists():
        return base
    with closing(live_tools.connect_readonly(path, budget=.8)) as db:
        rows = db.execute("""
            WITH current AS (
                SELECT t.id,t.mode,t.minutes,t.cost,t.execution,c.bar,c.issued,c.start,c.finish,c.prediction,c.guesses,
                       row_number() OVER(PARTITION BY t.minutes ORDER BY c.issued DESC,c.bar DESC,t.id DESC) AS chosen
                FROM trial t JOIN call c ON c.trial=t.id
                WHERE t.asset=? AND t.label=? AND c.bar=(SELECT max(last.bar) FROM call last WHERE last.trial=t.id)
            ) SELECT id,mode,minutes,cost,execution,bar,issued,start,finish,prediction,guesses FROM current WHERE chosen=1 ORDER BY minutes
        """, (asset, label)).fetchall()
        if not rows:
            return base
        display = {"label": label}
        calls = []
        total, hits = 0, 0
        plan = forwardtest.load_session()
        seed = next((t.get("members") for t in (plan or {}).get("trials", []) if t.get("label") == label), None)
        for key, mode, horizon, cost, execution_raw, bar, issued, start, finish, direction, guesses in rows:
            count, correct = db.execute("SELECT count(outcome),coalesce(sum(outcome=prediction),0) FROM call WHERE trial=?", (key,)).fetchone()
            total += count
            hits += correct
            display.update({f"pred_{horizon}m": {1: "UP", -1: "DOWN", 0: "FLAT"}.get(direction, "-"),
                f"acc_{horizon}m": round(100 * correct / count, 1) if count else None, f"resolved_{horizon}m": count,
                f"issued_{horizon}m": issued, f"expires_{horizon}m": finish})
            try:
                raw = json.loads(guesses)
                members = raw[0][0] if raw and isinstance(raw[0], list) else []
                execution = json.loads(execution_raw) if execution_raw else None
            except (ValueError, TypeError, IndexError):
                members, execution = [], None
            contract = False
            if seed:
                identity = [forwardtest.revision(), asset, label, horizon, cost, mode, seed]
                if execution:
                    identity.append(execution)
                contract = hashlib.sha256(forwardtest._json(identity).encode()).hexdigest() == key
            last = db.execute("SELECT ts,open,high,low,close,volume FROM candle WHERE asset=? AND ts=?", (asset, bar)).fetchone()
            basis = {"available": bool(last), "source": "retained immutable closed Coinbase 1m candle", "bar": bar,
                     "candle": dict(zip(("ts", "open", "high", "low", "close", "volume"), last)) if last else None,
                     "contract_verified": contract, "features": [], "features_available": False,
                     "reason": "The call did not fingerprint its complete original input membership/replay state. Stateful indicator values cannot be asserted as recorded."}
            if contract and len(members) == 1 and members[0].get("name") in ("ma_crossover", "sma_regime"):
                member = members[0]
                p = member.get("params", {})
                required = int(p.get("slow", 50)) if member["name"] == "ma_crossover" else int(p.get("window", 200))
                if 1 <= required <= forwardtest.HISTORY:
                    retained = db.execute("SELECT ts,close FROM candle WHERE asset=? AND ts<=? ORDER BY ts DESC LIMIT ?", (asset, bar, required)).fetchall()[::-1]
                    if len(retained) == required and retained[-1][0] == bar and all(b[0] - a[0] == 60 for a, b in zip(retained, retained[1:])):
                        prices = np.asarray([r[1] for r in retained], dtype=float)
                        if np.all(np.isfinite(prices)) and np.all(prices > 0):
                            slow = float(np.mean(prices))
                            fast = float(np.mean(prices[-int(p.get("fast", 20)):])) if member["name"] == "ma_crossover" else float(prices[-1])
                            allow_short = member["name"] == "ma_crossover" and bool((execution or {}).get("allow_short") or p.get("short_when_below"))
                            reproduced = 1 if fast > slow else -1 if allow_short else 0
                            if reproduced == direction:
                                # A non-null call under this verified contract
                                # implies more than warmup consecutive bars.
                                # These stateless trailing windows therefore
                                # belonged to its original contiguous tail.
                                basis.update(features_available=True, features=[{"name": "fast_sma" if member["name"] == "ma_crossover" else "close", "value": fast},
                                    {"name": "slow_sma" if member["name"] == "ma_crossover" else "sma", "period": required, "value": slow}],
                                    reason="Verified current-code trial identity, required contiguous immutable trailing window, and reproduced saved direction.",
                                    input_sha256=hashlib.sha256(forwardtest._json(retained).encode()).hexdigest())
            calls.append({"trial_id": key, "horizon_minutes": horizon, "issued_at": issued, "expires_at": finish,
                          "age_seconds": max(0., now - issued), "origin_candle_closed_at": bar + 60,
                          "bar": bar, "start": start, "direction": {1: "UP", -1: "DOWN", 0: "FLAT"}.get(direction),
                          "accuracy": round(100 * correct / count, 1) if count else None, "resolved": count, "hits": correct,
                          "members": members, "mode": mode, "execution": execution, "cost_bps": cost,
                          "rule": " ".join(_rule(m) for m in members), "recorded_signal_basis": basis})
        display.update(accuracy=round(100 * hits / total, 1) if total else 0., resolved=total)
        for call in calls:
            h = call["horizon_minutes"]
            single = {**display}
            for other in live_score.HORIZONS:
                if other != h:
                    single[f"expires_{other}m"] = None
            eligible = live_score.aggregate_predictions([single], now=now, min_accuracy=min_accuracy, min_resolved=min_resolved)["available"]
            call["eligible"] = eligible
            call["exclusion_reason"] = "" if eligible else "Expired or unavailable call, or record/horizon accuracy or sample floor not met."
            if eligible:
                base["eligible_horizons"].append(h)
        suggested = {}
        for call in calls:
            for member in call["members"]:
                suggested[forwardtest._json(member)] = {"strategy": member.get("name"), "params": member.get("params", {}),
                    "source": "saved call specification", "horizon_minutes": call["horizon_minutes"]}
        chosen = max([c for c in calls if c["eligible"]] or calls, key=lambda c: c["issued_at"])
        return {**base, "available": True, "calls": calls, "chart_suggestions": list(suggested.values())[:8], "chart": _chart(db, asset, chosen),
                "message": "Saved forecast and literal strategy rule; current quotes do not explain a historical call.",
                "voting_policy": {"min_accuracy": min_accuracy, "min_resolved": min_resolved}}
