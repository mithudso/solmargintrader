#!/usr/bin/env node
/**
 * CLI surface.
 *
 * Every command is generated from the registry in src/core/commands.js, so this
 * file contains no per-command logic and cannot fall behind the extension. Add
 * a command there and it appears here, in the help text, and in the HTTP API.
 *
 *   node tools/cli.js                        # help
 *   node tools/cli.js status
 *   node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7
 *   node tools/cli.js plan --price 75
 *   node tools/cli.js arm
 *   node tools/cli.js tick --count 3
 *   node tools/cli.js pnl --json
 *   node tools/cli.js reset --confirm
 *
 * Global flags: --json  --ephemeral  --quiet  --store-path P  --config-path P
 *               --passphrase P  --help
 */

import { runCommand, describeCommands, COMMANDS, CommandError, TYPE } from '../src/core/commands.js';
import { createNodeDeps } from './deps.js';

const GLOBAL_FLAGS = new Set([
  'json',
  'ephemeral',
  'quiet',
  'help',
  'store-path',
  'config-path',
  'passphrase',
]);

function parseArgv(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      positional.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    // A flag with no value, or followed by another flag, is boolean true.
    if (next === undefined || next.startsWith('--')) {
      flags[key] = true;
    } else {
      flags[key] = next;
      i++;
    }
  }
  return { positional, flags };
}

/** Coerce a raw CLI string into the type the registry declares. */
function coerce(param, raw) {
  if (param.type === TYPE.NUMBER) {
    const n = Number(raw);
    if (!Number.isFinite(n)) {
      throw new CommandError(`--${param.name} must be a number, got "${raw}"`, 400);
    }
    return n;
  }
  if (param.type === TYPE.BOOL) {
    if (raw === true || raw === 'true' || raw === '1' || raw === 'yes') return true;
    if (raw === 'false' || raw === '0' || raw === 'no') return false;
    throw new CommandError(`--${param.name} must be a boolean, got "${raw}"`, 400);
  }
  if (param.type === TYPE.JSON) {
    try {
      return JSON.parse(raw);
    } catch (err) {
      throw new CommandError(`--${param.name} must be valid JSON: ${err.message}`, 400);
    }
  }
  return String(raw);
}

function helpText() {
  const commands = describeCommands();
  const width = Math.max(...commands.map((c) => c.name.length));
  const lines = [
    'solmargintrader — Jupiter grid trading',
    '',
    'Usage: node tools/cli.js <command> [--flag value]',
    '',
    'Commands:',
  ];
  for (const c of commands) {
    const tag = c.destructive ? ' [destructive]' : c.readOnly ? '' : ' [writes]';
    lines.push(`  ${c.name.padEnd(width)}  ${c.describe}${tag}`);
  }
  lines.push(
    '',
    'Global flags:',
    '  --json          machine-readable output',
    '  --ephemeral     in-memory state; nothing persisted',
    '  --quiet         suppress engine log lines',
    '  --store-path P  journal file (default ~/.solmargintrader/journal.json)',
    '  --config-path P config file (default ~/.solmargintrader/config.json)',
    '  --passphrase P  unlock a full-auto session key',
    '',
    'Per-command flags: node tools/cli.js <command> --help',
  );
  return lines.join('\n');
}

function commandHelp(name) {
  const c = describeCommands().find((x) => x.name === name);
  const lines = [`${name} — ${c.describe}`, ''];
  if (c.params.length === 0) {
    lines.push('(no arguments)');
  } else {
    lines.push('Arguments:');
    const width = Math.max(...c.params.map((p) => p.name.length));
    for (const p of c.params) {
      const req = p.required ? ' (required)' : '';
      lines.push(`  --${p.name.padEnd(width)}  ${p.type}${req}${p.describe ? ` — ${p.describe}` : ''}`);
    }
  }
  return lines.join('\n');
}

/** Human-readable rendering; --json prints the raw payload instead. */
function render(name, result) {
  if (name === 'exportCsv') return result.csv;
  if (name === 'levels') {
    const rows = result.expectedRoundTripUsd
      .map((r) => `  $${r.level.toFixed(4)}  round trip +$${r.grossUsd.toFixed(4)}`)
      .join('\n');
    return `rung width ${result.rungWidthBps.toFixed(1)} bps\n${rows}`;
  }
  if (name === 'plan') {
    const head = `price $${result.price.toFixed(4)} — ${result.intents.length} order(s) to place, ${result.restingCount} resting`;
    const body = result.intents
      .map((i) => `  ${i.side.toUpperCase().padEnd(4)} $${i.level.toFixed(4)}  $${i.notionalUsd.toFixed(2)}  ${i.intentKey}`)
      .join('\n');
    const skips = result.skipped.length ? `\nskipped: ${summariseSkips(result.skipped)}` : '';
    return [head, body, skips].filter(Boolean).join('\n');
  }
  return JSON.stringify(result, null, 2);
}

function summariseSkips(skipped) {
  const counts = {};
  for (const s of skipped) counts[s.reason] = (counts[s.reason] ?? 0) + 1;
  return Object.entries(counts)
    .map(([reason, n]) => `${reason} x${n}`)
    .join(', ');
}

async function main() {
  const { positional, flags } = parseArgv(process.argv.slice(2));
  const name = positional[0];

  if (!name || flags.help === true && !name) {
    console.log(helpText());
    return;
  }
  if (!COMMANDS[name]) {
    console.error(`unknown command "${name}"\n`);
    console.error(helpText());
    process.exitCode = 2;
    return;
  }
  if (flags.help) {
    console.log(commandHelp(name));
    return;
  }

  // Split registry args from global flags, rejecting typos instead of ignoring
  // them — a silently dropped --notionalPerRungUsd would be a real money bug.
  const params = COMMANDS[name].params;
  const args = {};
  for (const [key, raw] of Object.entries(flags)) {
    if (GLOBAL_FLAGS.has(key)) continue;
    const param = params.find((p) => p.name === key);
    if (!param) {
      console.error(
        `command "${name}" has no argument --${key}. Accepts: ${
          params.map((p) => p.name).join(', ') || '(none)'
        }`,
      );
      process.exitCode = 2;
      return;
    }
    args[key] = coerce(param, raw);
  }

  const deps = await createNodeDeps({
    ephemeral: flags.ephemeral === true,
    quiet: flags.quiet === true || flags.json === true,
    storePath: typeof flags['store-path'] === 'string' ? flags['store-path'] : undefined,
    configPath: typeof flags['config-path'] === 'string' ? flags['config-path'] : undefined,
    passphrase: typeof flags.passphrase === 'string' ? flags.passphrase : undefined,
  });

  try {
    const result = await runCommand({ name, args, deps });
    console.log(flags.json === true ? JSON.stringify(result, null, 2) : render(name, result));
  } catch (err) {
    if (err instanceof CommandError) {
      console.error(`${name}: ${err.message}`);
      process.exitCode = 1;
      return;
    }
    throw err;
  }
}

main().catch((err) => {
  console.error(err?.stack ?? String(err));
  process.exitCode = 1;
});
