"""Paired, offline comparison of frozen strategy packages; never selects parameters.

Run ``python3 research/strategy_compare.py --help``. Research output, not investment
advice; simulation only. Every failed cell remains in the output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import frame_to_arrays, resolve_data_dir, validate_bars
from research.strategy_snapshots import ensure_snapshots
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.leverage import tier_config
from backtester.core.metrics import compute_metrics
from backtester.core.types import BarWindow, periods_per_year, INTERVAL_SECONDS

DEFAULT_DATASETS = ('SOL_1d', 'BTC_1d', 'ETH_1d', 'SOL_1h')


def source_hashes(root: Path) -> dict[str, str]:
    """Content identity independent of checkout name and Python bytecode caches."""
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix in ('.py', '.md', '.json')}


def load_registry(root: Path, variant: str) -> dict[str, Any]:
    """Load copies as independent packages so relative imports stay in their copy."""
    package = '_strategy_compare_' + variant
    for key in list(sys.modules):
        if key == package or key.startswith(package + '.'):
            del sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        package, root / '__init__.py', submodule_search_locations=[str(root)])
    if spec is None or spec.loader is None:
        raise ValueError(f'cannot load strategy package {root}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[package] = module
    spec.loader.exec_module(module)
    strategies = __import__(package + '.strategies', fromlist=['REGISTRY'])
    return strategies.REGISTRY


def window(arrays: dict[str, np.ndarray], i: int) -> BarWindow:
    return BarWindow(arrays['ts'], arrays['open'], arrays['high'], arrays['low'],
                     arrays['close'], arrays['volume'], i)


def targets(factory: Any, arrays: dict[str, np.ndarray]) -> np.ndarray:
    """Replay a fresh instance causally, with exactly the engine's warmup convention."""
    strategy = factory()
    out = np.zeros(len(arrays['ts']), dtype=float)
    for i in range(strategy.warmup_bars(), len(out)):
        value = float(strategy.on_bar(window(arrays, i)))
        if not math.isfinite(value):
            raise ValueError(f'non-finite signal at bar {i}')
        # Default strategy configurations use long/flat execution, including tiers.
        out[i] = min(1.0, max(0.0, value))
    return out


def accuracy_panel(signals: np.ndarray, arrays: dict[str, np.ndarray],
                   start: int, stop: int) -> dict[str, Any]:
    """Signal at t predicts the sign of next bar's open-to-close return.

    Zero exposure abstains. Zero return is an incorrect call, not a removed label.
    Majority baseline uses the identical active timestamps. This diagnostic does
    not represent the strategy's complete holding-period objective.
    """
    first = max(1, start)
    calls = signals[first - 1:stop - 1]
    labels = np.sign(arrays['close'][first:stop] - arrays['open'][first:stop])
    active = calls != 0
    n = int(active.sum())
    correct = int(np.sum(np.sign(calls[active]) == labels[active]))
    up = int(np.sum(labels[active] > 0))
    down = int(np.sum(labels[active] < 0))
    return {'accuracy': correct / n if n else None, 'correct_calls': correct,
            'active_calls': n, 'eligible_bars': len(calls),
            'coverage': n / len(calls) if len(calls) else None,
            'majority_baseline': max(up, down) / n if n else None,
            'accuracy_evidence': 'exploratory' if n >= 30 else 'insufficient (<30 active calls)'}


class EvaluationWindow:
    """Prime state using prefix history, but keep the portfolio flat until scoring."""
    def __init__(self, factory: Any, arrays: dict[str, np.ndarray], start: int) -> None:
        self.inner = factory()
        self.name, self.params = self.inner.name, self.inner.params
        self.first_signal = max(self.inner.warmup_bars(), start - 1)
        for i in range(self.inner.warmup_bars(), self.first_signal):
            self.inner.on_bar(window(arrays, i))

    def warmup_bars(self) -> int:
        return self.first_signal

    def on_bar(self, history: BarWindow) -> float:
        return self.inner.on_bar(history)


