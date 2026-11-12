"""Recover the owner's exact unstarted F5 plan after a bootstrap checkpoint gap.

The caller supplies a batch root dedicated to one bootstrap. Existing evidence
is read only. Ambiguous or partly used plans are preserved and refused.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import sqlite3
import stat
from contextlib import ExitStack, closing, contextmanager
from itertools import product
from pathlib import Path

ERROR = "batch_recovery_unavailable"
RUN_ID = re.compile(r"[0-9a-f]{32}\Z")
SCORING = (
    "capital",
    "fee_bps",
    "slippage_bps",
    "fill_delay",
    "cpcv_groups",
    "cpcv_k",
    "fee_schedule",
    "use_leverage",
    "leverage",
    "allow_short",
    "min_confidence",
    "borrow_long_bps_hour",
    "borrow_short_bps_hour",
)


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@contextmanager
def _idle(path: Path):
    """Acquire the same stable lock inode a future worker must acquire."""
    if path.is_symlink():
        raise ValueError(ERROR)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(ERROR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _expected(settings, cfg: dict) -> tuple[dict, dict, set]:
    from soltui import bgqueue, f5_batch

    selections = {}
    for name in ("coins", "intervals", "strategies", "horizons"):
        values = cfg[name]
        if (
            not isinstance(values, (list, tuple))
            or not values
            or any(type(value) is not str for value in values)
            or len(values) != len(set(values))
        ):
            raise ValueError(ERROR)
        selections[name] = list(values)
    assets = sorted(bgqueue.validate_asset(asset) for asset in selections["coins"])
    intervals = selections["intervals"]
    horizons = selections["horizons"]
    names = sorted(selections["strategies"])
    count = len(assets) * len(intervals) * len(horizons) * len(names)
    if not 0 < count <= 1_000_000:
        raise ValueError(ERROR)
    expected = {
        "assets": assets,
        "intervals": intervals,
        "strategies": names,
        "horizons": horizons,
        "longest_contiguous": False,
        "universe": {"source": "explicit list", "eligible": len(assets)},
    }
    frozen = {name: getattr(settings, name) for name in SCORING}
    frozen.update(
        start="", end="", data_dir=str(Path(settings.data_dir).expanduser().resolve())
    )
    # Bind the same canonical representation and owner fingerprint as F5 itself.
    expected["settings"] = frozen
    sources = f5_batch.bgworker.evaluation_code_fingerprint()
    expected["code_sources"] = sources
    expected["code_id"] = f5_batch._code_id(sources)
    cells = set(product(assets, intervals, names, horizons))
    return expected, selections, cells


def _adopt(directory: Path, expected: dict, cells: set) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(ERROR)
    if any(path.is_symlink() for path in directory.iterdir()):
        raise ValueError(ERROR)
    # These artifacts prove that a worker was started or forward work existed.
    if any(
        (directory / name).exists()
        for name in ("worker-token", "worker.log", "forward.sqlite3")
    ) or any(directory.glob("stop-*")):
        raise ValueError(ERROR)
    path = directory / "batch.sqlite3"
    if not path.is_file() or path.is_symlink():
        raise ValueError(ERROR)
    with closing(
        sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        metadata = {
            row["key"]: json.loads(row["value"])
            for row in db.execute("SELECT key,value FROM meta")
        }
        if (
            type(metadata.get("version")) is not int
            or metadata["version"] != 1
            or metadata.get("id") != directory.name
            or metadata.get("phase") != "planned"
            or metadata.get("current") != ""
            or any(
                _json(metadata.get(key)) != _json(value)
                for key, value in expected.items()
            )
        ):
            raise ValueError(ERROR)
        if db.execute("SELECT count(*) FROM cell").fetchone()[0] != len(cells):
            raise ValueError(ERROR)
        observed = set()
        for row in db.execute(
            "SELECT id,asset,interval,strategy,horizon,state,reason,selected,score FROM cell"
        ):
            if (
                type(row["id"]) is not int
                or row["id"] < 1
                or row["state"] != "pending"
                or row["reason"] != ""
                or row["selected"] is not None
                or row["score"] is not None
            ):
                raise ValueError(ERROR)
            observed.add(
                tuple(row[key] for key in ("asset", "interval", "strategy", "horizon"))
            )
        if observed != cells:
            raise ValueError(ERROR)
        for table in ("series", "attempt", "forward_check"):
            if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                raise ValueError(ERROR)
    return {
        "run_id": directory.name,
        "directory": str(directory),
        "cells": len(cells),
        "assets": expected["assets"],
        "intervals": expected["intervals"],
        "strategies": len(expected["strategies"]),
        "horizons": expected["horizons"],
        "phase": "planned",
        "universe": expected["universe"],
        "longest_contiguous": False,
    }


def ensure_batch(settings, cfg: dict, root: Path) -> dict:
    """Create one plan, or adopt the sole exact complete unstarted owner plan.

    All rejections use one public code and preserve every existing artifact.
    The bootstrap must checkpoint the returned run_id before starting a worker.
    """
    from .backtests import create_batch

    try:
        root = Path(root).expanduser().absolute()
        if root.is_symlink():
            raise ValueError(ERROR)
        expected, selections, cells = _expected(settings, cfg)
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(
            root / "bootstrap-create.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        with ExitStack() as stack:
            stack.callback(os.close, fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            stack.enter_context(_idle(root / "f5-worker.lock"))
            candidates = [
                path for path in root.iterdir() if RUN_ID.fullmatch(path.name)
            ]
            if len(candidates) > 1:
                raise ValueError(ERROR)
            if candidates and (
                candidates[0].is_symlink() or not candidates[0].is_dir()
            ):
                raise ValueError(ERROR)
            created = not candidates
            if created:
                batch = create_batch(
                    settings,
                    selections["coins"],
                    root=root,
                    intervals=selections["intervals"],
                    strategy_ids=selections["strategies"],
                    horizons=selections["horizons"],
                )
                run_id = batch["run_id"]
                if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
                    raise ValueError(ERROR)
                candidates = [root / run_id]
            stack.enter_context(_idle(candidates[0] / "worker.lock"))
            result = _adopt(candidates[0], expected, cells)
            return {**result, "recovery": "created" if created else "adopted"}
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        sqlite3.Error,
    ):
        raise ValueError(ERROR) from None
