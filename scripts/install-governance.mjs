#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const cwd=process.cwd();
function git(args){return execFileSync('git',args,{cwd,encoding:'utf8',windowsHide:true}).trim()}
try{git(['rev-parse','--show-toplevel']);}catch{console.error('[install] Not a Git workspace. Files are present, but Git hooks were not installed.');process.exit(2)}

const hookDir=path.join(cwd,'.githooks');
fs.mkdirSync(hookDir,{recursive:true});
const preCommit=`#!/bin/sh\nnode scripts/governance-check.mjs staged\n`;
const prePush=`#!/bin/sh\nnode scripts/governance-check.mjs head\n`;
fs.writeFileSync(path.join(hookDir,'pre-commit'),preCommit,'utf8');
fs.writeFileSync(path.join(hookDir,'pre-push'),prePush,'utf8');
try{fs.chmodSync(path.join(hookDir,'pre-commit'),0o755);fs.chmodSync(path.join(hookDir,'pre-push'),0o755);}catch{}
git(['config','core.hooksPath','.githooks']);
console.log('[install] Git governance hooks installed.');
console.log('[install] pre-commit -> staged scope gate');
console.log('[install] pre-push   -> HEAD scope gate');
console.log('[install] IMPORTANT: direct agent filesystem/shell/MCP routes are not made exclusive by Git hooks alone.');
console.log('[install] Route mutation-capable adapters through scripts/action-preflight.mjs or LBE/controller enforcement for stronger protection.');
