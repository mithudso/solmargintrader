# Solbot: create, edit, run and inspect a paper bot

Version: 1.1.0
Delta: Add the milestone 3 shared-archive workflow and four canonical reference strategies; retain the original demonstration as historical evidence.

`/Users/mitch/.local/bin/solbot` is a command-line program. Bare invocation prints help. Ordinary commands return JSON. `ok: true` confirms that command; a start receipt alone does not establish a running worker.

The manager supports saved defaults, immutable editing, independent Grid, DCA, Trend and Momentum reference-paper accounts, historical replay and prospective observations from the existing shared Oracle archive. It also diagnoses conditional Solana quote cycles. Jupiter execution certification, blind selection, learning, broader diagnostics and browser/executor integration have separate implementation and acceptance gates in the maintained handoff.

## Start a new paper bot watching the existing stream

This explicit source is /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3. Its observations come from Coinbase SOL/USD. The bot specification still targets Jupiter SOL/USDC; this reference test cannot establish executable Jupiter prices or costs. `--reference` records your consent to that distinction.

Create a draft and prepare its input. Use a new unique name:

```sh
/Users/mitch/.local/bin/solbot create grid --name paper-grid
/Users/mitch/.local/bin/solbot prepare-input paper-grid --archive shared-sol-usd --reference --output /Users/mitch/.config/solbot/paper-grid-input.json
/Users/mitch/.local/bin/solbot data-check paper-grid --descriptor /Users/mitch/.config/solbot/paper-grid-input.json
/Users/mitch/.local/bin/solbot register-input paper-grid --descriptor /Users/mitch/.config/solbot/paper-grid-input.json
```

Creation uses defaults. Preparation fixes the source policy, activation time, watermark, capital, currency and versioned cost assumptions. It starts no producer, worker or service. Existing descriptors are never overwritten. Inspect the `data-check` output: a healthy process cannot compensate for absent or stale input.

In terminal 1, request start and run the supervisor:

```sh
/Users/mitch/.local/bin/solbot start paper-grid
/Users/mitch/.local/bin/solbot daemon
```

The foreground daemon owns the workers and stays open. One supervisor manages the running requests in this home. If a compatible manager service already owns the home, use its status instead of launching another supervisor. `start` alone saves intent; it does not keep a short-lived CLI process running.

In terminal 2, inspect progress, then stop:

```sh
/Users/mitch/.local/bin/solbot status paper-grid --why
/Users/mitch/.local/bin/solbot events paper-grid --limit 100
/Users/mitch/.local/bin/solbot stop paper-grid
/Users/mitch/.local/bin/solbot status paper-grid --why
```

Expect stopped intent followed by observed stopped state and released worker ownership. Stop retains simulated positions and evidence; it does not sell them. After stopping the bots you started, press Ctrl-C in terminal 1 to close that foreground daemon. A daemon shutdown does not erase saved requests or journals.

## What the new run waits for

Prospective evidence starts after the frozen activation boundary. It excludes the partial activation minute. Each completed minute requires observed edges and sufficiently frequent samples. Warmup and a no-trade decision can be valid results.

Status separates process heartbeat, source age, evaluation progress and decision. Missing, stale, gapped or changed-policy input holds entries. Catch-up is labelled delayed replay. The existing producer owns acquisition; the manager does not start another recorder to clear a blocker.

This first prospective release has an explicit limit of 2,048 bars and 245,760 accepted samples per account. At the limit it holds with `resource_limit`, preserving inventory and cursor. Longer continuing observation belongs to the later learning milestone. Passing a fixture does not establish profitable or indefinite autonomous operation.

## Change only the values you want

All fields have defaults or an explicit resolver. Creation and editing accept only supplied changes:

```sh
/Users/mitch/.local/bin/solbot edit paper-grid --set range_pct=20
/Users/mitch/.local/bin/solbot config paper-grid --effective
/Users/mitch/.local/bin/solbot history paper-grid
/Users/mitch/.local/bin/solbot schema grid
/Users/mitch/.local/bin/solbot status paper-grid --why
```

