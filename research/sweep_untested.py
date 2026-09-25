"""Finds and sweeps untested strategies and configurations.

Identifies strategies in the REGISTRY that do not have baseline parameters in `research/sweep.py`
or runs new configurations for existing strategies to compute profitability metrics like Sharpe,
Kelly, and Drawdown.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.strategies import REGISTRY
from research.sweep import HORIZONS, load_horizon, walk_forward, Row, fmt_table

def main() -> int:
    # 1. Identify untested strategies in the REGISTRY
    tested_short = set(HORIZONS["short"]["params"].keys())
    tested_medium = set(HORIZONS["medium"]["params"].keys())
    tested_long = set(HORIZONS["long"]["params"].keys())
    
    all_tested = tested_short | tested_medium | tested_long
    untested_names = [name for name in REGISTRY if name not in all_tested]
    
    print("Untested strategies identified:", untested_names)
    
    # Example parameter grid for untested strategies
    # We would need to define default parameters for them. For now, we will
    # assume they can be instantiated with default kwargs if we just call them,
    # or we provide some dummy defaults.
    
    # 2. Sweep untested configurations
    horizon = "medium"
    arrays, cfg = load_horizon(horizon)
    
    rows = []
    
    # Test new configurations for existing strategies
    # Example: Kelly optimization testing
    print(f"\nSweeping new configurations for horizon: {horizon}...")
    
    # Let's test a very tight RSI strategy as an "untested config"
    test_configs = [
        ("rsi", {"period": 5, "oversold": 20.0, "exit_level": 70.0}),
        ("macd", {"fast": 5, "slow": 15, "signal": 5}),
        ("bb_reversion", {"window": 10, "num_std": 2.5})
    ]
    
    # Add any fully untested strategies with empty kwargs
    for name in untested_names:
        test_configs.append((name, {}))
        
    for name, params in test_configs:
        try:
            from backtester.core.strategies import build
            full, ins, oos = walk_forward(lambda n=name, q=params: build(n, **q), arrays, cfg)
            
            rows.append(
                Row(
                    label=f"untested_{name}",
                    kind="single",
                    horizon=horizon,
                    families="untested",
                    mode="-",
                    full=full,
                    in_sample=ins,
                    out_sample=oos,
                    members=[name],
                )
            )
        except Exception as e:
            print(f"Skipping {name} due to error: {e}")
            
    # 3. Output results
    if rows:
        print("\nResults for Untested Configurations:")
        print(fmt_table(rows))
        
        # Save to TOP5-RECOMMENDATION for the UI to pick up
        best_row = sorted([r for r in rows if r.rankable], key=lambda r: r.oos_sharpe, reverse=True)
        if best_row:
            best = best_row[0]
            print(f"\nBest untested strategy found: {best.label} (OOS Sharpe: {best.oos_sharpe:.3f})")
            
            # Write to a file for the UI to consume
            reco_file = REPO / "research" / "TOP_UNTESTED_RECOMMENDATION.json"
            import json
            reco_file.write_text(json.dumps({
                "strategy": best.members[0],
                "horizon": horizon,
                "sharpe": best.oos_sharpe,
                "max_drawdown": best.out_sample.max_drawdown if best.out_sample else 0
            }))
            
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
