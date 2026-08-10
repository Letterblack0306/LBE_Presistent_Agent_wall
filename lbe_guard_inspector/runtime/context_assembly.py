"""Deterministic provider-facing context assembly for R6D.

This module composes already-owned runtime inputs. It does not retrieve,
authorize, execute, validate completion, or create persistent context state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def assemble_reasoning_context(
    *,
    request_context: Sequence[Mapping[str, Any]] = (),
    indexed_reference_evidence: Sequence[Mapping[str, Any]] = (),
) -> tuple[Mapping[str, Any], ...]:
    """Compose bounded context in deterministic authority-preserving order.

    Caller/session context is preserved first and validated indexed reference
    evidence is appended after it. Guard relevance remains in the existing
    ``ReasoningRequest.approved_guard_ids`` field rather than being duplicated
    into reference context. Returned entries are shallow copies so assembly
    cannot mutate source records.
    """
    assembled: list[Mapping[str, Any]] = []

    for item in request_context:
        assembled.append(_copy_mapping(item, "request_context"))

    for item in indexed_reference_evidence:
        assembled.append(_copy_mapping(item, "indexed_reference_evidence"))

    return tuple(assembled)


def _copy_mapping(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} entries must be mappings")
    return dict(value)
