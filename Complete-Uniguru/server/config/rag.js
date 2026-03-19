import dotenv from 'dotenv';

dotenv.config();

const UNIGURU_ASK_URL = process.env.UNIGURU_ASK_URL;
const UNIGURU_API_TOKEN = process.env.UNIGURU_API_TOKEN;

if (!UNIGURU_ASK_URL) {
  throw new Error('UNIGURU_ASK_URL is not defined in .env');
}

function buildHeaders() {
  const headers = {
    'Content-Type': 'application/json',
    accept: 'application/json'
  };

  if (UNIGURU_API_TOKEN) {
    headers.Authorization = `Bearer ${UNIGURU_API_TOKEN}`;
  }

  return headers;
}

export function buildUniGuruRequest({
  query,
  sessionId = null,
  caller = 'bhiv-assistant',
  allowWeb = false,
  context = {}
}) {
  const normalizedQuery = String(query || '').trim();
  if (!normalizedQuery) {
    throw new Error('query is required');
  }

  return {
    query: normalizedQuery,
    context: {
      ...(context || {}),
      caller
    },
    allow_web: Boolean(allowWeb),
    ...(sessionId ? { session_id: String(sessionId) } : {})
  };
}

/**
 * Calls UniGuru /ask through a standardized bridge payload.
 */
export const getRagAnswer = async ({
  query,
  sessionId = null,
  context = {},
  caller = 'bhiv-assistant',
  allowWeb = false
}) => {
  const body = buildUniGuruRequest({
    query,
    sessionId,
    caller,
    allowWeb,
    context
  });

  const response = await fetch(UNIGURU_ASK_URL, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`UniGuru /ask error ${response.status}: ${errorText}`);
  }

  const result = await response.json();

  return {
    answer: result.answer || 'Sorry, I could not find an answer.',
    decision: result.decision,
    verification_status: result.verification_status,
    routing: result.routing,
    request_id: result.request_id,
    core_alignment: result.core_alignment,
    ontology_reference: result.ontology_reference,
    retrieved_chunks: result.retrieved_chunks || []
  };
};

export const getGurukulAnswer = async ({
  studentQuery,
  studentId = '',
  sessionId = null,
  classId = null,
  context = {}
}) =>
  getRagAnswer({
    query: studentQuery,
    sessionId,
    caller: 'gurukul-platform',
    context: {
      ...(context || {}),
      student_id: studentId || undefined,
      class_id: classId || undefined
    }
  });

export default { getRagAnswer, getGurukulAnswer, buildUniGuruRequest };
