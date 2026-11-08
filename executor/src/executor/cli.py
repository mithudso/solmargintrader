"""Command line: `executor quote|swap|status|journal|kill|resume|gates|reconcile|list|call|api`.

The CLI prints the registry envelope exactly as the HTTP API returns it (same serializer, byte-identical), and exits
0 when `ok` is true, 1 otherwise, 2 for a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import registry


def _emit(env: dict[str, Any]) -> int:
    sys.stdout.write(registry.dumps(env) + "\n")
    return 0 if env["ok"] else 1


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="executor", description="Guarded Solana spot-swap executor (dry-run by default)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("quote", help="best price, with an independent price reference")
    q.add_argument("--from", dest="from_", required=True)
    q.add_argument("--to", required=True)
    q.add_argument("--amount", required=True)
    q.add_argument("--to-chain", dest="to_chain")
    q.add_argument("--slippage-bps", dest="slippage_bps", type=int)

    s = sub.add_parser("swap", help="build, verify, simulate; send only with --live and config mode = live")
    s.add_argument("--from", dest="from_", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--amount", required=True)
    s.add_argument("--strategy")
    s.add_argument("--live", action="store_true")
    s.add_argument("--exit", dest="exit_", action="store_true")
    s.add_argument("--reason")
    s.add_argument("--slippage-bps", dest="slippage_bps", type=int)

    sub.add_parser("status")
    j = sub.add_parser("journal")
    j.add_argument("--limit", type=int)
    j.add_argument("--strategy")
    k = sub.add_parser("kill")
    k.add_argument("--reason")
    r = sub.add_parser("resume", help="remove the KILL file (needs --confirm)")
    r.add_argument("--confirm", action="store_true")
    g = sub.add_parser("gates", help="status | record-research")
    gs = g.add_subparsers(dest="gate_cmd")
    gst = gs.add_parser("status")
    gst.add_argument("--strategy", required=True)
    gr = gs.add_parser("record-research")
    gr.add_argument("--strategy", required=True)
    gr.add_argument("--result", required=True, choices=["pass", "fail"])
    gr.add_argument("--source", required=True)
    gr.add_argument("--note")
    g.add_argument("--strategy")
    sub.add_parser("reconcile")
    sub.add_parser("list")
    c = sub.add_parser("call", help="generic: call <name> [--json '{...}']")
    c.add_argument("name")
    c.add_argument("--json", dest="json_")
    a = sub.add_parser("api", help="serve the loopback HTTP API")
    a.add_argument("--port", type=int)
    return ap


def _params(ns: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    def pick(*names: str) -> dict[str, Any]:
        out = {}
        for n in names:
            v = getattr(ns, n, None)
            if v is not None and v is not False:
                out[n.rstrip("_")] = v
        return out

    if ns.cmd == "quote":
        return "quote", pick("from_", "to", "amount", "to_chain", "slippage_bps")
    if ns.cmd == "swap":
        return "swap", pick("from_", "to", "amount", "strategy", "live", "exit_", "reason", "slippage_bps")
    if ns.cmd == "journal":
        return "journal", pick("limit", "strategy")
    if ns.cmd == "kill":
        return "kill", pick("reason")
    if ns.cmd == "resume":
        return "resume", {"confirm": True} if ns.confirm else {}
    if ns.cmd == "gates":
        if ns.gate_cmd == "record-research":
            return "gates.record_research", pick("strategy", "result", "source", "note")
        return "gates", {"strategy": getattr(ns, "strategy", None)} if getattr(ns, "strategy", None) else {}
    return ns.cmd, {}


def main(argv: list[str] | None = None) -> int:
    ns = _parser().parse_args(argv)
    if ns.cmd == "list":
        return _emit(registry.dispatch("list", {}, surface="cli"))
    if ns.cmd == "api":
        from . import api

        return api.main(["--port", str(ns.port)] if ns.port else [])
    if ns.cmd == "call":
        try:
            params = json.loads(ns.json_) if ns.json_ else {}
        except ValueError:
            return _emit(registry.error_envelope(ns.name, "bad_params", "--json is not valid JSON"))
        return _emit(registry.dispatch(ns.name, params, surface="cli"))
    name, params = _params(ns)
    return _emit(registry.dispatch(name, params, surface="cli"))


if __name__ == "__main__":
    raise SystemExit(main())
