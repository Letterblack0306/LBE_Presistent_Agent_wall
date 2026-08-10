# Runtime Policy Production Wiring Evidence

Updated: 2026-08-10
Status: Documentation-only architecture checkpoint

## Finding

Current evidence shows that the typed R6B mode engine, R6C authorization resolver, and R6E governed tool orchestration exist and are tested, but are not yet composed into the normal agent/CLI request path.

Observed production searches:

```text
MODE_HIT_COUNT=0
AUTH_HIT_COUNT=0
```

The CLI currently persists `mode`, `active_profile_id`, `permission_policy_id`, and `evidence_policy_id` as session references. `GovernedAgentGateway` verifies request identity against the persisted session and routes reasoning, but current production evidence does not show the gateway resolving effective R6B policy or exposing a real R6B `ModeDecision` to R6C/R6E.

Therefore C0 must be broader than merely calling `resolve_mode()`. It must establish the smallest authoritative runtime-policy composition path using the owners already implemented.

## Research discipline

This decision follows the project research sequence:

1. GPT-Knowledge architecture references;
2. live GitHub repository state;
3. local Git/BirdEye diff evidence;
4. comparable live workflow/runtime patterns;
5. architecture/roadmap update before code.

This is informative engineering discipline, not a hard runtime blocker.

## Internal architecture evidence

### GPT-Knowledge

Relevant references:

- `ai-agents/lbe-cli-control-plane-provider-boundary.md`
- `ai-agents/reference-derived-agent-architecture.md`
- `ai-agents/studies/lbe-completion-contract-and-validation-evidence-study.md`

Common boundary:

```text
provider/model reasons
control plane owns session + policy + permissions
execution surfaces request capabilities
runtime resolves authority
validation proves
completion is separate from model opinion
```

### R6B

`runtime/mode_controller.py` already defines:

- `ModeRequest`
- `ModeDecision`
- `resolve_mode()`
- deterministic allowed behaviors/capabilities.

Its typed policy inputs are explicit:

```text
permission     = read_only | write_allowed | audit_only | elevated
runtime_policy = audit | development | strict | permissive
```

R6B does not grant these values; it consumes them. Current production inspection found no normal-path consumer supplying them.

### R6C

`runtime/authorization_resolver.py` already accepts a `ModeDecision` and returns deterministic `ALLOW`, `DENY`, or `ESCALATE`.

But current production inspection found no external normal-path callers; it is currently consumed by the standalone R6E orchestrator implementation rather than by the gateway/CLI composition path.

### R6E

`runtime/tool_orchestration.py` already requires `ToolExecutionContext.mode_decision` and routes registered capabilities through R6C before execution.

This is the correct downstream boundary. The missing piece is not another tool or permission engine; it is production composition supplying authoritative runtime policy to the existing owners.

### Gateway and CLI

`AgentRequestEnvelope` carries request/session/task/workspace/mode/operation identity. `GovernedAgentGateway._validate_identity()` verifies request mode equals persisted session mode.

The CLI creates/reconstructs `SessionMemoryRuntimeBridge` from persisted values:

```text
mode
active_profile_id
permission_policy_id
evidence_policy_id
provider_id/provider_model
```

Current inspection found these policy/profile fields functioning primarily as durable references. Searches found no authoritative production mapping from opaque `permission_policy_id` / `active_profile_id` values to the typed R6B `permission` or `runtime_policy` vocabulary.

The `session_state` persistence schema likewise has no typed `permission` or `runtime_policy` columns. `WorkspaceMemoryStore` currently initializes its schema by executing `memory_schema.sql`; there is no existing schema-migration framework or precedent that should be silently expanded into a broad migration subsystem for C0.

## Comparable live patterns

Live GitHub inspection was repeated before resolving the C0 input question.

### OpenHands software-agent-sdk

Current public repository inspection at commit `d2845a66657406eba601236820a0a7d700b352e1` shows runtime/settings state modeled as explicit typed configuration rather than inferring runtime authority from arbitrary provider prose or opaque display identifiers.

Reusable lesson for LBE:

```text
persist explicit runtime configuration that the execution boundary consumes
rather than reinterpret unrelated opaque IDs into authority
```

### LangGraph

Current public repository inspection at commit `d56666f7fbf0d380ad84cdf0cbe5aa48ab0cc086` exposes checkpoint persistence as a dedicated runtime concern (`libs/checkpoint`) with explicit thread/checkpoint state.

Reusable lesson for LBE:

```text
durable runtime facts should be recorded as runtime state
not reconstructed later from conversational/model output
```

### GitHub required-check pattern

The existing project research remains useful here: configured requirements, result producers, and final gate evaluation are independent responsibilities.

Reusable lesson:

```text
configured identity/reference
!=
resolved runtime authority
!=
execution result
!=
completion proof
```

## Resolved C0 authoritative-input decision

The repository contains **no authoritative existing mapping** from `permission_policy_id`, `active_profile_id`, `evidence_policy_id`, or provider selection to R6B's typed `permission` and `runtime_policy` inputs.

Therefore C0 must **not** guess such a mapping.

