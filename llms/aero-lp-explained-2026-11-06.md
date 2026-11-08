# Your Aero liquidity: the kill switch, your two positions, and the 5% rule

*Written 2026-11-06. Figures come from your wallet and the bot's live scout at that time. Positions and prices change.*

---

## 1. The "KILLED" message is not an error

> KILLED: the daemon takes no on-chain action. Press Resume to delete the KILL file.

The message confirms that the kill switch is **on**. The background bot (the "daemon") is paused and will not send any transaction until you press **Resume**. While paused it still reads prices and keeps the Liquidity tab up to date.

What the kill switch does **not** do:

- **It does not close or withdraw any position.** It only stops the bot from acting.
- **It does not affect the two positions below.** You opened them yourself in the Aero app, and the bot does not manage them. The bot manages only the positions it opens itself or the ones listed in its config. Right now it manages **none**.

So pressing Kill was harmless but changed nothing about your positions. The bot had no position and was holding your coins anyway.

---

## 2. Your two current positions (opened in the Aero app)

| | **#1660731 RSGP / USDC** | **#1661242 USDC / AMZNc** |
|---|---|---|
| Pool | CL100, 1% fee, [pool](https://www.geckoterminal.com/base/pools/0x8E859b6cf564C4ac2b848693C85C496E81DBf6C8) | CL10, about 0.12% fee, [pool](https://www.geckoterminal.com/base/pools/0x532e0F46d1e528507FC9454d5847C231f23bDDf6) |
| What it holds now | 5,258 RSGP ($8.64) + 8.21 USDC = **$16.85** | 13.60 USDC + 0.0904 AMZNc ($23.28) = **$36.88** |
| Uncollected fees | $0.008 | $0.15 |
| In range? | Yes, range about ±3.5% | Yes, range about ±0.15%, very narrow |
| How much the pair moves | **17.6% per day** (a very volatile small-cap token) | 1.5% per day (tokenized Amazon stock vs USDC) |
| Expected net, per year | **about −900% (model) / −860% (replay).** That rate applies only while in range. With moves this size it bleeds against holding and soon drifts out of range. Then it is all-RSGP if RSGP falls, or all-USDC if RSGP rises, and earns nothing. | **about −3%.** A small expected loss. |
| Flags | Unlisted token; income far below the arbitrage cost | Unlisted token (tokenized stock); short price history |

**Why RSGP/USDC loses.** Every time RSGP moves, arbitrage bots trade against your position at the old price. At 17.6% daily moves that cost is enormous. The pool's fees (about 0.4% a year at a ±10% range) cannot come close. A narrow range makes it worse: the position soon drifts out of range and ends up holding only whichever token is falling.

**Why USDC/AMZNc is roughly break-even.** Fees nearly cover the cost, and the price moves much less. It still pays less than holding, and the range is so narrow that it will often sit out of range and earn nothing.

**What you can do** (nothing happens unless you ask):

1. **Withdraw RSGP/USDC.** This is the one losing money fast. You get back whatever RSGP and USDC it holds at that moment. Whether to keep or sell the RSGP is a separate decision.
2. **Withdraw USDC/AMZNc**, or keep it if you are happy with a small expected loss.
3. **Hand them to the bot.** If their token ids go in its config, it tracks their P&L and rebalances them when that pays. Note: under the 5% rule it would *not* re-enter these pools if they went out of range, because both fail it.

Tell me "withdraw #1660731" (or both). I will exit it with the same safe withdraw used before: simulated first, then sent.

---

## 3. The 5% rule, explained

**In one sentence:** the bot moves your idle coins into a pool only if it expects to beat simply holding those same coins by at least 5% a year, and two independent checks must agree.

### What "net" means

**Net** is measured against simply holding the two coins:

- **Income.** What a deposit *actually* earned in the last 24 hours: trading fees plus AERO rewards, read from the blockchain. It is not the APR a website advertises. Advertised APRs overstated real fee income about 5× when this was checked.
- **Minus LVR (loss-versus-rebalancing).** When the price moves, arbitrage bots trade against your position at the old price, and your deposit ends up worth less than the two coins held. This is the ongoing form of "impermanent loss". It grows with **volatility squared** and with how **narrow** your range is.
- **Minus rebalancing.** Gas plus swap fees each time the bot re-centers your range.

So "5% net" means **5% a year more than just holding the coins.**

### Why two checks must agree

1. **The forward model:** income − LVR − rebalancing cost, using this week's volatility.
2. **The replay:** the pool's *actual* last 7 days of prices, re-run as if the bot had managed a position.

The two err in opposite directions:
- The model overcharges for price wobbles that bounce back. On pegged pairs those wobbles actually earn fees.
- The replay only sees one week, which may have been unusually calm.

Requiring both means the bot acts only when a pool is convincingly good.

### Why 5% and not 0%

- **The estimates are noisy.** One day's income can double or halve the next, and volatility comes from only a week of data.
- **Some risks are not in the numbers:**
  - contract bugs;
  - a stablecoin or staked-ETH token losing its peg;
  - AERO rewards being redirected to other pools;
  - unknown tokens.
- **Simpler options already pay about 3–5% with less risk.** ETH staking pays about 3% and USDC lending about 4–5%. A pool that cannot beat holding by more than that is not worth the extra risk.

### Today's numbers (Aero, $10 deposit, APR %)

| Pool | Fees | AERO | Arbitrage cost (LVR) at ±10% | Model net | Replay net | Verdict |
|---|---|---|---|---|---|---|
| WETH/USDC CL100 | 6.0 | 26.2 | 134 | **−33.9** | **+8.6** | Fails: the checks disagree. Last week was calm, but ETH moving about 3.5% a day eats the income. |
| WETH/cbBTC CL1 | 1.0 | 1.8 | 13 | −3.6 | −2.3 | Fails: both show a loss. |
| AERO/WETH CL200 | 4.2 | 7.2 | 53 | −14.3 | −12.2 | Fails: both show a loss. |
| Pegged pairs (USDC/USDT, cbETH/WETH…) | ~0 | ~0 | ~0 | ≈ 0 | ≈ 0 | Fails: safe but pointless. Professional 1-tick liquidity takes nearly all the income. |

The pattern: **volatile pairs pay 3–30% a year but lose 13–134% to arbitrage. Pegged pairs lose nothing and earn nothing.** That is why the bot is holding your coins.

### Changing it

The bar is `min_net_apr` under `[allocator]` in `/Users/mitch/.aero-lp/config.toml`.
- Lower makes the bot more willing to deploy.
- Below 0 means accepting an expected loss.

---

## 4. Still running

- **Comparing all liquidity providers on Base.** DefiLlama lists 620 Base pools over $100k across 21 providers: Uniswap v2/v3/v4, Aerodrome, PancakeSwap, Beefy, SushiSwap, Alien Base, Curve, Balancer and more. An agent is scoring them all with the same measures above. It writes a ranked report and adds an `aero-lp providers` command.
- **Finishing the Aero research.** This repairs the 9 claims that failed fact-checking, installs the Aero reference, builds the indexes and audits the skills.
