"""Coinbase market catalog and consumer-account reads; no signing or order execution.

The Coinbase for Agents CLI owns its credentials. The app invokes it with argument
arrays and never loads, stores, or logs keys. Market data uses the public Advanced
Trade endpoint and publishes a complete snapshot only after every page succeeds.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from . import config

PUBLIC_PRODUCTS = 'https://api.coinbase.com/api/v3/brokerage/market/products'
CLI_PATH = Path.home() / '.local/share/soltui/coinbase-cli/node_modules/.bin/coinbase'
MAX_PAGES = 200


def storage_dir() -> Path:
    return config.CONFIG_DIR / 'coinbase'


def markets_path() -> Path:
    return storage_dir() / 'markets.json'


def spot_pairs_path() -> Path:
    return storage_dir() / 'spot-pairs.json'


def _store(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        name = f.name
        os.fchmod(f.fileno(), 0o600)
        json.dump(value, f, separators=(',', ':'), allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={'User-Agent': 'solmargintrader-coinbase/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def _global_instruments() -> dict[str, Any]:
    body = json.dumps({'jsonrpc': '2.0', 'method': 'public/get_instruments', 'params': {}, 'id': 1}).encode()
    req = urllib.request.Request('https://drb.coinbase.com/api/v2', data=body,
                                 headers={'User-Agent': 'solmargintrader-coinbase/1.0',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def download_spot_pairs(fetch: Callable[[str], dict[str, Any]] = _get) -> dict[str, Any]:
    """Publish a spot-only catalog only after every Coinbase page succeeds."""
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    cursors: set[str] = set()
    cursor = ''
    for page in range(MAX_PAGES):
        params = {'limit':250, 'get_all_products':'true', 'product_type':'SPOT'}
        if cursor:
            params['cursor'] = cursor
        data = fetch(PUBLIC_PRODUCTS + '?' + urllib.parse.urlencode(params))
        products, paging = data.get('products'), data.get('pagination')
        if not isinstance(products,list) or not isinstance(paging,dict) or type(paging.get('has_next')) is not bool:
            raise ValueError('Incomplete Coinbase spot page; prior pair catalog preserved')
        for product in products:
            if (not isinstance(product,dict) or not isinstance(product.get('product_id'),str)
                    or not product['product_id'].strip() or product.get('product_type') != 'SPOT'):
                raise ValueError('Invalid Coinbase spot pair; prior pair catalog preserved')
            pid = product['product_id']
            if pid not in ids:
                ids.add(pid)
                rows.append(product)
        if not paging['has_next']:
            if not rows:
                raise ValueError('Empty Coinbase spot catalog; prior pair catalog preserved')
            result = {'source':PUBLIC_PRODUCTS, 'scope':'SPOT', 'complete':True,
                      'fetched_at':time.time(), 'pages':page + 1, 'count':len(rows), 'products':rows,
                      'note':'Public spot products; account eligibility and trading availability are separate.'}
            _store(spot_pairs_path(),result)
            return {k:v for k,v in result.items() if k != 'products'} | {'path':str(spot_pairs_path())}
        nxt = paging.get('next_cursor')
        if not products or not isinstance(nxt,str) or not nxt or nxt in cursors:
            raise ValueError('Coinbase spot pagination stalled; prior pair catalog preserved')
        cursors.add(nxt)
        cursor = nxt
    raise ValueError('Coinbase spot page limit reached; prior pair catalog preserved')


def spot_pairs(query: str = '') -> dict[str, Any]:
    try:
        result = json.loads(spot_pairs_path().read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'scope':'SPOT','complete':False,'count':0,'pairs':[],
                'message':'Spot-pair catalog has not been downloaded'}
    needle = query.strip().upper()
    pairs = [p['product_id'] for p in result.get('products',[]) if needle in p.get('product_id','').upper()]
    return {'scope':'SPOT','complete':result.get('complete') is True,'count':result.get('count',0),
            'fetched_at':result.get('fetched_at'),'pairs':pairs}


def download_markets(fetch: Callable[[str], dict[str, Any]] = _get,
                     global_fetch: Callable[[], dict[str, Any]] = _global_instruments) -> dict[str, Any]:
    products: list[dict[str, Any]] = []
    scopes: dict[str, dict[str, Any]] = {}
    for product_type in ('SPOT', 'FUTURE', 'EQUITY'):
        cursor = ''
        seen: set[str] = set()
        ids: set[str] = set()
        scope_rows: list[dict[str, Any]] = []
        problem = 'page limit reached'
        for page in range(MAX_PAGES):
            params = {'limit': 250, 'get_all_products': 'true', 'product_type': product_type}
            if cursor:
                params['cursor'] = cursor
            try:
                d = fetch(PUBLIC_PRODUCTS + '?' + urllib.parse.urlencode(params))
            except (OSError, ValueError) as exc:
                problem = 'request failed: ' + type(exc).__name__
                break
            rows, paging = d.get('products'), d.get('pagination')
            if not isinstance(rows, list) or not isinstance(paging, dict) or not isinstance(paging.get('has_next'), bool):
                problem = 'incomplete page'
                break
            if any(not isinstance(row, dict) or not isinstance(row.get('product_id'), str) for row in rows):
                problem = 'invalid market row'
                break
            for row in rows:
                if row['product_id'] not in ids:
                    ids.add(row['product_id'])
                    scope_rows.append(row)
            if not paging['has_next']:
                problem = ''
                break
            nxt = paging.get('next_cursor')
            if not rows or not isinstance(nxt, str) or not nxt or nxt in seen:
                problem = 'pagination stalled'
                break
            seen.add(nxt)
            cursor = nxt
        products.extend(scope_rows)
        scopes[product_type] = {'complete': not problem, 'count': len(scope_rows),
                                'pages': page + 1, 'error': problem}
    try:
        global_reply = global_fetch()
        instruments = global_reply.get('result')
        if not isinstance(instruments, list) or global_reply.get('error'):
            raise ValueError('invalid response')
        scopes['GLOBAL_DERIVATIVES'] = {'complete': True, 'count': len(instruments)}
    except (OSError, ValueError) as exc:
        instruments = []
        scopes['GLOBAL_DERIVATIVES'] = {'complete': False, 'count': 0,
                                       'error': 'request failed: ' + type(exc).__name__}
    result = {'source': PUBLIC_PRODUCTS, 'global_source': 'https://drb.coinbase.com/api/v2',
              'fetched_at': time.time(), 'complete': all(s['complete'] for s in scopes.values()),
              'scopes': scopes,
              'count': len(products), 'global_count': len(instruments), 'products': products,
              'global_instruments': instruments,
              'note': 'Public catalog; account eligibility and order support are separate.'}
    path = markets_path() if result['complete'] else storage_dir() / 'markets-partial.json'
    _store(path, result)
    return {k: v for k, v in result.items() if k not in ('products', 'global_instruments')} | {'path': str(path)}


def markets() -> dict[str, Any]:
    try:
        return json.loads(markets_path().read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'complete': False, 'products': [], 'message': 'Market catalog has not been downloaded'}


def _cli(args: list[str]) -> dict[str, Any]:
    executable = str(CLI_PATH) if CLI_PATH.is_file() else shutil.which('coinbase')
    if not executable:
        raise ValueError('Coinbase CLI is not installed; install the official Coinbase for Agents CLI')
    try:
        p = subprocess.run([executable, *args], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('Coinbase CLI could not complete the account read') from exc
    if p.returncode:
        raise ValueError('Coinbase CLI account access is unavailable; configure a read-enabled Coinbase API key')
    try:
        data = json.loads(p.stdout)
    except ValueError as exc:
        raise ValueError('Coinbase CLI returned an invalid account response') from exc
    if not isinstance(data, dict):
        raise ValueError('Coinbase CLI returned an invalid account response')
    return data


def sync_account(call: Callable[[list[str]], dict[str, Any]] = _cli) -> dict[str, Any]:
    data = call(['portfolios', 'list'])
    portfolios = data.get('portfolios')
    if not isinstance(portfolios, list):
        raise ValueError('Coinbase did not return a portfolio list')
    accounts = []
    breakdowns = []
    for portfolio in portfolios:
        if not isinstance(portfolio, dict) or portfolio.get('deleted'):
            continue
        pid = portfolio.get('uuid')
        if not isinstance(pid, str) or not pid:
            raise ValueError('Coinbase returned a portfolio without an id')
        breakdown = call(['portfolios', 'get', pid])
        if not isinstance(breakdown.get('portfolio'), dict) or breakdown['portfolio'].get('uuid') != pid:
            raise ValueError('Coinbase returned a breakdown for the wrong portfolio')
        breakdowns.append(breakdown)
        cursor = ''
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            args = ['balance', 'limit==250', 'portfolio_id==' + pid]
            if cursor:
                args.append('cursor==' + cursor)
            result = call(args)
            rows = result.get('accounts')
            has_next = result.get('has_next')
            # The official CLI omits false and empty fields on the final page.
            # Accept that representation only if the page is self-consistent.
            if has_next is None and not result.get('cursor') and isinstance(rows, list):
                size = result.get('size')
                if type(size) is int and size == len(rows):
                    has_next = False
            if not isinstance(rows, list) or not isinstance(has_next, bool):
                raise ValueError('Coinbase returned an incomplete balance page')
            if result.get('portfolio_id') != pid:
                raise ValueError('Coinbase returned balances for the wrong portfolio')
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('currency'), str):
                    raise ValueError('Coinbase returned an invalid balance row')
                accounts.append({**row, 'portfolio_id': pid, 'portfolio_name': portfolio.get('name', '')})
            if not has_next:
                break
            nxt = result.get('cursor')
            if not isinstance(nxt, str) or not nxt or nxt in seen:
                raise ValueError('Coinbase balance pagination stalled')
            seen.add(nxt)
            cursor = nxt
        else:
            raise ValueError('Coinbase balance page limit reached')
    snap = {'source': 'coinbase-cli', 'fetched_at': time.time(), 'complete': True,
            'portfolios': portfolios, 'accounts': accounts, 'breakdowns': breakdowns,
            'note': 'Trading balances and separate portfolio positions, including staked holdings.'}
    _store(storage_dir() / 'account.json', snap)
    return snap


def last_account() -> dict[str, Any]:
    try:
        return json.loads((storage_dir() / 'account.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'complete': False, 'accounts': [], 'message': 'Coinbase account has not been synced'}
