# UniGuru TASK14

Reorganized repository structure for UniGuru intelligence stack:

- `backend/`: Python FastAPI service and intelligence engine
- `frontend/`: React chat UI for `/ask` and `/voice/query`
- `deploy/`: NGINX/certbot/deployment config
- `docs/`: architecture, API docs, deployment docs, reports
- `scripts/`: utility scripts

## Quick Start

1. Backend env: copy `.env.example` and `backend/.env.example` as needed.
2. Run backend tests: `pytest backend/tests -q`
3. Start Node middleware: `cd node-backend && npm install && npm run dev`
4. Frontend dev: `cd frontend && npm install && npm run dev`

## Live Query Flow

`Frontend -> node-backend (/api/v1/chat/query) -> uniguru-api (/ask)`

`Gurukul -> node-backend (/api/v1/gurukul/query) -> uniguru-api (/ask)`
