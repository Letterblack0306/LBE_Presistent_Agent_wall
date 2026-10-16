//! LBE terminal UI — cockpit per the "LBE terminal UI proposal" (5 boards).
//!
//! Board 1 cockpit: header, transcript, SESSION rail, composer + one quiet status.
//! Board 2 mark:    half-block splash in an empty session, NO_COLOR/ASCII fallbacks.
//! Board 3 tiers:   wide (>=100 cols, rail), compact (60..99, rail folds to one
//!                  status line), very short (<20 rows, no header). Minimum 60x18.
//! Board 4 screens: F2 providers, F3 models, F4 settings, F5 capabilities, F6 report.
//! Board 5 gate:    tabs (Tab cycles), permission card (a allow / d deny), gate steps.
//!
//! Rules carried from the user's notes: AUDIT centers agent/UI text; pending items
//! are always visible; nothing is silent; a missing runtime is stated, not faked.

use ratatui::{
    layout::{Alignment, Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};

pub const MIN_WIDTH: u16 = 60;
pub const MIN_HEIGHT: u16 = 18;
const WIDE_WIDTH: u16 = 100;
const SHORT_HEIGHT: u16 = 20;
const RAIL_WIDTH: u16 = 30;

const BG: Color = Color::Rgb(0x06, 0x07, 0x0d);
const PANEL: Color = Color::Rgb(0x0b, 0x0c, 0x15);
const RAIL_BG: Color = Color::Rgb(0x12, 0x13, 0x1d);
const LINE: Color = Color::Rgb(0x2a, 0x2a, 0x2d);
const TEXT: Color = Color::Rgb(0xe9, 0xe9, 0xef);
const DIM: Color = Color::Rgb(0x8e, 0x8e, 0x93);
const RED: Color = Color::Rgb(0xef, 0x4b, 0x4b);
const GREEN: Color = Color::Rgb(0x4a, 0xde, 0x80);
const AMBER: Color = Color::Rgb(0xe5, 0xb5, 0x67);

/// Board 2, plain-text mark (22 columns x 12 rows).
pub const MARK: [&str; 12] = [
    "█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█",
    "█ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ █",
    "█ ██▀▀▀▀▀▀▀▀▀▀▀▀▀▀██ █",
    "█ ██  ▄▄▄ ██ ▄▄▄  ██ █",
    "█ ██  ██▀ ██ ▀██  ██ █",
    "█ ██  ██  ██  ██  ██ █",
    "█ ██  ██  ██  ██  ██ █",
    "█ ██  ██▄ ██ ▄██  ██ █",
    "█ ██  ▀▀▀ ██ ▀▀▀  ██ █",
    "█ ██▄▄▄▄▄▄▄▄▄▄▄▄▄▄██ █",
    "█ ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ █",
    "█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█",
];

/// Board 2, legacy-console ASCII mark.
pub const MARK_ASCII: [&str; 8] = [
    "+--------------------+",
    "| +----------------+ |",
    "| |  --  ## --     | |",
    "| | |    ##    |   | |",
    "| | |    ##    |   | |",
    "| |  --  ## --     | |",
    "| +----------------+ |",
    "+--------------------+",
];

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
pub enum Mode {
    Plan,
    Act,
    Audit,
}

impl Mode {
    pub fn label(self) -> &'static str {
        match self {
            Mode::Plan => "plan",
            Mode::Act => "act",
            Mode::Audit => "audit",
        }
    }
    pub fn next(self) -> Mode {
        match self {
            Mode::Plan => Mode::Act,
            Mode::Act => Mode::Audit,
            Mode::Audit => Mode::Plan,
        }
    }
    pub fn parse(s: &str) -> Option<Mode> {
        match s.trim().to_ascii_lowercase().as_str() {
            "plan" => Some(Mode::Plan),
            "act" => Some(Mode::Act),
            "audit" => Some(Mode::Audit),
            _ => None,
        }
    }
}

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
pub enum Tab {
    Conversation,
    Capabilities,
    Evidence,
    Gate,
}

impl Tab {
    pub const ALL: [Tab; 4] = [Tab::Conversation, Tab::Capabilities, Tab::Evidence, Tab::Gate];
    pub fn label(self) -> &'static str {
        match self {
            Tab::Conversation => "Conversation",
            Tab::Capabilities => "Capabilities",
            Tab::Evidence => "Evidence",
            Tab::Gate => "Gate",
        }
    }
    pub fn next(self) -> Tab {
        let i = Tab::ALL.iter().position(|t| *t == self).unwrap_or(0);
        Tab::ALL[(i + 1) % Tab::ALL.len()]
    }
}

