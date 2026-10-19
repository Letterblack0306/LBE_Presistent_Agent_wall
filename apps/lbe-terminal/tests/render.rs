//! Rendered-frame tests against LBE_TUI_SCREEN_SPEC.md: tiers, allowed lines only,
//! the NEVER SHOW list, accessibility modes. These prove the projection; they do
//! not prove the installed terminal journey.
use lbe_terminal::model::*;
use lbe_terminal::text::width;
use lbe_terminal::theme::Display;
use lbe_terminal::view::{draw, render_html, render_text};
use ratatui::backend::TestBackend;
use ratatui::style::Color;
use ratatui::Terminal;

const ON: Display = Display {
    color: true,
    unicode: true,
    motion: true,
};

fn base(d: Display) -> Model {
    let mut m = Model::new(d);
    m.attached = true;
    m.ready = true;
    m.session_id = "28457f04aa11".into();
    m.workspace = "brew".into();
    m.provider = "lmstudio".into();
    m.model = "gemma-4-e4b".into();
    m.git = Some(("main".into(), 12));
    m.ctx = Some((4100, 8000));
    m
}

fn rule(name: &str, target: &str, verdict: Verdict) -> Rule {
    Rule {
        id: String::new(),
        more: vec![],
        name: name.into(),
        target: target.into(),
        verdict,
        reason: String::new(),
        next: String::new(),
        tool: "workspace.patch".into(),
        event: "tool.completed".into(),
        receipt: "rcpt_7f3a".into(),
        resolver: String::new(),
        allowed: vec![],
        need: None,
    }
}

/// The ACT reference frame: one passed turn, then a block.
fn act_frame(d: Display) -> Model {
    let mut m = base(d);
    m.task = "Now write it to C:\\ProgramData\\lbe\\version.txt".into();
    m.entries = vec![
        Entry::User("Add a --version flag to the CLI".into()),
        Entry::Agent("Added --version. It prints the package version, exits 0.".into()),
        Entry::Rule(rule("intent recorded", "add --version flag", Verdict::Pass)),
        Entry::Rule(rule("change allowed", "src/cli.py", Verdict::Pass)),
        Entry::Rule(rule("change allowed", "tests/test_cli.py", Verdict::Pass)),
        Entry::Effect(Verdict::Pass, "1 change made".into()),
        Entry::User("Now write it to C:\\ProgramData\\lbe\\version.txt".into()),
        Entry::Agent("I can't write there.".into()),
        Entry::Rule(Rule {
            reason: "not in the allowed files".into(),
            next: "narrow the change".into(),
            ..rule("change in allowed files", "C:\\ProgramData\\lbe", Verdict::Block)
        }),
        Entry::Effect(Verdict::Block, "blocked · nothing changed".into()),
    ];
    m.turn_rules = vec![Verdict::Block];
    m.log = m
        .entries
        .iter()
        .filter_map(|e| {
            if let Entry::Rule(r) = e {
                Some(r.clone())
            } else {
                None
            }
        })
        .collect();
    m
}

fn permission_frame() -> Model {
    let mut m = base(ON);
    m.task = "wire turn path".into();
    m.entries = vec![Entry::Agent("One change before validation.".into())];
    m.pending = Some(Permission {
        id: "ap-1".into(),
        action: "workspace.write (write)".into(),
        scope: "creates 1 file · changes nothing else".into(),
        target: "tests/test_turn_path.py".into(),
    });
    m
}

const NEVER: &[&str] = &[
    "LBE live",
    "governed",
    "authority",
    "promotion",
    "consequence",
    "proof",
    "receipt",
    "rcpt_",
    "runtime.provider",
    "tool.requested",
    "tool.completed",
    "workspace_run",
    "birdeye_inspect",
    "workspace.patch",
    "workspace.write",
    "PROVEN",
    "INFERRED",
    "mock",
    "28457f04", // session id
    "NO_SCOPE_FOUND",
    "CHANGED_OUTSIDE_SCOPE",
    "secret-file-guard",
    "exit 0",
];

fn assert_never_show(frame: &str, what: &str) {
    for term in NEVER {
        assert!(
            !frame.to_lowercase().contains(&term.to_lowercase()),
            "{what} shows {term:?}:\n{frame}"
        );
    }
}

