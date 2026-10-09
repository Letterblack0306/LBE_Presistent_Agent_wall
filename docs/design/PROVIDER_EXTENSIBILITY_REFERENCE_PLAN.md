# LBE data-driven provider and engine integration plan

Status: PLANNED / NOT IMPLEMENTED. Observed baseline: 2026-10-09, LBE `main` at `4254ca6`.
Owner: LBE persistent Agent Wall and Rust/Ratatui TUI. Reference routing: GPT-Knowledge.

## Source-of-truth and scope
This document records the requested architecture before further implementation. It does not assert end-to-end provider functionality.
Evidence hierarchy: live runtime > current workspace source > accepted repository contracts > GPT-K/reference > historical conversations.
The user requires reference-backed changes and no artificial provider limit. Preserve the engine-neutral Agent Wall and existing governance, sessions, receipts, and evidence.

## Observed source evidence
- `lbe_guard_inspector/provider_registry.py`: `register_binding(engine_id, provider_id, factory)` accepts string IDs and maintains engine/provider bindings; the backend is extensible at this registry boundary.
- `apps/lbe-terminal/src/types.rs`: `ProviderId` is a closed Rust enum with 17 variants. Adding an unlisted provider requires editing Rust.
- `apps/lbe-terminal/src/app.rs`: provider configuration / validation CLI parsing contains named-provider mappings; source-specific adapter boundaries must be reconciled.
- Current `/provider-validate` and `provider check` evidence proves diagnostics for some configured or unavailable providers, not working inference across all.
- Runtime readiness, model enumeration, auth/config scope, streaming, and the coding tool loop need separate authoritative observations.

## External implementation references — behavior to investigate, not blindly copy
- OpenCode: https://github.com/opencode-ai/opencode ; https://opencode.ai/docs/providers ; https://opencode.ai/docs/models — provider/model abstraction and discovery; verify upstream revision and adapter contracts before implementing.
- ClinePass: https://docs.cline.bot/getting-started/clinepass — credential/account routing, supported access, not assumed interchangeable with third-party APIs.
- Cline free models: https://docs.cline.bot/getting-started/free-models — eligibility/catalog can change; fetch using supported surfaces instead of hardcoded entries.
- Cline models/config: https://docs.cline.bot/getting-started/config — configuration scope, precedence, and user control.
- Cline TUI/CLI/ACP: https://docs.cline.bot/usage/tui ; https://docs.cline.bot/usage/acp — interactive provider selection and agent protocol behavior.
- Cline tools/rules/skills/plugins/MCP/hooks/scheduling: https://docs.cline.bot/tools-reference/all-cline-tools ; https://docs.cline.bot/customization/cline-rules ; https://docs.cline.bot/customization/skills ; https://docs.cline.bot/customization/plugins ; https://docs.cline.bot/mcp/mcp-overview ; https://docs.cline.bot/customization/hooks ; https://docs.cline.bot/cli/scheduling.
Each proposed feature requires an exact upstream source/revision or authoritative documentation and a matching LBE owner + observable.

## Planned work packages (in dependency order)
1. **Evidence map:** Inspect current Python registry/engine bindings, profile persistence, TUI catalog/picker, CLI parser, active sessions, and connected tools. Record observed IDs and actual contracts; no speculative provider count.
2. **Provider identity:** Replace closed Rust `ProviderId` with a stable data-driven identity representing any provider ID returned by the authoritative backend, without changing existing stable IDs, sessions, or serialized compatibility. Update all exhaustive matches and label handling.
3. **Adapter/config resolution:** Keep native, OpenAI-compatible, local, cloud, Cline and future engine adapters distinct; use explicit capability metadata, profile precedence, credential references, auth state, reachability and selected model. Do not silently auto-switch credentials or provider.
4. **Dynamic models:** Resolve models and free/eligible offerings through actual supported catalog APIs, with provenance/freshness and non-ready states. No invented context windows, prices, free eligibility or tool support.
5. **User experience:** Provider/model search and switching in TUI, validation by any registered ID, honest state/footer, profile edit/activate without forced defaults, and accessible error/recovery paths.
6. **Agent execution acceptance:** Real provider > tool selection > Agent Wall authorization > actual read/effect > receipt > model consumes tool result > second reasoning turn > completion. Inspect process and session recovery, and distinguish timeout/offline/auth/no tools.
7. **Regression and installed acceptance:** Unit and adapter fixtures plus live providers (at least one local and one remotely configured if available). ConPTY interaction, actual runtime receipts, current release binary, cancellation, and clean restart; do not promote test PASS to product working.

## Acceptance classifications
Use PROVEN, DISPROVEN, INCONCLUSIVE, BLOCKED_CONFIGURATION, STALE_TEST_OR_FIXTURE, TEST_HARNESS_FAILURE.
No provider support may be declared PROVEN solely because it appears in a picker or registry.
Maintain an audit table for each work package: upstream reference + revision, LBE source owner, current-state evidence, implementation diff, runtime effect, falsifier, tests, final classification.

## Dependency / safety constraints
Do not alter dirty/unrelated files or create duplicate authority. Preserve intended governance and intent-registration before mutations. Do not unconditionally migrate credentials or active profiles. User-owned endpoints and secrets remain locally configured. New adapter code must not claim user subscriptions (including ClinePass) imply an exposed API.

## Current next step
Source-level map + falsifiable acceptance tests for Rust provider ID extensibility; then a narrowly scoped patch. THIS PLAN DOES NOT AUTHORIZE DECLARING THE PRODUCT COMPLETE.

## Implementation checkpoint — 2026-10-09

- **Reference decisions:** `docs/reference/AGENT_REASONING_TRANSPORT_BOUNDARY.md` prohibits semantic authority in transport; `docs/reference/TERMINAL_UI_CONTRACT_MAPPING.md` makes Rust presentation-only; `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md` keeps completion independent of provider text; `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` keeps authority independent of model/provider choice.
- **Current source owner:** `lbe_guard_inspector/provider_registry.py` registers provider/engine bindings via string IDs; `apps/lbe-terminal/src/types.rs` still exposes a fixed legacy `ProviderId` enum.
- **Implemented bounded initial slice:** Rust `ProviderKey` retains arbitrary discovered registry identities, and `parse_registered_provider_keys` validates and losslessly decodes the backend list. New regression cases cover previously unknown identifiers, duplicates and invalid IDs.
- **Not claimed:** The legacy TUI provider picker still consumes `ProviderId`. New `ProviderKey` is not yet connected to picker commands, model selection or live inference; these remain OPEN. Test PASS only validates the isolated contract.
- **Next ordered owner:** migrate the full picker/provider-event/request model to data-driven `ProviderKey` while preserving configured profiles and session identity. Then perform actual Windows ConPTY provider/tool end-to-end acceptance; do not change provider-based workspace authority or completion ownership.
