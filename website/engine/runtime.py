"""Dedicated public-data/Oracle/job owner for the hosted analysis container."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import inspect
import io
import json
import logging
import math
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from . import signals
from .jobs import Jobs
from .public_data import DataError, PublicData, atomic
from .server import (
    COINS,
    INTERVALS,
    Analysis,
    RequestError,
    catalogue,
    choose_top,
    make_server,
    record_event,
)
from .state import Checkpoint, RemoteState, StateError, canonical


def source_identity():
    import backtester
    import oracle

    digest = hashlib.sha256()
    for label, directory in (
        ("backtester", Path(inspect.getfile(backtester)).parent),
        ("oracle", Path(inspect.getfile(oracle)).parent),
        ("website/engine", Path(__file__).parent),
    ):
        for path in sorted(directory.rglob("*")):
            if (
                path.is_file()
                and path.suffix in (".py", ".md", ".txt")
                and not any(
                    part.startswith((".", "test_"))
                    or part in ("tests", "__pycache__", "build", "dist")
                    or part.endswith(".egg-info")
                    for part in path.relative_to(directory).parts
                )
            ):
                digest.update(
                    (label + "/" + path.relative_to(directory).as_posix()).encode()
                )
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
    return {
        "sha256": digest.hexdigest(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "solmargintrader-backtester",
                "solmargintrader-oracle",
                "numpy",
                "pandas",
            )
        },
    }


class Runtime:
    def __init__(self, root, remote, *, public=None, clock=time.time):
        self.root, self.clock = Path(root), clock
        self.lock = threading.RLock()
        self.compute = threading.BoundedSemaphore(1)
        self.checkpoint = Checkpoint(self.root, remote)
        self.public = public or PublicData(self.root / "data", clock=clock)
        self.initialized, self.storage_ready = False, False
        self.error, self.last_checkpoint = "starting", None
        self.started = clock()
        self.identity = source_identity()
        self.stop = threading.Event()
        self.engines, self.market_errors, self.bootstrap = {}, {}, {}
        self.jobs = None
        self.restored = False
        self.analysis = RuntimeAnalysis(self)

    def save(self):
        try:
            self.checkpoint.save()
            self.storage_ready, self.last_checkpoint = True, self.clock()
            self.error = None
        except Exception:  # noqa: BLE001 - readiness stays withheld for any unconfirmed checkpoint.
            self.storage_ready = False
            self.error = "durable_state_unavailable"
            raise StateError("durable_state_unavailable") from None

    def require_ready(self):
        if not self.initialized or not self.storage_ready:
            raise RequestError("runtime_not_ready")

    def initialize(self):
        from oracle.engine import OracleEngine
        from oracle.reader import ReadOnlyOracle

        with self.lock:
            if not self.restored:
                self.checkpoint.restore()
                self.restored = True
            if self.jobs is None:
                self.jobs = Jobs(self.root)
                self.jobs.recover()
            if not self.engines:
                for coin in COINS:
                    archive = self.root / "oracle" / coin / "history.sqlite3"
                    if archive.exists():
                        # Validate restored policy/relations before any writer
                        # can open that archive. Incompatible history is kept.
                        ReadOnlyOracle(archive, instrument=coin + "/USD")
                self.engines = {
                    coin: OracleEngine(
                        self.root / "oracle" / coin / "history.sqlite3",
                        instrument=coin + "/USD",
                    )
                    for coin in COINS
                }
            for coin in COINS:
                path = self.root / "bootstrap" / (coin + ".json")
                if path.exists():
                    self.bootstrap[coin] = json.loads(path.read_bytes())
            self.save()
            self.initialized, self.error = True, None

    def prime(self, coin):
        engine = self.engines[coin]
        if engine.status()["counts"]["observations"]:
            return
        path = self.root / "data" / (coin + "_1m.csv")
        if not path.is_file():
            return
        metadata = json.loads(path.with_suffix(".json").read_bytes())
        raw = path.read_bytes()
        if (
            len(raw) > 32 * 1024 * 1024
            or metadata.get("sha256") != hashlib.sha256(raw).hexdigest()
            or metadata.get("provider") != "https://api.exchange.coinbase.com"
            or metadata.get("product") != coin + "-USD"
            or metadata.get("interval") != "1m"
        ):
            raise StateError("bootstrap_source_integrity")
        now, count = self.clock(), 0
        reader = csv.DictReader(io.StringIO(raw.decode()))
        if reader.fieldnames != ["timestamp", "open", "high", "low", "close", "volume"]:
            raise StateError("bootstrap_source_integrity")
        rows = list(reader)[-300:]
        accepted = []
        for row in rows:
            try:
                timestamp, price = float(row["timestamp"]), float(row["close"])
                if (
                    not math.isfinite(timestamp)
                    or not timestamp.is_integer()
                    or timestamp < 0
                    or int(timestamp) % 60
                    or not math.isfinite(price)
                    or price <= 0
                ):
                    raise ValueError
                observed = int(timestamp)
            except (ValueError, TypeError, KeyError, OverflowError):
                raise StateError("bootstrap_source_integrity") from None
            # A closed candle is indexed by its real bucket start, not claimed
            # to be an instantaneous trade. Every index is at least60s old,
            # beyond max_age15, so it cannot issue a historical forecast.
            if observed + 60 > now:
                continue
            accepted.append((observed, price))
        for observed, price in accepted:
            engine.ingest(
                {
                    "source": "coinbase_exchange_public",
                    "instrument": coin + "/USD",
                    "venue": "coinbase",
                    "kind": "public_reference",
                    "event_id": f"{coin}:closed_candle:{observed}",
                    "observed_at": observed,
                    "received_at": now,
                    "price": price,
                    "timestamp_semantics": "closed_candle_start_index",
                    "provider": "api.exchange.coinbase.com",
                    "upstream_recency_verified": False,
                },
                now=now,
            )
            count += 1
        counts = engine.status()["counts"]
        if counts["forecasts"] or counts["resolutions"]:
            raise StateError("historical_bootstrap_must_not_forecast")
        self.bootstrap[coin] = {
            "sourceSha256": metadata["sha256"],
            "observations": count,
            "receivedAt": now,
            "timestampSemantics": "closed_candle_start_index",
            "sampleSemantics": "derived_closed_candle_close_not_instantaneous_trade_or_execution_quote",
            "historicalForecasts": 0,
            "historicalResolutions": 0,
        }
        atomic(
            self.root / "bootstrap" / (coin + ".json"), canonical(self.bootstrap[coin])
        )

    def refresh_cache(self, coin, interval):
        # Fetching happens outside the simulation engine and never accepts a
        # caller-supplied source URL. Serialize its filesystem publication.
        with self.lock:
            self.public.refresh(coin, interval)
            if interval == "1m":
                self.prime(coin)
            self.save()

    def tick(self):
        observations = []
        for coin in COINS:
            try:
                observations.append((coin, self.public.ticker(coin)))
            except DataError as error:
                self.market_errors[coin] = str(error)
        with self.lock:
            self.require_ready()
            for coin, item in observations:
                try:
                    self.engines[coin].ingest(item, now=self.clock())
                    self.market_errors.pop(coin, None)
                except ValueError:
                    self.market_errors[coin] = "market_observation_refused"
            self.save()

    def enqueue(self, body):
        with self.lock:
            self.require_ready()
            value, created = self.jobs.enqueue(body)
            if created:
                self.save()
            return value

    def get_job(self, identifier):
        with self.lock:
            self.require_ready()
            return self.jobs.get(identifier)

    def signal(self, body):
        signals.validate_request(body)
        if not signals.supported(body):
            return signals.unavailable(
                body, self.clock(), "unsupported_market_or_strategy"
            )
        if not self.compute.acquire(blocking=False):
            return signals.unavailable(body, self.clock(), "engine_busy")
        try:
            with self.lock:
                self.require_ready()
                # A fresh actual venue event is independent of OHLCV freshness.
                # Bootstrap reference samples cannot qualify this endpoint.
                market = self.engines[body["coin"]].market(now=self.clock())
                signals.current_observation(market, body["coin"], self.clock())
                try:
                    history = signals.closed_history(
                        self.root / "data", body, self.clock()
                    )
                except signals.SignalUnavailable as error:
                    if str(error) not in (
                        "cached_history_unavailable",
                        "stale_history",
                    ):
                        raise
                    try:
                        self.public.refresh(body["coin"], body["interval"])
                    except DataError:
                        raise signals.SignalUnavailable(
                            "public_data_unavailable"
                        ) from None
                    self.save()
                    history = signals.closed_history(
                        self.root / "data", body, self.clock()
                    )
            value = signals.calculate(
                body, history, market, self.identity, self.clock()
            )
            with self.lock:
                self.require_ready()
                if value["expiresAt"] <= self.clock():
                    raise signals.SignalUnavailable("signal_expired_during_calculation")
            return value
        except signals.SignalUnavailable as error:
            return signals.unavailable(body, self.clock(), str(error))
        finally:
            self.compute.release()

    def process(self, identifier=None, *, timeout=45):
        if not self.compute.acquire(blocking=False):
            raise RequestError("engine_busy")
        try:
            return self._process(identifier, timeout)
        finally:
            self.compute.release()

    def _process(self, identifier, timeout):
        with self.lock:
            self.require_ready()
            row = self.jobs.next(identifier)
            if not row:
                return None
            self.save()
        result = self.jobs.calculate(row, timeout=timeout)
        with self.lock:
            self.jobs.finish(row["id"], result)
            self.save()
            return self.jobs.get(row["id"])

    def synchronous(self, body):
        if (
            not isinstance(body, dict)
            or not {"coin", "strategy"}.issubset(body)
            or set(body) - {"coin", "strategy", "interval", "capital", "leverage"}
        ):
            raise RequestError("invalid_backtest_request")
        request = {"interval": "1h", "capital": 10000, "leverage": 1, **body}
        if not self.compute.acquire(blocking=False):
            raise RequestError("engine_busy")
        try:
            identifier = str(uuid.uuid4())
            accepted = self.enqueue({"id": identifier, "request": request})
            if accepted["status"] == "failed":
                raise RequestError(accepted["error"])
            output = self._process(identifier, 15)
            if not output or output["status"] != "complete":
                raise RequestError(
                    output.get("error", "calculation_failed")
                    if output
                    else "engine_busy"
                )
            return output["result"]
        finally:
            self.compute.release()

    def health(self):
        with self.lock:
            coins = {}
            for coin in COINS:
                caches = {}
                for interval in INTERVALS:
                    path = self.root / "data" / f"{coin}_{interval}.json"
                    if path.is_file():
                        metadata = json.loads(path.read_bytes())
                        caches[interval] = {
                            key: metadata[key]
                            for key in ("bars", "lastBar", "sha256", "contiguous")
                        }
                engine = self.engines.get(coin)
                market = engine.market(now=self.clock()) if engine else {}
                counts = engine.status()["counts"] if engine else {}
                coins[coin] = {
                    "instrument": coin + "/USD",
                    "cache": caches,
                    "nativeHistory": engine is not None,
                    "counts": counts,
                    "marketStatus": market.get("status", "unavailable"),
                    "marketAgeSeconds": market.get("age_seconds"),
                    "error": self.market_errors.get(coin),
                    "bootstrap": self.bootstrap.get(coin),
                    "qualification": "prospective_outcomes_only",
                }
            return {
                "status": "ready"
                if self.initialized and self.storage_ready
                else "starting",
                "ready": self.initialized and self.storage_ready,
                "version": "1.0.0",
                "sourceIdentity": self.identity,
                "uptimeSeconds": max(0, self.clock() - self.started),
                "epoch": self.checkpoint.remote.epoch,
                "checkpointSequence": self.checkpoint.sequence,
                "lastCheckpoint": self.last_checkpoint,
                "error": self.error,
                "stateCapacityBytes": 8 * 1024**3,
                "freeDiskBytes": shutil.disk_usage(self.root).free,
                "capabilities": {
                    "durableJobs": True,
                    "nativeOracle": True,
                    "publicData": True,
                    "strategySignals": True,
                    "execution": False,
                },
                "coins": coins,
            }

    def run(self):
        delay = 1
        while not self.stop.is_set():
            try:
                self.initialize()
                break
            except Exception as error:  # noqa: BLE001 - never create replacement history after an invalid restore.
                self.error = "restore_or_policy_failed"
                record_event(
                    "runtime_initialization_failed",
                    level=logging.ERROR,
                    error_type=type(error).__name__,
                )
                self.stop.wait(delay)
                delay = min(30, delay * 2)
        if self.stop.is_set():
            return
        # Prime genuine feature history before accepting the first live event.
        for coin in COINS:
            if self.stop.is_set():
                return
            try:
                self.refresh_cache(coin, "1m")
            except (DataError, StateError) as error:
                self.market_errors[coin] = type(error).__name__
        markets = [
            (coin, interval)
            for interval in INTERVALS
            if interval != "1m"
            for coin in COINS
        ]
        cursor, last_cache, last_minute_cache = 0, 0.0, self.clock()
        threading.Thread(
            target=self.run_jobs, name="analysis-jobs", daemon=True
        ).start()
        while not self.stop.is_set():
            began = self.clock()
            try:
                if not self.storage_ready:
                    with self.lock:
                        self.save()
                self.tick()
                if began - last_cache >= 10:
                    coin, interval = markets[cursor % len(markets)]
                    self.refresh_cache(coin, interval)
                    cursor += 1
                    last_cache = began
                # Update minute bars between bounded historical expansion pages.
                if began - last_minute_cache >= 60:
                    for coin in COINS:
                        self.refresh_cache(coin, "1m")
                    last_minute_cache = began
            except (RequestError, DataError, StateError) as error:
                record_event(
                    "runtime_cycle_deferred",
                    level=logging.WARNING,
                    error_type=type(error).__name__,
                )
            except Exception as error:  # noqa: BLE001 - keep the owner alive and withhold uncommitted state.
                self.storage_ready = False
                self.error = "runtime_cycle_failed"
                record_event(
                    "runtime_cycle_failed",
                    level=logging.ERROR,
                    error_type=type(error).__name__,
                )
            self.stop.wait(max(0.5, 5 - (self.clock() - began)))

    def run_jobs(self):
        while not self.stop.is_set():
            try:
                self.process()
            except Exception as error:  # noqa: BLE001 - pure-job retries retain pinned input and sanitized diagnostics.
                record_event(
                    "runtime_job_deferred",
                    level=logging.WARNING,
                    error_type=type(error).__name__,
                )
                if self.compute.acquire(blocking=False):
                    try:
                        with self.lock:
                            self.jobs.recover()
                            try:
                                self.save()
                            except StateError:
                                pass
                    finally:
                        self.compute.release()
            self.stop.wait(0.5)


class RuntimeAnalysis(Analysis):
    def __init__(self, runtime):
        super().__init__(runtime.root / "data", runtime.root / "oracle")
        self.runtime = runtime

    def health(self):
        return self.runtime.health()

    def strategies(self):
        value = catalogue()
        for row in value["strategies"]:
            row["strategyRevision"] = signals.strategy_revision(
                row["id"], self.runtime.identity
            )
        value["sourceIdentity"] = self.runtime.identity
        value["signalEconomicVersion"] = signals.ECONOMIC_VERSION
        return value

    def signal(self, body):
        return self.runtime.signal(body)

    def oracle(self, coin, now=None):
        with self.runtime.lock:
            self.runtime.require_ready()
            if coin not in COINS:
                raise RequestError("unsupported_coin")
            result = choose_top(self.runtime.engines[coin].predictions(now=now), coin)
            result["durability"] = {
                "epoch": self.runtime.checkpoint.remote.epoch,
                "sequence": self.runtime.checkpoint.sequence,
            }
            result["featureBootstrap"] = self.runtime.bootstrap.get(coin)
            return result

    def submit_job(self, body):
        return self.runtime.enqueue(body)

    def job(self, identifier):
        return self.runtime.get_job(identifier)

    def backtest(self, body):
        # Compatibility still uses the same durable pure-job executor and15s
        # hard child deadline; new clients should use the async job route.
        return self.runtime.synchronous(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    token = os.environ.get("ENGINE_TOKEN", "")
    remote = RemoteState(
        os.environ.get("ENGINE_STATE_URL", ""),
        os.environ.get("ENGINE_STATE_TOKEN", ""),
        int(os.environ.get("ENGINE_EPOCH", "0")),
    )
    runtime = Runtime(Path(os.environ.get("ENGINE_DATA_ROOT", "/data")), remote)
    server = make_server(runtime.analysis, token, args.host, args.port)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    threading.Thread(target=runtime.run, name="analysis-owner", daemon=True).start()
    try:
        server.serve_forever()
    finally:
        runtime.stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