/// Evidence vocabulary from board 4.
#[derive(PartialEq, Eq, Clone, Copy, Debug)]
pub enum Evidence {
    Proven,
    Supported,
    Hypothesis,
    Unknown,
    Blocked,
    Partial,
}

impl Evidence {
    pub fn label(self) -> &'static str {
        match self {
            Evidence::Proven => "PROVEN",
            Evidence::Supported => "SUPPORTED",
            Evidence::Hypothesis => "HYPOTHESIS",
            Evidence::Unknown => "UNKNOWN",
            Evidence::Blocked => "BLOCKED",
            Evidence::Partial => "PARTIAL",
        }
    }
    fn color(self) -> Color {
        match self {
            Evidence::Proven | Evidence::Supported => GREEN,
            Evidence::Hypothesis | Evidence::Partial => AMBER,
            Evidence::Unknown => DIM,
            Evidence::Blocked => RED,
        }
    }
}

#[derive(Clone, Debug)]
pub enum Entry {
    You(String),
    Lbe(String),
    /// Tool/process line: collapsed form is `▸ name detail  status`.
    Tool { name: String, detail: String, tag: Evidence, took: Option<String> },
    Note { tag: Evidence, text: String },
    Info(String),
}

#[derive(Clone, Debug)]
pub struct Permission {
    pub id: String,
    pub action: String,
    pub scope: String,
}

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
pub enum Screen {
    Providers,
    Models,
    Settings,
    Capabilities,
    Report,
    Keys,
    Commands,
}

impl Screen {
    fn title(self) -> &'static str {
        match self {
            Screen::Providers => "F2 providers",
            Screen::Models => "F3 models",
            Screen::Settings => "F4 settings",
            Screen::Capabilities => "F5 capabilities",
            Screen::Report => "F6 report",
            Screen::Keys => "F1 keys",
            Screen::Commands => "Ctrl+K commands",
        }
    }
}

/// Command table: single source for /help, Tab completion and Ctrl+K.
pub const COMMANDS: [(&str, &str); 11] = [
    ("/help", "list commands"),
    ("/providers", "list providers the runtime can use"),
    ("/model <id>", "select a model"),
    ("/mode plan|act|audit", "switch mode"),
    ("/audit", "switch to AUDIT mode"),
    ("/stop", "stop the active turn"),
    ("/keys", "show key bindings"),
    ("/clear", "clear the transcript"),
    ("/report", "open the report screen"),
    ("/quit", "leave LBE"),
    ("/exit", "leave LBE"),
];

pub const KEYS: [(&str, &str); 12] = [
    ("Enter", "send"),
    ("Ctrl+J", "newline"),
    ("Tab", "next tab"),
    ("Shift+Tab", "next mode"),
    ("F1", "keys"),
    ("F2", "providers"),
    ("F3", "models"),
    ("F4", "settings"),
    ("F5", "capabilities"),
    ("F6", "report"),
    ("Ctrl+K", "commands"),
    ("Esc", "back / stop turn"),
];

pub struct SessionSnapshot {
    pub workspace: String,
    pub provider: String,
    pub model: String,
    pub mode: Mode,
    pub tab: Tab,
    pub session_id: String,
    pub ctx_used: u32,
    pub ctx_max: u32,
    pub providers: Vec<String>,
    pub receipts: Vec<(Evidence, String)>,
    pub entries: Vec<Entry>,
    pub pending: Option<Permission>,
    pub busy: bool,
    pub runtime_attached: bool,
    pub screen: Option<Screen>,
    pub input_buffer: String,
    /// Lines scrolled up from the bottom (0 = stick to bottom).
    pub scroll_up: usize,
    pub no_color: bool,
    /// JSON lines queued for the runtime bridge (drained by main).
    pub outbox: Vec<String>,
}

pub struct App {
    pub snapshot: SessionSnapshot,
}

impl SessionSnapshot {
    pub fn new(workspace: String, session_id: String, providers: Vec<String>) -> Self {
        SessionSnapshot {
            workspace,
            provider: "no provider".to_string(),
            model: "[model]".to_string(),
            mode: Mode::Act,
            tab: Tab::Conversation,
            session_id,
            ctx_used: 0,
            ctx_max: 0,
            providers,
            receipts: Vec::new(),
            entries: Vec::new(),
            pending: None,
            busy: false,
            runtime_attached: false,
            screen: None,
            input_buffer: String::new(),
            scroll_up: 0,
            no_color: false,
            outbox: Vec::new(),
        }
    }
}

// ---------------------------------------------------------------- styles

fn dim() -> Style {
    Style::default().fg(DIM)
}
fn text() -> Style {
    Style::default().fg(TEXT)
}
fn red() -> Style {
    Style::default().fg(RED)
}

fn sp(s: impl Into<String>, st: Style) -> Span<'static> {
    Span::styled(s.into(), st)
}

