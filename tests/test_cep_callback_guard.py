from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import audit_controller


def _load_module():
    path = Path(__file__).resolve().parents[1] / "rules" / "cep_callback.py"
    spec = importlib.util.spec_from_file_location("test_cep_callback_rule_pack", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _context():
    return SimpleNamespace(roots=())


def _search_result(path: str = "workspace/src/panel.js") -> dict:
    return {
        "outcome": "matches_found",
        "searched_roots": ["workspace"],
        "results": [{"path": path, "score": 100}],
    }


def test_extract_evalscript_multiline_call_is_deterministic() -> None:
    module = _load_module()
    content = """const x = 1;
cs.evalScript(
  payload,
  function (result) { console.log(result); }
);
"""
    calls = module._extract_evalscript_calls(content)
    assert len(calls) == 1
    assert calls[0]["line_start"] == 2
    assert calls[0]["arguments"][0] == "payload"
    assert calls[0]["arguments"][1].startswith("function")


def test_definite_literal_callback_fails(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "search_workspace", lambda *args, **kwargs: _search_result())
    monkeypatch.setattr(
        module,
        "inspect_file",
        lambda *args, **kwargs: {
            "content": 'cs.evalScript(payload, "not-a-function");',
            "sha256": "abc123",
        },
    )

    result = module.rule_cep_callback_contract(_context(), {"roots": ["workspace"]})

    assert result.status == "failed"
    assert result.rule_id == "cep.callback_contract"
    finding = result.evidence["invalid_callbacks"][0]
    assert finding["classification"] == "definitely_invalid"
    assert finding["path"] == "workspace/src/panel.js"
    assert finding["hash"] == "abc123"
    assert finding["line_start"] == 1
    assert result.evidence["read_only"] is True
    assert result.evidence["bounded"] is True


def test_inline_function_callback_passes(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "search_workspace", lambda *args, **kwargs: _search_result())
    monkeypatch.setattr(
        module,
        "inspect_file",
        lambda *args, **kwargs: {
            "content": "cs.evalScript(payload, (result) => console.log(result));",
            "sha256": "def456",
        },
    )

    result = module.rule_cep_callback_contract(_context(), {"roots": ["workspace"]})

    assert result.status == "passed"
    assert result.evidence["invalid_callbacks"] == []
    assert result.evidence["unresolved_callbacks"] == []
    assert result.evidence["valid_or_omitted_callbacks"][0]["classification"] == "function"


def test_identifier_callback_is_blocked_not_guessed(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "search_workspace", lambda *args, **kwargs: _search_result())
    monkeypatch.setattr(
        module,
        "inspect_file",
        lambda *args, **kwargs: {
            "content": "cs.evalScript(payload, callbackValue);",
            "sha256": "789abc",
        },
    )

    result = module.rule_cep_callback_contract(_context(), {"roots": ["workspace"]})

    assert result.status == "blocked"
    assert result.evidence["invalid_callbacks"] == []
    unresolved = result.evidence["unresolved_callbacks"][0]
    assert unresolved["classification"] == "unresolved"
    assert unresolved["callback_expression"] == "callbackValue"


def test_missing_evalscript_is_not_applicable(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "search_workspace",
        lambda *args, **kwargs: {
            "outcome": "no_matches",
            "searched_roots": ["workspace"],
            "results": [],
        },
    )

    result = module.rule_cep_callback_contract(_context(), {"roots": ["workspace"]})

    assert result.status == "not_applicable"


def test_registered_rule_executes_through_audit_controller(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "search_workspace", lambda *args, **kwargs: _search_result())
    monkeypatch.setattr(
        module,
        "inspect_file",
        lambda *args, **kwargs: {
            "content": "cs.evalScript(payload, null);",
            "sha256": "feed00",
        },
    )
    audit_controller.register_rule(
        "cep_callback",
        module.RULE_ID,
        lambda ctx, params: module.rule_cep_callback_contract(ctx, params),
    )

    result = audit_controller.run_rule(
        "cep_callback",
        module.RULE_ID,
        _context(),
        {"roots": ["workspace"]},
    )

    assert result.status == "failed"
    assert result.evidence["invalid_callbacks"][0]["callback_expression"] == "null"
