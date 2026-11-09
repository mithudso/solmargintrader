"""Bounded loopback owner adapter. Discovery never starts an owner or creates state."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import socket
import sqlite3
import stat
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from ..domain import ManagerError, canonical, freeze, plain
from ..receipts import CommandReceipt
from ..status import legacy_snapshot
from ..store import data_home

SAFE_COMMANDS = frozenset(
    (
        "bots.overview",
        "bots.config",
        "bots.forward_start",
        "bots.forward_stop",
        "bots.forward_status",
        "bots.manager_snapshot",
        "bots.manager_control",
        "council.status",
    )
)
CONTROL_PARAMS = {
    "bot": ("string", True),
    "operation": ("string", True),
    "asset": ("string", True),
    "request_id": ("string", True),
    "expected_session": ("string", False),
    "expected_config_hash": ("string", True),
}
FAMILIES = ("grid", "dca", "trend", "triangle", "council")
_MISSING = object()


def _fail(code: str) -> ManagerError:
    return ManagerError(code, "The configured owner is unavailable or incompatible.", 3)


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _sha(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _session(value: Any) -> bool:
    return value is None or (
        type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) is not None
    )


def _control_semantics(
    operation, outcome, reason, session, expected_session, *, pending=False
):
    outcomes = {
        "already_running": ("skipped", "start"),
        "already_stopped": ("skipped", "stop"),
        "owner_session_changed": ("failed", operation),
        "configuration_changed": ("failed", operation),
        "family_slot_occupied": ("failed", "start"),
        "market_data_unavailable": ("failed", "start"),
        "request_id_conflict": ("failed", operation),
        "outcome_unknown": ("unknown", operation),
        "forward_requested_heartbeat_unknown": ("acknowledged", "start"),
        "stop_recorded_exposure_unknown": ("acknowledged", "stop"),
    }
    if pending:
        outcomes["submission_pending"] = ("pending", operation)
    if (
        type(reason) is not str
        or outcomes.get(reason) != (outcome, operation)
        or not _session(session)
    ):
        return False
    if outcome == "acknowledged" and operation == "start":
        return session is not None and session != expected_session
    if outcome == "acknowledged" and operation == "stop":
        return expected_session is not None and session == expected_session
    if reason == "already_running":
        return expected_session is not None and session == expected_session
    if reason not in ("owner_session_changed", "outcome_unknown"):
        return session == expected_session
    return True


def _invalid_receipt():
    return ManagerError(
        "invalid_receipt", "The control receipt is invalid or incompatible.", 4
    )


@dataclass(frozen=True, kw_only=True)
class Installation:
    installation_id: str
    source: str
    working_directory: Path
    interpreter: Path
    pinned_revision: str
    config_root: Path
    endpoint: str = "http://127.0.0.1:8788"
    descriptor_version: int = 1
    protocol_version: int = 1
    advertised_commands: tuple[str, ...] = ()
    transport: str = "loopback_http"

    def __post_init__(self):
        if (
            type(self.descriptor_version) is not int
            or self.descriptor_version != 1
            or type(self.protocol_version) is not int
            or self.protocol_version != 1
            or self.source not in ("soltui", "node_filestore", "browser")
            or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", self.installation_id)
            is None
            or re.fullmatch(r"[0-9a-f]{40}", self.pinned_revision) is None
            or any(
                not isinstance(p, Path) or not p.is_absolute()
                for p in (self.working_directory, self.interpreter, self.config_root)
            )
            or any(c not in SAFE_COMMANDS for c in self.advertised_commands)
        ):
            raise _fail("invalid_installation")
        _endpoint(self.endpoint)

    def to_dict(self):
        return {
            k: str(v) if isinstance(v, Path) else list(v) if isinstance(v, tuple) else v
            for k, v in vars(self).items()
        }


def _endpoint(url: str) -> tuple[str, int]:
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "http"
            or parts.hostname != "127.0.0.1"
            or not parts.port
            or parts.username
            or parts.password
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
        ):
            raise ValueError
        return parts.hostname, parts.port
    except (ValueError, TypeError, AttributeError):
        raise _fail("invalid_installation") from None


@dataclass(frozen=True)
class Snapshot:
    state: str
    installation: Installation
    bots: tuple[Mapping[str, Any], ...] | None = None
    loaded_source_hash: str | None = None
    advertised_commands: tuple[str, ...] = ()
    reason: str | None = None
    schema_version: int = 1

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "state": self.state,
            "reason": self.reason,
            "installation_id": self.installation.installation_id,
            "source": self.installation.source,
            "descriptor": self.installation.to_dict(),
            "loaded_source_hash": self.loaded_source_hash,
            "loaded_source_hash_reason": "owner_does_not_report_loaded_identity"
            if self.loaded_source_hash is None
            else None,
            "advertised_commands": list(self.advertised_commands),
            "bots": None if self.bots is None else [plain(r) for r in self.bots],
        }


@dataclass(frozen=True)
class Capabilities:
    inspect: bool = False
    delegated_controls: bool = False
    ownership_transfer: bool = False
    generation_fencing: bool = False
    reason: str = "owner_not_discovered"
    schema_version: int = 1

    def to_dict(self):
        return vars(self).copy()


class LegacyAdapter:
    def __init__(
        self,
        installation: Installation,
        *,
        home: Path | None = None,
        token_resolver: Callable[[], str] | None = None,
        timeout: float = 1.0,
        max_bytes: int = 1024 * 1024,
    ):
        if (
            not 0 < timeout <= 5
            or type(max_bytes) is not int
            or not 1024 <= max_bytes <= 1024 * 1024
        ):
            raise _fail("invalid_installation")
        self.installation = installation
        self.home = Path(home) if home is not None else data_home()
        self.timeout, self.max_bytes = timeout, max_bytes
        self._token_resolver = token_resolver
        self._caps = Capabilities()
        self._rows: dict[str, dict[str, Any]] = {}
        self._commands: dict[str, dict[str, Any]] = {}
        self._loaded_hash = None

    def _token(self) -> str:
        if self._token_resolver is not None:
            token = self._token_resolver()
        else:
            path = (
                Path(
                    os.environ.get("SOLTUI_SUPPORT_DIR")
                    or Path.home() / "Library" / "Application Support" / "soltui"
                )
                / "api-token"
            )
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(fd) as handle:
                    info = os.fstat(handle.fileno())
                    if (
                        not stat.S_ISREG(info.st_mode)
                        or stat.S_IMODE(info.st_mode) != 0o600
                        or info.st_uid != os.getuid()
                    ):
                        raise _fail("credentials_unavailable")
                    token = handle.read(4097).strip()
            except OSError:
                raise _fail("credentials_unavailable") from None
        if (
            type(token) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]{8,4096}", token) is None
        ):
            raise _fail("credentials_unavailable")
        return token

    def _http(self, method: str, path: str, *, token: str | None = None, params=None):
        host, port = _endpoint(self.installation.endpoint)
        connection = http.client.HTTPConnection(host, port, timeout=self.timeout)
        deadline = time.monotonic() + self.timeout
        deadline_timer = None
        try:
            connection.connect()
            sock = connection.sock

            def expire():
                # A socket's per-read timeout alone permits trickled response
                # headers to hold getresponse indefinitely. Bound the whole call.
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            deadline_timer = threading.Timer(
                max(0.0, deadline - time.monotonic()), expire
            )
            deadline_timer.daemon = True
            deadline_timer.start()
            payload = None if params is None else canonical(params).encode()
            headers = {} if token is None else {"Authorization": "Bearer " + token}
            if payload is not None:
                headers["Content-Type"] = "application/json"
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            if response.status == 401:
                raise _fail("credentials_unavailable")
            if response.status != 200:
                raise _fail("incompatible_owner")
            body = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                sock.settimeout(remaining)
                chunk = response.read1(min(65536, self.max_bytes + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > self.max_bytes:
                    raise _fail("incompatible_owner")
            result = json.loads(body, parse_constant=lambda _: None)
            if not isinstance(result, dict):
                raise _fail("incompatible_owner")
            return result
        except (OSError, http.client.HTTPException):
            raise _fail("owner_unreachable") from None
        except (ValueError, UnicodeError):
            raise _fail("incompatible_owner") from None
        finally:
            if deadline_timer is not None:
                deadline_timer.cancel()
                deadline_timer.join()
            connection.close()

    def _verify(self):
        health = self._http("GET", "/v1/health")
        if health.get("ok") is not True or health.get("service") != "soltui":
            raise _fail("incompatible_owner")

    def _call(self, name: str, *, params=None):
        # Validate identity before resolving a token. Never follow a redirect,
        # proxy environment, native host spawn, or arbitrary hostname.
        self._verify()
        body = self._http(
            "GET" if params is None else "POST",
            "/v1/" + name,
            token=self._token(),
            params=params,
        )
        expected = "list" if name == "commands" else name
        if (
            set(body) != {"ok", "command", "result", "error"}
            or body.get("ok") is not True
            or body.get("command") != expected
            or body.get("error") is not None
        ):
            raise _fail("incompatible_owner")
        return body["result"]

    def _read_commands(self):
        records = self._call("commands")
        if not isinstance(records, list) or len(records) > 2048:
            raise _fail("incompatible_owner")
        commands = {}
        for item in records:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise _fail("incompatible_owner")
            name = item["name"]
            if name not in SAFE_COMMANDS:
                continue
            if (
                name in commands
                or type(item.get("read_only")) is not bool
                or not isinstance(item.get("params"), list)
            ):
                raise _fail("incompatible_owner")
            commands[name] = item
        self._commands = commands
        for name in ("bots.overview", "council.status"):
            if (
                name not in commands
                or commands[name]["read_only"] is not True
                or commands[name]["params"]
            ):
                raise _fail("incompatible_owner")
        control = commands.get("bots.manager_control", {})
        params = control.get("params", [])
        try:
            shape = {p["name"]: (p["type"], p["required"]) for p in params}
        except (TypeError, KeyError):
            raise _fail("incompatible_owner") from None
        safe = (
            control.get("read_only") is False
            and len(params) == len(CONTROL_PARAMS)
            and shape == CONTROL_PARAMS
            and all(type(p.get("required")) is bool for p in params)
            and commands.get("bots.manager_snapshot", {}).get("read_only") is True
            and commands["bots.manager_snapshot"]["params"] == []
        )
        self._caps = Capabilities(
            inspect=True,
            delegated_controls=safe,
            reason="guarded_delegation_available" if safe else "capability_unavailable",
        )

    def capabilities(self) -> Capabilities:
        return self._caps

    def discover(self) -> Snapshot:
        self._rows, self._loaded_hash, self._caps = {}, None, Capabilities()
        try:
            self._read_commands()
            if "bots.manager_snapshot" in self._commands:
                if self._commands["bots.manager_snapshot"]["read_only"] is not True:
                    raise _fail("incompatible_owner")
                view = self._call("bots.manager_snapshot")
                if (
                    not isinstance(view, dict)
                    or type(view.get("protocol_version")) is not int
                    or view["protocol_version"] != 1
                    or not _sha(view.get("source_hash"))
                    or not isinstance(view.get("bots"), list)
                    or len(view["bots"]) > 4
                ):
                    raise _fail("incompatible_owner")
                self._loaded_hash = view["source_hash"]
                for row in view["bots"]:
                    self._observe(row, safe=True)
            else:
                overview = self._call("bots.overview")
                if (
                    not isinstance(overview, dict)
                    or not isinstance(overview.get("bots"), list)
                    or len(overview["bots"]) > 5
                ):
                    raise _fail("incompatible_owner")
                for row in overview["bots"]:
                    if not isinstance(row, dict):
                        raise _fail("incompatible_owner")
                    if row.get("bot") == "council":
                        continue
                    forward = row.get("forward") or {}
                    if not isinstance(forward, dict) or not isinstance(
                        row.get("config"), dict
                    ):
                        raise _fail("incompatible_owner")
                    self._observe(
                        {
                            "bot": row.get("bot"),
                            "asset": forward.get(
                                "asset",
                                "ALL" if row.get("bot") == "triangle" else "SOL",
                            ),
                            "session_id": forward.get("id"),
                            "config_hash": _hash(row["config"]),
                            "requested_state": "running"
                            if forward and forward.get("stopped_at") is None
                            else "stopped",
                        },
                        safe=False,
                    )
            council = self._call("council.status")
            if (
                not isinstance(council, dict)
                or type(council.get("running")) is not bool
                or not isinstance(council.get("config"), dict)
            ):
                raise _fail("incompatible_owner")
            asset = council["config"].get("asset")
            proxy = (
                council.get("fill_model")
                == "Paper: next-minute-open Coinbase OHLC proxy; Jupiter USD quote is reference only."
            )
            self._observe(
                {
                    "bot": "council",
                    "asset": asset,
                    "session_id": None,
                    "config_hash": _hash(
                        {
                            "config": council["config"],
                            "fill_model": council.get("fill_model"),
                        }
                    ),
                    "venue": "coinbase_proxy" if proxy else None,
                    "reference_price_source": "jupiter_usd_reference"
                    if council.get("price_source") == "Jupiter USD reference"
                    else None,
                    "bar_seconds": 60 if proxy else None,
                    "execution_model": "council_next_minute_open_coinbase_proxy"
                    if proxy
                    else None,
                    "requested_state": "running" if council["running"] else "stopped",
                    "running": council["running"],
                },
                safe=False,
            )
            bots = tuple(
                freeze(
                    legacy_snapshot(
                        self.installation, row, controls=self._caps.delegated_controls
                    )
                )
                for row in self._rows.values()
            )
            return Snapshot(
                "available",
                self.installation,
                bots,
                self._loaded_hash,
                tuple(sorted(self._commands)),
            )
        except ManagerError as exc:
            self._caps = Capabilities(reason=exc.code)
            self._rows = {}
            return Snapshot(exc.code, self.installation, reason=exc.code)
        except (ValueError, TypeError, KeyError, OverflowError):
            self._caps = Capabilities(reason="incompatible_owner")
            self._rows = {}
            return Snapshot(
                "incompatible_owner", self.installation, reason="incompatible_owner"
            )

    def _observe(self, row, *, safe: bool):
        if (
            not isinstance(row, dict)
            or row.get("bot") not in FAMILIES
            or row["bot"] in self._rows
            or not _session(row.get("session_id"))
            or not _sha(row.get("config_hash"))
            or (
                row.get("session_config_hash") is not None
                and not _sha(row["session_config_hash"])
            )
            or type(row.get("asset")) is not str
            or re.fullmatch(r"[A-Z0-9]{1,20}", row["asset"]) is None
            or row.get("requested_state") not in ("running", "stopped")
            or (safe and row.get("heartbeat_available") is not False)
        ):
            raise _fail("incompatible_owner")
        if safe:
            triangle = row["bot"] == "triangle"
            expected_model = (
                "recorded_bid_ask" if triangle else "recorded_1m_ohlc_replay"
            )
            if (
                row.get("venue") != "coinbase"
                or row.get("mode") != "paper"
                or row.get("armed") is not False
                or row.get("execution_model") != expected_model
                or (
                    row.get("bar_seconds") is not None
                    if triangle
                    else type(row.get("bar_seconds")) is not int
                    or row["bar_seconds"] != 60
                )
            ):
                raise _fail("incompatible_owner")
        self._rows[row["bot"]] = {
            k: row.get(k)
            for k in (
                "bot",
                "asset",
                "session_id",
                "config_hash",
                "session_config_hash",
                "requested_state",
                "running",
                "venue",
                "bar_seconds",
                "execution_model",
                "reference_price_source",
            )
        }
        self._rows[row["bot"]]["source_hash"] = (
            None if row["bot"] == "council" else self._loaded_hash
        )

    def _receipt(
        self,
        bot,
        operation,
        request_id,
        outcome,
        reason,
        *,
        session=None,
        config_hash=None,
        owner_revision=_MISSING,
    ):
        metadata = {}
        if config_hash is not None:
            metadata["config_hash"] = config_hash
        revision = self._loaded_hash if owner_revision is _MISSING else owner_revision
        if revision is not None:
            metadata["owner_revision"] = revision
        return CommandReceipt(
            schema_version=1,
            bot_id=str(
                uuid5(NAMESPACE_URL, self.installation.installation_id + ":" + bot)
            ),
            operation=operation,
            request_id=request_id,
            runtime_id=session,
            owner_id=self.installation.installation_id,
            owner_generation=None,
            config_revision=None,
            config_revision_unavailable_reason="owner_does_not_version_configurations",
            outcome=outcome,
            reason=reason,
            metadata=metadata,
        )

    def _ledger(self):
        db = None
        try:
            self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = self.home / "controls.sqlite3"
            db = sqlite3.connect(path, timeout=5, isolation_level=None)
            path.chmod(0o600)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                if db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchone():
                    raise _fail("incompatible_store")
                db.execute(
                    "CREATE TABLE requests (request_id TEXT PRIMARY KEY, identity_hash TEXT NOT NULL, fingerprint TEXT NOT NULL, body TEXT NOT NULL, binding TEXT)"
                )
                db.execute("PRAGMA user_version=2")
            elif version == 1:
                # Keep old receipts and request IDs. Their missing original
                # binding cannot be reconstructed safely from a result body;
                # replay refuses them instead of guessing or resubmitting.
                columns = [row[1] for row in db.execute("PRAGMA table_info(requests)")]
                if columns != ["request_id", "identity_hash", "fingerprint", "body"]:
                    raise _fail("incompatible_store")
                db.execute("ALTER TABLE requests ADD COLUMN binding TEXT")
                db.execute("PRAGMA user_version=2")
            elif version != 2:
                raise _fail("incompatible_store")
            db.commit()
            return db
        except (OSError, sqlite3.Error, ManagerError) as exc:
            if db is not None:
                db.close()
            if isinstance(exc, ManagerError):
                raise
            raise _fail("store_unavailable") from None

    def _binding(self, request, receipt):
        return canonical(
            {
                "schema_version": 1,
                "request": request,
                "receipt_hash": _hash(receipt.to_dict()),
            }
        )

    def _bound_receipt(self, request_id, row):
        try:
            identity_hash, fingerprint, body, raw_binding = row
            binding = json.loads(raw_binding)
            if (
                not isinstance(binding, dict)
                or set(binding) != {"schema_version", "request", "receipt_hash"}
                or type(binding["schema_version"]) is not int
                or binding["schema_version"] != 1
            ):
                raise ValueError
            request = binding["request"]
            fields = set(CONTROL_PARAMS) | {"installation_id"}
            if (
                not isinstance(request, dict)
                or set(request) != fields
                or request["request_id"] != request_id
                or type(request["installation_id"]) is not str
                or re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", request["installation_id"]
                )
                is None
                or request["bot"] not in FAMILIES
                or request["operation"] not in ("start", "stop")
                or type(request["asset"]) is not str
                or re.fullmatch(r"[A-Z0-9]{1,20}", request["asset"]) is None
                or not _session(request["expected_session"])
                or not _sha(request["expected_config_hash"])
            ):
                raise ValueError
            original_identity = _hash(
                [request["installation_id"], request["bot"], request["operation"]]
            )
            if identity_hash != original_identity or fingerprint != _hash(
                [
                    original_identity,
                    request["expected_session"],
                    request["expected_config_hash"],
                ]
            ):
                raise ValueError
            receipt = CommandReceipt.from_dict(json.loads(body))
            if (
                binding["receipt_hash"] != _hash(receipt.to_dict())
                or receipt.request_id != request_id
                or receipt.operation != request["operation"]
                or receipt.owner_id != request["installation_id"]
                or receipt.bot_id
                != str(
                    uuid5(
                        NAMESPACE_URL, request["installation_id"] + ":" + request["bot"]
                    )
                )
                or receipt.owner_generation is not None
                or receipt.config_revision is not None
                or set(receipt.metadata) - {"config_hash", "owner_revision"}
                or receipt.metadata.get("config_hash")
                != request["expected_config_hash"]
                or (
                    "owner_revision" in receipt.metadata
                    and not _sha(receipt.metadata["owner_revision"])
                )
                or not _control_semantics(
                    receipt.operation,
                    receipt.outcome,
                    receipt.reason,
                    receipt.runtime_id,
                    request["expected_session"],
                    pending=True,
                )
            ):
                raise ValueError
            return receipt
        except (ValueError, TypeError, KeyError, ManagerError):
            raise _invalid_receipt() from None

    def control(
        self,
        external_id: str,
        operation: str,
        request_id: str,
        expected_generation: int | None,
        *,
        expected_session=_MISSING,
        expected_config_hash=_MISSING,
    ) -> CommandReceipt:
        if (
            external_id not in FAMILIES
            or operation not in ("start", "stop")
            or type(request_id) is not str
        ):
            raise ManagerError(
                "invalid_input", "A valid external identity and operation are required."
            )
        try:
            if str(UUID(request_id)) != request_id:
                raise ValueError
        except ValueError:
            raise ManagerError(
                "invalid_input", "A canonical request UUID is required."
            ) from None
        if expected_generation is not None:
            return self._receipt(
                external_id,
                operation,
                request_id,
                "failed",
                "generation_fencing_unavailable",
            )
        explicit = (
            expected_session is not _MISSING or expected_config_hash is not _MISSING
        )
        if explicit and (
            expected_session is _MISSING
            or not _session(expected_session)
            or not _sha(expected_config_hash)
        ):
            raise ManagerError(
                "invalid_input",
                "Expected session and configuration hash are required together.",
            )
        identity_hash = _hash(
            [self.installation.installation_id, external_id, operation]
        )
        db = self._ledger()
        try:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT identity_hash,fingerprint,body,binding FROM requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if previous:
                receipt = self._bound_receipt(request_id, previous)
                if previous[0] != identity_hash or (
                    explicit
                    and previous[1]
                    != _hash([identity_hash, expected_session, expected_config_hash])
                ):
                    return self._receipt(
                        external_id,
                        operation,
                        request_id,
                        "failed",
                        "request_id_conflict",
                    )
                # Persisted pending means the process may have died after submit.
                # Read reconciliation can update observations, never resubmit.
                if receipt.outcome in ("pending", "unknown"):
                    self.discover()
                    return self._receipt(
                        external_id,
                        operation,
                        request_id,
                        "unknown",
                        "outcome_unknown",
                        session=receipt.runtime_id,
                        config_hash=receipt.metadata.get("config_hash"),
                        owner_revision=receipt.metadata.get("owner_revision")
                        if receipt.outcome == "unknown"
                        else None,
                    )
                return receipt
            if not self._rows:
                self.discover()
            if not self._caps.delegated_controls or external_id == "council":
                return self._receipt(
                    external_id,
                    operation,
                    request_id,
                    "failed",
                    "capability_unavailable",
                )
            row = self._rows.get(external_id)
            if row is None:
                return self._receipt(
                    external_id, operation, request_id, "failed", "bot_not_found"
                )
            session = expected_session if explicit else row["session_id"]
            config_hash = expected_config_hash if explicit else row["config_hash"]
            params = {
                "bot": external_id,
                "operation": operation,
                "request_id": request_id,
                "asset": row["asset"],
                "expected_session": session,
                "expected_config_hash": config_hash,
            }
            request_binding = {
                **params,
                "installation_id": self.installation.installation_id,
            }
            fingerprint = _hash([identity_hash, session, config_hash])
            pending = self._receipt(
                external_id,
                operation,
                request_id,
                "pending",
                "submission_pending",
                session=session,
                config_hash=config_hash,
                owner_revision=None,
            )
            db.execute(
                "INSERT INTO requests VALUES (?,?,?,?,?)",
                (
                    request_id,
                    identity_hash,
                    fingerprint,
                    canonical(pending.to_dict()),
                    self._binding(request_binding, pending),
                ),
            )
            db.commit()
            # Intent must be on durable storage before any POST. A stale owner
            # observation is checked atomically by the owner; no unsafe fallback.
            response_revision = None
            try:
                result = self._call("bots.manager_control", params=params)
                if (
                    not isinstance(result, dict)
                    or type(result.get("protocol_version")) is not int
                    or result["protocol_version"] != 1
                    or result.get("request_id") != request_id
                    or result.get("bot") != external_id
                    or result.get("operation") != operation
                    or result.get("config_hash") != config_hash
                    or not _session(result.get("session_id"))
                    or not _sha(result.get("source_hash"))
                ):
                    raise _fail("incompatible_owner")
                response_revision = result["source_hash"]
                if not _control_semantics(
                    operation,
                    result.get("outcome"),
                    result.get("reason"),
                    result.get("session_id"),
                    session,
                ):
                    raise _fail("incompatible_owner")
                receipt = self._receipt(
                    external_id,
                    operation,
                    request_id,
                    result["outcome"],
                    result["reason"],
                    session=result.get("session_id"),
                    config_hash=config_hash,
                    owner_revision=response_revision,
                )
            except (ManagerError, ValueError, TypeError, KeyError):
                self.discover()
                receipt = self._receipt(
                    external_id,
                    operation,
                    request_id,
                    "unknown",
                    "outcome_unknown",
                    session=session,
                    config_hash=config_hash,
                    owner_revision=response_revision,
                )
            db.execute(
                "UPDATE requests SET body=?,binding=? WHERE request_id=?",
                (
                    canonical(receipt.to_dict()),
                    self._binding(request_binding, receipt),
                    request_id,
                ),
            )
            return receipt
        except (sqlite3.Error, OSError, ValueError, TypeError):
            raise _fail("store_unavailable") from None
        finally:
            if db.in_transaction:
                db.rollback()
            db.close()
