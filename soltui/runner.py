"""Background sweep runner. Turns a roster into results while keeping the UI live.

The menu-bar indicator and the Backtest tab both need "how much is left", which
means the sweep has to report progress as it goes rather than blocking until
done. This module owns that: a worker thread, a progress callback, and a
cancellation flag.

## Threading contract

`AppState` is written from the worker thread and read from the UI thread. That is
safe here for one specific reason: every field is a scalar or a list that is
*replaced* rather than mutated in place, and CPython guarantees attribute
assignment is atomic. There is no read-modify-write on shared state, so no lock is
needed. If you add a field that gets `+=`'d or `.append()`ed from the worker,
that reasoning stops holding -- take the lock this class already exposes.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from backtester.core.cpcv import cpcv_evaluate
from backtester.core.data import CsvLoader, frame_to_arrays
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import CostConfig, Mode

from .config import Settings
from .roster import Roster, RosterEntry
from .status import AppState, Phase

ProgressFn = Callable[[int, int, str], None]


@dataclass
class SweepRow:
    """One evaluated configuration, flattened for display."""

    label: str
    family: str
    median_sharpe: float
    iqr: float
    frac_positive: float
    median_return: float
    trades: int
    evaluable: bool
    reason: str = ""


@dataclass
class SweepOutcome:
    """Everything a completed sweep produced."""

    rows: list[SweepRow] = field(default_factory=list)
    cancelled: bool = False
    error: str | None = None

    @property
    def evaluable(self) -> list[SweepRow]:
        """Rows that cleared the warm-up and trade-count floors."""
        return [r for r in self.rows if r.evaluable]

    @property
    def positive(self) -> list[SweepRow]:
        """Evaluable rows with a positive median path Sharpe."""
        return [r for r in self.evaluable if r.median_sharpe > 0]

    def ranked(self) -> list[SweepRow]:
        """Evaluable rows, best median Sharpe first."""
        return sorted(self.evaluable, key=lambda r: r.median_sharpe, reverse=True)


def load_arrays(settings: Settings) -> dict[str, np.ndarray]:
    """Load the configured price series as engine arrays.

    Raises FileNotFoundError with the fetch command when the cache is missing,
    which is the single most common first-run failure.
    """
    from pathlib import Path

    path = Path(settings.data_dir) / f"{settings.asset.upper()}_{settings.interval}.csv"
    loader = CsvLoader(path, allow_gaps=True)
    df = loader.load(settings.asset, settings.start or None, settings.end or None,
                     settings.interval)
    return frame_to_arrays(df)


def engine_config(settings: Settings) -> EngineConfig:
    """Build an EngineConfig from settings.

    Mode is hard-wired to SPOT: this build has no live path and no leverage
    surface in the UI, so there is nothing that should be selecting PERP here.
    """
    return EngineConfig(
        mode=Mode.SPOT,
        leverage=1.0,
        initial_capital=settings.capital,
        interval=settings.interval,
        fill_delay=settings.fill_delay,
        costs=CostConfig(
            fee_bps=settings.fee_bps, slippage_bps=settings.slippage_bps
        ),
    )


class SweepRunner:
    """Runs a roster through CPCV on a worker thread, reporting progress."""

    def __init__(self, state: AppState) -> None:
        self.state = state
        self.lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self.outcome: SweepOutcome | None = None

    @property
    def running(self) -> bool:
        """True while a sweep is in flight."""
        return self._thread is not None and self._thread.is_alive()

    def cancel(self) -> None:
        """Ask the worker to stop at the next configuration boundary."""
        self._cancel.set()

    def start(
        self,
        roster: Roster,
        settings: Settings,
        on_done: Callable[[SweepOutcome], None] | None = None,
    ) -> None:
        """Begin a sweep. Refuses to start a second one concurrently."""
        if self.running:
            raise RuntimeError("a sweep is already running")
        if len(roster) == 0:
            raise ValueError("the roster is empty — add a strategy first")
        self._cancel.clear()
        self.outcome = None
        self._thread = threading.Thread(
            target=self._run, args=(roster, settings, on_done), daemon=True
        )
        self._thread.start()

    def _run(
        self,
        roster: Roster,
        settings: Settings,
        on_done: Callable[[SweepOutcome], None] | None,
    ) -> None:
        """Worker body. Never raises into the thread boundary."""
        outcome = SweepOutcome()
        try:
            arrays = load_arrays(settings)
            cfg = engine_config(settings)
            entries: Sequence[RosterEntry] = roster.entries
            total = len(entries)
            self.state.phase = Phase.RUNNING
            self.state.activity = "backtest"
            self.state.total = total
            self.state.done = 0
            self.state.error = None

            for i, entry in enumerate(entries, start=1):
                if self._cancel.is_set():
                    outcome.cancelled = True
                    break
                outcome.rows.append(
                    self._evaluate(entry, arrays, cfg, settings)
                )
                self.state.done = i

            if not outcome.cancelled:
                best = max(
                    (r.median_return for r in outcome.evaluable), default=None
                )
                self.state.last_backtest_return = best
                self.state.phase = Phase.DONE
            else:
                self.state.phase = Phase.IDLE
        except FileNotFoundError as exc:
            outcome.error = str(exc)
            self.state.phase = Phase.ERROR
            self.state.error = "no data — run the fetch command"
        except Exception as exc:  # noqa: BLE001 - a UI worker must not die silently
            outcome.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            self.state.phase = Phase.ERROR
            self.state.error = f"{type(exc).__name__}"
        finally:
            self.outcome = outcome
            if on_done is not None:
                on_done(outcome)

    def _evaluate(
        self,
        entry: RosterEntry,
        arrays: dict[str, np.ndarray],
        cfg: EngineConfig,
        settings: Settings,
    ) -> SweepRow:
        """CPCV-evaluate one roster entry."""
        from backtester.core.strategies import build

        res = cpcv_evaluate(
            entry.label,
            lambda: build(entry.name, **entry.params),
            arrays,
            cfg,
            n_groups=settings.cpcv_groups,
            k_test=settings.cpcv_k,
        )
        return SweepRow(
            label=entry.label,
            family=entry.family,
            median_sharpe=res.median_sharpe,
            iqr=res.spread,
            frac_positive=res.frac_positive,
            median_return=res.median_return,
            trades=res.total_trades,
            evaluable=not res.insufficient,
            reason=res.reason,
        )


def quick_backtest(
    entry: RosterEntry, settings: Settings
) -> tuple[Any, dict[str, np.ndarray]]:
    """Single full-sample backtest for one entry, for the paper simulator.

    Returns (result, arrays) so the caller can build a PaperSession without
    reloading the data.
    """
    from backtester.core.strategies import build

    arrays = load_arrays(settings)
    result = run_backtest(
        build(entry.name, **entry.params), arrays, engine_config(settings)
    )
    return result, arrays
