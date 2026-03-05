from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pytest

from uniguru.ontology.graph import OntologyGraph
from uniguru.ontology.replay_test import run_replay_validation
from uniguru.ontology.schema import Concept, concept_from_dict
from uniguru.ontology.snapshot_manager import SNAPSHOT_V1_PATH, SnapshotManager
from uniguru.reasoning.concept_resolver import ConceptResolver
from uniguru.reasoning.graph_reasoner import GraphReasoner
from uniguru.reasoning.reasoning_trace import ReasoningTraceGenerator


def _concept_row(
    concept_id: str,
    canonical_name: str,
    parent_id: Optional[str],
    domain: str = "core",
    truth_level: int = 3,
) -> Dict[str, object]:
    return {
        "concept_id": concept_id,
        "canonical_name": canonical_name,
        "parent_id": parent_id,
        "truth_level": truth_level,
        "domain": domain,
        "source_reference": "tests/ontology_reasoning_test.py",
        "snapshot_version": 1,
        "created_at": "2026-03-05T00:00:00Z",
        "immutable": True,
    }


def _concepts(*rows: Dict[str, object]) -> list[Concept]:
    return [concept_from_dict(dict(row)) for row in rows]


def test_graph_single_root_validation() -> None:
    root_a = _concept_row("11111111-1111-4111-8111-111111111111", "Root A", None, "core", 4)
    root_b = _concept_row("22222222-2222-4222-8222-222222222222", "Root B", None, "core", 4)
    with pytest.raises(ValueError, match="Single root constraint violated"):
        OntologyGraph(_concepts(root_a, root_b))


def test_graph_cycle_rejection() -> None:
    root = _concept_row("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "Root", None, "core", 4)
    node_a = _concept_row(
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "Node A",
        "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    )
    node_b = _concept_row(
        "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "Node B",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    )
    with pytest.raises(ValueError, match="Ontology cycle detected"):
        OntologyGraph(_concepts(root, node_a, node_b))


def test_graph_parent_existence_validation() -> None:
    root = _concept_row("12121212-1212-4121-8121-121212121212", "Root", None, "core", 4)
    child = _concept_row(
        "34343434-3434-4343-8343-343434343434",
        "Child",
        "56565656-5656-4565-8565-565656565656",
    )
    with pytest.raises(ValueError, match="Parent concept missing"):
        OntologyGraph(_concepts(root, child))


def test_snapshot_deterministic_hashing() -> None:
    manager = SnapshotManager()
    snapshot = manager.load_snapshot(SNAPSHOT_V1_PATH)

    payload_a = {
        "snapshot_version": snapshot["snapshot_version"],
        "concepts": snapshot["concepts"],
    }
    payload_b = {
        "concepts": snapshot["concepts"],
        "snapshot_version": snapshot["snapshot_version"],
    }

    assert manager.hash_payload(payload_a) == manager.hash_payload(payload_b)


def test_snapshot_replay_integrity() -> None:
    replay = run_replay_validation()
    assert replay["snapshot_path"] == str(Path(SNAPSHOT_V1_PATH))
    assert replay["replay_passed"] is True


def test_reasoning_trace_for_qubit_query() -> None:
    resolver = ConceptResolver()
    reasoner = GraphReasoner()

    resolved = resolver.resolve(
        "What is a qubit?",
        retrieval_trace={
            "match_found": True,
            "confidence": 1.0,
            "sources_consulted": ["quantum"],
            "kb_file": "qubit.md",
        },
    )
    assert resolved["domain"] == "quantum"
    assert resolved["canonical_name"] == "Qubit"

    path = reasoner.reasoning_path_from_domain_root(resolved["concept_id"], resolved["domain"])
    trace = ReasoningTraceGenerator.from_reasoning_path(
        reasoning_path=path,
        snapshot_version=resolved["snapshot_version"],
        snapshot_hash=resolved["snapshot_hash"],
    )

    assert trace["concept_chain"] == ["quantum root", "qubit"]
    assert trace["truth_levels"] == [4, 3]


def test_reasoning_trace_for_jain_query() -> None:
    resolver = ConceptResolver()
    reasoner = GraphReasoner()

    resolved = resolver.resolve(
        "tell me about ahimsa",
        retrieval_trace={
            "match_found": True,
            "confidence": 1.0,
            "sources_consulted": ["jain"],
            "kb_file": "acharanga_sutra.md",
        },
    )
    assert resolved["domain"] == "jain"
    assert resolved["canonical_name"] == "Ahimsa"

    path = reasoner.reasoning_path_from_domain_root(resolved["concept_id"], resolved["domain"])
    trace = ReasoningTraceGenerator.from_reasoning_path(
        reasoning_path=path,
        snapshot_version=resolved["snapshot_version"],
        snapshot_hash=resolved["snapshot_hash"],
    )

    assert trace["concept_chain"] == ["jain root", "ahimsa"]
    assert trace["truth_levels"] == [4, 3]


def test_reasoning_trace_for_swaminarayan_query() -> None:
    resolver = ConceptResolver()
    reasoner = GraphReasoner()

    resolved = resolver.resolve(
        "what is vachanamrut",
        retrieval_trace={
            "match_found": True,
            "confidence": 1.0,
            "sources_consulted": ["swaminarayan"],
            "kb_file": "vachanamrut_core.md",
        },
    )
    assert resolved["domain"] == "swaminarayan"
    assert resolved["canonical_name"] == "Vachanamrut"

    path = reasoner.reasoning_path_from_domain_root(resolved["concept_id"], resolved["domain"])
    trace = ReasoningTraceGenerator.from_reasoning_path(
        reasoning_path=path,
        snapshot_version=resolved["snapshot_version"],
        snapshot_hash=resolved["snapshot_hash"],
    )

    assert trace["concept_chain"] == ["swaminarayan root", "vachanamrut"]
    assert trace["truth_levels"] == [4, 3]
