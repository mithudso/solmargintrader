---
name: solana-oracles-pyth-switchboard
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-1 gap, CVS 3.85
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  The price layer underneath Solana perps, lending and liquidations — Pyth and
  Switchboard. Covers the push-vs-pull oracle distinction and why Pyth moved to
  pull in V2; the ~400ms publisher cadence matching Solana's slot; the
  CONFIDENCE INTERVAL that quantifies publisher disagreement and how to actually
  use it as a trading gate; who bears the update cost and the staleness surface
  that creates; oracle risk as it reaches a trader (stale price, wide confidence,
  divergence from pool price, liquidation on mark not last); and the failure modes
  worth designing against. Educational only — NOT financial advice.
keywords:
  - Pyth Network
  - Switchboard
  - Solana oracle
  - pull oracle
  - push oracle
  - price feed
  - confidence interval
  - Pythnet
  - oracle staleness
  - oracle manipulation
  - mark price
  - liquidation price source
  - price aggregation
tags:
  - trading-and-investing
  - solana
  - defi
  - oracles
  - risk
---

# Solana Oracles — Pyth and Switchboard

> **Educational information only — NOT financial, investment, or tax advice.** Oracle behaviour and
> feed parameters change; everything here is stamped `verified-as-of: 2026-08-04`.

**Why a trader should care.** On Solana, the oracle is not background plumbing — it is **the price you
are actually filled at** on an oracle-priced venue, and **the price you are liquidated at**. Jupiter
Perps prices entries, exits and liquidations off an oracle rather than an order book
(`jupiter-perps-trading.md` §1). If you do not understand the feed, you do not understand your fill.

**Scope.**

| For… | Go to |
|---|---|
| How an oracle price becomes *your* fill and liquidation | `references/jupiter-perps-trading.md` §1, §3 |
| Pool prices vs oracle prices and divergence risk | `references/solana-dex-and-amm-landscape.md` §7 |
| Generic oracle *attacks* (flash-loan, manipulation) and smart-contract auditing | `~/.claude/skills/blockchain/references/smart-contract-security.md` |
| Priority fees, transaction landing, MEV | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |

## Contents

1. Push vs pull — the architectural split
2. Pyth: publishers, Pythnet, and the confidence interval
3. Switchboard and the aggregator model
4. Who pays for the update, and the staleness surface
5. Oracle risk as it reaches a trader
6. Anti-patterns

---

## 1. Push vs pull — the architectural split

**Push oracles** broadcast prices on a fixed schedule to every supported chain, whether or not anyone
reads them. The costs of that model: it is expensive and wasteful when no one is consuming the feed,
it relies on third-party node operators scraping public exchanges — adding intermediation between
source and consumer — and it typically delivers **a single point estimate with no information about
how confident the network is in that number**.

**Pull oracles** keep high-frequency pricing off-chain. When a contract needs a price, it **requests**
it, triggering an on-chain update at that moment. Prices are aggregated off-chain and pulled onto a
supported chain by whoever needs them.

**Pyth moved from push to pull with V2 (August 2022).** The efficiency argument is that on-chain
updates happen only when actually demanded, rather than on a schedule.

**The Solana-specific nuance worth holding.** Solana's low transaction costs make a push model far
more viable there than on an expensive L1 — a developer can simply read an already-published value.
So the push/pull distinction is sharper on expensive chains than on Solana, and the pull architecture's
biggest wins are cross-chain. **Do not import the "pull is strictly better" framing without asking
which chain's cost structure it was argued on.**

## 2. Pyth: publishers, Pythnet, and the confidence interval

**Publishers** — typically exchanges and trading firms with first-hand price data — submit updates
**every ~400ms**, matching Solana's slot length. Each update triggers aggregation.

Aggregation runs on **Pythnet**, a dedicated application-specific chain. The Pyth Oracle Program
combines publisher inputs into a single robust price **plus a confidence interval**.

**The actual algorithm** (Pyth documentation, primary, `verified-as-of: 2026-08-04`) is a two-step
procedure, and knowing it changes how you read the output:

1. **Aggregate price.** Each publisher gets **three votes** — one at their price, and one at each of
   their price **±** their own confidence interval. The aggregate is the **median of all votes**.
2. **Aggregate confidence.** Compute the distance from the aggregate price to the **25th and 75th
   percentiles** of the votes, then take **the larger of the two**.

Two consequences worth drawing out:

- **A publisher's own confidence is an input, not just metadata.** A publisher who reports tight
  confidence casts three tightly-clustered votes and therefore pulls the median harder; one reporting
  wide confidence spreads its votes and influences it less. Pyth states this is deliberate — the design
  lets **more precise sources have greater influence**.
- **Taking the *larger* of the two percentile distances is a conservative choice.** Asymmetric
  disagreement — publishers split with a tail on one side — produces a *wide* interval rather than an
  averaged-away one. The interval is built to over-report uncertainty, not under-report it. Treat a
  wide reading as a real signal rather than noise.

Pyth's stated intent is that the aggregate confidence **"should reflect the variation between
publishers' prices"**, widening when prices diverge across exchanges.

**The confidence interval is the feature that matters most and gets used least.** It quantifies **how
much the publishers agree**. It is not decoration and it is not a spread — it is a live measure of
price uncertainty, and it is exactly the input a risk-aware system should be gating on.

**How to actually use it:**

- **Wide confidence = publishers disagree.** That happens during fast moves, thin liquidity, venue
  outages and dislocations — precisely the moments an oracle-priced fill is most dangerous.
- **Gate on it.** Refusing to open a position, or widening your own risk limits, when confidence
  exceeds a threshold is a cheap and well-founded control. A point estimate cannot give you this;
  a push oracle delivering a bare number cannot either.
