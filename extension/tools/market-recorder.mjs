#!/usr/bin/env node
/**
 * Records every Jupiter 1000x and Perps market to one folder per coin, for as
 * long as it runs. Public reads only: no wallet, no key, and nothing is sent to
 * a venue except the two stream subscriptions.
 *
 *   node tools/market-recorder.mjs --out /Volumes/dasdata/CoinTradingData
 *
 * USAGE in lib/market-recorder.mjs lists the folders it writes. The recorder is
 * lib/market-recorder-run.mjs; this file hands it the real clock and network.
 */
import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { USAGE, parseArgs } from './lib/market-recorder.mjs';
import { Recorder, startWatchdog } from './lib/market-recorder-run.mjs';

const REQUEST_TIMEOUT_MS = 10_000;

let options;
try { options = parseArgs(process.argv.slice(2)); } catch (error) { console.error(`${error.message}\n\n${USAGE}`); process.exit(2); }
if (options.help) { console.log(USAGE); process.exit(0); }
// A network disk that hangs can freeze this process without ending it, from the very first look at the folder.
// The watchdog is started before anything touches the disk, and ends the process so the supervisor starts a new one.
const watchdog = startWatchdog();
await watchdog.ready;
// The folder must be there already: when the disk is not mounted the path is missing, and nothing may be written in its place.
if (!existsSync(options.out) || !statSync(options.out).isDirectory()) {
  console.error(`Output folder ${options.out} does not exist. Mount the disk or create the folder, then start again.`);
  process.exit(2);
}
if (typeof globalThis.WebSocket !== 'function' || typeof globalThis.fetch !== 'function') {
  console.error('This recorder needs Node 22 or later (built-in fetch and WebSocket).');
  process.exit(2);
}

async function fetchJson(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS), credentials: 'omit', redirect: 'error', cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

const recorder = new Recorder({ options, fetchJson, WebSocket: globalThis.WebSocket, log: text => console.error(text) });
process.on('SIGINT', () => void recorder.stop('SIGINT'));
process.on('SIGTERM', () => void recorder.stop('SIGTERM'));
// Anything nobody caught ends the run cleanly, so the supervisor starts a fresh one rather than leaving a half-working recorder.
process.on('uncaughtException', error => recorder.fault(error));
process.on('unhandledRejection', error => recorder.fault(error));
try { recorder.start(); } catch (error) {
  console.error(['ELOCKED', 'ESTANDBY'].includes(error.code) ? error.message : `Could not start: ${error.message}`);
  process.exit(error.code === 'ELOCKED' ? 3 : error.code === 'ESTANDBY' ? 2 : 1);
}
console.log(`Recording to ${options.out}. Status: ${join(options.out, '_recorder', 'status.json')}. Stop with Ctrl-C.`);
