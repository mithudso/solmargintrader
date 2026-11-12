"""Local stdio MCP views over the Oracle archive; never a submission surface."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import jsonschema
import mcp.server.stdio
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from .feeds import validate_instrument
from .guidance import guidance, readiness, veto

VERSION = "0.2.3"
RESOURCE_NAMES = {
    f"oracle://{name}": name for name in ("market", "predictions", "status")
}
EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}
ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "ok", "data", "error"],
    "properties": {
        "schema_version": {"const": 1},
        "ok": {"type": "boolean"},
        "data": {},
        "error": {"type": ["object", "null"]},
    },
    "additionalProperties": False,
}
TOOL_SCHEMAS = {
    "oracle_status": EMPTY,
    "oracle_market": EMPTY,
    "oracle_predictions": EMPTY,
    "oracle_strategies": EMPTY,
    "oracle_history": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
            "after": {"type": "integer", "minimum": 0},
        },
        "additionalProperties": False,
    },
    "oracle_guidance": {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": ["backtest", "forward", "live"]}
        },
        "additionalProperties": False,
    },
    "oracle_readiness": EMPTY,
    "oracle_veto": EMPTY,
}
DESCRIPTIONS = {
    "oracle_status": "Read Oracle archive and input status; does not start a worker.",
    "oracle_market": "Read the latest source-labelled market observation and freshness.",
    "oracle_predictions": "Read prospective strategy calls and weighted agreement, not profit probability.",
    "oracle_strategies": "List the 14 selected strategy cards and their version bindings.",
    "oracle_history": "Read paginated archived observations, forecasts and resolutions.",
    "oracle_guidance": "Route a lifecycle stage to source-bound guides and unmet prerequisites.",
    "oracle_readiness": "Inspect credential configuration and unavailable live execution gates without loading keys.",
    "oracle_veto": "Read an advisory veto for new entries; execution enforcement is unavailable.",
}


def envelope(data: Any = None, error: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "ok": error is None,
        "data": data,
        "error": None
        if error is None
        else {"code": error, "message": "Oracle request unavailable."},
    }


def encode(value: Any) -> str:
    text = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
    if len(text.encode()) > 512_000:
        raise ValueError("response too large")
    return text


class SubscriptionHub:
    """Coalesce resource changes with no unbounded event queue or cross-session state."""

    def __init__(self, *, timeout: float = 2.0) -> None:
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._sessions: dict[Any, dict[str, str | None]] = {}

    async def subscribe(self, session: Any, uri: str) -> None:
        if uri not in RESOURCE_NAMES:
            raise ValueError("unknown resource")
        async with self._lock:
            self._sessions.setdefault(session, {})[uri] = None

    async def unsubscribe(self, session: Any, uri: str) -> None:
        if uri not in RESOURCE_NAMES:
            raise ValueError("unknown resource")
        async with self._lock:
            subscriptions = self._sessions.get(session, {})
            subscriptions.pop(uri, None)
            if not subscriptions:
                self._sessions.pop(session, None)

    async def publish(self, values: dict[str, str]) -> None:
        async with self._lock:
            for session, subscriptions in list(self._sessions.items()):
                for uri in list(subscriptions):
                    digest = hashlib.sha256(values[uri].encode()).hexdigest()
                    if subscriptions[uri] == digest:
                        continue
                    try:
                        await asyncio.wait_for(
                            session.send_resource_updated(AnyUrl(uri)), self.timeout
                        )
                    except Exception as exc:  # noqa: BLE001 -- SDK transport failures must not echo request contents.
                        # A slow or dead client loses its subscriptions. It must reconnect,
                        # re-read the durable snapshot, and explicitly subscribe again.
                        self._sessions.pop(session, None)
                        logging.getLogger(__name__).warning(
                            "oracle_subscription_evicted reason=%s",
                            "timeout" if isinstance(exc, TimeoutError) else "transport_failure",
                        )
                        break
                    subscriptions[uri] = digest

    async def clear(self) -> None:
        async with self._lock:
            self._sessions.clear()


def build_server(
    engine: Any,
    *,
    manager_home: Path | None = None,
    repo: Path | None = None,
    poll_seconds: float = 0.5,
    prediction_view: Callable[[], dict] | None = None,
) -> tuple[Server, SubscriptionHub]:
    if not 0.1 <= poll_seconds <= 60:
        raise ValueError("invalid poll interval")
    hub = SubscriptionHub()

    def predictions():
        return (
            prediction_view() if prediction_view is not None else engine.predictions()
        )

    class SelectedView:
        def market(self, **kwargs):
            return engine.market(**kwargs)

        def predictions(self, **kwargs):
            return predictions()

    def resource(uri: str) -> dict:
        if uri not in RESOURCE_NAMES:
            raise ValueError("unknown resource")
        try:
            return envelope(
                predictions()
                if uri == "oracle://predictions"
                else getattr(engine, RESOURCE_NAMES[uri])()
            )
        except Exception:  # noqa: BLE001 -- Public response boundary never serializes dependency exception text.
            return envelope(error="archive_unavailable")

    async def watch() -> None:
        while True:
            values = {}
            for uri in RESOURCE_NAMES:
                try:
                    values[uri] = encode(await asyncio.to_thread(resource, uri))
                except (ValueError, TypeError, OverflowError):
                    values[uri] = encode(envelope(error="snapshot_unavailable"))
            await hub.publish(values)
            await asyncio.sleep(poll_seconds)

    @asynccontextmanager
    async def lifespan(_: Server):
        task = asyncio.create_task(watch())
        try:
            yield {}
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await hub.clear()

    server = Server("solmargintrader-oracle", version=VERSION, lifespan=lifespan)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=name,
                description=DESCRIPTIONS[name],
                inputSchema=schema,
                outputSchema=ENVELOPE_SCHEMA,
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
            for name, schema in TOOL_SCHEMAS.items()
        ]

    def tool_data(name, arguments):
        if name == "oracle_guidance":
            return guidance(**arguments, repo=repo)
        if name == "oracle_readiness":
            return readiness(engine, manager_home=manager_home)
        if name == "oracle_veto":
            return veto(SelectedView())
        if name == "oracle_predictions":
            return predictions()
        return getattr(engine, name.removeprefix("oracle_"))(**arguments)

    @server.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        try:
            if name not in TOOL_SCHEMAS:
                raise ValueError
            jsonschema.validate(arguments, TOOL_SCHEMAS[name])
        except (ValueError, jsonschema.ValidationError, jsonschema.SchemaError):
            result = envelope(error="invalid_request")
        else:
            try:
                data = await asyncio.to_thread(tool_data, name, arguments)
                result = envelope(data)
                encode(result)
            except Exception:  # noqa: BLE001 -- Public response boundary never serializes dependency exception text.
                result = envelope(error="archive_unavailable")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=encode(result))],
            structuredContent=result,
            isError=not result["ok"],
        )

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl(uri),
                name=name,
                mimeType="application/json",
                description="Read a snapshot; subscribe for invalidation notices, then read again.",
            )
            for uri, name in RESOURCE_NAMES.items()
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
        value = await asyncio.to_thread(resource, str(uri))
        try:
            text = encode(value)
        except (ValueError, TypeError, OverflowError):
            text = encode(envelope(error="snapshot_unavailable"))
        return [ReadResourceContents(text, "application/json")]

    @server.subscribe_resource()
    async def subscribe(uri: AnyUrl) -> None:
        await hub.subscribe(server.request_context.session, str(uri))

    @server.unsubscribe_resource()
    async def unsubscribe(uri: AnyUrl) -> None:
        await hub.unsubscribe(server.request_context.session, str(uri))

    return server, hub


def selection_home(
    archive: Path, instrument: str, control_home: Path | None = None
) -> Path | None:
    """Infer only the controller's exact documented archive layout."""
    archive = Path(archive).expanduser().absolute()
    instrument = validate_instrument(instrument)
    base = instrument.split("/")[0]
    if control_home is not None:
        home = Path(control_home).expanduser().absolute()
        if archive != home / "oracle" / base / "history.sqlite3":
            raise ValueError("control_home_archive_mismatch")
        return home
    if (
        archive.name == "history.sqlite3"
        and archive.parent.name == base
        and archive.parent.parent.name == "oracle"
    ):
        return archive.parent.parent.parent
    return None


