# Mode Policy Production Wiring Evidence

Updated: 2026-08-10
Status: Documentation-only architecture checkpoint

## Finding

The typed R6B mode policy engine exists and is tested, but current production inspection found no consumers of `ModeRequest`, `ModeDecision`, or `resolve_mode()` outside the mode-controller module itself.

That means the current gateway validates a caller-supplied/persisted mode identity, but does not yet prove that the effective runtime mode, allowed behaviors, and capabilities were deterministically resolved through the R6B policy engine for a normal agent request.

This matters before completion-contract establishment because completion requirements must be derived from authoritative LBE runtime policy, not from a disconnected helper, provider prose, CLI arguments, or ad-hoc defaults.

## Evidence

### Current repository

Verified local/main head during inspection:

- `74d9142c1da04a23abe3962f79630d02cc1d13a1`

Observed production search result:

```text
MODE_HIT_COUNT=0
```

for production consumers of:

- `ModeRequest(`
- `ModeDecision`
- `resolve_mode(`

The `AgentRequestEnvelope` currently carries request/session/task/workspace/mode/operation identity and arguments, while `GovernedAgentGateway._validate_identity()` verifies request mode equals persisted session mode. That proves identity consistency, not R6B policy resolution.

### Existing behavior contract

`validation_before_acceptance` requires independent validation. `development_mode_capabilities` includes proposal/testing/validation behavior. These are policy vocabulary, but current evidence does not show the normal gateway path consuming them through R6B resolution.

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
completion is separate from loop termination/model opinion
```

### External live references

OpenHands SDK architecture separates model output, confirmation checks, execution, observation events, and runtime conversation status.

LangGraph persistence keeps thread-bound checkpointed state and task writes so resumed execution uses durable recorded state.

OpenAI Codex documents runtime approval/execution modes governing what the agent can do separately from model reasoning.

These patterns support connecting policy/mode state to the actual execution path before downstream completion semantics depend on it.

## Revised dependency order

```text
C0  production mode-policy wiring
    -> resolve effective mode/behaviors/capabilities through R6B in the real request path
    -> preserve persisted session identity and permission authority

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

## C0 requirements

- reuse existing `ModeRequest` / `ModeDecision` / `resolve_mode()`;
- wire it into the normal runtime/gateway composition rather than create another resolver;
- derive inputs from authoritative session/request policy facts;
- reject contradictions between resolved mode and persisted/request identity;
- expose resolved behaviors/capabilities to downstream runtime consumers;
- never grant write authority merely because provider output asks for coding;
- preserve audit/investigation read-only behavior unless policy grants otherwise;
- keep provider/model selection independent from policy authority.

## Non-goals

C0 does not define completion evidence kinds, add `session validate`, add a permission system, let the model select validation requirements, change guard verdict ownership, or add unrestricted tool execution.

## Acceptance proof before C1

Before C1 begins, prove from the installed/normal request path that:

1. the mode controller is invoked;
2. the decision is deterministic from authoritative inputs;
3. request/session identity cannot silently contradict the resolved decision;
4. resolved behaviors/capabilities are available to runtime consumers;
5. provider switching does not change workspace policy;
6. audit/investigation cannot gain coding capabilities through provider output alone;
7. local Git/BirdEye evidence shows only intended wiring changes.
