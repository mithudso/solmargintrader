# Paper ecosystem control room 0.2.1

The headless service coordinates the existing F5 Backtester, prospective forward
trials, per-instrument Oracle archives and Bot Manager. Its independent local
control room remains available when a pipeline stops. It provides scoped action
buttons, configuration launches, stage progress, per-coin costed paper results,
versioned P&L recording and voter policies, source-linked documentation and an
isolated manual Jupiter swap page.

Run `python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py start`
from a clean source checkout, or use the installed `solecosystem` and
`solecosystem-ui` commands. Setup verifies
five installed packages, both strategy catalogs and actual MCP transport. Existing
completed environments stay immutable; new releases use a new versioned environment.

Release 0.2.1 uses `/Users/mitch/.venvs/solecosystem-0.2.1` and the primary home
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2`. It pins Bot Manager
0.4.0, Oracle 0.2.1 and the headless research runtime 0.1.2 over Backtester 0.1.1.
The `legacy-v1` view preserves the still-running V1 owner and its native evidence;
the new runtime must not resume that frozen F5 plan or relabel its Oracle policy.

All automated research and manager controls remain paper/disarmed. Oracle has no
order path. Forward P&L uses source-resolved, non-overlapping virtual trials with
costs already included. Missing outcomes, incomplete economics or disabled
recording periods do not establish profitability. Each trial has independent
configured capital, not a shared portfolio allocation.

Market-data venue and intended swap provider are separate. A configured Jupiter
cost scenario is not a verified executable quote or certified historical spot
execution model. Manual wallet swaps use Jupiter's separate browser interface;
no server key, signing or submission method is exposed.

The owner approved **0.5% = 50 bps** as the manual page's default referral fee
and the default referral assumption for new Jupiter paper scenarios. Earlier
explicit cost profiles, including 10 bps cohorts, remain frozen. A supported
configuration does not establish on-chain referral eligibility or funded-swap
readiness. Loading Jupiter still requires a manual click, and the browser wallet
must approve each action.

This fee release replaces only the independent control UI generation from a new
environment. Existing V1 and V2 pipeline owners, archives and economic settings
remain associated with their original installed versions.

See `/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-CONTROL-ROOM.md`,
`/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-BOOTSTRAP.md`,
`/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-WIKI.md` and
`/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-SWAPS.md` for operating contracts,
limits, exact commands and evidence. The packaged wiki provides all component
documentation with original file locations and content hashes.
