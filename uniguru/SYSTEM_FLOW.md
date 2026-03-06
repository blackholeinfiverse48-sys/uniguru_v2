# UniGuru System Flow Documentation

## 1. Execution Chain Diagram

```text
[ USER REQUEST ]
      |
      v
[ LAYER 1: API / INPUT LAYER ]
      | (Sanitization & Schema Validation)
      v
[ LAYER 2: GOVERNANCE PRE-CHECK ] ---> [ BLOCK ] (If "sudo", malicious, etc.)
      | (Safety Invariant Check)
      v
[ LAYER 3: RETRIEVAL LAYER ]
      | (Local KB Match in master_index.json)
      | (Optional: Verified Web Retrieval)
      v
[ LAYER 4: ONTOLOGY RESOLUTION ]
      | (Map result to concept_id & Domain)
      | (Graph Path Reasoning)
      v
[ LAYER 5: TRUTH VERIFICATION ]
      | (Source Audit: VERIFIED/PARTIAL/UNVERIFIED)
      v
[ LAYER 6: ENFORCEMENT LAYER ]
      | (Final Authority Lock & Sealing)
      v
[ LAYER 7: GOVERNANCE POST-AUDIT ] --> [ BLOCK ] (If output leaked authority)
      | (Action/Pattern Check)
      v
[ STRUCTURED REASONING RESPONSE ]
```

## 2. Layer Definitions

### Layer 1 — API / Input Layer
Receives the raw JSON payload (`user_query`). Ensures clean service boundaries and extracts parameters like `allow_web_retrieval`.

### Layer 2 — Governance Layer (Pre-Check)
Scans user input for malicious patterns (e.g., code injection, system commands) and classifies intent.

### Layer 3 — Retrieval Layer
Uses the `KnowledgeRetriever` to pull ground truth from the physical filesystem. If enabled, performs search-and-verify against allowed web domains.

### Layer 4 — Ontology Resolution
Anchors the retrieved data to the UniGuru Ontology Backbone. It identifies the `concept_id`, `version`, and calculates the `reasoning_path` from the domain root.

### Layer 5 — Truth Verification
Assigns a truth level and status to the response. Only `VERIFIED` or `PARTIAL` results are allowed to proceed. `UNVERIFIED` results trigger a fail-closed refusal.

### Layer 6 — Enforcement Layer
The final gatekeeper. It cryptographically binds the decision and ensures the response is sealed with a signature.

### Layer 7 — Output Governance (Post-Audit)
Performs a final audit of the generated string to ensure no system actions or executive authority patterns are leaked to the user.

## 3. Reasoning Trace Components
Every successful response must include:
- **Ontology Reference**: Proof of grounding in the registry.
- **Sources Consulted**: Traceability to physical files or URLs.
- **Confidence Score**: Deterministic overlap calculation.
- **Verification Status**: Clear declaration of truth status.
