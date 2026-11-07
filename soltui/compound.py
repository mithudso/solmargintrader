"""Compound five-minute tester: saved configuration, live reads, forward ledger, sweeps.

    python3 -m soltui.compound signal  --asset SOL         # score now, explain every metric
    python3 -m soltui.compound forward --asset SOL --loop  # record a call per closed 5m bar
    python3 -m soltui.compound status  --asset SOL         # forward-test hit rates
    python3 -m soltui.compound backtest --asset SOL        # compound + each component alone
    python3 -m soltui.compound sweep --all-assets --perturb --aggregate-grid --workers 6

The scoring lives in `backtester/core/scorecard.py` (pure) and the historical evaluation in
`backtester/core/compound.py` (engine-backed). This module owns everything with state or a
network edge, because `backtester/` may not touch the network (CLAUDE.md, backtester rule 4).

## Network reads (all public, keyless, read-only)

* Coinbase Exchange candles: the last ~600 closed 5m bars. The still-forming bar is DROPPED:
  scoring a bar that has not closed would forecast with a price from inside the forecast window.
* Hyperliquid `metaAndAssetCtxs` and `l2Book`: funding, premium, open interest, book depth.
  Only fetched when a component that needs them is enabled.
* RSS headlines (CoinDesk, Cointelegraph), only when `gate_news` is enabled. Keyword match on
  the asset's names, no sentiment scoring: there is no timestamped archive to test sentiment on.

A failed read never becomes a number. The component is reported unavailable; an enabled news
gate that could not read its feed blocks the call (fails closed).

## The forward ledger

`<config dir>/compound/forward/<ASSET>.jsonl`, append-only:

* `call`    -- one per closed bar per config: the call, composite and every component's score;
* `resolve` -- written once the NEXT bar has closed: its close and the return in bps;
* `ctx`     -- Hyperliquid open interest snapshots, which `oi_flow` needs a history of.

Each component's own score is logged with every call, so one forward run tests the compound
AND each enabled component as a standalone call. No order is ever placed: soltui has no
order path.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from backtester.core import compound as cbt  # noqa: E402
from backtester.core import scorecard as sc  # noqa: E402

from . import config as config_mod  # noqa: E402

COINBASE_CANDLES = "https://api.exchange.coinbase.com/products/{product}/candles"
HYPERLIQUID_INFO = "https://api.hyperliquid.xyz/info"
NEWS_FEEDS = ("https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss")
USER_AGENT = "soltui-compound/1.0 (read-only research)"
LIVE_BARS = 600
HTTP_TIMEOUT = 15

# Names a headline must contain (case-insensitive, word-bounded) to count for an asset.
ASSET_NAMES: dict[str, tuple[str, ...]] = {
    "SOL": ("solana", "sol"), "BTC": ("bitcoin", "btc"), "ETH": ("ethereum", "ether", "eth"),
    "DOGE": ("dogecoin", "doge"), "XRP": ("xrp", "ripple"), "ZEC": ("zcash", "zec"),
    "BNB": ("bnb", "binance coin"), "HYPE": ("hyperliquid", "hype"),
}


class CompoundError(RuntimeError):
    """A user-facing failure (bad input, unreadable file, no data)."""


# -- paths (resolved per call: tests and the bridge suite repoint the config dir) ---------------


def home() -> Path:
    return config_mod.CONFIG_DIR / "compound"


def config_path() -> Path:
    return home() / "config.json"


def forward_path(asset: str) -> Path:
    return home() / "forward" / f"{_asset(asset)}.jsonl"


def results_path() -> Path:
    return home() / "backtests.jsonl"


def _asset(asset: str) -> str:
    a = str(asset or "").strip().upper()
    if not a.isalnum() or len(a) > 12:
        raise CompoundError(f"bad asset symbol {asset!r}")
    return a


# -- saved configuration ---------------------------------------------------------------------


def load_state() -> dict[str, Any]:
    """{"config": normalised scorecard config, "events": [...]}. Missing file = defaults."""
    path = config_path()
    raw: dict[str, Any] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CompoundError(f"unreadable {path}: {exc}") from exc
    try:
        cfg = sc.normalise_config(raw.get("config"))
    except sc.ScorecardError as exc:
        raise CompoundError(f"{path}: {exc}") from exc
    return {"config": cfg, "events": _events(raw.get("events") or [])}


def _events(raw: Sequence[Any]) -> list[dict[str, Any]]:
    out = []
    for ev in raw:
        if not isinstance(ev, Mapping) or "ts" not in ev:
            raise CompoundError("each event needs a ts (UTC epoch seconds) and a title")
        try:
            ts = int(ev["ts"])
        except (TypeError, ValueError) as exc:
            raise CompoundError(f"event ts must be epoch seconds, got {ev['ts']!r}") from exc
        out.append({"ts": ts, "title": str(ev.get("title", ""))[:200]})
    return sorted(out, key=lambda e: e["ts"])


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def merge_config(base: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a partial update ({components: {id: {enabled, weight, params}}, aggregate, ...})."""
    out = json.loads(json.dumps(base))
    for cid, entry in (patch.get("components") or {}).items():
        if cid not in sc.BY_ID:
            raise CompoundError(f"unknown component {cid!r}")
        if not isinstance(entry, Mapping):
            raise CompoundError(f"{cid}: expected an object")
        tgt = out["components"][cid]
        for key in ("enabled", "weight"):
            if key in entry:
                tgt[key] = entry[key]
        tgt["params"].update(entry.get("params") or {})
    for section in ("aggregate", "execution"):
        out[section].update(patch.get(section) or {})
    if "blocked_hours" in patch:
        out["blocked_hours"] = patch["blocked_hours"]
    try:
        return sc.normalise_config(out)
    except sc.ScorecardError as exc:
        raise CompoundError(str(exc)) from exc


