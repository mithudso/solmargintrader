# Manual Jupiter swaps and paper cost scenarios

The control room can choose Jupiter as a swap provider while retaining Coinbase
as the labelled reference-price source. These are separate choices. A Coinbase
reference observation does not establish a Jupiter executable quote or total
execution cost.

## Isolated manual page

The manual Jupiter interface runs on a separate `127.0.0.1` port. That origin
serves only public configuration, its local HTML/JavaScript and HTTP health. It
has no owner store, control-room session, action endpoint, key reader, signer or
server order submission path. The parent embeds it in a sandboxed frame and must
keep the child port separate from the privileged control-room origin.

The local page does not load the third-party SDK at page load. A manual click
loads `https://plugin.jup.ag/plugin-v1.js`. The integrated Plugin receives
`autoConnect: false` and no wallet passthrough. Users connect their browser wallet
inside Jupiter, inspect its actual quote, and approve each wallet action. The
server never obtains signing custody. This does not change the native preview
path's blocked submission boundary.

Local HTTP health proves that the public page is listening. It does not prove
CDN availability, wallet connection, referral eligibility, transaction economics
or a funded swap. A missing SDK reports unavailable. There is no automatic retry
or fee escalation. Only SOL and USDC have verified initial mint mappings here;
another requested symbol requires an explicit initial-pair selection rather than
an invented wrapped-token mint. Jupiter's own token picker remains the user's
manual provider interface.

## Referral and actual fees

The owner's public accounts are recorded in the referral decision, `KNOW-1062`:

- Ultra: `9chjbn8wvLUbGCrWF3nYRF4xnhixnGHh5xrhvpQwrrQ9`.
- Swap/Trigger: `85vN9xt5wwXk3M4ikQ9amWs38QfFLu6kjqaz22wX9NsD`.

The current Plugin FAQ directs referral setup through the Ultra guide, so this
Plugin configuration uses the recorded Ultra account. The owner explicitly
approved **0.5% = 50 bps** as the default referral fee. Release 0.2.1 applies that
choice to the manual page and the referral assumption for new Jupiter paper
scenarios. The current published `/order` referral range is **50–255 bps**; the
new default is within that range. A manual choice outside the supported range
keeps Plugin initialization unavailable.

This is an explicit user-approved default change, not an automatic fee increase.
Existing experiments retain their frozen cost profiles, including earlier
explicit 10 bps assumptions. The release does not rewrite earlier calls,
settlements, backtests or P&L. The manual page still requires a click to load the
SDK, then a browser-wallet connection and approval for each action.

Matching the published fee range only passes the local configuration gate. It
does not establish on-chain referral eligibility or funded-swap readiness. Quote
fields must establish which fees actually applied. Jupiter documents that an
uninitialized referral token account can fall back to the default platform fee.
The user must inspect the provider and wallet preview. Network/priority charges,
token-account rent, route/platform costs, slippage and price impact remain
unknown until actual quote and transaction evidence are available. Avoid counting
a fee twice when it is already included in the quoted output.

Official documentation checked on 2026-11-10:

- https://developers.jup.ag/docs/tool-kits/plugin
- https://developers.jup.ag/docs/tool-kits/plugin/faq
- https://developers.jup.ag/docs/swap/order-and-execute#referral-fees

## Provider-independent paper costs

`validate_cost_model()` accepts an explicit `source: configured_scenario` with
base `fee_bps`, `referral_fee_bps`, `slippage_bps`, `borrow_long_bps_hour` and
`borrow_short_bps_hour`. For a new Jupiter scenario that omits an explicit
referral assumption, it defaults to the approved 50 bps. It computes
`total_fee_bps = fee_bps + referral_fee_bps`. The existing paper
engine consumes that total once, so validation of a persisted normalized model
does not add the referral a second time.

These fields are modelled per-side assumptions, not live fee observations. They
do not infer a lower fee from a Jupiter provider choice and do not relabel the
price source. A model can explore 10 bps without claiming that the live Plugin
accepts it. The reused F5 accounting scenario retains its own borrow and fill
semantics; the provider selector does not establish spot execution support.
Network/priority fees, rent and changing route charges remain unmodelled here.
Modelled net P&L therefore does not establish realized profit after every actual
execution cost.

## Existing installations and generation handoff

The new UI environment is `/Users/mitch/.venvs/solecosystem-0.2.1`. Keep completed
older environments immutable. Updating this release replaces only the separately
owned control UI generation after its lock, checkpoint and HTTP identity have
been reconciled. The existing V1 and V2 pipeline processes, Oracle archives,
shared recorder and frozen accounting settings remain running under their own
owners. Their version labels need not equal the new UI's version.

In particular, retain `/Users/mitch/.venvs/solecosystem-0.1.1` for the legacy V1
owner and `/Users/mitch/.venvs/solecosystem-0.2.0` for the existing V2 pipeline.
The UI generation update does not upgrade either environment in place.

The primary control home remains
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2`. The replacement
foreground UI command, after the prior UI generation has stopped, is:

```sh
/Users/mitch/.venvs/solecosystem-0.2.1/bin/solecosystem-ui \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2 --port 8768
```

Do not restart a pipeline merely to update its control UI. Do not use a blanket
process kill or reinterpret a PID as owner identity. A new page's 50 bps default
does not alter an existing pipeline's explicit 10 bps scenario.

## Source locations and checks

- `/Users/mitch/dev/solmargintrader/ecosystem/swaps.py` owns public settings and
  cost validation.
- `/Users/mitch/dev/solmargintrader/ecosystem/swap_web.py` owns the isolated public
  HTTP origin.
- `/Users/mitch/dev/solmargintrader/ecosystem/web/swap.html` and
  `/Users/mitch/dev/solmargintrader/ecosystem/web/swap.js` own the manual page.
- `/Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py` remains the separate
  native unsigned-preview owner.

```sh
python3 -m unittest ecosystem.tests.test_swaps ecosystem.tests.test_swap_web
node --check /Users/mitch/dev/solmargintrader/ecosystem/web/swap.js
```

Tests use isolated HTTP servers and controlled browser-contract inspection. They
do not connect a wallet, request a funded quote, sign or submit a transaction.
