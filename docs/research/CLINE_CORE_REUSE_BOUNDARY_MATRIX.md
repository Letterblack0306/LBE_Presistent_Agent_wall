# Cline Core Reuse Boundary Matrix

Status: **AUDIT WORKING RECORD**

Required classification: `REUSE | ADAPT | REJECT | UNVERIFIED`.

No row may be promoted from UNVERIFIED by assumption, README-level marketing language, or model memory.

Evidence routing:
- GitHub: canonical Cline/LBE remote source and exact revision.
- BirdEye: local LBE workspace identity, revision, diff, inspection, and governed execution.
- GPT-Knowledge: architecture/reference methodology.
- Runtime-specific proof: only where live behavior is necessary.

| Capability | Cline package/subsystem | Exact Cline revision | Source path / symbol | Observed behavior | Existing LBE owner | Authority / bypass impact | Decision | Evidence / reason | Follow-up proof |
|---|---|---|---|---|---|---|---|---|---|
| Provider adapters | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | provider/reasoning owners | Must not move authorization/evidence authority | UNVERIFIED | Pending source audit | Required |
| Provider/model capability metadata + probes | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | capability projection/resolver | provider+endpoint+model truth required | UNVERIFIED | Pending source audit | Required |
| Provider-native streaming | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | normalized provider event owners | Preserve actual provider semantics | UNVERIFIED | Pending source audit | Required |
| Tool-call parsing + continuation | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | provider turn/runtime continuation owners | LBE tool result must re-enter continuation without bypass | UNVERIFIED | Pending source audit | Required |
| Tool interception before mutation | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | R6C authorization + governed tool dispatcher | Strict governance impossible if bypass exists | UNVERIFIED | Pending source audit | Required |
| Filesystem/editor mutation | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | governed workspace tools | Mutation must remain LBE-authorized | UNVERIFIED | Pending source audit | Required |
| Shell/terminal/process execution | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | governed execution/tool owners | Raw shell bypass must be identified | UNVERIFIED | Pending source audit | Required |
| Session persistence | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | LBE session/task persistence | No competing canonical session authority | UNVERIFIED | Pending source audit | Required |
| Checkpoint/undo | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | LBE checkpoint/recovery policy | Snapshot mechanics != validated checkpoint truth | UNVERIFIED | Pending source audit | Required |
| Runtime/model event stream | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | LBE normalized event/history owners | Preserve provenance and diagnostic metadata | UNVERIFIED | Pending source audit | Required |
| Cancellation | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | persistent_turn_control/provider_turn_runtime/transport capability | Preserve truthful transport capability | UNVERIFIED | Pending source audit | Required |
| Interrupt / steering | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | control protocol/turn control | Interrupt != cancel | UNVERIFIED | Pending source audit | Required |
| MCP | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | future LBE MCP surface | MCP does not prove native-tool governance | UNVERIFIED | Pending source audit | Required |
| CLI/TUI | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | client/projection only | Must not become runtime authority | UNVERIFIED | Pending source audit | Required |
| Background processes | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | professional terminal/process capability | Typed process identity/events/control required | UNVERIFIED | Pending source audit | Required |
| Context/compaction | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | LBE context/checkpoint semantics | Compaction summary cannot become current truth | UNVERIFIED | Pending source audit | Required |

## Required audit conclusion

```text
FIRST_GENUINELY_MISSING_DEPENDENCY:
CLASSIFICATION:
EXISTING_LBE_OWNER:
CLINE_REUSE_DECISION:
WHY:
REQUIRED_EVIDENCE_LEVEL_FOR_NEXT_SLICE:
```

Do not propose implementation until that conclusion is supported by completed rows.
