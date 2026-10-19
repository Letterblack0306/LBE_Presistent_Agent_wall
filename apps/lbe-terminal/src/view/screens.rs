//! F2-F8 screens. Each shows only what the bridge reported; an unreported value
//! reads `-` or `not reported`, never a guess. No explainer copy.
use super::chrome::{mode_seg, sp, verdict_glyph, verdict_word};
use crate::model::{Entry, Model, Verdict};
use crate::text::{clip, clip_left, pad, wrap};
use crate::theme::Theme;
use ratatui::style::Style;
use ratatui::text::Line;

fn head(t: &Theme, title: &str, hint: &str, w: usize) -> Line<'static> {
    super::chrome::spread(
        vec![sp(format!(" {title}"), t.label())],
        vec![sp(format!("{hint} "), t.muted())],
        w,
    )
}

fn row(t: &Theme, selected: bool, active: bool, cols: Vec<(String, Style)>) -> Line<'static> {
    let g = t.g();
    let mark = if selected {
        format!(" {} ", g.cursor)
    } else {
        "   ".to_string()
    };
    let star = if active { "* " } else { "  " };
    let mut spans = vec![sp(mark, t.warn()), sp(star, t.warn())];
    for (text, st) in cols {
        spans.push(sp(text, st));
    }
    let mut line = Line::from(spans);
    if selected {
        line = line.style(t.selected());
    }
    line
}

fn unattached(m: &Model, t: &Theme, what: &str) -> Option<Vec<Line<'static>>> {
    if m.attached {
        None
    } else {
        Some(vec![
            Line::default(),
            Line::from(sp(format!("   {what}: offline"), t.err())),
        ])
    }
}

pub fn providers(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = vec![
        head(t, "PROVIDERS", "Enter detail · r refresh", w),
        Line::default(),
    ];
    if let Some(u) = unattached(m, t, "providers") {
        out.extend(u);
        return out;
    }
    let Some(rows) = &m.providers else {
        out.push(Line::from(sp("   loading", t.muted())));
        return out;
    };
    let c = [24usize, 14];
    out.push(Line::from(sp(
        format!("     {}{}state", pad("provider", c[0]), pad("sign-in", c[1])),
        t.muted(),
    )));
    for (i, p) in rows.iter().enumerate() {
        let (state, st) = match p.auth.as_str() {
            "login" => ("sign in", t.warn()),
            "none" | "configured" => ("ready", t.ok()),
            _ => ("-", t.muted()),
        };
        out.push(row(
            t,
            i == m.sel_provider,
            p.id == m.provider,
            vec![
                (pad(&p.id, c[0]), t.strong()),
                (pad(if p.auth.is_empty() { "-" } else { &p.auth }, c[1]), t.muted()),
                (state.to_string(), st),
            ],
        ));
    }
    if m.detail {
        if let Some(p) = rows.get(m.sel_provider) {
            out.push(Line::default());
            let hint = if p.login_hint.is_empty() {
                "no sign-in hint reported".to_string()
            } else {
                p.login_hint.clone()
            };
            out.push(Line::from(sp(
                clip(&format!("   {}  {hint}", p.id), w, !t.d.unicode),
                t.text(),
            )));
        }
    }
    out
}

pub fn models(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = vec![head(t, "MODELS", "Enter select · r refresh", w), Line::default()];
    if let Some(u) = unattached(m, t, "models") {
        out.extend(u);
        return out;
    }
    let Some(list) = &m.models else {
        out.push(Line::from(sp("   loading", t.muted())));
        return out;
    };
    if list.is_empty() {
        out.push(Line::from(sp("   the endpoint reported no models", t.warn())));
        return out;
    }
    let idw = w.saturating_sub(5 + 9 + 7).max(10);
    out.push(Line::from(sp(
        format!("     {}{}tools", pad("model", idw), pad("context", 9)),
        t.muted(),
    )));
    for (i, id) in list.iter().enumerate() {
        out.push(row(
            t,
            i == m.sel_model,
            *id == m.model,
            vec![
                (pad(&clip(id, idw - 1, !t.d.unicode), idw), t.strong()),
                (pad("—", 9), t.muted()),
                ("—".to_string(), t.muted()),
            ],
        ));
    }
    out
}

