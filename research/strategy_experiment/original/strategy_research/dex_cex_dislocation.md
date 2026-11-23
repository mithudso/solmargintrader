---
id: dex_cex_dislocation
name: DEX-vs-CEX Price Dislocation
kind: exposure-strategy
status: spec-only
family: microstructure
summary: Cross-venue basis as both a signal and an arbitrage.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [synchronous-quote-mid, l2-depth, mev-execution-model]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  threshold_bps: {default: 30.0, type: float, desc: "dislocation in bps required to act"}
presets: {}
---
# DEX-vs-CEX Price Dislocation

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #36.

## Equation
```
basis_t = (P_dex - P_cex) / P_cex
act when |basis_t| exceeds threshold plus round-trip cost
```

## Why it might work — and why that claim has been withdrawn

This card used to say it was "one of the few edges here that is a genuine arbitrage rather
than a forecast." **That is false in the DEX-CEX form and has been struck.**

The dividing line between an arbitrage and a spread trade is whether some contractual event
forces the spread to zero. A dated future has an expiry. A DEX-CEX pair has nothing: the two
legs do not settle atomically, the on-chain leg can be dropped, reverted or sandwiched, and
a one-sided fill leaves naked directional risk. It is a spread trade wearing the name.

The same test disposes of perpetual funding carry, which is the variant people reach for
next: perps never expire, so there is no convergence date, and funding flips sign and stays
flipped. Only intra-venue triangular (see `triangular_arbitrage.md`) and dated
cash-and-carry survive it — and even those are riskless only while inventory is already
sitting on both venues.

## What implementing it would take
Synchronised quote history from both venue types, and — critically — **MEV-aware
execution modelling**. `docs/trading-signals-concept-family.md` covers the relevant
machinery: private RPC, Jito bundles, and the sandwich exposure a naive public-mempool
arb walks into.

## Caveats
This is a latency business. A bar-resolution backtest of an arbitrage that lives in
milliseconds would be a fiction, and this harness is bar-resolution by design.

Two hazards specific to any future attempt:

- **Timestamp alignment is a lookahead vector.** Different close conventions, timezones or
  oracle publish-lag silently embed future information. It is worse on an oracle-priced
  venue, where the signal series and the fill series are *the same series* — a naive
  backtest then trades on the print it also fills at, a zero-cost round trip that will look
  spectacular and be fiction. `BarWindow` guards index leakage, not cross-series
  misalignment.
- **`core/perps.py` takes utilization as a constant (default 0.5)**, while
  `funding_utilization_extremes.md` documents sustained 100%. Any Jupiter-leg cost inherits
  that and is understated by construction.

## Likelihood of success: very-low

*Basis: a-priori — the mechanism was never run here. The basis series above was measured,
but measuring the input is not measuring the strategy, so this stays `a-priori` rather than
claiming `measured-oos`.*

**Lowered from `low`.** The old rating rested entirely on the claim that this is a genuine
arbitrage rather than a forecast, and that claim is struck above: the legs do not settle
atomically, so it is a spread trade. Once it is a spread trade it is competing with the
literature in the section above, which is four-for-four negative on the bar-testable
version, and with three searchers who capture 75% of the executable version.

The measurement supplies the rest. On the oracle basis the threshold this card itself
proposes was never reached in 4,310 hours. On pool prints it is reached 3.11% of the time in
single-hour bursts that look like print artifacts.

## Data gap — restated, because the old wording was wrong

This card previously said "no DEX quote history". **Price history is in fact retrievable**:
Pyth Benchmarks serves complete 1h OHLC for `Crypto.SOL/USD` back to 2022-02-03, and
GeckoTerminal serves Solana pool 1h OHLCV. (Pyth requires an API key from 2026-08-18.)

What is actually missing is narrower and harder: **synchronous quote mid with depth**, and
an MEV-aware execution model. Bars give a last print, and this mechanism is defined on the
executable side of a book at an instant.

## Measured: the basis you can retrieve is either zero or noise

Two series were pulled and compared against the repo's Coinbase SOL leg. The contrast
between them is the finding, and it is why `data_available` stays `false`.

