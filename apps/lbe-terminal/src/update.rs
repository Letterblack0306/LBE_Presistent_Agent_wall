//! State transitions. Input events and bridge messages go in; state changes and
//! effects (requests to the bridge) come out. Nothing here draws or blocks.
use crate::model::{
    Activity, Bridge, Entry, Life, Mode, Model, Palette, Rule, Screen, Verdict,
};
use crate::text;
use crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use serde_json::{json, Value};

#[allow(clippy::large_enum_variant)]
pub enum Input {
    Key(KeyEvent),
    Paste(String),
    Wheel(i8),
    Tick,
    Bridge(Bridge),
}

#[derive(Debug, PartialEq)]
pub enum Effect {
    Send(Value),
    Quit,
}

/// One table feeds `/help`, Tab completion and the Ctrl+K palette.
pub const COMMANDS: &[(&str, &str)] = &[
    ("/help", "keys and commands"),
    ("/home", "back to the cockpit"),
    ("/providers", "provider list (F2)"),
    ("/models", "model catalog (F3)"),
    ("/model", "/model <id>  select a model"),
    ("/intent", "/intent <reason>  answer a stopped change; recorded as proposed, authorizes nothing"),
    ("/settings", "session and display (F4)"),
    ("/capabilities", "registered capabilities (F5)"),
    ("/report", "report (F6)"),
    ("/sessions", "sessions and tasks (F7)"),
    ("/log", "decision log (F8)"),
    ("/plan", "plan mode: nothing executes"),
    ("/act", "act mode: governed execution"),
    ("/audit", "audit mode: read-only"),
    ("/stop", "stop the running turn"),
    ("/clear", "clear the transcript"),
    ("/quit", "leave"),
];

/// Windows consoles have no bracketed paste: pasted text arrives as a burst of key
/// events. A burst (more than 3 keys in one input batch) never submits; its
/// Enters become newlines, and the operator sends with a separate Enter.
pub fn guard_paste(inputs: Vec<Input>) -> Vec<Input> {
    let keys = inputs.iter().filter(|i| matches!(i, Input::Key(_))).count();
    if keys <= 3 {
        return inputs;
    }
    inputs
        .into_iter()
        .map(|i| match i {
            Input::Key(k)
                if k.code == KeyCode::Enter
                    && k.modifiers.is_empty()
                    && k.kind != KeyEventKind::Release =>
            {
                Input::Key(KeyEvent {
                    modifiers: KeyModifiers::ALT,
                    ..k
                })
            }
            other => other,
        })
        .collect()
}

const SCROLL_STEP: usize = 5;
const SCROLL_MAX: usize = 100_000;

pub fn update(m: &mut Model, input: Input) -> Vec<Effect> {
    match input {
        Input::Key(k) if k.kind != KeyEventKind::Release => on_key(m, k),
        Input::Key(_) => vec![],
        Input::Paste(p) => {
            if m.screen == Screen::Cockpit && m.palette.is_none() && !m.help {
                // Pasted newlines stay text; they never submit.
                m.composer.push_str(&text::sanitize(&p));
            }
            vec![]
        }
        Input::Wheel(d) => {
            scroll(m, d as i32 * 3);
            vec![]
        }
        Input::Tick => {
            m.tick = m.tick.wrapping_add(1);
            vec![]
        }
        Input::Bridge(b) => on_bridge(m, b),
    }
}

fn scroll(m: &mut Model, lines: i32) {
    if lines >= 0 {
        m.scroll = (m.scroll + lines as usize).min(SCROLL_MAX);
    } else {
        m.scroll = m.scroll.saturating_sub((-lines) as usize);
    }
}

fn send(m: &Model, v: Value) -> Vec<Effect> {
    if m.attached {
        vec![Effect::Send(v)]
    } else {
        vec![]
    }
}

fn goto(m: &mut Model, screen: Screen) -> Vec<Effect> {
    m.screen = screen;
    m.detail = false;
    match screen {
        Screen::Providers => send(m, json!({"op": "providers"})),
        Screen::Models => send(m, json!({"op": "models"})),
        Screen::Capabilities => send(m, json!({"op": "capabilities"})),
        _ => vec![],
    }
}

fn set_mode(m: &mut Model, mode: Mode) -> Vec<Effect> {
    if mode == m.mode {
        return vec![];
    }
    if m.attached {
        vec![Effect::Send(json!({"op": "mode", "mode": mode.name()}))]
    } else {
        m.mode = mode;
        vec![]
    }
}

