# SETUP_GUIDE.md
> Step-by-step instructions to run UniGuru from scratch.
> Target: Soham Kotkar — you should be running in under 30 minutes.
> Every "if this fails → do this" case is documented.

---

## Prerequisites

Before starting, verify you have:

| Tool | Minimum Version | How to Check |
|---|---|---|
| Python | 3.9+ (3.10 recommended) | `python --version` |
| pip | Latest | `pip --version` |
| Git | Any | `git --version` |
| 8 GB RAM | Required for embedding model | Check system info |
| Internet access | Required for Groq API | — |
| Groq API key | Free at console.groq.com | — |

> If RAM is limited: the embedding model (`multilingual-e5-large`) is ~2.2 GB. You need at least 6 GB free RAM to load it.

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/blackholeinfiverse48-sys/uniguru_v2.git
cd uniguru_v2
```

**If this fails → reasons:**
- Repo is private → request access from Yashika Tirkey (yashikart on GitHub)
- Git not installed → `sudo apt install git` (Linux) or install from git-scm.com
- SSH key not configured → use HTTPS URL instead of SSH

---

## Step 2 — Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Linux/Mac:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

**You'll know it's working when** your terminal prompt shows `(venv)` at the start.

**If this fails:**
- `python: command not found` → try `python3 -m venv venv` instead
- Permission error on Windows → run terminal as Administrator

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, uvicorn, chromadb, sentence-transformers, groq, python-dotenv, and all other dependencies.

**Expected time:** 3–8 minutes (downloads ~2 GB of packages including PyTorch).

**If this fails:**
- `ERROR: Could not find a version...` → upgrade pip first: `pip install --upgrade pip`
- Slow install → ensure stable internet connection
- Memory error → close other applications to free RAM
- `torch` install fails → install PyTorch manually first:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  ```
  Then re-run `pip install -r requirements.txt`

---

## Step 4 — Create .env File

Create a file named `.env` in the project root (same folder as `main.py`):

```env
# --- REQUIRED ---
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# --- OPTIONAL ---
CHROMA_PERSIST_PATH=./chromadb_store
KOSHA_PATH=./kosha
TOP_K=5
CONFIDENCE_THRESHOLD=0.65
EMBED_MODEL=intfloat/multilingual-e5-large
GROQ_MODEL=llama3-8b-8192
LOG_LEVEL=INFO
```

### Field Explanations

| Variable | Required | What it does |
|---|---|---|
| `GROQ_API_KEY` | YES | API key for Groq LLM. Get free at console.groq.com |
| `CHROMA_PERSIST_PATH` | No | Where ChromaDB is stored on disk. Default: `./chromadb_store` |
| `KOSHA_PATH` | No | Folder containing Kosha JSON files. Default: `./kosha` |
| `TOP_K` | No | How many chunks to retrieve per query. Default: 5 |
| `CONFIDENCE_THRESHOLD` | No | Below this score, fallback triggers. Default: 0.65 |
| `EMBED_MODEL` | No | HuggingFace embedding model name. Don't change unless you re-embed all data. |
| `GROQ_MODEL` | No | Which LLaMA model to use on Groq. `llama3-8b-8192` is fast, `llama3-70b-8192` is better quality. |
| `LOG_LEVEL` | No | Logging verbosity. Options: DEBUG, INFO, WARNING, ERROR |

**How to get a Groq API key:**
1. Go to https://console.groq.com
2. Create a free account
3. Go to "API Keys" section
4. Generate a new key
5. Copy it into your `.env`

---

## Step 5 — Set Up ChromaDB (Vector Store)

You have two options:

### Option A — Download Pre-built ChromaDB (Recommended)

The ChromaDB store with all 649,983 embedded chunks is saved as a zipped dataset on Kaggle.

1. Download the zipped ChromaDB dataset from Kaggle (ask Yashika Tirkey for the dataset link)
2. Unzip it:
   ```bash
   unzip uniguru_chromadb.zip -d ./chromadb_store
   ```
3. Verify the folder `chromadb_store/` exists with files inside

**Why this is recommended:** Re-embedding 649,983 chunks takes 3–6 hours on GPU. You don't want to do this unless you're adding new content.

### Option B — Re-embed Everything (Only if Option A fails)

Only do this if you have GPU access (Kaggle or Colab with GPU runtime):
```bash
python embed_and_index.py
```

This will:
1. Load all 157 source files from `data/`
2. Chunk them into ~500-token passages
3. Embed each chunk with `multilingual-e5-large`
4. Store all embeddings in ChromaDB

**Expected time:** 3–6 hours on GPU, much longer on CPU.

---

## Step 6 — Verify Kosha Layer

```bash
ls kosha/
```

You should see `.json` files. If the folder is empty or missing:
```bash
mkdir -p kosha
```

You can still run the system without Kosha entries — it just won't have the curated knowledge layer. RAG will still work.

---

## Step 7 — Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Loading embedding model: intfloat/multilingual-e5-large
INFO:     Embedding model loaded successfully.
INFO:     Connecting to ChromaDB at ./chromadb_store
INFO:     ChromaDB connected. Collection: uniguru_multilingual (649983 documents)
INFO:     Loading Kosha layer from ./kosha
INFO:     Kosha loaded: XX entries
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**API is live at: http://localhost:8000**

**Docs UI at: http://localhost:8000/docs** (Swagger interactive UI)

---

## If the Backend Won't Start

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: chromadb` | Dependencies not installed | `pip install -r requirements.txt` |
| `GROQ_API_KEY not found` | `.env` missing or wrong path | Create `.env` in project root |
| `Could not connect to ChromaDB` | `chromadb_store/` missing | Download and unzip ChromaDB dataset |
| `CUDA out of memory` | GPU RAM too low for embedding model | Set `CUDA_VISIBLE_DEVICES=""` to force CPU |
| `Port 8000 already in use` | Another process using the port | Change port: `--port 8001` |
| Model download hangs | HuggingFace slow | Pre-download: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large')"` |

---

## Step 8 — Test the System

Run a quick smoke test:

```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is dharma?", "language": "en"}'
```

**Expected response shape:**
```json
{
  "answer": "Dharma in the Bhagavad Gita refers to...",
  "signals": ["dharma", "vedic", "gita"],
  "confidence": 0.82,
  "sources": [
    {
      "text": "Original scripture passage...",
      "source": "Bhagavad_Gita_Chapter_3.txt",
      "score": 0.82
    }
  ],
  "fallback": false,
  "language_detected": "en"
}
```

If you get this → system is fully working.

---

## Step 9 — Frontend Integration (If Applicable)

If there is a separate frontend repo, point it to:
```
API_BASE_URL=http://localhost:8000
```

The primary endpoint is `POST /new_rag`.

---

## Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "chromadb": "connected",
  "documents": 649983,
  "kosha_entries": <number>,
  "model_loaded": true
}
```

---

## Running in Kaggle (Cloud GPU)

If you need to run with GPU for re-embedding:

1. Upload the repo to Kaggle as a dataset
2. Create a new Kaggle notebook
3. Enable GPU (T4 or P100)
4. Mount the repo dataset
5. Install requirements: `!pip install -r /kaggle/input/uniguru_v2/requirements.txt`
6. Run the notebook cells in order

The ChromaDB output from Kaggle should be downloaded and zipped for local use.
