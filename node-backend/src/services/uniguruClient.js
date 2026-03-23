import dotenv from "dotenv";

dotenv.config();

const UNIGURU_ASK_URL = process.env.UNIGURU_ASK_URL || "http://127.0.0.1:8000/ask";
const UNIGURU_API_TOKEN = String(process.env.UNIGURU_API_TOKEN || "").trim();
const UNIGURU_DEMO_SERVICE_TOKEN = String(process.env.UNIGURU_DEMO_SERVICE_TOKEN || "uniguru-demo-token").trim();
const RESOLVED_SERVICE_TOKEN = UNIGURU_API_TOKEN || UNIGURU_DEMO_SERVICE_TOKEN;
const REQUEST_TIMEOUT_MS = Number(process.env.UNIGURU_REQUEST_TIMEOUT_MS || 15000);

class UniGuruUpstreamError extends Error {
  constructor(message, status, bodyText) {
    super(message);
    this.name = "UniGuruUpstreamError";
    this.status = status;
    this.bodyText = bodyText;
  }
}

function ensureQuery(query) {
  const normalized = String(query || "").trim();
  if (!normalized) {
    throw new Error("query is required");
  }
  return normalized;
}

function ensureContext(context) {
  if (!context || typeof context !== "object" || Array.isArray(context)) {
    return {};
  }
  return { ...context };
}

export function buildUniGuruAskRequest({ query, caller, context = {}, sessionId = null, allowWeb = false }) {
  const normalizedQuery = ensureQuery(query);
  const normalizedContext = ensureContext(context);
  normalizedContext.caller = String(caller || normalizedContext.caller || "").trim();

  if (!normalizedContext.caller) {
    throw new Error("context.caller is required");
  }

  const payload = {
    query: normalizedQuery,
    context: normalizedContext,
    allow_web: Boolean(allowWeb),
  };

  if (sessionId) {
    payload.session_id = String(sessionId);
  }

  return payload;
}

export async function callUniGuruAsk(payload) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  if (RESOLVED_SERVICE_TOKEN) {
    headers.Authorization = `Bearer ${RESOLVED_SERVICE_TOKEN}`;
    headers["X-Service-Token"] = RESOLVED_SERVICE_TOKEN;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(UNIGURU_ASK_URL, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new UniGuruUpstreamError(`UniGuru /ask error ${response.status}: ${text}`, response.status, text);
    }

    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

export { UNIGURU_ASK_URL, UniGuruUpstreamError };