#[test]
fn every_screen_fits_every_size_without_panic() {
    for screen in Screen::ALL {
        for (w, h) in [
            (60, 18),
            (72, 20),
            (80, 24),
            (99, 30),
            (100, 30),
            (120, 40),
            (200, 50),
            (61, 19),
        ] {
            let mut m = act_frame(ON);
            m.screen = screen;
            m.entries.push(Entry::User("x ".repeat(300)));
            m.entries.push(Entry::Agent("y".repeat(900)));
            m.entries.push(Entry::Error("e".repeat(400)));
            m.entries
                .push(Entry::Banner("AUDIT · LBE is in control".into()));
            m.pending = Some(Permission {
                id: "ap".into(),
                action: "workspace.patch".into(),
                scope: "s ".repeat(200),
                target: "t".repeat(300),
            });
            m.providers = Some(vec![ProviderRow {
                id: "p".repeat(60),
                auth: "login".into(),
                installed: Some(true),
                login_hint: "h".repeat(200),
                engines: vec!["e".repeat(80)],
            }]);
            m.models = Some(vec!["m".repeat(200)]);
            m.caps = Some(Capabilities {
                configured: true,
                error: String::new(),
                items: vec![CapabilityRow {
                    id: "c".repeat(90),
                    kind: "k".into(),
                    enabled: true,
                    availability: "available".into(),
                    rationale: "r ".repeat(200),
                    risk: "low".into(),
                    access: "read".into(),
                }],
            });
            m.detail = true;
            m.composer = "line one\nline two\nline three\nline four\nline five\nline six".into();
            let out = render_text(&m, w, h);
            for (i, line) in out.lines().enumerate() {
                assert!(
                    width(line) <= w as usize,
                    "{screen:?} {w}x{h} row {i} is {} cells: {line:?}",
                    width(line)
                );
            }
            assert_eq!(out.lines().count(), h as usize, "{screen:?} {w}x{h}");
        }
    }
}

#[test]
fn wide_frame_matches_the_act_reference() {
    let out = render_text(&act_frame(ON), 120, 40);
    let first = out.lines().next().unwrap();
    assert!(
        first.contains("[┃]  LBE  brew")
            && first.contains("lmstudio · gemma-4-e4b")
            && first.contains("● connected"),
        "{first}"
    );
    for label in ["TASK", "SESSION", "SCOPE", "LAST RESULT", "CONTEXT", "KEYS"] {
        assert!(out.contains(label), "missing {label}:\n{out}");
    }
    assert!(out.contains("[ACT]"), "{out}");
    assert!(out.contains("❯ Message LBE"));
    let last = out.lines().last().unwrap();
    assert!(last.contains("● act · blocked") && last.contains("? help"), "{last}");
    assert!(out.contains("✓ change allowed") && out.contains("passed"));
    assert!(out.contains("■ change in allowed files") && out.contains("blocked"));
    assert!(out.contains("✓ 1 change made"));
}

#[test]
fn one_glance_shows_task_model_scope_decision_and_outcome() {
    let out = render_text(&act_frame(ON), 120, 40);
    for needle in [
        "gemma-4-e4b",
        "brew",
        "Now write it to",
        "■ change in allowed files",
    ] {
        assert!(out.contains(needle), "{needle:?} missing:\n{out}");
    }
}

#[test]
fn compact_folds_the_rail_into_one_status_line() {
    let out = render_text(&act_frame(ON), 80, 24);
    assert!(!out.contains("SESSION") && !out.contains("KEYS"), "rail must fold");
    let lines: Vec<&str> = out.lines().collect();
    let comp = lines
        .iter()
        .position(|l| l.contains("❯ Message LBE"))
        .unwrap();
    let status = lines[comp - 1];
    assert!(status.contains("act · blocked"), "{status}");
    assert!(
        status.contains("4.1k/8k") && status.contains("F1 keys"),
        "{status}"
    );
    assert!(
        !status.contains("F2"),
        "F-key labels never sit on the status line"
    );
}

#[test]
fn very_short_drops_the_header_and_tags_the_mode_at_the_composer() {
    let out = render_text(&base(ON), 100, 19);
    assert!(!out.lines().next().unwrap().contains("LBE  brew"), "{out}");
    let comp = out.lines().find(|l| l.contains("❯ Message LBE")).unwrap();
    assert!(comp.trim_end().ends_with("act"), "{comp}");
}

