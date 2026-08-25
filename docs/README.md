# LBE Documentation Library

This is the single entry point for LBE documentation. Start here, then follow the four-document
learning spine, then the active gate for authority.

The complete per-file intent inventory is [DOCUMENT_INTENT_MANIFEST.md](DOCUMENT_INTENT_MANIFEST.md).
Every material Markdown file must have an entry there before it can be treated as understood,
current, historical, protected, or disposable.

## What is LBE

LBE is a **persistent, provider-neutral runtime**: the agent/provider reasons, while LBE owns
workspace and session identity, context/evidence authority, mode/policy, authorization, governed
execution, operation receipts, validation/completion truth, and persistent state.

> **LBE governs an agent's capabilities and consequences; it does not prescribe the agent's
> reasoning procedure.**

Capabilities such as the Guard Inspector sit **on top of** the LBE boundary — they are never
parallel authority owners. Current workspace/runtime evidence outranks memory and reference
history throughout.

## The four-document learning spine

Read these four in order to understand how someone learns and uses LBE:

1. **README** (this file) — what LBE is and how to navigate the library.
2. **[LBE Agent Lifecycle](LBE_AGENT_LIFECYCLE.md)** — the complete operational flow: who
   reasons, who authorizes, who executes, and who decides a task is done.
3. **[Vision](IMPLEMENTATION_PLAN.md#1-product-goal)** — the platform direction: a persistent,
   provider-neutral runtime with the agent on top of LBE authority.
4. **[Architecture](design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md)** — the ownership boundary
   and the accepted separation of agent agency from LBE authority.

> Note: `docs/history/reference-legacy/docs/01_VISION.md` and `docs/history/reference-legacy/docs/02_ARCHITECTURE.md` describe the **Guard
> Inspector** as the first capability of this platform (its first vertical slice). Treat them as
> the capability's design; the platform framing above (Vision/Architecture in the spine) governs.

## Documentation routing

- question about present state -> `CURRENT_STATUS.md`
- question about permitted work -> `.lbe/governance/implementation-gates.json` -> active acceptance gate
- question about ordered work -> `IMPLEMENTATION_PLAN.md`
- question about operational flow -> `LBE_AGENT_LIFECYCLE.md`
- question about a finding -> `AUDIT_FINDING_REVIEW_REGISTER.md`
- question about product UI/CLI -> `reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md`
- question about architecture -> `design/`
- question about closed evidence -> `acceptance/` or `history/`

## Reading order (with the gate)

1. [Current status](CURRENT_STATUS.md) — concise present-tense product, gate, and proof state.
2. [Current implementation gate](acceptance/CURRENT_IMPLEMENTATION_GATE.md) — human projection
   of the authoritative machine gate.
3. `.lbe/governance/implementation-gates.json` — authoritative active-slice authorization.
4. [Canonical implementation plan](IMPLEMENTATION_PLAN.md) — ordered product work and ownership.

## Collection map

| Collection | Purpose | Status rule |
|---|---|---|
| Root (`CURRENT_STATUS`, `IMPLEMENTATION_PLAN`, `LBE_AGENT_LIFECYCLE`, `AUDIT_FINDING_REVIEW_REGISTER`) | Live operational documents. | Keep current; do not duplicate their subjects elsewhere. |
| [`acceptance/`](acceptance/) | Machine-gate projections, validation checkpoints, and release evidence. | The active gate is named by `implementation-gates.json`; all other records are historical unless explicitly identified there. |
| [`governance/`](governance/) | Cross-cutting implementation and progression rules. | Policy/routing reference, never a substitute for the active machine gate. |
| [`design/`](design/) | Architecture, ownership, and component contracts. | Design intent; live code and the active gate remain authoritative. |
| [`reference/`](reference/) | External/product research and technical evidence. | Reference only; not acceptance proof. |
| [`research/`](research/) | Exploratory comparison material. | Non-authoritative; promote conclusions only into an owner document. |
| [`contracts/`](contracts/) | Current technical registries used by the implementation. | Maintain as named contracts, not as status reports. |
| [`history/`](history/) | Closed phase records retained for evidence. | Immutable except for link repair or an explicit correction note. |

## Workspace document visibility and hygiene

Document organization is part of the LBE product boundary. A Markdown file is not made valid by
existing on disk, and it is not made irrelevant merely by living in a nested directory.

Every material Markdown file under the canonical workspace must be:

1. **owned** by one canonical subject or authority;
2. **classified** as live, supporting, acceptance, contract, design, reference, instruction,
   historical, generated, temporary, quarantined, or invalid;
3. **discoverable** from this documentation entrypoint or from the runtime/governance surface that
   is required to consume it;
4. **reachable** from current product, build, runtime, governance, active documentation, explicit
   history, or protected user work; and
5. **given one disposition**: keep, repair, archive, quarantine, or remove.

Nested folders are storage and ownership boundaries, not a way to hide documents. Required paths
such as `.agent/`, `.cline/`, `docs/acceptance/`, and `docs/history/` may remain nested when a
runtime, governance contract, or historical provenance depends on their path. Their contents must
still be listed, classified, and navigable from the appropriate entrypoint.

The hygiene invariant is:

```text
ZERO UNEXPLAINED MARKDOWN FILES
ZERO ORPHANED CURRENT-STATE CLAIMS
ZERO UNCLASSIFIED DOCUMENT DIRECTORIES
ZERO INVALID OR ABANDONED DOCUMENTS LEFT IN LIVE SURFACES
```

An unreferenced document is a cleanup candidate, not an automatic deletion order. It must first be
checked for runtime/tooling reachability, historical evidence value, protected ownership, and
duplicate authority. Once it is proven invalid, obsolete, duplicate, generated, temporary, or
abandoned, it must be removed or moved out of live surfaces with its references repaired. Unknown
material must be explicitly marked and tracked for resolution; it must not silently become current
context or permanent workspace clutter.

Before an implementation or documentation task is complete, the workspace reconciliation must
show every material Markdown path and its disposition. A clean Git index alone is insufficient.

## Design entry points

- [Runtime vision: doctrine-driven engineering](design/LBE_RUNTIME_VISION_DOCTRINE_DRIVEN_ENGINEERING.md)
  — proposed product and UX direction; not an implementation or gate owner.
- [LBE Agent Lifecycle](LBE_AGENT_LIFECYCLE.md) — operational flow owner.
- [Agent Lifecycle — Phases, Owners, Surfaces, Reuse](design/AGENT_LIFECYCLE_PHASES.md) — the
  single product lifecycle everything hangs off of.
- [Product Surface Living Spec](design/lbe_product_surface_spec.json) — the machine-legible model
  (panels, owners, contracts, states/transitions); rendered at
  `reference/ui/lbe_product_surface.html`.
- [Architecture Registry](reference/ui/lbe_architecture_registry.html) — the canonical
  **documentation/navigation** registry of the active LBE architecture. Only docs registered there
  are canonical **as documentation**; everything else is non-canonical by default. It enforces the
  single spine (README → Lifecycle → Vision → Architecture → Runtime Pipeline) and a six-level
  per-doc status model. Navigate this library through the registry, not by browsing the file
  system. It is a navigation/rendering registry only: it **does not supersede**
  `implementation-gates.json`, active acceptance gates, current source, or runtime evidence.

## Maintenance rules

- One fact has one live owner. Link to it; do not restate a competing status.
- Put a date and truth state (`READY`, `BLOCKED`, or `UNKNOWN`) on a current operational update.
- Preserve acceptance and historical evidence. Do not rewrite it to resemble a later state.
- When a document becomes historical, move it to `history/` and add a short catalog entry here or
  in that collection's README.
- Add a new document only when an existing owner cannot truthfully hold the information.
- `desktop.ini` is host metadata, is not a documentation artifact, and is intentionally excluded
  from this library.
