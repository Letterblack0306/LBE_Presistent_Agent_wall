//! Process lifecycle: terminal modes, the single input owner, the bridge pump and
//! the draw loop. Terminal state is restored on every exit path we control
//! (normal exit, error return, panic).
use crate::bridge::{Config, Runtime};
use crate::model::{Bridge, Entry, Model};
use crate::theme::Display;
use crate::update::{guard_paste, update, Effect, Input};
use crossterm::event::{
    self, DisableBracketedPaste, DisableMouseCapture, EnableBracketedPaste, EnableMouseCapture,
    Event, MouseEventKind,
};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use std::io::{self, Stdout};
use std::sync::mpsc;
use std::time::Duration;

/// Owns every terminal mode the app enables and undoes them on drop.
struct TerminalGuard;

impl TerminalGuard {
    fn enter() -> io::Result<TerminalGuard> {
        enable_raw_mode()?;
        if let Err(e) = execute!(
            io::stdout(),
            EnterAlternateScreen,
            EnableMouseCapture,
            EnableBracketedPaste
        ) {
            let _ = disable_raw_mode();
            return Err(e);
        }
        Ok(TerminalGuard)
    }
}

fn restore() {
    let _ = execute!(
        io::stdout(),
        DisableBracketedPaste,
        DisableMouseCapture,
        LeaveAlternateScreen
    );
    let _ = disable_raw_mode();
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        restore();
    }
}

pub fn run() -> io::Result<()> {
    let get = |k: &str| std::env::var(k).ok();
    let mut model = Model::new(Display::from_env(get));

    let (tx, rx) = mpsc::channel::<Bridge>();
    let mut runtime = None;
    if get("LBE_BRIDGE").as_deref() == Some("off") {
        model.entries.push(Entry::Info(
            "runtime bridge off (LBE_BRIDGE=off); UI only".into(),
        ));
    } else {
        match Runtime::spawn(&Config::from_env(get), tx) {
            Ok(r) => runtime = Some(r),
            Err(e) => model
                .entries
                .push(Entry::Error(format!("runtime bridge unavailable: {e}"))),
        }
    }

    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        restore();
        default_hook(info);
    }));

    let _guard = TerminalGuard::enter()?;
    let mut terminal: Terminal<CrosstermBackend<Stdout>> =
        Terminal::new(CrosstermBackend::new(io::stdout()))?;
    terminal.clear()?;

    let animate = |m: &Model| m.busy && m.display.motion;
    loop {
        terminal.draw(|f| crate::view::draw(f, &model))?;

        // The main thread is the only reader of terminal input.
        let wait = if animate(&model) {
            Duration::from_millis(90)
        } else {
            Duration::from_millis(250)
        };
        let mut inputs: Vec<Input> = Vec::new();
        if event::poll(wait)? {
            loop {
                match event::read()? {
                    Event::Key(k) => inputs.push(Input::Key(k)),
                    Event::Paste(s) => inputs.push(Input::Paste(s)),
                    Event::Mouse(me) => match me.kind {
                        MouseEventKind::ScrollUp => inputs.push(Input::Wheel(1)),
                        MouseEventKind::ScrollDown => inputs.push(Input::Wheel(-1)),
                        _ => {}
                    },
                    _ => {}
                }
                if !event::poll(Duration::from_millis(0))? {
                    break;
                }
            }
        } else if animate(&model) {
            inputs.push(Input::Tick);
        }
        while let Ok(msg) = rx.try_recv() {
            inputs.push(Input::Bridge(msg));
        }

        for input in guard_paste(inputs) {
            for effect in update(&mut model, input) {
                match effect {
                    Effect::Quit => return Ok(()),
                    Effect::Send(v) => {
                        let delivered = runtime.as_mut().map(|r| r.send(&v)).unwrap_or(false);
                        if !delivered {
                            model.attached = false;
                            model.busy = false;
                            model.entries.push(Entry::Error(
                                "request not delivered: runtime bridge is gone".into(),
                            ));
                        }
                    }
                }
            }
        }
        if model.quit {
            return Ok(());
        }
    }
}
