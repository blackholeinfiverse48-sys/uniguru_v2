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
        query_normalized = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_normalized))
        
        scored_entries = []
        
        if not domain:
            domain = self._detect_domain(query)
            
        for entry in self.entries:
            # Domain-aware filtering
            if domain and entry.domain != domain:
                continue
                
            # Scoring logic (Deterministic)
            score = 0.0
            
            # Tag match (high weight)
            matched_tags = [tag for tag in entry.tags if tag.lower() in query_normalized]
            if matched_tags:
                score += 0.5 + (0.1 * len(matched_tags))
                
            # Content keyword overlap (exact word matching)
            content_words = set(re.findall(r'\b\w+\b', entry.content.lower()))
            overlap = query_words.intersection(content_words)
            if overlap:
                score += (len(overlap) / max(len(query_words), 1)) * 0.4
                
            if score > 0:
                scored_entries.append((score, entry))
                
        # Sort descending deterministically by score, then timestamp, then knowledge_id
        scored_entries.sort(key=lambda x: (x[0], x[1].timestamp, x[1].knowledge_id), reverse=True)
        
        signals = []
        for rank, (score, entry) in enumerate(scored_entries):
            # Phase 4 Conversion
            sig_id = hashlib.md5(f"{entry.knowledge_id}_{score}".encode()).hexdigest()[:12]
            signal = {
                "signal_id": f"sig_{sig_id}",
                "signal_type": "KOSHA_VERIFIED",
                "content": entry.content,
                "confidence": min(1.0, score * entry.confidence), # Combining retrieval score and baseline entry confidence
                "source": entry.source,
                "trace": {
                    "knowledge_id": entry.knowledge_id,
                    "retrieval_method": "deterministic_keyword_tag_match",
                    "mapped_domain": domain or "global"
                }
            }
            signals.append(signal)
            
        return signals, domain
