# 03 — Runtime Pipeline

## States

1. `intake`
2. `workspace_resolution`
3. `knowledge_retrieval`
4. `evidence_packaging`
5. `guard_selection`
6. `guard_execution`
7. `governance_review`
8. `validation`
9. `verdict_synthesis`
10. `rule_proposal_optional`
11. `completion`

## State requirements

### Intake

Create a task record containing:

- user problem;
- target workspace, when applicable;
- expected outcome;
- requested mode;
- write permission state.

### Workspace resolution

Confirm the correct workspace identity. Stop on ambiguity.

### Knowledge retrieval

Search only for knowledge relevant to the current problem. Avoid broad corpus dumping.

### Evidence packaging

Assemble:

- indexed references;
- current workspace facts;
- validation results;
- authority metadata;
- contradictions and gaps.

### Guard selection

The reasoning agent selects guard IDs and states why each applies.

### Guard execution

Deterministic implementations return structured findings.

### Governance review

LBE Core evaluates scope, permission, capability, and proof requirements.

### Validation

Run the cheapest high-signal checks first.

### Verdict synthesis

Return a verdict that directly references guard output and evidence.

### Optional rule proposal

When a reusable workspace constraint is discovered:

- check for an equivalent rule;
- produce an exact proposed profile change;
- request approval;
- do not write automatically.

## Stop conditions

Stop with `INSUFFICIENT_EVIDENCE` when:

- the workspace is ambiguous;
- required files are missing;
- retrieved evidence conflicts without a current-source resolution;
- the selected guard cannot run;
- validation required for the verdict is unavailable.
