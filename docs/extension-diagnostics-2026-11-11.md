# Extension caught-error diagnostics repair

Extension source version 0.6.6 bounds caught tick errors to the operation, an
allowlisted error class and an integer HTTP status from 100 through 599. The
returned `errors[].error`, diagnostic log strings and persisted `intent.error`
use this metadata. Arbitrary upstream messages, class names and response bodies
are omitted. The durable event summary already used this boundary. Metadata properties are read once, then those same values are validated and used.
Internal
preparation exceptions still propagate to their caller.

Independent review found a repeated-property-read gap; its counterexample failed
before snapshotting metadata properties and passed afterwards. The original
review and the final disposition are retained alongside the other check logs.

A synthetic credential stored in an in-memory ConfigStore reproduced the old
exposure. No owner credential was accessed. The three regression cases failed
before the repair and passed afterwards. They cover price, reconciliation and
fill-read exceptions, plus a mock submission failure whose journal remains
UNKNOWN and whose intents are not retried on a later tick. Existing price and
unknown-order tests still establish that invalid inputs block planning; their
display assertions now use the bounded operation/type diagnostic.

Validation: 437 extension unit tests passed; the eight-tick offline economics
fixture closed one round trip with simulated net $0.3492; the guarded Chrome
fixture passed 26 checks and ended disarmed. Independent loaded Chrome acceptance also passed 25/25 with a fixture native
host; 12 origin-source hashes matched this checkout, including the engine.
The optional installed-SolTUI comparison accounts for the one-check difference.
Independent final source review found no remaining Medium-or-higher findings
within this narrow patch. These checks do not establish live
order execution or an updated everyday browser installation. The source patch
does not reload production owners, alter defaults or retire existing journal
errors. Detailed before/after logs and source snapshots are under
`/Users/mitch/.local/share/solmargintrader/audits/cdo-20261111-task1423/critical-repair/`.

This is a separate Critical repair from the ongoing 767-file deep code optimizer
run, tracked by TASK-1431 under TASK-1423. It does not establish whole-repository
coverage, convergence or a clean result. The draft audit checkpoint remains
https://github.com/mithudso/solmargintrader/pull/226
