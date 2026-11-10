"""Costed single-cell receipts and thin adapters to the established F5 owner.

The F5 batch runner remains the durable orchestration and prospective-forward
owner. These adapters do not create a second queue, worker or paper ledger.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import math
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtester.core.data import frame_to_arrays, validate_bars
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.leverage import tier_config
from backtester.core.strategies import REGISTRY
from backtester.core.strategy_cards import HORIZONS, load_all
from backtester.core.types import CostConfig

from .data import _publish, _symbol, canonical, file_sha256


def strategies() -> tuple[str, ...]:
    """All registered hypotheses, including those the batch reports unsupported."""
    return tuple(sorted(REGISTRY))


def _safe(value: Any, undefined: list[str], path: str = "") -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _safe(v, undefined, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v, undefined, f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            undefined.append(path)
            return None
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def code_fingerprint() -> str:
    """Bind the whole canonical core, not just a strategy's leaf implementation."""
    import backtester.core

    root = Path(inspect.getfile(backtester.core)).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    digest.update(np.__version__.encode())
    digest.update(pd.__version__.encode())
    return digest.hexdigest()


def backtest(
    asset: str,
    strategy: str,
    data_receipt: dict,
    out_dir: str | Path,
    *,
    interval: str = "1d",
) -> dict:
    """Run one default-card, costed model and persist an immutable JSON receipt.

    This is an offline model of the stated source series, not a promotion gate.
    The pipeline should use create_batch/start_batch for durable CPCV selection
    and forward handoff. Tier cells here use the canonical perp-aware config;
    F5 itself separately reports unsupported tier CPCV cells rather than mislabels.
    """
    base = {"schema_version": 1, "asset": None, "strategy": None, "interval": interval}
    try:
        asset = _symbol(asset)
        if strategy not in REGISTRY:
            raise ValueError("unsupported_strategy")
        base.update(asset=asset, strategy=strategy)
        if (
            not isinstance(data_receipt, dict)
            or data_receipt.get("status") != "complete"
        ):
            return {**base, "status": "blocked", "reason": "verified_data_unavailable"}
        if (
            data_receipt.get("asset") != asset
            or data_receipt.get("interval") != interval
            or data_receipt.get("instrument") != f"{asset}/USD"
            or data_receipt.get("venue") != "coinbase_exchange"
        ):
            return {**base, "status": "blocked", "reason": "data_context_mismatch"}
        path = Path(data_receipt["path"])
        expected = data_receipt["sha256"]
        if path.is_symlink() or file_sha256(path) != expected:
            return {**base, "status": "blocked", "reason": "data_digest_mismatch"}
        frame = validate_bars(pd.read_csv(path), interval, strict_gaps=True)
        card = next(
            (c for c in load_all().values() if c.registry_key == strategy), None
        )
        if card is None or not card.buildable or not card.data_available:
            return {**base, "status": "blocked", "reason": "strategy_card_unavailable"}
        if any(field not in ("ohlcv", "volume") for field in card.data_required):
            return {
                **base,
                "status": "blocked",
                "reason": "strategy_feature_unavailable",
            }
        instance = REGISTRY[strategy](**card.defaults())
        if len(frame) <= instance.warmup_bars() + 2:
            return {**base, "status": "blocked", "reason": "insufficient_history"}
        config = (
            tier_config(instance.leverage, interval)
            if strategy.startswith("lev_")
            else EngineConfig(
                interval=interval,
                fill_delay=1,
                costs=CostConfig(fee_bps=6, slippage_bps=2),
            )
        )
        code_hash = code_fingerprint()
        result = run_backtest(instance, frame_to_arrays(frame), config)
        if code_fingerprint() != code_hash:
            return {**base, "status": "blocked", "reason": "evaluation_code_changed"}
        if file_sha256(path) != expected:
            return {
                **base,
                "status": "blocked",
                "reason": "data_changed_during_backtest",
            }
        undefined: list[str] = []
        evidence = _safe(
            {
                **base,
                "status": "complete",
                "reason": None,
                "instrument": data_receipt["instrument"],
                "venue": data_receipt["venue"],
                "source": data_receipt["source"],
                "data_sha256": expected,
                "card_sha256": file_sha256(card.path),
                "code_sha256": code_hash,
                "parameters": dict(instance.params),
                "costs": dataclasses.asdict(config.costs),
                "mode": config.mode,
                "leverage": config.leverage,
                "fill_delay": config.fill_delay,
                "metrics": result.metrics.to_dict(),
                "gross_metrics": result.gross_metrics.to_dict(),
                "equity": result.equity.tolist(),
                "timestamps": result.timestamps.tolist(),
                "trades": [dataclasses.asdict(trade) for trade in result.trades],
                "evaluation": "single_default_card_full_window_no_out_of_sample_claim",
                "initial_capital": config.initial_capital,
            },
            undefined,
        )
        evidence["undefined_numeric_fields"] = undefined
        raw = canonical(evidence)
        digest = hashlib.sha256(raw).hexdigest()
        artifact = (
            Path(out_dir).expanduser().absolute() / f"{asset}-{strategy}-{digest}.json"
        )
        _publish(artifact, raw)
        return {**evidence, "path": str(artifact), "sha256": digest}
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError):
        return {
            **base,
            "status": "failed",
            "reason": "backtest_validation_or_execution_failed",
        }


def create_batch(
    settings: Any,
    coins: list[str] | tuple[str, ...],
    *,
    root: Path,
    intervals: tuple[str, ...] = ("1d",),
    horizons: tuple[str, ...] = HORIZONS,
    strategy_ids: tuple[str, ...] | None = None,
) -> dict:
    """Freeze every requested matrix cell through the existing F5 plan API."""
    from soltui import f5_batch

    return f5_batch.create(
        settings,
        coins,
        root=root,
        intervals=intervals,
        horizons=horizons,
        strategies=strategy_ids,
        longest_contiguous=False,
    )


def start_batch(run_id: str, *, root: Path) -> dict:
    """Ask F5 to own/resume its worker; do not start a parallel evaluator."""
    from soltui import f5_batch

    return f5_batch.start(run_id, root=root)


def batch_status(run_id: str, *, root: Path) -> dict:
    """Read the owner's status, including partial/missing/unsupported cells."""
    from soltui import f5_batch

    return f5_batch.status(run_id, root=root)


def batch_cells(
    run_id: str, *, root: Path, limit: int = 1000, offset: int = 0
) -> list[dict]:
    """Read a bounded page of the frozen matrix from its established owner."""
    from soltui import f5_batch

    return f5_batch.cells(run_id, root=root, limit=limit, offset=offset)
