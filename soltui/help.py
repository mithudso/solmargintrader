"""Plain-language help shared by hover tooltips and the F1 reference."""

from __future__ import annotations

HEADER_GLOSSARY = {
    "median sharpe": (
        "Sharpe ratio = mean return / volatility of returns (annualised): "
        "risk-adjusted performance, >0 means paid for the risk taken. This is "
        "the MEDIAN across all CPCV paths, not one backtest's number."),
    "iqr": (
        "Interquartile range: the spread between the 25th and 75th percentile "
        "of per-path Sharpe. Large IQR = the result depends heavily on which "
        "slice of history you test — less trustworthy."),
    "% paths +": (
        "Fraction of CPCV paths (regime-mixed train/test splits) where the "
        "Sharpe was positive. 100% of 15 is still only 15 paths."),
    "best backtest median net %": (
        "Net growth or decline (final / initial - 1) of the best rankable row, median across its CPCV "
        "paths, after costs. A simulation."),
    "chain": "The blockchain the row was read from.",
    "amount": "Units held, from the chain (`balanceOf`, `getTokenAccountsByOwner` or the native balance).",
    "price $": "USD price from Jupiter, DefiLlama or DexScreener at the time of the scan.",
    "value $ (wallet (live))": "Amount times price, read at scan time. A real balance, not a simulation.",
    "status": "Whether the row is in the total, and why not when it is not (airdrop flag, no price).",
    "holding": "The coin or position the contract belongs to.",
    "address": "The on-chain address of the contract or account.",
    "program": "The program or standard that owns the account (Token, Token-2022, ERC-20, position manager).",
    "explorer": "Link to the block explorer page for this address.",
    "source": "Where the figure comes from: backtest, paper, dry-run, dry-run LP or live LP.",
    "runs": "How many independent runs the row adds up (each on its own starting capital).",
    "net $": "Final minus initial equity inside the window, after fees, slippage and borrow.",
    "net % (source named)": (
        "Net growth or decline, final / initial - 1, over the window. The cell names its source; "
        "a bare percentage would read as real money."),
    "gross $": "Net P&L plus the fees, slippage and borrow paid inside the window.",
    "costs $": "Fees plus slippage plus borrow/funding paid inside the window.",
    "realized $": "Net result of the fills that closed risk inside the window.",
    "unrealized $": "Net P&L not yet realized: the mark on what is still open.",
    "contribution (source named)": (
        "Percentage points this row adds to its section's net %. The rows of a section sum to it."),
    "period": "The kind of period: a UTC day, an ISO week (keyed by its Monday) or a calendar month.",
    "best": "The period with the highest summed P&L, and that P&L.",
    "worst": "The period with the lowest summed P&L, and that P&L.",
    "date": "UTC calendar day.",
    "p&l $": "Equity change over the UTC day, after costs.",
    "cumulative $": "Equity change from the start of the window to the end of this day.",
    "cumulative % (source named)": "Cumulative net growth or decline since the window start.",
    "drawdown (source named)": "How far equity sits below its running peak (the opening value counts as a peak).",
    "backtest median net %": (
        "Net growth or decline of the backtest, final equity / initial equity - 1, taken as the "
        "MEDIAN across CPCV paths, after fees and slippage. A simulation, not a result in a "
        "real account."),
    "median ret": (
        "Median total return across CPCV paths over the tested window, "
        "after fees and slippage."),
    "median return": (
        "Median total return across CPCV paths over the tested window, "
        "after fees and slippage."),
    "trades": (
        "Total trades executed. Below 10 the engine refuses to rank the row "
        "(the evidence floor) — a great Sharpe on 6 trades is noise."),
    "paths": (
        "Number of CPCV paths evaluated. Nominal is C(blocks, k), but slow "
        "strategies lose warm-up blocks; fewer paths = weaker estimate."),
    "rankable": (
        "Rows with at least 1 path AND ≥10 trades — enough evidence to "
        "appear in a ranking at all."),
    "below floor": (
        "Rows the engine evaluated but refused: fewer than 10 trades. "
        "Counted separately, never mixed into rankings."),
    "positive": "Rankable rows whose median Sharpe is above zero.",
    "made money": "Rankable rows whose median return is above zero.",
    "best (rankable)": (
        "Highest median Sharpe among rankable rows only — below-floor rows "
        "are excluded no matter what they claim."),
    "claims sharpe": (
        "The Sharpe this below-floor row reports. Shown to make the point: "
        "on this few trades it would often top a naive ranking."),
    # NB: str.casefold() lowercases Δ to δ, so the key must be δ.
    "δ vs sol": (
        "Change in median Sharpe versus the SOL result the configuration was "
        "selected on. Large negative delta = does not transfer off-asset."),
    "horizon": (
        "Bar-interval class from research/sweep.py: short/medium/long map to "
        "different intervals and parameter scalings."),
    "signals": (
        "The member indicator strategies. (all) = every member must agree "
        "before a position; (any) = one agreeing member is enough."),
    "configuration": "Strategy (or composite) plus its parameter values.",
    "strategy": "The registered strategy name.",
    "in roster": "Strategy label with parameters, as the sweep will run it.",
    "family": (
        "Behavioural family (trend, momentum, mean-reversion, ...) — see the "
        "Signals tab for when each kind fails."),
    "warm-up": (
        "Bars of history the strategy needs before its first signal. Warm-up "
        "eats CPCV blocks, which is why slow strategies have fewer paths."),
    "file": "Source CSV in research/results/ — results are never pooled across files.",
    "equation": "The indicator's formula as implemented in backtester/core/indicators.py.",
    "kind": "Coarse file classification from the repo index (code, doc, result, test...).",
    "editable": "Whether the Docs editor may write this file. research/results/ never is.",
    "lines": "Line count at index build time.",
    "summary": "One-line summary extracted when the repo index was built.",
    "path": "File path relative to the repository root.",
    "bar": "Bar index within the replayed series.",
    "side": "buy or sell.",
    "reason": "Which rule produced the intended fill.",
    "units": "Position size in units of the asset.",
    "cost": "Cash spent or received including fees.",
    "equity": "Account value after the fill, marked at that bar's close.",
    "driver": "The research script that produces this artifact.",
    "answers": "The question the driver was built to answer.",
    "established": "What the run actually established, quoted from the docs.",
    "action": "What the rule would decide at the chosen bar: buy, sell or hold.",
    "holding -> wants": "Position it would be holding, versus what it wants now.",
    "warmup": "Bars of history the strategy needs before its first signal.",
    "bars": "Bars of the truncated series available to the replay.",
    "#": "Rank in research/TOP5-RECOMMENDATION.md — by robustness checks cleared, not by Sharpe.",
    "asset": "The coin the configuration was evaluated on for this row.",
    "when": "Timestamp of the bar (UTC).",
    "price": "Fill price used by the simulation for that bar.",
    "signal": "The indicator this row defines parameters for.",
    "what it is / when it fails": (
        "The family's bet in one line, and the market condition that "
        "reliably breaks it."),
}

