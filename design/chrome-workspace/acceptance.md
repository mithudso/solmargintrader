# Independent prototype acceptance

Version: 1.0
Delta: record final operations council re-review and observed standalone browser behavior.
Verifier: `live-acceptance-verifier`, definition 1.0.0, independent context `/root/council_ops`.
Observed: 2026-11-09 03:58–04:00 UTC.
Result: **Complete for the standalone proposal demonstration. No residual operations findings.**

## Subject and identity

Canonical artifact: /Users/mitch/dev/solmargintrader/docs/design/chrome-workspace/prototype.html.

Inspected private artifact: /Users/mitch/dev/solmargintrader-wt-01a1be64/docs/design/chrome-workspace/prototype.html.

Source baseline: `2ca304188c71bf258be5d1acb6a60ee5eefca8e9`. The prototype is a new proposal artifact; it is not an installed extension revision.

Observed origin:

http://127.0.0.1:8914/prototype.html

| Binding | SHA-256 | Result |
| --- | --- | --- |
| On-disk complete HTML | `4cdcbc154e4a9c903174531e9c46bc8ba43bbda3a0d9234ba7c903653bed9855` | Matches the parent's frozen candidate |
| HTTP-served complete HTML | `4cdcbc154e4a9c903174531e9c46bc8ba43bbda3a0d9234ba7c903653bed9855` | Byte-for-byte equal to disk |
| Browser-loaded inline script | `32ae2266c413667472660eba2d5fcac515ee9f0c89a6946dfef6a426e458ef75` | Matches extracted on-disk script |
| Browser-loaded inline style | `71973053e0ff0cf68a65a04aa6a74d10dfdbf474af00b6bb767eb0789ae83c23` | Matches extracted on-disk style |

The verifier reloaded after the final freeze. The verifier computed loaded script/style hashes with browser `crypto.subtle.digest`; Python computed source/served hashes and exact byte equality separately. Earlier exploratory loads occurred while the author was editing and are not the acceptance candidate.

Chrome DevTools MCP could not launch another browser on the parent's active profile. The verifier left that profile untouched and used the available Playwright browser tools in a separate tab. Browser inspection and interaction were executed by those tools, not inferred from the source.

## Observed interaction checks

| Check | Observed result |
| --- | --- |
| Desktop navigation, 1440×1000 | All five destinations switch to exactly one visible screen, update title, move focus to its heading and produce no document horizontal overflow |
| Narrow navigation, 390×844 | All five screens fit the document width; all four primary and four secondary navigation entries remain rendered; Settings opens its detail |
| Backtest-to-paper handoff | R-024 stages an explicitly labeled draft and opens Forward testing; existing trial F-012 remains Observing; notice states nothing started |
| Pause/resume demonstration | Button changes only the fixture label between Paused and Observing, with explicit no-service-change status |
| Stale, missing and disconnected previews | Agreement reads Unavailable; subordinate text says no current interpretation; score uses neutral ink and a neutral chip; retained fixture rows say Historical / excluded |
| Recovery to fresh preview | Returns the synthetic +67 agreement, six eligible strategies and correctly marked fixture rows |
| Strategy filter, no match | Shows zero visible rows, explanatory live status and a Clear filter action |
| Clear filter | Restores all five fixture rows and empties the input |
| Keyword search | Query `paper` returns the Forward testing destination without network/model/index activity |
| Evidence identity | T-04, M-02 and grouped fixture buttons open distinct matching evidence; current calls resolve at 14:35 after the 14:32 snapshot |
| Dialog names and focus | Both dialogs reference valid heading IDs. Escape closes each dialog and restores its triggering control's focus after native close processing |
| Native close timing | Verification waited two animation frames before reading closed/focus state; no synchronous-close assumption was used |
| Script syntax | Extracted JavaScript passed `node --check --input-type=commonjs`, exit 0 |
| Console | Playwright reported 0 errors and 0 warnings |
| Network | Playwright recorded only the local HTML document GET; resource timing recorded no subresources |

The loaded CSP has `connect-src 'none'`, `default-src 'none'`, and `form-action 'none'`. The standalone page intentionally allows its inline script/style and has no operational backend. This is not the production extension's CSP or a proposed CSP relaxation.

## Operations council resolutions

**O01 — archived controls in the registry fallback: resolved.** The proposal now applies archive policy to All tools. Archived mutators, including `liquidity.resume`, remain discoverable as unavailable. Ordinary controls cannot reactivate the discontinued service. The mockup's library/archive text follows that policy. The underlying registry is not changed by this proposal.

**O02 — search side effects: resolved.** The proposal and mockup now distinguish UI-local registry/catalog filtering from any `docs.search` invocation. Every backend search mode can trigger the idle index check; semantic mode can start Ollama. The default is `docs.list` plus local filtering. Any backend search is deliberate and discloses its resource effects, unless a future scoped adapter provides side-effect-free search.

The source review also confirmed the separate native-session and detached-worker lifetimes, unknown-submit reconciliation, blocked Trigger signing versus manual Jupiter spot, separate full-executor integration work, and disabled archived liquidity. Relevant current contracts are /Users/mitch/dev/solmargintrader/docs/EXTENSION-TUI-PARITY.md:47, /Users/mitch/dev/solmargintrader/soltui/README.md:327, /Users/mitch/dev/solmargintrader/executor/README.md:19 and /Users/mitch/dev/solmargintrader/liquidity/CLAUDE.md:3.

## Limits

This verifies a synthetic, standalone design option. It does not establish installed-extension/native-host acceptance, real fills, model quality, profitable research, production job persistence or production adapters for proposed metrics. No installed extension was reloaded; no host, recorder, trainer, scheduler, indexing process or trading service was started. No venue requests, orders, signing, credentials or user settings were used.

Dialog naming, Escape/focus behavior, responsive reachability and browser console/network were observed. A full WCAG conformance audit, contrast/200% zoom audit and screen-reader task test were outside this demonstration acceptance and remain production implementation gates in the proposal.

## Verification artifact cleanup

Playwright wrote three navigation snapshots under /Users/mitch/dev/solmargintrader/.playwright-mcp while using its configured workspace root. The verifier moved only those known task-owned files to /tmp/solmargin-ui-review-artifacts and removed the original directory only after it was empty. Shared Git status returned to its original three unrelated untracked paths. The browser session had renumbered the verifier tab from 1 to 0. The verifier listed the tab, confirmed its prototype URL, then closed that tab. The parent Chrome DevTools tab was not changed.
