"""Deterministic ontology reasoning modules for UniGuru."""

from uniguru.reasoning.concept_resolver import ConceptResolver
from uniguru.reasoning.graph_reasoner import GraphReasoner
from uniguru.reasoning.reasoning_trace import ReasoningTraceGenerator

__all__ = [
    "ConceptResolver",
    "GraphReasoner",
    "ReasoningTraceGenerator",
]
