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
AND each enabled component as a standalone call. This paper module never places an order.
The console's separate manual Coinbase ticket has its own arming and submission controls.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import sys
import tempfile
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
from backtester.core import universe as cu  # noqa: E402

from backtester.core import perps  # noqa: E402
from backtester.core.types import Side  # noqa: E402

from .diagnostics import external_read
from . import config as config_mod  # noqa: E402
from . import wallet as wallet_mod  # noqa: E402

COINBASE_CANDLES = "https://api.exchange.coinbase.com/products/{product}/candles"
HYPERLIQUID_INFO = "https://api.hyperliquid.xyz/info"
NEWS_FEEDS = ("https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss")
USER_AGENT = "soltui-compound/1.0 (read-only research)"
LIVE_BARS = 600
# With adaptive weighting on, the fetched bars give each metric its track record even before the
# forward ledger has any history. Fetch up to the whole record window (two weeks = 4,032 bars,
# 14 Coinbase requests).
ADAPTIVE_LIVE_BARS = 4032
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
    from backtester.core.assets import require_active_asset

    try:
        require_active_asset(a)
    except ValueError as exc:
        raise CompoundError(str(exc)) from None
    return a


# -- saved configuration ---------------------------------------------------------------------


# The coins the compound runs on: the owner's ten, screened from the top 50
# (backtester/core/universe.py COMPOUND_5M_UNIVERSE). A coin outside it with cached data can still
# be backtested from the CLI with --asset; the tab, Backtest all and unattended training stay on these.
COINS = cu.COMPOUND_5M_UNIVERSE


def coins() -> tuple[str, ...]:
    """The coins the tab, Backtest all coins and unattended training run on."""
    return tuple(COINS)


def live_capable(asset: str) -> bool:
    """Live calls and forward tests read Coinbase candles; coins from other venues are
    backtest-only until those venues get live adapters."""
    from backtester.core.fetch_minutes_alt import ASSET_VENUE

    return _asset(asset) not in ASSET_VENUE


def _read_raw() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CompoundError(f"unreadable {path}: {exc}") from exc
    return raw if isinstance(raw, dict) else {}


# Autopilot: the owner asked (2026-11-07) for a hands-off, self-optimizing forward trainer. It is a
# top-level flag in config.json, outside the scorecard config, so the backtester's defaults and the
# strategy cards stay what they are. Missing means on.
AUTOPILOT_DEFAULT = True


def autopilot_enabled(raw: Mapping[str, Any] | None = None) -> bool:
    raw = _read_raw() if raw is None else raw
    value = raw.get("autopilot")
    return AUTOPILOT_DEFAULT if value is None else bool(value)


def _autopilot_overlay(cfg: dict[str, Any]) -> dict[str, Any]:
    """Tuning is the search that proposes better settings; autopilot adopts what it finds, so it
    needs the search running. The overlay is part of the effective config, so its hash says so."""
    if cfg["aggregate"]["tune"]:
        return cfg
    out = json.loads(json.dumps(cfg))
    out["aggregate"]["tune"] = 1
    return sc.normalise_config(out)


@contextlib.contextmanager
def _state_lock() -> Any:
    """One writer at a time. Every coin's unattended process adopts tuned settings into the same
    config.json; without the lock two read-modify-writes interleave and one coin's adoption is lost."""
    import fcntl

    path = home() / "config.json.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def merge_patch(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge two partial configs (b wins). Used to stack a coin's own settings on the base."""
    out = json.loads(json.dumps(a))
    for k, v in b.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = merge_patch(out[k], v)
        else:
            out[k] = json.loads(json.dumps(v))
    return out


def load_state(asset: str | None = None) -> dict[str, Any]:
    """{"config", "base", "events", "overrides", "asset", "autopilot"}.

    Every coin has its own set of numbers: `config` is the shared base with that coin's own
    overrides stacked on top. Learned weights are per coin anyway (each coin has its own ledger
    and its own backtest); the overrides are for settings a coin should not share, such as
    adopted tuned parameters.
    """
    raw = _read_raw()
    path = config_path()
    try:
        base = sc.normalise_config(raw.get("config"))
    except sc.ScorecardError as exc:
        raise CompoundError(f"{path}: {exc}") from exc
    overrides = {k: v for k, v in (raw.get("assets") or {}).items() if isinstance(v, Mapping)}
    a = _asset(asset) if asset else None
    cfg = base
    if a and overrides.get(a):
        cfg = merge_config(base, overrides[a])
    pilot = autopilot_enabled(raw)
    if pilot:
        cfg = _autopilot_overlay(cfg)
    return {"config": cfg, "base": base, "events": _events(raw.get("events") or []),
            "overrides": overrides, "asset": a, "autopilot": pilot}


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
               events: Sequence[Any] | None = None, reset: bool = False,
               asset: str | None = None, reset_all: bool = False,
               autopilot: bool | None = None) -> dict[str, Any]:
    """Save a partial update to the shared base, or to ONE coin's own settings when `asset` is
    given. reset clears that coin's own settings (or, without a coin, the base); reset_all also
    clears every coin's own settings. The event list is data and is never reset; neither is the
    autopilot switch, which only `autopilot` changes."""
    with _state_lock():
        return _save_state_locked(config_patch, events, reset, asset, reset_all, autopilot)


def _save_state_locked(config_patch: Mapping[str, Any] | None, events: Sequence[Any] | None,
                       reset: bool, asset: str | None, reset_all: bool,
                       autopilot: bool | None) -> dict[str, Any]:
    raw = _read_raw()
    state = load_state()
    base, overrides = state["base"], dict(state["overrides"])
    a = _asset(asset) if asset else None
    if reset or reset_all:
        if a and not reset_all:
            overrides.pop(a, None)
        else:
            base = sc.default_config()
            if reset_all:
                overrides = {}
    if config_patch:
        if a:
            merged = merge_patch(overrides.get(a, {}), config_patch)
            merge_config(base, merged)  # validate the coin's stacked config before saving
            overrides[a] = merged
        else:
            base = merge_config(base, config_patch)
    ev = _events(events) if events is not None else _events(raw.get("events") or [])
    out: dict[str, Any] = {"config": base, "events": ev, "assets": overrides}
    pilot = raw.get("autopilot") if autopilot is None else bool(autopilot)
    if pilot is not None:
        out["autopilot"] = bool(pilot)
    _write_json(config_path(), out)
    return load_state(a)


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


