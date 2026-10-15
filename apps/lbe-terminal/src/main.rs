//! LBE terminal binary — runs the Main cockpit UI from `ui.rs`.
//!
//! Entry point for the `lbe-terminal` crate. Sets up a crossterm terminal,
//! renders the cockpit via `ui::draw_at`, and handles resize / quit.

use std::io;
use std::time::{Duration, Instant};
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    Terminal,
};

mod ui;
use ui::{App, RuntimeConnection, SessionSnapshot};

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn print_version() {
    println!("lbe-terminal {}", VERSION);
}

fn main() -> Result<(), io::Error> {
    // Handle --version / -V before touching the terminal
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        print_version();
        return Ok(());
    }

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // App state — provider catalog comes from the runtime (20 providers in
    // default_provider_registry). Keys/receipts come from session state.
    let app = App {
        snapshot: SessionSnapshot {
            connection: RuntimeConnection::Connected,
            providers: vec![
                "anthropic".to_string(),
                "bedrock".to_string(),
                "claude-code".to_string(),
                "deepseek".to_string(),
                "fireworks".to_string(),
                "gemini".to_string(),
                "gemini-cli".to_string(),
                "groq".to_string(),
                "lmstudio".to_string(),
                "mistral".to_string(),
                "ollama".to_string(),
                "openai".to_string(),
                "openai-codex-cli".to_string(),
                "openai-compatible".to_string(),
                "openai-native".to_string(),
                "opencode".to_string(),
                "openrouter".to_string(),
                "together".to_string(),
                "vertex".to_string(),
                "xai".to_string(),
            ],
            keys: Vec::new(),
            receipts: Vec::new(),
        },
    };

    let mut last_tick = Instant::now();
    let tick_rate = Duration::from_millis(250);

    loop {
        terminal.draw(|frame| {
            let elapsed = last_tick.elapsed();
            ui::draw_at(frame, &app, elapsed);
        })?;

        if event::poll(tick_rate)? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Esc => break,
                    KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => break,
                    _ => {}
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            last_tick = Instant::now();
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    Ok(())
}
