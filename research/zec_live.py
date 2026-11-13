"""Read-only live Oracle hypotheses for the frozen profitable ZEC study rows.

Quotes follow the existing recorder. Completed trade OHLCV comes from public
Coinbase candles, never from invented snapshot volume. No orders or services.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import sys
import threading
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np
import pandas as pd

from backtester.core.strategies import build
from backtester.core.zec_ensemble import spec_id
from oracle.feeds import FeedUnavailable, RecorderFeed
from research import zec_granular as granular
from research.shape_study import detect_shapes
from research.zec_cycles import Spectrum
from research.zec_expanded import BLOCK, MODES, TRAIN, gate_for

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "research/zec-expanded-20261113.llms"
CSV_HASH = "1ec8410c4f465de50d71d792c1c3fba0af6085dd1656f76dfce14f396d7b24ed"
PLAN_HASH = "cc802c846b8541442b29f0804781bf82aa1a7443551b74b827a9b1b741e7d51b"
STEPS = {"1m": 60, "5m": 300, "10m": 600, "1h": 3600}
BASE = "https://api.exchange.coinbase.com"
SETTLE_SECONDS = 3
MAX_HISTORY = 100_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def specs(config):
    return [
        *config["members"],
        *([config["gate"]] if "gate" in config else []),
        *([config["fallback"]] if "fallback" in config else []),
    ]


def select_winners(rows, configs):
    """Keep every positive, active, completed fee row; collapse only fee labels."""
    grouped = {}
    for row in rows:
        if row["interval"] not in STEPS or row["mode"] not in MODES:
            continue
        if row["status"] != "completed" or int(row["fee_bps"]) not in (15, 25):
            continue
        result = float(row["return_pct"])
        if not math.isfinite(result):
            raise ValueError("nonfinite_study_return")
        key = (row["interval"], row["candidate_id"], row["mode"])
        item = grouped.setdefault(
            key,
            {
                "interval": row["interval"],
                "candidate_id": row["candidate_id"],
                "mode": row["mode"],
                "market": row["market"],
                "family": row["family"],
                "config": configs.get(row["candidate_id"]),
                "historical": {},
                "winning_fee_bps": [],
            },
        )
        fee = int(row["fee_bps"])
        if str(fee) in item["historical"]:
            raise ValueError("duplicate_study_row")
        item["historical"][str(fee)] = {
            "return_pct": result,
            "fills": int(row["fills"]),
            "replay_id": row["replay_id"],
        }
        if result > 0 and int(row["fills"]) > 0:
            item["winning_fee_bps"].append(fee)
    selected = [item for item in grouped.values() if item["winning_fee_bps"]]
    if any(x["market"] == "spot_reference" and x["config"] is None for x in selected):
        raise ValueError("winning_config_missing")
    return sorted(
        selected,
        key=lambda x: (STEPS[x["interval"]], x["mode"], x["candidate_id"]),
    )


def load_winners(root=STUDY):
    raw, packed = (
        (root / "results.csv").read_bytes(),
        (root / "plan.json.gz").read_bytes(),
    )
    if digest(raw) != CSV_HASH or digest(packed) != PLAN_HASH:
        raise ValueError("accepted_study_hash_mismatch")
    plan = json.loads(gzip.decompress(packed))
    configs = {r["candidate_id"]: r["config"] for r in plan["inventory"]["candidates"]}
    return select_winners(csv.DictReader(io.StringIO(raw.decode())), configs)


def parse_candles(payload, step, start, end):
    """Provider order is time, LOW, HIGH, OPEN, CLOSE, VOLUME; end is exclusive."""
    if not isinstance(payload, list) or len(payload) > 301:
        raise FeedUnavailable("candle_schema_invalid")
    result = {}
    for values in payload:
        if not isinstance(values, list) or len(values) != 6:
            raise FeedUnavailable("candle_schema_invalid")
        if any(type(x) not in (float, int) or not math.isfinite(x) for x in values):
            raise FeedUnavailable("candle_schema_invalid")
        stamp, low, high, opening, close, volume = values
        if (
            stamp != int(stamp)
            or stamp % step
            or not 0 < low <= min(opening, close) <= max(opening, close) <= high
            or volume < 0
        ):
            raise FeedUnavailable("candle_schema_invalid")
        if start <= stamp < end:
            bar = dict(zip(("ts", "low", "high", "open", "close", "volume"), values))
            bar["ts"] = int(stamp)
            if stamp in result and result[stamp] != bar:
                raise FeedUnavailable("candle_duplicate_conflict")
            result[int(stamp)] = bar
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Candles:
    """Bounded public GET only. Successful pages advance by requested windows."""

    def __init__(self, *, opener=None, pause=0.15):
        self.opener = opener or build_opener(NoRedirect())
        self.pause = pause

    def fetch(self, step, start, end):
        result = {}
        while start < end:
            stop = min(end, start + 299 * step)
            query = urlencode(
                {"granularity": step, "start": iso(start), "end": iso(stop)}
            )
            request = Request(
                f"{BASE}/products/ZEC-USD/candles?{query}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "zec-oracle-display/1",
                },
                method="GET",
            )
            try:
                with self.opener.open(request, timeout=8) as response:
                    raw = response.read(1_048_577)
                if len(raw) > 1_048_576:
                    raise FeedUnavailable("candle_response_too_large")
                result.update(parse_candles(json.loads(raw), step, start, stop))
            except FeedUnavailable:
                raise
            except HTTPError as exc:
                raise FeedUnavailable(
                    "candle_rate_limited" if exc.code == 429 else "candle_http_error"
                ) from None
            except (OSError, ValueError, UnicodeError):
                raise FeedUnavailable("candle_provider_unavailable") from None
            start = stop
            if self.pause and start < end:
                time.sleep(self.pause)
        return result


def iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat().replace("+00:00", "Z")


def aggregate(rows, source_step, target_step):
    grouped = {}
    for stamp, bar in rows.items():
        grouped.setdefault(stamp // target_step * target_step, {})[stamp] = bar
    result = {}
    for stamp, parts in grouped.items():
        required = list(range(stamp, stamp + target_step, source_step))
        if sorted(parts) != required:
            continue  # Missing candles are gaps, never synthesized zero volume.
        bars = [parts[t] for t in required]
        result[stamp] = {
            "ts": stamp,
            "open": bars[0]["open"],
            "close": bars[-1]["close"],
            "high": max(b["high"] for b in bars),
            "low": min(b["low"] for b in bars),
            "volume": sum(b["volume"] for b in bars),
        }
    return result


def arrays_for(rows, step, end):
    """An explicit invalid row breaks each missing completed period's state."""
    if not rows:
        raise FeedUnavailable("candle_history_missing")
    start = min(rows)
    count = (end - start) // step
    if not 0 < count <= MAX_HISTORY:
        raise FeedUnavailable("history_capacity_exceeded")
    stamps = np.arange(start, end, step, dtype=np.int64)
    valid = np.array([int(t) in rows for t in stamps], dtype=bool)
    arrays = {"ts": stamps}
    for key in ("open", "high", "low", "close", "volume"):
        arrays[key] = np.array([rows.get(int(t), {}).get(key, np.nan) for t in stamps])
    return arrays, valid


