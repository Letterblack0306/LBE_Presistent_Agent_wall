import { createHandlerAsync } from "@cline/llms";
import process from "node:process";

const ALLOWED_PROVIDER_IDS = new Set([
  "anthropic",
  "openai-compatible",
  "openai-native",
  "gemini",
  "vertex",
  "bedrock",
  "ollama",
  "lmstudio",
  "openrouter",
]);

let activeHandler = null;

function fail(message, code = "CLINE_BRIDGE_ERROR") {
  process.stdout.write(`${JSON.stringify({ kind: "error", code, message })}\n`);
  process.exitCode = 1;
}

function requiredText(value, field) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${field} must be a non-empty string`);
  }
  return value.trim();
}

function validateTool(tool) {
  if (!tool || typeof tool !== "object" || Array.isArray(tool)) {
    throw new Error("tool definitions must be objects");
  }
  const name = requiredText(tool.name, "tool.name");
  const description = requiredText(tool.description, "tool.description");
  if (!tool.inputSchema || typeof tool.inputSchema !== "object" || Array.isArray(tool.inputSchema)) {
    throw new Error(`tool ${name} inputSchema must be an object`);
  }
  return { name, description, inputSchema: tool.inputSchema };
}

function sanitizeProviderConfig(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("provider_config must be an object");
  }

  const providerId = requiredText(raw.providerId, "provider_config.providerId");
  if (!ALLOWED_PROVIDER_IDS.has(providerId)) {
    throw new Error(`provider ${providerId} is not enabled for the LBE Cline transport bridge`);
  }

  const modelId = requiredText(raw.modelId, "provider_config.modelId");
  const allowedKeys = new Set([
    "providerId",
    "routingProviderId",
    "modelId",
    "apiKey",
    "accessToken",
    "baseUrl",
    "headers",
    "timeoutMs",
    "maxInputTokens",
    "maxOutputTokens",
    "temperature",
    "reasoningEffort",
    "thinkingBudgetTokens",
    "thinking",
    "region",
    "apiLine",
    "aws",
    "gcp",
    "azure",
  ]);

  const unexpected = Object.keys(raw).filter((key) => !allowedKeys.has(key));
  if (unexpected.length > 0) {
    throw new Error(`unsupported provider_config fields: ${unexpected.sort().join(", ")}`);
  }

  // Explicitly never accept extensionContext/logger/task/session/workspace data.
  return { ...raw, providerId, modelId };
}

async function readRequest() {
  let raw = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) raw += chunk;
  if (!raw.trim()) throw new Error("bridge request body is empty");
  const request = JSON.parse(raw);
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw new Error("bridge request must be a JSON object");
  }
  return request;
}

function installCancellation() {
  const abort = () => {
    try {
      activeHandler?.abort?.();
    } finally {
      process.exit(130);
    }
  };
  process.once("SIGINT", abort);
  process.once("SIGTERM", abort);
}

async function main() {
  installCancellation();
  const request = await readRequest();
  const providerConfig = sanitizeProviderConfig(request.provider_config);
  const systemPrompt = requiredText(request.system_prompt, "system_prompt");

  if (!Array.isArray(request.messages) || request.messages.length === 0) {
    throw new Error("messages must be a non-empty array");
  }
  const tools = request.tools == null ? [] : request.tools.map(validateTool);

  activeHandler = await createHandlerAsync(providerConfig);
  const stream = activeHandler.createMessage(systemPrompt, request.messages, tools);

  for await (const chunk of stream) {
    // Chunks are emitted unchanged. Python/LBE performs the authoritative P0
    // normalization and rejects semantics it cannot prove.
    process.stdout.write(`${JSON.stringify({ kind: "chunk", chunk })}\n`);
  }

  process.stdout.write(`${JSON.stringify({ kind: "end" })}\n`);
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  fail(message);
});
