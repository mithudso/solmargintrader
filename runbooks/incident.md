# Incident: wrong order, ambiguous submit or unexpected liquidity action

## Preconditions

Identify the execution component before acting. Record observed intent/order ids or
transaction hashes without copying keys, passphrases or API headers. Keep local journals
and the liquidity ledger; deleting evidence makes reconciliation harder.

## Actions

For the extension, from its directory:

```bash
node tools/cli.js kill
node tools/cli.js status
node tools/cli.js data
```

The command registry is the source of truth for command arguments. The kill command
stops new work; inspect venue state before assuming every cancel or submit succeeded.
An `unknown` intent remains occupied until a deliberate resolution with evidence.

For the liquidity service, from the repository root:

```bash
liquidity/scripts/aero-lp-service kill
liquidity/scripts/aero-lp-service status
liquidity/scripts/aero-lp-service logs
```

The KILL flag prevents new on-chain action inside the daemon's control flow. An already
broadcast transaction can still mine. Retain receipt/transaction hashes and partial
sequence state; do not infer failure from a local timeout.

## Verification

Confirm the component reports stopped/disarmed/kill state, then reconcile against the
venue or chain through the documented read-only commands. A local process exit, a
ledger row or a simulation result alone does not prove venue/chain state.

## Escalation

If the outcome remains ambiguous, leave the component killed and record the exact
unknown state in `memory.md`. See `docs/known-issues.md`, `extension/README.md` and
`liquidity/README.md`. Never raise risk caps to work around a failure.
