import json
import urllib.request

from uniguru.integrations.bucket_telemetry import BucketTelemetryClient, TelemetryEvent


def test_bucket_telemetry_includes_required_metadata(monkeypatch):
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setenv("UNIGURU_BUCKET_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("UNIGURU_BUCKET_TELEMETRY_ENDPOINT", "https://bucket.example.local/events")
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    client = BucketTelemetryClient()
    client.emit(
        TelemetryEvent(
            event="knowledge_verified",
            query_hash="abc123",
            route="ROUTE_UNIGURU",
            verification_status="VERIFIED",
            latency=12.3,
            caller="bhiv-assistant",
            session_id="session-1",
            ontology_reference={"concept_id": "quantum::qubit", "domain": "quantum"},
            routing={"route": "ROUTE_UNIGURU", "query_type": "KNOWLEDGE_QUERY"},
            decision="answer",
        )
    )

    assert captured["timeout"] == client.timeout_seconds
    assert captured["body"]["verification_status"] == "VERIFIED"
    assert captured["body"]["ontology_reference"]["concept_id"] == "quantum::qubit"
    assert captured["body"]["routing"]["route"] == "ROUTE_UNIGURU"
    assert captured["body"]["decision"] == "answer"

