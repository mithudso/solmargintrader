"""Private, bounded advisory relay. It has no trading or model-training authority."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import time
import uuid
from urllib.parse import quote as urlquote

from .autotrade import _home

HORIZONS = ('60', '300', '600', '900', '1200', '3600')
MODEL = 'live-softmax-l2-v1'
TARGET = 'endpoint-exact-price-v1'
SOURCES = {
    'BTC': 'fixed_rate@200ms:1:BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7:oracle-ohlc',
    'ZEC': 'fixed_rate@200ms:66:4ohWGDrmqdiEHinL5Kf2BYzM9UVSe3RJ1bzoveHehiwj:oracle-ohlc',
}
TTL = 2000
LEASE = 3000
LIMIT = 24


def _number(x, low=0, high=1e16):
    return type(x) in (int, float) and math.isfinite(x) and low <= x <= high


def _integer(x, high=10**12):
    return type(x) is int and 0 <= x <= high


def _keys(value, keys):
    return isinstance(value, dict) and set(value) == set(keys)


def _validate(packet):
    if not _keys(packet, ('schema_version', 'publisher_id', 'sequence', 'asset', 'quote', 'snapshot')):
        raise ValueError('invalid_packet')
    publisher, seq, asset = packet['publisher_id'], packet['sequence'], packet['asset']
    if (packet['schema_version'] != 1 or type(packet['schema_version']) is not int
        or not isinstance(publisher, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', publisher, re.ASCII)
        or not _integer(seq, 2**53 - 1) or seq == 0 or not isinstance(asset, str) or asset not in SOURCES):
        raise ValueError('invalid_identity')
    q, s = packet['quote'], packet['snapshot']
    if (not _keys(q, ('price', 'exchangeMs', 'receivedMs')) or not _number(q['price'], 1e-12)
        or not _number(q['exchangeMs']) or not _number(q['receivedMs'])):
        raise ValueError('invalid_quote')
    if not _keys(s, ('key', 'market', 'source', 'model', 'target', 'asOfMs', 'status', 'horizons')):
        raise ValueError('invalid_snapshot')
    key = json.dumps([1, MODEL, TARGET, asset, SOURCES[asset]], separators=(',', ':'), ensure_ascii=False)
    if (s['key'] != key or s['market'] != asset or s['source'] != SOURCES[asset]
        or s['model'] != MODEL or s['target'] != TARGET or s['asOfMs'] != q['receivedMs']
        or s['status'] not in ('warming', 'learning') or not _keys(s['horizons'], HORIZONS)):
        raise ValueError('invalid_snapshot_identity')
    for h in s['horizons'].values():
        fields = ('scores', 'direction', 'samples', 'issued', 'resolved', 'expired', 'capacityDrops', 'pending', 'candidate', 'uniform', 'frequency')
        if not _keys(h, fields) or any(not _integer(h[k]) for k in ('samples', 'issued', 'resolved', 'expired', 'capacityDrops', 'pending')):
            raise ValueError('invalid_horizon')
        if h['resolved'] + h['expired'] + h['pending'] != h['issued'] or h['samples'] != h['resolved'] or h['pending'] > 1500:
            raise ValueError('inconsistent_horizon')
        for name in ('candidate', 'uniform', 'frequency'):
            metric = h[name]
            if (not _keys(metric, ('brier', 'hits')) or not _number(metric['brier'], 0, 2 * h['resolved'] + 1e-8)
                or not _integer(metric['hits']) or metric['hits'] > h['resolved']):
                raise ValueError('invalid_metric')
        scores = h['scores']
        if scores is None:
            if s['status'] != 'warming' or h['direction'] != 'FLAT':
                raise ValueError('invalid_direction')
        else:
            if s['status'] != 'learning':
                raise ValueError('invalid_learning_status')
            if not _keys(scores, ('up', 'down', 'flat')) or any(not _number(v, 0, 1) for v in scores.values()) or abs(sum(scores.values()) - 1) > 1e-6:
                raise ValueError('invalid_scores')
            maximum = max(scores.values())
            winners = [k.upper() for k, v in scores.items() if v == maximum]
            direction = winners[0] if len(winners) == 1 else 'FLAT'
            if h['direction'] != direction:
                raise ValueError('invalid_direction')
    raw = json.dumps(packet, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(raw.encode()) > 32768:
        raise ValueError('packet_too_large')
    return raw


def _directory(home, create=False):
    if create:
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = home.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('signal_directory_not_private')
    return True


def _db(create=False):
    home = _home()
    if not _directory(home, create):
        return None
    path = home / 'signals.sqlite3'
    try:
        fd = os.open(path, (os.O_RDWR | os.O_CREAT if create else os.O_RDONLY) | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except FileNotFoundError:
        return None
    except OSError:
        raise ValueError('signal_file_not_private') from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('signal_file_not_private')
        # Check that SQLite will open the same inode inspected above.
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError('signal_file_changed')
        uri = 'file:' + urlquote(str(path), safe='/') + ('?mode=rw' if create else '?mode=ro')
        db = sqlite3.connect(uri, uri=True, timeout=1)
    finally:
        os.close(fd)
    if create:
        db.execute('CREATE TABLE IF NOT EXISTS signals (asset TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.commit()
    return db


def _close(window, end, reason):
    window = copy.deepcopy(window)
    window.update(end_ms=end, reason=reason, duration_ms=max(0, end - window['start_ms']))
    window['sustained'] = window['last_ms'] - window['start_ms'] >= 15000
    return window


def _expire(state, now):
    if now <= state['expires_at_ms']:
        return
    for row in state['horizons'].values():
        if row['window']:
            row['history'].append(_close(row['window'], state['expires_at_ms'], 'stale'))
            row['history'] = row['history'][-LIMIT:]
            row['window'] = None


def _view(state, now):
    state = copy.deepcopy(state)
    _expire(state, now)
    state['fresh'] = not state.get('invalidated', False) and now <= state['expires_at_ms'] and now >= state['as_of_ms']
    for row in state['horizons'].values():
        w = row['window']
        if w:
            w['duration_ms'] = max(0, w['last_ms'] - w['start_ms'])
            w['sustained'] = w['duration_ms'] >= 15000
    for key in ('sequence', 'digest', 'lease_until_ms'):
        state.pop(key, None)
    return state


def status(now_ms=None):
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if not _number(now):
        raise ValueError('invalid_time')
    db = _db()
    if db is None:
        return {'available': False, 'now_ms': now, 'assets': {}}
    try:
        rows = db.execute('SELECT asset, data FROM signals').fetchall()
        states = {asset: json.loads(data) for asset, data in rows}
        return {'available': True, 'now_ms': now, 'assets': {asset: _view(state, now) for asset, state in states.items() if not state.get('tombstone')}}
    finally:
        db.close()


def publish(packet, now_ms=None):
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if not _number(now):
        raise ValueError('invalid_time')
    raw = _validate(packet)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    q, snap, asset = packet['quote'], packet['snapshot'], packet['asset']
    db = _db(True)
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT data FROM signals WHERE asset=?', (asset,)).fetchone()
        old = json.loads(row[0]) if row else None
        if old and old['publisher_id'] == packet['publisher_id']:
            if packet['sequence'] == old['sequence'] and digest == old['digest']:
                db.rollback()
                return {'accepted': True, 'duplicate': True, 'asset': None if old.get('tombstone') else _view(old, now)}
            if packet['sequence'] <= old['sequence']:
                raise ValueError('sequence_conflict')
        elif old and now <= old['lease_until_ms']:
            raise ValueError('publisher_busy')
        if (q['receivedMs'] > now or now - q['receivedMs'] > TTL or q['exchangeMs'] > now + 250
            or now - q['exchangeMs'] > TTL or q['exchangeMs'] > q['receivedMs'] + 250):
            raise ValueError('quote_not_fresh')
        if old and not old.get('tombstone') and (q['receivedMs'] <= old['as_of_ms']
                or q['exchangeMs'] <= old['quote']['exchangeMs']):
            raise ValueError('quote_out_of_order')
        previous = copy.deepcopy(old) if old and not old.get('tombstone') else None
        if previous:
            _expire(previous, now)
        changed_publisher = previous and old['publisher_id'] != packet['publisher_id']
        horizons = {}
        for horizon, source_row in snap['horizons'].items():
            prev = previous['horizons'][horizon] if previous else None
            history = copy.deepcopy(prev['history']) if prev else []
            window = copy.deepcopy(prev['window']) if prev else None
            if window and changed_publisher:
                history.append(_close(window, min(now, old['expires_at_ms']), 'publisher_changed'))
                window = None
            scores, direction = source_row['scores'], source_row['direction']
            eligible = scores is not None and direction in ('UP', 'DOWN') and scores[direction.lower()] >= .8
            if window and (not eligible or window['direction'] != direction):
                history.append(_close(window, q['receivedMs'], 'side_flip' if eligible else 'below_threshold'))
                window = None
            if eligible:
                score = scores[direction.lower()]
                if window is None:
                    window = {'id': uuid.uuid4().hex, 'direction': direction, 'start_ms': q['receivedMs'], 'last_ms': q['receivedMs'], 'peak': score}
                else:
                    window['peak'] = max(window['peak'], score)
                    window['last_ms'] = q['receivedMs']
            horizons[horizon] = {**copy.deepcopy(source_row), 'window': window, 'history': history[-LIMIT:]}
        state = {'publisher_id': packet['publisher_id'], 'sequence': packet['sequence'], 'digest': digest,
                 'lease_until_ms': now + LEASE, 'source': snap['source'], 'model': MODEL, 'target': TARGET,
                 'quote': q, 'as_of_ms': q['receivedMs'], 'expires_at_ms': min(q['receivedMs'], q['exchangeMs']) + TTL,
                 'status': snap['status'], 'horizons': horizons}
        db.execute('INSERT OR REPLACE INTO signals(asset,data) VALUES (?,?)', (asset, json.dumps(state, separators=(',', ':'))))
        db.commit()
        return {'accepted': True, 'duplicate': False, 'asset': _view(state, now)}
    finally:
        db.close()


def invalidate(event, now_ms=None):
    """Fence late publications and close the current publisher's advisory windows."""
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if not _number(now):
        raise ValueError('invalid_time')
    if not _keys(event, ('asset', 'publisher_id', 'sequence', 'reason')):
        raise ValueError('invalid_invalidation')
    asset, publisher, seq, reason = (event[k] for k in ('asset', 'publisher_id', 'sequence', 'reason'))
    if (not isinstance(asset, str) or asset not in SOURCES
        or not isinstance(publisher, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', publisher, re.ASCII)
        or not _integer(seq, 2**53 - 1) or seq == 0
        or not isinstance(reason, str) or reason not in ('source_changed', 'feed_unavailable', 'page_closed', 'stale')):
        raise ValueError('invalid_invalidation')
    digest = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    db = _db(True)
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT data FROM signals WHERE asset=?', (asset,)).fetchone()
        old = json.loads(row[0]) if row else None
        if old and old['publisher_id'] != publisher:
            db.rollback()
            return {'accepted': False, 'duplicate': False, 'asset': None}
        if old and seq == old['sequence'] and digest == old['digest']:
            db.rollback()
            return {'accepted': True, 'duplicate': True, 'asset': None if old.get('tombstone') else _view(old, now)}
        if old and seq <= old['sequence']:
            raise ValueError('sequence_conflict')
        if old and not old.get('tombstone'):
            state = copy.deepcopy(old)
            _expire(state, now)
            for horizon in state['horizons'].values():
                if horizon['window']:
                    horizon['history'].append(_close(horizon['window'], min(now, state['expires_at_ms']), reason))
                    horizon['history'] = horizon['history'][-LIMIT:]
                    horizon['window'] = None
            state['invalidated'] = True
            state['status'] = 'stale'
            state['expires_at_ms'] = min(now, state['expires_at_ms'])
        else:
            state = {'publisher_id': publisher, 'tombstone': True}
        state.update(sequence=seq, digest=digest, lease_until_ms=-1)
        db.execute('INSERT OR REPLACE INTO signals(asset,data) VALUES (?,?)',
                   (asset, json.dumps(state, separators=(',', ':'))))
        db.commit()
        return {'accepted': True, 'duplicate': False, 'asset': None if state.get('tombstone') else _view(state, now)}
    finally:
        db.close()
