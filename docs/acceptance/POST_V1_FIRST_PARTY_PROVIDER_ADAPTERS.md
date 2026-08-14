# Post-V1 first-party provider adapters

Status: **PACKAGE VALIDATED; READY FOR AN EXPLICIT PYTHON-RUNTIME DISTRIBUTION ACTION**

This bounded post-V1 release slice extends only the existing provider registry.
It leaves the npm launcher and all LBE session, workspace, mode, permission,
governance, tool, evidence, validation, and completion owners unchanged.

## Included adapters

The registry now exposes these provider IDs:

```text
openai
anthropic
gemini
openai-compatible
```

`openai-compatible` remains available for user-supplied compatible endpoints,
including local services. The first-party adapters translate only the relevant
provider HTTP envelope before returning the decoded object to the existing
ToolAware reasoning backend, which validates the same bounded LBE plan and
explanation contracts.

First-party adapters require an explicit `api_key` in a user-owned provider
configuration file. No adapter discovers credentials, reads another
application's secret store, packages a secret, or creates provider-owned LBE
state. Gemini rejects endpoints with an embedded key.

## Regression evidence

Focused source validation:

```text
python -m pytest -q tests/test_first_party_reasoning_provider.py tests/test_provider_registry.py tests/test_provider_health.py tests/test_reasoning_provider.py tests/test_c5_coding_execution.py tests/test_cli.py tests/test_cli_c4.py
84 passed
```

Authoritative repository validation:

```text
python -m pytest -q
648 passed
```

The mocked transport/contract tests establish that Anthropic and Gemini:

- produce their documented transport envelopes;
- decode only the expected response envelope;
- return through the shared LBE bounded planning/explanation contracts; and
- preserve a proposed `workspace.replace_text` request for the existing R6E/R6C
  path rather than executing it in the adapter.

No live provider call is recorded in this document. Live provider health or
governed execution remains dependent on an explicit user-owned connection.

## Release boundary

The Python distribution version is `0.2.1`. A clean Python 3.14 virtual
environment installed `lbe_guard_inspector-0.2.1-py3-none-any.whl`; `lbe
--help`, `lbe provider list`, and `lbe session create` all succeeded. The
installed list contained all four provider IDs, `memory_schema.sql` was found
through `importlib.resources`, persistent SQLite state was non-empty, and the
wheel archive contained no runtime database, provider/configuration JSON,
`.env`, `.truth`, or test files. Wheel SHA-256:

```text
7193D21CD7769B0DD6D79D658F467DE68C62FC79E96CDF8A95A2EF4EA46BA5C5
```

`git diff --check` passed. The existing `@letterblack/lbe` npm wrapper does
not need a version change because it already discovers and launches compatible
`0.2.x` Python runtime wheels; it does not own provider logic.

The existing npm bootstrap was also exercised against that exact wheel in a
fresh isolated `LBE_HOME`. `lbe --install --wheel` completed, `lbe --diagnose`
reported `LBE_RUNTIME_COMPATIBLE` with Python package `0.2.1`, `lbe provider
list` returned all four provider IDs, and an installed `lbe session create`
created persistent SQLite state.
