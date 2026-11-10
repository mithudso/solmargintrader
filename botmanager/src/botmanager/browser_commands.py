"""Manager registry definitions for browser-owned singleton paper control."""

from __future__ import annotations

from .adapters.extension import BrowserStore, resolve_browser
from .domain import ManagerError


def browser_status(params, context):
    adapter = resolve_browser(params["identity"], home=context.home)
    if adapter is None:
        raise ManagerError("bot_not_found", "Browser identity is required.")
    return adapter.discover()


def browser_control(params, context):
    adapter = resolve_browser(params["identity"], home=context.home)
    if adapter is None:
        raise ManagerError("bot_not_found", "Browser identity is required.")
    return adapter.control(
        params["operation"],
        params["request_id"],
        expected_generation=params["expected_generation"],
        expected_config_hash=params["expected_config_hash"],
    )


def browser_receipt(params, context):
    return BrowserStore(context.home).receipt(params["request_id"])


def command_specs(command_type):
    identity = ((("identity",), {}),)
    return (
        command_type(
            "browser-status",
            "Read browser registration without starting a host.",
            browser_status,
            identity,
        ),
        command_type(
            "browser-control",
            "Queue a generation-bound paper browser-owner operation.",
            browser_control,
            identity
            + (
                (("operation",), {"choices": ("start", "stop")}),
                (("--request-id",), {"required": True}),
                (("--expected-generation",), {"type": int, "required": True}),
                (("--expected-config-hash",), {"required": True}),
            ),
        ),
        command_type(
            "browser-receipt",
            "Read a durable browser-owner operation outcome.",
            browser_receipt,
            ((("request_id",), {}),),
        ),
    )
