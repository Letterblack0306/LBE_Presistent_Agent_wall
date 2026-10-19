//! Shared chrome: header, rule, composer, status line and the right-hand rail.
//! Only what the spec lists appears here; internals live in the details layer.
use crate::model::{Entry, Life, Mode, Model, Screen, Verdict};
use crate::text::{clip, width, wrap};
use crate::theme::Theme;
use ratatui::style::Style;
use ratatui::text::{Line, Span};

pub fn sp(s: impl Into<String>, st: Style) -> Span<'static> {
    Span::styled(s.into(), st)
}

pub fn spans_width(v: &[Span]) -> usize {
    v.iter().map(|s| width(&s.content)).sum()
}

/// `left` flush left, `right` flush right, clipped so neither overruns `w`.
pub fn spread(mut left: Vec<Span<'static>>, right: Vec<Span<'static>>, w: usize) -> Line<'static> {
    let lw = spans_width(&left);
    let rw = spans_width(&right);
    if lw + rw < w {
        left.push(sp(" ".repeat(w - lw - rw), Style::default()));
        left.extend(right);
    } else if lw < w {
        left.push(sp(" ", Style::default()));
    }
    Line::from(left)
}

pub fn rule(t: &Theme, w: usize) -> Line<'static> {
    Line::from(sp(t.g().rule.repeat(w), t.rule()))
}

pub fn fmt_k(n: u64) -> String {
    if n >= 1000 {
        let v = n as f64 / 1000.0;
        if (v - v.round()).abs() < 0.05 {
            format!("{}k", v.round() as u64)
        } else {
            format!("{v:.1}k")
        }
    } else {
        n.to_string()
    }
}

pub fn bar(t: &Theme, used: u64, total: u64, cells: usize) -> String {
    let g = t.g();
    let f = if total == 0 {
        0
    } else {
        ((cells as f64) * (used as f64 / total as f64)).round() as usize
    }
    .min(cells);
    format!(
        "{}{}{}{}",
        g.bar_l,
        g.fill.repeat(f),
        g.empty.repeat(cells - f),
        g.bar_r
    )
}

pub fn mark(t: &Theme) -> Vec<Span<'static>> {
    let g = t.g();
    vec![
        sp(g.mark[0], t.strong()),
        sp(g.mark[1], t.accent()),
        sp(g.mark[2], t.strong()),
        sp("  LBE", t.strong()),
    ]
}

pub fn target(m: &Model) -> String {
    match (m.provider.is_empty(), m.model.is_empty()) {
        (true, _) => "no provider".into(),
        (false, true) => m.provider.clone(),
        (false, false) => format!("{} · {}", m.provider, m.model),
    }
}

/// Control-plane dot: green connected, red offline. (Reconnecting is not reported.)
fn connection(m: &Model, t: &Theme) -> Span<'static> {
    if m.attached {
        sp(format!("{} connected", t.g().busy), t.ok())
    } else {
        sp(format!("{} offline", t.g().off), t.err())
    }
}

pub fn top_bar(m: &Model, t: &Theme, w: usize) -> Line<'static> {
    let mut left = vec![sp(" ", Style::default())];
    left.extend(mark(t));
    let conn = connection(m, t);
    let conn_w = width(&conn.content);
    let text = if let Some(k) = m.screen.fkey() {
        format!("F{k} {}   esc back", fkey_name(m.screen))
    } else {
        match m.mode {
            Mode::Audit => "AUDIT · read-only".to_string(),
            Mode::Plan => "PLAN · nothing executes".to_string(),
            Mode::Act => target(m),
        }
    };
    let screen_nav = m.screen.fkey().is_some();
    let left_w = spans_width(&left);
    let budget = w.saturating_sub(left_w + 3);
    let tail = if screen_nav { 0 } else { conn_w + 2 };
    let right_text = clip(&text, budget.saturating_sub(tail + 8), !t.d.unicode);
    let mut right: Vec<Span<'static>> = Vec::new();
    let text_st = if m.mode == Mode::Audit && !screen_nav {
        t.accent()
    } else {
        t.muted()
    };
    if !right_text.is_empty() {
        right.push(sp(right_text, text_st));
    }
    if !screen_nav {
        if !right.is_empty() {
            right.push(sp("  ", Style::default()));
        }
        right.push(conn);
    }
    let rw = spans_width(&right);
    let ws_budget = w.saturating_sub(left_w + 3 + rw + 1);
    left.push(sp(
        format!("  {}", clip(&m.workspace, ws_budget, !t.d.unicode)),
        t.muted(),
    ));
    right.push(sp(" ", Style::default()));
    spread(left, right, w)
}

fn fkey_name(s: Screen) -> &'static str {
    match s {
        Screen::Receipts => "log",
        other => other.title(),
    }
}

pub fn mode_seg(m: &Model, t: &Theme) -> Vec<Span<'static>> {
    let mut v = Vec::new();
    for mode in Mode::ALL {
        let name = mode.name().to_ascii_uppercase();
        if mode == m.mode {
            v.push(sp(format!("[{name}]"), t.accent()));
        } else {
            v.push(sp(format!(" {name} "), t.muted()));
        }
    }
    v
}

