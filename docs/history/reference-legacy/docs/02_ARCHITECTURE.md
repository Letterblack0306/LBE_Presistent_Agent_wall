# 02 — Architecture

## Components

### 1. User interface

Accepts a problem statement, workspace target, and optional permission intent.

### 2. Guard Inspector orchestrator

Owns:

- task state;
- tool sequencing;
- evidence-package assembly;
- guard requests;
- result aggregation;
- user-facing explanation.

It does not decide guard truth by itself.

### 3. Agents Memory Tool SQLite index

Contains indexed reference knowledge such as:

- rules;
- guards;
- patterns;
- proofs;
- examples;
- historical mistakes;
- confirmed project Q&A;
- verified decisions;
- UI, CEP, animation, automation, and agent references.

The index is retrieval infrastructure, not authority.

### 4. Search and inspect tools

Retrieve ranked evidence from the index and, when required, inspect the current workspace.

### 5. Small LBE reasoning agent

Responsibilities:

- interpret the user problem;
- identify likely failure domains;
- select relevant guards;
- request specific evidence;
- explain findings;
- propose a workspace-rule candidate when justified.

It cannot:

- produce a deterministic guard verdict;
- authorize writes;
- declare validation passed;
- silently create permanent policy.

### 6. Deterministic guard implementations

Evaluate explicit conditions and return evidence-bound results.

### 7. LBE Core

Owns:

- workspace identity;
- task scope;
- policy;
- capability;
- approval requirements;
- execution authority;
- audit and completion proof.

### 8. Validation and proof

Confirms the guard result or any approved change using explicit checks.

## Trust hierarchy

From highest to lowest:

1. Passing current validation evidence.
2. Current target workspace source and configuration.
3. Active workspace policy and authoritative rules.
4. Verified proofs and checkpoints.
5. Verified historical repairs.
6. Curated patterns and examples.
7. Unverified historical matches.
8. General chat history.
9. Model inference.

## Responsibility boundary

```text
Model selects and interprets.
Retrieval supplies historical evidence.
Workspace tools supply current facts.
Guards detect.
LBE Core authorizes.
Validation proves.
User approval creates persistent constraints.
```
