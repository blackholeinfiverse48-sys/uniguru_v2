import os
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Gurukul Backend Integration")

UNIGURU_ASK_URL = os.getenv("UNIGURU_ASK_URL", "http://127.0.0.1:8000/ask")
UNIGURU_API_TOKEN = os.getenv("UNIGURU_API_TOKEN", "").strip()


class GurukulAskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    student_id: str = Field(..., min_length=1, max_length=128)
    session_id: Optional[str] = Field(default=None, max_length=128)
    class_id: Optional[str] = Field(default=None, max_length=128)
    context: Optional[Dict[str, Any]] = None
    allow_web: bool = False


def _headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Caller-Name": "gurukul-platform",
    }
    if UNIGURU_API_TOKEN:
        headers["Authorization"] = f"Bearer {UNIGURU_API_TOKEN}"
    return headers


@app.post("/api/v1/chat/ask")
def ask_uniguru(request: GurukulAskRequest) -> Dict[str, Any]:
    try:
        response = requests.post(
            UNIGURU_ASK_URL,
            json={
                "query": request.query,
                "session_id": request.session_id,
                "allow_web": request.allow_web,
                "context": {
                    **(request.context or {}),
                    "caller": "gurukul-platform",
                    "student_id": request.student_id,
                    "class_id": request.class_id,
                },
            },
            headers=_headers(),
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach UniGuru /ask: {exc}") from exc

    payload = response.json()
    return {
        "success": True,
        "integration": "gurukul-platform",
        "student_id": request.student_id,
        "session_id": request.session_id,
        "answer": payload.get("answer"),
        "verification_status": payload.get("verification_status"),
        "route": (payload.get("routing") or {}).get("route"),
        "uniguru_response": payload,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "gurukul-backend", "uniguru_ask_url": UNIGURU_ASK_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