/// One state word from the runtime's facts, with the dot colour that goes with it.
pub fn state_word(m: &Model, t: &Theme) -> (&'static str, Style) {
    if !m.attached {
        return ("offline", t.err());
    }
    match m.life {
        Life::Stopping => return ("stopping…", t.warn()),
        Life::ConfirmStop => return ("waiting for you", t.warn()),
        Life::Running => {}
    }
    if m.pending.is_some() {
        ("waiting for you", t.warn())
    } else if m.busy {
        if m.activity.is_empty() {
            ("thinking", t.ok())
        } else {
            ("executing", t.ok())
        }
    } else if m.turn_rules.contains(&Verdict::Block) || m.turn_rules.contains(&Verdict::Failed) {
        ("blocked", t.err())
    } else {
        ("ready", t.ok())
    }
}

/// `● act · executing ■`
pub fn status_left(m: &Model, t: &Theme) -> Vec<Span<'static>> {
    let g = t.g();
    let (word, st) = state_word(m, t);
    let word = if t.d.unicode {
        word.to_string()
    } else {
        word.replace('…', "...")
    };
    let mut left = vec![
        sp(format!(" {} ", g.busy), st),
        sp(format!("{} {} ", m.mode.name(), g.dot), t.text()),
        sp(word, t.text()),
    ];
    if m.busy && m.pending.is_none() {
        left.push(sp(format!(" {}", bounce(t, m.tick)), t.muted()));
    }
    left
}

pub fn status_line(m: &Model, t: &Theme, w: usize) -> Line<'static> {
    spread(
        status_left(m, t),
        vec![sp("? help ", t.muted())],
        w,
    )
}

/// A single bouncing cell on a short track; static when motion is off.
pub fn bounce(t: &Theme, tick: u64) -> String {
    let cell = if t.d.unicode { '■' } else { '#' };
    if !t.d.motion {
        return cell.to_string();
    }
    let track = 5usize;
    let phase = (tick / 2) as usize % (2 * (track - 1));
    let pos = if phase < track {
        phase
    } else {
        2 * (track - 1) - phase
    };
    let mut s = vec![' '; track];
    s[pos] = cell;
    s.into_iter().collect()
}

/// Composer: `❯ Message LBE`, one row per input line (up to 4 shown). Returns lines
/// and the cursor offset (row, col) inside the area.
pub fn composer(
    m: &Model,
    t: &Theme,
    w: usize,
    mode_tag: bool,
) -> (Vec<Line<'static>>, (usize, usize)) {
    let prompt = t.g().prompt;
    let lead_w = width(prompt) + 2;
    let tag = if mode_tag {
        Some(m.mode.name().to_string())
    } else {
        None
    };
    let tag_w = tag.as_ref().map_or(0, |s| width(s) + 2);
    let avail = w.saturating_sub(lead_w + 1 + tag_w).max(1);
    let mut lines: Vec<Line<'static>> = Vec::new();
    let cursor0 = (0usize, lead_w);
    if m.composer.is_empty() || m.screen != Screen::Cockpit {
        let body = if m.screen == Screen::Cockpit {
            "Message LBE"
        } else {
            "esc to go back"
        };
        let mut left = vec![
            sp(format!(" {prompt} "), t.strong()),
            sp(clip(body, avail, !t.d.unicode), t.muted()),
        ];
        if let Some(tag) = &tag {
            let lw = spans_width(&left);
            left.push(sp(
                " ".repeat(w.saturating_sub(lw + width(tag) + 1)),
                Style::default(),
            ));
            left.push(sp(tag.clone(), t.muted()));
        }
        lines.push(Line::from(left));
        return (lines, cursor0);
    }
    let rows: Vec<String> = wrap(&m.composer, avail);
    let start = rows.len().saturating_sub(4);
    for (i, row) in rows[start..].iter().enumerate() {
        let lead = if i == 0 {
            format!(" {prompt} ")
        } else {
            " ".repeat(lead_w)
        };
        lines.push(Line::from(vec![
            sp(lead, t.strong()),
            sp(row.clone(), t.text()),
        ]));
    }
    let last = rows[start..].last().map(|r| width(r)).unwrap_or(0);
    (lines.clone(), (lines.len() - 1, lead_w + last))
}

fn lbl(t: &Theme, s: &str) -> Line<'static> {
    Line::from(sp(s.to_string(), t.label()))
}

/// Latest outcome for the rail: the last effect line, else the last blocked rule.
pub fn last_result(m: &Model, t: &Theme) -> Line<'static> {
    for e in m.entries.iter().rev() {
        match e {
            Entry::Effect(v, text) => {
                let (glyph, st) = verdict_glyph(*v, t);
                return Line::from(sp(format!("{glyph} {text}"), st));
            }
            Entry::Rule(r) if r.verdict != Verdict::Pass => {
                let (glyph, st) = verdict_glyph(r.verdict, t);
                return Line::from(sp(format!("{glyph} {} · {}", verdict_word(r.verdict), r.name), st));
            }
            _ => {}
        }
    }
    Line::from(sp("none yet", t.muted()))
}

