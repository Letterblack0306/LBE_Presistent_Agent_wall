"use strict";

const childProcess = require("node:child_process");

const MINIMUM_PYTHON = [3, 11];

function parsePythonVersion(value) {
  const match = /Python\s+(\d+)\.(\d+)(?:\.(\d+))?/.exec(String(value));
  return match ? [Number(match[1]), Number(match[2]), Number(match[3] || 0)] : null;
}

function isSupportedPython(version) {
  return Array.isArray(version) && (version[0] > MINIMUM_PYTHON[0] || (version[0] === MINIMUM_PYTHON[0] && version[1] >= MINIMUM_PYTHON[1]));
}

function defaultRun(command, args) {
  return childProcess.spawnSync(command, args, { encoding: "utf8", windowsHide: true });
}

function probePython(command, args = [], run = defaultRun) {
  const result = run(command, [...args, "--version"]);
  if (result.error || result.status !== 0) {
    return null;
  }
  const version = parsePythonVersion(`${result.stdout || ""}\n${result.stderr || ""}`);
  return version ? { command, args, version } : null;
}

function discoverPython({ platform = process.platform, run = defaultRun } = {}) {
  const candidates = platform === "win32"
    ? [["py", ["-3.14"]], ["py", ["-3.13"]], ["py", ["-3.12"]], ["py", ["-3.11"]], ["python", []]]
    : [["python3", []], ["python", []]];
  const found = candidates.map(([command, args]) => probePython(command, args, run)).filter(Boolean);
  const supported = found.find((candidate) => isSupportedPython(candidate.version));
  if (supported) {
    return { state: "PYTHON_SUPPORTED", python: supported, candidates: found };
  }
  if (found.length) {
    return { state: "PYTHON_UNSUPPORTED", python: found[0], candidates: found };
  }
  return { state: "PYTHON_NOT_FOUND", python: null, candidates: [] };
}

module.exports = { MINIMUM_PYTHON, parsePythonVersion, isSupportedPython, discoverPython };
