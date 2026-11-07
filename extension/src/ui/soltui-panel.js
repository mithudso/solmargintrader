/**
 * Dashboard panel for the soltui command bridge.
 *
 * The command list comes from the registry (`soltuiCommands`), the form is
 * built from each command's declared params by type, and a Run sends only
 * `soltuiCall` with a command name taken from that list. Nothing here knows a
 * soltui command by name, so a new soltui command shows up with no change.
 *
 * Results and errors are written with textContent only (KNOW-407): soltui
 * output is data, and it is never parsed as markup.
 */

const send = (msg) => chrome.runtime.sendMessage(msg);

/**
 * Turn the raw text of one form field into the value the registry expects.
 * Returns { skip: true } for an empty optional field so it is left out of the
 * call, or { error } with a sentence for the person at the form.
 * Pure, so the coercion is unit-tested without a DOM.
 */
export function coerceField(param, raw) {
  if (param.type === 'bool') return raw === true ? { value: true } : { skip: true };
  const text = typeof raw === 'string' ? raw.trim() : '';
  if (text === '') return param.required ? { error: `${param.name} is required` } : { skip: true };
  if (param.type === 'number') {
    const n = Number(text);
    return Number.isFinite(n) ? { value: n } : { error: `${param.name} must be a number` };
  }
  if (param.type === 'json') {
    try {
      return { value: JSON.parse(text) };
    } catch {
      return { error: `${param.name} must be valid JSON` };
    }
  }
  return { value: text };
}

/**
 * Build the params object for a command from the raw field values.
 * The confirm flag is an ordinary entry in params: soltui, not this page,
 * decides whether a command needs it.
 */
export function buildParams(command, values, { confirmed = false } = {}) {
  const params = {};
  const errors = [];
  for (const param of command.params ?? []) {
    if (param.name === 'confirm') continue;
    const out = coerceField(param, values[param.name]);
    if (out.error) errors.push(out.error);
    else if (!out.skip) params[param.name] = out.value;
  }
  if (confirmed === true) params.confirm = true;
  return { params, errors };
}

/** The command names the page may send: exactly those the registry listed. */
export const commandNames = (commands) => new Set((commands ?? []).map((c) => c.name));

/* ------------------------------------------------------------------ rendering -- */

// Element kinds are set by assignment (input.type = ...), never as `type: '...'`:
// test/surfaces.test.js scans the UI scripts for that literal to find the
// messages they send, and an input kind is not a message.
const el = (tag, props = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) node[key] = value;
  for (const child of children) node.append(child);
  return node;
};

function fieldFor(param) {
  const label = el('label');
  label.append(`${param.name}${param.required ? ' *' : ''}${param.describe ? ` — ${param.describe}` : ''}`);
  let input;
  if (param.type === 'bool') {
    input = el('input');
    input.type = 'checkbox';
  } else if (param.type === 'json') {
    input = el('textarea', { rows: 3, spellcheck: false });
  } else {
    input = el('input', { spellcheck: false });
    input.type = param.type === 'number' ? 'number' : 'text';
    if (param.type === 'number') input.step = 'any';
  }
  input.name = param.name;
  label.append(input);
  return { label, input };
}

export function mountSoltuiPanel(root = document) {
  const select = root.querySelector('#soltuiCommand');
  const describe = root.querySelector('#soltuiDescribe');
  const form = root.querySelector('#soltuiForm');
  const result = root.querySelector('#soltuiResult');
  const status = root.querySelector('#soltuiStatus');
  let commands = [];
  let inputs = new Map();
  let confirmBox = null;
  let runButton = null;

  const current = () => commands.find((c) => c.name === select.value);

  function renderForm() {
    form.replaceChildren();
    inputs = new Map();
    confirmBox = null;
    const command = current();
    describe.textContent = command
      ? `${command.describe}${command.read_only ? '' : ' — changes state.'}${command.long_running ? ' May take minutes.' : ''}`
      : '';
    if (!command) return;

    for (const param of command.params ?? []) {
      if (param.name === 'confirm') continue;
      const { label, input } = fieldFor(param);
      inputs.set(param.name, input);
      form.append(label);
    }
    if (command.requires_confirm) {
      const label = el('label');
      confirmBox = el('input');
      confirmBox.type = 'checkbox';
      label.append(confirmBox, ' I confirm: this removes a safety stop on a real-money system.');
      form.append(label);
    }
    runButton = el('button', { className: 'primary', textContent: 'Run' });
    runButton.type = 'submit';
    if (confirmBox) {
      runButton.disabled = true;
      confirmBox.addEventListener('change', () => { runButton.disabled = !confirmBox.checked; });
    }
    form.append(runButton);
  }

  async function loadList() {
    status.textContent = 'Loading soltui commands…';
    let res;
    try {
      res = await send({ type: 'soltuiCommands' });
    } catch (err) {
      status.textContent = `Could not reach the extension: ${err.message}`;
      return;
    }
    const envelope = res?.result;
    if (!res?.ok || !envelope?.ok || !Array.isArray(envelope.result)) {
      commands = [];
      select.replaceChildren();
      renderForm();
      status.textContent = envelope?.error?.message ?? res?.error ?? 'soltui is not available.';
      return;
    }
    commands = envelope.result;
    select.replaceChildren(...commands.map((c) => el('option', { value: c.name, textContent: c.name })));
    status.textContent = `${commands.length} commands`;
    renderForm();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const command = current();
    // Only a name soltui itself listed is ever sent.
    if (!command || !commandNames(commands).has(command.name)) return;

    const values = {};
    for (const [name, input] of inputs) values[name] = input.type === 'checkbox' ? input.checked : input.value;
    const { params, errors } = buildParams(command, values, { confirmed: confirmBox?.checked === true });
    if (errors.length) {
      result.textContent = errors.join('\n');
      return;
    }
    runButton.disabled = true;
    result.textContent = 'Running…';
    try {
      const res = await send({ type: 'soltuiCall', command: command.name, params });
      result.textContent = res?.ok
        ? JSON.stringify(res.result, null, 2)
        : `Refused: ${res?.error ?? 'unknown error'}`;
    } catch (err) {
      result.textContent = `Failed: ${err.message}`;
    } finally {
      runButton.disabled = confirmBox ? !confirmBox.checked : false;
    }
  });

  select.addEventListener('change', renderForm);
  root.querySelector('#soltuiReload').addEventListener('click', loadList);
  return loadList();
}
