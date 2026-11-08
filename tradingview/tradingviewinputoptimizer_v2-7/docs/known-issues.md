# Known issues and limits

Observed by static inspection on 2026-11-08:

- The directory suffix says v2-7, while the manifest and popup say 2.3.11. Treat the manifest as the declared runtime version.
- `manifest.json` includes `workers.js` in web-accessible resources, but no such file exists at the bundle root. Runtime impact is unverified; a declaration alone does not show it is requested.
- `test.html` references `../subworkers.js`, `browser.js` and `blob-browser.js`; the relative targets are absent. It is not a working automated optimizer suite.
- The source is largely obfuscated/minified. Visible symbols and strings cannot establish full message validation, retry behavior or security correctness.
- The manifest declares minimum Chrome 88 while code uses additional browser APIs; no compatible browser range was tested.
- Parent Git ignores the upstream source. A clean parent clone contains these docs but cannot run the extension or fully validate source links without the local bundle.

Unverified: actual extension load, license-service behavior, page UI compatibility, scanner correctness, data round-trip integrity, cancellation and result/statistical validity. The docs-only pass records these limits and does not change runtime behavior.