#[test]
fn below_minimum_size_says_so() {
    let out = render_text(&base(ON), 50, 12);
    assert!(out.contains("needs at least 60x18"), "{out}");
}

#[test]
fn default_views_never_show_internals() {
    for (m, name) in [
        (act_frame(ON), "act"),
        (permission_frame(), "approval"),
        (base(ON), "empty"),
    ] {
        for (w, h) in [(120, 40), (80, 24), (60, 18)] {
            assert_never_show(&render_text(&m, w, h), &format!("{name} {w}x{h}"));
        }
    }
    let mut p = act_frame(ON);
    p.mode = Mode::Plan;
    assert_never_show(&render_text(&p, 120, 40), "plan");
    let mut a = act_frame(ON);
    a.mode = Mode::Audit;
    a.entries.insert(
        0,
        Entry::Banner("AUDIT · LBE is in control · read-only, nothing can change".into()),
    );
    assert_never_show(&render_text(&a, 120, 40), "audit");
}

#[test]
fn a_blocked_rule_has_exactly_one_next_line() {
    let out = render_text(&act_frame(ON), 120, 40);
    assert_eq!(out.matches("next:").count(), 1, "{out}");
    assert!(
        out.contains("not in the allowed files") && out.contains("next: narrow the change")
    );
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(rule("change in allowed files", "x", Verdict::Block))];
    let out = render_text(&m, 120, 40);
    assert!(out.contains("next: ask LBE why (d)"), "{out}");
}

#[test]
fn more_than_three_passed_rules_collapse() {
    let mut m = base(ON);
    m.entries = (0..7)
        .map(|i| Entry::Rule(rule("read allowed", &format!("f{i}.py"), Verdict::Pass)))
        .collect();
    m.entries
        .insert(2, Entry::Rule(rule("change in allowed files", "bad", Verdict::Block)));
    let out = render_text(&m, 120, 40);
    assert_eq!(out.matches("✓ read allowed").count(), 3, "{out}");
    assert!(out.contains("+4 more rules passed"), "{out}");
    assert!(
        out.contains("■ change in allowed files"),
        "a blocked rule is never collapsed"
    );
}

#[test]
fn audit_shows_the_banner_header_and_its_own_rail() {
    let mut m = base(ON);
    m.mode = Mode::Audit;
    m.entries = vec![
        Entry::Banner("AUDIT · LBE is in control · read-only, nothing can change".into()),
        Entry::Agent("Two files are uncommitted.".into()),
    ];
    m.reads = 14;
    let out = render_text(&m, 120, 30);
    assert_eq!(out.matches("LBE is in control").count(), 1);
    assert!(out.lines().next().unwrap().contains("AUDIT · read-only"));
    for label in ["SCOPE", "READ", "REPORT"] {
        assert!(out.contains(label), "{label}:\n{out}");
    }
    assert!(out.contains("14 reads") && out.contains("nothing changed"));
    assert!(!out.contains("TASK"), "audit replaces the rail body");
}

#[test]
fn plan_header_and_rail() {
    let mut m = base(ON);
    m.mode = Mode::Plan;
    m.entries = vec![Entry::Agent("1 add flag".into())];
    let out = render_text(&m, 120, 30);
    assert!(out
        .lines()
        .next()
        .unwrap()
        .contains("PLAN · nothing executes"));
    assert!(out.contains("PLAN STATE") && out.contains("proposed"));
    assert!(out.contains("[A] approve → ACT"));
}

#[test]
fn approval_prompt_has_actor_action_target_workspace_and_keys() {
    let out = render_text(&permission_frame(), 120, 40);
    assert!(out.contains("PERMISSION NEEDED"));
    assert!(out.contains("lmstudio wants to write") && out.contains("tests/test_turn_path.py"));
    assert!(out.contains("in brew"));
    assert!(
        out.contains("a allow once") && out.contains("d deny") && out.contains("v view change")
    );
    assert!(out.lines().last().unwrap().contains("waiting for you"));
    assert!(!out.contains("expires"), "no expiry unless the runtime reports one");
}

#[test]
fn offline_header_and_status() {
    let mut m = base(ON);
    m.attached = false;
    let out = render_text(&m, 120, 30);
    assert!(out.lines().next().unwrap().contains("○ offline"));
    assert!(out.lines().last().unwrap().contains("offline"));
    assert!(!out.contains("● connected"));
}