fn on_key(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    let ctrl = k.modifiers.contains(KeyModifiers::CONTROL);
    if m.help {
        if matches!(
            k.code,
            KeyCode::Esc | KeyCode::F(1) | KeyCode::Char('?') | KeyCode::Enter
        ) {
            m.help = false;
        }
        return vec![];
    }
    if m.palette.is_some() {
        return on_palette_key(m, k);
    }
    if ctrl && k.code == KeyCode::Char('c') {
        if m.busy {
            return cancel(m);
        }
        m.quit = true;
        return vec![Effect::Quit];
    }
    if m.life == Life::ConfirmStop {
        return on_stop_confirm(m, k);
    }
    if ctrl && k.code == KeyCode::Char('x') {
        if m.busy && m.attached {
            m.life = Life::ConfirmStop;
        }
        return vec![];
    }
    if ctrl && k.code == KeyCode::Char('p') {
        // The runtime has no pause operation; say so instead of faking a state.
        if m.busy {
            m.entries.push(Entry::Lifecycle(
                "pause is not available: the runtime cannot hold a running step".into(),
            ));
        }
        return vec![];
    }
    if ctrl && k.code == KeyCode::Char('k') {
        m.palette = Some(Palette::default());
        return vec![];
    }
    match k.code {
        KeyCode::F(1) => {
            m.help = true;
            return vec![];
        }
        KeyCode::F(n @ 2..=8) => return goto(m, Screen::ALL[(n - 1) as usize]),
        KeyCode::Esc => {
            if m.detail {
                m.detail = false;
                return vec![];
            }
            if m.busy {
                return cancel(m);
            }
            if m.screen != Screen::Cockpit {
                return goto(m, Screen::Cockpit);
            }
            m.composer.clear();
            return vec![];
        }
        KeyCode::BackTab => return set_mode(m, m.mode.next(true)),
        KeyCode::PageUp => {
            scroll(m, SCROLL_STEP as i32);
            return vec![];
        }
        KeyCode::PageDown => {
            scroll(m, -(SCROLL_STEP as i32));
            return vec![];
        }
        _ => {}
    }
    match m.screen {
        Screen::Cockpit => cockpit_key(m, k),
        Screen::Providers | Screen::Models | Screen::Capabilities | Screen::Receipts => {
            list_key(m, k)
        }
        Screen::Sessions => {
            if k.code == KeyCode::Tab {
                return set_mode(m, m.mode.next(false));
            }
            vec![]
        }
        Screen::Settings => settings_key(m, k),
        Screen::Report => {
            if k.code == KeyCode::Tab {
                return set_mode(m, m.mode.next(false));
            }
            vec![]
        }
    }
}

fn cancel(m: &mut Model) -> Vec<Effect> {
    m.life = Life::Stopping;
    send(m, json!({"op": "cancel"}))
}

/// `Ctrl+X` asked once; `y` stops, anything else keeps going.
fn on_stop_confirm(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    match k.code {
        KeyCode::Char('y') | KeyCode::Char('Y') => cancel(m),
        _ => {
            m.life = Life::Running;
            vec![]
        }
    }
}

fn cockpit_key(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    let alt = k.modifiers.contains(KeyModifiers::ALT);
    let ctrl = k.modifiers.contains(KeyModifiers::CONTROL);
    match k.code {
        // Gate and plan shortcuts only fire while the composer is empty, so
        // typing text never triggers a decision.
        KeyCode::Char(c @ ('a' | 'd')) if m.composer.is_empty() && m.pending.is_some() && !ctrl => {
            let decision = if c == 'a' { "approve" } else { "reject" };
            m.detail = false;
            send(m, json!({"op": "decision", "decision": decision}))
        }
        KeyCode::Char('v') if m.composer.is_empty() && m.pending.is_some() && !ctrl => {
            m.detail = !m.detail;
            vec![]
        }
        KeyCode::Char('d' | 'o') if m.composer.is_empty() && m.pending.is_none() && !ctrl => {
            m.detail = !m.detail;
            vec![]
        }
        KeyCode::Char('a')
            if m.composer.is_empty()
                && m.pending.is_none()
                && m.mode == Mode::Plan
                && has_agent_reply(m)
                && !ctrl =>
        {
            set_mode(m, Mode::Act)
        }
        KeyCode::Enter if alt => {
            m.composer.push('\n');
            vec![]
        }
        KeyCode::Char('j') if ctrl => {
            m.composer.push('\n');
            vec![]
        }
        KeyCode::Enter => submit(m),
        KeyCode::Backspace => {
            text::pop_grapheme(&mut m.composer);
            vec![]
        }
        KeyCode::Tab => {
            if m.composer.starts_with('/') && !m.composer.contains(' ') {
                complete(m);
                vec![]
            } else if m.composer.is_empty() {
                set_mode(m, m.mode.next(false))
            } else {
                vec![]
            }
        }
        KeyCode::Up => {
            scroll(m, 1);
            vec![]
        }
        KeyCode::Down => {
            scroll(m, -1);
            vec![]
        }
        KeyCode::Char(c) if !ctrl => {
            m.composer.push(c);
            m.scroll = 0;
            vec![]
        }
        _ => vec![],
    }
}

fn has_agent_reply(m: &Model) -> bool {
    m.entries.iter().any(|e| matches!(e, Entry::Agent(_)))
}

fn complete(m: &mut Model) {
    let hits: Vec<&str> = COMMANDS
        .iter()
        .map(|(c, _)| *c)
        .filter(|c| c.starts_with(m.composer.as_str()))
        .collect();
    if let Some(first) = hits.first() {
        m.composer = (*first).to_string();
    }
}

fn submit(m: &mut Model) -> Vec<Effect> {
    let line = m.composer.trim().to_string();
    if line.is_empty() {
        return vec![];
    }
    m.composer.clear();
    if line.starts_with('/') {
        return run_command(m, &line);
    }
    if m.pending.is_some() {
        m.entries.push(Entry::Info(
            "answer the permission first: a allow once, d deny".into(),
        ));
        m.composer = line;
        return vec![];
    }
    if m.busy {
        m.entries
            .push(Entry::Info("a task is running; Esc stops it".into()));
        m.composer = line;
        return vec![];
    }
    if !m.attached {
        m.entries
            .push(Entry::Error("no runtime attached; message not sent".into()));
        m.composer = line;
        return vec![];
    }
    m.task = line.clone();
    m.turn_rules.clear();
    m.life = Life::Running;
    m.entries.push(Entry::User(line.clone()));
    m.busy = true;
    m.scroll = 0;
    m.activity.clear();
    vec![Effect::Send(json!({"op": "turn", "text": line}))]
}

