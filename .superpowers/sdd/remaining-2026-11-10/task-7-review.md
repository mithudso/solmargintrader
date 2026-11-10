# Task 7 independent review

Version: 1.0.2
Delta: final independent re-review of pending-awareness repair at source HEAD f24ad194a541f99e4a6902a5c054d046fb90c48e; all five concrete review findings resolved. Historical findings and reproductions retained below.

## SPEC COMPLIANCE — PASS (source-review scope)

The original four findings and the subsequent enrollment awareness replay finding are resolved. Shared authority retains imported uncertainty and conservative ceilings, manager live authorization explicitly fails closed, and dry-run evaluates the shared financial gates without reserving capital. No open source-review blocker remains in the reviewed Task 7 scope. Final integrated checks, independent regular installed acceptance, and remote delivery remain controller gates; this verdict does not certify production trading or completion of those gates.

## CODE QUALITY — PASS

The fixes address the failure conditions directly and include targeted adversarial regressions. The pending enrollment now binds exact normalized writer awareness in addition to roots/history/cap. Conflicting or legacy incomplete replay refuses, while unchanged replay retains the unaware writer barrier. No additional code change is requested by this review.

## Final awareness repair verification

Inspected /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/authority.py:237-251 and /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/tests/test_authority.py:704. The pending `writers` map is generated from the normalized absolute-root inventory and participates in the existing exact replay comparison. Missing writer maps fail closed. First-enrollment and additional-client tests check false-to-true rejection, unchanged pending bytes, successful original replay, and retained unaware-writer refusal.

Independently executed from /Users/mitch/dev/solmargintrader-wt-01a1c447/executor:

```sh
/Users/mitch/.local/state/solbot/releases/0.5.0/executor-test-venv/bin/pytest -q tests/test_authority.py -k 'crashed_enrollment_retains_exact_unaware_writer_inventory or old_pending_enrollment_without_awareness_refuses_replay'
```

Result: **3 passed, 59 deselected in 0.06 seconds; final exit 0**. Source HEAD was f24ad194a541f99e4a6902a5c054d046fb90c48e, with no unstaged diff in the reviewed authority source or test file. The worker's reported full run of 491 passes/5 network deselections and Ruff checks remains supplied evidence; this final review reran only the three requested crash cases. The earlier independent 59 authority and 11 adapter checks are recorded below.

Only this report was edited by the reviewer. Tests used isolated temporary fixture authorities and synthetic fixture keys; no real key, real wallet authority, network, installation or live transaction was used. No commit or staging was performed by the reviewer.

## Prior correction review — historical, superseded verdict

The following evidence records the earlier failed re-review. Its remaining awareness finding is now resolved by the final repair above.

## Re-review evidence (correction 2f2eb26)

Commands completed with final exit 0:

- From /Users/mitch/dev/solmargintrader-wt-01a1c447/executor: `/Users/mitch/.local/state/solbot/releases/0.5.0/executor-test-venv/bin/pytest -q tests/test_authority.py` — **59 passed**, 0.50 seconds.
- From /Users/mitch/dev/solmargintrader-wt-01a1c447: `PYTHONPATH=botmanager/src:backtester:soltui /Users/mitch/.local/state/solbot/releases/0.5.0/executor-test-venv/bin/python -m unittest discover -s botmanager/tests -p test_executor_adapter.py -v` — **11 passed**.
- Scoped `git diff --check` for the four changed authority/engine/admission/manager-command modules — passed.
- Independent TemporaryDirectory reproduction below — exit 0 and printed `crash replay changed known unaware B to aware: ACCEPTED`.

The first combined test command also attempted a source read with an incorrect executor-prefixed path from the executor directory; that read failed, and the correct source path was read in the next command. The pytest result itself completed successfully.

### Resolved original findings

1. Legacy import anchors now persist before policy publication. A durable pending marker blocks ordinary admission after interrupted enrollment. First/additional imported history loss and crash/replay tests pass.
2. All three tighter ceilings persist under the wallet lock. Existing client configuration files are read. Cross-home/default configuration and concurrent-thread regressions pass.
3. Both manager and executor refuse manager-originated live calls, including forged eligible-looking claims, because the current paper-only manager has no live authorization issuer. Direct explicit tracked executor recovery retains KILL/certificate exemptions and the verifier. This is an explicit activation limitation, not live readiness.
4. Dry-run evaluates aggregate policy and measured portfolio budget with reserve=False. The paired cap refusal and no-policy/no-request/no-soak mutation tests pass. Missing authority remains uninitialized. Pending wallet state prevents would_send=True.

