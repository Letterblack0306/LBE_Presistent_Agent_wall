from __future__ import annotations

import json
from pathlib import Path

from lbe_guard_inspector import product_entry


def _write_registry(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "integrations": [
                    {
                        "integration_id": "mcp-files",
                        "adapter_id": "mcp.files.local",
                        "kind": "mcp",
                        "tool_id": "mcp.files.read",
                        "description": "Local MCP file inspection",
                        "enabled": True,
                        "credential_ref": None,
                        "required_arguments": ["query"],
                        "optional_arguments": [],
                        "access_class": "read",
                        "network_behavior": "none",
                        "risk_class": "low",
                        "timeout_seconds": 30.0,
                        "retry_policy": "none",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_capabilities_list_projects_registry_without_execution(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    _write_registry(registry)
    code = product_entry.main(["capabilities", "list", "--registry", str(registry)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "capabilities.list"
    assert payload["count"] == 1
    assert payload["execution_attempted"] is False
    assert payload["integrations"][0]["integration_id"] == "mcp-files"
    assert payload["integrations"][0]["availability"] == "UNAVAILABLE"
    assert "credential_ref" not in payload["integrations"][0]


def test_capabilities_validate_accepts_valid_registry(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    _write_registry(registry)
    code = product_entry.main(["--format", "json", "capabilities", "validate", "--registry", str(registry)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "capabilities.validate"
    assert payload["schema_version"] == 1
    assert payload["execution_attempted"] is False


def test_capabilities_validate_fails_closed_on_plaintext_secret(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "integrations": [
                    {
                        "integration_id": "bad",
                        "adapter_id": "hosted.bad",
                        "kind": "hosted_service",
                        "tool_id": "hosted.bad.query",
                        "description": "bad",
                        "network_behavior": "required",
                        "api_key": "secret",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    code = product_entry.main(["capabilities", "validate", "--registry", str(registry)])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "plaintext credential field is forbidden" in payload["message"]


def test_legacy_cli_commands_still_delegate(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(product_entry._cli, "main", lambda values: calls.append(list(values)) or 17)
    code = product_entry.main(["provider", "list"])
    assert code == 17
    assert calls == [["provider", "list"]]


def test_capabilities_install_enable_disable_and_remove(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    definition = {
        "integration_id": "skill-review",
        "adapter_id": "skill.review",
        "kind": "skill",
        "tool_id": "skill.review.invoke",
        "description": "Review current workspace evidence",
        "enabled": True,
        "required_arguments": ["query"],
        "optional_arguments": [],
        "access_class": "read",
        "network_behavior": "none",
        "risk_class": "low",
        "timeout_seconds": 30.0,
        "retry_policy": "none",
    }

    code = product_entry.main([
        "capabilities",
        "install",
        "--registry",
        str(registry),
        "--definition",
        json.dumps(definition),
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "capabilities.install"
    assert payload["changed_integration_id"] == "skill-review"
    assert payload["integrations"][0]["kind"] == "skill"

    code = product_entry.main([
        "capabilities", "disable", "--registry", str(registry),
        "--integration-id", "skill-review",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["integrations"][0]["enabled"] is False
    assert payload["integrations"][0]["availability"] == "DISABLED"

    code = product_entry.main([
        "capabilities", "enable", "--registry", str(registry),
        "--integration-id", "skill-review",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["integrations"][0]["enabled"] is True

    code = product_entry.main([
        "capabilities", "remove", "--registry", str(registry),
        "--integration-id", "skill-review",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 0


def test_capabilities_install_supports_definition_file(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    definition_path = tmp_path / "connector.json"
    definition_path.write_text(json.dumps({
        "integration_id": "connector-demo",
        "adapter_id": "connector.demo",
        "kind": "connector",
        "tool_id": "connector.demo.query",
        "description": "Demo connector",
    }), encoding="utf-8")

    code = product_entry.main([
        "capabilities", "install", "--registry", str(registry),
        "--definition", "@" + str(definition_path),
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["integrations"][0]["kind"] == "connector"


def test_capabilities_management_fails_closed_for_missing_identity(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "capabilities.json"
    code = product_entry.main(["capabilities", "disable", "--registry", str(registry)])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "--integration-id" in payload["message"]
