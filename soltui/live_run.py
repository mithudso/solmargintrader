"""Live Run dashboard for SolTUI.

Loads the best configuration from TOP5-RECOMMENDATION (or untested sweep)
and provides a UI to launch the Node.js extension in dry-run mode.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from textual.widgets import Static

from backtester.core.strategies import REGISTRY
from . import top5 as top5_mod

REPO = Path(__file__).resolve().parent.parent
RECOMMENDATION_FILE = REPO / "research" / "TOP_UNTESTED_RECOMMENDATION.json"


def get_best_strategy() -> dict[str, str]:
    """Retrieve the best recommended strategy.
    
    Prefers the untested recommendation if available, otherwise falls back to the top-ranked
    from TOP5-RECOMMENDATION.
    """
    if RECOMMENDATION_FILE.exists():
        try:
            data = json.loads(RECOMMENDATION_FILE.read_text())
            if "strategy" in data:
                return {
                    "strategy": data["strategy"],
                    "source": "Untested Sweep",
                    "details": f"Horizon: {data.get('horizon', 'unknown')}, Sharpe: {data.get('sharpe', 0):.3f}"
                }
        except Exception:
            pass

    try:
        top5 = top5_mod.load_top5()
        if top5:
            best = top5[0]
            return {
                "strategy": best.label,
                "source": "TOP5-RECOMMENDATION",
                "details": f"Horizon: {best.horizon}, Rank: 1"
            }
    except top5_mod.EvidenceUnavailable:
        pass

    return {
        "strategy": "buy_and_hold",
        "source": "Fallback",
        "details": "No recommendations found. Defaulting to baseline."
    }


def spawn_dryrun(strategy_name: str, update_status: callable) -> None:
    """Spawns the Node.js dryrun tool with the selected strategy."""
    ext_dir = REPO / "extension"
    dryrun_script = ext_dir / "tools" / "dryrun.js"
    
    if not dryrun_script.exists():
        update_status("[red]Error: extension/tools/dryrun.js not found.[/]")
        return
        
    cmd = ["node", str(dryrun_script), "--strategy", strategy_name, "--ticks", "8"]
    
    update_status(f"Spawning dryrun: {' '.join(cmd)}")
    try:
        # We launch it asynchronously and detach, or run and capture output.
        # Since this is a TUI, we run it and capture the output to display.
        # We will use Popen to capture stdout/stderr non-blockingly if needed,
        # but for a simple "spawn" we can just run it.
        result = subprocess.run(
            cmd, cwd=str(ext_dir), capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            update_status(f"Dryrun finished successfully.\n[green]{result.stdout}[/]")
        else:
            update_status(f"[red]Dryrun failed (code {result.returncode}):\n{result.stderr}[/]")
    except Exception as e:
        update_status(f"[red]Failed to spawn dryrun: {e}[/]")
