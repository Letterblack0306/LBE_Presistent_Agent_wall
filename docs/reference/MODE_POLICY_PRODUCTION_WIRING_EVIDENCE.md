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

But current production inspection found no normal-path consumers.

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

Current inspection found these policy/profile fields functioning primarily as durable references. No new generic policy registry or resolver should be invented merely to make C0 compile.

## External live patterns

Comparable systems reinforce the same separation:

- GitHub required checks: requirements exist independently, producers report structured status, and the gate evaluates satisfaction.
- LangGraph durable execution: thread/task state and task writes are persisted independently of model prose.
- OpenHands/Codex-style agent runtimes separate model reasoning from execution/approval/runtime state.

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

## Revised dependency order

```text
C0  minimal authoritative runtime-policy composition
    -> resolve effective R6B mode/behaviors/capabilities in the real request path
    -> preserve persisted session identity and existing policy references
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
- reuse the existing persisted session/runtime identity;
- resolve policy at the normal gateway/runtime composition boundary;
- reject contradictions between resolved mode and persisted/request mode;
- make the resolved `ModeDecision` available to downstream runtime consumers;
- preserve R6C as the authorization owner;
- preserve R6E as the governed tool orchestration owner;
- keep provider/model selection independent from workspace authority;
- keep audit/investigation from gaining coding capabilities through provider output;
- fail closed when authoritative input required for policy resolution is unavailable rather than fabricate policy semantics.

C0 should **not**:

- create a generic `RuntimePolicyResolver` parallel to R6B;
- create a second permission system;
- reinterpret arbitrary `permission_policy_id` or `evidence_policy_id` strings as permissions without an existing authoritative mapping;
- add unrestricted shell/tool execution;
- define completion evidence kinds;
- add `session validate`;
- let the provider select validation/completion requirements;
- make the CLI the policy authority.

## Open implementation question

Before the code PR, determine the smallest authoritative mapping for R6B inputs from existing session/request state.

The key unresolved point is **not** whether R6B/R6C/R6E should be used; that is now supported. The remaining question is which existing persisted/session facts legitimately supply `permission` and `runtime_policy` without inventing semantics for opaque policy IDs.

If current code contains no authoritative mapping, C0 must fail closed or introduce only the minimum explicit typed session-policy state required by the existing R6B contract, with documentation and migration kept bounded.

## Acceptance proof before C1

Before C1 begins, prove through the installed/normal request path that:

1. R6B is invoked;
2. its inputs come from authoritative runtime/session state rather than provider prose;
3. resolved mode cannot silently contradict persisted/request identity;
4. the resolved `ModeDecision` reaches downstream consumers;
5. R6C remains the authorization decision owner;
6. R6E remains the tool orchestration owner;
7. provider switching does not alter workspace policy;
8. audit/investigation cannot gain coding capabilities through model output alone;
9. no duplicate policy/session/permission/tool authority was introduced;
10. local Git/BirdEye evidence shows only intended wiring changes.
