# UniGuru

UniGuru is a demo-safe AI backend stack with deterministic KB routing, LLM fallback, and guaranteed response behavior.

## 3-Step Startup

1. Configure environment values from [`config/env/.env.example`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/config/env/.env.example).
2. Start backend:
   - Windows: `powershell -ExecutionPolicy Bypass -File run/run_backend.ps1`
   - Linux/macOS: `bash run/run_backend.sh`
3. Start node middleware:
   - Windows: `powershell -ExecutionPolicy Bypass -File run/run_node.ps1`
   - Linux/macOS: `bash run/run_node.sh`

## Validate End-to-End

Run:

`python test/run_phase8_validation.py`

Output:

[`demo_logs/phase8_test_outputs.json`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/demo_logs/phase8_test_outputs.json)

Additional failure-injection proof:

`python test/run_demo_safety_proof.py`

Output:

[`demo_logs/demo_safety_proof.json`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/demo_logs/demo_safety_proof.json)

## Canonical Flow

`UI -> Node (/api/v1/chat/query) -> Python (/ask) -> ConversationRouter -> KB or ROUTE_LLM -> Safe fallback`

Safe fallback phrase:

`I am still learning this topic, but here is a basic explanation...`

## Repository Map

- `backend/`: Python FastAPI + UniGuru engine
  - `uniguru/router/`, `uniguru/service/`, `uniguru/core/`, `uniguru/integrations/`
- `node-backend/`: middleware
  - `src/routes/`, `src/services/`, `src/server.js`
- `frontend/`: client app
- `run/`: canonical startup scripts
- `test/`: executable validation scripts
- `tests/`: test index
- `config/`: environment and runtime settings
- `docs/architecture/`: system design docs
- `docs/handover/`: onboarding and failure guides
- `docs/reports/`: evidence and historical reports
