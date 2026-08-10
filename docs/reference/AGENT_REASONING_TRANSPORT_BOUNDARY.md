# Agent Reasoning / Transport Boundary

Updated: 2026-08-11
Status: Project architecture invariant

## Rule

LBE integrations must treat browser-side models, local LLMs, coding agents, and other agent participants as **reasoning-capable agents**, not as deterministic machines whose conversational meaning must be reconstructed by a relay/router.

The project rule is:

> **Agents reason; bridges transport. LBE governance constrains authority, but must not become a second reasoning engine.**

## Intended architecture

```text
Browser / Remote Reasoning Agent
          |
          | message + conversation/session/workspace metadata
          v
Transport / Relay
          |
          | reliable bounded delivery
          v
Local Reasoning Agent
          |
          +-- inspect live workspace/runtime
          +-- reason from local + conversational context
          +-- plan
          +-- use authorized tools
          +-- validate
          +-- return response/evidence
          v
Transport / Relay
          v
Browser / Remote Reasoning Agent
```

The browser-side agent may reason over GitHub/remote/context evidence. The local agent may reason over the working tree, runtime, terminal, tools, and local evidence. The bridge should preserve those reasoning capabilities rather than replacing them with a second semantic decision engine.

## Transport responsibilities

The relay/bridge may own hard technical properties including:

- reliable capture and delivery;
- source/target/session/workspace identity;
- target-tab/process identity;
- authentication;
- workspace isolation;
- capability/tool/command security boundaries;
- cancellation and timeout propagation;
- delivery ordering;
- technical transport-level idempotency where accidental duplicate delivery could repeat a side effect;
- operation identity;
- evidence provenance;
- returning results to the originating side.

These are transport/integrity/security responsibilities.

## Governance responsibilities

LBE remains authoritative for deterministic boundaries such as:

- workspace identity;
- persisted runtime policy;
- permissions and capability authorization;
- registered tool execution;
- destructive/persistent-policy controls;
- task completion contracts;
- accepted evidence provenance;
- deterministic validation/completion gates.

These constrain **what an agent may do**. They should not duplicate **how the agent understands free-form conversational context**.

## What must stay agent-owned

Unless a specific deterministic policy requirement proves otherwise, the reasoning agent should decide questions such as:

- whether repeated wording is redundant, corrective, or a continuation;
- whether a reformatted instruction changes task meaning;
- whether more workspace inspection is needed;
- what implementation approach is appropriate;
- how new evidence changes the plan;
- whether a conversational follow-up belongs to the current task;
- what tool/validation step to request within available authority.

The relay must preserve the actual message/context instead of reducing it to rigid semantic labels before the agent receives it.

## Transport deduplication is not semantic deduplication

A stable delivery/operation ID may prevent accidental double execution.

A content hash, wording similarity, timestamp, or "historical" flag must not automatically decide that a user message is semantically redundant or should be hidden from the reasoning agent.

Repeated, expanded, shortened, reformatted, or corrected instructions may carry meaning. Preserve them as conversational context and let the agent reason about them.

## Architecture smell

Treat the following as evidence of possible overbuilt relay intelligence:

```text
strict envelope parser
  -> historical/new hash classifier
  -> relay lifecycle state
  -> task-state router
  -> runtime semantic classifier
  -> agent-state classifier
  -> local LLM
```

Additional smells:

- several layers independently decide `waiting`, `historical`, `needs_decision`, `complete`, or `stopped`;
- repeated approvals appear despite unchanged delegated authority;
- transport rewrites/summarizes instructions before local reasoning;
- message hashes are used to infer user intent;
- a bridge accumulates planning/diagnosis logic unrelated to transport integrity;
- browser and local agents both have useful context, but an intermediate layer discards it and reconstructs a smaller task state.

Before adding another parser, classifier, state flag, task router, approval layer, or lifecycle state, ask:

> Is this enforcing a hard security/integrity/governance property, or is it thinking on behalf of an agent that can already reason?

If it is the latter, keep the responsibility with the agent.

## Relationship to C0/C1/C2

This invariant does not remove C0/C1/C2 deterministic ownership.

- C0 runtime policy composition remains LBE-owned authority.
- C1 task completion policy remains LBE-owned deterministic completion requirement declaration.
- C2 trusted producers remain LBE-owned evidence production/provenance.

Those layers are governance/proof infrastructure, not a reason to move conversational interpretation into the gateway or relay.

The gateway should compose identity/policy/evidence boundaries around agent reasoning, not replace agent reasoning.

## Final invariant

```text
Agent / LLM = reasoning capability
Relay / bridge = transport + integrity
LBE governance = authority constraint
Validation/evidence = proof

Do not make the bridge a second agent.
Do not make governance a substitute for cognition.
```
