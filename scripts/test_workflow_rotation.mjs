import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';
const modulePath = process.env.ROTATION_TEST_SOURCE || path.join(import.meta.dirname, 'rotate-workflow-logs.mjs');
const { rotateLog, splitSections } = await import(pathToFileURL(modulePath));

test('fenced version headings remain inside their original entry', () => {
  const content = '# log\n\n## v1\nSTOP retain\n```md\n## v999 example\n```\n\n## v2\nlatest\n';
  const parts = splitSections(content);
  assert.equal(parts.sections.length, 2);
  assert.ok(parts.sections[0].body.includes('## v999 example'));
});

test('failed publication preserves the active log and retry does not duplicate entries', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'workflow-rotation-'));
  const file = path.join(root, 'memory.md');
  const content = '# log\n\n## v1\nSTOP retain\n\n## v2\nsecond\n\n## v3\nlatest\n';
  fs.writeFileSync(file, content);
  const original = fs.renameSync;
  try {
    fs.renameSync = (source, target) => {
      if (target === file) throw Object.assign(new Error('synthetic ENOSPC'), { code: 'ENOSPC' });
      return original(source, target);
    };
    assert.throws(() => rotateLog('memory.md', { root, maxKb: 0, keep: 1 }), /ENOSPC/);
    assert.equal(fs.readFileSync(file, 'utf8'), content);
    fs.renameSync = original;
    rotateLog('memory.md', { root, maxKb: 0, keep: 1 });
    const archive = fs.readdirSync(path.join(root, 'docs/archive')).filter(x => x.endsWith('.md'));
    assert.equal(archive.length, 1);
    const archived = fs.readFileSync(path.join(root, 'docs/archive', archive[0]), 'utf8');
    assert.equal((archived.match(/^## v1$/gm) || []).length, 1);
    assert.equal((archived.match(/^## v2$/gm) || []).length, 1);
    assert.equal((archived.match(/STOP retain/g) || []).length, 1);
    assert.ok(fs.readFileSync(file, 'utf8').includes('## v3'));
  } finally {
    fs.renameSync = original;
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('failed preparation cannot truncate either existing file', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'workflow-rotation-'));
  const file = path.join(root, 'memory.md');
  const content = '# log\n\n## v1\nSTOP retain\n\n## v2\nlatest\n';
  fs.writeFileSync(file, content);
  const original = fs.fsyncSync;
  try {
    fs.fsyncSync = () => { throw new Error('synthetic ENOSPC'); };
    assert.throws(() => rotateLog('memory.md', { root, maxKb: 0, keep: 1 }), /ENOSPC/);
    assert.equal(fs.readFileSync(file, 'utf8'), content);
    const dir = path.join(root, 'docs/archive');
    assert.equal(fs.existsSync(dir) ? fs.readdirSync(dir).filter(x => x.endsWith('.md')).length : 0, 0);
  } finally {
    fs.fsyncSync = original;
    fs.rmSync(root, { recursive: true, force: true });
  }
});
