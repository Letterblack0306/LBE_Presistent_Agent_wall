"""Live CLI boundary: wildcard scopes must not grant protected governance writes."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "action-preflight.mjs"

def preflight(action: str, target: str):
    return subprocess.run(
        ["node", str(PREFLIGHT), action, target],
        cwd=ROOT, capture_output=True, text=True, timeout=20,
    )

def test_protected_governance_scope_does_not_self_authorize():
    for target in (".governance/task-scope.json", ".lbe/governance/implementation-gates.json", "scripts/action-preflight.mjs"):
        result = preflight("write", target)
        assert result.returncode != 0, (target, result.stdout)
        assert "PROTECTED_PATH_REQUIRES_SEPARATE_AUTHORITY" in result.stderr

def test_ordinary_scoped_maintenance_remains_allowed():
    result = preflight("write", "tools/lbe_product_integration.ps1")
    assert result.returncode == 0, result.stderr

def test_protected_policy_can_be_read():
    result = preflight("read", ".governance/workspace-policy.json")
    assert result.returncode == 0, result.stderr