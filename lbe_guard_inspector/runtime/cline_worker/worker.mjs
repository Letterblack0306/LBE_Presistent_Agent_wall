import readline from "node:readline";
import { AgentRuntime, createAgentRuntime } from "@cline/agents";

const PROTOCOL_VERSION = "lbe-cline-stdio/1";
const PINNED_CLINE_AGENTS_VERSION = "0.0.75";
const PYTHON_TO_NODE = new Set([
  "runtime.start",
  "turn.execute",
  "tool.result",
  "control.cancel",
  "control.steer",
  "runtime.shutdown",
]);

let sequence = 0;
let started = false;
let allowedTools = [];

function write(messageType, source, payload = {}) {
  sequence += 1;
  const frame = {
    protocol_version: PROTOCOL_VERSION,
    message_id: `node-${sequence}`,
    message_type: messageType,
    session_id: source.session_id,
    turn_id: source.turn_id,
    payload,
  };
  process.stdout.write(`${JSON.stringify(frame)}\n`);
}

function fail(source, code, message) {
  write("runtime.error", source, { code, message });
}

function validate(frame) {
  if (!frame || typeof frame !== "object" || Array.isArray(frame)) {
    throw new Error("frame must be an object");
  }
  for (const key of [
    "protocol_version",
    "message_id",
    "message_type",
    "session_id",
    "turn_id",
  ]) {
    if (typeof frame[key] !== "string" || !frame[key].trim()) {
      throw new Error(`${key} must be a non-empty string`);
    }
  }
  if (frame.protocol_version !== PROTOCOL_VERSION) {
    throw new Error(
      `unsupported protocol_version: ${frame.protocol_version}`,
    );
  }
  if (!PYTHON_TO_NODE.has(frame.message_type)) {
    throw new Error(
      `unknown or invalid message_type: ${frame.message_type}`,
    );
  }
}

function validateAllowedTools(value) {
  if (!Array.isArray(value)) {
    throw new Error("allowed_tools must be an array");
  }
  const ids = new Set();
  return value.map((tool) => {
    if (!tool || typeof tool !== "object" || Array.isArray(tool)) {
      throw new Error("allowed tool definition must be an object");
    }
    if (typeof tool.tool_id !== "string" || !tool.tool_id.trim()) {
      throw new Error("allowed tool tool_id must be a non-empty string");
    }
    if (ids.has(tool.tool_id)) {
      throw new Error(`duplicate allowed tool_id: ${tool.tool_id}`);
    }
    ids.add(tool.tool_id);
    return { ...tool };
  });
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

rl.on("line", (line) => {
  let frame;
  try {
    frame = JSON.parse(line);
    validate(frame);
  } catch (error) {
    fail(frame ?? { session_id: "unknown", turn_id: "unknown" }, "PROTOCOL_ERROR", String(error?.message ?? error));
    process.exitCode = 2;
    rl.close();
    return;
  }

  if (frame.message_type === "runtime.start") {
    if (started) {
      fail(frame, "DUPLICATE_START", "runtime already started");
      process.exitCode = 2;
      rl.close();
      return;
    }
    try {
      allowedTools = validateAllowedTools(frame.payload?.allowed_tools ?? []);
    } catch (error) {
      fail(frame, "INVALID_TOOL_ALLOWLIST", String(error?.message ?? error));
      process.exitCode = 2;
      rl.close();
      return;
    }
    started = true;
    write("runtime.ready", frame, {
      worker_version: "0.1.0",
      cline_agents_version: PINNED_CLINE_AGENTS_VERSION,
      agent_runtime_export: typeof AgentRuntime === "function",
      create_agent_runtime_export: typeof createAgentRuntime === "function",
      allowed_tool_ids: allowedTools.map((tool) => tool.tool_id),
      native_mutation_tools_registered: false,
    });
    return;
  }

  if (!started) {
    fail(frame, "RUNTIME_NOT_STARTED", "runtime.start required first");
    process.exitCode = 2;
    rl.close();
    return;
  }

  if (frame.message_type === "runtime.shutdown") {
    write("turn.completed", frame, { shutdown: true });
    rl.close();
    return;
  }

  if (frame.message_type === "turn.execute") {
    write("turn.failed", frame, {
      code: "FOUNDATION_CONTINUATION_UNVERIFIED",
      message:
        "Provider-backed AgentRuntime execution is intentionally not enabled in the foundation slice.",
    });
    return;
  }

  if (
    frame.message_type === "tool.result" ||
    frame.message_type === "control.cancel" ||
    frame.message_type === "control.steer"
  ) {
    fail(
      frame,
      "FOUNDATION_MESSAGE_UNIMPLEMENTED",
      `${frame.message_type} is not enabled in the foundation slice`,
    );
  }
});

rl.on("close", () => {
  if (process.exitCode === undefined) {
    process.exitCode = 0;
  }
});
