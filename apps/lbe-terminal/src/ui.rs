//! LBE terminal UI — Main cockpit implementation (Rust / Ratatui).
//! Design source: 5-board proposal (Cockpit wide, Logo in the terminal,
//! Layout tiers, Screens and integrations, Sessions and approval gate).
//! Rule applied by the user: no separate landing screen — the first screen
//! IS the Main cockpit plus the logo mark. Layout tiers draw the working
//! screen as header / body / composer / footer. No permanent sidebar.
//! Intent registered 2026-10-16: Rust implementation per the approved design.
//! NOTE: no Cargo.toml or `apps/` crate exists yet, so this cannot compile
//! until a Rust project is added.

use ratatui::{
    layout::{Alignment, Constraint, Layout, Margin, Rect},
    style::{Color, Modifier, Style},
    widgets::{Block, Borders, Paragraph},
    Frame,
};
use std::time::Duration;

const PALETTE_BG: Color = Color::Rgb(24, 24, 24);
const PALETTE_AMBER: Color = Color::Rgb(255, 179, 0);
const PALETTE_LINE: Color = Color::Rgb(96, 96, 96);
const PALETTE_RED: Color = Color::Rgb(180, 30, 30);
const PALETTE_TEXT: Color = Color::Rgb(229, 229, 229);
const HEADER_MARK: &str = "┃ LBE";
const MIN_WIDTH: u16 = 60;
const MIN_HEIGHT: u16 = 20;

#[derive(PartialEq, Eq, Clone, Copy, Debug)]
pub enum RuntimeConnection {
    Connected,
    Disconnected,
}

impl RuntimeConnection {
    pub fn color(self) -> Color {
        match self {
            RuntimeConnection::Connected => Color::Green,
            RuntimeConnection::Disconnected => Color::Red,
        }
    }
}

pub struct SessionSnapshot {
    pub connection: RuntimeConnection,
    pub providers: Vec<String>,
    pub keys: Vec<String>,
    pub receipts: Vec<String>,
}

pub struct App {
    pub snapshot: SessionSnapshot,
}

pub(crate) fn draw_at(frame: &mut Frame, app: &App, elapsed: Duration) {
    let area = frame.size();
    frame.render_widget(
        Block::default().style(Style::default().bg(PALETTE_BG)),
        area,
    );
    if area.width < MIN_WIDTH || area.height < MIN_HEIGHT {
        let message = format!(
            "LBE terminal needs at least {MIN_WIDTH}×{MIN_HEIGHT}.\nCurrent terminal: {}×{}.",
            area.width, area.height
        );
        frame.render_widget(
            Paragraph::new(message)
                .style(Style::default().fg(PALETTE_AMBER).bg(PALETTE_BG))
                .alignment(Alignment::Center)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(PALETTE_LINE)),
                ),
            centered(area, 46, 5),
        );
        return;
    }
    let safe_area = area.inner(&Margin::new(if area.width < 72 { 1 } else { 2 }, 1));
    let compact = safe_area.width < 72 || safe_area.height < 20;
    if compact {
        let sections = Layout::vertical([
            Constraint::Length(1),
            Constraint::Min(2),
            Constraint::Length(2),
            Constraint::Length(2),
        ])
        .split(safe_area);
        draw_header(frame, sections[0], app);
        draw_body(frame, sections[1], app);
        draw_composer(frame, sections[2], app, elapsed);
        draw_footer(frame, sections[3], app);
    } else {
        let sections = Layout::vertical([
            Constraint::Length(1),
            Constraint::Min(10),
            Constraint::Length(3),
            Constraint::Length(2),
        ])
        .split(safe_area);
        draw_header(frame, sections[0], app);
        draw_body(frame, sections[1], app);
        draw_composer(frame, sections[2], app, elapsed);
        draw_footer(frame, sections[3], app);
    }
}

pub(crate) fn draw_header(frame: &mut Frame, area: Rect, app: &App) {
    let connection = app.snapshot.connection;
    let connection_label = if connection == RuntimeConnection::Connected {
        " LIVE "
    } else {
        " OFFLINE "
    };
    let connection_style = Style::default()
        .fg(PALETTE_BG)
        .bg(connection.color())
        .add_modifier(Modifier::BOLD);
    let header_columns = Layout::horizontal([
        Constraint::Length(if area.width < 72 { 5 } else { 18 }),
        Constraint::Length(1),
        Constraint::Length(connection_label.len() as u16 + 2),
        Constraint::Min(1),
    ])
    .split(area);
    let mark = Paragraph::new(HEADER_MARK)
        .style(
            Style::default()
                .fg(PALETTE_RED)
                .bg(PALETTE_BG)
                .add_modifier(Modifier::BOLD),
        );
    frame.render_widget(mark, header_columns[0]);
    let divider = Paragraph::new("│")
        .style(Style::default().fg(PALETTE_LINE).bg(PALETTE_BG));
    frame.render_widget(divider, header_columns[1]);
    let badge = Paragraph::new(connection_label)
        .style(connection_style)
        .alignment(Alignment::Center);
    frame.render_widget(badge, header_columns[2]);
    let title = Paragraph::new("LBE Cockpit")
        .style(
            Style::default()
                .fg(PALETTE_BG)
                .bg(PALETTE_RED)
                .add_modifier(Modifier::BOLD),
        )
        .alignment(Alignment::Left);
    frame.render_widget(title, header_columns[3]);
}

pub(crate) fn draw_body(frame: &mut Frame, area: Rect, app: &App) {
    let providers = &app.snapshot.providers;
    let lines: Vec<String> = if providers.is_empty() {
        vec!["Provider catalog — empty. Runtime projected no providers.".to_string()]
    } else {
        let mut rows: Vec<String> = vec!["Provider catalog".to_string(), "".to_string()];
        rows.extend(providers.iter().map(|p| format!("  • {}", p)));
        rows
    };
    let body = Paragraph::new(lines.join("\n"))
        .style(Style::default().fg(PALETTE_TEXT).bg(PALETTE_BG))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(PALETTE_LINE)),
        );
    frame.render_widget(body, area);
}

pub(crate) fn draw_composer(frame: &mut Frame, area: Rect, _app: &App, _elapsed: Duration) {
    let composer = Paragraph::new("> ")
        .style(Style::default().fg(PALETTE_AMBER).bg(PALETTE_BG))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(PALETTE_LINE)),
        );
    frame.render_widget(composer, area);
}

pub(crate) fn draw_footer(frame: &mut Frame, area: Rect, app: &App) {
    let status = format!(
        "SESSION │ KEYS: {} │ RECEIPTS: {} │ quiet",
        app.snapshot.keys.len(),
        app.snapshot.receipts.len()
    );
    let footer = Paragraph::new(status)
        .style(Style::default().fg(PALETTE_LINE).bg(PALETTE_BG))
        .alignment(Alignment::Center);
    frame.render_widget(footer, area);
}

fn centered(area: Rect, width: u16, height: u16) -> Rect {
    let x = area.left() + area.width.saturating_sub(width) / 2;
    let y = area.top() + area.height.saturating_sub(height) / 2;
    Rect::new(
        x,
        y,
        width.min(area.width),
        height.min(area.height),
    )
}
