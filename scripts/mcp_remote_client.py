#!/usr/bin/env python3
"""File-backed MCP authentication and an SDK stdio-to-HTTPS transport bridge.

The headers command is consumed by native MCP clients, never a user-facing log.
The bridge supports desktop clients that only launch stdio servers.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit

__version__ = "1.0.0"


class ConfigurationError(Exception):
    """A safe-to-display configuration error without credential contents."""


def authorization_headers(token_file: Path) -> dict[str, str]:
    """Read only a small, regular, private credential owned by this user."""
    try:
        descriptor = os.open(token_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ConfigurationError("MCP credential must be a regular file owned by this user.")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise ConfigurationError("MCP credential permissions must exclude other users.")
            raw = stream.read(4097)
    except OSError:
        raise ConfigurationError("MCP credential file cannot be read safely.") from None
    try:
        token = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        raise ConfigurationError("MCP credential is invalid.") from None
    if len(raw) > 4096 or not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ConfigurationError("MCP credential is invalid.")
    return {"Authorization": "Bearer " + token}


def validate_endpoint(endpoint: str) -> None:
    """Do not send credentials over cleartext or put them into a URL."""
    try:
        parsed = urlsplit(endpoint)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ConfigurationError("MCP endpoint must be HTTPS without user information, query or fragment.")


async def bridge(endpoint: str, headers: dict[str, str]) -> None:
    """Forward SDK messages in both directions, including notifications."""
    import anyio
    import httpx2
    from mcp.client.streamable_http import streamable_http_client
    from mcp.server.stdio import stdio_server

    # Do not let library diagnostics emit request details into a client's log.
    logging.disable(logging.CRITICAL)
    async with (
        httpx2.AsyncClient(
            headers=headers,
            timeout=httpx2.Timeout(30, read=300),
            trust_env=False,
        ) as http_client,
        streamable_http_client(
            endpoint, http_client=http_client, terminate_on_close=False
        ) as (remote_read, remote_write),
        stdio_server() as (local_read, local_write),
    ):
        try:
            async with anyio.create_task_group() as group:
                async def forward(source, destination) -> None:
                    try:
                        async for message in source:
                            if isinstance(message, Exception):
                                # Exceptions are an SDK transport message, not invalid input types.
                                raise RuntimeError("MCP transport failed.") from None  # noqa: TRY004
                            await destination.send(message)
                    finally:
                        group.cancel_scope.cancel()

                group.start_soon(forward, remote_read, local_write)
                await forward(local_read, remote_write)
        finally:
            await local_write.aclose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("headers", "bridge"))
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--url")
    args = parser.parse_args(argv)
    try:
        if args.mode == "bridge":
            validate_endpoint(args.url or "")
        headers = authorization_headers(args.token_file)
        if args.mode == "headers":
            print(json.dumps(headers))
        else:
            import anyio

            anyio.run(bridge, args.url, headers)
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception:  # noqa: BLE001 - third-party transport failures must not leak credentials
        # Never echo an HTTP response, exception, traceback, or header value.
        print("MCP bridge failed; check Tailscale, endpoint and credential access.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
