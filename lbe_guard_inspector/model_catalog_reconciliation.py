"""Reconcile a persisted session model against the provider's live catalog.

This module never substitutes a model. It classifies the persisted model so
that an absent one becomes an explicit, evidence-bound condition rather than a
silent divergence.

Design authority: the R7 acceptance record, Final Architectural Invariants,
requires that provider failure be explicit and that "the silent substitution
of models or providers is strictly forbidden." A fallback list would satisfy
that only on paper: the substituted model was never authorized, and the
substitution would be recorded as if it had been chosen.

The durable thing is the session selection. Whether a third party still serves
it is not durable. When the two disagree, the correct outcome is a
deterministic verdict the caller can surface, not a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

ModelReconciliation = Literal[
    "live_discovered",
    "absent_from_live_catalog",
    "catalog_unavailable",
]


@dataclass(frozen=True)
class ModelCatalogReconciliation:
    """Bounded verdict for one persisted model against one observed catalog."""

    persisted_model: str
    effective_model: str
    reconciliation: ModelReconciliation
    catalog_source: Literal["live", "unavailable"]
    catalog_size: int

    @property
    def is_divergent(self) -> bool:
        """True when the persisted model is known not to be served."""
        return self.reconciliation == "absent_from_live_catalog"


def reconcile_persisted_model(
    persisted_model: str, live_catalog: Iterable[str] | None
) -> ModelCatalogReconciliation:
    """Classify ``persisted_model`` against an observed live catalog.

    ``live_catalog`` is ``None`` when no catalog could be observed. That is
    deliberately not treated as absence: an unreachable or un-probed provider
    is unknown, and unknown must not be reported as a vanished model.
    """
    if not isinstance(persisted_model, str) or not persisted_model.strip():
        raise ValueError("persisted_model must be a non-empty string")
    model = persisted_model.strip()

    if live_catalog is None:
        # Unknown, not absent. Keep the persisted selection and say so.
        return ModelCatalogReconciliation(
            persisted_model=model,
            effective_model=model,
            reconciliation="catalog_unavailable",
            catalog_source="unavailable",
            catalog_size=0,
        )

    observed = tuple(
        sorted(
            {e.strip() for e in live_catalog if isinstance(e, str) and e.strip()}
        )
    )
    if model in observed:
        return ModelCatalogReconciliation(
            persisted_model=model,
            effective_model=model,
            reconciliation="live_discovered",
            catalog_source="live",
            catalog_size=len(observed),
        )

    # Known divergence. Report it; do not pick a replacement. Choosing here
    # would authorize a model no session, policy, or operator ever approved.
    return ModelCatalogReconciliation(
        persisted_model=model,
        effective_model=model,
        reconciliation="absent_from_live_catalog",
        catalog_source="live",
        catalog_size=len(observed),
    )
