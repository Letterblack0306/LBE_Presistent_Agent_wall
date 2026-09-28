import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
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

export function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((o, k) => { o[k] = stable(value[k]); return o; }, {});
  }
  return value;
}

export function canonicalScope(scope) {
  return JSON.stringify(stable(scope));
}

export function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

export function verifyScopeAuthorization(root) {
  const policyPath = path.join(root, '.governance', 'workspace-policy.json');
  const scopePath = path.join(root, '.governance', 'task-scope.json');
  const sigPath = path.join(root, '.governance', 'task-scope.sig.json');
  if (!fs.existsSync(policyPath)) return { ok: false, code: 'POLICY_MISSING' };
  if (!fs.existsSync(scopePath)) return { ok: false, code: 'SCOPE_MISSING' };
  if (!fs.existsSync(sigPath)) return { ok: false, code: 'SCOPE_SIGNATURE_MISSING' };
  const policy = readJson(policyPath);
  const scope = readJson(scopePath);
  const sig = readJson(sigPath);
  if (!scope.active) return { ok: false, code: 'NO_ACTIVE_SCOPE', policy, scope };
  if (policy.scopeRequiresOperatorSignature !== true) return { ok: false, code: 'POLICY_SIGNATURE_REQUIREMENT_DISABLED', policy, scope };
  const pubPath = path.join(root, policy.operatorPublicKey || '.governance/operator-public.pem');
  if (!fs.existsSync(pubPath)) return { ok: false, code: 'OPERATOR_PUBLIC_KEY_MISSING', policy, scope };
  if (!sig.signatureBase64 || !sig.scopeSha256) return { ok: false, code: 'SCOPE_UNSIGNED', policy, scope };
  const canonical = canonicalScope(scope);
  const digest = sha256(canonical);
  if (digest !== sig.scopeSha256) return { ok: false, code: 'SCOPE_SIGNATURE_STALE', policy, scope, digest };
  let valid = false;
  try {
    valid = crypto.verify(null, Buffer.from(canonical), fs.readFileSync(pubPath, 'utf8'), Buffer.from(sig.signatureBase64, 'base64'));
  } catch { valid = false; }
  if (!valid) return { ok: false, code: 'SCOPE_SIGNATURE_INVALID', policy, scope };
  return { ok: true, policy, scope, signature: sig, digest };
}

function globToRegExp(glob) {
  let s = String(glob).replace(/\\/g, '/').replace(/[.+^${}()|[\]\\]/g, '\\$&');
  s = s.replace(/\*\*/g, '§§DOUBLESTAR§§').replace(/\*/g, '[^/]*').replace(/§§DOUBLESTAR§§/g, '.*');
  return new RegExp(`^${s}$`);
}

export function matchesAny(file, patterns = []) {
  const f = String(file).replace(/\\/g, '/');
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
  return [...new Set(files.map(f=>f.replace(/\\/g,'/')))].sort();
}

export function printBlocked(code, detail='') {
  console.error(`\n[GOVERNANCE BLOCKED] ${code}`);
  if (detail) console.error(detail);
  console.error('\nRequired reading:');
  DOCS.forEach((d,i)=>console.error(`${i+1}. ${d}`));
  console.error('\nIf authorization is required: create/update a scope proposal, then have an external operator sign it with operator-kit/Approve-Scope.mjs.');
  console.error('Do not make the gate pass by editing governance text, signatures, indexes, or scope after the fact.\n');
}
