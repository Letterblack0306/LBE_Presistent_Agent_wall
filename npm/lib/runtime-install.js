"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const childProcess = require("node:child_process");
const { managedPaths } = require("./paths");
const { discoverPython } = require("./python-discovery");
const { pythonExecutable, lbeExecutable, readRuntime } = require("./runtime-discovery");

const PUBLIC_PYTHON_PACKAGE = "lbe-guard-inspector";
const PUBLIC_PYTHON_PACKAGE_VERSION = "2.0.1";
const PUBLIC_PYPI_METADATA_URL = `https://pypi.org/pypi/${PUBLIC_PYTHON_PACKAGE}/${PUBLIC_PYTHON_PACKAGE_VERSION}/json`;
const APPROVED_WHEEL_HOSTS = new Set(["files.pythonhosted.org"]);

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

function selectPublicWheel(metadata) {
  const urls = Array.isArray(metadata?.urls) ? metadata.urls : [];
  const wheels = urls.filter((entry) =>
    entry?.packagetype === "bdist_wheel" &&
    typeof entry.filename === "string" &&
    entry.filename.endsWith("-py3-none-any.whl")
  );
  if (wheels.length !== 1) {
    throw new Error(`Public runtime metadata must contain exactly one universal py3-none-any wheel; found ${wheels.length}.`);
  }
  const wheel = wheels[0];
  const sha256 = wheel?.digests?.sha256;
  if (typeof sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(sha256)) {
    throw new Error("Public runtime metadata is missing a valid SHA-256 digest.");
  }
  let url;
  try {
    url = new URL(wheel.url);
  } catch {
    throw new Error("Public runtime metadata contains an invalid wheel URL.");
  }
  if (url.protocol !== "https:" || !APPROVED_WHEEL_HOSTS.has(url.hostname)) {
    throw new Error(`Public runtime wheel URL is not on an approved HTTPS host: ${url.hostname || "unknown"}.`);
  }
  return { filename: wheel.filename, url: url.toString(), sha256: sha256.toLowerCase() };
}

async function acquirePublicRuntimeWheel({ env = process.env, platform = process.platform, fetchImpl = globalThis.fetch } = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("Public runtime acquisition requires a Node.js runtime with fetch support (Node 20 or later).");
  }
  const metadataResponse = await fetchImpl(PUBLIC_PYPI_METADATA_URL, { headers: { accept: "application/json" } });
  if (!metadataResponse?.ok) {
    throw new Error(`Public runtime ${PUBLIC_PYTHON_PACKAGE}==${PUBLIC_PYTHON_PACKAGE_VERSION} is unavailable from PyPI (HTTP ${metadataResponse?.status ?? "unknown"}).`);
  }
  const metadata = await metadataResponse.json();
  if (metadata?.info?.name !== PUBLIC_PYTHON_PACKAGE || metadata?.info?.version !== PUBLIC_PYTHON_PACKAGE_VERSION) {
    throw new Error("Public runtime metadata identity/version does not match the configured release.");
  }
  const wheel = selectPublicWheel(metadata);
  const artifactResponse = await fetchImpl(wheel.url);
  if (!artifactResponse?.ok) {
    throw new Error(`Unable to download public runtime wheel (HTTP ${artifactResponse?.status ?? "unknown"}).`);
  }
  const bytes = Buffer.from(await artifactResponse.arrayBuffer());
  const actualHash = crypto.createHash("sha256").update(bytes).digest("hex");
  if (actualHash !== wheel.sha256) {
    throw new Error(`Public runtime wheel SHA-256 mismatch: expected ${wheel.sha256}, got ${actualHash}.`);
  }
  const paths = managedPaths(env, platform);
  const downloadRoot = path.join(paths.runtimeRoot, ".downloads");
  fs.mkdirSync(downloadRoot, { recursive: true });
  const wheelPath = path.join(downloadRoot, wheel.filename);
  fs.writeFileSync(wheelPath, bytes);
  return {
    wheelPath,
    expectedVersion: PUBLIC_PYTHON_PACKAGE_VERSION,
    expectedSha256: wheel.sha256,
    source: "pypi",
    sourceUrl: PUBLIC_PYPI_METADATA_URL
  };
}

