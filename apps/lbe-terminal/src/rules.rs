//! Rule map (spec section 4a). The UI never invents a rule name or a next step:
//! every rule id the runtime returns is looked up here. An id that is not in the
//! map is shown as its plain words, blocked, with `next: ask LBE why (d)`.
use crate::model::Verdict;

pub struct Mapped {
    pub name: &'static str,
    pub verdict: Verdict,
    pub reason: &'static str,
    /// `next:` options in registry order; the first is shown, the rest sit behind `o`.
    pub options: &'static [&'static str],
}

const fn m(
    name: &'static str,
    verdict: Verdict,
    reason: &'static str,
    options: &'static [&'static str],
) -> Mapped {
    Mapped {
        name,
        verdict,
        reason,
        options,
    }
}

use Verdict::{Block, Failed, Pass};

/// A. LBE Core audit statuses (`AUDIT_STATUS`, blocker registry `decisionOptions`).
/// B. LB Guards default required set; class sets the result (security and scope
///    block, quality fails). C. Repo governance template rules, keyed by the
///    kebab-case names this client uses until the runtime returns its own ids.
pub fn lookup(id: &str) -> Option<Mapped> {
    Some(match id.trim() {
        // A
        "NO_SCOPE_FOUND" => m(
            "task scope set",
            Block,
            "no task scope registered",
            &["set scope", "ask you"],
        ),
        "REQUIRED_READING_MISSING" => m(
            "required reading done",
            Block,
            "required files not read yet",
            &["read the files", "update scope", "ask you"],
        ),
        "NO_INTENT_FOUND" => m(
            "intent recorded",
            Block,
            "no intent before changes",
            &["record intent", "ask you"],
        ),
        "INTENT_SCOPE_MISMATCH" => m(
            "intent matches scope",
            Block,
            "intent points at another scope",
            &["record intent again", "ask you"],
        ),
        "CHANGED_OUTSIDE_SCOPE" => m(
            "change in scope",
            Failed,
            "files changed outside allowed scope",
            &["roll back", "expand scope", "ask you"],
        ),
        "FORBIDDEN_FILE_TOUCHED" => m(
            "forbidden files untouched",
            Failed,
            "a forbidden file was changed",
            &["roll back", "update scope", "ask you"],
        ),
        "MISMATCH_DETECTED" => m(
            "proof matches work",
            Failed,
            "proof found mismatches",
            &["fix violations", "update scope", "ask you"],
        ),
        "VALIDATION_MISSING" => m(
            "checks run",
            Block,
            "required checks not run",
            &["run checks", "ask you"],
        ),
        "PROOF_INCOMPLETE" => m(
            "proof complete",
            Block,
            "proof cycle not finished",
            &["run proof", "ask you"],
        ),
        "CLEAN" => m("all checks", Pass, "", &[]),
        // B
        "push-without-test-proof-guard" => m(
            "tests proven for this commit",
            Failed,
            "",
            &["run tests for this commit"],
        ),
        "claim-without-proof-guard" => m(
            "claim backed by proof",
            Failed,
            "",
            &["run tests, then claim again"],
        ),
        "missing-module-guard" => m(
            "imports resolve",
            Failed,
            "",
            &["add the missing module or dependency"],
        ),
        "duplicate-index-guard" => m(
            "one index per folder",
            Failed,
            "",
            &["remove or merge the duplicate index"],
        ),
        "empty-button-guard" => m(
            "buttons labelled",
            Failed,
            "",
            &["add a label to the button"],
        ),
        "feature-owner-guard" => m("owner declared", Block, "", &["declare the owner", "ask you"]),
        "generated-pollution-guard" => m(
            "no generated files",
            Failed,
            "",
            &["remove or ignore generated files"],
        ),
        "secret-file-guard" => m(
            "no secret files",
            Block,
            "",
            &["remove the file and rotate the secret"],
        ),
        "destructive-command-guard" => m(
            "command is safe",
            Block,
            "",
            &["use a safe command", "ask you"],
        ),
        "wrong-workspace-guard" => m(
            "right workspace",
            Block,
            "",
            &["switch to the right workspace"],
        ),
        // C
        "no-task-contract" => m(
            "task contract exists",
            Block,
            "no task contract",
            &["write the task contract"],
        ),
        "file-not-in-allowed-files" => m(
            "change in allowed files",
            Block,
            "not in the allowed files",
            &["narrow the change", "ask you to add the file"],
        ),
        "role-denies-path" => m(
            "role allows this path",
            Block,
            "role does not allow this path",
            &["hand to the right role"],
        ),
        "protected-zone-no-signoff" => m(
            "protected zone signed off",
            Block,
            "protected zone has no signoff",
            &["request architecture signoff"],
        ),
        "signoff-expired" => m(
            "signoff still valid",
            Block,
            "signoff has expired",
            &["request a new signoff"],
        ),
        // Emitted by this runtime's owner-authority gate (`authority_ownership.py`).
        "OWNER_AUTHORITY_BLOCKER" => m(
            "owner sign-off supplied",
            Block,
            "owner sign-off was not supplied",
            &["ask the owner to attach their sign-off"],
        ),
        "OWNER_SCOPE_VIOLATION" => m(
            "change within owner scope",
            Failed,
            "changed files outside the owner scope",
            &["roll back", "ask you"],
        ),
        _ => return None,
    })
}

/// Unmapped id as plain words: `SOME_NEW_CODE` becomes `some new code`.
pub fn plain_words(id: &str) -> String {
    id.trim()
        .chars()
        .map(|c| {
            if c == '_' || c == '-' {
                ' '
            } else {
                c.to_ascii_lowercase()
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn changed_outside_scope_is_failed_with_rollback_first() {
        let r = lookup("CHANGED_OUTSIDE_SCOPE").unwrap();
        assert_eq!(r.verdict, Verdict::Failed);
        assert_eq!(r.name, "change in scope");
        assert_eq!(r.options[0], "roll back");
        assert_eq!(r.options.len(), 3);
    }

    #[test]
    fn checks_before_a_change_are_blocked_not_failed() {
        for id in [
            "NO_SCOPE_FOUND",
            "NO_INTENT_FOUND",
            "VALIDATION_MISSING",
            "PROOF_INCOMPLETE",
        ] {
            assert_eq!(lookup(id).unwrap().verdict, Verdict::Block, "{id}");
        }
    }

    #[test]
    fn guard_class_sets_the_result() {
        assert_eq!(lookup("secret-file-guard").unwrap().verdict, Verdict::Block);
        assert_eq!(
            lookup("missing-module-guard").unwrap().verdict,
            Verdict::Failed
        );
    }

    #[test]
    fn owner_authority_ids_from_this_runtime_are_mapped() {
        let b = lookup("OWNER_AUTHORITY_BLOCKER").unwrap();
        assert_eq!((b.name, b.verdict), ("owner sign-off supplied", Verdict::Block));
        let v = lookup("OWNER_SCOPE_VIOLATION").unwrap();
        assert_eq!((v.name, v.verdict), ("change within owner scope", Verdict::Failed));
    }

    #[test]
    fn unknown_ids_are_not_invented() {
        assert!(lookup("SOMETHING_NEW").is_none());
        assert_eq!(plain_words("SOMETHING_NEW"), "something new");
    }

    #[test]
    fn screen_names_never_look_like_ids() {
        for id in ["NO_SCOPE_FOUND", "secret-file-guard", "CHANGED_OUTSIDE_SCOPE"] {
            let n = lookup(id).unwrap().name;
            assert!(!n.contains('_') && !n.contains("-guard") && n != n.to_uppercase());
        }
    }
}
