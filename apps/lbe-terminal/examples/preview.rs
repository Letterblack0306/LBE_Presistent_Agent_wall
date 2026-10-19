//! Renders representative frames to text and one HTML page (no terminal window).
//! usage: cargo run --example preview -- <out-dir>
use lbe_terminal::model::*;
use lbe_terminal::theme::Display;
use lbe_terminal::view::{render_html, render_text};

fn base(d: Display) -> Model {
    let mut m = Model::new(d);
    m.attached = true;
    m.ready = true;
    m.session_id = "28457f04aa11".into();
    m.workspace = "Agents-Memory-Tool-v6".into();
    m.provider = "lmstudio".into();
    m.model = "google/gemma-4-e4b".into();
    m.permission = "write_allowed".into();
    m.policy = "development".into();
    m.git = Some(("main".into(), 12));
    m.ctx = Some((4100, 8000));
    m
}

fn rule(name: &str, target: &str, verdict: Verdict) -> Rule {
    Rule {
        id: String::new(),
        more: vec![],
        name: name.into(),
        target: target.into(),
        verdict,
        reason: String::new(),
        next: String::new(),
        tool: "workspace.patch".into(),
        event: "tool.completed".into(),
        receipt: "rcpt_7f3a".into(),
        resolver: String::new(),
        allowed: vec![],
        need: None,
    }
}

fn cockpit(d: Display) -> Model {
    let mut m = base(d);
    m.task = "Now write it to C:/ProgramData/lbe/version.txt".into();
    m.entries = vec![
        Entry::User("Add a --version flag to the CLI".into()),
        Entry::Agent("Added --version. It prints the package version, exits 0.".into()),
        Entry::Rule(rule("intent recorded", "add --version flag", Verdict::Pass)),
        Entry::Rule(rule("change allowed", "src/cli.py", Verdict::Pass)),
        Entry::Rule(rule("change allowed", "tests/test_cli.py", Verdict::Pass)),
        Entry::Effect(Verdict::Pass, "1 change made".into()),
        Entry::User("Now write it to C:/ProgramData/lbe/version.txt".into()),
        Entry::Agent("I can't write there.".into()),
        Entry::Rule(Rule {
            reason: "not in the allowed files".into(),
            next: "narrow the change".into(),
            ..rule("change in allowed files", "C:/ProgramData/lbe", Verdict::Block)
        }),
        Entry::Effect(Verdict::Block, "blocked · nothing changed".into()),
    ];
    m.turn_rules = vec![Verdict::Block];
    m.log = m
        .entries
        .iter()
        .filter_map(|e| if let Entry::Rule(r) = e { Some(r.clone()) } else { None })
        .collect();
    m
}

