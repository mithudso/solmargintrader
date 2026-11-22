"""Peer-relative-value reversion: trade a cointegrated spread, not a raw price.

One mechanism serving two cards. `pairs_cointegration.md` runs it against BTC or
ETH, which this repo can fetch keyless; `jlp_vs_sol_relative_value.md` runs it
against JLP, whose price history nobody publishes — the code is identical and only
the peer series differs.

**Why this is not just `zscore` with extra steps.** A z-score entry assumes the
series it measures is stationary. Raw SOL price is not, so `zscore.md` applies a
stationarity-dependent method to a series that fails the assumption — a known
theoretical error that its measured result does not repair. Here the traded object
is the *residual* of `SOL ~ beta * peer`, which is constructed to be stationary,
and `require_cointegration` makes the strategy **refuse to trade at all** until an
ADF test says the residual plausibly is. That refusal is the point.

**Exposure is still single-asset.** This is an ordinary `Strategy`: the peer series
is an input to the signal, not a second leg that gets traded. So it measures
"does the spread predict SOL" and **not** the dollar-neutral long-SOL/short-peer
trade the literature describes. A real pairs trade needs short exposure in the peer,
which this harness cannot express — stated here because it is the difference between
what was measured and what the mechanism actually is.

**No look-ahead.** The peer array is aligned to the traded asset's bars by the
caller, and `on_bar` slices it to `history.i + 1` — never further. A misaligned peer
array is the one way to cheat here, so `align_peer` matches on timestamps and
refuses rather than truncating blindly.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from . import indicators as ind
from .cointegration import engle_granger
from .types import BarWindow


def align_peer(
    base_ts: np.ndarray, peer_ts: np.ndarray, peer_closes: np.ndarray
) -> np.ndarray:
    """Peer closes reindexed onto `base_ts`, or a raised error.

    Refuses rather than forward-filling: a silently-filled gap would make the
    spread look calmer than it was, which flatters every reversion statistic
    computed from it. The caller can drop bars deliberately if it wants to.
    """
    base_ts = np.asarray(base_ts, dtype="int64")
    peer_ts = np.asarray(peer_ts, dtype="int64")
    peer_closes = np.asarray(peer_closes, dtype="float64")
    if peer_ts.size != peer_closes.size:
        raise ValueError("peer timestamps and closes differ in length")

    lookup = dict(zip(peer_ts.tolist(), peer_closes.tolist()))
    missing = [int(t) for t in base_ts if int(t) not in lookup]
    if missing:
        raise ValueError(
            f"peer series is missing {len(missing)} of {base_ts.size} bars "
            f"(first at epoch {missing[0]}); align the ranges before backtesting "
            "rather than letting a gap be filled silently"
        )
    return np.array([lookup[int(t)] for t in base_ts], dtype="float64")


class PeerSpreadReversion:
    """Long the traded asset when its spread against a peer is stretched down.

    The spread is the residual of an OLS fit over the trailing `fit_window`, so
    beta is re-estimated every bar from visible data only. `require_cointegration`
    gates entry on an ADF test of that residual.
    """

    def __init__(
        self,
        peer_closes: np.ndarray | None = None,
        peer_name: str = "peer",
        fit_window: int = 250,
        entry_z: float = -2.0,
        exit_z: float = 0.0,
        stop_z: float = -3.0,
        adf_max_p: float = 0.05,
        require_cointegration: bool = True,
    ) -> None:
        if fit_window < 30:
            raise ValueError("fit_window must be at least 30 to fit a spread")
        if entry_z >= 0:
            raise ValueError("entry_z is the oversold threshold and must be negative")
        if stop_z >= entry_z:
            raise ValueError("stop_z must sit below entry_z")
        if not 0.0 < adf_max_p < 1.0:
            raise ValueError("adf_max_p must be a probability")

        self.peer_closes = (
            None if peer_closes is None else np.asarray(peer_closes, dtype="float64")
        )
        self.peer_name = peer_name
        self.fit_window = fit_window
        self.entry_z, self.exit_z, self.stop_z = entry_z, exit_z, stop_z
        self.adf_max_p = adf_max_p
        self.require_cointegration = require_cointegration

        self.name = f"pair_{peer_name.lower()}_{fit_window}_{entry_z:g}"
        self.params: dict[str, Any] = {
            "peer_name": peer_name,
            "fit_window": fit_window,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "stop_z": stop_z,
            "adf_max_p": adf_max_p,
            "require_cointegration": require_cointegration,
        }
        self._holding = False
        # Diagnostics, so a flat run can be explained rather than guessed at.
        self.bars_screened_out = 0
        self.bars_cointegrated = 0

    def warmup_bars(self) -> int:
        return self.fit_window + 1

    def on_bar(self, history: BarWindow) -> float:
        # Without a peer there is no pair. Refusing to trade is the only honest
        # answer, and it is why this class is not in the strategy registry: a
        # registered strategy that silently does nothing is a footgun.
        if self.peer_closes is None:
            return 0.0

        i = history.i
        if i + 1 < self.fit_window + 1:
            return 0.0
        if self.peer_closes.size <= i:
            raise ValueError(
                f"peer series has {self.peer_closes.size} bars but the engine reached "
                f"bar {i}; align it with align_peer() before running"
            )

        closes = history.closes
        # Trailing window only, and the peer sliced to exactly the same bars.
        base = closes[-self.fit_window :]
        peer = self.peer_closes[i + 1 - self.fit_window : i + 1]

        try:
            result = engle_granger(base, peer)
        except (ValueError, np.linalg.LinAlgError):
            return 0.0

        if self.require_cointegration and result.adf.pvalue > self.adf_max_p:
            # The relation is not established on this window, so the spread is not
            # a mean-reverting object and the trade has no premise.
            self.bars_screened_out += 1
            self._holding = False
            return 0.0
        self.bars_cointegrated += 1

        spread = result.spread
        z = ind.zscore(spread, min(self.fit_window, len(spread)))
        if not np.isfinite(z):
            return 0.0

        if self._holding:
            # Stop first: a spread that keeps diverging is the documented way this
            # strategy loses badly rather than slightly, so the stop outranks the
            # profit target.
            if z <= self.stop_z or z >= self.exit_z:
                self._holding = False
                return 0.0
            return 1.0

        if z <= self.entry_z:
            self._holding = True
            return 1.0
        return 0.0
