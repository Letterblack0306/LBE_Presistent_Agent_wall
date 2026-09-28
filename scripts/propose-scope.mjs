#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { repoRoot, canonicalScope, sha256 } from './governance-lib.mjs';
const root = repoRoot();
const scopePath = path.join(root,'.governance','task-scope.json');
if (!fs.existsSync(scopePath)) { console.error('Missing .governance/task-scope.json'); process.exit(1); }
const scope = JSON.parse(fs.readFileSync(scopePath,'utf8'));
const digest = sha256(canonicalScope(scope));
const req = {
  version:1,
  requestType:'SCOPE_APPROVAL_REQUEST',
  scopeId: scope.scopeId,
  scopeSha256:digest,
  objective:scope.objective,
  mode:scope.mode,
  allowedFiles:scope.allowedFiles,
  allowedActions:scope.allowedActions
};
const out = path.join(root,'.governance','scope-approval-request.json');
fs.writeFileSync(out, JSON.stringify(req,null,2)+'\n');
console.log(`Wrote ${path.relative(root,out)}\nScope SHA-256: ${digest}\nAn external operator must now sign the scope. This request is not authorization.`);
