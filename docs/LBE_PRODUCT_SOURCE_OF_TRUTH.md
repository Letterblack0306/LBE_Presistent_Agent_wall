# LBE Product Source of Truth

Status: **CANONICAL PRODUCT TRUTH**
Last consolidated: 2026-09-19

This document is the single human-readable source of current LBE product truth.

It exists to prevent agents from reconstructing product intent from scattered roadmap, status,
acceptance, research, or historical documents.

## 1. Authority order

When sources disagree, use this order:

1. current runtime evidence;
2. current canonical source and tests;
3. current machine governance in `.lbe/governance/implementation-gates.json`;
4. this document for current product intent, feature preservation, architecture boundaries, and product scope;
5. bounded technical contracts;
6. historical acceptance/design/research records;
7. prior chat/history/screenshots.

Historical documents remain evidence of what was decided or proven at a point in time. They are
not allowed to silently override current source/runtime truth.

## 2. Product identity

```text
PRODUCT                = LBE / LetterBlack
ENTRYPOINT             = lbe
VISIBLE CLIENT         = LBE-owned Rust/Ratatui terminal client
BACKEND / RUNTIME      = LBE runtime
AUTHORITY OWNER        = LBE
BRANDING               = LBE / LetterBlack only
```

The product is an execution-control wall and persistent coding-agent runtime. It is not a generic
agent framework, not a thin model wrapper, and not a rebranded Cline product.

## 3. Core authority boundary

LBE owns all authority-bearing consequences:

- workspace and session identity;
- mode and policy truth;
- authorization;
- governed execution;
- operation and receipt identity;
- evidence provenance;
- persistence and recovery;
- deterministic validation;
- completion truth.

The reasoning/provider layer may reason, plan, select capabilities, interpret results, and continue
from results. It does not gain independent filesystem, process, Git, MCP, browser, persistence,
receipt, validation, or completion authority.

The Rust/Ratatui client owns presentation and input only. It must project authoritative runtime
state; it must not invent runtime truth.

## 4. Current runtime composition

Current canonical source contains both of these implemented assets and both must be preserved:

### Writable ACT/coding path

Current source routes writable coding turns through the existing LBE-owned governed coding runtime,
including `GovernedProviderReasoningController` / `GovernedCodingTurnRuntime`, the LBE coding tool
surface, authorization, governed execution, receipts, evidence, persistence, and completion owners.

### Cline integration path

The repository also contains the governed Cline worker/stdio/provider integration and Cline-backed
provider surface. Cline remains a reuse/adaptation source for reasoning/provider/continuation
mechanics where explicitly wired.

### Preservation rule

Neither implementation may be deleted merely because the other is present or because a current
work slice does not mention it.

Any change to their long-term ownership relationship is an architecture decision and requires
explicit user authorization. Agents must not resolve a documentation conflict by deleting working
features or by rewriting product architecture to match whichever path they happen to inspect first.

## 5. Canonical product flow

```text
USER
  -> lbe
  -> Rust/Ratatui client
  -> RealLbeWrapper / canonical LBE product entry
  -> authoritative session/workspace/provider/mode/policy state
  -> reasoning/provider turn
  -> LBE-generated capability request
  -> authorization
  -> governed execution
  -> ToolReceipt + evidence
  -> continuation
  -> persistence/recovery
  -> deterministic validation/completion
  -> truthful terminal projection
```

No client/provider/native tool path may bypass the LBE authorization/execution/receipt boundary.

## 6. Product modes

Visible product modes:

```text
PLAN
ACT
AUDIT
```

Backend/runtime policy and permission owners remain authoritative. The UI cannot grant itself
permission.

Previously validated mapping includes:

- PLAN + read-only -> investigation;
- AUDIT + read-only -> audit;
- ACT + read-only -> permission required with no mutation;
- ACT + write-allowed -> coding.

## 7. Feature preservation law

This rule applies to every feature in both the backend and TUI repositories:

```text
implemented + working
= preserve as product capability

implemented + disconnected
= integration gap

implemented + partially wired
= continue/reconnect from the existing owner

accepted/planned but unfinished
= preserve as pending product scope

not present in current work slice
!= obsolete

mock/test-only
!= live production capability

historical/reference only
!= current runtime truth

explicitly superseded/deprecated/rejected
= only then eligible for removal
```

