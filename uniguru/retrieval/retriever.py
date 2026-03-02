import os
import re
from typing import Dict, Optional, Tuple, Any, List

# Paths for knowledge bases
_MODULE_DIR = os.path.dirname(__file__)
_KB_ROOT = os.path.normpath(os.path.join(_MODULE_DIR, "..", "knowledge"))

KB_PATHS: Dict[str, str] = {
    "quantum": os.path.normpath(os.path.join(_MODULE_DIR, "..", "Quantum_KB")),
    "jain": os.path.normpath(os.path.join(_KB_ROOT, "jain")),
    "swaminarayan": os.path.normpath(os.path.join(_KB_ROOT, "swaminarayan")),
    "gurukul": os.path.normpath(os.path.join(_KB_ROOT, "gurukul")),
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

    def _load_memory(self):
        for kb_name, kb_path in KB_PATHS.items():
            if not os.path.exists(kb_path):
                continue
            for root, _, files in os.walk(kb_path):
                for file_name in files:
                    if not file_name.endswith(".md"):
                        continue
                    full_path = os.path.join(root, file_name)
                    keyword = os.path.splitext(file_name)[0].lower().replace("_", " ")
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.knowledge_map[keyword] = content
                    self.source_map[keyword] = kb_name
                    self.file_map[keyword] = file_name

    def retrieve_multi(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves top N documents matching the query."""
        query_lower = query.lower()
        clean_query = re.sub(r"[^\w\s]", "", query_lower)
        tokens = clean_query.split()

        matches = []
        for keyword, content in self.knowledge_map.items():
            kw_tokens = keyword.split()
            content_lower = content.lower()

            keyword_match = sum(1 for t in kw_tokens if t in tokens)
            content_match = sum(1 for t in tokens if t in content_lower)

            total_match = keyword_match + content_match

            if total_match > 0:
                confidence = total_match / len(tokens) if tokens else 0.0
                matches.append(
                    {
                        "content": content,
                        "confidence": confidence,
                        "keyword": keyword,
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
                "top_confidence": primary.get("confidence", 0.0),
            },
        }


def retrieve_advanced(query: str) -> Dict[str, Any]:
    retriever = AdvancedRetriever()
    results = retriever.retrieve_multi(query)
    return retriever.reason_and_compare(results)


def retrieve_knowledge(query: str) -> Optional[str]:
    result = retrieve_advanced(query)
    return result.get("content") if result.get("decision") == "answer" else None


def retrieve_knowledge_with_trace(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    retriever = AdvancedRetriever()
    results = retriever.retrieve_multi(query)
    result = retriever.reason_and_compare(results)

    if result.get("decision") == "answer" and result.get("content"):
        metadata = result.get("metadata") or {}
        trace = {
            "engine": "AdvancedRetriever_v2",
            "kb_path": _KB_ROOT,
            "match_found": True,
            "confidence": float(metadata.get("top_confidence", 0.0)),
            "kb_file": metadata.get("top_match"),
            "sources_consulted": metadata.get("sources_consulted", []),
        }
        return result.get("content"), trace

    trace = {
        "engine": "AdvancedRetriever_v2",
        "kb_path": _KB_ROOT,
        "match_found": False,
        "confidence": 0.0,
        "kb_file": None,
        "sources_consulted": [],
    }
    return None, trace
