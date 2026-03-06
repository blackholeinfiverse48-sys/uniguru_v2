# UniGuru Live Service Report

## Architecture
- API layer: FastAPI `/ask` endpoint accepts external calls.
- Orchestration layer: deterministic pipeline coordinator in `LiveUniGuruService`.
- Core reasoning: governance + retrieval + ontology concept resolution + reasoning path.
- Truth and enforcement: verification metadata, output governance hardening, and signed enforcement output.

## Request Flow
1. API request accepted by `/ask`.
2. Governance input validation executed by deterministic rule engine.
3. Local retrieval and source verification executed.
4. Ontology concept resolved and ontology reference attached.
5. Reasoning trace generated (`sources_consulted`, `retrieval_confidence`, `ontology_domain`, `verification_status`).
6. Optional web retrieval executed only when requested and always verification-gated.
7. Governance output hardening validates response text.
8. Enforcement seals final response and returns structured payload.

## Deployment Method
- Start script: `scripts/start_uniguru_service.ps1`
- Service module: `uniguru.service.api:app`
- Launch command: `python -m uvicorn uniguru.service.api:app --host 0.0.0.0 --port 8010`
- Runtime instructions: `uniguru/docs/LIVE_SERVICE_RUNBOOK.md`

