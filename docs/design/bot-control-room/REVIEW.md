# Bot control room: browser acceptance review

Version: 1.2.0
Delta: 1.1.0 to 1.2.0; verify the durable single-file export through file:// without repeating the full suite.
Delta: 1.0.0 to 1.1.0; recheck four source repairs, verify final loaded identity, and refresh clean-state captures.

## Scope and identity

This review covers the illustrative browser prototype only. It does not verify a production installation, an account connection, trading, job execution, or profitability. Expert review and browser observations are not participant research, a complete WCAG audit, or optimizer convergence.

- Source checkout: /Users/mitch/dev/solmargintrader-wt-01a1c198
- Source baseline: `4d4c7a137b8f78a9e2655c059ca75dfcec0f2b36` plus uncommitted design files.
- Loaded origin: http://127.0.0.1:18796/
- Browser: existing Chrome for Testing `156.0.8078.47`, launched headlessly through existing Playwright in a separate temporary context. No dependency installation.
- The shared Chrome DevTools MCP could not open because its browser profile was already running. The reviewer preserved that browser and used an independent process.
- Final browser recheck: 2026-11-09T18:54:43.258Z.

Final browser-fetched SHA-256 digests matched disk exactly:

| File under /Users/mitch/dev/solmargintrader-wt-01a1c198/docs/design/bot-control-room | SHA-256 |
| --- | --- |
| index.html | `03e0f2f4c35ab4175f572e18b83242634bb44ebb71301bd9dc613134b154ca63` |
| mockup.js | `36026a581b603e3adbb885a5eabc7d70e476fbe651371f54c76d92af40b8810e` |
| mockup.css | `fddb1efa7adb3a51f6feb7a679adba260f13bcd4b9a13e99560d36e0096f1cb1` |

## Observed checks

The final independent Node/Playwright run completed with exit code 0 and 49 passing assertions, with zero assertion failures. It exercised rendered controls rather than importing the prototype's functions. The initial run passed 28 functional assertions and identified the four defects below. The final run checked those repairs as well as the original flows.

| Check | Observed result |
| --- | --- |
| Select ETH accumulator | Inspector shows negative net P&L `−$28.40`. |
| Search for a nonexistent bot | Zero table rows; explanatory empty state is visible. |
| Filter to held bots | Only Council appears. |
| Inspect held Council | Resume control is disabled; stale inputs remain the reason. |
| Pause and resume Grid | Fleet changes from 3 running to 2, then back to 3. Other bots retain state. |
| Live-readiness dialog | Shows unavailable capability, no account, and no order route. Escape closes and returns focus to its opener. |
| Five strategy choices | Grid, DCA, Trend, Council and Arbitrage each update the preview. |
| Invalid allocation | A zero allocation cannot advance from market/budget. |
| Grid spacing | Selecting Geometric updates the readable rule; exit remains one level above the buy. |
| Invalid exposure | Exposure above the allocation produces a specific error and cannot advance. |
| Review checkbox | Saving is refused until review is acknowledged. |
| Complete creation | Repeated submission through the Save control creates exactly one new draft; P&L remains unavailable and no worker starts. |
| Step navigation | Forward focuses the new step heading; Back focuses the restored step heading. |
| Command palette | Meta+K opens and focuses search; a nonempty search closes on the first Escape and restores opener focus. |
| Equity coordinates | Starting-capital baseline is y=130; final point is y=36.46, matching $10,000.00 and $10,311.80 on the linear scale. |
| Name containing `<script>` | Name renders as literal text. No injected element runs. |
| Network and console | No page errors; functional run requested only the local HTML, CSS and JavaScript using GET. |
| Accessible names | Sampled visible, enabled anchors, buttons, fields and selects have a label or accessible-name source. |

## Findings and verified repairs

| ID | Severity | Location | Evidence and requested repair | Status |
| --- | --- | --- | --- | --- |
| BCR-01 | Medium | `.desk-main`, `.performance`, roster at 320 CSS px | Page width is 377 px for a 320 px viewport. Grid min-content expands the main column. The author added appropriate `min-width: 0`, wrapped narrow headings and contained table overflow. Final page width is 320 px for the 320 px viewport. | Fixed and rechecked |
| BCR-02 | Medium | `.form-step h2`, creator submit focus | Advancing to step 2 leaves focus on `#next-step`. The query selects the earlier heading, but it is not focusable. The author made step headings programmatically focusable and added `focusStep()`. Forward and Back now focus the new step heading. | Fixed and rechecked |
| BCR-03 | Medium | `#command-query`, `#command-dialog` | With a nonempty search, first Escape clears the native search field while leaving the modal open; second Escape closes it. The instruction says “Escape to close.” The author changed the query field to text. The first Escape now closes the modal and restores the opener. | Fixed and rechecked |
| BCR-04 | Medium | `.equity-chart` coordinates, baseline and labels | Axis labels imply 150 USD per 45 y units. Starting y=139 and ending y=23 do not match the displayed $10,000.00 and $10,311.80. The author aligned the drawing and baseline to the stated values. The final baseline y=130 and endpoint y=36.46 match the linear axis. | Fixed and rechecked |

