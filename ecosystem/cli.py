"""Installable control surface for the paper ecosystem supervisor."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from . import runner


def default_home() -> Path:
    return Path.home() / ".local/share/solmargintrader/ecosystem-paper-v2"


def emit(value: dict) -> None:
    print(
        json.dumps({"schema_version": 1, **value}, sort_keys=True, allow_nan=False),
        flush=True,
    )


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print("Invalid ecosystem arguments.", file=sys.stderr)
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("start", "status", "stop", "registrations", "telemetry", "supervise"),
        nargs="?",
        default="start",
    )
    parser.add_argument("--home", type=Path, default=default_home())
    parser.add_argument("--coins", nargs="+")
    parser.add_argument("--intervals", nargs="+")
    parser.add_argument("--horizons", nargs="+")
    parser.add_argument("--strategies", nargs="+")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--offline", action="store_true", default=None)
    parser.add_argument("--no-recorder", action="store_true", default=None)
    parser.add_argument("--manager-home", type=Path)
    parser.add_argument(
        "--research-min-confidence",
        type=float,
        help="Frozen paper simulation gate (0 to 1); default 0 scores raw signals with costs.",
    )
    parser.add_argument("--after", type=int, default=0)
    parser.add_argument("--cursor", default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--token", help=argparse.SUPPRESS)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    home = args.home.expanduser().absolute()
    try:
        existing = runner.load(home).get("config", {})
        manager_home = args.manager_home
        if manager_home is None and existing.get("manager_home"):
            manager_home = Path(existing["manager_home"])
        disabled_ui = {"running": False, "url": None, "reason": "embedded_ui_disabled"}
        if args.command == "status":
            from .ui_service import status as ui_status

            data = runner.status(home)
            if data.get("ui_url"):
                data["recorded_ui_url"] = data["ui_url"]
            interface = ui_status(home, manager_home)
            data.update(
                home=str(home),
                control_server=interface,
                ui_url=interface.get("url") if interface.get("running") else None,
            )
            emit({"ok": True, "data": data})
        elif args.command == "stop":
            emit({"ok": True, "data": runner.stop(home)})
        elif args.command == "registrations":
            from .registration import read_registrations

            emit(
                {
                    "ok": True,
                    "data": read_registrations(
                        home, limit=args.limit, after=args.cursor
                    ),
                }
            )
        elif args.command == "telemetry":
            from .telemetry import report

            emit(
                {
                    "ok": True,
                    "data": report(
                        home, args.manager_home, after=args.after, limit=args.limit
                    ),
                }
            )
        elif args.command == "supervise":
            try:
                return runner.supervise(home, args.token)
            except Exception:  # noqa: BLE001 - fixed public failure, never echo upstream content
                try:
                    with runner.lock(home):
                        state = runner.load(home)
                        if state.get("supervisor_token") == args.token:
                            state.update(
                                phase="failed",
                                error="supervisor_failed",
                                failed_at=time.time(),
                            )
                            if state.get("batch_id"):
                                from soltui import f5_batch

                                try:
                                    f5_batch.stop(
                                        state["batch_id"], root=home / "batches"
                                    )
                                    state["owned_batch_stop_requested"] = True
                                except (OSError, RuntimeError, ValueError):
                                    state["owned_batch_may_still_be_running"] = True
                            runner.save(home / "state.json", state)
                except BlockingIOError:
                    pass  # Another generation owns the lock; its state is authoritative.
                emit({"ok": False, "error": "supervisor_failed"})
                return 3
        else:
            from .ui_service import ensure as ensure_ui

            if runner.running(home):
                interface = ensure_ui(home, manager_home) if existing.get("embedded_ui", True) else disabled_ui
                emit(
                    {
                        "ok": True,
                        "data": {
                            "status": "already_running",
                            "home": str(home),
                            "ui": interface,
                        },
                    }
                )
                return 0
            from botmanager.store import data_home

            from backtester.core.strategies import REGISTRY

            from .data import universe

            existing = runner.load(home).get("config", {})
            config = {
                "coins": args.coins or existing.get("coins") or list(universe()),
                "intervals": args.intervals or existing.get("intervals") or ["1d"],
                "horizons": args.horizons or existing.get("horizons") or ["medium"],
                "strategies": args.strategies
                or existing.get("strategies")
                or sorted(REGISTRY),
                "start": args.start or existing.get("start") or "2025-01-01",
                "end": args.end
                or existing.get("end")
                or datetime.now(UTC).date().isoformat(),
                "offline": existing.get("offline", False)
                if args.offline is None
                else args.offline,
                "manager_home": str(args.manager_home.expanduser().absolute())
                if args.manager_home
                else existing.get("manager_home", str(data_home())),
                "recorder": existing.get("recorder", True)
                if args.no_recorder is None
                else not args.no_recorder,
                "research_min_confidence": args.research_min_confidence
                if args.research_min_confidence is not None
                else existing.get("research_min_confidence", 0.0),
                "research_capital": existing.get("research_capital", 10000.0),
                "swap_provider": existing.get("swap_provider", "reference"),
                "cost_model": existing.get("cost_model"),
                "embedded_ui": existing.get("embedded_ui", True),
            }
            runner.plan(home, **config)
            interface = ensure_ui(home, Path(config["manager_home"])) if config["embedded_ui"] else disabled_ui
            result = runner.start(home)
            # Observe real progress, not just successful Popen.
            for _ in range(100):
                state = runner.load(home)
                if state["phase"] != "starting":
                    break
                time.sleep(0.1)
            result["phase"] = state["phase"]
            result["ui_url"] = interface.get("url")
            result["control_server"] = interface
            result["supervisor_running"] = runner.running(home)
            emit({"ok": state["phase"] != "failed", "data": result})
            return (
                3
                if state["phase"] == "failed"
                or (
                    not result["supervisor_running"]
                    and state["phase"] != "offline_prepared"
                )
                else 0
            )
        return 0
    except (OSError, RuntimeError, ValueError, TypeError):
        emit({"ok": False, "error": "ecosystem_operation_failed"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
