import { readFile } from 'node:fs/promises';

export async function sourceText(relative) {
  const key = `extension/${relative}`;
  if (process.env.CDO_BASELINE_ROOT && (process.env.CDO_BASELINE_FILES ?? '').split(',').includes(key)) {
    return readFile(`${process.env.CDO_BASELINE_ROOT}/${key}.iter1`, 'utf8');
  }
  return readFile(new URL(`../../${relative}`, import.meta.url), 'utf8');
}

/** Exercise actual import-unsafe tool bodies with inert effects and no child. */
export async function importSource(relative, { replace = [], tail, append = '' } = {}) {
  const url = new URL(`../../${relative}`, import.meta.url);
  let source = await sourceText(relative);
  source = source.replace(/^#![^\n]*\n/, '');
  for (const [before, after] of replace) {
    if (!source.includes(before)) throw new Error(`Missing test seam in ${relative}`);
    source = source.replace(before, after);
  }
  if (tail) source = source.slice(0, source.lastIndexOf(tail));
  source = source.replace(/from '([^']+)'/g, (_, specifier) => `from ${JSON.stringify(specifier.startsWith('.') ? new URL(specifier, url).href : specifier)}`);
  source = source.replaceAll('import.meta.url', JSON.stringify(url.href));
  return import(`data:text/javascript;base64,${Buffer.from(source + '\n' + append).toString('base64')}`);
}