# Define the unit and an example before the statistical qualification. A green
# closed trade, a high ranking and a wallet deposit are three different facts.
HEADER_GLOSSARY.update({
    "median sharpe": "Sharpe is risk-adjusted performance: average return divided by return variability, scaled to a year. Median means the middle result across the tested history splits. Positive is better than negative, but a high number on a few trades can be luck; it does not mean that many percent profit.",
    "iqr": "Interquartile range: the middle half of the Sharpe results, from the 25th to 75th percentile. If those are -0.2 and +0.6, IQR is 0.8. A wider spread means the result changes more between periods; IQR alone does not tell you whether it made money.",
    "% paths +": "Share of tested history splits with positive Sharpe. For example, 12 of 20 paths is 60%. These paths reuse some of the same history, so they are not independent trials or a 60% probability of winning the next trade.",
    "trades": "Trades counted by this result, not the number of price bars or winning trades. At least 10 trades are needed for ranking, but that is only a minimum evidence floor, not proof of reliability. Different result files can count trading activity differently.",
    "paths": "Number of usable train/test history splits in combinatorial purged cross-validation (CPCV). Training chooses a rule; held-out testing checks it on other periods. Long warm-ups can remove splits, so the nominal maximum is not always reached.",
    "backtest median net %": "Middle net account return across tested history splits. A backtest net +10% means $1,000 became $1,100 after modelled costs on that split. It is a total for the tested period, not a monthly rate or a forecast. Compare it with holding the same asset over the same dates.",
    "best backtest median net %": "Net return of the row selected as best by the rankable Sharpe ranking, not the largest net return in the file. For example, backtest +10% turns $1,000 into $1,100 in the model. Choosing the winner of many trials can select luck.",
    "net $": "Profit or loss after the source's costs. For a simulated account, $1,000 becoming $1,050 is net +$50. A wallet (live) value change also includes deposits and withdrawals; it is not necessarily trading profit.",
    "net % (source named)": "Net change divided by the source's starting capital. $50 gained on $1,000 is +5%. The source word says whether it is simulated or real. A dash means no valid capital base or usable data, not zero profit.",
    "gross $": "Result before the reported fees, slippage and borrowing costs: gross = net + those costs. Gross +$12 minus $15 costs is net -$3. Gross gains alone do not establish profitability.",
    "costs $": "Fees plus modelled slippage and borrowing costs for this source and window. Slippage is the difference between the reference price and execution price. Costs can turn a profitable-looking strategy into a loser.",
    "realized $": "Net result attributed to positions that closed during the window. A profitable sale can coexist with larger losses on inventory still held. Read this together with unrealized and total net P&L.",
    "unrealized $": "Profit or loss on positions still held, valued at the current or replayed price. Buying for $100 and now holding something worth $80 gives a $20 open loss even without selling. It can change before exit.",
    "drawdown (source named)": "Drop from the account's previous high. Falling from $1,000 to $800 is a 20% drawdown; recovering needs a 25% gain. The source distinguishes real account values from a simulation.",
    "contribution (source named)": "Percentage points this row adds to its own section's return. A +2-point contribution and -1-point contribution give +1% for that section. Do not add simulated sections to real-money sections.",
    "rankable": "Results with at least one usable test path and at least 10 trades. This only admits them to a ranking; it does not certify an edge, prevent overfitting, or make the highest row a recommendation.",
    "below floor": "Results with fewer than the minimum 10 trades. They remain visible but cannot rank. A spectacular return on two trades is weak evidence and should not win a leaderboard.",
    "why": "Reason this result cannot rank, such as too few trades or no usable history split. Fix missing data or insufficient history before interpreting its headline return.",
    "positive": "Rankable configurations with a median Sharpe above zero. This counts configurations, not dollars, and differs from the 'made money' count, which uses median net return.",
    "made money": "Rankable configurations with positive median net return across their tested splits. This is historical simulation; the count does not measure how much money they made or how many will work in future.",
    "horizon": "Preset timescale for the research. Short uses hourly bars; medium and long use daily bars with different lookbacks. A bar is one price interval. Equal numbers of bars can cover very different amounts of clock time.",
    "warm-up": "Price bars needed before the rule can calculate a signal. A 50-bar average needs 50 observations. Warm-up is not traded evidence and can reduce the number of usable test paths.",
    "signals": "Indicators used by the configuration. A signal measures something, while a strategy decides how to trade it. In an 'all' combination every rule must agree; in 'any' one agreeing rule can suffice. More indicators do not automatically mean stronger evidence.",
    "configuration": "A strategy and its exact parameter values, such as a moving-average rule with fast=20 and slow=50. Changing a parameter makes a different experiment. Searching many configurations increases the chance of finding a lucky winner.",
    "strategy": "A rule that turns past price or volume observations into a desired position. This is an experimental rule name, not a recommendation. Hover its row for the mechanism or press F1 for the glossary.",
    "family": "The kind of bet a strategy makes: trend follows continuing moves; mean reversion expects a move back toward an average. Related strategies often share the same failure mode rather than providing independent diversification.",
    "δ vs sol": "Change in median Sharpe when the same selected configuration is tested on another coin. -0.4 means its Sharpe fell by 0.4, not a 40% money loss. A large drop suggests it did not transfer well beyond SOL.",
    "source": "Origin of the number. Backtest and paper are simulations; dry-run sends no orders; live LP is reported by the liquidity bot; wallet (live) is a real balance snapshot. Their totals must be interpreted separately.",
    "price $": "Estimated USD price at the wallet scan, using the supported price provider for that chain. Amount times price gives value. A missing or stale price can make the total incomplete; a dash does not mean a worthless token.",
    "status": "How to read this row: for a wallet it can say excluded, unpriced or partial; for an experiment it says whether it is running or complete. Check the reason before treating a number as a complete result.",
    "bar": "One price observation in the replay. An hourly bar summarizes an hour; a daily bar a day. The bar number is a position in the dataset, not a trade number.",
    "holding -> wants": "Exposure the replay would already hold versus its new target. A move from 0 to 1 means moving from cash to full unlevered exposure; 0.5 means half-size. This is a model decision, not an executed order.",
    "equity": "Total account value: cash plus the marked value of positions, after the simulation's costs. Open losses count here even if no losing trade has closed. This is the figure to compare with starting capital.",
    "cost": "Cash spent by a simulated buy or received from a simulated sell, including its fees. This column is a cash flow, not simply the fee or the profit on the trade.",
    "pair": "Two assets traded in a liquidity pool, such as ETH/USDC. Providing liquidity holds exposure to their changing relative prices and is different from owning a single coin.",
    "range (token1/token0)": "Lower and upper prices of the liquidity position, quoted as units of token1 per token0. This may differ from the price direction on an exchange screen; check the token order before comparing ranges.",
    "range status": "Whether the pool price is inside the position's chosen range. Outside the range the position generally earns no swap fees and can hold mostly one of the two assets.",
    "staked": "Whether the liquidity position is deposited in the pool's reward gauge. Staking may earn AERO rewards in addition to swap fees. It does not remove price risk or guarantee positive net P&L.",
    "value now": "The position's latest reported USD value. Prices and state come from the daemon snapshot, so check its age and whether its mode is live or dry-run.",
    "deposited": "USD value assigned to capital put into this position or experiment arm. It is the comparison base for reported P&L; it is not the current position value.",
    "decision: reason": "What the liquidity daemon proposes or last decided, with its stated reason. Reading this table does not execute the action. Check the timestamp, mode and risk limits before interpreting it as current.",
    "tvl": "Total value locked: USD capital currently in the whole pool. It is pool size, not your balance or earnings. Large TVL alone does not make a pool profitable.",
    "24h volume": "USD trading volume through the pool during the reported 24 hours. Volume generates potential swap fees, but a busy day may not persist and some trades impose adverse price-selection losses.",
    "modelled fee apr @ ±10%": "Estimated annual simple rate from swap fees for a position roughly 10% either side of the reference price. APR projects a rate over a year without compounding; it is a model, not money already earned.",
    "modelled aero apr @ ±10%": "Estimated annual simple rate from AERO staking rewards at the reference range. The token's price and reward emissions can change, so this is not a fixed yield.",
    "modelled lvr apr @ ±10%": "Loss-versus-rebalancing (LVR): estimated annual cost of trading against better-informed or faster traders as pool prices adjust. The model subtracts it from income. It is related to, but not the same measure as, impermanent loss.",
    "edge ratio (income/lvr)": "Estimated income divided by estimated LVR cost. 2x means income is twice that particular modelled cost, before any other costs the model handles separately. It is not a two-times money return or proof of an edge.",
    "best mode, half-width (modelled)": "The range style and distance from the centre that the scout model currently prefers. ±10% means 10% each side. A narrower range concentrates fees but leaves the range more easily and may cost more to rebalance.",
    "modelled net apr": "Estimated annual income after the scout's modelled costs. A displayed 20% is a projection if conditions persist, not a promise or a realized account return. Check confidence, flags, gas and range risk.",
    "break-even deposit": "Modelled capital needed for expected income to cover the operation's costs. A smaller deposit may lose money to gas even in a pool with a positive APR. Estimates change with fees and gas prices.",
    "confidence": "The scout's assessment of how much evidence supports its estimate. It is not a statistically calibrated probability of profit; read the data flags and observed history too.",
    "flags": "Warnings about the model or its input data, such as limited history or missing information. A flag explains why an attractive projected return may not be usable.",
    "experiment": "A comparison run grouping different pool or range choices. Its arms are alternatives being observed side by side, not independently proven investment recommendations.",
    "arm": "One alternative in an experiment, such as a particular pool and range. Compare net results on the same dates and capital basis before calling one better.",
    "winner": "The arm labelled best by the daemon's comparison. A winner can still lose money or owe its lead to a short sample. Check net P&L, capital, duration and costs.",
    "time": "Timestamp reported for the daemon action. The table formats it in the display timezone; price-bar timestamps elsewhere explicitly use UTC. Check age before assuming an action just happened.",
    "slot": "The daemon's identifier for a managed position. This is a bookkeeping slot, not a Solana block slot or an amount of money.",
    "detail": "The daemon's recorded description of an action. It reports what the daemon wrote, not an independently confirmed blockchain receipt.",
    "tx (basescan)": "Transaction link on Base's block explorer. A link allows checking the on-chain receipt; its presence alone does not prove success, finality or profit.",
})

