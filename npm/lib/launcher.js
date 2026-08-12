"use strict";

const childProcess = require("node:child_process");
const { readRuntime } = require("./runtime-discovery");
const { installRuntime } = require("./runtime-install");
const { discoverPython } = require("./python-discovery");

function emit(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function fail(message, code = 2) {
  process.stderr.write(`lbe installer: ${message}\n`);
  process.exitCode = code;
}

function forward(executable, args) {
  const child = childProcess.spawn(executable, args, { stdio: "inherit", windowsHide: true });
  child.on("error", (error) => fail(`Unable to launch managed Python LBE runtime: ${error.message}`));
  child.on("exit", (code, signal) => { process.exitCode = signal ? 1 : (code ?? 1); });
}

function runLauncher(args, { env = process.env, platform = process.platform } = {}) {
  if (args[0] === "--diagnose") {
    emit({ python: discoverPython({ platform }), runtime: readRuntime({ env, platform }) });
    return;
  }
  if (args[0] === "--install") {
    const wheelIndex = args.indexOf("--wheel");
    const wheelPath = wheelIndex >= 0 ? args[wheelIndex + 1] : undefined;
    try {
      const runtime = installRuntime({ wheelPath, env, platform });
      emit({ action: "install", ok: true, runtime: runtime.metadata });
    } catch (error) {
      fail(error.message);
    }
    return;
  }
  const runtime = readRuntime({ env, platform });
  if (runtime.state !== "LBE_RUNTIME_COMPATIBLE") {
    fail(`${runtime.state}. Install a local approved Python runtime with: lbe --install --wheel <path-to-lbe_guard_inspector.whl>`);
    return;
  }
  forward(runtime.executable, args);
}

module.exports = { runLauncher };
