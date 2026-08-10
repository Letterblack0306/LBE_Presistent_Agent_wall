"""Deterministic provider-facing context assembly for R6D.

This module composes already-owned runtime inputs. It does not retrieve,
authorize, execute, validate completion, or create persistent context state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..guard_catalog import evidence_contract_for_guard


def assemble_reasoning_context(
    *,
    request_context: Sequence[Mapping[str, Any]] = (),
    approved_guard_ids: Sequence[str] = (),
    indexed_reference_evidence: Sequence[Mapping[str, Any]] = (),
) -> tuple[Mapping[str, Any], ...]:
    """Compose bounded context in deterministic authority-preserving order.

    Caller/session context is preserved first, approved guard contracts are
    injected second, and validated indexed reference evidence is appended last.
    The returned objects are copies so assembly cannot mutate source records.
    """
    assembled: list[Mapping[str, Any]] = []

    for item in request_context:
        assembled.append(_copy_mapping(item, "request_context"))

    seen_guards: set[str] = set()
    for raw_guard_id in approved_guard_ids:
        guard_id = _text(raw_guard_id, "approved_guard_id")
        if guard_id in seen_guards:
            continue
        seen_guards.add(guard_id)
        contract = evidence_contract_for_guard(guard_id)
        assembled.append(
            {
                "context_kind": "approved_guard_contract",
                "guard_id": guard_id,
                "evidence_contract": dict(contract),
            }
        )

    for item in indexed_reference_evidence:
        assembled.append(_copy_mapping(item, "indexed_reference_evidence"))

    return tuple(assembled)


def _copy_mapping(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} entries must be mappings")
    return dict(value)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
