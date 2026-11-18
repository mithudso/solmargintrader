/** Decode the published Jupiter Perps replay rankings. Writes CSV to stdout. */
import { readFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { pathToFileURL } from 'node:url';
import { PRESETS, RISK_PRESETS } from '../src/perps/strategies.js';

const INPUT = new URL('../../research/results/jupiter_perps_leverage_20261118.csv', import.meta.url);
const PRESETS_BY_ID = new Map(PRESETS.map(preset => [preset.id, preset]));
const EXTRA_COLUMNS = [
  'scope', 'rank', 'strategyFamily', 'strategyName', 'strategyRules',
  'sizingAmountUsd', 'takeProfitPct', 'stopLossPct',
];

function describeMember({ strategy, params }) {
  switch (strategy) {
    case 'rsi': {
      const exit = params.exit_level === 100 ? ' (unreachable by signal)' : '';
      return {
        family: 'RSI',
        rules: `RSI(${params.period}) enters below ${params.oversold}, exits above ${params.exit_level}${exit}`,
      };
    }
    case 'zscore':
      return {
        family: 'Z-score',
        rules: `Z-score(${params.window} closes, sample SD) enters at or below ${params.entry_z}, exits at or above ${params.exit_z}`,
      };
    case 'bb_reversion':
      return {
        family: 'Bollinger',
        rules: `Bollinger(${params.window} closes, ${params.num_std} population SD) enters below the lower band, exits above the mean`,
      };
    default:
      throw new Error(`Unknown archived strategy ${strategy}.`);
  }
}

export function describePreset(preset) {
  if (preset.members) {
    const members = preset.members.map(describeMember);
    return {
      family: members.map(member => member.family).join(' + '),
      rules: members.map(member => member.rules).join(' | '),
    };
  }
  if (preset.kind === 'volty') {
    return {
      family: 'Volty',
      rules: `Prior closed bar close ± ${preset.factor} × the ${preset.length}-bar SMA of true range, opposite stop reverses`,
    };
  }
  const family = { mean: 'RSI + Z-score + Bollinger', zscore: 'Z-score', bands: 'Bollinger' }[preset.kind];
  if (!family) throw new Error(`Unknown preset kind ${preset.kind}.`);
  return { family, rules: preset.details };
}

const csvLine = fields => fields.map(value => {
  const text = String(value);
  return /[,"\r\n]/u.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}).join(',');

function decodeLeaderboard(csv) {
  // The published source grid contains only unquoted IDs, labels, and numbers.
  const [header, ...lines] = csv.trimEnd().split(/\r?\n/u);
  const columns = header.split(',');
  const required = ['asset', 'strategy', 'cadenceSeconds', 'size', 'leverage', 'risk', 'test_returnPct'];
  if (required.some(name => !columns.includes(name))) throw new Error('Expected the published Jupiter Perps CSV columns.');
  const ranked = lines.map((line, i) => {
    const cells = line.split(',');
    if (cells.length !== columns.length) throw new Error(`Invalid replay CSV at line ${i + 2}.`);
    const row = Object.fromEntries(columns.map((name, column) => [name, cells[column]]));
    if (![row.test_returnPct, row.cadenceSeconds, row.leverage].every(value => value.trim() && Number.isFinite(Number(value)))) {
      throw new Error(`Missing or invalid replay metric at line ${i + 2}.`);
    }
    return { cells, row };
  }).sort((a, b) => Number(b.row.test_returnPct) - Number(a.row.test_returnPct));

  const focus = ({ row }) => row.asset === 'ZEC'
    && [300, 600].includes(Number(row.cadenceSeconds)) && [25, 50].includes(Number(row.leverage));
  const scopes = [['global', ranked], ['zec-5m-10m-25x-50x', ranked.filter(focus)]];
  const output = [csvLine([...EXTRA_COLUMNS, ...columns])];
  for (const [scope, results] of scopes) {
    for (const [i, { cells, row }] of results.slice(0, 50).entries()) {
      const preset = PRESETS_BY_ID.get(row.strategy);
      const risk = RISK_PRESETS[row.risk];
      if (!preset || !risk || !['collateral', 'notional'].includes(row.size)) {
        throw new Error(`Missing strategy, risk or sizing for ${row.strategy}.`);
      }
      const { family, rules } = describePreset(preset);
      const sizingAmount = row.size === 'collateral' ? 25 : 250;
      output.push(csvLine([scope, i + 1, family, preset.name, rules, sizingAmount, risk.tp, risk.sl, ...cells]));
    }
  }
  return output.join('\n') + '\n';
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { values } = parseArgs({ options: { input: { type: 'string' }, help: { type: 'boolean' } } });
  if (values.help) {
    console.log('node extension/tools/zec-leaderboard.mjs [--input published-replay.csv]');
  } else {
    process.stdout.write(decodeLeaderboard(readFileSync(values.input ?? INPUT, 'utf8')));
  }
}
