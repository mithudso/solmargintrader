"""Job queue for the background backtest sweep. Pure logic; no UI, no processes.

The TUI's own sweep (`runner.py`) evaluates the roster and blocks a thread until
it finishes. This module serves a different question: *"keep grinding through
parameter space in the background, cheapest-first, and show me the leaderboard
whenever I look."* That means three things this module owns:

  * **A deterministic, resumable job list.** Every job has a stable `job_id`
    derived from its content, so a worker killed mid-sweep resumes by skipping
    the ids already in the results file rather than starting over.
  * **An ordering that puts the most promising work first.** A background sweep
    is never finished — it is interrupted. So the value delivered is whatever it
    got through, which makes the ORDER the main design decision, not the extent.
  * **The evidence floor, carried into the leaderboard.** `research/sweep.py`
    exists to avoid the "liar's leaderboard": ranking on in-sample performance,
    or ranking a Sharpe computed from three trades. A background sweep that
    quietly re-introduces either is worse than no sweep, because it looks
    authoritative and runs unattended.

## Where "most promising" comes from

Not from a ranking invented here. Each strategy card declares a
`success_likelihood` (`moderate` / `low` / `very-low`) and per-horizon presets,
and `tests/test_strategy_cards.py` checks the machine-readable half against the
code in both directions. So the ordering reads the cards:

  1. perturbation distance — every card's own horizon preset before ANY
     variation of one, then near variations, then far ones;
  2. the card's declared likelihood, most promising first, within a distance;
  3. strategy id and horizon, purely so the order is reproducible.

Distance outranks likelihood deliberately: an interrupted sweep should have
covered every card's published configuration before it starts guessing at any of
them. The reverse order would spend the first hours on far variations of one
promising card while another card's own preset went unevaluated.

Sourcing defaults from `strategy_cards.load_all()` rather than copying them here
is deliberate. A second copy of the defaults would pass every test and go stale
silently, which is the exact drift the card test was written to catch.

## The file contract

The worker is a separate process, so the TUI shares *files* with it, not memory:

  * `results.jsonl` — one JSON object per line, append-only. The worker writes a
    whole line in a single `write()`; readers skip any line that does not parse,
    which is what makes a read during an in-flight append safe rather than fatal.
  * `state.json` — progress, rewritten via tmp+rename so a reader never observes
    a half-written file.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from backtester.core.strategy_cards import HORIZONS, StrategyCard, load_all

from .config import CONFIG_DIR

# Where the worker and the TUI meet. Under the existing config dir rather than a
# new location, so there is one place to look for everything this app owns.
BG_DIR = CONFIG_DIR / "bg"
RESULTS_PATH = BG_DIR / "results.jsonl"
STATE_PATH = BG_DIR / "state.json"
PID_PATH = BG_DIR / "worker.pid"


def active_results_path() -> Path:
    """Return the selected sweep file; absence selects the original history."""
    pointer = RESULTS_PATH.parent / "active-results"
    try:
        name = pointer.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return RESULTS_PATH
    if not re.fullmatch(r"results-[0-9a-f]{32}\.jsonl", name):
        raise ValueError(f"invalid background results selection at {pointer}")
    return RESULTS_PATH.parent / name

# An asset symbol becomes a filename (`data/SOL_1d.csv`), so it has to be a
# single path component. Without this, `--asset ../../etc/passwd` reads outside
# the data directory -- and because `Path("data") / "/tmp/x"` DISCARDS the left
# operand, an absolute value escapes entirely. Read-only and same-privilege, but
# it is still an unvalidated value crossing into a path.
ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Same floor as research/sweep.py:51. A Sharpe computed from a handful of trades
# is noise, and noise sorted descending is a ranking of luck. Rows below the
# floor are listed, never ranked.
MIN_TRADES = 10

# Bar interval each horizon is defined at, matching research/sweep.py's HORIZONS.
# A horizon is a parameter SCALE, and a scale is only meaningful against a bar
# size -- running the "short" presets against daily bars would evaluate a
# 12-bar fast MA as 12 days rather than 12 hours and report it under the wrong
# name. Derived here rather than accepted from the caller for that reason.
HORIZON_INTERVAL = {"short": "1h", "medium": "1d", "long": "1d"}

# Declared likelihood, most promising first. Anything a card does not declare
# sorts last rather than raising -- a new likelihood value should degrade the
# ordering, not stop the sweep.
LIKELIHOOD_ORDER = {"moderate": 0, "low": 1, "very-low": 2}
_UNKNOWN_LIKELIHOOD = len(LIKELIHOOD_ORDER)

# Multiplicative perturbations of a card's preset, grouped by distance. Tier 0 is
# the preset itself, untouched -- the published configuration is the single most
# informative point in the space, so it is always evaluated before any variation
# of it. Later tiers vary ONE parameter at a time: a joint grid over every
# parameter explodes combinatorially and spends a background sweep's whole
# budget on the first strategy.
# Nearer variations come FIRST, because "most promising" means "closest to the
# configuration someone had a reason to publish". An earlier version had these
# reversed, so `--max-tier 1` swept only the half/double extremes while its help
# text sold it as the cheap, close-in option.
PERTURBATION_TIERS: tuple[tuple[float, ...], ...] = (
    (),               # tier 0: the preset as declared
    (0.75, 1.5),      # tier 1: near variations
    (0.5, 2.0),       # tier 2: half and double
)


@dataclass(frozen=True)
class Job:
    """One configuration to evaluate.

    `frozen=True` stops the fields being rebound, but a dict field can still be
    mutated in place through the reference -- and `job_id` is recomputed from
    `params` on every access, so an in-place edit would silently change a job's
    identity after it had been written to the results file. `__post_init__`
    therefore replaces the dict with a read-only view of a private copy, which
    makes the "stable content hash" claim true rather than merely intended.
    """

    strategy: str
    horizon: str
    asset: str
    interval: str
    params: Mapping[str, Any] = field(default_factory=dict)
    # Which perturbation tier produced this job. 0 means "the card's preset".
    tier: int = 0
    # Human-readable note on what was varied, e.g. "fast x0.5". Empty at tier 0.
    variation: str = ""
    likelihood: str = ""
    family: str = ""

    def __post_init__(self) -> None:
        """Freeze `params` behind a read-only view of our own copy."""
        object.__setattr__(
            self, "params", MappingProxyType(dict(self.params))
        )

    def __hash__(self) -> int:
        """Hash the content id rather than the fields.

        The generated `__hash__` would call `hash()` on the params mapping and
        raise, so the frozen dataclass advertised a hashability it did not have
        -- `set(jobs)` or using a Job as a dict key blew up at runtime.
        """
        return hash(self.job_id)

    @property
    def job_id(self) -> str:
        """Stable content hash, used for resume and de-duplication.

        Hashes the *semantic* fields only -- `variation` and `likelihood` are
        commentary, and including them would make an id change when a card's
        prose changed, silently re-running work already done.
        """
        payload = json.dumps(
            {
                "strategy": self.strategy,
                "horizon": self.horizon,
                "asset": self.asset,
                "interval": self.interval,
                "params": _canonical(self.params),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    @property
    def label(self) -> str:
        """Short display label."""
        base = f"{self.strategy} · {self.horizon}"
        return f"{base} · {self.variation}" if self.variation else base


@dataclass
class JobResult:
    """A CPCV evaluation of one job, as written to the results file."""

    job_id: str
    strategy: str
    horizon: str
    asset: str
    interval: str
    params: dict[str, Any]
    tier: int
    variation: str
    family: str
    median_sharpe: float
    iqr: float
    frac_positive: float
    median_return: float
    trades: int
    evaluable: bool
    reason: str = ""
    seconds: float = 0.0
    # Unix time the row was written. 0.0 means the row predates this field, so its date is unknown:
    # the Strategies tab says so rather than inventing one.
    finished_at: float = 0.0

    @property
    def label(self) -> str:
        """Short display label, matching `Job.label`."""
        base = f"{self.strategy} · {self.horizon}"
        return f"{base} · {self.variation}" if self.variation else base

    @property
    def ranked_ok(self) -> bool:
        """True when this row may appear in a ranking rather than a listing.

        Two gates, not one: the engine must have judged the path evaluable at
        all, AND the trade count must clear the evidence floor.
        """
        return self.evaluable and self.trades >= MIN_TRADES

    def to_json(self) -> str:
        """One line of `results.jsonl`."""
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobResult":
        """Rebuild from a parsed line, tolerating fields added since it was written.

        Numeric fields are coerced rather than trusted. A single corrupted line
        carrying a string where a float belongs would otherwise reach
        `leaderboard`'s sort and raise TypeError comparing str to float -- taking
        out the whole pane over one bad row, which is exactly the failure the
        line-skipping in `read_results` exists to prevent.
        """
        known = {f for f in cls.__dataclass_fields__}  # noqa: SLF001 - dataclass API
        clean = {k: v for k, v in data.items() if k in known}
        for name in ("median_sharpe", "iqr", "frac_positive", "median_return", "seconds",
                     "finished_at"):
            if name in clean:
                clean[name] = _as_float(clean[name])
        for name in ("trades", "tier"):
            if name in clean:
                clean[name] = _as_int(clean[name])
        if "evaluable" in clean:
            clean["evaluable"] = bool(clean["evaluable"])
        return cls(**clean)


@dataclass
class QueueState:
    """Worker progress, rewritten after every job."""

    phase: str = "idle"  # idle | running | stopped | done | error
    done: int = 0
    total: int = 0
    current: str = ""
    asset: str = ""
    interval: str = ""
    pid: int = 0
    started_at: float = 0.0
    updated_at: float = 0.0
    error: str = ""
    results_path: str = ""

    @property
    def remaining(self) -> int:
        """Jobs left; 0 when the total is unknown."""
        return max(self.total - self.done, 0) if self.total > 0 else 0

    @property
    def percent(self) -> float | None:
        """Completion in [0, 1], or None when the total is unknown."""
        if self.total <= 0:
            return None
        return min(self.done / self.total, 1.0)


# -- building the queue ----------------------------------------------------


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value read off disk to a float, defaulting when it cannot be."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    # NaN would propagate silently through a sort and a median; a corrupt row
    # should read as uninformative, not as a value that poisons comparisons.
    return default if out != out else out


def _as_int(value: Any, default: int = 0) -> int:
    """Coerce a value read off disk to an int, defaulting when it cannot be."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_asset(asset: str) -> str:
    """Return the upper-cased symbol, or raise if it could escape the data dir."""
    symbol = asset.strip().upper()
    if not ASSET_RE.match(symbol):
        raise ValueError(
            f"invalid asset {asset!r}: expected a plain symbol like SOL, "
            "with no path separators"
        )
    return symbol


