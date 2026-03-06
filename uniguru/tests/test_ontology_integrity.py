from pathlib import Path

import pytest

from uniguru.ontology.exceptions import ImmutableConceptViolation, OntologyGraphValidationError
from uniguru.ontology.schema import concept_from_dict
from uniguru.ontology.snapshot_manager import SnapshotManager


def _row(
    concept_id: str,
    canonical_name: str,
    parent_id: str | None,
    immutable: bool = True,
) -> dict:
    return {
        "concept_id": concept_id,
        "canonical_name": canonical_name,
        "parent_id": parent_id,
        "truth_level": 3,
        "domain": "core",
        "source_reference": "uniguru/tests/test_ontology_integrity.py",
        "snapshot_version": 1,
        "created_at": "2026-03-06T00:00:00Z",
        "immutable": immutable,
    }


def test_cycle_update_rejected(tmp_path: Path) -> None:
    manager = SnapshotManager()
    root = _row("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "Root", None)
    b = _row("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "B", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    c = _row("cccccccc-cccc-4ccc-8ccc-cccccccccccc", "C", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    manager.save_snapshot(
        concepts=[concept_from_dict(root), concept_from_dict(b), concept_from_dict(c)],
        snapshot_version=1,
        path=tmp_path / "snapshot.json",
    )

    with pytest.raises((OntologyGraphValidationError, ImmutableConceptViolation)):
        manager.mutate_snapshot_concepts(
            path=tmp_path / "snapshot.json",
            updates={
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                    "parent_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
                }
            },
            deletions=[],
            snapshot_version=2,
        )


def test_immutable_modification_rejected(tmp_path: Path) -> None:
    manager = SnapshotManager()
    root = _row("11111111-1111-4111-8111-111111111111", "Root", None)
    child = _row("22222222-2222-4222-8222-222222222222", "Child", "11111111-1111-4111-8111-111111111111")
    manager.save_snapshot(
        concepts=[concept_from_dict(root), concept_from_dict(child)],
        snapshot_version=1,
        path=tmp_path / "snapshot.json",
    )

    with pytest.raises(ImmutableConceptViolation):
        manager.mutate_snapshot_concepts(
            path=tmp_path / "snapshot.json",
            updates={
                "22222222-2222-4222-8222-222222222222": {"canonical_name": "Child Updated"}
            },
            deletions=[],
            snapshot_version=2,
        )
