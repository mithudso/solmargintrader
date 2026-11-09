# Handoff: SolTUI Jupiter advanced orders

As of 2026-11-08 22:54 UTC. The owner wants Gemini to finish the work. The work is **not complete**. Do not claim Jupiter trading works.

## Request

Move the advanced order ticket from Money > Wallet to its own page under Money, and enable choosing Coinbase or Jupiter. Use `/Users/mitch/dev/solmargintrader/soltui/JUPITER_ORDER_WIDGET_IMPLEMENTATION_GUIDE.md` and inspect Stele decision KNOW-1053 and task TASK-1044. The owner explicitly requested correcting safety problems in the guide and continuing until the whole task is complete. They did not authorize a live test swap for this task.

Stele task TASK-1044 is open and was released for the next agent. Its criteria require explicit wallet and venue, verified mint and decimals, balances, quote, fees, exact transaction review and explicit submission. Preserve fail-closed safety, dry-run defaults, and no automatic retry of an ambiguous submit. The related decision is https://app.stele-ai.dev/p/dev-y3seh/nodes/KNOW-1053 and the task is https://app.stele-ai.dev/p/dev-y3seh/nodes/TASK-1044 . Re-read both, claim the task, and follow repository `AGENTS.md` and `CLAUDE.md` before implementation.

## Git and workspace

- PR https://github.com/mithudso/solmargintrader/pull/134 was merged at 2026-11-08 22:52:58 UTC as `314fe989a18ba16ec4e306ec6aa62a7992724cff`, even though it was a WIP and checks were not all green. This agent did not merge it. It is on `origin/master` as observed when fetched. Check the current remote tip before starting.
- Feature worktree `/Users/mitch/dev/solmargintrader-wt-jupiter` is clean on `feat/jupiter-manual-orders-20261108`, head `be6c3545e4797ac21290eb461637615962350d72`; its contents were squash-merged. Do not assume the branch head is an ancestor of master.
- The original checkout `/Users/mitch/dev/solmargintrader` was at `b8cc700` and behind remote when checked. It has untracked `/Users/mitch/dev/solmargintrader/soltui/JUPITER_ORDER_WIDGET_IMPLEMENTATION_GUIDE.md` and `/Users/mitch/dev/solmargintrader/llms/jupsol-llms.txt`. Preserve both; the guide is not in the merged commit. Do not reset, clean, stash or sweep other worktrees. Make a fresh worktree from the latest remote default branch if appropriate.
- This handoff is in `/Users/mitch/dev/solmargintrader-wt-jupiter-handoff/JUPITER_GEMINI_HANDOFF.md`. That handoff worktree is separate from the feature worktree and original checkout.

## What was implemented

1. `soltui/tui.py`: moved the existing advanced ticket into `tab-advanced-order`; entering that view refreshes Coinbase order safety. The price context timer now follows the new tab. `soltui/shell.py` adds Advanced order to Money. Existing Coinbase ticket logic remains in place.
2. Added `soltui/jupiter_tokens.py` and `jupiter.tokens_search` in `soltui/commands.py`. It queries Jupiter Tokens API v2 via `JUPITER_API_KEY`, displays full mint addresses, rejects invalid or missing decimals, preserves zero decimals, and refuses ambiguous symbol resolution and unverified token resolution. The UI has a search field and results display. This is discovery only; selecting Jupiter in the order ticket remains unavailable.
3. Guarded `_docs_view_changed` in `soltui/tui.py` against a queued `TextArea.Changed` event arriving after the editor or its status widget unmounts. Stele lesson KNOW-1055 records the trigger.
4. Updated `soltui/tests/test_advanced_order_ui.py` and added `soltui/tests/test_jupiter_tokens.py`. Rebuilt checked-in keyword indexes. Prompt and continuation records were updated.

## What is missing

There is no Jupiter Swap v2 quote/preview, balance verification, fee validation, on-chain mint/decimals check, semantic verification of the exact returned transaction, signing, execute, journal/recovery, reconciliation, or functional Jupiter order selection. There is no verified full end-to-end UI workflow or loaded-app acceptance. Do not turn on the venue merely to make the selection active.