// ---------------------------------------------------------------- draw

pub fn draw(frame: &mut Frame, app: &App) {
    let area = frame.size();
    frame.render_widget(Block::default().style(Style::default().bg(BG).fg(TEXT)), area);

    if area.width < MIN_WIDTH || area.height < MIN_HEIGHT {
        let msg = format!(
            "LBE needs at least {MIN_WIDTH}x{MIN_HEIGHT}.\nThis terminal is {}x{}.",
            area.width, area.height
        );
        let w = area.width.min(46);
        let h = area.height.min(4);
        let r = Rect::new(
            area.x + area.width.saturating_sub(w) / 2,
            area.y + area.height.saturating_sub(h) / 2,
            w,
            h,
        );
        frame.render_widget(
            Paragraph::new(msg)
                .style(Style::default().fg(AMBER).bg(BG))
                .alignment(Alignment::Center),
            r,
        );
        return;
    }

    let s = &app.snapshot;
    let wide = area.width >= WIDE_WIDTH;
    let short = area.height < SHORT_HEIGHT;
    let composer_lines = s.input_buffer.split('\n').count().clamp(1, 5) as u16;

    let header_h: u16 = if short { 0 } else { 1 };
    let tabs_h: u16 = if wide && !short { 1 } else { 0 };
    // composer: 1 rule + lines + 1 status (wide/compact status folded into a line)
    let composer_h: u16 = composer_lines + 1;
    let status_h: u16 = 1;

    let rows = Layout::vertical([
        Constraint::Length(header_h),
        Constraint::Length(tabs_h),
        Constraint::Min(3),
        Constraint::Length(composer_h),
        Constraint::Length(status_h),
    ])
    .split(area);

    if header_h > 0 {
        draw_header(frame, rows[0], s);
    }
    if tabs_h > 0 {
        draw_tabs(frame, rows[1], s);
    }

    let body = rows[2];
    if let Some(screen) = s.screen {
        draw_screen(frame, body, s, screen);
    } else if s.tab != Tab::Conversation && wide {
        draw_tab_body(frame, body, s);
    } else if wide {
        let cols = Layout::horizontal([Constraint::Min(20), Constraint::Length(RAIL_WIDTH)]).split(body);
        draw_transcript(frame, cols[0], s);
        draw_rail(frame, cols[1], s);
    } else {
        draw_transcript(frame, body, s);
    }

    let cursor = draw_composer(frame, rows[3], s);
    draw_status(frame, rows[4], s, wide);
    if s.screen.is_none() {
        frame.set_cursor(cursor.0, cursor.1);
    }
}

fn mark_line(s: &SessionSnapshot, narrow: bool) -> Vec<Span<'static>> {
    if narrow {
        return vec![sp("LBE", text().add_modifier(Modifier::BOLD))];
    }
    if s.no_color {
        return vec![
            sp("[|] ", text()),
            sp("LBE", text().add_modifier(Modifier::BOLD)),
        ];
    }
    vec![
        sp("[", text()),
        sp("┃", red().add_modifier(Modifier::BOLD)),
        sp("] ", text()),
        sp("LBE", text().add_modifier(Modifier::BOLD)),
    ]
}

fn draw_header(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let narrow = area.width < 64;
    let mut left = mark_line(s, narrow);
    left.push(sp(format!(" {}", s.workspace), dim()));
    let right = if s.provider == "no provider" {
        format!("{} · {}", s.provider, s.model)
    } else {
        format!("{} · {}", s.provider, s.model)
    };
    let used = left.iter().map(|x| x.content.chars().count()).sum::<usize>();
    let rlen = right.chars().count();
    let gap = (area.width as usize).saturating_sub(used + rlen + 2);
    left.push(sp(" ".repeat(gap + 1), Style::default()));
    left.push(sp(right, dim()));
    frame.render_widget(
        Paragraph::new(Line::from(left)).style(Style::default().bg(PANEL)),
        area,
    );
}

fn draw_tabs(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let mut spans = vec![sp(" ", Style::default())];
    for t in Tab::ALL {
        let active = t == s.tab;
        let st = if active {
            text().add_modifier(Modifier::UNDERLINED)
        } else {
            dim()
        };
        spans.push(sp(t.label(), st));
        spans.push(sp("   ", Style::default()));
    }
    let gate = if s.pending.is_some() { "BLOCKED" } else { "clear" };
    let gate_color = if s.pending.is_some() { AMBER } else { GREEN };
    spans.push(sp(format!("gate {gate}"), Style::default().fg(gate_color)));
    frame.render_widget(Paragraph::new(Line::from(spans)).style(Style::default().bg(PANEL)), area);
}

// ---------------------------------------------------------------- transcript

