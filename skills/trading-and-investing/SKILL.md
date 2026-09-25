---
name: trading-and-investing
version: "1.5.0"
updated: "2026-08-05"
category: custom
model: claude-sonnet-5
effort: medium
metadata:
  changelog:
    - "2026-06-16 created via /dr deep-research — FOUNDATION + HUB root for the trading & markets family; 6 concepts, 30+ independent sources (regulator-grade: SEC/Investor.gov, FINRA, CFTC, SIPC, DTCC, OCC, peer-reviewed Barber/Odean). Routes to 16 intended spokes; SKIP edge to investing-and-retirement."
    - "2026-06-16 sko v1.0.0->v1.0.1 — Pass H 10/10 pos, 0/10 neg (predicted); fixed 1 High (desc 1745->~995 chars, Glean cap) + 7 Medium (manifest reconcile; BrokerCheck/target-date routing split; brokerage-account/cash-vs-margin foundation; output contract; commodities routing; volatile-claims bullet split; LULD date + rare-winner figure); 2 hygiene"
    - "2026-06-16 spoke #1 stock-and-equity-trading BUILT via /dr — references/stock-and-equity-trading.md (6 concepts; ~40 independent sources: SEC/Investor.gov, FINRA, DTCC, Congress.gov CRS, IRS, NYSE/Nasdaq, S&P DJI/MSCI/FTSE Russell, SPIVA, Sharpe/Bessembinder/Barber&Odean). Covers equity instruments/structure, fundamental analysis, dividends/buybacks/splits, IPOs/SPACs/primary market, long/short mechanics, active-vs-passive evidence; SKIP edges to options/derivatives/technical-analysis/microstructure/investing-and-retirement."
    - "2026-06-21 spoke #15 defi-and-onchain-trading BUILT via /dr — references/defi-and-onchain-trading.md (10 concepts; 34 cited sources: Uniswap v2/v3 whitepapers, Paradigm research, arXiv MEV studies, Flashbots/MEVBlocker docs, CoW/UniswapX/1inch official docs, GMX/dYdX/Hyperliquid docs, L2Beat, Chainlink, Ledger/Trezor, Safe ERC-4337 docs). Covers AMM x*y=k, concentrated liquidity, IL math, price impact, MEV sandwich defense (private RPC, intent protocols), intent-based order flow, perp DEXs, bridges, self-custody wallets."
    - "2026-06-21 sko v1.0.7->v1.0.8 — Pass H 9/10 pos (predicted); 0 High + 6 Medium fixed (desc+triggers DeFi coverage; whenToUse DeFi entries x6; output contract restored full read logic; related_skills +blockchain +consumer-credit-and-debt; cross-hub map prose tightened); 2 Low"
    - "2026-06-21 spoke #16 ai-and-ml-for-trading BUILT via /dr — references/ai-and-ml-for-trading.md (9 concepts; 23 footnoted citations; 4 post-cutoff arXiv papers spot-fetched + confirmed; covers feature engineering/info bars/fractional-diff, gradient boosting/SHAP/purged-CV, NNs/918-experiment study, alt-data taxonomy, LLM hallucination risk, RL execution/Nevmyvaka/failure-modes, ML backtesting pitfalls/HLZ/McLean-Pontiff/PBO, production systems/IC-monitoring/drift). Hub v1.0.8->v1.0.9."
    - "2026-06-21 spoke technical-analysis BUILT via /dr — references/technical-analysis.md (12 sections; 46 footnoted citations; covers chart types/candlesticks/Nison, chart patterns/H&S/double-top-bottom/triangles/flags/wedges, trend analysis, S/R/Osler 2000+2003, RSI/Wilder/MACD/Appel/Bollinger Bands/SMA-EMA/ATR/stochastics, OBV/Granville/VWAP/Volume Profile/A-D line/McClellan/Zweig, Dow Theory/Hamilton/Rhea/Brown-Goetzmann-Kumar, Elliott Wave/Elliott/Batchelor-Ramyar critique, empirical evidence: Fama 1970/1991, BLL 1992, Sullivan-Timmermann-White 1999, Park-Irwin 2007, Lo-Mamaysky-Wang 2000, Bajgrowicz-Scaillet 2012, Neely et al 2014, Lo AMH 2004, Menkhoff 2010, Jegadeesh-Titman 1993, Moskowitz et al 2012). Hub v1.0.9->v1.0.10."
    - "2026-06-21 sko v1.0.10->v1.0.11 — Pass H predicted 8/10 pos; 5 Medium fixed (desc +ML/AI triggers; triggers +10 ML/AI keywords; whenToUse +3 ML/AI entries; cross-hub-map +ai-and-ml-for-trading); 1 Low (Pass O peer seed da-analytical-methods skipped — edge already present in body)"
    - "2026-06-21 sko v1.0.11->v1.0.12 — Pass H 10/10 pos, 0/10 neg (predicted); 2 Medium fixed (technical-analysis +3 whenToUse entries +11 triggers; blockchain seam note added to cross-cutting notes); 0 High"
    - "2026-08-04 spoke jupiter-perps-and-jlp SPLIT into jupiter-perps-trading (trader side: oracle execution, borrow fee, liquidation drift) + jupiter-jlp-pool (LP side: composition, fee accrual, payoff, risk). Pass J: 14.2k tokens exceeded the ~10k hard ceiling; both halves now ~8.8k and ~7.7k. All inbound references rewired; hub routing table and cross-hub map updated."
    - "2026-08-03 spoke jupiter-perps-and-jlp BUILT via /dr --verify-claims — references/jupiter-perps-and-jlp.md. Venue-specific Jupiter Perps (jup.ag) + JLP coverage: oracle-priced peer-to-pool execution, the borrow-fee model contrasted against funding rates (both sides always pay, never negative, utilization-driven), leverage/margin and liquidation-price drift from accruing borrow fees, JLP composition/target weights and mint-redeem, fee accrual into the JLP virtual price, LP-as-counterparty payoff, JLP risk profile, venue anti-patterns. SKIP edges: generic perp/funding/margin theory -> crypto-and-digital-asset-trading.md §2-4; sizing/Kelly/drawdown -> trading-risk-management.md; EVM perp DEX landscape -> defi-and-onchain-trading.md §8. Hub v1.0.13->v1.0.14."
    - "2026-06-21 sko v1.0.12->v1.0.13 — 1 High fixed (manifest.yaml synced to v1.0.13: triggers/whenToUse/description/related_skills/version all updated to match SKILL.md); 2 Medium fixed (routing table annotated with Built/Unbuilt state per spoke; whenNotToUse +3 SKIP edges: blockchain-economics/da-analytical-methods/blockchain); 1 Low (field name keywords→tags noted, manifest updated)"
    - "2026-08-04 spoke #27 asset-specific-vs-universal-parameters BUILT in-thread — references/asset-specific-vs-universal-parameters.md. Three parameter classes (structural / scale-dependent / asset-specific) and the test that assigns one: run the identical selection procedure on both assets and compare SELECTED VALUES, not returns. Normalisation table converting price- and volatility-denominated parameters into dimensionless ones. Measured SOL-vs-BTC split on matched 48-month OOS windows: STRUCTURAL = 10-level grid (modal both, 48/48 BTC) and 4-hourly sampling (modal both); ASSET-SPECIFIC = trend standalone edge, which FLIPPED SIGN (+4.49% SOL vs -1.00% BTC) — agreeing parameters do not imply a universal edge. §4.1 added after the scale hypothesis was TESTED rather than assumed: sigma_SOL/sigma_BTC=1.91 but the grid and trend tail ratios are 2.39 and 1.55, so normalisation leaves a ~5pp residual in OPPOSITE directions — the tails are not purely scale. Hub v1.1.0->v1.1.1; spoke count in description corrected 32->27 (33 reference files minus 6 foundation refs); routing-table header corrected 16->17; manifest resynced from v1.0.14 (had drifted to 'routes to 16 spokes')."
    - "2026-08-04 sko v1.1.1->v1.1.2 (outer-loop-driven, --max-iter=1 per iteration) — iter1: 2 Medium fixed: (1) Pass A — asset-specific-vs-universal-parameters.md §5 and its References section cited `trading-strategies-and-styles.md §5` for degrees-of-freedom/multiple-testing, but that section is 'Backtesting a Discretionary Strategy' with no such content; repointed both citations to `algorithmic-and-quant-trading.md §5.3` (the actual Multiple Testing Problem section), spoke v1.0.0->v1.0.1; (2) Pass N — `triggers` had zero coverage for the 3 new-spoke whenToUse entries (parameter reuse/universality/normalisation) with the description pinned at the 1000-char cap; added 3 bounded trigger phrases (asset-specific parameters, universal parameters, parameter normalisation) to SKILL.md+manifest.yaml. Reported not fixed: investing-and-retirement bare-spoke-form pointer (Low — 3 other resolution paths + pinned desc); hub SKILL.md body ~10.16k tokens vs ~10k Pass J ceiling (report-only, same class as the 6 pre-existing oversized spokes); em-dash density 1.08/100 words unadjusted for headings (Low, likely <1.00 adjusted); da-analytical-methods missing a reciprocal SKIP edge back to this hub for trading-specific generalization testing (Low/speculative, no peer edit made)."
    - "2026-08-04 spoke #28 walk-forward-window-length-and-refit-cadence BUILT in-thread — references/walk-forward-window-length-and-refit-cadence.md. Round-6 top gap (CVS 4.65). Measures the two knobs run_walkforward.py and run_walkforward_book.py both hardcode (TRAIN_W=12, implicit cadence=1) and never justified. 28 cells (7 windows x 4 cadences) scored on IDENTICAL 24 OOS months via the common-OOS-window discipline, book weight held fixed to avoid per-cell refitting. Result: monthly refit sub-optimal at 7 of 7 window lengths (unanimous); cadence near-monotone (1:-1.46% -> 6:-0.89%) with config switches 18 -> 4.4 per 24 months; window 12 was the best window averaged over cadences, so ONE inherited default was right and the other wrong. ALL 28 cells lost money (B&H -1.95% same months) — reported as which way of losing lost least. Spread 1.97pp mean / 3.56pp worst, much smaller than the ~50pp sampling-frequency effect. Hub v1.1.2->v1.1.3."
    - "2026-08-04 Pass J CEILING SWEEP — 6 references exceeded the ~10k-token hard ceiling; all resolved. indicator-signal-implementation-and-backtesting (21,728 tok) split 3 ways -> +signal-backtest-protocol-and-regime-evidence, +signal-pairing-volume-and-pattern-signal-sets; stock-and-equity-trading -> +equity-fundamentals-and-corporate-actions (issuer side, SS2-4 verbatim); technical-analysis -> +technical-analysis-breadth-frameworks-and-evidence (SS8-12); ai-and-ml-for-trading -> +ml-backtesting-pitfalls-and-production-systems; defi-and-onchain-trading -> +self-custody-wallets-and-key-security. Section numbering and footnote labels preserved across every split so existing SSN.M citations still resolve; footnote closure verified per file. Hub body itself was 10,491 tok: the Foundation-references routing table was hand-compacted (28 rows rewritten, 5 DUPLICATE rows removed incl. a doubled trading-strategies-and-styles) -> body 8,802 tok. options-trading-and-strategies: 4 pointers to never-built sub-references relabelled Unbuilt with an explicit do-not-Read warning; dead refs 10 -> 5 (all remaining are legitimate forward refs to Unbuilt spokes). 34 spokes / 40 reference files. Hub v1.1.3->v1.2.0."
    - "2026-08-04 sko v1.2.0->v1.2.1 (outer-loop-driven convergence run, --max-iter=1 per iteration) — iter1: 11 Medium fixed, all restructure-consistency defects from the same-day Pass J Ceiling Sweep: (1) two stray blank lines had split the Foundation-references table in two right where the 6 Pass-J split-file rows were appended, so those rows carried no header/separator and would not render as table cells — removed; (2) the last row (self-custody-wallets-and-key-security) ran directly into the '## How to answer from this hub' heading with no line break, so the heading could not render — separated; (3-5) three '(see next row)' pointers (on defi-and-onchain-trading, ai-and-ml-for-trading, technical-analysis) now pointed at the wrong row because the 6 new rows were appended at the table's end, not adjacent to their parents — repointed by name, matching the stock-and-equity-trading pattern; (6) intro line 200 still said '33 reference files as built' against the current 40 — corrected; (7-9) the 17-planned-spokes routing-table rows for technical-analysis, defi-and-onchain-trading, and ai-and-ml-for-trading didn't disclose their Pass-J split (unlike stock-and-equity-trading's row, which does) — added matching split-pointers; (10-11) signal-backtest-protocol-and-regime-evidence and ml-backtesting-pitfalls-and-production-systems had zero whenToUse/trigger coverage — added 2 whenToUse lines + 4 trigger phrases each, manifest.yaml mirrored. Reported not fixed (Low): technical-analysis-breadth-frameworks-and-evidence and signal-pairing-volume-and-pattern-signal-sets have partial whenToUse coverage only (retrieval still works once inside the hub via the Foundation-references table's own per-row description); cross-hub-map's 'Example reference files' list omits 5 files by design (explicitly illustrative, not exhaustive)."
    - "2026-08-04 spoke #35 selection-rule-design BUILT in-thread — references/selection-rule-design.md. Round-7 top gap (CVS 4.65), the third inherited walk-forward knob after window and cadence. 5 rules compared on 48 OOS months with protocol fixed. KEY: added a RANDOM baseline (200 seeds) and an ORACLE look-ahead bound, without which a rule comparison is just a beauty contest. All 5 rules beat random (-1.61%); incumbent argmax-mean best at +1.66%, outside random 95% band [-3.72%, +0.03%], and won 3 of 5 distinct window settings (p ~ 0.058, suggestive only) — so unlike refit cadence, THIS inherited default looks right. But the incumbent captured only 29.1% of the random->oracle span (+9.65%) and buy-and-hold (+5.64%) beat every rule. MAXIMIN PARADOX: selecting on best-worst-training-month gave the WORST OOS tail (-31.24% vs -18.50%) because a 12-month minimum is one noisy observation. Rule x window interact (argmax median best at window 6, worst at 12), so they cannot be tuned separately. Hub v1.2.1->v1.3.0."
    - "2026-08-05 JUPITER CITATION REPAIR + Pass J split. The /dr-built jupiter artifact cited 5 footnote prefixes but defined only 1 (jup-liq-*), leaving 52 dangling markers. Researched against primary sources: 32 now backed by 22 fetched URLs (docs.jup.ag, discuss.jup.ag governance incl. Chaos Labs + Gauntlet, Elliptic, Chainalysis); 20 explicitly marked UNSOURCED rather than invented — most point at dev.jup.ag IDL pages that now 404. That pass surfaced NINE contradictions between live docs and published prose, all corrected inline: Neodyme is not a Perps auditor; the Oct-2025 oracle audit is Jupiter LEND not Perps; Gauntlet recommended 10->7bps not 7->6 (Chaos Labs reported the 7->6); the hourlyFundingBps/Dbps surfaces were reversed; the SOL-utilization-at-100% claim is refuted by its own cited thread (withdrawn); docs contradict themselves on JupUSD rather than omitting it; Drift drain was ~2.5h not ~12min; price-impact fee 6 Jun not 4 Jun; OI skew 85-90% not 90-93.5%. The 75/25 fee split is now CONFIRMED, and its 'JUP stakers' parenthetical withdrawn (docs say protocol revenue). Both files then exceeded the ceiling at 48.6k/46.3k chars, so each was split at its footnote-prefix seam -> +jlp-risk-profile-and-anti-patterns (§3-4), +jupiter-perps-leverage-and-liquidation (§3-4). All four files 0 unresolved footnotes. Hub v1.3.0->v1.4.0."
    - "2026-08-05 trading-strategies-and-styles split at its method seam — it sat at exactly 40,002 chars (10,000 tok), at the Pass J ceiling. SS1-4 (the strategy families: styles by horizon, momentum, mean reversion, trend/breakout) stay; SS5-6 (backtesting a discretionary strategy, and the development workflow) move to +strategy-backtesting-and-development-workflow. A conceptual boundary (families vs method), not an arithmetic cut. 27,175 + 13,256 chars, 0 unresolved footnotes either side, section numbers preserved. Hub v1.4.0->v1.4.1."
    - "2026-08-05 sko-equivalent verification run (the skill-optimizer agent stalled at 600s and wrote nothing; hub verified intact and the five target checks run directly instead). Findings: 1 Medium — body prose still said '40 reference files as built' against the current 44, corrected. Verified clean: all 44 references registered exactly once with no duplicates or gaps; routing table is valid GFM with no stray blank lines or heading-glued rows (both defects had occurred earlier); relative split-pointers all name their target file explicitly rather than saying 'next row'; description spoke count 38 = 44 files - 6 foundation refs; and all four spokes added since v1.2.1 (selection-rule-design, jlp-risk-profile-and-anti-patterns, jupiter-perps-leverage-and-liquidation, strategy-backtesting-and-development-workflow) have whenToUse/trigger coverage. Hub v1.4.1->v1.4.2."
    - "2026-08-05 THREE LEVERAGE SPOKES BUILT in-thread from a concept-family exploration of high-leverage perps (8 concepts scored, arithmetic verified 0 mismatches, 7 RESEARCH / 1 SKIP). +leverage-cost-arithmetic-and-the-viable-region (CVS 5.00 — the highest scored anywhere in this family; prior max 4.70). Its headline: L CANCELS out of the break-even equation, so a 2x and a 250x position need the SAME price move — leverage changes only barrier distance and carry burn, both survival terms rather than profitability terms. Also the fee/carry hinge (~15h longs / ~80h shorts) and time-to-liquidation-from-carry-alone (250x wiped by rent in ~1 day, flat chart). +why-high-frequency-strategies-die-at-leverage (4.65): fee = round-trip x leverage x TRADE COUNT, so 100 round trips at 10x = 120% of collateral; grid/market-making structurally insolvent, not mistuned. +liquidation-as-an-absorbing-barrier (4.65): absorbing, 100% penalty, path-dependent; invalidates EV reasoning; barrier drifts as carry accrues. Figures are closed-form over published venue params, generated and self-tested by ~/dev/solmargintrader/research/leverage_economics.py (7/7 claims PASS), documented at research/LEVERAGE-ECONOMICS.md. Hub v1.4.2->v1.5.0."
