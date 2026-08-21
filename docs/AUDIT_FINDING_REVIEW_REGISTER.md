> **Governance Notice:** This workspace operates under a strict **no destructive action** policy. No file modification, code generation, rule creation, memory promotion, or workspace mutation is permitted without explicit user authorization. All operations are read-only unless explicitly approved. Violations must be reported as findings, not silently corrected.
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

# Mode Controller Architecture

The system must separate audit behavior from development behavior. The same reasoning capability is useful in both modes, but the authority boundaries are different.

```
User Request
      ↓
Mode Detector
      ↓
 ┌───────────────┬────────────────┐
 │               │                │
Audit Mode       Development Mode
 │               │
Read-only        Read/write
Existing guards  Discover patterns
Evidence only    Create candidates
Findings         Validate changes
```
This architecture effectively solves the core failure mode of workspace-level analysis: **mixing discovery with execution.**

By formalizing the separation between **Audit Mode** and **Development Mode**, you establish a firm operational boundary. Audit Mode operates strictly as a deterministic diagnostic pass (measuring reality against proven rules), while Development Mode remains the generative, creative space for problem-solving and rule proposal.

### Key Strengths of This Final Model

1. **Elimination of "Premature Refactoring":** In Audit Mode, the agent is constrained from attempting quick code edits or inventing new speculative rules on the fly. It forces every observation into a review queue (`AUDIT_FINDING_REVIEW_REGISTER.md`) as a candidate finding rather than an immediate task.
2. **Context Window Insurance:** The **Guard Knowledge Graph / Rule Discovery Flow** ensures that lightweight models don't drop related rules due to context limits. The system uses deterministic guard retrieval to expand candidate rules based on failure domain, rather than relying on LLM memory recall.
3. **Evidence-Driven Decision Tree:** Requiring an explicit `INSUFFICIENT_EVIDENCE` state prevents hallucinated conclusions when data is missing, upholding the LBE evidence boundary.

---

### Operating Lifecycle Overview

```
                      ┌────────────────────────┐
                      │    USER REQUEST        │
                      └───────────┬────────────┘
                                  │
                           Mode Detection
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│       AUDIT MODE        │               │    DEVELOPMENT MODE     │
├─────────────────────────┤               ├─────────────────────────┤
│ • Read-Only             │               │ • Read / Write          │
│ • Existing Guards Only  │               │ • Discover Patterns     │
│ • Evidence Collection   │               │ • Propose & Test Rules  │
│ • Findings Output       │               │ • Code Modifications    │
└────────┬────────────────┘               └────────┬────────────────┘
         │                                         │
         ▼                                         ▼
Finding Review Register                    Candidate Rules / Code
(Historical Baseline)                      (Validated Memory)

```

The system now has a controlled, verifiable pipeline that honors historical context without letting speculative observations disrupt the workspace state.
> **Note — Target Architecture:** The Operating Lifecycle Overview above describes the **target architecture**. The current implementation (see workspace structure below) has the building blocks for the audit side but does not yet have an explicit Mode Detector, a formal Development Mode pipeline, or automated Finding Review Register population. No structural changes to the codebase are required — the existing modular layout supports this evolution.

## Audit Mode

Purpose:

> Measure current workspace reality against existing guards.

Rules:

```json
{
  "mode": "audit",
  "capabilities": [
    "read workspace",
    "select existing guards",
    "collect evidence",
    "produce findings"
  ],
  "restrictions": [
    "no file modification",
    "no new guard creation",
    "no unsupported assumptions",
    "stop on insufficient evidence"
  ]
}
```

Workflow:

```
Audit request
      ↓
Workspace identity
      ↓
Failure domain detection
      ↓
Guard retrieval
      ↓
Evidence requirements
      ↓
Bounded inspection
      ↓
Finding output
      ↓
Stop
```

Audit mode does not allow:

- broad uncontrolled exploration;
- creating rules from observations;
- converting model reasoning into truth;
- proposing code changes without evidence.

## Development Mode

Purpose:

> Explore, implement, discover patterns, and create validated improvements.

Rules:

```json
{
  "mode": "development",
  "capabilities": [
    "read workspace",
    "modify files with approval",
    "discover patterns",
    "create candidate rules"
  ],
  "requirements": [
    "provenance tracking",
    "validation before promotion",
    "evidence-backed decisions"
  ]
}
```

Workflow:

```
Development request
      ↓
Workspace identity
      ↓
Explore problem
      ↓
Discover patterns
      ↓
Create candidate rule
      ↓
Validate
      ↓
Promote only if proven
```

## Mode Detection

Mode detection should be explicit and conservative.

Examples:

| Request | Mode |
|---|---|
| audit workspace for feature gaps | audit |
| review module ownership | audit |
| check contract validity | audit |
| fix callback registration bug | development |
| implement new feature | development |
| ambiguous request | ask user |

