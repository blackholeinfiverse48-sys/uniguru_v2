# KOSHA_GUIDE.md
> Everything about the Kosha layer — what it is, where the data lives, how to add to it.
> Audience: Vijay Dhawan (Core + Contracts) and Vinayak Tiwari (Testing)

---

## What is Kosha?

"Kosha" (कोश) means **treasury** or **storehouse** in Sanskrit. Fitting for a Hindu scripture system.

In technical terms, Kosha is the **structured, hand-curated knowledge layer** that sits alongside the ChromaDB vector store.

**Why does it exist?**

Vector retrieval is probabilistic. For well-known, high-importance questions ("What is the Atman?", "What does the Gita say about action?"), the vector search might not rank the most authoritative passage at the top. Kosha guarantees that for known critical questions, the best curated answer is always available.

Think of it as:
- ChromaDB = the **library** (searches millions of passages by similarity)
- Kosha = the **librarian's personal curated file** (hand-selected answers for important questions)

During retrieval, both are checked. Kosha matches are boosted in confidence and included in the final response context.

---

## Where is Kosha Data Stored?

```
uniguru_v2/
└── kosha/
    ├── dharma.json
    ├── karma.json
    ├── moksha.json
    ├── vedas.json
    ├── upanishads.json
    └── ... (one file per major topic, or grouped)
```

Each file is a valid JSON array of Kosha entries.

---

## Kosha JSON Schema

Each entry in a Kosha JSON file follows this structure:

```json
{
  "id": "kosha_dharma_001",
  "topic": "dharma",
  "tags": ["dharma", "righteousness", "duty", "gita", "vedic"],
  "language": "en",
  "question_variants": [
    "What is dharma?",
    "What does dharma mean?",
    "Define dharma in Hinduism",
    "dharma kya hai",
    "What is one's duty according to the Gita?"
  ],
  "source_text": "Sva-dharme nidhanam shreyah para-dharmo bhayavahah — It is better to perform one's own duty imperfectly than to perform another's duty perfectly. (Bhagavad Gita 3.35)",
  "canonical_answer": "Dharma refers to one's righteous duty — the moral, spiritual, and social obligations that are aligned with one's nature (svabhava) and station in life. The Bhagavad Gita teaches that following one's own dharma (svadharma), even imperfectly, is superior to following the dharma of another.",
  "source_ref": "Bhagavad_Gita_Chapter_3.txt",
  "confidence_weight": 0.95,
  "verified": true,
  "added_by": "Yashika Tirkey",
  "added_on": "2025-09-01"
}
```

### Field-by-Field Explanation

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | YES | Unique ID for this entry. Format: `kosha_{topic}_{number}` |
| `topic` | string | YES | Primary topic name (must match file name for organization) |
| `tags` | array of strings | YES | Semantic tags used for matching at query time. More tags = better recall |
| `language` | string | YES | Language of this entry: `en`, `hi`, `sa`, `ta`, `te`, `bn` |
| `question_variants` | array of strings | YES | Different ways a user might ask this question. At least 3 variants recommended. Multilingual variants welcome. |
| `source_text` | string | YES | The actual scripture passage. Must be verbatim. Include citation (book, chapter, verse). |
| `canonical_answer` | string | YES | The curated, verified answer derived from the source text. |
| `source_ref` | string | YES | Filename or identifier of the source document in the data corpus |
| `confidence_weight` | float | YES | 0.0–1.0. How authoritative this entry is. Verified entries should be 0.90+. |
| `verified` | boolean | YES | Has this been checked against original scripture? Only set `true` if you are certain. |
| `added_by` | string | No | Who created this entry (for accountability) |
| `added_on` | string | No | ISO date when added (YYYY-MM-DD) |

---

## How Tags Affect Retrieval

When a user query comes in, the system:
1. Embeds the query with `multilingual-e5-large`
2. Searches ChromaDB for top-k semantic matches
3. **Also** tokenizes the query and checks all Kosha tags
4. Any Kosha entry whose `tags` overlap significantly with query tokens → considered a Kosha match
5. Kosha matches get their `confidence_weight` applied → boosted in ranking
6. If Kosha match score > ChromaDB top result score → Kosha answer is prioritized in context

**Practical impact:**
- More tags on an entry = more likely to be retrieved
- Wrong tags = false positives (irrelevant Kosha entries appearing)
- Missing tags = entry not retrieved even when it should be

**Tag guidelines:**
- Include the topic word in multiple forms: `dharma`, `dharm`, `dharmic`, `righteousness`, `duty`
- Include Sanskrit, Hindi, and English variants where relevant
- Include related scripture names: `gita`, `bhagavad gita`, `mahabharata`
- Do NOT add tags for topics the entry doesn't actually cover

