//! Process bridge: spawns the LBE Python runtime bridge and speaks JSON lines
//! over stdio. A reader thread parses lines into `Bridge` messages; the UI thread
//! never blocks on the runtime.
use crate::model::Bridge;
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::Sender;
use std::thread;

pub struct Runtime {
    child: Child,
    stdin: ChildStdin,
}

pub struct Config {
    pub python: String,
    pub repo: Option<String>,
}

impl Config {
    pub fn from_env(get: impl Fn(&str) -> Option<String>) -> Config {
        Config {
            python: get("LBE_PYTHON")
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| "python".into()),
            repo: get("LBE_REPO").filter(|s| !s.is_empty()),
        }
    }
}

impl Runtime {
    pub fn spawn(cfg: &Config, tx: Sender<Bridge>) -> Result<Runtime, String> {
        // Resolve the governed workspace before any chdir into the repo.
        let workspace = std::env::var("LBE_TARGET_WORKSPACE")
            .ok()
            .filter(|s| !s.is_empty())
            .or_else(|| {
                std::env::current_dir()
                    .ok()
                    .map(|p| p.to_string_lossy().into_owned())
            })
            .unwrap_or_else(|| ".".into());
        let mut cmd = Command::new(&cfg.python);
        cmd.args([
            "-m",
            "lbe_guard_inspector.tui_bridge",
            "--workspace",
            &workspace,
        ]);
        if let Some(repo) = &cfg.repo {
            cmd.current_dir(repo);
            cmd.env("PYTHONPATH", repo);
        }
        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("cannot start {}: {e}", cfg.python))?;
        let stdin = child.stdin.take().ok_or("bridge stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("bridge stdout unavailable")?;
        thread::spawn(move || {
            for l in lossy_lines(BufReader::new(stdout)) {
                if let Some(msg) = Bridge::parse(&l) {
                    if tx.send(msg).is_err() {
                        return;
                    }
                }
            }
            let _ = tx.send(Bridge::Closed);
        });
        Ok(Runtime { child, stdin })
    }

    pub fn send(&mut self, v: &Value) -> bool {
        writeln!(self.stdin, "{v}")
            .and_then(|_| self.stdin.flush())
            .is_ok()
    }
}

/// Lines from the bridge, decoded leniently: one stray byte becomes U+FFFD in that line
/// instead of ending the connection ("runtime bridge closed").
fn lossy_lines<R: BufRead>(mut reader: R) -> impl Iterator<Item = String> {
    std::iter::from_fn(move || {
        let mut buf = Vec::new();
        match reader.read_until(b'\n', &mut buf) {
            Ok(0) | Err(_) => None,
            Ok(_) => Some(
                String::from_utf8_lossy(&buf)
                    .trim_end_matches(['\r', '\n'])
                    .to_string(),
            ),
        }
    })
}

impl Drop for Runtime {
    fn drop(&mut self) {
        let _ = writeln!(self.stdin, "{}", serde_json::json!({"op": "quit"}));
        let _ = self.stdin.flush();
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_invalid_byte_does_not_end_the_stream() {
        let bytes: &[u8] = b"{\"a\":1}\n{\"t\":\"x\x97y\"}\r\n{\"b\":2}";
        let lines: Vec<String> = lossy_lines(bytes).collect();
        assert_eq!(lines.len(), 3, "{lines:?}");
        assert_eq!(lines[0], "{\"a\":1}");
        assert!(lines[1].contains('\u{FFFD}') && lines[1].ends_with("\"}"));
        assert_eq!(lines[2], "{\"b\":2}");
    }


    #[test]
    fn config_defaults_to_python_on_path() {
        let c = Config::from_env(|_| None);
        assert_eq!(c.python, "python");
        assert!(c.repo.is_none());
    }

    #[test]
    fn config_reads_overrides_and_ignores_empty() {
        let c = Config::from_env(|k| match k {
            "LBE_PYTHON" => Some("py313".into()),
            "LBE_REPO" => Some(String::new()),
            _ => None,
        });
        assert_eq!(c.python, "py313");
        assert!(c.repo.is_none());
    }

    #[test]
    fn spawn_failure_is_reported_not_panicked() {
        let (tx, _rx) = std::sync::mpsc::channel();
        let err = Runtime::spawn(
            &Config {
                python: "definitely-not-a-real-python".into(),
                repo: None,
            },
            tx,
        )
        .err();
        assert!(err.unwrap().starts_with("cannot start"));
    }
}
