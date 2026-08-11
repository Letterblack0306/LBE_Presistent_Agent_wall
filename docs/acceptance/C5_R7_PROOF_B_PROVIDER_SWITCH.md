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

## Cline-derived local-provider investigation

A later proof attempt created:

`G:\Developments\lbe-p1-002-proof\provider-local-b4-cline.json`

The goal was to reuse a request shape known to have worked in Cline with a local model, but the available Cline session evidence did not provide an unambiguous successful governed-planning contract that could legitimately be reused as LBE proof.

Files inspected:

- `tests\test differfence\1785460319869_yl0hf`
- `tests\test differfence\1785461332072_pt9mp`

Findings:

- `1785460319869_yl0hf` is an LM Studio Cline session, but uses `text-embedding-nomic-embed-text-v1.5` in plan mode. It is not governed coding/tool-execution evidence.
- `1785461332072_pt9mp` is a Cline Pass session using `deepseek/deepseek-v4-flash`, not the local LM Studio provider under test.
- neither session provides a reusable successful local-provider B1 planning contract.
- Gemma remains the only Cline-configured local candidate found that reached the LBE governed-tool boundary, but that run did not produce a valid exact replacement request, so it cannot satisfy B1.

Correct classification:

```text
Cline config/session evidence: useful for candidate request-shape discovery only
successful local governed-planning contract: NOT PROVEN
B1 governed execution: NOT PROVEN
product defect: NOT PROVEN by these sessions
```

Do not copy a Cline request shape merely because a session exists. Reuse is allowed only after identifying a **specific successful session message** whose non-sensitive planning contract can be extracted and shown to correspond to actual successful local-model tool planning.

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

A proof timeout may be increased to match observed local-model latency, provided the outer proof runner exceeds it and no LBE authority, evidence, validation, or completion semantics are weakened.

Do not treat `300` seconds as a universal C5 value. Select the timeout from the actual provider/model/hardware behavior being tested.

## Next execution scope

Do not repeat already-proven Provider A execution or the provider-switch authority comparison unless the session/revision changed enough to invalidate those receipts.

The next valid B1 attempt is:

```text
identify one actually successful local-model planning session
  -> extract only its non-sensitive request/planning contract
  -> confirm that contract corresponds to successful tool planning, not embedding/plan-only/non-local execution
  -> apply that exact contract shape to one switched-provider B1 run
  -> require a valid governed tool request
  -> governed execution receipt
  -> completion evidence
  -> deterministic validation
  -> persisted terminal state
```

If no such successful local planning session exists, do not infer or fabricate a contract from nearby Cline sessions. Use a provider/model known to satisfy the existing LBE structured planning contract instead.

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
