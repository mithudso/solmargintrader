---
id: social_sentiment
name: Social / Dev-Activity Sentiment
kind: exposure-strategy
status: spec-only
family: alt-data
summary: Documented alpha horizon of 1-2 days with fast decay; bot noise is the principal difficulty.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [social-sentiment-feed]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  window: {default: 48, type: int, desc: "bars over which to aggregate sentiment"}
  decay_hours: {default: 36, type: int, desc: "assumed alpha half-life in hours"}
presets: {}
---
# Social / Dev-Activity Sentiment

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #42.

## Equation
```
score_t = weighted mean sentiment over window, decayed
```

## Why it might work
Social-sentiment alpha is documented with horizons of **1–2 days and fast decay**, which
is short enough to be tradeable and long enough to be measurable on hourly bars.

## What implementing it would take
A feed, plus classification. The classification is the hard part.

## Caveats
**Bot noise and sarcasm are the documented principal difficulties**, and crypto social
data is close to the adversarial worst case: much of the volume is manufactured
precisely to move the metric this signal reads. A sentiment signal on paid promotion is
a signal about marketing budgets.

## Likelihood of success: very-low

*Basis: a-priori — never run here, so this is a judgement about the mechanism and
the literature, not a measurement. There is no 'high' rating in this scheme: across
311 rankable configurations measured in this repo, 14% had a positive out-of-sample
Sharpe and 9% made money.*

A documented 1-2 day alpha horizon is short enough to trade and long enough to
measure, so the mechanism is plausible. Crypto social data is close to the
adversarial worst case though: much of the volume is manufactured precisely to move
the metric this signal reads, which makes a sentiment signal on paid promotion a
signal about marketing budgets.

## Data gap
**No sentiment feed.**
