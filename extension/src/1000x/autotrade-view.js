import { soltui } from '../ui/ui-kit.js';

const val = value => value == null ? 'unknown' : String(value);
const numeric = value => typeof value === 'number' && Number.isFinite(value);

// Only the actual stored forecast and its source identity may cross the bridge.
export async function forecastPayload(view, identity, now = Date.now(), digest = crypto.subtle) {
  if (!view?.inputReady || view.mode !== 'active' || !identity || identity.kind !== 'oracle-ohlc' || identity.stream !== 'fixed_rate@200ms') return null;
  const asset = identity.symbol, feed = { BTC: 1, ZEC: 66 }[asset];
  if (!feed || identity.feedId !== feed || typeof identity.marketAddress !== 'string') return null;
  const f = view.state?.pending?.at(-1);
  if (!f || f.mode !== 'active' || f.modelSamples < 20 || !numeric(f.issuedAtMs)
      || now - f.issuedAtMs < 0 || now - f.issuedAtMs > 30000 || f.target * 1000 <= now) return null;
  const hash = await digest.digest('SHA-256', new TextEncoder().encode(f.id));
  const forecast_id = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
  return { forecast_id, asset, horizon_seconds: view.horizon, source_basis: `jupiter-pyth:${feed}`,
    stream: identity.stream, market_address: identity.marketAddress, kind: identity.kind,
    model_version: 'projected-logit-l2-v1', target_type: 'closed-price-up-vs-nonup-v1',
    cutoff_at: f.cutoff, target_at: f.target, issued_at: f.issuedAtMs / 1000,
    reference_price: f.reference, p_up: f.servedP, sample_count: f.modelSamples, mode: f.mode };
}