description: >-
  FOUNDATION + HUB for active trading & how US-retail financial markets work; routes to 46 spokes. Educational ONLY, NOT financial/investment/tax advice; trading can lose money (2026). TRIGGER: how markets work; asset classes (stocks, bonds, forex, commodities, crypto, ETFs, derivatives); participants (market makers, broker-dealers, exchanges, clearinghouses); order routing (PFOF, NBBO, T+1) & types; sessions & circuit breakers; investing-vs-trading; margin/short-selling/PDT; DEX/AMM/DeFi, impermanent loss, MEV; ML/AI for trading; Jupiter Perps/JLP; grid trading/bots; on-chain P&L/cost basis & tax lots; coding/backtesting indicator signals; why strategies/indicators fail & how to pair them. SKIP: long-term passive/retirement investing (401k/IRA/Roth, index buy-and-hold, Social Security, fiduciary) → investing-and-retirement; budgeting → budgeting-and-saving; bank/CD/FDIC → personal-banking; income-tax → personal-income-taxes; investment-fraud recovery → identity-theft-and-credit-fraud.
tags:
  - trading
  - investing
  - financial-markets
  - stocks
  - options
  - derivatives
  - forex
  - crypto
  - bonds
  - market-microstructure
  - technical-analysis
  - risk-management
