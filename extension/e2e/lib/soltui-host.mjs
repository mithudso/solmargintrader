/**
 * The soltui native messaging host, for the real-browser e2e.
 *
 * Chrome for Testing runs with a throwaway --user-data-dir, and Chrome looks for
 * native messaging host manifests in <user-data-dir>/NativeMessagingHosts first.
 * Writing the manifest there lets the e2e connect the extension under test to a
 * host WITHOUT touching the owner's real browsers' NativeMessagingHosts
 * directories, which `python -m soltui.native_host_install` owns.
 *
 * Two hosts, picked at run time and reported by the run:
 *   real     python -m soltui.native_host, the production host (needs soltui's venv)
 *   fixture  e2e/fixtures/fake-soltui-host.mjs, same framing and envelope shapes,
 *            used where soltui is not installed (for example the Linux CI runner)
 * SOLTUI_E2E_HOST=real|fixture forces one; "real" fails the run if it cannot start.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { createNodeSoltuiTransport, defaultHostCommand, repoRoot, soltuiPython } from '../../tools/soltui-transport.js';

export const HOST_NAME = 'com.mitchhudson.soltui';
const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const FIXTURE = path.join(EXT, 'e2e', 'fixtures', 'fake-soltui-host.mjs');

const shq = (value) => `'${String(value).replace(/'/g, `'\\''`)}'`;

/** Does the production host answer a ping? */
export async function realHostAnswers(env = process.env) {
  if (!fs.existsSync(path.join(repoRoot(env), 'soltui', 'native_host.py'))) return false;
  const envelope = await createNodeSoltuiTransport({ env })
    .request({ op: 'ping' }, { timeoutMs: 15_000 })
    .catch(() => null);
  return envelope?.ok === true;
}

/**
 * Write the wrapper script and the host manifest for this run.
 * @returns {{kind: 'real'|'fixture', manifestPath: string, env: object, remove: function, restore: function}}
 */
export async function installHost({ profile, extensionId, mode = process.env.SOLTUI_E2E_HOST, probe = realHostAnswers }) {
  const real = mode !== 'fixture' && await probe();
  if (mode === 'real' && !real) throw new Error('SOLTUI_E2E_HOST=real but the soltui native host did not answer a ping');

  const dir = path.join(profile, 'NativeMessagingHosts');
  fs.mkdirSync(dir, { recursive: true });
  const wrapper = path.join(profile, 'soltui-host.sh');
  // Popup recovery is now an explicit feature. The real-host smoke remains
  // read-only and isolated from the owner's running prediction plan.
  const configDir = path.join(profile, 'soltui-config');
  fs.mkdirSync(path.join(configDir, 'forwardtest'), { recursive: true });
  fs.writeFileSync(path.join(configDir, 'forwardtest', 'control.json'), JSON.stringify({ paused: true }), { mode: 0o600 });
  const scopedEnv = { ...process.env, SOLTUI_CONFIG_DIR: configDir };
  const host = defaultHostCommand(process.env);
  const launch = real
    ? `cd ${shq(host.cwd)} && exec ${shq(host.command)} ${host.args.map(shq).join(' ')}`
    : `exec ${shq(process.execPath)} ${shq(FIXTURE)}`;
  fs.writeFileSync(wrapper, `#!/bin/sh\nexport SOLTUI_CONFIG_DIR=${shq(configDir)}\n${launch}\n`, { mode: 0o700 });

  const manifestPath = path.join(dir, `${HOST_NAME}.json`);
  const manifest = {
    name: HOST_NAME,
    description: 'soltui native messaging host (e2e)',
    path: wrapper,
    type: 'stdio',
    allowed_origins: [`chrome-extension://${extensionId}/`],
  };
  const write = () => fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  write();

  return {
    kind: real ? 'real' : 'fixture',
    manifestPath,
    wrapper,
    // The same wrapper the browser runs, for the node CLI and API to use.
    env: { ...scopedEnv, SOLTUI_NATIVE_HOST: wrapper },
    // `soltui list` / `soltui call`, the Python CLI. Only with the real host.
    cli: real
      ? (args) => new Promise((resolve) => {
          execFile(soltuiPython(), ['-m', 'soltui.cli', ...args], { cwd: repoRoot(), env: scopedEnv, timeout: 120_000, maxBuffer: 64 * 1024 * 1024 },
            (err, stdout, stderr) => resolve({ code: err?.code ?? 0, stdout, stderr }));
        })
      : null,
    remove: () => fs.rmSync(manifestPath, { force: true }),
    restore: write,
  };
}
