#!/usr/bin/env node
// Speaks Chrome's native messaging framing on stdio, over the fake registry.
// SOLTUI_FAKE_MODE: hang (never answers) | crash (exits at once) | garbage (bad frame).
import { fakeHandle } from './fake-soltui-registry.js';

const mode = process.env.SOLTUI_FAKE_MODE;
if (mode === 'crash') process.exit(3);

const frame = (message) => {
  const body = Buffer.from(JSON.stringify(message));
  const head = Buffer.alloc(4);
  head.writeUInt32LE(body.length);
  return Buffer.concat([head, body]);
};

let buffer = Buffer.alloc(0);
process.stdin.on('data', (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  while (buffer.length >= 4 && buffer.length >= 4 + buffer.readUInt32LE(0)) {
    const length = buffer.readUInt32LE(0);
    const request = JSON.parse(buffer.subarray(4, 4 + length).toString());
    buffer = buffer.subarray(4 + length);
    if (mode === 'hang') continue;
    if (mode === 'garbage') { process.stdout.write(Buffer.from([3, 0, 0, 0, 0x78, 0x79, 0x7a])); continue; }
    process.stdout.write(frame({ id: request.id, response: fakeHandle(request, { hash: process.env.SOLTUI_FAKE_HASH }) }));
  }
});
process.stdin.on('end', () => process.exit(0));
