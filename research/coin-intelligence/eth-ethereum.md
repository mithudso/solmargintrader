---
name: eth-ethereum
description: Trader-facing reference on Ethereum (ETH) — mechanics, supply and burn, the L2 value-accrual bear case, the ETH/BTC ratio, market structure, measured volatility and beta vs BTC, and what backtesting on the local ETH_1d.csv does and does not establish. Educational only, not investment advice.
---

# Ethereum (ETH)

> **Educational reference for a systematic backtesting project. NOT investment advice.**
> Nothing here is a recommendation to buy, sell, or hold. Every figure is a historical
> measurement or a sourced third-party number, not a forecast.

> **All figures decay.** Prices, flows, yields, fee revenue, staking share, and fork
> parameters in this file are stamped with the date they were true. Ethereum ships a hard
> fork roughly twice a year, and the block gas limit, the blob target/max, and which fork is
> live all change when it does. Anything more than a few weeks past its stamp should be
> re-checked against the primary source in **Sources** before you rely on it. Figures carried
> from the local corpus are stamped with that corpus's own `verified-as-of` date, not today's.
> A dedicated **"Explicitly NOT verified in this file"** table sits just above **Sources** —
> read it before quoting any number this document does not itself establish.

---

## Snapshot (AS OF 2026-08-04)

| Field | Value | As of | Source |
|---|---|---|---|
| Price | **$1,873.83** | 2026-08-05T02:15:22Z | CoinGecko snapshot in `research/TOP_COINS.md` |
| Price (local close) | **$1,868.38** | 2026-08-04 (daily close) | `data/ETH_1d.csv` (first-party) |
| Market cap | **$226.1B** | 2026-08-05T02:15:22Z | CoinGecko snapshot |
| 24h volume | **$6.90B** | 2026-08-05T02:15:22Z | CoinGecko snapshot |
| **Turnover (24h vol ÷ mcap)** | **3.05%** — 3rd of the ten coins here[^turnover-std] | 2026-08-05T02:15:22Z | derived from the two rows above |
| Rank by market cap | **#2** (behind BTC $1,292.1B) | 2026-08-05T02:15:22Z | CoinGecko snapshot |
| ETH/BTC | **0.02925** | 2026-08-04 | computed from `data/ETH_1d.csv` + `data/BTC_1d.csv` |
| Total supply | **121,924,835 ETH** (no cap) | 2026-08-04 | ultrasound.money |
| **Net supply growth** | **+0.85%/yr — net INFLATIONARY** | 2026-08-04 (7d annualized) | ultrasound.money |
| Burn vs issuance | **20K vs 1,057K ETH/yr — burn offsets 1.9%** | 2026-08-04 (7d annualized) | ultrasound.money |
| Drawdown from cycle high | **−61.3%** from $4,831.24 close | high 2025-08-22 | computed, local CSVs |
| Drawdown from 2021 high | **−61.2%** from $4,811.90 close | high 2021-11-08 | computed, local CSVs |
| 2026 YTD | **−37.0%** (BTC −27.0%) | 2025-12-31 close → 2026-08-04 | computed, local CSVs |
| Realized vol, trailing 90d | **49.6%** annualized (BTC 34.7%) | to 2026-08-04 | computed, local CSVs |
| Beta vs BTC, trailing 90d | **1.26** (corr 0.883) | to 2026-08-04 | computed, local CSVs |

**The two price figures differ by 0.3%** because they are different instruments at different
timestamps: CoinGecko is a cross-venue spot composite sampled ~2 hours after the local daily
close. That gap is the floor on how precisely any "current price" can be stated for a 24/7
asset with no consolidated tape. Do not reconcile them; cite whichever matches your use.

**Where ETH sits.** Well off its highs on every horizon. It made a marginal new closing high
in August 2025 ($4,831 on 2025-08-22, narrowly above the $4,812 of 2021-11-08) and has since
lost roughly three-fifths of its value. Over the full local sample (2021-06-17 → 2026-08-04,
1,875 daily bars) ETH is **down 21.3%** while BTC is **up 67.7%** — the single most important
context for anything below.

---

## What it is, mechanically

Ethereum is a single globally replicated state machine. Since **The Merge (2022-09-15)** each
node runs two coupled clients: an **execution layer** (world state, EVM, EIP-1559 gas pricing)
and a **consensus layer** (Proof of Stake). `blockchain/references/ethereum-protocol-expert.md`,
verified-as-of 2026-06-16.

**Account model.** Unlike Bitcoin's UTXO set, Ethereum tracks accounts directly. Every account
is four fields: `(nonce, balance, storageRoot, codeHash)`. Two kinds — **EOAs** (key-controlled,
can originate transactions) and **contract accounts** (code-controlled, only act when called).
Since **EIP-7702** (Pectra, 2025-05-07) an EOA can temporarily point its code field at a
contract, so `tx.origin == msg.sender` and "is this an EOA" checks are no longer reliable — a
detail that matters if you are parsing on-chain flow for signals.

The world state is not stored in blocks; only the `stateRoot` of a **hexary Merkle-Patricia
trie** sits in the header. Its replacement (Verkle vs binary tree) is an open roadmap question.

**The EVM.** A quasi-Turing-complete 256-bit stack machine. "Quasi" because gas bounds every
execution, which sidesteps the halting problem. Three data locations with very different costs:
storage (persistent, expensive), memory (per-call, cheap), calldata (read-only input, cheapest).

**Gas has two separate layers, and conflating them is a common error.** *In-EVM gas accounting*
is per-opcode cost — cold/warm access pricing (EIP-2929), the 21,000-gas intrinsic floor.
*The fee market* (EIP-1559) sets the price per unit of gas. A transaction pays
`gas_used × (base_fee + priority_fee)`.

**EIP-1559.** The base fee is computed by the protocol from the parent block, moves at most
±12.5% per block toward a 50%-full target, and is **burned**. The priority fee ("tip") goes to
the block proposer. The corpus flags a specific and widespread error here: **EIP-1559 did not
lower fees.** It changed how blockspace is priced — easier estimation, lower intra-block
variance — not how much it costs. L2s and blobs lowered fees.

Transactions are typed (EIP-2718): five types defined, 0x00 (legacy) through 0x04 (EIP-7702
set-code). Type 0x02 (dynamic-fee) is the default; **type 0x03 carries blobs**.

**Proof of Stake / Gasper.** 32 ETH activates a validator; EIP-7251 (Pectra) raised only the
*ceiling* to 2048, not the floor. Validators propose and attest. Consensus is **Gasper** =
**LMD-GHOST** (fork choice — picks the head by accumulated attestation weight each slot) plus
**Casper FFG** (finality — justifies and finalizes epoch-boundary checkpoints with a ⅔ stake
supermajority). Provable equivocation is **slashed**; being offline incurs small penalties, with
a quadratic inactivity leak only while the chain fails to finalize.

**Finality is ~12.8 minutes (two epochs) — fast, but neither instant nor objective.** For a
trader this is the exchange-deposit crediting question. Slots are 12 seconds, so the
12–64-confirmation range most venues use spans roughly **2.4 to 12.8 minutes**; true economic
finality sits at the top of that range, not the bottom. (The local corpus glosses this range as
"under 5 minutes", which holds only at the low end — 64 slots × 12s is 12.8 minutes, which is the
two-epoch finality figure, not a sub-5-minute one.) Weak-subjectivity checkpoints exist precisely
because PoS finality is not objective.

**Where most transactions actually go.** A large and growing share bypass the public mempool
through private order flow and builders. Block building is dominated by **MEV-Boost**
(out-of-protocol **proposer-builder separation, PBS** — the split between who *orders* a block
and who *proposes* it). **Enshrined PBS (ePBS)** — the same split written into the protocol
rather than run by out-of-protocol relays — **is not live** as of 2026-06-16.

**Fastest-moving parameters** (corpus `verified-as-of: 2026-06-16` — re-verify before use):
block gas limit ≈ **60M** (EIP-7935, Fusaka, Dec 2025), *not* the long-quoted 30M; blob
target/max **14/21** — set by **BPO2**, the second "blob-parameter-only" fork, on 2026-01-07 —
*not* Dencun's 3/6 or Pectra's 6/9; **PeerDAS is live** (peer data-availability sampling: nodes
verify blob data is available by sampling small erasure-coded chunks instead of downloading all
of it; Fusaka, 2025-12-03). **Full danksharding** — the endgame version that scales that sampling
to many more blobs — **is not** shipped.

---

## Supply and issuance

**There is no supply cap.** This is the first-order difference from Bitcoin and the most common
thing traders get wrong when they map a BTC mental model onto ETH. ETH has no 21M ceiling, no
halving schedule, and no terminal supply. What it has instead is a **variable net issuance**:
gross issuance to validators minus the EIP-1559 base-fee burn.

```
net supply change  =  validator issuance  −  base fee burned
```

Both terms float. Issuance scales roughly with the square root of total ETH staked (more
validators → more total issuance, but lower yield each). The burn scales with L1 demand for
blockspace. **Neither is fixed by schedule, so ETH's inflation rate is an output of network
usage, not an input.**