for _source in ("live", "dry-run", "reported"):
    HEADER_GLOSSARY[f"{_source} lp p&l $"] = "Reported position profit or loss in USD after the daemon's accounting. Check its source mode and snapshot age. Compare with P&L versus HODL to see whether providing liquidity improved on holding the original tokens."
    HEADER_GLOSSARY[f"{_source} lp p&l vs hodl $"] = "Difference between the LP result and simply holding the original deposited tokens over the same period. An LP gain of $10 versus a holding gain of $15 is -$5 versus HODL. Positive fees alone do not settle this comparison."
    HEADER_GLOSSARY[f"{_source} lp net %"] = HEADER_GLOSSARY[f"{_source} lp p&l %"] = "Reported LP net P&L divided by deposited capital. +5% means a $5 gain on $100 deposited. Live is real activity; dry-run is simulated; reported has an unknown mode. This is a period return, not an annual rate."
    HEADER_GLOSSARY[f"{_source} realized apr"] = "Annualized simple rate inferred from observed earnings over the elapsed time. A short observation can imply a very high APR that will not persist. It is not the account's total net return or a guaranteed future yield."

TAB_HELP = {
    "tab-settings": "Settings choose the historical data, starting capital, trading costs and test splits. They also hold public wallet identifiers. Save settings to apply edits. These choices affect the simulation; they do not enable live orders.",
    "tab-strategies": "Build the roster, the list of strategy configurations to test. A strategy is a trading rule; its parameters specify the exact version. Adding one does not make it profitable. Explicit roster parameters take precedence over signal defaults.",
    "tab-signals": "Signals measure price or volume; strategies turn them into position decisions. Edit their default lookbacks and thresholds here. A 20-bar lookback means 20 observations, not always 20 days. Existing explicit roster settings are preserved.",
    "tab-backtest": "A backtest simulates a rule on cached history after modelled costs. CPCV tests it on several held-out periods. Read net return, risk, path consistency and trade count together; compare with buying and holding. A top rank alone is not evidence of skill.",
    "tab-top5": "Five research presets selected using robustness checks on a dated dataset. They are starting points for investigation, not five proven profitable strategies. Transfer rows show what happened when the same rule was tried on other coins.",
    "tab-liverun": "Live Run is a launcher for the extension's Node dry-run process. The name does not mean real orders: the offered launch is simulated. Check the actual engine output rather than treating the selected strategy name as proof that a research rule was executed.",
    "tab-execute": "Execute replays cached historical bars with a paper account. Step advances simulated time; no order is sent. Equity includes open positions, so closed winning trades can coexist with a losing total account.",
    "tab-analyze": "Analyze asks what each rule would have decided using history available up to the chosen time. Buy, sell and hold are model signals, not orders or forecasts. A preset restricts the rules shown; it does not validate them.",
    "tab-cumulative": "Compare saved research files without pooling their different histories. Positive Sharpe and positive net return are separate counts. Below-floor results remain visible but cannot rank. More experiments can produce more lucky winners.",
    "tab-queue": "Queue controls a separate background research process. Start uses CPU to test configurations; Stop asks it to stop between jobs. Reading this tab does not start it. Searching more parameters increases the risk of fitting noise.",
    "tab-liquidity": "Liquidity reports the separate Aero bot's files, including real or simulated LP positions and modelled pool estimates. APR is an annual rate, not total profit. Kill pauses the bot without closing positions; Resume can allow it to act on real funds.",
    "tab-pnl": "P&L means profit and loss. Compare net results after costs and include open losses. Each source has its own section: simulated results and real money are never summed. Wallet value changes include transfers and are not trading profit.",
    "tab-wallet": "Wallet scans public addresses and extended public keys for balances and estimated USD values. Partial means something could not be read; unpriced means a value is unknown. Deposits, withdrawals and price moves all change wallet value.",
    "tab-research": "Research explains which question each analysis script answers and what its dated experiment established. A statistical test can disprove a claim without finding a profitable replacement. Saved research is evidence about its data period.",
    "tab-docs": "Browse source code, explanations and saved results. Filter to find a term, then open the selected file in the shared editor. Some source files are editable; generated research results are deliberately read-only.",
}

