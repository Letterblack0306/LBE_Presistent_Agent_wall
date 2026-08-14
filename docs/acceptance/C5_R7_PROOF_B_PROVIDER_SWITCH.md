# C5 / R7 Proof B — Provider Switch Acceptance Record

Updated: 2026-08-12
Status: **PROVEN — B1 provider-replacement semantics; B2 capability testing deferred**
Parent record: `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`

This file records the installed-path Provider Switch proof so future agents do not repeat already-proven steps or misclassify timeout behavior as an authority defect.

## Requirement

Proof B must establish that changing provider/model does not change LBE-owned authority or lifecycle semantics, and that the switched provider can subsequently complete at least one governed installed-path operation.

Required chain:

```text
persistent installed session
  -> provider/model A executes governed task
  -> capture workspace/mode/permission/runtime-policy baseline
  -> supported provider/model switch in same session
  -> authority fields remain unchanged
  -> provider/model B is healthy for the required reasoning contract
  -> provider/model B completes a governed operation
  -> normal evidence/validation/completion semantics remain unchanged
```

## Controlled proof environment

Disposable proof project:

`G:\Developments\lbe-p1-002-proof\c5-provider-switch-project-v2`

Provider-B configs are kept outside tracked project source under:

`G:\Developments\lbe-p1-002-proof\provider-b1.json`

No product source or PR #53 runtime source was changed by this proof attempt.

## Proven A-side baseline

Provider/model A:

`openai-compatible / qwen/qwen3-coder-30b`

Observed installed-path evidence:

- provider check: `READY`;
- governed task completed;
- governed edit executed;
- session validation completed successfully.

## Provider switch result

The same persistent session was switched through the supported installed path.

The following LBE-owned fields were preserved across the switch:

- workspace identity;
- mode;
- permission;
- runtime policy.

Recorded result:

`policy_unchanged = true` for all checked policy fields.

This proves the provider/model switch itself does not mutate those authority fields in the observed installed session.

It does **not** yet prove the whole Proof B family because provider/model B has not completed a governed operation.

## Provider/model B attempts

### `qwen/qwen3.5-9b`

Observed:

- readiness attempt timed out.

This model is a heavier local model. The timeout is classified as **environment/performance inconclusive**, not as evidence of a provider-switch, authorization, or governance defect. No health or governed-execution claim is made for this model from that attempt.

### `second-state/smollm3-3b`

Observed:

- provider check reached `READY`;
- governed planning exceeded the configured provider timeout;
- execution failed closed;
- no governed mutation occurred;
- no completion was claimed.

Correct classification:

```text
provider/model B health contract: READY observed
provider/model B planning execution: timeout
LBE authority preservation: proven for checked fields
Proof B overall: PARTIALLY PROVEN
```

Do not reinterpret this timeout as permission/policy failure without new evidence.

A lightweight model may be used to prove provider-replacement mechanics on a controlled fixture, but such a result must not be interpreted as proof that the same model is suitable for large real workspaces.

## Cline-derived provider investigation

A later proof attempt created:

`G:\Developments\lbe-p1-002-proof\provider-local-b4-cline.json`

The goal was to reuse a request shape known to have worked in Cline, but the available inspected Cline session evidence did not provide an unambiguous successful governed-planning contract that could legitimately be reused as LBE proof.

Files inspected:

- `tests\test differfence\1785460319869_yl0hf`
- `tests\test differfence\1785461332072_pt9mp`

Findings:

- `1785460319869_yl0hf` is an LM Studio Cline session, but uses `text-embedding-nomic-embed-text-v1.5` in plan mode. It is not governed coding/tool-execution evidence.
- `1785461332072_pt9mp` is a Cline Pass session using `deepseek/deepseek-v4-flash`, not the local LM Studio provider previously under test.
- neither inspected session by itself provides reusable successful B1 planning evidence.
- Gemma reached the LBE governed-tool boundary in a separate attempt, but did not produce a valid exact replacement request, so that attempt did not satisfy B1.

Correct classification:

```text
Cline config/session evidence: useful for provider/model discovery
successful governed B1 execution: NOT YET PROVEN
product defect: NOT PROVEN by these sessions
```

Do not copy a request shape merely because a Cline session exists. If reusing a request/planning shape, it must come from a specific successful message whose non-sensitive contract is known to correspond to actual successful tool planning.

## User-authorized Cline connection reuse — deferred integration option

Cline may eventually be used as a provider/model and credential source when the user explicitly grants permission, but **the current installed LBE runtime does not provide a supported Cline credential/session adapter**.

Therefore this is **not a current B1 proof path** and must not be implemented merely to finish V1 Proof B.

The future boundary, if implemented later, is:

```text
user authorizes reuse of Cline-managed provider connection
  -> Cline supplies/holds provider identity, model selection, and credential/session access
  -> LBE consumes that authorized connection through a supported provider/auth adapter
  -> LBE does not silently scrape, copy, persist, log, or expose the secret
  -> LBE session/workspace/policy/permissions remain LBE-owned
```

Without a supported adapter:

```text
Cline credentials remain Cline-owned
LBE uses an explicit LBE-owned provider connection
```

The product does **not** need to bundle AI models or issue provider credentials. Authentication remains between the user and the selected provider. Cline integration is a possible later convenience surface, not a V1 acceptance dependency.

