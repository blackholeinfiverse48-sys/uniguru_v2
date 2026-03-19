# UniGuru Live Test Logs

Date: 2026-03-19

Source log files:
- `demo_logs/uniguru_live_activation_logs.json`
- `docs/reports/UNIGURU_LIVE_ACTIVATION_LOGS.json`

## Product Chat Query

- Endpoint: `POST /api/v1/chat/query`
- Input query: `What is a qubit?`
- HTTP status: `200`
- Routing: `ROUTE_UNIGURU`
- Verification status: `VERIFIED`
- Request ID: `cbc3c6bf-334a-46ed-82be-322de17a2f7e`

## Gurukul Student Query

- Endpoint: `POST /api/v1/gurukul/query`
- Input query: `Explain the Pythagorean theorem.`
- Student ID: `STU-1001`
- HTTP status: `200`
- Routing: `ROUTE_UNIGURU`
- Verification status: `UNVERIFIED`
- Status action: `REFUSE`
- Request ID: `3fa74f78-42c4-4bba-bc17-c9b49b0666d3`

## Full Activation Matrix

Scenarios executed:
1. Gurukul student query
2. Product chat query
3. Knowledge query
4. Unsafe query
5. General chat query

Result: `all_passed = true`
