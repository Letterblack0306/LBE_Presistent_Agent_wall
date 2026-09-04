# LetterBlack Product Integration Machine Check

## Purpose

`tools/lbe_product_integration.ps1` is the single machine-level integration verifier, proof runner, builder, and candidate packager for the two current LetterBlack product repositories:

- runtime authority: `Letterblack0306/LBE_Presistent_Agent_wall`
- Rust client/projection: `Letterblack0306/LBE_Agents_wall_Intigration`

The script is not a third runtime authority. Agent Wall remains the owner of workspace/session identity, authorization, governed execution, receipts/evidence, persistence, recovery, validation, and completion truth. The Rust repository remains the client/projection layer.

## Default workspaces

```text
C:\Agents-Memory-Tool-v6-integration
C:\LBE-TUI-Lab
```

The local worktrees may be dirty. The script never packages arbitrary worktree content. It refreshes and packages `origin/main` for each repository using `git archive`.

## Modes

```powershell
.\tools\lbe_product_integration.ps1 check
.\tools\lbe_product_integration.ps1 prove
.\tools\lbe_product_integration.ps1 build
.\tools\lbe_product_integration.ps1 package
```

### check

Read-only integration inspection.

It verifies:

- exact repository identity;
- `origin/main` SHA for both repositories;
- one-worktree policy;
- canonical product-entry commands;
- Rust `RealLbeWrapper` routing through Agent Wall;
- read-only workspace capability presence on both sides;
- persisted approval/operation binding;
- exact-operation approval test presence;
- changed-payload rejection proof presence;
- BirdEye governed routing presence;
- session identity projection.

It writes:

```text
dist/product-integration/integration-manifest.json
```

### prove

Exports clean `origin/main` snapshots and runs bounded proof suites against those snapshots.

Agent Wall proof:

```text
tests/test_authorization_resolver.py
tests/test_tool_orchestration.py
tests/test_product_entry.py
tests/test_provider_continuation.py
```

Rust proof:

```text
cargo test --locked
cargo fmt -- --check
```

A dirty local tree cannot turn these proofs into PASS because tests execute from clean exported snapshots.

### build

Requires structural integration and proof PASS.

It builds:

- Agent Wall wheel with `python -m pip wheel`;
- governed Cline worker dependencies with `npm ci --omit=dev`;
- Rust `lbe.exe` with `cargo build --release --locked`.

The build output is assembled under:

```text
dist/product-integration/LetterBlack-LBE/
  runtime/
  client/
  cline-worker/
  install.ps1
```

### package

Performs `check + prove + build`, then emits:

```text
LetterBlack-LBE-2.0.3-win-x64-candidate.zip
integration-manifest.json
checksums.json
```

The ZIP is intentionally classified as a candidate until external installed PTY/ConPTY interaction is proven. The script does not convert missing installed interactive evidence into release readiness.

## Integration contract

The machine check follows this ownership path:

```text
Rust client
  -> Agent Wall product_entry
  -> persisted session/mode/policy
  -> authorization
  -> registered governed tool
  -> persisted operation binding
  -> ToolReceipt/evidence
  -> provider continuation
  -> Rust projection
```

For writable mutation the required proof is:

```text
workspace.patch
  -> ESCALATED
  -> approval_id bound to operation/capability/workspace
  -> APPROVE
  -> same request fingerprint
  -> exactly one execution
  -> persisted receipt
  -> replay returns same receipt
  -> changed payload rejected
```

The Agent Wall published test `test_product_entry_approval_bridge_executes_exact_operation_once` is the current deterministic cross-process proof for this seam. The integration script requires that proof to exist and then executes the current product-entry test suite in `prove` mode.

## Failure behavior

The script fails closed.

- repository identity mismatch -> stop;
- missing workspace -> stop;
- more than one registered worktree -> stop;
- missing cross-repository contract -> exit 2;
- proof failure or blocked proof -> exit 3;
- wheel, worker dependency, or Rust build failure -> stop;
- package mode never reports release-ready without the separate installed interactive acceptance.

Missing seams remain visible in `integration-manifest.json`; they are not silently inferred as connected.

## Package provenance

Every manifest records:

- Agent Wall local HEAD;
- Agent Wall `origin/main`;
- Rust local HEAD;
- Rust `origin/main`;
- dirty-entry counts;
- worktree counts;
- structural contract results;
- proof commands and outputs;
- generated artifact inventory.

The package is therefore bound to exact remote source SHAs even when the local workspaces contain unrelated user work.
