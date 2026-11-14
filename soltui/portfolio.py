"""Portfolio monitoring: timestamped per-chain snapshots, the changes between them, and a notice line.

A snapshot is one line of `snapshots.jsonl` under `~/Library/Application Support/soltui/portfolio/`
(mode 600). It holds per-chain balances by symbol, a USD value, the prices used and the script types an
xpub scan found. It holds **no address and no xpub**, so the file can be read, backed up or attached to a
bug report without exposing the wallet's history.

## Honest rules

* Everything is `wallet (live)`: a read of real money. Nothing here is a simulation and nothing here is
  ever added to a simulated figure.
* A change is reported only between two snapshots in which the chain read `ok`. A chain that was partial
  or failed in either one is listed as skipped: a failed read looks exactly like "balance fell to zero".
* A balance with no USD price is unknown, never zero. A snapshot whose total is not complete is marked,
  and the P&L value curve skips it rather than plot a fake drop.
* The notice compares the latest snapshot with the one at the last view (`last-view.json`).
"""

from __future__ import annotations

import json
import hashlib
import tempfile
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import wallet as wallet_mod
from .wallet import LABEL, scan_wallet

SNAPSHOT_FILE = "snapshots.jsonl"
SEEN_FILE = "last-view.json"
FETCH_BUDGET_S = 420.0  # an xpub scan is many small requests; the default 60 s would cut it short
MAX_NOTICE_ITEMS = 3


def support_dir() -> Path:
    return Path(os.environ.get("SOLTUI_SUPPORT_DIR") or Path.home() / "Library" / "Application Support" / "soltui")


def portfolio_dir() -> Path:
    return support_dir() / "portfolio"


def snapshots_path() -> Path:
    return portfolio_dir() / SNAPSHOT_FILE


LAST_SCAN_FILE = "last-scan.json"


def last_scan_path() -> Path:
    return portfolio_dir() / LAST_SCAN_FILE