class FrozenSignals:
    """Feed an already-causal signal replay into the unchanged execution engine."""
    def __init__(self, strategy: Any, signals: np.ndarray, start: int) -> None:
        self.name, self.params = strategy.name, strategy.params
        self.signals = signals
        self.first_signal = max(strategy.warmup_bars(), start - 1)

    def warmup_bars(self) -> int:
        return self.first_signal

    def on_bar(self, history: BarWindow) -> float:
        return float(self.signals[history.i])


def load_sample(raw: bytes, interval: str, contiguous_tail: bool = False) -> tuple[pd.DataFrame, dict]:
    """Select a suffix by timestamp gaps only; never fill missing candles."""
    frame = validate_bars(pd.read_csv(io.BytesIO(raw)), interval,
                          strict_gaps=not contiguous_tail)
    original_count = len(frame)
    gaps = np.flatnonzero(np.diff(frame['timestamp'].to_numpy()) > INTERVAL_SECONDS[interval])
    first = int(gaps[-1] + 1) if contiguous_tail and len(gaps) else 0
    selected = validate_bars(frame.iloc[first:].reset_index(drop=True), interval)
    return selected, {'raw_bars': original_count, 'selected_start_index': first,
                      'timestamp_gaps': int(len(gaps)),
                      'selection': 'latest contiguous suffix by timestamp only' if first else 'full file',
                      'selected_frame_sha256': hashlib.sha256(selected.to_csv(index=False).encode()).hexdigest()}


def evaluate(factory: Any, arrays: dict[str, np.ndarray], interval: str,
             start: int, stop: int, signals: np.ndarray | None = None) -> dict[str, Any]:
    """No training trade crosses a split; indicator state sees only historical bars."""
    sample = {k: v[:stop] for k, v in arrays.items()}
    probe = factory()
    config = (tier_config(probe.engine_leverage, interval)
              if getattr(probe, 'engine_mode', None) == 'perp'
              else EngineConfig(interval=interval))
    strategy = (EvaluationWindow(factory, sample, start) if signals is None
                else FrozenSignals(probe, signals, start))
    if stop - max(start, strategy.first_signal + 1) < 2:
        raise ValueError('insufficient evaluation bars after strategy warmup')
    result = run_backtest(strategy, sample, config)
    metric = compute_metrics(result.equity[start:], result.timestamps[start:],
                             result.trades, result.exposure[start:], periods_per_year(interval),
                             config.risk_free_rate, result.liquidation_count,
                             initial_equity=config.initial_capital)
    panel = accuracy_panel(signals if signals is not None else targets(factory, sample),
                           sample, max(start, strategy.first_signal + 1), stop)
    return {**metric.to_dict(), **panel, 'scored_start_index': start, 'scored_stop_index': stop, 'mode': str(config.mode),
            'leverage': config.leverage, 'costs': asdict(config.costs),
            'trade_evidence': 'exploratory' if metric.trade_count >= 30
            else 'insufficient (<30 realized trade events)',
            'params': probe.params, 'status': 'ok'}


def clean_json(value: Any) -> Any:
    """JSON null means undefined, never emit JavaScript's invalid Infinity/NaN."""
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def pair_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row['dataset'], row['strategy'], row['split']), {})[row['variant']] = row
    paired = []
    for (dataset, strategy, split), variants in grouped.items():
        old, new = variants.get('original', {}), variants.get('candidate', {})
        entry: dict[str, Any] = {'dataset': dataset, 'strategy': strategy, 'split': split,
                                'status': 'ok' if old.get('status') == new.get('status') == 'ok' else 'failed'}
        for key in ('accuracy', 'win_rate', 'total_return', 'sharpe', 'max_drawdown',
                    'trade_count', 'active_calls', 'coverage', 'total_fees', 'total_borrow_fees'):
            a, b = old.get(key), new.get(key)
            entry['original_' + key], entry['candidate_' + key] = a, b
            entry['delta_' + key] = b - a if a is not None and b is not None else None
        paired.append(entry)
    return paired


