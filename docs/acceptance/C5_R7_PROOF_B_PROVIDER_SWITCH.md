# C5 / R7 Proof B — Provider Switch Acceptance Record

Updated: 2026-08-12
Status: **PARTIALLY PROVEN — execution after switch still missing**
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

`G:\Developments\lbe-p1-002-proof\c5-provider-switch-project`

Provider-B configs are kept outside tracked project source under:

`G:\Developments\lbe-p1-002-proof\provider-local-b*.json`

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

No health or governed-execution claim is made for this model.

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

## Authorized next proof adjustment

The current provider configuration contract accepts any positive `timeout_seconds`; there is no product-defined maximum in `ProviderConfig`.

For the next **proof-only** Provider B attempt, use:

```json
{
  "endpoint": "<same verified local OpenAI-compatible endpoint>",
  "model": "second-state/smollm3-3b",
  "timeout_seconds": 300
}
```

Preserve any already-required `api_key` field exactly if the existing verified config uses one.

This 300-second timeout is an acceptance-environment adjustment only. It must not alter workspace identity, permission, runtime policy, completion policy, evidence semantics, or validation policy.

The outer proof runner/process timeout must be greater than the provider timeout so the provider can fail or complete through the LBE runtime rather than being killed externally.

## Next execution scope

Rerun only the missing B execution portion:

```text
existing switched session
  -> provider check for second-state/smollm3-3b with timeout_seconds=300
  -> continue/resume same session authority
  -> one bounded governed task
  -> governed tool receipt
  -> completion evidence
  -> deterministic validation
  -> persisted terminal state
```

Do not repeat the already-proven A execution or provider-switch authority comparison unless the session/revision has changed enough to invalidate those receipts.

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

Until then:

**C5/R7 Proof B = PARTIALLY PROVEN.**

**C5/R7 overall = NOT READY.**
