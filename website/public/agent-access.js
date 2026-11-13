const REQUEST_ID = /^[A-Za-z0-9_-]{43}$/;
const GRANT_ID = /^[a-f0-9-]{36}$/;
const SCOPE_LABELS = { 'status:read': 'Read your account, configurations and trade status', 'trade:prepare': 'Prepare trades within your limits', 'trade:submit': 'Submit authorized trades within your limits' };
const now = () => Math.floor(Date.now() / 1000);
class ConsentError extends Error {}
const element = (tag, value, className) => {
  const item = document.createElement(tag);
  if (value !== undefined) item.textContent = String(value);
  if (className) item.className = className;
  return item;
};
const date = seconds => new Date(seconds * 1000).toLocaleString();
const money = value => new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(value);
const busy = (form, value) => {
  for (const control of form.querySelectorAll('button,input,select,textarea')) control.disabled = value;
  form.setAttribute('aria-busy', String(value));
};
const localDate = seconds => {
  const instant = new Date(seconds * 1000);
  return new Date(instant.getTime() - instant.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const policyKey = policy => JSON.stringify({ venues: [...policy.venues].sort(), assets: [...policy.assets].sort(), maxTradeUsd: policy.maxTradeUsd, maxTotalUsd: policy.maxTotalUsd, expiresAt: policy.expiresAt });

function labelControl(label, input) {
  const wrapper = element('label', label);
  wrapper.append(input);
  return wrapper;
}
function choices(legend, name, options, selected) {
  const fieldset = element('fieldset'); fieldset.className = 'agent-choices';
  fieldset.append(element('legend', legend));
  for (const [value, label] of options) {
    const input = element('input'); input.type = 'checkbox'; input.name = name; input.value = value; input.checked = value === selected;
    fieldset.append(labelControl(label, input));
  }
  return fieldset;
}
function readPolicy(form) {
  const selected = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);
  const policy = { venues: selected('venues'), assets: selected('assets'), maxTradeUsd: Number(form.elements.namedItem('maxTradeUsd').value), maxTotalUsd: Number(form.elements.namedItem('maxTotalUsd').value), expiresAt: Math.floor(new Date(form.elements.namedItem('expiresAt').value).getTime() / 1000) };
  if (!policy.venues.length || !policy.assets.length) throw new ConsentError('Choose at least one venue and one asset.');
  if (![policy.maxTradeUsd, policy.maxTotalUsd].every(value => Number.isFinite(value) && value > 0 && value <= 1000000 && /^(\d+)(?:\.(\d{1,2}))?$/.test(String(value))) || policy.maxTotalUsd < policy.maxTradeUsd) throw new ConsentError('Enter positive USD limits with up to two decimal places. The total must cover at least one trade.');
  if (!Number.isSafeInteger(policy.expiresAt) || policy.expiresAt <= now() + 60 || policy.expiresAt > now() + 30 * 86400) throw new ConsentError('Choose an expiry between one minute and thirty days from now.');
  return policy;
}

// The browser only follows the server's response to the registered URI it
// displayed. Authorization codes stay in this function and never enter the DOM.
function approvedRedirect(result, details) {
  const destination = new URL(result.redirectTo);
  const registered = new URL(details.client.redirectUri);
  const loopback = destination.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(destination.hostname);
  if (!(destination.protocol === 'https:' || loopback) || destination.username || destination.password || destination.hash || destination.origin !== registered.origin || destination.pathname !== registered.pathname) throw new Error('The authorization service returned an unexpected redirect.');
  const code = destination.searchParams.getAll('code'); const error = destination.searchParams.getAll('error');
  if (!((code.length === 1 && !error.length) || (error.length === 1 && !code.length)) || destination.searchParams.getAll('state').length > 1) throw new Error('The authorization service returned an unexpected redirect.');
  for (const key of ['code', 'error', 'state']) { destination.searchParams.delete(key); registered.searchParams.delete(key); }
  destination.searchParams.sort(); registered.searchParams.sort();
  if (destination.href !== registered.href) throw new Error('The authorization service returned an unexpected redirect.');
  return result.redirectTo;
}

export function createAgentAccess({ api, getUser, isSettings, openWallet, toast }) {
  let revision = 0;
  const invalidate = () => { revision++; };

  function mount(container) {
    const token = ++revision; const user = getUser();
    const current = () => revision === token && isSettings() && container.isConnected && getUser()?.id === user?.id && getUser()?.wallet === user?.wallet;
    const intro = element('section', undefined, 'panel agent-access'); intro.dataset.agentAccess = '';
    intro.append(element('p', 'YOUR AGENT, YOUR LIMITS', 'eyebrow'), element('h3', 'Connect your agent'), element('p', 'Add this MCP address to a compatible agent, then approve its access here. Every request uses your signed-in wallet.'));
    intro.append(element('code', `${location.origin}/mcp`, 'agent-endpoint'));
    intro.append(element('p', 'Choose status access or a trading preauthorization with a per-trade limit, total limit and expiry. Approve that authorization once; trades within it do not require repeated wallet approval. Revoke access here at any time.'));
    intro.append(element('p', 'Trading also needs a supported, verified venue connection and delegated signing authority for this wallet. Agent access alone does not enable execution. Already submitted orders are not canceled by revoking access.', 'fine-print'));
    container.append(intro);
    const requestId = new URL(location.href).searchParams.get('agent_request');
    const consent = requestId ? element('section', undefined, 'panel agent-consent') : null;
    if (consent) { consent.dataset.agentConsent = ''; container.prepend(consent); }
    const grants = element('section', undefined, 'panel agent-access'); grants.dataset.agentGrants = ''; grants.append(element('h3', 'Authorized agents')); container.append(grants);
    if (!user) {
      if (consent) { consent.append(element('h3', 'Sign in to review agent access'), element('p', 'Connect the wallet you want this agent to use. You will review its requested permissions before granting access.')); }
      grants.append(element('p', 'Sign in with your wallet to view or revoke its authorizations.'));
      const connect = element('button', 'Connect wallet', 'button button-outline'); connect.type = 'button'; connect.addEventListener('click', openWallet); (consent || intro).append(connect);
      return;
    }
    if (consent) {
      consent.append(element('h3', 'Review agent access'), element('p', 'Loading the exact request for your wallet…', 'agent-message'));
      if (!REQUEST_ID.test(requestId)) consent.replaceChildren(element('h3', 'Invalid authorization request'), element('p', 'Start the connection again from your agent.'));
      else loadConsent(consent, requestId, user, current);
    }
    loadGrants(grants, current);
  }

  async function loadConsent(section, requestId, user, current) {
    try {
      const details = await api(`/api/agent/authorization?request_id=${encodeURIComponent(requestId)}`);
      if (!current()) return;
      if (details.requestId !== requestId || details.wallet !== user.wallet || !Array.isArray(details.scopes) || !details.scopes.length || details.scopes.some(scope => !Object.hasOwn(SCOPE_LABELS, scope)) || details.resource !== `${location.origin}/mcp` || !details.client?.redirectUri || new URL(details.client.redirectUri).origin !== details.client.redirectOrigin) throw new Error();
      const trading = details.scopes.some(scope => scope.startsWith('trade:'));
      if (details.requiresPolicyProof !== trading || details.expiresAt <= now()) throw new Error();
      section.replaceChildren(element('p', trading ? 'TRADING PREAUTHORIZATION' : 'STATUS ACCESS', 'eyebrow'), element('h3', `${details.client.name} requests access`));
      section.append(element('p', 'Agent names are supplied by the connecting application. Check the return address and permissions before continuing.', 'fine-print'));
      section.append(element('p', 'Wallet'), element('code', user.wallet, 'agent-endpoint'), element('p', 'Return address'), element('code', details.client.redirectUri, 'agent-endpoint'));
      const scopes = element('ul', undefined, 'agent-scopes');
      for (const scope of details.scopes) scopes.append(element('li', SCOPE_LABELS[scope]));
      section.append(scopes);
      const form = element('form'); form.id = 'agent-consent-form';
      if (trading) {
        form.append(element('p', 'Set the limits this agent may use. Your wallet will sign this policy once, separately from your sign-in.'));
        form.append(choices('Allowed venues', 'venues', [['coinbase', 'Coinbase spot'], ['jupiter', 'Jupiter leveraged positions']], 'coinbase'));
        form.append(choices('Allowed assets', 'assets', [['SOL', 'SOL'], ['BTC', 'BTC'], ['ETH', 'ETH'], ['ZEC', 'ZEC']], 'SOL'));
        const grid = element('div', undefined, 'form-grid');
        for (const [name, text, value] of [['maxTradeUsd', 'Maximum per trade (USD)', '100'], ['maxTotalUsd', 'Maximum total (USD)', '1000']]) {
          const input = element('input'); Object.assign(input, { type: 'number', name, min: '0.01', max: '1000000', step: '0.01', value, required: true }); grid.append(labelControl(text, input));
        }
        form.append(grid);
        const expires = element('input'); Object.assign(expires, { type: 'datetime-local', name: 'expiresAt', min: localDate(now() + 120), max: localDate(now() + 30 * 86400), value: localDate(now() + 86400), required: true }); form.append(labelControl('Expires (your local time)', expires));
        const wallet = element('select'); wallet.name = 'walletProvider';
        for (const [value, text] of [['phantom', 'Phantom'], ['solflare', 'Solflare']]) { const option = element('option', text); option.value = value; wallet.append(option); }
        form.append(labelControl('Wallet to sign this authorization', wallet));
        form.append(element('p', 'These limits reserve the maximum spend, including quoted fees. Unknown submissions continue to use the total until resolved. This policy cannot grant authority over another wallet.', 'fine-print'));
      } else form.append(element('p', 'This request can read status only. It cannot prepare or submit trades. Access expires in seven days unless you revoke it sooner.'));
      const message = element('p', '', 'form-message'); message.setAttribute('role', 'status'); form.append(message);
      const actions = element('div', undefined, 'agent-actions');
      const approve = element('button', trading ? 'Sign preauthorization' : 'Allow status access', 'button button-dark'); approve.type = 'submit';
      const deny = element('button', 'Deny access', 'button button-outline'); deny.type = 'button'; actions.append(approve, deny); form.append(actions); section.append(form);
      let inFlight = false;
      deny.addEventListener('click', () => authorize(false));
      form.addEventListener('submit', event => { event.preventDefault(); authorize(true); });
      async function authorize(allow) {
        if (!current() || inFlight) return;
        inFlight = true;
        busy(form, true); message.textContent = '';
        try {
          const body = { requestId, approve: allow };
          if (allow && trading) {
            const policy = readPolicy(form);
            const providerName = form.elements.namedItem('walletProvider').value;
            const provider = providerName === 'phantom' ? window.phantom?.solana || (window.solana?.isPhantom ? window.solana : null) : window.solflare;
            if (!provider?.connect || !provider?.signMessage) throw new ConsentError('Open the selected wallet’s browser or install its extension, then try again.');
            message.textContent = 'Connect the wallet shown above, then sign the limits in its authorization message.';
            const connection = await provider.connect();
            if (!current()) return;
            const address = (connection?.publicKey || provider.publicKey)?.toString();
            if (address !== user.wallet || provider.publicKey?.toString() !== user.wallet) throw new ConsentError('The selected wallet does not match your signed-in account. Switch to the wallet shown above.');
            const challenge = await api('/api/agent/authorization/challenge', { method: 'POST', body: JSON.stringify({ requestId, policy }) });
            if (!current()) return;
            if (!challenge.policy || policyKey(challenge.policy) !== policyKey(policy) || typeof challenge.message !== 'string' || challenge.message.length > 8192 || challenge.expiresAt <= now()) throw new ConsentError('The authorization limits changed. Review this request again.');
            if (provider.publicKey?.toString() !== user.wallet) throw new ConsentError('Your connected wallet changed. Review this request again.');
            const signed = await provider.signMessage(new TextEncoder().encode(challenge.message), 'utf8');
            if (!current()) return;
            if (provider.publicKey?.toString() !== user.wallet) throw new ConsentError('Your connected wallet changed. Review this request again.');
            const bytes = new Uint8Array(signed.signature || signed);
            if (bytes.length !== 64) throw new ConsentError('The wallet did not return a valid authorization signature.');
            body.challengeId = challenge.challengeId; body.signature = btoa(String.fromCharCode(...bytes));
          }
          if (!current()) return;
          const result = await api('/api/agent/authorization', { method: 'POST', body: JSON.stringify(body) });
          if (!current()) return;
          location.assign(approvedRedirect(result, details));
        } catch (error) {
          if (current()) message.textContent = error?.code === 4001 ? 'Authorization canceled. No access was granted.' : error instanceof ConsentError ? error.message : 'Authorization could not be completed. Reload this request or reconnect from your agent.';
        } finally { inFlight = false; if (current()) busy(form, false); }
      }
    } catch {
      if (current()) section.replaceChildren(element('h3', 'This request is unavailable'), element('p', 'It may have expired, been used or belong to another wallet. Start the connection again from your agent.'));
    }
  }

  async function loadGrants(section, current) {
    const status = element('p', 'Loading authorizations…'); status.setAttribute('role', 'status'); section.append(status);
    try {
      const result = await api('/api/agent/grants');
      if (!current()) return;
      if (!Array.isArray(result.grants)) throw new Error();
      status.remove();
      if (!result.grants.length) { section.append(element('p', 'No agent authorizations have been recorded for this wallet.')); return; }
      for (const grant of result.grants) {
        if (!GRANT_ID.test(grant.id)) continue;
        const active = !grant.revokedAt && grant.expiresAt > now();
        const card = element('article', undefined, 'agent-grant'); card.dataset.grantId = grant.id;
        card.append(element('h4', grant.clientName), element('p', grant.revokedAt ? `Revoked ${date(grant.revokedAt)}` : `${active ? 'Authorized until' : 'Expired'} ${date(grant.expiresAt)}`, 'agent-grant-status'));
        const scopes = element('ul', undefined, 'agent-scopes'); for (const scope of grant.scopes || []) scopes.append(element('li', SCOPE_LABELS[scope] || 'Unrecognized permission')); card.append(scopes);
        if (grant.policy) card.append(element('p', `${grant.policy.venues.join(', ')} · ${grant.policy.assets.join(', ')} · ${money(grant.policy.maxTradeUsd)} per trade · ${money(grant.policy.maxTotalUsd)} total`, 'agent-policy-summary'));
        if (active) {
          const revoke = element('button', 'Revoke access', 'button button-outline'); revoke.type = 'button'; card.append(revoke);
          revoke.addEventListener('click', async () => {
            if (!current()) return;
            revoke.disabled = true;
            try {
              await api(`/api/agent/grants/${encodeURIComponent(grant.id)}/revoke`, { method: 'POST', body: '{}' });
              if (!current()) return;
              card.querySelector('.agent-grant-status').textContent = 'Access revoked. Already submitted orders are not canceled.'; revoke.remove(); toast('Agent access revoked.');
            } catch { if (current()) { revoke.disabled = false; toast('Access could not be revoked. Please try again.'); } }
          });
        }
        section.append(card);
      }
    } catch { if (current()) status.textContent = 'Authorizations could not be loaded. Reload Settings to try again.'; }
  }
  return { mount, invalidate };
}
