# FreeLLMAPI test-proxy boundary — LET-44

Status: owner decision, 2026-10-24. Scope: provider selection, session configuration, provider attribution, and acceptance evidence.

## Product ownership

FreeLLMAPI is a locally hosted proxy used only for development, integration tests, diagnostics and live-turn verification. **It is not an LBE product provider.** Do not add it as a built-in provider ID, default profile, hard-coded catalog row, onboarding choice, product dependency or automatic selection.

LBE's supported provider/model discovery comes from the runtime-owned `@cline/llms` catalog and legitimate user-declared endpoints. The generic custom OpenAI-compatible endpoint feature remains supported: a user can deliberately declare an endpoint and choose a model. Such a custom declaration does not promote the endpoint's product/name to a built-in catalog provider. Never silently select FreeLLMAPI on startup.

## Test and attribution rules

Tests may connect to a FreeLLMAPI proxy to exercise the actual provider transport, streaming, model response, error reporting, gateway attribution and governed tool turn. Test fixtures for generic custom-provider selection must use neutral IDs rather than `freellmapi`, to avoid suggesting product-level support. A runtime attribution test may retain the literal `freellmapi` when verifying an observed proxy's name and address.

A successful proxy-backed live turn proves only the exercised route, not working provider discovery across catalog entries, installed F2/F3 picker behavior, or final product acceptance. Provider identity, local proxy identity, and upstream provider/model returned in response metadata are separate facts; display only observed facts. The proxy must not own LBE provider selection, authorization, sessions, model catalog, or completion.

## Acceptance

1. No implicit FreeLLMAPI catalog registration or startup selection.
2. Generic user-declared OpenAI-compatible endpoints continue functioning without special-casing the proxy.
3. Test fixtures do not misclassify FreeLLMAPI as a native/provider-catalog choice.
4. Proxy-backed runtime tests, if run, are reported explicitly as diagnostic evidence; installed terminal provider/model selection remains a separate acceptance requirement.
5. Credentials remain referenced by environment variable name in persisted configuration; never include secret values in evidence.

Evidence baseline: workspace main e22490f4 (2026-10-24), `tests/test_provider_selection.py`, `tests/test_tui_bridge.py`, `apps/lbe-terminal/tests/render.rs`, `lbe_guard_inspector/provider_selection.py`, and provider-attribution adapter.