#[test]
fn stopping_shows_a_pending_word_not_stopped() {
    let mut m = base(ON);
    m.busy = true;
    m.life = Life::Stopping;
    let out = render_text(&m, 120, 30);
    assert!(out.lines().last().unwrap().contains("stopping…"));
    assert!(!out.lines().last().unwrap().contains("stopped"));
    m.life = Life::ConfirmStop;
    m.task = "fix --version".into();
    let out = render_text(&m, 120, 30);
    assert!(out.contains("Stop \"fix --version\"?") && out.contains("y stop · n keep going"));
}

#[test]
fn details_pane_is_the_only_place_for_internals() {
    let mut m = act_frame(ON);
    m.detail = true;
    let out = render_text(&m, 120, 40);
    assert!(out.contains("Details") && out.contains("rcpt_7f3a") && out.contains("PROVEN"));
    m.detail = false;
    let closed = render_text(&m, 120, 40);
    assert!(!closed.contains("rcpt_7f3a"));
}

#[test]
fn receipts_screen_lists_newest_first() {
    let mut m = act_frame(ON);
    m.screen = Screen::Receipts;
    let out = render_text(&m, 120, 30);
    let a = out.find("change in allowed files").unwrap();
    let b = out.find("intent recorded").unwrap();
    assert!(a < b, "newest first:\n{out}");
    assert!(out.lines().next().unwrap().contains("F8 log"));
}

#[test]
fn capabilities_never_pre_fill_green() {
    let mut m = base(ON);
    m.screen = Screen::Capabilities;
    m.caps = Some(Capabilities {
        configured: true,
        error: String::new(),
        items: vec![CapabilityRow {
            id: "birdeye".into(),
            kind: "mcp".into(),
            enabled: true,
            availability: "unavailable".into(),
            rationale: String::new(),
            risk: "low".into(),
            access: "read".into(),
        }],
    });
    let out = render_text(&m, 120, 30);
    assert!(out.contains("configured") && out.contains("connected") && out.contains("healthy"));
    assert!(out.contains("○ offline"), "{out}");
    m.caps = Some(Capabilities {
        configured: false,
        error: String::new(),
        items: vec![],
    });
    assert!(render_text(&m, 120, 30).contains("nothing discovered"));
}

#[test]
fn no_color_keeps_glyphs_and_ascii_is_ascii_only() {
    let nc = Display {
        color: false,
        unicode: true,
        motion: true,
    };
    let out = render_text(&act_frame(nc), 120, 40);
    assert!(out.contains('✓') && out.contains('■'));
    let html = render_html(&act_frame(nc), 120, 40);
    assert!(!html.contains("color:#"), "no colour escapes with NO_COLOR");

    let ascii = Display {
        color: true,
        unicode: false,
        motion: true,
    };
    for mut m in [act_frame(ascii), permission_frame()] {
        m.display = ascii;
        for (w, h) in [(120, 40), (80, 24), (60, 18)] {
            let out = render_text(&m, w, h);
            assert!(out.is_ascii(), "{w}x{h} has non-ascii:\n{out}");
        }
    }
    let out = render_text(&act_frame(ascii), 120, 40);
    assert!(out.contains("v change allowed") && out.contains("x change in allowed files"));
    assert!(out.contains("[|]  LBE"));
}

#[test]
fn red_is_only_used_where_the_spec_allows() {
    let red = Color::Rgb(0xef, 0x4b, 0x4b);
    // ACT, nothing blocked: red may only be the logo bar and the active mode.
    let mut m = base(ON);
    m.entries = vec![
        Entry::User("hi".into()),
        Entry::Agent("hello".into()),
        Entry::Rule(rule("read allowed", "a.py", Verdict::Pass)),
        Entry::Effect(Verdict::Pass, "1 change made".into()),
    ];
    let mut term = Terminal::new(TestBackend::new(120, 30)).unwrap();
    term.draw(|f| draw(f, &m)).unwrap();
    let buf = term.backend().buffer().clone();
    let mut red_text = String::new();
    for y in 0..buf.area.height {
        for x in 0..buf.area.width {
            let c = buf.get(x, y);
            if c.fg == red {
                red_text.push_str(c.symbol());
            }
        }
    }
    let cleaned: String = red_text.chars().filter(|c| !c.is_whitespace()).collect();
    assert_eq!(cleaned, "┃[ACT]", "unexpected red text: {red_text:?}");
}

