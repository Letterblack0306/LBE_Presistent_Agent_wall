# Reasoning Engine / Provider Binding Separation Checkpoint

Status: IMPLEMENTED / STATIC VALIDATION ADDED / LIVE ACCEPTANCE PENDING
Intent: LBE-INTENT-REASONING-ENGINE-PROVIDER-BINDING-SEPARATION-001
Canonical base head: 5ad590bd0113d3c336589510de258ac815d6920a

## Current implementation truth

- Provider and reasoning-engine identities are explicit and separately persisted.
- Cline is lazy-loaded only for an explicitly selected Cline binding.
- Native LBE and Cline bindings may coexist for the same provider.
- Governed coding for both engines reuses the same LBE ToolRegistry, R6C authorization, GovernedToolOrchestrator, ToolReceipt/evidence, workspace/session and completion owners.
- Native governed coding now fails closed unless the configured endpoint proves the OpenAI-compatible chat/completions protocol actually implemented by OpenAICompatibleEventAdapter.
- Anthropic Messages, Gemini GenerateContent/Interactions, OpenAI Responses, unknown protocols and future transports are not silently routed through the chat/completions adapter.
- No automatic fallback to Cline or another provider is introduced.

## Added falsifier coverage

Focused tests now require:

1. native-LBE governed coding rejects Anthropic Messages;
2. native-LBE governed coding rejects Gemini GenerateContent;
3. native-LBE governed coding rejects OpenAI Responses;
4. native-LBE governed coding accepts configured chat/completions routes for OpenAI-compatible, LM Studio, Ollama and OpenRouter;
5. existing Cline governed coding still uses the same LBE-owned tool/receipt authority.

## Acceptance status

STATIC SOURCE / OWNER ALIGNMENT: IMPLEMENTED
FOCUSED TESTS: ADDED, execution not available in this GitHub-API-only environment
FULL REGRESSION: UNVERIFIED
LIVE NATIVE ENGINE TURN: UNVERIFIED
LIVE CLINE REGRESSION: UNVERIFIED
INSTALLED MULTI-ENGINE ACCEPTANCE: UNVERIFIED

Do not close the machine slice from this checkpoint alone.