### Resolved P1 — Enrollment replay could erase a known unaware writer

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/authority.py:237-247.

The pending enrollment document stores wallet, portfolio cap, history digests and limits. It omits each client's aware flag. Before policy publication there is no old policy from which to recover sticky unaware flags. Replay checks only the pending fields shown above. Thus the same roots and unchanged histories can be replayed with a previously false awareness flag set true, after which check admits the wallet. The same gap applies to a newly added unaware client if an existing authority's enrollment is interrupted before its new policy is published.

Exact independent reproduction, executed with only temporary authority paths:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from executor import authority
from executor.authority import WalletAuthority
from executor.config import Config

with TemporaryDirectory() as t:
    root = Path(t)
    a, b = root / "a", root / "b"
    a.mkdir()
    b.mkdir()
    with patch.object(authority, "wallet_root", lambda owner: root / "wallet"), patch.object(authority, "default_client_root", lambda: a):
        wallet = WalletAuthority(Config(owner="synthetic"), a)
        write = authority._atomic_write
        def crash(path, value):
            if path == wallet.policy_path:
                raise RuntimeError("crash before policy")
            return write(path, value)
        with patch.object(authority, "_atomic_write", crash):
            try:
                wallet.register("100", [{"root": str(a), "aware": True}, {"root": str(b), "aware": False}], True)
            except RuntimeError:
                pass
        wallet.register("100", [{"root": str(a), "aware": True}, {"root": str(b), "aware": True}], True)
        wallet.check()  # Unexpected success: known unaware B has been forgotten.