#[test]
fn lifecycle_lines_render_without_internals() {
    let mut m = base(ON);
    m.entries = vec![Entry::Lifecycle(
        "stopped by you · check the log (F8) for steps that already ran".into(),
    )];
    let out = render_text(&m, 120, 30);
    assert!(out.contains("stopped by you"));
}

#[test]
fn launch_splash_carries_the_full_product_title() {
    let out = render_text(&base(ON), 120, 30);
    assert!(out.contains("Lockstep Boundary Engine (LBE)"), "{out}");
    let mut m = base(ON);
    m.entries = vec![Entry::User("hi".into())];
    assert!(
        !render_text(&m, 120, 30).contains("Lockstep"),
        "splash is gone after the first message"
    );
}

fn mapped(id: &str, target: &str) -> Rule {
    let r = lbe_terminal::rules::lookup(id).expect("id is in the rule map");
    Rule {
        id: id.into(),
        more: r.options.iter().skip(1).map(|s| s.to_string()).collect(),
        name: r.name.into(),
        target: target.into(),
        verdict: r.verdict,
        reason: r.reason.into(),
        next: r.options.first().map(|s| s.to_string()).unwrap_or_default(),
        tool: "workspace.write".into(),
        event: "tool.denied".into(),
        receipt: String::new(),
        resolver: String::new(),
        allowed: vec![],
        need: None,
    }
}

fn owner_block(resolver: &str) -> Rule {
    Rule {
        reason: "no owner sign-off was supplied. Only the owner can supply it.".into(),
        next: "stop writing and ask the owner to approve hello.txt".into(),
        resolver: resolver.into(),
        allowed: vec!["hello.txt".into(), "notes.txt".into()],
        event: "tool.denied".into(),
        ..rule("owner sign-off supplied", "hello.txt", Verdict::Block)
    }
}

#[test]
fn the_owner_rule_names_from_the_map_respect_the_never_show_list() {
    for id in ["OWNER_AUTHORITY_BLOCKER", "OWNER_SCOPE_VIOLATION"] {
        let mut m = base(ON);
        m.entries = vec![Entry::Rule(mapped(id, "hello.txt"))];
        assert_never_show(&render_text(&m, 120, 40), id);
    }
}

#[test]
fn an_owner_only_block_is_an_actionable_stop_card_with_one_next_line() {
    for (w, h) in [(120u16, 40u16), (80, 24), (60, 18)] {
        let mut m = base(ON);
        m.entries = vec![Entry::Rule(owner_block("owner"))];
        let out = render_text(&m, w, h);
        assert!(out.contains("only you can resolve this"), "{w}x{h}:\n{out}");
        assert!(out.contains("no owner sign-off was supplied"), "{w}x{h}:\n{out}");
        assert!(out.contains("allowed  hello.txt, notes.txt"), "{w}x{h}:\n{out}");
        assert_eq!(out.matches("next:").count(), 1, "{w}x{h}:\n{out}");
        assert_never_show(&out, "stop card");
    }
}

#[test]
fn a_block_the_agent_can_resolve_stays_collapsed() {
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(owner_block("agent"))];
    let out = render_text(&m, 120, 40);
    assert!(!out.contains("only you can resolve this"), "{out}");
    assert!(!out.contains("allowed  "), "{out}");
    assert_eq!(out.matches("next:").count(), 1, "{out}");
    // no resolver reported at all: exactly the existing two-line block
    m.entries = vec![Entry::Rule(owner_block(""))];
    let out = render_text(&m, 120, 40);
    assert!(!out.contains("only you can resolve this"), "{out}");
}

#[test]
fn the_stop_card_survives_ascii_and_no_color() {
    let ascii = Display {
        color: false,
        unicode: false,
        motion: false,
    };
    let mut m = base(ascii);
    m.entries = vec![Entry::Rule(owner_block("owner"))];
    let out = render_text(&m, 100, 30);
    assert!(out.is_ascii(), "{out}");
    assert!(out.contains("only you can resolve this") && out.contains("next:"), "{out}");
}

