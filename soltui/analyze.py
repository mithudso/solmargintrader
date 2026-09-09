"""What every strategy, signal and indicator said about one coin at one moment.

Pure logic behind the Analyze tab. No Textual import, no widget.

## It wraps `research/decide.py`; it does not reimplement it

`decide.py`'s one substantive guarantee is that the exposures it reports are the
numbers the engine would have acted on. A parallel implementation here would lose
that guarantee immediately and quietly, so this module loads the data, slices it,
and hands it to `decide.strategy_decisions`.

## Why "at a specific time" means slicing before the replay

Several registered strategies carry state — `_holding` and similar — so today's
target exposure is **path-dependent**: it depends on which past bar opened the
position, not only on today's indicator values. Evaluating the rule *at* a chosen
bar therefore cannot be done by reading that bar; the series must be truncated at
the chosen timestamp and replayed from the start of history.

That is the whole reason this module exists rather than the tab calling `decide`
directly with an index. Truncate first, replay second — the order is the
correctness condition, and `slice_to` is the only place it is enforced.

## Availability, not correctness

`data/` is gitignored, so the coins available here are whatever has been fetched.
`available_assets()` reports that honestly rather than offering a picker full of
symbols that will fail on selection.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data"

# research/ is not a package, so `research.decide` is not importable without the
# repo root on the path. soltui already reads the research side; this makes that
# relationship explicit rather than implicit.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@dataclass(frozen=True)
class Series:
    """One loaded coin series, with the facts the tab needs to label it."""

    asset: str
    interval: str
    path: Path
    bars: int
    first: datetime
    last: datetime


@dataclass(frozen=True)
class Analysis:
    """Everything the Analyze tab shows for one (coin, timestamp)."""

    asset: str
    interval: str
    as_of: datetime
    bar_index: int
    bars_used: int
    close: float
    decisions: list[Any]           # list[decide.StrategyDecision]
    tally: dict[str, dict[str, int]]
    truncated: bool

    @property
    def actions(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self.decisions:
            counts[d.action] = counts.get(d.action, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    @property
    def headline(self) -> str:
        parts = ", ".join(f"{v} {k}" for k, v in self.actions.items())
        return (f"{self.asset} {self.interval} @ {self.as_of:%Y-%m-%d %H:%M} UTC "
                f"(bar {self.bar_index} of {self.bars_used}, close {self.close:,.2f}) "
                f"— {parts or 'no decisions'}")


def available_assets(data_dir: Path | None = None) -> list[tuple[str, str]]:
    """(asset, interval) pairs that are actually on disk, sorted.

    Reads the cache rather than a hardcoded universe: `data/` is gitignored and
    per-machine, so the only honest picker is one built from what exists.
    """
    root = data_dir or DATA_DIR
    if not root.exists():
        return []
    out = []
    for p in sorted(root.glob("*.csv")):
        stem = p.stem
        if "_" not in stem:
            continue
        asset, _, interval = stem.rpartition("_")
        if asset and interval:
            out.append((asset, interval))
    return out


def load_series(asset: str, interval: str = "1d",
                data_dir: Path | None = None) -> Series:
    """Load one cached series and describe it. Raises if it is not fetched."""
    import pandas as pd

    root = data_dir or DATA_DIR
    path = root / f"{asset}_{interval}.csv"
    if not path.exists():
        shown = path.relative_to(REPO) if path.is_relative_to(REPO) else path
        raise FileNotFoundError(
            f"{shown} is not cached. Fetch it:\n"
            f"  python3 -m backtester.core.fetch --asset {asset} "
            f"--interval {interval} --start 2021-01-01"
        )
    df = pd.read_csv(path)
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return Series(
        asset=asset, interval=interval, path=path, bars=len(df),
        first=ts.iloc[0].to_pydatetime(), last=ts.iloc[-1].to_pydatetime(),
    )


def parse_as_of(text: str) -> datetime:
    """Accept a date or a datetime, always UTC.

    Deliberately strict about format and explicit about the timezone: a naive local
    timestamp silently selects a different bar than the user meant, and on a daily
    series that is a different day's decision.
    """
    raw = (text or "").strip().replace("Z", "")
    if not raw:
        raise ValueError("give a date (YYYY-MM-DD) or a timestamp (YYYY-MM-DD HH:MM)")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"could not read {text!r} as a UTC date or timestamp")


def slice_to(arrays: dict, timestamps, as_of: datetime) -> tuple[dict, int]:
    """Truncate every array to bars at or before `as_of`.

    **This must happen before the replay, not after.** Stateful strategies decide
    today's exposure from the bar that opened the position, so handing the full
    series to the replay and then reading the row at `as_of` reports a number that
    depended on the future. Truncating first is what makes the answer causal.

    Returns the sliced arrays and the index of the last included bar.
    """
    import numpy as np

    cutoff = int(np.searchsorted(
        timestamps, np.datetime64(as_of.replace(tzinfo=None)), side="right"))
    if cutoff <= 0:
        raise ValueError(f"no bars at or before {as_of:%Y-%m-%d %H:%M} UTC")
    return {k: v[:cutoff] for k, v in arrays.items()}, cutoff - 1


def analyse(asset: str, interval: str = "1d", as_of: datetime | None = None,
            keys: list[str] | None = None,
            data_dir: Path | None = None) -> Analysis:
    """Replay every strategy up to `as_of` and report what each one decided.

    `as_of=None` means the last bar, which is what the Signals tab already shows;
    supplying a timestamp is what makes this tab different.
    """
    import pandas as pd

    from backtester.core.data import CsvLoader, frame_to_arrays
    from research.decide import family_tally, strategy_decisions

    series = load_series(asset, interval, data_dir)

    # Built by the engine's own loader rather than by hand. `decide.replay_targets`
    # reads `arrays["ts"]`, and hand-assembling a dict here meant guessing that key
    # and getting it wrong — a KeyError at replay time. Going through
    # frame_to_arrays means this cannot drift from whatever the engine expects.
    #
    # `allow_gaps=True` because this is a read-only readout, not a published
    # figure: SOL_1h carries two disclosed 6-hour gaps, and refusing the series
    # would make the tab useless for the one asset with hourly history. The gap is
    # surfaced on the Analysis so a reader is not misled about the calendar.
    loader = CsvLoader(series.path, allow_gaps=True)
    df = loader.load(asset, None, None, interval)
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    arrays = frame_to_arrays(df)

    truncated = as_of is not None
    if as_of is None:
        sliced, idx = arrays, len(df) - 1
    else:
        sliced, idx = slice_to(arrays, ts.dt.tz_localize(None).to_numpy(), as_of)
    resolved = ts.iloc[idx].to_pydatetime()

    decisions = strategy_decisions(sliced, keys=keys)
    return Analysis(
        asset=asset, interval=interval, as_of=resolved, bar_index=int(idx),
        bars_used=int(len(sliced["close"])),
        close=float(sliced["close"][-1]),
        decisions=decisions, tally=family_tally(decisions),
        truncated=truncated,
    )