An agent must never infer "not in the active plan" -> "delete/hide/ignore".

## 8. Current feature inventory

The table below is a product inventory, not a claim that every row is fully live.

| Area | Current classification | Preservation requirement |
|---|---|---|
| Transcript / conversation timeline | IMPLEMENTED client surface | Preserve |
| Model picker / provider catalog selection | IMPLEMENTED / integrated surface | Preserve |
| Session start/list/resume | IMPLEMENTED | Preserve |
| Session close | REQUEST CONTRACT EXISTS; production support incomplete | Preserve and integrate, do not remove |
| Checkpoint compare/restore | REQUEST/UI CONTRACT EXISTS; production support incomplete | Preserve and integrate |
| Background / registered processes | PARTIAL / governed process owner exists | Preserve |
| Provider catalog / validation / model selection | IMPLEMENTED | Preserve |
| Provider configuration editing/removal | REQUEST/UI CONTRACT EXISTS; production support incomplete | Preserve and integrate |
| Tool registry | IMPLEMENTED governed owner | Preserve |
| Workspace read/list/glob/search | IMPLEMENTED governed tools | Preserve |
| Workspace patch/write | IMPLEMENTED governed mutation path | Preserve |
| Git bounded mutation | IMPLEMENTED governed backend capability | Preserve |
| Evidence projection/browser | IMPLEMENTED/partial live projection | Preserve |
| Receipt projection/browser | IMPLEMENTED/partial live projection | Preserve |
| MCP / BirdEye registration and governed query | IMPLEMENTED backend integration; broader live acceptance may vary | Preserve |
| Diagnostics | IMPLEMENTED | Preserve |
| Turn abort/cancellation request | IMPLEMENTED request path; exact runtime support must be evidenced per path | Preserve |
| Session memory / recall/checkpoint memory | CONTRACT/PARTIAL; production Rust integration incomplete | Preserve |
| Browser chat bridge | CONTRACT/PARTIAL; live integration incomplete | Preserve |
| Permissions / policy hooks / approvals | IMPLEMENTED core boundary | Preserve |
| Schedules | PLANNED / not fully implemented | Preserve product intent |
| Connectors | PARTIAL external-registration foundation | Preserve product intent |
| Agent teams | PLANNED/PARTIAL registration foundation | Preserve product intent |
| Conversation handoff | PLANNED/PARTIAL persistence foundation | Preserve product intent |
| Artifacts / review | PARTIAL evidence/diff foundation | Preserve product intent |
| Subagents | PARTIAL governed registration foundation | Preserve product intent |
| Projects / settings | PARTIAL backend owners; UI incomplete | Preserve product intent |
| Composer / prompt editor | PARTIAL / UI incomplete | Preserve product intent |
| Statusline / title | PLANNED / UI incomplete | Preserve product intent |
| Code search | PARTIAL backend search exists; richer UI incomplete | Preserve product intent |
| Usage / quotas | PLANNED/PARTIAL provider-health foundation | Preserve product intent |
| Workspace changes / diff | IMPLEMENTED client surface; live writable acceptance path-specific | Preserve |
| File editor / patch review | IMPLEMENTED client contract; live execution path-specific | Preserve |
| Plain CLI / no-TUI mode | IMPLEMENTED contract | Preserve |
| Terminal compatibility / responsive UI | IMPLEMENTED client behavior | Preserve |
| Deterministic runtime state projection | IMPLEMENTED foundation | Preserve |
| Cline interoperability/reuse | IMPLEMENTED/PARTIAL integration asset | Preserve |
| OpenCode reuse/reference analysis | REFERENCE/REUSE INPUT | Preserve as reference, not runtime authority |

This inventory must be changed only from current source/runtime evidence or an explicit product
decision. Omission from a future plan does not remove a row.

## 9. Production request surfaces currently known to be incomplete

The Rust request contract contains capabilities whose production `RealLbeWrapper` path has been
reported as unsupported or incomplete in current source. These are integration gaps, not deletion
candidates:

- CloseSession;
- ConfigureProvider;
- RemoveProvider;
- CompareCheckpoint;
- RestoreCheckpoint;
- CompactContext;
- session-memory operations;
- browser-chat operations.

