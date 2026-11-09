"""Stable experiment identities and byte-bound discovery gate evidence."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                      default=lambda x: x.tolist() if isinstance(x, np.ndarray) else x.item() if isinstance(x, np.generic) else str(x))


def identity(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def array_checksum(arrays: dict[str, np.ndarray]) -> str:
    """Bind all bar inputs, their shapes and names in a platform-stable order."""
    h=hashlib.sha256()
    for name in sorted(arrays):
        values=np.asarray(arrays[name])
        h.update(canonical([name, list(values.shape)]).encode())
        h.update(values.astype('<f8').tobytes())
    return h.hexdigest()



def source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    paths = [root / name for name in (
        "backtester/core/engine.py", "backtester/core/types.py", "backtester/core/metrics.py",
        "backtester/core/cpcv.py", "backtester/core/indicators.py", "research/sweep.py",
        "research/signal_redundancy.py", "research/decide.py", "research/cpcv_sweep.py", "research/evidence.py")]
    paths += sorted((root / "backtester/core/strategies").glob("*.py"))
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

def discovery_context(arrays: dict[str, np.ndarray], params: dict, asset: str, horizon: str, split: float) -> tuple[dict, dict]:
    cut=int(len(arrays['ts'])*split)
    if cut < 1 or cut >= len(arrays['ts']):
        raise ValueError('discovery split must retain both discovery and held-out bars')
    prefix={key:value[:cut] for key,value in arrays.items()}
    context=dict(scope='discovery', asset=asset, horizon=horizon, split=split, bars=cut,
                 cutoff_ts=int(arrays['ts'][cut]), data_checksum=array_checksum(prefix), parameters=params,
                 source_sha256=source_hashes())
    return prefix, context


def write_gate_proof(path: Path, context: dict) -> None:
    proof={**context, 'artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    path.with_suffix('.manifest.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')


def read_gate_table(path: Path, context: dict | None = None) -> pd.DataFrame:
    raw=path.read_bytes()
    if context is not None:
        try:
            proof=json.loads(path.with_suffix('.manifest.json').read_text())
        except (OSError, ValueError) as exc:
            raise SystemExit(f'{path}: discovery manifest proof is required; regenerate discovery-only redundancy evidence') from exc
        expected={**context,'artifact_sha256':hashlib.sha256(raw).hexdigest()}
        if proof != expected:
            raise SystemExit(f'{path}: discovery manifest does not match this data, cutoff, parameters or artifact bytes')
    return pd.read_csv(io.BytesIO(raw))