def _canonical(params: Mapping[str, Any]) -> dict[str, Any]:
    """Params in a form that hashes identically across runs.

    Floats that are exactly integral are folded to int so that `20` and `20.0`,
    which the engine cannot tell apart, do not become two jobs.
    """
    out: dict[str, Any] = {}
    for key in sorted(params):
        value = params[key]
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        out[key] = value
    return out


def _perturb(value: Any, factor: float) -> Any | None:
    """Scale one parameter, or None when it is not meaningfully scalable.

    Booleans are excluded explicitly: `bool` is a subclass of `int` in Python, so
    a naive numeric check would turn `allow_short=True` into `allow_short=2`.
    An int that would land below 1 is dropped rather than clamped -- clamping
    would produce a duplicate of the tier-0 job under a different label.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, int):
        scaled = int(round(value * factor))
        if scaled < 1 or scaled == value:
            return None
        return scaled
    scaled = round(value * factor, 6)
    if scaled == value or scaled == 0:
        return None
    return scaled


def jobs_for_card(
    card: StrategyCard,
    horizon: str,
    asset: str,
    interval: str | None = None,
    *,
    max_tier: int = 2,
) -> list[Job]:
    """Every job this card contributes, nearest-to-the-preset first.

    `interval` defaults to the one the horizon is defined at; pass it only to
    override, and only knowing the presets were not scaled for it.
    """
    interval = interval or HORIZON_INTERVAL.get(horizon, "1d")
    try:
        preset = card.preset(horizon)
    except KeyError:
        return []
    if card.required_params():
        # A required parameter has no default anywhere, so there is nothing
        # honest to sweep it from. The ladder grid is the live example.
        return []

    strategy = card.registry_key or card.id
    jobs = [
        Job(
            strategy=strategy,
            horizon=horizon,
            asset=asset,
            interval=interval,
            params=_canonical(preset),
            tier=0,
            likelihood=card.success_likelihood,
            family=card.family,
        )
    ]
    seen = {jobs[0].job_id}

    for tier, factors in enumerate(PERTURBATION_TIERS):
        if tier == 0 or tier > max_tier:
            continue
        for name in sorted(preset):
            for factor in factors:
                scaled = _perturb(preset[name], factor)
                if scaled is None:
                    continue
                params = dict(preset)
                params[name] = scaled
                job = Job(
                    strategy=strategy,
                    horizon=horizon,
                    asset=asset,
                    interval=interval,
                    params=_canonical(params),
                    tier=tier,
                    variation=f"{name} x{factor:g}",
                    likelihood=card.success_likelihood,
                    family=card.family,
                )
                if job.job_id in seen:
                    continue
                seen.add(job.job_id)
                jobs.append(job)
    return jobs


def build_queue(
    asset: str,
    *,
    horizons: Sequence[str] = HORIZONS,
    cards: dict[str, StrategyCard] | None = None,
    max_tier: int = 2,
    strategies: Sequence[str] | None = None,
) -> list[Job]:
    """The full job list, most promising first.

    `strategies` restricts the list to those registry names (None means every buildable card).

    Only cards that this repo can actually build and has data for are included;
    a spec-only card would fail at `build()` time and turn every one of its jobs
    into an identical error row.
    """
    asset = validate_asset(asset)
    catalogue = load_all() if cards is None else cards
    wanted = None if strategies is None else set(strategies)
    jobs: list[Job] = []
    for card in catalogue.values():
        if not card.buildable or not card.data_available:
            continue
        if wanted is not None and (card.registry_key or card.id) not in wanted:
            continue
        for horizon in horizons:
            jobs.extend(jobs_for_card(card, horizon, asset, max_tier=max_tier))
    return dedupe(order_jobs(jobs))


def dedupe(jobs: Sequence[Job]) -> list[Job]:
    """Drop jobs whose evaluation would be identical to one already in the list.

    `job_id` includes the horizon, because a horizon is a meaningful label. But
    two horizons can resolve to the same parameters at the same interval --
    `buy_and_hold` has no parameters at all, and `medium` and `long` are both
    daily -- and evaluating that twice buys nothing but heat. Keeps the FIRST
    occurrence, so ordering must already have run: the survivor is then the
    most promising of the identical set.
    """
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Job] = []
    for job in jobs:
        key = (
            job.strategy,
            job.asset,
            job.interval,
            json.dumps(_canonical(job.params), sort_keys=True, separators=(",", ":")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def order_jobs(jobs: Iterable[Job]) -> list[Job]:
    """Sort by declared promise, then distance from the preset, then id.

    Tier before likelihood inside a tier would front-load one strategy's whole
    neighbourhood; likelihood before tier would evaluate far variations of a
    `moderate` card before the published preset of a `low` one. Tier first is the
    right call: an interrupted sweep should have covered every card's own
    configuration before it starts guessing at any of them.
    """
    return sorted(
        jobs,
        key=lambda j: (
            j.tier,
            LIKELIHOOD_ORDER.get(j.likelihood, _UNKNOWN_LIKELIHOOD),
            j.strategy,
            j.horizon,
            j.variation,
        ),
    )


def pending(jobs: Sequence[Job], done_ids: set[str]) -> list[Job]:
    """Jobs not already present in the results file, order preserved."""
    return [j for j in jobs if j.job_id not in done_ids]


# -- the file contract -----------------------------------------------------


def ensure_dir(path: Path | None = None) -> Path:
    """Create the shared directory if it is missing."""
    path = path or BG_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_result(result: JobResult, path: Path | None = None) -> None:
    """Append one result as a single line.

    One `write()` of one line, opened in append mode: the kernel serialises an
    O_APPEND write, so a reader can be part-way through the file without ever
    seeing two results interleaved on one line.

    The path is resolved HERE rather than in the signature. A `path=RESULTS_PATH`
    default binds the module constant once, at import, so a test that points the
    constant somewhere temporary would still be writing to the real file.
    """
    path = path or RESULTS_PATH
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(result.to_json() + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _parse_lines(text: str) -> list[JobResult]:
    """Parse whole lines, skipping any that do not decode.

    A read that races an in-flight append can observe a final line with no
    newline yet. Skipping it means the pane shows one fewer row for a second;
    raising would mean the pane shows an error instead of the leaderboard.
    """
    out: list[JobResult] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "job_id" not in data:
            continue
        try:
            out.append(JobResult.from_dict(data))
        except TypeError:
            continue
    return out


def read_results(path: Path | None = None) -> list[JobResult]:
    """Every parseable result."""
    path = path or active_results_path()
    if not path.exists():
        return []
    return _parse_lines(path.read_text(encoding="utf-8", errors="replace"))


@dataclass(frozen=True)
class ResultsCursor:
    """How far a reader has consumed the results file, and which file that was.

    The identity half is load-bearing. A byte offset alone cannot tell "the
    worker appended" from "the file was deleted and a new sweep regrew past my
    offset" -- the second looks like a bigger file either way, and reading from
    the stale offset then splices one sweep's tail onto another's rows. Result
    lines are near enough uniform in length that checking for a line boundary
    does not catch it either; the inode does, because a replacement gets a new
    one.
    """

    offset: int = 0
    inode: int = 0
    device: int = 0
    # Modification time of the file state this cursor was taken against, so a
    # poller can ask "has anything changed?" without a second stat that could
    # observe a NEWER file than the one that was actually read. Recording an
    # mtime taken after the read would silently strand any row appended during
    # it -- and if that was a sweep's last row, the leaderboard stays one result
    # short until someone refreshes by hand.
    mtime: float = 0.0

    def matches(self, stat: os.stat_result) -> bool:
        """True when `stat` is the same file this cursor was taken against."""
        return (self.inode, self.device) == (stat.st_ino, stat.st_dev)


def read_results_since(
    cursor: ResultsCursor | None = None, path: Path | None = None
) -> tuple[list[JobResult], ResultsCursor, bool]:
    """Results appended since `cursor`, the new cursor, and whether it restarted.

    Re-reading the whole file on every append makes the cost of watching a sweep
    quadratic in the number of jobs -- and a long background sweep is precisely
    where the file gets big. Reading only the tail keeps a refresh proportional
    to what actually arrived.

    The third element is True when the read started from the beginning because
    the file was truncated or replaced. A caller holding earlier rows must drop
    them in that case; without the flag it could not tell "here is the tail" from
    "here is a whole new file".
    """
    path = path or active_results_path()
    cursor = cursor or ResultsCursor()
    try:
        # Open first, then stat the OPEN DESCRIPTOR. Statting by name and then
        # opening by name would let the file be replaced in between, and the
        # cursor would carry the old file's inode over the new file's bytes --
        # defeating the identity check this cursor exists for.
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return [], ResultsCursor(), True

    with fh:
        stat = os.fstat(fh.fileno())
        offset = cursor.offset
        restarted = not cursor.matches(stat) or offset > stat.st_size
        if restarted:
            offset = 0
        fh.seek(offset)
        text = fh.read()
    # Only consume through the last complete line; a trailing partial line is
    # left unread so the next call re-reads it once it is whole.
    cut = text.rfind("\n")
    here = ResultsCursor(offset, stat.st_ino, stat.st_dev, stat.st_mtime)
    if cut == -1:
        return [], here, restarted
    consumed = text[: cut + 1]
    # `to_json` writes with json.dumps' default ensure_ascii=True, so the file is
    # pure ASCII and this byte count equals the file's. A field written with
    # ensure_ascii=False would break that equivalence and this arithmetic.
    advanced = ResultsCursor(
        offset + len(consumed.encode("utf-8")),
        stat.st_ino,
        stat.st_dev,
        stat.st_mtime,
    )
    return _parse_lines(consumed), advanced, restarted


def completed_ids(results: Sequence[JobResult]) -> set[str]:
    """The ids a resumed worker should skip."""
    return {r.job_id for r in results}


def write_state(state: QueueState, path: Path | None = None) -> None:
    """Rewrite the state file atomically.

    tmp+rename rather than truncate+write: a reader polling every couple of
    seconds will otherwise eventually catch a zero-length file and report the
    sweep as idle while it is running.
    """
    path = path or STATE_PATH
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(asdict(state), fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_state(path: Path | None = None) -> QueueState:
    """Current worker state, or a fresh idle state when there is none."""
    path = path or STATE_PATH
    if not path.exists():
        return QueueState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return QueueState()
    if not isinstance(data, dict):
        return QueueState()
    known = {f for f in QueueState.__dataclass_fields__}  # noqa: SLF001
    clean = {k: v for k, v in data.items() if k in known}
    # Same reasoning as JobResult.from_dict: a non-numeric `total` read off disk
    # would make `percent` raise inside a UI refresh.
    for name in ("done", "total", "pid"):
        if name in clean:
            clean[name] = _as_int(clean[name])
    for name in ("started_at", "updated_at"):
        if name in clean:
            clean[name] = _as_float(clean[name])
    for name in ("phase", "current", "asset", "interval", "error", "results_path"):
        if name in clean and not isinstance(clean[name], str):
            clean[name] = str(clean[name])
    try:
        return QueueState(**clean)
    except TypeError:
        return QueueState()


# -- reading the results ---------------------------------------------------


@dataclass(frozen=True)
class MissingSeries:
    """A price file the queue needs and the command that would create it."""

    asset: str
    interval: str
    path: Path

    @property
    def command(self) -> list[str]:
        """The fetch argv, as a list so it can be run without a shell."""
        return [
            "python3", "-m", "backtester.core.fetch",
            "--asset", self.asset, "--interval", self.interval,
        ]

    @property
    def command_text(self) -> str:
        """The same command, for someone to copy out of the pane."""
        return " ".join(self.command)


def missing_series(
    asset: str,
    *,
    horizons: Sequence[str] = HORIZONS,
    data_dir: str | Path = "data",
) -> list[MissingSeries]:
    """Price files the sweep needs for these horizons but does not have.

    Checked up front rather than discovered job by job. The queue interleaves
    intervals by promise, so without this the first hourly job is where a missing
    1h file surfaces -- minutes in, after the pane has already said "running".
    Knowing before the sweep starts is what lets the tab offer to fix it.
    """
    asset = validate_asset(asset)
    root = Path(data_dir)
    seen: set[str] = set()
    out: list[MissingSeries] = []
    for horizon in horizons:
        interval = HORIZON_INTERVAL.get(horizon, "1d")
        if interval in seen:
            continue
        seen.add(interval)
        path = root / f"{asset}_{interval}.csv"
        if not path.exists():
            out.append(MissingSeries(asset, interval, path))
    return sorted(out, key=lambda m: m.interval)


def for_asset(results: Sequence[JobResult], asset: str | None) -> list[JobResult]:
    """Rows for one asset, or all rows when no asset is given.

    Every sweep shares one results file, so a run against a second asset lands
    beside the first. Ranking them together would let a BTC configuration take
    the top row of a table the user is reading as SOL -- a wrong answer, not
    merely an untidy one. `job_id` already includes the asset, so resume and
    dedup were never affected; only the read side needed scoping.
    """
    if asset is None:
        return list(results)
    symbol = asset.strip().upper()
    return [r for r in results if r.asset.upper() == symbol]


def leaderboard(
    results: Sequence[JobResult], asset: str | None = None
) -> tuple[list[JobResult], list[JobResult]]:
    """Split results into (ranked, below-floor), optionally scoped to one asset.

    Returns two lists rather than one sorted list with a flag column, because a
    caller that renders "the top row" must not be able to reach a below-floor row
    by accident. The floor rows are still returned -- hiding them would overstate
    how much of the space has been usefully covered.
    """
    rows = for_asset(results, asset)
    ranked = sorted(
        (r for r in rows if r.ranked_ok),
        key=lambda r: r.median_sharpe,
        reverse=True,
    )
    floor = sorted(
        (r for r in rows if not r.ranked_ok),
        key=lambda r: (r.strategy, r.horizon, r.variation),
    )
    return ranked, floor


# Which horizon's card-preset row stands for a strategy in the one-line result. Medium is the
# card's headline daily configuration; the others only stand in when it is absent.
_PRESET_HORIZON_ORDER = ("medium", "long", "short")


@dataclass(frozen=True)
class StrategyHistory:
    """What the background sweep has recorded for one strategy on one asset."""

    name: str
    runs: int = 0               # distinct configurations evaluated or attempted
    evaluable: int = 0          # of those, how many produced a usable CPCV result
    ranked: int = 0             # of those, how many cleared the trade floor
    positive: int = 0           # of the ranked, how many had median Sharpe above zero
    last_at: float = 0.0        # newest finished_at; 0.0 when no row carries a date
    preset: JobResult | None = None  # the card's own configuration, the fairest single number

    @property
    def tested(self) -> bool:
        """True once any configuration has been run for it."""
        return self.runs > 0

    @property
    def result_text(self) -> str:
        """One line a person can act on, or why there is no number."""
        if not self.tested:
            return "not tested"
        row = self.preset
        if row is None:
            return f"{self.runs} run(s), none at the card's own parameters"
        if not row.evaluable:
            return f"preset not evaluable: {row.reason or 'no usable result'}"[:120]
        thin = "" if row.trades >= MIN_TRADES else f" (under the {MIN_TRADES}-trade floor)"
        spread = f" · {self.positive}/{self.ranked} ranked runs positive" if self.ranked > 1 else ""
        return (f"{row.horizon}: Sharpe {row.median_sharpe:+.2f}, net {row.median_return:+.1%}, "
                f"{row.trades} trades{thin}{spread}")


def strategy_history(
    results: Sequence[JobResult], asset: str | None = None
) -> dict[str, StrategyHistory]:
    """Per-strategy test history for one asset, from the results file.

    Duplicates by `job_id` collapse to the newest row (a restarted sweep can write a job twice),
    so "runs" counts configurations, not file lines. The headline `preset` is the card's own
    parameters, never the best of many variations: choosing the best row would report the
    selection, not the strategy.
    """
    latest: dict[str, JobResult] = {}
    for row in for_asset(results, asset):
        previous = latest.get(row.job_id)
        if previous is None or row.finished_at >= previous.finished_at:
            latest[row.job_id] = row
    grouped: dict[str, list[JobResult]] = {}
    for row in latest.values():
        grouped.setdefault(row.strategy, []).append(row)
    out: dict[str, StrategyHistory] = {}
    for name, rows in grouped.items():
        ranked = [r for r in rows if r.ranked_ok]
        tier0 = [r for r in rows if r.tier == 0]
        preset = None
        for horizon in _PRESET_HORIZON_ORDER:
            pick = [r for r in tier0 if r.horizon == horizon]
            if pick:
                preset = pick[0]
                break
        out[name] = StrategyHistory(
            name=name, runs=len(rows), evaluable=sum(1 for r in rows if r.evaluable),
            ranked=len(ranked), positive=sum(1 for r in ranked if r.median_sharpe > 0),
            last_at=max((r.finished_at for r in rows), default=0.0), preset=preset,
        )
    return out


def format_when(timestamp: float) -> str:
    """Local date and time of a result, or why there is none."""
    if timestamp <= 0:
        return "date not recorded"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))


def summarise(
    state: QueueState,
    results: Sequence[JobResult],
    asset: str | None = None,
    *,
    worker_alive: bool | None = None,
) -> str:
    """One status line for the pane.

    Says how many rows are *rankable*, not how many were evaluated: the second
    number flatters the sweep, and the first is the one that bears on a decision.

    `worker_alive=False` against a state that still says "running" means the
    process died without writing a final state -- a kill -9, an OOM, a reboot.
    Reporting that as "running" would leave the pane claiming progress forever
    for a process that no longer exists, so it is called what it is.
    """
    ranked, floor = leaderboard(results, asset)
    positive = sum(1 for r in ranked if r.median_sharpe > 0)
    bits = []
    stalled = state.phase == "running" and worker_alive is False
    if stalled:
        bits.append(
            f"stopped unexpectedly at {state.done}/{state.total} "
            "— no worker is running; press Start to resume"
        )
    elif state.phase == "running":
        pct = state.percent
        pct_txt = f" ({pct:.0%})" if pct is not None else ""
        bits.append(f"running {state.done}/{state.total}{pct_txt}, {state.remaining} left")
    elif state.phase == "error":
        error = state.error or "unknown"
        if worker_alive is False and "evaluation proof is missing or differs" in error:
            bits.append("previous sweep stopped: its evaluation proof no longer matches; "
                        "press Start fresh to start a separate sweep and preserve these results")
            bits.append(f"previous error: {error}")
        else:
            bits.append(f"error: {error}")
    else:
        bits.append(state.phase)
        # A sweep that finished having skipped a whole interval for want of its
        # price file still carries the reason. Showing it only in the "error"
        # phase would render a partly-blind sweep as an unqualified "done", with
        # every 1h configuration silently absent and nothing saying why.
        if state.error:
            bits.append(f"incomplete — {state.error}")
    bits.append(f"{len(ranked)} rankable, {positive} with positive median Sharpe")
    if floor:
        bits.append(f"{len(floor)} below the {MIN_TRADES}-trade floor")
    return " · ".join(bits)
