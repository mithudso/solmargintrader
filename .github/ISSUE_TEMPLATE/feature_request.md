---
name: Feature request
about: Propose a change to a component
labels: enhancement
---

## Component and motivation

<!-- Which component, and what question can you not currently answer / what can
you not currently do? -->

## Proposal

## What would make it correct

<!-- The important part. For a strategy: what would show it is not curve-fit?
For an extension change: which rail covers the new failure mode? -->

- [ ] A new strategy comes with a `backtester/strategy_cards/<id>.md`.
- [ ] A signal-generation or fill-timing change comes with a one-bar-leak test.
- [ ] An extension change names the rail in `src/core/risk.js` that gates it.

## Scope check

- [ ] This does **not** add live-trading capability to `backtester/` (see its README's Scope section).
- [ ] This does **not** add a runtime dependency to `extension/`.