def save_state(config_patch: Mapping[str, Any] | None = None,
               events: Sequence[Any] | None = None, reset: bool = False) -> dict[str, Any]:
    state = {"config": sc.default_config(), "events": []} if reset else load_state()
    if config_patch:
        state["config"] = merge_config(state["config"], config_patch)
    if events is not None:
        state["events"] = _events(events)
    _write_json(config_path(), state)
    return state


def parse_kv(text: str) -> dict[str, float]:
    """`fast=9 slow=21 weight=1.5` -> {"fast": 9.0, ...}. The tab's edit box uses this."""
    out: dict[str, float] = {}
    for token in text.replace(",", " ").split():
        if "=" not in token:
            raise CompoundError(f"expected name=value, got {token!r}")
        k, v = token.split("=", 1)
        try:
            out[k.strip()] = float(v)
        except ValueError as exc:
            raise CompoundError(f"{k}: {v!r} is not a number") from exc
    return out


def component_patch(cid: str, values: Mapping[str, float]) -> dict[str, Any]:
    """Split `weight`/`enabled` from parameters for one component."""
    if cid not in sc.BY_ID:
        raise CompoundError(f"unknown component {cid!r}")
    entry: dict[str, Any] = {"params": {}}
    for k, v in values.items():
        if k == "weight":
            entry["weight"] = v
        elif k == "enabled":
            entry["enabled"] = bool(v)
        else:
            entry["params"][k] = v
    return {"components": {cid: entry}}


def aggregate_patch(values: Mapping[str, float]) -> dict[str, Any]:
    agg = {s.name for s in sc.AGGREGATE_SPECS}
    ex = {s.name for s in sc.EXECUTION_SPECS}
    out: dict[str, Any] = {"aggregate": {}, "execution": {}}
    for k, v in values.items():
        if k in agg:
            out["aggregate"][k] = v
        elif k in ex:
            out["execution"][k] = v
        else:
            raise CompoundError(f"unknown setting {k!r}; aggregate: {', '.join(sorted(agg))}; "
                                f"execution: {', '.join(sorted(ex))}")
    return out


# -- network reads ---------------------------------------------------------------------------

Fetcher = Callable[..., Any]