Editing keeps the UUID, appends a saved revision and preserves unspecified values and manual pins. It never changes an active worker. Status shows saved versus active revision, pending changes and adoption blockers. A UI or concurrent writer should supply `--expected-revision N` from the version it inspected. An optional canonical UUID `--request-id` identifies a durable mutation receipt.

To adopt a staged revision explicitly:

```sh
/Users/mitch/.local/bin/solbot stop paper-grid
/Users/mitch/.local/bin/solbot status paper-grid --why
/Users/mitch/.local/bin/solbot apply paper-grid
/Users/mitch/.local/bin/solbot history paper-grid
```

Application requires a verified stopped, owner-released, zero-exposure, reconciled boundary and compatible input. It starts no worker. Exposed or uncertain runs refuse without deleting lots. The complete old run remains archived under its original configuration and evidence. A new prospective account needs a freshly prepared descriptor and explicit activation; pass that new path with `apply --descriptor` when required. Do not edit hashes, reset cursors or delete state to clear a refusal.

## Run another strategy or another independent bot

Use `dca`, `trend` or `momentum` instead of `grid`, then prepare and register a separate descriptor for the new name. Each specification has its own UUID, virtual account and runtime. Bots can share one producer without sharing positions.

```sh
/Users/mitch/.local/bin/solbot create trend --name paper-trend
/Users/mitch/.local/bin/solbot prepare-input paper-trend --archive shared-sol-usd --reference --output /Users/mitch/.config/solbot/paper-trend-input.json
/Users/mitch/.local/bin/solbot register-input paper-trend --descriptor /Users/mitch/.config/solbot/paper-trend-input.json
/Users/mitch/.local/bin/solbot start paper-trend
/Users/mitch/.local/bin/solbot status paper-trend --why
```

The existing supervisor observes the new request. The current release admits at most four desired-running bots; an extra start reports a capacity blocker. Later load/queue work must prove any broader capacity. Independent virtual capital is not reserved wallet money and must not be summed as a funded portfolio.

Arbitrage currently supports explicit directed-quote cycle diagnosis, with exact amounts, timing and cost assumptions. It has no autonomous live cycle worker. Council remains externally owned. Use `help` and `schema` for actual capabilities rather than assuming a strategy label enables execution.

## The original bot already created and run for you

`session-demo-grid`, UUID ca28be71-3b24-4473-874a-8ac97614edb8, remains in /Users/mitch/.config/solbot. Its actual historical demonstration consumed two recorded bars, reached the end of its input, then stopped and released both process locks. It produced zero fills, exposure and net P&L on 1,000 virtual USD.

Its unchanged recording covers 2026-11-08 08:21–08:23 UTC. The descriptor is /Users/mitch/.config/solbot/session-demo-input.json and command receipt is /Users/mitch/.config/solbot/session-demo-receipt.json. It is retained historical evidence; upgrading a simulator does not relabel it as a new live feed or restart it on changed economics.

```sh
/Users/mitch/.local/bin/solbot config session-demo-grid --effective
/Users/mitch/.local/bin/solbot status session-demo-grid --why
/Users/mitch/.local/bin/solbot history session-demo-grid
```

A read leaves its old schema, identity and evidence unchanged. Follow the new-bot workflow above for a current-engine observation account.

## Instructions and maintenance

The complete operating, architecture, source ownership, recovery and release guide is /Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md. The Oracle UI contract is /Users/mitch/dev/solmargintrader/docs/bot-manager-oracle-interface.md. The approved remaining milestone order is /Users/mitch/dev/solmargintrader/docs/superpowers/plans/2026-11-09-bot-manager.md.

The stable regular installation lives in /Users/mitch/.venvs/solbot. Source lives in /Users/mitch/dev/solmargintrader/botmanager. Installing source does not start a service. Upgrade compatible first-party packages together and verify the loaded code before restarting an affected owner. Preserve frozen experiment environments and take a consistent backup before a state migration.
