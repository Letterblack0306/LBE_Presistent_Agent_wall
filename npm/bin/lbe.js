#!/usr/bin/env node
"use strict";

const { runLauncher } = require("../lib/launcher");

runLauncher(process.argv.slice(2)).catch((error) => {
  process.stderr.write(`lbe installer: ${error.message}\n`);
  process.exitCode = 2;
});
