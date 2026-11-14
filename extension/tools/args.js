/** Strict argument handling shared by the small Node entrypoints. No I/O. */
export function toolArgs(argv, defaults, { booleans = [], usage }) {
  const out = { ...defaults };
  const flags = new Set(booleans);
  try {
    for (let i = 0; i < argv.length; i++) {
      const token = argv[i];
      if (token === '--help' || token === '-h') return { ...out, help: true };
      if (!token.startsWith('--') || !Object.hasOwn(defaults, token.slice(2))) throw new Error('unknown argument');
      const name = token.slice(2);
      if (flags.has(name)) { out[name] = true; continue; }
      if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) throw new Error(`--${name} needs a value`);
      out[name] = argv[++i];
    }
  } catch (error) {
    throw Object.assign(new Error(`${error.message}\n${usage}`), { exitCode: 2 });
  }
  return out;
}

export function toolFailure(error) {
  console.error(error.message);
  process.exitCode = error.exitCode ?? 1;
}
