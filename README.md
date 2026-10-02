# Letterblack Workspace Governance Kit v1.1

Portable governance baseline for Brew, Access Browser Agent, LBE Wall/TUI, BirdEye, GPT-K tooling, and other Letterblack workspaces.

## Authorization model

Governance uses an active locked task scope plus file/action allowlists. External operator signatures, signing keys, detached signatures, and signing ceremonies are not part of the current workspace authorization path.

```text
user-authorized task
→ active locked scope
→ file/action preflight
→ required validation
→ commit/push when allowed
```

## Install

Extract into the repository root, then:

```powershell
.\Install-Governance.ps1
```

Then review `AGENTS.md`, `docs/GOVERNANCE_RULES.md`, and the active task scope.

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

This kit provides active-scope validation, Git gates, and an action-preflight surface. It is not exclusive host enforcement until every mutation-capable route is forced through the governance controller/preflight or disabled.

## MCP Usage Directive (Pre-Action Requirement)

**Before taking any action**, agents MUST consult the MCP (Memory, Capabilities, and Planning) system to:
1. **Check historical context**: Use `mcp-local-birdeye__memory_search` to find relevant previous plans, discussions, and actions
2. **Discover applicable skills**: Use `mcp-local-birdeye__skills` to identify relevant capabilities for the task
3. **Verify current state**: Use workspace inspection tools to confirm alignment with active implementation gates
4. **Avoid repeating solved problems**: Leverage derived memory and historical evidence to build on prior work

Failure to consult MCP before action may result in:
- Repeating previously solved challenges
- Misalignment with current governance gates
- Inefficient use of agent capabilities
- Potential violation of workspace integrity constraints

The MCP system provides the authoritative context for informed agent operation within this governed workspace.

## Governance Intent Clarification

While governance rules and blockers are designed to maintain project direction and prevent unauthorized mutations, they are not intended to block all enhancements or improvements. The purpose of governance is to:

1. **Maintain directional integrity**: Ensure changes align with the project's approved scope and vision
2. **Prevent uncontrolled divergence**: Avoid drift from authorized implementation paths
3. **Enable safe experimentation**: Allow enhancements within governed boundaries when properly scoped
4. **Preserve evidence-based decisions**: Ensure modifications are grounded in verified requirements

**Important**: A governance blocker indicating "NO_ACTIVE_SCOPE" or similar does not mean an enhancement is forbidden—it means the enhancement requires proper scoping and authorization through the established channels. Agents should:
- View blockers as requests for proper scoping, not permanent rejections
- Use the blocker guidance to prepare a proper scope proposal
- Update the active scope only to match explicit user-authorized work
- Remember that governance enables safe progress, not prevents it

The system is designed to be enhancable while maintaining auditability and directional consistency.
