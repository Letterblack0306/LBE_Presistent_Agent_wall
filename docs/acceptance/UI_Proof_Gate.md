# UI Proof Gate — LBE Terminal

Binding rules for any agent changing the LBE terminal UI or its bridge.
Same principle as the LBE implementation gate: **no proof, no save.**
"Completed", "working" and "done" are claims; only a passing proof manifest is evidence.

## 1. Scope

The gate applies when a staged change touches any of:

- `apps/lbe-terminal/**`
- `lbe_guard_inspector/tui_bridge.py`, `lbe_guard_inspector/terminal_ui.py`
- `docs/LBE_TERMINAL_UI.md` (only when behaviour is described as changed)

## 2. Reference intent: what "correct" means

Every UI change names its reference before any code is written:

1. **Spec section.** `LBE_TUI_SCREEN_SPEC.md` (v4) section numbers. The rule map is §4a; the mode labels are `ACT`, `PLAN · nothing runs yet` and `AUDIT · read-only`.
2. **Golden frames.** Owner-approved goldens for 130×38, 80×24 and 100×30 live outside the repository. Copy them into the unique `%TEMP%\agent-validation\<run-id>\golden\` directory for one validation run.
3. **Behaviour scenarios.** These are listed in §4 below.

Golden frames are **owner-approved and protected**. An agent may propose a new golden in the run's temporary directory but may not overwrite an approved source. Updating goldens to make a failing check pass is a gate violation. No new test, mock, fixture, golden or scratch-validation artifact may be created inside this repository.

## 3. How proof is produced (never by description)

Proof comes from running the **real release binary** in a headless pseudo-console, never from unit tests or previews alone.

- **Harness:** `tools/ui-proof/harness.py`. It uses pywinpty and pyte to drive the real `lbe-terminal.exe`; its generated `.txt`, `.html` and log files go only under the unique validation directory.
- **Scenario specs:** create run-specific specs under `%TEMP%\agent-validation\<run-id>\specs\`. Each spec lists keys to send, text to type, waits, and snapshots to take.
- **Environment:** use a scratch workspace under the same validation directory with its **own** `git init`, its own `LBE_WALL_DATABASE`, and an explicit `LBE_PROVIDER_CONFIG`.
- **Build:** `cargo build --release` first. The manifest records the sha256 of the exe that produced the frames.

## 4. Checks that must all pass

### A. Visual / structural (every screen)

| Case | Keys | Must show |
|---|---|---|
| idle | none | banner `LBE  ACT` with `workspace · model` when available and no connection dot; rail shows INTENT and PLAN only when an active intent exists; composer `Message LBE`; status `act · ready` |
| help | F1 | full key list; Esc closes |
| screens | F2–F8 | each screen opens, has a title, and Esc returns to the cockpit |
| palette | Ctrl+K | command list incl. `/plan /act /audit`; Esc closes |
| mode | Tab, Shift+Tab, `/audit`, `/act` | rail and status both change to the new mode within 5 s; ACT is restored afterwards |
| composer | type text | text visible in the composer |
| startup failure | missing provider config | the error states **what is missing, where, and the exact next step** (not just "bridge closed") |
| narrow tiers | 80×24, 100×30 | no wrapped or clipped labels; mode word only |
| useful-or-hidden | frames before, during and after a scripted turn | every rail line either changes across the three frames or is a decision element (approval, blocked item); nothing static remains (spec §0 rule 7) |
| no placeholders | all frames | none of `unknown`, `none yet`, `no task yet`, `n/a`, `not reported`, `bridge closed`, bare `offline` |
| live header | frames 1 s apart during a turn | the tok/s or "ago" value differs between frames; a paused provider shows amber `no output Ns` |
| plan rail | plan file with mixed states | glyphs and colours as in spec §16; the count is proved/total; collapsing works above 7 items |
| logo | launch frame | matches the owner-approved logo golden exactly; no substitute mark (spec §11) |

Every frame must also meet these conditions:

- no mojibake
- no text past the right border
- a golden diff equal to the approved golden, after masking only timestamps, ids and model names

### B. Behaviour / autonomy (live model, scratch workspace)

| Scenario | Prompt | Pass |
|---|---|---|
| read | "What does notes.txt say?" | reply quotes the file; status returns to ready; no approval asked |
| write in ACT | "Append a line to notes.txt" | approval card with `a / d / v`; after `a` the file really changed (verified with `git diff` in scratch) and a receipt exists |
| recoverable block | "Read docs/plan.md …" (file absent) | agent **checks for itself** (lists or searches), then reports that the file is absent. It does not hand the lookup back to the user |
| owner-authority block | write that needs owner intent | **exactly one** precise ask, naming the rule, what is missing and who can satisfy it. No iteration exhaustion and no repeated attempts |
| AUDIT write | "Create todo.txt" in AUDIT | refused with rule plus next step; **no file created** (verified on disk) |
| answer ≠ authority | answer a clarifying question | answer recorded as intent; no write happens without a separate approval |

Disk state and `git status` of the scratch workspace are captured before and after each scenario. A pass that the disk contradicts is a fail.

## 5. Proof manifest

The run manifest lives at `%TEMP%\agent-validation\<run-id>\manifest.json`. Capture its content and the command, hashes, frames and receipts before deleting the temporary validation files. Retain proof only in an approved evidence location outside the repository:

```json
{
  "intent_id": "LBE-INTENT-…",
  "spec_sections": ["4a", "6.2"],
  "staged_tree": "<output of git write-tree>",
  "binary_sha256": "<lbe-terminal.exe>",
  "harness_sha256": "<tools/ui-proof/harness.py>",
  "model": "lmstudio · qwen/qwen3.5-9b",
  "cases": [
    {"id": "idle", "frame": "frames/idle.txt", "frame_sha256": "…",
     "golden": "golden/idle.txt", "result": "PASS", "detail": ""}
  ],
  "scenarios": [
    {"id": "audit-write", "result": "PASS", "disk_before": "…", "disk_after": "…"}
  ],
  "verdict": "PASS"
}
```

`verdict` is computed by `scripts/check-ui-proof.py`, never typed by the agent.

## 6. The gate: changes cannot be saved without proof

**Required contract:** `scripts/check-ui-proof.py` must be wired into pre-commit and CI before either route can be called enforcing. It must block UI acceptance unless all of these hold:

1. A manifest exists for the active `intent_id` in `implementation-gates.json`.
2. `staged_tree` equals the current `git write-tree`. Any edit after the proof invalidates it.
3. `binary_sha256` matches a fresh release build of that tree. CI rebuilds and re-runs the structural cases itself.
4. Every case and scenario is PASS, and every referenced frame file exists with a matching hash.
5. No approved golden, no `tools/ui-proof/**` file and no `check-ui-proof.py` changed, unless the intent explicitly authorizes that path.

**Current implementation status (2026-10-19):** the script exists but is not wired into pre-commit or CI, and it does not yet verify the complete case/scenario contract above. No current enforcement or UI acceptance is claimed. A local hook can be skipped with `--no-verify`; CI plus branch protection and an LBE preflight integration remain required for binding enforcement.

## 6a. Plan progress is written by the gate, not the agent

- **Planned, not implemented:** `scripts/check-ui-proof.py` is to be the only writer of `state: "proved"` in `.lbe/plan/<intent-id>.json`, after a passing manifest. The plan file does not yet exist.
- A later change to files covered by a proved item's manifest must reset it to `working` until it is proved again.
- An agent-authored `proved` state must be rejected. The existing script does not yet perform these checks.

## 6b. Docs agent paths and evidence

The docs agent (spec §17) runs in AUDIT mode with its own path list in LBE preflight:

| Agent | May write | May never write |
|---|---|---|
| coding | `apps/lbe-terminal/**`, `lbe_guard_inspector/**`, plan item `working` state | `docs/**`, goldens, gate file, `tools/ui-proof/**`, `proved` state; creating new repository test artifacts |
| docs | `docs/**`, `PROPOSED` intents in the ledger, plan proposals | code, gate file, `ACTIVE`/`AUTHORIZATION` lines, goldens, plan states other than proposals |

- **Evidence for docs (planned):** a proposed `scripts/check-doc-evidence.py` would block a docs commit if a claim that something is implemented or working lacks a resolving receipt or manifest. This script does not yet exist. Unbacked statements must be written as `planned`.
- **One owner per commit.** A single commit may not mix both agents' paths, so each commit has one owner and one kind of proof.
- **Activating intents.** Making an intent `ACTIVE` stays an owner action, outside both agents.

## 7. Agent conduct

- Never write "done", "working", "fixed" or "complete" without citing the manifest path and its verdict in the same message.
- Report failures as they are: the failing case id, the frame path, and the line that differs. Do not summarize a failure as "mostly working".
- Do not weaken checks, widen masks, lengthen timeouts past the spec, or edit goldens to get a pass.
- **Retry loop:**
  1. Fix and re-run. Proof is regenerated from scratch each time.
  2. After **3** consecutive failures of the same case, stop.
  3. Report the frame and the hypothesis.
  4. Ask the owner only for missing authority or intent, never for something the agent can check itself.
- Clarifying answers from the owner are intent, not write approval (§4B, last row).

## 8. Known defects to fix first (observed live, 2026-10-19)

1. **Missing provider config is a dead end.** A fresh launch shows `provider config missing: %LOCALAPPDATA%\LetterBlack\LBE\config\provider-config.json` and `runtime bridge closed`, with no next step. No config exists anywhere on the machine, and the repo has no `config/` folder.
2. **Mouse does nothing on the mode labels.** Clicking `AUDIT` in the rail has no effect. Mouse capture is enabled, but only scroll is handled. Either support clicks or stop implying the labels are clickable.
3. **Shift+Tab mode change is unconfirmed.** The rail still showed `[ACT]` 0.6 s after the key press. Re-test with the 5 s window in §4A.
4. **CONTEXT shows `unknown` on the idle rail.** Show a real value or hide the section until known.
6. **Static rail content.** The KEYS block, SESSION and LAST RESULT are static, and the green `● connected` is a one-time handshake shown as if it were live. All of these are replaced by the live rail and header in spec v4, sections 3 and 16.
7. **The logo is not the owner's original.** The launch screen shows a bracket mark. It needs the original artwork (spec §11, open question 4).
5. **Harness setup lesson.** A scratch folder under `%TEMP%` sits inside the git repo rooted at the user's home folder, so git state is reported for the wrong repo. Always `git init` the scratch workspace (§3).

## 7. Owner golden approval record

Golden frames are approved by the owner, never by an agent. The approval is the
list of golden SHA-256 values in `.lbe/proofs/ui/approved-goldens.json`
(`{"approved_sha256": ["..."]}`), a protected path under `.lbe/**`.
`scripts/check-ui-proof.py` fails any manifest whose `golden_sha256` is not on
that list, and outside `--verify-only` it also fails unless `binary_sha256`
equals the release binary on disk. CI runs with `--verify-only` because it
cannot reproduce the exact local build.