fn wrap(text_: &str, width: usize) -> Vec<String> {
    let width = width.max(8);
    let mut out = Vec::new();
    for raw in text_.split('\n') {
        let mut line = String::new();
        let mut len = 0usize;
        for word in raw.split(' ') {
            let wl = word.chars().count();
            if len > 0 && len + 1 + wl > width {
                out.push(std::mem::take(&mut line));
                len = 0;
            }
            if len > 0 {
                line.push(' ');
                len += 1;
            }
            // hard-split very long words
            let mut w = word;
            while w.chars().count() > width {
                let cut: String = w.chars().take(width).collect();
                if len > 0 {
                    out.push(std::mem::take(&mut line));
                    len = 0;
                }
                out.push(cut.clone());
                w = &w[cut.len()..];
            }
            line.push_str(w);
            len += w.chars().count();
        }
        out.push(line);
    }
    out
}

fn entry_lines(e: &Entry, width: usize, pending: Option<&Permission>) -> Vec<Line<'static>> {
    let mut out: Vec<Line<'static>> = Vec::new();
    match e {
        Entry::You(t) => {
            for (i, l) in wrap(t, width.saturating_sub(4)).into_iter().enumerate() {
                let prefix = if i == 0 { sp("you ", dim()) } else { sp("    ", dim()) };
                out.push(Line::from(vec![prefix, sp(l, text())]));
            }
            out.push(Line::from(""));
        }
        Entry::Lbe(t) => {
            for (i, l) in wrap(t, width.saturating_sub(4)).into_iter().enumerate() {
                let prefix = if i == 0 { sp("lbe ", red()) } else { sp("    ", dim()) };
                out.push(Line::from(vec![prefix, sp(l, text())]));
            }
        }
        Entry::Tool { name, detail, tag, took } => {
            let mut v = vec![
                sp("    ▸ ", dim()),
                sp(name.clone(), dim()),
                sp("  ", dim()),
                sp(detail.clone(), dim()),
                sp("  ", dim()),
            ];
            let status = match took {
                Some(t) if *tag == Evidence::Proven => format!("✓ {t}"),
                _ => tag.label().to_string(),
            };
            v.push(sp(status, Style::default().fg(tag.color())));
            out.push(Line::from(v));
        }
        Entry::Note { tag, text: t } => {
            let label = format!("{} ", tag.label());
            let pad = " ".repeat(4 + label.chars().count());
            for (i, l) in wrap(t, width.saturating_sub(4 + label.chars().count())).into_iter().enumerate() {
                if i == 0 {
                    out.push(Line::from(vec![
                        sp("    ", dim()),
                        sp(label.clone(), Style::default().fg(tag.color()).add_modifier(Modifier::BOLD)),
                        sp(l, text()),
                    ]));
                } else {
                    out.push(Line::from(vec![sp(pad.clone(), dim()), sp(l, text())]));
                }
            }
        }
        Entry::Info(t) => {
            for l in wrap(t, width.saturating_sub(4)) {
                out.push(Line::from(vec![sp("    ", dim()), sp(l, dim())]));
            }
        }
    }
    let _ = pending;
    out
}

fn permission_lines(p: &Permission, width: usize) -> Vec<Line<'static>> {
    let bar = Style::default().fg(AMBER);
    let mut v = Vec::new();
    v.push(Line::from(vec![
        sp("  ▌ ", bar),
        sp("PERMISSION REQUIRED", bar.add_modifier(Modifier::BOLD)),
        sp(format!("   {}", p.id), dim()),
    ]));
    for l in wrap(&p.action, width.saturating_sub(6)) {
        v.push(Line::from(vec![sp("  ▌ ", bar), sp(l, Style::default().fg(Color::Rgb(0xf0, 0xd4, 0x9e)))]));
    }
    for l in wrap(&p.scope, width.saturating_sub(6)) {
        v.push(Line::from(vec![sp("  ▌ ", bar), sp(l, dim())]));
    }
    v.push(Line::from(vec![
        sp("  ▌ ", bar),
        sp(" a Allow once ", Style::default().bg(GREEN).fg(BG).add_modifier(Modifier::BOLD)),
        sp("  ", Style::default()),
        sp(" d Deny ", Style::default().fg(DIM)),
    ]));
    v
}

fn build_transcript(s: &SessionSnapshot, width: usize) -> Vec<Line<'static>> {
    let mut lines: Vec<Line<'static>> = Vec::new();
    for e in &s.entries {
        lines.extend(entry_lines(e, width, s.pending.as_ref()));
    }
    if let Some(p) = &s.pending {
        lines.extend(permission_lines(p, width));
    }
    lines
}

