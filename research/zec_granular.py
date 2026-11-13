"""Offline, receive-time ZEC tape replay. No network or live execution path.

The book is sampled at the first received update in each UTC second. Orders
wait at least one second after a closed-bar decision (or observed stop trigger),
then use the first sampled book at/after eligibility. This is deliberately not
an exchange matching-engine or queue-position simulation.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import heapq
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.strategies import REGISTRY
from backtester.core.types import BarWindow
from backtester.core.volty import VoltyConfig, stop_levels
from backtester.core.zec_ensemble import _Member, spec_id
from backtester.voltycli import GRID
from research.zec_ensembles import catalog, component_specs, targets

VERSION = 1
STEPS = {"1m": 60, "5m": 300, "10m": 600, "1h": 3600}
NS = 1_000_000_000
CAPTURE_HASH = "eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31"
CAPTURE_START = 1794459387224912000
CAPTURE_END = CAPTURE_START + 86400 * NS
DEPTH = 40
LATENCY_NS = NS
MAX_WAIT_NS = 2 * NS


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path: Path, value) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    tmp.replace(path)


class Book:
    """Exact displayed sizes; lazy heaps retain sorted top depth without full sorts."""
    def __init__(self):
        self.sizes = [{}, {}]
        self.heaps = [[], []]
        self.valid = False

    def update(self, side: int, price: float, size: float):
        if not (math.isfinite(price) and price > 0 and math.isfinite(size) and size >= 0):
            raise ValueError("invalid displayed price/size")
        values = self.sizes[side]
        if size:
            if price not in values:
                heapq.heappush(self.heaps[side], price if side else -price)
            values[price] = size
        else:
            values.pop(price, None)

    def snapshot(self, payload):
        self.__init__()
        for side, name in enumerate(("bids", "asks")):
            for price, size in payload[name]:
                self.update(side, float(price), float(size))
        self.valid = True

    def levels(self, side: int):
        heap, values = self.heaps[side], self.sizes[side]
        taken, seen = [], set()
        while heap and len(taken) < DEPTH:
            key = heapq.heappop(heap)
            price = key if side else -key
            if price in values and price not in seen:
                taken.append((price, values[price]))
                seen.add(price)
        # Reinsert only live unique levels. Deleted then re-added prices can
        # leave duplicates in a lazy heap; never count their liquidity twice.
        for price, _ in taken:
            heapq.heappush(heap, price if side else -price)
        return taken

    def quote(self):
        if not self.valid:
            return None
        sides = [self.levels(0), self.levels(1)]
        if not all(sides) or sides[0][0][0] >= sides[1][0][0]:
            return None
        a = np.zeros((2, DEPTH, 2), dtype=float)
        for side in (0, 1):
            a[side, :len(sides[side])] = sides[side]
        return a


def prepare_capture(wal: Path, output: Path, *, expected_hash=CAPTURE_HASH,
                    start_ns=CAPTURE_START, end_ns=CAPTURE_END):
    """Read original bytes once; hash and validate sequence before publishing cache."""
    output.mkdir(parents=True, exist_ok=True)
    trades, quote_times, quotes, gaps = [], [], [], []
    book = Book()
    h = hashlib.sha256()
    previous_ns = None
    previous_trade = None
    book_connection = None
    last_sample_second = -1
    counts = Counter()
    with wal.open("rb") as stream:
        for seq, line in enumerate(stream, 1):
            h.update(line)
            row = json.loads(line)
            t = row["received_ns"]
            if row["seq"] != seq or not start_ns <= t < end_ns:
                raise ValueError("capture sequence/window mismatch")
            if previous_ns is not None:
                if t < previous_ns:
                    raise ValueError("capture receive clock moved backwards")
                if t - previous_ns > MAX_WAIT_NS:
                    gaps.append((previous_ns, t, "receipt_gap"))
            previous_ns = t
            kind = row["type"]
            counts[kind] += 1
            payload = json.loads(row["raw"])
            if kind in {"connection_open", "connection_gap"}:
                book.valid = False
                gaps.append((t, t, kind))
            elif kind == "snapshot":
                book.snapshot(payload)
                book_connection = row["connection_id"]
            elif kind == "l2update" and book.valid and row["connection_id"] == book_connection:
                for side, price, size in payload["changes"]:
                    book.update(0 if side == "buy" else 1, float(price), float(size))
            elif kind == "match":
                trade_id = int(payload["trade_id"])
                if previous_trade is not None and trade_id > previous_trade[1] + 1:
                    gaps.append((previous_trade[0], t, "trade_id_gap"))
                previous_trade = (t, trade_id)
                price, size = float(payload["price"]), float(payload["size"])
                if not (price > 0 and size > 0 and math.isfinite(price + size)):
                    raise ValueError("invalid trade")
                trades.append((t, price, size, trade_id))
            if kind in {"snapshot", "l2update"} and book.valid and row["connection_id"] == book_connection and t // NS != last_sample_second:
                quote = book.quote()
                if quote is not None:
                    quote_times.append(t)
                    quotes.append(quote)
                    last_sample_second = t // NS
            if seq % 250000 == 0:
                print(f"prepared {seq} capture records", flush=True)
    actual = h.hexdigest()
    if actual != expected_hash:
        raise ValueError("original capture SHA256 mismatch")
    if not trades or not quotes:
        raise ValueError("capture has no trades/books")
    # Explicit dtypes avoid losing nanosecond precision by coercing mixed tuples.
    arrays = {"trade_ns": np.array([x[0] for x in trades], dtype=np.int64),
              "price": np.array([x[1] for x in trades]),
              "size": np.array([x[2] for x in trades]),
              "trade_id": np.array([x[3] for x in trades], dtype=np.int64),
              "quote_ns": np.array(quote_times, dtype=np.int64), "books": np.array(quotes)}
    np.savez(output / "tape.npz", **arrays)
    info = {"version": VERSION, "wal_sha256": actual, "records": seq,
            "counts": dict(counts), "start_ns": start_ns, "end_ns": end_ns,
            "gaps": gaps, "book_depth": DEPTH, "quote_samples": len(quotes),
            "book_validity": "reset on connection loss/change; receive silence waits for fresh ordered update without discarding same-connection state",
            "tape_sha256": digest(output / "tape.npz")}
    save_json(output / "capture.json", info)
    return arrays, info


def make_bars(tape, info, step):
    first = (info["start_ns"] // (step * NS) + 1) * step
    end = info["end_ns"] // (step * NS) * step
    ts = np.arange(first, end, step, dtype=np.int64)
    bars = {"ts": ts, **{k: np.zeros(len(ts)) for k in ("open", "high", "low", "close", "volume")}}
    valid = np.ones(len(ts), dtype=bool)
    counts = np.zeros(len(ts), dtype=np.int64)
    for i, t in enumerate(ts):
        lo, hi = np.searchsorted(tape["trade_ns"], [int(t) * NS, int(t + step) * NS])
        p = tape["price"][lo:hi]
        counts[i] = hi - lo
        if not len(p):
            valid[i] = False  # Never invent a price for an unobserved candle.
            continue
        for name, value in zip(("open", "high", "low", "close", "volume"),
                               (p[0], p.max(), p.min(), p[-1], tape["size"][lo:hi].sum())):
            bars[name][i] = value
        for gap_start, gap_end, _ in info["gaps"]:
            if int(t) * NS <= gap_end < int(t + step) * NS:
                valid[i] = False
                break
    return bars, valid, counts


def segments(valid):
    edges = np.diff(np.r_[False, valid, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def member_signals(spec, bars, valid, step):
    values = np.full(len(valid), np.nan)
    eligible = np.zeros(len(valid), dtype=bool)
    for start, end in segments(valid):
        # Existing ensemble implementation rescales annual volatility. Instantiate
        # at 1m and apply the exact sqrt(cadence ratio) for custom 10m bars; do not
        # alter the global venue interval registry or relabel 10m as another bar.
        member = _Member(spec, interval="1m")
        if spec["strategy"] in {"voltarget", "garch_voltarget"}:
            member.strategy.target_vol *= math.sqrt(step / 60)
            member.strategy.params["target_vol"] = member.strategy.target_vol
        arrays = [bars[k][start:end] for k in ("ts", "open", "high", "low", "close", "volume")]
        for i in range(end - start):
            value = member.step(BarWindow(*arrays, i))
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("spot member returned invalid target")
            values[start + i] = value
            eligible[start + i] = i >= member.strategy.warmup_bars()
    return values, eligible


def frozen_catalog():
    rows = catalog("1m")
    # Registry singles already appear in this finite historical ensemble grid,
    # except trigger_trade and the three venue-specific leverage wrappers.
    rows.append({"candidate_id": "registry-trigger_trade", "family": "canonical-single",
                 "config": {"members": [{"strategy": "trigger_trade", "params": {}}],
                            "mode": "single", "persistence": 1, "rebalance_threshold": 0}})
    return rows


def policy_signal(config, signals, eligible, valid):
    out = np.full(len(valid), np.nan)
    mask = np.zeros(len(valid), dtype=bool)
    specs = [*config["members"], *([config["gate"]] if "gate" in config else []),
             *([config["fallback"]] if "fallback" in config else [])]
    keys = [spec_id(x) for x in specs]
    for a, b in segments(valid):
        warmups = {key: int(np.argmax(eligible[key][a:b])) if eligible[key][a:b].any() else b-a for key in keys}
        if max(warmups.values()) >= b-a:
            continue
        cfg = copy.deepcopy(config)
        train_end = max(max(warmups.values()) + 64, 256)
        if cfg.get("weighting") and train_end >= b-a-1:
            continue
        raw, _ = targets(cfg, {k: np.nan_to_num(signals[k][a:b]) for k in keys}, warmups, train_end)
        out[a:b] = raw
        mask[a:b] = np.logical_and.reduce([eligible[k][a:b] for k in keys])
        if cfg.get("weighting"):
            mask[a:a+train_end] = False
    out[~mask] = np.nan
    return out, mask


class Portfolio:
    def __init__(self, tape, fee_bps, *, synthetic_short=False, capital=10000):
        self.tape, self.fee = tape, fee_bps / 10000
        self.synthetic_short, self.capital = synthetic_short, capital
        self.cash, self.qty = float(capital), 0.0
        self.fees = self.turnover = self.residual_slip = 0.0
        self.fills, self.rejections, self.equity = [], Counter(), [capital]
        self.last_fill_ns = None
        self.last_mark = None
        self.carry = 0.0
        if "carry_integral" not in tape:
            mids = (tape["books"][:,0,0,0]+tape["books"][:,1,0,0])/2
            tape["carry_integral"] = np.r_[0.0, np.cumsum(mids[:-1]*np.diff(tape["quote_ns"])/NS/3600)]

    def quote_index(self, requested):
        i = int(np.searchsorted(self.tape["quote_ns"], requested, side="left"))
        if i >= len(self.tape["quote_ns"]) or self.tape["quote_ns"][i] - requested > MAX_WAIT_NS:
            return None
        return i

    def mark(self, i):
        book = self.tape["books"][i]
        mid = (book[0, 0, 0] + book[1, 0, 0]) / 2
        return self.cash + self.qty * mid

    def target(self, target, i, decision_ns, threshold=0.0):
        now = int(self.tape["quote_ns"][i])
        if now < decision_ns + LATENCY_NS:
            raise ValueError("fill preceded signal eligibility")
        if self.last_fill_ns is not None and now < self.last_fill_ns:
            raise ValueError("noncausal fill order")
        book = self.tape["books"][i]
        mid = (book[0, 0, 0] + book[1, 0, 0]) / 2
        if self.synthetic_short and self.last_mark is not None:
            carry = abs(self.qty)*(self.tape["carry_integral"][i]-self.tape["carry_integral"][self.last_mark])*0.1/10000
            self.carry += carry
            self.cash -= carry
        self.last_mark = i
        equity = self.cash + self.qty * mid
        if equity <= 0:
            self.rejections["nonpositive_equity"] += 1
            return False
        desired = target * equity / mid
        delta = desired - self.qty
        if abs(delta)*mid < 1e-6 or abs(delta)*mid/equity < threshold:
            self.equity.append(equity)
            return True
        if not self.synthetic_short and delta < 0:
            delta = max(delta, -self.qty)
        side = 1 if delta > 0 else 0
        remaining, notional, units = abs(delta), 0.0, 0.0
        budget = max(0.0, self.cash) if not self.synthetic_short and side == 1 else math.inf
        direction = 1 if side else -1
        for price, size in book[side]:
            if price <= 0 or size <= 0:
                continue
            unit_cost = price * (1 + direction*2/10000) * (1+self.fee)
            used = min(remaining, size, budget/unit_cost)
            notional += used * price
            units += used
            remaining -= used
            budget -= used * unit_cost
            if remaining < 1e-10 or budget < 1e-8:
                break
        if remaining > 1e-8 and budget > 1e-8:
            self.rejections["insufficient_40_level_depth"] += 1
            return False
        if units*mid < 1e-6:
            return False
        delta = direction*units
        # VWAP and fees use the final affordable quantity, including any
        # cash cap, rather than pricing a larger order and shrinking it later.
        raw = notional / units
        execution = raw * (1 + direction * 2/10000)
        cost = abs(delta)*execution*self.fee
        self.cash -= delta*execution + cost
        self.qty += delta
        self.fees += cost
        self.turnover += abs(delta)*execution
        self.residual_slip += abs(delta)*abs(execution-raw)
        self.last_fill_ns = now
        self.fills.append({"decision_ns": int(decision_ns), "fill_ns": now, "target": float(target),
                           "qty": float(delta), "price": execution, "fee": cost,
                           "cash": self.cash, "position": self.qty})
        self.equity.append(self.cash+self.qty*mid)
        return True

    def result(self):
        terminal = self.mark(len(self.tape["quote_ns"])-1)
        e = np.array([*self.equity, terminal])
        dd = float(np.min(e/np.maximum.accumulate(e)-1)*100)
        return {"return_pct": (terminal/self.capital-1)*100, "end_equity": terminal,
                "fees_usd": self.fees, "turnover_usd": self.turnover,
                "residual_slippage_usd": self.residual_slip, "carry_usd": self.carry,
                "fills": len(self.fills), "decision_fill_drawdown_pct": dd,
                "rejections": dict(self.rejections), "open_units": self.qty,
                "terminal_mark_ns": int(self.tape["quote_ns"][-1]),
                "terminal_mark_age_seconds": (int(self.tape["end_ns"])-int(self.tape["quote_ns"][-1]))/NS,
                "terminal_state": "closed" if abs(self.qty)<1e-8 else "open_unliquidated"}


def spot_replay(tape, bars, values, fee, threshold=0):
    p = Portfolio(tape, fee)
    for t, value in zip(bars["ts"], values):
        decision = (int(t) + int(bars["step"])) * NS
        i = p.quote_index(decision+LATENCY_NS)
        if i is None:
            p.rejections["no_fresh_book"] += 1
            continue
        # Invalid/warmup bar is known only at its close: unwind there, never
        # retrospectively before the outage. Indicator state restarts separately.
        p.target(0.0 if not np.isfinite(value) else float(value), i, decision,
                 threshold if np.isfinite(value) else 0.0)
    terminal_close(p)
    return p


def terminal_close(p):
    # Fixed deadline policy is declared before replay; no choice of the last
    # favourable quote. Main supplies end_ns alongside the immutable arrays.
    decision = int(p.tape["end_ns"]) - 3*NS
    i = p.quote_index(decision + LATENCY_NS)
    if i is None:
        p.rejections["terminal_book_unavailable"] += 1
    else:
        p.target(0, i, decision)


def volty_replay(tape, bars, valid, length, mult, fee):
    levels = [np.full(len(valid)+1, np.nan), np.full(len(valid)+1, np.nan)]
    for a, b in segments(valid):
        data = {k: np.r_[bars[k][a:b], bars[k][b-1]] for k in ("high", "low", "close")}
        up, down = stop_levels(data, VoltyConfig(length=length, atr_mult=mult))
        levels[0][a:b+1], levels[1][a:b+1] = up, down
    p = Portfolio(tape, fee, synthetic_short=True)
    desired = 0
    pending = None
    step = int(bars["step"])
    observed_gaps = sorted(g[1] for g in tape.get("gaps", []))
    gap_i, invalid_until = 0, -1
    for t, price in zip(tape["trade_ns"], tape["price"]):
        t = int(t)
        if t >= int(tape["end_ns"]) - 3*NS:
            break
        while gap_i < len(observed_gaps) and observed_gaps[gap_i] <= t:
            invalid_until = (observed_gaps[gap_i]//(step*NS)+1)*step*NS
            gap_i += 1
        if pending is not None and int(tape["quote_ns"][pending[0]]) <= t:
            if p.target(pending[1], pending[0], pending[2]):
                desired = pending[1]
            pending = None
        bar = (t//NS-int(bars["ts"][0]))//step
        if not 0 <= bar < len(valid) or t < (int(bars["ts"][bar])*NS + LATENCY_NS):
            continue
        up, down = levels[0][bar], levels[1][bar]
        target = 0 if not np.isfinite(up) or t < invalid_until else (1 if price >= up else (-1 if price <= down else desired))
        if pending is None and target != desired:
            i = p.quote_index(t+LATENCY_NS)
            if i is not None:
                pending = (i, target, t)
            else:
                p.rejections["no_fresh_book"] += 1
    if pending is not None and int(tape["quote_ns"][pending[0]]) < int(tape["end_ns"])-2*NS:
        p.target(pending[1], pending[0], pending[2])
    terminal_close(p)
    return p, int(np.isfinite(levels[0][:-1]).sum())


def run_matrix(tape, info, output, fees=(10, 25, 60)):
    identity = source_identity()
    save_json(output/"identity.json", identity)
    tape["end_ns"] = info["end_ns"]
    tape["gaps"] = info["gaps"]
    catalog_rows = frozen_catalog()
    specs = component_specs(catalog_rows)
    plan = {"version": VERSION, "registry": sorted(REGISTRY), "ensemble_catalog": catalog_rows,
            "volty_grid": GRID, "intervals": STEPS, "fee_bps": fees,
            "capital": 10000, "latency_seconds": 1, "book_sampling_seconds": 1,
            "max_book_wait_seconds": 2, "residual_slippage_bps": 2,
            "synthetic_short_carry_bps_hour": 0.1,
            "source_sha256": info["wal_sha256"],
            "book_validity": info.get("book_validity", "fixture"),
            "selection": "all predefined cases; no winner selection or new parameter mining",
            "weighted_training": "fixed first256bars of each valid segment, or warmup+64 if greater; scored suffix only",
            "excluded_families": {"lev_low": "actual perp venue, funding and liquidation oracle absent",
              "lev_medium": "actual perp venue, funding and liquidation oracle absent",
              "lev_high": "actual perp venue, funding and liquidation oracle absent",
              "resting_ladder_grid": "no venue queue priority or limit fill adapter; exposure grid included separately",
              "compound": "requires paired BTC/context and venue-specific execution; ZEC-only tape cannot supply these",
              "pairs": "second instrument absent", "spec_only_cards": "no executable implementation"}}
    plan["benchmark"] = "cash and one entry near capture start held to fixed deadline exit, independent of signal-bar gaps"
    save_json(output/"plan.json", plan)
    rows, coverage = [], {}
    fills = (output/"fills.jsonl").open("w")
    for interval, step in STEPS.items():
        bars, valid, counts = make_bars(tape, info, step)
        bars["step"] = step
        np.savez(output/f"bars-{interval}.npz", **bars, valid=valid, trades=counts)
        signals, eligible = {}, {}
        for n, (key, spec) in enumerate(specs.items()):
            signals[key], eligible[key] = member_signals(spec, bars, valid, step)
            if n % 15 == 0:
                print(f"{interval}: computed member {n+1}/{len(specs)}", flush=True)
        quote_probe = Portfolio(tape,0)
        coverage[interval] = {"complete_utc_bars": len(valid), "valid_bars": int(valid.sum()),
                              "excluded_bars": int((~valid).sum()),
                              "longest_valid_segment": int(max((b-a for a,b in segments(valid)), default=0)),
                              "trades_in_complete_bars": int(counts.sum()),
                              "decisions_with_fresh_book": sum(quote_probe.quote_index((int(t)+step)*NS+LATENCY_NS) is not None for t in bars["ts"])}
        for candidate in catalog_rows:
            cfg = candidate["config"]
            values, mask = policy_signal(cfg, signals, eligible, valid)
            for fee in fees:
                base = {"interval": interval, "candidate_id": candidate["candidate_id"],
                        "family": candidate["family"], "fee_bps": fee,
                        "eligible_signal_bars": int(mask.sum()), "market": "coinbase_spot_reference"}
                if not mask.any():
                    rows.append({**base, "status": "insufficient_contiguous_warmup"})
                    continue
                p = spot_replay(tape, bars, values, fee, cfg["rebalance_threshold"])
                rows.append({**base, "status": "completed", **p.result()})
                for f in p.fills:
                    fills.write(json.dumps({**base, **f})+"\n")
        for length, mult in GRID:
            for fee in fees:
                p, usable = volty_replay(tape, bars, valid, length, mult, fee)
                base = {"interval": interval, "candidate_id": f"volty-{length}-{mult}", "family": "volty-stop",
                        "fee_bps": fee, "eligible_signal_bars": usable,
                        "market": "synthetic_1x_long_short_on_spot_tape"}
                rows.append({**base, "status": "completed" if usable else "insufficient_contiguous_warmup", **p.result()})
                for f in p.fills:
                    fills.write(json.dumps({**base, **f})+"\n")
        for fee in fees:
            for name in ("cash", "capture_buy_and_hold"):
                p = Portfolio(tape,fee)
                if name != "cash":
                    q = p.quote_index(info["start_ns"]+LATENCY_NS)
                    if q is not None:
                        p.target(1,q,info["start_ns"])
                    else:
                        p.rejections["entry_book_unavailable"] += 1
                    terminal_close(p)
                base = {"interval":interval,"candidate_id":name,"family":"benchmark","fee_bps":fee,
                        "market":"coinbase_spot_reference","status":"completed"}
                rows.append({**base,**p.result()})
                for f in p.fills:
                    fills.write(json.dumps({**base,**f})+"\n")
        for name, reason in plan["excluded_families"].items():
            rows.append({"interval": interval, "candidate_id": name, "family": "unsupported",
                         "status": "unsupported_inputs_or_execution", "reason": reason})
        print(f"{interval}: finished {len(rows)} cumulative matrix rows", flush=True)
    fills.close()
    for row in rows:
        if row["status"] == "completed" and row.get("terminal_state") == "open_unliquidated":
            row["status"] = "incomplete_terminal_exit"
    save_json(output/"coverage.json", coverage)
    save_json(output/"results.json", rows)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (output/"results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    if source_identity() != identity:
        raise ValueError("code or runtime changed during run; results are not publishable")
    manifest = {"version": VERSION, "identity": identity, "capture_sha256": info["wal_sha256"],
                "rows": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
                "artifacts": {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name not in {"manifest.json", "run.lock"} and p.suffix != ".log"}}
    save_json(output/"manifest.json", manifest)
    return rows, coverage


def source_identity():
    root = Path(__file__).resolve().parents[1]
    paths = [Path(__file__), root/"research/zec_ensembles.py", root/"backtester/voltycli.py",
             *sorted((root/"backtester/core").rglob("*.py"))]
    return {"code": {str(p.relative_to(root)): digest(p) for p in paths},
            "python": platform.python_version(), "executable": sys.executable,
            "numpy": np.__version__, "pandas": pd.__version__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-prepared", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    import fcntl

    lock = (args.output/"run.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (args.output/"manifest.json").exists():
        raise ValueError("finished output is immutable; use a new output directory")
    if args.reuse_prepared:
        info = json.loads((args.output/"capture.json").read_text())
        if info["wal_sha256"] != CAPTURE_HASH or digest(args.wal) != CAPTURE_HASH or digest(args.output/"tape.npz") != info["tape_sha256"]:
            raise ValueError("prepared input hash mismatch")
        with np.load(args.output/"tape.npz", allow_pickle=False) as loaded:
            tape = {key: loaded[key] for key in loaded.files}
    else:
        tape, info = prepare_capture(args.wal, args.output)
    if not args.prepare_only:
        run_matrix(tape, info, args.output)


if __name__ == "__main__":
    main()
