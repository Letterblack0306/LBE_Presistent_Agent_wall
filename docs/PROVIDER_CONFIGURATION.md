# Provider configuration

LBE owns persistent sessions, workspace identity, mode, permissions, governed
tools, evidence, validation, and completion. A configured provider only
performs bounded reasoning through that existing runtime boundary.

Provider configuration is an explicit user-owned JSON file. Keep it outside
the repository, package source, runtime database, and any tracked fixture.
The supported fields are exactly `endpoint`, `model`, `timeout_seconds`, and
optional `api_key`.

```json
{
  "endpoint": "https://provider.example/v1/endpoint",
  "model": "user-selected-model",
  "timeout_seconds": 120,
  "api_key": "user-owned-secret"
}
```

Use the file with the provider selected for the session or command:

```powershell
lbe provider check --provider <provider-id> --provider-config C:\LBE\config\provider.json
```

The CLI reads the supplied connection only for the requested command. It does
not discover credentials, read other applications' secret stores, package a
key, or persist the raw key in LBE state.

## Built-in provider IDs

| Provider ID | Endpoint shape | Authentication |
| --- | --- | --- |
| `openai` | OpenAI Chat Completions endpoint | Required explicit API key; Bearer authorization |
| `anthropic` | Anthropic Messages endpoint | Required explicit API key; Anthropic request headers |
| `gemini` | Gemini `generateContent` endpoint for the chosen model | Required explicit API key; supplied only from the config field |
| `openai-compatible` | User-supplied OpenAI-compatible chat-completions endpoint | Optional, for local/compatible services that do not require a key |

For Gemini, set `endpoint` to the complete selected-model `generateContent`
URL and keep the key exclusively in `api_key`; do not embed a key in the URL.

Each adapter translates only the provider HTTP request/response envelope. LBE
validates the same bounded planning/explanation contract after decoding the
response, then applies the existing mode, authorization, tool, evidence,
validation, and completion owners. Provider adapters cannot grant tools or
execute workspace mutations themselves.
