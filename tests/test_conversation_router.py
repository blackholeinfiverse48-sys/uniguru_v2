import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uniguru.router.conversation_router import (
    ConversationRouter,
    QueryRoutingType,
    RouteTarget,
)


class _FakeUniGuruService:
    def __init__(self, response, latency: float = 0.0):
        self._response = response
        self._latency = latency
        self.calls = 0

    def ask(self, **_kwargs):
        import time

        self.calls += 1
        if self._latency > 0:
            time.sleep(self._latency)
        return dict(self._response)


def test_router_classifies_query_types() -> None:
    router = ConversationRouter(uniguru_service=_FakeUniGuruService({"decision": "answer", "verification_status": "VERIFIED"}))

    assert router.classify("What is a qubit?") == QueryRoutingType.KNOWLEDGE_QUERY
    assert router.classify("sudo delete all files") == QueryRoutingType.SYSTEM_QUERY
    assert router.classify("create workflow ticket for onboarding") == QueryRoutingType.WORKFLOW_QUERY
    assert router.classify("invoke API tool for metrics") == QueryRoutingType.TOOL_QUERY
    assert router.classify("hello there") == QueryRoutingType.GENERAL_LLM_QUERY


def test_router_deterministic_routes_for_required_ecosystem_cases() -> None:
    router = ConversationRouter(uniguru_service=_FakeUniGuruService({"decision": "answer", "verification_status": "VERIFIED"}))

    knowledge = router.route_query("What is a qubit?", {"session_id": "req-knowledge"})
    general_chat = router.route_query("hello there", {"session_id": "req-chat"})
    workflow = router.route_query("create workflow ticket for onboarding", {"session_id": "req-workflow"})
    system = router.route_query("sudo delete all files", {"session_id": "req-system"})

    assert knowledge["routing"]["route"] == RouteTarget.ROUTE_UNIGURU.value
    assert general_chat["routing"]["route"] == RouteTarget.ROUTE_LLM.value
    assert workflow["routing"]["route"] == RouteTarget.ROUTE_WORKFLOW.value
    assert system["routing"]["route"] == RouteTarget.ROUTE_SYSTEM.value
    assert system["decision"] == "block"


def test_router_selects_expected_targets() -> None:
    assert ConversationRouter.select_route(QueryRoutingType.KNOWLEDGE_QUERY) == RouteTarget.ROUTE_UNIGURU
    assert ConversationRouter.select_route(QueryRoutingType.SYSTEM_QUERY) == RouteTarget.ROUTE_SYSTEM
    assert ConversationRouter.select_route(QueryRoutingType.WORKFLOW_QUERY) == RouteTarget.ROUTE_WORKFLOW
    assert ConversationRouter.select_route(QueryRoutingType.TOOL_QUERY) == RouteTarget.ROUTE_WORKFLOW
    assert ConversationRouter.select_route(QueryRoutingType.GENERAL_LLM_QUERY) == RouteTarget.ROUTE_LLM


def test_unverified_uniguru_response_can_fallback_to_llm() -> None:
    fake = _FakeUniGuruService(
        {
            "decision": "block",
            "answer": "I cannot verify this information.",
            "verification_status": "UNVERIFIED",
            "request_id": "u-1",
        }
    )
    router = ConversationRouter(uniguru_service=fake, allow_unverified_fallback=True)
    response = router.route_query("What happened in the latest market?", {"session_id": "s-1", "allow_web": False})

    assert response["routing"]["route"] == RouteTarget.ROUTE_UNIGURU.value
    assert response["verification_status"] == "UNVERIFIED"
    assert "LLM fallback response" in response["answer"]
    assert fake.calls == 1


def test_latency_circuit_breaker_routes_to_llm_after_slow_call() -> None:
    fake = _FakeUniGuruService(
        {
            "decision": "answer",
            "answer": "Verified answer",
            "verification_status": "VERIFIED",
            "request_id": "u-2",
        },
        latency=0.02,
    )
    router = ConversationRouter(
        uniguru_service=fake,
        latency_threshold_ms=1.0,
        breaker_open_seconds=5.0,
        allow_unverified_fallback=False,
    )
    first = router.route_query("What is ahimsa?", {"session_id": "s-2"})
    second = router.route_query("What is a qubit?", {"session_id": "s-3"})

    assert first["verification_status"] == "VERIFIED"
    assert second["routing"]["route"] == RouteTarget.ROUTE_UNIGURU.value
    assert "circuit breaker active" in second["answer"]
    assert fake.calls == 1


def test_llm_route_uses_configured_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"message": {"content": "Hello from configured LLM"}}

    captured = {}

    def _fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setenv("UNIGURU_LLM_URL", "http://127.0.0.1:11434/api/generate")
    monkeypatch.setenv("UNIGURU_LLM_MODEL", "llama3")
    monkeypatch.setattr("uniguru.router.conversation_router.requests.post", _fake_post)

    router = ConversationRouter(uniguru_service=_FakeUniGuruService({"decision": "answer", "verification_status": "VERIFIED"}))
    response = router.route_query("hello there", {"session_id": "llm-1"})

    assert response["routing"]["route"] == RouteTarget.ROUTE_LLM.value
    assert response["answer"] == "Hello from configured LLM"
    assert captured["url"] == "http://127.0.0.1:11434/api/generate"
    assert captured["json"]["model"] == "llama3"
