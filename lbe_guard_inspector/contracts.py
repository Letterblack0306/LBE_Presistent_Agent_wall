from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

SCHEMA_FILES = {
    "task_record": "task_record.schema.json",
    "evidence_package": "evidence_package.schema.json",
    "guard_request": "guard_request.schema.json",
    "guard_result": "guard_result.schema.json",
    "rule_proposal": "rule_proposal.schema.json",
}


class ContractValidationError(ValueError):
    """Raised when a payload does not satisfy an LBE contract."""

    def __init__(self, contract_name: str, errors: list[str]) -> None:
        super().__init__(f"{contract_name} validation failed: " + "; ".join(errors))
        self.contract_name = contract_name
        self.errors = errors


def load_schema(contract_name: str) -> dict[str, Any]:
    try:
        filename = SCHEMA_FILES[contract_name]
    except KeyError as exc:
        raise KeyError(f"Unknown contract: {contract_name}") from exc

    schema_path = SCHEMA_DIR / filename
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_contract(contract_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a plain dict. Raises ContractValidationError on failure."""
    schema = load_schema(contract_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(validator.iter_errors(dict(payload)), key=lambda e: list(e.absolute_path))
    if errors:
        formatted = [_format_error(error) for error in errors]
        raise ContractValidationError(contract_name, formatted)

    return dict(payload)


def _format_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    location = path or "<root>"
    return f"{location}: {error.message}"
