"use strict";

const os = require("node:os");
const path = require("node:path");

function lbeHome(env = process.env, platform = process.platform) {
  if (env.LBE_HOME && env.LBE_HOME.trim()) {
    return path.resolve(env.LBE_HOME);
  }
  if (platform === "win32") {
    return path.join(env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), "LetterBlack", "LBE");
  }
  return path.join(env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share"), "letterblack", "lbe");
}

function managedPaths(env = process.env, platform = process.platform) {
  const home = lbeHome(env, platform);
  return {
    home,
    runtimeRoot: path.join(home, "runtime"),
    configRoot: path.join(home, "config"),
    stateRoot: path.join(home, "state"),
    metadataPath: path.join(home, "runtime", "runtime.json")
  };
}

module.exports = { lbeHome, managedPaths };
