# Agent Evaluation Transcripts

Cross-workspace Cline session transcripts preserved for historical reference. These are **not** LBE proof artifacts and are not referenced by any acceptance gate — they illustrate prior agent behaviors and must not be confused with runtime/contract evidence.

## Catalog

### `test-differfence-transcripts/`

Captured agent sessions that originated in a *different* workspace (`G:\Developments\45_Accecc_Browser_Agent`, repo `Letterblack0306/Accecc_Browser_Agent.git`). Relocated out of `tests/` because they are not executable test proof against this repository.

| Session | Model / provider | Notes |
|---|---|---|
| `1785460319869_yl0hf` | Nomic Embed v1.5 via LM Studio | **Negative example:** produced findings and claimed file deletions with no tool calls / evidence. Demonstrates the "prose as proof" failure mode the execution wall forbids. |
| `1785461332072_pt9mp` | DeepSeek | Tool-using repository exploration, but scoped to the Browser Agent workspace, not the current LBE implementation. |

## Archival rule

These transcripts are retained solely as negative/positive reference material. They do not establish acceptance evidence for LBE and are never promoted into a canonical doc.