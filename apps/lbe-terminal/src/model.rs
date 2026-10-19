//! Application state. Pure data: no I/O, no drawing. Every field is either
//! operator input or something the bridge reported; unknown stays unknown.
use crate::theme::Display;
use serde_json::Value;
use std::collections::VecDeque;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Screen {
    Cockpit,
    Providers,
    Models,
    Settings,
    Capabilities,
    Report,
    Sessions,
    Receipts,
}

impl Screen {
    pub const ALL: [Screen; 8] = [
        Screen::Cockpit,
        Screen::Providers,
        Screen::Models,
        Screen::Settings,
        Screen::Capabilities,
        Screen::Report,
        Screen::Sessions,
        Screen::Receipts,
    ];

    pub fn title(self) -> &'static str {
        match self {
            Screen::Cockpit => "cockpit",
            Screen::Providers => "providers",
            Screen::Models => "models",
            Screen::Settings => "settings",
            Screen::Capabilities => "capabilities",
            Screen::Report => "report",
            Screen::Sessions => "sessions",
            Screen::Receipts => "receipts",
        }
    }

    pub fn fkey(self) -> Option<u8> {
        match self {
            Screen::Cockpit => None,
            Screen::Providers => Some(2),
            Screen::Models => Some(3),
            Screen::Settings => Some(4),
            Screen::Capabilities => Some(5),
            Screen::Report => Some(6),
            Screen::Sessions => Some(7),
            Screen::Receipts => Some(8),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Plan,
    Act,
    Audit,
}

impl Mode {
    pub const ALL: [Mode; 3] = [Mode::Plan, Mode::Act, Mode::Audit];

    pub fn name(self) -> &'static str {
        match self {
            Mode::Plan => "plan",
            Mode::Act => "act",
            Mode::Audit => "audit",
        }
    }

    pub fn parse(s: &str) -> Option<Mode> {
        match s.trim().to_ascii_lowercase().as_str() {
            "plan" => Some(Mode::Plan),
            "act" | "coding" => Some(Mode::Act),
            "audit" => Some(Mode::Audit),
            _ => None,
        }
    }

    pub fn next(self, back: bool) -> Mode {
        let i = Mode::ALL.iter().position(|m| *m == self).unwrap_or(1);
        let n = Mode::ALL.len();
        Mode::ALL[if back { (i + n - 1) % n } else { (i + 1) % n }]
    }
}

/// Result of one LBE decision, as the runtime reported it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Verdict {
    Pass,
    Block,
    Needs,
    /// A check ran after a change and found it wrong: the change DID happen.
    Failed,
    /// Advisory only; never shown as a block.
    Advisory,
    /// The tool failed: whether anything changed is not known.
    Unknown,
}

/// One LBE decision: rule, target, result. `tool`/`event`/`receipt` are internals
/// shown only in the details layer and the receipts screen.
#[derive(Clone, Debug, PartialEq)]
pub struct Rule {
    /// Rule id from the runtime (details only); empty when none was returned.
    pub id: String,
    /// Further `next:` options, reached with `o`.
    pub more: Vec<String>,
    pub name: String,
    pub target: String,
    pub verdict: Verdict,
    pub reason: String,
    pub next: String,
    pub tool: String,
    pub event: String,
    pub receipt: String,
    /// `owner` when only the owner can resolve the block (drawn as the stop card).
    pub resolver: String,
    pub allowed: Vec<String>,
    pub need: Option<Box<Need>>,
}

// Entries are short-lived UI rows; boxing `Rule` would only churn every construction site.
#[allow(clippy::large_enum_variant)]
#[derive(Clone, Debug, PartialEq)]
pub enum Entry {
    User(String),
    Agent(String),
    Info(String),
    Error(String),
    Rule(Rule),
    /// Observed effect of a completed action (`✓` / `■` / `~`).
    Effect(Verdict, String),
    Lifecycle(String),
    Banner(String),
}

/// What a stop needs from the person, exactly as the runtime reported it (any field may be empty).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Need {
    pub checked: String,
    pub missing: String,
    pub investigate: String,
    pub ask: String,
}

