//! Cockpit body: the transcript is the timeline (turn, rule lines, effect lines),
//! plus the permission prompt, the launch splash and the details pane.
//! Only the line types in the screen spec appear; internals stay in `details`.
use super::chrome::{sp, target, verdict_glyph, verdict_word};
use crate::model::{Entry, Life, Mode, Model, Rule, Verdict};
use crate::text::{clip, clip_left, pad, wrap};
use crate::theme::Theme;
use ratatui::layout::Alignment;
use ratatui::text::Line;

const MAX_RULES: usize = 3;
const NAME_W: usize = 28;
const RESULT_W: usize = 9;

fn aligned(mut l: Line<'static>, centre: bool) -> Line<'static> {
    if centre {
        l = l.alignment(Alignment::Center);
    }
    l
}

/// One rule line: `  ✓ change in scope      …/src/cli.py      passed`, plus a single
/// `next:` line when blocked.
fn rule_lines(r: &Rule, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let ascii = !t.d.unicode;
    let (glyph, st) = verdict_glyph(r.verdict, t);
    let tw = w.saturating_sub(2 + 2 + NAME_W + 1 + 2 + RESULT_W).max(6);
    let tgt = if r.target.is_empty() {
        "-".to_string()
    } else {
        r.target.clone()
    };
    let mut out = vec![Line::from(vec![
        sp(format!("  {glyph} "), st),
        sp(pad(&r.name, NAME_W), t.text()),
        sp(" ", t.text()),
        sp(pad(&clip_left(&tgt, tw, ascii), tw), t.muted()),
        sp("  ", t.text()),
        sp(verdict_word(r.verdict).to_string(), st),
    ])];
    let card = if r.resolver == "owner" {
        Some("only you can resolve this")
    } else if r.need.is_some() {
        Some("needs your answer")
    } else {
        None
    };
    if let (Verdict::Block, Some(header)) = (r.verdict, card) {
        // Stop card: a block a person has to resolve, shown in full and actionable.
        // Every line is the runtime's own data; none is drawn when it was not sent.
        let body_w = w.saturating_sub(8).max(8);
        out.push(Line::from(sp(clip(&format!("      {header}"), w, ascii), t.strong())));
        if let Some(need) = &r.need {
            for (label, value) in [
                ("checked ", &need.checked),
                ("missing ", &need.missing),
                ("look at ", &need.investigate),
            ] {
                if !value.is_empty() {
                    out.push(Line::from(sp(
                        clip(&format!("      {label} {value}"), w, ascii),
                        t.muted(),
                    )));
                }
            }
        } else {
            let reason = if r.reason.is_empty() {
                "blocked by LBE".to_string()
            } else {
                r.reason.clone()
            };
            for row in wrap(&reason, body_w).into_iter().take(2) {
                out.push(Line::from(sp(format!("      {row}"), t.muted())));
            }
        }
        if !r.allowed.is_empty() {
            out.push(Line::from(sp(
                clip(&format!("      allowed  {}", r.allowed.join(", ")), w, ascii),
                t.muted(),
            )));
        }
        let next = if r.next.is_empty() {
            "ask LBE why (d)".to_string()
        } else {
            r.next.clone()
        };
        let more = if r.more.is_empty() { "" } else { "  (o more options)" };
        out.push(Line::from(sp(
            clip(&format!("      next: {next}{more}"), w, ascii),
            t.muted(),
        )));
        return out;
    }
    if matches!(r.verdict, Verdict::Block | Verdict::Failed) {
        let words: Vec<&str> = r.reason.split_whitespace().take(8).collect();
        let reason = if words.is_empty() {
            "blocked by LBE".to_string()
        } else {
            words.join(" ")
        };
        let next = if r.next.is_empty() {
            "ask LBE why (d)".to_string()
        } else {
            r.next.clone()
        };
        let more = if r.more.is_empty() { "" } else { "  (o more options)" };
        out.push(Line::from(sp(
            clip(
                &format!("      {reason} {} next: {next}{more}", t.g().dot),
                w,
                ascii,
            ),
            t.muted(),
        )));
    }
    out
}

/// A run of rule lines for one turn: at most three passed lines; blocked and
/// needs-you lines are never collapsed.
fn rule_run(run: &[&Rule], t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = Vec::new();
    let mut passed_shown = 0;
    let mut hidden = 0;
    for r in run {
        if r.verdict == Verdict::Pass {
            if passed_shown >= MAX_RULES {
                hidden += 1;
                continue;
            }
            passed_shown += 1;
        }
        out.extend(rule_lines(r, t, w));
    }
    if hidden > 0 {
        out.push(Line::from(sp(
            format!(
                "  +{hidden} more rule{} passed   d details",
                if hidden == 1 { "" } else { "s" }
            ),
            t.muted(),
        )));
    }
    out
}

pub fn transcript(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out: Vec<Line<'static>> = Vec::new();
    let centre = m.mode == Mode::Audit;
    let body_w = w.saturating_sub(2).max(8);
    let ascii = !t.d.unicode;
    let mut i = 0;
    while i < m.entries.len() {
        match &m.entries[i] {
            Entry::User(s) => {
                for (k, row) in wrap(s, body_w.saturating_sub(6)).into_iter().enumerate() {
                    let lead = if k == 0 { "you   " } else { "      " };
                    out.push(Line::from(vec![
                        sp(" ", t.text()),
                        sp(lead, t.muted()),
                        sp(row, t.strong()),
                    ]));
                }
                out.push(Line::default());
            }
            Entry::Agent(s) => {
                for (k, row) in wrap(s, body_w.saturating_sub(6)).into_iter().enumerate() {
                    let lead = if centre {
                        ""
                    } else if k == 0 {
                        "lbe   "
                    } else {
                        "      "
                    };
                    out.push(aligned(
                        Line::from(vec![
                            sp(" ", t.text()),
                            sp(lead, t.strong()),
                            sp(row, t.text()),
                        ]),
                        centre,
                    ));
                }
            }
            Entry::Rule(_) => {
                let mut run: Vec<&Rule> = Vec::new();
                while let Some(Entry::Rule(r)) = m.entries.get(i) {
                    run.push(r);
                    i += 1;
                }
                out.extend(rule_run(&run, t, w));
                continue;
            }
            Entry::Effect(v, text) => {
                let (glyph, st) = verdict_glyph(*v, t);
                out.push(Line::from(sp(
                    clip(&format!("{glyph} {text}"), w, ascii),
                    st,
                )));
                out.push(Line::default());
            }
            Entry::Lifecycle(s) => out.push(Line::from(sp(
                clip(&format!(" {s}"), w, ascii),
                t.muted(),
            ))),
            Entry::Banner(s) => {
                let g = t.g().heavy;
                let text = format!(" {s} ");
                let lead = g.repeat(2);
                let fill = w.saturating_sub(2 + crate::text::width(&text));
                out.push(Line::from(vec![
                    sp(lead, t.accent()),
                    sp(text, t.strong()),
                    sp(g.repeat(fill), t.accent()),
                ]));
                out.push(Line::default());
            }
            Entry::Info(s) => {
                for row in wrap(s, body_w.saturating_sub(2)) {
                    out.push(Line::from(sp(format!("   {row}"), t.muted())));
                }
            }
            Entry::Error(s) => {
                for (k, row) in wrap(s, body_w.saturating_sub(4)).into_iter().enumerate() {
                    let lead = if k == 0 { "  ! " } else { "    " };
                    out.push(Line::from(sp(format!("{lead}{row}"), t.err())));
                }
            }
        }
        i += 1;
    }
    out
}

fn verb(action: &str) -> &'static str {
    let a = action.to_ascii_lowercase();
    if a.contains("delete") {
        "delete"
    } else if a.contains("write") || a.contains("patch") || a.contains("edit") || a.contains("create")
    {
        "write"
    } else if a.contains("command") || a.contains("run") || a.contains("exec") {
        "run"
    } else {
        "use"
    }
}

