# API_GUIDE.md
> UniGuru API — Complete Guide for Vijay Dhawan (Core + Contracts)
> Every endpoint, every field, every edge case documented.

---

## Base URL

```
Local:      http://localhost:8000
Production: https://your-deployed-url.com
```

All endpoints use JSON (except health check which returns JSON too).

---

## Authentication

Current version: **No authentication required.** All endpoints are open.

If authentication is added in future, it will use Bearer token in the header:
```
Authorization: Bearer <uniguru_secret_123>
```

---

## Primary Endpoint — POST /new_rag

This is the **only endpoint users interact with**. It handles the full RAG pipeline.

### Request

```
POST /new_rag
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What is dharma according to the Bhagavad Gita?",
  "language": "en",
  "top_k": 5,
  "min_confidence": 0.65
}
```

### Request Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | YES | — | The user's question. Can be in any supported language. |
| `language` | string | No | `"en"` | Hint for response language. Options: `en`, `hi`, `sa`, `ta`, `te`, `bn`. Does not restrict retrieval. |
| `top_k` | integer | No | 5 (env default) | How many scripture chunks to retrieve. Range: 1–20. Higher = more context but slower. |
| `min_confidence` | float | No | 0.65 (env default) | Override the confidence threshold for this request. Below this → fallback. Range: 0.0–1.0. |

---

### Response

**Response 200 — Successful retrieval and generation:**

```json
{
  "answer": "Dharma in the Bhagavad Gita is understood as one's righteous duty — determined by one's nature (svabhava) and station in life. In Chapter 3, verse 35, Krishna teaches: 'Sva-dharme nidhanam shreyah para-dharmo bhayavahah' — it is better to perform one's own duty imperfectly than to perfectly perform another's duty. Dharma encompasses moral, social, and spiritual responsibilities and is considered the foundation of righteous living.",
  "signals": ["dharma", "gita", "svadharma", "duty", "vedic"],
  "confidence": 0.87,
  "sources": [
    {
      "text": "Sva-dharme nidhanam shreyah para-dharmo bhayavahah. Sva-dharme is better even if performed imperfectly...",
      "source": "Bhagavad_Gita_Chapter_3.txt",
      "score": 0.87,
      "chunk_id": "bg_ch3_chunk_042"
    },
    {
      "text": "Niyatam kuru karma tvam karma jyayo hy akarmanah...",
      "source": "Bhagavad_Gita_Chapter_3.txt",
      "score": 0.81,
      "chunk_id": "bg_ch3_chunk_031"
    }
  ],
  "kosha_used": true,
  "kosha_entry_id": "kosha_dharma_001",
  "fallback": false,
  "language_detected": "en",
  "processing_time_ms": 1240
}
```

---

### Response Fields — Explained

| Field | Type | Description |
|---|---|---|
| `answer` | string | The generated answer from the LLM, grounded in retrieved scripture. This is what you show the user. |
| `signals` | array of strings | Semantic signals extracted from the query and retrieved content. Represents detected topics/concepts. Use these for UI tagging, analytics, or routing. |
| `confidence` | float (0.0–1.0) | How confident the retrieval system is in the relevance of results. 0.0 = no match found, 1.0 = perfect match. Score is the highest cosine similarity from ChromaDB, potentially boosted by Kosha weight. |
| `sources` | array of objects | The scripture chunks that were retrieved and used as context for the answer. Each has: `text` (the chunk), `source` (filename), `score` (similarity score), `chunk_id` (identifier). |
| `sources[].text` | string | Verbatim scripture passage used as context |
| `sources[].source` | string | Source file name |
| `sources[].score` | float | Cosine similarity score for this chunk (0.0–1.0) |
| `sources[].chunk_id` | string | Internal chunk identifier |
| `kosha_used` | boolean | Whether a Kosha entry was found and used in generating the answer |
| `kosha_entry_id` | string or null | ID of the Kosha entry used, if `kosha_used` is true |
| `fallback` | boolean | If `true`, the LLM was NOT called. A safe fallback message is returned instead. Happens when `confidence < min_confidence` or Groq API fails. |
| `language_detected` | string | What language the system detected the query to be in |
| `processing_time_ms` | integer | Total time taken for the full pipeline in milliseconds |

---

### What "signals" mean

Signals are extracted semantic tags that represent what the system understood the query to be about.

```json
"signals": ["dharma", "gita", "svadharma", "duty", "vedic"]
```

These come from:
1. Tags on matched Kosha entries
2. Topic extraction from retrieved ChromaDB chunks
3. Keyword detection from the query itself

**How to use signals in your frontend/integration:**
- Display them as topic badges on the answer UI
- Route to different response templates based on signal content
- Log them for analytics ("most-asked topics")
- Filter responses based on signals (e.g. show only Gita-related content)

---

### What "confidence" means

```json
"confidence": 0.87
```

This is a cosine similarity score (0.0–1.0) representing how close the query was to the retrieved scripture content.