pub fn settings(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let kv = |k: &str, v: String, st: Style| {
        Line::from(vec![sp(format!("   {:<16}", k), t.muted()), sp(v, st)])
    };
    let known = |s: &str| {
        if s.is_empty() {
            "not reported".to_string()
        } else {
            s.to_string()
        }
    };
    let onoff = |b: bool| if b { "on" } else { "off" }.to_string();
    let mut mode = vec![sp("   mode            ", t.muted())];
    mode.extend(mode_seg(m, t));
    vec![
        head(t, "SETTINGS", "Esc back", w),
        Line::default(),
        Line::from(sp(" Session", t.label())),
        Line::from(mode),
        kv("permission", known(&m.permission), t.text()),
        kv("policy", known(&m.policy), t.text()),
        kv("session id", known(&m.session_id), t.text()),
        Line::default(),
        Line::from(sp(" Providers · Capabilities", t.label())),
        Line::from(sp("   F2 and F5", t.muted())),
        Line::default(),
        Line::from(sp(" Memory & history", t.label())),
        Line::from(sp("   not reported", t.muted())),
        Line::default(),
        Line::from(sp(" Display", t.label())),
        kv("c  colour", onoff(m.display.color), t.text()),
        kv(
            "g  glyphs",
            if m.display.unicode { "unicode" } else { "ascii" }.into(),
            t.text(),
        ),
        kv("m  motion", onoff(m.display.motion), t.text()),
        Line::default(),
        Line::from(sp(" Workspace policy", t.label())),
        Line::from(sp("   read-only · edited outside the UI", t.muted())),
    ]
}

pub fn capabilities(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = vec![
        head(t, "CAPABILITIES", "Enter detail · r refresh", w),
        Line::default(),
    ];
    if let Some(u) = unattached(m, t, "capabilities") {
        out.extend(u);
        return out;
    }
    let Some(caps) = &m.caps else {
        out.push(Line::from(sp("   loading", t.muted())));
        return out;
    };
    if !caps.configured {
        out.push(Line::from(sp("   nothing discovered", t.warn())));
        out.push(Line::from(sp(
            "   set LBE_CAPABILITY_REGISTRY to project a registry here",
            t.muted(),
        )));
        return out;
    }
    if !caps.error.is_empty() {
        out.push(Line::from(sp(
            clip(&format!("   registry error: {}", caps.error), w, !t.d.unicode),
            t.err(),
        )));
        return out;
    }
    if caps.items.is_empty() {
        out.push(Line::from(sp("   registry is empty", t.muted())));
        return out;
    }
    let c = [24usize, 10, 12, 11];
    out.push(Line::from(sp(
        format!(
            "     {}{}{}{}healthy",
            pad("name", c[0]),
            pad("kind", c[1]),
            pad("configured", c[2]),
            pad("connected", c[3])
        ),
        t.muted(),
    )));
    for (i, it) in caps.items.iter().enumerate() {
        // Three separate facts; never merged into one "ok".
        let (healthy, st) = match it.availability.as_str() {
            "" => ("-".to_string(), t.muted()),
            a if a.contains("unavail") || a.contains("not") => {
                (format!("{} offline", t.g().off), t.err())
            }
            a if a.contains("unhealthy") || a.contains("degrad") => {
                (format!("{} unhealthy", t.g().partial), t.warn())
            }
            _ => ("yes".to_string(), t.ok()),
        };
        out.push(row(
            t,
            i == m.sel_cap,
            false,
            vec![
                (pad(&it.id, c[0]), t.strong()),
                (pad(&it.kind, c[1]), t.muted()),
                (pad(if it.enabled { "yes" } else { "no" }, c[2]), t.text()),
                (pad("-", c[3]), t.muted()),
                (healthy, st),
            ],
        ));
    }
    if m.detail {
        if let Some(it) = caps.items.get(m.sel_cap) {
            out.push(Line::default());
            out.push(Line::from(sp(
                format!("   {}  access {}  risk {}", it.id, it.access, it.risk),
                t.muted(),
            )));
            for r in wrap(&it.rationale, w.saturating_sub(6)) {
                out.push(Line::from(sp(format!("   {r}"), t.text())));
            }
        }
    }
    out
}

