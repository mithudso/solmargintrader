# ZEC GUM 25× 5m bracket sweep and walk-forward tests

The three highest-ranked eligible strategies were **Volty(10 × 1.5)**, the same Volty rule with **Z-score + RSI** confirmation, and Volty with **RSI** confirmation alone. All three lost in the added week, with no modeled liquidations. Ungated Volty was the only one of the three to make money on the continuous October 28–November 18 test. The live setup runs three independent paper accounts against public GUM prices.

## Data and selection

The suite kept the original 60,480 minute candles and added 10,080 consecutive minutes, for **70,560 candles and 1,176 observed hourly funding records**. All dates are UTC and all boundaries are 01:10. The appended candles match the seven-day capture used in the older broad Perps study. The present profiles were frozen before this suite scored those dates.

| Role | Start | End exclusive |
| --- | --- | --- |
| Indicator warmup | 2026-09-30 | 2026-10-14 |
| Development ranking, four one-week episodes | 2026-10-14 | 2026-11-11 |
| Added scoring week | 2026-11-11 | 2026-11-18 |
| Continuous test, one account per card | 2026-10-28 | 2026-11-18 |

The grid has **108 signal specifications × 56 brackets = 6,048 configurations**, all at 5m, 25× and $250 fixed target exposure on a $1,000 virtual account. TP distances are 0%, 0.35%, 0.5%, 0.75%, 1%, 1.5%, 2% and 3%. SL distances are 0%, 0.2%, 0.35%, 0.5%, 0.8%, 1.2% and 1.6%. Zero disables that bracket leg. The signal catalog spans Z-score and RSI reversion, Balance of Power, reversion votes, pressure confirmation, and Volty stops with standalone and directional filters. The earlier shape-filtered Balance of Power baseline was included.

The rank requires at least 24 development exits, at least three each week, zero modeled liquidations and zero refused entries. It sums the four net weekly returns at a constant $1,000 starting balance for each week. Ties favor the better worst week, then lower maximum weekly drawdown. One bracket per exact signal stream advances. Of 2,787 eligible rows, 87 made money in development and 16 made money in both development and the added week. The figures count overlapping parameter variants.

## Selected configurations

| Development rank and card | TP / SL | Development return sum | Added week | Added exits / liq. | Continuous 21-day test |
| --- | --- | ---: | ---: | ---: | ---: |
| [#1 Volty 10 × 1.5](zec_gum_25x_5m_card_1.md) | 0% / 0.8% | +2.63% | −2.79% | 112 / 0 | +4.75% |
| [#2 Volty 10 × 1.5 with Z-score and RSI](zec_gum_25x_5m_card_2.md) | 0% / 1.2% | +1.49% | −3.46% | 18 / 0 | −4.60% |
| [#3 Volty 10 × 1.5 with RSI](zec_gum_25x_5m_card_3.md) | 0% / 0.8% | +1.36% | −3.00% | 23 / 0 | −3.00% |

The added week cost the three $1,000 accounts **$27.93, $34.61 and $30.05**. The preceding two-week bracket adaptation also lost in the added week, returning **−2.79%, −2.11% and −0.69%**, respectively. Each card contains all five fixed episodes and three rolling two-week training → one-week test folds. The three rules share one breakout mechanism.

## Leading result by family

| Family | Signal specs | Development leader | TP / SL | Development sum | Added week |
| --- | ---: | --- | --- | ---: | ---: |
| Z-score | 15 | Z-score(20) ≤ -2.5 → ≥ 0 | 1% / 0.2% | −0.49% | −0.56% |
| RSI | 16 | RSI(21) < 30 → > 55 | 3% / 0.35% | +1.20% | −0.21% |
| Balance of Power | 11 | Balance of Power SMA(5) · shape | 1.5% / 0.5% | +1.27% | −1.15% |
| Indicator vote or confirmation | 36 | Entry confirmation · RSI(21) < 35 → > 60 + Balance of Power SMA(3) > 0 → ≤ 0 | 0.5% / 1.2% | +0.23% | −0.06% |
| Volty or gated Volty | 30 | Volty(10 × 1.5) | 0% / 0.8% | +2.63% | −2.79% |

Cash returned 0%. A single $250 fixed-notional buy-and-hold long liquidated in every weekly episode, including the added week.

## Replay and execution

Entries use completed 5m signals and the next available minute path. The existing isolated paper model floors size to GUM lot increments, uses 3.5 bps taker fee per side, 2 bps assumed slippage per side, $0.01 per side, 75 bps liquidation fee and 100 bps first-tier maintenance. It applies each observed hourly funding rate to the simulated position. Trade OHLC proxies for fills and marks. The model favors the adverse result when intraminute events cannot be ordered.

The live process reads the current ZEC GUM mark, funding and documented venue terms. It uses the same signal catalog and fixed brackets. It starts each profile flat and advances on a new closed 5m signal. Paper fills and barriers use sampled marks, so outcomes can differ from the historical minute-candle replay. It writes an isolated session manifest and a JSONL event stream. A new launch starts a new paper session. The funded TradingView webhook is a separate directional account path and cannot represent these rules and bracket exits as configured. [GUM funding contract](https://github.com/jupnet/gum-perp-sdk/blob/08bc398d78350a49ae047ecbdd3ffc6233c082d3/docs/REST_API.md#get-funding-rate-history)

## Run live with paper accounts

From the repository root, pass a fresh output directory. A bounded check uses `--once`; the foreground command continues until interrupted.

```sh
node extension/tools/zec-gum-live.mjs --once --output /tmp/zec-gum-paper-smoke
node extension/tools/zec-gum-live.mjs --output /tmp/zec-gum-paper-session
```

Expect `session.json` to bind the three profiles and `events.jsonl` to record quote observations, closed-bar decisions, paper positions, and exits.

## Reproduce the walk-forward tests

```sh
node research/scripts/perps/zec-gum-walk-forward.mjs --base /path/to/frozen-42-days.json \
  --week /path/to/frozen-added-week.json --output /path/to/new-run-directory
```

The runner writes `selection.json` before scoring the added week. The `walkForward` array in `results.json` contains the three tests. The runner also writes the matching `live.json` profile file.

| Receipt | SHA-256 |
| --- | --- |
| Original capture | `933b9f6e116d8d366d6c73ccda5ec360b30f60dbe63daa26214c3fa010c46dee` |
| Added-week capture | `0193765cb58e9550f129f77f27f066b69b4700f2d36b39d293278a2259564a7b` |
| Frozen development selection | `c6a56a3e42865111210e857047c30583b139923726ef3d50fc41918a21e07b4b` |
| Full result, decompressed | `fa2324e78f547b7bec0848d8c29f6bd1bcb38fa516e40221698c7bf725e45496` |

[Bracket rankings](../../results/zec_gum_25x_5m_bracket_rankings.csv) · [Frozen selection](../../json/results/zec_gum_25x_5m_selection.json) · [All 6,048 cases and three walk-forward tests](../../json/results/zec_gum_25x_5m_walk_forward.json.gz)
