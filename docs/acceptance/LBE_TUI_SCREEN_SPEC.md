# LBE Terminal UI — Screen Spec (v4)



Status: binding spec for any agent building or changing the LBE (Lockstep Boundary Engine) terminal UI.

Sources: `LBE Terminal Options` (cockpit rail, 8 screens), `LBE terminal UI proposal` (5 boards), `Agents_Wall_LBE_CLI_Master_Record` v3 (18 Oct 2026, sections 4, 5, 7 and 10), and the rule sources in section 4a: `LetterBlack-LBE-Core` @ `7cd5566`, `LB_Guards_Rules` @ `c404789`, `repo-governance-template` (local, 18 Oct 2026).

Where the designs show more than this spec allows, **this spec wins**. Where the brief sets a requirement, this spec meets it. Section 14 lists each place where they conflicted.



v3 adds the exact mode labels for the top banner (section 3), the rule map (section 4a), the `failed` result for checks that run after a change, and three never-show items from LBE Core's TUI direction doc.



v4 (19 Oct 2026, owner review of the live build):

- adds the "useful or hidden" rule (section 0, rule 7)

- replaces the static `● connected` dot with a live model readout (section 3)

- rebuilds the rail around live work and project progress, dropping KEYS (section 3 and section 16)

- adds the parallel docs agent (section 17)

- requires the owner's original logo files (section 11)



Section 13 and section 14 are updated to match. Every change has to be proved through `UI_Proof_Gate.md`.



---



## 0. Rules for the agent building this



1. Build exactly what this spec lists. If a region, label or line is not listed here, it does not appear on screen.

2. Do not add explanatory copy about how LBE works (authority, receipts, evidence, proof). That belongs in docs, not on screen.

3. Section 10 (NEVER SHOW) is a hard list. Any item there that reaches the default view is a bug.

4. Internals appear only in the **Details layer** and the **Receipts screen** (section 8), opened by a key press.

5. The UI displays and requests. It never decides. Every state it shows (mode, paused, connected, passed, blocked) must come from the runtime, not from the UI's own guess. A label changes only after the runtime confirms the change.

6. If you are unsure whether something belongs on screen, leave it out and list it in your hand-off note as "held back".

7. **Useful or hidden.** An element may stay on the default view only if it meets one of two tests:

   - it changes while work is happening, or

   - the user needs it for a decision right now.



   Anything learned once (key lists, legends, explanations) lives behind F1 or an F-screen. Empty space stays empty: never fill it with placeholders such as `unknown`, `none yet` or `no task yet`; hide the section until it has a real value. When things are healthy, stay quiet; when something breaks, say it loudly with the next step.



## 1. The one idea



The user sees **what is happening, which rule LBE applied, and the result**. Nothing else by default.



- LBE is the only authority in **every** mode. AUDIT adds investigation and visibility. It never adds permission, and it is not a separate policy engine.

