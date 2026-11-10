# Paper ecosystem control room 0.2.0

The headless service coordinates the existing F5 Backtester, prospective forward
trials, per-instrument Oracle archives and Bot Manager. Its independent local
control room remains available when a pipeline stops. It provides scoped action
buttons, configuration launches, stage progress, per-coin costed paper results,
versioned P&L recording and voter policies, source-linked documentation and an
isolated manual Jupiter swap page.

Run `python3 scripts/bootstrap_ecosystem.py start` from a clean source checkout,
or use the installed `solecosystem` and `solecosystem-ui` commands. Setup verifies
five installed packages, both strategy catalogs and actual MCP transport. Existing
completed environments stay immutable; new releases use a new versioned environment.

All automated research and manager controls remain paper/disarmed. Oracle has no
order path. Forward P&L uses source-resolved, non-overlapping virtual trials with
costs already included. Missing outcomes, incomplete economics or disabled
recording periods do not establish profitability. Each trial has independent
configured capital, not a shared portfolio allocation.

Market-data venue and intended swap provider are separate. A configured Jupiter
cost scenario is not a verified executable quote or certified historical spot
execution model. Manual wallet swaps use Jupiter's separate browser interface;
no server key, signing or submission method is exposed.

See `docs/ECOSYSTEM-CONTROL-ROOM.md`, `docs/ECOSYSTEM-BOOTSTRAP.md`,
`docs/ECOSYSTEM-WIKI.md` and `docs/ECOSYSTEM-SWAPS.md` for operating contracts,
limits, exact commands and evidence. The packaged wiki provides all component
documentation with original file locations and content hashes.