def selected_prediction_view(
    engine: Any, home: Path | None, *, required: bool = False
) -> Callable[[], dict] | None:
    if home is None:
        return None

    def unavailable():
        return {
            "schema_version": 1,
            "instrument": engine.instrument,
            "status": "unavailable",
            "signal": None,
            "balance_percent": None,
            "reason": "voter_selection_unavailable",
            "tradable": False,
            "percentage_semantics": "signed_weighted_vote_balance_not_probability",
            "strategies": [],
            "selection": {"status": "unavailable"},
            "aggregate": {
                "status": "unavailable",
                "signal": None,
                "balance_percent": None,
                "included": [],
                "excluded": [],
                "reason": "voter_selection_unavailable",
            },
        }

    def selected():
        preference = home / "voters.sqlite3"
        try:
            from ecosystem.votes import report
        except ImportError:
            # A standalone Oracle need not depend on the ecosystem package.
            # A saved/explicit selection must never fall back to all voters.
            if required or preference.exists() or preference.is_symlink():
                return unavailable()
            return engine.predictions()
        try:
            return report(home, engine.instrument)
        except Exception:  # noqa: BLE001 - selection failures never expose private dependency text
            return unavailable()

    return selected


async def run(
    archive: Path,
    *,
    instrument: str = "SOL/USDC",
    manager_home: Path | None = None,
    repo: Path | None = None,
    poll_seconds: float = 0.5,
    control_home: Path | None = None,
) -> None:
    from .engine import OracleEngine

    home = selection_home(archive, instrument, control_home)
    if home is not None:
        from .reader import ReadOnlyOracle

        engine = ReadOnlyOracle(archive, instrument=instrument, archived_versions=True)
    else:
        engine = OracleEngine(archive, instrument=instrument)
    server, _ = build_server(
        engine,
        manager_home=manager_home,
        repo=repo,
        poll_seconds=poll_seconds,
        prediction_view=selected_prediction_view(
            engine, home, required=control_home is not None
        ),
    )
    capabilities = server.get_capabilities(NotificationOptions(), {})
    assert capabilities.resources is not None
    capabilities.resources.subscribe = True
    async with mcp.server.stdio.stdio_server() as (reader, writer):
        await server.run(
            reader,
            writer,
            InitializationOptions(
                server_name="solmargintrader-oracle",
                server_version=VERSION,
                capabilities=capabilities,
            ),
        )


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("invalid command arguments")


def main(argv: list[str] | None = None) -> int:
    logging.disable(logging.CRITICAL)
    parser = Parser(description="Oracle local stdio MCP server; no order capability.")
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path.home() / ".local/share/solmargintrader/oracle/history.sqlite3",
    )
    parser.add_argument("--instrument", default="SOL/USDC")
    parser.add_argument("--manager-home", type=Path)
    parser.add_argument("--control-home", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    try:
        args = parser.parse_args(argv)
        asyncio.run(
            run(
                args.archive,
                instrument=args.instrument,
                manager_home=args.manager_home,
                repo=args.repo,
                poll_seconds=args.poll_seconds,
                control_home=args.control_home,
            )
        )
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 -- CLI failure boundary suppresses dependency details.
        print("Oracle MCP server stopped or unavailable.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