pub fn report(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let h = |s: &str| Line::from(sp(format!(" {s}"), t.strong()));
    let mut out = vec![head(t, "REPORT", "x export · Esc back", w), Line::default()];
    out.push(h("1  Scope"));
    out.push(Line::from(sp(
        clip(
            &format!(
                "   {} · {} · {} read{} · {} changed",
                m.workspace,
                m.mode.name(),
                m.reads,
                if m.reads == 1 { "" } else { "s" },
                m.executed
            ),
            w,
            !t.d.unicode,
        ),
        t.muted(),
    )));
    out.push(h("2  Findings"));
    let blocked: Vec<_> = m
        .log
        .iter()
        .filter(|r| r.verdict != Verdict::Pass)
        .collect();
    if blocked.is_empty() {
        out.push(Line::from(sp("   none reported", t.muted())));
    }
    for r in blocked {
        let (glyph, st) = verdict_glyph(r.verdict, t);
        out.push(Line::from(sp(
            clip(
                &format!("   {glyph} {} · {}", r.name, verdict_word(r.verdict)),
                w,
                !t.d.unicode,
            ),
            st,
        )));
    }
    out.push(h("3  Open questions"));
    match &m.pending {
        Some(p) => out.push(Line::from(sp(
            clip(&format!("   ? permission: {}", p.target), w, !t.d.unicode),
            t.warn(),
        ))),
        None => out.push(Line::from(sp("   none", t.muted()))),
    }
    out.push(h("4  Not verified"));
    out.push(Line::from(sp(
        "   anything the runtime did not report",
        t.muted(),
    )));
    out.push(h("5  Last reply"));
    match m.entries.iter().rev().find_map(|e| {
        if let Entry::Agent(s) = e {
            Some(s)
        } else {
            None
        }
    }) {
        Some(s) => {
            for r in wrap(s, w.saturating_sub(5)).into_iter().take(5) {
                out.push(Line::from(sp(format!("   {r}"), t.text())));
            }
        }
        None => out.push(Line::from(sp("   none", t.muted()))),
    }
    out
}

pub fn sessions(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = vec![head(t, "SESSIONS & TASKS", "Esc back", w), Line::default()];
    let (state, st) = super::chrome::state_word(m, t);
    let task = if m.task.is_empty() {
        "no task yet".to_string()
    } else {
        m.task.clone()
    };
    out.push(row(
        t,
        true,
        true,
        vec![
            (
                clip(&task, w.saturating_sub(24).max(8), !t.d.unicode),
                t.strong(),
            ),
            (
                format!(" {} {state}", t.g().dot),
                st,
            ),
        ],
    ));
    out.push(Line::default());
    out.push(Line::from(sp(
        "   queued and past sessions: not reported by the runtime",
        t.muted(),
    )));
    out
}

pub fn receipts(m: &Model, t: &Theme, w: usize) -> Vec<Line<'static>> {
    let mut out = vec![head(t, "RECEIPTS", "Enter details · Esc back", w), Line::default()];
    if m.log.is_empty() {
        out.push(Line::from(sp("   nothing recorded this session", t.muted())));
        return out;
    }
    let c = [4usize, 29];
    let tw = w.saturating_sub(5 + c[0] + c[1] + 10 + 12).max(8);
    out.push(Line::from(sp(
        format!(
            "     {}{}{}{}receipt",
            pad("#", c[0]),
            pad("action", c[1]),
            pad("target", tw),
            pad("decision", 10)
        ),
        t.muted(),
    )));
    let total = m.log.len();
    for (i, r) in m.log.iter().rev().enumerate() {
        let (_, st) = verdict_glyph(r.verdict, t);
        out.push(row(
            t,
            i == m.sel_log,
            false,
            vec![
                (pad(&(total - i).to_string(), c[0]), t.muted()),
                (pad(&r.name, c[1]), t.text()),
                (
                    pad(
                        &clip_left(if r.target.is_empty() { "-" } else { &r.target }, tw - 1, !t.d.unicode),
                        tw,
                    ),
                    t.muted(),
                ),
                (pad(verdict_word(r.verdict), 10), st),
                (
                    if r.receipt.is_empty() {
                        "-".to_string()
                    } else {
                        r.receipt.clone()
                    },
                    t.muted(),
                ),
            ],
        ));
    }
    out
}