**Why "ultrasound money" is a contested thesis and not a fact.** The corpus lists this
explicitly as an anti-pattern: *"'Ultrasound money' as settled fact — ETH net-deflationary only
when burn > issuance; post-Dencun largely net-inflationary. State mechanism; flag direction as
volatile and contested."* (`blockchain-economics.md`, verified-as-of 2026-06-16.) The mechanism
is real and permanent. The *direction* is a function of fee revenue, and fee revenue is exactly
what the L2 transition reduced.

**The inflection date is 2024-03-13 (Dencun / EIP-4844).** Before it, L2s posted their data to
L1 as calldata, which competed for the same gas as everything else and burned a lot of ETH.
After it, they post to **blobs** — a separate fee market with its own base fee, priced
independently and initially far cheaper. L2 costs collapsed by roughly an order of magnitude;
so did the L1 burn.

### Where net issuance actually stands — AS OF 2026-08-04

Read live from **ultrasound.money on 2026-08-04**, 7-day time frame:

| Metric | Value | Note |
|---|---|---|
| **Total supply** | **121,924,835.39 ETH** | EVM 166,975,436.26 + beacon 41,669,699.90 − beacon deposits 86,720,300.76 |
| **ETH staked** | **41,669,699.90 ETH** | the beacon-chain balance term above |
| **Staking ratio** | **34.18%** | computed: 41,669,699.90 / 121,924,835.39 |
| **Gross issuance** | **~1,057,000 ETH/year** | 7d annualized |
| **Burn** | **~20,000 ETH/year** | 7d annualized |
| **Net supply growth** | **+0.85%/year** | **ETH is net INFLATIONARY** |
| Base fee | ~13.2 Gwei | 7d chart |
| Price shown | $1,874 | corroborates the CoinGecko $1,873.83 |

**These figures are internally consistent, which is why they can be trusted.** 1,057,000 − 20,000
= 1,037,000 ETH/year; 1,037,000 / 121,924,835 = **0.851%**, matching the site's own headline
+0.85%/year to the rounding. That arithmetic check is the verification — it also proves *which*
numbers on the page had loaded: the burn-total, burn-rate and gas-market panels were all showing
un-hydrated `0.00` at scrape time, and one "fee burn: 2.0K ETH/day" reading belongs to the site's PoW
**simulator**, not the live gauge (2.0K/day would be 730,000 ETH/year, which contradicts the
consistent trio above). That simulator figure is excluded.

**The number that matters: the burn is offsetting 1.9% of issuance.** Twenty thousand ETH burned
against 1,057,000 issued. For ETH to return to net-zero supply growth, **the burn would have to
rise roughly 53×** from its current level.

**So, stated plainly and with a date: as of 2026-08-04 ETH is net inflationary at +0.85% per
year, and the "ultrasound money" (net-deflationary) thesis is not true on current data.** It has
been true in the past — during high-fee periods after the Merge and before Dencun the burn did
exceed issuance for extended stretches. It is not true now, and the reason it is not true is the
subject of the next section.

### The issuance-policy debate is now a live EIP — as of 2026-08-04

