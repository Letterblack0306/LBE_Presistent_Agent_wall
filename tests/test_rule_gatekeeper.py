from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from lbe_guard_inspector.rule_gatekeeper import (
    CatalogEntry,
    RuleGatekeeper,
    STATUS_ALREADY_COVERED,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_PROPOSAL_READY,
)

TRIGGER = (
    "No rule validates that all Python packages in lbe_guard_inspector "
    "have proper __init__.py files."
)
RULE_ID = "custom.rule_validates_python_packages"
FIXED_TIME = datetime(2026, 7, 26, 0, 0, tzinfo=timezone.utc)


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    package = root / "lbe_guard_inspector"
    profile_dir = root / "profiles"
    package.mkdir(parents=True)
    profile_dir.mkdir(parents=True)
    (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (profile_dir / "workspace.policy.json").write_text(
        json.dumps({"workspace_id": "agents-memory-tool", "rules": {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _gatekeeper(catalog=()):
    return RuleGatekeeper(
        catalog_provider=lambda _root: list(catalog),
        clock=lambda: FIXED_TIME,
    )


def _propose(gatekeeper: RuleGatekeeper, root: Path, **overrides):
    kwargs = {
        "workspace_root": root,
        "workspace_id": "agents-memory-tool",
        "trigger": TRIGGER,
        "rule_id": RULE_ID,
        "pack_id": "agents-memory-tool",
        "package_roots": ["lbe_guard_inspector"],
        "target_profile_path": "profiles/workspace.policy.json",
    }
    kwargs.update(overrides)
    return gatekeeper.propose_rule(**kwargs)


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_equivalent_rule_returns_already_covered(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    gatekeeper = _gatekeeper(
        [CatalogEntry("agents-memory-tool", RULE_ID, trigger=TRIGGER)]
    )
    result = gatekeeper.inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["status"] == STATUS_ALREADY_COVERED
    assert result["proposal"] is None


def test_conflicting_rule_returns_conflict(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    gatekeeper = _gatekeeper(
        [
            CatalogEntry(
                "agents-memory-tool",
                "custom.allow_python_packages_without_init",
                trigger="Allow Python packages without init files.",
            )
        ]
    )
    result = gatekeeper.inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger="Python packages must require init files.",
        rule_id="custom.require_python_package_init",
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["status"] == STATUS_CONFLICT
    assert result["contradiction_result"]["rule_id"] == "custom.allow_python_packages_without_init"


def test_missing_protection_is_proposal_ready(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["status"] == STATUS_PROPOSAL_READY
    assert result["scope"] == ["lbe_guard_inspector/__init__.py"]
    assert result["proposal"] is None


def test_no_python_package_evidence_is_insufficient(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text(TRIGGER, encoding="utf-8")
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert result["package_evidence"] == []


def test_scope_contains_only_expected_package_paths(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    (root / "config.json").write_text(TRIGGER, encoding="utf-8")
    (root / "BASELINE_VALIDATION.md").write_text(TRIGGER, encoding="utf-8")
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["scope"] == ["lbe_guard_inspector/__init__.py"]
    assert all("config.json" not in item for item in result["scope"])
    assert all("BASELINE" not in item for item in result["scope"])


def test_reference_evidence_stays_separate_from_workspace_scope(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
        reference_evidence_refs=["reference:example:python-package-rule"],
    )
    assert result["reference_evidence_refs"] == ["reference:example:python-package-rule"]
    assert result["scope"] == ["lbe_guard_inspector/__init__.py"]


def test_valid_namespace_package_exception(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    namespace = root / "lbe_guard_inspector" / "namespace_pkg"
    namespace.mkdir()
    (namespace / "plugin.py").write_text("PLUGIN = True\n", encoding="utf-8")
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
        namespace_packages=["lbe_guard_inspector/namespace_pkg"],
    )
    assert "lbe_guard_inspector/namespace_pkg/__init__.py" not in result["scope"]
    ns = next(item for item in result["package_evidence"] if item["package_path"] == "lbe_guard_inspector/namespace_pkg")
    assert ns["namespace_package"] is True


def test_nested_python_packages_are_scoped(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    nested = root / "lbe_guard_inspector" / "nested"
    nested.mkdir()
    (nested / "worker.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["scope"] == [
        "lbe_guard_inspector/__init__.py",
        "lbe_guard_inspector/nested/__init__.py",
    ]


def test_generated_vendor_archive_and_tests_are_excluded(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    for relative in (
        "generated/fake.py",
        "vendor/fake.py",
        "archive/fake.py",
        "tests/fake.py",
        "lbe_guard_inspector/__pycache__/fake.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("VALUE = 1\n", encoding="utf-8")
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    assert result["scope"] == ["lbe_guard_inspector/__init__.py"]


def test_deterministic_proposal_id(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    first = _propose(_gatekeeper(), root)
    second = _propose(_gatekeeper(), root)
    assert first["status"] == STATUS_PROPOSAL_READY
    assert first["proposal"]["proposal_id"] == second["proposal"]["proposal_id"]
    assert first["proposal"]["proposal_id"].startswith("prop-")


def test_proposal_contains_complete_governance_fields(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = _propose(_gatekeeper(), root, exceptions=["legacy_namespace"])
    proposal = result["proposal"]
    required = {
        "evidence_refs",
        "exceptions",
        "validation_plan",
        "rollback_plan",
        "provenance",
        "target_profile_path",
        "diff",
        "equivalent_rule_result",
        "contradiction_result",
    }
    assert required <= proposal.keys()
    assert proposal["target_profile_path"] == "profiles/workspace.policy.json"
    assert proposal["approval_required"] is True
    assert proposal["provenance"]["mode"] == "propose-rule"
    assert "custom.rule_validates_python_packages" in proposal["diff"]


def test_unresolved_profile_path_is_insufficient(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = _propose(_gatekeeper(), root, target_profile_path=None)
    assert result["status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert "will not invent" in result["missing_evidence"][0]


def test_inspect_mode_is_runtime_read_only(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    before = _snapshot(root)
    result = _gatekeeper().inspect(
        workspace_root=root,
        workspace_id="agents-memory-tool",
        trigger=TRIGGER,
        rule_id=RULE_ID,
        pack_id="agents-memory-tool",
        package_roots=["lbe_guard_inspector"],
    )
    after = _snapshot(root)
    assert before == after
    assert result["mutation_report"]["runtime_mutations_performed"] is False


def test_propose_rule_mode_is_runtime_read_only(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    before = _snapshot(root)
    result = _propose(_gatekeeper(), root)
    after = _snapshot(root)
    assert before == after
    assert result["status"] == STATUS_PROPOSAL_READY
    assert result["mutation_report"] == {
        "runtime_mutations_performed": False,
        "target_workspace_changed": False,
        "target_profile_changed": False,
        "rule_registry_changed": False,
        "index_changed": False,
    }
