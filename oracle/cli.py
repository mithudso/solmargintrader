"""Oracle forecasts, inert queries and explicitly enabled venue webhooks."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import signal
import sqlite3
import stat
import sys
import tempfile
import threading
from contextlib import closing, contextmanager
from pathlib import Path


def default_archive() -> Path:
    return Path.home() / ".local/share/solmargintrader/oracle/history.sqlite3"


def emit(data: dict) -> None:
    print(
        json.dumps({"schema_version": 1, **data}, allow_nan=False, sort_keys=True),
        flush=True,
    )


def prerequisite_message(error: ModuleNotFoundError) -> str:
    packages = {"numpy": "numpy", "pandas": "pandas", "mcp": "mcp",
                "jsonschema": "jsonschema", "pydantic": "pydantic",
                "cryptography": "cryptography", "backtester": "solmargintrader-backtester"}
    package = packages.get((error.name or "").split(".")[0], "a required Python package")
    return (f"Missing {package}. From the repository root, run: "
            "uv pip install --python .venv/bin/python -e ./backtester -e ./oracle")


@contextmanager
def owner(archive: Path):
    archive.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = archive.with_suffix(archive.suffix + ".owner.lock")
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("archive_owner_already_running") from None
        yield
    finally:
        os.close(fd)


def snapshot(archive: Path, destination: Path) -> dict:
    """Publish a consistent immutable database copy; never overwrite an archive."""
    if destination.exists() or not archive.is_file():
        raise ValueError("snapshot_source_missing_or_destination_exists")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".oracle-snapshot-", dir=destination.parent)
    os.close(fd)
    try:
        with (
            closing(
                sqlite3.connect(archive.resolve().as_uri() + "?mode=ro", uri=True)
            ) as source,
            closing(sqlite3.connect(temp)) as target,
        ):
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("archive_integrity_failed")
        with open(temp, "rb") as handle:
            os.fsync(handle.fileno())
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        os.link(temp, destination)
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {
            "status": "saved",
            "path": str(destination.absolute()),
            "sha256": digest,
            "bytes": destination.stat().st_size,
            "format": "oracle-sqlite-v1",
        }
    finally:
        Path(temp).unlink(missing_ok=True)


def read_private_secret(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("secret_file_must_be_private")
        secret = handle.read(4097).strip()
        if len(secret) > 4096:
            raise ValueError("secret_file_too_large")
        return secret


def run(args) -> int:
    from .engine import OracleEngine
    from .feeds import FeedUnavailable, JupiterPriceFeed, RecorderFeed

    stop = threading.Event()
    old = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            old[sig] = signal.signal(sig, lambda *_: stop.set())
    try:
        with owner(args.archive):
            engine = OracleEngine(args.archive, instrument=args.instrument)
            feed = (
                JupiterPriceFeed(
                    instrument=args.instrument,
                    mints={
                        args.instrument.upper().split("/")[0]: args.base_mint,
                        args.instrument.upper().split("/")[1]: args.quote_mint,
                    }
                    if args.base_mint or args.quote_mint
                    else None,
                )
                if args.source == "jupiter"
                else RecorderFeed(root=args.recorder_root, instrument=args.instrument)
            )
            attempts, failures = 0, 0
            while not stop.is_set() and (
                args.max_ticks is None or attempts < args.max_ticks
            ):
                attempts += 1
                try:
                    observation = feed.poll()
                    if observation is not None:
                        engine.ingest(observation)
                    failures = 0
                    emit(
                        {
                            "ok": True,
                            "status": "observed" if observation else "unchanged",
                            "market": engine.market(),
                        }
                    )
                except FeedUnavailable as exc:
                    failures += 1
                    emit(
                        {"ok": False, "status": "feed_unavailable", "reason": exc.code}
                    )
                # A failed archive write is fatal: predictions may not proceed unlogged.
                delay = max(args.interval, min(30, args.interval * (2 ** min(failures, 5))))
                if args.max_ticks is None or attempts < args.max_ticks:
                    stop.wait(delay)
        return 3 if failures and args.max_ticks is not None else 0
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print("Invalid Oracle command arguments.", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None) -> int:
    parser = Parser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=default_archive())
    parser.add_argument("--instrument", default="SOL/USDC")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser(
        "run", help="own the archive and consume the selected source"
    )
    p.add_argument("--source", choices=("recorder", "jupiter"), default="recorder")
    p.add_argument("--recorder-root", type=Path)
    p.add_argument("--base-mint")
    p.add_argument("--quote-mint")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--max-ticks", type=int)
    for name in ("status", "market", "predictions", "strategies", "veto"):
        commands.add_parser(name)
    p = commands.add_parser("readiness")
    p.add_argument("--manager-home", type=Path)
    p = commands.add_parser("guidance")
    p.add_argument(
        "--stage", choices=("backtest", "forward", "live"), default="backtest"
    )
    p.add_argument("--repo", type=Path)
    p = commands.add_parser("history")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--after", type=int, default=0)
    p = commands.add_parser(
        "webhook",
        help="receive TradingView alerts; optional Coinbase spot or Jupiter ZEC perps",
    )
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--inbox", type=Path, required=True)
    p.add_argument("--secret-file", type=Path)
    venues = p.add_mutually_exclusive_group()
    venues.add_argument("--coinbase", action="store_true")
    venues.add_argument("--jupiter-perps", action="store_true")
    p.add_argument("--portfolio-id")
    p.add_argument("--owner")
    p.add_argument("--trading-account")
    p.add_argument("--subaccount-id", type=int, default=0)
    p.add_argument("--leverage")
    p.add_argument(
        "--allocation", default="75", help="percentage of available USDC (maximum 75)"
    )
    p.add_argument("--allocation-basis", choices=("collateral", "notional"))
    p.add_argument("--max-slippage-bps", type=int, default=10)
    p.add_argument("--key-file", type=Path)
    p.add_argument("--live", action="store_true")
    p = commands.add_parser(
        "jupiter-preflight", help="read ZEC GUM market and owner accounts; never signs"
    )
    p.add_argument("--owner", required=True)
    p = commands.add_parser("webhook-status", help="read inbox order receipts")
    p.add_argument("--inbox", type=Path, required=True)
    p.add_argument("--limit", type=int, default=50)
    p = commands.add_parser("snapshot")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "jupiter-preflight":
            from .gum_orders import discover

            emit({"ok": True, "data": discover(args.owner)})
            return 0
        if args.command == "webhook":
            from .webhook import serve
            from .webhook_orders import process_one, recover_planning

            if (
                args.live
                and not (args.coinbase or args.jupiter_perps)
                or args.coinbase
                and not args.portfolio_id
            ):
                raise ValueError("coinbase_requires_portfolio")
            if args.jupiter_perps and (
                not args.owner
                or not args.trading_account
                or not args.leverage
                or not args.allocation_basis
                or args.portfolio_id
                or args.live
                and not args.key_file
            ):
                raise ValueError("jupiter_requires_explicit_account_and_policy")
            secret = os.environ.get("ORACLE_WEBHOOK_SECRET", "")
            if args.secret_file:
                fd = os.open(args.secret_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd) as handle:
                    info = os.fstat(handle.fileno())
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or info.st_uid != os.getuid()
                        or info.st_mode & 0o077
                    ):
                        raise ValueError("secret_file_must_be_private")
                    secret = handle.read(4097).strip()
                    if len(secret) > 4096:
                        raise ValueError("secret_file_too_large")
            venue = None
            if args.coinbase:
                from .coinbase_orders import CoinbaseOrders

                venue = CoinbaseOrders()
            if args.jupiter_perps:
                from .gum_orders import GumOrders
                from .gum_webhook_orders import process_one, recover_planning

                def sign_action(message):
                    from .gum_signer import load_signer

                    return load_signer(args.key_file, args.owner)(message)

                venue = GumOrders(
                    owner=args.owner,
                    trading_account=args.trading_account,
                    subaccount_id=args.subaccount_id,
                    leverage=args.leverage,
                    allocation=args.allocation,
                    allocation_basis=args.allocation_basis,
                    max_slippage_bps=args.max_slippage_bps,
                    signer=sign_action if args.live else None,
                )
                args.portfolio_id = venue.binding
            with owner(args.inbox):
                serve(
                    args.inbox,
                    secret,
                    args.port,
                    venue=venue,
                    portfolio_id=args.portfolio_id,
                    live=args.live,
                    processor=process_one,
                    recover=recover_planning,
                )
            return 0
        if args.command == "webhook-status":
            from .webhook_orders import records

            emit({"ok": True, "data": records(args.inbox, args.limit)})
            return 0
        if args.command == "run":
            if (
                not math.isfinite(args.interval)
                or not 0.1 <= args.interval <= 300
                or (args.max_ticks is not None and args.max_ticks < 1)
            ):
                raise ValueError("invalid_run_limits")
            return run(args)
        if args.command == "snapshot":
            emit({"ok": True, "data": snapshot(args.archive, args.out)})
            return 0
        from .engine import OracleEngine

        engine = OracleEngine(args.archive, instrument=args.instrument)
        if args.command in ("status", "market", "predictions", "strategies"):
            data = getattr(engine, args.command)()
        elif args.command == "history":
            if not 1 <= args.limit <= 1000 or args.after < 0:
                raise ValueError("invalid_history_limits")
            data = engine.history(limit=args.limit, after=args.after)
        else:
            from .guidance import guidance, readiness, veto

            if args.command == "guidance":
                data = guidance(
                    args.stage, **({"repo": args.repo} if args.repo else {})
                )
            elif args.command == "readiness":
                data = readiness(engine, manager_home=args.manager_home)
            else:
                data = veto(engine)
        emit({"ok": True, "data": data})
        return 0
    except ModuleNotFoundError as error:
        emit({"ok": False, "error": "oracle_prerequisite_unavailable", "remedy": prerequisite_message(error)})
        return 3
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        emit({"ok": False, "error": "oracle_operation_failed"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