pub fn verdict_glyph(v: Verdict, t: &Theme) -> (&'static str, Style) {
    let g = t.g();
    match v {
        Verdict::Pass => (g.ok, t.ok()),
        Verdict::Block => (g.block, t.err()),
        Verdict::Needs => (g.needs, t.warn()),
        Verdict::Failed => (g.failed, t.err()),
        Verdict::Advisory => (g.info, t.muted()),
        Verdict::Unknown => (g.partial, t.warn()),
    }
}

pub fn verdict_word(v: Verdict) -> &'static str {
    match v {
        Verdict::Pass => "passed",
        Verdict::Block => "blocked",
        Verdict::Needs => "needs you",
        Verdict::Failed => "failed",
        Verdict::Advisory => "advisory",
        Verdict::Unknown => "unknown",
    }
}

fn context(m: &Model, t: &Theme) -> Vec<Line<'static>> {
    let mut v = vec![lbl(t, "CONTEXT")];
    match m.ctx {
        Some((used, total)) if total > 0 => v.push(Line::from(sp(
            format!("{} {}/{}", bar(t, used, total, 12), fmt_k(used), fmt_k(total)),
            t.text(),
        ))),
        Some((used, _)) => v.push(Line::from(sp(format!("{} used", fmt_k(used)), t.muted()))),
        None => v.push(Line::from(sp("unknown", t.muted()))),
    }
    v
}

fn keys(t: &Theme) -> Vec<Line<'static>> {
    vec![
        lbl(t, "KEYS"),
        Line::from(sp("F2 providers  F3 models", t.muted())),
        Line::from(sp("F4 settings   F5 capabilities", t.muted())),
        Line::from(sp("F6 report     F7 sessions", t.muted())),
        Line::from(sp("F8 log", t.muted())),
    ]
}

fn scope(m: &Model, t: &Theme, read_only: bool) -> Vec<Line<'static>> {
    let mut v = vec![lbl(t, "SCOPE")];
    v.push(Line::from(sp(
        if m.workspace.is_empty() {
            "unknown".to_string()
        } else {
            m.workspace.clone()
        },
        t.strong(),
    )));
    if let Some((b, n)) = &m.git {
        v.push(Line::from(sp(format!("{b} · {n} changed"), t.muted())));
    }
    if read_only {
        v.push(Line::from(sp("read-only", t.muted())));
    }
    v
}

pub fn rail(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut v: Vec<Line<'static>> = Vec::new();
    let gap = |v: &mut Vec<Line<'static>>| v.push(Line::default());
    if m.screen == Screen::Cockpit && m.mode == Mode::Audit {
        v.extend(scope(m, t, true));
        gap(&mut v);
        v.push(lbl(t, "READ"));
        v.push(Line::from(sp(
            if m.reads == 1 {
                "1 read".to_string()
            } else {
                format!("{} reads", m.reads)
            },
            t.text(),
        )));
        v.push(Line::from(sp(
            if m.executed == 0 {
                "nothing changed".to_string()
            } else {
                format!("{} changed", m.executed)
            },
            if m.executed == 0 { t.muted() } else { t.warn() },
        )));
        gap(&mut v);
        v.push(lbl(t, "REPORT"));
        v.push(Line::from(sp("F6 preview", t.muted())));
        return v;
    }
    v.push(lbl(t, "TASK"));
    if m.task.is_empty() {
        v.push(Line::from(sp("no task yet", t.muted())));
    } else {
        let rows = wrap(&m.task, w.max(8));
        let more = rows.len() > 2;
        for (i, r) in rows.into_iter().take(2).enumerate() {
            let r = if more && i == 1 {
                clip(&format!("{r} {}", t.g().dot.repeat(3)), w.max(8), !t.d.unicode)
            } else {
                r
            };
            v.push(Line::from(sp(clip(&r, w.max(8), !t.d.unicode), t.text())));
        }
    }
    gap(&mut v);
    v.push(lbl(t, "SESSION"));
    v.push(Line::from(sp(
        if m.provider.is_empty() {
            "no provider".to_string()
        } else if m.model.is_empty() {
            m.provider.clone()
        } else {
            format!("{} · {}", m.provider, m.model)
        },
        t.text(),
    )));
    v.push(Line::from(mode_seg(m, t)));
    gap(&mut v);
    if m.screen == Screen::Cockpit && m.mode == Mode::Plan {
        let proposed = m.entries.iter().any(|e| matches!(e, Entry::Agent(_)));
        v.push(lbl(t, "PLAN STATE"));
        v.push(Line::from(sp(
            if proposed { "proposed" } else { "no plan yet" },
            if proposed { t.warn() } else { t.muted() },
        )));
    } else {
        v.extend(scope(m, t, false));
        gap(&mut v);
        v.push(lbl(t, "LAST RESULT"));
        v.push(last_result(m, t));
    }
    gap(&mut v);
    v.extend(context(m, t));
    gap(&mut v);
    v.extend(keys(t));
    v
}