/// Permission prompt (or the stop confirmation) below the transcript.
pub fn gate(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let ascii = !t.d.unicode;
    if m.life == Life::ConfirmStop {
        let task = clip(&m.task, w.saturating_sub(40).max(8), ascii);
        return vec![
            Line::default(),
            Line::from(vec![
                sp(format!("  Stop \"{task}\"? "), t.warn()),
                sp("y stop · n keep going", t.muted()),
            ]),
        ];
    }
    let Some(p) = &m.pending else { return vec![] };
    let actor = if m.provider.is_empty() {
        "the agent"
    } else {
        m.provider.as_str()
    };
    let tgt = if p.target.is_empty() {
        "(target not reported)".to_string()
    } else {
        p.target.clone()
    };
    let ws = if m.workspace.is_empty() {
        "this workspace"
    } else {
        m.workspace.as_str()
    };
    vec![
        Line::default(),
        Line::from(sp("  PERMISSION NEEDED", t.warn())),
        Line::from(vec![
            sp(format!("  {actor} wants to {}  ", verb(&p.action)), t.text()),
            sp(clip_left(&tgt, w.saturating_sub(40).max(8), ascii), t.strong()),
        ]),
        Line::from(sp(
            clip(&format!("  in {ws} {} {}", t.g().dot, p.scope), w, ascii),
            t.muted(),
        )),
        Line::from(vec![
            sp("  a", t.warn()),
            sp(" allow once    ", t.text()),
            sp("d", t.warn()),
            sp(" deny    ", t.text()),
            sp("v", t.warn()),
            sp(" view change", t.text()),
        ]),
    ]
}