@external_read("compound.http_json")
def http_json(url: str, body: Mapping[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 - fixed public hosts
        return json.loads(resp.read().decode())


@external_read("compound.http_text")
def http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 - fixed public hosts
        return resp.read().decode("utf-8", "replace")


def candle_cache_path(asset: str, seconds: int = 300) -> Path:
    suffix = "-1m" if seconds == 60 else "" if seconds == 300 else f"-{seconds}s"
    return home() / "candles" / f"{_asset(asset)}{suffix}.npz"


def _load_candle_cache(asset: str, seconds: int = 300) -> dict[int, list[float]]:
    path = candle_cache_path(asset, seconds)
    if not path.exists():
        return {}
    try:
        with np.load(path, allow_pickle=False) as z:
            return {int(t): [float(v) for v in row] for t, row in zip(z["ts"], z["rows"], strict=True)}
    except (OSError, ValueError, KeyError):
        return {}


def _save_candle_cache(asset: str, rows: Mapping[int, list[float]], keep: int, seconds: int = 300) -> None:
    ts = np.array(sorted(rows)[-keep:], dtype="int64")
    path = candle_cache_path(asset, seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".npz", delete=False) as handle:
        tmp = Path(handle.name)
        try:
            np.savez(handle, ts=ts, rows=np.array([rows[int(t)] for t in ts], dtype="float64").reshape(-1, 5))
            handle.close()
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def _get_with_retry(get: Fetcher, url: str, sleep: Callable[[float], None] = time.sleep) -> Any:
    """Retry a rate limit (429) or a server error a few times; with every coin ticking at once,
    a 429 at the 5-minute boundary is expected, not exceptional."""
    delay = 1.0
    for attempt in range(4):
        try:
            return get(url)
        except urllib.error.HTTPError as exc:
            if attempt == 3 or not (exc.code == 429 or exc.code >= 500):
                raise
        sleep(delay)
        delay *= 2
    return get(url)


def fetch_closed_candles(asset: str, *, now: float | None = None, bars: int = LIVE_BARS,
                         get: Fetcher = http_json, cache: bool = True, seconds: int = 300,
                         sleep: Callable[[float], None] = time.sleep) -> dict[str, np.ndarray]:
    """The last `bars` CLOSED Coinbase candles, oldest first, with gaps preserved.

    Closed candles never change, so they are cached per coin and only the bars after the newest
    cached one are requested: a tick then costs one request instead of fourteen, which is what
    lets every coin forward-test at once inside the venue's rate limit.
    """
    if seconds not in (60, 300, 900, 3600, 21600, 86400):
        raise ValueError("unsupported Coinbase candle granularity")
    now = time.time() if now is None else now
    product = f"{_asset(asset)}-USD"
    last_closed_start = (int(now) // seconds) * seconds - seconds
    need_from = last_closed_start - seconds * (bars - 1)
    rows: dict[int, list[float]] = {}
    if cache:
        rows = {t: r for t, r in _load_candle_cache(asset, seconds).items()
                if need_from <= t <= last_closed_start}
    # Revisit recent minutes so a temporary publication gap can settle on a later tick.
    overlap = 32 * seconds if seconds == 60 else 0
    stop_at = max(need_from - seconds, max(rows) - overlap) if rows else need_from - seconds
    end = last_closed_start + seconds
    while end > stop_at:
        start = max(end - 299 * seconds, stop_at)
        url = (COINBASE_CANDLES.format(product=product)
               + f"?granularity={seconds}&start={_iso(start)}&end={_iso(end)}")
        try:
            payload = _get_with_retry(get, url, sleep)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise CompoundError(f"coinbase candles for {product}: {exc}") from exc
        if not isinstance(payload, list):
            raise CompoundError(f"coinbase candles for {product}: unexpected reply {str(payload)[:120]}")
        for row in payload:
            t, lo, hi, op, cl, vol = (float(x) for x in row[:6])
            if t + seconds <= now and need_from <= t <= last_closed_start:
                rows[int(t)] = [op, hi, lo, cl, vol]
        if not payload and not rows:
            break
        end = start
    if len(rows) < 50:
        raise CompoundError(f"coinbase returned only {len(rows)} closed {seconds}s bars for {product}")
    if cache:
        _save_candle_cache(asset, rows, max(bars, ADAPTIVE_LIVE_BARS), seconds)
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
    if failures:
        # One dead feed must not read as "no headlines": the gate fails closed.
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


def _append(asset: str, rows: Sequence[Mapping[str, Any]], *, unique: bool = False,
            not_after: int | None = None, clock: Callable[[], float] = time.time) -> list[Mapping[str, Any]]:
    """Append rows to a coin's ledger under a lock; return the rows written.

    unique: drop any call or resolve whose id the ledger already holds, checked inside the lock.
    A forward tick reads the ledger, then spends seconds fetching candles before it writes, so two
    writers (an unattended trainer and the console, say) both saw "not recorded" and both wrote
    the same bar (SOL, 2026-11-07). The re-check under the lock is what makes "once" true.
    """
    if not rows:
        return []
    import fcntl

    path = forward_path(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path.with_suffix(".ledger.lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if unique:
            existing = read_ledger(asset)
            have = {(r.get("type"), r.get("id")) for r in existing if r.get("type") in ("call", "resolve", "horizon_call", "horizon_resolve")}
            latest: dict[int, int] = {}
            for old in existing:
                if old.get("type") == "horizon_call":
                    h = int(old["minutes"])
                    latest[h] = max(latest.get(h, 0), int(old["start"]))
            rows = [r for r in rows if (r.get("type") not in ("call", "resolve", "horizon_call", "horizon_resolve")
                    or (r["type"], r.get("id")) not in have) and (r.get("type") != "horizon_call"
                    or int(r["start"]) >= latest.get(int(r["minutes"]), 0) + int(r["minutes"]) * 60)]
        if not_after is not None and clock() >= not_after:
            return []  # never record a forecast after its measured interval begins
        if rows:
            with path.open("a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows))
    finally:
        os.close(fd)
    return list(rows)


def component_sig(cid: str, params: Mapping[str, Any]) -> str:
    """Short hash of one metric's parameters. A learned track record only carries over between
    calls whose metric was computed the same way."""
    body: dict[str, Any] = {"id": cid, "params": dict(params)}
    version = sc.FORMULA_VERSIONS.get(cid, 1)
    if version != 1:  # unchanged metrics keep the signatures their records already carry
        body["formula"] = version
    text = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode()).hexdigest()[:10]


def ledger_seed(ledger: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any],
                window_start: int) -> dict[str, list[tuple[int, float, float]]]:
    """Resolved forward calls made BEFORE the scored bars, per metric, as (k, hit, call).

    k is the call's bar index relative to the first scored bar (k < 0). Calls inside the scored
    bars are counted again by `scorecard.adaptive_counts` from the bars themselves, so only
    earlier ones are taken, and only when the metric's settings then match its settings now.
    Calls older than the record window are left out; adaptive_counts expires the rest on time.
    """
    agg = cfg["aggregate"]
    entry = float(agg["entry"])
    window = int(agg["adaptive_window"])
    outcome = {r["id"]: float(r["ret_bps"]) for r in ledger if r.get("type") == "resolve" and "ret_bps" in r}
    sigs = {cid: component_sig(cid, e["params"]) for cid, e in cfg["components"].items()}
    seed: dict[str, list[tuple[int, float, float]]] = {}
    # One call per bar: the same bar recorded under two settings (two writers, or a settings change
    # between them) is one outcome, and counting it twice would double its weight in the record.
    seen: set[str] = set()
    seen_bars: set[int] = set()
    for call in reversed(ledger):  # the latest record of a bar wins
        if call.get("type") != "call" or call.get("id") in seen or call.get("id") not in outcome:
            continue
        seen.add(call["id"])
        if int(call["bar_ts"]) in seen_bars:
            continue
        seen_bars.add(int(call["bar_ts"]))
        k = (int(call["bar_ts"]) - window_start) // 300
        ret = outcome[call["id"]]
        if k >= 0 or k + 1 < -window or ret == 0:
            continue
        for cid, s in (call.get("scores") or {}).items():
            if s is None or abs(s) < entry or (call.get("sigs") or {}).get(cid) != sigs.get(cid):
                continue
            seed.setdefault(cid, []).append((k, 1.0 if (s > 0) == (ret > 0) else 0.0, 1.0))
    return seed


def _needs(cfg: Mapping[str, Any], *ids: str) -> bool:
    return any(cfg["components"][i]["enabled"] for i in ids)


def live_inputs(asset: str, cfg: Mapping[str, Any], events: Sequence[Mapping[str, Any]], *,
                now: float | None = None, get: Fetcher = http_json, post: Fetcher = http_json,
                get_text: Callable[[str], str] = http_text,
                ledger: Sequence[Mapping[str, Any]] = ()) -> tuple[sc.Bars, dict[str, Any], dict[str, Any]]:
    """(bars, aux, ctx snapshot) for scoring the latest closed bar."""
    asset = _asset(asset)
    agg = cfg["aggregate"]
    n_bars = max(LIVE_BARS, min(ADAPTIVE_LIVE_BARS, int(agg["adaptive_window"]))) if agg["adaptive"] else LIVE_BARS
    raw = fetch_closed_candles(asset, now=now, get=get, bars=n_bars)
    closes_all = dict(zip(raw["ts"].astype(int).tolist(), raw["close"].tolist(), strict=True))
    segs = sc.contiguous_segments(raw["ts"])
    a, b = segs[-1]  # score the most recent contiguous run only: indicators restart at a gap
    bars = sc.Bars.from_mapping({k: v[a:b] for k, v in raw.items()})
    aux: dict[str, Any] = {"events": list(events), "live": {}}
    if cbt.maintenance_fraction(asset) is not None:
        aux["maintenance_fraction"] = cbt.maintenance_fraction(asset)
    if agg["adaptive"]:
        aux["adaptive_seed"] = ledger_seed(ledger, cfg, int(bars.ts[0]))
    notes: dict[str, Any] = {}
    if _needs(cfg, "btc_lead") and asset != "BTC":
        try:
            ref = fetch_closed_candles("BTC", now=now, get=get, bars=n_bars)
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
    return bars, aux, {"ctx": ctx, "notes": notes, "closes": closes_all}


# -- the wallet: read from Settings, never from a key ------------------------------------------
#
# Wallet information has ONE home: the soltui Settings (`solana_address`, edited on the Settings
# tab, stored in ~/.config/soltui/config.yaml at mode 600). Private keys stay in their key files; nothing
# here reads them: sizing a call needs balances, which are public. Jupiter Perps accepts SOL, USDC
# and USDT as collateral, so those are the "usable" balances. Stablecoins are matched by MINT, not
# by symbol text, because anyone can mint a token called "USDC".

COLLATERAL_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCE8BenwNYB": "USDT",
}
WALLET_LABEL = "wallet (live)"
WALLET_TTL_S = 240  # one scan per forward tick at most; balances do not need 5-second freshness
_WALLET_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def wallet_balances(address: str | None, *, fetch: Fetcher | None = None,
                    now: float | None = None) -> dict[str, Any]:
    """Usable collateral at the Settings address, or why it is unavailable. Never a guess."""
    if not address or not wallet_mod.valid_solana_address(address):
        return {"available": False, "label": WALLET_LABEL,
                "reason": "no valid solana_address in Settings (Settings tab)"}
    now = time.time() if now is None else now
    hit = _WALLET_CACHE.get(address)
    if fetch is None and hit and now - hit[0] < WALLET_TTL_S:
        return hit[1]
    scan = wallet_mod.scan_solana(address, fetch or wallet_mod.HttpFetcher(budget_s=20)).to_dict()
    parts: dict[str, float] = {}
    unknown: list[str] = []
    native = scan.get("native") or {}
    if (native.get("amount") or 0) > 0:
        if native.get("usd") is None:
            unknown.append("SOL")
        else:
            parts["SOL"] = float(native["usd"])
    for h in scan.get("holdings") or []:
        sym = COLLATERAL_MINTS.get(h.get("mint", ""))
        if not sym or not h.get("included", True):
            continue
        if h.get("usd") is None:
            unknown.append(sym)
        else:
            parts[sym] = parts.get(sym, 0.0) + float(h["usd"])
    if scan.get("status") == "error" and not parts:
        out = {"available": False, "label": WALLET_LABEL,
               "reason": "; ".join(e["message"] for e in scan.get("errors") or []) or "wallet scan failed"}
    else:
        out = {"available": True, "label": WALLET_LABEL, "address_tail": address[-4:],
               "usable_usd": round(sum(parts.values()), 2), "parts": {k: round(v, 2) for k, v in parts.items()},
               "unpriced": unknown, "complete": not unknown and scan.get("status") == "ok",
               "errors": [e["message"] for e in scan.get("errors") or []]}
    if fetch is None:
        _WALLET_CACHE[address] = (now, out)
    return out


HYPERLIQUID_LABEL = "Hyperliquid (live)"
_HL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _num(value: Any) -> float:
    """A Hyperliquid decimal string as a float; a missing or unparseable field is an error, not 0."""
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"non-finite number {value!r}")
    return out


def hyperliquid_balances(address: str | None, *, post: Fetcher = http_json,
                         now: float | None = None, cache: bool = True) -> dict[str, Any]:
    """Free perp margin and open positions on the owner's Hyperliquid account. Read-only.

    Two public `info` calls; no key, no signature. Usable collateral is the perp account's
    `withdrawable` (margin not tied up in positions). Spot USDC is reported but not counted: it
    must be moved to the perp account before it can margin a trade.
    """
    from . import hdwallet

    try:
        hdwallet.validate_evm_address(address or "")
    except hdwallet.ExtKeyError:
        return {"available": False, "label": HYPERLIQUID_LABEL,
                "reason": "no valid hyperliquid_address in Settings (Settings tab)"}
    addr = (address or "").strip()
    now = time.time() if now is None else now
    hit = _HL_CACHE.get(addr.lower())
    if cache and hit and now - hit[0] < WALLET_TTL_S:
        return hit[1]
    try:
        perp = post(HYPERLIQUID_INFO, {"type": "clearinghouseState", "user": addr})
        spot = post(HYPERLIQUID_INFO, {"type": "spotClearinghouseState", "user": addr})
        withdrawable = _num(perp["withdrawable"])
        account_value = _num(perp["marginSummary"]["accountValue"])
        spot_usdc = sum(_num(b["total"]) - _num(b.get("hold", 0)) for b in spot.get("balances") or []
                        if b.get("coin") == "USDC")
        positions = []
        for row in perp.get("assetPositions") or []:
            pos = row.get("position") or {}
            liq = pos.get("liquidationPx")
            positions.append({"coin": pos.get("coin"), "size": _num(pos["szi"]), "entry": _num(pos["entryPx"]),
                              "liquidation_price": None if liq in (None, "") else _num(liq),
                              "unrealized_pnl_usd": round(_num(pos.get("unrealizedPnl", 0)), 2),
                              "leverage": (pos.get("leverage") or {}).get("value")})
    except Exception as exc:  # noqa: BLE001 - a failed read is reported, never turned into a balance
        return {"available": False, "label": HYPERLIQUID_LABEL, "reason": f"Hyperliquid read failed: {exc}"}
    out = {"available": True, "label": HYPERLIQUID_LABEL, "venue": "hyperliquid", "address_tail": addr[-4:],
           "usable_usd": round(withdrawable, 2), "parts": {"perp free margin": round(withdrawable, 2)},
           "account_value_usd": round(account_value, 2), "spot_usdc_not_counted": round(spot_usdc, 2),
           "positions": positions, "unpriced": [], "complete": True, "errors": [],
           "empty_reason": ("no free margin on the Hyperliquid perp account (account value "
                            f"${account_value:,.2f}); deposit USDC to Hyperliquid"
                            + (f", or move the ${spot_usdc:,.2f} spot USDC to perps" if spot_usdc > 0 else ""))}
    if cache:
        _HL_CACHE[addr.lower()] = (now, out)
    return out


def size_call(wallet: Mapping[str, Any], bars: sc.Bars, cfg: Mapping[str, Any], call: str,
              asset: str | None = None) -> dict[str, Any]:
    """Position size for this call at the wallet's usable collateral, or why there is none.

    The trade may lose `risk_pct` of usable collateral if price reaches the stop (`stop_atr` x ATR,
    the same stop the liquidation gate checks) PLUS the round-trip cost, and may not exceed
    collateral x leverage. The smaller of the two wins. Liquidation prices come from the engine's
    venue formula (`backtester.core.perps.liquidation_price`), not from 1/leverage.
    """
    if not wallet.get("available"):
        return {"available": False, "reason": wallet.get("reason", "wallet unavailable")}
    usable = float(wallet["usable_usd"])
    if usable <= 0:
        return {"available": False,
                "reason": wallet.get("empty_reason") or "no SOL, USDC or USDT at the Settings address"}
    ex = cfg["execution"]
    lev = float(ex["leverage"])
    gate = cfg["components"]["gate_liquidation"]["params"]
    price = float(bars.close[-1])
    atr_now = float(sc.atr(bars, int(gate["atr"]))[-1])
    if not math.isfinite(atr_now) or atr_now <= 0:
        return {"available": False, "reason": "ATR not defined yet for the stop distance"}
    stop_pct = float(gate["stop_atr"]) * atr_now / price
    cost_pct = sc.round_trip_bps(ex["fee_bps"], ex["slippage_bps"]) / 1e4
    risk_usd = usable * float(ex["risk_pct"]) / 100.0
    max_notional = usable * lev
    risk_notional = risk_usd / (stop_pct + cost_pct)
    notional = min(max_notional, risk_notional)
    collateral = notional / lev
    costs = cbt.engine_config(cfg, asset).costs
    liq = {}
    for side, name in ((Side.LONG, "long"), (Side.SHORT, "short")):
        info = perps.liquidation_price(price, side, collateral, notional, 0.0, costs)
        liq[name] = round(info.price, 4) if info.in_domain else None
    return {
        "available": True, "label": WALLET_LABEL, "usable_usd": round(usable, 2), "leverage": lev,
        "risk_pct": float(ex["risk_pct"]), "stop_pct": round(100 * stop_pct, 4), "cost_pct": round(100 * cost_pct, 4),
        "max_notional_usd": round(max_notional, 2), "risk_notional_usd": round(risk_notional, 2),
        "notional_usd": round(notional, 2), "collateral_usd": round(collateral, 2),
        "round_trip_cost_usd": round(notional * cost_pct, 2),
        "loss_at_stop_usd": round(notional * (stop_pct + cost_pct), 2),
        "bound_by": "risk" if risk_notional <= max_notional else "leverage",
        "side": {"UP": "long", "DOWN": "short"}.get(call), "liquidation_price": liq,
        "complete": bool(wallet.get("complete")),
    }


def _wallet_and_size(address: str | None, cfg: Mapping[str, Any], bars: sc.Bars, call: str,
                     wallet_fetch: Fetcher | None, asset: str | None = None,
                     hyperliquid_address: str | None = None,
                     hl_post: Fetcher | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """The owner trades these coins on Hyperliquid, so its perp account sizes the call when Settings
    has its address; the Solana wallet (Jupiter collateral) is the fallback."""
    if not cfg["execution"]["use_wallet"]:
        off = {"available": False, "label": WALLET_LABEL, "reason": "use_wallet=0"}
        return off, {"available": False, "reason": "use_wallet=0"}
    try:
        if hyperliquid_address:
            w = hyperliquid_balances(hyperliquid_address, post=hl_post or http_json, cache=hl_post is None)
        else:
            w = wallet_balances(address, fetch=wallet_fetch)
    except Exception as exc:  # noqa: BLE001 - a wallet read must never break the call itself
        w = {"available": False, "label": WALLET_LABEL, "reason": f"{type(exc).__name__}: {exc}"}
    return w, size_call(w, bars, cfg, call, asset)


def signal(asset: str, *, now: float | None = None, wallet_address: str | None = None,
           wallet_fetch: Fetcher | None = None, hyperliquid_address: str | None = None,
           hl_post: Fetcher | None = None, **fetchers: Any) -> dict[str, Any]:
    """Score the latest closed bar live, explain every component, and size it to the wallet."""
    state = load_state(asset)
    cfg = state["config"]
    bars, aux, extra = live_inputs(asset, cfg, state["events"], now=now,
                                   ledger=read_ledger(asset), **fetchers)
    ev = sc.evaluate(bars, cfg, aux)
    out = sc.explain(ev, -1, catalogue=False)
    wallet, sizing = _wallet_and_size(wallet_address, cfg, bars, out["call"], wallet_fetch, asset,
                                      hyperliquid_address, hl_post)
    out.update(asset=_asset(asset), config_hash=sc.config_hash(cfg), bars_used=len(bars),
               live=extra["ctx"], notes=extra["notes"], wallet=wallet, sizing=sizing)
    return out


def last_adoptions(ledger: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """metric id -> time (epoch s) its tuned settings were last adopted for this coin."""
    out: dict[str, int] = {}
    for r in ledger:
        if r.get("type") == "adopt" and r.get("metric"):
            out[r["metric"]] = max(out.get(r["metric"], 0), int(r.get("ts") or 0))
    return out


def auto_adopt(asset: str, state: Mapping[str, Any], components: Sequence[Mapping[str, Any]],
               ledger: Sequence[Mapping[str, Any]], stamp: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Save the settings tuning moved to as this coin's own numbers (autopilot only).

    Tuning already gates every move: a neighbour must beat the current settings with posterior
    probability `tune_confidence` on `tune_min_calls` decayed calls. What tuning cannot gate is the
    next evaluation: it starts again from the adopted settings, so without a memory across ticks
    the search could step once per bar. The `adopt` rows in the forward ledger are that memory: a
    metric adopts again only `tune_cooldown` bars after its last adoption.

    Returns ({metric: {"from", "to"}}, ledger rows). Writes nothing when autopilot is off.
    """
    if not state.get("autopilot"):
        return {}, []
    cfg = state["config"]
    cooldown_s = int(cfg["aggregate"]["tune_cooldown"]) * 300
    last = last_adoptions(ledger)
    patch: dict[str, Any] = {}
    adopted: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for row in components:
        cid, tuned = row.get("id"), row.get("tuned_params")
        if not tuned or cid not in cfg["components"]:
            continue
        current = cfg["components"][cid]["params"]
        if dict(tuned) == dict(current) or (cid in last and stamp - last[cid] < cooldown_s):
            continue
        patch[cid] = {"params": dict(tuned)}
        adopted[cid] = {"from": dict(current), "to": dict(tuned)}
        rows.append({"type": "adopt", "ts": stamp, "asset": _asset(asset), "metric": cid,
                     "from": dict(current), "to": dict(tuned), "tuned_since": row.get("tuned_since"),
                     "config_hash_before": sc.config_hash(cfg)})
    if patch:
        save_state({"components": patch}, asset=asset)
    return adopted, rows


def forward_tick(asset: str, *, now: float | None = None, wallet_address: str | None = None,
                 wallet_fetch: Fetcher | None = None, hyperliquid_address: str | None = None,
                 hl_post: Fetcher | None = None, **fetchers: Any) -> dict[str, Any]:
    """Record the call for the latest closed bar (once per config) and resolve older calls."""
    asset = _asset(asset)
    state = load_state(asset)
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
    sizing: dict[str, Any] = {"available": False}
    if new_call:
        _, sizing = _wallet_and_size(wallet_address, cfg, bars, x["call"], wallet_fetch, asset,
                                     hyperliquid_address, hl_post)
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
            "sigs": {r["id"]: component_sig(r["id"], r["params"]) for r in x["components"]
                     if r["kind"] == "score" and r["enabled"]},
            "adaptive": {r["id"]: r.get("adaptive_mult") for r in x["components"] if "adaptive_mult" in r},
            # Paper size at the wallet's value when the call was made; None when unavailable.
            "notional_usd": sizing.get("notional_usd") if sizing.get("available") else None,
        })
    # Resolve against every fetched bar, not only the newest contiguous run: a call made just
    # before a feed gap still has its next bar on the other side of an older gap.
    closes = extra["closes"]
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
    # Record first: a failed adoption must never cost the bar its call.
    written = _append(asset, rows, unique=True)
    if new_call and not any(r.get("type") == "call" for r in written):
        new_call = False  # another writer recorded this bar first
    n_resolved = sum(1 for r in written if r.get("type") == "resolve")
    horizon_stamp = int(time.time() if now is None else now)
    if new_call:
        saved_call = next(r for r in written if r.get("type") == "call")
    else:
        saved_call = next((r for r in ledger if r.get("type") == "call" and r.get("id") == call_id), None)
    if saved_call and horizon_stamp < int(saved_call["bar_ts"]) + 600:
        _record_horizon_calls(asset, saved_call, horizon_stamp,
                              clock=time.time if now is None else lambda: now)
    try:
        horizon_resolved = _resolve_horizons(asset, int(time.time() if now is None else now),
                                             get=fetchers.get("get", http_json))
    except (CompoundError, OSError, ValueError) as exc:
        horizon_resolved = 0
        extra["notes"]["horizon_error"] = str(exc)
    # The call above was made with the tuned settings already (tuning walks inside the evaluation);
    # adopting saves them so the next bar starts from them instead of re-deriving the walk.
    try:
        adopted, adopt_rows = auto_adopt(asset, state, x["components"], ledger, stamp)
    except CompoundError as exc:
        adopted, adopt_rows = {}, []
        extra["notes"] = [*extra["notes"], f"autopilot could not adopt tuned settings: {exc}"]
    _append(asset, adopt_rows)
    return {"asset": asset, "recorded": new_call, "call": x["call"], "composite": x["composite"],
            "bar_ts": x["bar_ts"], "regime": x["regime"], "blocked_by": x["blocked_by"],
            "resolved": n_resolved, "horizon_resolved": horizon_resolved, "notes": extra["notes"], "adopted": adopted,
            "autopilot": bool(state.get("autopilot")),
            "notional_usd": sizing.get("notional_usd") if sizing.get("available") else None}


HORIZON_MINUTES = (1, 5, 30)


def _record_horizon_calls(asset: str, call: Mapping[str, Any], stamp: int, *,
                          clock: Callable[[], float] = time.time) -> None:
    """Record separate forward horizons against the next future minute open.

    The same five-minute signal is evaluated at three horizons; these are not three
    independently trained predictors. Historical calls are deliberately not backfilled.
    """
    start = (stamp // 60 + 1) * 60
    rows = [{"type": "horizon_call", "id": f"{call['id']}:{start}:{h}m", "source_id": call["id"],
             "asset": asset, "minutes": h, "start": start, "finish": start + h * 60,
             "issued_at": stamp, "call": call["call"], "config_hash": call["config_hash"]}
            for h in HORIZON_MINUTES]
    _append(asset, rows, unique=True, not_after=start, clock=clock)


def _horizon_tick(asset: str, *, now: float | None = None, get: Fetcher = http_json) -> dict[str, Any]:
    """Sample the latest closed-five-minute signal once per horizon's cadence."""
    stamp = int(time.time() if now is None else now)
    ledger = read_ledger(asset)
    calls = [r for r in ledger if r.get("type") == "call" and r.get("recorded_at") is not None]
    call = max(calls, key=lambda r: int(r["recorded_at"]), default=None)
    recorded = False
    if call and int(call["recorded_at"]) <= stamp < int(call["bar_ts"]) + 600:
        before = len([r for r in ledger if r.get("type") == "horizon_call"])
        _record_horizon_calls(asset, call, stamp, clock=time.time if now is None else lambda: now)
        recorded = len([r for r in read_ledger(asset) if r.get("type") == "horizon_call"]) > before
    resolved = _resolve_horizons(asset, stamp, get=get)
    return {"asset": asset, "horizon_recorded": recorded, "horizon_resolved": resolved,
            "stale_signal": not call or stamp >= int(call["bar_ts"]) + 600}


def _resolve_horizons(asset: str, stamp: int, get: Fetcher = http_json) -> int:
    ledger = read_ledger(asset)
    done = {r.get("id") for r in ledger if r.get("type") == "horizon_resolve"}
    pending = [r for r in ledger if r.get("type") == "horizon_call" and r.get("id") not in done
               and r["finish"] <= stamp]
    if not pending:
        return 0
    raw = fetch_closed_candles(asset, now=stamp, bars=600, seconds=60, get=get)
    candles = {int(t): (float(o), float(c)) for t, o, c in zip(raw["ts"], raw["open"], raw["close"], strict=True)
               if math.isfinite(o) and math.isfinite(c) and o > 0 and c > 0}
    rows = []
    for call in pending:
        start, finish = int(call["start"]), int(call["finish"])
        if not all(t in candles for t in range(start, finish, 60)):
            continue
        op, close = candles[start][0], candles[finish - 60][1]
        if not (math.isfinite(op) and math.isfinite(close) and op > 0 and close > 0):
            continue
        rows.append({"type": "horizon_resolve", "id": call["id"], "open": op, "close": close,
                     "ret_bps": round(1e4 * math.log(close / op), 4), "resolved_at": stamp})
    return len(_append(asset, rows, unique=True))


def horizon_status(ledger: Sequence[Mapping[str, Any]], recent: int = 30) -> dict[str, Any]:
    """Independent results for each horizon; missing minute data stays pending."""
    resolves = {r["id"]: r for r in ledger if r.get("type") == "horizon_resolve"}
    calls = [r for r in ledger if r.get("type") == "horizon_call"]
    dirs = {"UP": 1, "DOWN": -1}
    by_horizon = {}
    for h in HORIZON_MINUTES:
        selected = [c for c in calls if c["minutes"] == h]
        done = [(c, resolves[c["id"]]) for c in selected if c["id"] in resolves]
        tally = _tally([(dirs.get(c["call"], 0), float(r["ret_bps"])) for c, r in done], 0)
        by_horizon[h] = {"recorded": len(selected), "resolved": len(done),
                         "pending": len(selected) - len(done), "hit_rate": tally["hit_rate"],
                         "decided": tally["decided"]}
    rows = []
    for c in calls[-recent:]:
        r = resolves.get(c["id"])
        ret = None if r is None else r["ret_bps"]
        rows.append({**c, "ret_bps": ret, "hit": None if ret is None or not ret or c["call"] == "FLAT"
                     else (ret > 0) == (c["call"] == "UP")})
    return {"horizons": by_horizon, "recent": rows}


def _tally(pairs: Sequence[tuple[int, float]], rt: float,
           costs: Sequence[float] | None = None) -> dict[str, Any]:
    decided = [(d, r) for d, r in pairs if d != 0 and r != 0]
    hits = sum(1 for d, r in decided if (r > 0) == (d > 0))
    n = len(decided)
    signed = [d * r for d, r in pairs if d != 0]
    net = [d * r - (costs[i] if costs is not None else rt)
           for i, (d, r) in enumerate(pairs) if d != 0]
    return {
        "calls": sum(1 for d, _ in pairs if d != 0), "decided": n,
        "hit_rate": None if n == 0 else round(hits / n, 4),
        "z_vs_coinflip": None if n == 0 else round((hits - 0.5 * n) / math.sqrt(0.25 * n), 2),
        "gross_bps_per_call": None if not signed else round(sum(signed) / len(signed), 3),
        "net_bps_per_call_if_one_bar": None if not net else round(sum(net) / len(net), 3),
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
    costs = [float(c.get("round_trip_bps", 16.0)) for c, _ in done]
    rt = sum(costs) / len(costs) if costs else 16.0
    dirs = {"UP": 1, "DOWN": -1}
    compound = _tally([(dirs.get(c["call"], 0), float(r["ret_bps"])) for c, r in done], rt, costs)
    ungated = _tally([(int(c.get("ungated", 0)), float(r["ret_bps"])) for c, r in done], rt, costs)
    per: dict[str, list[tuple[int, float]]] = {}
    per_costs: dict[str, list[float]] = {}
    for c, r in done:
        entry = float(c.get("entry", 0.25))
        for cid, s in (c.get("scores") or {}).items():
            d = 0 if s is None or abs(s) < entry else (1 if s > 0 else -1)
            per.setdefault(cid, []).append((d, float(r["ret_bps"])))
            per_costs.setdefault(cid, []).append(float(c.get("round_trip_bps", 16.0)))
    rows = []
    for c in calls[-recent:]:
        r = res.get(c["id"])
        rows.append({"bar_ts": c["bar_ts"], "call": c["call"], "composite": c.get("composite"),
                     "price": c["price"], "regime": c.get("regime"), "blocked_by": c.get("blocked_by"),
                     "ret_bps": None if r is None else r["ret_bps"],
                     "hit": None if r is None or c["call"] == "FLAT" or r["ret_bps"] == 0
                     else (r["ret_bps"] > 0) == (c["call"] == "UP")})
    # Paper dollars at the wallet size recorded with each call: what trading every compound call
    # for one bar would have made after costs. Calls made without a wallet reading are left out.
    sized = [(dirs[c["call"]], float(r["ret_bps"]), float(c["notional_usd"]),
              float(c.get("round_trip_bps", 16.0))) for c, r in done
             if c["call"] in dirs and c.get("notional_usd")]
    paper = {"label": "paper $ at wallet size", "calls": len(sized),
             "net_usd": round(sum(n * (d * ret - cost) / 1e4 for d, ret, n, cost in sized), 2) if sized else None,
             "costs_usd": round(sum(n * cost / 1e4 for _, _, n, cost in sized), 2) if sized else None}
    return {"asset": asset, "calls_recorded": len(calls), "resolved": len(done), "paper": paper,
            "pending": len(calls) - len(done), "round_trip_bps": rt,
            "round_trip_bps_basis": "mean of resolved calls; each outcome uses its recorded cost",
            "compound": compound, "compound_ungated": ungated,
            "components": {cid: _tally(v, rt, per_costs[cid]) for cid, v in sorted(per.items())},
            "recent": rows, "horizon_results": horizon_status(ledger)}


# -- backtests -------------------------------------------------------------------------------

_PREPARED: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
_PREPARED_MAX = 2  # coins held per process: a year of 5m bars is ~30 MB, minute files are not


def _data_signature(asset: str) -> tuple[Any, ...]:
    """mtimes of every file `prepare` may read, so a re-fetch invalidates the cache."""
    from backtester.core.data import resolve_data_dir

    data = resolve_data_dir()
    paths = [p for p, _ in cbt.candidate_files(asset, data)] + [p for p, _ in cbt.candidate_files("BTC", data)]
    paths.append(data / f"{asset}_funding_1h.csv")
    return tuple(p.stat().st_mtime_ns if p.exists() else None for p in paths)


def bars_cache_path(asset: str) -> Path:
    return home() / "bars" / f"{_asset(asset)}_5m.npz"


def materialize_bars(asset: str) -> tuple[Any, str]:
    """5m bars for `asset`, built once from the longest cached series (minute files included)
    and saved as a compact .npz keyed by the source files' mtimes. Parallel workers read this
    instead of each re-reading and re-aggregating a multi-million-row minute file."""
    import pandas as pd

    a = _asset(asset)
    # "v2": the cache now carries the per-bar minute count; older caches are rebuilt.
    sig = ["v2", *_data_signature(a)]
    path = bars_cache_path(a)
    if path.exists():
        try:
            with np.load(path, allow_pickle=False) as z:
                if list(z["sig"]) == [str(s) for s in sig]:
                    cols = [k for k in ("timestamp", "open", "high", "low", "close", "volume", "minutes") if k in z]
                    df = pd.DataFrame({k: z[k] for k in cols})
                    return df, str(z["source"])
        except (OSError, ValueError, KeyError):
            pass
    df, source = cbt.load_bars_5m(a)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez(tmp, sig=np.array([str(s) for s in sig]), source=np.array(source),
             **{k: df[k].to_numpy() for k in ("timestamp", "open", "high", "low", "close", "volume", "minutes")
                if k in df})
    os.replace(tmp, path)
    return df, source


def _prepared(asset: str) -> dict[str, Any]:
    # The tab's process lives for days; without the signature it would keep backtesting the
    # data it first loaded after research/full_suite.py replaced the files.
    sig = _data_signature(asset)
    cached = _PREPARED.get(asset)
    if cached is None or cached[0] != sig:
        df, source = materialize_bars(asset)
        while len(_PREPARED) >= _PREPARED_MAX:
            _PREPARED.pop(next(iter(_PREPARED)))
        _PREPARED[asset] = (sig, cbt.prepare(asset, bars=df, source=source))
    return _PREPARED[asset][1]


def _run_one(asset: str, label: str, cfg: Mapping[str, Any], events: Sequence[Mapping[str, Any]],
             run_id: str) -> dict[str, Any]:
    try:
        row = cbt.run_compound(asset, cfg, label=label, events=events, prepared=_prepared(asset))
    except Exception as exc:  # noqa: BLE001 - one bad configuration must not sink a sweep
        return {"asset": asset, "label": label, "error": f"{type(exc).__name__}: {exc}", "run_id": run_id}
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


def backtest_all(*, standalone: bool = True, perturb: bool = False, aggregate_grid: bool = False,
                 frontier: bool = False, workers: int | None = None,
                 progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Every coin with cached data, in parallel processes, each with its own settings."""
    workers = workers or max(1, min(8, (os.cpu_count() or 2) // 2))
    return sweep(list(coins()), standalone=standalone, perturb=perturb, aggregate_grid=aggregate_grid,
                 frontier=frontier, workers=workers, progress=progress)


def backtest(asset: str, *, standalone: bool = True, perturb: bool = False, aggregate_grid: bool = False,
             frontier: bool = False, workers: int = 1,
             progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run the saved config (and its variants) on one asset's cached 5m data; append results."""
    if frontier and workers <= 1:
        workers = max(1, min(8, (os.cpu_count() or 2) // 2))  # ~100 configurations: use the cores
    return sweep([asset], standalone=standalone, perturb=perturb, aggregate_grid=aggregate_grid,
                 frontier=frontier, workers=workers, progress=progress)


def sweep(assets: Sequence[str], *, standalone: bool = True, perturb: bool = False,
          aggregate_grid: bool = False, frontier: bool = False, workers: int = 1,
          progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    events = load_state()["events"]
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    jobs = []
    skipped = {}
    for a in assets:
        a = _asset(a)
        try:
            # Built once here, so the workers read a small cache instead of the minute file.
            _prepared(a) if workers <= 1 else materialize_bars(a)
        except cbt.CompoundDataError as exc:
            skipped[a] = str(exc).splitlines()[0]
            continue
        cfg = load_state(a)["config"]  # each coin with its own settings
        for label, c in cbt.variants(cfg, standalone=standalone, perturb=perturb, aggregate_grid=aggregate_grid,
                                     frontier=frontier):
            jobs.append((a, label, c))
    rows: list[dict[str, Any]] = []

    def keep(row: dict[str, Any], i: int) -> None:
        # Written as each finishes: an interrupted multi-hour sweep keeps what it computed.
        rows.append(row)
        append_results([row])
        if progress:
            progress(f"{i}/{len(jobs)} {row['asset']} {row['label']}")

    if workers <= 1:
        for i, (a, label, c) in enumerate(jobs, 1):
            keep(_run_one(a, label, c, events, run_id), i)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_one, a, label, c, events, run_id): (a, label) for a, label, c in jobs}
            for i, f in enumerate(as_completed(futs), 1):
                try:
                    row = f.result()
                except Exception as exc:  # noqa: BLE001 - a crashed worker process
                    a, label = futs[f]
                    row = {"asset": a, "label": label, "error": f"{type(exc).__name__}: {exc}", "run_id": run_id}
                keep(row, i)
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
        "oos_buy_hold": r["oos"].get("buy_hold_return"),
        "oos_horizons": f_oos.get("horizons") or [],
        "leverage": r.get("leverage"), "bars": r.get("bars"), "source": r.get("source"),
        "run_id": r.get("run_id"), "oos_bars": f_oos.get("bars"), "split_ts": r.get("split_ts"),
        "to_ts": r.get("to_ts"), "round_trip_bps": f_oos.get("round_trip_bps"),
        "data_incomplete_pct": r.get("data_incomplete_pct"),
    }


# Above this share of 5m bars built from incomplete minutes, results carry a data warning.
DATA_WARN_PCT = 1.0


def verdict_word(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "not tested"
    strong = [r for r in rows if r.get("ranked") and (r.get("oos_z") or 0) >= 2]
    if any((r.get("oos_return") or 0) > 0 for r in strong):
        return "possible edge"
    return "signal, costs eat it" if strong else "no edge"


def overview(coin_list: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """One row per coin: its own settings, data, latest backtest verdict, forward test, trainer."""
    raw = _read_raw()
    overrides = raw.get("assets") or {}
    results = [r for r in read_results() if "error" not in r and "oos" in r]
    out = []
    for c in (coin_list if coin_list is not None else coins()):
        a = _asset(c)
        mine = [r for r in results if r.get("asset") == a]
        latest = [summary_row(r) for r in mine if r.get("run_id") == mine[-1]["run_id"]] if mine else []
        comp = next((r for r in latest if r["label"] == "compound"), None)
        fwd = forward_status(a)
        data_from = None
        for path, _ in cbt.candidate_files(a, cbt.resolve_data_dir()):
            if path.exists():
                data_from = path.name
                break
        bad = None if comp is None else comp.get("data_incomplete_pct")
        if data_from and bad is not None:
            data_from = f"{data_from} ({bad:.1f}% bars incomplete)"
        out.append({
            "asset": a, "own_settings": bool(overrides.get(a)), "data": data_from,
            "backtest_verdict": verdict_word(latest),
            "backtest_hit": None if comp is None else comp.get("oos_hit"),
            "backtest_bars": None if comp is None else comp.get("bars"),
            "fwd_calls": fwd["compound"]["decided"], "fwd_hit": fwd["compound"]["hit_rate"],
            "paper_usd": fwd["paper"]["net_usd"], "unattended": unattended_status(a)["running"],
            "live": live_capable(a),
        })
    return out


def readable_label(label: str) -> str:
    """`only:rsi` -> "RSI alone"; `frontier:htf_trend hold=288 top2% 1x` -> "HTF trend: top 2%, held 24 h, 1x".
    The raw label stays in the results file; this is what a person reads in the tab."""
    def name(cid: str) -> str:
        comp = sc.BY_ID.get(cid)
        return comp.name if comp else cid

    def hours(bars: str) -> str:
        minutes = int(bars) * 5
        return f"{minutes // 60} h" if minutes % 60 == 0 else f"{minutes} min"

    if label == "compound":
        return "Compound (every enabled metric voting)"
    if label.startswith("only:"):
        rest = label[5:].split(" ", 1)
        return f"{name(rest[0])} alone" + (f" ({rest[1]})" if len(rest) > 1 else "")
    if label.startswith("frontier:"):
        parts = label[9:].split()
        hold = next((p[5:] for p in parts if p.startswith("hold=")), None)
        lev = next((p for p in parts if p.endswith("x")), "")
        return f"{name(parts[0])}: top 2%, held {hours(hold) if hold else '?'}" + (f", {lev}" if lev else "")
    if label.startswith("compound "):
        return "Compound, " + label[9:]
    return label


def tested_line(asset: str, rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> str:
    """One paragraph: what the Backtest table tested, on what data and at what cost."""
    ex = cfg["execution"]
    rt = sc.round_trip_bps(ex["fee_bps"], ex["slippage_bps"])
    head = rows[0] if rows else {}
    when = ""
    if head.get("split_ts"):
        when = f"; out-of-sample from {time.strftime('%Y-%m-%d', time.gmtime(int(head['split_ts'])))}"
    data = (f"{head.get('bars'):,} 5m bars from {head.get('source') or '?'}{when}" if head.get("bars")
            else "no backtest yet: press Backtest this coin")
    return (f"What is tested ({_asset(asset)}): {data}. Every row fills at the next bar's open and pays "
            f"{ex['fee_bps']:g} bps fee + {ex['slippage_bps']:g} bps slippage per side ({rt:g} bps a round trip), "
            f"at {ex['leverage']:g}x unless the row says 1x. Compound = every enabled metric voting; "
            "'X alone' = one metric, no gates; 'top 2%, held N h' = only that metric's strongest 2% of "
            "readings (by its own trailing record), kept N hours. Buy & hold is the coin itself over the "
            "same out-of-sample window: a row that only matches it shows drift, not skill. Net bps 1h / 24h "
            "is what a call earns held that long, after one round trip.")


def run_summary(rows: Sequence[Mapping[str, Any]], window_count: int | None = None) -> str:
    """The backtest table in plain words: what was tested, the best direction, money, a verdict."""
    if not rows:
        return "No backtest yet: press Backtest selected (it uses the cached 5m history of the Settings asset)."
    first = rows[0]
    n = len(rows)
    when = ""
    if first.get("split_ts") and first.get("to_ts"):
        days = (first["to_ts"] - first["split_ts"]) / 86400
        when = (f"{time.strftime('%m-%d', time.gmtime(first['split_ts']))} to "
                f"{time.strftime('%m-%d', time.gmtime(first['to_ts']))} ({days:.1f} days, "
                f"{first.get('oos_bars') or 0:,} bars)")
    head = (f"{first['asset']}: {n} configuration{'s' if n != 1 else ''} tested"
            + (f" ({window_count} on this window across all runs)" if window_count else "")
            + f". Scored on the held-out last 30% of the history{', ' + when if when else ''}; "
            f"costs {first.get('round_trip_bps') or 16:g} bps per round trip.")
    called = [r for r in rows if r.get("oos_hit") is not None and (r.get("oos_calls") or 0) > 0]
    best_dir = max(called, key=lambda r: (r.get("oos_z") or -99), default=None)
    compound = next((r for r in rows if r["label"] == "compound"), None)
    direction = "Direction: no configuration made a call." if not best_dir else (
        f"Direction: best is {best_dir['label']} at {100 * best_dir['oos_hit']:.1f}% right "
        f"(z {best_dir['oos_z']:+.1f}; anything within about +-2 is a coin flip)"
        + (f"; the compound {100 * compound['oos_hit']:.1f}%." if compound and compound.get("oos_hit") is not None else "."))
    made = [r for r in rows if (r.get("oos_return") or -1) > 0]
    best_ret = max(rows, key=lambda r: (r.get("oos_return") if r.get("oos_return") is not None else -9))
    oracle = first.get("oracle_net_bps")
    money = (f"Money: {len(made)} of {n} made money after costs; best {best_ret['label']} "
             f"{100 * (best_ret.get('oos_return') or 0):+.1f}%."
             + (f" Even a perfect next-bar call would net {oracle:+.1f} bps per trade here." if oracle is not None else ""))
    strong = [r for r in rows if r.get("ranked") and (r.get("oos_z") or 0) >= 2]
    if any((r.get("oos_return") or 0) > 0 for r in strong):
        verdict = "Verdict: a possible edge. Confirm it in the forward test before trusting it."
    elif strong:
        verdict = "Verdict: some direction signal, but costs eat it."
    else:
        verdict = "Verdict: no measurable edge after costs."
    bad = first.get("data_incomplete_pct")
    data = ""
    if bad is not None and bad >= DATA_WARN_PCT:
        data = (f" Data: {bad:.1f}% of these 5m bars were built from incomplete minutes. Coinbase drops "
                "minutes that traded (research/CANDLE-GAP-AUDIT.md), so closes, highs and lows there may be "
                "wrong and liquidations understated.")
    return " ".join((head, direction, money, verdict)) + data


def latest_results(asset: str | None = None, top: int = 40) -> dict[str, Any]:
    rows = [r for r in read_results() if "error" not in r and "oos" in r]
    if asset:
        rows = [r for r in rows if r.get("asset") == _asset(asset)]
    if not rows:
        return {"run_id": None, "rows": [], "leaderboard": []}
    last = rows[-1]["run_id"]
    latest = [r for r in rows if r.get("run_id") == last]
    # Every run that scored the same bars against the same OOS split has looked at that OOS
    # slice. The honest multiple-testing denominator for the latest numbers is all of them,
    # not just this run's count.
    windows = {(r.get("asset"), r.get("data_hash"), r.get("split_ts")) for r in latest}
    same_window = sum(1 for r in rows if (r.get("asset"), r.get("data_hash"), r.get("split_ts")) in windows)
    return {"run_id": last, "rows": [summary_row(r) for r in cbt.leaderboard(latest, top=len(latest))],
            "leaderboard": [summary_row(r) for r in cbt.leaderboard(rows, top=top)],
            "configurations_ever": len(rows), "configurations_on_this_oos_window": same_window}


# -- CLI -------------------------------------------------------------------------------------


def wallet_line(wallet: Mapping[str, Any], sizing: Mapping[str, Any]) -> str:
    """One line for the CLI and the tab."""
    if not wallet.get("available"):
        return f"{wallet.get('label', WALLET_LABEL)}: unavailable -- {wallet.get('reason', 'not read')}"
    parts = " · ".join(f"{k} ${v:,.2f}" for k, v in (wallet.get("parts") or {}).items())
    label = wallet.get("label", WALLET_LABEL)
    head = f"{label} ...{wallet.get('address_tail', '')}: ${wallet['usable_usd']:,.2f} usable ({parts or 'none'})"
    if wallet.get("positions"):
        head += "; open: " + ", ".join(f"{p['coin']} {p['size']:+g} @ {p['entry']:,.4g}" for p in wallet["positions"])
    if wallet.get("unpriced"):
        head += f"; unpriced, not counted: {', '.join(wallet['unpriced'])}"
    if not sizing.get("available"):
        return head + f" -- no size: {sizing.get('reason', '')}"
    liq = sizing["liquidation_price"]
    side = sizing.get("side")
    liq_text = (f"liq {side} ${liq[side]:,.4g}" if side and liq.get(side) else
                f"liq long ${liq['long'] or 0:,.4g} / short ${liq['short'] or 0:,.4g}")
    return (head + f" -> ${sizing['notional_usd']:,.0f} notional (${sizing['collateral_usd']:,.0f} collateral at "
            f"{sizing['leverage']:g}x, bound by {sizing['bound_by']}); loses ${sizing['loss_at_stop_usd']:,.2f} "
            f"({sizing['risk_pct']:g}%) at the {sizing['stop_pct']:.2f}% stop incl. ${sizing['round_trip_cost_usd']:,.2f} "
            f"round trip; {liq_text}")


# -- previews for the console's shared editor ---------------------------------------------------
# Plain markdown, built from the same data the tab's tables show, so the editor below the tab can
# explain the selected row in full instead of one truncated table line.


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, Mapping):
        return " ".join(f"{k}={_fmt(x)}" for k, x in v.items()) or "-"
    return "-" if v in (None, "") else str(v)


def _when(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(ts)))
    except (TypeError, ValueError):
        return "-"


def metric_preview(cid: str, cfg: Mapping[str, Any], *, asset: str, own: Mapping[str, Any] | None = None,
                   columns: Mapping[str, str] | None = None, adoptions: Sequence[Mapping[str, Any]] = (),
                   autopilot: bool = False) -> str:
    """Everything known about one metric or gate for one coin, as markdown."""
    comp = sc.BY_ID[cid]
    entry = cfg["components"][cid]
    own_entry = (own or {}).get("components", {}).get(cid, {})
    agg = cfg["aggregate"]
    lines = [f"# {comp.name} ({cid}) - {_asset(asset)}", "",
             f"- kind: {comp.kind}" + (" (forward only: needs live data, skipped in backtests)" if comp.forward_only else ""),
             f"- family / style: {comp.family} / {comp.style}",
             f"- source: {comp.source}",
             f"- state: {'ON' if entry['enabled'] else 'off'} (double-click the row or press Space to switch)",
             f"- weight: {entry['weight']:g}",
             f"- settings: {_fmt(entry['params'])}"
             + (f" (this coin's own: {_fmt(own_entry.get('params') or {})})" if own_entry.get("params") else ""),
             "", "## Formula", "", comp.formula, "",
             "## Works when", "", comp.useful_when, "",
             "## Fails when", "", comp.not_useful_when, ""]
    if comp.params:
        lines += ["## Parameters", "", "| name | now | default | range | meaning |", "| --- | --- | --- | --- | --- |"]
        for spec in comp.params:
            lines.append(f"| {spec.name} | {_fmt(entry['params'].get(spec.name))} | {spec.default:g} | "
                         f"{spec.lo:g}..{spec.hi:g} | {spec.describe or '-'} |")
        lines.append("")
    rel = sc.RELATIONS.get(cid, ())
    if rel:
        lines += ["Constraints: " + "; ".join(r[2] for r in rel), ""]
    cols = {k: v for k, v in (columns or {}).items() if v}
    if cols:
        lines += ["## Evidence for this coin", ""] + [f"- {k}: {v}" for k, v in cols.items()] + [""]
    lines += ["## Self-optimizing", "",
              f"- autopilot: {'ON' if autopilot else 'off'}; tuning {'on' if agg['tune'] else 'off'} "
              f"(neighbours at x(1 +/- {agg['tune_step']:g}); a move needs P(better) > {agg['tune_confidence']:g} "
              f"on {agg['tune_min_calls']:g} decayed calls; then {agg['tune_cooldown']} bars of cooldown)",
              f"- learned weighting {'on' if agg['adaptive'] else 'off'} over the last {agg['adaptive_window']} bars"
              + (", inverting a metric that is reliably wrong" if agg["adaptive_flip"] else "")]
    mine = [a for a in adoptions if a.get("metric") == cid and _asset(str(a.get("asset") or asset)) == _asset(asset)]
    if mine:
        lines += ["", "Adopted automatically:"]
        lines += [f"- {_when(a.get('ts'))}: {_fmt(a.get('from') or {})} -> {_fmt(a.get('to') or {})}" for a in mine[-8:]]
    else:
        lines.append("- no tuned settings adopted yet for this coin")
    return "\n".join(lines) + "\n"


def coin_preview(row: Mapping[str, Any], *, own: Mapping[str, Any] | None = None,
                 adoptions: Sequence[Mapping[str, Any]] = (), autopilot: bool = False) -> str:
    """One overview row (a coin) in full."""
    a = _asset(str(row.get("asset")))
    lines = [f"# {a} - compound 5m", "",
             f"- cached data: {row.get('data') or 'none'}",
             f"- latest backtest verdict: {_fmt(row.get('backtest_verdict'))}; bt hit {_fmt(row.get('backtest_hit'))}",
             f"- forward calls: {_fmt(row.get('fwd_calls'))}; fwd hit {_fmt(row.get('fwd_hit'))}",
             f"- paper $ at wallet size: {_fmt(row.get('paper_usd'))} (no order was placed)",
             f"- unattended training: {'RUNNING' if row.get('unattended') else 'stopped'}"
             + (" (autopilot restarts it within five minutes)" if autopilot and not row.get("unattended") else ""),
             "", "## This coin's own settings (on top of the shared ones)", ""]
    comps = (own or {}).get("components") or {}
    if comps:
        lines += [f"- {cid}: {_fmt(e)}" for cid, e in sorted(comps.items())]
    else:
        lines.append("- none: it uses the shared settings")
    for section in ("aggregate", "execution"):
        if (own or {}).get(section):
            lines.append(f"- {section}: {_fmt(own[section])}")
    mine = [x for x in adoptions if _asset(str(x.get("asset") or "")) == a]
    lines += ["", "## Tuned settings adopted automatically", ""]
    lines += ([f"- {_when(x.get('ts'))} {x.get('metric')}: {_fmt(x.get('from') or {})} -> {_fmt(x.get('to') or {})}"
               for x in mine[-12:]] or ["- none yet"])
    return "\n".join(lines) + "\n"


def record_preview(title: str, record: Mapping[str, Any], note: str = "") -> str:
    """A results or forward-call row as a field list."""
    lines = [f"# {title}", ""] + ([note, ""] if note else [])
    lines += [f"- {k}: {_fmt(v)}" for k, v in record.items()]
    return "\n".join(lines) + "\n"


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
        if "learned_hit" in r:
            tail = f"{tail} learned {r['learned_hit']:.1%}/{r['learned_calls']:.0f} x{r['adaptive_mult']:+.3f}"
        if r["kind"] == "gate":
            tail = "BLOCK" if r.get("blocked") else "pass"
        print(f"  {r['id']:<20} {r['status']:<11} {tail!s:<36} w={r['weight']:<4} {r['family']}/{r['style']}")
    for k, v in (x.get("notes") or {}).items():
        print(f"  note {k}: {v}")
    print(wallet_line(x.get("wallet") or {}, x.get("sizing") or {}))


# -- unattended forward training -------------------------------------------------------------
#
# A detached process that takes one forward tick per closed 5m bar until stopped. Every tick
# records the call, resolves earlier calls, and the next call learns from them (adaptive
# weighting seeds from this ledger), so leaving it running IS the training. It is a separate
# process, not a TUI timer, so it keeps going when the console closes. One per asset: the child
# holds an flock on `forward-<ASSET>.lock` for its whole life, and "running?" is answered by
# trying that lock -- a pid can be recycled, a lock cannot outlive its holder.


def unattended_paths(asset: str) -> dict[str, Path]:
    a = _asset(asset)
    base = home() / "unattended"
    return {"lock": base / f"{a}.lock", "pid": base / f"{a}.pid", "log": base / f"{a}.log",
            "stop": base / f"{a}.stop"}


def _try_lock(path: Path) -> int | None:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def unattended_status(asset: str) -> dict[str, Any]:
    paths = unattended_paths(asset)
    fd = _try_lock(paths["lock"])
    running = fd is None
    if fd is not None:
        os.close(fd)
    pid = None
    try:
        pid = int(paths["pid"].read_text().strip())
    except (OSError, ValueError):
        pass
    tail = ""
    try:
        lines = paths["log"].read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-1][:300] if lines else ""
    except OSError:
        pass
    since = None
    if running and paths["pid"].exists():
        since = int(paths["pid"].stat().st_mtime)
    return {"asset": _asset(asset), "running": running, "pid": pid if running else None, "since": since,
            "log": str(paths["log"]), "last_line": tail}


def start_unattended(asset: str, offset: float = 0.0) -> dict[str, Any]:
    """Spawn the unattended loop for one coin, detached, at background priority."""
    out = start_unattended_many([asset])
    if not out["started"]:
        raise CompoundError(next(iter(out["skipped"].values()), "not started"))
    return {"started": True, "asset": _asset(asset), "pid": out["pid"], "log": out["log"]}


def start_unattended_many(coin_list: Sequence[str]) -> dict[str, Any]:
    """ONE detached process that forward-tests every listed coin once per bar.

    One process for all coins rather than one each: thirty-six Python processes would hold
    about 3 GB to do what one does sequentially in well under a minute per bar. Each coin keeps
    its own lock, pid file, log and stop file, so status and Stop still work per coin.
    """
    import subprocess

    from . import bgcontrol

    todo, skipped = [], {}
    for c in coin_list:
        a = _asset(c)
        if not live_capable(a):
            skipped[a] = "backtest only: live candles come from Coinbase, which does not list it"
        elif unattended_status(a)["running"]:
            skipped[a] = "already running"
        else:
            todo.append(a)
    if not todo:
        return {"started": [], "skipped": skipped, "pid": None, "log": None}
    for a in todo:
        unattended_paths(a)["stop"].unlink(missing_ok=True)
    log_path = home() / "unattended" / ("run.log" if len(todo) > 1 else f"{todo[0]}.log")
    cmd = [sys.executable, "-m", "soltui.compound", "forward", "--assets", ",".join(todo), "--loop",
           "--unattended"]
    launcher = bgcontrol.taskpolicy_path()
    if launcher:
        cmd = [launcher, "-b", *cmd]
    env = {**os.environ, "PYTHONPATH": str(REPO) + os.pathsep + os.environ.get("PYTHONPATH", ""),
           "SOLTUI_CONFIG_DIR": str(config_mod.CONFIG_DIR)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,  # noqa: S603
                                stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):  # up to 6 s for the child to take its locks
        time.sleep(0.1)
        if proc.poll() is not None:
            raise CompoundError(f"unattended run exited at once (code {proc.returncode}); see {log_path}")
        if all(unattended_status(a)["running"] for a in todo):
            break
    return {"started": todo, "skipped": skipped, "pid": proc.pid, "log": str(log_path)}


def start_unattended_all(coin_list: Sequence[str] | None = None) -> dict[str, Any]:
    return start_unattended_many(list(coin_list if coin_list is not None else coins()))


def stop_unattended_all(coin_list: Sequence[str] | None = None) -> dict[str, Any]:
    return {"stopping": [c for c in (coin_list if coin_list is not None else coins())
                         if stop_unattended(c)["stopping"]]}


def stop_unattended(asset: str) -> dict[str, Any]:
    """Ask the loop to drop this coin through its cooperative stop file.

    The worker checks between ticks and during waits. A recorded PID never
    authorizes a signal: it may name an unrelated process after a crash.
    """
    a = _asset(asset)
    paths = unattended_paths(a)
    status = unattended_status(a)
    if not status["running"]:
        return {"stopping": False, "asset": a, "message": "not running"}
    paths["stop"].write_text("stop\n")
    pid = status["pid"]
    # Autopilot keeps every coin training; a stopped coin comes back at its next check.
    try:
        restarts = autopilot_enabled()
    except CompoundError:
        restarts = False  # an unreadable config must not stop the stop
    return {"stopping": True, "asset": a, "pid": pid, "autopilot_restarts": restarts}


def set_autopilot(enabled: bool) -> dict[str, Any]:
    state = save_state(autopilot=bool(enabled))
    return {"autopilot": state["autopilot"]}


def _live_coins(coin_list: Sequence[str] | None = None) -> list[str]:
    return [_asset(c) for c in (coin_list if coin_list is not None else coins()) if live_capable(c)]


def autopilot_status(coin_list: Sequence[str] | None = None) -> dict[str, Any]:
    """The switch, which live coins train right now, the LaunchAgent and the latest adoptions."""
    from . import compound_agent

    live = _live_coins(coin_list)
    adoptions = []
    for c in live:
        path = forward_path(c)
        if not path.exists():
            continue
        # The console asks once a minute and ledgers grow ~900 lines a coin a day: parse only the
        # rare adoption lines, not every call.
        for line in path.read_text(encoding="utf-8").splitlines():
            if '"adopt"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("type") == "adopt":
                adoptions.append({k: r.get(k) for k in ("ts", "asset", "metric", "from", "to")})
    adoptions.sort(key=lambda r: r["ts"] or 0)
    return {"autopilot": autopilot_enabled(), "live_coins": live,
            "running": [c for c in live if unattended_status(c)["running"]],
            "agent": compound_agent.status(), "adoptions": adoptions[-20:]}


def autopilot_ensure(coin_list: Sequence[str] | None = None) -> dict[str, Any]:
    """What the autopilot LaunchAgent runs every five minutes: start one trainer for every live coin
    whose loop is not running. Idempotent, because each coin's loop holds that coin's lock."""
    if not autopilot_enabled():
        return {"autopilot": False, "started": [], "already_running": [], "skipped": {}}
    live = _live_coins(coin_list)
    running = [c for c in live if unattended_status(c)["running"]]
    out = start_unattended_many([c for c in live if c not in running])
    return {"autopilot": True, "already_running": running, **out}


def run_unattended(assets: str | Sequence[str], *, hold_lock: bool = True, max_ticks: int | None = None,
                   offset: float = 0.0, sleep: Callable[[float], None] = time.sleep,
                   clock: Callable[[], float] = time.time,
                   tick: Callable[..., dict[str, Any]] | None = None) -> int:
    """The loop the detached process runs: every active coin once per closed bar.

    A failed tick is logged and skipped, never fatal: unattended means a network blip at 03:05
    must not end the run. A coin whose stop file appears is dropped (its lock released) while
    the others continue; SIGTERM ends the whole loop.
    """
    import signal as signal_mod

    names = [_asset(a) for a in ([assets] if isinstance(assets, str) else assets)]
    held: dict[str, int | None] = {}
    for a in names:
        paths = unattended_paths(a)
        if hold_lock:
            fd = _try_lock(paths["lock"])
            if fd is None:
                print(f"{a}: another unattended run holds {paths['lock']}; skipped", flush=True)
                continue
            paths["pid"].write_text(f"{os.getpid()}\n")
            held[a] = fd
        else:
            held[a] = None
    if not held:
        return 1
    stopping = {"flag": False}

    def on_term(signum: int, frame: Any) -> None:
        stopping["flag"] = True

    if hold_lock:
        signal_mod.signal(signal_mod.SIGTERM, on_term)
    injected_tick = tick is not None
    tick = tick or forward_tick
    last_scored: dict[str, int] = {}
    ticks = 0

    def stamp() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(clock()))

    def say(a: str, line: str) -> None:
        print(line, flush=True)
        if len(held) > 1 or len(names) > 1:  # a shared run also keeps each coin's own log current
            with unattended_paths(a)["log"].open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def release(a: str) -> None:
        paths = unattended_paths(a)
        say(a, f"{stamp()} unattended forward training {a} stopped after {ticks} tick(s)")
        fd = held.pop(a)
        if hold_lock:
            paths["stop"].unlink(missing_ok=True)
            paths["pid"].unlink(missing_ok=True)
            if fd is not None:
                os.close(fd)

    for a in held:
        say(a, f"{stamp()} unattended forward training {a} started (pid {os.getpid()})")
    try:
        while held and not stopping["flag"]:
            for a in list(held):
                if unattended_paths(a)["stop"].exists():
                    release(a)
                    continue
                try:
                    latest = (int(clock()) // 300) * 300 - 300
                    if injected_tick or last_scored.get(a, -1) < latest:
                        out = tick(a, wallet_address=_settings_address(), hyperliquid_address=_settings_hyperliquid())
                        if not injected_tick:
                            last_scored[a] = int(out["bar_ts"])
                    else:
                        out = _horizon_tick(a)
                    say(a, json.dumps({"at": int(clock()), **out}, default=_jsonable))
                except Exception as exc:  # noqa: BLE001 - keep running; the next bar will try again
                    say(a, json.dumps({"at": int(clock()), "asset": a, "error": f"{type(exc).__name__}: {exc}"}))
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            # The signal is refreshed on five-minute bars; horizon samples settle each minute.
            cadence = 300 if injected_tick else 60
            wake = clock() + cadence - (clock() % cadence) + 5 + offset
            while clock() < wake and not stopping["flag"] and held:
                for a in list(held):
                    if unattended_paths(a)["stop"].exists():
                        release(a)
                sleep(min(1.0, max(0.0, wake - clock())))
    finally:
        for a in list(held):
            release(a)
    return 0


def _settings_address() -> str | None:
    try:
        return config_mod.load_settings().solana_address
    except Exception:  # noqa: BLE001 - an unreadable settings file means "no wallet", not a crash
        return None


def _settings_hyperliquid() -> str | None:
    try:
        return config_mod.load_settings().hyperliquid_address or None
    except Exception:  # noqa: BLE001 - an unreadable settings file means "no account", not a crash
        return None


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m soltui.compound", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    for name in ("signal", "forward", "status", "backtest", "results"):
        p = sub.add_parser(name)
        p.add_argument("--asset", default="SOL")
        p.add_argument("--json", action="store_true", help="print the raw result")
        if name == "forward":
            p.add_argument("--loop", action="store_true", help="tick once per closed 5m bar until killed")
            p.add_argument("--unattended", action="store_true",
                           help="hold the per-asset lock (what the tab's Start unattended button runs)")
            p.add_argument("--offset", type=float, default=0.0,
                           help="extra seconds after each 5m boundary (staggers coins)")
            p.add_argument("--assets", default="", help="comma list: one loop over several coins")
        if name == "backtest":
            p.add_argument("--perturb", action="store_true")
            p.add_argument("--aggregate-grid", action="store_true")
            p.add_argument("--frontier", action="store_true",
                           help="every metric alone, top 2%% of readings, held 1 h / 4 h / 24 h")
    sw = sub.add_parser("sweep", help="every asset with cached 5m data, every variant")
    sw.add_argument("--assets", default="", help="comma list; default: every cached asset")
    sw.add_argument("--all-assets", action="store_true")
    sw.add_argument("--perturb", action="store_true", help="one-at-a-time parameter variations")
    sw.add_argument("--aggregate-grid", action="store_true", help="threshold/gate/leverage variations")
    sw.add_argument("--frontier", action="store_true",
                    help="every metric alone, top 2%% of readings, held 1 h / 4 h / 24 h")
    sw.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    sub.add_parser("catalog")
    sub.add_parser("autopilot", help="start every coin's unattended loop that is not running (the "
                   "LaunchAgent runs this); nothing when autopilot is off")
    args = ap.parse_args(argv)
    try:
        if args.verb == "catalog":
            print(json.dumps(sc.catalog(), indent=2))
        elif args.verb == "autopilot":
            out = autopilot_ensure()
            print(json.dumps({"at": int(time.time()), **out}, default=_jsonable), flush=True)
        elif args.verb == "signal":
            x = signal(args.asset, wallet_address=_settings_address(), hyperliquid_address=_settings_hyperliquid())
            print(json.dumps(x, indent=2, default=_jsonable)) if args.json else _print_signal(x)
        elif args.verb == "forward":
            if args.loop:
                many = [a for a in args.assets.split(",") if a.strip()] or [args.asset]
                return run_unattended(many, hold_lock=args.unattended, offset=args.offset)
            out = forward_tick(args.asset, wallet_address=_settings_address(),
                               hyperliquid_address=_settings_hyperliquid())
            print(json.dumps(out, default=_jsonable), flush=True)
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
                print(run_summary(out["rows"], out.get("configurations_on_this_oos_window")))
                _print_table({"run_id": out["run_id"], "configurations": len(out["rows"]),
                              "assets": [_asset(args.asset)], "skipped": {}, "rows": out["rows"]},
                             appended=False)
                print(f"{out['configurations_on_this_oos_window']} configurations have been scored on this "
                      "out-of-sample window across all runs; that is the multiple-testing denominator.")
        elif args.verb == "backtest":
            out = backtest(args.asset, perturb=args.perturb, aggregate_grid=args.aggregate_grid,
                           frontier=args.frontier, progress=lambda s: print(s, file=sys.stderr))
            _print_table(out)
        else:
            assets = [a for a in args.assets.split(",") if a.strip()] or list(coins())
            out = sweep(assets, perturb=args.perturb, aggregate_grid=args.aggregate_grid, frontier=args.frontier,
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
