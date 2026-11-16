"""Bounded bridge to pinned SDK builders and the checked official service."""

from __future__ import annotations

import json
from pathlib import Path

from oracle_leverage.cli import MAX_INPUT, AdapterError, _clean_json, _timeout, run_json

APPROVED_NODE = Path("/opt/homebrew/bin/node")
BRIDGE_SCRIPT = Path(__file__).resolve().parent / "sdk/bridge.mjs"
ACTIONS = frozenset(
    {
        "status",
        "build-open",
        "build-close",
        "simulate",
        "service-markets",
        "service-positions",
        "service-build-open",
        "service-inspect-open",
        "service-build-close",
        "service-signed",
        "service-execute",
        "service-request",
    }
)


class SDKBridge:
    def __init__(self, binary="node", script=BRIDGE_SCRIPT, timeout=20):
        if str(binary) not in ("node", str(APPROVED_NODE)):
            raise AdapterError("unapproved_node_binary")
        if Path(script).resolve() != BRIDGE_SCRIPT:
            raise AdapterError("unapproved_sdk_bridge_script")
        self.binary = str(APPROVED_NODE)
        self.script = BRIDGE_SCRIPT
        self.timeout = _timeout(timeout)

    def call(self, payload):
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("action"), str)
            or payload["action"] not in ACTIONS
        ):
            raise AdapterError("unsupported_sdk_action")
        if not self.script.is_file():
            raise AdapterError("sdk_bridge_missing")
        try:
            _clean_json(payload, refuse_secrets=True)
            body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
        except (TypeError, ValueError, RecursionError):
            raise AdapterError("invalid_or_secret_sdk_payload") from None
        if len(body) > MAX_INPUT:
            raise AdapterError("process_input_limit")
        transmitting = payload["action"] == "service-execute"
        result = run_json(
            [self.binary, str(self.script)],
            timeout=self.timeout,
            payload=body,
            ambiguous=transmitting,
        )
        if not isinstance(result, dict):
            raise AdapterError("invalid_sdk_result", ambiguous=transmitting)
        return result