Reducing issuance has been a research topic since 2024 (Elowsson/Schwarz-Schilling on the
issuance curve; Drake's "croissant issuance"). **None of it reached the EIP repo until now.**

- **EIP-8361, "Tapered Issuance Burn"** — submitted as **PR #12081 on 2026-08-04**
  (`github.com/ethereum/EIPs/pull/12081`), status **Draft**, Standards Track / Core, created
  2026-07-14. Authors include **Justin Drake** (Ethereum Foundation) alongside pintail-xyz,
  Jérôme de Tychey, dapplion, pa7x1, and Ladislaus von Daniels.
- **Mechanism:** a per-epoch deduction on every validator duty (attestation, proposal, sync
  committee), **burned**. The burn fraction tapers linearly with the staking ratio, reaching 100%
  at a fixed saturation balance. The goal is to remove the ~1.5% yield floor implicit in the
  current 1/√(staked) curve so equilibrium staking settles **below 50%**. Issuance would peak near
  a 20% staking ratio and decline beyond it — and the ratio is **34.18% today**. An 18-month
  phase-in is proposed. Note it layers a burn *on top of* the √ curve; it does not rewrite it.
- **Proposed for the Hegotá fork** (the one *after* Glamsterdam) via PR #12087, also 2026-08-04.
  Hegotá's meta-EIP is EIP-8081 (Draft).

> **Status discipline — this has changed nothing yet.** PR #12081 is **open and unmerged**;
> `EIPS/eip-8361.md` 404s on `master`; there is no page for it on eips.ethereum.org; the number
> 8361 is provisional; and **no issuance EIP is in Glamsterdam**. `BASE_REWARD_FACTOR` is still
> 64 and every supply figure above is unaffected. What changed on 2026-08-04 is only that the
> issuance-reduction argument acquired a formal EIP with an EF researcher on it. Treat it as a
> signal about direction of debate, not as a scheduled change. Verify current status at the PR
> before repeating any of this.

**Why a trader should care at all:** gross issuance currently runs roughly **53× the burn**, so
it is by far the larger term in the supply equation. If anything in this family ever ships, it
reduces *that* term — which would move ETH's net supply growth far more than any plausible
recovery in the burn could. The burn is the term everyone argues about; issuance is the term that
actually sets the number. (To be clear about magnitude: EIP-8361 tapers issuance via a duty-level
burn to lower the equilibrium staking ratio. It is **not** a 53× cut to issuance.)

> **Caveat on the window.** These are **7-day annualized** rates, not trailing-twelve-month. A
> single week of unusual congestion or unusual quiet moves them materially. The *direction* does
> not depend on the window — a burn at 1.9% of issuance cannot be flipped to net-deflationary by
> a normal week — but do not quote "+0.85%" as an annual realized figure. Re-pull before citing.

**Staking.** Validators earn consensus-layer rewards (attestation, proposal, sync committee)
plus execution-layer priority fees and MEV. Staking yield is therefore *not* a fixed rate — it
has a protocol-issuance component that declines as total stake rises, and a fee/MEV component
that rises with network activity. **Withdrawals have been enabled since the Shapella upgrade
(2023-04-12)**, so staked ETH is no longer a one-way door; the exit queue is the remaining
friction.

**One structural point traders miss:** because withdrawals are live and the entry/exit queues
are rate-limited, staked ETH behaves as a *slow-moving* float rather than a locked one. Large
unstaking waves show up in the exit queue days before they hit spot. Queue length is a public,
observable, and under-used data series.

---

## The L2 question

**This is the central bear case on ETH and it deserves to be stated at full strength.**

### The argument

Ethereum chose a **rollup-centric roadmap**: L1 stops trying to scale execution and becomes a
cheap, guaranteed-available *data and settlement layer* for rollups (Arbitrum, Base, Optimism,
zkSync, Linea, and others). Execution sharding was explicitly abandoned. Scaling now means
**data availability**, not more L1 throughput.

That worked. Activity moved. Retail DeFi is now overwhelmingly on L2s — the corpus puts L1 swaps
at **$5–$50+** in gas and L2 swaps at **$0.01–$0.50**, roughly 100× cheaper
(`defi-and-onchain-trading.md`, verified-as-of 2026-06-21). A user has no reason to transact on
L1 for anything under a few thousand dollars.

**The problem is what that does to ETH's value accrual.** ETH's non-speculative demand sinks are
(a) gas paid on L1, of which the base fee is burned, and (b) staking collateral. If activity
migrates to L2s and L2s pay L1 only a small blob fee instead of large calldata fees, then:

1. L1 fee revenue falls,
2. the burn falls,
3. net issuance turns positive (ETH inflates),
4. and the "ETH is a productive, deflationary asset" thesis loses its empirical leg.

Meanwhile the L2s capture the sequencer revenue, the MEV, and increasingly the user relationship
— and the largest of them (Arbitrum, Optimism) have their own tokens. The sharp version of the
critique is that **L2s free-ride
on L1 security while routing the economic surplus to their own equity holders**, and that
Ethereum has successfully scaled the *network* while dis-intermediating the *asset*.

**EIP-4844 made this worse before it made it better, by design.** Blobs are priced in a separate
market with their own base fee, and while blob demand sits below target that base fee sits at its
floor — so L1 collects almost nothing for data availability. **A fee market with no congestion
collects no rent.**

### What the current numbers say about the bear case

The supply section's live reading is the bear case measured rather than argued:

| | Value | As of |
|---|---|---|
| Gross issuance | ~1,057,000 ETH/year | 2026-08-04, 7d annualized |
| **Burn** | **~20,000 ETH/year** | 2026-08-04, 7d annualized |
| **Burn as a share of issuance** | **1.9%** | computed |
| Net supply growth | **+0.85%/year** | 2026-08-04 |
| Base fee | ~13.2 Gwei | 2026-08-04, 7d |

Source: ultrasound.money, scraped 2026-08-04; internal consistency verified (see Supply and
issuance).

**This is about as stark as the evidence gets.** The EIP-1559 burn — the entire mechanism by
which L1 activity accrues value to ETH holders — is currently returning about one-fiftieth of
what issuance pays out. Whatever the theoretical merits of either side, the *measured* state of
ETH's value accrual as of 2026-08-04 is that it is not happening at meaningful scale.

**Two honest qualifications, both of which cut against over-reading the table.**

First, **this is a 7-day window in a low-activity market.** ETH is 61% off its high, volumes are
depressed, and a quiet week produces a quiet burn. Some of this is cyclical demand, not
structural L2 leakage, and the two cannot be separated from this snapshot alone. Distinguishing
them requires the pre/post-Dencun fee-revenue series, which is **not verified in this file** —
see the unverified list at the end.

Second, **a low base fee is what the roadmap was trying to achieve.** Cheap L1 gas and cheap
blobs are the *intended* outcome of scaling, not a malfunction. The bear case is not "fees are
low"; it is "fees are low *and* the asset's value accrual depends on them being high." Whether
that second clause is true depends on whether ETH's value rests on the burn or on its role as
staking collateral and cross-L2 gas, which is precisely the unresolved question.

### The counter-arguments, also at full strength

Treating the bear case as settled is as much an error as ignoring it. The serious responses:

- **The blob fee market has its own price discovery.** The blob base fee uses the same
  EIP-1559-style adjustment as gas. It is near-zero only while blobs are under-subscribed. When
  blob demand exceeds target, the blob base fee rises exponentially and is *also burned*. Cheap
  blobs are a statement about current demand, not a permanent property.
- **Blob capacity is being increased deliberately, and that is a choice with a cost.** Target/max
  went 3/6 (Dencun) → 6/9 (Pectra) → 14/21 (BPO2, 2026-01-07). Every increase suppresses the blob
  fee. That is a policy decision to prioritize L2 cost over L1 revenue, and it can be reversed or
  slowed. Whether it *will* be is a governance question, not a technical one.
- **L2s settle to L1 and cannot leave.** A rollup that stops posting to L1 is a sidechain and
  loses the security property that justifies its valuation. The demand for L1 DA is structural,
  even if currently cheap.
- **ETH is the gas and collateral asset across the L2 ecosystem.** L2 users pay fees in ETH,
  bridge ETH, and post ETH as collateral. Some of that is a demand sink even when the burn is not.
- **Staking is the other sink and it is large.** A meaningful fraction of supply is locked in
  validators and liquid-staking derivatives, which is a float reduction independent of the burn.
- **The roadmap has partly turned back toward L1.** "Based" and "native" rollup designs push
  sequencing back to L1 proposers; there has been an explicit push to raise the L1 gas limit
  (~60M as of Fusaka, up from 30M) and to scale L1 itself rather than only DA.

### What would settle it, in either direction

State the falsifiers, because that is what makes this a reference rather than a position:

- **Bear case strengthens** if: blobs stay chronically under-subscribed at 14/21 or higher
  targets; L1 fee revenue stays at post-Dencun lows through a full demand cycle; net issuance
  stays positive across a high-activity period; L2 sequencer revenue keeps growing while L1 DA
  revenue does not.
- **Bear case weakens** if: blob base fee sustains above its floor for extended periods; blob
  revenue becomes a material share of L1 revenue; L1 base fee recovers on non-DA demand
  (institutional settlement, high-value DeFi, restaking); or governance slows blob-capacity
  growth to preserve L1 revenue.

**For a systematic trader, the practical upshot is narrower than the debate.** The value-accrual
question is a multi-year fundamental thesis. It does not generate a daily-bar signal. What it
*does* affect is (a) whether you should expect ETH's long-run drift to resemble BTC's — the
2021–2026 sample says no, emphatically — and (b) whether a strategy that implicitly depends on
positive drift is safe to port from BTC to ETH. See **For this backtester**.

---

## ETH/BTC

The ratio is the cleanest single expression of "has ETH been worth owning instead of BTC," and
the answer over this sample is no.

**Measured from the local CSVs** (`data/ETH_1d.csv`, `data/BTC_1d.csv`, daily closes,
2021-06-17 → 2026-08-04, 1,875 aligned bars):

| Point | ETH/BTC | Date |
|---|---|---|
| Sample start | 0.06230 | 2021-06-17 |
| **Cycle peak** | **0.08790** | 2021-12-08 |
| 2022 year-end | 0.07231 | 2022-12-31 |
| 2023 year-end | 0.05394 | 2023-12-31 |
| 2024 year-end | 0.03567 | 2024-12-31 |
| **Cycle trough** | **0.01805** | 2025-04-21 |
| 2025 rebound high | 0.04212 | 2025-08-24 |
| 2025 year-end | 0.03391 | 2025-12-31 |
| **Current** | **0.02925** | 2026-08-04 |

**The shape.** A 3.4-year decline from 0.0879 (2021-12-08) to 0.0181 (2025-04-21) — a **−79.5%**
fall in ETH's price *measured in BTC*. Then a violent +133% rebound over four months
(2025-04-21 → 2025-08-24), and then a −30.6% give-back to today. Current level is **−66.7% below
the 2021 peak** and **−53.1% below where the sample starts**.

Note what the rebound does and does not mean. A +133% rally in ETH/BTC that retraces most of the
way is characteristic of a downtrending ratio, not a reversal of one. As of 2026-08-04 ETH/BTC
sits below its 2025 year-end level and below every year-end from 2021 through 2025.

**Why it has behaved this way.** Five explanations are commonly offered; they are not mutually
exclusive and none is cleanly testable:

1. **The value-accrual question above.** ETH's fee burn collapsed post-Dencun while BTC's
   scarcity narrative is mechanical and unchanged. Whatever one thinks of the argument, it is
   the one most cited by allocators.
2. **Different marginal buyers.** BTC's 2024–2025 bid came substantially from spot ETFs and
   corporate treasury allocation — a flow with no ETH analogue at the same scale. The BTC ETFs
   launched roughly six months before the ETH ETFs, into much stronger demand.
3. **Competition on ETH's own turf.** ETH competes with Solana, other L1s, and its own L2s for
   the smart-contract-platform trade. BTC has no comparable substitute for the "digital gold"
   trade. Competition compresses ETH's share of a growing pie; it does not compress BTC's.
4. **The ratio has no anchor.** ETH/BTC is not a spread between two claims on the same cash
   flow. It has no cointegrating relationship to mean-revert to, no carry to anchor it, and no
   fundamental fair value. Treating it as a mean-reverting pair is a category error — the repo's
   own cointegration work (below) is a live example of how that assumption fails in practice.
5. **Beta, not alpha.** Over the sample, ETH's beta to BTC is **1.13** with **R² 0.712** (daily
   log returns). ETH is largely a leveraged BTC position plus idiosyncratic drag. In a market
   where BTC compounds and ETH does not, a beta above 1 with negative alpha produces exactly
   this ratio chart.

**For the backtester:** ETH/BTC is *not* a good candidate for a pair or spread strategy on this
evidence. It has no anchor, it trends persistently, and the repo's cointegration test already
found the SOL/ETH pair behaves badly out of sample despite passing a full-sample ADF test. A
ratio that trends for four years is a momentum series wearing a mean-reversion costume.

---

## What drives the price

Ordered roughly by how much of the daily variance each explains, which is the ordering a
systematic trader should care about.

1. **BTC.** Overwhelmingly the dominant factor. Daily-return correlation to BTC is **0.844** over
   the full sample and **0.883** over the trailing 90 days; **R² = 0.712**. Roughly seven-tenths
   of ETH's daily variance is BTC's daily variance. Any ETH signal that does not beat "trade BTC
   with 1.1× size" has not demonstrated anything.
2. **Broad risk appetite / macro.** Crypto trades as a long-duration risk asset. Rate
   expectations, dollar strength, and equity-vol regimes move the whole complex together. This is
   mostly transmitted *through* BTC, which is why factor 1 absorbs so much of it.
3. **Flows.** Spot ETF creations/redemptions, exchange balances, and stablecoin supply growth.
   These are slower-moving and better suited to weekly or monthly conditioning than daily signals.
4. **The staking and float channel.** Total ETH staked, entry/exit queue lengths, and
   liquid-staking-token supply. Changes here alter effective float. Observable on-chain.
5. **Leverage and positioning.** Perp open interest, funding rates, and liquidation clusters.
   These do not predict direction well but they predict *the shape of moves* — cascades happen
   where leverage is. See **Known failure modes**.
6. **Protocol events.** Hard forks, blob-parameter changes, ETF/regulatory decisions. Discrete,
   scheduled or semi-scheduled, and mostly priced in advance. Fork dates matter more as
   *volatility events* than as directional ones.
7. **Fee revenue and net issuance.** The fundamental channel of the L2 debate. Real, and almost
   certainly the slowest-moving item here. It does not produce a tradeable daily signal; it
   shapes the multi-year drift assumption that a backtest silently inherits.

**What is conspicuously absent:** earnings, dividends, a discount rate, a book value, or any
cash flow with a legal claim attached. ETH has usage-linked economics but no security-like
valuation anchor. Every "fair value" model for ETH is an analogy, and analogies do not
mean-revert on a schedule.

---

## Market structure

