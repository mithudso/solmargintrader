/**
 * Reads the Jupiter 1000x positions table and order form, and presses their buttons.
 *
 * A classic content script: it defines one object in the isolated world and
 * does nothing until content.js relays a request from this extension's own
 * background worker. It reads text the page already shows and clicks a button
 * the owner could click: one position's Close, the order form's size buttons
 * and its Long or Short button. It never touches the wallet and never reads
 * page storage. Anything it cannot read exactly is refused.
 *
 * The table layout is the one observed in the public bundle (English labels):
 * docs/JUPITER-1000X-SCALP.md records the evidence and its limits.
 */
(() => {
  if (globalThis.__smt1000xBridge) return;
  const HEADERS = { position: 'Position', value: 'Value / PnL', entryMark: 'Entry / Mark price', bust: 'Bust price',
    size: 'Size', collateral: 'Collateral', held: 'Held', status: 'Status' };
  // The page shows a display name for two markets; the URL and the feed use the catalog symbol.
  const DISPLAY = { GOLD: 'XAU', OIL: 'WTI' };
  const RECLICK_MS = 10_000;
  const clicks = new Map();
  const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();

  /** "$59,905.26" -> 59905.26. Any other shape (locale decimals, ranges, words) is refused. */
  function money(text) {
    const match = /^[$]?\s?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)$/.exec(clean(text));
    if (!match) return null;
    const value = Number(match[1].replaceAll(',', ''));
    return Number.isFinite(value) && value > 0 ? value : null;
  }

  /** What the row's own button currently offers. */
  function closeState(buttons) {
    const list = (buttons ?? []).map(button => ({ text: clean(button.text), disabled: button.disabled === true }));
    const ready = list.findIndex(button => button.text === 'Close');
    if (ready >= 0) return { state: list[ready].disabled ? 'disabled' : 'ready', label: 'Close', index: ready };
    const locked = list.findIndex(button => /^Close in \d+s$/.test(button.text));
    if (locked >= 0) return { state: 'locked', label: list[locked].text, index: locked };
    const closing = list.findIndex(button => /^(Closing|Closed · finalizing|Finalizing|Approve)/.test(button.text));
    if (closing >= 0) return { state: 'closing', label: list[closing].text, index: closing };
    return { state: 'none', label: list.map(button => button.text).filter(Boolean).join(' / '), index: -1 };
  }

  /** One table row's visible text -> a position, or the reason it cannot be trusted. */
  function parseRow(cells) {
    const coinMatch = /^([A-Z0-9]{1,12})(?:\s*#\d+)?$/.exec(clean(cells.coinText));
    if (!coinMatch) return { ok: false, reason: 'coin_unreadable' };
    const sideMatch = /^([\d.,\s]+)×\s*(Long|Short)$/.exec(clean(cells.sideText));
    if (!sideMatch) return { ok: false, reason: 'side_unreadable' };
    // "1,000" or "500": a separator is accepted only before a group of three digits, so "1.5" is refused.
    const leverageText = sideMatch[1].replace(/\s/g, '');
    const leverage = /^(?:\d{1,3}(?:[.,]\d{3})+|\d+)$/.test(leverageText) ? Number(leverageText.replace(/[.,]/g, '')) : NaN;
    if (!Number.isInteger(leverage) || leverage < 1 || leverage > 1000) return { ok: false, reason: 'leverage_unreadable' };
    const parts = clean(cells.entryMarkText).split(' / ');
    if (parts.length !== 2) return { ok: false, reason: 'entry_unreadable' };
    const entry = money(parts[0]);
    if (entry === null) return { ok: false, reason: 'entry_unreadable' };
    return { ok: true, row: {
      coin: DISPLAY[coinMatch[1]] ?? coinMatch[1], side: sideMatch[2].toLowerCase(), leverage,
      entry, entryText: clean(parts[0]), mark: money(parts[1]), bust: money(cells.bustText),
      size: clean(cells.sizeText), collateral: clean(cells.collateralText), value: clean(cells.valueText),
      mode: clean(cells.modeText), close: closeState(cells.buttons),
    } };
  }

  const sameRow = (row, expect) => row.coin === expect.coin && row.side === expect.side
    && row.leverage === expect.leverage && row.entryText === expect.entryText;

  function findTable(doc) {
    for (const table of doc.querySelectorAll('table')) {
      const heads = [...table.querySelectorAll('thead th')].map(th => clean(th.textContent));
      const index = Object.fromEntries(Object.entries(HEADERS).map(([key, label]) => [key, heads.indexOf(label)]));
      if (['position', 'entryMark', 'bust', 'status'].every(key => index[key] >= 0)) return { table, index };
    }
    return null;
  }

  /** Rows with their DOM buttons. Callers outside this file only ever see `rows[i].row`. */
  function scan(doc) {
    const found = findTable(doc);
    if (!found) return { recognized: false, reason: 'positions_table_not_found', entries: [] };
    const entries = [];
    const problems = [];
    let pending = 0;
    for (const tr of found.table.querySelectorAll('tbody tr')) {
      if (tr.getAttribute('aria-busy') === 'true') { pending++; continue; }
      const cells = [...tr.children];
      const at = key => found.index[key] >= 0 ? cells[found.index[key]] : null;
      const position = at('position');
      const side = position && [...position.querySelectorAll('span')].find(span => /^[\d.,\s]+×\s*(Long|Short)$/.test(clean(span.textContent)));
      const buttons = at('status') ? [...at('status').querySelectorAll('button')] : [];
      // Stacked spans carry no whitespace between them; join their texts for display.
      const spaced = cell => cell && cell.children.length ? [...cell.children].map(child => child.textContent).join(' ') : cell?.textContent;
      const parsed = parseRow({
        coinText: position?.querySelector('strong')?.textContent, sideText: side?.textContent,
        modeText: side?.nextElementSibling?.textContent,
        entryMarkText: at('entryMark')?.textContent, bustText: at('bust')?.textContent,
        sizeText: at('size')?.textContent, collateralText: spaced(at('collateral')), valueText: spaced(at('value')),
        buttons: buttons.map(button => ({ text: button.textContent, disabled: button.disabled || button.getAttribute('aria-disabled') === 'true' })),
      });
      if (parsed.ok) entries.push({ row: parsed.row, buttons });
      else problems.push(parsed.reason);
    }
    return { recognized: true, entries, pending, problems };
  }

  /** The listed positions as plain data. */
  function readPositions(doc) {
    const result = scan(doc);
    return result.recognized
      ? { recognized: true, positions: result.entries.map(entry => entry.row), pending: result.pending, unreadable: result.problems.length, problems: result.problems }
      : { recognized: false, reason: result.reason, positions: [] };
  }

  /**
   * Press Close for exactly the expected position. Never "Close all", never a
   * second click within ten seconds, never a row that is not a unique match.
   */
  function closePosition(doc, expect, nowMs = Date.now()) {
    if (!expect || typeof expect.coin !== 'string' || !['long', 'short'].includes(expect.side)
        || !Number.isInteger(expect.leverage) || typeof expect.entryText !== 'string' || !expect.entryText) {
      return { clicked: false, reason: 'invalid_request' };
    }
    const result = scan(doc);
    if (!result.recognized) {
      // The table only exists on the Positions tab; select it and let the caller ask again.
      const tab = [...doc.querySelectorAll('button')].find(button => /^Positions \(\d+\)$/.test(clean(button.textContent)));
      if (!tab) return { clicked: false, reason: result.reason };
      tab.click();
      return { clicked: false, retry: true, reason: 'opened_positions_tab' };
    }
    const matches = result.entries.filter(entry => sameRow(entry.row, expect));
    if (matches.length === 0) return { clicked: false, reason: 'position_not_listed' };
    if (matches.length > 1) return { clicked: false, reason: 'ambiguous_position' };
    const [{ row, buttons }] = matches;
    const key = [row.coin, row.side, row.leverage, row.entryText].join('|');
    const { state, label, index } = row.close;
    if (state === 'closing') return { clicked: false, already: true, label };
    if (clicks.has(key) && nowMs - clicks.get(key) < RECLICK_MS) return { clicked: false, already: true, reason: 'recently_clicked', label };
    if (state === 'locked') return { clicked: false, retry: true, reason: 'close_locked', label };
    if (state === 'disabled') return { clicked: false, retry: true, reason: 'close_disabled', label };
    if (state !== 'ready') return { clicked: false, reason: 'close_unavailable', label };
    clicks.set(key, nowMs);
    buttons[index].click();
    return { clicked: true, label };
  }

  /* ------------------------------------------------------------ order form -- */

  const FORM_LABEL = 'Degen market order';
  // The page's own quick-size buttons. It has none for three quarters.
  const SIZE_BUTTON = { 0.25: '25%', 0.5: 'Half', 1: 'Max' };
  const REOPEN_MS = 5000;
  let lastOpenMs = -Infinity;

  /** "15.80352" or "1,234.5" -> the plain decimal string, or null. */
  function amount(text) {
    const match = /^((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)$/.exec(clean(text));
    if (!match) return null;
    const plain = match[1].replaceAll(',', '');
    return Number(plain) > 0 ? plain : null;
  }

  /** Three quarters of a decimal string, rounded down at six decimals (or the input's own, if finer). */
  function threeQuarters(plain) {
    const [whole, fraction = ''] = plain.split('.');
    const places = Math.max(fraction.length, 6);
    const digits = (BigInt(whole + fraction.padEnd(places, '0')) * 3n / 4n).toString().padStart(places + 1, '0');
    return `${digits.slice(0, -places)}.${digits.slice(-places)}`.replace(/0+$/, '').replace(/\.$/, '');
  }

  function leverageOf(text) {
    const match = /^([\d.,\s]+)×$/.exec(clean(text));
    if (!match) return null;
    const digits = match[1].replace(/\s/g, '');
    const value = /^(?:\d{1,3}(?:[.,]\d{3})+|\d+)$/.test(digits) ? Number(digits.replace(/[.,]/g, '')) : NaN;
    return Number.isInteger(value) && value >= 1 && value <= 1000 ? value : null;
  }

  function findForm(doc) {
    const forms = [...doc.querySelectorAll('form')].filter(form => form.getAttribute('aria-label') === FORM_LABEL
      && form.querySelector('#degen-amount') && form.getClientRects().length > 0);
    return forms.length === 1 ? forms[0] : null;
  }

  function formParts(doc) {
    const form = findForm(doc);
    if (!form) return null;
    const buttons = [...form.querySelectorAll('button')];
    const side = name => buttons.find(button => button.getAttribute('data-side') === name) ?? null;
    const mode = doc.querySelector('nav[aria-label="Trading mode"] a[aria-current="page"]');
    const balance = buttons.find(button => /^Available balance: /.test(button.getAttribute('aria-label') ?? ''));
    const pressed = buttons.find(button => button.getAttribute('aria-pressed') === 'true' && leverageOf(button.textContent) !== null);
    const balanceText = balance ? clean(balance.getAttribute('aria-label')).replace(/^Available balance: /, '') : null;
    return { form, buttons, input: form.querySelector('#degen-amount'), long: side('long'), short: side('short'),
      // The mode link can carry a badge after its name; the first word is the mode.
      mode: clean(mode?.textContent).split(' ')[0] || null,
      balanceText, balance: balanceText === null ? null : amount(balanceText.split(' ')[0]),
      // The line under the amount is drawn from the page's own state, so it shows what the page accepted.
      hint: clean(form.querySelector('#degen-amount-hint')?.textContent),
      leverage: pressed ? leverageOf(pressed.textContent) : leverageOf(form.querySelector('output')?.textContent),
      error: clean(form.querySelector('#degen-amount-error')?.textContent) };
  }

  /** What the page's order form currently shows. Read only. */
  function readOrderForm(doc) {
    const parts = formParts(doc);
    if (!parts || !parts.input || !parts.long || !parts.short) return { recognized: false, reason: 'order_form_not_found' };
    const disabled = button => button.disabled || button.getAttribute('aria-disabled') === 'true';
    return { recognized: true, mode: parts.mode, amountText: clean(parts.input.value), balanceText: parts.balanceText, leverage: parts.leverage,
      longEnabled: !disabled(parts.long), shortEnabled: !disabled(parts.short),
      busy: [parts.long, parts.short].some(button => button.getAttribute('aria-busy') === 'true'), error: parts.error };
  }

  // The page's Max can sit a little under the balance (fee reserve, size cap). Further off than this is not the size asked for.
  const SIZE_FLOOR = 0.85, SIZE_CEILING = 1.0001, OPEN_DEADLINE_MS = 6000;
  let opening = false;

  /**
   * Set the size with the page's own button, then press its Long or Short
   * button once. The amount the page then shows must match the chosen share of
   * the balance it shows. Three quarters has no page button: the page's Max is
   * read and three quarters of it is typed, and the page's own derived line
   * must change before the press. Anything unexpected stops before the press.
   * One call at a time, never within five seconds of the last, never late.
   */
  async function openPosition(doc, request, { now = Date.now, wait = ms => new Promise(resolve => setTimeout(resolve, ms)), stillValid = () => true } = {}) {
    if (!request || !['long', 'short'].includes(request.side) || ![0.25, 0.5, 0.75, 1].includes(request.fraction)
        || ![undefined, null, 500, 1000].includes(request.leverage)) {
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
      if (!parts || !parts.input || !parts.long || !parts.short) return { clicked: false, reason: 'order_form_not_found' };
      if (parts.mode !== 'Classic') return { clicked: false, reason: 'mode_not_classic' };
      if ([parts.long, parts.short].some(button => button.getAttribute('aria-busy') === 'true')) return { clicked: false, reason: 'page_busy' };
      if (parts.balance === null) return { clicked: false, reason: 'balance_unreadable' };
      const balance = Number(parts.balance);
      const near = (text, share) => {
        const value = amount(text);
        return value !== null && Number(value) >= share * balance * SIZE_FLOOR && Number(value) <= share * balance * SIZE_CEILING;
      };
      /** Poll the form until `ready` holds, for at most a second and a half. */
      const settle = async ready => {
        for (let i = 0; i < 30; i++) {
          await wait(50);
          parts = formParts(doc);
          if (!parts || !parts.input) return false;
          if (ready()) return true;
        }
        return false;
      };
      if (request.leverage && parts.leverage !== request.leverage) {
        // The page's own leverage preset, pressed before the size: the page caps the amount by leverage.
        const preset = parts.buttons.find(candidate => candidate.getAttribute('aria-pressed') !== null && leverageOf(candidate.textContent) === request.leverage);
        if (!preset || preset.disabled) return { clicked: false, reason: 'leverage_button_unavailable' };
        preset.click();
        if (!await settle(() => parts.leverage === request.leverage)) return { clicked: false, reason: parts ? 'leverage_not_set' : 'order_form_not_found' };
      }
      const typed = request.fraction === 0.75;
      const label = typed ? 'Max' : SIZE_BUTTON[request.fraction];
      const quick = parts.buttons.find(candidate => clean(candidate.textContent) === label);
      if (!quick || quick.disabled) return { clicked: false, reason: 'size_button_unavailable' };
      quick.click();
      // A value left in the field from before only passes if it is the size this button gives.
      if (!await settle(() => near(parts.input.value, typed ? 1 : request.fraction))) return { clicked: false, reason: parts ? 'amount_unexpected' : 'order_form_not_found' };
      if (typed) {
        const target = threeQuarters(amount(parts.input.value)), before = parts.hint;
        if (!near(target, 0.75)) return { clicked: false, reason: 'amount_unexpected' };
        // The value setter on the prototype reaches the element without the page framework's own wrapper,
        // so the following input event is seen as a real change.
        Object.getOwnPropertyDescriptor(Object.getPrototypeOf(parts.input), 'value').set.call(parts.input, target);
        parts.input.dispatchEvent(new Event('input', { bubbles: true }));
        // The field alone only shows what was typed. The page's derived line changing shows it took the amount.
        if (!await settle(() => amount(parts.input.value) === target && parts.hint !== '' && parts.hint !== before)) {
          return { clicked: false, reason: parts ? 'amount_not_accepted' : 'order_form_not_found' };
        }
      }
      await settle(() => parts.error !== '' || !parts[request.side].disabled);
      if (!parts || !parts.input) return { clicked: false, reason: 'order_form_not_found' };
      if (parts.error) return { clicked: false, reason: 'amount_rejected', detail: parts.error.slice(0, 120) };
      const button = parts[request.side];
      if (!button || button.disabled) return { clicked: false, reason: 'side_disabled' };
      if (!near(parts.input.value, request.fraction)) return { clicked: false, reason: 'amount_unexpected' };
      // Timers crawl in a hidden tab. A press that comes late is one the owner has stopped expecting.
      if (now() - started > OPEN_DEADLINE_MS) return { clicked: false, reason: 'too_slow' };
      if (parts.mode !== 'Classic' || !stillValid() || (request.leverage && parts.leverage !== request.leverage)) return { clicked: false, reason: 'page_changed' };
      button.click();
      return { clicked: true, amountText: amount(parts.input.value), leverage: parts.leverage };
    } finally {
      opening = false;
    }
  }

  globalThis.__smt1000xBridge = Object.freeze({ money, closeState, parseRow, readPositions, closePosition,
    amount, threeQuarters, readOrderForm, openPosition });
})();