fn draw_transcript(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let w = area.width.saturating_sub(2) as usize;
    let h = area.height as usize;
    let inner = Rect::new(area.x + 1, area.y, area.width.saturating_sub(2), area.height);

    if s.entries.is_empty() && s.pending.is_none() {
        draw_splash(frame, inner, s);
        return;
    }

    let mut lines = build_transcript(s, w);
    let total = lines.len();
    let max_up = total.saturating_sub(h);
    let up = s.scroll_up.min(max_up);
    let end = total - up;
    let start = end.saturating_sub(h);
    let mut view: Vec<Line<'static>> = lines.drain(start..end).collect();
    if s.mode == Mode::Audit {
        // AUDIT: agent + UI text is centered to mark the difference.
        view = view
            .into_iter()
            .map(|l| l.alignment(Alignment::Center))
            .collect();
    }
    // bottom-align so the latest line sits just above the composer
    let blank = h.saturating_sub(view.len());
    let mut padded: Vec<Line<'static>> = (0..blank).map(|_| Line::from("")).collect();
    padded.extend(view);
    frame.render_widget(Paragraph::new(padded).style(Style::default().bg(BG)), inner);
}

fn draw_splash(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let mut lines: Vec<Line<'static>> = Vec::new();
    let mark: &[&str] = if s.no_color && area.height < 14 { &MARK_ASCII } else { &MARK };
    let show_mark = area.height as usize >= mark.len() + 4;
    if show_mark {
        for (i, row) in mark.iter().enumerate() {
            let edge = i == 0 || i == mark.len() - 1;
            let st = if s.no_color {
                text()
            } else if edge {
                red()
            } else {
                text()
            };
            lines.push(Line::from(sp(row.to_string(), st)).alignment(Alignment::Center));
        }
        lines.push(Line::from(""));
    }
    lines.push(
        Line::from(sp("What can I do for you?", text().add_modifier(Modifier::BOLD)))
            .alignment(Alignment::Center),
    );
    lines.push(Line::from(sp("/help lists commands · F1 keys", dim())).alignment(Alignment::Center));
    if !s.runtime_attached {
        lines.push(Line::from(""));
        lines.push(
            Line::from(vec![
                sp("BLOCKED ", Style::default().fg(AMBER).add_modifier(Modifier::BOLD)),
                sp("no runtime session attached; messages cannot be answered yet", dim()),
            ])
            .alignment(Alignment::Center),
        );
    }
    let h = lines.len() as u16;
    let top = area.height.saturating_sub(h) / 2;
    let r = Rect::new(area.x, area.y + top, area.width, area.height.saturating_sub(top));
    frame.render_widget(Paragraph::new(lines), r);
}

// ---------------------------------------------------------------- rail

fn ctx_bar(used: u32, max: u32, cells: usize) -> (String, String, String) {
    let filled = if max == 0 { 0 } else { ((used as usize * cells) / max as usize).min(cells) };
    ("█".repeat(filled), "░".repeat(cells - filled), String::new())
}

fn fmt_k(n: u32) -> String {
    if n >= 1000 {
        format!("{:.1}k", n as f32 / 1000.0)
    } else {
        n.to_string()
    }
}

fn draw_rail(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let head = |t: &str| Line::from(sp(t.to_string(), dim()));
    let mut l: Vec<Line<'static>> = Vec::new();
    l.push(head("SESSION"));
    l.push(Line::from(vec![sp("provider ", dim()), sp(s.provider.clone(), text())]));
    l.push(Line::from(vec![sp("model    ", dim()), sp(s.model.clone(), text())]));
    let seg = |m: Mode, label: &str| {
        if s.mode == m {
            sp(format!(" {label} "), Style::default().bg(RED).fg(BG).add_modifier(Modifier::BOLD))
        } else {
            sp(format!(" {label} "), dim())
        }
    };
    l.push(Line::from(vec![seg(Mode::Plan, "PLAN"), seg(Mode::Act, "ACT"), seg(Mode::Audit, "AUDIT")]));
    let short_id: String = s.session_id.chars().take(RAIL_WIDTH as usize - 12).collect();
    l.push(Line::from(vec![sp("id       ", dim()), sp(short_id, text())]));
    l.push(Line::from(""));
    l.push(head("CONTEXT"));
    if s.ctx_max == 0 {
        l.push(Line::from(sp("unknown", dim())));
    } else {
        let (a, b, _) = ctx_bar(s.ctx_used, s.ctx_max, 12);
        l.push(Line::from(vec![
            sp("▕", dim()),
            sp(a, red()),
            sp(b, Style::default().fg(LINE)),
            sp("▏ ", dim()),
            sp(format!("{} of {}", fmt_k(s.ctx_used), fmt_k(s.ctx_max)), text()),
        ]));
    }
    l.push(Line::from(""));
    l.push(head("KEYS"));
    for (k, d) in [("F2", "providers"), ("F3", "models"), ("F4", "settings"), ("F5", "capabilities"), ("F6", "report")] {
        l.push(Line::from(vec![sp(k.to_string(), Style::default().fg(AMBER)), sp(format!(" {d}"), text())]));
    }
    l.push(Line::from(""));
    l.push(head("RECEIPTS"));
    if s.receipts.is_empty() {
        l.push(Line::from(sp("none yet", dim())));
    }
    for (tag, name) in s.receipts.iter().rev().take(4) {
        let (mark, c) = match tag {
            Evidence::Proven | Evidence::Supported => ("✓", GREEN),
            Evidence::Blocked => ("✗", RED),
            _ => ("~", AMBER),
        };
        l.push(Line::from(vec![sp(format!("{mark} "), Style::default().fg(c)), sp(name.clone(), text())]));
    }
    let block = Block::default().borders(Borders::LEFT).border_style(Style::default().fg(LINE));
    frame.render_widget(Paragraph::new(l).block(block).style(Style::default().bg(RAIL_BG)), area);
}

