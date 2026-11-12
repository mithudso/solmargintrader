"""Offline paired comparison of executable mechanisms outside the strategy registry."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from backtester.core.data import CsvLoader, frame_to_arrays, resolve_data_dir
from research.strategy_compare import accuracy_panel, clean_json, load_registry, load_sample, source_hashes, window
from research.strategy_snapshots import ensure_snapshots


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _percent(value: float | None) -> str:
    return 'undefined' if value is None else f'{value:.2%}'


def module(variant: str, name: str) -> Any:
    return importlib.import_module('_strategy_compare_' + variant + '.' + name)


def paired_bots(variant: str, arrays: dict[str, np.ndarray], interval: str,
                bot: str) -> dict[str, Any]:
    k = int(len(arrays['ts']) * .7)
    scored = {key: val[k:] for key, val in arrays.items()}
    types = module(variant, 'types')
    costs = types.CostConfig(fee_bps=6, slippage_bps=2)
    if bot == 'ladder_grid':
        sim = module(variant, 'gridsim')
        # Fixed rails use the first evaluation open, before any orders become fillable.
        anchor = float(scored['open'][0])
        cfg = sim.GridConfig(lower=.85 * anchor, upper=1.15 * anchor, rungs=7,
                             notional_per_rung_usd=100, spacing='geom')
        result = sim.run_grid_backtest(cfg, scored, initial_capital=10000,
                                      interval=interval, costs=costs)
        extra = {'round_trips': result.round_trips, 'carry_bps_per_hour': 0}
    else:
        sim = module(variant, 'dcasim')
        cfg = sim.DcaConfig()
        result = sim.run_dca_backtest(cfg, scored, initial_capital=10000,
                                     interval=interval, costs=costs)
        extra = {'deals_completed': result.deals_completed,
                 'deals_stopped': result.deals_stopped}
    return {'status': 'ran', 'config': cfg.to_dict(), 'metrics': result.metrics.to_dict(),
            'accuracy': None, 'accuracy_reason': 'Resting-order mechanism emits no directional forecast.',
            'fill_win_rate_definition': 'profitable realized fills including final forced exit',
            'bars': len(scored['ts']), 'start_ts': int(scored['ts'][0]),
            'end_ts': int(scored['ts'][-1]), **extra}


def paired_peer(variant: str, base: dict[str, np.ndarray], peer: dict[str, np.ndarray],
                peer_name: str) -> dict[str, Any]:
    pairs = module(variant, 'pairs')
    engine = module(variant, 'engine')
    metrics = module(variant, 'metrics')
    types = module(variant, 'types')
    peer_closes = pairs.align_peer(base['ts'], peer['ts'], peer['close'])
    factory = lambda: pairs.PeerSpreadReversion(peer_closes=peer_closes, peer_name=peer_name)
    k, n = int(len(base['ts']) * .7), len(base['ts'])
    signals = np.zeros(n)
    strat = factory()
    for i in range(strat.warmup_bars(), n):
        signals[i] = strat.on_bar(window(base, i))

    class Primed:
        def __init__(self) -> None:
            self.inner = factory()
            self.name, self.params = self.inner.name, self.inner.params
            self.start = max(self.inner.warmup_bars(), k - 1)
            for i in range(self.inner.warmup_bars(), self.start):
                self.inner.on_bar(window(base, i))
        def warmup_bars(self) -> int:
            return self.start
        def on_bar(self, history: Any) -> float:
            return self.inner.on_bar(history)

    cfg = engine.EngineConfig(interval='1d')
    result = engine.run_backtest(Primed(), base, cfg)
    trades = [t for t in result.trades if t.bar_index >= k]
    panel = metrics.compute_metrics(result.equity[k:], result.timestamps[k:], trades,
                                    result.exposure[k:], types.periods_per_year('1d'),
                                    initial_equity=float(result.equity[k - 1]))
    return {'status': 'ran', 'params': factory().params, 'metrics': panel.to_dict(),
            'accuracy': accuracy_panel(signals, base, k, n),
            'bars': n - k, 'start_ts': int(base['ts'][k]), 'end_ts': int(base['ts'][-1]),
            'limitation': 'Trades SOL only; peer is a signal input, not a hedged second leg.'}


def run(experiment: Path, data_dir: Path, prices_dir: Path) -> dict[str, Any]:
    ensure_snapshots(experiment)
    variants = ('original', 'candidate')
    before = {v: source_hashes(experiment / v) for v in variants}
    for v in variants:
        load_registry(experiment / v / 'core', v)
    rows: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}
    datasets = ['SOL_1d', 'BTC_1d', 'ETH_1d', 'SOL_1h']
    for dataset in datasets:
        asset, interval = dataset.rsplit('_', 1)
        path = data_dir / (dataset + '.csv')
        try:
            identity = sha(path)
            raw = path.read_bytes()
            full_refusal = None
            try:
                load_sample(raw, interval)
            except ValueError as exc:
                full_refusal = str(exc)
            frame, selection = load_sample(raw, interval, contiguous_tail=(interval == '1h'))
            arrays = frame_to_arrays(frame)
            inputs[dataset] = {'sha256': identity, 'path': str(path), 'bars': len(arrays['ts']),
                               'full_cache_refusal': full_refusal, 'selection': selection}
            for bot in ('ladder_grid', 'dca_bot'):
                row: dict[str, Any] = {'mechanism': bot, 'dataset': dataset}
                for v in variants:
                    try:
                        row[v] = paired_bots(v, arrays, interval, bot)
                    except (ValueError, TypeError) as exc:
                        row[v] = {'status': 'failed', 'error': str(exc)}
                row['identical'] = row['original'] == row['candidate']
                rows.append(row)
            if sha(path) != identity:
                raise RuntimeError(f'input changed during run: {path}')
        except (OSError, ValueError) as exc:
            for bot in ('ladder_grid', 'dca_bot'):
                rows.append({'mechanism': bot, 'dataset': dataset, 'status': 'failed', 'error': str(exc)})
    for peer_name in ('BTC', 'ETH'):
        row = {'mechanism': 'peer_spread', 'dataset': 'SOL/' + peer_name + '_1d'}
        try:
            paths = [data_dir / (name + '_1d.csv') for name in ('SOL', peer_name)]
            raw_pairs = [p.read_bytes() for p in paths]
            for raw, name in zip(raw_pairs, ('SOL', peer_name)):
                if hashlib.sha256(raw).hexdigest() != inputs[name + '_1d']['sha256']:
                    raise RuntimeError('daily input changed before peer comparison')
            frames = [load_sample(raw, '1d')[0] for raw in raw_pairs]
            # Trim only unequal outer ranges; never remove internal missing candles.
            start = max(int(f.timestamp.iloc[0]) for f in frames)
            end = min(int(f.timestamp.iloc[-1]) for f in frames)
            arrays = [frame_to_arrays(f[(f.timestamp >= start) & (f.timestamp <= end)]) for f in frames]
            for v in variants:
                row[v] = paired_peer(v, *arrays, peer_name)
            row['identical'] = row['original'] == row['candidate']
        except (OSError, ValueError) as exc:
            row.update(status='failed', error=str(exc))
        rows.append(row)
    # Use the completed UTC day only. Never replay the active recorder file while it appends.
    path = prices_dir / '2026-11-08.jsonl.gz'
    row = {'mechanism': 'triangle', 'dataset': path.name}
    try:
        identity = sha(path)
        tri = module('original', 'trianglesim')
        products: set[str] = set()
        usable = 0
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                item = tri.parse_snapshot_line(line, require_quote_time=True)
                if item:
                    usable += 1
                    products.update(item[1])
        inputs['triangle'] = {'path': str(path), 'sha256': identity,
                              'usable_snapshots': usable, 'quote_time_policy': 'measured timestamps required'}
        replays = {}
        for v in variants:
            sim = module(v, 'trianglesim')
            replays[v] = sim.TriangleReplay(sim.TriangleConfig(), sim.triangles_from_products(products))
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                item = tri.parse_snapshot_line(line, require_quote_time=True)
                if item:
                    for replay in replays.values():
                        replay.feed(*item)
        if sha(path) != identity:
            raise RuntimeError('recorded quote input changed during replay')
        for v, replay in replays.items():
            row[v] = {'status': 'ran', **replay.result().summary(),
                      'evidence': 'insufficient (<30 cycles)' if replay.result().executed < 30 else 'exploratory'}
        row['identical'] = row['original'] == row['candidate']
        row['limitation'] = 'One completed recording day; L1 quotes and assumed simultaneous legs. No prospective profitability inference.'
    except (OSError, ValueError, EOFError) as exc:
        row.update(status='insufficient evidence (inputs absent)', error=str(exc))
    rows.append(row)
    row = {'mechanism': 'scorecard', 'dataset': 'SOL_5m_last30d'}
    path = data_dir / 'SOL_5m_last30d.csv'
    try:
        identity = sha(path)
        arrays = frame_to_arrays(CsvLoader(path).load('SOL', None, None, '5m'))
        for v in variants:
            sim = module(v, 'scorecard')
            bars = sim.Bars(**arrays)
            result = sim.evaluate(bars)
            row[v] = {'status': 'ran', 'accuracy': accuracy_panel(result.indication, arrays,
                          int(len(arrays['ts']) * .7), len(arrays['ts'])), 'component_errors': result.errors,
                       'config': result.config,
                       'native_forecast_report': sim.forecast_stats([result],
                           ts_from=float(arrays['ts'][int(len(arrays['ts']) * .7)]))}
        # Every catalog mechanism receives an explicit coverage record, including disabled/auxiliary ones.
        row['component_coverage'] = []
        for comp in module('original', 'scorecard').COMPONENTS:
            entry = {'id': comp.id, 'kind': comp.kind,
                     'default_enabled': comp.default_enabled,
                     'forward_only': comp.forward_only, 'needs': list(comp.needs)}
            if comp.forward_only or comp.needs:
                entry['status'] = 'gap'
                entry['reason'] = 'Prospective history or declared auxiliary input absent; no neutral-value substitution.'
            else:
                for v in variants:
                    sim = module(v, 'scorecard')
                    cfg = sim.default_config()
                    for cid, settings in cfg['components'].items():
                        settings['enabled'] = cid == comp.id
                    one = sim.evaluate(sim.Bars(**arrays), cfg)
                    if comp.kind == 'score':
                        entry[v] = {'accuracy': accuracy_panel(one.indication, arrays,
                            int(len(arrays['ts']) * .7), len(arrays['ts'])), 'errors': one.errors}
                    else:
                        entry[v] = {'blocked_bars': int(one.blocked[int(len(arrays['ts']) * .7):].sum()),
                                    'errors': one.errors, 'accuracy': None,
                                    'reason': 'Gate blocks trades; no independent directional call.'}
                entry['status'] = 'ran'
            row['component_coverage'].append(entry)
        row['identical'] = row['original'] == row['candidate']
        inputs['scorecard'] = {'path': str(path), 'sha256': identity, 'bars': len(arrays['ts'])}
        if sha(path) != identity:
            raise RuntimeError('scorecard bars changed during run')
        row['limitation'] = 'Indicator diagnostic only; no P&L or position strategy. Auxiliary funding/OI/orderbook/headline inputs absent.'
    except (OSError, ValueError) as exc:
        row.update(status='insufficient evidence (inputs absent)', error=str(exc))
    rows.append(row)
    after = {v: source_hashes(experiment / v) for v in variants}
    if before != after:
        raise RuntimeError('source copies changed during evaluation')
    return {'version': 1, 'delta': 'Initial auxiliary mechanism paired comparison.',
            'disclaimer': 'research output, not investment advice; simulation only',
            'protocol': 'Frozen defaults, historical final 30%; no parameter search or promotion. Grid rails +/-15% first evaluation open, 7 geometric rungs at $100; $10000 capital. Spot fees 6bps, slippage 2bps.',
            'sources': before, 'inputs': inputs, 'rows': rows,
            'limitations': ['Unchanged auxiliary copies should produce parity; this does not establish independent engine agreement.',
                            'Auxiliary mechanisms did not receive all 273 DSO passes; no full convergence claim.',
                            'Realized-fill win rate is not episode win rate. No suitable directional accuracy for resting-order bots.']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, default=REPO / 'research/strategy_experiment')
    parser.add_argument('--data-dir', type=Path, default=resolve_data_dir())
    parser.add_argument('--prices-dir', type=Path, default=Path.home() / '.config/soltui/prices')
    args = parser.parse_args()
    result = clean_json(run(args.experiment, args.data_dir, args.prices_dir))
    out = args.experiment / 'results'
    out.mkdir(exist_ok=True)
    (out / 'auxiliary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    lines = ['# Auxiliary paired comparison', '', result['disclaimer'], '', result['protocol'], '',
             '| Mechanism | Dataset | Status | Old/new identical | Original return/P&L | Candidate return/P&L |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in result['rows']:
        vals = []
        for v in ('original', 'candidate'):
            cell = row.get(v, {})
            value = cell.get('metrics', {}).get('total_return', cell.get('pnl_usd'))
            vals.append((f'${value:.6f}' if row['mechanism'] == 'triangle' else f'{value:.3%}')
                        if value is not None else 'n/a')
        status = row.get('status', row.get('original', {}).get('status', 'unknown'))
        lines.append('| ' + ' | '.join([row['mechanism'], row['dataset'], status,
                                       str(row.get('identical', 'n/a')), *vals]) + ' |')
    score = next((r for r in result['rows'] if r['mechanism'] == 'scorecard'), {})
    if 'original' in score and 'candidate' in score:
        a, b = (score[v]['accuracy'] for v in ('original', 'candidate'))
        lines += ['', '## Directional accuracy', '',
                  f"Scorecard common executable next-open-to-close accuracy: {a['correct_calls']}/{a['active_calls']} "
                  f"({_percent(a['accuracy'])}) original, {b['correct_calls']}/{b['active_calls']} ({_percent(b['accuracy'])}) candidate. "
                  f"Flat calls abstain; coverage {_percent(b['coverage'])}; same-active-bar majority baseline {_percent(b['majority_baseline'])}. "
                  'Ties count as incorrect in this common diagnostic.', '',
                  'Native forecast reporting uses a different interval boundary and excludes ties. Its old/new percentages change '
                  'because the label changed from previous-close to executable next-open. That is a measurement correction, not an improved signal. '
                  'Exact native panels are retained in the JSON.', '',
                  f"All {len(score.get('component_coverage', []))} scorecard components have coverage records in the JSON. "
                  'Components requiring absent auxiliary inputs or prospective history are gaps. Gates do not make directional predictions.']
    lines += ['', *result['limitations'], '', 'Exact configs, inputs, source hashes, errors and indicator accuracy denominators are in auxiliary.json.', '']
    (out / 'auxiliary.md').write_text('\n'.join(lines))
    print(json.dumps({'rows': len(result['rows']), 'output': str(out / 'auxiliary.json')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
