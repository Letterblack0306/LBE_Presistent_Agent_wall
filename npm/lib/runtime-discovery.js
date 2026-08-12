"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { managedPaths } = require("./paths");

const SUPPORTED_PYTHON_PACKAGE_SERIES = "0.2.";

function pythonExecutable(runtimePath, platform = process.platform) {
  return platform === "win32"
    ? path.join(runtimePath, "Scripts", "python.exe")
    : path.join(runtimePath, "bin", "python");
}

function lbeExecutable(runtimePath, platform = process.platform) {
  return platform === "win32"
    ? path.join(runtimePath, "Scripts", "lbe.exe")
    : path.join(runtimePath, "bin", "lbe");
}

function readRuntime({ env = process.env, platform = process.platform, fsModule = fs } = {}) {
  const paths = managedPaths(env, platform);
  if (!fsModule.existsSync(paths.metadataPath)) {
    return { state: "LBE_RUNTIME_NOT_INSTALLED", paths, metadata: null };
  }
  let metadata;
  try {
    metadata = JSON.parse(fsModule.readFileSync(paths.metadataPath, "utf8"));
  } catch (error) {
    return { state: "LBE_RUNTIME_BROKEN", paths, error: `Cannot read runtime metadata: ${error.message}` };
  }
  if (!metadata || typeof metadata.runtimePath !== "string" || typeof metadata.pythonPackageVersion !== "string") {
    return { state: "LBE_RUNTIME_BROKEN", paths, metadata, error: "Runtime metadata is incomplete." };
  }
  if (!metadata.pythonPackageVersion.startsWith(SUPPORTED_PYTHON_PACKAGE_SERIES)) {
    return {
      state: "LBE_RUNTIME_INCOMPATIBLE",
      paths,
      metadata,
      error: `Managed Python package ${metadata.pythonPackageVersion} is outside supported series ${SUPPORTED_PYTHON_PACKAGE_SERIES}x.`
    };
  }
  const executable = lbeExecutable(metadata.runtimePath, platform);
  if (!fsModule.existsSync(executable)) {
    return { state: "LBE_RUNTIME_BROKEN", paths, metadata, error: `Managed lbe executable is missing: ${executable}` };
  }
  return { state: "LBE_RUNTIME_COMPATIBLE", paths, metadata, executable };
}

module.exports = { SUPPORTED_PYTHON_PACKAGE_SERIES, pythonExecutable, lbeExecutable, readRuntime };