- **Do not treat the point price as exact just because it is on-chain.** On-chain does not mean
  correct; it means published.

## 3. Switchboard and the aggregator model

**Switchboard** is the other major Solana oracle. Its distinguishing property is **customisability**:
rather than consuming a fixed catalogue of feeds, you can define a feed and its data sources.

Switchboard V2 operates **push-based** feeds on Solana, and its **on-demand** feeds can *reference*
those existing V2 push feeds inside an aggregator configuration. So the two models coexist inside one
system rather than being mutually exclusive.

**The practical trade-off.** A custom feed can source exactly the data you need — useful for long-tail
assets with no standard feed. It also means **you own the sourcing decision and its failure modes**:
which venues, how aggregated, what happens when one goes down. A widely-used standard feed has had far
more adversarial attention paid to it than a feed you configured yourself.

## 4. Who pays for the update, and the staleness surface

In a pull model, **someone has to submit the update transaction**, and that someone pays for it. This
creates a surface most trader-facing explanations skip:

- **A price is only as fresh as the last update someone chose to pay for.** If no one has pulled
  recently, the on-chain value is stale even though the off-chain aggregate is current.
- Protocols therefore usually enforce a **staleness check** — reject or halt if the published price is
  older than some threshold. That is correct behaviour, and it means **your transaction can fail for
  oracle-staleness reasons that have nothing to do with your order.**
- Update cost is small on Solana, but it is not zero, and it concentrates at exactly the busy moments
  when everyone wants a fresh price and blockspace is contended
  (`solana-transaction-execution-and-mev.md`).

## 5. Oracle risk as it reaches a trader

Five ways the oracle layer shows up in your P&L:

1. **You are liquidated on the oracle price, not the last trade.** On an oracle-priced venue the
   liquidation trigger is the feed. A wick on some *other* venue that moves the aggregate can
   liquidate you even if the pool you traded in never printed there
   (`jupiter-perps-trading.md` §3).
2. **Stale price = wrong fill or failed transaction.** Either you transact against an old number or the
   protocol's staleness guard rejects you (§4).
3. **Wide confidence = the feed is telling you it does not know.** Trading through that without
   widening your own risk limits is ignoring a free signal (§2).
4. **Oracle vs pool divergence.** The oracle aggregate and a specific thin pool can disagree
   substantially. Which one governs depends on the venue's design — oracle-priced perps use the feed;
   an AMM swap uses the pool. Know which applies before sizing
   (`solana-dex-and-amm-landscape.md` §7).
5. **Publisher concentration is a real dependency.** The aggregate is only as good as its contributor
   set. Fewer, more correlated publishers means a narrower confidence interval that is *less*
   trustworthy, not more — agreement among correlated sources is not independent confirmation.

## 6. Anti-patterns

1. **Ignoring the confidence interval.** The single most valuable field in the feed, routinely dropped
   because a point price is easier to plug in.
2. **Treating an on-chain price as verified truth.** On-chain means published, not correct.
3. **Assuming freshness.** In a pull model, freshness is someone else's paid action (§4).
4. **Reasoning about liquidation using the pool price.** Oracle-priced venues liquidate on the feed
   (§5.1).
5. **Reading a narrow confidence interval as high accuracy** without checking publisher count and
   independence (§5.5).
6. **Building on a custom feed without owning its failure modes.** Customisability transfers the
   sourcing risk to you (§3).
7. **Importing "pull beats push" reasoning to Solana unexamined.** Much of that argument is about
   expensive chains; Solana's cost structure changes it (§1).

## References

Internal: `references/jupiter-perps-trading.md` §1, §3 (oracle-priced execution and liquidation);
`references/solana-dex-and-amm-landscape.md` §7 (pool-vs-oracle divergence);
`~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` (update cost,
congestion); `~/.claude/skills/blockchain/references/smart-contract-security.md` (oracle attacks).

External:
1. Pyth Network — *A Proposal for Price Feed Aggregation*. Aggregation design and confidence intervals. https://www.pyth.network/blog/pyth-price-aggregation-proposal
2. Messari — *Understanding Pyth Network*. Publisher model, ~400ms cadence matching the Solana slot, aggregate price plus confidence interval. https://messari.io/report/understanding-pyth-network-a-comprehensive-overview
3. DEXTools — *What Is Pyth Network: Pull Oracle Pricing Guide*. Push-vs-pull contrast; the "single point estimate with no confidence information" critique of push oracles. https://www.dextools.io/tutorials/what-is-pyth-network-oracle-pull-pricing-guide-2026
4. Medium (Innocent Nweke) — *How Will Pyth V2 (Pull Oracle) Benefit Solana DeFi?* The V2 push→pull transition (August 2022) and the Solana-cost nuance. https://medium.com/@innocentnweke/how-will-pyth-v2-pull-oracle-benefit-solana-defi-9e965206e07b
5. Switchboard Documentation — *Oracle Aggregator*. On-demand feeds referencing Switchboard V2 push feeds; custom feed configuration. https://docs.switchboard.xyz/custom-feeds/advanced-feed-configuration/oracle-aggregator
6. QuickNode — *How to Use Pyth for Price Feeds on Solana*. Integration surface. https://www.quicknode.com/guides/solana-development/3rd-party-integrations/pyth-price-feeds

**Source-quality note.** Switchboard's own documentation is primary; the Pyth aggregation blog is
first-party. The remainder — publisher cadence, the V2 transition date, the push-vs-pull framing — is
**secondary** (research reports, tutorials, explainers), corroborated across sources but not verified
against Pyth's own technical documentation in this pass. **Architectural claims are stable; specific
figures (the ~400ms cadence, publisher counts, feed catalogues) are perishable** — verify against the
live docs before building. The §5 risk framing is analysis grounded in the mechanics above, not a
claim quoted from any source.
