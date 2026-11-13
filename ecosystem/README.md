# Paper ecosystem control room 0.4.8

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

The ZEC study release uses ecosystem 0.4.4 with Bot Manager 0.7.2, Oracle 0.2.3,
research runtime 0.4.0 and Backtester 0.2.0. Its dedicated paper owner uses
`/Users/mitch/.venvs/zec-ensembles-20261110`; the existing managed UI receives
the same coherent package bundle under the owner's ZEC publication request.
The earlier `/Users/mitch/.venvs/solecosystem-0.4.2` candidate is historical.
See [the measured ZEC study](../docs/ZEC-ENSEMBLE-STUDY.md) and
[forward owner commands](../docs/ZEC-ENSEMBLES-FORWARD.md). The managed suite can maintain manager/UI availability independently of research;
see [managed operations](../docs/bot-manager-managed-suite.md).
Persistent supervision, independent heartbeat alerts and daily reports are documented in
[Oraclebot operations](../docs/ORACLEBOT-OPERATIONS.md).
The operational primary home is `/Users/mitch/.local/share/solmargintrader/ecosystem-operational-20261112`.
The older `/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2` remains an archived cohort with its original code and Oracle policy guards.
Existing 0.2.1/V1 research owners and their environments remain frozen. The new
runtime must not resume a frozen F5 plan or relabel its Oracle policy.

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