#[test]
fn changed_outside_scope_is_failed_with_rollback_never_blocked() {
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(mapped("CHANGED_OUTSIDE_SCOPE", "src/other.py"))];
    let out = render_text(&m, 120, 30);
    assert!(out.contains("✗ change in scope"), "{out}");
    assert!(out.contains("failed"), "{out}");
    assert!(!out.contains("■ change in scope") && !out.contains("blocked"), "{out}");
    assert!(
        out.contains("files changed outside allowed scope")
            && out.contains("next: roll back")
            && out.contains("(o more options)"),
        "{out}"
    );
    assert_eq!(out.matches("next:").count(), 1);
    assert_never_show(&out, "failed rule");
}

#[test]
fn a_block_before_any_change_is_blocked_not_failed() {
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(mapped("NO_SCOPE_FOUND", "task"))];
    let out = render_text(&m, 120, 30);
    assert!(out.contains("■ task scope set") && out.contains("blocked"), "{out}");
    assert!(out.contains("next: set scope"), "{out}");
    assert!(!out.contains("failed"));
}

#[test]
fn rule_ids_appear_only_in_details() {
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(mapped("secret-file-guard", ".env"))];
    let out = render_text(&m, 120, 30);
    assert!(out.contains("no secret files") && !out.contains("secret-file-guard"), "{out}");
    m.detail = true;
    let out = render_text(&m, 120, 30);
    assert!(out.contains("secret-file-guard") && out.contains("rule id"), "{out}");
}

#[test]
fn every_mapped_rule_fits_at_the_smallest_size() {
    for id in [
        "NO_SCOPE_FOUND",
        "REQUIRED_READING_MISSING",
        "CHANGED_OUTSIDE_SCOPE",
        "FORBIDDEN_FILE_TOUCHED",
        "push-without-test-proof-guard",
        "destructive-command-guard",
        "protected-zone-no-signoff",
    ] {
        let mut m = base(ON);
        m.entries = vec![Entry::Rule(mapped(id, "C:/very/long/path/to/some/file.py"))];
        for (w, h) in [(60, 18), (80, 24)] {
            let out = render_text(&m, w, h);
            for line in out.lines() {
                assert!(width(line) <= w as usize, "{id} {w}x{h}: {line:?}");
            }
            assert_eq!(out.matches("next:").count(), 1, "{id} {w}x{h}\n{out}");
        }
    }
}

#[test]
fn ascii_mode_has_a_distinct_failed_glyph() {
    let ascii = Display {
        color: true,
        unicode: false,
        motion: true,
    };
    let mut m = base(ascii);
    m.entries = vec![Entry::Rule(mapped("CHANGED_OUTSIDE_SCOPE", "a.py"))];
    let out = render_text(&m, 120, 30);
    assert!(out.is_ascii() && out.contains("X change in scope"), "{out}");
}


fn needs_input() -> Rule {
    Rule {
        id: "INSUFFICIENT_EVIDENCE".into(),
        name: "insufficient evidence".into(),
        next: "Where is the evidence for this (README.md)? Name the file, or say it does not exist.".into(),
        need: Some(Box::new(Need {
            checked: "generic.index_present (needs bounded project metadata)".into(),
            missing: "generic.index_present: bounded project metadata".into(),
            investigate: "pyproject.toml, package.json, Cargo.toml, README.md (read-only lookup)".into(),
            ask: "Where is the evidence for this (README.md)? Name the file, or say it does not exist.".into(),
        })),
        event: "reasoning.needs_input".into(),
        ..rule("insufficient evidence", "", Verdict::Block)
    }
}

#[test]
fn a_stop_for_missing_evidence_shows_what_was_checked_what_is_missing_and_the_question() {
    for (w, h) in [(120u16, 40u16), (80, 24), (60, 18)] {
        let mut m = base(ON);
        m.entries = vec![Entry::Rule(needs_input())];
        let out = render_text(&m, w, h);
        for want in ["needs your answer", "checked ", "missing ", "look at "] {
            assert!(out.contains(want), "{w}x{h} lacks {want:?}:
{out}");
        }
        assert_eq!(out.matches("next:").count(), 1, "{w}x{h}:
{out}");
        assert!(!out.contains("only you can resolve this"), "{w}x{h}:
{out}");
        assert_never_show(&out, "needs-input card");
    }
}

#[test]
fn a_block_with_no_runtime_question_draws_no_needs_card() {
    let mut r = needs_input();
    r.need = None;
    let mut m = base(ON);
    m.entries = vec![Entry::Rule(r)];
    let out = render_text(&m, 120, 40);
    assert!(!out.contains("needs your answer") && !out.contains("checked "), "{out}");
}
