/**
 * Reads the Jupiter 1000x positions table and presses its Close button.
 *
 * A classic content script: it defines one object in the isolated world and
 * does nothing until content.js relays a request from this extension's own
 * background worker. It reads text the page already shows and clicks a button
 * the owner could click; it never opens a position, never touches the wallet
 * and never reads page storage. Anything it cannot read exactly is refused.
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
    const leverage = Number(sideMatch[1].replace(/\D/g, ''));
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

  globalThis.__smt1000xBridge = Object.freeze({ money, closeState, parseRow, readPositions, closePosition });
})();
