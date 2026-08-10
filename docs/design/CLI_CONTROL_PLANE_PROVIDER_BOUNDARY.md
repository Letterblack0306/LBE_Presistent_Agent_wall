# CLI Control Plane and Provider Boundary

**Status:** Accepted architecture direction  
**Scope:** LBE Persistent Agent runtime, CLI, provider integration, governance, and future TUI/API surfaces

## Decision

LBE remains the stable workspace-side control and evidence system. The language model is a replaceable reasoning provider selected by the user per session or configuration.

The primary interaction surface should be a CLI/runtime contract. A TUI may remain as an optional operator/debug surface, and an API may expose the same runtime contract, but neither the CLI nor the TUI becomes the source of workspace truth.

```text
LBE Core / workspace authority
        |
        +-- CLI  (primary agent/control surface)
        +-- API  (integration surface)
        +-- TUI  (optional operator/debug surface)
        |
        v
Persistent session controller
        |
        +-- mode policy
        +-- workspace identity
        +-- guard/profile selection
        +-- tool permissions
        +-- evidence requirements
        +-- validation/completion requirements
        |
        v
Provider adapter
        |
        +-- OpenAI-compatible API
        +-- Claude/provider API
        +-- LM Studio
        +-- Ollama
        +-- other compatible providers
```

## Stable boundary

### LBE owns

- canonical workspace/project identity;
- session/task lifecycle and persistent runtime state;
- active workspace policy and approved rules;
- deterministic guard execution;
- evidence classification and provenance;
- tool/capability permissions;
- validation and completion proof requirements;
- authorization decisions;
- persisted verified memory and checkpoints.

### The selected LLM owns

- interpreting the user request;
- forming temporary hypotheses;
- choosing among allowed reasoning/retrieval paths;
- requesting permitted tools and evidence;
- producing plans, explanations, and proposals inside the active contract.

The model does not become the authority for workspace truth, permissions, guard verdicts, or validation merely because it is the active provider.

## Provider replacement

A provider change must not change workspace policy.

```text
same workspace
+ same session contract
+ same approved permissions
+ same guards/evidence policy
+ different provider/model
= same LBE authority boundary
```

Switching from LM Studio to Ollama, OpenAI, Claude, or another provider changes the reasoning implementation, not the workspace contract.

Provider-specific context limits, tool-call formats, capabilities, and authentication are handled by provider adapters. They must not be encoded into workspace governance rules unless the rule actually concerns that provider capability.

## Execution modes

Modes are runtime contracts, not model personalities.

### Coding mode

Purpose: build, modify, debug, and validate within an explicitly permitted workspace boundary.

Typical capabilities:

- inspect current workspace files;
- edit files allowed by active policy;
- run allowed build/test/validation tools;
- create bounded patches;
- use applicable guards and workspace rules;
- continue autonomously while the active policy authorizes the required actions.

### Audit / inspect mode

Purpose: determine current reality without repair.

Typical capabilities:

- read current workspace evidence;
- retrieve relevant reference patterns;
- run deterministic read-only guards and validation;
- return evidence-bound findings and verdicts;
- no workspace modification.

### Investigation mode

Purpose: diagnose an unknown or failed condition.

Typical capabilities:

- begin from an error, failed guard, runtime event, or evidence reference;
- expand through relevant callers, handlers, dependencies, logs, and tests;
- remain bounded to the target project unless cross-project comparison is explicitly requested;
- no automatic write authority unless the session is operating under a coding policy that grants it.

## Approval model

The runtime must distinguish **authorization** from **per-action confirmation**.

If the user has already configured a workspace/session policy that grants automatic application of existing approved rules and controlled edits, the coding runtime does not need to ask again for every matching action.

```text
user/session settings
        |
        v
LBE authorization policy
        |
        +-- existing approved rule applies? -> execute if policy permits
        +-- edit/tool class permitted?      -> execute if policy permits
        +-- validation required?            -> run automatically when permitted
        |
        v
continue session
```

Repeated confirmation is required only when the requested action exceeds the authority already granted, for example:

- writing outside the approved workspace/scope;
- using a capability class not enabled by policy;
- destructive operations not covered by the active policy;
- creating, widening, or changing a persistent rule/profile when that policy change has not already been delegated;
- encountering a genuine scope or intent conflict.

This prevents approval fatigue while preserving an enforceable authority boundary.

### Important distinction

Applying an **existing approved rule** is not the same as **creating a new persistent rule**.

A workspace may be configured to auto-apply existing approved rules and edits. New persistent constraints, global-guard promotion, or authority expansion must follow the governance policy defined for those policy-changing actions. If the user explicitly delegates that class of policy change in settings, LBE may use that delegated authority; otherwise it must request approval.

## Why this architecture

### 1. Model quality and provider choice change faster than workspace governance

Binding LBE to one model would couple stable project rules and evidence semantics to a replaceable inference engine. The provider should be swappable without rewriting the workspace control system.

### 2. Model behavior is probabilistic

Rules must not depend on a model permanently learning them. LBE injects the relevant contract and enforces capabilities at runtime, so behavior does not disappear when the context is compacted, the model changes, or the session resumes.

### 3. One model per role creates drift

Separate "audit model", "coding model", and "rule-learning model" personalities would create multiple behavioral authorities. The correct distinction is mode policy, tool permission, evidence requirements, and validation requirements.

### 4. Repeated approvals are not governance

Governance should resolve whether an operation is authorized. Once a user has deliberately granted an operation class through settings, repeatedly asking for the same permission adds friction without increasing the authority boundary. LBE should enforce the configured policy instead.

### 5. CLI-first keeps the runtime reusable

A stable CLI/session contract can be consumed by humans, scripts, Cline-like coding agents, local models, remote providers, and future UI surfaces. A TUI can display and operate the same state without becoming a second runtime implementation.

## Session contract

The long-term interface should be session-oriented rather than isolated commands.

Conceptually:

```text
lbe session create
    --workspace <project>
    --mode <coding|audit|investigation>
    --provider <provider>
    --profile <workspace-policy>

lbe session continue
lbe session inspect
lbe session evidence
lbe session validate
lbe session status
```

The exact CLI syntax is implementation detail. The architectural requirement is that provider identity, mode, workspace identity, permissions, guard profile, evidence policy, and lifecycle state remain explicit session data.

## Non-goals

This decision does not authorize:

- model-generated workspace truth;
- passive learning of permanent rules from conversations;
- bypassing deterministic guards or validation;
- treating the CLI itself as an autonomous authority;
- provider-specific rules silently replacing workspace policy;
- unrestricted repair in audit mode.

## Invariant

```text
Provider reasons.
Runtime orchestrates.
Guards detect.
Workspace evidence supplies current facts.
LBE policy authorizes.
Validation proves.
User-configured authority determines when confirmation is required.
```

This boundary should be preserved when implementing persistent runtime R3-R7, provider adapters, CLI commands, API endpoints, or any future TUI.