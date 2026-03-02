import asyncio
from unittest.mock import Mock

from fastapi import HTTPException

from uniguru.bridge import server as bridge_server
from uniguru.enforcement.enforcement import SovereignEnforcement


def test_verified_response_is_prefixed_and_sealed(monkeypatch):
    decision = {
        "decision": "answer",
        "verification_status": "VERIFIED",
        "data": {
            "response_content": "The seven tattvas are jiva, ajiva, asrava, bandha, samvara, nirjara, moksha.",
            "verification": {"source_name": "Tattvartha Sutra"},
        },
    }

    monkeypatch.setattr(bridge_server.engine, "evaluate", lambda *_args, **_kwargs: decision)
    payload = asyncio.run(
        bridge_server.chat_bridge(
            bridge_server.ChatRequest(message="What are the seven tattvas?")
        )
    )
    assert "enforcement_signature" in payload
    assert payload["status_action"] == "ALLOW"
    assert payload["data"]["response_content"].startswith("Based on verified source:")
    assert bridge_server.enforcer.verify_bridge_seal(payload) is True


def test_forwarded_response_is_partial_with_required_disclaimer(monkeypatch):
    monkeypatch.setattr(
        bridge_server.engine,
        "evaluate",
        lambda *_args, **_kwargs: {"decision": "forward", "data": {"response_content": ""}},
    )

    fake_resp = Mock()
    fake_resp.raise_for_status = Mock()
    fake_resp.json.return_value = {"answer": "Legacy UniGuru answer payload."}

    called = {}

    def _fake_post(url, **kwargs):
        called["url"] = url
        called["kwargs"] = kwargs
        return fake_resp

    monkeypatch.setattr(bridge_server.requests, "post", _fake_post)
    payload = asyncio.run(
        bridge_server.chat_bridge(
            bridge_server.ChatRequest(message="Forward this request")
        )
    )
    assert called["url"] == bridge_server.LEGACY_URL
    assert payload["status_action"] == "ALLOW_WITH_DISCLAIMER"
    assert payload["data"]["response_content"].startswith(
        "This information is partially verified from:"
    )
    assert "enforcement_signature" in payload
    assert bridge_server.enforcer.verify_bridge_seal(payload) is True


def test_missing_or_invalid_seal_blocks_response(monkeypatch):
    decision = {
        "decision": "answer",
        "verification_status": "VERIFIED",
        "data": {"response_content": "Based on verified source: Test\n\ncontent"},
    }
    monkeypatch.setattr(bridge_server.engine, "evaluate", lambda *_args, **_kwargs: decision)
    monkeypatch.setattr(bridge_server.enforcer, "verify_bridge_seal", lambda _response: False)

    try:
        asyncio.run(bridge_server.chat_bridge(bridge_server.ChatRequest(message="test")))
        assert False, "Expected HTTPException for seal failure."
    except HTTPException as exc:
        assert exc.status_code == 500
        assert "Enforcement Seal Violation" in str(exc.detail)


def test_unverified_refusal_exact_text():
    enforcer = SovereignEnforcement()
    decision = {
        "decision": "answer",
        "verification_status": "UNVERIFIED",
        "data": {"response_content": "untrusted data"},
    }
    sealed = enforcer.process_and_seal(decision, "req-refuse-1")
    assert sealed["decision"] == "block"
    assert sealed["data"]["response_content"] == "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."
    assert sealed["verification_prefix"] == "Verification status: UNVERIFIED"
    assert enforcer.verify_bridge_seal(sealed) is True
