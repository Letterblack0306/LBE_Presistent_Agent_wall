"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");
const { managedPaths } = require("./paths");
const { discoverPython } = require("./python-discovery");
const { pythonExecutable, lbeExecutable, readRuntime } = require("./runtime-discovery");

function run(command, args, options = {}) {
  const result = childProcess.spawnSync(command, args, { encoding: "utf8", windowsHide: true, ...options });
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : `${result.stderr || result.stdout || "unknown failure"}`.trim();
    throw new Error(`Command failed: ${command} ${args.join(" ")}: ${detail}`);
  }
  return result.stdout || "";
}

function wheelHash(wheelPath) {
  return crypto.createHash("sha256").update(fs.readFileSync(wheelPath)).digest("hex");
}

function installRuntime({ wheelPath, env = process.env, platform = process.platform } = {}) {
  if (!wheelPath || !fs.existsSync(wheelPath)) {
    throw new Error("A local approved Python wheel is required. Re-run with --install --wheel <path-to-lbe_guard_inspector.whl>.");
  }
  const python = discoverPython({ platform });
  if (python.state !== "PYTHON_SUPPORTED") {
    throw new Error(`Cannot create managed LBE runtime: ${python.state}. Python 3.11 or later is required.`);
  }
  const paths = managedPaths(env, platform);
  fs.mkdirSync(paths.runtimeRoot, { recursive: true });
  fs.mkdirSync(paths.configRoot, { recursive: true });
  fs.mkdirSync(paths.stateRoot, { recursive: true });
  const hash = wheelHash(wheelPath);
  const runtimePath = path.join(paths.runtimeRoot, `python-${python.python.version.slice(0, 2).join(".")}-${hash.slice(0, 12)}`);
  const managedPython = pythonExecutable(runtimePath, platform);
  if (!fs.existsSync(managedPython)) {
    fs.mkdirSync(runtimePath, { recursive: true });
    run(python.python.command, [...python.python.args, "-m", "venv", runtimePath]);
  }
  run(managedPython, ["-m", "pip", "install", "--disable-pip-version-check", "--upgrade", wheelPath]);
  const packageVersion = run(managedPython, ["-c", "from importlib.metadata import version; print(version('lbe-guard-inspector'))"]).trim();
  const schema = run(managedPython, ["-c", "from importlib.resources import files; p=files('lbe_guard_inspector.memory').joinpath('memory_schema.sql'); assert p.is_file(); print(p)"]).trim();
  const executable = lbeExecutable(runtimePath, platform);
  if (!fs.existsSync(executable)) {
    throw new Error(`Managed install completed without lbe executable: ${executable}`);
  }
  const metadata = {
    schemaVersion: 1,
    runtimePath,
    python: { command: python.python.command, args: python.python.args, version: python.python.version.join(".") },
    pythonPackage: "lbe-guard-inspector",
    pythonPackageVersion: packageVersion,
    wheelSha256: hash,
    schemaResource: schema,
    installedAt: new Date().toISOString()
  };
  fs.writeFileSync(paths.metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, "utf8");
  return { ...readRuntime({ env, platform }), installed: true };
}

module.exports = { installRuntime, wheelHash };