| Range | Meaning | What happens |
|---|---|---|
| 0.85–1.0 | Excellent match | Strong, grounded answer |
| 0.70–0.85 | Good match | Reliable answer |
| 0.65–0.70 | Acceptable | Answer returned, but verify sources |
| below 0.65 | Weak match | Fallback triggered |
| 0.0 | No match | Fallback triggered, ChromaDB may be empty |

---

### What "fallback" means and when it triggers

```json
"fallback": true,
"answer": "I wasn't able to find a highly relevant passage in the scriptures for your question. Please try rephrasing, or ask about a specific scripture or concept."
```

Fallback triggers when:
1. `confidence < min_confidence` (default: 0.65)
2. Groq API call fails (key invalid, rate limit, network error)
3. ChromaDB returns no results (collection empty or connection failed)
4. Retrieved chunks are from completely unrelated topics (low score)

**Fallback does NOT mean the system is broken.** It means the system chose not to guess rather than return a hallucinated answer. This is correct behavior.

---

## Secondary Endpoints

### GET /health

Check if the system is running.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "chromadb": "connected",
  "documents": 649983,
  "kosha_entries": 47,
  "model_loaded": true,
  "groq_configured": true
}
```

If `chromadb: "disconnected"` → evidence the ChromaDB store is missing or corrupt.  
If `model_loaded: false` → embedding model failed to load.  
If `groq_configured: false` → `GROQ_API_KEY` not in env.

---

### GET /docs

Interactive Swagger UI. Opens in browser.

```
http://localhost:8000/docs
```

Use this to test any endpoint without writing curl commands.

---

### GET /kosha/topics

Returns a list of all topics covered in the Kosha layer.

```bash
curl http://localhost:8000/kosha/topics
```

Response:
```json
{
  "topics": ["dharma", "karma", "moksha", "atman", "brahman", "vedas", "upanishads", "gita", "yoga"],
  "total_entries": 47
}
```

---

### POST /kosha/lookup

Direct Kosha lookup for a query (bypasses ChromaDB retrieval, only checks Kosha).

```json
{
  "query": "What is atman?",
  "language": "en"
}
```

Response:
```json
{
  "found": true,
  "entry": { ... },
  "match_score": 0.91
}
```

Useful for testing whether a specific Kosha entry is being found.

---

## Full Request/Response Lifecycle (Step-by-Step)

```
1. User sends POST /new_rag with query: "What is karma?"

2. Backend receives request
   → Validates fields
   → Sets top_k and min_confidence from request or env defaults

3. Embed the query:
   → Runs "What is karma?" through multilingual-e5-large
   → Gets 1024-dimensional vector

4. ChromaDB search:
   → Queries uniguru_multilingual collection
   → Finds top-5 chunks by cosine similarity
   → Returns chunks with scores

5. Kosha lookup:
   → Tokenizes "What is karma?"
   → Checks all Kosha tags for overlap
   → Finds kosha_karma_001 (tags include "karma")
   → Score: 0.93 (confidence_weight)

6. Confidence scoring:
   → ChromaDB top score: 0.84
   → Kosha score: 0.93
   → Final confidence: max(0.84, 0.93) = 0.93
   → 0.93 > 0.65 threshold → proceed to LLM

7. Signals extraction:
   → From Kosha tags: ["karma", "action", "consequence", "karmaphala"]
   → Final signals: ["karma", "action", "consequence", "karmaphala"]

8. LLM call (Groq):
   → System prompt: "You are a Hindu scripture expert. Answer based only on the provided context."
   → Context: [kosha canonical answer + top ChromaDB chunks]
   → User: "What is karma?"
   → LLM generates answer

9. Response assembled:
   → answer: LLM output
   → signals: extracted tags
   → confidence: 0.93
   → sources: ChromaDB chunks
   → kosha_used: true
   → fallback: false

10. Response returned to user
```

---

## Error Responses

| HTTP Status | When | What to do |
|---|---|---|
| 400 | `query` field missing or empty | Add `query` field to request body |
| 422 | Invalid field types (e.g. `top_k` as string) | Fix data types in request |
| 500 | Server-side error (ChromaDB, model, Groq) | Check `/health` and server logs |
| 503 | Groq API unavailable | System will fallback — check Groq status at status.groq.com |

---

## Testing the API (Vinayak — Test Cases)

### Test 1 — Basic English Query
```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is dharma?", "language": "en"}'
```
Expected: `fallback: false`, `confidence > 0.70`, answer mentions duty/righteousness.

### Test 2 — Hindi Query
```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "कर्म क्या है?", "language": "hi"}'
```
Expected: `fallback: false`, signals include `karma`, answer is in English (or Hindi if model responds in Hindi).

### Test 3 — Fallback Trigger
```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the best pizza topping?", "language": "en"}'
```
Expected: `fallback: true`, low confidence, safe fallback message.

### Test 4 — Low top_k
```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is moksha?", "language": "en", "top_k": 1}'
```
Expected: Only 1 source in response, answer may be less complete.

### Test 5 — Health Check
```bash
curl http://localhost:8000/health
```
Expected: `status: healthy`, all fields showing connected state.
