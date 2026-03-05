# ONTOLOGY_HARDENING_REPORT

## 1) Immutable Concept Enforcement
Implemented in `uniguru/ontology/drift_detector.py`.

If `immutable=true` in a prior snapshot, the following are now hard-rejected:
- parent change
- canonical name change
- truth downgrade
- domain reassignment

Rejected changes produce:
- `type: immutable_concept_violation`
- `accepted: false`
- `rejected: true`

## 2) Graph Validation Hardening
Implemented in `uniguru/ontology/graph.py` and enforced during snapshot load in `uniguru/ontology/snapshot_manager.py`.

Active constraints:
- exactly one root (`parent_id=null`)
- parent existence for all non-root nodes
- DFS cycle rejection
- allowed domain enforcement: `quantum`, `jain`, `swaminarayan`, `gurukul`, `core`
- duplicate concept id rejection

## 3) Snapshot Determinism
Implemented in `uniguru/ontology/snapshot_manager.py`.

Hashing now uses deterministic canonical encoding:
- `json.dumps(snapshot, sort_keys=True)` (excluding `snapshot_hash` field itself)
- SHA256 over canonical JSON bytes

Current replay snapshot:
- version: `1`
- hash: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`