function installRuntime({
  wheelPath,
  expectedVersion,
  expectedSha256,
  source = "local-wheel",
  sourceUrl,
  env = process.env,
  platform = process.platform
} = {}) {
  if (!wheelPath || !fs.existsSync(wheelPath)) {
    throw new Error("Runtime wheel does not exist. Use `lbe --install` for public installation or `lbe --install --wheel <path>` for an offline wheel.");
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
  if (expectedSha256 && hash !== expectedSha256.toLowerCase()) {
    throw new Error(`Runtime wheel SHA-256 mismatch before installation: expected ${expectedSha256}, got ${hash}.`);
  }
  const runtimePath = path.join(paths.runtimeRoot, `python-${python.python.version.slice(0, 2).join(".")}-${hash.slice(0, 12)}`);
  const managedPython = pythonExecutable(runtimePath, platform);
  if (!fs.existsSync(managedPython)) {
    fs.mkdirSync(runtimePath, { recursive: true });
    run(python.python.command, [...python.python.args, "-m", "venv", runtimePath]);
  }
  run(managedPython, ["-m", "pip", "install", "--disable-pip-version-check", "--upgrade", wheelPath]);
  const packageVersion = run(managedPython, ["-c", `from importlib.metadata import version; print(version('${PUBLIC_PYTHON_PACKAGE}'))`]).trim();
  if (expectedVersion && packageVersion !== expectedVersion) {
    throw new Error(`Installed Python runtime version ${packageVersion} does not match expected ${expectedVersion}.`);
  }
  const schema = run(managedPython, ["-c", "from importlib.resources import files; p=files('lbe_guard_inspector.memory').joinpath('memory_schema.sql'); assert p.is_file(); print(p)"]).trim();
  const executable = lbeExecutable(runtimePath, platform);
  if (!fs.existsSync(executable)) {
    throw new Error(`Managed install completed without lbe executable: ${executable}`);
  }
  const metadata = {
    schemaVersion: 1,
    runtimePath,
    python: { command: python.python.command, args: python.python.args, version: python.python.version.join(".") },
    pythonPackage: PUBLIC_PYTHON_PACKAGE,
    pythonPackageVersion: packageVersion,
    wheelSha256: hash,
    installSource: source,
    sourceUrl: sourceUrl || null,
    schemaResource: schema,
    installedAt: new Date().toISOString()
  };
  fs.writeFileSync(paths.metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, "utf8");
  const runtime = readRuntime({ env, platform });
  if (runtime.state !== "LBE_RUNTIME_COMPATIBLE") {
    throw new Error(`Managed runtime installed but compatibility verification failed: ${runtime.state}.`);
  }
  return { ...runtime, installed: true };
}

async function installPublicRuntime({ env = process.env, platform = process.platform, fetchImpl = globalThis.fetch } = {}) {
  const acquired = await acquirePublicRuntimeWheel({ env, platform, fetchImpl });
  try {
    return installRuntime({ ...acquired, env, platform });
  } finally {
    fs.rmSync(acquired.wheelPath, { force: true });
    try {
      fs.rmdirSync(path.dirname(acquired.wheelPath));
    } catch {
      // Keep a non-empty/shared download directory intact.
    }
  }
}

module.exports = {
  APPROVED_WHEEL_HOSTS,
  PUBLIC_PYTHON_PACKAGE,
  PUBLIC_PYTHON_PACKAGE_VERSION,
  PUBLIC_PYPI_METADATA_URL,
  acquirePublicRuntimeWheel,
  installPublicRuntime,
  installRuntime,
  selectPublicWheel,
  wheelHash
};