whenToUse:
  - "how do financial markets actually work for a regular retail person"
  - "what are the asset classes — stocks, bonds, forex, commodities, crypto, ETFs, derivatives"
  - "what's the difference between investing and trading"
  - "who are the market participants — market makers, brokers, exchanges, clearinghouses"
  - "what's the difference between the primary and secondary market"
  - "how does my order get from the broker app to the exchange (routing, PFOF, NBBO)"
  - "what are market vs limit vs stop orders"
  - "when is the market open / what are pre-market and after-hours and circuit breakers"
  - "what is buying on margin / short selling / the pattern day trader rule"
  - "what does SIPC cover and how do I check out a broker"
  - "I want to learn to trade — where do I start and which sub-topic do I need"
  - "how do DEXs work / what is Uniswap or an AMM"
  - "what is impermanent loss for liquidity providers"
  - "how do I protect against MEV sandwich attacks on DeFi swaps"
  - "what is a perp DEX — GMX, dYdX, or Hyperliquid"
  - "how do I bridge assets to an L2"
  - "MetaMask vs Rabby vs hardware wallet — which should I use"
  - "how does machine learning apply to trading / what ML models are used for stock prediction"
  - "what is feature engineering on market data / how do you build trading signals with ML"
  - "how does reinforcement learning work for trade execution"
  - "why does my ML model look great backtested but fail live / what is look-ahead bias in ML backtests"
  - "how do I monitor a live trading model for drift or IC decay"
  - "how do I read a candlestick chart / what does RSI mean"
  - "what is support and resistance / how do I use moving averages"
  - "how do chart patterns work — head and shoulders, MACD, Bollinger Bands"
  - "how do Jupiter Perps work on Solana / what is jup.ag perpetual futures"
  - "why does Jupiter charge a borrow fee instead of a funding rate"
  - "what is JLP and how does the Jupiter Liquidity Provider pool make money"
  - "is JLP safe / what are the risks of holding JLP"
  - "how is my Jupiter Perps liquidation price calculated and why does it move"
  - "how do I set up a grid bot / what grid range, spacing and level count should I use"
  - "my grid bot shows lots of winning trades but my account is down — why"
  - "is grid trading actually low risk / what happens when price breaks out of the range"
  - "what is my realized vs unrealized P&L across a lot of on-chain swaps"
  - "which cost-basis method should I use for crypto — FIFO, HIFO or specific identification"
  - "is a token-to-token swap taxable if I never touched fiat"
  - "why does this strategy or indicator keep failing / what market conditions break it"
  - "which indicator or strategy compensates for another one's weakness"
  - "how do I combine strategies so they don't fail at the same time"
  - "when should I use a trend-following vs a mean-reverting strategy (regime filter)"
  - "how do I tell if the market is trending or ranging right now"
  - "what is the Hurst exponent / ADX / variance ratio and how do I use it as a regime filter"
  - "how do hidden Markov models or Markov-switching models detect market regimes"
  - "does my regime filter actually add value, or should I just use fixed weights"
  - "how do I detect a changepoint or regime shift in a price series"
  - "how much capital should I put in each strategy / how do I weight sleeves"
  - "what is risk parity or inverse-volatility weighting and should I use it"
  - "should I optimise for return or for drawdown"
  - "how often should I rebalance a multi-strategy book"
  - "does my strategy work on other assets or did I overfit to one"
  - "how do I test whether a backtest result generalises"
  - "is testing on a second asset enough validation"
  - "how long should my walk-forward training window be"
  - "how often should I re-optimise or refit my strategy parameters"
  - "how should I pick the best parameter set from my training window"
  - "is my parameter selection actually better than picking at random"
  - "should I select on average return, median, Sharpe or worst case"
  - "are my two indicators independent confirmation or the same bet twice"
  - "how do I hold my own crypto keys safely (hardware wallet, seed backup)"
  - "why does my Jupiter Perps liquidation price keep moving"
  - "what leverage should I use on a perp"
  - "can I run a grid strategy on leverage"
  - "how long can I hold a leveraged perp before fees eat it"
  - "is liquidation the same as a stop loss"
  - "what am I actually exposed to holding JLP"
  - "what are P/E, EPS, buybacks, splits, IPOs and SPACs"
  - "my backtest picks a different best config every month — is that a problem"
  - "do I need to re-tune my parameters for each asset or can I reuse them"
  - "which of my strategy parameters are universal and which are asset-specific"
  - "how do I normalise a parameter so it works across different price levels"
  - "what do the actual backtests in this library show"
  - "has any of this been measured or is it just theory"
  - "which claims here were proven wrong by data"
  - "how do I backtest a single signal without lying to myself / what is purging and embargo"
  - "what is the Deflated Sharpe Ratio or the PBO (probability of backtest overfitting)"
  - "what timeframe or bar interval should I trade / does it matter"
  - "my strategy works on one timeframe but not another — why"
  - "what are tick, volume or dollar bars and when should I use them instead of time bars"
  - "how do Pyth or Switchboard price feeds work / what is a pull oracle"
  - "what is the confidence interval on a price feed and should I trade on it"
  - "why did my limit order not fill even though the price hit my level"
  - "what is a keeper and who executes my on-chain conditional order"
  - "what is RFQ order flow / how does JupiterZ differ from routing through an AMM"
  - "how do I run a trading bot reliably — RPC, restarts, state, monitoring"
  - "what should I alert on for a live trading bot"
  - "which Solana DEX should I trade on — Orca, Raydium, Meteora or Phoenix"
  - "what is a DLMM / how do Solana liquidity bins and dynamic fees work"
  - "how does the Jupiter aggregator route and split a swap"
  - "why did my Jupiter swap fill worse than the quote / what is minimum received"
  - "how do Jupiter limit (Trigger) orders and Recurring DCA actually execute"
