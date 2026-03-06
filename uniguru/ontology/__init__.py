"""Deterministic ontology backbone for UniGuru."""

from uniguru.ontology.exceptions import ImmutableConceptViolation, OntologyGraphValidationError
from uniguru.ontology.graph import OntologyGraph, get_frozen_concepts
from uniguru.ontology.registry import OntologyRegistry
from uniguru.ontology.snapshot_manager import SnapshotManager

__all__ = [
    "ImmutableConceptViolation",
    "OntologyGraphValidationError",
    "OntologyGraph",
    "OntologyRegistry",
    "SnapshotManager",
    "get_frozen_concepts",
]
