# Runtime Settings

Canonical runtime settings are environment-driven.

- Backend host/port: `UNIGURU_HOST`, `UNIGURU_PORT`
- Node middleware port: `NODE_BACKEND_PORT`
- Python target for Node: `UNIGURU_ASK_URL`
- Auth mode: `UNIGURU_API_AUTH_REQUIRED`, `UNIGURU_API_TOKEN`, `UNIGURU_API_TOKENS`
- LLM route: `UNIGURU_LLM_URL`, `UNIGURU_LLM_MODEL`, `UNIGURU_LLM_TIMEOUT_SECONDS`
- Safety controls: `UNIGURU_ROUTER_QUEUE_LIMIT`, `UNIGURU_ROUTER_LATENCY_THRESHOLD_MS`, `UNIGURU_ROUTER_CIRCUIT_OPEN_SECONDS`, `UNIGURU_ROUTER_UNVERIFIED_FALLBACK`

Source file for local bootstrap values: [`config/env/.env.example`](/c:/Users/Yass0/OneDrive/Desktop/TASK14/config/env/.env.example)