// ---------------------------------------------------------------- tabs / screens

fn draw_tab_body(frame: &mut Frame, area: Rect, s: &SessionSnapshot) {
    let head = |t: &str| Line::from(sp(t.to_string(), dim()));
    let mut l: Vec<Line<'static>> = vec![Line::from("")];
    match s.tab {
        Tab::Capabilities => return draw_screen(frame, area, s, Screen::Capabilities),
        Tab::Evidence => {
            l.push(head("EVIDENCE"));
            l.push(Line::from(vec![sp("scope   ", dim()), sp(if s.pending.is_some() { "contained" } else { "none pending" }, text())]));
            l.push(Line::from(vec![sp("auth    ", dim()), sp(if s.pending.is_some() { "pending" } else { "n/a" }, text())]));
            l.push(Line::from(vec![sp("receipt ", dim()), sp(if s.receipts.is_empty() { "not issued" } else { "issued" }, text())]));
            l.push(Line::from(""));
            l.push(head("TAGS"));
            for e in [Evidence::Proven, Evidence::Supported, Evidence::Hypothesis, Evidence::Unknown, Evidence::Blocked] {
                l.push(Line::from(sp(e.label().to_string(), Style::default().fg(e.color()))));
            }
        }
        Tab::Gate => {
            let step = |done: bool, cur: bool, t: &str| {
                let (m, c) = if done { ("✓", GREEN) } else if cur { ("◐", AMBER) } else { ("○", DIM) };
                Line::from(vec![sp(format!("{m} "), Style::default().fg(c)), sp(t.to_string(), if done || cur { text() } else { dim() })])
            };
            let blocked = s.pending.is_some();
            l.push(Line::from(vec![
                sp("GATE ", dim()),
                sp(if blocked { "BLOCKED" } else { "clear" }, Style::default().fg(if blocked { AMBER } else { GREEN })),
            ]));
            l.push(step(true, false, "Intent understood"));
            l.push(step(true, false, "Policy resolved"));
            l.push(step(false, blocked, "Governed execution"));
            l.push(step(false, false, "Validation evidence"));
            l.push(step(false, false, "Promote to main"));
            l.push(Line::from(""));
            l.push(Line::from(sp(
                "LBE owns consequence. Provider reasoning proposes; every mutation crosses the permission boundary and returns a receipt.",
                dim(),
            )));
        }
        Tab::Conversation => {}
    }
    let inner = Rect::new(area.x + 1, area.y, area.width.saturating_sub(2), area.height);
    frame.render_widget(Paragraph::new(l).style(Style::default().bg(BG)), inner);
}