fn main() {
    let out = std::path::PathBuf::from(std::env::args().nth(1).expect("out dir"));
    std::fs::create_dir_all(&out).unwrap();
    let on = Display {
        color: true,
        unicode: true,
        motion: true,
    };
    let mut frames: Vec<(String, Model, u16, u16)> = Vec::new();

    frames.push(("01-cockpit-wide".into(), cockpit(on), 120, 30));
    let mut gate = cockpit(on);
    gate.entries = vec![Entry::Agent("One change before validation.".into())];
    gate.pending = Some(Permission { id: "ap-1".into(), action: "workspace.write (write)".into(), scope: "creates 1 file · changes nothing else".into(), target: "tests/test_turn_path.py".into() });
    frames.push(("02-gate".into(), gate, 120, 30));
    let mut empty = base(on);
    empty.entries.clear();
    frames.push(("03-splash".into(), empty, 120, 30));
    let mut unat = Model::new(on);
    unat.workspace = "Agents-Memory-Tool-v6".into();
    frames.push(("04-not-attached".into(), unat, 120, 30));

    let mut p = base(on);
    p.screen = Screen::Providers;
    p.detail = true;
    p.sel_provider = 2;
    let row = |id: &str, auth: &str, inst: Option<bool>, hint: &str, eng: &[&str]| ProviderRow {
        id: id.into(),
        auth: auth.into(),
        installed: inst,
        login_hint: hint.into(),
        engines: eng.iter().map(|s| s.to_string()).collect(),
    };
    p.providers = Some(vec![
        row("openai-compatible", "configured", None, "", &["native-lbe"]),
        row("lmstudio", "none", None, "", &["cline", "native-lbe"]),
        row(
            "claude-code",
            "login",
            Some(true),
            "run `claude` and sign in",
            &["native-lbe"],
        ),
        row(
            "gemini-cli",
            "login",
            Some(false),
            "run `gemini` and sign in",
            &["native-lbe"],
        ),
        row("openrouter", "api_key", None, "", &["cline", "native-lbe"]),
        row("bedrock", "cloud_credentials", None, "", &["cline"]),
    ]);
    frames.push(("05-providers".into(), p, 120, 30));

    let mut mo = base(on);
    mo.screen = Screen::Models;
    mo.models = Some(vec![
        "google/gemma-4-e4b".into(),
        "google/gemma-3-12b".into(),
        "qwen/qwen3-coder-30b".into(),
    ]);
    frames.push(("06-models".into(), mo, 120, 30));

    let mut s = base(on);
    s.screen = Screen::Settings;
    frames.push(("07-settings".into(), s, 120, 30));

    let mut c = base(on);
    c.screen = Screen::Capabilities;
    c.detail = true;
    let cap = |id: &str, kind: &str, en: bool, av: &str, why: &str, risk: &str| CapabilityRow {
        id: id.into(),
        kind: kind.into(),
        enabled: en,
        availability: av.into(),
        rationale: why.into(),
        risk: risk.into(),
        access: "read".into(),
    };
    c.caps = Some(Capabilities {
        configured: true,
        error: String::new(),
        items: vec![
            cap(
                "birdeye",
                "mcp",
                true,
                "available",
                "MCP gateway; governed query only",
                "low",
            ),
            cap(
                "subagent.delegate",
                "subagent",
                true,
                "available",
                "delegates bounded work",
                "medium",
            ),
            cap(
                "notes-connector",
                "connector",
                true,
                "not connected",
                "transport does not answer",
                "low",
            ),
        ],
    });
    frames.push(("08-capabilities".into(), c, 120, 30));

    let mut r = cockpit(on);
    r.busy = false;
    r.screen = Screen::Report;
    r.reads = 3;
    frames.push(("09-report".into(), r, 120, 30));

    let mut a = cockpit(on);
    a.mode = Mode::Audit;
    a.reads = 14;
    a.entries = vec![
        Entry::Banner("AUDIT · LBE is in control · read-only, nothing can change".into()),
        Entry::User("Which provider is the production default?".into()),
        Entry::Agent("Two providers are configured; lmstudio is selected.".into()),
        Entry::Rule(rule("read allowed", "docs/CURRENT_STATUS.md", Verdict::Pass)),
    ];
    frames.push(("10-audit".into(), a, 120, 30));

    let mut pl = cockpit(on);
    pl.mode = Mode::Plan;
    pl.entries = vec![Entry::User("Plan: add --version".into()), Entry::Agent("1. Add the flag in cli.py\n2. Read version from package metadata\n3. Cover it with a test".into())];
    frames.push(("11-plan".into(), pl, 120, 30));

    let mut rc = cockpit(on);
    rc.screen = Screen::Receipts;
    frames.push(("18-receipts".into(), rc, 120, 30));
    let mut ss = cockpit(on);
    ss.screen = Screen::Sessions;
    frames.push(("19-sessions".into(), ss, 120, 30));
    let mut dt = cockpit(on);
    dt.detail = true;
    frames.push(("20-details".into(), dt, 120, 30));
    let mut off = cockpit(on);
    off.attached = false;
    frames.push(("21-offline".into(), off, 120, 30));
    frames.push(("12-compact".into(), cockpit(on), 80, 24));
    frames.push(("13-very-short".into(), cockpit(on), 80, 16 + 3));
    frames.push(("14-too-small".into(), cockpit(on), 50, 14));
    let mut cmp = cockpit(on);
    cmp.palette = Some(Palette::default());
    frames.push(("15-palette".into(), cmp, 120, 30));
    let mut hp = cockpit(on);
    hp.help = true;
    frames.push(("16-help".into(), hp, 120, 30));
    let mono = Display {
        color: false,
        unicode: false,
        motion: false,
    };
    frames.push(("17-mono-ascii".into(), cockpit(mono), 120, 30));

    let mut html = String::from("<!doctype html><meta charset=utf-8><style>body{background:#06070d;color:#e6e8ee;font:13px/1.2 Consolas,monospace;padding:16px}h3{color:#8e8e93;font:12px sans-serif;margin:18px 0 4px}pre.term{background:#0b0c15;margin:0;padding:6px;display:inline-block;color:#e6e8ee;line-height:1.25}</style>");
    for (name, m, w, h) in &frames {
        std::fs::write(out.join(format!("{name}.txt")), render_text(m, *w, *h)).unwrap();
        html.push_str(&format!(
            "<h3>{name} ({w}x{h})</h3>{}",
            render_html(m, *w, *h)
        ));
    }
    std::fs::write(out.join("preview.html"), html).unwrap();
    println!("wrote {} frames to {}", frames.len(), out.display());
}
