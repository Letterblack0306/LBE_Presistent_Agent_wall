"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");
const { readRuntime, SUPPORTED_PYTHON_PACKAGE_SERIES } = require("../lib/runtime-discovery");
const { PUBLIC_PYTHON_PACKAGE_VERSION } = require("../lib/runtime-install");

const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8"));

test("package exposes the V2 public bootstrap contract", () => {
  assert.equal(packageJson.name, "@letterblack/lbe");
  assert.equal(packageJson.version, "2.0.2");
  assert.equal(PUBLIC_PYTHON_PACKAGE_VERSION, "2.0.2");
  assert.equal(SUPPORTED_PYTHON_PACKAGE_SERIES, "2.0.");
  assert.deepEqual(packageJson.bin, { lbe: "bin/lbe.js" });
  assert.equal(fs.existsSync(path.join(__dirname, "..", packageJson.bin.lbe)), true);
});

test("missing managed runtime is explicit", () => {
  const home = path.join(__dirname, ".tmp-missing-runtime");
  const result = readRuntime({ env: { LBE_HOME: home }, platform: process.platform });
  assert.equal(result.state, "LBE_RUNTIME_NOT_INSTALLED");
});

test("incompatible managed runtime is explicit", () => {
  const home = path.join(__dirname, ".tmp-incompatible-runtime");
  const runtimeRoot = path.join(home, "runtime");
  const fakeRuntime = path.join(runtimeRoot, "fake");
  fs.mkdirSync(path.join(fakeRuntime, process.platform === "win32" ? "Scripts" : "bin"), { recursive: true });
  const executable = path.join(
    fakeRuntime,
    process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "lbe.exe" : "lbe"
  );
  fs.writeFileSync(executable, "", "utf8");
  fs.writeFileSync(path.join(runtimeRoot, "runtime.json"), JSON.stringify({ runtimePath: fakeRuntime, pythonPackageVersion: "1.0.0" }), "utf8");
  const result = readRuntime({ env: { LBE_HOME: home }, platform: process.platform });
  assert.equal(result.state, "LBE_RUNTIME_INCOMPATIBLE");
  fs.rmSync(home, { recursive: true, force: true });
});

test("node wrapper source has no Python runtime authority modules", () => {
  const forbidden = /session_memory_runtime|authorization_resolver|completion_gate|tool_orchestration|provider_registry/;
  for (const entry of fs.readdirSync(path.join(__dirname, "..", "lib"))) {
    const content = fs.readFileSync(path.join(__dirname, "..", "lib", entry), "utf8");
    assert.equal(forbidden.test(content), false, entry);
  }
});

test("npm tarball contains only the declared bootstrap surface", () => {
  assert.ok(process.env.npm_execpath, "npm must provide npm_execpath while running the package test");
  const result = childProcess.spawnSync(process.execPath, [process.env.npm_execpath, "pack", "--dry-run", "--json"], {
    cwd: path.join(__dirname, ".."),
    encoding: "utf8",
    windowsHide: true
  });
  assert.equal(result.status, 0, `${result.error ?? ""}\n${result.stderr}`);
  const files = JSON.parse(result.stdout)[0].files.map((entry) => entry.path);
  assert.deepEqual(files, [
    "README.md",
    "bin/lbe.js",
    "lib/launcher.js",
    "lib/paths.js",
    "lib/python-discovery.js",
    "lib/runtime-discovery.js",
    "lib/runtime-install.js",
    "package.json"
  ]);
});
