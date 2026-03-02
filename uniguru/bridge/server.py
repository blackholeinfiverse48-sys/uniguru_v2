import os
import time
import uuid
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from uniguru.core.engine import RuleEngine
from uniguru.enforcement.enforcement import SovereignEnforcement
from uniguru.bridge.auth import generate_bridge_token
from uniguru.integrations.gurukul.adapter import GurukulIntegrationAdapter, GurukulQueryRequest

app = FastAPI(title="UniGuru Sovereign Bridge")

# Production UniGuru backend endpoint. Can be overridden via env.
PRODUCTION_UNIGURU_URL = os.getenv(
    "UNIGURU_BACKEND_URL",
    os.getenv("LEGACY_URL", "https://api.uniguru.ai/api/v1/chat/new"),
)
LEGACY_URL = PRODUCTION_UNIGURU_URL

BRIDGE_USER_ID = os.getenv("BRIDGE_USER_ID")
BRIDGE_CHATBOT_ID = os.getenv("BRIDGE_CHATBOT_ID")

engine = RuleEngine()
enforcer = SovereignEnforcement()
gurukul_adapter = GurukulIntegrationAdapter(engine=engine)


class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    query: Optional[str] = None
    session_id: Optional[str] = None
    source: str = "bridge_v3"


def _extract_answer(production_data: dict) -> str:
    return str(
        production_data.get("answer")
        or (production_data.get("aiResponse") or {}).get("content")
        or (production_data.get("data") or {}).get("response")
        or ""
    )


@app.post("/chat")
async def chat_bridge(request: ChatRequest):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    user_msg = request.message or request.question or request.query

    if not user_msg:
        raise HTTPException(status_code=400, detail="No valid query provided.")

    decision = engine.evaluate(user_msg, {"session_id": request.session_id, "trace_id": trace_id})

    if decision.get("decision") == "forward":
        try:
            token = generate_bridge_token()
            resp = requests.post(
                PRODUCTION_UNIGURU_URL,
                json={
                    "message": user_msg,
                    "session_id": request.session_id,
                    "userId": BRIDGE_USER_ID,
                    "chatbotId": BRIDGE_CHATBOT_ID,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
            )
            resp.raise_for_status()
            production_data = resp.json()

            answer = _extract_answer(production_data)
            if not answer:
                decision = {
                    "decision": "block",
                    "verification_status": "UNVERIFIED",
                    "reason": "Production backend response not verifiable.",
                    "data": {"response_content": ""},
                }
            else:
                decision["legacy_response"] = production_data
                decision["verification_status"] = "PARTIAL"
                decision["data"] = {
                    "response_content": answer,
                    "verification": {
                        "source_name": "Production UniGuru backend",
                        "truth_declaration": "VERIFIED_PARTIAL",
                        "formatted_response": "This information is partially verified from: Production UniGuru backend",
                    },
                }
                decision["forwarded_to"] = PRODUCTION_UNIGURU_URL

        except Exception as e:
            decision = {
                "decision": "block",
                "verification_status": "UNVERIFIED",
                "reason": f"Production backend unavailable: {str(e)}",
                "data": {
                    "response_content": "",
                },
            }

    sealed_response = enforcer.process_and_seal(decision, trace_id)

    if not enforcer.verify_bridge_seal(sealed_response):
        raise HTTPException(status_code=500, detail="Enforcement Seal Violation: Tampering Detected.")

    latency = (time.time() - start_time) * 1000
    sealed_response["latency_ms"] = round(latency, 2)
    sealed_response["trace_id"] = trace_id

    return sealed_response


@app.post("/integrations/gurukul/chat")
async def gurukul_chat(request: GurukulQueryRequest):
    if not request.student_query.strip():
        raise HTTPException(status_code=400, detail="student_query is required.")
    return gurukul_adapter.process_student_query(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bridge_version": "3.0.0",
        "production_target": PRODUCTION_UNIGURU_URL,
        "external_llm_calls": False,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
