"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const {
  PUBLIC_PYTHON_PACKAGE,
  PUBLIC_PYTHON_PACKAGE_VERSION,
  acquirePublicRuntimeWheel,
  selectPublicWheel
} = require("../lib/runtime-install");

function metadataFor(bytes, overrides = {}) {
  const sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
  return {
    info: { name: PUBLIC_PYTHON_PACKAGE, version: PUBLIC_PYTHON_PACKAGE_VERSION },
    urls: [{
      packagetype: "bdist_wheel",
      filename: `lbe_guard_inspector-${PUBLIC_PYTHON_PACKAGE_VERSION}-py3-none-any.whl`,
      url: `https://files.pythonhosted.org/packages/lbe_guard_inspector-${PUBLIC_PYTHON_PACKAGE_VERSION}-py3-none-any.whl`,
      digests: { sha256 },
      ...overrides
    }]
  };
}

test("selects exactly one approved universal wheel", () => {
  const bytes = Buffer.from("wheel-content");
  const wheel = selectPublicWheel(metadataFor(bytes));
  assert.equal(wheel.filename, `lbe_guard_inspector-${PUBLIC_PYTHON_PACKAGE_VERSION}-py3-none-any.whl`);
  assert.match(wheel.sha256, /^[a-f0-9]{64}$/);
});

test("rejects unapproved wheel hosts", () => {
  const bytes = Buffer.from("wheel-content");
  const metadata = metadataFor(bytes, { url: "https://example.invalid/runtime.whl" });
  assert.throws(() => selectPublicWheel(metadata), /approved HTTPS host/);
});

test("rejects missing or ambiguous universal wheels", () => {
  assert.throws(() => selectPublicWheel({ urls: [] }), /exactly one universal/);
  const bytes = Buffer.from("wheel-content");
  const metadata = metadataFor(bytes);
  metadata.urls.push({ ...metadata.urls[0] });
  assert.throws(() => selectPublicWheel(metadata), /exactly one universal/);
});

test("acquires the exact public runtime and verifies SHA-256 before writing", async () => {
  const home = path.join(__dirname, ".tmp-public-acquire");
  fs.rmSync(home, { recursive: true, force: true });
  const bytes = Buffer.from("verified-wheel-content");
  const metadata = metadataFor(bytes);
  const fetchImpl = async (url) => {
    if (String(url).includes("/pypi/")) {
      return { ok: true, status: 200, json: async () => metadata };
    }
    return { ok: true, status: 200, arrayBuffer: async () => bytes };
  };
  const acquired = await acquirePublicRuntimeWheel({ env: { LBE_HOME: home }, platform: process.platform, fetchImpl });
  try {
    assert.equal(acquired.expectedVersion, PUBLIC_PYTHON_PACKAGE_VERSION);
    assert.equal(acquired.expectedSha256, crypto.createHash("sha256").update(bytes).digest("hex"));
    assert.equal(fs.readFileSync(acquired.wheelPath).equals(bytes), true);
    assert.equal(acquired.source, "pypi");
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test("rejects a downloaded wheel whose SHA-256 differs from registry metadata", async () => {
  const home = path.join(__dirname, ".tmp-public-hash-mismatch");
  fs.rmSync(home, { recursive: true, force: true });
  const expectedBytes = Buffer.from("expected");
  const actualBytes = Buffer.from("tampered");
  const metadata = metadataFor(expectedBytes);
  const fetchImpl = async (url) => {
    if (String(url).includes("/pypi/")) {
      return { ok: true, status: 200, json: async () => metadata };
    }
    return { ok: true, status: 200, arrayBuffer: async () => actualBytes };
  };
  await assert.rejects(
    acquirePublicRuntimeWheel({ env: { LBE_HOME: home }, platform: process.platform, fetchImpl }),
    /SHA-256 mismatch/
  );
  assert.equal(fs.existsSync(home), false);
});