pub fn run_command(m: &mut Model, line: &str) -> Vec<Effect> {
    let mut parts = line.splitn(2, ' ');
    let cmd = parts.next().unwrap_or("");
    let arg = parts.next().unwrap_or("").trim();
    match cmd {
        "/help" => {
            m.help = true;
            vec![]
        }
        "/home" => goto(m, Screen::Cockpit),
        "/providers" => goto(m, Screen::Providers),
        "/models" => goto(m, Screen::Models),
        "/settings" => goto(m, Screen::Settings),
        "/capabilities" => goto(m, Screen::Capabilities),
        "/report" | "/evidence" => goto(m, Screen::Report),
        "/sessions" => goto(m, Screen::Sessions),
        "/log" | "/receipts" => goto(m, Screen::Receipts),
        "/plan" => set_mode(m, Mode::Plan),
        "/act" => set_mode(m, Mode::Act),
        "/audit" => set_mode(m, Mode::Audit),
        "/mode" => match Mode::parse(arg) {
            Some(mode) => set_mode(m, mode),
            None => {
                m.entries
                    .push(Entry::Error("usage: /mode plan|act|audit".into()));
                vec![]
            }
        },
        "/model" => {
            if arg.is_empty() {
                m.entries
                    .push(Entry::Error("usage: /model <model-id>".into()));
                vec![]
            } else {
                send(m, json!({"op": "select", "model": arg}))
            }
        }
        "/intent" => {
            if arg.is_empty() {
                m.entries
                    .push(Entry::Error("usage: /intent <reason>".into()));
                vec![]
            } else {
                send(m, json!({"op": "intent", "text": arg}))
            }
        }
        "/stop" => {
            if m.busy {
                cancel(m)
            } else {
                vec![]
            }
        }
        "/clear" => {
            m.entries.clear();
            m.scroll = 0;
            vec![]
        }
        "/quit" | "/exit" => {
            m.quit = true;
            vec![Effect::Quit]
        }
        other => {
            m.entries.push(Entry::Error(format!(
                "unknown command {other}; /help lists them"
            )));
            vec![]
        }
    }
}

fn palette_hits(query: &str) -> Vec<(&'static str, &'static str)> {
    let q = query.trim_start_matches('/').to_ascii_lowercase();
    COMMANDS
        .iter()
        .filter(|(c, d)| c.contains(&q) || d.contains(&q))
        .copied()
        .collect()
}

pub fn palette_items(p: &Palette) -> Vec<(&'static str, &'static str)> {
    palette_hits(&p.query)
}

fn on_palette_key(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    let Some(p) = m.palette.as_mut() else {
        return vec![];
    };
    match k.code {
        KeyCode::Esc => {
            m.palette = None;
        }
        KeyCode::Up => p.sel = p.sel.saturating_sub(1),
        KeyCode::Down => {
            let n = palette_hits(&p.query).len();
            if p.sel + 1 < n {
                p.sel += 1;
            }
        }
        KeyCode::Backspace => {
            text::pop_grapheme(&mut p.query);
            p.sel = 0;
        }
        KeyCode::Enter => {
            let hit = palette_hits(&p.query)
                .get(p.sel)
                .map(|(c, _)| c.to_string());
            m.palette = None;
            if let Some(cmd) = hit {
                // Commands that need an argument go to the composer instead of running bare.
                if cmd == "/model" || cmd == "/intent" {
                    m.screen = Screen::Cockpit;
                    m.composer = format!("{cmd} ");
                    return vec![];
                }
                return run_command(m, &cmd);
            }
        }
        KeyCode::Char(c) if !k.modifiers.contains(KeyModifiers::CONTROL) => {
            p.query.push(c);
            p.sel = 0;
        }
        _ => {}
    }
    vec![]
}

fn list_len(m: &Model) -> usize {
    match m.screen {
        Screen::Providers => m.providers.as_ref().map_or(0, Vec::len),
        Screen::Models => m.models.as_ref().map_or(0, Vec::len),
        Screen::Capabilities => m.caps.as_ref().map_or(0, |c| c.items.len()),
        Screen::Receipts => m.log.len(),
        _ => 0,
    }
}

fn sel_mut(m: &mut Model) -> &mut usize {
    match m.screen {
        Screen::Providers => &mut m.sel_provider,
        Screen::Models => &mut m.sel_model,
        Screen::Receipts => &mut m.sel_log,
        _ => &mut m.sel_cap,
    }
}

fn list_key(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    let n = list_len(m);
    match k.code {
        KeyCode::Up | KeyCode::Char('k') => {
            let s = sel_mut(m);
            *s = s.saturating_sub(1);
            vec![]
        }
        KeyCode::Down | KeyCode::Char('j') => {
            let s = sel_mut(m);
            if *s + 1 < n {
                *s += 1;
            }
            vec![]
        }
        KeyCode::Home => {
            *sel_mut(m) = 0;
            vec![]
        }
        KeyCode::End => {
            *sel_mut(m) = n.saturating_sub(1);
            vec![]
        }
        KeyCode::Tab => set_mode(m, m.mode.next(false)),
        KeyCode::Char('r') => {
            let screen = m.screen;
            goto(m, screen)
        }
        KeyCode::Enter => match m.screen {
            Screen::Models => {
                let id = m.models.as_ref().and_then(|v| v.get(m.sel_model)).cloned();
                match id {
                    Some(id) => {
                        m.entries.push(Entry::Info(format!("model {id}")));
                        send(m, json!({"op": "select", "model": id}))
                    }
                    None => vec![],
                }
            }
            _ => {
                m.detail = !m.detail;
                vec![]
            }
        },
        _ => vec![],
    }
}

