/**
 * Page bridge for the Jupiter Perps beta markets (HYPE and ZEC), the only Perps
 * markets where the page offers no take profit or stop loss of its own.
 *
 * A classic content script like page-bridge.js, and with the same contract, so
 * the 1s scalp window drives both pages one way: it can read the listed
 * positions and the order form, ask for one Long or Short press, and ask for
 * one position to be closed. Nothing else on the page is touched.
 *
 * The markup was read from the live order form and from the page's own code on
 * 2026-11-28 (docs/JUPITER-1000X-SCALP.md). No position was open then, so the
 * position row and the close steps come from the code alone. Every read is
 * strict: anything that does not look exactly as expected is refused.
 */
(() => {
  if (globalThis.__smtPerpsBridge) return;
  const RECLICK_MS = 10_000, REOPEN_MS = 5000, OPEN_DEADLINE_MS = 6000;
  // How long the page gets to ask its question after Quick close, and how long a question this bridge caused stays its own.
  const CONFIRM_WAIT_MS = 6000, ASKED_MS = 60_000;
  // The page's Max can sit a little under the balance (fees). Further off than this is not the size asked for.
  const SIZE_FLOOR = 0.85, SIZE_CEILING = 1.0001;
  const SIZE_BUTTON = { 0.5: 'HALF', 1: 'MAX' };
  const CLOSE_TITLE = 'Close Entire Position?';
  const clicks = new Map();
  let lastOpenMs = -Infinity, opening = false, closing = false, asked = null;
  const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
  // Laid out and not hidden by CSS. A copy of the markup kept for another screen width must not count.
  const visible = node => Boolean(node) && (typeof node.checkVisibility === 'function' ? node.checkVisibility({ visibilityProperty: true })
    : typeof node.getClientRects !== 'function' || node.getClientRects().length > 0);
  const off = node => !node || node.disabled === true || node.getAttribute?.('aria-disabled') === 'true';
  const all = (root, selector) => [...(root?.querySelectorAll?.(selector) ?? [])];
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  /** "$63.529" or "1,234.5" -> a positive number. Any other shape is refused. */
  function money(text) {
    const match = /^[$]?\s?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)$/.exec(clean(text));
    if (!match) return null;
    const value = Number(match[1].replaceAll(',', ''));
    return Number.isFinite(value) && value > 0 ? value : null;
  }
  /** "25x" or "21.9x" -> the number, within what the venue allows. */
  function leverageOf(text) {
    const match = /^(\d{1,3}(?:\.\d{1,2})?)x$/.exec(clean(text));
    const value = match ? Number(match[1]) : NaN;
    return value >= 1 && value <= 100 ? value : null;
  }

  /** One position row's visible text -> a position, or the reason it cannot be trusted. */
  function parseRow(cells) {
    const coin = /^[A-Z][A-Z0-9]{0,11}$/.test(clean(cells.coinText)) ? clean(cells.coinText) : null;
    if (!coin) return { ok: false, reason: 'coin_unreadable' };
    // The badge reads like "Long 25x". Exactly one side word and one leverage figure, or it is refused.
    const badge = clean(cells.badgeText), sides = badge.match(/\b(Long|Short)\b/g) ?? [], levers = badge.match(/\d{1,3}(?:\.\d{1,2})?x/g) ?? [];
    if (sides.length !== 1) return { ok: false, reason: 'side_unreadable' };
    const leverage = levers.length === 1 ? leverageOf(levers[0]) : null;
    if (leverage === null) return { ok: false, reason: 'leverage_unreadable' };
    const parts = clean(cells.entryMarkText).split('/').map(clean);
    if (parts.length !== 2) return { ok: false, reason: 'entry_unreadable' };
    const entry = money(parts[0]), mark = money(parts[1]);
    if (entry === null) return { ok: false, reason: 'entry_unreadable' };
    // Entry and mark of one market sit close together. Far apart means a misread, such as a decimal comma taken for thousands.
    if (mark !== null && (entry / mark > 1.5 || entry / mark < 1 / 1.5)) return { ok: false, reason: 'entry_unreadable' };
    return { ok: true, row: {
      coin, side: sides[0].toLowerCase(), leverage, entry, entryText: parts[0], mark,
      // The liquidation price plays the part the bust price plays on 1000x: a stop must sit inside it.
      bust: money(cells.liquidationText), size: clean(cells.sizeText), collateral: clean(cells.collateralText), value: clean(cells.valueText),
      mode: 'Perps', close: cells.close,
    } };
  }

  // One net position per market and side on this venue, so the leverage figure is not needed to tell rows apart.
  const sameRow = (row, expect) => row.coin === expect.coin && row.side === expect.side && row.entryText === expect.entryText;

  // The tab reads "Positions" when the list is empty; with positions it may carry a count, as it does on 1000x.
  const POSITIONS_TAB = /^Positions(?:\s*\(?\d+\)?)?$/;
  const positionsTab = doc => { const found = all(doc, '[role="tab"]').filter(node => POSITIONS_TAB.test(clean(node.textContent)) && visible(node)); return found.length === 1 ? found[0] : null; };

  /** Rows with their quick-close buttons. Callers outside this file only ever see the plain rows. */
  function scan(doc) {
    const tab = positionsTab(doc);
    if (!tab || tab.getAttribute('aria-selected') !== 'true') return { recognized: false, reason: 'positions_tab_not_shown', entries: [] };
    const rows = all(doc, '.perps-position-table-row').filter(visible);
    if (!rows.length) {
      // An empty list is trusted only when the page says it is empty or still loading.
      const text = clean(doc.body?.textContent ?? '');
      if (/Loading positions/.test(text)) return { recognized: true, entries: [], pending: 1, problems: [] };
      if (/No positions/.test(text)) return { recognized: true, entries: [], pending: 0, problems: [] };
      return { recognized: false, reason: 'positions_table_not_found', entries: [] };
    }
    const entries = [], problems = [];
    for (const row of rows) {
      const cells = [...(row.children ?? [])];
      if (cells.length !== 8) { problems.push('row_unreadable'); continue; }
      const symbol = all(cells[0], 'button')[0];
      const coinText = clean(symbol?.textContent);
      const quick = all(cells[7], 'button').filter(button => button.getAttribute('aria-label') === `Quick close ${coinText}`);
      const parsed = parseRow({
        coinText, badgeText: clean(cells[0].textContent).slice(coinText.length), valueText: cells[1].textContent, entryMarkText: cells[2].textContent,
        liquidationText: cells[3].textContent, sizeText: cells[4].textContent, collateralText: cells[5].textContent,
        close: quick.length !== 1 ? { state: 'none', label: '' } : { state: off(quick[0]) ? 'disabled' : 'ready', label: 'Quick close' },
      });
      if (parsed.ok) entries.push({ row: parsed.row, button: quick.length === 1 ? quick[0] : null });
      else problems.push(parsed.reason);
    }
    return { recognized: true, entries, pending: 0, problems };
  }

  /** The listed positions as plain data. */
  function readPositions(doc) {
    const result = scan(doc);
    return result.recognized
      ? { recognized: true, positions: result.entries.map(entry => entry.row), pending: result.pending, unreadable: result.problems.length, problems: result.problems }
      : { recognized: false, reason: result.reason, positions: [] };
  }

  /** Every open "Close Entire Position?" question, each with its own Confirm (null when it has none) and its text. */
  function closeDialogs(doc) {
    return all(doc, '[role="dialog"], [role="alertdialog"]').filter(node => visible(node) && clean(node.textContent).includes(CLOSE_TITLE)).map(node => {
      const buttons = all(node, 'button'), named = label => buttons.filter(button => clean(button.textContent) === label);
      const confirm = named('Confirm'), dismiss = named('Dismiss');
      // Both of the dialog's own buttons must be there: that is what tells it from any other dialog.
      return { text: clean(node.textContent), confirm: confirm.length === 1 && dismiss.length === 1 ? confirm[0] : null };
    });
  }

  /**
   * Close exactly the expected position with the row's own Quick close button,
   * and answer the page's "Close Entire Position?" question if it asks. Never
   * "Close All", never a second Quick close within ten seconds, never a row
   * that is not a unique match, never a question about another market or one
   * this bridge did not cause. A market order follows; the wallet may still ask.
   */
  async function closePosition(doc, expect, { now = Date.now, wait = sleep } = {}) {
    if (!expect || typeof expect.coin !== 'string' || !['long', 'short'].includes(expect.side)
        || typeof expect.entryText !== 'string' || !expect.entryText) return { clicked: false, reason: 'invalid_request' };
    // Another close is still being carried out: ask again shortly. Not a press.
    if (closing) return { clicked: false, retry: true, reason: 'page_busy' };
    const key = [expect.coin, expect.side, expect.entryText].join('|'), started = now();
    /** Wait for the page's question about this market and press its Confirm once. */
    const answer = async () => {
      // Bounded by the clock, not by a count of waits: timers crawl in a hidden tab.
      for (let i = 0; i < 1000 && now() - started < CONFIRM_WAIT_MS; i++) {
        await wait(50);
        const dialogs = closeDialogs(doc);
        if (!dialogs.length) continue;
        if (dialogs.length > 1 || !dialogs[0].confirm || !dialogs[0].text.includes(expect.coin)) return { clicked: false, reason: 'close_confirm_unavailable' };
        if (off(dialogs[0].confirm)) continue;
        dialogs[0].confirm.click();
        asked = null;
        return { clicked: true, label: 'Quick close', confirmed: true };
      }
      // Still asking with its Confirm disabled: the next request picks the same question up again.
      if (closeDialogs(doc).length) return { clicked: false, retry: true, reason: 'close_confirm_unavailable' };
      asked = null;
      return { clicked: true, label: 'Quick close', confirmed: false };
    };
    const open = closeDialogs(doc);
    if (open.length) {
      // A question this bridge caused for this very position, moments ago, is still its own to answer.
      if (open.length !== 1 || !asked || asked.key !== key || started - asked.at > ASKED_MS) return { clicked: false, reason: 'close_dialog_already_open' };
      closing = true;
      try { return await answer(); } finally { closing = false; }
    }
    const result = scan(doc);
    if (!result.recognized) {
      // The list only exists on the Positions tab. Select it and let the caller ask again; a list caught mid-render is asked again too.
      const tab = positionsTab(doc);
      if (result.reason === 'positions_tab_not_shown' && tab) { tab.click(); return { clicked: false, retry: true, reason: 'opened_positions_tab' }; }
      return { clicked: false, retry: result.reason === 'positions_table_not_found', reason: result.reason };
    }
    const matches = result.entries.filter(entry => sameRow(entry.row, expect));
    if (matches.length === 0) return { clicked: false, reason: 'position_not_listed' };
    if (matches.length > 1) return { clicked: false, reason: 'ambiguous_position' };
    const [{ row, button }] = matches;
    if (clicks.has(key) && started - clicks.get(key) < RECLICK_MS) return { clicked: false, already: true, reason: 'recently_clicked', label: row.close.label };
    if (row.close.state === 'disabled') return { clicked: false, retry: true, reason: 'close_disabled', label: row.close.label };
    if (row.close.state !== 'ready' || !button) return { clicked: false, reason: 'close_unavailable' };
    closing = true;
    clicks.set(key, started);
    asked = { key, at: started };
    try {
      button.click();
      const outcome = await answer();
      // Nothing was sent: the next request must not be told that a press is already out.
      if (!outcome.clicked) clicks.delete(key);
      return outcome;
    } finally {
      closing = false;
    }
  }

  /* ------------------------------------------------------------ order form -- */

  function formParts(doc) {
    const one = (selector, test = () => true) => { const found = all(doc, selector).filter(node => visible(node) && test(node)); return found.length === 1 ? found[0] : null; };
    const long = one('button[role="radio"]', node => node.getAttribute('aria-label') === 'Long');
    const short = one('button[role="radio"]', node => node.getAttribute('aria-label') === 'Short');
    const input = one('input', node => node.getAttribute('aria-label') === 'Collateral amount');
    const range = one('input[type="range"]', node => node.getAttribute('aria-label') === 'Leverage');
    if (!long || !short || !input || !range) return null;
    // The order form is the smallest box that holds the amount, the slider and both side buttons; its buttons are looked up inside it.
    let root = input.parentElement ?? null;
    const holds = (box, node) => all(box, node === range ? 'input[type="range"]' : 'button[role="radio"]').includes(node);
    while (root && !(holds(root, range) && holds(root, long) && holds(root, short))) root = root.parentElement ?? null;
    const buttons = all(root ?? doc, 'button').filter(visible);
    const text = label => { const found = buttons.filter(button => clean(button.textContent) === label && !button.getAttribute('role')); return found.length === 1 ? found[0] : null; };
    const tabs = all(root ?? doc, '[role="tab"]').filter(node => visible(node) && ['Market', 'Limit'].includes(clean(node.textContent)));
    const selectedTab = tabs.filter(tab => tab.getAttribute('aria-selected') === 'true');
    const balances = buttons.map(button => /^((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?) USDC$/.exec(clean(button.textContent))).filter(Boolean);
    const checked = node => (node.hasAttribute?.('data-checked') && node.getAttribute('data-checked') !== 'false') || node.getAttribute('aria-checked') === 'true';
    const side = checked(long) === checked(short) ? null : checked(long) ? 'long' : 'short';
    const leverage = Number(range.value);
    return { long, short, input, range, side, half: text('HALF'), max: text('MAX'),
      // The page's own submit button carries the side in its text and has no role; the side switch above it does.
      submit: side ? text(side === 'long' ? 'Long/Buy' : 'Short/Sell') : null,
      mode: tabs.length === 2 && selectedTab.length === 1 ? clean(selectedTab[0].textContent) : null,
      balance: balances.length === 1 ? Number(balances[0][1].replaceAll(',', '')) : null, balanceText: balances.length === 1 ? clean(balances[0][0]) : null,
      leverage: Number.isFinite(leverage) && leverage >= 1 && leverage <= 100 ? leverage : null,
      preset: value => { const found = buttons.filter(button => button.getAttribute('aria-label') === `Set leverage to ${value}x`); return found.length === 1 ? found[0] : null; } };
  }

  /** What the page's order form currently shows. Read only. */
  function readOrderForm(doc) {
    const parts = formParts(doc);
    if (!parts) return { recognized: false, reason: 'order_form_not_found' };
    return { recognized: true, mode: parts.mode, amountText: clean(parts.input.value), balanceText: parts.balanceText, leverage: parts.leverage, side: parts.side,
      longEnabled: !off(parts.long), shortEnabled: !off(parts.short), busy: false, error: '' };
  }

  /**
   * Choose the side, optionally a leverage preset, and half or all of the
   * available collateral with the page's own buttons, then press its Long/Buy
   * or Short/Sell button once. The amount the page then shows must match the
   * chosen share of the balance it shows. No amount is ever typed: this page
   * shows nothing that would prove it took a typed figure. One call at a time,
   * never within five seconds of the last, never late.
   */
  async function openPosition(doc, request, { now = Date.now, wait = sleep, stillValid = () => true } = {}) {
    if (!request || !['long', 'short'].includes(request.side) || !Object.hasOwn(SIZE_BUTTON, request.fraction)
        || !(request.leverage === undefined || request.leverage === null || (Number.isInteger(request.leverage) && request.leverage >= 2 && request.leverage <= 100))) {
      return { clicked: false, reason: 'invalid_request' };
    }
    const started = now();
    if (opening) return { clicked: false, reason: 'page_busy' };
    if (started - lastOpenMs < REOPEN_MS) return { clicked: false, reason: 'recently_opened' };
    // Claimed before the first wait: a second call cannot slip in while this one is parked.
    opening = true;
    lastOpenMs = started;
    try {
      let parts = formParts(doc);
      if (!parts) return { clicked: false, reason: 'order_form_not_found' };
      if (parts.mode !== 'Market') return { clicked: false, reason: 'mode_not_market' };
      if (parts.balance === null) return { clicked: false, reason: 'balance_unreadable' };
      if (!(parts.balance > 0)) return { clicked: false, reason: 'no_balance' };
      const balance = parts.balance;
      // With no preset asked for, the leverage the form shows now is the one the owner planned with: it must still be there at the press.
      const planned = request.leverage ?? parts.leverage;
      if (planned === null) return { clicked: false, reason: 'leverage_unreadable' };
      const near = text => { const value = money(text); return value !== null && value >= request.fraction * balance * SIZE_FLOOR && value <= request.fraction * balance * SIZE_CEILING; };
      /** Poll the form until `ready` holds, for at most a second and a half. */
      const settle = async ready => {
        for (let i = 0; i < 30; i++) {
          await wait(50);
          parts = formParts(doc);
          if (!parts) return false;
          if (ready()) return true;
        }
        return false;
      };
      if (parts.side !== request.side) {
        const radio = parts[request.side];
        if (off(radio)) return { clicked: false, reason: 'side_disabled' };
        radio.click();
        if (!await settle(() => parts.side === request.side)) return { clicked: false, reason: parts ? 'side_not_set' : 'order_form_not_found' };
      }
      if (request.leverage && parts.leverage !== request.leverage) {
        const preset = parts.preset(request.leverage);
        if (off(preset)) return { clicked: false, reason: 'leverage_button_unavailable' };
        preset.click();
        if (!await settle(() => parts.leverage === request.leverage)) return { clicked: false, reason: parts ? 'leverage_not_set' : 'order_form_not_found' };
      }
      const quick = request.fraction === 1 ? parts.max : parts.half;
      if (off(quick)) return { clicked: false, reason: 'size_button_unavailable' };
      quick.click();
      // A value left in the field from before only passes if it is the size this button gives.
      if (!await settle(() => near(parts.input.value))) return { clicked: false, reason: parts ? 'amount_unexpected' : 'order_form_not_found' };
      await settle(() => parts.submit && !off(parts.submit));
      if (!parts) return { clicked: false, reason: 'order_form_not_found' };
      if (off(parts.submit)) return { clicked: false, reason: 'side_disabled' };
      // Timers crawl in a hidden tab. A press that comes late is one the owner has stopped expecting.
      if (now() - started > OPEN_DEADLINE_MS) return { clicked: false, reason: 'too_slow' };
      if (parts.mode !== 'Market' || parts.side !== request.side || !near(parts.input.value) || parts.balance !== balance || !stillValid()
          || parts.leverage !== planned) return { clicked: false, reason: 'page_changed' };
      parts.submit.click();
      // The row's own leverage figure is entry size over collateral and need not equal the form's, so the
      // window is told not to match on it: one net position per market and side is enough to find the new row.
      return { clicked: true, amountText: clean(parts.input.value), leverage: null, formLeverage: parts.leverage };
    } finally {
      opening = false;
    }
  }

  globalThis.__smtPerpsBridge = Object.freeze({ money, leverageOf, parseRow, readPositions, closePosition, readOrderForm, openPosition });
})();
