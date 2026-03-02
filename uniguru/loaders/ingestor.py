import os
import json
import re
from typing import List, Dict, Any
try:
    from loaders.file_parser import FileParser
except ImportError:
    from uniguru.loaders.file_parser import FileParser


class KnowledgeIngestor:
    """
    Ingests files and builds a keyword-based runtime index.
    Saves artifacts under knowledge/index/.
    """

    def __init__(self, index_dir: str = "knowledge/index"):
        self.index_dir = index_dir
        self.parser = FileParser()
        self.index: Dict[str, List[Dict[str, Any]]] = {}
        self.ingestion_log: List[Dict[str, Any]] = []

        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"[^\w\s]", " ", text.lower())

    def _extract_keywords(self, text: str) -> List[str]:
        words = self._clean_text(text).split()
        return sorted(set(w for w in words if len(w) > 3))

    @staticmethod
    def _extract_frontmatter_value(content: str, key: str) -> str:
        match = re.search(r"---\s*(.*?)\s*---", content, flags=re.DOTALL)
        if not match:
            return ""
        header = match.group(1)
        for line in header.strip().splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            if k.strip().lower() == key.lower():
                return v.strip()
        return ""

    def ingest_directory(self, directory: str, category: str = "general"):
        """Walks through a directory and ingests all supported files."""
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist. Skipping.")
            return

        print(f"Ingesting directory: {directory} (Category: {category})")

        for root, _, files in os.walk(directory):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                result = self.parser.parse(file_path)
                if not result or not result.get("content"):
                    continue

                content = result["content"]
                metadata = result["metadata"]
                metadata["category"] = category
                status = str(
                    metadata.get("verification_status")
                    or self._extract_frontmatter_value(content, "verification_status")
                    or "UNSPECIFIED"
                ).upper()

                if status == "UNSPECIFIED" and category in ["jain", "swaminarayan", "gurukul"]:
                    status = "VERIFIED"
                
                metadata["verification_status"] = status

                base_keyword = os.path.splitext(file_name)[0].lower().replace("_", " ")
                self._add_to_index(base_keyword, content, metadata)

                dynamic_keywords = self._extract_keywords(base_keyword)[:5]
                for keyword in dynamic_keywords:
                    self._add_to_index(keyword, content, metadata)

                self.ingestion_log.append(
                    {
                        "path": metadata.get("path"),
                        "category": category,
                        "verification_status": metadata.get("verification_status"),
                    }
                )

    def _add_to_index(self, keyword: str, content: str, metadata: Dict[str, Any]):
        if keyword not in self.index:
            self.index[keyword] = []

        existing_sources = [entry["metadata"]["path"] for entry in self.index[keyword]]
        if metadata["path"] not in existing_sources:
            self.index[keyword].append({"content": content, "metadata": metadata})

    def _build_runtime_summary(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "documents_total": len(self.ingestion_log),
            "keywords_total": len(self.index),
            "categories": {},
            "verification_status": {},
        }

        for record in self.ingestion_log:
            category = record["category"]
            status = record["verification_status"]
            summary["categories"][category] = summary["categories"].get(category, 0) + 1
            summary["verification_status"][status] = summary["verification_status"].get(status, 0) + 1

        return summary

    def save_index(self):
        """Saves runtime index and ingestion manifest to disk."""
        index_file = os.path.join(self.index_dir, "master_index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

        manifest = {
            "summary": self._build_runtime_summary(),
            "ingestion_log": self.ingestion_log,
        }
        manifest_file = os.path.join(self.index_dir, "runtime_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(
            f"Index saved to {index_file} ({len(self.index)} keywords indexed). "
            f"Manifest saved to {manifest_file}."
        )


if __name__ == "__main__":
    ingestor = KnowledgeIngestor()

    ingestor.ingest_directory("uniguru/Quantum_KB", category="quantum")
    ingestor.ingest_directory("uniguru/knowledge/gurukul", category="gurukul")
    ingestor.ingest_directory("uniguru/knowledge/jain", category="jain")
    ingestor.ingest_directory("uniguru/knowledge/swaminarayan", category="swaminarayan")

    ingestor.save_index()
