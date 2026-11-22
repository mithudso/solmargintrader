import test from 'node:test';
import assert from 'node:assert/strict';
import { createJupiterIndicatorWindows } from '../src/bg/jupiter-indicator-window.js';

test('detached window ownership survives reconstruction of the background worker', async () => {
  const events = () => ({ addListener() {} });
  const notifications = [];
  const opened = new Map();
  let persisted = {};
  const options = {
    runtime: { getURL: path => `chrome-extension://fixture/${path}` },
    storage: {
      async get(key) { return { [key]: structuredClone(persisted[key]) }; },
      async set(values) { persisted = structuredClone(values); },
    },
    tabs: {
      onUpdated: events(), onRemoved: events(),
      async update(id, { url }) { opened.get(4).tabs[0] = { id, url }; },
      async sendMessage(...args) { notifications.push(args); },
    },
    windows: {
      onRemoved: events(),
      async create() {
        assert.equal(opened.size, 0);
        const popup = { id: 4, tabs: [{ id: 9 }] };
        opened.set(4, popup);
        return popup;
      },
      async get(id) { return opened.get(id); },
      async remove(id) { assert.ok(opened.delete(id)); },
    },
  };
  const source = { frameId: 0, documentId: 'source-document', tab: { id: 2 }, url: 'https://jup.ag/1000x?market=SOL' };
  assert.deepEqual(await createJupiterIndicatorWindows(options).control('open', source), { detached: true });
  const recoveredWorker = createJupiterIndicatorWindows(options);
  const popup = { frameId: 0, documentId: 'popup-document', tab: { id: 9, windowId: 4 }, url: opened.get(4).tabs[0].url };
  assert.deepEqual(await recoveredWorker.control('status', source), { detached: true });
  assert.deepEqual(await recoveredWorker.control('status', popup), { detached: true });
  await assert.rejects(recoveredWorker.control('dock', { ...popup, tab: { id: 10, windowId: 4 } }), /no longer attached/);
  assert.deepEqual(await recoveredWorker.control('dock', popup), { detached: false });
  assert.deepEqual(await recoveredWorker.control('status', source), { detached: false });
  assert.equal(opened.size, 0);
  assert.deepEqual(notifications, [[2, { type: 'jupiter1000xWindowClosed' }, { documentId: 'source-document' }]]);
});
