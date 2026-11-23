#!/usr/bin/env node
/** Register the private Zec advisory host for one Chrome extension ID. */
import { createHash, randomUUID } from 'node:crypto';
import { lstat, mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { isPrivateZecPath, isZecOrigin, validateZecSocketPath, zecSocketPath, ZEC_NATIVE_HOST } from './zec-transport.js';

const SOURCE_FILES = ['zec-native-host.js', 'zec-transport.js'];
const quote = (value) => "'" + value.replaceAll("'", "'\\''") + "'";

function defaultChromeHostDirectory() {
  const profileRoot = process.platform === 'darwin'
    ? path.join(os.homedir(), 'Library', 'Application Support', 'Google', 'Chrome')
    : path.join(process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config'), 'google-chrome');
  return path.join(profileRoot, 'NativeMessagingHosts');
}

async function writeAtomic(destination, content, mode) {
  const temp = `${destination}.${randomUUID()}.tmp`;
  try {
    await writeFile(temp, content, { flag: 'wx', mode });
    await rename(temp, destination);
  } finally {
    await unlink(temp).catch((error) => { if (error.code !== 'ENOENT') throw error; });
  }
}

async function mkdirPrivate(directory) {
  await mkdir(directory, { mode: 0o700, recursive: true });
  if (!isPrivateZecPath(await lstat(directory), 'isDirectory')) throw new Error('Zec native runtime directory is not private.');
}

export async function installZecNativeHost({
  extensionId, directory = defaultChromeHostDirectory(), endpoint = zecSocketPath(),
} = {}) {
  if (!['darwin', 'linux'].includes(process.platform)) throw new Error('Zec native host supports macOS and Linux.');
  const origin = `chrome-extension://${extensionId}/`;
  if (!isZecOrigin(origin)) throw new Error('Extension ID must contain 32 lowercase letters a through p.');
  if (!path.isAbsolute(directory)) throw new Error('NativeMessagingHosts directory must be an absolute path.');
  endpoint = validateZecSocketPath(endpoint);

  const sources = await Promise.all(SOURCE_FILES.map((name) => readFile(new URL(name, import.meta.url))));
  const packageType = '{"type":"module"}\n';
  const revision = createHash('sha256').update(packageType);
  for (const source of sources) revision.update(source);
  revision.update(JSON.stringify([process.execPath, origin, endpoint]));

  const runtimeRoot = path.join(directory, ZEC_NATIVE_HOST);
  const runtime = path.join(runtimeRoot, revision.digest('hex'));
  await mkdirPrivate(runtimeRoot);
  await mkdirPrivate(runtime);
  const host = path.join(runtime, SOURCE_FILES[0]);
  const wrapper = path.join(runtime, 'launch');
  const script = `#!/bin/sh\nexec ${[process.execPath, host, endpoint, origin].map(quote).join(' ')} "$@"\n`;
  await Promise.all([
    ...SOURCE_FILES.map((file, index) => writeAtomic(path.join(runtime, file), sources[index], 0o600)),
    writeAtomic(path.join(runtime, 'package.json'), packageType, 0o600),
    writeAtomic(wrapper, script, 0o700),
  ]);

  const manifestPath = path.join(directory, `${ZEC_NATIVE_HOST}.json`);
  const manifest = {
    name: ZEC_NATIVE_HOST,
    description: 'SolMarginTrader Zec advisory bridge',
    path: wrapper,
    type: 'stdio',
    allowed_origins: [origin],
  };
  await writeAtomic(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 0o600);
  return { manifestPath, endpoint, origin, wrapper };
}

async function main() {
  const { positionals, values } = parseArgs({
    allowPositionals: true,
    options: { dir: { type: 'string' }, socket: { type: 'string' }, help: { type: 'boolean', short: 'h' } },
  });
  if (values.help || positionals.length !== 1) {
    console.log('Usage: node extension/tools/zec-native-install.js <extension-id> [--dir <NativeMessagingHosts directory>] [--socket <private absolute socket path>]');
    if (!values.help) process.exitCode = 1;
    return;
  }
  const result = await installZecNativeHost({ extensionId: positionals[0], directory: values.dir, endpoint: values.socket });
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  main().catch((error) => { process.exitCode = 1; console.error(error.message); });
}