SETTING_HELP = {
    "asset": "Coin to simulate, for example SOL. This chooses the cached price series, not a token to buy. A different coin is a different experiment.",
    "start": "First historical date included, in UTC YYYY-MM-DD form. Testing only after a large crash can change the apparent result, so choose the period before comparing strategies.",
    "end": "Last historical date included, in UTC YYYY-MM-DD form. Blank uses all available cached history; it does not fetch prices up to today.",
    "capital": "Starting simulated account value in USD. $1,000 ending at $1,100 is +10%. Compare strategies using the same capital and dates; unused cash still belongs in account equity.",
    "fee_bps": "Trading fee per fill in basis points (bps). One bp is 0.01%; 6 bps on $1,000 is $0.60. Buying and selling each incur a fee, so a round trip has two fee legs.",
    "slippage_bps": "Adverse price movement allowed for each simulated fill. Two bps is 0.02%, or $0.20 on $1,000, in addition to fees. Both entry and exit pay it. Actual execution can be worse.",
    "fill_delay": "Delay in price bars between a signal and its fill. One hourly bar is one hour; one daily bar is one day. Delaying avoids pretending you could trade at a price already used to calculate the signal.",
    "cpcv_groups": "Number of chronological blocks used by combinatorial purged cross-validation (CPCV). It tests rules on different held-out pieces of history and removes overlapping information around boundaries. Changing the block geometry can change rankings.",
    "cpcv_k": "Number of blocks held out for testing in each CPCV path. For 8 blocks and k=2 there are 28 nominal combinations, but warm-up can reduce usable paths. k is a block count, not leverage or a confidence level.",
    "interval": "Duration summarized by one price bar: 1h means hourly, 1d daily. A 20-bar indicator spans 20 hours or 20 days respectively. Shorter bars usually mean more potential trading and more accumulated costs.",
    "solana_address": "Public Solana wallet address used for read-only balances. An address cannot authorize spending. Never enter a seed phrase or private key.",
    "base_address": "Public EVM address scanned on Base. The same address may exist on other networks with different balances; this field selects its Base holdings.",
    "eth_address": "Public EVM address scanned on Ethereum mainnet. Ethereum and Base are separate networks even when the address text is identical.",
}
for _chain in ("btc", "ltc", "doge"):
    SETTING_HELP[f"{_chain}_xpub"] = "Extended public key for read-only address discovery. It cannot spend, but it reveals a group of wallet addresses and their history. Blank keeps the saved key; type clear to remove it. Use an xpub/ypub/zpub, never an xprv or recovery phrase. A partial scan is a lower bound, not a complete balance."

