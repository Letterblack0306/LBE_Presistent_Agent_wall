# C5 / R7 Proof B — V1 Decision Record

Updated: 2026-08-12
Status: **B1 PARTIALLY PROVEN — one switched local-model governed execution still required**
Parent: `docs/acceptance/C5_R7_PROOF_B_PROVIDER_SWITCH.md`

This note records the latest negative evidence and the intentionally narrow V1 acceptance boundary so future agents do not repeat the same Cline-log investigation or expand Proof B into model benchmarking.

## Latest evidence

No product source was changed.

Inspected Cline fixtures do not supply reusable B1 evidence:

- `1785460319869_yl0hf` is an LM Studio session using `text-embedding-nomic-embed-text-v1.5` in plan mode; it is not governed coding/tool-execution proof.
- `1785461332072_pt9mp` is a successful Cline session using `deepseek/deepseek-v4-flash`; it is not the local second provider under test.
- existing automated coverage confirms provider selection preserves non-provider fields, but that is lower-level coverage and is not installed-path B1 proof.

Therefore the supplied logs do **not** identify a known-good local Provider-B planning contract.

## V1 scope decision

For the first version, Proof B is deliberately minimal.

B1 requires only:

```text
same persistent installed session
  -> switch to a second actual local model/provider identity
  -> preserve workspace/mode/permission/runtime policy
  -> second model emits one valid bounded governed request
  -> governed action executes
  -> normal validation/completion persists
```

The governed task may use a tiny controlled fixture. V1 does **not** require large-workspace capability, model benchmarking, Cline compatibility, performance tuning, or multiple Provider-B candidates.

Those concerns are deferred until after A-E architecture acceptance.

## Stop conditions

Do not:

- re-inspect the two Cline fixtures above for B1 evidence unless new message-level evidence is added;
- infer a successful local planning contract from embedding, plan-only, or cloud-provider sessions;
- block V1 on large-workspace performance;
- modify LBE source merely because a candidate model is slow or emits an invalid replacement;
- claim B1 from automated provider-selection tests alone.

## Next valid action

Select one actual local model that is known, or can be directly shown, to emit the current bounded structured coding request. Then run exactly one clean installed-path B1 proof.

Required success chain:

```text
provider switch persisted
  -> authority fields unchanged
  -> valid workspace.replace_text request
  -> EXECUTED governed receipt
  -> validation/completion semantics preserved
  -> persisted terminal completion
```

Until that chain exists:

- **B1 = PARTIALLY PROVEN**
- **C5/R7 = NOT READY**