### Spot ETFs

- **US spot Bitcoin ETFs** were approved 2024-01-10 and began trading 2024-01-11 (11 products).
  **US spot Ether ETFs** were approved 2024-07-22/23 (9 products), roughly six months later.
  Corpus, verified-as-of 2026-06-21.
- **Staking was excluded from every spot ETH ETF product at launch.** This was the structural
  handicap versus holding ETH directly: an ETF holder got price exposure and paid a fee, while a
  direct holder could also earn staking yield.
- **Structural note that matters for basis and flow analysis:** creations/redemptions on the US
  spot crypto ETFs launched **cash-based**, not in-kind, and Coinbase Custody is the dominant
  custodian across issuers. Cash creation adds a trading step between primary-market flow and
  spot demand, which loosens the intraday link between reported flows and price.

#### Staking inside US spot ETH ETPs — it happened, and not by the route usually cited

**No SEC order ever approved staking in a spot ETH ETP.** The one filing that asked for it —
SR-NYSEARCA-2025-13, "…to Permit Staking of the Ether Held by the Trusts" (filed 2025-02-14,
proceedings instituted 2025-05-28) — was **withdrawn 2025-09-29, never approved.** Staking
arrived another way:

| Date | Step |
|---|---|
| 2025-05-29 | SEC Corp Fin **staff statement**: protocol staking is not an offer/sale of a security. Staff view, "no legal force or effect." |
| 2025-08-05 | Staff statement extended to **liquid staking** and Staking Receipt Tokens. **Explicitly does not cover restaking.** |
| 2025-09-17 | SEC approves **generic listing standards** for Commodity-Based Trust Shares (Rel. 34-103995), removing the per-product bottleneck. |
| **2025-09-19** | **SR-NYSEARCA-2025-72** (Rel. 34-104021), immediately effective: moves Grayscale ETHE + Mini onto the *generic* NYSE Arca Rule 8.201-E so they operate under the generic standards rather than their original approval orders. **This is the enabling step to cite.** |
| 2025-09-29 | Grayscale withdraws the standalone staking filing — the generic route made it moot. |
| **2025-10-06** | **Grayscale ETHE and Mini ETH begin staking — the first US-listed spot crypto ETPs to do so.** |
| **2026-01-05** | **First staking-reward distribution by any US spot crypto ETP:** ETHE pays **$0.083178/share** (ex/record 2026-01-05) on rewards earned 2025-10-06 → 2025-12-31. |

The tax-side enabler was the IRS, not the SEC: **Rev. Proc. 2025-31** set the conditions under
which such a trust keeps grantor-trust status while staking.

**Who actually stakes** (issuer disclosures, dates as shown):

| Fund | Stakes? | Share of ETH staked | As of |
|---|---|---|---|
| 21Shares **TETH** | yes | **85.72%** | 2026-08-04 |
| Grayscale **ETHE** | yes | 80.66% | 2026-08-04 |
| Grayscale **ETH** (Mini) | yes | 80.33% | 2026-07-29 |
| BlackRock **ETHB** | yes | 76.09% | 2026-08-03 |
| BlackRock **ETHA** | **no** — never added it | — | 2026-07-31 |
| Fidelity **FETH** | **no** — S-3 filed 2026-06-24 (up to 100%, 15% staking fee) | — | 2026-06-30 |
| Bitwise ETHW / VanEck ETHV / Invesco QETH | **no** | — | 2026-07-29 / 06-15 / 03-31 |
| Franklin **EZET** | **no** — discloses "will not stake" | — | 2026-07-07 |

**BlackRock runs both**: ETHA (original, non-staking) and **ETHB**, a separate staking product —
fund launch 2026-02-18, exchange trading from **2026-03-12**.

**Pass-through yield, and why it trails the protocol:**

| Fund | Gross | **Net to shareholder** | Mgmt fee | As of |
|---|---|---|---|---|
| Grayscale Mini **ETH** | 2.77% | **2.60%** | 0.15% | 2026-07-29 |
| Grayscale **ETHE** | 2.75% | **2.11%** | 2.50% | 2026-08-04 |
| BlackRock **ETHB** | — | **1.80%** (30-day) | 0.25%, waived to 0.12% | 2026-08-03 |
| 21Shares **TETH** | — | **1.67%** | 0.21% | 2026-08-04 |

**Every ETF net rate sits below the 2.62% protocol reward rate** (StakingRewards, 2026-08-04),
and the spread across wrappers is wide: **2.60% vs 1.67% is 93bp on the same underlying asset.**
Two drags stack — the fee, and the **14–24% unstaked buffer** each fund holds against redemptions.
For a systematic trader the point is that "ETH ETF with staking" is not one instrument; the
wrapper costs between roughly 2bp and 95bp of yield depending on the ticker.

> **A naming trap.** There is **no US ETF with the ticker STETH** — "stETH" is Lido's
> liquid-staking token. The product sometimes mistaken for one is REX-Osprey **ESK** (inception
> 2025-09-25), which is **1940-Act registered, actively managed, and taxed as a C corporation** —
> categorically *not* a Commodity-Based Trust Share, since the generic standards require the trust
> **not** be registered under the 1940 Act. **Grayscale on 2025-10-06 was first.**

### Staking and liquid staking

- **41,669,699.90 ETH is staked — a 34.18% staking ratio** (2026-08-04, from the ultrasound.money
  beacon-chain balance divided by total supply).
- **Protocol reward rate: 2.62%** (StakingRewards, 2026-08-04). Yield has two components
  (protocol issuance + priority fees/MEV) and is therefore variable, not a posted rate. It falls
  as total stake rises — the protocol component scales as 1/√(staked). **Every US spot-ETF
  wrapper delivers less than this** (1.67%–2.60% net; see the ETF table above), so 2.62% is the
  ceiling a US fund holder can capture, not the rate they get.
- The **entry/exit queues** are the friction that makes staked ETH a slow-moving float rather
  than a locked one. As a worked check on 2026-08-04, the on-chain deposit-contract balance
  exceeded ultrasound.money's *credited* beacon deposits by ~2.49M ETH — that gap is the pending
  entry queue, and it reconciles with the ~2.51M ETH validatorqueue.com reported the same day.
  Queue length is public and observable, and it leads spot-market supply by days.
- **Liquid staking tokens** (Lido stETH, Rocket Pool rETH, Coinbase cbETH, Binance WBETH) let
  staked ETH remain transferable and usable as DeFi collateral. **Lido's share of staked ETH has
  sat near the ⅓ threshold** — the level at which a single operator set could in principle
  prevent finality — and the corpus explicitly flags this as a volatile figure to re-verify.
- **Restaking** (EigenLayer and successors) layers additional slashing conditions on the same
  staked ETH in exchange for additional yield. The corpus's framing: pooled security means
  **correlated** risk, and "centralization reappears one layer up."
- **LST depeg is a real, recurring trader-facing event.** stETH traded meaningfully below ETH
  during the June 2022 stress. LSTs are redemption-linked, not hard-pegged; their discount is a
  liquidity and exit-queue phenomenon and it widens exactly when you would want to exit.

### Derivatives, basis, and funding

- **Perpetual futures dominate.** Perps are ~93% of all crypto futures volume; standard funding
  is every 8 hours (00:00/08:00/16:00 UTC) on Binance, Bybit, OKX, BitMEX; Coinbase International
  and dYdX use hourly. Corpus, verified-as-of 2026-06-21.
- **Funding mechanics.** `F = premium index + clamp(interest rate − premium, ±0.05%)`, with the
  interest rate fixed at 0.01% per 8h (~10.95% annualized). Positive funding = longs pay shorts.
  Funding is charged on **notional**, not margin, so at 10× leverage the drag on your capital is
  10× the headline rate.
- **Funding as a signal:** coincident/lagging, not predictive. Sustained >+0.05%/8h for **three or
  more consecutive days** indicates crowded longs and has historically preceded deleveraging — but
  it can persist for weeks. The corpus lists "treating positive funding as a price signal" as an
  anti-pattern.
- **Cash-and-carry.** Long spot + short perp harvests positive funding delta-neutrally; the
  corpus puts a normal environment at 5–8% APY and bull extremes at 25–50%+. The risks are funding
  reversal, liquidation on the short leg, and exchange counterparty risk — all of which correlate
  with each other during stress.
- **Liquidation is triggered by mark price, not last price.** A wick that does not move the mark
  does not liquidate you; a slow drift in the index can liquidate you without a dramatic candle.