/// What the runtime reported about one tool step.
#[derive(Clone, Debug, PartialEq)]
pub struct Activity {
    pub event: String,
    pub tool: String,
    pub status: String,
    pub receipt: String,
    pub detail: String,
    pub reason: String,
    pub next: String,
    pub rule: String,
    /// `owner` or `agent` when the runtime says who can resolve the block; else empty.
    pub resolver: String,
    /// Paths the runtime says are allowed, when it returned them.
    pub allowed: Vec<String>,
    /// Present only when the runtime sent an `ask` line.
    pub need: Option<Box<Need>>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Permission {
    pub id: String,
    pub action: String,
    pub scope: String,
    pub target: String,
}

/// Lifecycle request in flight; the label changes only when the runtime confirms.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Life {
    Running,
    ConfirmStop,
    Stopping,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Receipt {
    pub status: String,
    pub id: String,
}

impl Receipt {
    pub fn proven(&self) -> bool {
        self.status == "EXECUTED" || self.status == "OK"
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct ProviderRow {
    pub id: String,
    pub auth: String,
    pub installed: Option<bool>,
    pub login_hint: String,
    pub engines: Vec<String>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct CapabilityRow {
    pub id: String,
    pub kind: String,
    pub enabled: bool,
    pub availability: String,
    pub rationale: String,
    pub risk: String,
    pub access: String,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Capabilities {
    pub configured: bool,
    pub error: String,
    pub items: Vec<CapabilityRow>,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct Palette {
    pub query: String,
    pub sel: usize,
}

pub struct Model {
    pub screen: Screen,
    pub mode: Mode,
    pub workspace: String,
    pub provider: String,
    pub model: String,
    pub session_id: String,
    pub permission: String,
    pub policy: String,
    pub git: Option<(String, u64)>,
    /// A bridge is attached; without one the UI is a projection of nothing.
    pub attached: bool,
    pub ready: bool,
    pub entries: Vec<Entry>,
    /// Lines scrolled up from the newest transcript line.
    pub scroll: usize,
    pub composer: String,
    pub busy: bool,
    pub tick: u64,
    pub pending: Option<Permission>,
    pub receipts: Vec<Receipt>,
    pub executed: u64,
    pub blocked: u64,
    pub reads: u64,
    pub ctx: Option<(u64, u64)>,
    pub activity: VecDeque<String>,
    /// Rules decided during the current turn (drives the effect line).
    pub turn_rules: Vec<Verdict>,
    /// Every rule decided this session, oldest first (F8).
    pub log: Vec<Rule>,
    pub sel_log: usize,
    pub life: Life,
    /// Launch splash shows once; the first message removes it.
    pub task: String,
    pub providers: Option<Vec<ProviderRow>>,
    pub models: Option<Vec<String>>,
    pub caps: Option<Capabilities>,
    pub sel_provider: usize,
    pub sel_model: usize,
    pub sel_cap: usize,
    pub detail: bool,
    pub help: bool,
    pub palette: Option<Palette>,
    pub display: Display,
    pub quit: bool,
}

impl Model {
    pub fn new(display: Display) -> Model {
        Model {
            screen: Screen::Cockpit,
            mode: Mode::Act,
            workspace: String::new(),
            provider: String::new(),
            model: String::new(),
            session_id: String::new(),
            permission: String::new(),
            policy: String::new(),
            git: None,
            attached: false,
            ready: false,
            entries: Vec::new(),
            scroll: 0,
            composer: String::new(),
            busy: false,
            tick: 0,
            pending: None,
            receipts: Vec::new(),
            executed: 0,
            blocked: 0,
            reads: 0,
            ctx: None,
            activity: VecDeque::new(),
            turn_rules: Vec::new(),
            log: Vec::new(),
            sel_log: 0,
            life: Life::Running,
            task: String::new(),
            providers: None,
            models: None,
            caps: None,
            sel_provider: 0,
            sel_model: 0,
            sel_cap: 0,
            detail: false,
            help: false,
            palette: None,
            display,
            quit: false,
        }
    }

    pub fn short_id(&self) -> String {
        self.session_id.chars().take(8).collect()
    }
}

/// Everything the bridge can say, already validated and sanitized.
#[derive(Clone, Debug, PartialEq)]
pub enum Bridge {
    Ready {
        session_id: String,
        mode: Option<Mode>,
        provider: String,
        model: String,
        workspace: String,
        permission: String,
        policy: String,
    },
    Error(String),
    Reply(String),
    Activity(Activity),
    Effects {
        executed: u64,
        blocked: u64,
    },
    Context {
        used: u64,
        total: u64,
    },
    Permission(Permission),
    Receipt(Receipt),
    Mode(Mode),
    Providers(Vec<ProviderRow>),
    Models(Vec<String>),
    Capabilities(Capabilities),
    Git {
        branch: String,
        diff: u64,
    },
    Done,
    Closed,
}

fn s(v: &Value, k: &str) -> String {
    crate::text::sanitize(v.get(k).and_then(Value::as_str).unwrap_or(""))
}

/// A list of strings the runtime returned (sanitized, bounded); empty when absent.
fn list(v: &Value, k: &str) -> Vec<String> {
    v.get(k)
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Value::as_str)
                .take(20)
                .map(crate::text::sanitize)
                .collect()
        })
        .unwrap_or_default()
}

fn n(v: &Value, k: &str) -> u64 {
    v.get(k).and_then(Value::as_u64).unwrap_or(0)
}

impl Bridge {
    /// Parse one JSON line; unknown message types are ignored, not guessed at.
    pub fn parse(line: &str) -> Option<Bridge> {
        let v: Value = serde_json::from_str(line).ok()?;
        let kind = v.get("type")?.as_str()?;
        Some(match kind {
            "ready" => Bridge::Ready {
                session_id: s(&v, "session_id"),
                mode: Mode::parse(&s(&v, "mode")),
                provider: s(&v, "provider"),
                model: s(&v, "model"),
                workspace: s(&v, "workspace"),
                permission: s(&v, "permission"),
                policy: s(&v, "policy"),
            },
            "error" => Bridge::Error(s(&v, "message")),
            "reply" => Bridge::Reply(s(&v, "text")),
            "activity" => Bridge::Activity(Activity {
                event: s(&v, "event"),
                tool: s(&v, "name"),
                status: s(&v, "status"),
                receipt: s(&v, "receipt"),
                detail: s(&v, "detail"),
                reason: s(&v, "reason"),
                next: s(&v, "next"),
                rule: s(&v, "rule"),
                resolver: s(&v, "satisfiable_by"),
                allowed: list(&v, "allowed_paths"),
                need: {
                    let ask = s(&v, "ask");
                    if ask.is_empty() {
                        None
                    } else {
                        Some(Box::new(Need {
                            checked: s(&v, "checked"),
                            missing: s(&v, "missing"),
                            investigate: s(&v, "investigate"),
                            ask,
                        }))
                    }
                },
            }),
            "effects" => Bridge::Effects {
                executed: n(&v, "executed"),
                blocked: n(&v, "blocked"),
            },
            "context" => Bridge::Context {
                used: n(&v, "used"),
                total: n(&v, "total"),
            },
            "permission" => Bridge::Permission(Permission {
                id: s(&v, "id"),
                action: s(&v, "action"),
                scope: s(&v, "scope"),
                target: s(&v, "target"),
            }),
            "receipt" => Bridge::Receipt(Receipt {
                status: s(&v, "status"),
                id: s(&v, "receipt_id"),
            }),
            "mode" => Bridge::Mode(Mode::parse(&s(&v, "mode"))?),
            "providers" => Bridge::Providers(
                v.get("providers")?
                    .as_array()?
                    .iter()
                    .map(|p| ProviderRow {
                        id: s(p, "id"),
                        auth: s(p, "auth"),
                        installed: p.get("installed").and_then(Value::as_bool),
                        login_hint: s(p, "login_hint"),
                        engines: p
                            .get("engines")
                            .and_then(Value::as_array)
                            .map(|a| {
                                a.iter()
                                    .filter_map(Value::as_str)
                                    .map(crate::text::sanitize)
                                    .collect()
                            })
                            .unwrap_or_default(),
                    })
                    .collect(),
            ),
            "models" => Bridge::Models(
                v.get("models")?
                    .as_array()?
                    .iter()
                    .filter_map(Value::as_str)
                    .map(crate::text::sanitize)
                    .collect(),
            ),
            "capabilities" => Bridge::Capabilities(Capabilities {
                configured: v
                    .get("configured")
                    .and_then(Value::as_bool)
                    .unwrap_or(false),
                error: s(&v, "error"),
                items: v
                    .get("items")
                    .and_then(Value::as_array)
                    .map(|a| {
                        a.iter()
                            .map(|c| CapabilityRow {
                                id: s(c, "integration_id"),
                                kind: s(c, "kind"),
                                enabled: c.get("enabled").and_then(Value::as_bool).unwrap_or(false),
                                availability: s(c, "availability"),
                                rationale: s(c, "rationale"),
                                risk: s(c, "risk_class"),
                                access: s(c, "access_class"),
                            })
                            .collect()
                    })
                    .unwrap_or_default(),
            }),
            "git" => Bridge::Git {
                branch: s(&v, "branch"),
                diff: n(&v, "diff"),
            },
            "done" => Bridge::Done,
            _ => return None,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mode_cycles_both_ways() {
        assert_eq!(Mode::Act.next(false), Mode::Audit);
        assert_eq!(Mode::Audit.next(false), Mode::Plan);
        assert_eq!(Mode::Plan.next(true), Mode::Audit);
    }

    #[test]
    fn parses_ready_and_sanitizes() {
        let b = Bridge::parse(r#"{"type":"ready","session_id":"abc","mode":"audit","provider":"p\u001b[31m","model":"m","workspace":"w"}"#).unwrap();
        match b {
            Bridge::Ready { mode, provider, .. } => {
                assert_eq!(mode, Some(Mode::Audit));
                assert_eq!(provider, "p");
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn unknown_and_malformed_lines_are_ignored() {
        assert!(Bridge::parse("not json").is_none());
        assert!(Bridge::parse(r#"{"type":"mystery"}"#).is_none());
        assert!(Bridge::parse(r#"{"type":"mode","mode":"nonsense"}"#).is_none());
    }

    #[test]
    fn parses_provider_rows_with_unknown_install_state() {
        let b = Bridge::parse(r#"{"type":"providers","providers":[{"id":"lmstudio","auth":"none","engines":["native-lbe"]},{"id":"claude-code","auth":"login","installed":true,"login_hint":"run claude"}]}"#).unwrap();
        match b {
            Bridge::Providers(rows) => {
                assert_eq!(rows[0].installed, None);
                assert_eq!(rows[1].installed, Some(true));
                assert_eq!(rows[0].engines, vec!["native-lbe"]);
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn capabilities_not_configured_is_distinct_from_empty() {
        let b = Bridge::parse(r#"{"type":"capabilities","configured":false,"items":[]}"#).unwrap();
        match b {
            Bridge::Capabilities(c) => assert!(!c.configured && c.items.is_empty()),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn activity_keeps_the_runtime_fields_apart() {
        let b = Bridge::parse(r#"{"type":"activity","name":"workspace.read","event":"tool.completed","status":"OK","receipt":"r-1","detail":"README.md","reason":"x","next":"y"}"#).unwrap();
        match b {
            Bridge::Activity(a) => {
                assert_eq!(a.tool, "workspace.read");
                assert_eq!(a.detail, "README.md");
                assert_eq!((a.reason.as_str(), a.next.as_str()), ("x", "y"));
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn activity_carries_a_need_only_when_the_runtime_sent_an_ask() {
        let with = Bridge::parse(r#"{"type":"activity","name":"reasoning.inspect","event":"reasoning.needs_input","status":"BLOCKED","rule":"INSUFFICIENT_EVIDENCE","checked":"g1","missing":"x","investigate":"README.md","ask":"Where is x?"}"#).unwrap();
        let without = Bridge::parse(r#"{"type":"activity","name":"reasoning.inspect","event":"model.error","status":"FAILED","checked":"g1"}"#).unwrap();
        match (with, without) {
            (Bridge::Activity(a), Bridge::Activity(b)) => {
                let n = a.need.expect("ask present");
                assert_eq!((n.checked.as_str(), n.missing.as_str(), n.ask.as_str()), ("g1", "x", "Where is x?"));
                assert!(b.need.is_none(), "no ask, no card");
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn activity_carries_who_can_resolve_and_the_allowed_paths_only_when_sent() {
        let sent = Bridge::parse(r#"{"type":"activity","name":"workspace.write_text","event":"tool.denied","status":"BLOCKED","satisfiable_by":"owner","allowed_paths":["a.txt","b.txt"]}"#).unwrap();
        let absent = Bridge::parse(r#"{"type":"activity","name":"workspace.read","event":"tool.completed","status":"OK"}"#).unwrap();
        match (sent, absent) {
            (Bridge::Activity(s), Bridge::Activity(a)) => {
                assert_eq!(s.resolver, "owner");
                assert_eq!(s.allowed, vec!["a.txt".to_string(), "b.txt".to_string()]);
                assert!(a.resolver.is_empty() && a.allowed.is_empty());
            }
            other => panic!("{other:?}"),
        }
    }
}
