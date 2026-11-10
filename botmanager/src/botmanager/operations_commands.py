"""Registered suite operations and verified local control-room discovery."""

from __future__ import annotations

import time

from .domain import ManagerError

_UI_READY_SECONDS = 10.0
_UI_POLL_SECONDS = 0.05
_UI_PENDING_REASONS = frozenset(
    {
        "control_server_not_running",
        "control_checkpoint_pending",
        "control_start_in_progress",
        "control_server_health_unverified",
    }
)


def _ecosystem_home(context):
    from .machine_health import homes

    return homes(context.home, context.ecosystem_home)[1]


def stack_command(params, context):
    from .suite import operation

    return operation(
        params["action"], home=context.home, ecosystem_home=context.ecosystem_home
    )


def ui_command(params, context):
    try:
        from ecosystem.ui_service import status
    except ImportError as exc:
        raise ManagerError(
            "capability_unavailable",
            "The control-room package is unavailable in this installation.",
            3,
        ) from exc

    action = params.get("action", "status")
    wait_for_ui = action in ("start", "open")
    if wait_for_ui:
        from .suite import operation

        operation("start", home=context.home, ecosystem_home=context.ecosystem_home)
    selected_home = _ecosystem_home(context)
    deadline = time.monotonic() + _UI_READY_SECONDS if wait_for_ui else None
    observed = status(selected_home, context.home)
    # The suite owns startup. Its owner socket can become ready just before the
    # UI publishes its checkpoint. Poll only verified reads for transient states;
    # a wrong home/version or conflicting owner returns immediately.
    while (
        wait_for_ui
        and not observed.get("running")
        and observed.get("reason") in _UI_PENDING_REASONS
    ):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(_UI_POLL_SECONDS, remaining))
        observed = status(selected_home, context.home)
    result = {**observed, "action": action}
    if action == "open":
        import webbrowser

        # status verifies the private checkpoint, owner lock and HTTP identity.
        # A stale checkpoint or an unrelated listener never reaches the browser.
        try:
            result["opened"] = bool(
                observed.get("running")
                and observed.get("url")
                and webbrowser.open(observed["url"], new=2)
            )
        except (webbrowser.Error, OSError):
            result["opened"] = False
        if observed.get("running") and not result["opened"]:
            result["reason"] = "browser_launch_unavailable"
    return result


def health_check_command(params, context):
    from .machine_health import check

    return check(home=context.home, ecosystem_home=context.ecosystem_home)


def metrics_command(params, context):
    from .machine_health import prometheus

    return {
        "format": "prometheus",
        "rendered": prometheus(health_check_command(params, context)),
    }


def component_alerts_command(params, context):
    from .suite import alerts

    return alerts(
        home=context.home, after=params.get("after", 0), limit=params.get("limit", 100)
    )


def command_specs(command_type):
    return (
        command_type(
            "stack",
            "Manage the persistent suite monitor, reference supervisor and verified UI.",
            stack_command,
            (
                (
                    ("action",),
                    {
                        "choices": (
                            "status",
                            "start",
                            "run",
                            "stop",
                            "restart",
                            "install",
                            "uninstall",
                        )
                    },
                ),
            ),
        ),
        command_type(
            "ui",
            "Find the verified UI URL; explicitly start the suite or open its control room.",
            ui_command,
            (
                (
                    ("action",),
                    {
                        "choices": ("status", "start", "open"),
                        "nargs": "?",
                        "default": "status",
                    },
                ),
            ),
        ),
        command_type(
            "health-check",
            "Read compact component readiness and ages for graphing or alerting.",
            health_check_command,
        ),
        command_type(
            "metrics",
            "Read Prometheus component gauges as plain text; never start components.",
            metrics_command,
        ),
        command_type(
            "component-alerts",
            "Read bounded suite component failure and recovery alerts.",
            component_alerts_command,
            (
                (("--after",), {"type": int, "default": 0}),
                (("--limit",), {"type": int, "default": 100}),
            ),
        ),
    )