def save_last_scan(result: dict[str, Any], chain: str) -> Path:
    """Keep the newest scan, so the Wallet tab shows it the moment the console starts instead of an
    empty table until someone presses Scan. Owner-only, created that way: it lists the holdings."""
    target = last_scan_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".last-scan-", dir=target.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"chain": chain, "saved_at": time.time(), "result": result}, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def load_last_scan() -> dict[str, Any] | None:
    """{"chain", "saved_at", "result"} of the newest scan, or None (none yet, or a torn file)."""
    try:
        data = json.loads(last_scan_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
        return None
    return data


def make_fetcher():
    # Looked up on the module (not imported by name) so a test can substitute the fetcher class.
    return wallet_mod.HttpFetcher(budget_s=FETCH_BUDGET_S)


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def build_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    """Reduce a `scan_wallet` result to what is worth keeping. No addresses, no xpubs."""
    chains: dict[str, Any] = {}
    for name, ch in result["chains"].items():
        rows = ([ch["native"]] if ch.get("native") else []) + [h for h in ch["holdings"] if h["included"]] + ch["stakes"]
        balances: dict[str, float] = {}
        prices: dict[str, float] = {}
        symbols: dict[str, str] = {}
        for r in rows:
            sym = r["symbol"] + (" (staked)" if r.get("kind") == "stake" else "")
            display = sym
            identifier = r.get("mint") or r.get("address") if r.get("kind") not in {"native", "stake"} else None
            if isinstance(identifier, str) and identifier:
                canonical = identifier.lower() if identifier.startswith("0x") else identifier
                sym = "token#" + hashlib.sha256((name + "|" + canonical).encode()).hexdigest()
            symbols[sym] = display
            balances[sym] = balances.get(sym, 0.0) + float(r["amount"])
            if r.get("price_usd") is not None:
                prices[sym] = float(r["price_usd"])
        entry: dict[str, Any] = {
            "status": ch["status"], "balances": balances, "prices": prices, "usd": ch["total_usd"],
            "balance_identity_version": 2, "balance_symbols": symbols,
            "usd_complete": ch.get("total_complete", True), "unpriced": ch.get("unpriced", []),
            "positions": len(ch["positions"]),
        }
        if "script_types" in ch:
            entry["script_types"] = [t["type"] for t in ch["script_types"]]
            entry["derived_addresses"] = ch.get("derived_addresses")
        chains[name] = entry
    ok = bool(chains) and all(c["status"] == "ok" and c["usd_complete"] for c in chains.values())
    return {"ts": result["ts"], "at": result["scanned_at"], "label": LABEL, "partial": result["partial"],
            "total_usd": result["total_usd"], "total_complete": ok, "chains": chains}


def append_snapshot(snap: dict[str, Any], path: Path | None = None) -> Path:
    target = path or snapshots_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, (json.dumps(snap, sort_keys=True) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(target, 0o600)
    return target


def _valid_snapshot(row):
    def finite(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if (not isinstance(row, dict) or not finite(row.get("ts")) or not isinstance(row.get("at"), str)
            or not finite(row.get("total_usd")) or not isinstance(row.get("chains"), dict)):
        return False
    for name, chain in row["chains"].items():
        if (not isinstance(name, str) or not isinstance(chain, dict) or not isinstance(chain.get("status"), str)
                or type(chain.get("usd_complete")) is not bool or not finite(chain.get("usd"))):
            return False
        for field in ("balances", "prices"):
            values = chain.get(field)
            if not isinstance(values, dict) or any(not isinstance(key, str) or not finite(value) or value < 0 for key, value in values.items()):
                return False
    return True


def load_snapshots(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or snapshots_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for raw in lines:
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if _valid_snapshot(row):
            out.append(row)
    return sorted(out, key=lambda r: r["ts"])


def take_snapshot(settings: Any, fetch: Any = None, daemon: dict[str, Any] | None = None,
                  path: Path | None = None, now: float | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Scan every configured wallet and append the snapshot. Returns (snapshot, full scan result)."""
    result = scan_wallet(
        settings.solana_address, settings.base_address, fetch or make_fetcher(), daemon=daemon, now=now,
        eth_address=settings.eth_address,
        xpubs={"btc": settings.btc_xpub, "ltc": settings.ltc_xpub, "doge": settings.doge_xpub})
    snap = build_snapshot(result)
    if snap["chains"]:
        append_snapshot(snap, path)
    return snap, result


# -- changes -------------------------------------------------------------------------------------------


def _differs(before: float, after: float) -> bool:
    return abs(after - before) > max(1e-9, 1e-7 * max(abs(before), abs(after)))


def diff_snapshots(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Balance changes per chain and symbol between two snapshots; chains not `ok` in both are skipped."""
    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    value_before = value_after = 0.0
    value_ok = True
    for name, now in new["chains"].items():
        was = old["chains"].get(name)
        if was is None:
            skipped.append({"chain": name, "reason": "no earlier snapshot of this chain"})
            value_ok = False
            continue
        if was["status"] != "ok" or now["status"] != "ok":
            skipped.append({"chain": name, "reason": f"read was {was['status']} then {now['status']}: "
                                                      "a failed or partial read is not a balance change"})
            value_ok = False
            continue
        if was["usd_complete"] and now["usd_complete"]:
            value_before += was["usd"]
            value_after += now["usd"]
        else:
            value_ok = False
        if was.get("balance_identity_version", 1) != now.get("balance_identity_version", 1) and any(key.startswith("token#") for key in (*was["balances"], *now["balances"])):
            skipped.append({"chain": name, "reason": "token identity format changed; need two snapshots using the current format"})
            value_ok = False
            continue
        for sym in sorted(set(was["balances"]) | set(now["balances"])):
            b, a = was["balances"].get(sym, 0.0), now["balances"].get(sym, 0.0)
            if not _differs(b, a):
                continue
            px = now["prices"].get(sym) or was["prices"].get(sym)
            changes.append({"chain": name, "symbol": now.get("balance_symbols", {}).get(sym, was.get("balance_symbols", {}).get(sym, sym)),
                            "identity": sym, "before": b, "after": a, "delta": a - b,
                            "usd_delta": None if px is None else (a - b) * px})
    for name in old["chains"]:
        if name not in new["chains"]:
            skipped.append({"chain": name, "reason": "not in the later snapshot (address removed from Settings?)"})
            value_ok = False
    return {"label": LABEL, "from": old["at"], "to": new["at"], "from_ts": old["ts"], "to_ts": new["ts"],
            "changes": changes, "skipped": skipped,
            "value": {"before_usd": value_before if value_ok else None, "after_usd": value_after if value_ok else None,
                      "change_usd": value_after - value_before if value_ok else None,
                      "note": "value change includes price moves, deposits and withdrawals; not trading P&L"}}


def changes_report(snaps: list[dict[str, Any]], hours: float | None = None) -> dict[str, Any]:
    """Latest snapshot against the previous one, or against the newest one at least `hours` older."""
    if len(snaps) < 2:
        return {"label": LABEL, "snapshots": len(snaps), "changes": [], "skipped": [],
                "message": "need two snapshots to compare: run portfolio.snapshot again later"}
    new = snaps[-1]
    old = snaps[-2]
    if hours is not None:
        cutoff = new["ts"] - hours * 3600
        older = [s for s in snaps[:-1] if s["ts"] <= cutoff]
        if not older:
            return {"label": LABEL, "snapshots": len(snaps), "changes": [], "skipped": [],
                    "message": f"no snapshot is {hours:g} h or more older than the latest"}
        old = older[-1]
    return {**diff_snapshots(old, new), "snapshots": len(snaps)}


# -- last view and the notice ----------------------------------------------------------------------------


def _seen_path() -> Path:
    return portfolio_dir() / SEEN_FILE


def _read_seen() -> float | None:
    try:
        value = json.loads(_seen_path().read_text(encoding="utf-8")).get("ts")
    except (OSError, ValueError, AttributeError):
        return None
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def _write_seen(ts: float) -> None:
    target = _seen_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"ts": ts}, fh)


def notice_line(report: dict[str, Any]) -> str | None:
    """One line for the TUI and menu bar, or None when nothing changed."""
    changes = report.get("changes") or []
    if not changes:
        return None
    parts = [f"{c['symbol']} {c['delta']:+.6g}" for c in changes[:MAX_NOTICE_ITEMS]]
    if len(changes) > MAX_NOTICE_ITEMS:
        parts.append(f"+{len(changes) - MAX_NOTICE_ITEMS} more")
    value = (report.get("value") or {}).get("change_usd")
    tail = "" if value is None else f", value {value:+,.2f} USD"
    return f"{LABEL}: balance changed since {report['from'][:16].replace('T', ' ')} UTC: {', '.join(parts)}{tail}"


def notice(mark_seen: bool = False, path: Path | None = None) -> dict[str, Any]:
    """What changed since the last view. `mark_seen` moves the last-view marker to the latest snapshot."""
    snaps = load_snapshots(path)
    if not snaps:
        return {"label": LABEL, "changed": False, "line": None, "message": "no snapshots yet"}
    latest = snaps[-1]
    seen = _read_seen()
    if seen is None:
        baseline = snaps[0]
    else:
        earlier = [s for s in snaps if s["ts"] <= seen]
        baseline = earlier[-1] if earlier else snaps[0]
    report = diff_snapshots(baseline, latest) if baseline is not latest else {"changes": [], "from": latest["at"]}
    line = notice_line(report)
    if mark_seen:
        _write_seen(latest["ts"])
    return {"label": LABEL, "changed": line is not None, "line": line, "since": baseline["at"],
            "latest": latest["at"], "changes": len(report.get("changes") or []), "marked_seen": bool(mark_seen)}


# -- the P&L value curve ------------------------------------------------------------------------------------


def value_rows(snaps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """(rows for the wallet value curve, how many snapshots were left out).

    Only complete snapshots of the same set of wallets as the latest complete one are used. Adding a wallet
    to Settings would otherwise show as a jump in value that nobody earned or lost.
    """
    complete = [s for s in snaps if s.get("total_complete")]
    if not complete:
        return [], len(snaps)
    shape = sorted(complete[-1]["chains"])
    rows = [{"ts": s["ts"], "total_usd": s["total_usd"]} for s in complete if sorted(s["chains"]) == shape]
    return rows, len(snaps) - len(rows)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wrapper over the registry
    """`python -m soltui.portfolio` takes one snapshot through the registry (the LaunchAgent's job)."""
    import argparse

    argparse.ArgumentParser(description="Scan configured public wallets and save one portfolio snapshot.").parse_args(argv)
    from . import commands

    env = commands.dispatch("portfolio.snapshot", {}, surface="cli")
    print(commands.dumps(env), flush=True)
    return 0 if env["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
