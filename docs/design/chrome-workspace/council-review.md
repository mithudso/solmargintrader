# Advisor council review

Version: 1.1
Delta: v1.0 to v1.1; all three advisors verified corrections in round 2; zero residual actionable findings.
Scope: one UI design option and isolated synthetic prototype, no production interface change.

Three independent agent contexts reviewed the draft. These are model-based advisor perspectives, not human endorsement or different-model consensus. Product/accessibility reviewer: `/root/council_product`; quantitative research reviewer: `/root/capability_inventory`; operations/extension reviewer and independent browser verifier: `/root/council_ops` (live-acceptance-verifier). The quantitative reviewer had also audited the source capability map, independently of the proposal author.

Round 1 surfaced 12 numbered criticisms and one additional threshold clarification. All 13 are actionable and implemented below. No conflicting recommendations required discarding another advisor's correction. Round 2 verifies the revised artifacts before the option is presented. Scope is proposal quality, source accuracy and prototype behavior; full production accessibility conformance and live-trading acceptance are future implementation gates, not implied approvals.

| ID | Severity | Criticism | Implemented revision | Verification |
| --- | --- | --- | --- | --- |
| P01 | Medium | Unavailable scores retained positive labels/styling | Preview updates dependent subtitles, score styling, eligible count, badge, scale and historical table labels together | Browser exercise fresh/stale/missing/offline; round 2 resolved |
| P02 | Medium | Dialogs had no accessible names | Both dialogs reference their exact heading using aria-labelledby | Accessible name/escape/focus return check; round 2 resolved |
| P03 | Medium | Narrow layout hid secondary routes | Mobile secondary navigation remains visible and wraps | 390px reachability/overflow check; round 2 resolved |
| P04 | Low | Unmatched strategy filter produced a blank table | Live status says No matching strategies with Clear filter recovery | Filter unmatched/clear/browser focus check; round 2 resolved |
| Q01 | Medium | Included fixture vote expired at capture | T-04 current call is 14:30–14:35, capture 14:32 | Date order agrees; expired learners stay excluded; round 2 resolved |
| Q02 | Medium | Single-horizon F-012 showed four pending calls | Pending count is one; 137/216 resolved accuracy remains separate | Trial/horizon/count consistency; round 2 resolved |
| Q03 | Medium | All Inspect controls opened T-04 evidence | T-04 and M-02 have distinct evidence; grouped row lists four member identities | Click each and inspect correct version/group; round 2 resolved |
| Q04 | Medium | CPCV metric and benchmark aggregation ambiguous | Explicit median ten-OOS-path labels, path construction/dispersion and matched costed benchmark | Headline/detail aggregation consistent; round 2 resolved |
| Q05 | Medium | Ideal metrics treated as existing summary fields | Proposal metric contract separates existing results from Phase 2 path/cost/benchmark work; mockup labels synthetic proposed metrics | Source contract versus phases; round 2 resolved |
| Q06 | Low | Forward accuracy lacked baseline/uncertainty disclosure | Ledger gives matched 216-call baseline, sample scope, pending exclusion and dependence caveat | Details distinguish classification and profit probability; round 2 resolved |
| Q07 | Low | Forward threshold explanation omitted strategy-wide floor | Explain both strategy-wide and each contributed horizon accuracy/count floors | Match existing live score policy; round 2 resolved |
| O01 | Medium | Complete registry fallback could expose archived Resume | All tools preserves discoverability while archived/policy-blocked mutators are unavailable; no routine LP reactivation | Proposal/navigation/library/archive checks; round 2 resolved |
| O02 | Medium | Keyword docs.search can also trigger indexing | Default uses docs.list and UI-local filtering; every docs.search is explicit and resource-disclosed, or future no-side-effect adapter | Source command/README contract; round 2 resolved |

Artifacts under review:

- /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/proposal.md
- /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/prototype.html

## Decision and review status

Round 2 completed. Product/accessibility resolved P01–P04; quantitative research resolved Q01–Q07; operations resolved O01–O02. All three reported zero residual actionable findings, including Low. No third round was needed. The final prototype SHA-256 is `4cdcbc154e4a9c903174531e9c46bc8ba43bbda3a0d9234ba7c903653bed9855`.

Product and quantitative acceptance were independent source/artifact judgments (ISOLATED). The operations specialist additionally exercised the loaded prototype in a browser and matched served bytes plus loaded script/style hashes to disk (EXECUTED). The design option can now be presented. These reviews do not establish real trading behavior or measured usability.

Independent final browser identity/behavior evidence is in /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/acceptance.md.