def latest_shape(bars, valid, step):
    if len(valid) < 48 or not valid[-48:].all():
        return {"shape": "unknown", "reason": "needs_48_contiguous_completed_bars"}
    # The detector's rolling return volatility also reads the preceding close.
    # Replaying the whole contiguous suffix preserves its initial conditions.
    gaps = np.flatnonzero(~valid)
    start = int(gaps[-1]) + 1 if len(gaps) else 0
    frame = pd.DataFrame(
        {
            "timestamp": bars["ts"][start:],
            **{k: bars[k][start:] for k in ("high", "low", "close")},
        }
    )
    row = detect_shapes(frame, window=48).iloc[-1]
    return {
        "shape": str(row["shape"]),
        "zone": str(row["zone"]),
        "range_position": float(row["range_position"]),
        "fit_r2": float(row["quadratic_r2"]),
        "available_at": int(bars["ts"][-1]) + step,
    }


def latest_cycle(bars, valid, step, frozen=None):
    """Same 64/16 frozen causal search, anchored to this process's seed history.

    No null simulations run in a display. This is an unqualified cycle filter;
    none of the original study's cycle tests survived multiplicity correction.
    """
    decision = TRAIN - 1 + ((len(valid) - TRAIN) // BLOCK) * BLOCK
    if decision < TRAIN - 1:
        return None
    decision_at = int(bars["ts"][decision])
    if frozen is not None and frozen.get("decision_at") == decision_at:
        model = frozen["model"]
    else:
        model = fit_cycle(bars, valid, step, decision)
        if frozen is not None:
            frozen.update(decision_at=decision_at, model=model)
    if model is None:
        return None
    elapsed = float(bars["ts"][-1]) - model["origin"]
    angle, next_angle = (
        2 * np.pi * np.array([elapsed, elapsed + step]) / model["period_seconds"]
    )
    increment = (np.cos(next_angle) - np.cos(angle)) * model["coefficients"][2] + (
        np.sin(next_angle) - np.sin(angle)
    ) * model["coefficients"][3]
    return {
        **model,
        "cycle": 1.0 if increment > 0 else -1.0,
        "linear": 1.0 if model["linear_coefficients"][1] > 0 else -1.0,
        "qualified": False,
    }


def fit_cycle(bars, valid, step, decision):
    if not valid[decision]:
        return None
    past = np.flatnonzero(valid[: decision + 1])[-TRAIN:]
    if len(past) < TRAIN:
        return None
    ts = bars["ts"][past].astype(float)
    if TRAIN / ((ts[-1] - ts[0]) / step + 1) < 0.95:
        return None
    y = np.log(bars["close"][past])
    projector = Spectrum(ts, step)
    period = float(projector.periods[int(np.argmax(projector.power(y)[0]))])
    scale = ts[-1] - ts[0] + step

    def design(times):
        elapsed = np.asarray(times) - ts[0]
        return np.column_stack(
            [
                np.ones(len(elapsed)),
                elapsed / scale,
                np.cos(2 * np.pi * elapsed / period),
                np.sin(2 * np.pi * elapsed / period),
            ]
        )

    coefficients = np.linalg.lstsq(design(ts), y, rcond=None)[0]
    linear = np.linalg.lstsq(design(ts)[:, :2], y, rcond=None)[0]
    return {
        "origin": float(ts[0]),
        "scale": float(scale),
        "coefficients": coefficients.tolist(),
        "linear_coefficients": linear.tolist(),
        "period_seconds": period,
        "fit_available_at": int(ts[-1]) + step,
        "training_sha256": digest(
            canonical({"timestamps": ts.tolist(), "log_prices": y.tolist()}).encode()
        ),
    }


def evaluate(interval, winners, rows, end, *, frozen_cycle=None):
    step = STEPS[interval]
    bars, valid = arrays_for(rows, step, end)
    contiguous = next((i for i, ok in enumerate(valid[::-1]) if not ok), len(valid))
    shape = latest_shape(bars, valid, step)
    cycle = latest_cycle(bars, valid, step, frozen_cycle)
    context = {
        "shape": np.array([shape["shape"]]),
        "cycle": np.array([cycle["cycle"] if cycle else np.nan]),
        "linear": np.array([cycle["linear"] if cycle else np.nan]),
    }
    unique = {
        spec_id(s): s
        for w in winners
        if w["config"] is not None
        for s in specs(w["config"])
    }
    signals, eligible, failures = {}, {}, set()
    for sid, spec in unique.items():
        try:
            signals[sid], eligible[sid] = granular.member_signals(
                spec, bars, valid, step
            )
        except (ArithmeticError, ValueError, TypeError, KeyError, IndexError):
            failures.add(sid)  # No provider/card text or paths cross this boundary.
    policy_cache, results = {}, []
    for winner in winners:
        row = {
            **winner,
            "shape": shape,
            "cycle": cycle,
            "bar_close_at": end,
            "target_at": end + step,
            "horizon_seconds": step,
            "input_kind": "coinbase_trade_ohlcv",
            "input_start_at": int(bars["ts"][0]),
            "contiguous_bars": contiguous,
            "direction": None,
        }
        cfg = winner["config"]
        if winner["market"] != "spot_reference" or cfg is None:
            row.update(
                status="unavailable",
                reason="lifecycle_policy_has_no_directional_adapter",
            )
        elif failures.intersection(spec_id(s) for s in specs(cfg)):
            row.update(status="unavailable", reason="strategy_evaluation_failed")
        else:
            cid = winner["candidate_id"]
            try:
                if cid not in policy_cache:
                    policy_cache[cid] = granular.policy_signal(
                        cfg, signals, eligible, valid
                    )[0][-1]
                exposure = policy_cache[cid]
                allow = gate_for(winner["mode"], context, cfg)[0]
                if not math.isfinite(exposure):
                    row.update(
                        status="warming",
                        reason="insufficient_contiguous_strategy_history",
                    )
                elif not math.isfinite(allow):
                    row.update(
                        status="warming", reason="shape_or_cycle_history_unavailable"
                    )
                else:
                    target = float(exposure * allow)
                    row.update(
                        status="ready",
                        reason=None,
                        exposure=target,
                        direction="UP"
                        if target > 0
                        else "DOWN"
                        if target < 0
                        else "FLAT",
                    )
            except (ArithmeticError, ValueError, TypeError, KeyError, IndexError):
                row.update(status="unavailable", reason="strategy_evaluation_failed")
        results.append(row)
    fingerprint = digest(canonical([rows[t] for t in sorted(rows) if t < end]).encode())
    for row in results:
        row["input_sha256"] = fingerprint
    return results


class LiveDisplay:
    def __init__(self, winners, *, client=None):
        self.winners = winners
        self.client = client or Candles()
        self.raw, self.ends, self.views = {}, {}, {}
        self.cycles = {}
        self.lock = threading.Lock()
        self.implementation = {
            str(p.relative_to(ROOT)): digest(p.read_bytes())
            for p in (
                Path(__file__),
                ROOT / "research/zec_granular.py",
                ROOT / "research/zec_expanded.py",
                ROOT / "research/shape_study.py",
                ROOT / "research/zec_cycles.py",
                *sorted((ROOT / "backtester/core").rglob("*.py")),
            )
        }

    def refresh(self, now):
        for interval in dict.fromkeys(w["interval"] for w in self.winners):
            group = [w for w in self.winners if w["interval"] == interval]
            step = STEPS[interval]
            end = int((now - SETTLE_SECONDS) // step) * step
            if self.ends.get(interval) == end:
                continue
            base_step = 300 if step == 600 else step
            saved = self.raw.setdefault(interval, {})
            warmup = max(
                [
                    build(s["strategy"], **s["params"]).warmup_bars()
                    for w in group
                    if w["config"]
                    for s in specs(w["config"])
                ]
                + [64]
            )
            start = (
                max(min(saved), max(saved) - 3 * base_step)
                if saved
                else end - max(128, warmup + 128) * step
            )
            try:
                if saved and (end - min(saved)) // step > MAX_HISTORY:
                    raise FeedUnavailable("history_capacity_exceeded")
                fetched = self.client.fetch(base_step, start, end)
                saved.update(fetched)
                rows = aggregate(saved, base_step, step) if base_step != step else saved
                view = evaluate(
                    interval,
                    group,
                    rows,
                    end,
                    frozen_cycle=self.cycles.setdefault(interval, {}),
                )
                for row in view:
                    row["calculated_at"] = time.time()
                # Recent omitted candles may arrive late. Keep retrying an
                # incomplete boundary; future refreshes also reread an overlap.
                if end - step in rows:
                    self.ends[interval] = end
            except (
                FeedUnavailable,
                OSError,
                ArithmeticError,
                ValueError,
                TypeError,
                KeyError,
            ) as exc:
                reason = (
                    exc.code
                    if isinstance(exc, FeedUnavailable)
                    else "candle_evaluation_failed"
                )
                view = [
                    {**w, "status": "unavailable", "direction": None, "reason": reason}
                    for w in group
                ]
            with self.lock:
                self.views[interval] = view

    def frame(self, now, quote=None, feed_error=None):
        if not feed_error and (
            quote is None or not 0 <= now - quote["observed_at"] <= 15
        ):
            feed_error = "quote_stale" if quote else "quote_unavailable"
        output = []
        with self.lock:
            views = {k: list(v) for k, v in self.views.items()}
        for interval in dict.fromkeys(w["interval"] for w in self.winners):
            source = views.get(interval) or [
                {
                    **w,
                    "status": "warming",
                    "direction": None,
                    "reason": "loading_completed_trade_candles",
                }
                for w in self.winners
                if w["interval"] == interval
            ]
            for original in source:
                row = dict(original)
                if row["status"] == "ready":
                    if (
                        feed_error
                        or quote is None
                        or not 0 <= now - quote["observed_at"] <= 15
                    ):
                        row.update(
                            status="stale",
                            last_direction=row["direction"],
                            direction=None,
                            reason=feed_error or "quote_stale",
                        )
                    elif now >= row["target_at"]:
                        row.update(
                            status="stale",
                            last_direction=row["direction"],
                            direction=None,
                            reason="completed_bar_prediction_expired",
                        )
                output.append(row)
        return {
            "schema_version": 1,
            "instrument": "ZEC/USD",
            "generated_at": now,
            "quote": quote if not feed_error else None,
            "feed_error": feed_error,
            "source": "shared_coinbase_recorder_plus_public_completed_trade_candles",
            "study_csv_sha256": CSV_HASH,
            "study_plan_sha256": PLAN_HASH,
            "implementation_sha256": self.implementation,
            "direction_method": "strategy_target_exposure_sign_for_next_bar_not_profit_probability",
            "winning_fee_rows": sum(len(w["winning_fee_bps"]) for w in self.winners),
            "display_rows": len(output),
            "status_counts": dict(Counter(w["status"] for w in output)),
            "rows": output,
        }


def render(frame, *, limit=0):
    quote = frame["quote"]
    price = f"${quote['price']:.6f}" if quote else "unavailable"
    lines = [
        f"ZEC/USD {price} | {iso(frame['generated_at'])} | {frame['display_rows']} configurations/modes; {frame['winning_fee_rows']} winning fee rows",
        "Live shared-recorder midpoint; completed Coinbase trade bars. Next-bar exposure hypothesis, NOT probability. Long/flat exits stay FLAT.",
        "Control modes are benchmarks; cycles unqualified. Unsupported lifecycle directions remain unavailable. Positive one-day selection is not live profit evidence.",
    ]
    for interval in dict.fromkeys(row["interval"] for row in frame["rows"]):
        row = next(r for r in frame["rows"] if r["interval"] == interval)
        timing = (
            f"bar close {iso(row['bar_close_at'])}; target {iso(row['target_at'])}; {row['contiguous_bars']} contiguous bars"
            if "bar_close_at" in row
            else row["reason"]
        )
        lines.append(f"{interval}: {timing}")
    lines.append(
        "BAR  MODE              CONFIGURATION             STRATEGY                         CALL   SHAPE / ZONE          RET@.25% RET@.15% STATUS"
    )
    for row in frame["rows"][: limit or None]:
        historical = row["historical"]
        returns = [
            f"{historical[str(f)]['return_pct']:+.3f}"
            if str(f) in historical
            else "n/a"
            for f in (25, 15)
        ]
        shape = row.get("shape", {})
        tag = f"{shape.get('shape', 'unknown')}/{shape.get('zone', '-')}"
        call = row.get("direction") or "N/A"
        status = row["reason"] or row["status"]
        config = row["config"]
        name = (
            "+".join(dict.fromkeys(s["strategy"] for s in specs(config)))
            if config
            else row["family"]
        )
        lines.append(
            f"{row['interval']:4} {row['mode']:17} {row['candidate_id']:25} {name:32} {call:6} {tag:21} {returns[0]:>8} {returns[1]:>8}  {status}"
        )
    if limit and limit < len(frame["rows"]):
        lines.append(
            f"Showing {limit}/{len(frame['rows'])}; omit --limit for every configuration. Full configuration parameters are in --json output."
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prices", type=Path, help="existing shared recorder directory"
    )
    parser.add_argument("--intervals", nargs="+", choices=STEPS, default=list(STEPS))
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument(
        "--refresh",
        type=float,
        default=10,
        help="display seconds; actual bar horizon is unchanged",
    )
    parser.add_argument(
        "--frames", type=int, default=0, help="bounded smoke; 0 runs until Ctrl-C"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="table rows, 0 shows all; JSON always complete",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="one complete machine-readable frame per line",
    )
    args = parser.parse_args(argv)
    if (
        not math.isfinite(args.refresh)
        or not 0.2 <= args.refresh <= 300
        or args.frames < 0
        or args.limit < 0
    ):
        parser.error("invalid_refresh_frames_or_limit")
    winners = [
        w
        for w in load_winners()
        if w["interval"] in args.intervals and w["mode"] in args.modes
    ]
    display = LiveDisplay(winners)
    feed = RecorderFeed(args.prices, instrument="ZEC/USD")
    stop = threading.Event()

    def update():
        while not stop.is_set():
            display.refresh(time.time())
            stop.wait(15)  # At most one successful candle refresh per bar boundary.

    worker = threading.Thread(target=update, name="completed-candles", daemon=True)
    worker.start()
    quote, feed_error, count = None, None, 0
    deadline = time.monotonic()
    try:
        while not args.frames or count < args.frames:
            try:
                observation = feed.poll()
                if observation:
                    quote = observation
                feed_error = None
            except FeedUnavailable as exc:
                feed_error = exc.code
            now = time.monotonic()
            if now >= deadline:
                frame = display.frame(time.time(), quote, feed_error)
                if args.json:
                    print(canonical(frame), flush=True)
                else:
                    if sys.stdout.isatty():
                        print("\x1b[2J\x1b[H", end="")
                    print(render(frame, limit=args.limit), flush=True)
                count += 1
                deadline = now + args.refresh
            stop.wait(min(0.25, max(0, deadline - time.monotonic())))
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        stop.set()
        worker.join(timeout=0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
