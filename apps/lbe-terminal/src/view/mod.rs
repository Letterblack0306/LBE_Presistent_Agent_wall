//! Drawing. Reads a `Model` snapshot and paints it; never mutates state or does I/O.
//! Layout tiers: wide (>=100 cols) has the rail; compact (60-99) folds it into a
//! status line above the composer; very short (<20 rows) drops header and status.
pub mod chrome;
pub mod cockpit;
pub mod screens;

use crate::model::{Model, Screen};
use crate::text::{clip, width};
use crate::theme::Theme;
use crate::update::{palette_items, COMMANDS};
use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::style::Style;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, Paragraph};
use ratatui::{Frame, Terminal};

pub const WIDE: u16 = 100;
pub const MIN_W: u16 = 60;
pub const MIN_H: u16 = 18;
const RAIL_W: u16 = 30;

/// ASCII mode guarantee: whatever glyph or text reached a widget is folded to ASCII.
fn fold_ascii(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '·' | '•' | '▸' | '▌' | '│' | '┃' => ".".to_string(),
            '—' | '–' | '─' => "-".to_string(),
            '…' => "~".to_string(),
            '→' => "->".to_string(),
            '✓' => "v".to_string(),
            '■' => "x".to_string(),
            '✗' => "X".to_string(),
            '●' => "*".to_string(),
            '○' => "o".to_string(),
            '❯' => ">".to_string(),
            '━' => "=".to_string(),
            c if c.is_ascii() => c.to_string(),
            _ => "?".to_string(),
        })
        .collect()
}

fn fold_if(t: &Theme, s: &str) -> String {
    if t.d.unicode {
        s.to_string()
    } else {
        fold_ascii(s)
    }
}

fn put_t(f: &mut Frame, t: &Theme, area: Rect, lines: Vec<Line<'static>>) {
    if area.width == 0 || area.height == 0 {
        return;
    }
    let lines = if t.d.unicode {
        lines
    } else {
        lines
            .into_iter()
            .map(|l| {
                let st = l.style;
                let al = l.alignment;
                let mut out = Line::from(
                    l.spans
                        .into_iter()
                        .map(|s| Span::styled(fold_ascii(&s.content), s.style))
                        .collect::<Vec<_>>(),
                )
                .style(st);
                out.alignment = al;
                out
            })
            .collect()
    };
    f.render_widget(Paragraph::new(lines), area);
}

