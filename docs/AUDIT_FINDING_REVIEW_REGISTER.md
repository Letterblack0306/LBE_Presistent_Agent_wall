# Audit Finding Review Register

## Purpose

Audit snapshots are historical investigation records. They are not workspace truth and must not directly create implementation tasks, guards, or memory entries.

A finding moves through this lifecycle:

```
Audit snapshot
      ↓
Categorization
      ↓
Current workspace verification
      ↓
Review outcome
      ↓
Validated memory / enhancement backlog (only when proven)
```

## Finding States

| State | Meaning |
|---|---|
| pending_review | Observed in an audit snapshot and awaiting verification |
| confirmed | Verified against current workspace evidence |
| false_positive | Audit observation was incorrect |
| stale | Was true previously but no longer applies |
| resolved | Was confirmed and later fixed |
| enhancement | Improvement opportunity, not a defect |
| insufficient_evidence | Cannot be confirmed or rejected yet |

## Finding Record

Each finding should contain:

```json
{
  "finding_id": "AUDIT-001",
  "source_snapshot": "session-or-audit-id",
  "model_used": "model-name",
  "category": "architecture_gap",
  "description": "Observed gap description",
  "observed_at": "timestamp",
  "status": "pending_review",
  "verification_required": true,
  "evidence": []
}
```

## Model Selection Boundary

The reasoning model is an investigation assistant, not the source of truth.

Model selection should balance:

- reasoning capability for broad workspace investigation;
- coding understanding for implementation-related audits;
- context efficiency;
- local/runtime cost.

DeepSeek coding models remain valid options for implementation-heavy analysis because of their coding capability. However, audits should not depend only on the largest coding model.

Preferred future architecture:

```
Lightweight model
        ↓
Problem classification
Guard catalog retrieval
Candidate rule discovery
        ↓
Reasoning model (when required)
Complex investigation
Architecture comparison
        ↓
Deterministic guards
Evidence validation
Final verdict
```

The model should not be required to remember every rule. Rule discovery must expand through registered guards and relationships.

## Guard Discovery Requirement

Before applying a guard, the system should identify:

```
Problem domain
        ↓
Possible affected areas
        ↓
Related guards
        ↓
Required evidence
        ↓
Selected inspection path
```

This prevents narrow-context failures where a model selects one visible rule and misses related rules.

Example:

```
callback failure
        ↓
Possible checks:
- callback contract
- module registration
- bridge communication
- runtime ownership
- dependency compatibility
```

The final selected guard must still be evidence-backed.

## Review Rules

- Audit snapshots preserve what was observed at the time.
- Current workspace inspection is required before declaring truth.
- Reference knowledge cannot become workspace evidence.
- Findings cannot automatically create guards or repairs.
- Only validated evidence may become durable memory.
- Model output is a hypothesis source, not a compliance verdict.

## Categories

- blocker
- architecture_gap
- feature_gap
- governance_gap
- enhancement
- investigation_item

## Review Comparison

During later reviews compare:

```
Previous snapshot
        +
Current source/runtime evidence
        ↓
Confirmed / False / Changed
```

This keeps historical audits useful without allowing stale observations to override current workspace reality.