/// Plan footer: only when a plan reply exists and nothing is pending.
pub fn plan_footer(m: &Model, t: &Theme) -> Vec<Line<'static>> {
    if m.mode != Mode::Plan
        || m.pending.is_some()
        || !m.entries.iter().any(|e| matches!(e, Entry::Agent(_)))
    {
        return vec![];
    }
    vec![
        Line::default(),
        Line::from(vec![
            sp(" [A]", t.warn()),
            sp(
                format!(" approve {} ACT", t.g().arrow),
                t.text(),
            ),
        ]),
    ]
}

/// Launch splash: shown once, gone on the first message.
pub fn splash(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let g = t.g();
    let ascii = !t.d.unicode;
    let row = |k: &str, v: String| {
        Line::from(vec![
            sp(format!("  {:<11}", k), t.label()),
            sp(clip(&v, w.saturating_sub(14), ascii), t.text()),
        ])
    };
    vec![
        Line::default(),
        Line::from(vec![
            sp(format!("  {}", g.mark[0]), t.strong()),
            sp(g.mark[1], t.accent()),
            sp(g.mark[2], t.strong()),
            sp("  Lockstep Boundary Engine (LBE)", t.strong()),
        ]),
        Line::default(),
        row(
            "workspace",
            if m.workspace.is_empty() {
                "unknown".into()
            } else {
                m.workspace.clone()
            },
        ),
        row("model", target(m)),
        row(
            "runtime",
            if m.attached {
                "connected".into()
            } else {
                "offline".into()
            },
        ),
        Line::default(),
        Line::from(sp(
            "  Type a message and press Enter.   F1 keys   Ctrl+K commands",
            t.muted(),
        )),
    ]
}

/// Details layer: the full chain for ONE action, using only reported fields.
pub fn details(m: &Model, rule: Option<&Rule>, t: &Theme) -> Vec<Line<'static>> {
    let kv = |k: &str, v: &str| {
        Line::from(vec![
            sp(format!(" {k:<11}"), t.muted()),
            sp(v.to_string(), t.text()),
        ])
    };
    let nr = "not reported";
    let some = |s: &str| if s.is_empty() { nr.to_string() } else { s.to_string() };
    let mut out = Vec::new();
    if let (Some(p), None) = (&m.pending, rule) {
        out.push(kv("request", &format!("{} {}", verb(&p.action), some(&p.target))));
        out.push(kv("actor", &some(&m.provider)));
        out.push(kv("workspace", &some(&m.workspace)));
        out.push(kv("decision", "needs you"));
        out.push(kv("why", &some(&p.scope)));
        out.push(kv("approval", &some(&p.id)));
        out.push(kv("evidence", "UNVERIFIED"));
        return out;
    }
    let Some(r) = rule else {
        out.push(Line::from(sp(" nothing to show yet", t.muted())));
        return out;
    };
    out.push(kv("request", &format!("{} {}", r.name, some(&r.target))));
    out.push(kv("rule id", &some(&r.id)));
    out.push(kv("tool", &some(&r.tool)));
    if !r.next.is_empty() {
        out.push(kv("next", &r.next));
    }
    for (i, opt) in r.more.iter().enumerate() {
        out.push(kv(if i == 0 { "more options" } else { "" }, opt));
    }
    out.push(kv("actor", &some(&m.provider)));
    out.push(kv("workspace", &some(&m.workspace)));
    out.push(kv("decision", verdict_word(r.verdict)));
    if !r.reason.is_empty() {
        out.push(kv("reason", &r.reason));
    }
    if let Some(need) = &r.need {
        for (label, value) in [
            ("checked", &need.checked),
            ("missing", &need.missing),
            ("look at", &need.investigate),
            ("ask", &need.ask),
        ] {
            if !value.is_empty() {
                out.push(kv(label, value));
            }
        }
    }
    out.push(kv("event", &some(&r.event)));
    out.push(kv("receipt", &some(&r.receipt)));
    out.push(kv(
        "evidence",
        if r.receipt.is_empty() {
            "UNVERIFIED"
        } else {
            "PROVEN"
        },
    ));
    out
}
