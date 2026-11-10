"""Report command definitions imported lazily by the application registry."""

from __future__ import annotations

from .reports import render_report, report_page
from .store import ManagerStore


def report_command(params, context):
    page = report_page(
        ManagerStore(context.home),
        params.get("identity"),
        run_id=params.get("run_id"),
        after=params.get("after", 0),
        limit=params.get("limit", 100),
    )
    format = params.get("format", "json")
    return {"page": page, "format": format, "rendered": render_report(page, format)}


def command_specs(command_type):
    return (
        command_type(
            "report",
            "Read attributed accounting and bounded runtime evidence.",
            report_command,
            arguments=(
                (("identity",), {}),
                (("--run-id",), {}),
                (("--after",), {"type": int, "default": 0}),
                (("--limit",), {"type": int, "default": 100}),
                (
                    ("--format",),
                    {"choices": ("human", "json", "csv"), "default": "json"},
                ),
            ),
            api_parameters=("identity", "run_id", "after", "limit", "format"),
        ),
    )
