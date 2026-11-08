---
id: event_driven
name: Event-Driven Trading
kind: exposure-strategy
status: spec-only
family: event
summary: Trade around scheduled or news events (listings, unlocks, forks, macro prints). Spec-only: needs a dated event feed.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [event-calendar]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  window_bars: {default: 24, type: int, desc: "bars held around the event"}
presets: {}
---
# Event-Driven Trading

## What it is
The guides describe event-driven trading as positioning for, or reacting to, news and scheduled events.

## What it looks for
An abnormal return in a window around a dated event, relative to the asset's normal variance.

## Equation
```
AR_t  = r_t - E[r_t]                     abnormal return
CAR   = sum of AR over [event - a, event + b]
signal = sign(CAR_prior_events) if |CAR| exceeds k * sigma
```

## Implementation
None. `trigger_trade` is the nearest existing card, but it trades price-pattern triggers mined from the asset's own history, not external events. An event study needs a dated, timestamp-accurate event list, and a feed that knows an event only after the fact leaks the future into the test.

## Works when
Events are scheduled, public in advance and move price on the surprise component, not the announcement.

## Fails when
The event is anticipated and priced in, or the feed's timestamp is later than when the market learned of it (lookahead).

## Pairs with
`trigger_trade`, once an event feed supplies the trigger.

## Measured on SOL
Not measured. No code exists for this card.

## Likelihood of success: very-low

*Basis: a-priori. No event data, and the dominant failure (late timestamps) is a lookahead bug the test would not reveal.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
No runner. Needs an event calendar data source first.
```
