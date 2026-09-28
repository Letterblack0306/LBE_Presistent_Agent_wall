# Operator Authorization

This document closes the initial-governance deadlock without allowing agent self-authorization.

## One-time operator setup (outside the agent session)

Run from a trusted terminal controlled by the operator:

```powershell
node operator-kit/Initialize-Operator-Key.mjs
node operator-kit/Install-Public-Key.mjs C:\path\to\workspace
```

The private key is created outside the workspace under:

```text
%USERPROFILE%\.letterblack-governance\operator-private.pem
```

Do not copy the private key into the repository or expose it to an agent.

## Activate a task

1. Edit `.governance/task-scope.json` to the exact intended scope.
2. Set `active: true` and `scopeLocked: true`.
3. Include exact file patterns in `allowedFiles`.
4. Include only required actions in `allowedActions`; add `commit` or `push` only when intended.
5. Review the proposal:

```powershell
node scripts/propose-scope.mjs
```

6. From the trusted operator terminal, sign it:

```powershell
node operator-kit/Approve-Scope.mjs C:\path\to\workspace "Pravesh"
```

7. Validate:

```powershell
node scripts/governance-check.mjs worktree
```

Any later edit to `task-scope.json` makes the detached signature stale and blocks again until re-approved.

## Governance bootstrap commit

For the first governance-kit commit, authorize only the governance-kit paths and actions `write` + `commit` (+ `push` only if you intend to push that bootstrap). Do not include unrelated source files in this bootstrap scope.

After the governance bootstrap is committed/pushed, replace it with a new signed implementation scope for the actual task.
