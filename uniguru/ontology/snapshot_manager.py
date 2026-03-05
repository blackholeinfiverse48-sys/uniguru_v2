from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from uniguru.ontology.graph import OntologyGraph, get_frozen_concepts
from uniguru.ontology.schema import Concept, concept_from_dict, concept_to_dict


_MODULE_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = _MODULE_DIR / "snapshots"
SNAPSHOT_V1_PATH = SNAPSHOT_DIR / "snapshot_v1.json"


class SnapshotManager:
    @staticmethod
    def _canonical_json(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True)

    @staticmethod
    def _sorted_concepts(concepts: Iterable[Concept]) -> List[Dict[str, Any]]:
        return [
            concept_to_dict(concept)
            for concept in sorted(concepts, key=lambda item: item.concept_id)
        ]

    def build_snapshot_payload(self, concepts: Iterable[Concept], snapshot_version: int) -> Dict[str, Any]:
        payload = {
            "snapshot_version": snapshot_version,
            "concepts": self._sorted_concepts(concepts),
        }
        payload["snapshot_hash"] = self.hash_payload(payload)
        return payload

    def hash_payload(self, payload: Dict[str, Any]) -> str:
        core = dict(payload)
        core.pop("snapshot_hash", None)
        return hashlib.sha256(self._canonical_json(core).encode("utf-8")).hexdigest()

    def save_snapshot(
        self,
        concepts: Iterable[Concept],
        snapshot_version: int,
        path: Path,
    ) -> Dict[str, Any]:
        payload = self.build_snapshot_payload(concepts=concepts, snapshot_version=snapshot_version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    def load_snapshot(self, path: Path) -> Dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        calculated_hash = self.hash_payload(payload)
        if payload.get("snapshot_hash") != calculated_hash:
            raise ValueError(
                f"Snapshot hash mismatch for {path}: "
                f"stored={payload.get('snapshot_hash')} calculated={calculated_hash}"
            )

        # Validate each concept against frozen schema.
        concepts = [concept_from_dict(concept_row) for concept_row in payload.get("concepts", [])]
        OntologyGraph(concepts)

        return payload

    def create_default_snapshot_v1(self) -> Dict[str, Any]:
        concepts = get_frozen_concepts()
        return self.save_snapshot(concepts=concepts, snapshot_version=1, path=SNAPSHOT_V1_PATH)
