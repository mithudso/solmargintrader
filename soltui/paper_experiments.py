"""Prospective strategy experiments. Paper only: no keys, orders or venue execution.

A detached worker records a strategy's forecasts with forwardtest's causal minute
contract. Each directional forecast is a separate, non-overlapping 1x simulated
trade entered at the next future minute open and closed at the horizon close.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from . import config, forwardtest
from backtester.core.strategies import REGISTRY

REPO = Path(__file__).resolve().parent.parent
HORIZONS = (1, 5, 30)


def root() -> Path:
    return config.CONFIG_DIR / "paper-experiments"


def _path(eid: str, suffix: str) -> Path:
    if len(eid) != 24 or any(c not in '0123456789abcdef' for c in eid):
        raise ValueError('invalid experiment id')
    return root() / f'{eid}.{suffix}'


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as f:
        tmp = f.name
        json.dump(data, f, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _locked(eid: str) -> bool:
    path = _path(eid, 'lock')
    if not path.exists():
        return False
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False
    finally:
        os.close(fd)


def _revision() -> str:
    return hashlib.sha256((forwardtest.revision() + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()).encode()).hexdigest()


def _launch(eid: str) -> dict[str, Any]:
    try:
        with _path(eid, 'log').open('ab') as log:
            p = subprocess.Popen([sys.executable, '-m', 'soltui.paper_experiments', 'run', eid],
                                 cwd=REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, env={**os.environ, 'SOLTUI_CONFIG_DIR': str(config.CONFIG_DIR)})
    except OSError as exc:
        plan = _read(_path(eid, 'json'))
        plan.update(phase='error', message=f'Could not start worker: {exc}')
        _write(_path(eid, 'json'), plan)
        raise
    return {'id': eid, 'pid': p.pid, 'phase': 'starting'}


def start(strategy: str, asset: str, minutes: int, capital: float, cost_bps: float,
          params: dict[str, Any] | None = None, *, execution: dict | None = None) -> dict[str, Any]:
    from .bgqueue import validate_asset

    asset = validate_asset(asset)
    if strategy not in REGISTRY or minutes not in HORIZONS:
        raise ValueError('Choose a registered strategy and a 1, 5 or 30 minute horizon')
    if not math.isfinite(capital) or capital <= 0 or not math.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError('Capital must be positive and costs must be nonnegative')
    if execution:
        from .simulation import Execution
        Execution(**execution)
    spec = forwardtest.member(strategy, params or {})
    eid = secrets.token_hex(12)
    plan = {'id': eid, 'asset': asset, 'strategy': strategy, 'minutes': minutes,
            'capital': capital, 'cost_bps': cost_bps, 'spec': spec, 'execution': execution,
            'code': _revision(), 'label': f'paper-experiment:{eid}',
            'created_at': time.time(), 'launch_requested_at': time.time(), 'phase': 'starting', 'message': 'Starting'}
    _write(_path(eid, 'json'), plan)
    return _launch(eid)


def resume(eid: str) -> dict[str, Any]:
    plan = _read(_path(eid, 'json'))
    if _locked(eid) or (plan['phase'] == 'starting' and time.time() - plan.get('launch_requested_at', 0) < 30):
        raise ValueError('Experiment is already running or starting')
    if _revision() != plan['code']:
        raise ValueError('Strategy code changed; start a new experiment')
    _path(eid, 'stop').unlink(missing_ok=True)
    plan.update(phase='starting', message='Resuming', launch_requested_at=time.time())
    _write(_path(eid, 'json'), plan)
    return _launch(eid)


def stop(eid: str) -> dict[str, Any]:
    plan = _read(_path(eid, 'json'))
    if not _locked(eid) and plan['phase'] != 'starting':
        return {'id': eid, 'stopping': False, 'message': 'Experiment is not running'}
    _path(eid, 'stop').touch(mode=0o600)
    return {'id': eid, 'stopping': True}


def run(eid: str) -> int:
    plan = _read(_path(eid, 'json'))
    fd = os.open(_path(eid, 'lock'), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1
        trial = {'label': plan['label'], 'mode': 'all', 'members': [plan['spec']]}
        plan.update(phase='running', pid=os.getpid(), message='Waiting for a closed minute')
        _write(_path(eid, 'json'), plan)
        last_minute = -1
        while not _path(eid, 'stop').exists():
            now = time.time()
            minute = int(now // 60)
            if minute != last_minute and now % 60 >= 5:
                last_minute = minute
                try:
                    if _revision() != plan['code']:
                        plan.update(phase='error', message='Strategy code changed; start a new experiment')
                        break
                    result = forwardtest.tick(plan['asset'], [trial], (plan['minutes'],), plan['cost_bps'],
                                              code=plan['code'], tune=False, execution=plan.get('execution'))
                    plan['message'] = result['message']
                    plan['checked_at'] = time.time()
                except Exception as exc:  # retain the paper run across transient feed errors
                    plan['message'] = f'{type(exc).__name__}: {exc}'[:250]
                    plan['checked_at'] = time.time()
                _write(_path(eid, 'json'), plan)
            time.sleep(1)
        if plan['phase'] != 'error':
            plan.update(phase='stopped', message='Stopped by user')
        _write(_path(eid, 'json'), plan)
        _path(eid, 'stop').unlink(missing_ok=True)
        return 0
    finally:
        os.close(fd)


def status(eid: str) -> dict[str, Any]:
    plan = _read(_path(eid, 'json'))
    plan['running'] = _locked(eid)
    if not plan['running'] and (plan['phase'] == 'running' or (plan['phase'] == 'starting'
            and time.time() - plan.get('launch_requested_at', 0) >= 30)):
        plan['phase'] = 'interrupted'
    rows = [r for r in forwardtest.status(plan['asset']) if r['label'] == plan['label']]
    plan['trial'] = rows[0] if rows else None
    plan['equity'] = plan['capital']
    plan['trades'] = 0
    plan['calls'] = []
    plan['calls_recorded'] = 0
    if rows:
        dbpath = config.CONFIG_DIR / 'forwardtest' / 'trials.sqlite3'
        with sqlite3.connect(dbpath.resolve().as_uri() + '?mode=ro', uri=True) as db:
            columns = {r[1] for r in db.execute('PRAGMA table_info(call)')}
            extra = ',net_return,traded' if 'net_return' in columns else ',NULL,NULL'
            calls = db.execute('SELECT issued,start,finish,prediction,outcome,bps,expired' + extra + ' FROM call WHERE trial=? ORDER BY bar',
                               (rows[0]['id'],)).fetchall()
        plan['calls_recorded'] = len(calls)
        equity = float(plan['capital'])
        for issued, start_ts, finish, prediction, outcome, bps, expired, net_return, traded in calls:
            pnl = None
            eligible = bool(traded) if plan.get('execution') else bool(prediction)
            if outcome is not None and eligible and bps is not None:
                if plan.get('execution') and net_return is None:
                    continue
                net = (net_return if plan.get('execution') else
                       prediction * math.expm1(float(bps) / 10000) - plan['cost_bps'] / 10000)
                pnl = equity * net
                equity = max(0.0, equity + pnl)
                plan['trades'] += 1
            plan['calls'].append({'issued': issued, 'start': start_ts, 'finish': finish,
                                  'prediction': prediction, 'outcome': outcome, 'bps': bps,
                                  'expired': bool(expired), 'paper_pnl': pnl})
        plan['equity'] = equity
        plan['calls'] = plan['calls'][-50:]
    plan['pnl'] = plan['equity'] - plan['capital']
    return plan


def list_experiments() -> list[dict[str, Any]]:
    if not root().exists():
        return []
    out = []
    for path in sorted(root().glob('*.json')):
        try:
            out.append(status(path.stem))
        except (OSError, ValueError, KeyError, sqlite3.Error):
            continue
    return sorted(out, key=lambda r: r['created_at'], reverse=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('verb', choices=['run'])
    p.add_argument('id')
    args = p.parse_args()
    return run(args.id)


if __name__ == '__main__':
    raise SystemExit(main())
