#!/usr/bin/env node
import path from 'node:path';
import { repoRoot, verifyScopeAuthorization, matchesAny, printBlocked } from './governance-lib.mjs';

const [, , action, target=''] = process.argv;
if (!action) { console.error('Usage: node scripts/action-preflight.mjs <action> [workspace-relative-target]'); process.exit(2); }
const root = repoRoot();
const auth = verifyScopeAuthorization(root);
if (!auth.ok) { printBlocked(auth.code); process.exit(1); }
const { scope } = auth;
if (!(scope.allowedActions || []).includes(action)) { printBlocked('ACTION_NOT_AUTHORIZED', action); process.exit(1); }
if (target) {
  const normalized = target.replace(/\\/g,'/').replace(/^\.\//,'');
  const absolute = path.resolve(root, normalized);
  if (!absolute.startsWith(path.resolve(root) + path.sep) && absolute !== path.resolve(root)) { printBlocked('TARGET_OUTSIDE_WORKSPACE', normalized); process.exit(1); }
  if (matchesAny(normalized, scope.forbiddenFiles || [])) { printBlocked('FORBIDDEN_FILE_TOUCHED', normalized); process.exit(1); }
  if (!matchesAny(normalized, scope.allowedFiles || [])) { printBlocked('CHANGED_OUTSIDE_SCOPE', normalized); process.exit(1); }
}
console.log(`[governance] ALLOW action=${action}${target ? ` target=${target}` : ''} scope=${scope.scopeId}`);
