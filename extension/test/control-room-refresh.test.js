import test from 'node:test';
import assert from 'node:assert/strict';
import { mountControlRoom } from '../src/ui/control-room.js';

class Element {
  constructor() { this.children = []; this.dataset = {}; this.textContent = ''; this.listeners = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

async function fixture(t, answer) {
  const previousDocument = globalThis.document, previousNode = globalThis.Node;
  globalThis.Node = Element; globalThis.document = { createElement: () => new Element() };
  t.after(() => { globalThis.document = previousDocument; globalThis.Node = previousNode; });
  const root = new Element(), pending = new Map(), calls = [];
  let nextId = 0;
  const ui = mountControlRoom(root, {
    send: async message => { calls.push(message.type); return answer(calls.length); },
    schedule: (callback, delay) => { const id = ++nextId; pending.set(id, { callback, delay }); return id; },
    cancel: id => pending.delete(id),
  });
  t.after(() => ui?.close());
  await new Promise(resolve => setImmediate(resolve));
  return { root, pending, calls, ui,
    async next() {
      assert.equal(pending.size, 1, 'exactly one bounded status refresh remains scheduled');
      const [id, value] = pending.entries().next().value;
      pending.delete(id); value.callback();
      await new Promise(resolve => setImmediate(resolve));
    } };
}

const status = state => ({ ok: true, result: { helper: 'available', state, ready: state === 'up', components: [] } });

test('healthy dashboard notices outage and recovery through read-only automatic refresh', async t => {
  const f = await fixture(t, n => status(n === 2 ? 'down' : 'up'));
  assert.equal(f.root.dataset.state, 'up');
  await f.next(); assert.equal(f.root.dataset.state, 'down');
  await f.next(); assert.equal(f.root.dataset.state, 'up');
  assert.deepEqual(f.calls, ['controlRoomStatus', 'controlRoomStatus', 'controlRoomStatus']);
  f.ui.close(); assert.equal(f.pending.size, 0);
});

test('unavailable helper is retried without requesting a server start', async t => {
  const f = await fixture(t, n => { if (n === 1) throw new Error('unavailable'); return status('up'); });
  assert.equal(f.root.dataset.state, 'unknown');
  await f.next(); assert.equal(f.root.dataset.state, 'up');
  assert.ok(f.calls.every(command => command === 'controlRoomStatus'));
});
