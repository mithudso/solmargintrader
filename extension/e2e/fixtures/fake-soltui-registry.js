// A stand-in for soltui's registry with the same envelope shapes as the
// contract. It exists so the extension's side of the bridge is tested without
// Python; the real host is exercised in tools/e2e.mjs.

export const FAKE_COMMANDS = [
  { name: 'demo.echo', describe: 'Echo the text back.', params: [{ name: 'text', type: 'string', required: false, describe: 'Text.' }], read_only: true, long_running: false, requires_confirm: false },
  { name: 'demo.sweep', describe: 'A long read-only run.', params: [{ name: 'n', type: 'number', required: false, describe: 'Count.' }, { name: 'opts', type: 'json', required: false, describe: 'Options.' }, { name: 'dry', type: 'bool', required: false, describe: 'Dry.' }], read_only: true, long_running: true, requires_confirm: false },
  { name: 'demo.resume', describe: 'Removes a safety stop.', params: [], read_only: false, long_running: false, requires_confirm: true },
  { name: 'zec.volty.status', describe: 'Read the ZEC Volty status.', params: [], read_only: true, long_running: false, requires_confirm: false },
];

export function voltyStatusFixture() {
  const at = Math.floor(Date.now() / 1000);
  return {
    schema: 1, mode: 'live', state: 'armed', updated_at: at,
    signal: { event_id: 'e2e-volty-signal', side: 'sell', at, mark: 540, lower: 541, upper: 560 },
    orders: [
      { event_id: 'e2e-volty-signal', client_order_id: '7654321', side: 'sell', leg: 'open', state: 'pending',
        order_id: null, requested_quantity: '0.02', filled_quantity: null, updated_at: at, fills: [] },
      { event_id: 'e2e-volty-signal', client_order_id: '7654320', side: 'sell', leg: 'close', state: 'filled', order_id: '1234567890123456',
        requested_quantity: '0.02', filled_quantity: '0.02', updated_at: at - 1,
        fills: [{ signature: '0:e2e-fixture-transaction', price: '540', size: '0.02', fee: '0.00378', timestamp: at - 1 }] },
    ],
  };
}

const envelope = (command, result) => ({ ok: true, command, result, error: null });
const failure = (command, code, message) => ({ ok: false, command, result: null, error: { code, message } });

export function fakeHandle(request, { hash } = {}) {
  switch (request.op) {
    case 'ping': return envelope('ping', { pong: true });
    case 'list': return envelope('list', FAKE_COMMANDS);
    case 'buildHash': return envelope('buildHash', { hash: hash || 'a'.repeat(64), files: 3, root: '/fake/extension' });
    case 'call': {
      const spec = FAKE_COMMANDS.find((c) => c.name === request.command);
      if (!spec) return failure(request.command, 'unknown_command', `unknown command "${request.command}"`);
      const params = request.params ?? {};
      if (spec.requires_confirm && params.confirm !== true) return failure(spec.name, 'forbidden', `${spec.name} requires confirm`);
      if (spec.name === 'demo.echo') {
        if (params.text !== undefined && typeof params.text !== 'string') return failure(spec.name, 'bad_params', 'text must be a string');
        return envelope(spec.name, { echo: params.text ?? null });
      }
      if (spec.name === 'zec.volty.status') return envelope(spec.name, voltyStatusFixture());
      return envelope(spec.name, { ran: spec.name, params });
    }
    default: return failure(String(request.op), 'unknown_command', 'unknown op');
  }
}
