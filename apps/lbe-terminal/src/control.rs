//! Key handling and slash commands. Pure state transitions on `App`, so every
//! behaviour is unit-testable without a terminal.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::ui::{App, Entry, Evidence, Mode, Screen, Tab, COMMANDS};

#[derive(PartialEq, Eq, Debug)]
pub enum Outcome {
    Continue,
    Quit,
}

const NO_RUNTIME: &str =
    "No runtime session is attached, so this message was not sent to a provider. \
     LBE reasons through the runtime; connect one to get replies.";

pub fn on_key(app: &mut App, key: KeyEvent) -> Outcome {
    let ctrl = key.modifiers.contains(KeyModifiers::CONTROL);
    let s = &mut app.snapshot;

    match key.code {
        KeyCode::Char('c') if ctrl => {
            if s.busy {
                stop(app);
                return Outcome::Continue;
            }
            return Outcome::Quit;
        }
        KeyCode::Char('d') if ctrl && s.input_buffer.is_empty() => return Outcome::Quit,
        KeyCode::Char('k') if ctrl => {
            s.screen = Some(Screen::Commands);
            return Outcome::Continue;
        }
        KeyCode::Char('j') if ctrl => {
            s.input_buffer.push('\n');
            return Outcome::Continue;
        }
        KeyCode::F(1) => s.screen = Some(Screen::Keys),
        KeyCode::F(2) => s.screen = Some(Screen::Providers),
        KeyCode::F(3) => s.screen = Some(Screen::Models),
        KeyCode::F(4) => s.screen = Some(Screen::Settings),
        KeyCode::F(5) => s.screen = Some(Screen::Capabilities),
        KeyCode::F(6) => s.screen = Some(Screen::Report),
        KeyCode::Esc => {
            if s.screen.is_some() {
                s.screen = None;
            } else if s.busy {
                stop(app);
            } else if !s.input_buffer.is_empty() {
                s.input_buffer.clear();
            }
        }
        KeyCode::BackTab => s.mode = s.mode.next(),
        KeyCode::Tab => tab(app),
        KeyCode::PageUp | KeyCode::Up => s.scroll_up = s.scroll_up.saturating_add(if matches!(key.code, KeyCode::Up) { 1 } else { 10 }),
        KeyCode::PageDown | KeyCode::Down => s.scroll_up = s.scroll_up.saturating_sub(if matches!(key.code, KeyCode::Down) { 1 } else { 10 }),
        KeyCode::Backspace => {
            s.input_buffer.pop();
        }
        KeyCode::Enter => return submit(app),
        KeyCode::Char(c) if !ctrl && !key.modifiers.contains(KeyModifiers::ALT) => {
            // permission shortcuts only when the composer is empty
            if s.input_buffer.is_empty() && s.pending.is_some() && (c == 'a' || c == 'd') {
                let p = s.pending.take().expect("checked");
                if c == 'a' {
                    s.entries.push(Entry::Note {
                        tag: Evidence::Supported,
                        text: format!("Allowed once: {} ({}). No runtime attached to execute it, so no receipt was issued.", p.action, p.id),
                    });
                } else {
                    s.entries.push(Entry::Note {
                        tag: Evidence::Blocked,
                        text: format!("Denied: {} ({}).", p.action, p.id),
                    });
                }
            } else if c == '?' && s.input_buffer.is_empty() {
                s.screen = Some(Screen::Keys);
            } else {
                s.input_buffer.push(c);
                s.scroll_up = 0;
            }
        }
        _ => {}
    }
    Outcome::Continue
}

pub fn on_scroll(app: &mut App, up: bool) {
    let s = &mut app.snapshot;
    if up {
        s.scroll_up = s.scroll_up.saturating_add(3);
    } else {
        s.scroll_up = s.scroll_up.saturating_sub(3);
    }
}

fn stop(app: &mut App) {
    let s = &mut app.snapshot;
    if s.busy {
        s.busy = false;
        s.entries.push(Entry::Note { tag: Evidence::Blocked, text: "Turn stopped by user.".into() });
    } else {
        s.entries.push(Entry::Info("Nothing is running.".into()));
    }
}

