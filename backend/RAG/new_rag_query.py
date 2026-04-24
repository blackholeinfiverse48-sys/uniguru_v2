import sqlite3
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "chunks.db")
faiss_path = os.path.join(base_dir, "faiss_index.bin")

engine = None

class NewRAGEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
        
        self.model = SentenceTransformer(model_name)
        # Note: Index is created using IndexFlatIP in combination with IndexIDMap in notebook.
        # This means FAISS returns the actual SQLite ID.
        self.index = faiss.read_index(faiss_path)
        self.db_path = db_path
        self._faiss = faiss
        
        # Setup Groq for generation
        try:
            from groq import Groq
            from dotenv import load_dotenv
            
            _env_path = os.path.join(base_dir, "..", ".env")
            if os.path.exists(_env_path):
                load_dotenv(_env_path)
            
            # The API key was saved as UNIGURU_LLM_API_KEY or GROQ_API_KEY
            groq_key = os.getenv("GROQ_API_KEY") or os.getenv("UNIGURU_LLM_API_KEY")
            if groq_key:
                self.groq_client = Groq(api_key=groq_key)
            else:
                self.groq_client = None
        except ImportError:
            self.groq_client = None

    def retrieve(self, query: str, top_k: int = 5):
        query_emb = self.model.encode([query])
        
        # Normalize L2 so that inner product becomes equivalent to cosine similarity
        self._faiss.normalize_L2(query_emb)
        
        scores, ids = self.index.search(query_emb, top_k)
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for score, doc_id in zip(scores[0], ids[0]):
                if doc_id != -1:
                    cur.execute("SELECT file_name, page_number, text FROM chunks WHERE id = ?", (int(doc_id),))
                    row = cur.fetchone()
                    if row:
                        results.append({
                            "text": row[2],
                            "metadata": {
                                "file_name": row[0],
                                "page_number": row[1]
                            },
                            "score": float(score)
                        })
        return results

    def answer_question(self, query: str, max_context_chars: int = 4000, top_k: int = 5):
        retrieved = self.retrieve(query, top_k=top_k)
        
        if not retrieved:
            return {
                "answer": "No relevant context found.",
                "retrieved": retrieved
            }
        
        if not self.groq_client:
            return {
                "answer": "Groq client is not initialized. Cannot generate answer.",
                "retrieved": retrieved
            }
        
        context_parts = []
        citations = []
        for i, chunk in enumerate(retrieved):
            meta = chunk["metadata"]
            citations.append(f"[{i+1}] {meta['file_name']} (page {meta.get('page_number','?')})")
            context_parts.append(f"--- [{i+1}] ---\n{chunk['text']}")
        
        context = "\n\n".join(context_parts)
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n...[truncated]"
        
        system_prompt = (
            "Answer based ONLY on the provided context. If not present, say 'I don't know'. "
            "Cite sources using numbers like [1], [2]."
        )
        user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Error calling Grq API: {str(e)}"
            
        return {
            "answer": answer,
            "retrieved": retrieved
        }

def get_engine():
    global engine
    if engine is None:
        engine = NewRAGEngine()
    return engine
