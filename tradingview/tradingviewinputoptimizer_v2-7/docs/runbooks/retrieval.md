# Refresh and verify retrieval

Precondition: the original local bundle and documentation exist. Inspect `memory.md` and the existing external index manifest. Preserve other sessions and paused services.

1. Run `python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py check` to compare current source hashes with the recorded corpus.
2. If stale and a refresh is authorized, run `python3 /Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/retrieval.py build`. This explicitly creates embeddings and reuses same-content vectors; it does not start a watcher.
3. Re-run `check`, a specific keyword query and a paraphrase semantic query. Verify the returned source path and chunk offsets against the current file.
4. Inspect the external manifest/verification receipt for all-text coverage, binary exclusions, failed chunks and the model identity. A process exit alone does not establish completeness.

If embedding fails, retain the checkpoint and record the exact error and remaining chunk count. Do not label keyword-only results as semantic completion. Never clear application databases or registration settings to repair retrieval.
