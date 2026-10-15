#!/usr/bin/env node
// Harness-run pre-tool adapter: maps an agent platform's pre-tool hook payload
// onto scripts/action-preflight.mjs. The platform runs this; the agent does not
// choose to call it. Exit 0 = allow, exit 2 = block (stderr is shown to agent).
//
// Verified payload shapes (official docs, 2026-10-15):
//   Claude Code PreToolUse : { tool_name: Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell,
//                              tool_input: { file_path | notebook_path | command }, cwd }
//   Codex PreToolUse       : { tool_name: Bash|apply_patch|mcp__*, tool_input: { command } }
//                            (apply_patch's command is the patch text)
//   Gemini CLI BeforeTool  : { tool_name: write_file|replace|run_shell_command|...,
//                              tool_input: { file_path | command }, cwd }
// Cline hooks are SDK plugins (TypeScript beforeTool), not a stdin command, and
// are not handled here. Operations outside the workspace root are not governed
// by this workspace and pass through. Shell commands are classified only where
// the action is unambiguous (git commit / git push / delete); other shell
// effects are NOT claimed as enforced (docs/INTEGRATION.md: exclusive
// enforcement requires disabling mutation routes that bypass the controller).
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const preflight = path.join(here, 'action-preflight.mjs');

const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'write_file', 'replace']);
const SHELL_TOOLS = new Set(['Bash', 'PowerShell', 'run_shell_command']);

function classifyShell(cmd) {
  if (/\bgit\s+(?:-[^\s]+\s+)*commit\b/.test(cmd)) return { action: 'commit', target: '' };
  if (/\bgit\s+(?:-[^\s]+\s+)*push\b/.test(cmd)) return { action: 'push', target: '' };
  if (/(?:^|[;&|]\s*)(?:rm|del|rmdir|Remove-Item)\b/.test(cmd)) return { action: 'delete', target: '' };
  return null;
}

// Codex apply_patch envelope: "*** Add|Update|Delete File: <path>" / "*** Move to: <path>"
export function patchOperations(patch) {
  const ops = [];
  for (const line of String(patch).split(/\r?\n/)) {
    const m = /^\*\*\* (Add|Update|Delete) File:\s*(.+?)\s*$/.exec(line);
    if (m) ops.push({ action: m[1] === 'Delete' ? 'delete' : 'write', target: m[2] });
    const mv = /^\*\*\* Move to:\s*(.+?)\s*$/.exec(line);
    if (mv) ops.push({ action: 'write', target: mv[1] });
  }
  return ops;
}

export function classify(payload) {
  const tool = payload?.tool_name;
  const input = payload?.tool_input ?? {};
  if (tool === 'apply_patch' && typeof input.command === 'string') return patchOperations(input.command);
  if (WRITE_TOOLS.has(tool)) {
    const target = input.file_path ?? input.notebook_path ?? input.path;
    return target ? [{ action: 'write', target }] : [];
  }
  if (SHELL_TOOLS.has(tool) && typeof input.command === 'string') {
    const op = classifyShell(input.command);
    return op ? [op] : [];
  }
  return [];
}

function relativeInside(target, cwd) {
  if (!target) return '';
  const absolute = path.resolve(cwd || root, target);
  const rel = path.relative(root, absolute);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null; // outside workspace
  return rel.split(path.sep).join('/');
}

export function decide(payload) {
  const ops = classify(payload);
  if (ops.length === 0) return { allow: true, reason: 'not a governed action' };
  for (const op of ops) {
    const rel = relativeInside(op.target, payload?.cwd);
    if (rel === null) continue; // outside workspace root
    const args = [preflight, op.action];
    if (rel) args.push(rel);
    const result = spawnSync('node', args, { cwd: root, encoding: 'utf8', timeout: 20000 });
    if (result.status !== 0) {
      return { allow: false, reason: (result.stderr || result.stdout || 'preflight failed').trim() };
    }
  }
  return { allow: true, reason: 'all governed operations allowed' };
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
