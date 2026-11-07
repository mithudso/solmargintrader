// The manifest version is what the owner sees in chrome://extensions and in the
// popup header. A change that ships without bumping it looks like no change at
// all (2026-11-07: the SolTUI panel shipped as 0.1.0 and read as "nothing
// changed"). CI also fails a pull request that edits src/ or manifest.json
// without bumping the version; this test keeps the two version fields in step.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => JSON.parse(readFileSync(new URL(`../${p}`, import.meta.url), 'utf8'));

test('manifest.json and package.json carry the same semver version', () => {
  const manifest = read('manifest.json');
  const pkg = read('package.json');
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.equal(pkg.version, manifest.version);
});

test('popup and dashboard show the manifest version', () => {
  for (const page of ['src/ui/popup.html', 'src/ui/dashboard.html']) {
    const html = readFileSync(new URL(`../${page}`, import.meta.url), 'utf8');
    assert.match(html, /id="version"/, page);
  }
  const popup = readFileSync(new URL('../src/ui/popup.js', import.meta.url), 'utf8');
  assert.match(popup, /getManifest\(\)\.version/);
});
