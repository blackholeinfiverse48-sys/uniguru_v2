from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)

class SovereignRetriever:
    """
    Sovereign Retrieval Engine for UniGuru.
    Operates on the structured index in knowledge/index/
    """
    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "knowledge", "index", "master_index.json")
        )
        self.index: Dict[str, Any] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not os.path.exists(self.index_path):
            logger.warning("KB index not found at %s. Running with empty index.", self.index_path)
            self.index = {}
            return
        try:
            with open(self.index_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                self.index = loaded
                logger.info("Sovereign index loaded with %s keywords.", len(self.index))
                return
            logger.warning("KB index at %s is not a JSON object. Running with empty index.", self.index_path)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load KB index (%s). Running with empty index.", exc)
        self.index = {}

    def _calculate_confidence(self, query: str, keyword: str) -> float:
        """
        Calculates confidence based on keyword coverage in query tokens.
        """
        query_tokens = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        kw_tokens = set(keyword.split())

        if not kw_tokens:
            return 0.0

        matched = kw_tokens.intersection(query_tokens)
        return len(matched) / len(kw_tokens) if len(kw_tokens) > 0 else 0.0

    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Main entry point for retrieval.
        Returns a structured response with source trace.
        """
        query_lower = user_query.lower()
        best_match = None
        highest_confidence = 0.0

        # Greedy multi-word keyword matching
        sorted_keywords = sorted(self.index.keys(), key=len, reverse=True)

        for kw in sorted_keywords:
            if kw in query_lower:
                # Basic confidence: if the keyword is in the query
                # We can also check token overlap
                conf = self._calculate_confidence(user_query, kw)

                # If substring match, we give it a boost if it's the exact phrase
                if kw in query_lower:
                    conf = max(conf, 0.5)  # Minimum 0.5 for exact phrase match

                if conf > highest_confidence:
                    highest_confidence = conf
                    best_match = kw

        if best_match and highest_confidence >= 0.3:
            entry_list = self.index.get(best_match) or []
            entry = entry_list[0] if isinstance(entry_list, list) and entry_list else {}
            content = str(entry.get("content") or "")
            meta = entry.get("metadata") if isinstance(entry, dict) else {}
            if not isinstance(meta, dict):
                meta = {}
            return {
                "answer": content,
                "source_file": meta.get("source"),
                "author": meta.get("author"),
                "publication": meta.get("publication"),
                "confidence_level": round(highest_confidence, 2),
                "verified": bool(content),
            }

        return {
            "answer": "I do not have verified knowledge to answer this question.",
            "source_file": None,
            "confidence_level": 0.0,
            "verified": False,
        }


# Singleton for easy access
_engine = SovereignRetriever()


def retrieve(query: str) -> Dict[str, Any]:
    return _engine.query(query)