fn draw_screen(frame: &mut Frame, area: Rect, s: &SessionSnapshot, screen: Screen) {
    frame.render_widget(Clear, area);
    let head = |t: &str| Line::from(sp(t.to_string(), dim()));
    let mut l: Vec<Line<'static>> = Vec::new();
    l.push(Line::from(vec![
        sp("[", text()),
        sp("┃", red().add_modifier(Modifier::BOLD)),
        sp("] ", text()),
        sp("LBE", text().add_modifier(Modifier::BOLD)),
        sp(format!(" · {}", screen.title()), dim()),
        sp("    esc back", dim()),
    ]));
    l.push(Line::from(""));
    match screen {
        Screen::Providers => {
            l.push(head("PROVIDERS THE RUNTIME KNOWS"));
            for p in &s.providers {
                let active = *p == s.provider;
                l.push(Line::from(vec![
                    sp(if active { "▸ " } else { "  " }, red()),
                    sp(p.clone(), if active { text() } else { dim() }),
                ]));
            }
            l.push(Line::from(""));
            l.push(Line::from(sp("Secrets never appear on this screen.", dim())));
        }
        Screen::Models => {
            l.push(head("MODELS"));
            l.push(Line::from(vec![sp("selected  ", dim()), sp(s.model.clone(), text())]));
            l.push(Line::from(sp("Discovery needs a runtime session. Use /model <id> to select.", dim())));
        }
        Screen::Settings => {
            l.push(head("SETTINGS"));
            l.push(Line::from(vec![sp("workspace ", dim()), sp(s.workspace.clone(), text())]));
            l.push(Line::from(vec![sp("session   ", dim()), sp(s.session_id.clone(), text())]));
            l.push(Line::from(vec![sp("mode      ", dim()), sp(s.mode.label().to_string(), text())]));
            l.push(Line::from(vec![sp("color     ", dim()), sp(if s.no_color { "off (NO_COLOR)" } else { "on" }, text())]));
        }
        Screen::Capabilities => {
            l.push(head("CONNECTED"));
            let (c, t) = if s.runtime_attached { (GREEN, "runtime session attached") } else { (AMBER, "no runtime session attached") };
            l.push(Line::from(vec![sp("● ", Style::default().fg(c)), sp(t, text())]));
            l.push(Line::from(""));
            l.push(head("NOT PROBED FROM THIS CLIENT"));
            for n in ["BirdEye (workspace evidence, receipts)", "Skills catalog", "Memory recall"] {
                l.push(Line::from(vec![sp("○ ", dim()), sp(n, dim())]));
            }
        }
        Screen::Report => {
            l.push(head("REPORT"));
            l.push(Line::from(vec![sp("receipts ", dim()), sp(s.receipts.len().to_string(), text())]));
            l.push(Line::from(vec![sp("entries  ", dim()), sp(s.entries.len().to_string(), text())]));
            l.push(Line::from(vec![sp("gate     ", dim()), sp(if s.pending.is_some() { "BLOCKED" } else { "clear" }, text())]));
            l.push(Line::from(sp("/audit then scope → investigate → clarify → report", dim())));
        }
        Screen::Keys => {
            l.push(head("KEYS"));
            for (k, d) in KEYS {
                l.push(Line::from(vec![sp(format!("{k:<10}"), Style::default().fg(AMBER)), sp(d.to_string(), text())]));
            }
        }
        Screen::Commands => {
            l.push(head("COMMANDS"));
            for (c, d) in COMMANDS {
                l.push(Line::from(vec![sp(format!("{c:<22}"), Style::default().fg(AMBER)), sp(d.to_string(), text())]));
            }
        }
    }
    let inner = Rect::new(area.x + 1, area.y, area.width.saturating_sub(2), area.height);
    frame.render_widget(Paragraph::new(l).style(Style::default().bg(BG)), inner);
}

// ---------------------------------------------------------------- composer / status

fn draw_composer(frame: &mut Frame, area: Rect, s: &SessionSnapshot) -> (u16, u16) {
    let rule = Block::default().borders(Borders::TOP).border_style(Style::default().fg(LINE));
    let inner = rule.inner(area);
    frame.render_widget(rule, area);

    let lines: Vec<&str> = s.input_buffer.split('\n').collect();
    let mut out: Vec<Line<'static>> = Vec::new();
    let take = lines.len().min(inner.height as usize).max(1);
    let first = lines.len() - take;
    for (i, l) in lines[first..].iter().enumerate() {
        let prompt = if i == 0 && first == 0 { sp("❯ ", red()) } else { sp("  ", dim()) };
        if s.input_buffer.is_empty() {
            out.push(Line::from(vec![prompt, sp("Message LBE", dim())]));
        } else {
            out.push(Line::from(vec![prompt, sp(l.to_string(), text())]));
        }
    }
    frame.render_widget(Paragraph::new(out), inner);

    let last = lines.last().map(|l| l.chars().count()).unwrap_or(0) as u16;
    let x = (inner.x + 2 + last).min(inner.x + inner.width.saturating_sub(1));
    let y = inner.y + (take as u16).saturating_sub(1);
    (x, y)
}

