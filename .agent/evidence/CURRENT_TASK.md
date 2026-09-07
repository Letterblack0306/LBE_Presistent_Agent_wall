# Current Task Evidence

## Task
Extend the active LBE doctrine-to-provider context bridge from the coding TUI
path to the non-coding provider path, then validate the next live-provider gate.

## Target Repo
`C:\Agents-Memory-Tool-v6-integration`

## Confirmed Broken Behavior
`GovernedProviderReasoningController` supplies active doctrine to coding turns,
but `NonStreamingProviderTurnRuntime` currently sends only a user message.
Audit and investigation TUI turns therefore do not receive the active LBE
doctrine context.

## Evidence
- File: `lbe_guard_inspector/provider_turn_runtime.py`
- Evidence: `NonStreamingProviderTurnRuntime.run` calls the adapter with only a
  user message.
- File: `lbe_guard_inspector/cli.py`
- Evidence: non-coding TUI sessions construct `NonStreamingProviderTurnRuntime`
  without guidance.
- Gate: `.lbe/governance/implementation-gates.json`
- Gate slice: `DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE`

## Root Cause
The doctrine builder is wired into the governed coding controller only; the
non-streaming provider runtime has no system-guidance input.

## Minimal Fix
Allow the existing non-streaming runtime to receive provider-only
`AgentGuidance`, prepend its prompt to the provider request, and persist only
safe guidance provenance. Build that guidance from the persisted session mode
for non-coding TUI sessions.

## Allowed Edit Paths
- `lbe_guard_inspector/provider_turn_runtime.py`
- `lbe_guard_inspector/cli.py`
- `tests/test_provider_turn_runtime.py`
- `tests/test_background_provider_turn_runtime.py`

## Required Validation
- Focused provider-turn tests.
- Existing doctrine-guidance tests.
- Implementation gate checker.
- Live local-provider coding versus audit comparison if a configured local
  endpoint and advertised model are available; no cloud fallback.

## Remaining Risks
Source and focused tests do not prove that a real provider changes behavior
between doctrines. That requires a live local model response and must remain
unverified until the local endpoint/model contract is exercised.

## TUI Acceptance Update

Installed `2.0.3` TUI launch and initial rendering are evidenced by the user
supplied screenshot. The six command labels are visible, but command execution
has not yet been captured. Cyan replacement glyphs around the composer/input
panel are recorded as a separate terminal Unicode/rendering defect, not as a
command-handler failure.

The subsequent screenshot also proves keyboard focus/input handling: the typed
`E` is visible in the objective composer. The current acceptance classification
is therefore `LAUNCH_RENDER_INPUT=PROVEN`, `COMMAND_EXECUTION=UNPROVEN`,
`UNICODE_RENDERING=DEFECT`, and `BLANK_PYTHON_WINDOW_CAUSE=UNRESOLVED`.

Next acceptance requires live results for `/status`, `/provider`, `/evidence`,
`/help`, `/interrupt`, and `/cancel`, with the last two exercised during an
active turn. A targetable terminal input surface is still required to collect
that evidence.