/// Show the newest lines that fit, `scroll` lines up from the bottom.
fn window(lines: Vec<Line<'static>>, h: usize, scroll: usize) -> Vec<Line<'static>> {
    if lines.len() <= h {
        return lines;
    }
    let max_up = lines.len() - h;
    let up = scroll.min(max_up);
    let end = lines.len() - up;
    lines[end - h..end].to_vec()
}

pub fn draw(f: &mut Frame, m: &Model) {
    let t = Theme::new(m.display);
    let area = f.size();
    if area.width < MIN_W || area.height < MIN_H {
        let a = format!("LBE needs at least {MIN_W}x{MIN_H}");
        let b = format!(
            "now {}x{}  {} Ctrl+C quits",
            area.width,
            area.height,
            t.g().dot
        );
        let aw = area.width as usize;
        put_t(
            f,
            &t,
            area,
            vec![
                Line::from(Span::styled(clip(&a, aw, !t.d.unicode), t.warn())),
                Line::from(Span::styled(clip(&b, aw, !t.d.unicode), t.muted())),
            ],
        );
        return;
    }
    let w = area.width as usize;
    let wide = area.width >= WIDE;
    let short = area.height < 20;
    let (clines, cursor) = chrome::composer(m, &t, w, short);
    let crow = clines.len() as u16;

    // Vertical plan, top to bottom.
    let mut y = area.y;
    let mut take = |rows: u16| {
        let r = Rect {
            x: area.x,
            y,
            width: area.width,
            height: rows,
        };
        y += rows;
        r
    };
    let chrome_rows: u16 = if short {
        2 + crow
    } else if wide {
        4 + crow + 1
    } else {
        3 + crow + 1
    };
    let body_h = area.height.saturating_sub(chrome_rows);
    let top = if short { None } else { Some(take(1)) };
    let top_rule = if short { None } else { Some(take(1)) };
    let body = take(body_h);
    let rule1 = take(1);
    let (status_a, comp, rule2, status_b);
    if short {
        comp = take(crow);
        status_a = None;
        rule2 = None;
        status_b = None;
    } else if wide {
        comp = take(crow);
        rule2 = Some(take(1));
        status_b = Some(take(1));
        status_a = None;
    } else {
        status_a = Some(take(1));
        comp = take(crow);
        rule2 = None;
        status_b = None;
    }

    if let Some(r) = top {
        put_t(f, &t, r, vec![chrome::top_bar(m, &t, w)]);
    }
    if let Some(r) = top_rule {
        put_t(f, &t, r, vec![chrome::rule(&t, w)]);
    }
    put_t(f, &t, rule1, vec![chrome::rule(&t, w)]);

    // Body: main column plus (wide only) the rail.
    let (main, rail_area) = if wide {
        let mw = body.width - RAIL_W - 1;
        (
            Rect { width: mw, ..body },
            Some(Rect {
                x: body.x + mw + 1,
                width: RAIL_W,
                ..body
            }),
        )
    } else {
        (body, None)
    };
    draw_main(f, m, &t, main);
    if let Some(r) = rail_area {
        let mut lines = chrome::rail(m, &t, (RAIL_W as usize).saturating_sub(2));
        lines.truncate(r.height as usize);
        let sep: Vec<Line<'static>> = (0..r.height)
            .map(|_| Line::from(Span::styled(if t.d.unicode { "│" } else { "|" }, t.rule())))
            .collect();
        put_t(
            f,
            &t,
            Rect {
                x: r.x - 1,
                width: 1,
                ..r
            },
            sep,
        );
        let padded: Vec<Line<'static>> = lines
            .into_iter()
            .map(|l| {
                let mut v = vec![Span::raw(" ")];
                v.extend(l.spans);
                Line::from(v)
            })
            .collect();
        put_t(f, &t, r, padded);
    }

    put_t(f, &t, comp, clines);
    if let Some(r) = rule2 {
        put_t(f, &t, r, vec![chrome::rule(&t, w)]);
    }
    if let Some(r) = status_b {
        put_t(f, &t, r, vec![chrome::status_line(m, &t, w)]);
    }
    if let Some(r) = status_a {
        put_t(f, &t, r, vec![compact_status(m, &t)]);
    }

    if m.help {
        draw_help(f, &t, area);
    } else if m.detail && matches!(m.screen, Screen::Cockpit | Screen::Receipts) {
        draw_details(f, m, &t, area);
    } else if m.palette.is_some() {
        draw_palette(f, m, &t, area);
    } else if m.screen == Screen::Cockpit {
        let cx = comp.x + cursor.1 as u16;
        let cy = comp.y + cursor.0 as u16;
        if cx < comp.x + comp.width && cy < comp.y + comp.height {
            f.set_cursor(cx, cy);
        }
    }
}

/// Compact tier: `● act · fix --version · 4.1k/8k · F1 keys` above the composer.
fn compact_status(m: &Model, t: &Theme) -> Line<'static> {
    let sep = format!(" {} ", t.g().dot);
    let mut parts: Vec<String> = Vec::new();
    if !m.task.is_empty() {
        parts.push(clip(&m.task, 24, !t.d.unicode));
    }
    if let Some((u, tot)) = m.ctx {
        parts.push(if tot > 0 {
            format!("{}/{}", chrome::fmt_k(u), chrome::fmt_k(tot))
        } else {
            chrome::fmt_k(u)
        });
    }
    parts.push("F1 keys".to_string());
    let (word, st) = chrome::state_word(m, t);
    let word = if t.d.unicode { word.to_string() } else { word.replace('…', "...") };
    let mut left = vec![
        chrome::sp(format!(" {} ", t.g().busy), st),
        chrome::sp(format!("{}{sep}", m.mode.name()), t.text()),
        chrome::sp(word, t.text()),
    ];
    left.push(chrome::sp(format!("{sep}{}", parts.join(&sep)), t.muted()));
    Line::from(left)
}