Do not add Cline credential/session integration during B1 unless it becomes an independently approved product slice.

## Proof B claim split

To avoid overstating what a small fixture/model proves, interpret Proof B in two layers:

### B1 — provider replacement semantics

Proves:

```text
same persistent session
  -> provider/model switch
  -> workspace/mode/permission/runtime policy unchanged
  -> switched provider completes one governed operation
  -> normal evidence/validation/completion semantics preserved
```

A small controlled fixture is acceptable for B1.

### B2 — representative provider capability

Separately evaluates whether a realistically capable provider/model can operate over a representative larger workspace through bounded LBE retrieval/context and still complete governed work.

B1 must not be used to claim B2.

## Authorized next proof adjustment

The current provider configuration contract accepts any positive `timeout_seconds`; there is no product-defined maximum in `ProviderConfig`.

A proof timeout may be increased to match observed provider/model latency, provided the outer proof runner exceeds it and no LBE authority, evidence, validation, or completion semantics are weakened.

Do not treat `300` seconds as a universal C5 value. Select the timeout from the actual provider/model/environment behavior being tested.

## Next execution scope

Do not repeat already-proven Provider A execution or the provider-switch authority comparison unless the session/revision changed enough to invalidate those receipts.

For current V1 B1, use the existing installed adapter and one explicit user-owned OpenAI-compatible Provider-B config, for example:

`G:\Developments\lbe-p1-002-proof\provider-b1.json`

Then run only:

```text
same persistent session
  -> load explicit Provider-B connection
  -> switch provider/model
  -> confirm authority fields unchanged
  -> one bounded workspace.replace_text request
  -> governed execution receipt
  -> completion evidence
  -> deterministic validation
  -> persisted terminal state
```

Do not block V1 on Cline integration, Cline compatibility completeness, large-workspace quality, benchmarking, performance tuning, or a universal credential abstraction.

## Completion predicate

Proof B becomes `PROVEN` only when all of the following exist in the same installed-path evidence chain:

1. provider/model switch persisted;
2. workspace identity unchanged;
3. mode unchanged;
4. permission unchanged;
5. runtime policy unchanged;
6. switched provider/model B passes the required health contract;
7. switched provider/model B completes a governed operation;
8. normal evidence/validation/completion semantics remain intact;
9. terminal result is persisted.

The completion predicate was satisfied by the installed Provider-B receipt
recorded below. This proves B1 only; B2 remains explicitly deferred.

---

## Provider-B explicit-config attempt — 2026-08-12

The user supplied the required external configuration:

`G:\Developments\lbe-p1-002-proof\provider-b1.json`

Its required non-secret connection fields were structurally complete. Before
changing the persisted session, installed LBE ran the required provider health
check through the existing `openai-compatible` adapter.

Observed result:

```text
HTTP 429
code: credit_balance_exhausted
message: no credits remaining
```

No provider switch, governed operation, workspace mutation, completion claim,
or product-source change was made after this failed health check.

Classification:

```text
owner: user-owned Provider-B account/billing state
LBE product defect: not indicated
Proof B: BLOCKED
```

The controlled Provider-B fixture baseline was committed clean before a future
retry so prior proof residue cannot be attributed to Provider B.

This earlier account-quota result is retained as historical context only. It
was superseded by the successful user-owned OpenRouter Provider-B connection
below; no secret, credential, or provider configuration was committed.

---

## Final B1 installed receipt — 2026-08-12

Controlled fixture and persisted session:

```text
workspace: G:\Developments\lbe-p1-002-proof\c5-provider-switch-project-v2
runtime DB: G:\Developments\lbe-p1-002-proof\c5-provider-switch-runtime-v2\acceptance.sqlite3
session: c5-provider-switch-session-v2
task: c5-provider-b-task-v3
```

The existing installed adapter health check returned `READY` with structured
output for Provider B `openai-compatible / nvidia/nemotron-nano-9b-v2:free`.
The same session was then switched through `lbe provider select`; its response
reported all tracked authority fields unchanged and retained the same workspace
and coding mode.

The real Provider-B planning response returned one schema-valid,
workspace-relative `workspace.replace_text` request. Existing LBE owners then
performed the rest of the path:

```text
real Provider-B proposal
  -> R6C ALLOW modify
  -> R6E EXECUTED one README.md replacement
  -> receipt-bound source_change PASS
  -> registered focused test PASS (1 passed)
  -> git_status PASS
  -> session validate READY
  -> persisted completed / VALIDATED_COMPLETION
```

The persisted receipt records:

```text
operation_id: reasoning.inspect:c5-provider-b-request-v3:workspace.replace_text
path: README.md
replacement_count: 1
before/after SHA-256: recorded and current after-hash verified
```

Git status contained only the governed fixture README mutation. No product
source, provider adapter, authority, evidence, validation, or completion owner
was changed to obtain this proof.

**Verdict: C5/R7 Proof B1 = PROVEN.**

Durable lesson: a provider that passes health may still omit required planning
elements. That behavior must fail closed and be classified at the provider
boundary; it does not authorize bypassing LBE's existing guard, R6C, R6E,
evidence, or completion owners. A small controlled fixture proves replacement
semantics, not representative provider capability (B2).
