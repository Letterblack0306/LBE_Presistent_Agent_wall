# Provider Config Model Field: Required, Parsed, Then Discarded

Date: 2026-09-29
Revision examined: 734816f
Classification: CONTRACT / CONFIGURATION INCONSISTENCY
Status: RECORDED, NOT RESOLVED

## Finding

`reasoning-provider.json` declares a `model` field. That field is required,
type-checked, parsed, and stored on `ProviderConfig` — and is then
unconditionally replaced by the persisted session model before any request
is made.

The declared model is therefore documentation, not configuration.

## Evidence

`lbe_guard_inspector/reasoning_config.py`:

- line 21 — `_REQUIRED_FIELDS = frozenset({"endpoint", "model", "timeout_seconds"})`
  A config lacking `model` is rejected outright.
- line 71 — `model=raw["model"]` in `provider_config_from_mapping`
  The declared value is accepted and carried on the `ProviderConfig`.
- line 89 — docstring: "the model always comes from the persisted session"
- lines 109-113 — generic OpenAI-compatible branch returns
  `replace(config, model=session_model.strip(), ...)`
- line 118 — declared-provider branch returns
  `replace(config, model=session_model.strip(), ...)`
- line 91-97 — `bind_provider_config_to_session` refuses an empty
  `session_model`, so the persisted value is always present

Both exit paths discard the configured model. There is no configuration in
which the declared `model` reaches a request.

## Why this was not caught earlier

PROV-1 (commit `bed2e4b`) bound the provider model to the persisted session
selection, which is the correct authority direction: the session owns the
selection and the config cannot override it. That change is sound and this
record does not question it.

The side effect is what went unnoticed: making the session authoritative
also made the config field vestigial, and the field remained in
`_REQUIRED_FIELDS`. A required field that is validated and then ignored is
the shape of a contract that no longer describes the system.

Live confirmation at 734816f: `reasoning-provider.json` declares
`google/gemma-4-e4b`; the persisted session model is used regardless.

## Why it is recorded separately from 734816f

`734816f` adds a bounded classifier that compares the persisted model to an
observed live catalog. It is correct, tested, and deliberately UNWIRED.

This finding is a different class of problem: it concerns what the
configuration contract claims, not what any runtime observes. Resolving it
would change the accepted configuration surface, which is a different
ownership question from adding an observable.

The two must not be fused. C0 also touches the request path, and all three
must retain separate intents and separate acceptance evidence.

## Candidate resolutions — not chosen here

1. Remove `model` from `_REQUIRED_FIELDS` and from the example config, so
   the contract states what it actually governs. Smallest change.
2. Keep the field and use it as a first-run default when a session has no
   model yet. Larger; gives the config real authority at session creation.
3. Keep it required and treat a mismatch with the persisted session as a
   configuration error, rather than silently discarding.

Which is correct is an ownership decision about the provider/configuration
contract owner. This record does not make it and does not authorize any of
the three.

## What this record does NOT claim

- It does not claim the current provider behavior is wrong. Session-owned
  model selection is the correct authority direction.
- It does not claim data loss or a runtime defect. Nothing is lost; the
  value is simply unused.
- It does not invalidate `734816f`.
- It does not authorize changing the configuration contract.