SIGNAL_HELP = {
    "sma_fast": "Bars in the fast simple moving average (SMA). A 20-bar SMA is the average of the last 20 closes. A smaller window reacts faster and can create more false switches.",
    "sma_slow": "Bars in the slow SMA used for comparison with the fast average. It should exceed the fast window. A cross can indicate a trend change, but tends to lag and churn in sideways prices.",
    "regime_window": "SMA lookback used to classify a broad market regime. Being above the average is treated as a favourable condition. This is a filter, not a guarantee that a downtrend has ended.",
    "macd_fast": "Fast exponential moving average (EMA) span in MACD. MACD subtracts a slow EMA from a fast EMA to measure trend momentum. Spans count bars.",
    "macd_slow": "Slow EMA span in moving average convergence/divergence (MACD). Keep it longer than the fast span. The difference measures relative trend momentum, not an expected percentage gain.",
    "macd_signal": "EMA span used to smooth the MACD line into its signal line. Crossing the two can trigger a rule; short spans react faster and may generate more fee-paying churn.",
    "rsi_period": "Relative strength index (RSI) lookback in bars. RSI compares recent gains with recent losses on a 0–100 scale. Low does not mean a coin is cheap or about to rebound.",
    "rsi_oversold": "RSI level below which the reversion rule can consider buying. 30 is a conventional oversold threshold. During a persistent fall RSI can stay low while losses grow.",
    "rsi_exit": "RSI recovery threshold used to exit the reversion position. For example, entering below 30 and exiting near 50 waits for recovery; it does not guarantee the sale price exceeds the purchase price after costs.",
    "stoch_k": "Bars in the stochastic oscillator's price range. %K locates the close between the recent lowest low and highest high, on a 0–100 scale. It is a location, not a probability.",
    "stoch_d": "Bars used to smooth stochastic %K into %D. More smoothing reacts more slowly. The two lines help a rule describe price momentum inside a range.",
    "stoch_oversold": "Stochastic level considered near the bottom of the recent range. For example, 20 means roughly the lower fifth. Price can keep falling and form a new range.",
    "stoch_exit": "Stochastic recovery level used to leave a position. A value of 80 means near the top of its recent range, not an 80% gain or win probability.",
    "bollinger_window": "Bars used for the Bollinger middle average and price variability. The bands describe a recent range; crossing one is not proof that price will return to the middle.",
    "bollinger_std": "Band distance in standard deviations from the average. 2 means twice the estimated variability, not 2%. Crypto prices are not normally distributed, so the bands do not promise a 95% containment rate.",
    "keltner_ema": "EMA lookback for the Keltner channel centre. The channel surrounds an average with bands based on typical bar movement, rather than a fixed dollar width.",
    "keltner_atr": "Average true range (ATR) lookback for Keltner band width. ATR measures price movement including gaps, in price units. It measures movement size, not direction.",
    "keltner_mult": "ATR multiplier setting channel width. 2 means two ATRs on each side of the centre. Wider bands react to fewer moves; it is not two-times leverage.",
    "donchian_entry": "Bars in the Donchian high/low channel used for breakout entry. The rule looks for movement beyond the prior range. False breakouts can produce many small losses.",
    "donchian_exit": "Bars in the shorter Donchian channel used for exit. Shorter windows usually leave sooner but can also cut off trends. Count is in the selected bar interval.",
    "obv_ma": "Moving-average bars for on-balance volume (OBV), which adds volume on up closes and subtracts it on down closes. It measures participation; it does not directly measure dollars flowing into your account.",
    "vwap_window": "Bars in the rolling volume-weighted average price (VWAP). High-volume bars count more in the average. This is a historical reference price, not a promised execution price.",
    "vwap_discount": "Fraction below VWAP used for an entry: 0.02 means 2% below, not 0.02%. A discount can reflect a continuing fall rather than a bargain.",
    "zscore_window": "Bars used to estimate the average and variability for a z-score. The score measures distance from that average in standard deviations and can be unstable when the price regime changes.",
    "zscore_entry": "Z-score at which the rule enters. -2 means two standard deviations below the recent average, not a 2% loss or a guaranteed rebound.",
    "roc_window": "Bars for rate of change (ROC): current close divided by the earlier close minus one. +0.10 means a 10% past gain. Momentum rules assume some continuation; past gains do not establish it.",
    "vol_window": "Bars used to estimate return volatility, or how much returns vary. Volatility measures movement size in both directions, not just loss risk.",
    "vol_target": "Target annualized volatility as a fraction: 0.60 means 60%. The overlay adjusts simulated position size toward that risk level; it is not a 60% return target and size caps can prevent reaching it.",
    "trend_window": "Bars in the average used by the trend gate for a risk overlay. Position sizing and the entry direction are separate choices; a sizing overlay cannot create a forecasting edge by itself.",
    "grid_anchor": "Bars in the rolling SMA anchor for the grid exposure-staircase strategy. This grid increases exposure as price falls below that average. It is a different model from the extension's resting buy/sell ladder.",
    "grid_levels": "Number of exposure steps in the grid strategy. Four levels can move toward quarter, half, three-quarter and full exposure. More levels do not remove the risk of reaching maximum size in a continuing fall.",
    "grid_step": "Fractional spacing below the grid's rolling average. 0.05 means 5%, not 0.05%. This controls an exposure staircase, not the extension's resting-order rung spacing.",
    "dual_formation": "Bars over which dual momentum measures past performance, before its skipped recent bars. Longer formation windows react slowly; this parameter is a lookback, not leverage.",
    "dual_skip": "Most recent bars excluded from dual momentum's formation return. Skipping them reduces sensitivity to very recent moves; it does not remove all overfitting or lookahead risk.",
    "adx_period": "Bars in average directional index (ADX). ADX measures trend strength on a 0–100 scale. It does not by itself tell you whether the trend points up or down.",
    "adx_threshold": "Minimum ADX used to call a trend strong enough. For example, 25 is a strength threshold, not a 25% gain. Changing it after inspecting test results can fit noise.",
    "ribbon_windows": "Number of moving averages in the ribbon. The rule uses their ordering as evidence of trend alignment. Similar averages are related measurements, not independent votes.",
    "ribbon_base": "Base lookback in bars used to construct the ribbon's moving-average windows. Smaller windows react faster and can change position more often.",
    "ichimoku_tenkan": "Short high/low midpoint lookback in Ichimoku, called Tenkan. It describes recent price balance; it is not an average future price.",
    "ichimoku_kijun": "Longer high/low midpoint lookback in Ichimoku, called Kijun. It is a slower balance reference and can act as a trend filter.",
    "ichimoku_senkou_b": "Long high/low midpoint lookback for Ichimoku's second cloud boundary. The traditional chart draws the cloud ahead; that drawing convention does not give the strategy future data.",
    "ichimoku_displacement": "Bars of Ichimoku cloud displacement. The implemented rule aligns data causally; visually drawing a line ahead is not a forecast or permission to use future bars.",
    "ou_fit_window": "Past bars used to fit the Ornstein–Uhlenbeck (OU) mean-reversion model. It estimates whether deviations tend to decay. A fitted mean can move, and many markets do not follow the model.",
    "ou_hold_multiple": "Maximum holding time as a multiple of the fitted OU half-life. 2.5 means two and a half estimated decay times, not a 2.5-times position.",
    "ou_max_half_life": "Largest estimated reversion half-life accepted, in bars. Half-life is the estimated time to halve a deviation from the fitted mean; it is not a guaranteed recovery time.",
    "hurst_window": "Bars used to estimate the Hurst exponent. Values above roughly 0.5 suggest persistence; below roughly 0.5 suggest reversion in the fitted sample. The estimate can be noisy.",
    "hurst_lag": "Lag in bars used by the Hurst calculation. It changes the spacing of observations in the estimate, not a delay before a trading fill.",
    "hurst_trend_threshold": "Hurst value above which the rule selects trend-following behavior. 0.55 is an exponent estimate, not a 55% win probability.",
    "hurst_revert_threshold": "Hurst value below which the rule selects mean reversion. 0.45 is not a promised return or probability; estimates near the boundary can switch regimes often.",
    "volregime_lookback": "Past bars used to compare today's volatility with its historical distribution. The regime filter labels conditions; it does not predict profit by itself.",
    "volregime_calm_quantile": "Historical volatility percentile dividing calm from active conditions. 0.5 means the middle of the fitted history, not a 50% chance of a profitable trade.",
    "atr_risk_per_trade": "Fraction of simulated equity budgeted for risk to the modelled ATR stop. 0.01 means 1%. Gaps and adverse execution can exceed a modelled stop, so it is not a guaranteed maximum loss.",
    "atr_stop_multiple": "Distance to the modelled stop in units of ATR. 2 means twice typical bar movement. A wider distance usually requires a smaller position for the same risk budget.",
    "ewma_lambda": "Decay factor for exponentially weighted volatility. 0.94 retains 94% of the previous estimate in the next update. A larger value forgets old observations more slowly; it is not leverage or a return.",
}

