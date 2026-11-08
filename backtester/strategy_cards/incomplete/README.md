## Standalone coin-test qualification

All691 source-profile cards in the expanded TradingView collection remain incomplete as standalone coin tests. Some disclose mathematical components, but no full coin-test contract or runnable implementation has been qualified. Source interpretation is a separate status. Start with the full source-card index in research/TRADINGVIEW-SCRIPT-CARDS.md.

# Incomplete TradingView research cards

Version: 1.0.0 (2026-11-08). Delta: separate incomplete source material from the active catalog.

These cards need further research before their core calculation or trading rules
can be reproduced. A name, parameter list or partial description is not an
implementation. The cards retain their captured sources and limitations.

The normal strategy-card loader excludes this directory. Source coverage checks
include it, so moving a card does not remove its provenance or inventory record.

For each card, `research/tradingview-card-readiness.json` records exact evidence,
the reason for moving it and the missing mechanics. Recover those details from
the source before moving a card back to the parent directory. Update the review
and run `python3 scripts/check_tradingview_cards.py` after changing its content.

Complete indicator specifications may remain active without order rules. They
still require an implementation before the repository can execute them; a
mathematical specification does not change `spec-only` into `implemented`.
