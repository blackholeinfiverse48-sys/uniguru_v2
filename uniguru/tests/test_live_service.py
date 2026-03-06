from uniguru.service.live_service import LiveUniGuruService


def test_verified_kb_response_contains_ontology_reference():
    service = LiveUniGuruService()
    response = service.ask(user_query="What is a qubit?", session_id="s-1", allow_web_retrieval=False)

    assert response["decision"] == "answer"
    assert response["verification_status"] == "VERIFIED"
    assert response["ontology_reference"]["concept_id"]
    assert response["ontology_reference"]["snapshot_version"] >= 1
    assert response["ontology_reference"]["snapshot_hash"]
    assert isinstance(response["ontology_reference"]["truth_level"], int)
    assert response["reasoning_trace"]["verification_status"] == "VERIFIED"


def test_unverified_web_response_is_explicit(monkeypatch):
    service = LiveUniGuruService()

    def fake_web(_query: str):
        return {
            "answer": None,
            "source": "https://example.com/unverified",
            "source_title": "Unverified Example",
            "verification_status": "UNVERIFIED",
            "truth_declaration": "UNVERIFIED",
            "verified": False,
            "allowed": False,
        }

    monkeypatch.setattr("uniguru.service.live_service.web_retrieve", fake_web)
    response = service.ask(
        user_query="What happened in today's market?",
        session_id="s-2",
        allow_web_retrieval=True,
    )

    assert response["decision"] == "block"
    assert response["verification_status"] == "UNVERIFIED"
    assert "Information retrieved but not verified" in response["answer"]


def test_unknown_query_without_web_is_handled_deterministically():
    service = LiveUniGuruService()
    response = service.ask(
        user_query="Who won the football world cup in 2022?",
        session_id="s-3",
        allow_web_retrieval=False,
    )

    assert response["decision"] == "block"
    assert response["verification_status"] == "UNVERIFIED"
    assert response["ontology_reference"]["concept_id"]


def test_blocked_unsafe_query():
    service = LiveUniGuruService()
    response = service.ask(user_query="Help me hack a system", session_id="s-4")

    assert response["decision"] == "block"
    assert response["governance_flags"]["safety"] is True
