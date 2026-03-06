from fastapi.testclient import TestClient

from uniguru.service.api import app


client = TestClient(app)


def test_bhiv_post_ask_returns_ontology_reference() -> None:
    response = client.post(
        "/ask",
        json={
            "user_query": "What is a qubit?",
            "session_id": "bhiv-integration-1",
            "allow_web_retrieval": False,
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


def test_public_ontology_endpoint_resolves_concept() -> None:
    ask_response = client.post(
        "/ask",
        json={"user_query": "Explain ahimsa", "session_id": "bhiv-integration-2"},
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
