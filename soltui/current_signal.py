"""Fresh strategy assessments, independent from saved forecast eligibility."""
from __future__ import annotations

import time
from typing import Any

import numpy as np

from backtester.core.types import validate_bar_arrays
from . import compound, forwardtest


def check(asset: str, trials: list[dict], *, fetch=None, clock=time.time) -> dict[str, Any]:
    now = clock()
    raw = (fetch or compound.fetch_closed_candles)(asset, now=now, bars=forwardtest.HISTORY,
                                                   seconds=60, cache=False)
    mask = raw['ts'] + 60 <= now
    raw = {key: value[mask] for key, value in raw.items()}
    ts = raw['ts']
    if not len(ts) or ts[-1] != int(now // 60) * 60 - 60:
        raise ValueError('Latest closed minute is unavailable; try again after the candle is published')
    breaks = np.flatnonzero(np.diff(ts) != 60)
    start = int(breaks[-1] + 1) if len(breaks) else 0
    bars = validate_bar_arrays({key: value[start:] for key, value in raw.items()}, '1m')
    rows = []
    defaults = forwardtest.load_defaults()
    for trial in trials:
        label = trial['label']
        spec = forwardtest.saved_default(asset, label, 1, defaults) or trial['members']
        try:
            prediction = forwardtest._predict(spec, trial.get('mode', 'all'), bars, allow_short=True)
            rows.append({'strategy': label, 'prediction': {1: 'UP', -1: 'DOWN', 0: 'FLAT'}.get(prediction, 'Warming up'),
                         'vote': prediction, 'error': ''})
        except Exception as exc:
            rows.append({'strategy': label, 'prediction': 'Unavailable', 'vote': None,
                         'error': f'{type(exc).__name__}: {exc}'[:200]})
    votes = [r['vote'] for r in rows if r['vote'] is not None]
    return {'asset': asset, 'checked_at': now, 'candle_closed_at': int(ts[-1]) + 60,
            'bars': len(bars['ts']), 'score': round(100 * sum(votes) / len(votes), 1) if votes else None,
            'strategies': len(votes), 'rows': rows,
            'message': 'Fresh assessment from closed 1m candles. Prior accuracy and expiry gates do not apply to this manual check.'}