---

## How to Add a New Kosha Entry

### Step 1 — Identify the question gap
Run a query through the system and notice the answer is poor or wrong. That's your signal a Kosha entry is needed.

### Step 2 — Find the authoritative source text
Look it up in your corpus (`data/` folder) or a verified scripture source. Copy verbatim.

### Step 3 — Write the entry

Open or create the appropriate file in `kosha/`. For example, for a new moksha entry:
```bash
nano kosha/moksha.json
```

Add your entry to the JSON array. Example:
```json
{
  "id": "kosha_moksha_003",
  "topic": "moksha",
  "tags": ["moksha", "liberation", "mukti", "nirvana", "freedom", "enlightenment", "advaita", "vedanta"],
  "language": "en",
  "question_variants": [
    "What is moksha?",
    "How to attain moksha?",
    "moksha kya hai",
    "What is liberation in Hinduism?",
    "What is mukti?"
  ],
  "source_text": "Mukti or moksha is the liberation of the soul from the cycle of birth and death (samsara). The Mandukya Upanishad declares: 'Ayam atma brahma' — This self is Brahman. Recognizing this non-duality is moksha.",
  "canonical_answer": "Moksha (also called mukti) is the ultimate goal of human life in Hindu philosophy — liberation from samsara (the cycle of death and rebirth). It is achieved through self-realization: understanding that the individual self (Atman) is identical to the universal consciousness (Brahman). Different schools offer different paths: jnana (knowledge), bhakti (devotion), karma (action), or raja (meditation).",
  "source_ref": "Mandukya_Upanishad.txt",
  "confidence_weight": 0.92,
  "verified": true,
  "added_by": "Vijay Dhawan",
  "added_on": "2026-05-07"
}
```

### Step 4 — Validate the JSON

```bash
python -c "import json; json.load(open('kosha/moksha.json')); print('Valid JSON')"
```

If it prints "Valid JSON" → you're good. If it throws an error → fix the JSON syntax.

### Step 5 — Restart the backend

The Kosha layer is loaded at startup. You must restart:
```bash
# Stop current server (Ctrl+C), then:
uvicorn main:app --reload --port 8000
```

### Step 6 — Test the new entry

```bash
curl -X POST http://localhost:8000/new_rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is moksha?", "language": "en"}'
```

Check that:
- `confidence` is high (should be near your `confidence_weight`)
- `signals` includes the tags from your entry
- `answer` reflects your `canonical_answer`

---

## Kosha Quality Rules (Do Not Skip)

| Rule | Why |
|---|---|
| Only add entries you can verify against original scripture | Wrong answers at high confidence are worse than no answer |
| Set `"verified": false` if you're uncertain | This flags the entry for review |
| Use at least 5 `question_variants` | Low variants = low recall |
| Always include `source_text` verbatim | It's the evidence chain |
| Keep `id` unique across all files | Duplicate IDs can cause silent overwrite bugs |
| Don't set `confidence_weight` above 0.95 | Leaves room for vector results to compete |

---

## Viewing All Kosha Entries

```bash
# Count total entries
python -c "
import json, os
total = 0
for f in os.listdir('kosha'):
    if f.endswith('.json'):
        data = json.load(open(f'kosha/{f}'))
        total += len(data)
        print(f'{f}: {len(data)} entries')
print(f'Total: {total} entries')
"
```

---

## Real Example — What a Complete Kosha File Looks Like

File: `kosha/karma.json`

```json
[
  {
    "id": "kosha_karma_001",
    "topic": "karma",
    "tags": ["karma", "action", "consequence", "rebirth", "deed", "karmaphala", "sanchita", "prarabdha", "kriyamana"],
    "language": "en",
    "question_variants": [
      "What is karma?",
      "How does karma work?",
      "karma kya hai",
      "What is the law of karma?",
      "Does karma determine rebirth?",
      "What are the types of karma?"
    ],
    "source_text": "Niyatam kuru karma tvam karma jyayo hy akarmanah — Perform your prescribed duty, for action is better than inaction. (Bhagavad Gita 3.8)",
    "canonical_answer": "Karma (कर्म) literally means 'action' or 'deed.' In Hindu philosophy, every action generates a corresponding reaction — known as karmaphala (fruit of action). There are three types: Sanchita karma (accumulated from all past lives), Prarabdha karma (the portion unfolding in this life), and Kriyamana karma (being created by current actions). The Bhagavad Gita teaches nishkama karma — action without attachment to results — as the path to liberation.",
    "source_ref": "Bhagavad_Gita_Chapter_3.txt",
    "confidence_weight": 0.93,
    "verified": true,
    "added_by": "Yashika Tirkey",
    "added_on": "2025-08-15"
  }
]
```