The smallest correct design is to add only the explicit typed session-policy state already required by R6B:

```text
permission
runtime_policy
```

These values are LBE-owned session policy facts. They are persisted independently of provider/model selection and supplied directly to `ModeRequest` at the authoritative runtime/gateway composition boundary.

Opaque references remain references:

```text
permission_policy_id
active_profile_id
evidence_policy_id
```

C0 must not reinterpret those IDs. A future profile/policy registry may resolve an ID into typed policy values, but that is a separate capability and is not required to wire the existing R6B/R6C/R6E path correctly.

### Backward compatibility / fail-closed rule

Existing persisted sessions do not have the new typed fields. C0 should not silently infer write authority from their historical `mode` or opaque policy IDs.

For an existing session with no authoritative typed policy state:

- preserve its durable identity and historical `mode` value;
- treat missing typed policy as unresolved authority;
- fail closed for normal governed execution that requires R6B resolution;
- allow only an explicit policy-establishment/update path to persist valid typed values before governed execution continues.

Do not map historical `mode=coding` automatically to `write_allowed` or `development`; that would manufacture authority that was not previously persisted.

For newly created sessions, the normal creation path should require or deterministically establish typed `permission` and `runtime_policy` before the session is eligible for governed agent execution.

## Revised dependency order

```text
C0  minimal authoritative runtime-policy composition
    -> persist explicit typed permission/runtime_policy session facts
    -> resolve effective R6B mode/behaviors/capabilities in the real request path
    -> reject unresolved/contradictory authority rather than infer it
    -> preserve opaque policy/profile IDs as references only
    -> supply ModeDecision to existing downstream R6C/R6E consumers
    -> do not invent a second policy/permission/tool system

C1  establish immutable task completion contract
    -> consume already-authoritative runtime/task policy facts
    -> persist once per task

C2  trusted semantic validation producers
    -> execute registered validation capabilities
    -> persist producer-bound semantic evidence

C3  thin session validate
    -> load contract + trusted evidence
    -> call existing completion gate
```

## C0 implementation boundary

C0 should:

- reuse `ModeRequest`, `ModeDecision`, and `resolve_mode()`;
- add only explicit typed `permission` and `runtime_policy` to LBE session policy state;
- persist/reload those values with the session independently of provider/model selection;
- keep opaque profile/policy IDs as references rather than reinterpret them;
- resolve policy at the normal gateway/runtime composition boundary;
- reject missing typed policy for governed execution rather than infer authority from legacy mode;
- reject contradictions between resolved mode and persisted/request mode;
- make the resolved `ModeDecision` available to downstream runtime consumers;
- preserve R6C as the authorization owner;
- preserve R6E as the governed tool orchestration owner;
- keep provider/model selection independent from workspace authority;
- keep audit/investigation from gaining coding capabilities through provider output;
- keep compatibility work bounded to the session-policy persistence surface rather than create a generic migration framework unless implementation evidence proves one is necessary.

C0 should **not**:

- create a generic `RuntimePolicyResolver` parallel to R6B;
- create a second permission system;
- reinterpret arbitrary `permission_policy_id`, `active_profile_id`, or `evidence_policy_id` strings as typed authority;
- infer write authority from legacy `mode=coding`;
- add unrestricted shell/tool execution;
- define completion evidence kinds;
- add `session validate`;
- let the provider select policy or validation/completion requirements;
- make the CLI the policy authority.

## Code-PR slice

The first code PR should remain narrow. Candidate ownership surfaces are:

1. `memory/models.py` / `memory_schema.sql` / `memory/store.py` for the two typed session-policy facts and bounded compatibility handling;
2. `session_memory_runtime.py` for durable session construction/reconfiguration and access to authoritative policy facts;
3. `agent_integration.py` for normal-path `ModeRequest` resolution, contradiction rejection, and exposure of the resulting `ModeDecision`;
4. focused tests for new-session policy persistence, legacy fail-closed behavior, provider-switch invariance, request/resolved-mode contradiction, and audit/investigation non-escalation.

R6C/R6E should be reused, not rewritten. If connecting the first registered R6E tool would materially widen the PR, the initial C0 PR may expose the resolved `ModeDecision` through the gateway/runtime boundary and prove it is consumable, then connect normal-path governed tool invocation as the immediately following bounded slice. The acceptance criteria still require no parallel authority path.

## Acceptance proof before C1

Before C1 begins, prove through the installed/normal request path that:

1. R6B is invoked;
2. its `permission` and `runtime_policy` inputs come from explicit authoritative LBE session state rather than provider prose or opaque IDs;
3. legacy sessions lacking that authority fail closed rather than inherit fabricated write permission;
4. resolved mode cannot silently contradict persisted/request identity;
5. the resolved `ModeDecision` reaches downstream runtime consumers;
6. R6C remains the authorization decision owner;
7. R6E remains the tool orchestration owner;
8. provider switching does not alter workspace policy;
9. audit/investigation cannot gain coding capabilities through model output alone;
10. no duplicate policy/session/permission/tool authority was introduced;
11. local Git/BirdEye evidence shows only intended wiring changes.
