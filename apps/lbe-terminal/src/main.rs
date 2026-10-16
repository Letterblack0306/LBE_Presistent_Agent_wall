//! LBE terminal binary — the cockpit from the "LBE terminal UI proposal".
//!
//! `ui.rs` draws, `control.rs` handles keys and slash commands, this file owns
//! the terminal lifecycle (raw mode, alternate screen, mouse, restore on panic).

use std::io;
use std::time::Duration;

use crossterm::event::{
    DisableMouseCapture, EnableMouseCapture, Event, KeyEventKind, MouseEventKind,
};
use crossterm::{
    event, execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};

mod control;
mod ui;
use control::Outcome;
use ui::{App, SessionSnapshot};

const VERSION: &str = env!("CARGO_PKG_VERSION");

const HELP: &str = "lbe-terminal - LBE cockpit\n\n\
Usage: lbe-terminal [--version|-V] [--help|-h]\n\n\
Environment:\n  LBE_WORKSPACE   workspace label (default: current folder name)\n  \
LBE_PROVIDER    provider shown in the header\n  LBE_MODEL       model shown in the header\n  \
LBE_SESSION_ID  session id (default: generated)\n  NO_COLOR        monochrome mark and header\n\n\
Inside: /help lists commands, F1 keys, Ctrl+K commands, Ctrl+C quits.";

const PROVIDERS: [&str; 20] = [
    "anthropic", "bedrock", "claude-code", "deepseek", "fireworks", "gemini", "gemini-cli",
    "groq", "lmstudio", "mistral", "ollama", "openai", "openai-codex-cli", "openai-compatible",
    "openai-native", "opencode", "openrouter", "together", "vertex", "xai",
];

fn env_nonempty(k: &str) -> Option<String> {
    std::env::var(k).ok().filter(|v| !v.trim().is_empty())
}

fn session_id() -> String {
    env_nonempty("LBE_SESSION_ID").unwrap_or_else(|| {
        let n = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        format!("{:08x}", (n as u64) & 0xffff_ffff)
    })
}

fn workspace() -> String {
    env_nonempty("LBE_WORKSPACE").unwrap_or_else(|| {
        std::env::current_dir()
            .ok()
            .and_then(|p| p.file_name().map(|n| n.to_string_lossy().into_owned()))
            .unwrap_or_else(|| "workspace".to_string())
    })
}

fn restore() {
    let _ = disable_raw_mode();
    let _ = execute!(io::stdout(), DisableMouseCapture, LeaveAlternateScreen);
}

fn main() -> Result<(), io::Error> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("lbe-terminal {VERSION}");
        return Ok(());
    }
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("{HELP}");
        return Ok(());
    }

    let mut snapshot = SessionSnapshot::new(
        workspace(),
        session_id(),
        PROVIDERS.iter().map(|p| p.to_string()).collect(),
    );
    if let Some(p) = env_nonempty("LBE_PROVIDER") {
        snapshot.provider = p;
    }
    if let Some(m) = env_nonempty("LBE_MODEL") {
        snapshot.model = m;
    }
    snapshot.no_color = std::env::var_os("NO_COLOR").is_some();
    let mut app = App { snapshot };

    // Always leave the user's terminal usable, even on panic.
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        restore();
        default_hook(info);
    }));

    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;

    let tick = Duration::from_millis(250);
    loop {
        terminal.draw(|frame| ui::draw(frame, &app))?;
        if !event::poll(tick)? {
            continue;
        }
        match event::read()? {
            // Windows delivers Press and Release; act on Press only.
            Event::Key(key) if key.kind == KeyEventKind::Press => {
                if control::on_key(&mut app, key) == Outcome::Quit {
                    break;
                }
            }
            Event::Mouse(m) => match m.kind {
                MouseEventKind::ScrollUp => control::on_scroll(&mut app, true),
                MouseEventKind::ScrollDown => control::on_scroll(&mut app, false),
                _ => {}
            },
            _ => {}
        }
    }

    restore();
    terminal.show_cursor()?;
    Ok(())
}
