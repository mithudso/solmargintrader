# Strategy cards

One file per strategy or signal. Each card is self-contained: the equations, the code
pointer, the reasoning, the failure modes, the caveats, the measured results, and the
**machine-readable parameters with defaults already set** — enough for a person to edit
or an agent to run without reading anything else.

Cards are meant to be **edited, added, swapped, archived and shared**. Adding one is
dropping in a `.md` file; archiving one is `git mv` to wherever you keep archives;
sharing one is sending a file.

```bash
# what exists, and what each card needs to run
python3 -m backtester.core.strategy_cards
```

That command is the index. There is deliberately no committed table here, because a
committed table drifts the moment someone adds a card.

## Anatomy

```markdown
---
id: macd
name: MACD Crossover
kind: exposure-strategy
status: measured
family: trend
summary: one line
registry_key: macd
runner: backtester.cli
warmup_bars: 53
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  fast: {default: 12, type: int, desc: "fast EMA span"}
presets:
  short: {fast: 6, slow: 13, signal: 5}
---

# Body: equations, reasoning, limitations, caveats, how to run
```

**Note there are no trailing `#` comments above.** A full-line comment is fine, but
`warmup_bars: 53  # must match` parses as the *string* `"53  # must match"`, so the
loader raises rather than accept it. The fields mean:

| Field | Rule |
|---|---|
| `id` | stable slug; **must equal the filename stem** |
| `kind` | `exposure-strategy` or `ladder` |
| `status` | `measured` or `spec-only` |
| `family` | must match `FAMILY[]` in `core/strategies/__init__.py` |
| `registry_key` | `null` unless the strategy is in `REGISTRY`; two cards may not claim one key |
| `runner` | `backtester.cli`, `backtester.gridcli`, or `null` for spec-only |
| `warmup_bars` | must match the instance's `warmup_bars()` |
| `evaluation` | how any number in the body was produced; required on `measured` cards |
| `params` | each entry needs **either** `default:` **or** `required: true`, never both. `type:` is enforced against the default |
| `presets` | per-horizon overrides; may only name declared params, and layer over the defaults |

The frontmatter is a **strict YAML subset** parsed by `core/strategy_cards.py` — no
`pyyaml`, because `requirements.txt` deliberately excludes it. Scalars, flow sequences
(`[a, b]`), flow mappings (`{a: 1}`) and one level of block mapping are supported.
Block sequences (`- item`) and deeper nesting are **refused**, loudly. A card that
supplies numbers to a backtest is the wrong place for a parser that guesses.

## Using a card

```python
from backtester.core import strategy_cards as sc

cards = sc.load_all()
card = cards["macd"]

card.defaults()          # {'fast': 12, 'slow': 26, 'signal': 9}
card.required_params()   # [] here; ['lower', 'rungs', ...] on ladder_grid
card.preset("short")     # defaults, with the short-horizon overrides layered on top

strategy = sc.build_from_card(card, horizon="short")
strategy = sc.build_from_card(card, fast=8)          # overrides beat the preset

sc.implementable_today(cards)   # spec-only cards needing no new data source
```

## What the tests guarantee

Prose in a card can be wrong and no test will catch it. **Numbers cannot.**
`backtester/tests/test_strategy_cards.py` enforces:

- every card parses, and its `id` matches its filename;
- **both directions of registry drift** — every `REGISTRY` strategy has a card, and every
  card's `registry_key` still exists;
- every declared default equals the constructor's actual default — and a parameter with
  no default in the code must be marked `required: true` rather than given an invented
  one, which is checked for the ladder card against `GridConfig` directly since it has no
  registry key to compare against;
- `warmup_bars` and `family` match the code;
- every card's presets agree with `research/sweep.py`, so the card documents the same
  experiment the sweep runs;
- every buildable card constructs *and completes a backtest*;
- spec-only cards refuse to build and say what data they need.

Those checks are the reason to trust the frontmatter. If you edit a default in a card
without editing the code, the suite fails — which is the point.

## Reading the measured numbers

Every `measured` card carries `evaluation: single-split-70-30`, and every one of them
repeats the same caveat, because it matters more than any individual figure: **that split
lands within one bar of the highest close in the series**, separating a bull market from a
bear leg. In-sample rank did not predict out-of-sample rank — the medium-horizon Spearman
correlation was **-0.419**, actively inverted.

Across the whole sweep, 45 of 311 rankable configurations (14%) had a positive
out-of-sample Sharpe and 28 (9%) made money. The evidence floor is 10 out-of-sample
trades; below that a row is listed, never ranked.

Treat those numbers as evidence about **one regime transition**, not as performance
estimates. When a CPCV evaluation supersedes them, change `evaluation:` and the numbers
together.

## Two things called "grid"

- **`grid.md`** — an exposure staircase off a rolling SMA anchor. A `Strategy`, filled at
  bar boundaries. It never captures a rung width.
- **`ladder_grid.md`** — the ladder of resting limit orders with paired exits that the
  Chrome extension actually trades, simulated by `core/gridsim.py`.

They share a name and almost nothing else. Conflating them puts a wrong number under the
live strategy.

## Adding a card

1. Copy the nearest existing card.
2. Set `id` to the filename stem.
3. If it is implemented, set `registry_key`, `runner`, `warmup_bars` and `family` to match
   the code — the tests check all four.
4. If it is not, set `status: spec-only`, leave `registry_key` and `runner` null, and name
   the data gap in `data_required` with `data_available: false`.
5. Run `python3 -m unittest backtester.tests.test_strategy_cards`.