CONTROL_HELP = {
    "indicator": "Current console phase and its labelled result. Backtest and paper figures are simulations; a source label is part of the number. This indicator is not a combined real-wallet balance or proof of profitable live trading.",
    "help-hint": "Move the pointer over a control, table header or value to read its definition. Press F1 for the full searchable help; use Tab and Page Up/Down to read it, then Esc to return without changing the current input.",
    "btn-save": "Save the edited Settings and apply them to later actions. This persists configuration; it does not start a backtest, background sweep or live trading.",
    "strategy-params": "Explicit strategy parameters in name=value form, for example fast=20 slow=50. These override signal defaults for the added roster entry. An empty field uses the saved defaults.",
    "btn-add": "Add the selected available strategy and these parameters to the test roster. The roster is a list of experiments; adding a rule does not place an order.",
    "btn-remove": "Remove the selected configuration from the test roster. This does not close positions or delete saved research results.",
    "btn-reset-roster": "Restore the default test roster, replacing its current entries. Saved backtest results remain separate. This changes which configurations the next roster backtest tests.",
    "btn-save-signals": "Save signal defaults for later strategy construction. Explicit parameter values in an existing roster entry still win, so this does not silently rewrite those choices.",
    "btn-reset-signals": "Restore the shipped signal defaults. This resets the Signals form and saved defaults; it is not a search for more profitable parameters.",
    "btn-run": "Run the roster through historical cross-validation using Settings. It uses cached prices and simulated fills after costs. Results are research, not a forecast or real account P&L.",
    "btn-run-untested": "Start the research sweep for combinations not yet covered by the saved files. This can be a lengthy CPU job. Trying more combinations also raises the chance of selecting a lucky winner.",
    "btn-cancel": "Request cancellation of this app's active backtest or sweep. The separate Queue worker has its own Stop button. Cancellation does not close real positions.",
    "live-run-strategy": "Strategy label passed to the dry-run launcher. Inspect the launch output for the engine actually used; a named research rule is not proof of live execution or validated performance.",
    "btn-spawn-dryrun": "Launch the extension's Node dry-run process. It simulates activity and does not submit orders. Read its output to see the executable, arguments, results and any refusal.",
    "btn-refresh-live-run": "Reload the recommendation from the existing research evidence. Refresh does not fetch new market history or make the recommendation reliable in future conditions.",
    "exec-strategy": "Choose a roster strategy or Top 5 preset for historical paper replay. The replay uses cached data and simulated account equity, not your wallet balance.",
    "btn-paper-start": "Start a historical paper replay for the selected strategy. It advances only when stepped. This creates simulated state, never a venue order.",
    "btn-step1": "Advance the paper replay by one price bar. One bar is the selected interval, such as one hour or one day; it is not necessarily one trade.",
    "btn-step25": "Advance the paper replay by 25 price bars. The rule can hold, trade or remain in cash during those bars. Inspect total equity as well as closed fills.",
    "btn-step-end": "Replay to the last cached bar. This fast-forwards historical time; it does not wait for future prices or switch to live trading.",
    "btn-paper-reset": "Discard the current in-memory paper replay and its displayed fills. It does not reset your wallet, saved research or the liquidity bot.",
    "top5-add-selected": "Add the selected research preset's member signals to the roster. The preset was chosen on historical evidence and still needs evaluation on the data and costs you intend to use.",
    "top5-add-all": "Add the member signals from all five research presets to the roster. Overlapping signals are related experiments rather than independent evidence.",
    "top5-run": "Backtest the current roster. Adding a Top 5 preset's signals and running them individually is different from running its combined rule; use the preset choices in Analyze or Execute for the composite.",
    "top5-reload": "Read the saved Top 5 evidence again. Reload does not repeat its historical experiments or update the underlying prices.",
    "analyze-asset": "Choose the cached coin and bar interval to replay. The displayed dates say what history is available. Selecting a dataset does not download fresh prices.",
    "analyze-when": "Replay only history available at this UTC date/time, such as 2026-01-15 12:00. Blank means the latest cached bar, which can be older than today. The analysis does not use later bars.",
    "analyze-run": "Calculate what the rules would decide at the selected historical time. A buy or sell is a model instruction, not an executed order or a guarantee that price will follow it.",
    "cumulative-reload": "Reload the existing result files and summarize each separately. Their histories and search sizes differ, so counts and rankings are not pooled into one proof of profitability.",
    "queue-start": "Start a separate low-priority research worker. It consumes CPU and saves results as jobs finish. This starts experiments, not trades; many parameter trials can overfit history.",
    "queue-stop": "Ask the background worker to stop at a safe job boundary. The current job may finish first, and already saved results remain available. It does not stop the liquidity daemon.",
    "queue-refresh": "Re-read the background worker's status and saved results. This is observation only: it does not start, resume or restart the worker.",
    "queue-fetch": "Download missing historical price files into the local cache. This uses the network and may take time. It does not start the sweep automatically.",
    "wallet-chain": "Choose which blockchain balances to read. All includes every configured supported wallet; Base and Ethereum have separate balances even for the same address.",
    "wallet-scan": "Read balances from public chain services and update the wallet view. An all-chain scan also records a portfolio snapshot. Partial and unpriced holdings make totals incomplete; this scan cannot authorize spending.",
    "pnl-window": "Period to report: 24h, 7d, 30d, 90d, year-to-date (ytd), or all available history. Historical backtests may have no data near today. Use custom dates inside their actual data period.",
    "pnl-start": "Optional custom beginning in UTC YYYY-MM-DD form. Enter both custom dates to choose a historical window rather than the relative window preset.",
    "pnl-end": "Optional custom ending in UTC YYYY-MM-DD form. A date includes that entire UTC day. The report cannot invent data outside the source's actual coverage.",
    "pnl-source": "Select a source or show separate sections for all. Backtest, paper and dry-run are simulations; live LP and wallet (live) are real observations. Wallet changes include deposits and withdrawals.",
    "pnl-run": "Build profit-and-loss summaries over the chosen dates. Include unrealized losses and costs. Missing capital or data displays as a dash or explanation rather than an invented zero.",
    "liq-refresh": "Re-read the liquidity bot's local state files. This does not ask it to trade. Check its reported live/dry-run mode and update age before relying on a balance or APR.",
    "liq-kill": "Pause the separate liquidity bot by creating its kill-switch file. Existing positions remain invested and can still lose value; this is not an exit-to-cash command.",
    "liq-resume": "Remove the liquidity bot's kill switch, allowing it to act under its own mode and limits, potentially with real funds. Press twice within 10 seconds to confirm. This does not change its risk caps.",
    "docs-filter": "Filter the repository file list by path or summary. For example, grid finds grid-related code and explanations. This searches the catalogue; it does not edit or execute a file.",
    "docs-kind": "Narrow the file catalogue to code, documents, results or another indexed kind. This kind describes a file; wallet contract kinds on the Wallet tab mean something different.",
    "docs-save": "Save the currently opened editable source file. Generated research results stay read-only. The editor checks for changes on disk so it cannot silently overwrite another writer's edits.",
    "docs-view": "Shared source viewer/editor, available below every tab. Ctrl+E shows or hides it; Ctrl+S saves when allowed. Read-only files cannot be changed here. Press F1 for help even while editing.",
    "key-sources": "Shows whether expected signing-key files exist with safe permissions. This view checks file metadata only and does not open them, reveal their contents or enable signing.",
    "portfolio-notice": "Notice of balance changes between recorded wallet scans. Deposits and withdrawals can produce a notice; it is not automatically a trading gain or loss.",
    "pnl-summary": "Net is profit or loss after costs; gross is before those costs. Realized comes from closed positions, while unrealized is the marked result still open. Win rate counts winning closes, not total profitability: nine $1 wins and one $20 loss still lose money. Expectancy is average net result per close. Drawdown is the drop from a prior account high; recovery measures whether it regained that high. A wallet value change also includes transfers. Press F1 to search any of these terms.",
    "queue-data": "Cached price-file availability for the worker. Missing intervals are skipped until fetched; a partial set of data is not evidence that the whole research search finished.",
    "wallet-summary": "USD value of included, priced holdings at scan time. Flagged, unreadable and unpriced items are separate. A partial total is not a complete portfolio valuation or trading P&L.",
    "liq-scout-note": "Age and completeness of the pool scout's snapshot. The scout estimates returns from its inputs; it does not report income already earned in your account.",
}