- **CME ETH futures** are the regulated venue and the reference for institutional basis. CME
  crypto futures carry **price-limit halts** (a tiered schedule; the specific percentages are
  **UNVERIFIED here** — check the CME rulebook, since the local corpus's "±10% per 60-minute
  window" reading could not be corroborated). The load-bearing contrast is unaffected and is the
  point worth remembering: **no circuit breaker of any kind exists on spot CEX.**
- **Options implied vol: Deribit DVOL 47.94** (2026-08-04). Read that against the realized
  numbers in the next section — trailing-30d realized was **40.2%** and trailing-90d **49.6%**,
  so implied sat above short-dated realized and roughly at the 90-day level. No skew, term
  structure, or put/call figures were confirmed.
- **Other current levels are UNVERIFIED in this file.** No figure is given for futures basis,
  perp open interest, or funding rates, because none was confirmed against a source. These are
  the fastest-decaying numbers in the subject and the ones most likely to be quoted stale; pull
  them live from Coinglass or CME. The *mechanics* above are stable and can be relied on; those
  *levels* are not present.

### Venue and regulatory context

- No Regulation NMS, no NBBO, no consolidated tape, no cross-venue circuit breakers on spot.
  Arbitrageurs, not regulation, keep venues aligned. Volume figures from unregulated exchanges
  should be discounted — Bitwise (2019) estimated 95% of reported spot volume on unregulated
  venues was fake.
- **ETH is classified as a digital commodity** in the SEC/CFTC joint interpretation published
  **2026-03-17** (5-group taxonomy; binding on both agencies but modifiable by a future
  administration without legislation). The **CLARITY Act** passed the House 2025-07-17 and, as of
  the corpus's 2026-06-21 stamp, had **not** passed the Senate. Corpus, verified-as-of 2026-06-21.

---

## Volatility and correlation

All figures below are **first-party computations** from `data/ETH_1d.csv` and `data/BTC_1d.csv`
(daily closes, log returns, 1,875 aligned bars, 2021-06-17 → 2026-08-04). Annualization uses
√365. Reproduce with the same two files.

### Level and dispersion

| Window | ETH ann. vol | BTC ann. vol | σ_ETH/σ_BTC | corr | beta |
|---|---|---|---|---|---|
| **Full sample** (2021-06 → 2026-08) | **71.0%** | 53.2% | **1.34** | **0.844** | **1.13** |
| Trailing 365d | 65.5% | 43.4% | 1.51 | 0.880 | 1.33 |
| Trailing 180d | 56.8% | 42.1% | 1.35 | 0.909 | 1.23 |
| Trailing 90d | 49.6% | 34.7% | 1.43 | 0.883 | 1.26 |
| Trailing 30d | 40.2% | 28.9% | 1.39 | 0.874 | 1.22 |

For scale, SOL's full-sample vol on the same bars is **98.5%** (σ_SOL/σ_BTC = **1.85**). **ETH
sits between BTC and SOL on the risk ladder and is closer to BTC than to SOL.**

### Per calendar year — the numbers are not stable

| Year | n | ETH vol | BTC vol | ratio | corr | beta | ETH ret | BTC ret |
|---|---|---|---|---|---|---|---|---|
| 2021 (partial) | 197 | 85.8% | 68.6% | 1.25 | 0.838 | 1.05 | +54.9% | +21.3% |
| 2022 | 365 | 87.5% | 64.5% | 1.36 | 0.897 | 1.22 | −67.5% | −64.2% |
| 2023 | 365 | 46.5% | 43.5% | 1.07 | 0.832 | 0.89 | +90.8% | +155.8% |
| 2024 | 366 | 64.3% | 53.0% | 1.21 | 0.800 | 0.97 | +46.0% | +120.8% |
| **2025** | 365 | **74.5%** | **41.9%** | **1.78** | 0.822 | **1.46** | −10.9% | −6.3% |
| 2026 (to 08-04) | 216 | 62.9% | 46.8% | 1.35 | 0.919 | 1.24 | −37.0% | −27.0% |

**Three things to take from this table.**

1. **Beta is not a constant.** It ranged 0.89 (2023) to 1.46 (2025) — a 64% spread. A strategy
   sized on a full-sample beta of 1.13 was under-hedged through all of 2025. Any risk model that
   treats ETH's beta to BTC as a fixed parameter is wrong in a way that shows up precisely during
   stress.
2. **Correlation is high and rising.** 0.80–0.92 across every year, and the trailing-90d and 2026
   readings are at the top of that range. **ETH does not diversify a BTC book.** Holding both is
   mostly a position-sizing decision, not a diversification one.
3. **ETH underperformed BTC in every full calendar year of the sample — 2022, 2023, 2024 and
   2025 — while carrying more volatility in every single one of them.** (ETH did outperform over
   the partial 2021 stub, +54.9% vs +21.3%, but that is six months, not a year.) That is the
   ETH/BTC chart restated as a risk-adjusted statement, and it is the fact most likely to be
   missing from a backtest's assumptions.

### Tails and shape

| Statistic | ETH | Window |
|---|---|---|
| Max drawdown (close basis) | **−79.4%** (2021-11-08 → 2022-06-18) | full sample |
| Worst single day | **−17.6%** | full sample |
| Best single day | +21.8% | full sample |
| Days with \|return\| > 5% | **13.8%** of all days | full sample |
| Positive days | 50.5% | full sample |
| Monthly return, mean / median | **+1.82% / −0.41%** | 62 months |
| Monthly return, stdev | 21.25% | 62 months |
| Positive months | **50%** (31 of 62) | 62 months |
| Worst month | **−44.9%** (2022-06) | 62 months |
| Best month | +56.9% (2022-07) | 62 months |

**The mean/median gap is the whole story of ETH's return distribution.** Mean monthly return is
positive (+1.82%) while the median is negative (−0.41%), and exactly half of months are up. The
positive mean is carried by a small number of enormous months. That is a right-skewed,
fat-tailed distribution in which the *typical* month loses money.

Two direct consequences for strategy design: (a) any strategy that systematically misses the
largest up-months — most short-vol, mean-reversion, and grid approaches do — will underperform
buy-and-hold on this asset by more than its hit rate suggests; and (b) a backtest of fewer than
~40 months on ETH is dominated by whether it happened to contain 2022-07 or 2022-06.

BTC's max drawdown over the same window was −76.7% (2021-11-08 → 2022-11-21). Note the different
trough dates: ETH bottomed in June 2022 on the Terra/3AC/Celsius sequence, BTC in November 2022
on FTX. **The two assets have shared peaks but not always shared troughs**, which is where the
residual 29% of variance lives.

---

## Known failure modes for traders

1. **Importing the Bitcoin supply model.** ETH has no cap, no halving, and no fixed schedule.
   Any model, signal, or narrative that depends on programmatic scarcity does not transfer.
2. **Treating "ultrasound money" as a fact.** Net issuance is an output of fee revenue. It has
   been positive for long stretches post-Dencun. State it as a mechanism with a *current* sign
   and a date, never as a property.
3. **Assuming ETH diversifies a BTC book.** Correlation 0.80–0.92 every year in the sample, R²
   0.712. Two positions, one factor.
4. **Using a static beta.** 0.89 to 1.46 across years. Hedge ratios and vol targets need to be
   re-estimated on a rolling window or they will be most wrong when it matters most.
5. **Trading ETH/BTC as a mean-reverting pair.** No cointegrating anchor, no carry, no fair
   value, and a four-year trend. See the repo's own cointegration result below.
6. **Ignoring that liquidation uses mark price.** The chart shows last price. Your liquidation
   is computed on mark. In illiquid moments they differ materially.
7. **Underestimating cascade risk.** The corpus records **~$3.21B liquidated in 60 seconds
   (October 2025)** and **~$1.9B in a 4-hour window (November 2025, ~85% longs, BTC OI −35%)**.
   Crypto spot has no circuit breakers. Stop-losses do not fill at your stop price during these.
8. **Funding-cost blindness on leveraged carry.** Funding accrues on notional. At 10× leverage a
   0.05%/8h rate is ~1.5%/day against your margin, which will exceed most edges.
9. **Confusing an exchange balance with ownership.** A CEX balance is a claim on the exchange's
   balance sheet. FTX. Proof-of-reserves proves assets at a snapshot, not liabilities.
10. **Treating LSTs as ETH.** stETH, rETH, cbETH are redemption-linked, not pegged. Discounts
    open under exactly the conditions in which you would want to exit, and restaking layers
    additional correlated slashing risk on top.
11. **Gas and MEV as unmodelled costs.** On-chain execution costs $5–$50+ per L1 swap and is
    exposed to sandwich attacks sized to your slippage tolerance. If a strategy's edge is smaller
    than round-trip gas plus MEV leakage, it does not exist on-chain regardless of the backtest.
    Private RPCs (MEV Blocker, Flashbots Protect) and intent protocols mitigate this.
12. **Bridge risk on L2 strategies.** Bridge hacks account for **>69% of funds stolen in DeFi
    since 2022, >$2.8B cumulative** — and Ronin, Wormhole, and Nomad had all been audited.
    Optimistic-rollup withdrawals take 7 days unless you pay a fast-withdrawal relayer.
13. **Fitting to the 2021–2026 era.** One cycle, one macro path, one regulatory arc. Every number
    in this file is conditional on that window.

---

## For this backtester

**ETH data is already local.** `data/ETH_1d.csv` — **1,875 daily OHLCV bars, 2021-06-17 →
2026-08-04**, timestamp-aligned bar-for-bar with `data/BTC_1d.csv` and `data/SOL_1d.csv`. No
fetch is required. `data/SOL_1h.csv` (8,823 bars) is the only hourly series.

**Data integrity, checked 2026-08-04:** 1,875 rows, 1,875 unique timestamps, **zero gaps** (every
step is exactly 86,400s), **zero OHLC violations** (`low ≤ open,close ≤ high` on every bar), and
**zero non-positive volume bars**. The series needs no cleaning and no forward-filling, so any
result is not an artifact of gap handling. Note this also means there are **no missing days to
explain away** — the file is a continuous 24/7 series, unlike an equity series with weekends.

**ETH is not a new test — it is already in the CPCV panel, and the result is on record.**
This is the most important correction to make before designing anything: the repo has *already*
run 25 strategy configurations on ETH daily, and the file is
`research/results/cpcv_all25_btc_eth_1d.csv`.

**CPCV** here is *combinatorial purged cross-validation*: the price series is cut into N
contiguous blocks and every combination of k blocks forms one out-of-sample "path", so each
configuration yields a *distribution* of results rather than the single point estimate a 70/30
split gives. *Purged* means bars adjacent to a test block are dropped from training so a
strategy's warmup window cannot peek into its own test period. Throughout this section,
**"median path Sharpe"** means the median across a configuration's paths, **"Q1"** means the
first quartile of that same path distribution (the conservative quarter of regime mixes), and
**"B&H"** abbreviates **buy-and-hold**, which the repo carries as one of the 25 configurations
so every strategy has an in-panel benchmark.

**The path geometry is not uniform, and this matters for the comparison below.** The BTC/ETH run
used 8 groups at k=2, but warmup consumes different numbers of leading blocks per configuration:

| Configs | Usable blocks | Paths | Which |
|---|---|---|---|
| 21 of 25 | 7 | **21** | most strategies |
| 1 of 25 | **8** | **28** | `buy_and_hold` (no warmup) |
| 3 of 25 | 6 | **15** | `hurst_switch`, `ou_reversion`, `vol_regime` (~251-bar lookback) |

**Read the benchmark caveat that falls out of this.** `buy_and_hold` spans **all 8 blocks,
including the earliest** — which for this window is the 2021 stub, where ETH returned +54.9%.
The 21-path strategies drop that block to warmup. So every "beat B&H" count below compares a
21-path strategy median against a **28-path benchmark median computed over a partly different
block set**. The repo's own PBO script restricts to `common_blocks` precisely to avoid this
asymmetry; the panel comparison does not. The counts are still informative and the direction of
the conclusions does not change, but this is not a like-for-like comparison and should not be
quoted as one.

### The panel as it stands

| Dataset | Configs with positive median path Sharpe | Buy-and-hold median return |
|---|---|---|
| BTC daily, 2021-06 → 2026-08 | **25 of 25** | **+25.6%** |
| **ETH daily, same window** | **18 of 25** | **−6.3%** |
| SOL daily, same window | **13 of 25** | +9.4% |
| SOL hourly, 2025-08 → 2026-08 | **0 of 25** | **−22.9%** |
| DOGE daily, 2021-06 → 2026-08 | **16 of 25** | −4.4% |
| ZEC daily, 2021-01 → 2026-08 | **24 of 25** | +5.2% |

Source: `backtester/strategy_cards/README.md` ("The finding that outranks any individual card").
All rows recomputed from the underlying CSVs and they reproduce exactly: BTC +25.56% / 25 of 25
and ETH −6.31% / 18 of 25 from `cpcv_all25_btc_eth_1d.csv` (21 paths over 7 usable blocks — 8
groups, k=2, one block lost to warmup); SOL daily +9.39% / **13 of 25**, plus the DOGE and ZEC
rows, from `cpcv_all25_sol_doge_zec_1d.csv`; SOL hourly −22.94% / 0 of 25 from
`cpcv_all25_1h.csv`. The README records the SOL daily cell as "mixed"; the precise count is 13
of 25.

> **Corrected 2026-08-05.** The SOL daily count read **14 of 25** until its source,
> `cpcv_all25_1d.csv`, was found to be a medium-horizon file with the long-horizon
> `sma_regime_200` row spliced in. `sma_regime`'s real medium SOL median is −0.066, not +0.254,
> which removes it from the positive set. That file is now deleted; diagnosis in
> `research/CROSS-ASSET-TRANSFER.md`. The two new rows come from the same 2026-08-05 run, and they
> are why this table now spans five assets: on identical, unrefitted parameters the count ranges
> from **0 to 25 of 25**.

**Read the two columns together.** The count of "winning" configurations tracks the buy-and-hold
return of the underlying almost perfectly. That is the repo's own conclusion, and it is the
correct one: *"The dataset explains far more than the strategy does."*

**One thing the 18/25 hides: buy-and-hold is itself one of the 25 configurations, and on ETH it
is one of the 18.** ETH buy-and-hold has a *positive* median path Sharpe (+0.303) despite a
*negative* median path return (−6.3%) — the median is taken across paths independently for each
metric, so the two need not agree in sign. "Positive median path Sharpe" is therefore a very low bar.

### The sharper cut: what beats buy-and-hold on both assets

Counting configurations that clear zero is weak. Counting those that beat the benchmark on the
same dataset is stronger, and counting those that do it on *both* assets is stronger still.
Computed from `cpcv_all25_btc_eth_1d.csv` on 2026-08-04 (24 strategies, excluding the
buy-and-hold row itself):

- **BTC:** 10 of 24 beat B&H median path Sharpe (0.619). Only **5 of 24** beat it on return.
- **ETH:** 9 of 24 beat B&H median path Sharpe (0.303). **16 of 24** beat it on return.

**That return/Sharpe inversion is the drift effect in one line.** On ETH, beating buy-and-hold on
*return* is easy (16 of 24) because buy-and-hold lost money — a strategy that simply sat in cash
part of the time cleared the bar. On BTC the reverse holds: beating +25.6% of drift on return is
hard (5 of 24). **On a negative-drift asset, return-vs-benchmark is a near-meaningless test and
risk-adjusted comparison is the only one that carries information.**

**Five strategies beat buy-and-hold on median path Sharpe on both assets:**

| Strategy | BTC Sharpe | ETH Sharpe | BTC return | ETH return | BTC trades | ETH trades |
|---|---|---|---|---|---|---|
| `ts_momentum` | 0.687 | **0.739** | +25.7% | **+34.3%** | 82 | 80 |
| `keltner` | 0.692 | **0.625** | +17.1% | +18.1% | 38 | 34 |
| `ichimoku` | 0.825 | 0.433 | +28.4% | +12.3% | 76 | 62 |
| `atr_sized` | 0.785 | 0.360 | +4.9% | +2.1% | 854 | 822 |
| `vol_regime` ⚠ | 0.700 | 0.343 | +15.3% | +7.8% | 76 | 80 |

⚠ **`vol_regime` is measured on a different block set than the other four** — 15 paths over 6
usable blocks (its ~251-bar lookback costs two blocks to warmup), against 21 paths over 7 for
`ts_momentum`, `keltner`, `ichimoku` and `atr_sized`. Its *membership* in this table is sound
(it clears both buy-and-hold bars), but do not compare its Sharpe magnitude across rows as if
the denominators matched. This is the same like-for-like caveat raised above, applied to the
table most likely to be quoted.

*(B&H median path Sharpe: BTC 0.619, ETH 0.303. Beaten on BTC only: `garch_voltarget`,
`ou_reversion`, `rsi`, `sma_regime`, `voltarget`. On ETH only: `adx_trend`, `bb_breakout`,
`ma_crossover`, `ma_ribbon`.)*

**Now deflate it properly, because this is exactly where a reader would over-read.** With 10 of 24
beating on BTC and 9 of 24 on ETH, the overlap expected purely by chance under independence is
`24 × (10/24) × (9/24) ≈ 3.75` — an approximation that also treats all 24 strategies as
exchangeable draws, which they are not, since 3 of the 24 sit on the smaller 6-block set.
**Observed overlap is 5.** Treating the overlap count as roughly
Poisson, its standard deviation is `√3.75 ≈ 1.9` — so **5 sits within one standard deviation of
the chance expectation.** And because BTC and ETH correlate 0.844 on daily returns, independence
*understates* the chance overlap, pushing the null expectation above 3.75; the magnitude of that
push is **not estimated here**. **So the observed overlap is consistent with chance.** This table
is a **shortlist of what to test next, not a set of five validated edges.** All five clear the repo's 10-trade evidence floor comfortably, which is
more than `ou_half_life_sizing`'s BTC rank-1 could say, but clearing an evidence floor is a
precondition for a claim, not the claim itself.

One asymmetry is still worth flagging: **`ts_momentum` and `keltner` held up best on the harder
dataset**, and `ts_momentum` actually scored *higher* on ETH than on BTC (0.739 vs 0.687) with
near-identical trade counts (80 vs 82). That is the mechanism surviving the removal of the drift
tailwind, which is the more demanding test.

**What this is not:** it is **not** the "returns agree, parameters agree" cell of
`cross-asset-generalisation-testing.md` §4. That rubric is about whether the *selected parameter
values* land in the same place across assets, and **this panel cannot answer that** —
`cpcv_all25_btc_eth_1d.csv` has a `strategy` column but no parameter columns, so parameter
agreement is unmeasured here. The claim this evidence supports is the weaker one: *the mechanism
held on the harder dataset.* Pulling the per-configuration parameter values and checking whether
BTC and ETH select the same ones is the second cheapest upgrade available to this evidence base,
after computing PBO for the ETH panel.

### What testing on ETH establishes

**It is rung 3 on the generalisation ladder** (`cross-asset-generalisation-testing.md` §1):
a correlated second asset. That rung rules out single-asset idiosyncrasy. It does **not** rule
out crypto-wide regime luck, and it does not rule out era dependence.

**The asymmetry is the whole point (§2): a correlated second asset falsifies well and confirms
poorly.** ETH, BTC and SOL over 2021–2026 share one macro path and their pairwise daily-return
correlations run **0.71 to 0.84** (ETH–BTC 0.844, ETH–SOL 0.729, BTC–SOL 0.709, computed on the
1,875 shared bars). Three series that correlated are closer to *one and a bit* independent
observations than to three. So:

- **If a strategy breaks on ETH, that is strong evidence it was fitted.**
- **If a strategy holds on ETH, that is weak evidence it generalises.**

Weight the failures. Do not bank the passes.

**ETH has already done real falsification work in this repo.** Two cards lost a `moderate`
rating partly on it:

| Card | BTC daily **rank** | ETH daily **rank** | Note |
|---|---|---|---|
| `hurst_regime_test` | **13th** of 25 | **19th** of 25 | ETH: median path Sharpe +0.000, Q1 −1.471, **0% of paths positive**, 4 trades |
| `ou_half_life_sizing` | **1st** of 25 | **18th** of 25 | BTC rank-1 rests on **6 trades** with Q1 exactly +0.000; ETH traded 18 times and went nowhere (median path Sharpe +0.012, median return 0.0%) |

> **Read these as ranks, not counts.** Elsewhere in this section "18 of 25" means *18
> configurations had a positive median path Sharpe* (a good outcome). Here "18th of 25" means
> *placed 18th* (a bad one). Same asset, opposite meaning — hence the explicit ordinals.

Read `ou_half_life_sizing` carefully — it is the cleanest lesson in the panel. It ranked *first*
on BTC and *18th* on ETH. The BTC rank came from six trades. **Every good rank it earned came
with a tiny trade count, and the one dataset where it traded properly is the one where it lost.**

The cointegration card is the other ETH-specific result worth knowing:
**SOL and ETH *are* cointegrated on the full daily sample** (ADF −3.127, p≈0.032) while SOL and
BTC are not (−2.648, p≈0.087). Despite passing the test, the gated strategy produced **zero
out-of-sample trades**; with the gate disabled it produced **2 trades and −24.70%**. A passing
statistical test on a full sample did not survive contact with an out-of-sample protocol.

### What testing on ETH does **not** establish

1. **It does not establish that a strategy works.** 18/25 configurations "positive" on ETH is not
   18 discovered edges. The repo's **PBO (probability of backtest overfitting) at the daily
   horizons is 0.700** — the in-sample winner ranks below median out-of-sample 70% of the time,
   so **a good rank at these horizons is not an edge.** (Short horizon: 0.343.
   `research/results/cpcv_pbo.json`, 25 configs, 20 splits at medium/long, 35 at short.)
   **Attribution matters here: that PBO was computed on SOL, not ETH.** `research/cpcv_sweep.py`
   is a SOL sweep, and `cpcv_pbo.json` carries no asset field. **No PBO has been computed for the
   ETH panel at all** — the BTC/ETH run (`cpcv_all25_btc_eth_1d.csv`) reports per-configuration
   path statistics but no overfitting probability. So the honest statement is: ETH's 18/25 is
   un-deflated by any multiple-testing correction, and the one asset where that correction *was*
   measured returned 0.700. Computing PBO on the ETH panel is the cheapest single upgrade
   available to this evidence base.
2. **It does not add an independent sample.** BTC, ETH and SOL over the same window are three
   views of one cycle. Confirming on ETH moves you from rung 1–2 to rung 3, not to rung 5.
3. **It does not test era dependence.** The window is one bull-to-bear crypto cycle under one
   regulatory and rate regime. Nothing in the panel tests 2017, or a non-crypto asset class.
4. **It does not rescue anything from SOL hourly.** The 0-of-25 hourly result is a *different
   sampling frequency* and a *different, shorter period*, not just a different asset. ETH daily
   speaks to neither of those. **There is no ETH hourly file**, so the scale question cannot
   currently be re-tested on ETH at all — and scale is precisely where `hurst_regime_test` broke
   (1st of 25 on SOL daily → 23rd of 25 on SOL hourly).

### What ETH is uniquely good for in this panel

**ETH is the only daily dataset in the panel with a negative buy-and-hold return (−6.3%).**
BTC (+25.6%) and SOL (+9.4%) both had a tailwind; the only other negative-return dataset is SOL
hourly, which is confounded by both frequency and period.

**Be precise about what that buys, because the obvious phrasing overstates it.** ETH is *not*
cleanly "drift-neutral": its buy-and-hold **median path Sharpe is +0.303**, comfortably positive,
even though its median path return is −6.3%. Risk-adjusted, holding ETH still scored above zero.
So the correct statement is narrower and more useful:

**ETH daily is the only dataset in the panel where beating the benchmark on return carries no
information — which is exactly why it forces risk-adjusted comparison.** On ETH, 16 of 24
strategies beat buy-and-hold on return, and that tells you almost nothing, because the benchmark
lost money and any strategy that spent time in cash cleared it. Only 9 of 24 beat it on Sharpe.
On BTC the ordering inverts: 5 of 24 beat on return, 10 of 24 on Sharpe.

**The practical rule that falls out:** report ETH results against buy-and-hold **on Sharpe, never
on return**, and treat any ETH strategy card quoting "beat buy-and-hold" without saying which
metric as unevaluated. Used that way, ETH is the panel's discipline-enforcing dataset — the one
that makes you pick a benchmark metric on purpose instead of inheriting whichever one flatters
the result.

### Concrete protocol notes for an ETH run

- **Hold fixed:** the signal logic, the train window, the selection rule, the fill model
  (`cross-asset-generalisation-testing.md` §3). Changing any of these between assets means
  "out-of-sample" denotes two different things.
- **Re-fit via the identical procedure:** periods, thresholds, weights. Re-fitting by running the
  same selection code is fair; hand-picking on the new asset is a fresh fit wearing the language
  of validation.
- **Must be re-derived, never ported literally:** any price-scale-dependent parameter. Grid
  ranges, tick sizes, and dollar-denominated thresholds are meaningless across a $1,868 asset,
  a $63,883 asset, and a $74 asset. Normalize to ATR, percentage, or volatility units.
- **Match the OOS windows exactly.** BTC and ETH already share the identical 2021-06-17 →
  2026-08-04 span bar-for-bar, so this is free here — but §5c of the generalisation reference
  records a case where a truncated BTC sample produced a *confident, coherent, wrong* conclusion
  (sleeve correlation +0.198 on 31 months, −0.131 on 48) that survived sanity checks and was only
  caught by extending the sample.
- **Report parameter agreement, not just returns** (§4). If ETH and BTC select similar
  parameters, that is the strongest available evidence. If returns agree but parameters diverge
  wildly, you have two separate fits and a coincidence.
- **Vol-scale before comparing tails.** σ_ETH/σ_BTC = 1.34 full-sample but 1.78 in 2025 alone.
  Dividing by a single full-sample ratio will leave a residual, in the same way the SOL/BTC
  comparison did.
- **Benchmark against never re-selecting.** `empirical-backtest-findings-log.md` §9.6 found that
  monthly re-selection beat blind picking by +6.88pp mean but had a *worse median* and a *lower
  win rate* than simply fixing one configuration and never touching it. That comparison is
  skipped almost universally and it is the one that matters.
- **Mind the evidence floor.** The repo uses a 10-trade minimum before a result is ranked. Both
  ETH-relevant downgrades above turned on trade counts of 4, 6, and 18.

### The honest one-line summary

**Testing on ETH is a rung-3 falsification test on a correlated asset over a shared era, and it
is the panel's only daily dataset where return-vs-benchmark carries no information, which is
what forces risk-adjusted comparison. A failure there is strong evidence against a
strategy; a pass there is weak evidence for it, and at PBO 0.700 a good rank is not an edge.**

---

## Sources

### First-party (this repo — reproduce rather than cite)

- `data/ETH_1d.csv`, `data/BTC_1d.csv`, `data/SOL_1d.csv` — 1,875 aligned daily OHLCV bars,
  2021-06-17 → 2026-08-04. All price, ratio, volatility, correlation, beta, drawdown, and
  return-distribution figures in this file were computed from these on **2026-08-04**.
- `research/TOP_COINS.md` — CoinGecko `/coins/markets` snapshot, stamped
  **AS OF 2026-08-05T02:15:22+00:00**. Source of the price / market cap / 24h volume row.
  Machine-readable copy at `research/results/top_coins.csv`.
- `research/results/cpcv_all25_btc_eth_1d.csv` — the BTC and ETH CPCV panel (25 strategies each,
  21 paths, 7 usable blocks). BTC 25/25 and ETH 18/25 recomputed from this file on 2026-08-04.
- `research/results/cpcv_pbo.json` — PBO 0.343 (short), **0.700 (medium)**, **0.700 (long)**.
  **Measured on SOL**, per `research/cpcv_sweep.py` ("CPCV sweep for SOL strategies"); the file
  carries no asset field. No PBO exists for the BTC/ETH panel.
- `backtester/strategy_cards/README.md` — the four-dataset panel table and the "dataset explains
  more than the strategy" finding.
- `backtester/strategy_cards/hurst_regime_test.md`, `ou_half_life_sizing.md`,
  `pairs_cointegration.md` — the ETH-specific card results quoted above.

### Local corpus (dated; these carry their own verification stamps)

- `~/.claude/skills/blockchain/references/ethereum-protocol-expert.md` — account model, EVM,
  gas, EIP-1559, Gasper, blobs, L2 framing. `verified-as-of: 2026-06-16`.
- `~/.claude/skills/blockchain/references/blockchain-economics.md` — burn as mechanism design,
  the ultrasound-money anti-pattern, staking economics, MEV supply chain, fee-market design.
  `verified-as-of: 2026-06-16`.
- `~/.claude/skills/blockchain/references/smart-contract-security.md` — on-chain execution risk
  classes.
- `~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md` —
  perps, funding, liquidation, mark price, ETFs, custody, market structure, regulation.
  `verified-as-of: 2026-06-21`.
- `~/.claude/skills/trading-and-investing/references/defi-and-onchain-trading.md` — gas costs,
  MEV/sandwich mechanics and defenses, L2 economics, bridge risk. `verified-as-of: 2026-06-21`.
- `~/.claude/skills/trading-and-investing/references/cross-asset-generalisation-testing.md` —
  the generalisation ladder, the falsify-well/confirm-poorly asymmetry, hold-fixed vs re-fit,
  the truncated-sample trap. `verified-as-of: 2026-08-04`.
- `~/.claude/skills/trading-and-investing/references/empirical-backtest-findings-log.md` §9 —
  walk-forward and selection-bias measurements.

### Third-party, verified for this file

- **ultrasound.money** — https://ultrasound.money/ — scraped **2026-08-04**. Source of total
  supply (121,924,835.39 ETH), gross issuance (~1,057K ETH/yr), burn (~20K ETH/yr), net supply
  growth (+0.85%/yr), base fee (~13.2 Gwei), and the $1,874 price cross-check. All 7-day
  annualized. Verified by internal arithmetic consistency (1,057K − 20K = 1,037K; ÷ 121.92M =
  0.851% ≈ the site's stated 0.85%), which also identified which panels had loaded and excluded
  the PoW-simulator "2.0K ETH/day" reading. The 34.18% staking ratio is computed from the same
  page's beacon-chain balance term.
- **EIP-8361 "Tapered Issuance Burn"** — https://github.com/ethereum/EIPs/pull/12081 —
  checked **2026-08-04**: PR open, unmerged, not draft, opened 2026-08-04T10:06:31Z; EIP
  frontmatter status Draft, created 2026-07-14. `EIPS/eip-8361.md` returns **404 on `master`**
  (the negative check that establishes it is unmerged). Inclusion proposal for the Hegotá fork:
  https://github.com/ethereum/EIPs/pull/12087 (open, 2026-08-04T15:29:51Z). Hegotá meta-EIP:
  https://eips.ethereum.org/EIPS/eip-8081 (Draft).
- **ETF staking — SEC and issuer primary sources**, all checked 2026-08-04:
  staff statements https://www.sec.gov/newsroom/speeches-statements/statement-certain-protocol-staking-activities-052925
  (2025-05-29) and https://www.sec.gov/newsroom/speeches-statements/corpfin-certain-liquid-staking-activities-080525
  (2025-08-05); generic listing standards https://www.sec.gov/newsroom/press-releases/2025-121-sec-approves-generic-listing-standards-commodity-based-trust-shares
  (2025-09-17); the enabling rule change https://www.sec.gov/files/rules/sro/nysearca/2025/34-104021.pdf
  (SR-NYSEARCA-2025-72); the **withdrawn** staking filing https://www.sec.gov/rules-regulations/self-regulatory-organization-rulemaking/sr-nysearca-2025-13;
  go-live https://www.globenewswire.com/news-release/2025/10/06/3161548/0/en/grayscale-launches-first-staking-spot-crypto-etps-in-u-s.html
  (2025-10-06); first distribution https://www.globenewswire.com/news-release/2026/01/05/3212772/0/en/grayscale-ethereum-staking-etf-ticker-ethe-becomes-first-u-s-ethereum-etp-to-distribute-staking-rewards.html;
  Fidelity S-3 https://www.sec.gov/Archives/edgar/data/2000046/000119312526281283/d15998ds3.htm;
  yields from issuer pages (etfs.grayscale.com/eth, /ethe; iShares ETHB; 21shares.com TETH).
  Protocol reward rate 2.62% from StakingRewards, 2026-08-04. Deribit **DVOL 47.94**, 2026-08-04.

### Explicitly NOT verified in this file — pull before citing

These are required by a complete treatment and are **not** established here. Do not quote a
number for any of them from this document.

> **Why these gaps exist, precisely.** Three parallel research agents were dispatched on
> 2026-08-04 covering supply/issuance, L2 fee revenue, and market structure/ETFs. **The supply
> agent returned** (its findings are the EIP-8361 subsection) and **the market-structure agent
> returned** (the ETF-staking tables and DVOL). **The L2 fee-revenue agent had not returned when
> this file was finalized**, and the session's web-search budget was exhausted. Everything still
> listed below was in its scope or was a stated gap in the market-structure agent's own report.
> This is "not yet retrieved", not "looked for and not found" — resuming that agent is cheaper
> than re-researching from scratch.

| Item | Status | Where to get it |
|---|---|---|
| **L1 fee revenue, pre- vs post-Dencun** | **UNVERIFIED** — the L2 section argues the mechanism and shows the *current* burn, but carries no measured pre/post-2024-03-13 fee-revenue series | growthepie.xyz, Dune, Token Terminal |
| **Blob fee revenue and blob base-fee history** | **UNVERIFIED** — the scrape showed blob-market panels at `0.0`, but neighbouring panels were confirmed un-hydrated placeholders, so these could not be distinguished from load artifacts | ultrasound.money (blob section), Dune |
| **L2 share of ecosystem activity** | **UNVERIFIED** — no measured figure | L2BEAT, growthepie.xyz |
| **Cumulative ETH burned since EIP-1559** | **UNVERIFIED** | ultrasound.money |
| **Lido / liquid-staking market share, restaking TVL** | **UNVERIFIED** — corpus flags the "near ⅓" figure as volatile and it is not re-verified here | Dune, DeFiLlama, L2BEAT |
| **Spot ETH ETF cumulative flows and AUM** | **UNVERIFIED** — launch dates, staking status, and net yields **are** established (2026-08-04); *flows and AUM* are not | farside.co.uk/eth/ |
| **Invesco QETH staking status after 2026-03-31** | **UNVERIFIED** — no later filing opened; every other issuer's status is established | SEC filings, issuer site |
| **Futures basis, perp OI, funding rates** | **UNVERIFIED** — mechanics are described; no current level is given. (**Options: Deribit DVOL 47.94 at 2026-08-04 is established**; skew, term structure and put/call are not) | coinglass.com, CME |
| **Live fork after Fusaka; current blob target/max; block gas limit** | **CORPUS-DATED 2026-06-16, not re-verified** — 14/21 blobs, ~60M gas, PeerDAS live, ePBS not live | ethereum.org/roadmap, eips.ethereum.org |
| **ETH intraday all-time high** | **UNVERIFIED** — this file uses *closing* prices only ($4,831.24 on 2025-08-22; $4,811.90 on 2021-11-08). The intraday ATH is a different and higher number | CoinGecko, TradingView |
| **The ETH/BTC narrative explanations (§ETH/BTC items 1–3)** | **INTERPRETATION, not measurement** — commonly-offered explanations, explicitly labelled as not cleanly testable | — |

### Live sources to re-verify before relying on any current figure

| Figure | Source |
|---|---|
| Net issuance vs burn, ETH supply | https://ultrasound.money/ |
| L1 fee revenue, blob revenue, L2 activity share | https://growthepie.xyz/ , https://dune.com/ |
| L2 stages, TVS, sequencer decentralization | https://l2beat.com/ |
| Staked ETH, validator queue, staking yield | https://beaconcha.in/ |
| Spot ETH ETF daily and cumulative flows | https://farside.co.uk/eth/ |
| Perp OI, funding rates, liquidations | https://www.coinglass.com/ |
| Options OI and implied vol (DVOL) | https://www.deribit.com/ |
| Fork status, EIP text, blob parameters | https://ethereum.org/en/roadmap/ , https://eips.ethereum.org/ |
| Price, market cap, volume | https://www.coingecko.com/en/coins/ethereum |

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
