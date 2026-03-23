function stripVerificationPrefix(answer) {
  if (!answer) {
    return "";
  }
  const patterns = [
    /^Based on verified source:[^\n]*\n\n/i,
    /^This information is partially verified from:[^\n]*\n\n/i,
    /^Verification status:[^\n]*\n\n/i,
  ];
  let text = String(answer);
  for (const pattern of patterns) {
    text = text.replace(pattern, "");
  }
  return text;
}

function compactKnowledgeAnswer(answer) {
  const noPrefix = stripVerificationPrefix(answer)
    .replace(/^UniGuru Deterministic Knowledge Retrieval:\s*/i, "")
    .replace(/\r/g, "");
  const lines = noPrefix
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length <= 12 && noPrefix.length <= 1200) {
    return noPrefix.trim();
  }
  const preview = lines.slice(0, 8).join("\n");
  return `${preview}\n\n[Truncated for chat view. Full answer is available in raw_answer.]`;
}

function buildIntegrationNotes(response) {
  const notes = [];
  const route = response?.routing?.route;
  const reason = String(response?.reason || "");
  if (route === "ROUTE_LLM" && reason.includes("UNIGURU_LLM_URL")) {
    notes.push("LLM fallback route selected, but UNIGURU_LLM_URL is not configured.");
  }
  if (response?.verification_status === "UNVERIFIED") {
    notes.push("Response is UNVERIFIED; consumer should show disclaimer.");
  }
  return notes;
}

export function buildSafeMiddlewareFallback({ query, reason, route = "ROUTE_LLM" }) {
  const normalizedQuery = String(query || "").trim();
  const lower = normalizedQuery.toLowerCase();
  let body = "Please ask a specific question and I will explain step by step.";
  if (lower.includes("joke")) {
    body = "Here is one: Why did the function return early? It had a callback.";
  } else if (lower.includes("news") || lower.includes("current") || lower.includes("latest")) {
    body = "In demo safety mode I cannot fetch live feeds, but I can provide a general overview framework.";
  } else if (normalizedQuery) {
    body = `${normalizedQuery} can be explained through definition, context, and examples.`;
  }
  return {
    decision: "answer",
    answer: `I am still learning this topic, but here is a basic explanation... ${body}`,
    reason: reason || "Node middleware safe fallback activated.",
    verification_status: "UNVERIFIED",
    status_action: "ALLOW_WITH_DISCLAIMER",
    governance_flags: { fallback_mode: true },
    governance_output: {
      allowed: true,
      reason: "Middleware fallback mode active.",
      flags: { router_route: route },
    },
    routing: { route, query_type: "general_llm_query", router_latency_ms: 0 },
  };
}

export function formatEngineResponse(response) {
  if (!response || typeof response !== "object") {
    return response;
  }
  const normalized = { ...response };
  const answer = String(normalized.answer || "");
  const looksLikeKbDump = answer.includes("UniGuru Deterministic Knowledge Retrieval:");
  if (looksLikeKbDump) {
    normalized.raw_answer = answer;
    normalized.answer = compactKnowledgeAnswer(answer);
  }
  const notes = buildIntegrationNotes(normalized);
  if (notes.length > 0) {
    normalized.integration_notes = notes;
  }
  return normalized;
}
