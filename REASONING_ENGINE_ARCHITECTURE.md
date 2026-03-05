# REASONING_ENGINE_ARCHITECTURE

## Overview
UniGuru now includes deterministic ontology reasoning modules under `uniguru/reasoning/`:
- `concept_resolver.py`
- `graph_reasoner.py`
- `reasoning_trace.py`

No ML/LLM/embedding/vector behavior is used.

## 1) Concept Resolver
File: `uniguru/reasoning/concept_resolver.py`

Input:
- user query
- retrieval trace

Output (contract):
- `concept_id`
- `canonical_name`
- `domain`
- `truth_level`
- `snapshot_version`
- `snapshot_hash`

Behavior:
- deterministic domain resolution from retrieval trace and strict token map
- deterministic concept match by canonical-name token overlap
- deterministic fallback to domain concept or unresolved concept

## 2) Graph Traversal Reasoning
File: `uniguru/reasoning/graph_reasoner.py`

Behavior:
- builds ontology adjacency deterministically from snapshot
- computes shortest path with BFS
- supports domain-root reasoning path generation

Example chain:
- `Qubit -> Superposition -> Entanglement -> Quantum Algorithms` (when traversing deeper ontology path)

## 3) Reasoning Trace Design
File: `uniguru/reasoning/reasoning_trace.py`

Trace schema:
- `concept_chain`
- `truth_levels`
- `snapshot_version`
- `snapshot_hash`

Example:
```json
{
  "concept_chain": ["quantum root", "qubit"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

## Engine Integration
File: `uniguru/core/engine.py`

Runtime chain:
- Input
- Governance
- Retrieval
- Source Verification
- Concept Resolution
- Ontology Reasoning
- Enforcement
- Response

Reasoning execution condition:
- runs only when retrieval succeeds (`decision=answer` and `retrieval_trace.match_found=true`).
