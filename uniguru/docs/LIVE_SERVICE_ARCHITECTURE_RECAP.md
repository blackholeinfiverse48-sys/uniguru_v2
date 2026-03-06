# UniGuru Live Service Architecture Recap

## Query Flow
1. `POST /ask` receives `user_query`, `session_id`, optional `context`, and `allow_web_retrieval`.
2. Request enters `RuleEngine` in deterministic order:
   - safety
   - authority
   - delegation
   - emotional
   - ambiguity
   - local retrieval
   - forward decision
3. For KB answers:
   - retrieval trace is verified by truth verifier
   - ontology concept is resolved
   - reasoning path is generated from ontology graph
   - ontology reference is attached (`concept_id`, `snapshot_version`, `snapshot_hash`, `truth_level`)
4. For forward decisions:
   - if `allow_web_retrieval=false`: unknown response path returns unverified deterministic refusal
   - if `allow_web_retrieval=true`: web retrieval runs, then verification gate decides:
     - `VERIFIED` or `PARTIAL` -> answer allowed with verification prefix
     - `UNVERIFIED` -> blocked with explicit unverified message
5. Output governance runs on every output and blocks authority/action leakage.
6. Enforcement layer seals final response with cryptographic signature and verification status.

## Service Boundaries
- API boundary: `uniguru/service/api.py`
- Orchestration boundary: `uniguru/service/live_service.py`
- Core deterministic reasoning: `uniguru/core/engine.py`
- Ontology backbone: `uniguru/ontology/*`
- Verification and enforcement: `uniguru/verifier/*`, `uniguru/enforcement/*`

