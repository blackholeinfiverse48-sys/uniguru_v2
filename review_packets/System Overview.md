# SYSTEM_OVERVIEW.md
> UniGuru v2 — Complete System Overview


---

## What Is UniGuru?

UniGuru is a **Multilingual Retrieval-Augmented Generation (RAG) system** for Hindu scriptures and spiritual texts.

In plain language:
- A user asks a question in **any of 6 languages** (Hindi, English, Sanskrit, Tamil, Telugu, Bengali, or others supported)
- The system searches through **649,983 chunks from 157 scripture files** to find relevant passages
- An **LLM (LLaMA via Groq)** reads those passages and generates a clear, grounded answer
- The response includes the **source text**, **confidence score**, and **semantic signals**

It is NOT a chatbot that makes things up. Every answer is grounded in retrieved scripture text. If it can't find relevant content with sufficient confidence, it falls back gracefully rather than hallucinating.

---

## What Does It Cover?

| Content | Description |
|---|---|
| Hindu scriptures | Bhagavad Gita, Upanishads, Vedas, Puranas, Ramayana, Mahabharata |
| Related spiritual texts | Dharmashastra, yoga texts, stotra literature |
| Languages | 6+ languages with multilingual embeddings |
| Total chunks | 649,983 across 157 source files |

---

## System Architecture (No Code — Just Clarity)

```
USER
  |
  | asks a question (any language)
  v
FASTAPI BACKEND  (/new_rag endpoint)
  |
  | 1. Embed the query using multilingual model
  v
multilingual-e5-large (HuggingFace embedding model)
  |
  | 2. Search the vector store
  v
ChromaDB  (collection: uniguru_multilingual)
  |  cosine similarity search
  | returns top-k relevant scripture chunks
  |
  | 3. Also check Kosha (structured JSON knowledge layer)
  v
KOSHA LAYER  (curated JSON entries for known important topics)
  |
  | 4. Combine retrieved chunks + kosha matches
  |    Score confidence
  |    Extract semantic signals (topic tags)
  |
  | 5. If confidence >= threshold → call LLM
  v
GROQ API  (LLaMA model hosted by Groq)
  |
  | 6. LLM generates answer grounded in retrieved text
  |
  | 7. If confidence < threshold → use fallback
  v
RESPONSE to user:
  {
    "answer": "...",
    "signals": ["dharma", "karma", "vedic"],
    "confidence": 0.87,
    "sources": [...],
    "fallback": false
  }
```

---

## The 5 Core Components

### 1. Embedding Model — `intfloat/multilingual-e5-large`
- Converts any text (query or document chunk) into a 1024-dimensional vector
- Works across all supported languages without separate translation
- Loaded once at startup, kept in memory
- This is what makes UniGuru multilingual — the same model handles Hindi, Sanskrit, Tamil, etc.

### 2. ChromaDB Vector Store
- Stores all 649,983 pre-computed embeddings and their text chunks
- Collection name: `uniguru_multilingual`
- Similarity metric: cosine similarity
- Persisted as a directory on disk (or zipped Kaggle dataset in cloud deployment)
- At query time: embed query → find nearest neighbors → return top-k chunks

### 3. Kosha Layer
- "Kosha" = treasury in Sanskrit (intentionally named for the Hindu context)
- A curated JSON knowledge base of hand-verified Q&A pairs and scripture entries
- Complements vector retrieval — catches well-known questions that the vector search may rank poorly
- Lives in `kosha/` directory as `.json` files
- Each entry has: topic tags, language, source text, canonical answer, confidence weight

### 4. Groq LLM (LLaMA)
- Groq provides fast inference for LLaMA models
- The retrieved chunks (context) + user query are sent as a prompt
- LLM generates a grounded, natural-language answer
- If Groq API key is missing or call fails → fallback activates

### 5. FastAPI Backend
- Entry point: `main.py`
- Exposes `/new_rag` as the primary endpoint
- Handles embedding, retrieval, Kosha lookup, confidence scoring, LLM call, and response assembly
- Runs locally on port 8000 (or as configured)

---

## What the System Does NOT Do

- Does NOT answer questions outside Hindu scripture / spiritual content scope
- Does NOT use internet search or live web data
- Does NOT store conversation history between sessions (stateless)
- Does NOT translate the answer — it responds in the language of the source content (mostly)
- Does NOT support real-time document ingestion (adding new scripture requires re-embedding)
- Does NOT have a UI built in — it is a pure API (frontend integration is separate)

---

## Deployment Context

| Environment | Notes |
|---|---|
| Local (development) | Python venv, ChromaDB on disk, Groq API key in `.env` |
| Kaggle (cloud GPU) | Used for embedding 649,983 chunks (free GPU) |
| ChromaDB persistence | Zipped and saved as Kaggle dataset to avoid re-embedding |
| Production target | FastAPI on any server with ChromaDB volume mounted |

---

## Key Numbers to Remember

| Fact | Value |
|---|---|
| Total document chunks | 649,983 |
| Source files indexed | 157 |
| Embedding model | `intfloat/multilingual-e5-large` |
| Vector dimensions | 1024 |
| LLM provider | Groq (LLaMA) |
| Default top-k retrieval | 5 chunks |
| Confidence threshold | 0.65 (below this → fallback) |
| ChromaDB collection | `uniguru_multilingual` |

---

## Ownership After Handover

| Responsibility | Owner |
|---|---|
| Runtime stability | Soham Kotkar |
| API + system contracts | Vijay Dhawan |
| Testing & validation | Vinayak Tiwari |
| Original developer | Yashika Tirkey |