Before changing any of them, inspect current source because this list may become stale as fixes
land.

## 10. Accepted runtime baseline

The backend has established LBE-owned foundations for:

- persistent session/task lifecycle;
- provider-neutral reasoning boundary;
- authorization;
- ToolRegistry / GovernedToolOrchestrator / ToolReceipt;
- governed workspace/process/Git mutation;
- governed external capability registration;
- installed capability registry;
- evidence and receipt projection;
- bounded recovery;
- deterministic completion;
- installed product composition.

The installed product acceptance gate currently records PASS for its defined tested scope. A PASS
for one acceptance scope does not prove every product feature is integrated.

## 11. Evidence vocabulary

Use these classifications exactly:

- **PROVEN** — claim supported by matching current runtime/acceptance evidence.
- **IMPLEMENTED** — source exists, but live behavior may not be proven.
- **DOCUMENTED** — contract/plan exists.
- **PARTIAL** — some required path exists, but end-to-end behavior is incomplete.
- **INFERRED** — conclusion from evidence that has not been directly proven.
- **UNVERIFIED** — evidence required but absent.
- **STALE** — source/document was once relevant but no longer matches current truth.
- **BLOCKED** — a required dependency/authorization/evidence prevents progress.
- **SUPERSEDED** — explicitly replaced by a newer decision.

Never report IMPLEMENTED or DOCUMENTED as PROVEN.

## 12. Documentation model

This file is the only human-readable current product source of truth.

Other documentation classes have narrower roles:

```text
PROJECT_INTENT_LEDGER.md
    = bounded mutation intent history/lifecycle

technical contracts
    = implementation contracts, not current product status

acceptance records
    = evidence/history, not product roadmap authority

research/reference
    = input/evidence, not current product truth

Git history
    = historical document retention
```

Agents must not create parallel status, roadmap, architecture-summary, handoff, checkpoint, or
"current truth" documents.

## 13. Document consolidation rule

The one-time cleanup may:

- absorb still-valid product facts into this document;
- repair inbound references;
- relocate historical evidence when needed;
- delete redundant current-truth prose after its useful information is preserved;
- retain machine-consumed contracts/specifications where code still depends on them.

The cleanup must not:

- delete product code;
- remove a feature because it is absent from the current plan;
- rewrite completed historical intent records;
- convert mock evidence into live proof;
- delete acceptance evidence before its evidentiary role is preserved in Git/history;
- break machine consumers such as `lbe_product_surface_spec.json` without also updating/removing those consumers.

## 14. Post-consolidation agent documentation rule

After the consolidation intent closes, ordinary agents are not allowed to create or edit
documentation.

The sole normal agent-writable documentation path is:

```text
docs/governance/PROJECT_INTENT_LEDGER.md
```

and only for one bounded intent lifecycle entry.

All other `docs/**` mutations require explicit user authorization for that specific document
change.

Technical enforcement requirements are defined in
`docs/governance/AGENT_DOCUMENT_WRITE_POLICY.md`.

## 15. Fix workflow after consolidation

For each product fix:

```text
read this source of truth
-> inspect current code/runtime
-> identify existing owner
-> create/update one bounded intent
-> preserve existing features
-> implement only the missing/faulty seam
-> run matching tests/runtime proof
-> update that intent result
```

Do not create a new roadmap, status file, checkpoint prose, architecture note, or handoff document
for routine fixes.

## 16. Repository roles

```text
Letterblack0306/LBE_Presistent_Agent_wall
    = canonical backend/runtime/governance repository

Letterblack0306/LBE_Agents_wall_Intigration
    = canonical Rust/Ratatui visible-client repository

Letterblack0306/GPT-Knowledge
    = project knowledge/projection; useful for routing and history, but current source/runtime
      evidence outranks it for implementation truth
```

Cross-repository feature work must preserve the same ownership boundary: the Rust client projects
and controls; the backend owns authority-bearing runtime truth.

## 17. Change rule for this file

Agents must treat this file as read-only after the one-time consolidation.

It may change only when:

1. the user explicitly authorizes a product-truth/document change;
2. the change is backed by current source/runtime evidence or a deliberate product decision;
3. feature-preservation rules are respected;
4. contradictory historical records are not silently rewritten;
5. the corresponding bounded intent records the change.
