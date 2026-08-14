"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { discoverPython, isSupportedPython, parsePythonVersion } = require("../lib/python-discovery");

test("parses and classifies supported Python versions", () => {
  assert.deepEqual(parsePythonVersion("Python 3.12.10"), [3, 12, 10]);
  assert.equal(isSupportedPython([3, 11, 0]), true);
  assert.equal(isSupportedPython([3, 10, 15]), false);
});

test("reports PYTHON_SUPPORTED deterministically", () => {
  const run = (command, args) => command === "py" && args[0] === "-3.12"
    ? { status: 0, stdout: "Python 3.12.10\n", stderr: "" }
    : { status: 1, stdout: "", stderr: "" };
  const result = discoverPython({ platform: "win32", run });
  assert.equal(result.state, "PYTHON_SUPPORTED");
  assert.equal(result.python.args[0], "-3.12");
});

test("reports PYTHON_UNSUPPORTED and PYTHON_NOT_FOUND", () => {
  const unsupported = discoverPython({ platform: "linux", run: () => ({ status: 0, stdout: "Python 3.10.9", stderr: "" }) });
  assert.equal(unsupported.state, "PYTHON_UNSUPPORTED");
  const absent = discoverPython({ platform: "linux", run: () => ({ status: 1, stdout: "", stderr: "" }) });
  assert.equal(absent.state, "PYTHON_NOT_FOUND");
});
