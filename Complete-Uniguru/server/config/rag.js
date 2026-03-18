import dotenv from 'dotenv';
dotenv.config();

const UNIGURU_ASK_URL = process.env.UNIGURU_ASK_URL;
const UNIGURU_API_TOKEN = process.env.UNIGURU_API_TOKEN;

if (!UNIGURU_ASK_URL) {
  throw new Error('UNIGURU_ASK_URL is not defined in .env');
}

// Test connection on startup
(async () => {
  try {
    const testRes = await fetch(
      UNIGURU_ASK_URL.replace('/ask', '/health'),
      { method: 'GET' }
    );
    if (testRes.ok) {
      console.log('UniGuru /ask endpoint reachable');
    } else {
      console.warn('UniGuru health check failed:', testRes.status);
    }
  } catch (err) {
    console.warn('Could not reach UniGuru:', err.message);
  }
})();

/**
 * Call TASK14's /ask endpoint - the full pipeline.
 * @param {string} query - The user's message
 * @param {string} sessionId - MongoDB chat._id (for session tracking)
 * @param {Array} context - Optional previous context array
 * @returns {Promise<object>} - Normalised response object
 */
export const getRagAnswer = async (query, sessionId = null, context = []) => {
  const headers = {
    'Content-Type': 'application/json',
    accept: 'application/json',
  };

  if (UNIGURU_API_TOKEN) {
    headers.Authorization = `Bearer ${UNIGURU_API_TOKEN}`;
  }

  const contextPayload = {
    caller: 'gurukul-platform',
  };
  if (Array.isArray(context) && context.length > 0) {
    contextPayload.history = context;
  }

  const body = {
    query,
    session_id: sessionId,
    context: contextPayload,
    allow_web: false,
  };

  const response = await fetch(UNIGURU_ASK_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
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
    retrieved_chunks: result.retrieved_chunks || [],
  };
};

export default { getRagAnswer };