- Mode: PLAN, ACT or AUDIT. Always visible. (In the brief's terms, Normal = PLAN + ACT.)

- The top banner always shows the product name and the current mode. In AUDIT it reads `LBE  AUDIT · read-only`.

- Each LBE decision is **one line**: rule → target → result (passed / blocked / needs you).

- A block always shows the next step. The screen never just stops.



**One-glance test (brief §10):** a non-technical operator can read the current task, model, scope, last decision and outcome from the default view, and can reach the evidence with one key.



## 2. Layout



```

┌ header ─────────────────────────────────────────────────────┐

│ transcript                                     │ rail (30ch)│

│                                                │            │

├ composer ───────────────────────────────────────────────────┤

└ status (one quiet line) ────────────────────────────────────┘

```



### Size tiers (minimum 60 × 18)



| Tier | Size | Rail | Bottom |

|---|---|---|---|

| Wide / standard | ≥ 100 cols | on, 30 cols, right side | composer + status |

| Compact | 60–99 cols | folds into one status line: `● act · fix --version · 4.1k/8k · F1 keys` | composer below it |

| Very short | < 20 rows | no header | composer with mode at the right: `❯ Message LBE      act` |



F1 opens a keys popup in the folded tiers. F-key labels never sit on the status line.



The plain text CLI (scripted/CI use) prints the same rule lines and effect lines as section 4, one per line, with no rail or colour. The TUI and the CLI share one vocabulary.



## 3. Regions: what is allowed



### Header / top banner (1 line)

- Left: mark `[┃]` + `LBE` + the mode label. Example: `[┃]  LBE  AUDIT · read-only`

- Right side, which must be **live or absent**:

  - **Idle:** `workspace · model`, muted. No connection dot. A one-time handshake result is not a live signal.

  - **During a turn:** `model · 41 tok/s · 0.8s ago`. These come from the bridge's stream: throughput over the last 5 s, and time since the last token. They update at least every second.

  - **Stalled:** no token for longer than the provider's stall threshold (default 20 s). The readout turns amber: `model · no output 23s`.

  - **Broken:** the provider or control plane is unreachable. The right side is replaced by one red line naming the cause and the next step, for example `LM Studio not answering · start it or F2` or `provider config missing · F4 to set it`. It never says only `offline` or `bridge closed`.

  - **F-screen:** the right side reads `F5 capabilities   esc back`.



**Mode labels (exact wording):**



| Mode | Wide tier | Compact / very short tier |

|---|---|---|

| ACT | `ACT` | `ACT` |

| PLAN | `PLAN · nothing runs yet` | `PLAN` |

| AUDIT | `AUDIT · read-only` | `AUDIT` |



- The mode word is red and bold. The qualifier after `·` is muted.

- The label changes only after the runtime confirms the mode switch (section 0, rule 5).

- The label never says who is in control ("LBE is in control", "LBE is leading"). LBE governs every mode, so the label only describes what the mode does for the user.



### Transcript

Allowed line types only. Together they form the readable activity timeline (proposal → decision → effect):



| Type | Format | Example |

|---|---|---|

| User turn | `you  ` muted + text | `you   scan brew and report what is uncommitted` |

| Agent reply | `<agent>  ` red + plain text | `lbe   Two files are uncommitted.` |

| Rule line | see section 4 | `  ✓ change in scope      src/cli.py      passed` |

| Effect line | `✓` / `■` + observed result | `✓ 1 file changed · checks passed` |

| Question | `?` amber + question | `? Should --version also print the engine?` |

| Lifecycle line | muted | `paused by you · 14:02`  /  `stopped · step 2 of 3 not run` |

| Mode entry / exit line | muted, see section 5 | `── AUDIT started · read-only, nothing will change ──` |

| Next-step hint | muted, one line | `Say /audit to widen scope, or press F6 for the report.` |



Rule lines per turn: show at most **3**. Collapse the rest to `  +4 more rules passed   d details`. A blocked rule is always shown, never collapsed.



An effect line reports the **observed** effect ("1 file changed"), never the tool's own claim ("patch applied", "exit 0").



### Rail (wide tier only), PLAN / ACT



The rail answers two questions at a glance: **where the project stands**, and **what is happening right now**. Every line in it is fed by runtime events and changes as work happens.



```

INTENT  TUI v4 · 3/7

✓ provider config next step

✓ live header

▸ rail live sections

· contextual keys

· mouse mode switch

! narrow tiers

  needs golden · F7

─────────────────────────

NOW     editing chrome.rs

        step 3 of 5

CHANGED 2 files  · d list

READ    README.md +4

WRITES  allowed

CONTEXT ▕█████░░░▏ 38%

TIME    2m14s · iter 4

DOCS    updated 1m ago

```



Sections, top to bottom:



- **INTENT and PLAN.** See section 16.

- **NOW.** The step the agent is on, in plain words, plus `step n of m`.

- **CHANGED and READ.** Live counts and names of files touched in this task, observed from disk or receipts.

- **WRITES.** `allowed`, `needs approval` or `blocked · <rule>`, as the gate reports it for the active intent.

- **CONTEXT.** Context used, as a bar and a percentage.

- **TIME.** Elapsed time and iteration count. The line turns amber when iterations approach the limit.

- **DOCS.** When the docs agent last updated (section 17).



Rules:

- **Before the first task:** the rail shows only INTENT and PLAN, or nothing if there is no active intent. It never shows placeholder sections.

- **Removed from the rail:**

  - KEYS. It is learned once, so it moves to F1 (section 0, rule 7).

  - SESSION. The model is already in the header, and the mode in the banner and status.

  - LAST RESULT. It is now the latest effect line in the transcript, and the plan item it moved.

- **Contextual keys:** a key hint appears only where it applies, as one muted line under the element:

  - `a allow · d deny · v view` under a pending approval

  - `Ctrl+X stop` in the status while a turn runs

  - `d list` next to CHANGED

- **Mode switching by mouse:** clicking `PLAN`, `ACT` or `AUDIT` wherever a mode label is shown sends the same mode request as the keyboard. If the build does not support mouse clicks, mode words must not be laid out to look clickable.



AUDIT replaces the rail body (section 5). No receipt ids, no event names and no readiness ladders in the rail.



### Composer

`❯ Message LBE` with cursor. In AUDIT with open questions, the placeholder becomes the prompt: `❯ Answer ? 1 with a, b or free text`.



### Status (1 line)

`● <mode> · <state>` on the left, `? help` on the right. Example: `● act · executing ■`

- State words only: `ready`, `thinking`, `executing`, `waiting for you`, `blocked`, `clarifying`, `pausing…`, `paused`, `stopping…`, `stopped`, `resuming…`.

- Dot colour: green ready/executing, amber waiting/clarifying/paused, red blocked/stopped.

- The bouncing `■` shows only while work is in flight, and is removed when motion is off.



### Lifecycle keys (brief §5)

| Key | Action | Rule |

|---|---|---|

| `Ctrl+P` | pause / resume | Show `pausing…` until the runtime confirms in-flight work has paused, and only then `paused`. |

| `Ctrl+X` | stop current task | Ask once: `Stop "fix --version"? step 2 of 3 is running  y stop · n keep going`. Show `stopping…` until confirmed. |

| on relaunch | resume prompt | `Resume "fix --version"? last confirmed: step 1 done  r resume · n new`. Never re-run a step whose effect is unknown without asking. |



## 4. Rule line: the core element



Grammar: `<glyph> <rule name, plain words>   <target>   <result>`



```

  ✓ intent recorded        add --version flag      passed

  ✓ change in scope        src/cli.py              passed

  ■ change in allowed files  C:\ProgramData\lbe    blocked

      not in the task's allowed files  ·  next: narrow the change   (r retry · d details)

  ? approval needed        tests/test_cli.py       needs you

```



- Glyphs: `✓` green passed, `■` red blocked, `✗` red failed, `?` amber needs you, `~` amber partial, `i` muted advisory.

- Result words:

  - `passed`: the check ran and was satisfied

  - `blocked`: stopped **before** any effect, so nothing changed

  - `failed`: the check ran **after** a change and found it wrong, for example `CHANGED_OUTSIDE_SCOPE`. The change did happen, so the `next:` line must offer the rollback.

  - `needs you`: waiting on the user

- Rule name = the plain screen name from the rule map (section 4a). Never the internal id. The id (`CHANGED_OUTSIDE_SCOPE`, `secret-file-guard`) appears only in details.

- Target = file, path, command or intent, truncated from the left to fit (`…/src/cli.py`).

- **Blocked** always adds exactly one indented line: the reason in 8 words or fewer, then `next:` and one concrete action taken from LBE's block response. If LBE gives no next step, show `next: ask LBE why (d)`. A blocked line is never left without a `next:`.

- A DENY line also means **nothing happened**. If the runtime cannot confirm that no effect occurred, show `~ effect unknown · d details` instead of `■ blocked`.

- A `failed` line follows the same one-extra-line rule as `blocked`: reason, then `next:`.



## 4a. Rule map: where rule names and `next:` steps come from



The TUI never invents a rule name or a next step. Every rule line is looked up here by the id the runtime returns. An id that is not in this map shows as `■ <id as plain words>   blocked`, with `next: ask LBE why (d)`, and the build agent adds it to this map.



### A. LBE Core audit statuses

Source: `LBE_Core_Engine/src/state/auditMode.js` (`AUDIT_STATUS`) and `src/state/blockerRegistry.js`.



The `next:` options come from the registry's `decisionOptions`, in its order. Show the first option as `next:`; the rest go behind `o more options`. The `forbidden` field goes to details.



| Id | Screen name | Result | Reason (≤ 8 words) | `next:` (from decisionOptions) |

|---|---|---|---|---|

| `NO_SCOPE_FOUND` | task scope set | blocked | no task scope registered | set scope · ask you |

| `REQUIRED_READING_MISSING` | required reading done | blocked | required files not read yet | read the files · update scope · ask you |

| `NO_INTENT_FOUND` | intent recorded | blocked | no intent before changes | record intent · ask you |

| `INTENT_SCOPE_MISMATCH` | intent matches scope | blocked | intent points at another scope | record intent again · ask you |

| `CHANGED_OUTSIDE_SCOPE` | change in scope | **failed** | files changed outside allowed scope | roll back · expand scope · ask you |

| `FORBIDDEN_FILE_TOUCHED` | forbidden files untouched | **failed** | a forbidden file was changed | roll back · update scope · ask you |

| `MISMATCH_DETECTED` | proof matches work | **failed** | proof found mismatches | fix violations · update scope · ask you |

| `VALIDATION_MISSING` | checks run | blocked | required checks not run | run checks · ask you |

| `PROOF_INCOMPLETE` | proof complete | blocked | proof cycle not finished | run proof · ask you |

| `CLEAN` | all checks | passed | — | — |



"Expand scope" and "update scope" are never done silently. They open an approval prompt (section 6), because the registry forbids "silently widen scope".



### B. LB Guards, the default required set

Source: `LB_Guards_Rules/.workspace-trust/policy.json` (`requiredGuards`).



Guards return only `{ success, errors[] }`, with no next step, so the `next:` column below is defined by this spec. The guard class comes from the Guards README and sets the glyph:

- execution/security boundary → `■ blocked`, and never offer a bypass

- scope → `■ blocked`

- quality/test → `✗ failed`

- advisory → `i`, never `■`



A failed guard blocks only its own stage. Other authorized work keeps going.



| Guard id | Screen name | Class | Stage | `next:` |

|---|---|---|---|---|

| `push-without-test-proof-guard` | tests proven for this commit | quality | push | run tests for this commit |

| `claim-without-proof-guard` | claim backed by proof | quality | done / commit | run tests, then claim again |

| `missing-module-guard` | imports resolve | quality | any change | add the missing module or dependency |

| `duplicate-index-guard` | one index per folder | quality | any change | remove or merge the duplicate index |

| `empty-button-guard` | buttons labelled | quality | any change | add a label to the button |

| `feature-owner-guard` | owner declared | scope | any change | declare the owner, or ask you |

| `generated-pollution-guard` | no generated files | quality | commit | remove or ignore generated files |

| `secret-file-guard` | no secret files | security | commit | remove the file and rotate the secret |

| `destructive-command-guard` | command is safe | security | run | use a safe command, or ask you |

| `wrong-workspace-guard` | right workspace | security | any | switch to the right workspace |



The other 22 registered guards (`src/guards/index.js` imports 32) are not in the default set. They are added here only when a workspace profile requires them.



### C. Repo governance template

Source: `repo-governance-template/ROOT_GOVERNANCE/` (`task-contract.md`, `ownership-map.json`, `architecture/architecture-signoff.json`).



| Rule | Screen name | Result | `next:` |

|---|---|---|---|

| No task contract | task contract exists | blocked | write the task contract |

| File not in Allowed Files | change in allowed files | blocked | narrow the change · ask you to add the file |

| Agent role denies the path | role allows this path | blocked | hand to the right role (e.g. fix agent) |

| Protected zone, no active signoff | protected zone signed off | blocked | request architecture signoff |

| Signoff expired | signoff still valid | blocked | request a new signoff |



### D. CLI exit codes (`lbe verify`)

Source: `LBE_Core_Engine/docs/CLI_EXIT_CODES.md`.



The plain CLI prints these as rule lines too.



| Code | Screen name | Result | `next:` |

|---|---|---|---|

| 2 | policy allows this | blocked | change the proposal, or ask you |

| 3 | signature valid | blocked | re-sign the proposal |

| 4 | not a replay | blocked | send a fresh proposal |

| 5 | proposal well-formed | blocked | fix the proposal file |

| 6 | clock in sync | blocked | check the system clock, then retry |

| 7 | within rate limit | blocked | wait, then retry |

| 8 | policy state valid | blocked | ask LBE why (d) |



### E. Owner authority rules

Source: `lbe_guard_inspector/authority_ownership.py` and `governed_coding.py`.



Emitted by this runtime's owner-authority gate.



| Rule id | Screen name | Result | Reason | `next:` |

|---|---|---|---|---|

| `OWNER_AUTHORITY_BLOCKER` | owner sign-off supplied | blocked | owner sign-off was not supplied | ask the owner to attach their sign-off |

| `OWNER_SCOPE_VIOLATION` | change within owner scope | **failed** | changed files outside the owner scope | roll back · ask you |



## 5. Modes



### ACT (default working mode)

Transcript, rule lines and one effect line per completed action. Rail as in section 3.



### PLAN

Banner label: `PLAN · nothing runs yet`. Body:

```

Goal      Ship `lbe --version` and prove it works

Assumed   version comes from installed metadata

Unknown   ? should --version also print the engine?



  1  Add --version to the CLI entry point     cli.py              medium

  2  Read version from package metadata       cli.py              low

  3  Cover it with a test                     tests/test_cli_v…   low



Check     pytest tests/test_cli_version.py

Changes   2 files if approved. Nothing has changed yet.



[A] approve → ACT   [R] revise   [Q] answer question   [E] export

```

Rail: `PLAN STATE proposed` · `TOUCHES 2 files` · `NEEDS 1 answer`. Approving switches mode only. Each ACT step still gets its own rule lines.



### AUDIT

Banner label: `AUDIT · read-only`, for as long as the mode lasts.



**On entry**, print one muted line in the transcript, once:

```

── AUDIT started · read-only, nothing will change ──────────────────────────────

```



Body, in this order:

1. Phase crumbs: `scope → investigate → [clarify] → report` (current phase red and in brackets, done phases white, upcoming muted).

2. `QUESTIONS FOR YOU   2 open · 1 answered`. Each question has `? n`, the question, one muted line of up to 2 evidence files, and options `[a] … [b] … [c] other…`.

3. `FINDINGS`, one line each: `✓ F1 proven` / `~ F2 unverified · needs Q2` / `· F3 checking` + plain title.



Rail in AUDIT:

```

SCOPE

src/, docs/

read-only



READ

14 files

nothing changed



COVERAGE

▕█████████░░░▏ 9/12



REPORT

draft · 2 open Qs

F6 preview



NOT VERIFIED

runtime behaviour

on this machine

```

**On exit**, print one line: `AUDIT ended · report draft saved · F6 to open`.



## 6. Approval prompt (brief §5: precise action, actor, workspace, target, side effects, expiry)



```

  PERMISSION NEEDED                                          expires in 4:59

  claude-code wants to write  tests/test_turn_path.py

  in brew · creates 1 file · changes nothing else

  a allow once    d deny    v view change

```

- Line 2 = actor + action + target. Line 3 = workspace + side effects, in plain words.

- "Allow once" is bound to this exact action and target. If the agent changes the target or content, a new prompt appears and the old approval does not carry over.

- If the prompt expires, it is replaced by `■ approval expired · nothing changed · r ask again`.

- After the answer, the prompt is replaced by a single effect line: `✓ written · tests/test_turn_path.py` or `■ denied by you · nothing changed`.

- Not shown: call id, receipt id, gate checklist (intent → policy → execution → validation → promote). Those are in details.



## 7. Capabilities truthfulness (brief §5)



- F5 and the header show only capabilities the runtime **discovered**. Nothing is pre-filled from config.

- Offline or unhealthy items show `○ offline` or `~ unhealthy`. They never get a green dot or an active style.

- `configured`, `connected` and `healthy` are three separate columns and are never merged into one "ok".



## 8. Details layer and Receipts screen (the only places internals live)



**Details (`d`)** on any rule, effect, approval or lifecycle line opens a pane for **that line only**. `Esc` closes it. It may show:

- the full chain for that action: request → actor/session → workspace → LBE decision → adapter → observed effect → receipt

- receipt id, policy revision, execution window, errors

- evidence label, using the brief's vocabulary only: `PROVEN`, `IMPLEMENTED`, `DOCUMENTED`, `INFERRED`, `UNVERIFIED`, `BLOCKED`, `DISPROVEN`



**F8 Receipts** is a browsable list, newest first: `time · action · target · decision · effect`. `Enter` opens the same details pane. `/` filters.



Nothing from details leaks back into the transcript after the pane closes.



## 9. F-key screens



All F-screens reuse the frame (header, rail, composer, status). `Esc` goes back.



| Key | Screen | Show | Cut from the mock |

|---|---|---|---|

| F2 | Providers | `provider · sign-in · state`, with state as one word: `ready` / `sign in` / `key not set`. `Enter select · t test · a add custom` | engine column, readiness-ladder rail, credential explainer copy |

| F3 | Models | `model id · context · tools` (`—` when unknown). `Enter select · c run checks` | catalog explainer sentence |

| F4 | Settings | menu: Session, Providers, Capabilities, Memory & history, Display, Workspace policy. Session shows mode, permission, policy and session id. Display: colour, glyphs, motion. Workspace policy: read-only, one line `edited outside the UI` | owner-authority token text, long policy explainer |

| F5 | Capabilities | `name · kind · configured · connected · healthy` (section 7). BirdEye row shows `27 tools`, plus a warning only when unhealthy | "STATE WORDS" explainer rail, governed-call copy |

| F6 | Report | numbered sections: scope, findings with evidence links, open questions, not verified, next steps. `x export · Esc back` | "generated from persisted evidence" subtitle |

| F7 | Sessions & tasks | list: `▸ Wire the governed turn path · paused`, current first, then queued, then past. `Enter open · n new · r resume` | — |

| F8 | Receipts | section 8 | — |



## 10. NEVER SHOW in the default view



- The words `LBE live`, `governed`, `authority`, `authority bridge`, `promotion`, `consequence`, `proof` (as a label), `receipt` or receipt ids (`r-7f3a`, `rcpt_…`)

- Raw runtime events: `runtime.provider.running`, `tool.requested`, `tool.completed`, or any `dotted.event.name`

- A raw event log or ACTIVITY panel. The transcript lines are the timeline.

- Tool function names as the main label (`workspace_run`, `birdeye_inspect`, `workspace.patch`). Use the rule name instead.

- Evidence labels (PROVEN, INFERRED…) in ACT or PLAN. Use the `✓ ~ ■ ?` glyphs. AUDIT findings may use `proven` / `unverified`.

- Gate or pipeline checklists, call ids (`lbe-call-014-01`), hashes, session ids, SIDs, turn counters

- Policy explainer sentences ("Selecting a provider does not grant authorization…", "A provider completion is not promotion proof…")

- A tool's own success claim presented as the effect ("exit 0", "patch applied")

- Debug labels, `mock`, `[model]` placeholders, JSON

- Tokens, secrets, raw audit logs or raw shell output (LBE Core `docs/LBE_TUI_PRODUCT_DIRECTION.md`). A command's output goes to details, trimmed to what the rule line needs.

- Status codes or guard ids (`NO_SCOPE_FOUND`, `secret-file-guard`) as the main label. Use the section 4a screen name; the id goes to details.

- More than one line per rule, except the single `next:` line on a block

- A permanent key list (KEYS block) or any legend; these belong behind F1

- Placeholder values: `unknown`, `none yet`, `no task yet`, `n/a`, `not reported`

- A static "connected" or "online" indicator; the header readout is live or absent (section 3)

- Errors that name a symptom without a cause and a next step (`runtime bridge closed`, `offline`)



## 11. Visual tokens



| Token | Value | Use |

|---|---|---|

| bg | `#0b0c15` | terminal body (outer `#06070d`) |

| panel | `#12131d` | rail |

| fg | `#e9e9ef` | text |

| muted | `#8e8e93` | labels, hints |

| rule | `#2a2a2d` | dividers, empty bar |

| red | `#ef4b4b` | **only** the logo bar, the active mode word (banner and rail), and blocked/stopped/offline |

| green | `#4ade80` | passed, proved plan items, ready (never a static "connected") |

| amber | `#e5b567` | needs you, partial, paused, F-key letters |

| chip | `#1c1d29` | selected row |



- Font: JetBrains Mono / Cascadia Code / Consolas. Section labels uppercase, muted, bold.

- `NO_COLOR` set or output piped: no escape codes, but keep bold and the glyphs `✓ ■ ? ~` so meaning survives.

- `LBE_ASCII` / legacy console: `[|]` mark, `+ - |` box chars, `v x ? ~` glyphs.

- Motion off: no bouncing indicator.

- Logo: half-block mark, 22 × 12, shown **once** on launch or in an empty session, and gone on the first message. Files: `lbe_mark.ansi`, `lbe_mark.txt`, `lbe_mark_cells.json`. Header mark elsewhere: `[┃]`, or `[|]` in monochrome, or just `LBE` when very narrow.

- **The logo must be the owner's original.** The mark files are generated from the owner's original logo artwork, and nothing else. The agent may not draw, simplify or substitute a mark.

- **What the live build does today.** On 19 Oct 2026 the build showed a bracket mark (`[│] Lockstep Boundary Engine`) in place of the 22 × 12 mark, and the owner rejected it as not their logo.

- **Until the original is supplied:** show the word `LBE` only, and list "logo source missing" as held back.

- **Proof:** the proof gate compares the launch frame against a golden that the owner approved from the original artwork.



## 12. Reference frames



### ACT, wide

```

[┃]  LBE  ACT                                  brew · gemma-4-e4b · 38 tok/s · 0.6s ago

──────────────────────────────────────────────────────────────────────────────────────────────

you   Add a --version flag to the CLI                           │ INTENT  cli-version · 2/4

                                                                │ ✓ --version flag

lbe   Added --version. It prints the package version, exits 0.  │ ✓ version test

  ✓ intent recorded        add --version flag      passed       │ ▸ write version file

  ✓ change in scope        src/cli.py              passed       │ · update README

  ✓ checks run             tests/test_cli.py       passed       │ ────────────────────────────

✓ 1 file changed · checks passed                                │ NOW     writing version.txt

                                                                │         step 1 of 2

you   Now write it to C:\ProgramData\lbe\version.txt            │ CHANGED 1 file  · d list

                                                                │ WRITES  blocked · allowed

lbe   I can't write there.                                      │         files

  ■ change in allowed files  C:\ProgramData\lbe    blocked      │ CONTEXT ▕█████░░░▏ 51%

      not in allowed files · next: narrow the change        │ TIME    1m02s · iter 3

                                                                │ DOCS    updated 20s ago

──────────────────────────────────────────────────────────────────────────────────────────────

❯ Message LBE

● act · blocked                                                                        ? help

```



### Approval

```

lbe   One change before validation.                             │ INTENT  TUI v4 · 3/7

                                                                │ ✓ provider config next step

  PERMISSION NEEDED                          expires in 4:59    │

  claude-code wants to write  src/turn_path.py                  │ ▸ rail live sections

  in brew · changes 1 file · changes nothing else               │ · contextual keys

  a allow once    d deny    v view change                       │ · mouse mode switch

                                                                │   needs golden · F7

                                                                │ NOW     reviewing change

                                                                │ WRITES  needs approval

                                                                │         a allow · d deny · v view

──────────────────────────────────────────────────────────────────────────────────────────────

❯ Message LBE

● act · waiting for you                                                                ? help

```



### AUDIT entry

```

[┃]  LBE  AUDIT · read-only                                          brew · gemma-4-e4b

──────────────────────────────────────────────────────────────────────────────────────────────

── AUDIT started · read-only, nothing will change ────────────────────────│ SCOPE

                                                                          │ src/, docs/

scope → investigate → [clarify] → report                                  │ read-only

                                                                          │

QUESTIONS FOR YOU   2 open · 1 answered                                   │ READ

 ? 1  Which provider counts as the production default?                    │ 14 files

        provider-config.json, docs/CURRENT_STATUS.md                      │ nothing changed

        [a] lmstudio   [b] openai-compatible   [c] other…                 │

 ✓ 3  Scope is src/ and docs/ only, you answered: yes                     │ COVERAGE

                                                                          │ ▕█████████░░░▏ 9/12

FINDINGS                                                                  │

 ✓ F1 proven      Installer resolves the checkout, not the package        │ REPORT

 ~ F2 unverified  Policy files disagree on max_patch_bytes · needs Q2     │ draft · F6

──────────────────────────────────────────────────────────────────────────────────────────────

❯ Answer ? 1 with a, b or free text

● audit · clarifying                                                                   ? help

```



## 13. Acceptance checklist (the agent checks every item before saying done)



UI checks:

- [ ] The default view at 120 × 40, 80 × 24 and 60 × 18 matches the tiers in section 2

- [ ] Searching the default-view render for every term in section 10 finds nothing

- [ ] Every blocked or failed rule line has exactly one `next:` line

- [ ] Every rule name on screen is in section 4a, or was added there by this hand-off

- [ ] A `CHANGED_OUTSIDE_SCOPE` result shows `✗ failed` with `next: roll back`, never `■ blocked`

- [ ] "Expand scope" opens an approval prompt and never widens scope on its own

- [ ] No turn shows more than 3 rule lines without the `+n more` collapse

- [ ] The banner shows the exact mode label from section 3 in every mode, and only after the runtime confirms the switch

- [ ] The AUDIT entry line appears once on entry, and the exit line once on exit

- [ ] `d` opens details for one line; `Esc` closes it; the transcript is unchanged afterwards

- [ ] `NO_COLOR=1` render keeps the glyphs and bold; `LBE_ASCII=1` render uses ASCII only

- [ ] Red appears only in the allowed places

- [ ] Every default-view element changes during a scripted turn or is needed for a decision (section 0, rule 7). The proof harness diffs the rail between before, during and after a turn, and any line that never changes and is not a decision fails.

- [ ] No placeholder value from section 10 appears in any captured frame

- [ ] The header tok/s and "ago" values change at least once per second during a turn, and the header shows the amber stall text when the provider is paused

- [ ] A missing provider config on launch shows the cause, the path and the next step, not `bridge closed`

- [ ] Plan items move to ✓ only when their proof manifest passes (section 16)

- [ ] The launch frame matches the owner-approved logo golden (section 11)



Truth checks (brief §7 and §10: a mock or a green test suite is not enough):

- [ ] One-glance test: a person who did not build it names task, model, scope, last decision and outcome from a capture of the default view

- [ ] One real ALLOW through the TUI: the effect line matches the observed file change, and F8 shows the matching receipt

- [ ] One real DENY through the TUI: nothing changed on disk, and the blocked line shows `next:`

- [ ] `Ctrl+P` during a running step: work actually pauses (no further effects), and only then does the status read `paused`

- [ ] `Ctrl+X`, then relaunch: the resume prompt appears, and no step runs twice

- [ ] Unplug the control plane: the header shows one red line naming the cause and the next step, and F5 shows nothing as healthy

- [ ] The docs agent runs during a real task, writes only inside its allowed paths, and a write attempt outside them is blocked with a receipt (section 17)

- [ ] Captures of ACT, PLAN, AUDIT, a block, an approval and paused are attached to the hand-off, taken from the installed build rather than a dev checkout



## 14. Decisions where sources disagreed



| # | Topic | Templates | Brief | Decision |

|---|---|---|---|---|

| 1 | F-key labels | status line (Options) vs rail (board 1) | — | v4: neither. F1 only, plus contextual hints (owner review, 19 Oct) |

| 2 | Activity | ACTIVITY event stream | "structured chronological events … with detailed drill-down" | the transcript lines are the timeline in plain words; drill-down via `d` and F8. No raw event panel. |

| 3 | Receipts | listed in the rail | TUI owns "receipt browsing" | off the rail, onto the new F8 Receipts screen |

| 4 | Approval content | call id, scope text, gate checklist | actor, workspace, target, side effects, expiry | brief's fields in 3 plain lines; ids and the gate go to details |

| 5 | Evidence labels | PROVEN / SUPPORTED / HYPOTHESIS / UNKNOWN / BLOCKED | PROVEN / IMPLEMENTED / DOCUMENTED / INFERRED / UNVERIFIED / BLOCKED / DISPROVEN | brief's list, in details only |

| 6 | Modes | PLAN / ACT / AUDIT | Normal / Audit, one authority | keep the three runtime modes; Normal = PLAN + ACT; AUDIT never adds permission |

| 7 | Pause / stop / resume | not shown | required, must affect real work | `Ctrl+P`, `Ctrl+X`, resume prompt, with "…ing" states until confirmed |

| 8 | Task, scope, connection | sessions list on board 5 only | Home must show task queue, live connection, last verified outcome | v4: the PLAN list is the task queue; a *live* model readout replaces the connection dot; the last verified outcome is the latest effect line plus ✓ plan items; F7 for full plan and sessions |

| 13 | Static rail content | KEYS, SESSION, placeholders | one-glance test | owner review 19 Oct: only live or decision-relevant content (section 0, rule 7) |

| 14 | Docs while coding | one agent does both | — | a parallel docs agent in AUDIT mode (section 17) |

| 9 | Session id | in status | server-owned session | off the status line, onto F4 → Session and details |

| 10 | Status labels on screen | LBE Core scope contract: "normal user-facing output should use labels only" (`NO_SCOPE_FOUND` …) | non-technical operator test | plain screen names from section 4a; the codes go to details and the plain CLI's `--json` |

| 11 | Before vs after checks | LBE Core audit checks run after the change (proof) | DENY must cause no effect | new `failed` result, so a post-change check is never shown as a block that "stopped" anything |

| 12 | AUDIT label | "LBE is in control" banner across the transcript | LBE is the authority in every mode | top banner reads `LBE  AUDIT · read-only`; the transcript gets one muted entry line; no wording about who is in control |



## 15. Open questions for the owner



1. **Where the TUI is built**: LBE Core's `tasks/ACTIVE_TASK.json` (LBE-P1-001) forbids `src/tui/**` and "TUI work". Building this spec there breaks that task. It needs either its own active task or the separate terminal-integration repo (draft PR #1, 17 Oct per Master Record v3).

2. **Guard next steps**: guards return no next step, so section 4a B is this spec's own wording. Should guards return a structured `next` field the way LBE Core's blocker registry does? That would let the guards repo own the wording.

3. **Source freshness**: discover the current BirdEye workspace and Git revision at execution time. LBE Agent Wall is C:/Agents-Memory-Tool-v6-integration (2026-10-22); historical LBE Core references are not live workspace authority.

4. **Logo source**: where is the original logo artwork? `lbe_mark.*` must be regenerated from it, and the launch golden approved by the owner (section 11).



## 16. Plan and project progress (v4)



The user must be able to see how far the whole intent has got, not just the current turn.



**Source.** The plan file is `.lbe/plan/<intent-id>.json`. It is a list of items, each with:

- `id`

- `title`, at most 28 characters so it fits the rail

- `state`

- `proof`, the path of the item's proof manifest, or null

- `blocked_reason` and `next`, used only when blocked



The bridge sends a new `plan` event (bridge to client) whenever the file changes. The client never edits plan state itself.



**States and glyphs:**



| State | Glyph | Colour | Who sets it |

|---|---|---|---|

| pending | `·` | muted | coding agent or docs agent (proposal) |

| working | `▸` | fg, bold | coding agent, one item at a time |

| blocked | `!` | amber, red if an owner-authority block | runtime, with reason and next |

| proved | `✓` | green | **only** `scripts/check-ui-proof.py`, when the item's proof manifest passes |



**Rules:**

- **Only a passed check marks an item done.** No agent can set `proved`; the check script writes it after a passing manifest. If a proved item's files change later, it drops back to `working` until it is proved again.

- **The count** in the INTENT line (`3/7`) is proved over total.

- **One working item at a time.** If the agent starts a second item, the first must be proved or explicitly paused.

- **Space.**

  - The rail shows the INTENT line plus up to 7 items.

  - With more items it shows proved items collapsed (`✓ 4 proved`), the working item, the next 3 pending, and all blocked items.

  - A blocked item always shows, with its reason on a second muted line.

- **Detail.** F7 opens the full plan: every item with its state history, proof manifest path and receipts.

- **Compact tier.** The folded status line gains a `3/7` count. The plan itself is on F7.

- **Adding items.** New plan items are drafted by the docs agent (section 17) as `pending · proposed`, and appear muted and italic. They join the count only after the owner accepts them, with `/plan accept <id>` or in F7.



## 17. Parallel docs agent (v4)



A second agent runs alongside the coding agent and keeps intent and backend docs current, so the coding agent can stay on code.



**Mode and authority.**

- It always runs in **AUDIT** mode. That mode may write intent and plans, never code (section 5). LBE governs it exactly like the coding agent: every write goes through preflight and leaves a receipt.

- **Allowed writes:**

  - `docs/**`

  - intent drafts in `docs/governance/PROJECT_INTENT_LEDGER.md`, always `STATUS: PROPOSED`

  - plan items, as proposals only

  - `docs/LBE_TERMINAL_UI.md`

- **Forbidden writes:**

  - any code path

  - `.lbe/governance/implementation-gates.json`

  - any `STATUS: ACTIVE` or `AUTHORIZATION:` line

  - golden frames

  - `tools/ui-proof/**` and `scripts/check-ui-proof.py`

  - plan states other than proposals



  Activating an intent remains an owner decision every time.



**Input: evidence only.**

- It works from the coding agent's receipts, diffs, proof manifests and plan events as they land. It does not read the coding agent's chat.

- Every doc statement about behaviour cites a receipt or proof manifest. A statement with no evidence is written as `planned`, never as implemented.



**No collisions.**

- The coding agent never writes under `docs/`, and the docs agent never writes outside its allowed paths. LBE preflight enforces both from a per-agent path list.

- Each agent commits separately. A code commit needs its proof manifest (`UI_PROOF_GATE.md`). A docs commit needs every behaviour claim to resolve to an existing receipt or manifest; `scripts/check-doc-evidence.py` checks this.



**Cost.** It may run on a cheaper or local model, because it summarises evidence and never decides.



**On screen:**

- The rail's DOCS line shows its last update time. It turns amber if the docs are more than one proved plan item behind.

- `Ctrl+T` switches the transcript between the coding agent and the docs agent.

- The docs agent's transcript uses the same line types (section 3), with the agent name `docs`.

- It never interrupts the main transcript. Its questions to the owner appear only as one amber count on the DOCS line (`DOCS 2 questions · Ctrl+T`).