The visual structure supports its intended tasks: fleet and selected-bot details remain adjacent on desktop; negative results and held status use text as well as color; the studio exposes strategy risks beside each template; illustrative and paper scope remain visible. These are expert judgments, not measured user outcomes.

## Contrast samples

Computed CSS colors and effective solid ancestor backgrounds were measured with the WCAG sRGB relative-luminance equation. These samples exceed 4.5:1 for normal text. This is sampled verification, not proof that every rendered state passes.

| Sample | Ratio |
| --- | --- |
| Main secondary text on canvas | 5.46:1 |
| Primary button text | 6.47:1 |
| Paper workspace badge | 6.48:1 |
| Design disclosure banner | 6.55:1 |
| Active sidebar navigation | 8.84:1 |
| Sidebar explanatory text | 8.10:1 |
| Held-state text on white | 6.78:1 |
| Negative P&L on white | 6.24:1 |
| Neutral badge | 5.68:1 |
| Live-readiness link | 5.97:1 |

## Viewport coverage and captures

| Viewport | Observed state | Result |
| --- | --- | --- |
| 1440 × 1100 | Fleet, studio | Page width equals viewport width. Desktop screenshots inspected. |
| 390 × 844 | Fleet | Page width equals viewport width. Final full-page screenshot inspected. |
| 320 × 844 | Fleet, evidence, studio template/risk/review | Page width equals viewport width in every sampled state. BCR-01 is repaired. |

Final clean-state captures were refreshed after source repairs, without created test bots:

- /Users/mitch/dev/solmargintrader-wt-01a1c198/docs/design/bot-control-room/screens/fleet-desktop.png — 1440 × 1751, full page.
- /Users/mitch/dev/solmargintrader-wt-01a1c198/docs/design/bot-control-room/screens/studio-desktop.png — 1440 × 1100.
- /Users/mitch/dev/solmargintrader-wt-01a1c198/docs/design/bot-control-room/screens/fleet-mobile.png — 390 × 2973, full page.

Screen-reader use, human task testing, every browser and every possible input remain unverified.

## Final gate

Passed for the stated prototype scope: all four findings were repaired and rechecked, final loaded files match disk, all 49 final assertions pass, and screenshots show the final clean state. No additional probe is needed for this scope. Production integration and the explicitly unverified checks above are outside this acceptance receipt.


## Durable single-file export acceptance

Observed at 2026-11-09T18:57:08.091Z in a new isolated headless Chrome for Testing 156.0.8078.47 context. The focused verification command exited 0. The full 49-assertion suite was not repeated.

- Export: /Users/mitch/Downloads/sol-bot-control-room-2026-11-09.html
- Export SHA-256: `808371f16713688f21eeb5c2c367bf646bd9d5b37adc0c7cdbeff4b12182dc48`.
- Loaded origin: `file:///Users/mitch/Downloads/sol-bot-control-room-2026-11-09.html`.
- The fleet loads with the five clean illustrative bots. The Create route opens the studio and displays “A strategy with a plan.”
- No browser console errors or page errors occurred. The browser requested only the local export file. There were no HTTP, HTTPS or other external requests.
- The loaded inline CSS and JavaScript contain the exact reviewed source bytes, with one wrapper newline before and after each source. Raw inline hashes therefore differ from the source hashes; trimming boundary whitespace produces the matching hashes below. No code or style content changed.

| Embedded source | Reviewed source SHA-256 | Matching boundary-trimmed SHA-256, loaded inline and disk source |
| --- | --- | --- |
| mockup.css | `fddb1efa7adb3a51f6feb7a679adba260f13bcd4b9a13e99560d36e0096f1cb1` | `ecfb64cfc652da7bbc18d3550330f6ae7c6d72e625f6e8dab5190c0431f02d76` |
| mockup.js | `36026a581b603e3adbb885a5eabc7d70e476fbe651371f54c76d92af40b8810e` | `612267796235d9f357dabb48a8c93ce691ea02085b1899f7821e99d9dfb60201` |

Passed for the focused export scope. The export remains an illustrative design with no connected account or execution path.
