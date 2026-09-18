# Agent Document Write Policy

Status: **CANONICAL DOCUMENT-GOVERNANCE POLICY**

## Purpose

After the one-time documentation consolidation, agents must stop generating competing product
plans, status files, architecture notes, checkpoints, handoffs, or acceptance prose.

The normal agent documentation surface is reduced to one bounded intent ledger.

## Default rule

```text
docs/** = READ ONLY FOR AGENTS
```

Normal agent writes are allowed only to:

```text
docs/governance/PROJECT_INTENT_LEDGER.md
```

and only for the lifecycle of one bounded intent.

## Allowed ledger mutations

An agent may:

- append one new bounded intent before implementation;
- update the status/result of that same intent;
- record exact affected owners and paths;
- record required evidence and actual validation evidence;
- close or supersede that intent when supported.

## Forbidden ledger mutations

An agent may not:

- rewrite completed historical intent records;
- use the ledger as a general status document;
- rewrite product architecture through an intent entry;
- manufacture PASS without matching evidence;
- silently change product scope;
- remove an existing feature from product scope because it is not in the current slice;
- use an intent to bypass explicit user authorization required for architecture/publication/destructive work.

## All other docs paths

Without explicit user authorization for the exact document mutation, agents must not:

- create Markdown/JSON/YAML documentation under `docs/`;
- edit `docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md`;
- edit design/roadmap/reference/research documents;
- generate new checkpoint/gate/status/handoff files;
- rewrite README files as current project truth;
- update acceptance prose merely because code changed;
- delete/relocate documentation.

## One-time consolidation exception

The intent:

```text
LBE-INTENT-DOCUMENT-SOURCE-OF-TRUTH-CONSOLIDATION-001
```

is the temporary exception for consolidating existing documentation, repairing references, and
installing enforcement.

When that intent is closed, the exception ends.

## Machine enforcement requirement

Documentation cleanup is not complete until repository enforcement rejects staged agent-created
documentation outside the ledger.

Required enforcement behavior:

```text
for each staged path:

  if path does not begin with docs/:
      normal repository governance applies

  else if path == docs/governance/PROJECT_INTENT_LEDGER.md:
      allow only if intent-ledger structural validation passes

  else:
      reject unless an explicit human/user document-write authorization is present
```

The enforcement should be implemented in the existing governance/check-hook path rather than as a
parallel policy engine.

At minimum enforce from:

- the existing implementation-gate checker or a helper it owns;
- `.githooks/pre-commit`;
- CI validation where practical, so a local-hook bypass is detectable.

## Human/user exception

A non-ledger documentation mutation requires an explicit user-authorized exception.

Recommended auditable mechanism:

```text
LBE_HUMAN_DOC_WRITE=1
```

plus a bounded intent that names the exact allowed documentation paths and reason.

The environment flag is not, by itself, product authorization. Agents must not self-assert it
without an explicit user instruction covering the exact document change.

A stronger external authorization mechanism may replace this environment flag later without
changing the policy.

## Source-of-truth protection

`docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` is protected.

An agent may read it freely. It may not edit it during routine implementation.

If current source/runtime evidence contradicts it, the agent must:

1. report the contradiction;
2. preserve the working feature/source;
3. create a bounded intent for the actual product fix or reconciliation;
4. request explicit user authorization before changing product truth when the contradiction
   represents an architecture/product decision.

The agent must not "fix" the contradiction by deleting implemented features.

## Intent-only operating loop

After consolidation:

```text
SOURCE OF TRUTH      read-only
        |
        v
INTENT LEDGER        only normal agent-writable doc
        |
        v
SOURCE / RUNTIME     implementation
        |
        v
TESTS / RECEIPTS     proof
        |
        v
INTENT RESULT        close/update same intent
```

No new status/roadmap/checkpoint document is created for routine work.

## Historical evidence

Historical acceptance/design/reference files may remain in Git history or a clearly non-current
archive. Their existence does not grant agents permission to rewrite them.

Git history is the durable record of removed documentation. Current product truth belongs only in
`docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md`.

## Feature preservation invariant

```text
NOT IN CURRENT SLICE != OBSOLETE
```

Existing implemented or partial capabilities must be preserved unless explicitly superseded,
deprecated, rejected, or removed by an authorized product decision.

Documentation cleanup is never sufficient evidence to remove product capability.