fn settings_key(m: &mut Model, k: KeyEvent) -> Vec<Effect> {
    match k.code {
        KeyCode::Tab => set_mode(m, m.mode.next(false)),
        KeyCode::Char('c') => {
            m.display.color = !m.display.color;
            vec![]
        }
        KeyCode::Char('g') => {
            m.display.unicode = !m.display.unicode;
            vec![]
        }
        KeyCode::Char('m') => {
            m.display.motion = !m.display.motion;
            vec![]
        }
        _ => vec![],
    }
}

/// Tool-level fallback names, used only when the runtime returns no rule id.
/// Added to the spec's rule map by this hand-off (see docs/LBE_TERMINAL_UI.md).
pub fn tool_rule_name(tool: &str) -> &'static str {
    let t = tool.to_ascii_lowercase();
    let has = |words: &[&str]| words.iter().any(|w| t.contains(w));
    if has(&["read", "list", "glob", "search", "inspect"]) {
        "read allowed"
    } else if has(&["write", "patch", "edit", "create", "delete", "move"]) {
        "change allowed"
    } else if has(&["command", "exec", "run", "shell"]) {
        "command allowed"
    } else {
        "action allowed"
    }
}

fn rule_from(a: &Activity) -> Rule {
    if !a.rule.is_empty() {
        return mapped_rule(a);
    }
    let verdict = if a.event == "tool.escalated" {
        Verdict::Needs
    } else if a.status == "BLOCKED" {
        Verdict::Block
    } else if a.status == "FAILED" {
        Verdict::Unknown
    } else {
        Verdict::Pass
    };
    Rule {
        id: String::new(),
        more: Vec::new(),
        name: tool_rule_name(&a.tool).to_string(),
        target: a.detail.clone(),
        verdict,
        reason: a.reason.clone(),
        next: a.next.clone(),
        tool: a.tool.clone(),
        event: a.event.clone(),
        receipt: a.receipt.clone(),
        resolver: a.resolver.clone(),
        allowed: a.allowed.clone(),
        need: a.need.clone(),
    }
}

/// A rule id the runtime returned: looked up in the spec's rule map. An id that is
/// not in the map is shown as plain words, blocked, with `next: ask LBE why (d)`.
fn mapped_rule(a: &Activity) -> Rule {
    use crate::rules::{lookup, plain_words};
    let (name, verdict, reason, options): (String, Verdict, String, Vec<String>) =
        match lookup(&a.rule) {
            Some(r) => (
                r.name.to_string(),
                r.verdict,
                if a.reason.is_empty() {
                    r.reason.to_string()
                } else {
                    a.reason.clone()
                },
                r.options.iter().map(|s| s.to_string()).collect(),
            ),
            None => (
                plain_words(&a.rule),
                Verdict::Block,
                a.reason.clone(),
                Vec::new(),
            ),
        };
    // The runtime's own next step wins over the map's first option.
    let mut options = options;
    if !a.next.is_empty() {
        options.insert(0, a.next.clone());
    }
    let next = options.first().cloned().unwrap_or_default();
    Rule {
        id: a.rule.clone(),
        more: options.into_iter().skip(1).collect(),
        name,
        target: a.detail.clone(),
        verdict,
        reason,
        next,
        tool: a.tool.clone(),
        event: a.event.clone(),
        receipt: a.receipt.clone(),
        resolver: a.resolver.clone(),
        allowed: a.allowed.clone(),
        need: a.need.clone(),
    }
}

/// One banner on entering AUDIT, one line on leaving it; only on a runtime-confirmed change.
fn mode_changed(m: &mut Model, mode: Mode) {
    if m.mode == mode {
        return;
    }
    if mode == Mode::Audit {
        m.entries.push(Entry::Banner(
            "AUDIT · LBE is in control · read-only, nothing can change".into(),
        ));
    } else if m.mode == Mode::Audit {
        m.entries
            .push(Entry::Lifecycle("AUDIT ended · F6 opens the report".into()));
    }
    m.mode = mode;
}

