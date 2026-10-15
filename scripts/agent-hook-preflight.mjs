#!/usr/bin/env node
// Harness-run pre-tool adapter: maps an agent platform's pre-tool hook payload
// onto scripts/action-preflight.mjs. The platform runs this; the agent does not
// choose to call it. Exit 0 = allow, exit 2 = block (stderr is shown to agent).
//
// Currently understands the Claude Code PreToolUse payload shape:
//   { tool_name, tool_input: { file_path | notebook_path | command }, cwd }
// Operations outside the workspace root are not governed by this workspace and
// pass through. Shell commands are classified only where the action is
// unambiguous (git commit / git push / delete); other shell effects are NOT
// claimed as enforced here (see docs/INTEGRATION.md: exclusive enforcement
// requires disabling mutation routes that bypass the controller).
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const preflight = path.join(here, 'action-preflight.mjs');

const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const SHELL_TOOLS = new Set(['Bash', 'PowerShell']);

export function classify(payload) {
  const tool = payload?.tool_name;
  const input = payload?.tool_input ?? {};
  if (WRITE_TOOLS.has(tool)) {
    const target = input.file_path ?? input.notebook_path;
    return target ? { action: 'write', target } : null;
  }
  if (SHELL_TOOLS.has(tool) && typeof input.command === 'string') {
    const cmd = input.command;
    if (/\bgit\s+(?:-[^\s]+\s+)*commit\b/.test(cmd)) return { action: 'commit', target: '' };
    if (/\bgit\s+(?:-[^\s]+\s+)*push\b/.test(cmd)) return { action: 'push', target: '' };
    if (/(?:^|[;&|]\s*)(?:rm|del|rmdir|Remove-Item)\b/.test(cmd)) return { action: 'delete', target: '' };
  }
  return null;
}

function relativeInside(target) {
  if (!target) return '';
  const absolute = path.resolve(root, target);
  const rel = path.relative(root, absolute);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null; // outside workspace
  return rel.split(path.sep).join('/');
}

export function decide(payload) {
  const op = classify(payload);
  if (!op) return { allow: true, reason: 'not a governed action' };
  const rel = relativeInside(op.target);
  if (rel === null) return { allow: true, reason: 'outside workspace root' };
  const args = [preflight, op.action];
  if (rel) args.push(rel);
  const result = spawnSync('node', args, { cwd: root, encoding: 'utf8', timeout: 20000 });
  if (result.status === 0) return { allow: true, reason: result.stdout.trim() };
  return { allow: false, reason: (result.stderr || result.stdout || 'preflight failed').trim() };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => { raw += chunk; });
  process.stdin.on('end', () => {
    let payload;
    try { payload = JSON.parse(raw); } catch {
      console.error('[governance] BLOCK hook payload is not valid JSON (fail closed)');
      process.exit(2);
    }
    const verdict = decide(payload);
    if (verdict.allow) process.exit(0);
    console.error(`[governance] BLOCK ${verdict.reason}`);
    process.exit(2);
  });
}