TERMS = {
    "grid": "Two different models share this name here. The registered grid strategy changes target exposure below a rolling average. The extension's resting ladder buys a price rung and sells one rung higher. Either can accumulate losing inventory in a persistent fall. Closed winning cycles do not prove total account profit.",
    "basis points (bps)": SETTING_HELP["fee_bps"],
    "CPCV": SETTING_HELP["cpcv_groups"] + " " + SETTING_HELP["cpcv_k"],
    "in-sample and out-of-sample": "In-sample (IS) data helps choose a rule. Out-of-sample (OOS) data is held back to test it. Repeatedly choosing changes after seeing OOS results turns that test set into training data and makes the apparent performance optimistic.",
    "PBO": "Probability of backtest overfitting: a historical diagnostic of how often a winner chosen on one period ranks poorly on held-out periods. It is not the chance that a live trade will lose. Searching more configurations can make this problem worse.",
    "DSR": "Deflated Sharpe ratio adjusts apparent performance for the number of trials and return distribution. It asks whether a high Sharpe could be a search winner by luck. Passing a threshold is not proof of future profit or a substitute for enough independent data.",
    "win rate": "Winning closed outcomes divided by all measured closed outcomes. Nine +$1 wins and one -$20 loss gives a 90% win rate but loses $11 before costs. Read win rate alongside average win/loss and net equity.",
    "expectancy": "Average net profit or loss per measured closed outcome. Positive expectancy in a short or selected backtest may be luck, and ignores still-open losses unless the report explicitly includes them.",
    "APR and APY": "Annual percentage rate (APR) scales a simple earnings rate to a year; annual percentage yield (APY) assumes compounding. A high projected APR can vanish as market conditions change. Neither is the same as the actual period's net account return.",
    "impermanent loss and LVR": "Impermanent loss compares a liquidity position with holding its original tokens as relative prices change. Loss-versus-rebalancing (LVR) measures adverse selection as pool prices adjust. Fees and rewards must cover relevant costs and inventory losses for LP to outperform holding.",
    "leverage and liquidation": "Leverage increases market exposure relative to your equity: 5x means about $500 exposure for $100 capital. It magnifies losses and costs as well as gains. Liquidation can forcibly close the position when collateral becomes insufficient.",
    "SMA": SIGNAL_HELP["sma_fast"], "EMA": "Exponential moving average: a recent-price average giving more weight to newer observations. It reacts faster than a simple average of similar length but still lags price and can whipsaw.",
    "RSI": SIGNAL_HELP["rsi_period"], "MACD": SIGNAL_HELP["macd_slow"],
    "Bollinger": SIGNAL_HELP["bollinger_std"], "ATR": SIGNAL_HELP["keltner_atr"],
    "Stochastic": SIGNAL_HELP["stoch_k"], "OBV": SIGNAL_HELP["obv_ma"],
    "VWAP": SIGNAL_HELP["vwap_window"], "Z-score": SIGNAL_HELP["zscore_window"],
    "ROC": SIGNAL_HELP["roc_window"], "RealisedVol": SIGNAL_HELP["vol_window"],
    "buy_and_hold": "Buy the asset once and keep it over the comparison period. This is a baseline: an active rule can make money yet underperform holding. Compare the same dates, starting capital and costs.",
    "mean-reversion": "Bet that price will move back toward a recent average. A permanently lower price or changing average can break the assumption. Buying every dip can build the largest position during the worst decline.",
    "trend": "Bet that a direction will persist. It tends to be whipsawed when prices repeatedly reverse in a narrow range. Costs matter on every switch.",
    "momentum": "Bet that recent relative or absolute performance will continue. A sharp reversal can make yesterday's strongest asset today's loser.",
    "regime-filter": "A gate classifying conditions such as rising versus falling markets. It can veto an entry but can react late or reject profitable opportunities. A filter is a hypothesis to test, not a cure for a losing strategy.",
    "leverage-tier": "A wrapper that runs a rule with 2x, 5x or 20x exposure plus borrowing and liquidation rules. It changes risk and cost, not the quality of the underlying signal.",
    "trigger": "A conjunction of conditions mined from past data to predict a move. It remains exploratory unless it passes held-out evidence, stability and replication checks. The word trigger does not mean an order was sent.",
    "baseline": "A simple comparison rule, such as buying and holding, used to test whether a complicated strategy earns its extra costs and effort. A positive strategy return can still trail the baseline.",
    "breakout": "Bet that moving beyond a recent high or low begins a larger move. Many breakouts reverse quickly; a small number of large winners must pay for false starts and costs.",
    "oscillator-reversion": "Use an indicator such as RSI to buy after recent weakness and exit on recovery. An oversold reading can stay low during a sustained decline, so it is not proof that price has reached a bottom.",
    "volume-flow": "Use trading volume and price direction to describe participation. Volume-based rules do not directly measure your profit or guarantee that large traders are buying.",
    "risk-overlay": "Change the size of a position using a risk estimate. An overlay adjusts exposure; it does not provide an independent reason why the underlying trade should be profitable.",
    "sma-gated": "Allow exposure only when price is above a simple moving average, then apply a sizing rule. Similar sizing variants can act as the same underlying bet rather than independent strategies.",
}