fn tab(app: &mut App) {
    let s = &mut app.snapshot;
    if s.input_buffer.starts_with('/') && !s.input_buffer.contains(' ') {
        let prefix = s.input_buffer.clone();
        let hits: Vec<&str> = COMMANDS
            .iter()
            .map(|(c, _)| *c)
            .filter(|c| c.starts_with(&prefix))
            .collect();
        match hits.len() {
            0 => s.entries.push(Entry::Info(format!("No command starts with {prefix}."))),
            1 => {
                let cmd = hits[0].split(' ').next().unwrap_or(hits[0]);
                s.input_buffer = cmd.to_string();
            }
            _ => s.entries.push(Entry::Info(format!("Matches: {}", hits.join("  ")))),
        }
    } else {
        s.tab = s.tab.next();
        s.screen = None;
    }
}

fn submit(app: &mut App) -> Outcome {
    let line = app.snapshot.input_buffer.trim().to_string();
    app.snapshot.input_buffer.clear();
    app.snapshot.scroll_up = 0;
    app.snapshot.screen = None;
    app.snapshot.tab = Tab::Conversation;
    if line.is_empty() {
        return Outcome::Continue;
    }
    app.snapshot.entries.push(Entry::You(line.clone()));
    if line.starts_with('/') {
        return command(app, &line);
    }
    // No bridge to a runtime exists in this client yet: say so, never go silent.
    app.snapshot.entries.push(Entry::Note { tag: Evidence::Blocked, text: NO_RUNTIME.into() });
    Outcome::Continue
}

