import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

export const DOCS = [
  'AGENTS.md',
  'docs/GOVERNANCE_RULES.md',
  '.governance/workspace-policy.json',
  '.governance/task-scope.json',
  'docs/BLOCKER_GUIDE.md'
];

export function repoRoot(cwd = process.cwd()) {
  try { return execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8', windowsHide: true }).trim(); }
  catch { return path.resolve(cwd); }
}

export function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }

export function verifyScopeAuthorization(root) {
  const policyPath = path.join(root, '.governance', 'workspace-policy.json');
  const scopePath = path.join(root, '.governance', 'task-scope.json');
  if (!fs.existsSync(policyPath)) return { ok: false, code: 'POLICY_MISSING' };
  if (!fs.existsSync(scopePath)) return { ok: false, code: 'SCOPE_MISSING' };
  const policy = readJson(policyPath);
  const scope = readJson(scopePath);
  if (!scope.active) return { ok: false, code: 'NO_ACTIVE_SCOPE', policy, scope };
  if (scope.scopeLocked !== true) return { ok: false, code: 'SCOPE_NOT_LOCKED', policy, scope };
  return { ok: true, policy, scope };
}

function globToRegExp(glob) {
  let s = String(glob).replace(/\\\\/g, '/').replace(/[.+^${}()|[\]\\]/g, '\\$&');
  s = s.replace(/\*\*/g, '§§DOUBLESTAR§§').replace(/\*/g, '[^/]*').replace(/§§DOUBLESTAR§§/g, '.*');
  return new RegExp(`^${s}$`);
}

export function matchesAny(file, patterns = []) {
  const f = String(file).replace(/\\\\/g, '/');
  return patterns.some(p => globToRegExp(p).test(f));
}

export function changedFiles(root, mode = 'worktree') {
  const run = args => {
    try { return execFileSync('git', args, { cwd: root, encoding: 'utf8', windowsHide: true }).split(/\r?\n/).map(x=>x.trim()).filter(Boolean); }
    catch { return []; }
  };
  let files = [];
  if (mode === 'staged') files = run(['diff', '--cached', '--name-only']);
  else if (mode === 'head') files = run(['diff-tree', '--root', '--no-commit-id', '--name-only', '-r', 'HEAD']);
  else files = [...run(['diff','--name-only']), ...run(['diff','--cached','--name-only']), ...run(['ls-files','--others','--exclude-standard'])];
  return [...new Set(files.map(f=>f.replace(/\\\\/g,'/')))].sort();
}

export function printBlocked(code, detail='') {
  console.error(`\n[GOVERNANCE BLOCKED] ${code}`);
  if (detail) console.error(detail);
  console.error('\nRequired reading:');
  DOCS.forEach((d,i)=>console.error(`${i+1}. ${d}`));
  console.error('\nUse an active locked task scope whose allowedFiles and allowedActions cover the intended operation.');
  console.error('Denial is limited to the named effect and path. Continue independent scoped development, including additions, fixes and deletions; do not treat an acceptance gap as a task-wide prohibition.');
  console.error('Preserve genuine file/action scope and protected-effect checks.\n');
}
