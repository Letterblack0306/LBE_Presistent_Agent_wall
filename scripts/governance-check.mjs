#!/usr/bin/env node
import { repoRoot, verifyScopeAuthorization, changedFiles, matchesAny, printBlocked } from './governance-lib.mjs';

const mode = process.argv[2] || 'worktree';
const root = repoRoot();
const auth = verifyScopeAuthorization(root);
if (!auth.ok) { printBlocked(auth.code); process.exit(1); }
const { scope } = auth;
const action = mode === 'staged' ? 'commit' : mode === 'head' ? 'push' : 'write';
if (!(scope.allowedActions || []).includes(action)) {
  printBlocked('ACTION_NOT_AUTHORIZED', `${action} is not in allowedActions.`);
  process.exit(1);
}
const files = changedFiles(root, mode);
const blocked = [];
for (const file of files) {
  if (matchesAny(file, scope.forbiddenFiles || [])) blocked.push({ file, reason: 'FORBIDDEN_FILE_TOUCHED' });
  else if (!matchesAny(file, scope.allowedFiles || [])) blocked.push({ file, reason: 'CHANGED_OUTSIDE_SCOPE' });
}
if (blocked.length) {
  for (const b of blocked) console.error(`${b.reason}: ${b.file}`);
  printBlocked('SCOPE_VIOLATION', `${blocked.length} changed path(s) are not authorized by the signed scope.`);
  process.exit(1);
}
console.log(`[governance] PASS mode=${mode} scope=${scope.scopeId} files=${files.length}`);
