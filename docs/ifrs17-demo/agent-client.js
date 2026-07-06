const AGENT_QUERY_SCHEMA = "ifrs17-agent-query-v1";
const AGENT_RESPONSE_SCHEMA = "ifrs17-agent-response-v1";
const DEFAULT_ENDPOINT_KEY = "ifrs17.agentEndpoint";

export function buildAgentQueryPayload({
  question,
  profile = "ifrs17",
  model = { provider: "ollama", name: "qwen2.5:7b" },
  variant = "bm25_dense",
  topK = 8,
} = {}) {
  const cleanQuestion = String(question || "").trim();
  if (!cleanQuestion) throw new Error("Agent question is required.");

  return {
    schema_version: AGENT_QUERY_SCHEMA,
    profile: String(profile || "ifrs17"),
    model: normalizeModel(model),
    question: cleanQuestion,
    variant,
    top_k: Number(topK) || 8,
  };
}

function normalizeModel(model) {
  if (!model || typeof model !== "object") {
    return { provider: "ollama", name: "qwen2.5:7b" };
  }
  return {
    provider: String(model.provider || "ollama"),
    name: String(model.name || "qwen2.5:7b"),
  };
}

export function validateAgentResponse(rawResponse) {
  if (!rawResponse || typeof rawResponse !== "object") {
    throw new Error("Agent response must be an object.");
  }
  if (rawResponse.schema_version !== AGENT_RESPONSE_SCHEMA) {
    throw new Error(`Unsupported Agent response schema: ${rawResponse.schema_version || "missing"}`);
  }
  if (!String(rawResponse.answer || "").trim()) {
    throw new Error("Agent response answer is required.");
  }

  const contexts = rawResponse.retrieval?.contexts || [];
  const contextRanks = new Set(contexts.map((context) => Number(context.rank)));
  const contextIds = new Set(contexts.map((context) => String(context.id)));
  const citations = Array.isArray(rawResponse.citations) ? rawResponse.citations : [];

  for (const citation of citations) {
    const rank = Number(citation.rank);
    const id = String(citation.id || "");
    if (!contextRanks.has(rank) && !contextIds.has(id)) {
      throw new Error(`Agent citation does not match returned contexts: ${rank || id}`);
    }
  }

  return {
    schemaVersion: rawResponse.schema_version,
    runId: String(rawResponse.run_id || ""),
    profile: rawResponse.profile || "ifrs17",
    answer: String(rawResponse.answer),
    confidence: rawResponse.confidence || "medium",
    citations,
    groundingWarnings: rawResponse.grounding_warnings || [],
    retrieval: rawResponse.retrieval || { contexts: [] },
    model: rawResponse.model || { provider: "unknown", name: "unknown" },
    timings: rawResponse.timings || {},
  };
}

export async function callAgentEndpoint(endpoint, payload, options = {}) {
  const cleanEndpoint = String(endpoint || "").trim();
  if (!cleanEndpoint) throw new Error("Agent endpoint is not configured.");
  const endpointUrl = parseEndpointUrl(cleanEndpoint);
  const pageProtocol = options.pageProtocol ?? globalThis.location?.protocol ?? "";
  if (pageProtocol === "https:" && endpointUrl.protocol !== "https:") {
    throw new Error("HTTPS GitHub Pages requires an HTTPS Agent endpoint.");
  }

  const fetchImpl = options.fetchImpl || fetch;
  const timeoutMs = Number(options.timeoutMs || 90000);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(endpointUrl.href, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Agent endpoint returned HTTP ${response.status}`);
    }
    const body = await response.json();
    return validateAgentResponse(body);
  } finally {
    clearTimeout(timeout);
  }
}

function parseEndpointUrl(endpoint) {
  try {
    return new URL(endpoint);
  } catch {
    throw new Error("Agent endpoint must be an absolute URL.");
  }
}

export function readAgentEndpoint({ location = globalThis.location, storage = globalThis.localStorage } = {}) {
  const fromUrl = new URLSearchParams(location?.search || "").get("agent");
  if (fromUrl) return fromUrl.trim();
  return storage?.getItem(DEFAULT_ENDPOINT_KEY)?.trim() || "";
}

export function saveAgentEndpoint(endpoint, storage = globalThis.localStorage) {
  const cleanEndpoint = String(endpoint || "").trim();
  if (!storage) return cleanEndpoint;
  if (cleanEndpoint) storage.setItem(DEFAULT_ENDPOINT_KEY, cleanEndpoint);
  else storage.removeItem(DEFAULT_ENDPOINT_KEY);
  return cleanEndpoint;
}