| | Pyth oracle vs CEX | Orca pool print vs CEX |
|---|---|---|
| Aligned hours | 4,310 (2026-02-06 → 08-05) | 1,320 (2026-06-11 → 08-05) |
| Median abs basis | **0.7 bps** | **12.8 bps** |
| p99 abs basis | 4.6 bps | 37.2 bps |
| Hours above 8 bps (one leg of this repo's cost model) | 0.88% | 68.86% |
| Hours above 30 bps (**this card's own default threshold**) | **0.00%** | 3.11% |

**On the oracle basis the card's own 30 bps threshold was never reached, in 4,310 hours.**

The pool-print column looks tradeable, and probably is not. Two pieces of evidence point at
microstructure artifact rather than economics: the 39 episodes above 30 bps have a **mean
length of 1.05 hours** and a maximum of 2 — single-bar spikes, not dislocations arbitrageurs
failed to close — and the signed distribution is near-symmetric about zero. Candidate
mechanisms are asynchronous last-print timing inside the bar, swap prints embedding taker
impact so buys print above and sells below mid, and SOL/USDC-versus-SOL/USD depeg.

**This is a hypothesis, not a settled result.** The test that would settle it: compare
against a pool mid reconstructed from reserves at the bar boundary, or against a second
independent SOL/USDC pool. If two independent pools disagree with each other by ~13 bps, it
is microstructure.

The reason this matters more than a null result would: the retrievable series shows a gap
large enough to look tradeable and short-lived enough to be an artifact. A naive
implementation would find "signal", and the backtest would look excellent.

## Funding carry is not available on this venue at all

Worth stating because it is the obvious next idea. **Jupiter has no funding rate.** The
borrow rate is `(hourlyFundingDbps/1000) x utilization`, charged on notional to **both**
sides and structurally floored at zero — nobody is ever paid to hold. Long spot plus short
perp therefore pays borrow on the hedge as pure cost. Carry on this venue is harvestable
only by *becoming* JLP, which is a long crypto basket with a written short-vol overlay, not
a delta-neutral trade.

For scale on what the trade earns where it does exist: Ethena's sUSDe, the largest public
delta-neutral funding-carry vehicle, averaged 18% in 2024 and **3.50% in Mar/Apr 2026**
(Ethena governance disclosures). Aggregate perp funding averaged ~11% annualised in 2024 and
~5% in 2025 (Coin Metrics *State of the Network* #335, 2025-10-28).

## Basis as a *signal* rather than a trade: four negatives

The bar-testable version of this idea is "does a dislocation predict short-horizon returns".
The literature is against it:

1. The one paper claiming carry positively predicts returns — Franz & Schmeling, *Crypto
   Carry*, SSRN 3774118 — **has been withdrawn** (the SSRN page returns HTTP 410). It cannot
   be cited as support and its magnitudes are unrecoverable.
2. The peer-reviewed treatment predicts **liquidations, not returns**: Schmeling, Schrimpf &
   Todorov, *Crypto Carry*, Management Science (online 2026-05-06) — a 10% rise in
   standardised carry predicts a rise in short-futures liquidations of 22% of open interest
   over the next month. High carry forecasts unwind risk, arguably the opposite trading
   implication.
3. A direct test of funding to next-period price finds nothing: contemporaneous 7d funding
   vs 7d price R^2 = 12.5%, but predictive T→T+1 correlation near zero (Presto Research,
   2024-08-02; industry, not peer-reviewed).
4. Basis is **absent from the priced factors** in the broadest cross-section: Babiak &
   Bianchi, JFQA (online 2025-10-27), 600+ coins — liquidity, size, reversal, market and
   downside risk are priced; basis is not.

Cost sensitivity is the number that decides it: He, Manela, Ross & von Wachter,
arXiv:2212.06888, report a BTC perp ladder falling from Sharpe ~3.9 gross to ~1.9 at retail
costs, with annualised alpha 22.6% → 5.5% and **the t-statistic dropping to 1.38 — not
significant**.

A counterweight in fairness: Cao, Zhai & Luo, *Journal of Futures Markets* (in press), find
a two-factor model including log-basis explains a large set of perp predictors. That is
support for basis carrying systematic information as a priced factor — not for a
cost-surviving short-horizon directional forecast.

## What the arbitrage is worth to those who can execute it

Documented and large, and captured by very few. Wu, Sui, Thiery & Pai (AFT 2025,
peer-reviewed) measure **$233.8M** extracted across 7,203,560 CEX-DEX arbitrages by 19
searchers, Aug 2023 – Mar 2025, with **three searchers capturing roughly 75%**. Two of them
transfer ~90% of arbitrage revenue to their integrated builders. Heimbach, Pahari &
Schertenleib (IEEE S&P 2024) put non-atomic arbitrage at over 25% of volume on Ethereum's
five largest DEXes, **$132B**, with eleven searchers responsible for over 80%.

The historical spatial opportunity has decayed sharply. Makarov & Schoar (JFE 135(2), 2020)
recorded US-Korea daily average price ratios above 15% and reaching 40% in Dec 2017 – Feb
2018. Crépellière, Pelster & Zeisberger (Journal of Financial Markets 64, 2023) — the direct
follow-up — find the average maximum price difference falling from 2.8% (2017-18) to 1.1%
post-2019, and state plainly that "starting in 2019, the strategy does not provide
consistent profits any longer... net returns are negative due to trading costs." Makarov &
Schoar attribute the original persistence to **capital controls** rather than transaction
costs — their sharpest evidence being that when USD/BTC differed by more than 20% between
the US and Korea, ETH/BTC on the same exchanges differed by only about 3%.