fn on_bridge(m: &mut Model, b: Bridge) -> Vec<Effect> {
    match b {
        Bridge::Ready {
            session_id,
            mode,
            provider,
            model,
            workspace,
            permission,
            policy,
        } => {
            let first = !m.ready;
            m.attached = true;
            m.ready = true;
            m.session_id = session_id;
            if let Some(mode) = mode {
                if first {
                    m.mode = mode;
                } else {
                    mode_changed(m, mode);
                }
            }
            m.provider = provider;
            m.model = model;
            m.workspace = workspace;
            m.permission = permission;
            m.policy = policy;
        }
        Bridge::Error(msg) => m.entries.push(Entry::Error(msg)),
        Bridge::Reply(t) => {
            m.entries.push(Entry::Agent(text::plain_markdown(&t)));
            m.scroll = 0;
        }
        Bridge::Activity(a) => {
            if a.event.contains("error") {
                let msg = if a.detail.is_empty() { a.tool } else { a.detail };
                m.entries.push(Entry::Error(msg));
            } else {
                let rule = rule_from(&a);
                if rule.verdict == Verdict::Pass && rule.name == "read allowed" {
                    m.reads += 1;
                }
                m.turn_rules.push(rule.verdict);
                m.log.push(rule.clone());
                m.entries.push(Entry::Rule(rule));
                m.activity.push_back(a.tool);
                while m.activity.len() > 3 {
                    m.activity.pop_front();
                }
            }
        }
        Bridge::Effects { executed, blocked } => {
            m.executed += executed;
            m.blocked += blocked;
            let any = |v: Verdict| m.turn_rules.contains(&v);
            let line = if executed > 0 && any(Verdict::Failed) {
                Some((
                    Verdict::Failed,
                    format!(
                        "{executed} change{} made · a check failed · d details",
                        if executed == 1 { "" } else { "s" }
                    ),
                ))
            } else if executed > 0 {
                Some((
                    Verdict::Pass,
                    format!("{executed} change{} made", if executed == 1 { "" } else { "s" }),
                ))
            } else if any(Verdict::Needs) {
                None
            } else if any(Verdict::Block) {
                Some((Verdict::Block, "blocked · nothing changed".to_string()))
            } else if any(Verdict::Failed) {
                Some((Verdict::Failed, "change made · a check failed · d details".to_string()))
            } else if any(Verdict::Unknown) {
                Some((Verdict::Unknown, "effect unknown · d details".to_string()))
            } else {
                None
            };
            if let Some((v, t)) = line {
                m.entries.push(Entry::Effect(v, t));
            }
        }
        Bridge::Context { used, total } => m.ctx = Some((used, total)),
        Bridge::Permission(p) => m.pending = Some(p),
        Bridge::Receipt(r) => {
            let target = m
                .pending
                .as_ref()
                .map(|p| p.target.clone())
                .unwrap_or_default();
            let (verdict, line) = match r.status.as_str() {
                "EXECUTED" => (Some(Verdict::Pass), format!("written · {target}")),
                "DENIED" => (
                    Some(Verdict::Block),
                    "denied by you · nothing changed".to_string(),
                ),
                "FAILED" => (
                    Some(Verdict::Unknown),
                    "effect unknown · d details".to_string(),
                ),
                _ => (None, String::new()),
            };
            if let Some(v) = verdict {
                m.pending = None;
                m.detail = false;
                m.entries.push(Entry::Effect(v, line.trim_end_matches(" · ").to_string()));
            }
            m.receipts.push(r);
        }
        Bridge::Mode(mode) => mode_changed(m, mode),
        Bridge::Providers(p) => {
            m.sel_provider = m.sel_provider.min(p.len().saturating_sub(1));
            m.providers = Some(p);
        }
        Bridge::Models(v) => {
            m.sel_model = m.sel_model.min(v.len().saturating_sub(1));
            if let Some(i) = v.iter().position(|id| *id == m.model) {
                if m.models.is_none() {
                    m.sel_model = i;
                }
            }
            m.models = Some(v);
        }
        Bridge::Capabilities(c) => {
            m.sel_cap = m.sel_cap.min(c.items.len().saturating_sub(1));
            m.caps = Some(c);
        }
        Bridge::Git { branch, diff } => {
            m.git = if branch.is_empty() {
                None
            } else {
                Some((branch, diff))
            }
        }
        Bridge::Done => {
            if m.life == Life::Stopping {
                m.entries.push(Entry::Lifecycle(
                    "stopped by you · check the log (F8) for steps that already ran".into(),
                ));
            }
            m.life = Life::Running;
            m.busy = false;
            m.activity.clear();
        }
        Bridge::Closed => {
            m.attached = false;
            m.busy = false;
            m.life = Life::Running;
            m.entries.push(Entry::Error("runtime bridge closed".into()));
        }
    }
    vec![]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Permission, ProviderRow, Receipt};
    use crate::theme::Display;
    use crossterm::event::KeyEventState;

    fn model() -> Model {
        Model::new(Display {
            color: true,
            unicode: true,
            motion: true,
        })
    }
    fn key(code: KeyCode) -> Input {
        Input::Key(KeyEvent {
            code,
            modifiers: KeyModifiers::NONE,
            kind: KeyEventKind::Press,
            state: KeyEventState::NONE,
        })
    }
    fn ctrl(c: char) -> Input {
        Input::Key(KeyEvent {
            code: KeyCode::Char(c),
            modifiers: KeyModifiers::CONTROL,
            kind: KeyEventKind::Press,
            state: KeyEventState::NONE,
        })
    }
    fn type_text(m: &mut Model, s: &str) {
        for c in s.chars() {
            update(m, key(KeyCode::Char(c)));
        }
    }
    fn attached() -> Model {
        let mut m = model();
        update(
            &mut m,
            Input::Bridge(Bridge::Ready {
                session_id: "28457f04aa".into(),
                mode: Some(Mode::Act),
                provider: "lmstudio".into(),
                model: "gemma".into(),
                workspace: "ws".into(),
                permission: "write_allowed".into(),
                policy: "development".into(),
            }),
        );
        m
    }

    #[test]
    fn enter_sends_a_turn_once_and_marks_busy() {
        let mut m = attached();
        type_text(&mut m, "hello");
        let fx = update(&mut m, key(KeyCode::Enter));
        assert_eq!(
            fx,
            vec![Effect::Send(json!({"op": "turn", "text": "hello"}))]
        );
        assert!(m.busy && m.composer.is_empty());
        type_text(&mut m, "again");
        assert!(
            update(&mut m, key(KeyCode::Enter)).is_empty(),
            "no second turn while busy"
        );
        assert_eq!(m.composer, "again", "unsent text is kept");
    }

    #[test]
    fn without_a_bridge_nothing_is_sent_and_the_user_is_told() {
        let mut m = model();
        type_text(&mut m, "hi");
        assert!(update(&mut m, key(KeyCode::Enter)).is_empty());
        assert!(
            matches!(m.entries.last(), Some(Entry::Error(e)) if e.contains("no runtime attached"))
        );
    }

    #[test]
    fn decision_keys_only_work_with_an_empty_composer() {
        let mut m = attached();
        update(
            &mut m,
            Input::Bridge(Bridge::Permission(Permission {
                id: "ap".into(),
                action: "workspace.write".into(),
                scope: "s".into(),
                target: "t.txt".into(),
            })),
        );
        type_text(&mut m, "xad");
        assert_eq!(
            m.composer, "xad",
            "a and d are text once the composer has content"
        );
        assert!(m.pending.is_some());
        m.composer.clear();
        let fx = update(&mut m, key(KeyCode::Char('a')));
        assert_eq!(
            fx,
            vec![Effect::Send(
                json!({"op": "decision", "decision": "approve"})
            )]
        );
        let fx = update(&mut m, key(KeyCode::Char('d')));
        assert_eq!(
            fx,
            vec![Effect::Send(
                json!({"op": "decision", "decision": "reject"})
            )]
        );
    }

    #[test]
    fn terminal_receipt_clears_the_pending_gate() {
        let mut m = attached();
        m.pending = Some(Permission {
            id: "ap".into(),
            action: "x".into(),
            scope: "".into(),
            target: "".into(),
        });
        update(
            &mut m,
            Input::Bridge(Bridge::Receipt(Receipt {
                status: "EXECUTED".into(),
                id: "r-1".into(),
            })),
        );
        assert!(m.pending.is_none() && m.receipts.len() == 1);
    }

    #[test]
    fn ctrl_c_stops_a_running_turn_then_quits() {
        let mut m = attached();
        m.busy = true;
        assert_eq!(
            update(&mut m, ctrl('c')),
            vec![Effect::Send(json!({"op": "cancel"}))]
        );
        assert!(!m.quit);
        m.busy = false;
        assert_eq!(update(&mut m, ctrl('c')), vec![Effect::Quit]);
        assert!(m.quit);
    }

    #[test]
    fn function_keys_open_screens_and_request_their_data() {
        let mut m = attached();
        assert_eq!(
            update(&mut m, key(KeyCode::F(2))),
            vec![Effect::Send(json!({"op": "providers"}))]
        );
        assert_eq!(m.screen, Screen::Providers);
        assert_eq!(
            update(&mut m, key(KeyCode::F(3))),
            vec![Effect::Send(json!({"op": "models"}))]
        );
        assert_eq!(
            update(&mut m, key(KeyCode::F(5))),
            vec![Effect::Send(json!({"op": "capabilities"}))]
        );
        assert!(update(&mut m, key(KeyCode::F(4))).is_empty());
        update(&mut m, key(KeyCode::Esc));
        assert_eq!(m.screen, Screen::Cockpit);
    }

    #[test]
    fn mode_change_waits_for_the_runtime_when_attached() {
        let mut m = attached();
        let fx = update(&mut m, key(KeyCode::Tab));
        assert_eq!(
            fx,
            vec![Effect::Send(json!({"op": "mode", "mode": "audit"}))]
        );
        assert_eq!(
            m.mode,
            Mode::Act,
            "UI does not assume the runtime accepted it"
        );
        update(&mut m, Input::Bridge(Bridge::Mode(Mode::Audit)));
        assert_eq!(m.mode, Mode::Audit);
    }

    #[test]
    fn mode_change_is_local_only_when_no_runtime_is_attached() {
        let mut m = model();
        update(&mut m, key(KeyCode::Tab));
        assert_eq!(m.mode, Mode::Audit);
    }

    #[test]
    fn tab_completes_slash_commands() {
        let mut m = model();
        type_text(&mut m, "/pro");
        update(&mut m, key(KeyCode::Tab));
        assert_eq!(m.composer, "/providers");
    }

    #[test]
    fn paste_never_submits_and_is_sanitized() {
        let mut m = attached();
        update(&mut m, Input::Paste("rm -rf\n\x1b[2Jx".into()));
        assert_eq!(m.composer, "rm -rf\nx");
        assert!(!m.busy);
    }

    #[test]
    fn palette_filters_and_runs_a_command() {
        let mut m = attached();
        update(&mut m, ctrl('k'));
        type_text(&mut m, "audit");
        update(&mut m, key(KeyCode::Enter));
        assert!(m.palette.is_none());
        assert_eq!(m.mode, Mode::Act, "attached: waits for runtime");
    }

    #[test]
    fn model_screen_enter_selects_by_identity() {
        let mut m = attached();
        update(
            &mut m,
            Input::Bridge(Bridge::Models(vec!["a".into(), "b".into()])),
        );
        m.screen = Screen::Models;
        update(&mut m, key(KeyCode::Down));
        let fx = update(&mut m, key(KeyCode::Enter));
        assert_eq!(
            fx,
            vec![Effect::Send(json!({"op": "select", "model": "b"}))]
        );
    }

    #[test]
    fn selection_is_clamped_when_the_list_shrinks() {
        let mut m = attached();
        m.sel_provider = 5;
        let row = |id: &str| ProviderRow {
            id: id.into(),
            auth: "none".into(),
            installed: None,
            login_hint: String::new(),
            engines: vec![],
        };
        update(
            &mut m,
            Input::Bridge(Bridge::Providers(vec![row("a"), row("b")])),
        );
        assert_eq!(m.sel_provider, 1);
    }

    fn act(event: &str, tool: &str, status: &str, detail: &str) -> Activity {
        Activity {
            event: event.into(),
            tool: tool.into(),
            status: status.into(),
            receipt: String::new(),
            detail: detail.into(),
            reason: String::new(),
            next: String::new(),
            rule: String::new(),
            resolver: String::new(),
            allowed: Vec::new(),
            need: None,
        }
    }

    fn feed(m: &mut Model, a: Activity) {
        update(m, Input::Bridge(Bridge::Activity(a)));
    }

    #[test]
    fn done_ends_the_turn_and_clears_activity() {
        let mut m = attached();
        m.busy = true;
        feed(&mut m, act("tool.completed", "workspace.read", "OK", "a.py"));
        assert!(!m.activity.is_empty());
        update(&mut m, Input::Bridge(Bridge::Done));
        assert!(!m.busy && m.activity.is_empty());
    }

    #[test]
    fn runtime_rule_ids_are_mapped_and_unknown_ids_are_not_invented() {
        let mut m = attached();
        let mut a = act("tool.denied", "workspace.write", "BLOCKED", "x.py");
        a.rule = "CHANGED_OUTSIDE_SCOPE".into();
        feed(&mut m, a);
        let mut b = act("tool.denied", "workspace.write", "BLOCKED", "y.py");
        b.rule = "SOMETHING_NEW".into();
        feed(&mut m, b);
        let mut c = act("tool.denied", "workspace.write", "BLOCKED", "z.py");
        c.rule = "NO_SCOPE_FOUND".into();
        c.next = "ask the owner".into();
        feed(&mut m, c);
        let r: Vec<&Rule> = m
            .entries
            .iter()
            .filter_map(|e| if let Entry::Rule(r) = e { Some(r) } else { None })
            .collect();
        assert_eq!((r[0].name.as_str(), r[0].verdict), ("change in scope", Verdict::Failed));
        assert_eq!(r[0].next, "roll back");
        assert_eq!(r[0].more, vec!["expand scope", "ask you"]);
        assert_eq!((r[1].name.as_str(), r[1].verdict), ("something new", Verdict::Block));
        assert!(r[1].next.is_empty(), "no invented next step; the view shows ask LBE why");
        assert_eq!(r[2].next, "ask the owner", "the runtime's own next step wins");
        assert_eq!(r[2].more.first().map(String::as_str), Some("set scope"));
    }

    #[test]
    fn a_failed_check_after_a_change_gets_a_failed_effect_line() {
        let mut m = attached();
        let mut a = act("tool.completed", "workspace.patch", "OK", "x.py");
        a.rule = "CHANGED_OUTSIDE_SCOPE".into();
        feed(&mut m, a);
        update(&mut m, Input::Bridge(Bridge::Effects { executed: 1, blocked: 0 }));
        assert!(matches!(m.entries.last(), Some(Entry::Effect(Verdict::Failed, t)) if t.contains("1 change made")));
    }

    #[test]
    fn tool_steps_become_rule_lines_with_human_names() {
        let mut m = attached();
        feed(&mut m, act("tool.completed", "workspace.patch", "OK", "src/cli.py"));
        feed(&mut m, act("tool.denied", "workspace.write", "BLOCKED", "C:/x"));
        feed(&mut m, act("tool.escalated", "workspace.write", "BLOCKED", "t.py"));
        feed(&mut m, act("tool.failed", "shell.run", "FAILED", "make"));
        let rules: Vec<&Rule> = m
            .entries
            .iter()
            .filter_map(|e| if let Entry::Rule(r) = e { Some(r) } else { None })
            .collect();
        assert_eq!(rules[0].name, "change allowed");
        assert_eq!(rules[0].verdict, Verdict::Pass);
        assert_eq!(rules[1].verdict, Verdict::Block);
        assert_eq!(rules[2].verdict, Verdict::Needs);
        assert_eq!(rules[3].verdict, Verdict::Unknown);
        assert_eq!(rules[3].name, "command allowed");
        assert_eq!(m.log.len(), 4);
    }

    #[test]
    fn effect_line_reports_what_the_runtime_confirmed() {
        let mut m = attached();
        feed(&mut m, act("tool.completed", "workspace.patch", "OK", "a.py"));
        update(&mut m, Input::Bridge(Bridge::Effects { executed: 1, blocked: 0 }));
        assert!(matches!(m.entries.last(), Some(Entry::Effect(Verdict::Pass, t)) if t == "1 change made"));

        let mut m = attached();
        feed(&mut m, act("tool.denied", "workspace.write", "BLOCKED", "x"));
        update(&mut m, Input::Bridge(Bridge::Effects { executed: 0, blocked: 1 }));
        assert!(matches!(m.entries.last(), Some(Entry::Effect(Verdict::Block, _))));

        // A failed tool: not known whether anything changed.
        let mut m = attached();
        feed(&mut m, act("tool.failed", "shell.run", "FAILED", "x"));
        update(&mut m, Input::Bridge(Bridge::Effects { executed: 0, blocked: 1 }));
        assert!(matches!(m.entries.last(), Some(Entry::Effect(Verdict::Unknown, t)) if t.contains("unknown")));

        // Waiting for approval: the prompt resolves it, no effect line yet.
        let mut m = attached();
        feed(&mut m, act("tool.escalated", "workspace.write", "BLOCKED", "x"));
        let before = m.entries.len();
        update(&mut m, Input::Bridge(Bridge::Effects { executed: 0, blocked: 1 }));
        assert_eq!(m.entries.len(), before);
    }

    #[test]
    fn audit_banner_once_on_entry_and_one_line_on_exit() {
        let mut m = attached();
        update(&mut m, Input::Bridge(Bridge::Mode(Mode::Audit)));
        update(&mut m, Input::Bridge(Bridge::Mode(Mode::Audit)));
        let banners = m.entries.iter().filter(|e| matches!(e, Entry::Banner(_))).count();
        assert_eq!(banners, 1);
        update(&mut m, Input::Bridge(Bridge::Mode(Mode::Act)));
        let ends = m
            .entries
            .iter()
            .filter(|e| matches!(e, Entry::Lifecycle(s) if s.starts_with("AUDIT ended")))
            .count();
        assert_eq!(ends, 1);
    }

    #[test]
    fn stop_asks_once_and_says_stopped_only_after_the_runtime_is_done() {
        let mut m = attached();
        type_text(&mut m, "go");
        update(&mut m, key(KeyCode::Enter));
        assert!(update(&mut m, ctrl('x')).is_empty());
        assert_eq!(m.life, Life::ConfirmStop);
        // anything but y keeps going
        update(&mut m, key(KeyCode::Char('n')));
        assert_eq!(m.life, Life::Running);
        update(&mut m, ctrl('x'));
        let fx = update(&mut m, key(KeyCode::Char('y')));
        assert_eq!(fx, vec![Effect::Send(json!({"op": "cancel"}))]);
        assert_eq!(m.life, Life::Stopping);
        assert!(!m.entries.iter().any(|e| matches!(e, Entry::Lifecycle(s) if s.starts_with("stopped"))));
        update(&mut m, Input::Bridge(Bridge::Done));
        assert!(m.entries.iter().any(|e| matches!(e, Entry::Lifecycle(s) if s.starts_with("stopped"))));
        assert_eq!(m.life, Life::Running);
    }

    #[test]
    fn pause_is_not_faked() {
        let mut m = attached();
        m.busy = true;
        assert!(update(&mut m, ctrl('p')).is_empty());
        assert!(m.entries.iter().any(|e| matches!(e, Entry::Lifecycle(s) if s.contains("not available"))));
    }

    #[test]
    fn answering_a_permission_leaves_one_effect_line() {
        let mut m = attached();
        m.pending = Some(Permission {
            id: "ap".into(),
            action: "workspace.write".into(),
            scope: "s".into(),
            target: "tests/t.py".into(),
        });
        update(
            &mut m,
            Input::Bridge(Bridge::Receipt(Receipt {
                status: "EXECUTED".into(),
                id: "r-1".into(),
            })),
        );
        assert!(m.pending.is_none());
        assert!(matches!(m.entries.last(), Some(Entry::Effect(Verdict::Pass, t)) if t == "written · tests/t.py"));
    }

    #[test]
    fn rule_names_are_human_never_tool_ids() {
        assert_eq!(tool_rule_name("workspace.read"), "read allowed");
        assert_eq!(tool_rule_name("workspace.patch"), "change allowed");
        assert_eq!(tool_rule_name("mystery"), "action allowed");
    }

    #[test]
    fn plan_approval_key_switches_mode_only_after_a_reply() {
        let mut m = attached();
        m.mode = Mode::Plan;
        assert!(update(&mut m, key(KeyCode::Char('a'))).is_empty() || m.composer.is_empty());
        m.composer.clear();
        update(&mut m, Input::Bridge(Bridge::Reply("the plan".into())));
        let fx = update(&mut m, key(KeyCode::Char('a')));
        assert_eq!(fx, vec![Effect::Send(json!({"op": "mode", "mode": "act"}))]);
    }

    #[test]
    fn bridge_close_detaches_and_says_so() {
        let mut m = attached();
        update(&mut m, Input::Bridge(Bridge::Closed));
        assert!(!m.attached);
        assert!(matches!(m.entries.last(), Some(Entry::Error(_))));
    }

    #[test]
    fn evidence_reads_are_counted_from_passed_read_rules() {
        let mut m = attached();
        feed(&mut m, act("tool.completed", "workspace.read", "OK", "README.md"));
        feed(&mut m, act("tool.denied", "workspace.read", "BLOCKED", "secret"));
        assert_eq!(m.reads, 1);
    }

    #[test]
    fn a_burst_of_keys_never_submits() {
        let mut burst: Vec<Input> = "echo hi".chars().map(|c| key(KeyCode::Char(c))).collect();
        burst.push(key(KeyCode::Enter));
        burst.extend("second line".chars().map(|c| key(KeyCode::Char(c))));
        burst.push(key(KeyCode::Enter));
        let mut m = attached();
        let mut fx = Vec::new();
        for i in guard_paste(burst) {
            fx.extend(update(&mut m, i));
        }
        assert!(fx.is_empty(), "nothing sent: {fx:?}");
        assert_eq!(
            m.composer,
            "echo hi
second line
"
        );
        assert!(!m.busy);
    }

    #[test]
    fn a_normal_enter_still_submits() {
        let mut m = attached();
        let batch = vec![
            key(KeyCode::Char('h')),
            key(KeyCode::Char('i')),
            key(KeyCode::Enter),
        ];
        let mut fx = Vec::new();
        for i in guard_paste(batch) {
            fx.extend(update(&mut m, i));
        }
        assert_eq!(fx, vec![Effect::Send(json!({"op": "turn", "text": "hi"}))]);
    }

    #[test]
    fn settings_toggles_flip_display_only() {
        let mut m = model();
        m.screen = Screen::Settings;
        update(&mut m, key(KeyCode::Char('c')));
        update(&mut m, key(KeyCode::Char('g')));
        update(&mut m, key(KeyCode::Char('m')));
        assert!(!m.display.color && !m.display.unicode && !m.display.motion);
    }

    #[test]
    fn intent_answer_goes_to_the_runtime_as_one_explicit_command_and_never_as_chat() {
        let mut m = attached();
        type_text(&mut m, "/intent fix the parser bug");
        let fx = update(&mut m, key(KeyCode::Enter));
        assert_eq!(
            fx,
            vec![Effect::Send(
                json!({"op": "intent", "text": "fix the parser bug"})
            )]
        );
        let mut m = attached();
        type_text(&mut m, "/intent");
        assert!(update(&mut m, key(KeyCode::Enter)).is_empty());
        assert!(matches!(m.entries.last(), Some(Entry::Error(e)) if e.contains("usage: /intent")));
        let mut m = attached();
        type_text(&mut m, "because the owner asked");
        let fx = update(&mut m, key(KeyCode::Enter));
        assert_eq!(
            fx,
            vec![Effect::Send(
                json!({"op": "turn", "text": "because the owner asked"})
            )],
            "plain text is a normal turn; only /intent records an intent"
        );
    }
}
