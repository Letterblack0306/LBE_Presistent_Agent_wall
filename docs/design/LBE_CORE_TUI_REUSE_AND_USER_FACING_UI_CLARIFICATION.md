# LBE Core TUI Reuse and User-Facing UI Clarification

Status: **AUTHORITATIVE ARCHITECTURE CLARIFICATION**
Updated: 2026-08-14

This clarification narrows the interpretation of the existing CLI/TUI design documents.
It does not create a new runtime owner, command executor, or parallel terminal product.

The intended TUI is a **user-facing interface over the existing LBE runtime**, and its
implementation direction is to **reuse and adapt the existing LBE Core UI/TUI work**
rather than design a new execution-oriented TUI from scratch.

The existing project documents remain authoritative for runtime ownership, event
contracts, capability control, governance, evidence, validation, completion, and
provider/session semantics. This clarification is authoritative specifically for the
UI reuse and wiring boundary.

---

## 1. Product boundary

The TUI is not the command-execution engine.

Correct ownership:

```text
LBE runtime / LBE Core
  -> sessions
  -> provider/model state
  -> permissions and policy
  -> governed capabilities and tool execution
  -> evidence
  -> validation
  -> completion
  -> ordered runtime/session events

existing LBE Core UI/TUI
  -> reused and updated
  -> user-facing interaction surface
  -> renders current runtime state and events
  -> sends user intent/control requests back to existing runtime owners
```

The UI may expose commands, tools, approvals, diffs, validation, provider selection,
session controls, and agent messages, but it does not independently execute or own
those operations.

Forbidden interpretation:

```text
new TUI
  -> its own command runner
  -> its own session state
  -> its own permission logic
  -> its own completion logic
```

---

## 2. Reuse requirement

Before implementing a new TUI renderer or terminal application, the project must locate
and inspect the existing LBE Core UI/TUI source and determine which presentation,
navigation, session, composer, status, and interaction components can be reused.

The implementation sequence is therefore:

```text
locate existing LBE Core UI/TUI
  -> identify reusable user-facing components
  -> map those components onto the current persistent-agent runtime/event contracts
  -> adapt only where the current runtime requires new session/tool/evidence states
  -> preserve one runtime authority
  -> wire the installed `lbe` launcher to the reused user-facing UI when ready
```

Do not replace reusable LBE Core UI work merely because the current public runtime is
exposed through argparse commands.

The current argparse CLI is a transport/administrative surface. Its existence does not
define the intended user-facing TUI architecture.

---

## 3. User-facing purpose

The primary purpose of the TUI is to let the user interact with and observe the
persistent agent runtime.

The primary surface should support:

- session/workspace identity;
- user input/composer;
- agent responses and commentary;
- provider/model selection and status;
- mode and permission visibility;
- tool/activity presentation;
- approvals or blockers;
- changed files/diff visibility;
- evidence and validation visibility;
- session resume/checkpoint/history;
- final validated completion state.

Tool execution shown in the UI is a projection of runtime-owned work. The UI is not the
tool authority.

---

## 4. Wiring rule

The existing design rule remains:

```text
LBE runtime
  -> persisted session/item/event state
  -> user-facing UI renderer
```

For the reused LBE Core UI this becomes:

```text
current LBE persistent runtime
  -> normalized session/turn/item events and control APIs
  -> adapter between current runtime contracts and reusable LBE Core UI components
  -> reused/updated LBE Core user-facing TUI
```

User actions travel in the reverse direction through existing runtime owners:

```text
user action in TUI
  -> runtime control/request API
  -> existing session/request/policy/capability owner
  -> governed execution or state change
  -> resulting event/state
  -> TUI render update
```

The adapter may translate presentation contracts. It must not duplicate execution,
governance, session, or completion authority.

---

## 5. `lbe` launch behavior

The intended final user experience is:

```text
lbe
  -> launch the installed user-facing TUI
```

while explicit non-interactive commands remain available for automation and direct
administration, for example:

```text
lbe session ...
lbe provider ...
lbe code ...
lbe audit ...
lbe investigate ...
lbe policy ...
lbe permissions ...
```

Plain `lbe` must not become a second runtime. It should select/launch the user-facing UI
surface over the same installed runtime.

Until the reuse/wiring work is implemented and validated, argparse requiring a command
is an implementation-state fact, not the desired final UX.

---

## 6. Relationship to the existing CLI/TUI specification

`LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md` remains authoritative for:

- one runtime owner;
- session/turn/item lifecycle;
- runtime event projection;
- capability registry;
- approvals and continuation;
- provider/tool authority boundaries;
- replayability;
- user-visible agent/tool state;
- future GUI/external-client compatibility.

This clarification changes the implementation interpretation of the visual/client
surface:

> **Implement the user-facing TUI by reusing and adapting the existing LBE Core UI/TUI
> wherever technically compatible. Do not treat the TUI phase as permission to invent a
> new command-execution application.**

The existing LBE Core UI direction and GPT-Knowledge references are supporting design
evidence. Before coding, the exact reusable source modules must be inspected and mapped
to current runtime contracts rather than assumed.

---

## 7. Implementation gate

Before TUI implementation begins, produce a reuse map with these classifications:

```text
REUSE_AS_IS
REUSE_WITH_ADAPTER
REUSE_WITH_UI_UPDATE
SUPERSEDED_BY_CURRENT_RUNTIME
NOT_REUSABLE
MISSING_IN_CURRENT_UI
```

For each relevant LBE Core UI component, record:

- source path/module;
- original responsibility;
- current persistent-runtime owner it maps to;
- required adapter/event contract;
- whether behavior or only presentation changes;
- validation needed.

Only after that reuse map is complete should UI implementation begin.

---

## 8. Acceptance criteria

The user-facing TUI reuse/wiring slice is accepted only when:

```text
existing LBE Core UI/TUI source has been inspected
reuse map is recorded
reused UI does not own command/tool execution
reused UI does not own session/governance/completion state
current runtime remains the single authority
user actions route through existing runtime controllers
runtime events/state drive UI updates
plain `lbe` launches the user-facing TUI
explicit non-interactive CLI commands still work
session/provider/mode/permission state is consistent across CLI and TUI
resume/history/evidence/validation render from runtime-owned state
focused tests pass
full suite passes
installed-package smoke proves the same behavior
```

Until these conditions are met, do not describe a newly built terminal command runner as
the LBE TUI and do not claim the intended user-facing TUI is complete.
