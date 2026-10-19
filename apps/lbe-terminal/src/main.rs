use std::io::IsTerminal;

const HELP: &str = "lbe-terminal: LBE terminal client (presentation only)

Environment:
  LBE_PYTHON          Python >= 3.11 used to start the runtime bridge
  LBE_REPO            repo root containing lbe_guard_inspector
  LBE_TARGET_WORKSPACE  workspace the session governs
  LBE_BRIDGE=off      UI only, no runtime
  NO_COLOR            no colour (bold and words remain)
  LBE_ASCII           ASCII glyphs
  LBE_NO_MOTION       no animation
";

fn main() {
    let arg = std::env::args().nth(1);
    match arg.as_deref() {
        Some("--help") | Some("-h") => {
            print!("{HELP}");
            return;
        }
        Some("--version") | Some("-V") => {
            println!("lbe-terminal {}", env!("CARGO_PKG_VERSION"));
            return;
        }
        _ => {}
    }
    if !std::io::stdin().is_terminal() || !std::io::stdout().is_terminal() {
        eprintln!("lbe-terminal needs an interactive terminal");
        std::process::exit(2);
    }
    if let Err(e) = lbe_terminal::app::run() {
        eprintln!("lbe-terminal: {e}");
        std::process::exit(1);
    }
}
