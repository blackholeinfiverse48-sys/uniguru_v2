from fastapi.testclient import TestClient

from uniguru.service import api as api_module
from uniguru.service.api import app


client = TestClient(app)


def _ask_payload(query: str) -> dict:
    return {"query": query, "context": {"caller": "internal-testing"}}


def test_bhiv_post_ask_returns_ontology_reference() -> None:
    response = client.post(
        "/ask",
        json={
            "user_query": "What is a qubit?",
            "session_id": "bhiv-integration-1",
            "allow_web_retrieval": False,
            "context": {"caller": "internal-testing"},
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert "ontology_reference" in payload
    reference = payload["ontology_reference"]
    assert reference.get("concept_id")
    assert reference.get("snapshot_hash")
    assert isinstance(reference.get("truth_level"), int)
    assert reference.get("domain")


def test_canonical_contract_request_shape_is_accepted() -> None:
    response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "session_id": "bhiv-integration-contract",
            "allow_web": False,
            "context": {"origin": "bhiv-tests", "caller": "internal-testing"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "decision" in payload
    assert "answer" in payload
    assert "ontology_reference" in payload
    assert "verification_status" in payload
    assert "reasoning_trace" in payload
    assert "governance_output" in payload
    assert "enforcement_signature" in payload


def test_malformed_input_is_rejected() -> None:
    response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "unknown_field": "not-allowed",
        },
    )
    assert response.status_code == 422


def test_public_ontology_endpoint_resolves_concept() -> None:
    ask_response = client.post(
        "/ask",
        json={
            "user_query": "Explain ahimsa",
            "session_id": "bhiv-integration-2",
            "context": {"caller": "internal-testing"},
        },
    )
    assert ask_response.status_code == 200
    concept_id = ask_response.json()["ontology_reference"]["concept_id"]

    response = client.get(f"/ontology/concept/{concept_id}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["concept_id"] == concept_id
    assert payload.get("snapshot_hash")
    assert isinstance(payload.get("truth_level"), int)
    assert payload.get("domain")
    assert "immutable" in payload


def test_observability_endpoints_exposed() -> None:
    live = client.get("/health/live")
    root_ready = client.get("/ready")
    ready = client.get("/health/ready")
    metrics = client.get("/metrics")
    dashboard = client.get("/monitoring/dashboard")

    assert live.status_code == 200
    assert root_ready.status_code == 200
    assert ready.status_code == 200
    assert metrics.status_code == 200
    assert dashboard.status_code == 200
    assert "uniguru_requests_total" in metrics.text
    assert "uniguru_requests_per_minute" in metrics.text
    assert "uniguru_verification_success_rate" in metrics.text


def test_rate_limit_is_enforced() -> None:
    original_limit = api_module._RATE_LIMIT_MAX_REQUESTS
    original_window = api_module._RATE_LIMIT_WINDOW_SECONDS
    try:
        api_module._RATE_LIMIT_MAX_REQUESTS = 1
        api_module._RATE_LIMIT_WINDOW_SECONDS = 60
        api_module._RATE_LIMIT_BUCKET.clear()

        first = client.post("/ask", json=_ask_payload("What is a qubit?"))
        second = client.post("/ask", json=_ask_payload("Explain ahimsa"))

        assert first.status_code == 200
        assert second.status_code == 429
    finally:
        api_module._RATE_LIMIT_MAX_REQUESTS = original_limit
        api_module._RATE_LIMIT_WINDOW_SECONDS = original_window
        api_module._RATE_LIMIT_BUCKET.clear()


def test_service_token_auth_can_be_enforced() -> None:
    original_required = api_module._API_AUTH_REQUIRED
    original_tokens = set(api_module._API_TOKENS)
    original_pytest_runtime = api_module._is_pytest_runtime
    try:
        api_module._API_AUTH_REQUIRED = True
        api_module._API_TOKENS = {"test-token"}
        api_module._is_pytest_runtime = lambda: False

        unauthorized = client.post("/ask", json=_ask_payload("What is a qubit?"))
        assert unauthorized.status_code == 200
        unauthorized_payload = unauthorized.json()
        assert unauthorized_payload["verification_status"] == "UNVERIFIED"
        assert "I am still learning this topic" in unauthorized_payload["answer"]

        authorized = client.post(
            "/ask",
            json=_ask_payload("What is a qubit?"),
            headers={"Authorization": "Bearer test-token"},
        )
        assert authorized.status_code == 200
    finally:
        api_module._API_AUTH_REQUIRED = original_required
        api_module._API_TOKENS = original_tokens
        api_module._is_pytest_runtime = original_pytest_runtime


def test_service_token_header_can_be_enforced() -> None:
    original_required = api_module._API_AUTH_REQUIRED
    original_tokens = set(api_module._API_TOKENS)
    original_pytest_runtime = api_module._is_pytest_runtime
    try:
        api_module._API_AUTH_REQUIRED = True
        api_module._API_TOKENS = {"test-token"}
        api_module._is_pytest_runtime = lambda: False

        authorized = client.post(
            "/ask",
            json=_ask_payload("What is a qubit?"),
            headers={"X-Service-Token": "test-token"},
        )
        assert authorized.status_code == 200
    finally:
        api_module._API_AUTH_REQUIRED = original_required
        api_module._API_TOKENS = original_tokens
        api_module._is_pytest_runtime = original_pytest_runtime


def test_metrics_endpoint_requires_token_when_auth_is_enabled() -> None:
    original_required = api_module._API_AUTH_REQUIRED
    original_tokens = set(api_module._API_TOKENS)
    original_pytest_runtime = api_module._is_pytest_runtime
    try:
        api_module._API_AUTH_REQUIRED = True
        api_module._API_TOKENS = {"test-token"}
        api_module._is_pytest_runtime = lambda: False

        unauthorized = client.get("/metrics")
        assert unauthorized.status_code == 401

        authorized = client.get("/metrics", headers={"Authorization": "Bearer test-token"})
        assert authorized.status_code == 200
    finally:
        api_module._API_AUTH_REQUIRED = original_required
        api_module._API_TOKENS = original_tokens
        api_module._is_pytest_runtime = original_pytest_runtime


def test_metrics_reset_endpoint_clears_counters() -> None:
    api_module._reset_metrics()
    first = client.post("/ask", json=_ask_payload("What is a qubit?"))
    assert first.status_code == 200

    before = client.get("/metrics")
    assert "uniguru_ask_requests_total 1" in before.text

    reset = client.post("/metrics/reset")
    assert reset.status_code == 200

    after = client.get("/metrics")
    assert "uniguru_ask_requests_total 0" in after.text


def test_missing_caller_returns_safe_fallback() -> None:
    response = client.post("/ask", json={"query": "What is a qubit?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "UNVERIFIED"
    assert "I am still learning this topic" in payload["answer"]


def test_unknown_caller_returns_safe_fallback() -> None:
    response = client.post("/ask", json={"query": "What is a qubit?", "context": {"caller": "unknown-client"}})
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "UNVERIFIED"
    assert "I am still learning this topic" in payload["answer"]


def test_allowed_header_caller_is_accepted() -> None:
    response = client.post(
        "/ask",
        json={"query": "What is a qubit?"},
        headers={"X-Caller-Name": "internal-testing"},
    )
    assert response.status_code == 200


def test_system_query_is_blocked_by_router_policy() -> None:
    response = client.post(
        "/ask",
        json={"query": "sudo delete all files", "context": {"caller": "internal-testing"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"
    assert payload["routing"]["route"] == "ROUTE_SYSTEM"


def test_workflow_query_is_delegated_to_workflow_route() -> None:
    response = client.post(
        "/ask",
        json={"query": "create workflow ticket for access request", "context": {"caller": "internal-testing"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "answer"
    assert payload["routing"]["route"] == "ROUTE_WORKFLOW"
    assert "Delegated to workflow engine" in payload["answer"]


def test_open_chat_is_delegated_to_llm_route() -> None:
    response = client.post(
        "/ask",
        json={"query": "hello there", "context": {"caller": "internal-testing"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "answer"
    assert payload["routing"]["route"] == "ROUTE_LLM"


def test_router_queue_limit_returns_safe_fallback_when_full() -> None:
    original_limit = api_module._ASK_QUEUE_LIMIT
    original_inflight = api_module._ASK_INFLIGHT
    try:
        api_module._ASK_QUEUE_LIMIT = 0
        api_module._ASK_INFLIGHT = 0

        response = client.post(
            "/ask",
            json={"query": "What is a qubit?", "context": {"caller": "internal-testing"}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "answer"
        assert payload["verification_status"] == "UNVERIFIED"
        assert "I am still learning this topic" in payload["answer"]
    finally:
        api_module._ASK_QUEUE_LIMIT = original_limit
        api_module._ASK_INFLIGHT = original_inflight


def test_language_adapter_metadata_is_present() -> None:
    response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "context": {"caller": "internal-testing", "language": "en"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "language_adapter" in payload
    assert payload["language_adapter"]["source_language"] == "en"


def test_core_alignment_metadata_is_present_and_read_only() -> None:
    response = client.post(
        "/ask",
        json={
            "query": "What is a qubit?",
            "context": {"caller": "internal-testing"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "core_alignment" in payload
    assert payload["core_alignment"]["read_only"] is True


def test_voice_query_routes_transcribed_audio_through_router() -> None:
    class _FakeSTTEngine:
        def transcribe(self, _audio_bytes, *, filename, content_type, hinted_language=None):
            return {
                "text": "What is a qubit?",
                "language": hinted_language or "en",
                "confidence": 0.97,
                "provider": "test-double",
                "metadata": {
                    "audio": {
                        "filename": filename,
                        "content_type": content_type,
                    }
                },
            }

    original_engine = api_module.stt_engine
    api_module.stt_engine = _FakeSTTEngine()
    try:
        response = client.post(
            "/voice/query",
            content=b"RIFF....WAVEfmt ",
            headers={
                "content-type": "audio/wav",
                "X-Caller-Name": "internal-testing",
                "X-Voice-Language": "en",
                "X-Session-Id": "voice-1",
                "X-Audio-Filename": "voice.wav",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["transcription"]["text"] == "What is a qubit?"
        assert payload["routing"]["route"] == "ROUTE_UNIGURU"
        assert payload["language_adapter"]["source_language"] == "en"
    finally:
        api_module.stt_engine = original_engine


def test_voice_query_returns_safe_fallback_when_stt_is_unavailable() -> None:
    class _UnavailableSTTEngine:
        def transcribe(self, *_args, **_kwargs):
            raise api_module.STTUnavailableError("local STT unavailable")

    original_engine = api_module.stt_engine
    api_module.stt_engine = _UnavailableSTTEngine()
    try:
        response = client.post(
            "/voice/query",
            content=b"RIFF....WAVEfmt ",
            headers={
                "content-type": "audio/wav",
                "X-Caller-Name": "internal-testing",
                "X-Audio-Filename": "voice.wav",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "answer"
        assert payload["verification_status"] == "UNVERIFIED"
        assert "I am still learning this topic" in payload["answer"]
    finally:
        api_module.stt_engine = original_engine
