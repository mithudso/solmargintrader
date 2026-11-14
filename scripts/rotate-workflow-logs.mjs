#!/usr/bin/env node
// Rotate the workflow logs memory.md and prompts.md.
//
// If a log is larger than the size limit (default 200 KB), this script keeps the
// file header and the newest N `## v` sections in place. It moves every
// older `## v` section to docs/archive/<name>-<YYYY-MM-DD>.md. If that archive
// file exists, the script appends to it.
//
//   node scripts/rotate-workflow-logs.mjs [--dry-run] [--max-kb N] [--keep N] [--root DIR]
//
//   --dry-run   print what would move; change nothing
//   --max-kb N  size limit in KB (default 200)
//   --keep N    number of newest sections to keep (default 20)
//   --root DIR  directory that holds memory.md and prompts.md (default: repository root)
//
// Exit codes: 0 done (or nothing to do), 1 error, 2 refused because an editor swap
// file (.memory.md.swp, .memory.md.swo, and the same for prompts.md) exists next to a
// log that needs rotation.

import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const SELF_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LOGS = ['memory.md', 'prompts.md'];
const SWAP_SUFFIXES = ['swp', 'swo'];

function parseArgs(argv) {
  const opts = { dryRun: false, maxKb: 200, keep: 20, root: SELF_ROOT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const num = (name) => {
      const v = Number(argv[++i]);
      if (!Number.isFinite(v) || v < 0) throw new Error(`${name} needs a non-negative number`);
      return v;
    };
    if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--max-kb') opts.maxKb = num('--max-kb');
    else if (a === '--keep') opts.keep = Math.floor(num('--keep'));
    else if (a === '--root') {
      if (!argv[i + 1]) throw new Error('--root needs a directory');
      opts.root = path.resolve(argv[++i]);
    } else if (a === '-h' || a === '--help') opts.help = true;
    else throw new Error(`unknown option ${a}`);
  }
  return opts;
}

// Support both `## v1` integer versions and `## v1.2.3` semver versions.
const VERSION_RE = /^## v(\d+)(?:\.(\d+))?(?:\.(\d+))?/;

