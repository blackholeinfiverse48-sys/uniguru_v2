import re
from typing import List, Dict, Any
import hashlib
from .kosha_validator import KoshaEntry

class KoshaRetriever:
    def __init__(self, entries: List[KoshaEntry]):
        self.entries = entries

    def _detect_domain(self, query: str) -> str:
        """
        Phase 7: Deterministic Keyword-based Domain Authentication. 
        Categorizes query strictly to allowed domains without LLM randomness.
        """
        query_low = query.lower()
        
        domain_weights = {
            "Agriculture": ["crop", "farm", "soil", "nitrogen", "legume", "irrigation", "harvest", "plant", "seed", "rural", "grow"],
            "Urban": ["transit", "density", "city", "metropolitan", "zoning", "traffic", "building", "street", "pollution", "urban"],
            "Water / Rivers": ["river", "runoff", "water", "ocean", "lake", "stream", "basin", "riparian", "aquifer", "marine"],
            "Infrastructure": ["grid", "energy", "load", "electrical", "sensor", "blackout", "bridge", "road", "telecom", "infrastructure"]
        }
        
        scores = {d: 0 for d in domain_weights}
        
        for domain, keywords in domain_weights.items():
            for kw in keywords:
                if kw in query_low:
                    scores[domain] += 1
                    
        # Find dominant domain
        best_domain = max(scores, key=scores.get)
        if scores[best_domain] > 0:
            return best_domain
            
        return None  # No strict domain caught

    def retrieve(self, query: str, domain: str = None) -> tuple[List[Dict[str, Any]], str]:
        """
        Deterministic Keyword + Tag matched retrieval. NO embeddings.
        """
        STOPWORDS = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "if",
            "then",
            "else",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "to",
            "of",
            "in",
            "on",
            "at",
            "by",
            "for",
            "from",
            "as",
            "with",
            "about",
            "into",
            "over",
            "under",
            "who",
            "whom",
            "whose",
            "what",
            "which",
            "when",
            "where",
            "why",
            "how",
        }

        query_normalized = query.lower()
        raw_query_terms = re.findall(r"\b\w+\b", query_normalized)
        query_words = {t for t in raw_query_terms if len(t) > 2 and t not in STOPWORDS}
        
        if not domain:
            domain = self._detect_domain(query)

        scored_entries: List[tuple[float, KoshaEntry]] = []

        for entry in self.entries:
            # Tag match score: proportion of query terms covered by this entry's tags.
            normalized_tags = []
            for tag in entry.tags or []:
                tag_norm = str(tag).lower().strip()
                if len(tag_norm) > 2 and tag_norm not in STOPWORDS:
                    normalized_tags.append(tag_norm)

            matched_tags = [t for t in normalized_tags if t in query_words]
            tag_match_score = 0.0
            if query_words:
                # Value in [0..1]; prevents "the" from dominating tag confidence.
                tag_match_score = len(matched_tags) / len(query_words)

            # Content similarity score: exact word overlap between query and entry.content.
            content_raw_terms = re.findall(r"\b\w+\b", str(entry.content).lower())
            content_words = {t for t in content_raw_terms if len(t) > 2 and t not in STOPWORDS}
            overlap = query_words.intersection(content_words)
            similarity_score = 0.0
            if query_words:
                similarity_score = len(overlap) / len(query_words)

            # Kosha confidence rule: similarity_score OR tag_match_score.
            base_match_score = max(tag_match_score, similarity_score)

            # Optional tiny boost when domain matches (does not hard-filter).
            domain_boost = 0.05 if domain and entry.domain == domain else 0.0
            match_score = min(1.0, base_match_score + domain_boost)

            if match_score > 0 and str(entry.content).strip():
                scored_entries.append((match_score, entry))

        # Sort descending deterministically by match_score, then timestamp, then knowledge_id.
        scored_entries.sort(key=lambda x: (x[0], x[1].timestamp, x[1].knowledge_id), reverse=True)

        signals: List[Dict[str, Any]] = []
        for rank, (match_score, entry) in enumerate(scored_entries):
            signal_id_hash = hashlib.md5(f"{entry.knowledge_id}_{entry.source}_{rank}".encode()).hexdigest()[:12]
            confidence = float(min(1.0, max(match_score, 0.0)))

            signals.append(
                {
                    "signal_id": f"signal_{signal_id_hash}",
                    "type": "string",
                    "content": entry.content,
                    "source": entry.source,  # file name only
                    "confidence": confidence,
                    "trace": {
                        "knowledge_id": entry.source,  # file name only
                        "method": "kosha_retrieval",
                    },
                }
            )

        return signals, domain