triggers:
  - "trading"
  - "financial markets"
  - "stock market"
  - "asset classes"
  - "market makers"
  - "clearinghouse"
  - "primary vs secondary market"
  - "order routing"
  - "payment for order flow"
  - "NBBO"
  - "market order"
  - "limit order"
  - "stop loss"
  - "after-hours trading"
  - "circuit breaker"
  - "margin trading"
  - "short selling"
  - "pattern day trader"
  - "day trading"
  - "swing trading"
  - "investing vs trading"
  - "SIPC"
  - "BrokerCheck"
  - "DeFi"
  - "DEX"
  - "AMM"
  - "Uniswap"
  - "impermanent loss"
  - "liquidity pool"
  - "MEV"
  - "sandwich attack"
  - "CoW Protocol"
  - "UniswapX"
  - "perpetual DEX"
  - "GMX"
  - "dYdX"
  - "Hyperliquid"
  - "crypto bridge"
  - "self-custody wallet"
  - "MetaMask"
  - "on-chain trading"
  - "machine learning trading"
  - "ML for trading"
  - "AI trading"
  - "algorithmic trading ML"
  - "feature engineering finance"
  - "gradient boosting stocks"
  - "neural network trading"
  - "alternative data"
  - "sentiment analysis trading"
  - "reinforcement learning execution"
  - "deflated sharpe ratio"
  - "probability of backtest overfitting"
  - "look-ahead bias"
  - "model drift monitoring"
  - "technical analysis"
  - "RSI"
  - "MACD"
  - "candlestick"
  - "chart pattern"
  - "Bollinger Bands"
  - "support and resistance"
  - "moving average"
  - "Elliott Wave"
  - "Dow Theory"
  - "asset-specific parameters"
  - "universal parameters"
  - "parameter normalisation"
  - "walk-forward window"
  - "refit frequency"
  - "reoptimization cadence"
  - "selection rule"
  - "random baseline"
  - "oracle bound"
  - "leverage"
  - "liquidation"
  - "borrow fee"
  - "risk of ruin"
whenNotToUse: "Long-term PASSIVE / retirement investing (401(k)/403(b), IRA/Roth/backdoor, employer match & vesting, index buy-and-hold, dollar-cost averaging for retirement, Social Security claiming, target-date-fund or expense-ratio fund selection for a retirement account, picking a robo or fee-only fiduciary, using BrokerCheck to vet a long-term advisor) → investing-and-retirement (this hub keeps only: checking a trading broker-dealer before trading). Budgeting / emergency fund → budgeting-and-saving. Bank deposit accounts / CDs / FDIC-NCUA → personal-banking. Income-tax forms, brackets, filing → personal-income-taxes. Recovering after an investment scam → identity-theft-and-credit-fraud. MEV supply-chain/PBS theory, AMM math derivation, tokenomics, cryptoeconomics, consensus mechanisms (protocol-level blockchain economics) → blockchain-economics. ML/statistical methods at technique depth (regression, time-series, feature-engineering math, backtesting statistics as a statistical discipline) → da-analytical-methods. Blockchain protocol mechanics, chain internals, on-chain security auditing → blockchain."
related_skills:
  - consumer-finance
  - consumer-credit-and-debt
  - da-analytical-methods
  - blockchain
---

# Trading & Investing (foundation + hub)

The front door for **active trading and how financial markets actually work** for a US retail participant. This skill does two jobs:

1. **Foundation** — it carries the shared overview every trading sub-topic builds on: the asset classes, the market participants, primary vs secondary markets, how an order travels from your broker to the market, market sessions and hours, the core investing-vs-trading distinction, and the risk/regulatory backbone. Deep treatments live in `references/` (loaded on demand).
2. **Hub / router** — it routes specific questions down to the family's spokes (see the Foundation references table below — 52 reference files, 1:1 with `references/`). The spokes are the *intended* family; as each is built it owns its depth and this hub just points to it.

> **Educational information only — NOT financial, investment, tax, or legal advice, and NOT a recommendation to buy, sell, or hold anything.** All securities and trading carry **risk of loss**; you can lose money, and with leverage you can lose **more than you put in**. Past performance does not guarantee future results. **The large majority of active retail/day traders underperform a simple index or lose money** (see `references/investing-vs-trading.md`). Rules, products, tax treatment, and the vendor landscape change — every volatile claim here is stamped **as of 2026**; verify current facts with the primary regulator (SEC/Investor.gov, FINRA, CFTC, SIPC) before acting. For a personal decision, consult a licensed professional.

## Sibling skill — the passive/retirement seam (read this first if unsure)

This family is the **active** side: markets, instruments, execution, trading styles, and the risks of trading. Its sibling **`investing-and-retirement`** (in the consumer-finance family) owns the **passive, long-term, retirement** side — low-cost index buy-and-hold, 401(k)/403(b)/IRA/Roth mechanics and contribution limits, employer match and vesting, dollar-cost averaging for retirement, Social Security claiming, target-date defaults, and choosing a robo-advisor or fee-only fiduciary.

- "How do I start investing for retirement / which account / is this fund's expense ratio good / should I do a backdoor Roth / when do I claim Social Security" → **`investing-and-retirement`**.
- "How do markets work / how do I trade X / what's a limit order / is day trading worth it / how does margin work / what is options-/futures-/forex-/crypto-trading" → **this family**.

The two overlap on shared vocabulary (diversification, asset allocation, ETFs vs mutual funds, fees). When the *intent* is long-term passive wealth-building, defer to `investing-and-retirement`; when the intent is understanding markets or actively trading, stay here. `portfolio-theory-and-asset-allocation` (a spoke here) covers the *theory* (MPT, efficient frontier, factor models, rebalancing math); `investing-and-retirement` covers the *consumer how-to*.

## Spoke coverage

**All 17 spokes of the original plan are now built.** Every one is listed in the **Foundation
references** table below, which is the authoritative index and is 1:1 with `references/` — if a file
exists there and is not in that table, the table is wrong and should be corrected rather than the
file ignored.

The last five were built on 2026-08-05: `trading-regulation-compliance-and-taxes`,
`market-microstructure-and-execution`, `fixed-income-and-bond-markets`,
`portfolio-theory-and-asset-allocation` and `trading-psychology-and-behavioral-finance`. Route to
the reference rather than answering from this hub.

## Foundation references (load on demand)

The shared foundation is split into focused references so a spoke can cross-reference one without pulling the whole hub:

