"""Explicitly reviewed Coinbase spot orders. Never retries a submitted order."""
from __future__ import annotations

import fcntl
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from . import coinbase_account as cb

MAX_QUOTE = Decimal('100')  # estimated per-order cap in USD or USDC
PREVIEW_SECONDS = 60
TERMINAL = {'FILLED', 'CANCELLED', 'EXPIRED', 'FAILED', 'REJECTED'}


def _decimal(value: Any, name: str, *, allow_zero: bool = False) -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{name} must be a finite number') from None
    if not x.is_finite() or x < 0 or (not allow_zero and x == 0):
        raise ValueError(f'{name} must be a finite positive number')
    return x


def _dir() -> Path:
    return cb.storage_dir() / 'manual-orders'


def _path(preview_id: str) -> Path:
    if not re.fullmatch(r'[0-9a-f]{32}', preview_id):
        raise ValueError('Invalid preview ID')
    return _dir() / (preview_id + '.json')


@contextmanager
def _lock():
    _dir().mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(_dir() / '.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding='utf-8') as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError('Invalid manual order record')
    return value


def _save(path: Path, record: dict[str, Any]) -> None:
    cb._store(path, record)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _has_unresolved() -> bool:
    for p in _dir().glob('*.json'):
        r = _read(p)
        if r.get('state') in ('submitting', 'unknown', 'pending'):
            return True
    return False


def _block_unresolved() -> None:
    if _has_unresolved():
        raise ValueError('A previous Coinbase order is unresolved. Check its status at Coinbase before placing another order.')


def state() -> dict[str, Any]:
    """Expose unresolved intent after a restart without revealing account details."""
    pending = []
    for p in _dir().glob('*.json'):
        r = _read(p)
        if r.get('state') in ('submitting', 'unknown', 'pending'):
            pending.append({k:r.get(k) for k in ('preview_id','product_id','side','state','order_id','submit_started_at')})
    return {'unresolved':bool(pending), 'orders':pending}


def _details(product_id: str, side: str, size: str, size_currency: str,
             call: Callable[[list[str]], dict[str, Any]], *, order_type: str = 'market',
             limit_price: str = '', stop_price: str = '') -> dict[str, Any]:
    product_id = product_id.strip().upper()
    side = side.strip().upper()
    if order_type not in ('market', 'limit', 'stop_limit', 'bracket'):
        raise ValueError('Unsupported Coinbase order type')
    if order_type != 'market' and size_currency != 'base':
        raise ValueError('Conditional and limit orders require a base-coin quantity')
    if order_type == 'bracket' and side != 'SELL':
        raise ValueError('Coinbase spot brackets require SELL')
    prices = {}
    for key, value in (('limit_price', limit_price), ('stop_price', stop_price)):
        required = key == 'limit_price' and order_type != 'market' or key == 'stop_price' and order_type in ('stop_limit', 'bracket')
        if required:
            if not re.fullmatch(r'\d+(?:\.\d+)?', str(value)) or len(str(value)) > 32:
                raise ValueError(f'Enter an exact positive {key.replace("_", " ")}')
            prices[key] = _decimal(value, key.replace('_', ' '))
        elif value:
            raise ValueError(f'{key} is not used for this order type')
    if order_type == 'bracket' and prices['limit_price'] <= prices['stop_price']:
        raise ValueError('Take-profit price must exceed the stop trigger')
    if not re.fullmatch(r'[A-Z0-9]{1,15}-[A-Z0-9]{1,15}', product_id):
        raise ValueError('Enter a spot pair such as SOL-USDC')
    if (side, size_currency) not in (('BUY', 'quote'), ('BUY', 'base'), ('SELL', 'base')):
        raise ValueError('Market buys use quote or base quantity; market sells use base-coin quantity')
    if not re.fullmatch(r'\d+(?:\.\d+)?', str(size)) or len(str(size)) > 32:
        raise ValueError('Enter an exact positive decimal size')
    amount = _decimal(size, 'Order size')
    product = call(['products', 'get', product_id, 'product_type==SPOT'])
    base, quote = product_id.split('-')
    if (product.get('product_id') != product_id or product.get('product_type') != 'SPOT'
            or product.get('base_currency_id') != base or product.get('quote_currency_id') != quote
            or product.get('status', '').lower() != 'online'):
        raise ValueError('Coinbase did not confirm an online spot market for this pair')
    if quote not in ('USD', 'USDC'):
        raise ValueError('Manual orders currently support USD or USDC quote markets')
    prefix = 'quote' if size_currency == 'quote' else 'base'
    minimum = _decimal(product.get(prefix + '_min_size'), 'Market minimum')
    maximum = _decimal(product.get(prefix + '_max_size'), 'Market maximum')
    increment = _decimal(product.get(prefix + '_increment'), 'Market increment')
    if not minimum <= amount <= maximum or amount % increment != 0:
        raise ValueError(f'Size must meet the market minimum, maximum and {increment} increment')
    snapshot = cb.sync_account(call)
    defaults = [p for p in snapshot['portfolios'] if p.get('type') == 'DEFAULT' and not p.get('deleted')]
    if len(defaults) != 1 or not defaults[0].get('uuid'):
        raise ValueError('Coinbase did not identify one default trading portfolio')
    pid = defaults[0]['uuid']
    wanted = quote if side == 'BUY' else base
    matches = [a for a in snapshot['accounts'] if a.get('portfolio_id') == pid and a.get('currency') == wanted]
    if len(matches) != 1 or not isinstance(matches[0].get('available_balance'), dict):
        raise ValueError(f'Cannot determine the available {wanted} balance')
    available = _decimal(matches[0]['available_balance'].get('value'), 'Available balance', allow_zero=True)
    if (side, size_currency) != ('BUY', 'base') and amount > available:
        raise ValueError(f'Insufficient available {wanted} balance')
    size_field = 'quote_size' if size_currency == 'quote' else 'base_size'
    if prices and amount * max(prices.values()) > MAX_QUOTE:
        raise ValueError('Manual orders are limited to an estimated 100 USD or USDC per order')
    fields = ['product_id='+product_id, 'side='+side, 'type='+order_type, size_field+'='+str(amount),
              'product_type=SPOT', 'portfolio_id='+pid]
    if order_type != 'market':
        fields += ['time_in_force=GTC', 'limit_price='+str(prices['limit_price'])]
        if 'stop_price' in prices:
            fields.append('stop_price='+str(prices['stop_price']))
        if order_type == 'stop_limit':
            fields.append('stop_direction=' + ('down' if side == 'SELL' else 'up'))
    estimate = call(['orders', 'preview', *fields])
    if estimate.get('errs') or estimate.get('error') or estimate.get('errorType'):
        raise ValueError('Coinbase preview reports an order error; no order was submitted')
    price = _decimal(estimate.get('est_average_filled_price'), 'Estimated price')
    fee = _decimal(estimate.get('commission_total'), 'Estimated fee', allow_zero=True)
    gross = _decimal(estimate.get('quote_size'), 'Estimated quote amount')
    total = _decimal(estimate.get('order_total'), 'Estimated order total')
    if fee >= gross or (side == 'BUY' and size_currency == 'quote' and total > amount):
        raise ValueError('Coinbase estimate exceeds the reviewed budget or fees exceed proceeds')
    if side == 'BUY' and total > available:
        raise ValueError(f'Insufficient available {wanted} balance')
    if side == 'BUY' and prices and amount * prices['limit_price'] + fee > available:
        raise ValueError(f'Insufficient available {wanted} balance at the limit price')
    if side == 'BUY' and prices and amount * prices['limit_price'] + fee > MAX_QUOTE:
        raise ValueError('Manual orders are limited to an estimated 100 USD or USDC per order')
    if gross > MAX_QUOTE or (side == 'BUY' and total > MAX_QUOTE) or (side == 'BUY' and size_currency == 'quote' and amount > MAX_QUOTE):
        raise ValueError('Manual orders are limited to an estimated 100 USD or USDC per order')
    quoted_size = amount if (side, size_currency) == ('BUY', 'quote') else gross
    if quoted_size < _decimal(product.get('quote_min_size'), 'Market quote minimum'):
        raise ValueError('Estimated order value is below the market minimum')
    return {'product_id':product_id, 'side':side, 'size':str(amount), 'size_currency':size_currency,
            'order_type':order_type, 'limit_price':limit_price, 'stop_price':stop_price,
            'portfolio_id':pid, 'fields':fields, 'price':str(price), 'fee':str(fee),
            'estimate':{'price':str(price), 'fee':str(fee), 'gross_quote':str(gross),
                        'order_total':str(total), 'base_size':str(estimate.get('base_size', '')),
                        'quote_size':str(estimate.get('quote_size', '')), 'available':str(available),
                        'available_currency':wanted, 'warning':str(estimate.get('warning') or '')}}


def preview(product_id: str, side: str, size: str, size_currency: str,
            call: Callable[[list[str]], dict[str, Any]] | None = None, *, order_type: str = 'market',
            limit_price: str = '', stop_price: str = '') -> dict[str, Any]:
    call = call or cb._cli
    with _lock():
        _block_unresolved()
        details = _details(product_id, side, size, size_currency, call, order_type=order_type,
                           limit_price=limit_price, stop_price=stop_price)
        preview_id = uuid.uuid4().hex
        expires_at = time.time() + PREVIEW_SECONDS
        _save(_path(preview_id), {**details, 'preview_id':preview_id, 'expires_at':expires_at,
                                  'state':'preview', 'client_order_id':str(uuid.uuid4())})
    return {k:details[k] for k in ('product_id','side','size','size_currency','order_type','limit_price','stop_price','estimate')} | {
        'preview_id':preview_id, 'expires_at':expires_at,
        'notice':'Estimates can change; price moves over 1% or materially higher fees require a new review. '
                 'Maximum estimated order value: 100 USD/USDC.'}


def percent_preview(product_id: str, side: str, percent: str,
                    call: Callable[[list[str]], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Review a percentage of the available quote (buy) or base (sell) balance."""
    call = call or cb._cli
    product_id, side = product_id.strip().upper(), side.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{1,15}-[A-Z0-9]{1,15}', product_id) or side not in ('BUY', 'SELL'):
        raise ValueError('Enter a valid spot pair and side')
    value = _decimal(percent, 'Balance percentage')
    if value > 100:
        raise ValueError('Balance percentage must be at most 100')
    product = call(['products', 'get', product_id, 'product_type==SPOT'])
    base, quote = product_id.split('-')
    if (product.get('product_id') != product_id or product.get('product_type') != 'SPOT'
            or product.get('base_currency_id') != base or product.get('quote_currency_id') != quote
            or product.get('status', '').lower() != 'online' or quote not in ('USD', 'USDC')):
        raise ValueError('Coinbase did not confirm an online USD or USDC spot market for this pair')
    snapshot = cb.sync_account(call)
    defaults = [p for p in snapshot['portfolios'] if p.get('type') == 'DEFAULT' and not p.get('deleted')]
    if len(defaults) != 1 or not defaults[0].get('uuid'):
        raise ValueError('Coinbase did not identify one default trading portfolio')
    wanted = quote if side == 'BUY' else base
    matches = [a for a in snapshot['accounts'] if a.get('portfolio_id') == defaults[0]['uuid']
               and a.get('currency') == wanted]
    if len(matches) != 1 or not isinstance(matches[0].get('available_balance'), dict):
        raise ValueError(f'Cannot determine the available {wanted} balance')
    available = _decimal(matches[0]['available_balance'].get('value'), 'Available balance', allow_zero=True)
    unit = 'quote' if side == 'BUY' else 'base'
    increment = _decimal(product.get(unit + '_increment'), 'Market increment')
    exact = available * value / Decimal('100')
    amount = (exact // increment) * increment
    if amount <= 0:
        raise ValueError('Percentage rounds below the market increment')
    result = preview(product_id, side, str(amount), unit, call)
    if _decimal(result['estimate']['available'], 'Available balance', allow_zero=True) != available:
        raise ValueError('Available balance changed while sizing; review again')
    result['balance_percentage'] = str(value)
    result['sizing_notice'] = f'{value}% of available {wanted}, rounded down to the market increment.'
    return result


def _public_order(order: dict[str, Any]) -> dict[str, Any]:
    fields = ('order_id', 'product_id', 'side', 'status', 'created_time', 'last_fill_time',
              'completion_percentage', 'filled_size', 'average_filled_price', 'total_fees',
              'total_value_after_fees', 'number_of_fills')
    return {k: order[k] for k in fields if k in order}


def submit(preview_id: str, call: Callable[[list[str]], dict[str, Any]] | None = None) -> dict[str, Any]:
    call = call or cb._cli
    with _lock():
        record = _read(_path(preview_id))
        if record.get('state') != 'preview':
            raise ValueError('This preview has already been used; do not submit it again')
        if time.time() >= record['expires_at']:
            raise ValueError('Preview expired; review a new quote')
        _block_unresolved()
        fresh = _details(record['product_id'], record['side'], record['size'], record['size_currency'], call,
                         order_type=record.get('order_type', 'market'), limit_price=record.get('limit_price', ''),
                         stop_price=record.get('stop_price', ''))
        if time.time() >= record['expires_at']:
            raise ValueError('Preview expired while checking Coinbase; review a new quote')
        if fresh['portfolio_id'] != record['portfolio_id']:
            raise ValueError('The default portfolio changed; review a new quote')
        if abs(_decimal(fresh['price'],'Price') / _decimal(record['price'],'Price') - 1) > Decimal('0.01'):
            raise ValueError('Estimated price changed by more than 1%; review a new quote')
        old_fee = _decimal(record['fee'], 'Reviewed fee', allow_zero=True)
        new_fee = _decimal(fresh['fee'], 'Current fee', allow_zero=True)
        if new_fee > max(old_fee * Decimal('1.10'), old_fee + Decimal('0.000001')):
            raise ValueError('Estimated fee increased; review a new quote')
        record['state'] = 'submitting'
        record['submit_started_at'] = time.time()
        _save(_path(preview_id), record)  # durable before the one allowed submission
        try:
            result = call(['orders','create',*fresh['fields'],'client_order_id='+record['client_order_id']])
        except Exception:
            record['state'] = 'unknown'
            _save(_path(preview_id), record)
            raise RuntimeError('Order outcome is unknown. Check Coinbase before placing another order; do not retry.') from None
        order_id = result.get('order_id')
        if (not isinstance(order_id, str) or not order_id
                or result.get('product_id', record['product_id']) != record['product_id']
                or result.get('side', record['side']) != record['side']
                or result.get('client_order_id', record['client_order_id']) != record['client_order_id']):
            record['state'] = 'unknown'
            _save(_path(preview_id), record)
            raise RuntimeError('Order outcome is unknown. Check Coinbase before placing another order; do not retry.')
        record.update(state='pending', order_id=order_id)
        _save(_path(preview_id), record)
        try:
            outcome = call(['orders','get',order_id])
            if (outcome.get('order_id') != order_id or outcome.get('product_id') != record['product_id']
                    or outcome.get('side') != record['side']
                    or outcome.get('client_order_id', record['client_order_id']) != record['client_order_id']):
                raise ValueError('Order identity differs')
            status = str(outcome.get('status') or '').upper()
            if status in TERMINAL:
                record['state'] = 'complete'
            record['status'] = status or 'UNKNOWN'
            _save(_path(preview_id), record)
            return {'order_id':order_id, 'status':record['status'], 'order':_public_order(outcome)}
        except Exception:
            return {'order_id':order_id, 'status':'PENDING',
                    'message':'Order submitted; status lookup failed. Check Coinbase before another order.'}


def status(order_id: str, call: Callable[[list[str]], dict[str, Any]] | None = None) -> dict[str, Any]:
    if not re.fullmatch(r'[A-Za-z0-9-]{1,128}', order_id):
        raise ValueError('Enter a valid Coinbase order ID')
    call = call or cb._cli
    with _lock():
        result = call(['orders','get',order_id])
        if result.get('order_id') != order_id:
            raise ValueError('Coinbase returned a different order')
        for p in _dir().glob('*.json'):
            record = _read(p)
            known_order = record.get('order_id') == order_id
            recovered_order = (not record.get('order_id')
                and record.get('state') in ('submitting', 'unknown', 'pending')
                and isinstance(record.get('client_order_id'), str)
                and bool(record['client_order_id'])
                and result.get('client_order_id') == record['client_order_id']
                and result.get('product_id') == record.get('product_id')
                and result.get('side') == record.get('side'))
            if known_order or recovered_order:
                if (result.get('product_id') != record.get('product_id')
                        or result.get('side') != record.get('side')
                        or (result.get('client_order_id') is not None
                            and result['client_order_id'] != record.get('client_order_id'))):
                    raise ValueError('Coinbase order identity differs from the saved submission')
                verified_status = str(result.get('status') or '').upper()
                record.update(order_id=order_id, status=verified_status or 'UNKNOWN',
                              state='complete' if verified_status in TERMINAL else 'pending')
                _save(p, record)
        return _public_order(result) | {'unresolved':_has_unresolved()}
