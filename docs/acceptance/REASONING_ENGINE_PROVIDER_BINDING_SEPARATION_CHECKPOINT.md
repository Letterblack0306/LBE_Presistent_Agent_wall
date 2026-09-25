# Reasoning Engine / Provider Binding Separation Checkpoint

Status: IMPLEMENTED / STATIC VALIDATION ADDED / LIVE ACCEPTANCE PENDING
Intent: LBE-INTENT-REASONING-ENGINE-PROVIDER-BINDING-SEPARATION-001
Canonical base head: 5ad590bd0113d3c336589510de258ac815d6920a
Current source head recorded before this checkpoint update: 944b4e65978f149b68ed36d26c404191bcedec74

## Current implementation truth

- Provider and reasoning-engine identities are explicit and separately persisted.
- Cline is lazy-loaded only for an explicitly selected Cline binding.
- Native LBE and Cline bindings may coexist for the same provider.
- Governed coding for both engines reuses the same LBE ToolRegistry, R6C authorization, GovernedToolOrchestrator, ToolReceipt/evidence, workspace/session and completion owners.
- Native governed coding selects only an explicitly implemented provider-native event adapter from configured protocol evidence.
- Implemented native governed coding transports now include OpenAI-compatible Chat Completions, Anthropic Messages, Gemini GenerateContent, and OpenAI Responses.
- Gemini Interactions, unknown protocols and future transports fail closed; no unsupported provider is silently routed through another wire protocol.
- OpenAI Responses preserves provider response identity, function `call_id`, and `previous_response_id` across tool continuation.
- Anthropic preserves provider `tool_use.id` through `tool_result`; Gemini preserves provider `functionCall.id` through `functionResponse`.
- No automatic fallback to Cline or another provider is introduced.
- Canonical `lbe code` now delegates coding-controller selection to the same engine-neutral `build_governed_coding_controller` used by the product runtime; the previous native-only CLI rejection is removed.
- Focused CLI coverage now includes an explicitly persisted Cline engine selection and verifies that it reaches the shared governed coding factory.
- Cross-engine coverage compares native-LBE and Cline `workspace.read` receipt/projection truth through the same LBE authority fields.
- Native bounded reasoning is now protocol-aware: OpenAI Chat Completions and OpenAI Responses use distinct request envelopes; Anthropic requires Messages; Gemini requires GenerateContent.
- OpenAI Responses bounded reasoning uses the provider-native `text.format = json_schema` contract instead of a Chat Completions payload.
- The canonical `lbe code` CLI path was identified as a remaining native-only bypass; current scope is explicitly amended to converge that existing owner onto `build_governed_coding_controller` before slice closure.

## Added falsifier coverage

Focused tests now require:

1. native-LBE governed coding rejects unimplemented Gemini Interactions and unknown protocols;
2. native-LBE governed coding accepts Anthropic Messages, Gemini GenerateContent, OpenAI Responses and configured chat/completions routes;
3. Anthropic tool-use/result correlation preserves the provider tool-use ID;
4. Gemini function-call/result correlation preserves the provider function-call ID;
5. OpenAI Responses continuation preserves function call_id and previous_response_id;
6. existing Cline governed coding still uses the same LBE-owned tool/receipt authority.

## Acceptance status

STATIC SOURCE / OWNER ALIGNMENT: IMPLEMENTED
FOCUSED TESTS: ADDED; execution pending a GitHub Actions runner
FULL REGRESSION: BLOCKED_BY_CI_RUNNER — attempts 1 and 2 both terminated all 8 Ubuntu/Windows matrix jobs before any workflow step executed; no test logs were produced
LIVE NATIVE ENGINE TURN: UNVERIFIED
LIVE CLINE REGRESSION: UNVERIFIED
INSTALLED MULTI-ENGINE ACCEPTANCE: UNVERIFIED

Do not close the machine slice from this checkpoint alone.

## Validation infrastructure blocker — 2026-09-21

GitHub Actions run `35559528172` was rerun after the engine/provider source convergence. Attempt 2 reproduced the same infrastructure symptom as attempt 1: all eight matrix jobs completed `failure` with an empty steps list and no logs. This does not classify the source as failing; it blocks focused/full regression evidence.

Classification: `BLOCKED_CONFIGURATION / CI_RUNNER`.

The machine slice remains OPEN. Do not advance to the proposed Rust TUI or later convergence slices until claim-matched regression executes successfully on a functioning runner or equivalent current workspace.
