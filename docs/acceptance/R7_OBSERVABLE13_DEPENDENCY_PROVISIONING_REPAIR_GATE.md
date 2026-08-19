# R7 Observable 13 — Installed Cline Dependency Provisioning Repair Gate


Status: **OPEN — IMPLEMENTATION ALLOWED — ARCHITECTURE CHANGES FORBIDDEN — NEXT OBSERVABLE LOCKED**


phase: `R7_OBSERVABLE13_REPAIR_IMPLEMENTATION`


slice: `PROVISION_INSTALLED_CLINE_WORKER_DEPENDENCIES`


required_evidence_level: `INTEGRATION_PLUS_ISOLATED_INSTALLED_RUNTIME`


## Trigger


Observable 13 proved that the installed `GovernedClineWorker` cannot start.


The installed package contains:


- `runtime/cline_worker/worker.mjs`
- `runtime/cline_worker/package.json`
- `runtime/cline_worker/package-lock.json`


but its isolated installed environment does not contain or deterministically provision `@cline/agents`.


Direct Node startup fails with:


`ERR_MODULE_NOT_FOUND: Cannot find package '@cline/agents'`


The source checkout succeeds only when the ignored local `runtime/cline_worker/node_modules` dependency tree exists.


The historical Observable 3 dependency result is not accepted as self-contained installed-runtime proof because its own checkpoint records `worker_node_modules_inside_wheel: absent`, while no dependency-provisioning implementation existed.


## Authorized repair


Implement only the smallest deterministic provisioning mechanism required for the existing bounded Cline worker to resolve its pinned dependencies in an isolated installed runtime.


Preserve:


- `GovernedClineWorker`
- the current stdio protocol
- existing Cline `AgentRuntime`
- R6C authorization
- R6E `GovernedToolOrchestrator`
- `ToolReceipt`
- session/provider/completion authority
- existing `package.json` / `package-lock.json` dependency contract


## Forbidden


- runtime `npm install` / `npm ci` during an agent turn;
- dependency resolution from the repository source checkout;
- reliance on ignored local `node_modules`;
- new worker/provider architecture;
- duplicated authorization/tool/session/completion authority;
- Observable 14 work;
- release/version/tag/publish work.


## Repair hypothesis


If the existing Cline worker dependencies are provisioned deterministically as part of the installed distribution lifecycle, then a fresh isolated install can launch `worker.mjs`, resolve `@cline/agents`, perform the governed provider/tool/final continuation flow, and complete Observable 13 without dependence on source-tree state.


## Falsifiers


- isolated installed worker still produces `ERR_MODULE_NOT_FOUND`;
- dependency resolution reaches the source checkout;
- install success depends on pre-existing local `node_modules`;
- an agent turn performs dependency installation;
- package lock is bypassed or dependency versions become nondeterministic;
- existing LBE authority ownership changes;
- Observable 13 governed continuation or receipts regress.


## Validation ladder


`source/package design inspection`
→ `focused provisioning tests`
→ `fresh wheel build`
→ `fresh isolated install`
→ `direct installed worker startup`
→ `@cline/agents origin proof`
→ `installed governed provider/tool/final continuation`
→ `full Observable 13`
→ `source workspace mutation/leakage check`


Observable 14 remains locked until this repair closes PASS and Observable 13 is reclassified.