Keyword matching may assist detection, but ambiguous requests should not silently choose a mutation-capable mode.

## Model Selection Boundary

The reasoning model is an investigation assistant, not the source of truth.

Model selection should balance:

- reasoning capability;
- coding understanding;
- context efficiency;
- runtime cost.

DeepSeek coding models remain valid options for implementation-heavy analysis because of their coding capability. However, audits should not depend only on the largest coding model.

Preferred architecture:

```
Lightweight model
        ↓
Problem classification
Guard catalog retrieval
        ↓
Reasoning model (when required)
Complex investigation
        ↓
Deterministic guards
Evidence validation
Final verdict
```

The model should not remember every rule. Registered guard relationships must expand the investigation boundary.

## Guard Discovery Requirement

Before applying a guard:

```
Problem domain
        ↓
Affected areas
        ↓
Related guards
        ↓
Required evidence
        ↓
Inspection path
```

This prevents narrow-context failures where a model selects one visible rule and misses related checks.

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

## Current CLI product findings — 2026-08-21

These entries are based on current source inspection and isolated installed-runtime probes. They
are not created from external-reference material alone.

| Finding ID | Category | Status | Verified finding | Required review outcome |
|---|---|---|---|---|
| CLI-001 | blocker | resolved | The legacy Node-worker package dependency failure was removed by the provider-neutral governed coding loop in `67ba749`; clean staged-wheel and isolated installed R7 proof reached provider, governed receipt, and deterministic completion. | Retain clean-staging/fresh-clone package proof because ignored local build residue can affect a source-root build. |
| CLI-002 | architecture_gap | confirmed | The governed coding registry remains deliberately bounded (`workspace.read` and create-only candidate text); it is not yet a complete terminal-agent capability product. | Expand only through existing R6C/R6E/ToolReceipt/completion owners, with an explicit authorization contract per new capability. |
| CLI-003 | feature_gap | confirmed | The committed Textual TUI is a transcript/composer projection. It does not render governed tool cells, approval previews/actions, diffs, evidence, or validated completion as first-class terminal surfaces. | Build the terminal workspace over persisted runtime events; do not create a parallel executor or a display-only mock. |
| CLI-004 | feature_gap | confirmed | Starting or resuming a TUI requires a pre-existing `--session-id`; provider selection/health/model configuration are separate commands/files, not an integrated terminal workflow. | Add a single truthful launcher/resume flow with provider/model state, health result, and explicit unavailable/error states. |
| CLI-005 | investigation_item | insufficient_evidence | Current uncommitted coding-TUI routing has focused coverage (24 passed) but no installed interactive provider session has proved receipt/diff/approval rendering. | Run an installed terminal acceptance flow using a local test provider and retain the persisted event evidence. |

Reference context and the detailed future-work sequence are in
`docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md`.

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
## Current Workspace Structure

The workspace is organized as follows — all components are modular; adding or removing a module does not break the rest:

```
/
├── agent.py                         # Core runtime: Context, Governance, search, inspect
├── audit_controller.py              # Rule registry + resolve_rule + run_rule + audit reporting
├── server.py                        # Local HTTP entry point
├── migrate_legacy_state.py          # Standalone migration utility
├── governance.json                  # Allowed-read / forbidden-glob governance config
├── lbe_guard_inspector/             # Guard inspector framework
│   ├── authority_ownership*.py      # Authority ownership contracts + inspector + extractor (3 files)
│   ├── reasoning_*.py               # Reasoning provider, contracts, config, runtime (4 files)
│   ├── memory/                      # SQLite-backed validated workspace memory (7 files)
│   ├── module_registry/             # Module registry models + store + watcher (4 files)
│   ├── callback_vertical_slice.py   # Callback inspection vertical slice
│   ├── module_registry_vertical_slice.py
│   ├── contracts.py / evidence_service.py / guard_*.py
│   ├── invocation_adapter.py / project_*.py
│   ├── registry_inspection.py / request_controller.py
│   ├── rule_gatekeeper.py / runtime_*.py
│   ├── session_memory_runtime.py / workspace_identity.py
│   └── __init__.py
├── rules/                           # Deterministic rule packs (4 files)
│   ├── generic.py                   # Foundation guards: index_present, forbidden_roots
│   ├── cep.py                       # CEP guards: manifest, host, menu, debug, zip, symlink
│   ├── cep_callback.py              # Callback contract guard
│   └── module_registry.py           # Module registry loaded-module guard
├── schemas/                         # JSON validation schemas
├── tests/                           # Test suite mirroring source structure
├── tools/                           # Standalone utility scripts
├── docs/                            # Documentation
├── state/                           # Generated runtime state (git-ignored)
├── pyproject.toml
├── requirements.txt
└── MANIFEST.json
```

All local imports flow one direction: `core (agent.py, audit_controller.py)` → `lbe_guard_inspector/` → `rules/`. No circular imports exist.
