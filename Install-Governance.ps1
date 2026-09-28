$ErrorActionPreference = 'Stop'
Write-Host 'Letterblack Workspace Governance Kit v1'
Write-Host 'Installing repository Git hooks...'
node scripts/install-governance.mjs
Write-Host ''
Write-Host 'Running worktree governance check...'
node scripts/governance-check.mjs worktree
Write-Host ''
Write-Host 'Read docs/GOVERNANCE_RULES.md before enabling an implementation scope.'
