"""Deterministic configuration identity for newly produced continuation state.

Bindings describe values and intrabar content, never Python object addresses.
The version prefix intentionally refuses legacy repr-based checkpoints.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields, is_dataclass
from enum import Enum

import numpy as np

from .types import IntrabarLayer


def _value(value):
    if isinstance(value, Enum):
        return _value(value.value)
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            raise ValueError("continuation configuration must be finite")
        return float(value)
    if isinstance(value, IntrabarLayer):
        return {"intrabar_interval": value.interval,
                "arrays": {name: _value(getattr(value, name))
                           for name in ("ts", "open", "high", "low", "close")}}
    if isinstance(value, np.ndarray):
        if value.dtype.kind not in "biuf" or not np.isfinite(value).all():
            raise ValueError("continuation arrays must contain finite numeric values")
        # Endianness is an encoding choice, not a different market observation.
        array = np.ascontiguousarray(value.astype(value.dtype.newbyteorder("<"), copy=False))
        return {"array_dtype": array.dtype.str, "shape": list(array.shape),
                "sha256": hashlib.sha256(array.tobytes()).hexdigest()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_value(item) for item in value]
    raise ValueError("unsupported continuation configuration value")


def configuration_binding(*values) -> str:
    """Bind supported configuration values without copying stateful objects."""
    encoded = json.dumps(_value(values), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "config-v2:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
