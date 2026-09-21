# Reasoning Engine / Provider Binding Separation Checkpoint

Status: IMPLEMENTED / STATIC VALIDATION ADDED / LIVE ACCEPTANCE PENDING
Intent: LBE-INTENT-REASONING-ENGINE-PROVIDER-BINDING-SEPARATION-001
Canonical base head: 5ad590bd0113d3c336589510de258ac815d6920a

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
FOCUSED TESTS: ADDED, execution not available in this GitHub-API-only environment
FULL REGRESSION: UNVERIFIED
LIVE NATIVE ENGINE TURN: UNVERIFIED
LIVE CLINE REGRESSION: UNVERIFIED
INSTALLED MULTI-ENGINE ACCEPTANCE: UNVERIFIED

Do not close the machine slice from this checkpoint alone.
