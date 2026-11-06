"""Configuration must not disable a safety gate through coercion or IEEE special values."""

from __future__ import annotations

from dataclasses import fields

import pytest

from aero_lp.config import AllocatorConfig, Config, SafetyConfig, load
from aero_lp.executor import ExecConfig

OWNER = "0x" + "ab" * 20


@pytest.mark.parametrize("cls", [SafetyConfig, ExecConfig])
def test_all_execution_and_safety_numbers_must_be_finite(cls):
    for f in fields(cls):
        for bad in (float("nan"), float("inf"), -float("inf"), True, "1"):
            with pytest.raises(ValueError, match=f.name):
                cls(**{f.name: bad})


def test_estimates_and_intervals_cannot_disable_gas_or_scheduling_checks():
    for name in ("l1_fee_usd_estimate", "gas_units_estimate", "poll_seconds"):
        for bad in (-1, float("nan"), float("inf"), True, "1"):
            with pytest.raises(ValueError, match=name):
                Config(OWNER, **{name: bad})
    for name in ("gas_units_estimate",):
        with pytest.raises(ValueError, match=name):
            Config(OWNER, **{name: 1.5})


def test_allocator_settings_reject_boolean_and_collection_coercion(tmp_path):
    for settings in ({"enabled": "false"}, {"max_arms": 1.5}, {"allowed_tokens": "WETH"}, {"exclude_tokens": "WETH"}):
        with pytest.raises(ValueError):
            AllocatorConfig(**settings)
    path = tmp_path / "bad.toml"
    for line in ('enabled = "false"', 'exclude_tokens = "WETH"', "max_arms = 1.5"):
        path.write_text(f'owner = "{OWNER}"\n[allocator]\n{line}\n')
        with pytest.raises(ValueError):
            load(path)


def test_execution_timing_requires_positive_whole_seconds():
    for name in ("deadline_s", "receipt_timeout_s"):
        with pytest.raises(ValueError, match=name):
            ExecConfig(**{name: 1.5})
