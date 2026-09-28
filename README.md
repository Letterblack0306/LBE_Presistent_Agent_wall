# Letterblack Workspace Governance Kit v1.1

Portable governance baseline for Brew, Access Browser Agent, LBE Wall/TUI, BirdEye, GPT-K tooling, and other Letterblack workspaces.

## What changed in v1.1

The initial version correctly blocked self-authorization but left no machine-verifiable activation mechanism. v1.1 adds detached Ed25519 operator authorization:

```text
proposed task scope
→ external operator signature
→ workspace verifies signature
→ authorized action
```

The private signing key stays outside the repository.

## Install

Extract into the repository root, then:

```powershell
.\Install-Governance.ps1
```

Then follow `docs/OPERATOR_AUTHORIZATION.md`.

## Gate commands

```powershell
node scripts/governance-check.mjs worktree
node scripts/governance-check.mjs staged
node scripts/governance-check.mjs head
node scripts/action-preflight.mjs write src/file.js
node scripts/action-preflight.mjs shell
node scripts/propose-scope.mjs
```

## Claim boundary

This kit provides signed-scope validation, Git gates, and an action-preflight surface. It is not exclusive host enforcement until every mutation-capable route is forced through the governance controller/preflight or disabled.
