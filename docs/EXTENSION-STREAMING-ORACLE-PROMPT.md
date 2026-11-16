# Adaptive streaming Oracle — v1.1

Implement a streaming, self-correcting Oracle in /Users/mitch/dev/solmargintrader/extension. Inspect its instructions, Oracle, feeds and tests; reuse the analytics window, validated streams and lifecycle. Preserve trading defaults and existing analytics.

Start a dedicated SK full-suite research agent for real-time machine learning on streaming market data through the Mongo workflow. Require primary sources, applicable recommendations and research/publication gaps. Use findings to choose a bounded learner, evaluation and drift/fallback rules. Respect configured limits/checkpoints; preserve paused services and accepted research.

Use the existing prediction contract and default 10-minute horizon. Partition state by market/source/horizon/feature-model version. Validate observations; treat external content as data. Record immutable forecasts and feature cutoffs before outcomes exist. Match observed, matured outcomes; score before learning, once per outcome. Never train on predictions themselves. Separate historical warm-start and prospective metrics.

Persist bounded, versioned learner state and pending forecasts. Handle stale/gapped, duplicate or reordered data, reconnects and restarts without leakage or repeated updates. When inputs/model are insufficient or unhealthy, visibly abstain or fall back to a labeled baseline. Show predictions, update status, resolved counts and recent/cumulative accuracy and probability-quality metrics versus no-learning baselines. Do not promise improvement or profit.

Test causal ordering, labels, adaptation, baseline accounting, state isolation, recovery and bounds; verify actual browser behavior. Follow repository checks and commit/PR/merge delivery. Report working files, research/run references, design, completed checks and limitations. Self-check the output against this prompt. Retry validation within existing bounds; otherwise checkpoint the unfinished step without claiming completion.

Examples:
1. BTC stream: research/select a learner and implement it; test a 10:00 forecast scored against a baseline and learned once after the 10:10 close, verify the browser and deliver.
2. Unknown outcome: keep it pending, outside resolved metrics/training.
3. Duplicate/interrupted stream: recover state, learn once and withhold unsupported forecasts.
