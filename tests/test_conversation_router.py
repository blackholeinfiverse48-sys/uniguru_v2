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