fn draw_main(f: &mut Frame, m: &Model, t: &Theme, area: Rect) {
    let w = area.width as usize;
    let h = area.height as usize;
    let lines = match m.screen {
        Screen::Cockpit => {
            let gate = cockpit::gate(m, t, w);
            let gate_h = gate.len().min(h.saturating_sub(3));
            let mut body = if m.entries.is_empty() && !m.busy && m.pending.is_none() {
                cockpit::splash(m, t, w)
            } else {
                let mut v = cockpit::transcript(m, t, w);
                v.extend(cockpit::plan_footer(m, t));
                v
            };
            let body_h = h - gate_h;
            body = window(body, body_h, m.scroll);
            while body.len() < body_h {
                body.push(Line::default());
            }
            let skip = gate.len().saturating_sub(gate_h);
            body.extend(gate.into_iter().skip(skip).take(gate_h));
            body
        }
        Screen::Providers => screens::providers(m, t, w),
        Screen::Models => screens::models(m, t, w),
        Screen::Settings => screens::settings(m, t, w),
        Screen::Capabilities => screens::capabilities(m, t, w),
        Screen::Report => screens::report(m, t, w),
        Screen::Sessions => screens::sessions(m, t, w),
        Screen::Receipts => screens::receipts(m, t, w),
    };
    let mut lines = lines;
    lines.truncate(h);
    put_t(f, t, area, lines);
}

fn centered(area: Rect, w: u16, h: u16) -> Rect {
    let w = w.min(area.width);
    let h = h.min(area.height);
    Rect {
        x: area.x + (area.width - w) / 2,
        y: area.y + (area.height - h) / 2,
        width: w,
        height: h,
    }
}

fn draw_help(f: &mut Frame, t: &Theme, area: Rect) {
    let mut lines: Vec<Line<'static>> = Vec::new();
    let kv = |k: &str, v: &str| {
        Line::from(vec![
            Span::styled(format!(" {k:<14}"), t.strong()),
            Span::styled(v.to_string(), t.muted()),
        ])
    };
    lines.push(Line::from(Span::styled(
        " Lockstep Boundary Engine (LBE)",
        t.strong(),
    )));
    lines.push(Line::default());
    lines.push(kv("Enter", "send"));
    lines.push(kv("Ctrl+J / Alt+Enter", "newline"));
    lines.push(kv("Tab", "complete /cmd, or cycle mode when empty"));
    lines.push(kv("Shift+Tab", "cycle mode back"));
    lines.push(kv("F2-F8", "providers models settings capabilities report sessions log"));
    lines.push(kv("Ctrl+K", "command palette"));
    lines.push(kv("a / d / v", "allow once / deny / view change (composer empty)"));
    lines.push(kv("d", "details for the last action (nothing pending)"));
    lines.push(kv("Ctrl+X", "stop the current task (asks once)"));
    lines.push(kv("Ctrl+P", "pause (only if the runtime supports it)"));
    lines.push(kv("Esc", "close details · back · stop · clear"));
    lines.push(kv("PgUp / PgDn", "scroll transcript"));
    lines.push(kv("Ctrl+C", "stop the task, then quit"));
    lines.push(Line::default());
    let cmds: Vec<String> = COMMANDS.iter().map(|(c, _)| (*c).to_string()).collect();
    for row in crate::text::wrap(&cmds.join("  "), 60) {
        lines.push(Line::from(Span::styled(format!(" {row}"), t.muted())));
    }
    overlay(f, t, area, " Keys ", lines, 68);
}

fn draw_details(f: &mut Frame, m: &Model, t: &Theme, area: Rect) {
    let rule = if m.screen == Screen::Receipts {
        m.log.iter().rev().nth(m.sel_log)
    } else {
        m.entries.iter().rev().find_map(|e| match e {
            crate::model::Entry::Rule(r) => Some(r),
            _ => None,
        })
    };
    let lines = cockpit::details(m, rule, t);
    overlay(f, t, area, " Details · Esc closes ", lines, 64);
}