fn command(app: &mut App, line: &str) -> Outcome {
    let mut parts = line.splitn(2, ' ');
    let cmd = parts.next().unwrap_or("");
    let arg = parts.next().unwrap_or("").trim();
    let s = &mut app.snapshot;
    match cmd {
        "/quit" | "/exit" => return Outcome::Quit,
        "/help" => {
            s.entries.push(Entry::Lbe("Commands".into()));
            for (c, d) in COMMANDS {
                s.entries.push(Entry::Info(format!("{c:<22}{d}")));
            }
            s.entries.push(Entry::Info("Tab completes a /command, or cycles the tabs. F1 shows all keys.".into()));
        }
        "/providers" => s.screen = Some(Screen::Providers),
        "/keys" => s.screen = Some(Screen::Keys),
        "/report" => s.screen = Some(Screen::Report),
        "/audit" => {
            s.mode = Mode::Audit;
            s.entries.push(Entry::Info("Mode: AUDIT. Scope, investigate, clarify, report.".into()));
        }
        "/mode" => match Mode::parse(arg) {
            Some(m) => {
                s.mode = m;
                s.entries.push(Entry::Info(format!("Mode: {}.", m.label().to_uppercase())));
            }
            None => s.entries.push(Entry::Note {
                tag: Evidence::Unknown,
                text: "Usage: /mode plan|act|audit".into(),
            }),
        },
        "/model" => {
            if arg.is_empty() {
                s.screen = Some(Screen::Models);
            } else {
                s.model = arg.to_string();
                s.entries.push(Entry::Info(format!("Model set to {arg} for this client. The runtime has not confirmed it.")));
            }
        }
        "/stop" => stop(app),
        "/clear" => {
            s.entries.clear();
        }
        other => s.entries.push(Entry::Note {
            tag: Evidence::Unknown,
            text: format!("Unknown command {other}. /help lists commands."),
        }),
    }
    Outcome::Continue
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ui::{Permission, SessionSnapshot};
    use crossterm::event::{KeyEventKind, KeyEventState};

    fn app() -> App {
        App { snapshot: SessionSnapshot::new("brew".into(), "abcd1234".into(), vec!["lmstudio".into()]) }
    }
    fn key(c: KeyCode) -> KeyEvent {
        KeyEvent { code: c, modifiers: KeyModifiers::NONE, kind: KeyEventKind::Press, state: KeyEventState::NONE }
    }
    fn ctrl(c: char) -> KeyEvent {
        KeyEvent { code: KeyCode::Char(c), modifiers: KeyModifiers::CONTROL, kind: KeyEventKind::Press, state: KeyEventState::NONE }
    }
    fn type_str(a: &mut App, s: &str) {
        for ch in s.chars() {
            on_key(a, key(KeyCode::Char(ch)));
        }
    }

    #[test]
    fn letter_q_is_just_a_letter() {
        let mut a = app();
        assert_eq!(on_key(&mut a, key(KeyCode::Char('q'))), Outcome::Continue);
        assert_eq!(a.snapshot.input_buffer, "q");
    }

    #[test]
    fn repeated_letters_are_not_dropped() {
        let mut a = app();
        type_str(&mut a, "aabbcc");
        assert_eq!(a.snapshot.input_buffer, "aabbcc");
    }

    #[test]
    fn plain_message_is_never_silent() {
        let mut a = app();
        type_str(&mut a, "hello");
        on_key(&mut a, key(KeyCode::Enter));
        assert!(a.snapshot.input_buffer.is_empty());
        assert!(matches!(a.snapshot.entries[0], Entry::You(_)));
        assert!(matches!(a.snapshot.entries[1], Entry::Note { tag: Evidence::Blocked, .. }));
    }

    #[test]
    fn help_lists_every_command() {
        let mut a = app();
        type_str(&mut a, "/help");
        on_key(&mut a, key(KeyCode::Enter));
        let all = format!("{:?}", a.snapshot.entries);
        for (c, _) in COMMANDS {
            assert!(all.contains(c), "missing {c}");
        }
    }

    #[test]
    fn unknown_command_says_so() {
        let mut a = app();
        type_str(&mut a, "/nope");
        on_key(&mut a, key(KeyCode::Enter));
        assert!(format!("{:?}", a.snapshot.entries).contains("Unknown command /nope"));
    }

    #[test]
    fn tab_completes_unique_prefix_and_cycles_tabs_otherwise() {
        let mut a = app();
        type_str(&mut a, "/prov");
        on_key(&mut a, key(KeyCode::Tab));
        assert_eq!(a.snapshot.input_buffer, "/providers");
        let mut b = app();
        on_key(&mut b, key(KeyCode::Tab));
        assert_eq!(b.snapshot.tab, Tab::Capabilities);
    }

    #[test]
    fn shift_tab_cycles_mode_and_audit_command_sets_audit() {
        let mut a = app();
        on_key(&mut a, key(KeyCode::BackTab));
        assert_eq!(a.snapshot.mode, Mode::Audit);
        let mut b = app();
        type_str(&mut b, "/audit");
        on_key(&mut b, key(KeyCode::Enter));
        assert_eq!(b.snapshot.mode, Mode::Audit);
    }

    #[test]
    fn esc_and_ctrl_c_stop_a_busy_turn_before_quitting() {
        let mut a = app();
        a.snapshot.busy = true;
        assert_eq!(on_key(&mut a, ctrl('c')), Outcome::Continue);
        assert!(!a.snapshot.busy);
        assert_eq!(on_key(&mut a, ctrl('c')), Outcome::Quit);
    }

    #[test]
    fn permission_a_and_d_resolve_when_composer_empty() {
        let mut a = app();
        a.snapshot.pending = Some(Permission { id: "x".into(), action: "write".into(), scope: "s".into() });
        on_key(&mut a, key(KeyCode::Char('a')));
        assert!(a.snapshot.pending.is_none());
        assert!(a.snapshot.input_buffer.is_empty());
    }

    #[test]
    fn ctrl_j_newline_and_ctrl_k_commands_and_function_keys() {
        let mut a = app();
        type_str(&mut a, "a");
        on_key(&mut a, ctrl('j'));
        type_str(&mut a, "b");
        assert_eq!(a.snapshot.input_buffer, "a\nb");
        on_key(&mut a, ctrl('k'));
        assert_eq!(a.snapshot.screen, Some(Screen::Commands));
        on_key(&mut a, key(KeyCode::Esc));
        assert_eq!(a.snapshot.screen, None);
        on_key(&mut a, key(KeyCode::F(5)));
        assert_eq!(a.snapshot.screen, Some(Screen::Capabilities));
    }

    #[test]
    fn backspace_removes_last_char() {
        let mut a = app();
        type_str(&mut a, "ab");
        on_key(&mut a, key(KeyCode::Backspace));
        assert_eq!(a.snapshot.input_buffer, "a");
    }
}
