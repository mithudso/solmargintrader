"""Liquidity tab logic: read the Aero LP daemon's state files, format them.

Pure, stdlib-only, and read-only with one exception. The liquidity daemon
(`liquidity/`, `aero-lp daemon`) writes `status.json` and `scout.json`; this
module only reads them. The single write is the `KILL` switch file, which
`set_kill()` creates or deletes. The contract is `liquidity/STATE_FILES.md`.

There is no order path here: no `aero_lp`, no web3, no keys, no network. If a
daemon file is missing, corrupt or from an unknown schema the loaders return a
`Loaded` with `data=None` and a human reason -- they never raise -- so the tab
shows "no data" instead of taking the console down.

**Labelling rule.** Every percentage and money figure carries its source word,
the same rule as the menu bar (see README, "Why every number carries a word").
A bare "+2.1%" reads as "my money is up"; here it must say whether it is a
*live* LP result, a *dry-run* one or a *modelled* scout estimate. Table columns
carry the word in their header (`Column.pct` marks the ones that hold a %), and
the summary line carries it inline. A test walks both.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any, Mapping

STATUS_SCHEMA = "aero-lp-status/1"
SCOUT_SCHEMA = "aero-lp-scout/1"
STATUS_FILE = "status.json"
SCOUT_FILE = "scout.json"
KILL_FILE = "KILL"
ENV_HOME = "AERO_LP_HOME"
DEFAULT_HOME = "~/.aero-lp"

# How often the tab re-reads the files, and how old `generated_at` may get
# before the summary says the daemon looks dead.
REFRESH_SECONDS = 15.0
STALE_AFTER_SECONDS = 180.0

SCOUT_ROWS = 25
ACTION_ROWS = 50
REASON_CLIP = 70
DASH = "—"

BASESCAN_TX = "https://basescan.org/tx/"
_TX_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

# The source words a percentage may be labelled with. `source_word` yields the
# first two; "modelled" labels scout estimates, which are neither.
SOURCE_WORDS = ("live", "dry-run", "reported", "modelled")


# -- locating and loading ----------------------------------------------------


def state_dir(env: Mapping[str, str] | None = None) -> Path:
    """`$AERO_LP_HOME`, else `~/.aero-lp`. Read at call time, never cached."""
    env = os.environ if env is None else env
    raw = (env.get(ENV_HOME) or "").strip() or DEFAULT_HOME
    return Path(raw).expanduser()


@dataclass(frozen=True)
class Loaded:
    """A state file read attempt. `data is None` means "show no data"."""

    data: dict[str, Any] | None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.data is not None


def _load(path: Path, schema: str) -> Loaded:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Loaded(None, f"{path.name} not found in {path.parent}")
    except (OSError, UnicodeDecodeError) as exc:
        return Loaded(None, f"cannot read {path.name}: {exc}")
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        return Loaded(None, f"{path.name} is not valid JSON: {exc}")
    if not isinstance(doc, dict):
        return Loaded(None, f"{path.name} is not a JSON object")
    found = doc.get("schema")
    if found != schema:
        return Loaded(None, f"{path.name} has schema {found!r}, expected {schema!r}")
    return Loaded(doc)


def load_status(home: Path | None = None) -> Loaded:
    return _load((home or state_dir()) / STATUS_FILE, STATUS_SCHEMA)


def load_scout(home: Path | None = None) -> Loaded:
    return _load((home or state_dir()) / SCOUT_FILE, SCOUT_SCHEMA)


# -- tolerant field access -----------------------------------------------------


def num(value: Any) -> float | None:
    """A finite number, else None. Bools are not numbers here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _dicts(value: Any) -> list[dict[str, Any]]:
    """The dict items of a list; anything else is treated as empty."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]


def _text(value: Any) -> str:
    if value is None:
        return DASH
    text = str(value).replace("\n", " ").strip()
    return text or DASH


def positions_of(status: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _dicts(status.get("positions"))


def experiments_of(status: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _dicts(status.get("experiments"))


def actions_of(status: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _dicts(status.get("actions"))


def pools_of(scout: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _dicts(scout.get("pools"))


# -- source words ----------------------------------------------------------------


def source_word(mode: Any) -> str:
    """The word that says where a P&L figure comes from.

    `live` only when the daemon says it is live; `dry-run` when it says so; and
    `reported` for anything else, because guessing "live" is the dangerous error.
    """
    if mode == "live":
        return "live"
    if mode == "dry-run":
        return "dry-run"
    return "reported"


def is_live(mode: Any) -> bool:
    return mode == "live"


# -- number formatting -----------------------------------------------------------


def fmt_usd(value: Any, *, signed: bool = False) -> str:
    v = num(value)
    if v is None:
        return DASH
    sign = ("+" if v > 0 else "-" if v < 0 else "") if signed else ("-" if v < 0 else "")
    # "-$0.00" is noise: a value that rounds to zero has no sign.
    if round(abs(v), 2) == 0:
        sign = ""
    return f"{sign}${abs(v):,.2f}"


def fmt_usd_compact(value: Any) -> str:
    v = num(value)
    if v is None:
        return DASH
    a = abs(v)
    sign = "-" if v < 0 else ""
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= limit:
            return f"{sign}${a / limit:,.1f}{suffix}"
    return f"{sign}${a:,.0f}"


def fmt_pct(value: Any, *, signed: bool = False, places: int = 2) -> str:
    """A percent given already in percent units (18.2 -> "18.20%")."""
    v = num(value)
    if v is None:
        return DASH
    sign = "+" if signed and v > 0 else ""
    return f"{sign}{v:.{places}f}%"


def fmt_price(value: Any) -> str:
    v = num(value)
    return DASH if v is None else f"{v:.6g}"


def fmt_range(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = num(value[0]), num(value[1])
        if lo is not None and hi is not None:
            return f"{lo:.6g}–{hi:.6g}"
    return DASH


def fmt_ts(ts: Any, tz: tzinfo | None = None) -> str:
    v = num(ts)
    if v is None:
        return DASH
    try:
        return datetime.fromtimestamp(v, tz).strftime("%m-%d %H:%M:%S")
    except (OverflowError, OSError, ValueError):
        return DASH


def fmt_age(seconds: float | None) -> str:
    if seconds is None:
        return "age unknown"
    s = max(0, int(seconds))
    if s < 90:
        return f"{s}s ago"
    if s < 90 * 60:
        return f"{s // 60}m ago"
    return f"{s // 3600}h ago"


def age_seconds(generated_at: Any, now: float | None = None) -> float | None:
    g = num(generated_at)
    if g is None:
        return None
    return (time.time() if now is None else now) - g


def tx_link(tx: Any) -> str:
    """A basescan URL for a full tx hash; anything else is shown as written."""
    t = str(tx).strip()
    return f"{BASESCAN_TX}{t}" if _TX_RE.match(t) else t


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# -- the summary line ----------------------------------------------------------------


@dataclass(frozen=True)
class Summary:
    """Everything the header needs, computed from `status.json` alone."""

    mode: str
    live: bool
    killed: bool
    idle_usd: float | None
    deployed_usd: float | None
    total_pnl_usd: float | None
    total_vs_hodl_usd: float | None
    n_positions: int
    age: float | None
    stale: bool
    word: str

    def line(self) -> str:
        """One plain-text line. Money only, each figure naming its source."""
        w = self.word
        parts = [
            f"idle {fmt_usd(self.idle_usd)}",
            f"deployed {fmt_usd(self.deployed_usd)}",
            f"{w} LP P&L {fmt_usd(self.total_pnl_usd, signed=True)}",
            f"{w} LP P&L vs HODL {fmt_usd(self.total_vs_hodl_usd, signed=True)}",
            f"{self.n_positions} position{'s' if self.n_positions != 1 else ''}",
            f"daemon state {fmt_age(self.age)}",
        ]
        if self.stale:
            parts[-1] += " (STALE: daemon may be down)"
        return " | ".join(parts)


def _sum(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [v for v in (num(r.get(key)) for r in rows) if v is not None]
    return sum(vals) if vals else None


def summarise(
    status: Mapping[str, Any],
    *,
    kill_file_present: bool = False,
    now: float | None = None,
) -> Summary:
    """Totals across `positions`.

    Positions only: experiment arms refer to positions by `slot`, so adding the
    arms as well would count the same money twice.
    """
    mode = status.get("mode")
    wallet = status.get("wallet")
    wallet = wallet if isinstance(wallet, dict) else {}
    positions = positions_of(status)
    age = age_seconds(status.get("generated_at"), now)
    return Summary(
        mode=mode if isinstance(mode, str) else "unknown",
        live=is_live(mode),
        killed=bool(status.get("killed")) or kill_file_present,
        idle_usd=num(wallet.get("idle_usd")),
        deployed_usd=num(wallet.get("deployed_usd")),
        total_pnl_usd=_sum(positions, "pnl_usd"),
        total_vs_hodl_usd=_sum(positions, "pnl_vs_hodl_usd"),
        n_positions=len(positions),
        age=age,
        stale=age is None or age > STALE_AFTER_SECONDS,
        word=source_word(mode),
    )


def mode_badge_text(mode: Any) -> str:
    """Plain text for the mode badge. LIVE is shouted; the tab also styles it."""
    if is_live(mode):
        return "LIVE"
    if mode == "dry-run":
        return "dry-run"
    return "mode unknown"


def wallet_line(status: Mapping[str, Any]) -> str:
    wallet = status.get("wallet")
    wallet = wallet if isinstance(wallet, dict) else {}
    bits = []
    for t in _dicts(wallet.get("tokens")):
        tag = "idle" if t.get("idle") else "in positions"
        bits.append(f"{_text(t.get('symbol'))} {fmt_usd(t.get('usd'))} ({tag})")
    eth = num(wallet.get("eth"))
    if eth is not None:
        bits.append(f"ETH gas {eth:.6f}")
    owner = status.get("owner")
    head = f"wallet {owner}: " if isinstance(owner, str) and owner else "wallet: "
    return head + (", ".join(bits) if bits else "no token balances reported")


def scout_line(scout: Mapping[str, Any], now: float | None = None) -> str:
    dep = num(scout.get("deposit_usd"))
    age = fmt_age(age_seconds(scout.get("generated_at"), now))
    basis = f"for a {fmt_usd(dep)} deposit" if dep is not None else "deposit size unknown"
    return f"modelled estimates {basis}, scouted {age}; not results"


# -- tables ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Column:
    """A table column. `pct=True` means its cells hold a percentage, so its
    header must carry a source word (asserted by the tests)."""

    header: str
    pct: bool = False


@dataclass(frozen=True)
class Table:
    columns: tuple[Column, ...]
    rows: tuple[tuple[str, ...], ...]

    @property
    def headers(self) -> list[str]:
        return [c.header for c in self.columns]


def positions_table(status: Mapping[str, Any]) -> Table:
    w = source_word(status.get("mode"))
    columns = (
        Column("pair"),
        Column("range (token1/token0)"),
        Column("price"),
        Column("range status"),
        Column("staked"),
        Column("value now"),
        Column("deposited"),
        Column(f"{w} LP P&L $"),
        Column(f"{w} LP P&L vs HODL $"),
        Column(f"{w} realized APR", pct=True),
        Column("decision: reason"),
    )
    rows = []
    for p in positions_of(status):
        in_range = p.get("in_range")
        decision = _text(p.get("decision"))
        reason = p.get("reason")
        if isinstance(reason, str) and reason.strip():
            decision = f"{decision}: {_clip(reason.strip(), REASON_CLIP)}"
        rows.append((
            _text(p.get("pair")),
            fmt_range(p.get("range")),
            fmt_price(p.get("price")),
            DASH if not isinstance(in_range, bool) else ("IN range" if in_range else "OUT of range"),
            DASH if not isinstance(p.get("staked"), bool) else ("yes" if p["staked"] else "no"),
            fmt_usd(p.get("value_usd")),
            fmt_usd(p.get("deposited_usd")),
            fmt_usd(p.get("pnl_usd"), signed=True),
            fmt_usd(p.get("pnl_vs_hodl_usd"), signed=True),
            fmt_pct(p.get("apr_realized"), signed=True, places=1),
            decision,
        ))
    return Table(columns, tuple(rows))


def _sort_scout(pools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Contract says pre-sorted; re-sorting is cheap and survives a daemon bug.
    return sorted(pools, key=lambda p: (num(p.get("expected_net_apr")) is None,
                                        -(num(p.get("expected_net_apr")) or 0.0)))


def scout_table(scout: Mapping[str, Any], limit: int = SCOUT_ROWS) -> Table:
    columns = (
        Column("pair"),
        Column("TVL"),
        Column("24h volume"),
        Column("modelled fee APR @ ±10%", pct=True),
        Column("modelled AERO APR @ ±10%", pct=True),
        Column("modelled LVR APR @ ±10%", pct=True),
        Column("edge ratio (income/LVR)"),
        Column("best mode, half-width (modelled)", pct=True),
        Column("modelled net APR", pct=True),
        Column("break-even deposit"),
        Column("confidence"),
        Column("flags"),
    )
    rows = []
    for p in _sort_scout(pools_of(scout))[:limit]:
        width = num(p.get("best_half_width_pct"))
        best = _text(p.get("best_mode"))
        if width is not None:
            best = f"{best} ±{width:g}%"
        edge = num(p.get("edge_ratio"))
        flags = p.get("flags")
        flag_text = ", ".join(str(f) for f in flags) if isinstance(flags, list) and flags else DASH
        rows.append((
            _text(p.get("pair")),
            fmt_usd_compact(p.get("tvl_usd")),
            fmt_usd_compact(p.get("volume_24h_usd")),
            fmt_pct(p.get("fee_apr_ref"), places=1),
            fmt_pct(p.get("aero_apr_ref"), places=1),
            fmt_pct(p.get("lvr_apr_ref"), places=1),
            DASH if edge is None else f"{edge:.1f}x",
            best,
            fmt_pct(p.get("expected_net_apr"), signed=True, places=1),
            fmt_usd(p.get("break_even_deposit_usd")),
            _text(p.get("confidence")),
            flag_text,
        ))
    return Table(columns, tuple(rows))


def _is_winner(exp: Mapping[str, Any], arm: Mapping[str, Any]) -> bool:
    """The contract does not say what `winner` holds. Accept the arm's slot,
    pair or pool, compared as strings."""
    winner = exp.get("winner")
    if winner is None:
        return False
    w = str(winner)
    return w in {str(arm.get(k)) for k in ("slot", "pair", "pool") if arm.get(k) is not None}


def experiments_table(status: Mapping[str, Any]) -> Table:
    w = source_word(status.get("mode"))
    columns = (
        Column("experiment"),
        Column("status"),
        Column("arm"),
        Column("deposited"),
        Column(f"{w} LP P&L $"),
        Column(f"{w} LP P&L %", pct=True),
        Column(f"{w} realized APR", pct=True),
        Column("winner"),
    )
    rows = []
    for exp in experiments_of(status):
        arms = _dicts(exp.get("arms"))
        if not arms:
            rows.append((_text(exp.get("id")), _text(exp.get("status")), DASH,
                         DASH, DASH, DASH, DASH, DASH))
            continue
        for i, arm in enumerate(arms):
            label = _text(arm.get("pair"))
            if arm.get("slot") is not None:
                label += f" #{arm['slot']}"
            rows.append((
                _text(exp.get("id")) if i == 0 else "",
                _text(exp.get("status")) if i == 0 else "",
                label,
                fmt_usd(arm.get("deposited_usd")),
                fmt_usd(arm.get("pnl_usd"), signed=True),
                fmt_pct(arm.get("pnl_pct"), signed=True),
                fmt_pct(arm.get("apr_realized"), signed=True, places=1),
                "WINNER" if _is_winner(exp, arm) else "",
            ))
    return Table(columns, tuple(rows))


def actions_table(status: Mapping[str, Any], tz: tzinfo | None = None,
                  limit: int = ACTION_ROWS) -> Table:
    columns = (
        Column("time"),
        Column("kind"),
        Column("slot"),
        Column("detail"),
        Column("tx (basescan)"),
    )
    actions = actions_of(status)
    # File order is oldest-first; reverse it, then stable-sort by ts so equal
    # timestamps keep the later file entry first.
    ordered = sorted(reversed(actions), key=lambda a: -(num(a.get("ts")) or 0.0))
    rows = []
    for a in ordered[:limit]:
        txs = a.get("tx")
        if isinstance(txs, str):
            txs = [txs]
        links = " ".join(tx_link(t) for t in txs) if isinstance(txs, list) and txs else DASH
        rows.append((
            fmt_ts(a.get("ts"), tz),
            _text(a.get("kind")),
            _text(a.get("slot")),
            _text(a.get("detail")),
            links,
        ))
    return Table(columns, tuple(rows))


# -- the kill switch -------------------------------------------------------------------


def kill_path(home: Path | None = None) -> Path:
    return (home or state_dir()) / KILL_FILE


def is_killed(home: Path | None = None) -> bool:
    return kill_path(home).exists()


def set_kill(on: bool, home: Path | None = None) -> bool:
    """Create (`on`) or delete the `KILL` file. Returns whether it now exists.

    This is the only write soltui makes outside its own config dir. Creation
    uses `O_CREAT|O_EXCL`, so it is atomic and a second press is a no-op; the
    file's contents are ignored by the daemon, a timestamp is only for humans.
    Deletion tolerates the file already being gone.
    """
    path = kill_path(home)
    if on:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return True
        try:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            os.write(fd, f"killed from soltui at {stamp}\n".encode())
        finally:
            os.close(fd)
        return True
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    return False