export function autotradeView(container, { call = soltui, clock = Date.now, id = () => crypto.randomUUID() } = {}) {
  const section = document.createElement('section'); section.className = 'autotrade';
  const title = document.createElement('h2'); title.textContent = 'Auto Long / Short';
  const status = document.createElement('p'); status.setAttribute('role', 'status'); status.textContent = 'Auto-trade owner unavailable';
  const detail = document.createElement('pre'); detail.className = 'autotrade-detail';
  const fields = document.createElement('div'); fields.className = 'autotrade-fields';
  const inputs = {};
  for (const [key, label] of [['asset', 'Asset BTC/ZEC'], ['venue', 'Venue'], ['base_collateral_usd', 'Base collateral $'], ['max_collateral_usd', 'Maximum collateral $'], ['max_session_loss_usd', 'Session loss cap $']]) {
    const wrap = document.createElement('label'); wrap.textContent = label;
    const input = document.createElement(key === 'venue' || key === 'asset' ? 'select' : 'input');
    if (key === 'asset' || key === 'venue') {
      const options = key === 'asset' ? [['BTC', 'BTC'], ['ZEC', 'ZEC']] : [['jupiter-cli-10x', '10× paper proxy'], ['jupiter-sdk-1000x', '1000× paper proxy']];
      for (const [value, text] of options) { const option = document.createElement('option'); option.value = value; option.textContent = text; input.append(option); }
    }
    input.required = true; input.name = key; wrap.append(input); fields.append(wrap); inputs[key] = input;
  }
  const adviceLabel = document.createElement('label'); adviceLabel.textContent = 'Optional private advice';
  const advice = document.createElement('input'); advice.type = 'checkbox'; advice.checked = false; adviceLabel.append(advice); fields.append(adviceLabel);
  const liveEdited = new Set();
  for (const key of ['base_collateral_usd', 'max_collateral_usd', 'max_session_loss_usd']) inputs[key].addEventListener('input', () => liveEdited.add(key));
  const buttons = document.createElement('div'); buttons.className = 'autotrade-buttons';
  const paper = document.createElement('button'); paper.textContent = 'Start Paper';
  const live = document.createElement('button'); live.textContent = 'Start Live';
  const stop = document.createElement('button'); stop.textContent = 'Stop entries / manage position';
  buttons.append(paper, live, stop); section.append(title, status, fields, buttons, detail); container.before(section);
  let disposed = false, initialized = false, busy = false, retry = null, current = null, sent = new Set(), pending = new Set();
  const render = s => {
    if (disposed) return;
    current = s;
    status.textContent = `${val(s.state).toUpperCase()} · ${val(s.mode)} · ${val(s.reason)}`;
    status.dataset.state = s.state || 'unknown';
    if (!initialized && (s.configuration || s.defaults)) { const saved = s.configuration || s.defaults; for (const key of Object.keys(inputs)) inputs[key].value = saved[key] ?? ''; advice.checked = saved.advice_enabled === true; initialized = true; }
    const p = s.position || {}, plan = p.plan || {}, f = s.forecast || {}, l = s.learner || {}, policy = s.policy || {};
    const remaining = numeric(s.first_entry_deadline) ? Math.max(0, Math.ceil(s.first_entry_deadline - clock() / 1000)) + 's' : 'unknown';
    detail.textContent = `Live readiness: ${val(s.readiness?.live)}\n1000× readiness: ${val(s.readiness?.['1000x'])} · advice ${val(s.readiness?.advice)}\nFirst entry deadline: ${remaining} · session ${val(s.session_id)}\nPosition: ${val(p.state)} ${val(plan.direction)} · entry ${val(plan.target_entry)} · target ${val(plan.target_price)} · stop ${val(plan.stop_price)} · liquidation ${val(plan.liquidation_price)}\nModeled fills: entry ${val(plan.entry_fill)} · exit ${val(p.exit_price)} · modeled net PnL ${val(s.net_pnl_usd)}\nModel ${val(plan.model_version)} · ${val(plan.assumptions)} · ${val(plan.cost_scope)}\nOutcomes: wins ${val(l.wins)} · losses ${val(l.losses)} · liquidations ${val(l.liquidations)} · data/continuity failures ${val(l.availability_failures)}\nAll-cohort modeled results: ${val(s.history?.samples)} samples · net ${val(s.history?.net_pnl_usd)} · ${val(s.history?.scope)}\nTraining ${val(s.training)} · samples ${val(l.samples)} · confidence ${val(f.score)} (uncalibrated) · boost ${val(f.boost_eligible)} ${val(f.boost_reason)}\nCaps: base ${val(policy.base_collateral_usd)} · max ${val(policy.max_collateral_usd)} · loss ${val(policy.max_session_loss_usd)}\nForecast provenance: ${val(f.source || f.advisory_forecast_id)}\nStop prevents new entries and manages open positions; ending an unknown paper outcome requires acknowledgement. Session continues when this panel closes.`;
  };
  const refresh = async () => { try { render(await call('autotrade.status')); } catch { if (!disposed) status.textContent = 'Auto-trade owner unavailable'; } };
  async function act(command, params) {
    if (busy) return; busy = true; for (const b of [paper, live, stop]) b.disabled = true;
    const signature = JSON.stringify([command, params]);
    const request_id = retry?.signature === signature ? retry.request_id : id(); retry = { signature, request_id };
    try { const result = await call(command, { request_id, ...params }); retry = null; render(result); }
    catch (e) { status.textContent = `Request failed: ${e.message}. Retry uses the same request ID.`; }
    finally { busy = false; if (!disposed) for (const b of [paper, live, stop]) b.disabled = false; }
  }
  const config = mode => Object.fromEntries(Object.entries(inputs).map(([k, input]) => [k, k.endsWith('_usd') ? (input.value.trim() ? Number(input.value) : null) : input.value.trim()]).concat([['mode', mode], ['advice_enabled', advice.checked]]));
  paper.onclick = () => void act('autotrade.start_paper', { config: config('paper') });
  live.onclick = () => { if (liveEdited.size !== 3) { status.textContent = 'Enter each live collateral and loss cap explicitly before requesting live start.'; return; } if (window.confirm('Request live start with these explicit limits?')) void act('autotrade.start_live', { config: config('live'), confirm: true }); };
  stop.onclick = () => { if (current?.position?.state === 'unknown') { if (!window.confirm('Acknowledge the unknown paper outcome and stop this session?')) return; void act('autotrade.stop', { acknowledge_unknown: true }); } else void act('autotrade.stop', {}); };
  const timer = setInterval(refresh, 5000); void refresh();
  return {
    async observe(view, identity) {
      const forecast = await forecastPayload(view, identity); if (!forecast || disposed || sent.has(forecast.forecast_id) || pending.has(forecast.forecast_id)) return;
      pending.add(forecast.forecast_id);
      try { await call('autotrade.ingest_forecast', { request_id: `forecast-${forecast.forecast_id}`, forecast }); sent.add(forecast.forecast_id); }
      catch { /* The owner can be absent; retry the same immutable request without affecting analytics. */ }
      finally { pending.delete(forecast.forecast_id); }
    },
    close() { disposed = true; clearInterval(timer); },
  };
}