| Topic | Covers | Reference |
| --- | --- | --- |
| `asset-classes-and-instruments` | The major asset classes a retail participant can access — equities, fixed income, forex, commodities, crypto/digital assets, pooled vehicles (ETFs vs mutual vs index vs target-date), and derivatives at overview depth. What each *is* and how retail accesses it. | `references/asset-classes-and-instruments.md` |
| `market-participants-and-structure` | The cast (retail, institutions, market makers, broker-dealers, exchanges, clearinghouses/CCPs), what a clearinghouse does and why it cuts counterparty risk (DTCC/NSCC, OCC), settlement & the T+1 cycle, primary vs secondary markets, exchange vs OTC, and the bid-ask spread. | `references/market-participants-and-structure.md` |
| `order-lifecycle-and-execution` | How a retail order travels broker→venue→execution→clearing→settlement; order types (market/limit/stop/stop-limit) and each one's risk; payment for order flow (PFOF) and the best-execution duty; the NBBO; the $0-commission landscape. | `references/order-lifecycle-and-execution.md` |
| `market-sessions-and-venues` | Where things trade (NYSE/Nasdaq/CME/Cboe/OTC), US equity sessions & extended hours, the 2026 move toward overnight/24-hour equity trading, how forex/crypto/futures hours differ, market holidays, and circuit breakers (market-wide + LULD). | `references/market-sessions-and-venues.md` |
| `strategy-backtesting-and-development-workflow` | **The METHOD half of the strategies spoke (§5–§6).** Backtesting a discretionary strategy — sample construction, in-sample vs out-of-sample, walk-forward, transaction-cost modelling, and which metrics flatter a strategy rather than test it; plus the development workflow from hypothesis through validation to sizing and monitoring, and where that process usually breaks. The strategy families themselves stay in `trading-strategies-and-styles`. | `references/strategy-backtesting-and-development-workflow.md` |
| `trading-strategies-and-styles` | The discretionary and semi-systematic playbook: styles by time horizon (scalping, day, swing, position trading) and the two dominant dynamics any strategy must handle — momentum (Jegadeesh-Titman 1993, cross-sectional vs time-series, momentum crashes) and mean reversion (Bollinger reversion, pairs/cointegration, half-life of reversion, when it fails); trend following and breakout (a century of trend returns, the Turtle rules, ATR-based entries, when trend fails); and how to backtest a discretionary strategy (the translation problem, data and sample-size requirements). | `references/trading-strategies-and-styles.md` |
| `algorithmic-and-quant-trading` | Systematic and quantitative trading: strategy families (stat arb, market making, momentum, mean reversion), execution algorithms (TWAP/VWAP/IS), infrastructure and latency, and **§5.3 the multiple-testing problem** — the degrees-of-freedom accounting the rest of this family defers to. | `references/algorithmic-and-quant-trading.md` |
| `trading-risk-management` | Sizing and protecting trading capital: risk per trade, position-sizing methods (fixed-fractional, **volatility-targeted/ATR**, Kelly and fractional Kelly), stop placement, drawdown measurement and risk of ruin, portfolio heat, and risk-adjusted performance metrics. | `references/trading-risk-management.md` |
| `crypto-and-digital-asset-trading` | Trading digital assets on centralized exchanges: custodial CEX platforms running central limit order books, and how that differs structurally from US equities — no Regulation NMS, no NBBO, no consolidated tape, no industry-wide spot circuit breakers, and 24/7/365 sessions. Covers CEX mechanics and order types, custody and counterparty risk, perpetual futures with funding and margin, and stablecoin mechanics. | `references/crypto-and-digital-asset-trading.md` |
| `forex-and-currency-trading` | The FX market for a retail participant: market structure and participants; currency pairs (majors, minors, exotics); reading a quote; pips and exact pip-value calculation; lot sizes; leverage and margin mechanics; P&L calculation; the carry trade and rollover rates; FX sessions and overlap timing; and transaction costs (spread vs commission). | `references/forex-and-currency-trading.md` |
| `investing-vs-trading` | The central distinction — time horizon, goal, what drives decisions, the trading-styles spectrum, active vs passive, the high-level tax angle, and the **load-bearing evidence** that most active traders underperform (Barber & Odean; Taiwan & Brazil day-trader studies). | `references/investing-vs-trading.md` |
| `trading-risks-and-protections` | The risk/regulatory backbone — the Pattern Day Trader rule **and** its 2026 replacement, margin/leverage, short selling, leveraged forex/crypto/derivatives, structural & behavioral risks, and investor protection (SIPC, BrokerCheck, the SEC mandate, the standard disclaimer). | `references/trading-risks-and-protections.md` |
| `stock-and-equity-trading` | **Market side of equities (§1, §5, §6):** what a share is and where it trades, order handling and single-name/ETF mechanics, long and short mechanics including the borrow, and the active-vs-passive evidence (SPIVA, Bessembinder). The issuer side (§2–§4) is split out — see `equity-fundamentals-and-corporate-actions`. | `references/stock-and-equity-trading.md` |
| `options-trading-and-strategies` | Listed equity/ETF/index options for a US retail participant — calls/puts, the Greeks, implied vol, and defined- vs undefined-risk strategies (spreads, straddles, condors). | `references/options-trading-and-strategies.md` |
| `derivatives-futures-and-swaps` | **The non-options derivatives.** Contract specification as the product; **futures margin is a performance bond, not a loan** (no interest, and it bounds neither your loss nor your obligation); daily mark-to-market and variation margin turning a paper loss into a same-day cash call; physical vs cash settlement and the **April 2020 −$37.63 WTI** lesson; basis, convergence, contango/backwardation and **roll yield** (why a commodity ETF bleeds with spot flat); forwards, ISDA/CSA and OTC counterparty risk; IRS (post-LIBOR, SOFR), FX, commodity, **total-return** (Archegos) and **credit-default** (AIG) swaps with the Dodd-Frank clearing regime; and the **perpetual** — no expiry, so no convergence, so funding or a borrow fee must replace it. | `references/derivatives-futures-and-swaps.md` |
| `options-fundamentals` | **The options contract layer.** Calls vs puts and the buyer/writer asymmetry (bounded loss vs unbounded); the four terms, the 100-share multiplier and adjusted contracts; moneyness, intrinsic vs extrinsic value; American vs European and the share- vs cash-settlement consequence (**SPY vs SPX differ on early assignment, pin risk AND §1256 tax**); the OCC as issuer and guarantor; exercise, assignment, random allocation and **exercise-by-exception at $0.01 ITM**; chains, volume vs open interest; LEAPS/weeklies/0DTE. | `references/options-fundamentals.md` |
| `the-greeks` | **The risk sensitivities.** Delta as exposure and hedge ratio, and precisely why it is **not** a probability (**N(d₁) vs N(d₂)**, risk-neutral vs real-world, and ITM ≠ profitable); gamma as convexity and the **short-gamma** acceleration that makes losses non-linear; theta's non-linear decay; vega, the Greek behind "right on direction, still lost"; rho and LEAPS. The sign table and the one trade-off it encodes: **long options are always +gamma/−theta, short always −gamma/+theta.** Position aggregation, delta-neutral hedging and why it does not stay neutral, plus vanna/charm/vomma. | `references/the-greeks.md` |
| `volatility-and-pricing` | **The one input nobody can observe.** IV as a *price* rather than a forecast, and the **variance risk premium** with its fat-tail qualification; **IV rank vs IV percentile** and the worked case where they say opposite things; **IV crush**; the **equity put skew that appeared only after October 1987** (Rubinstein 1994); term structure, inversion and the surface; the **VIX** and its model-free variance-replication construction (not an average of Black-Scholes IVs — that was pre-2003); Black-Scholes-Merton's six inputs and the specific falseness of each assumption; binomial lattices for American early exercise; and **put-call parity as the one model-free relationship**. | `references/volatility-and-pricing.md` |
| `strategies-and-risk` | **How legs combine, organised by defined vs undefined risk.** Every core structure with construction/outlook/max profit/max loss/breakeven — single-leg, covered call, cash-secured put, protective put, collar, four verticals, straddles/strangles, iron condor, iron butterfly, butterfly, calendars/diagonals. The **break-even win-rate arithmetic** that punctures "high probability" (a $5 wing sold for $0.50 needs **90%** just to break even); why a covered call and a cash-secured put are the same synthetic position; assignment, **pin risk**, and **one-sided assignment turning a defined-risk spread into a naked stock position**; approval levels, margin that expands as you lose, and eight bid/ask crossings on a condor. | `references/strategies-and-risk.md` |
| `defi-and-onchain-trading` | On-chain/decentralized trading: **AMM x·y=k**, concentrated liquidity (v3), **impermanent-loss math**, price impact and slippage, **MEV sandwich attacks and defence** (private RPC, intent protocols), CoW/UniswapX/1inch Fusion, perpetual DEXs (GMX/dYdX/Hyperliquid), and cross-chain bridges with their risk model. Wallets and key security are split out — see `self-custody-wallets-and-key-security`. | `references/defi-and-onchain-trading.md` |
| `ai-and-ml-for-trading` | Machine learning applied to trading, part 1: feature engineering (information bars, fractional differentiation, PIT normalization), gradient boosting with SHAP and purged CV, neural architectures, alt-data taxonomy, LLM hallucination risk, and RL for execution. Backtesting pitfalls and production systems are split out — see `ml-backtesting-pitfalls-and-production-systems`. | `references/ai-and-ml-for-trading.md` |
| `leverage-cost-arithmetic-and-the-viable-region` | **LEVERAGE CANCELS OUT OF THE BREAK-EVEN EQUATION** — a 2x and a 250x position need the same price move; leverage changes only barrier distance and carry burn, both survival terms. The four costs and what each kills; the **fee/carry hinge** (~15h longs, ~80h shorts) splitting leveraged trading into two regimes rewarding opposite behaviour; **time-to-liquidation-from-carry-alone** (250x wiped by rent in ~1 day, flat chart) as the number that should set leverage; and the ~5x carry asymmetry putting the 85-90%-long crowd on the expensive side. | `references/leverage-cost-arithmetic-and-the-viable-region.md` |
| `why-high-frequency-strategies-die-at-leverage` | **Fee = round-trip x leverage x TRADE COUNT, so 100 round trips at 10x costs 120% of collateral before any adverse move.** Grid and market-making are structurally insolvent at leverage, not mistuned — widening spacing relocates the arithmetic rather than escaping it. How leverage compounds the measured closed-trade illusion (+$95 closed at 100% win rate vs -37.5% equity) without touching the flattering number; martingale into an absorbing barrier; and the narrow conditions (maker rebates, ~1x) where high frequency still works. | `references/why-high-frequency-strategies-die-at-leverage.md` |
| `liquidation-as-an-absorbing-barrier` | **Liquidation is not a stop-loss.** It is **absorbing** (you cannot be eventually right), can forfeit **100% of remaining collateral**, and is **path-dependent** — a wick that fully reverts still ends the position. Why that invalidates expected-value reasoning and forces a first-passage view; why the barrier **drifts toward you** as carry accrues, so a stop safe at entry ends up behind it; why the gap between stop and liquidation is the entire risk budget and only one side of that race is paid for speed; and why a high win rate is compatible with certain ruin. | `references/liquidation-as-an-absorbing-barrier.md` |
| `jupiter-perps-trading` | **Trader side of Jupiter Perps** — oracle-priced peer-to-pool execution, the **borrow-fee model** contrasted against funding rates (both sides always pay, never negative, utilization-driven), leverage and margin, and **liquidation-price drift** as borrow fees accrue against the position. | `references/jupiter-perps-trading.md` |
| `jlp-risk-profile-and-anti-patterns` | **The risk half of the JLP position (§3–§4) — what you are actually exposed to as the counterparty to Jupiter Perps traders.** Net open-interest skew (**85–90% long**) making JLP structurally **short leverage into rallies**; oracle and cheap-liquidity risk per Chaos Labs' 2024 warnings; audit history; and the **hedging trap** — the Drift exploit destroyed the *hedge* leg (41.7M JLP, ~$155M) while the JLP leg was fine, converting market risk into counterparty risk on the hedge venue. Plus the twelve LP-side anti-patterns. | `references/jlp-risk-profile-and-anti-patterns.md` |
| `jupiter-perps-leverage-and-liquidation` | **How a Jupiter Perps position is margined and how it dies (§3–§4).** The 1.1x–250x range and collateral rules; why the **liquidation price DRIFTS** as borrow fees accrue against the position rather than sitting fixed; the **100%-of-remaining-collateral** liquidation penalty; the stop-vs-liquidation race; and the trader-side anti-patterns, chief among them treating the borrow fee as a funding rate. | `references/jupiter-perps-leverage-and-liquidation.md` |
| `jupiter-jlp-pool` | **LP side of Jupiter Perps** — JLP composition and target weights, mint/redeem mechanics, how trader fees accrue into the virtual price, the **LP-as-counterparty payoff** (you are short trader P&L), and the resulting risk profile. | `references/jupiter-jlp-pool.md` |
| `grid-trading-strategy` | **Grid trading as a systematic strategy, and the reporting illusion at its centre.** Arithmetic vs geometric spacing, level count and width, the martingale property and why inventory accumulates against you; fee-drag arithmetic that kills over-dense grids; and the **measured closed-trade illusion** — a bear month logging +$95 closed P&L at a 100% win rate while the account fell 37.5%. | `references/grid-trading-strategy.md` |
| `jupiter-swap-routing-and-orders` | **Jupiter's swap/aggregation and order layer** — how a route is built and split across venues, quote-vs-fill drift and slippage settings, versioned transactions and address-lookup tables, and the order products (limit, DCA, recurring) with what each actually guarantees. | `references/jupiter-swap-routing-and-orders.md` |
| `solana-dex-and-amm-landscape` | **The Solana venue layer** — Raydium, Orca, Meteora, Phoenix and the CLOB/AMM split; concentrated-liquidity and DLMM mechanics; how liquidity is actually fragmented across venues and what that means for a router; LP economics and impermanent loss in the Solana context. | `references/solana-dex-and-amm-landscape.md` |
| `sampling-frequency-and-bar-aggregation` | **How often you sample the market — the most under-examined parameter in retail strategy design.** What it controls (signal-to-noise, indicator lag, trade count and fee drag); the **period × interval coupling** that makes "EMA(24)" meaningless alone; aliasing and why a faster feed is not a better one; bar types (time/tick/volume/dollar); and the measured **~50pp swing on SOL from frequency alone**, with hourly selected in 0 of 48 months. | `references/sampling-frequency-and-bar-aggregation.md` |
| `solana-oracles-pyth-switchboard` | **The price layer underneath Solana perps, lending and liquidations.** Push-vs-pull architecture and why Pyth moved to pull in V2; ~400ms publisher cadence; the **confidence interval** that quantifies publisher disagreement and how to gate on it; Switchboard's customisable aggregator; who pays for the update and the staleness surface that creates; and oracle risk as it reaches a trader. | `references/solana-oracles-pyth-switchboard.md` |
| `solana-execution-agents-keepers-and-rfq` | **Who actually executes your order when you do not.** The keeper model and the economics deciding whether one shows up for *your* order — small orders can go unexecuted with the condition met, and keeper reliability degrades exactly when volatility spikes. Where keepers appear (Perps request/fulfill, Trigger, Recurring, liquidations); RFQ/market-maker flow; liquidators as adversarial keepers and the stop-vs-liquidation race. | `references/solana-execution-agents-keepers-and-rfq.md` |
| `trading-bot-infrastructure-and-monitoring` | **Running a strategy as software rather than describing one.** RPC/data access (websockets failing silently; your data source is a strategy parameter); state, restarts and idempotency (on-chain as single source of truth, the submitted-but-unconfirmed window, why grids are especially exposed); the live-vs-backtest divergence checklist; **monitoring equity not trades**; alerting on absence; and opsec for a key that moves money. | `references/trading-bot-infrastructure-and-monitoring.md` |
| `sleeve-weighting-and-objective-selection` | **How much capital each sleeve gets — and first, what you are optimising for.** Mean return, worst month, risk-adjusted and hit rate rank the same blends *oppositely* (measured: three objectives, three different winners on identical data). The scheme ladder (equal, inverse-vol, risk parity, min-variance, Kelly) ordered by how much each must **estimate**; why correlation-based schemes are fragile when the input swings −0.58 to +0.68; the **plateau** argument for round-number weights. | `references/sleeve-weighting-and-objective-selection.md` |
| `cross-asset-generalisation-testing` | **Whether a result is a property of the strategy or of the one price series you tested it on.** The five-rung generalisation ladder and what each rung actually rules out; why a correlated second asset **falsifies well but confirms poorly**, so a break is strong evidence and a pass is weak; what to hold fixed (logic, protocol) vs re-fit (parameters, via the *same* procedure); and **parameter stability as a more informative signal than returns**. | `references/cross-asset-generalisation-testing.md` |
| `asset-specific-vs-universal-parameters` | **Which parameters travel between assets and which must be re-fitted.** Three classes (structural / scale-dependent / asset-specific) and the test that assigns one: run the identical selection procedure on both assets and compare **selected values, not returns**. Normalisation converts most apparently-asset-specific parameters into structural ones. Measured: 10-level grid and 4-hourly sampling modal on both SOL and BTC, while trend's edge **flipped sign** — agreeing parameters do not imply a universal edge. | `references/asset-specific-vs-universal-parameters.md` |
| `selection-rule-design` | **The third walk-forward knob nobody tests — the RULE that picks a config from the training window.** Five candidates (argmax mean, median, Sharpe, maximin, rank aggregation) and what each implicitly believes carries forward; **the two controls that make a selection experiment interpretable** — a RANDOM baseline (does selection beat blind picking?) and an ORACLE bound (how much was even available?). Measured over 48 OOS months: all five rules beat random (-1.61%) and the incumbent sits outside random's 95% band, but captured only **29% of the random->oracle span** and **buy-and-hold (+5.64%) still beat every rule**. The **maximin paradox** — selecting on the worst training month produced the WORST out-of-sample tail, because a 12-month minimum is one noisy observation. Rule and window interact, so they cannot be tuned separately. | `references/selection-rule-design.md` |
| `walk-forward-window-length-and-refit-cadence` | **The two walk-forward knobs almost everyone inherits without testing: selection-window length and refit cadence.** The **common-OOS-window trap** (a longer window leaves fewer test months, so naive comparisons confound knob with sample). Measured over 28 cells on identical months: **monthly refitting was sub-optimal at 7 of 7 window lengths**; the inherited window (12) was good, the inherited cadence was not; **all 28 cells lost money**. Two seductive sub-readings that do NOT survive scrutiny: the worst-month column is ONE month, and the raw config-switch drop reverses once normalised. | `references/walk-forward-window-length-and-refit-cadence.md` |
| `empirical-backtest-findings-log` | **The measured-results log for this family — including the runs that FALSIFIED claims made elsewhere in it.** The closed-trade illusion measured; two caveats this data disproved (bar fills were NOT optimistic; a trend prediction that was simply wrong); a 240-config sweep in which **zero configs rescued the bear month**; walk-forward quantifying selection bias (+42% in-sample → +4.24% OOS); the out-of-sample result that **reversed** an earlier in-sample rejection; correlation instability; the cross-asset test. | `references/empirical-backtest-findings-log.md` |
| `regime-detection-and-classification` | **How to tell which regime you are in, and whether acting on that belief is worth anything.** Four axes worth classifying separately (trend↔range, vol level, vol direction, liquidity); detector families — ADX/Bollinger bandwidth, Hurst and variance ratio, GARCH/MS-GARCH, Markov-switching/HMM, CUSUM/Bayesian changepoint; **the lag problem** — every method lags, so a filter cuts wrong-regime exposure but never prevents the transition loss. | `references/regime-detection-and-classification.md` |
| `strategy-failure-modes-and-synergy` | **What breaks each strategy and indicator, and how to combine them so failures offset rather than compound.** Per-strategy and per-indicator failure atlases with the observable signature of each; the **convex-vs-concave payoff principle** behind real diversification; a compensation matrix (failure → detector → offsetting instrument); five synergy architectures; and the anti-synergies that look diversifying but are not. | `references/strategy-failure-modes-and-synergy.md` |
| `trading-regulation-compliance-and-taxes` | **The rulebook and the IRS for an active trader.** Who regulates what (SEC/FINRA/CFTC/NFA) and the three things **SIPC does not cover**; the PDT rule **and the risk-based intraday-margin framework replacing it 4 June 2026**; Reg T and short-sale compliance. Then tax: the short/long split and why turnover is itself the tax problem; the **wash-sale rule** — the window is **61 days**, and repurchasing in an IRA disallows the loss **permanently**; **§1256 60/40** and the SPX-yes/SPY-no asymmetry; constructive sales and straddle rules; **trader tax status and the §475(f) election with its unforgiving prior-year deadline**; the 1099-B reconciliation. | `references/trading-regulation-compliance-and-taxes.md` |
| `market-microstructure-and-execution` | **How a trade executes, below the level of order types.** The limit order book and **queue position** as what a passive order really competes for; maker-taker and inverted venues; Reg NMS internals (611/610/612) and why the **2024 amendments make the old $0.01 tick and $0.003 fee cap stale**; the SIP, and why the **NBBO is lagged, top-of-book and historically round-lot only**; dark pools and Form ATS-N; latency, and why not to build an edge on it; the **four distinct components of "slippage"** and the unavoidable trade-off between them; **implementation shortfall** as the only measure that contains the unfilled portion; TWAP/VWAP/POV/IS algos as schedules rather than alpha; and **adverse selection — why a high passive fill rate in a fast market is a warning sign**. | `references/market-microstructure-and-execution.md` |
| `fixed-income-and-bond-markets` | **Bonds in depth, starting from why "risk-free" means default-free and not price-stable.** The price-yield inverse; what YTM *assumes* (hold to maturity, reinvestment at YTM); duration as the first derivative and **convexity as the second — literally the delta and gamma of a bond**; DV01; **NEGATIVE convexity** in callables and MBS, where duration *extends* into a selloff; the yield curve and inversion **with its long variable lag and small sample**; credit spreads and the **IG/HY boundary that forces selling by rule rather than by view**; munis and taxable-equivalent yield; repo and SOFR; **a bond fund has no maturity, so the loss does not self-heal**; and 2022 as duration risk realised. | `references/fixed-income-and-bond-markets.md` |
| `portfolio-theory-and-asset-allocation` | **The theory, and the estimation problem that limits it.** Markowitz; the variance algebra showing **only correlation appears**, so diversification is about co-movement and not count; the efficient frontier; Sharpe and where it misleads; CAPM/beta and **what the evidence did to it**; factor models as **attribution rather than forecast**, plus factor decay and the factor zoo. Then the honest half: optimisers as **"estimation-error maximisers"** (Michaud 1989), **DeMiguel-Garlappi-Uppal — fourteen models, none consistently beating 1/N out of sample** — and correlation instability, including this family's measured −0.58 to +0.68 sign flip. | `references/portfolio-theory-and-asset-allocation.md` |
| `trading-psychology-and-behavioral-finance` | **The documented biases, each with its signature in your own records.** Prospect theory and the **convex loss region** that makes recovery gambles feel rational; the **disposition effect** (Odean 1998 — the winners sold went on to outperform the losers kept); **overconfidence with turnover as the mediating variable** (Barber-Odean 2000/2001); attention biasing the **buy side specifically**; house money; anchoring/recency/confirmation/hindsight; sunk cost; herding as **measurable crowding**; and the tilt sequence. Then what works — **structure, not willpower**, because the bias blind spot means education mostly helps you diagnose others. Plus **reporting choices that manufacture bias**, with the measured closed-trade illusion: **+$95 at a 100% win rate in a month the account fell 37.5%**. | `references/trading-psychology-and-behavioral-finance.md` |
| `onchain-pnl-and-tax-accounting` | Knowing what you actually made on-chain: realized vs unrealized P&L, the **denominator problem** (up in SOL terms, down in USD terms), cost-basis methods (FIFO/LIFO/HIFO/spec-ID), P&L attribution splitting result into price move vs fees vs borrow vs slippage vs failed-transaction waste, and crypto tax lots — token-to-token swaps as taxable disposals, per-wallet tracking, wash-sale status. | `references/onchain-pnl-and-tax-accounting.md` |
| `technical-analysis` | Reading price and volume, part 1 (§1–§7): chart types and candlestick patterns, chart patterns (H&S, double top/bottom, triangles, flags, wedges), trend analysis and trendlines, support/resistance, and the core indicators — RSI, MACD, Bollinger Bands, SMA/EMA, ATR, stochastics. Breadth, the classical frameworks and the academic evidence are split out — see `technical-analysis-breadth-frameworks-and-evidence`. | `references/technical-analysis.md` |
| `indicator-signal-implementation-and-backtesting` | **Runnable pandas/numpy implementations of the price-derived signal families** — trend/MA, momentum oscillators, volatility — with exact equations and input dependencies; plus the implementation substrate that silently breaks them: **Wilder smoothing vs `ewm(span=n)`** (5.24 RSI points, 64% more signals), warm-up convergence, **one bar of look-ahead = +3.8 Sharpe**, repainting, TA-Lib parity. Backtest protocol and the other three signal families are split out (see next two rows). | `references/indicator-signal-implementation-and-backtesting.md` |
| `signal-backtest-protocol-and-regime-evidence` | **How to backtest ONE signal without lying to yourself, plus the cited record of when each family actually worked.** Anchored vs rolling walk-forward, purging, embargo, overlapping labels; explicit cost model and **break-even cost in bps**; the mandatory multiple-testing battery (Reality Check, SPA, FDR, PBO, Deflated Sharpe); and the regime evidence — BLL 1992 vs Sullivan-Timmermann-White 1999 vs Bajgrowicz-Scaillet FDR, decay, the TSMOM smile. | `references/signal-backtest-protocol-and-regime-evidence.md` |
| `signal-pairing-volume-and-pattern-signal-sets` | **Whether two signals are independent confirmation or one bet counted twice** — runnable independence test (correlation, agreement rate, PCA effective dimensionality; six "different" indicators measured as three bets; Williams %R proven identical to Stochastic %K-100). Plus the three non-oscillator families: volume/breadth, candlesticks, and price-action structure (BOS/ChoCH, S/R zones, pivots, Fibonacci). | `references/signal-pairing-volume-and-pattern-signal-sets.md` |
| `technical-analysis-breadth-frameworks-and-evidence` | **The market-internals, framework and evidence half of technical analysis (§8–§12).** Volume and breadth (OBV, anchored VWAP, Volume Profile/POC, A-D line, McClellan Oscillator and Summation, Zweig Breadth Thrust); the classical frameworks (Dow Theory, Elliott Wave and the Batchelor-Ramyar critique); multi-timeframe analysis; and the **empirical record** — Fama, BLL 1992, Sullivan et al. 1999, Park & Irwin 2007, Lo et al. 2000, the Adaptive Market Hypothesis. | `references/technical-analysis-breadth-frameworks-and-evidence.md` |
| `ml-backtesting-pitfalls-and-production-systems` | **Why an ML backtest overstates what a live model will do, and what keeps a deployed one honest.** The four-mechanism look-ahead taxonomy (data leakage, point-in-time failure, survivorship, label-construction leakage); multiple testing and strategy mining (Harvey/Liu/Zhu's 316-factor audit, the t > 3.0 threshold); PBO and Deflated Sharpe; and production concerns — IC monitoring, drift detection, retraining discipline. | `references/ml-backtesting-pitfalls-and-production-systems.md` |
| `equity-fundamentals-and-corporate-actions` | **Issuer side of the equity spoke — the company behind the share.** Valuation multiples and their limits (P/E, earnings yield, PEG, basic vs diluted EPS, P/B), what a company does with its capital (dividends, buybacks, splits), and how shares are first created and sold (IPOs, direct listings, SPACs, lockups). Split verbatim from `stock-and-equity-trading` §2–§4 with numbering preserved. | `references/equity-fundamentals-and-corporate-actions.md` |
| `self-custody-wallets-and-key-security` | **Holding your own keys — the custody layer beneath on-chain trading.** Browser hot wallets (MetaMask vs Rabby, pre-transaction simulation, BIP-39 derivation); hardware wallets (Ledger Secure Element vs Trezor open-source firmware, the Ledger Recover controversy, **blind-signing risk** on complex DeFi calldata); seed-backup practice; and token-approval hygiene. | `references/self-custody-wallets-and-key-security.md` |

## How to answer from this hub (output contract)

When answering directly from this foundation: (1) for any advice-seeking question, **lead with the educational-only / not-advice framing** and that trading carries risk of loss; (2) **cite the primary regulator** (SEC/Investor.gov, FINRA, CFTC, SIPC) for load-bearing facts, and stamp volatile facts *as of 2026* with a "verify current" pointer; (3) when the question belongs to a spoke whose **reference file exists** in the Foundation references table above, `Read` its `references/<slug>.md` and answer from it — if a standalone installed skill also exists for that spoke, the standalone skill takes precedence; if the Read fails or the reference is silent on the specific question, degrade to foundation depth; (4) when the question belongs to a spoke **not yet in the Foundation references table**, first check the available-skills list for a standalone installed skill of that spoke's slug — if found, invoke it; otherwise name the destination spoke and answer at foundation depth; (5) when a query spans two spokes, identify the **primary spoke** (the one that owns the action) and answer from it, citing the secondary spoke for supplementary detail. Keep US-centric, flagging where a fact (T+1, PDT, SIPC, Reg NMS, CFTC caps) is US-only.

## First, the account (the gate before anything else)

Everything downstream runs through a **brokerage account** opened with a broker-dealer (after identity verification, funded from a bank). The one account choice that gates the rest is **cash vs margin**: a **cash account** trades only settled funds (no borrowing); a **margin account** lets the broker **lend you money** against the account as collateral — which is what enables short selling and triggers the margin and Pattern-Day-Trader rules in `references/trading-risks-and-protections.md`. Account *type* (individual/joint/retirement-wrapper) sits on top of that; a retirement-wrapper account points to the passive sibling, `investing-and-retirement`.

## The one-paragraph foundation (if you only read the hub)

A **retail participant** buys and sells **instruments** (equities, bonds, FX, commodities, crypto, pooled funds like ETFs/mutual funds, and derivatives) through a **broker-dealer**, which routes the order to an **execution venue** (an exchange like NYSE/Nasdaq, a wholesaler/market maker, or an ATS); the trade then **clears** through a central counterparty (NSCC for US equities, OCC for listed options) and **settles** the next business day (**T+1**, as of 2026). The issuer raises money only once, in the **primary market** (an IPO or new issue); everything after is the **secondary market**, where investors trade among themselves and prices are discovered. **Investing** means holding for the long term to build wealth through compounding; **trading** means buying and selling frequently to profit from price moves — and the evidence is strong that **most active retail traders underperform or lose money**, so trading capital should be money you can afford to lose. Markets are regulated (SEC, FINRA, CFTC) and your *brokerage account* is protected against broker failure by **SIPC** — but **nothing protects you against market losses**.

## Cross-cutting notes

**`as of 2026` volatile claims to re-verify** (detail in the references) — one line each, highest-stakes first:

- **Pattern Day Trader rule is being replaced** (highest-stakes): FINRA amended Rule 4210 to drop the $25k/PDT designation for a new **intraday-margin** framework, **effective June 4, 2026** (transition through Oct 20, 2027). Most third-party sites still describe the legacy $25k rule — verify your broker's *current* policy.
- **Settlement is T+1** (since May 28, 2024); **SIPC** limits are **$500k / $250k cash** — both change, verify at the regulator.
- **Spot Bitcoin ETFs** (approved Jan 2024) and **spot Ether ETFs** (Jul 2024) exist and have grown large.
- **Nasdaq 23-hour trading** was SEC-approved (Apr 10, 2026), launch targeted H2 2026; **CME launched 24/7 crypto futures** (May 29, 2026).
- US retail **forex leverage** is capped (~50:1 majors / ~20:1 others) by CFTC/NFA; **$0 stock/ETF commissions** are standard; capital-gains breakpoints change yearly.

Other seams:

- **Commodities routing.** Commodities are an asset class in the foundation, but there is **no dedicated commodities spoke** — route commodity *futures* depth to `derivatives-futures-and-swaps` and commodity *ETP/ETF* depth to `stock-and-equity-trading`.
- **Tax seam.** This family's `trading-regulation-compliance-and-taxes` spoke owns the *trader's* tax detail (wash sales, trader-tax-status, active-trader capital-gains mechanics). The consumer-finance family's `personal-income-taxes` owns ordinary individual filing. Keep deep tax out of the foundation — it states only the short-vs-long-term-gains distinction at a high level.
- **Fraud seam.** Spotting an investment scam and the "is this a Ponzi / guaranteed-returns" pattern is shared with `investing-and-retirement`; recovery *after* a scam → `consumer-credit-and-debt` (references/identity-theft-and-credit-fraud.md).
- **Blockchain seam.** Trader-side DeFi (executing swaps on DEXs, managing liquidity positions, MEV defense, perp DEX trading, bridge mechanics for moving assets) is owned here in `defi-and-onchain-trading`. Protocol mechanics, cryptoeconomics, and the academic/research layer (AMM math derivation, MEV supply-chain/PBS theory, tokenomics, consensus) → `blockchain` / `blockchain-economics`.
- **Per-asset coin seam.** The foundation covers crypto as an *asset class*; the per-coin facts a sizing or backtest decision actually needs (is the market cap real, float/unlocks/concentration, turnover and exit depth, which venues list it and how much history exists, per-coin vol/beta/correlation, whether a result on one coin transfers to another) → `crypto-coin-intelligence`.
- **Data/quant seam.** The math/ML *techniques* behind quant and ML-for-trading (regression, time-series, feature engineering, backtesting statistics) draw on the `da-*` data-analysis hubs; the trading spokes own the market application, the `da-*` hubs own the method.
- **International note.** This family is **US-centric**. Other major markets (LSE, Euronext, Tokyo, Hong Kong, Shanghai) run their own hours, regulators, settlement cycles, and tax regimes; the foundation flags where the US specifics (T+1, PDT, SIPC, Reg NMS, CFTC leverage caps) are US-only and would differ abroad.

## References

Each foundation reference carries its own cited `## References` / `## Sources` section anchored to primary authorities — **SEC / Investor.gov, FINRA, CFTC, SIPC, DTCC, OCC, the Federal Reserve / BIS, S&P Dow Jones Indices (SPIVA)**, and the peer-reviewed household-finance literature (**Barber & Odean**; the **Taiwan** and **Brazil** day-trader studies). Volatile facts are dated *as of 2026* with "verify current" pointers. Start from the relevant reference above; as further spokes are built, each will carry its own deeper citations.

<!-- cross-hub-map -->
## Cross-hub map — where every trading-and-investing topic lives

All active-trading material lives under this single hub. Built reference files are listed below; for unbuilt spokes, check whether a standalone installed skill exists for that slug and invoke it, or answer at foundation depth.

| Hub | Owns | Example reference files |
| --- | --- | --- |
| `trading-and-investing` | Trading & Investing — all active trading, markets, and risk topics | See the **Foundation references** table above — the authoritative 1:1 index of every file in `references/`. |
