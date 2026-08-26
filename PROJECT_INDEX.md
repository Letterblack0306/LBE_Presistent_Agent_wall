# Project Structural Authority Index

Status: **CANONICAL GOVERNANCE INDEX**

This is the root registry of structural responsibility. It is not a file dump and it does not
replace source, contracts, machine governance, or acceptance evidence. Every implementation area
must map to one row before it may be changed.

| Path / area | Purpose | Authority owner | Canonical supporting document | Mutation boundary |
|---|---|---|---|---|
| `lbe_guard_inspector/` | Product runtime and governed execution source | LBE runtime | `docs/LBE_AGENT_LIFECYCLE.md` | Active intent and machine gate only |
| `lbe_guard_inspector/session_lifecycle.py` | Shared CLI/Textual session creation, resume, and provider-selection application service | Session application contract owner | `docs/acceptance/SESSION_APPLICATION_CONTRACT_UNIFICATION_CHECKPOINT.md` | Active session-contract intent only |
| `lbe_guard_inspector/runtime/` | Session, provider-turn, orchestration, and governed runtime owners | LBE runtime | `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` | Existing owner required |
| `lbe_guard_inspector/behavior/` | Mode and behavior contracts | LBE policy | `docs/contracts/PRIORITY_MODULE_REGISTRY.md` | Contract-scoped intent only |
| `tests/` | Runtime and acceptance regression coverage | LBE validation | Active acceptance gate | Must prove the affected intent |
| `scripts/` | Gate checks and validation tooling | LBE governance/validation | `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | Governance intent required |
| `.github/` | CI and release workflow governance | Release/repository governance | `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | Explicit release or governance intent |
| `.lbe/` | Machine governance, receipts, and protected runtime state | Machine governance | `.lbe/governance/implementation-gates.json` | Protected; explicit governance intent |
| `.agent/` | Retired local agent-routing material | Historical/local control surface | `docs/README.md` and `.lbe/governance/implementation-gates.json` | Do not treat deleted routing aliases as live authority |
| `.cline/` | Retired local Cline control material | Historical/local control surface | `docs/README.md` and `.lbe/governance/implementation-gates.json` | Do not treat deleted routing aliases as live authority |
| `docs/` | Canonical documentation, contracts, design, gates, reference, and history | Documentation owner + machine gate | `docs/README.md` | Classify and update intent manifest |
| `docs/acceptance/` | Active gate records and bounded acceptance checkpoints | Machine gate + acceptance owners | `docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | Active intent and machine-selected slice only |
| `docs/acceptance/RECOVERY_COMPLETION_PROMOTION_CHECKPOINT.md` | PASS checkpoint for recovery, deterministic completion, and proof promotion | Recovery/completion acceptance owner | `.lbe/governance/implementation-gates.json` | Active recovery intent only; immutable after canonicalization |
| `docs/acceptance/INSTALLED_PACKAGE_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | PASS checkpoint for isolated installed-package end-to-end runtime proof | Complete-runtime acceptance owner | `.lbe/governance/implementation-gates.json` | Acceptance evidence only; publication remains separately locked |
| `docs/acceptance/SESSION_APPLICATION_CONTRACT_UNIFICATION_CHECKPOINT.md` | PASS checkpoint for shared CLI/Textual session/provider lifecycle ownership | Session application contract owner | `.lbe/governance/implementation-gates.json` | Acceptance evidence only; no next product slice active |
| `docs/acceptance/LBE_INTERFACE_PRODUCT_SURFACE_CHECKPOINT.md` | PASS checkpoint for the usable LBE Textual interface product surface | LBE interface product-surface owner | `.lbe/governance/implementation-gates.json` | Acceptance evidence only; no independent runtime authority |
| `.githooks/` | Commit and push enforcement | Repository governance | `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | Hook change requires governance intent |
| `schemas/` | Machine-readable contract/reference schemas | Contract owner | `docs/contracts/` | Contract intent required |
| `rules/` | Active audit and rule implementation | LBE audit/rule owner | `docs/AUDIT_FINDING_REVIEW_REGISTER.md` | Active implementation intent plus affected rule owner |
| `tools/` | Deterministic validation and acceptance utilities | LBE validation owner | `docs/acceptance/STAGE_2_FINAL_CHECKPOINT.md` | Validation/tooling intent required |
| `examples/` | Non-authoritative examples and reference material | Reference owner | `docs/reference/README.md` | No runtime authority |
| `lbe-core/` | Embedded independent LBE Core repository retained for reuse research | Separate Git repository authority | `lbe-core/LBE_Core_Engine/INDEX.md` | Read-only from parent; no parent mutation authority |
| `unused-in-repo/` | Preserved material proven not to participate in the live repository | Workspace-hygiene preservation owner | `unused-in-repo/MANIFEST.md` | Move only after complete non-use proof; never use as live authority |
| `README.md` | Product and installation entrypoint | Product documentation | `docs/README.md` | Product-doc intent only |
| `PROJECT_INDEX.md` | Root structural authority registry | LBE governance | `docs/governance/PROJECT_INTENT_LEDGER.md` | Protected; update before new structure |
| `pyproject.toml` | Package metadata and version authority | Release governance | Active publication gates | Publication intent only |

## Structural law

```text
UNINDEXED_STRUCTURE = NO_MUTATION
```

If a new subsystem, adapter, provider, UI, database, integration, or directory is discovered,
register its purpose, owner, supporting contract, and mutation boundary here before implementation.

Embedded repositories and protected local-only material require separate ownership classification;
they are not silently absorbed into this canonical index.