fn draw_status(frame: &mut Frame, area: Rect, s: &SessionSnapshot, wide: bool) {
    let (dot, dot_c) = if s.pending.is_some() {
        ("●", AMBER)
    } else if s.busy {
        ("●", RED)
    } else if s.runtime_attached {
        ("●", GREEN)
    } else {
        ("○", DIM)
    };
    let left_txt = if s.pending.is_some() {
        format!("waiting for decision · {}", s.session_id)
    } else if s.busy {
        format!("working · esc stops · {}", s.session_id)
    } else if wide {
        format!("{} · {}", s.mode.label(), s.session_id)
    } else if s.ctx_max > 0 {
        format!("{} · {} · {}/{} · F1 keys", s.mode.label(), s.session_id, fmt_k(s.ctx_used), fmt_k(s.ctx_max))
    } else {
        format!("{} · {} · F1 keys", s.mode.label(), s.session_id)
    };
    let right = "? help";
    let used = 2 + left_txt.chars().count();
    let gap = (area.width as usize).saturating_sub(used + right.len() + 1);
    let spans = vec![
        sp(" ", Style::default()),
        sp(dot, Style::default().fg(dot_c)),
        sp(format!(" {left_txt}"), dim()),
        sp(" ".repeat(gap), Style::default()),
        sp(right, dim()),
    ];
    frame.render_widget(Paragraph::new(Line::from(spans)).style(Style::default().bg(BG)), area);
}

// ---------------------------------------------------------------- tests

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{backend::TestBackend, Terminal};

    fn render(w: u16, h: u16, f: impl FnOnce(&mut SessionSnapshot)) -> String {
        let mut s = SessionSnapshot::new("brew".into(), "28457f04".into(), vec!["lmstudio".into(), "openai".into()]);
        f(&mut s);
        let app = App { snapshot: s };
        let mut t = Terminal::new(TestBackend::new(w, h)).unwrap();
        t.draw(|fr| draw(fr, &app)).unwrap();
        let buf = t.backend().buffer().clone();
        let mut out = String::new();
        for y in 0..h {
            for x in 0..w {
                out.push_str(buf.get(x, y).symbol());
            }
            out.push('\n');
        }
        out
    }

    #[test]
    fn too_small_says_so() {
        let o = render(50, 12, |_| {});
        assert!(o.contains("LBE needs at least 60x18"));
    }

    #[test]
    fn wide_has_header_rail_and_composer() {
        let o = render(120, 30, |s| {
            s.entries.push(Entry::You("scan brew".into()));
            s.entries.push(Entry::Lbe("Checking.".into()));
        });
        assert!(o.contains("LBE brew"), "{o}");
        assert!(o.contains("SESSION"));
        assert!(o.contains("KEYS"));
        assert!(o.contains("❯ Message LBE"));
        assert!(o.contains("? help"));
        assert!(o.contains("PLAN") && o.contains("ACT") && o.contains("AUDIT"));
    }

    #[test]
    fn compact_folds_rail_to_status_line() {
        let o = render(80, 24, |s| {
            s.entries.push(Entry::You("hi".into()));
        });
        assert!(!o.contains("SESSION"));
        assert!(o.contains("F1 keys"));
        assert!(o.contains("act · 28457f04"));
    }

    #[test]
    fn very_short_has_no_header() {
        let o = render(100, 19, |s| s.entries.push(Entry::You("hi".into())));
        assert!(!o.contains("[┃] LBE"));
        assert!(o.contains("❯ Message LBE"));
    }

    #[test]
    fn empty_session_shows_splash_and_blocked_runtime() {
        let o = render(100, 30, |_| {});
        assert!(o.contains("What can I do for you?"));
        assert!(o.contains("no runtime session attached"));
        assert!(o.contains("█▀▀▀"));
    }

    #[test]
    fn permission_card_is_visible_and_status_waits() {
        let o = render(120, 30, |s| {
            s.entries.push(Entry::You("write it".into()));
            s.pending = Some(Permission {
                id: "lbe-call-014-01".into(),
                action: "workspace.write → tests/test_turn_path.py".into(),
                scope: "Scope: current workspace.".into(),
            });
        });
        assert!(o.contains("PERMISSION REQUIRED"));
        assert!(o.contains("a Allow once"));
        assert!(o.contains("d Deny"));
        assert!(o.contains("waiting for decision"));
    }

    #[test]
    fn typed_text_appears_once() {
        let o = render(100, 24, |s| s.input_buffer = "abc".into());
        assert!(o.contains("❯ abc"));
        assert!(!o.contains("aabbcc"));
    }

    #[test]
    fn audit_centers_transcript() {
        let plain = render(100, 24, |s| s.entries.push(Entry::Lbe("hello".into())));
        let audit = render(100, 24, |s| {
            s.mode = Mode::Audit;
            s.entries.push(Entry::Lbe("hello".into()));
        });
        let col = |o: &str| o.lines().find(|l| l.contains("hello")).and_then(|l| l.find("hello")).unwrap();
        assert!(col(&audit) > col(&plain) + 10);
    }

    #[test]
    fn screens_render() {
        for sc in [Screen::Providers, Screen::Models, Screen::Settings, Screen::Capabilities, Screen::Report, Screen::Keys, Screen::Commands] {
            let o = render(100, 24, |s| s.screen = Some(sc));
            assert!(o.contains(sc.title()), "{:?}", sc);
        }
    }
}
