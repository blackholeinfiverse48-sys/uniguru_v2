# FULL_REASONING_TEST_RESULTS

## Test Execution
Command:
- `PYTHONPATH=. pytest -q tests/ontology_reasoning_test.py`

Result:
- `6 passed`

## Deterministic Reasoning Traces
Snapshot:
- version: `1`
- hash: `e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad`

### 1) Quantum Query
Query:
- `What is a qubit?`

Reasoning trace:
```json
{
  "concept_chain": ["quantum root", "qubit"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

### 2) Jain Query
Query:
- `Explain ahimsa in jainism`

Reasoning trace:
```json
{
  "concept_chain": ["jain root", "ahimsa"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```

### 3) Swaminarayan Query
Query:
- `What is vachanamrut in swaminarayan tradition?`

Reasoning trace:
```json
{
  "concept_chain": ["swaminarayan root", "vachanamrut"],
  "truth_levels": [4, 3],
  "snapshot_version": 1,
  "snapshot_hash": "e7292c6b78cfa8c7fe0008b36f6916879af5b9c78d763a3cbf402d3e3d6895ad"
}
```