def http_json(url: str, body: Mapping[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 - fixed public hosts
        return json.loads(resp.read().decode())


def http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 - fixed public hosts
        return resp.read().decode("utf-8", "replace")


def fetch_closed_candles(asset: str, *, now: float | None = None, bars: int = LIVE_BARS,
                         get: Fetcher = http_json) -> dict[str, np.ndarray]:
    """The last `bars` CLOSED 5m candles from Coinbase, oldest first, with gaps preserved."""
    now = time.time() if now is None else now
    product = f"{_asset(asset)}-USD"
    last_closed_start = (int(now) // 300) * 300 - 300
    rows: dict[int, list[float]] = {}
    end = last_closed_start + 300
    while len(rows) < bars:
        start = end - 300 * 300
        url = (COINBASE_CANDLES.format(product=product)
               + f"?granularity=300&start={_iso(start)}&end={_iso(end)}")
        try:
            payload = get(url)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise CompoundError(f"coinbase candles for {product}: {exc}") from exc
        if not isinstance(payload, list):
            raise CompoundError(f"coinbase candles for {product}: unexpected reply {str(payload)[:120]}")
        if not payload:
            break
        for row in payload:
            # Coinbase row order is [time, low, high, open, close, volume] -- not OHLCV.
            t, lo, hi, op, cl, vol = (float(x) for x in row[:6])
            if t + 300 <= now and t <= last_closed_start:
                rows[int(t)] = [op, hi, lo, cl, vol]
        end = start
        if end < last_closed_start - 300 * bars * 2:
            break
    if len(rows) < 50:
        raise CompoundError(f"coinbase returned only {len(rows)} closed 5m bars for {product}")
    ts = np.array(sorted(rows)[-bars:], dtype="int64")
    vals = np.array([rows[t] for t in ts], dtype="float64")
    return {"ts": ts, "open": vals[:, 0], "high": vals[:, 1], "low": vals[:, 2],
            "close": vals[:, 3], "volume": vals[:, 4]}


def _iso(epoch: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def fetch_hyperliquid(asset: str, depth_bps: float, *, need_book: bool,
                      post: Fetcher = http_json) -> dict[str, Any]:
    """Funding, premium, open interest and (optionally) book imbalance for `asset`."""
    coin = _asset(asset)
    try:
        meta, ctxs = post(HYPERLIQUID_INFO, {"type": "metaAndAssetCtxs"})
        names = [u.get("name") for u in meta.get("universe", [])]
        ctx = ctxs[names.index(coin)]
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise CompoundError(f"hyperliquid has no context for {coin}: {exc}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise CompoundError(f"hyperliquid: {exc}") from exc
    out: dict[str, Any] = {}
    for key, name in (("funding", "funding"), ("premium", "premium"), ("oi", "openInterest"),
                      ("mark", "markPx"), ("oracle", "oraclePx")):
        try:
            v = float(ctx.get(name))
            if math.isfinite(v):
                out[key] = v
        except (TypeError, ValueError):
            pass
    if need_book:
        try:
            book = post(HYPERLIQUID_INFO, {"type": "l2Book", "coin": coin})
            out["book_imbalance"] = book_imbalance(book, depth_bps)
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as exc:
            out["book_error"] = str(exc)
    return out


def book_imbalance(book: Mapping[str, Any], depth_bps: float) -> float | None:
    """(bid size - ask size) / (bid + ask) within depth_bps of the mid."""
    bids, asks = book["levels"][0], book["levels"][1]
    if not bids or not asks:
        return None
    best_bid, best_ask = float(bids[0]["px"]), float(asks[0]["px"])
    mid = (best_bid + best_ask) / 2.0
    lo, hi = mid * (1 - depth_bps / 1e4), mid * (1 + depth_bps / 1e4)
    b = sum(float(x["sz"]) for x in bids if float(x["px"]) >= lo)
    a = sum(float(x["sz"]) for x in asks if float(x["px"]) <= hi)
    return None if a + b <= 0 else (b - a) / (b + a)


def headline_hits(asset: str, window_min: float, *, now: float | None = None,
                  get_text: Callable[[str], str] = http_text) -> list[dict[str, Any]]:
    """Headlines naming the asset within the last `window_min` minutes, across NEWS_FEEDS."""
    import re

    now = time.time() if now is None else now
    names = ASSET_NAMES.get(_asset(asset), (asset.lower(),))
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I)
    hits, failures = [], []
    for url in NEWS_FEEDS:
        try:
            root = ET.fromstring(get_text(url))
        except (urllib.error.URLError, OSError, ET.ParseError, ValueError) as exc:
            failures.append(f"{url}: {exc}")
            continue
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            when = item.findtext("pubDate")
            try:
                dt = parsedate_to_datetime(when) if when else None
                # RFC 822 "-0000" parses as naive; .timestamp() would then read it as LOCAL time.
                ts = None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()
            except (TypeError, ValueError):
                ts = None
            if ts is None or now - ts > window_min * 60 or ts > now + 300:
                continue
            if pattern.search(title):
                hits.append({"ts": int(ts), "title": title[:200], "feed": url})
    if failures and len(failures) == len(NEWS_FEEDS):
        raise CompoundError("; ".join(failures))
    return hits


# -- the forward ledger ----------------------------------------------------------------------


def read_ledger(asset: str) -> list[dict[str, Any]]:
    path = forward_path(asset)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a torn final line from an interrupted append
        if isinstance(row, dict):
            out.append(row)
    return out


def _append(asset: str, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    path = forward_path(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows))


def _needs(cfg: Mapping[str, Any], *ids: str) -> bool:
    return any(cfg["components"][i]["enabled"] for i in ids)


def live_inputs(asset: str, cfg: Mapping[str, Any], events: Sequence[Mapping[str, Any]], *,
                now: float | None = None, get: Fetcher = http_json, post: Fetcher = http_json,
                get_text: Callable[[str], str] = http_text,
                ledger: Sequence[Mapping[str, Any]] = ()) -> tuple[sc.Bars, dict[str, Any], dict[str, Any]]:
    """(bars, aux, ctx snapshot) for scoring the latest closed bar."""
    asset = _asset(asset)
    raw = fetch_closed_candles(asset, now=now, get=get)
    segs = sc.contiguous_segments(raw["ts"])
    a, b = segs[-1]  # score the most recent contiguous run only: indicators restart at a gap
    bars = sc.Bars.from_mapping({k: v[a:b] for k, v in raw.items()})
    aux: dict[str, Any] = {"events": list(events), "live": {}}
    notes: dict[str, Any] = {}
    if _needs(cfg, "btc_lead") and asset != "BTC":
        try:
            ref = fetch_closed_candles("BTC", now=now, get=get)
            m = dict(zip(ref["ts"].tolist(), ref["close"].tolist(), strict=True))
            aux["btc_close"] = np.array([m.get(int(t), np.nan) for t in bars.ts])
        except CompoundError as exc:
            notes["btc_error"] = str(exc)
    ctx: dict[str, Any] = {}
    if _needs(cfg, "funding", "premium", "oi_flow", "book_imbalance"):
        depth = cfg["components"]["book_imbalance"]["params"]["depth_bps"]
        try:
            ctx = fetch_hyperliquid(asset, depth, need_book=_needs(cfg, "book_imbalance"), post=post)
        except CompoundError as exc:
            notes["hyperliquid_error"] = str(exc)
        if "funding" in ctx:
            aux["funding"] = {"ts": np.array([int(bars.ts[-1])]), "rate": np.array([ctx["funding"]])}
        live = aux["live"]
        for key in ("premium", "book_imbalance"):
            if key in ctx and ctx[key] is not None:
                live[key] = ctx[key]
        history = [(int(r["ts"]), float(r["oi"])) for r in ledger if r.get("type") == "ctx" and "oi" in r]
        if "oi" in ctx:
            history.append((int(time.time() if now is None else now), ctx["oi"]))
        live["oi_history"] = history
    if _needs(cfg, "gate_news"):
        window = cfg["components"]["gate_news"]["params"]["window_min"]
        try:
            hits = headline_hits(asset, window, now=now, get_text=get_text)
            aux["live"]["news_hits"] = hits
            notes["headlines"] = hits
        except CompoundError as exc:
            aux["live"]["news_error"] = str(exc)
            notes["news_error"] = str(exc)
    return bars, aux, {"ctx": ctx, "notes": notes}


def signal(asset: str, *, now: float | None = None, **fetchers: Any) -> dict[str, Any]:
    """Score the latest closed bar live and explain every component."""
    state = load_state()
    cfg = state["config"]
    bars, aux, extra = live_inputs(asset, cfg, state["events"], now=now,
                                   ledger=read_ledger(asset), **fetchers)
    ev = sc.evaluate(bars, cfg, aux)
    out = sc.explain(ev, -1, catalogue=False)
    out.update(asset=_asset(asset), config_hash=sc.config_hash(cfg), bars_used=len(bars),
               live=extra["ctx"], notes=extra["notes"])
    return out


def forward_tick(asset: str, *, now: float | None = None, **fetchers: Any) -> dict[str, Any]:
    """Record the call for the latest closed bar (once per config) and resolve older calls."""
    asset = _asset(asset)
    state = load_state()
    cfg = state["config"]
    h = sc.config_hash(cfg)
    ledger = read_ledger(asset)
    bars, aux, extra = live_inputs(asset, cfg, state["events"], now=now, ledger=ledger, **fetchers)
    ev = sc.evaluate(bars, cfg, aux)
    x = sc.explain(ev, -1)
    rows: list[dict[str, Any]] = []
    stamp = int(time.time() if now is None else now)
    ctx = extra["ctx"]
    if "oi" in ctx:
        rows.append({"type": "ctx", "ts": stamp, "asset": asset, "oi": ctx["oi"],
                     **{k: ctx[k] for k in ("funding", "premium", "mark") if k in ctx}})
    call_id = f"{asset}:{x['bar_ts']}:{h}"
    recorded = {r.get("id") for r in ledger if r.get("type") == "call"}
    new_call = call_id not in recorded
    if new_call:
        ungated = 0
        comp = x["composite"]
        if comp is not None and abs(comp) >= x["entry"]:
            ungated = 1 if comp > 0 else -1
        rows.append({
            "type": "call", "id": call_id, "asset": asset, "bar_ts": x["bar_ts"],
            "decided_at": x["decided_at"], "price": x["price"], "call": x["call"],
            "ungated": ungated, "composite": comp, "coverage": x["coverage"], "regime": x["regime"],
            "trend_stage": x["trend_stage"], "cycle_phase": x["cycle_phase"],
            "blocked_by": x["blocked_by"], "config_hash": h, "entry": x["entry"],
            "round_trip_bps": x["round_trip_bps"], "recorded_at": stamp,
            "scores": {r["id"]: r.get("score") for r in x["components"]
                       if r["kind"] == "score" and r["enabled"]},
        })
    closes = dict(zip(bars.ts.astype(int).tolist(), bars.close.tolist(), strict=True))
    resolved = {r.get("id") for r in ledger if r.get("type") == "resolve"}
    pending = [r for r in ledger if r.get("type") == "call" and r.get("id") not in resolved]
    n_resolved = 0
    for r in pending:
        nxt = closes.get(int(r["bar_ts"]) + 300)
        if nxt is None:
            continue
        ret = 1e4 * math.log(nxt / float(r["price"]))
        rows.append({"type": "resolve", "id": r["id"], "next_close": nxt, "ret_bps": round(ret, 4),
                     "resolved_at": stamp})
        n_resolved += 1
    _append(asset, rows)
    return {"asset": asset, "recorded": new_call, "call": x["call"], "composite": x["composite"],
            "bar_ts": x["bar_ts"], "regime": x["regime"], "blocked_by": x["blocked_by"],
            "resolved": n_resolved, "notes": extra["notes"]}


def _tally(pairs: Sequence[tuple[int, float]], rt: float) -> dict[str, Any]:
    decided = [(d, r) for d, r in pairs if d != 0 and r != 0]
    hits = sum(1 for d, r in decided if (r > 0) == (d > 0))
    n = len(decided)
    signed = [d * r for d, r in pairs if d != 0]
    return {
        "calls": sum(1 for d, _ in pairs if d != 0), "decided": n,
        "hit_rate": None if n == 0 else round(hits / n, 4),
        "z_vs_coinflip": None if n == 0 else round((hits - 0.5 * n) / math.sqrt(0.25 * n), 2),
        "gross_bps_per_call": None if not signed else round(sum(signed) / len(signed), 3),
        "net_bps_per_call_if_one_bar": None if not signed else round(sum(signed) / len(signed) - rt, 3),
    }


def forward_status(asset: str, config_hash: str | None = None, recent: int = 20) -> dict[str, Any]:
    """Forward hit rates: the compound, the compound without gates, and each component alone."""
    asset = _asset(asset)
    ledger = read_ledger(asset)
    res = {r["id"]: r for r in ledger if r.get("type") == "resolve"}
    calls, seen = [], set()
    for r in ledger:
        # Two tickers (the tab's auto-forward and a `forward --loop`) can append the same call;
        # count each bar/config once.
        if r.get("type") == "call" and r.get("id") not in seen and (
                config_hash is None or r.get("config_hash") == config_hash):
            seen.add(r.get("id"))
            calls.append(r)
    done = [(c, res[c["id"]]) for c in calls if c["id"] in res]
    rt = float(done[0][0].get("round_trip_bps", 16.0)) if done else 16.0
    dirs = {"UP": 1, "DOWN": -1}
    compound = _tally([(dirs.get(c["call"], 0), float(r["ret_bps"])) for c, r in done], rt)
    ungated = _tally([(int(c.get("ungated", 0)), float(r["ret_bps"])) for c, r in done], rt)
    per: dict[str, list[tuple[int, float]]] = {}
    for c, r in done:
        entry = float(c.get("entry", 0.25))
        for cid, s in (c.get("scores") or {}).items():
            d = 0 if s is None or abs(s) < entry else (1 if s > 0 else -1)
            per.setdefault(cid, []).append((d, float(r["ret_bps"])))
    rows = []
    for c in calls[-recent:]:
        r = res.get(c["id"])
        rows.append({"bar_ts": c["bar_ts"], "call": c["call"], "composite": c.get("composite"),
                     "price": c["price"], "regime": c.get("regime"), "blocked_by": c.get("blocked_by"),
                     "ret_bps": None if r is None else r["ret_bps"],
                     "hit": None if r is None or c["call"] == "FLAT" or r["ret_bps"] == 0
                     else (r["ret_bps"] > 0) == (c["call"] == "UP")})
    return {"asset": asset, "calls_recorded": len(calls), "resolved": len(done),
            "pending": len(calls) - len(done), "round_trip_bps": rt,
            "compound": compound, "compound_ungated": ungated,
            "components": {cid: _tally(v, rt) for cid, v in sorted(per.items())},
            "recent": rows}


# -- backtests -------------------------------------------------------------------------------

_PREPARED: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}


def _data_signature(asset: str) -> tuple[Any, ...]:
    """mtimes of every file `prepare` may read, so a re-fetch invalidates the cache."""
    from backtester.core.data import resolve_data_dir

    data = resolve_data_dir()
    paths = [p for p, _ in cbt.candidate_files(asset, data)] + [p for p, _ in cbt.candidate_files("BTC", data)]
    paths.append(data / f"{asset}_funding_1h.csv")
    return tuple(p.stat().st_mtime_ns if p.exists() else None for p in paths)


def _prepared(asset: str) -> dict[str, Any]:
    # The tab's process lives for days; without the signature it would keep backtesting the
    # data it first loaded after research/full_suite.py replaced the files.
    sig = _data_signature(asset)
    cached = _PREPARED.get(asset)
    if cached is None or cached[0] != sig:
        _PREPARED[asset] = (sig, cbt.prepare(asset))
    return _PREPARED[asset][1]


def _run_one(asset: str, label: str, cfg: Mapping[str, Any], events: Sequence[Mapping[str, Any]],
             run_id: str) -> dict[str, Any]:
    try:
        row = cbt.run_compound(asset, cfg, label=label, events=events, prepared=_prepared(asset))
    except (cbt.CompoundDataError, sc.ScorecardError, ValueError) as exc:
        return {"asset": asset, "label": label, "error": str(exc), "run_id": run_id}
    row["run_id"] = run_id
    row["finished_at"] = int(time.time())
    row["config"] = cfg
    return row


def append_results(rows: Sequence[Mapping[str, Any]]) -> None:
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, default=_jsonable) + "\n")


def _jsonable(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not math.isfinite(float(o)) else float(o)
    raise TypeError(type(o).__name__)


def read_results() -> list[dict[str, Any]]:
    path = results_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def backtest(asset: str, *, standalone: bool = True, perturb: bool = False, aggregate_grid: bool = False,
             workers: int = 1, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run the saved config (and its variants) on one asset's cached 5m data; append results."""
    return sweep([asset], standalone=standalone, perturb=perturb, aggregate_grid=aggregate_grid,
                 workers=workers, progress=progress)


def sweep(assets: Sequence[str], *, standalone: bool = True, perturb: bool = False,
          aggregate_grid: bool = False, workers: int = 1,
          progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    state = load_state()
    cfg, events = state["config"], state["events"]
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{sc.config_hash(cfg)}"
    jobs = []
    skipped = {}
    for a in assets:
        a = _asset(a)
        try:
            _prepared(a) if workers <= 1 else cbt.load_bars_5m(a)
        except cbt.CompoundDataError as exc:
            skipped[a] = str(exc).splitlines()[0]
            continue
        for label, c in cbt.variants(cfg, standalone=standalone, perturb=perturb, aggregate_grid=aggregate_grid):
            jobs.append((a, label, c))
    rows: list[dict[str, Any]] = []
    if workers <= 1:
        for i, (a, label, c) in enumerate(jobs, 1):
            rows.append(_run_one(a, label, c, events, run_id))
            if progress:
                progress(f"{i}/{len(jobs)} {a} {label}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_run_one, a, label, c, events, run_id) for a, label, c in jobs]
            for i, f in enumerate(as_completed(futs), 1):
                rows.append(f.result())
                if progress:
                    progress(f"{i}/{len(jobs)} {rows[-1]['asset']} {rows[-1]['label']}")
    append_results(rows)
    good = [r for r in rows if "error" not in r]
    return {"run_id": run_id, "configurations": len(jobs), "assets": sorted({j[0] for j in jobs}),
            "skipped": skipped, "errors": [r for r in rows if "error" in r][:20],
            "rows": [summary_row(r) for r in cbt.leaderboard(good, top=len(good))]}


def summary_row(r: Mapping[str, Any]) -> dict[str, Any]:
    """The flat row the tab and the CLI print."""
    f_is, f_oos = r["is"]["forecast"], r["oos"]["forecast"]
    p_oos = r["oos"]["pnl"]
    return {
        "asset": r["asset"], "label": r["label"], "ranked": r.get("ranked", False),
        "is_calls": f_is.get("calls"), "is_hit": f_is.get("hit_rate"),
        "oos_calls": f_oos.get("calls"), "oos_hit": f_oos.get("hit_rate"),
        "oos_z": f_oos.get("z_vs_coinflip"), "oos_base_up": f_oos.get("base_up_rate"),
        "oos_gross_bps": f_oos.get("gross_bps_per_call"), "oracle_net_bps": f_oos.get("oracle_net_bps"),
        "oos_return": p_oos.get("total_return"), "oos_sharpe": p_oos.get("sharpe"),
        "oos_trades": p_oos.get("trades"), "oos_max_dd": p_oos.get("max_drawdown"),
        "oos_fees_pct": p_oos.get("fees_pct"), "liquidations": p_oos.get("liquidations"),
        "leverage": r.get("leverage"), "bars": r.get("bars"), "source": r.get("source"),
        "run_id": r.get("run_id"),
    }


def latest_results(asset: str | None = None, top: int = 40) -> dict[str, Any]:
    rows = [r for r in read_results() if "error" not in r and "oos" in r]
    if asset:
        rows = [r for r in rows if r.get("asset") == _asset(asset)]
    if not rows:
        return {"run_id": None, "rows": [], "leaderboard": []}
    last = rows[-1]["run_id"]
    latest = [r for r in rows if r.get("run_id") == last]
    return {"run_id": last, "rows": [summary_row(r) for r in cbt.leaderboard(latest, top=len(latest))],
            "leaderboard": [summary_row(r) for r in cbt.leaderboard(rows, top=top)],
            "configurations_ever": len(rows)}


# -- CLI -------------------------------------------------------------------------------------


def _print_signal(x: Mapping[str, Any]) -> None:
    when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(x["decided_at"]))
    print(f"{x['asset']} next 5m from {when}: {x['call']}  composite={x['composite']}  "
          f"coverage={x['coverage']}  agreement={x['agreement']}")
    print(f"regime={x['regime']}  trend_stage={x['trend_stage']}  cycle_phase={x['cycle_phase']}  "
          f"round_trip={x['round_trip_bps']} bps  blocked_by={x['blocked_by'] or '-'}")
    for r in x["components"]:
        if not r["enabled"]:
            continue
        tail = r.get("score", r.get("detail", ""))
        if r["kind"] == "gate":
            tail = "BLOCK" if r.get("blocked") else "pass"
        print(f"  {r['id']:<20} {r['status']:<11} {tail!s:<8} w={r['weight']:<4} {r['family']}/{r['style']}")
    for k, v in (x.get("notes") or {}).items():
        print(f"  note {k}: {v}")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m soltui.compound", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    for name in ("signal", "forward", "status", "backtest", "results"):
        p = sub.add_parser(name)
        p.add_argument("--asset", default="SOL")
        p.add_argument("--json", action="store_true", help="print the raw result")
        if name == "forward":
            p.add_argument("--loop", action="store_true", help="tick once per closed 5m bar until killed")
        if name == "backtest":
            p.add_argument("--perturb", action="store_true")
            p.add_argument("--aggregate-grid", action="store_true")
    sw = sub.add_parser("sweep", help="every asset with cached 5m data, every variant")
    sw.add_argument("--assets", default="", help="comma list; default: every cached asset")
    sw.add_argument("--all-assets", action="store_true")
    sw.add_argument("--perturb", action="store_true", help="one-at-a-time parameter variations")
    sw.add_argument("--aggregate-grid", action="store_true", help="threshold/gate/leverage variations")
    sw.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    sub.add_parser("catalog")
    args = ap.parse_args(argv)
    try:
        if args.verb == "catalog":
            print(json.dumps(sc.catalog(), indent=2))
        elif args.verb == "signal":
            x = signal(args.asset)
            print(json.dumps(x, indent=2, default=_jsonable)) if args.json else _print_signal(x)
        elif args.verb == "forward":
            while True:
                out = forward_tick(args.asset)
                print(json.dumps(out, default=_jsonable), flush=True)
                if not args.loop:
                    break
                # Wake 5 s after the next 5m boundary so the bar has closed on the venue.
                time.sleep(300 - (time.time() % 300) + 5)
        elif args.verb == "status":
            print(json.dumps(forward_status(args.asset), indent=2))
        elif args.verb == "results":
            out = latest_results(args.asset)
            if args.json:
                print(json.dumps(out, indent=2))
            elif out["run_id"] is None:
                print(f"no compound backtest recorded for {_asset(args.asset)}; run: "
                      f"python3 -m soltui.compound backtest --asset {_asset(args.asset)}")
            else:
                _print_table({"run_id": out["run_id"], "configurations": len(out["rows"]),
                              "assets": [_asset(args.asset)], "skipped": {}, "rows": out["rows"]},
                             appended=False)
        elif args.verb == "backtest":
            out = backtest(args.asset, perturb=args.perturb, aggregate_grid=args.aggregate_grid,
                           progress=lambda s: print(s, file=sys.stderr))
            _print_table(out)
        else:
            assets = [a for a in args.assets.split(",") if a.strip()] or cbt.available_assets()
            out = sweep(assets, perturb=args.perturb, aggregate_grid=args.aggregate_grid,
                        workers=args.workers, progress=lambda s: print(s, file=sys.stderr, flush=True))
            _print_table(out)
    except (CompoundError, cbt.CompoundDataError, sc.ScorecardError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


def _print_table(out: Mapping[str, Any], *, appended: bool = True) -> None:
    where = f"results appended to {results_path()}" if appended else f"read from {results_path()}"
    print(f"run {out['run_id']}: {out['configurations']} configurations over {', '.join(out['assets']) or '-'} "
          f"(the multiple-testing denominator); {where}")
    for a, why in out["skipped"].items():
        print(f"  skipped {a}: {why}")
    hdr = f"{'asset':<5} {'label':<38} {'OOS calls':>9} {'hit':>6} {'z':>6} {'gross':>7} {'oracle':>7} {'return':>8} {'trades':>6} rank"
    print(hdr)
    for r in out["rows"][:40]:
        print(f"{r['asset']:<5} {r['label'][:38]:<38} {r['oos_calls'] or 0:>9} {_f(r['oos_hit']):>6} {_f(r['oos_z']):>6} "
              f"{_f(r['oos_gross_bps']):>7} {_f(r['oracle_net_bps']):>7} {_f(r['oos_return']):>8} {r['oos_trades'] or 0:>6} "
              f"{'yes' if r['ranked'] else 'thin'}")


def _f(v: Any) -> str:
    return "-" if v is None else f"{v:.3g}" if isinstance(v, float) else str(v)


if __name__ == "__main__":
    raise SystemExit(main())
