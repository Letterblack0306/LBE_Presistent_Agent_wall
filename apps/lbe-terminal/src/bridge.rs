//! Process bridge to the LBE runtime (`lbe_guard_inspector.tui_bridge`).
//! JSON lines over the child's stdio; a reader thread forwards parsed
//! messages to the UI loop so rendering never blocks on a turn.

use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver};
use std::thread;

use serde_json::Value;

pub struct Bridge {
    child: Child,
    stdin: ChildStdin,
    pub rx: Receiver<Value>,
}

fn repo_root() -> Option<PathBuf> {
    if let Ok(r) = std::env::var("LBE_REPO") {
        let p = PathBuf::from(r);
        if p.join("lbe_guard_inspector").join("tui_bridge.py").is_file() {
            return Some(p);
        }
    }
    let mut starts: Vec<PathBuf> = Vec::new();
    if let Ok(c) = std::env::current_dir() {
        starts.push(c);
    }
    if let Ok(e) = std::env::current_exe() {
        if let Some(d) = e.parent() {
            starts.push(d.to_path_buf());
        }
    }
    for s in starts {
        let mut cur: Option<&Path> = Some(s.as_path());
        while let Some(d) = cur {
            if d.join("lbe_guard_inspector").join("tui_bridge.py").is_file() {
                return Some(d.to_path_buf());
            }
            cur = d.parent();
        }
    }
    None
}

/// First interpreter that is Python >= 3.11 (the runtime uses `enum.StrEnum`).
fn find_python() -> Option<(String, Vec<String>)> {
    let mut candidates: Vec<(String, Vec<String>)> = Vec::new();
    if let Ok(p) = std::env::var("LBE_PYTHON") {
        candidates.push((p, vec![]));
    }
    candidates.push(("python".into(), vec![]));
    candidates.push(("python3".into(), vec![]));
    candidates.push(("py".into(), vec!["-3".into()]));
    for (cmd, pre) in candidates {
        let ok = Command::new(&cmd)
            .args(&pre)
            .args(["-c", "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if ok {
            return Some((cmd, pre));
        }
    }
    None
}

impl Bridge {
    pub fn start() -> Result<Bridge, String> {
        let root = repo_root().ok_or("LBE runtime not found (set LBE_REPO to the repo root)")?;
        let (py, pre) = find_python().ok_or("Python 3.11+ not found (set LBE_PYTHON)")?;
        let workspace = std::env::var("LBE_TARGET_WORKSPACE")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .or_else(|| std::env::current_dir().ok().map(|p| p.to_string_lossy().into_owned()))
            .unwrap_or_else(|| ".".into());

        let mut cmd = Command::new(py);
        cmd.args(pre)
            .args(["-m", "lbe_guard_inspector.tui_bridge", "--workspace", &workspace])
            .current_dir(&root)
            .env("PYTHONPATH", &root)
            .env("PYTHONUTF8", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        let has_cfg = std::env::var("LBE_PROVIDER_CONFIG").map(|v| !v.trim().is_empty()).unwrap_or(false);
        if !has_cfg {
            let local = root.join("reasoning-provider.json");
            if local.is_file() {
                cmd.arg("--provider-config").arg(local);
            }
        }
        let mut child = cmd.spawn().map_err(|e| format!("could not start runtime bridge: {e}"))?;
        let stdin = child.stdin.take().ok_or("bridge stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("bridge stdout unavailable")?;
        let (tx, rx) = mpsc::channel();
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let Ok(line) = line else { break };
                if let Ok(v) = serde_json::from_str::<Value>(&line) {
                    if tx.send(v).is_err() {
                        break;
                    }
                }
            }
            let _ = tx.send(serde_json::json!({"type": "closed"}));
        });
        Ok(Bridge { child, stdin, rx })
    }

    pub fn send_line(&mut self, line: &str) {
        let _ = writeln!(self.stdin, "{line}");
        let _ = self.stdin.flush();
    }

    pub fn shutdown(&mut self) {
        self.send_line("{\"op\":\"quit\"}");
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
