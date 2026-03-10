from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from uniguru.service import api as api_module
from uniguru.service.api import app


def main() -> None:
    client = TestClient(app)
    token = os.getenv("UNIGURU_API_TOKEN", "uniguru-dev-token-2026")
    auth_headers = {"Authorization": f"Bearer {token}"}

    valid_response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "context": {"caller": "internal-testing"},
            "allow_web": False,
            "session_id": "evidence-valid-1",
        },
        headers=auth_headers,
    )

    invalid_response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "unknown_field": "invalid",
        },
    )

    original_limit = api_module._RATE_LIMIT_MAX_REQUESTS
    original_window = api_module._RATE_LIMIT_WINDOW_SECONDS
    try:
        api_module._RATE_LIMIT_MAX_REQUESTS = 1
        api_module._RATE_LIMIT_WINDOW_SECONDS = 60
        api_module._RATE_LIMIT_BUCKET.clear()
        rl_first = client.post(
            "/ask",
            json={"query": "Explain ahimsa", "context": {"caller": "internal-testing"}},
            headers=auth_headers,
        )
        rl_second = client.post(
            "/ask",
            json={"query": "Explain anekantavada", "context": {"caller": "internal-testing"}},
            headers=auth_headers,
        )
    finally:
        api_module._RATE_LIMIT_MAX_REQUESTS = original_limit
        api_module._RATE_LIMIT_WINDOW_SECONDS = original_window
        api_module._RATE_LIMIT_BUCKET.clear()

    health = client.get("/health")
    ready = client.get("/ready")
    metrics = client.get("/metrics", headers=auth_headers)
    dashboard = client.get("/monitoring/dashboard", headers=auth_headers)

    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": {
            "valid_request": {
                "status_code": valid_response.status_code,
                "body": valid_response.json(),
            },
            "invalid_request_rejection": {
                "status_code": invalid_response.status_code,
                "body": invalid_response.json(),
            },
            "rate_limit_enforcement": {
                "first_status_code": rl_first.status_code,
                "second_status_code": rl_second.status_code,
                "second_body": rl_second.json(),
            },
        },
        "metrics_snapshot": metrics.text,
        "health_snapshot": health.json(),
        "ready_snapshot": ready.json(),
        "dashboard_snapshot": dashboard.json(),
        "structured_log_examples": [
            {
                "event": "request_processed",
                "request_id": valid_response.json().get("request_id"),
                "query_type": "concept_query",
                "decision": valid_response.json().get("decision"),
                "verification_status": valid_response.json().get("verification_status"),
                "latency_ms": valid_response.json().get("latency_ms"),
            },
            {
                "event": "invalid_request_rejected",
                "status_code": invalid_response.status_code,
                "detail": invalid_response.json().get("detail"),
            },
            {
                "event": "rate_limit_enforced",
                "status_code": rl_second.status_code,
                "detail": rl_second.json().get("detail"),
            },
        ],
    }

    output_path = Path("demo_logs") / "service_stability_evidence.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