def write_outputs(out: Path, manifest: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pairs = clean_json(pair_rows(rows))
    (out / 'manifest.json').write_text(json.dumps(clean_json(manifest), indent=2) + '\n')
    (out / 'results.json').write_text(json.dumps(clean_json(rows), indent=2) + '\n')
    for filename, data in (('results.csv', clean_json(rows)), ('comparison.csv', pairs)):
        columns = list(dict.fromkeys(key for row in data for key in row))
        with (out / filename).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows([{k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v
                              for k, v in row.items()} for row in data])
    holdout = [p for p in pairs if p['split'] == 'holdout']
    changed = sum(any(p.get('delta_' + k) not in (None, 0) for k in ('accuracy', 'total_return'))
                  for p in holdout if p['status'] == 'ok')
    lines = ['# Original versus DSO candidate', '',
             'Research output, not investment advice; simulation only.', '',
             f"{len(holdout)} holdout strategy/dataset pairs; {changed} changed accuracy or net return; "
             f"{sum(p['status'] != 'ok' for p in holdout)} failed pairs.", '',
             'All results are exploratory historical comparisons, not proof of a live edge. '
             'The final chronological 30% is a temporal holdout in this run. Previously researched '
             'data is not a fresh independent confirmation set. No parameter search or promotion runs.', '',
             'Accuracy is active long/short signal(t) versus sign(close/open - 1) at t+1. '
             'Flat signals abstain; flat outcomes count as misses. Coverage and majority baseline '
             'use identical eligible timestamps. This one-bar diagnostic is distinct from holding-period '
             'strategy returns and net realized trade-event win rate. Accuracy differences may use '
             'different active timestamps; inspect counts/coverage before comparing percentages.', '',
             'The common current engine applies costs, next-open fills, and terminal liquidation. '
             'Each split starts with fresh capital and no position. Stateful signals are primed on '
             'prefix history; no working-set trade crosses the split. Leverage tiers use perp mode '
             'and borrow/liquidation costs. Engine win rate counts realized events (including partial '
             'resizes), not independent round trips. Fewer than 30 active calls or realized events '
             'is insufficient evidence. Even above 30, serial dependence is not corrected.', '',
             '| Dataset | Strategy | Accuracy old → new | Net return old → new | Sharpe old → new | Trades old → new |',
             '|---|---|---:|---:|---:|---:|']
    def fmt(value: Any, percent: bool = False) -> str:
        return 'undefined' if value is None else (f'{value:.2%}' if percent else f'{value:.3f}')
    for p in holdout:
        if p['status'] != 'ok':
            lines.append(f"| {p['dataset']} | {p['strategy']} | failed; see results.json | — | — | — |")
            continue
        cells = [f"{fmt(p['original_' + k], percent)} → {fmt(p['candidate_' + k], percent)}"
                 for k, percent in (('accuracy', True), ('total_return', True), ('sharpe', False))]
        lines.append(f"| {p['dataset']} | {p['strategy']} | " + ' | '.join(cells)
                     + f" | {p['original_trade_count']} → {p['candidate_trade_count']} |")
    lines += ['', 'Source and data hashes, split boundaries, cost conventions, and package '
              'integrity checks are in manifest.json. Full denominators, undefined metrics, '
              'baseline accuracy, coverage, failures, costs and risk metrics are in results.json '
              'and results.csv. Signed candidate-minus-original differences are in comparison.csv.', '']
    (out / 'comparison.md').write_text('\n'.join(lines))


def run(experiment: Path, data_dir: Path, datasets: list[str], out: Path,
        split: float = 0.7, names: list[str] | None = None,
        contiguous_tail: bool = False) -> dict[str, Any]:
    if not 0 < split < 1:
        raise ValueError('split must lie strictly between zero and one')
    ensure_snapshots(experiment)
    before = {v: source_hashes(experiment / v) for v in ('original', 'candidate')}
    registries = {v: load_registry(experiment / v / 'core', v) for v in before}
    if set(registries['original']) != set(registries['candidate']):
        raise ValueError('original and candidate registry membership differs')
    names = sorted(registries['original']) if names is None else names
    if set(names) - set(registries['original']):
        raise ValueError('unknown strategy requested')
    manifest: dict[str, Any] = {'schema_version': 1, 'split_fraction': split,
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'contiguous_tail_requested': contiguous_tail, 'strategy_count': len(names), 'strategies': names, 'sources': before,
        'common_engine_sources': source_hashes(REPO / 'backtester' / 'core'),
        'datasets': [], 'selection': 'defect fixes only; no parameter search or promotion',
        'confirmation': 'none; historically researched cache', 'initial_capital': 10000}
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        path = data_dir / (dataset + '.csv')
        asset, interval = dataset.rsplit('_', 1)
        try:
            raw = path.read_bytes()
            frame, selection = load_sample(raw, interval, contiguous_tail)
            # Refuse a cache changing during read rather than mixing its identities.
            if path.read_bytes() != raw:
                raise ValueError('data cache changed during read')
            arrays = frame_to_arrays(frame)
            boundary = int(len(frame) * split)
            manifest['datasets'].append({'dataset': dataset, 'path': str(path),
                'sha256': hashlib.sha256(raw).hexdigest(), 'bars': len(frame),
                'start': int(arrays['ts'][0]), 'end': int(arrays['ts'][-1]),
                **selection, 'holdout_start_index': boundary, 'holdout_start_ts': int(arrays['ts'][boundary])})
            dataset_error = None
        except Exception as exc:
            dataset_error = f'{type(exc).__name__}: {exc}'
            manifest['datasets'].append({'dataset': dataset, 'path': str(path), 'error': dataset_error})
        for name in names:
            try:
                common_warmup = max(r[name]().warmup_bars() for r in registries.values())
            except Exception:
                common_warmup = 0
            for variant, registry in registries.items():
                try:
                    if dataset_error:
                        raise ValueError(dataset_error)
                    signal = targets(registry[name], {k: v[:boundary] for k, v in arrays.items()})
                    signal_error = None
                except Exception as exc:
                    signal_error = f'{type(exc).__name__}: {exc}'
                for label, start, stop in (('working', 0, boundary if not dataset_error else 0),
                                            ('holdout', boundary if not dataset_error else 0,
                                             len(frame) if not dataset_error else 0)):
                    row: dict[str, Any] = {'dataset': dataset, 'strategy': name,
                                          'variant': variant, 'split': label}
                    try:
                        if dataset_error:
                            raise ValueError(dataset_error)
                        if label == 'working':
                            if signal_error:
                                raise ValueError(signal_error)
                            split_signal = signal
                        else:
                            split_signal = targets(registry[name], arrays)
                        row.update(evaluate(registry[name], arrays, interval, max(start, common_warmup + 1), stop, split_signal))
                    except Exception as exc:
                        row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                    rows.append(row)
            print(f'{dataset}: {name}', flush=True)
    after = {v: source_hashes(experiment / v) for v in before}
    manifest['packages_unchanged_during_run'] = before == after
    if before != after:
        raise RuntimeError('strategy package changed during comparison; results invalid')
    manifest['failed_cells'] = sum(r['status'] != 'ok' for r in rows)
    manifest['completed_cells'] = len(rows) - manifest['failed_cells']
    write_outputs(out, manifest, rows)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, default=REPO / 'research/strategy_experiment')
    parser.add_argument('--data-dir', type=Path, default=resolve_data_dir())
    parser.add_argument('--datasets', nargs='+', default=list(DEFAULT_DATASETS))
    parser.add_argument('--strategies', nargs='+')
    parser.add_argument('--contiguous-tail', action='store_true',
                        help='select latest contiguous suffix by timestamp gaps only; never impute bars')
    parser.add_argument('--split', type=float, default=0.7)
    parser.add_argument('--out', type=Path, default=REPO / 'research/strategy_experiment/results')
    args = parser.parse_args()
    manifest = run(args.experiment.resolve(), args.data_dir.resolve(), args.datasets,
                   args.out.resolve(), args.split, args.strategies, args.contiguous_tail)
    print(json.dumps({k: manifest[k] for k in ('completed_cells', 'failed_cells',
                                              'packages_unchanged_during_run')}))
    return 1 if manifest['failed_cells'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
