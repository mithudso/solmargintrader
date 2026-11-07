"""The Top 5 configurations as ready-to-use presets for Analyze, Live Run and Execute.

`top5.py` reads the committed evidence; this module turns each row into something a tab can apply
with one click, from one place, so every surface (TUI, CLI, API, extension) sees the same list.

A preset carries the configuration's label (what Live Run launches), its member signals with the
SOL-tuned parameters of `research/sweep.py`'s `HORIZONS` (what Execute replays and Analyze judges)
and the data series it was fitted on. The parameters are read from `HORIZONS`, not copied: a copy
would drift from the research that produced the evidence.

Read-only: building a preset runs nothing and touches no network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import top5 as top5_mod
from .netpct import labelled

PREFIX = "top5:"


def preset_value(rank: int) -> str:
    """The Execute/Live Run selection value for a rank, e.g. `top5:1`."""
    return f"{PREFIX}{rank}"


def parse_value(value: str) -> int | None:
    """The rank in a `top5:N` value, else None."""
    if isinstance(value, str) and value.startswith(PREFIX):
        try:
            return int(value[len(PREFIX):])
        except ValueError:
            return None
    return None


def _horizons() -> dict[str, dict[str, Any]]:
    from research.sweep import HORIZONS  # imports pandas; kept lazy so `import presets` is cheap

    return HORIZONS


def build_presets(configs: list[top5_mod.Top5Config] | None = None,
                  horizons: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """One dict per Top 5 configuration, in rank order. Raises `EvidenceUnavailable` if no file."""
    configs = top5_mod.load_top5() if configs is None else configs
    horizons = _horizons() if horizons is None else horizons
    out: list[dict[str, Any]] = []
    for c in configs:
        spec = horizons.get(c.horizon)
        members = []
        if spec:
            for name in c.members:
                # A name HORIZONS has no parameters for is dropped, not given defaults: the preset
                # would then replay a configuration the evidence never tested.
                if name in spec["params"]:
                    members.append({"name": name, "params": dict(spec["params"][name])})
        home = c.home
        interval = spec["interval"] if spec else "1d"
        net = home.median_return if home else None
        out.append({
            "rank": c.rank, "value": preset_value(c.rank), "label": c.label,
            "title": f"#{c.rank} {c.label} ({c.horizon}, {top5_mod.HOME_ASSET} {interval})",
            "horizon": c.horizon, "mode": c.mode, "asset": top5_mod.HOME_ASSET,
            "interval": interval, "allow_gaps": bool(spec["allow_gaps"]) if spec else False,
            "members": members,
            "member_names": [m["name"] for m in members],
            # `None` when the evidence row carries no median return: absent, not zero.
            "net_pct": net,
            "net_pct_text": labelled(net, "backtest", "median net"),
            "usable": bool(members) and len(members) == len(c.members),
            "params_text": "; ".join(
                f"{m['name']}({', '.join(f'{k}={v}' for k, v in m['params'].items()) or 'defaults'})"
                for m in members),
            "applies": {
                "analyze": {"asset": top5_mod.HOME_ASSET, "interval": interval,
                            "preset": preset_value(c.rank)},
                "live_run": {"strategy": c.label},
                "execute": {"label": preset_value(c.rank)},
            },
        })
    return out


def find_preset(rank: int, presets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The preset for `rank`; ValueError names the ranks that exist."""
    presets = build_presets() if presets is None else presets
    for p in presets:
        if p["rank"] == rank:
            return p
    raise ValueError(f"no Top 5 configuration with rank {rank}; have {[p['rank'] for p in presets]}")


def build_strategy(preset: dict[str, Any]):
    """The strategy object a preset describes (a single signal, or an all()/any() composite)."""
    from backtester.core.strategies import build, build_composite

    if not preset["usable"]:
        raise ValueError(f"preset {preset['label']} has no parameters in research/sweep.py HORIZONS")
    specs = [(m["name"], m["params"]) for m in preset["members"]]
    if len(specs) == 1:
        return build(specs[0][0], **specs[0][1])
    return build_composite(specs, mode=preset["mode"])


def load_preset_arrays(preset: dict[str, Any], data_dir: str | Path = "data") -> dict:
    """Price arrays for the series a preset was fitted on (asset + horizon interval)."""
    from backtester.core.data import CsvLoader, frame_to_arrays

    path = Path(data_dir) / f"{preset['asset']}_{preset['interval']}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is not cached. Fetch it:\n  python3 -m backtester.core.fetch --asset "
            f"{preset['asset']} --interval {preset['interval']} --start 2021-01-01")
    df = CsvLoader(path, allow_gaps=True).load(preset["asset"], None, None, preset["interval"])
    return frame_to_arrays(df)