The guide is a design aid, **not safe code to copy verbatim**. It defaults missing/zero decimals with `or 9`, falls back to zero for missing USD valuations, chooses the first token match, estimates a BUY base amount using a token price, signs a returned transaction without semantic verification, and treats non-success execution too broadly as definite failure. It also suggests quick submission without review; TASK-1044 requires explicit review. `KNOW-1054` records these risks. The guide's sample signing code must not be shipped as-is.

The existing guarded executor is under `executor/src/executor/`. Its `txverify.py` inspects allowed programs/instructions, fee payer, signers and lookup tables and checks simulated writable-account balance changes; `engine.py` verifies before signing, re-simulates signed bytes, journals before sending and reconciles ambiguous outcomes. It is documented and tested for Jupiter Swap v1, not all Swap v2 managed routes. It presently allows only specific Jupiter v6 instruction discriminators. Reuse only after establishing that all required invariants apply to the exact v2 bytes and quote, including amounts, thresholds, mint ownership, wallet, fees and expiry. Refuse unsupported routers, instructions, token programs or unresolved lookup tables. Do not weaken existing executor rails, allowed mints, KILL, research gates or dry-run behavior. The SolTUI environment checked during this work did not contain `solders` or `httpx`; dependency and packaging behavior needs a deliberate solution.

Jupiter current documentation retrieved via Context7 describes `/tokens/v2/search`, `/price/v3`, `/swap/v2/order`, and `/swap/v2/execute`, with `x-api-key`. `/execute` accepts the signed transaction and requestId from `/order` and itself manages landing and retries. Preserve an irreversible submission boundary and handle ambiguous responses as unknown; do not automatically resubmit. Do not expose key material in logs, UI, files, or error messages.

## Verification and CI

- The focused previous run of `soltui.tests.test_advanced_order_ui` plus `soltui.tests.test_v2_shell` had 23 passes and one teardown error; after the guard, the previously failing test passed in isolation. The new discovery suite and one UI test passed (5 tests). The full focused suite has **not** been rerun after the guard.
- `python3 index/build.py --check` passed locally after index regeneration at `be6c354`.
- PR 134 checks at handoff: backtester, executor, extension, real-browser extension e2e, liquidity and mongo passed; targeted SolTUI was pending; docs failed. Check current results at https://github.com/mithudso/solmargintrader/actions/runs/42532164868 . The docs failure is test-count drift: files claim 1155 SolTUI / 2459 total; actual 1160 / 2464. Run `python3 scripts/check_docs.py`, update the affected count references and regenerate indexes as dictated by current source. Earlier CI failures at `17ef585` were due to stale index; the later docs failure is distinct.
- No live transaction was placed. No installed or loaded app was verified. Do not say these are verified.

## Next actions

1. Claim TASK-1044 and inspect current master, PR checks and worktree state; read current project instructions and the original untracked guide.
2. Fix the merged docs drift and rerun focused tests. Preserve any changes made after this handoff.
3. Design and implement verified Jupiter discovery, quote, balance/fee checks, immutable reviewed transaction, explicit submission, persistent locking and on-chain reconciliation. Bind the selected full mint and exact reviewed parameters to the transaction; refuse missing, stale, mismatched or unsupported data. Review the existing verifier and its real limits rather than assuming v1 checks cover v2. Tests should include malicious or malformed transactions, ambiguous mint, zero decimals, missing prices, price cap, stale review, double submit, failed simulation, unknown execution and restart recovery.
4. Wire venue-dependent UI and command dispatch; maintain Coinbase behavior and make the selected wallet and venue explicit. Prevent quick mode from bypassing required Jupiter review. Test the actual UI interactions without submitting a real swap.
5. Run appropriate tests, docs/index checks, required CI on the final commit, merge only after checks pass, and confirm the remote result. Verify the actual loaded application separately. Keep the task open until all acceptance criteria are met.
