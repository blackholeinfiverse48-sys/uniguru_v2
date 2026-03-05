# GRAPH_VALIDATION_REPORT

## Implemented Validation Rules
Code: `uniguru/ontology/graph.py`

1. Single Root Constraint
- Exactly one concept must have `parent_id = null`.
- Violations raise `ValueError("Single root constraint violated...")`.

2. Parent Existence Validation
- Every non-root node must point to an existing parent id.
- Missing parent raises `ValueError("Parent concept missing...")`.

3. Cycle Detection
- Deterministic DFS traversal over graph adjacency.
- Back-edge detection raises `ValueError("Ontology cycle detected...")`.

4. Domain Constraints
- Allowed domains only:
  - `quantum`
  - `jain`
  - `swaminarayan`
  - `gurukul`
  - `core`
- Any out-of-contract domain is rejected.

5. Deterministic Snapshot Gate
- `SnapshotManager.load_snapshot` now validates schema and constructs `OntologyGraph`.
- Invalid graph snapshots are rejected before runtime use.
