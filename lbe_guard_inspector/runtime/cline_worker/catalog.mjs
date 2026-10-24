// Read-only export of the provider/model catalog that @cline/llms ships.
// No provider is contacted and no credential is read: this prints catalog data only.
// Owner: LBE runtime (lbe_guard_inspector/provider_catalog.py). LET-44.
import { readFile } from "node:fs/promises";

const llms = await import("@cline/llms");

let version = null;
try {
  const pkg = new URL("./node_modules/@cline/llms/package.json", import.meta.url);
  version = JSON.parse(await readFile(pkg, "utf8")).version ?? null;
} catch {
  version = null;
}

const providers = (await llms.getAllProviders()).map((p) => ({
  id: p.id,
  name: p.name ?? p.id,
  protocol: p.protocol ?? null,
  client: p.client ?? null,
  base_url: p.baseUrl || null,
  key_env: Array.isArray(p.env) ? p.env : [],
  default_model: p.defaultModelId ?? null,
  models_source: p.modelsSourceUrl ?? null,
}));

const generated = llms.getGeneratedProviderModels();
const models = {};
for (const [providerId, entries] of Object.entries(generated)) {
  models[providerId] = Object.entries(entries).map(([id, info]) => ({
    id,
    name: info?.name ?? id,
    context_window: info?.contextWindow ?? null,
    max_tokens: info?.maxTokens ?? null,
    capabilities: Array.isArray(info?.capabilities) ? info.capabilities : [],
    status: info?.status ?? null,
  }));
}

process.stdout.write(JSON.stringify({ source: "@cline/llms", version, providers, models }));
