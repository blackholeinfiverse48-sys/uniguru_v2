# UniGuru Live API Specification

## Endpoint
`POST /ask`

## Request Body
```json
{
  "user_query": "What is a qubit?",
  "session_id": "optional-session-id",
  "context": {
    "caller": "bhiv-system"
  },
  "allow_web_retrieval": false
}
```

## Response Body
```json
{
  "decision": "answer",
  "answer": "Based on verified source: ...",
  "session_id": "optional-session-id",
  "reason": "Knowledge found in local KB and verified.",
  "ontology_reference": {
    "concept_id": "uuid",
    "domain": "quantum",
    "snapshot_version": 1,
    "snapshot_hash": "sha256...",
    "truth_level": 3
  },
  "reasoning_trace": {
    "sources_consulted": ["quantum"],
    "retrieval_confidence": 1.0,
    "ontology_domain": "quantum",
    "verification_status": "VERIFIED",
    "verification_details": "VERIFIED"
  },
  "governance_flags": {
    "authority": false,
    "delegation": false,
    "emotional": false,
    "ambiguity": false,
    "safety": false
  },
  "governance_output": {
    "allowed": true,
    "reason": "Output governance passed.",
    "flags": {
      "output_authority_violation": false
    }
  },
  "verification_status": "VERIFIED",
  "status_action": "ALLOW",
  "enforcement_signature": "sha256...",
  "request_id": "uuid",
  "sealed_at": "2026-03-06T00:00:00Z",
  "latency_ms": 12.4
}
```

## Health Endpoint
`GET /health`

Returns:
```json
{
  "status": "ok",
  "service": "uniguru-live-reasoning"
}
```