fn draw_palette(f: &mut Frame, m: &Model, t: &Theme, area: Rect) {
    let Some(p) = &m.palette else { return };
    let mut lines: Vec<Line<'static>> = vec![Line::from(vec![
        Span::styled(" > ", t.accent()),
        Span::styled(p.query.clone(), t.text()),
    ])];
    lines.push(Line::default());
    for (i, (c, d)) in palette_items(p).into_iter().enumerate() {
        let st: Style = if i == p.sel {
            t.selected()
        } else {
            Style::default()
        };
        let cur = if i == p.sel { t.g().cursor } else { " " };
        lines.push(
            Line::from(vec![
                Span::styled(format!(" {cur} {c:<14}"), t.strong()),
                Span::styled(d.to_string(), t.muted()),
            ])
            .style(st),
        );
    }
    overlay(f, t, area, " Commands ", lines, 60);
}

fn overlay(f: &mut Frame, t: &Theme, area: Rect, title: &str, lines: Vec<Line<'static>>, w: u16) {
    let h = (lines.len() as u16 + 2).min(area.height);
    let r = centered(area, w, h);
    f.render_widget(Clear, r);
    let mut block = Block::default()
        .borders(Borders::ALL)
        .border_style(t.rule())
        .title(Span::styled(fold_if(t, title), t.label()));
    if !t.d.unicode {
        block = block.border_set(ratatui::symbols::border::Set {
            top_left: "+",
            top_right: "+",
            bottom_left: "+",
            bottom_right: "+",
            vertical_left: "|",
            vertical_right: "|",
            horizontal_top: "-",
            horizontal_bottom: "-",
        });
    }
    let inner = block.inner(r);
    f.render_widget(block, r);
    put_t(f, t, inner, lines);
}

/// Render one frame into plain text rows (used by tests and the preview example).
pub fn render_text(m: &Model, w: u16, h: u16) -> String {
    let backend = TestBackend::new(w, h);
    let mut term = Terminal::new(backend).expect("test terminal");
    term.draw(|f| draw(f, m)).expect("draw");
    let buf = term.backend().buffer().clone();
    let mut out = String::new();
    for y in 0..buf.area.height {
        let mut line = String::new();
        let mut skip = 0usize;
        for x in 0..buf.area.width {
            if skip > 0 {
                skip -= 1;
                continue;
            }
            let sym = buf.get(x, y).symbol();
            skip = width(sym).saturating_sub(1);
            line.push_str(sym);
        }
        out.push_str(line.trim_end());
        out.push('\n');
    }
    out
}

/// The frame as a coloured HTML snippet, for visual preview in a browser.
pub fn render_html(m: &Model, w: u16, h: u16) -> String {
    use ratatui::style::{Color, Modifier};
    let backend = TestBackend::new(w, h);
    let mut term = Terminal::new(backend).expect("test terminal");
    term.draw(|f| draw(f, m)).expect("draw");
    let buf = term.backend().buffer().clone();
    let mut out = String::from("<pre class=\"term\">");
    for y in 0..buf.area.height {
        let mut skip = 0usize;
        for x in 0..buf.area.width {
            if skip > 0 {
                skip -= 1;
                continue;
            }
            let c = buf.get(x, y);
            skip = width(c.symbol()).saturating_sub(1);
            let mut css = String::new();
            if let Color::Rgb(r, g, b) = c.fg {
                css.push_str(&format!("color:#{r:02x}{g:02x}{b:02x};"));
            }
            if let Color::Rgb(r, g, b) = c.bg {
                css.push_str(&format!("background:#{r:02x}{g:02x}{b:02x};"));
            }
            if c.modifier.contains(Modifier::BOLD) {
                css.push_str("font-weight:bold;");
            }
            if c.modifier.contains(Modifier::REVERSED) {
                css.push_str("filter:invert(1);");
            }
            let s = c.symbol().replace('&', "&amp;").replace('<', "&lt;");
            if css.is_empty() {
                out.push_str(&s);
            } else {
                out.push_str(&format!("<span style=\"{css}\">{s}</span>"));
            }
        }
        out.push('\n');
    }
    out.push_str("</pre>");
    out
}