for _name, _explanation in {
    "ma_crossover": SIGNAL_HELP["sma_fast"] + " " + SIGNAL_HELP["sma_slow"],
    "sma_regime": SIGNAL_HELP["regime_window"],
    "bb_reversion": "Buy below the lower Bollinger band in the expectation of a recovery toward the average. A persistent decline can keep price below the band while losses grow.",
    "bb_breakout": "Trade expansion beyond Bollinger bands rather than a return to the average. The same indicator can support the opposite hypothesis; sideways markets can generate false breakouts.",
    "breakout": SIGNAL_HELP["donchian_entry"],
    "keltner": SIGNAL_HELP["keltner_atr"] + " " + SIGNAL_HELP["keltner_mult"],
    "ts_momentum": SIGNAL_HELP["roc_window"],
    "vwap_reversion": SIGNAL_HELP["vwap_discount"],
    "obv_trend": SIGNAL_HELP["obv_ma"],
    "zscore": SIGNAL_HELP["zscore_entry"],
    "voltarget": SIGNAL_HELP["vol_target"],
    "dual_momentum": SIGNAL_HELP["dual_formation"],
    "adx_trend": SIGNAL_HELP["adx_period"] + " " + SIGNAL_HELP["adx_threshold"],
    "ma_ribbon": SIGNAL_HELP["ribbon_windows"],
    "ichimoku": SIGNAL_HELP["ichimoku_senkou_b"],
    "ou_reversion": SIGNAL_HELP["ou_fit_window"],
    "hurst_switch": SIGNAL_HELP["hurst_window"],
    "vol_regime": SIGNAL_HELP["volregime_lookback"],
    "atr_sized": SIGNAL_HELP["atr_risk_per_trade"],
    "garch_voltarget": SIGNAL_HELP["ewma_lambda"] + " " + SIGNAL_HELP["vol_target"],
    "trigger_trade": TERMS["trigger"],
}.items():
    TERMS[_name] = _explanation
for _name, _leverage in (("lev_low", 2), ("lev_medium", 5), ("lev_high", 20)):
    TERMS[_name] = f"Runs an underlying rule with {_leverage}x exposure and the model's borrowing and liquidation rules. " + TERMS["leverage and liquidation"]


def column_help(label: str, table_id: str | None = None) -> str | None:
    """Resolve overloaded labels using the actual table, not a global guess."""
    key = label.strip().casefold()
    if key == "kind":
        if table_id == "wallet-contracts":
            return "Type of on-chain account: a token mint defines an asset; a token account holds units; a stake account delegates SOL; a position NFT identifies an LP position. This is not a file classification."
        if table_id == "liq-actions":
            return "Type of action recorded by the liquidity daemon, such as rebalance or compound. Check its detail and receipt; an action label alone does not establish successful execution."
        return "Repository file classification, such as code, document, saved result or test. It describes how to browse the file, not whether its contents prove a profitable strategy."
    return HEADER_GLOSSARY.get(key)


def control_help(widget_id: str | None) -> str | None:
    if not widget_id:
        return None
    if widget_id.startswith("set-"):
        return SETTING_HELP.get(widget_id[4:])
    if widget_id.startswith("sig-"):
        return SIGNAL_HELP.get(widget_id[4:])
    if widget_id.startswith("preset-"):
        return "Select a dated Top 5 research preset to fill this tab's strategy choices. The return shown is a historical backtest result, not your account's profit. Reusing a preset on new history can produce different results."
    return CONTROL_HELP.get(widget_id) or TAB_HELP.get(widget_id)


def row_help(value: str) -> str | None:
    """Explain recognised indicator/strategy names without echoing cell data."""
    name = value.strip().casefold().split("(")[0]
    for term, explanation in TERMS.items():
        if name == term.casefold():
            return explanation
    return None