export function splitSections(text) {
  const lines = text.split('\n');
  const starts = [];
  let fence = null;
  lines.forEach((line, i) => {
    const marker = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (marker) {
      const token = marker[1];
      if (!fence) fence = token;
      else if (token[0] === fence[0] && token.length >= fence.length && /^ {0,3}(`+|~+)\s*$/.test(line)) fence = null;
      return;
    }
    if (!fence && VERSION_RE.test(line)) starts.push(i);
  });
  if (!starts.length) return { header: text, sections: [] };
  const header = lines.slice(0, starts[0]).join('\n');
  const sections = starts.map((s, n) => {
    const end = n + 1 < starts.length ? starts[n + 1] : lines.length;
    const body = lines.slice(s, end).join('\n');
    const m = VERSION_RE.exec(lines[s]);
    return {
      body,
      version: m ? [Number(m[1]), Number(m[2] || 0), Number(m[3] || 0)] : null,
    };
  });
  return { header, sections };
}

function compareVersion(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

export function pickArchived(sections, keep) {
  const versioned = sections
    .map((s, index) => ({ index, version: s.version }))
    .filter((s) => s.version);
  versioned.sort((a, b) => compareVersion(b.version, a.version) || b.index - a.index);
  const keepIdx = new Set(versioned.slice(0, keep).map((s) => s.index));
  return versioned
    .filter((s) => !keepIdx.has(s.index))
    .map((s) => s.index)
    .sort((a, b) => a - b);
}

function swapFilesFor(dir, name) {
  return SWAP_SUFFIXES.map((ext) => path.join(dir, `.${name}.${ext}`)).filter((p) => fs.existsSync(p));
}

function today() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function rotateLogLocked(logName, opts) {
  const filePath = path.join(opts.root, logName);
  if (!fs.existsSync(filePath)) return { status: 'missing' };
  const stat = fs.statSync(filePath);
  const sizeKb = stat.size / 1024;
  if (sizeKb <= opts.maxKb) {
    return { status: 'ok', sizeKb };
  }

  const swaps = swapFilesFor(opts.root, logName);
  if (swaps.length > 0) {
    return { status: 'refused_swap', swaps };
  }

  const content = fs.readFileSync(filePath, 'utf8');
  const { header, sections } = splitSections(content);
  if (sections.length <= opts.keep) {
    return { status: 'too_few_sections', count: sections.length };
  }

  const toArchiveIndices = pickArchived(sections, opts.keep);
  if (toArchiveIndices.length === 0) {
    return { status: 'nothing_to_archive' };
  }

  const archiveDir = path.join(opts.root, 'docs', 'archive');
  const baseName = logName.replace(/\.md$/, '');
  const archiveFile = path.join(archiveDir, `${baseName}-${today()}.md`);


  const keptIndices = new Set(toArchiveIndices);
  const keptSections = sections.filter((_, i) => !keptIndices.has(i));

  const newLogContent = (header.trimEnd() + '\n\n' + keptSections.map((s) => s.body.trimEnd()).join('\n\n')).trimEnd() + '\n';

  if (opts.dryRun) {
    return {
      status: 'dry_run',
      archivedCount: toArchiveIndices.length,
      keptCount: keptSections.length,
      archiveFile,
    };
  }

  if (!fs.existsSync(archiveDir)) {
    fs.mkdirSync(archiveDir, { recursive: true });
  }

  const previousArchive = fs.existsSync(archiveFile) ? fs.readFileSync(archiveFile, 'utf8') : '';
  // An earlier attempt can publish the archive and fail before publishing the
  // active log. Match exact bodies with multiplicity so retry preserves history.
  const archivedCounts = new Map();
  for (const section of splitSections(previousArchive).sections) {
    const body = section.body.trimEnd();
    archivedCounts.set(body, (archivedCounts.get(body) || 0) + 1);
  }
  const missing = [];
  for (const index of toArchiveIndices) {
    const body = sections[index].body.trimEnd();
    const count = archivedCounts.get(body) || 0;
    if (count) archivedCounts.set(body, count - 1);
    else missing.push(body);
  }
  const archiveHeader = `# Archived ${logName} entries\n\nArchived on ${today()}.\n\n`;
  const newArchiveContent = (previousArchive || archiveHeader).trimEnd()
    + (missing.length ? '\n\n' + missing.join('\n\n') : '') + '\n';
  let archiveTemp, logTemp;
  try {
    archiveTemp = prepareFile(archiveFile, newArchiveContent);
    logTemp = prepareFile(filePath, newLogContent);
    if (fs.readFileSync(filePath, 'utf8') !== content
        || (fs.existsSync(archiveFile) ? fs.readFileSync(archiveFile, 'utf8') : '') !== previousArchive) {
      throw new Error('workflow log changed during rotation; retry after the writer finishes');
    }
    // Commit the archive first. The active file remains intact until every
    // archived byte is durable. A retry deduplicates an already committed archive.
    fs.renameSync(archiveTemp, archiveFile);
    syncDirectory(archiveDir);
    fs.renameSync(logTemp, filePath);
    syncDirectory(opts.root);
  } finally {
    for (const tmp of [archiveTemp, logTemp]) if (tmp && fs.existsSync(tmp)) fs.unlinkSync(tmp);
  }
  return {
    status: 'rotated',
    archivedCount: toArchiveIndices.length,
    keptCount: keptSections.length,
    archiveFile,
  };
}

function prepareFile(target, content) {
  const tmp = target + `.tmp-${process.pid}-${randomUUID()}`;
  const mode = fs.existsSync(target) ? fs.statSync(target).mode & 0o777 : 0o600;
  const fd = fs.openSync(tmp, 'wx', mode);
  try {
    fs.writeFileSync(fd, content, 'utf8');
    fs.fsyncSync(fd);
  } catch (error) {
    fs.unlinkSync(tmp);
    throw error;
  } finally {
    fs.closeSync(fd);
  }
  return tmp;
}

function syncDirectory(dir) {
  const fd = fs.openSync(dir, 'r');
  try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}

export function rotateLog(logName, opts) {
  const lock = path.join(opts.root, `.${logName}.rotate.lock`);
  const fd = fs.openSync(lock, 'wx', 0o600);
  try { return rotateLogLocked(logName, opts); }
  finally { fs.closeSync(fd); fs.unlinkSync(lock); }
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log('Usage: node scripts/rotate-workflow-logs.mjs [--dry-run] [--max-kb N] [--keep N] [--root DIR]');
    process.exit(0);
  }

  let hasRefused = false;
  for (const log of LOGS) {
    const res = rotateLog(log, opts);
    if (res.status === 'refused_swap') {
      console.error(`Refused to rotate ${log}: live swap files found: ${res.swaps.join(', ')}`);
      hasRefused = true;
    } else if (res.status === 'rotated') {
      console.log(`Rotated ${log}: moved ${res.archivedCount} sections to ${res.archiveFile}, kept ${res.keptCount}.`);
    } else if (res.status === 'dry_run') {
      console.log(`[dry-run] Would rotate ${log}: ${res.archivedCount} sections to ${res.archiveFile}, keeping ${res.keptCount}.`);
    } else if (res.status === 'ok') {
      console.log(`${log} is ${res.sizeKb.toFixed(1)} KB (under ${opts.maxKb} KB limit).`);
    }
  }

  if (hasRefused) {
    process.exit(2);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main();
}