```

Required repair: bind the normalized writer inventory, including awareness, into enrollment.pending and reject conflicting replay; alternatively preserve an immutable sticky unaware set across replay. Test both first enrollment and additional-client interruption. Exact unchanged replay must still preserve/import unresolved history.

## Historical initial review — superseded findings

The four findings below describe d7aa933 before correction 2f2eb26. They are retained for reproduction history and are no longer open. That P1 was the sole open source-review finding at version 1.0.1 and is resolved in version 1.0.2.

## Findings

### P1 — Initial legacy import is not anchored, so losing the shared journal erases unresolved sends

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/authority.py:180 and :195-198; anchor verification :214-219.

register imports legacy records, writes policy, and creates journal_anchor with count=0. It never saves an anchor for the imported records. check compares only the zero-length prefix. Consequently, deletion or truncation of the shared journal after enrollment but before the first live swap/reconciliation passes check. The unchanged original client history still matches its digest, but is not re-imported. An imported sending/unknown barrier and its risk disappear. This is an actual history-loss case, not a request to defend against an attacker rewriting all authority files.

Reproduction executed offline in TemporaryDirectory, with wallet_root and default_client_root patched to that directory: append legacy intent and sending records to client A; register A; observe one shared unresolved send; unlink only the imported shared journal; call authority.check(); observe success and zero unresolved sends. Output: `imported unresolved before deletion: 1`, `check after imported journal deletion: ACCEPTED; unresolved: 0`. Exit 0.

Required repair: persist the imported history anchor before successful enrollment returns, including additional-client imports. Make incomplete enrollment fail closed and test loss of imported sending history before any swap has run.

### P1 — Tightened limits are not sticky across enrolled clients/config revisions

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/authority.py:182-187 and :231-234.

The durable limits only change during register. effective_config computes a minimum for the current request without retaining it. Tightening an enrolled client's configured position/trade/daily-loss cap does not constrain another enrolled client, or a new home enrolled with defaults. The new home can restore the original higher cap even after the authority has evaluated the tightened client. register also imports other clients' history without reading their tighter configured limits.

Reproduction executed offline with temporary authority: enroll A at defaults; set A config max_position_usd=1; evaluate A effective_config, obtaining 1; enroll B for the same wallet with default Config and unchanged portfolio cap; B effective_config returns 25.0. Output: `current stricter client effective position limit: 1`, `new home effective position limit after tightening first client: 25.0`. Exit 0. The same three-field projection covers max_trade_usd and daily_loss_stop_usd.

Required repair: persist newly observed tighter canonical risk limits under the shared lock, and bind/validate enrolled-client policy revisions so switching homes cannot restore an older ceiling. Include a test that first tightens A without calling register again.

### P1 — Manager live delegation ignores paper/disarmed runtime configuration

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/botmanager/src/botmanager/executor_commands.py:16-55; /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/manager.py:99-110.

_request checks identity fields but never checks pinned mode, resolved_values.armed, or runtime lifecycle. A request setting swap.live=true is forwarded for a paper/disarmed runtime. The downstream owner checks its own live configuration and the opaque config hash, not the manager's mode/arming. A certificate is evidence eligibility, not authorization to override a disarmed manager. Current missing certificates still prevent ordinary production entry; this finding does not claim current autonomous live readiness. It is a missing independent safety gate once compatible evidence exists, and certificate-free tracked exits also traverse this route.

Reproduction executed at the actual _request boundary with mocked storage reads: row.spec mode=paper, resolved_values.armed=False, stopped row, and matching scope identity; swap.live=True is returned unchanged. Output: `paper disarmed stopped runtime live request forwarded: True`. Exit 0. No subprocess, signer or network was invoked. The adapter test suite currently exercises transport, not this boundary.

Required repair: explicitly reject live entry delegation from paper/disarmed or ineligible runtime state; bind the authorization state to the owner request/evidence rather than only an opaque hash. Preserve deliberate tracked recovery exits under the documented executor exit policy instead of applying an indiscriminate entry prohibition.

### P2 — Dry-run skips shared budget and effective aggregate policy

Location: /Users/mitch/dev/solmargintrader-wt-01a1c447/executor/src/executor/engine.py:124-137 and :270-278.

The dry-run branch returns before the shared authority/effective_config path, and _swap_locked returns would_send=True before authority.budget. Thus dry-run can pass local rails and earn soak credit while the exact trade fails the shared portfolio cap or sticky cross-client cap in live mode. This violates executor non-negotiable 6 and weakens the proposed keyless/dry-run acceptance gate.

Reproduction executed with existing in-memory buyer/chain fixtures, synthetic public owner, no key file: enroll a $1.40 shared portfolio cap, then dry-run a $1 USDC-to-SOL trend buy. The reserve plus measured fee makes the live budget fail (the existing portfolio-budget test already covers that amount), but dry-run returns would_send=True. Output: `dry run above shared cap: True`. Exit 0. No signing or network occurred.

Required repair: split shared policy/budget evaluation from reservation mutation. Evaluate the same applicable aggregate financial gates during dry-run without binding/reserving live capital. Add paired dry-run/live refusal tests.

## Reviewed boundaries and limitations

- The public legacy live swap uses the shared wallet lock and shared journal; no separate direct legacy path bypasses that authority. Its older research/soak gates are distinct from manager-scoped evidence. This review does not classify that intentional compatibility surface as a separate defect without a stronger requirement to retire it.
- Exact live replay returns the durable original result. Changed normalized intent/context conflicts. Signing starts after binding and reservation; sending is journaled before the sole application send. Exceptions after sending retain uncertainty and reservation. Reconciliation holds the shared writer before releasing proven-no-send requests.
- Manager scope checks bind strategy/version, config/revision, owner/source/installation identity and receipt bytes. No production issuer exists. Synthetic certificate fixtures establish branches only, not real eligibility.
- The pre-existing verifier, mode+live requirement, tracked exit/KILL behavior, and path-validation code caps remain in the flow. No live-money test was performed.
- Reported controller verification (475 offline pytest passes / 5 network deselections, 7 adapter checks, Ruff/format) was treated as supplied evidence, not independently rerun. Two narrowly scoped offline reproduction commands completed with exit 0. All runtime state used TemporaryDirectory and patched authority roots. No production wallet state, real key, installation, service or network was accessed.
- Only this review document was written in the worktree. Product source remains unchanged. Controller owns remediation, regression validation, installed acceptance and delivery.
