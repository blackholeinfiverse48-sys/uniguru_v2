import os
import re
from typing import Any, Dict, List, Optional, Tuple

from reasoning.concept_resolver import ConceptResolver
from reasoning.graph_reasoner import GraphReasoner

# Paths for knowledge bases
_MODULE_DIR = os.path.dirname(__file__)
_KB_ROOT = os.path.normpath(os.path.join(_MODULE_DIR, "..", "knowledge"))

KB_PATHS: Dict[str, str] = {
    "quantum": os.path.normpath(os.path.join(_KB_ROOT, "quantum")),
    "jain": os.path.normpath(os.path.join(_KB_ROOT, "jain")),
    "swaminarayan": os.path.normpath(os.path.join(_KB_ROOT, "swaminarayan")),
    "gurukul": os.path.normpath(os.path.join(_KB_ROOT, "gurukul")),
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
    "about",
    "for",
    "to",
    "in",
    "on",
    "of",
    "and",
    "or",
    "me",
    "tell",
    "explain",
}


class AdvancedRetriever:
    """
    Multi-source internal KB retriever.
    Only local knowledge paths are used.
    """

    def __init__(self, top_n: int = 3):
        self.top_n = top_n
        self.knowledge_map: Dict[str, str] = {}
        self.source_map: Dict[str, str] = {}
        self.file_map: Dict[str, str] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        for kb_name, kb_path in KB_PATHS.items():
            if not os.path.exists(kb_path):
                continue
            for root, _, files in os.walk(kb_path):
                for file_name in files:
                    if not file_name.endswith(".md"):
                        continue
                    full_path = os.path.join(root, file_name)
                    keyword = os.path.splitext(file_name)[0].lower().replace("_", " ")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except OSError:
                        # Demo-safety mode: unreadable KB files are skipped, not fatal.
                        continue
                    self.knowledge_map[keyword] = content
                    self.source_map[keyword] = kb_name
                    self.file_map[keyword] = file_name

    def retrieve_multi(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves top N documents matching the query."""
        query_lower = query.lower()
        clean_query = re.sub(r"[^\w\s]", "", query_lower)
        tokens = [token for token in clean_query.split() if token and token not in STOPWORDS]
        if not tokens:
            return []

        matches = []
        for keyword, content in self.knowledge_map.items():
            kw_tokens = keyword.split()
            content_lower = content.lower()

            keyword_match = sum(1 for t in kw_tokens if t in tokens)
            content_match = sum(1 for t in tokens if t in content_lower)

            if keyword_match == 0 and content_match < 2:
                continue

            keyword_coverage = keyword_match / len(kw_tokens) if kw_tokens else 0.0
            content_density = min(content_match / len(tokens), 1.0)
            confidence = min((0.7 * keyword_coverage) + (0.3 * content_density), 1.0)
            matches.append(
                {
                    "content": content,
                    "confidence": confidence,
                    "keyword": keyword,
                    "keyword_match_count": keyword_match,
                    "query_token_count": len(tokens),
                    "source": self.source_map.get(keyword, "unknown"),
                    "file": self.file_map.get(keyword, "unknown"),
                }
            )

        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[0 : self.top_n]

    def reason_and_compare(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Structured comparison and conflict detection across local sources."""
        if not results:
            return {"decision": "no_match", "content": None, "reasoning": "No relevant documents found."}

        num_docs = len(results)
        primary = results[0]

        sources_list = [r.get("source", "unknown") for r in results]
        unique_sources = list(set(sources_list))

        reasoning_str = (
            f"Retrieved {num_docs} documents from {len(unique_sources)} internal sources "
            f"({', '.join(unique_sources)})."
        )

        status = "AGREEMENT"
        if num_docs > 1:
            first_len = len(str(primary.get("content", "")))
            for i in range(1, num_docs):
                result = results[i]
                result_content = str(result.get("content", ""))
                if abs(len(result_content) - first_len) > 2000:
                    status = "POTENTIAL_CONTRADICTION"
                    reasoning_str = (
                        f"{reasoning_str} Warning: significant variance in source detail detected."
                    )
                    break

        return {
            "decision": "answer",
            "content": primary.get("content"),
            "verification_status": "VERIFIED" if status == "AGREEMENT" else "PARTIAL",
            "reasoning": reasoning_str,
            "status": status,
            "metadata": {
                "sources_consulted": sources_list,
                "top_match": primary.get("file"),
                "top_keyword": primary.get("keyword"),
                "keyword_match_count": primary.get("keyword_match_count", 0),
                "query_token_count": primary.get("query_token_count", 0),
                "top_confidence": primary.get("confidence", 0.0),
            },
        }


def retrieve_advanced(query: str) -> Dict[str, Any]:
    try:
        retriever = AdvancedRetriever()
        results = retriever.retrieve_multi(query)
        return retriever.reason_and_compare(results)
    except Exception:
        return {"decision": "no_match", "content": None, "reasoning": "Retriever fallback mode activated."}


def retrieve_knowledge(query: str) -> Optional[str]:
    result = retrieve_advanced(query)
    return result.get("content") if result.get("decision") == "answer" else None


def retrieve_knowledge_with_trace(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    try:
        retriever = AdvancedRetriever()
        results = retriever.retrieve_multi(query)
        result = retriever.reason_and_compare(results)
    except Exception:
        trace = {
            "engine": "AdvancedRetriever_v2",
            "kb_path": _KB_ROOT,
            "match_found": False,
            "confidence": 0.0,
            "kb_file": None,
            "sources_consulted": ["retriever_fallback", "ontology_registry", "ontology_graph"],
        }
        return None, trace

    if result.get("decision") == "answer" and result.get("content"):
        metadata = result.get("metadata") or {}
        trace = {
            "engine": "AdvancedRetriever_v2",
            "kb_path": _KB_ROOT,
            "match_found": True,
            "confidence": float(metadata.get("top_confidence", 0.0)),
            "kb_file": metadata.get("top_match"),
            "matched_keyword": metadata.get("top_keyword"),
            "keyword_match_count": int(metadata.get("keyword_match_count", 0)),
            "query_token_count": int(metadata.get("query_token_count", 0)),
            "sources_consulted": metadata.get("sources_consulted", []),
        }
        concept_resolution = ConceptResolver().resolve(query=query, retrieval_trace=trace)
        reasoning_path = GraphReasoner().reasoning_path_from_domain_root(
            concept_id=concept_resolution["concept_id"],
            domain=concept_resolution["domain"],
        )
        trace["ontology_domain"] = concept_resolution["domain"]
        trace["ontology_concept_id"] = concept_resolution["concept_id"]
        trace["ontology_relationship_depth"] = len(reasoning_path)
        trace["ontology_relationship_chain"] = [node["concept_id"] for node in reasoning_path]
        trace["sources_consulted"] = sorted(
            set(list(trace["sources_consulted"]) + ["ontology_registry", "ontology_graph"])
        )
        return result.get("content"), trace

    trace = {
        "engine": "AdvancedRetriever_v2",
        "kb_path": _KB_ROOT,
        "match_found": False,
        "confidence": 0.0,
        "kb_file": None,
        "sources_consulted": ["ontology_registry", "ontology_graph"],
    }
    return None, trace
