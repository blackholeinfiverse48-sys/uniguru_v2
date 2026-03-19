# UNIGURU LIVE INTEGRATION REPORT

Date: 2026-03-19

## Scope Delivered

This integration activates UniGuru as a live shared reasoning service for BHIV product chat and Gurukul queries, without changing ontology or core reasoning logic.

## Phase Delivery Summary

### Phase 1: Node to Python bridge
- Added `node-backend` middleware service.
- Standardized Node to UniGuru request payload:
```json
{
  "query": "...",
  "context": {
    "caller": "bhiv-assistant"
  }
}
```
- Optional fields (`session_id`, `allow_web`) are additive only.

### Phase 2: Product chat integration
- Product endpoint implemented in Node:
  - `POST /api/v1/chat/query`
- Frontend chat call now routes through Node middleware:
  - `frontend -> node-backend -> uniguru-api`
- Existing BHIV `Complete-Uniguru/server/config/rag.js` now uses caller-aware standardized forwarding.

### Phase 3: Gurukul integration
- Gurukul endpoint implemented in Node:
  - `POST /api/v1/gurukul/query`
- Gurukul context forwarded with:
```json
{
  "caller": "gurukul-platform",
  "student_id": "..."
}
```
- Existing BHIV controller now includes `sendGurukulQuery` and uses UniGuru forwarding.

### Phase 4: Bucket + core alignment
- Bucket telemetry events now include:
  - `ontology_reference`
  - `verification_status`
  - `routing`
- Metadata emission is done in `backend/uniguru/service/api.py` through `BucketTelemetryClient`.
- Added metadata-focused test coverage.

### Phase 5: Deployment readiness
- `docker-compose.yml` now defines:
  - `uniguru-api`
  - `node-backend`
  - `nginx`
- NGINX routes:
  - `/api/v1/* -> node-backend`
  - `/ask -> uniguru-api`

### Phase 6: Live activation
- Added `scripts/run_live_activation.py` to boot local Python + Node services and run 5 scenario validation:
  1. Gurukul student query
  2. Product chat query
  3. Knowledge query
  4. Unsafe query
  5. General chat query
- Evidence log output:
  - `demo_logs/uniguru_live_activation_logs.json`
  - `docs/reports/UNIGURU_LIVE_ACTIVATION_LOGS.json`

## Architecture Diagram

- [UNIGURU_LIVE_INTEGRATION_ARCHITECTURE.md](/c:/Users/Yass0/OneDrive/Desktop/TASK14/docs/architecture/UNIGURU_LIVE_INTEGRATION_ARCHITECTURE.md)

## Key Files Changed

- Node middleware:
  - `node-backend/src/server.js`
  - `node-backend/src/uniguruClient.js`
- BHIV Node wiring:
  - `Complete-Uniguru/server/config/rag.js`
  - `Complete-Uniguru/server/controller/chatController.js`
- Python telemetry alignment:
  - `backend/uniguru/service/api.py`
  - `backend/uniguru/integrations/bucket_telemetry.py`
- Frontend product routing:
  - `frontend/src/services/uniguru-api.ts`
- Deployment:
  - `docker-compose.yml`
  - `deploy/nginx/conf.d/uniguru.conf`

## Request Flow

### Product query
Frontend sends query to Node:
- `POST /api/v1/chat/query`
Node forwards to UniGuru:
- `POST /ask` with `caller=bhiv-assistant`
UniGuru returns deterministic routed response with verification metadata.

### Gurukul query
Gurukul sends query to Node:
- `POST /api/v1/gurukul/query`
Node forwards to UniGuru:
- `POST /ask` with `caller=gurukul-platform`, `student_id`
UniGuru returns structured response with routing and ontology metadata.

## Deployment Setup

1. Configure env:
   - `UNIGURU_API_TOKEN`
   - `UNIGURU_ALLOWED_CALLERS`
   - bucket telemetry env variables
2. Start stack:
   - `docker compose up --build`
3. Validate:
   - `GET /health` on `uniguru-api`
   - `GET /health` on `node-backend`
   - run `python scripts/run_live_activation.py`
