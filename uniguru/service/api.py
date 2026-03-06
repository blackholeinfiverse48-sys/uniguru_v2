from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from uniguru.ontology.registry import OntologyRegistry
from uniguru.service.live_service import LiveUniGuruService


class AskRequest(BaseModel):
    user_query: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    allow_web_retrieval: bool = False


app = FastAPI(title="UniGuru Live Reasoning Service", version="1.0.0")
service = LiveUniGuruService()
registry = OntologyRegistry()


@app.post("/ask")
def ask(request: AskRequest) -> Dict[str, Any]:
    query = request.user_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="user_query is required.")
    return service.ask(
        user_query=query,
        session_id=request.session_id,
        context=request.context,
        allow_web_retrieval=request.allow_web_retrieval,
    )


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "uniguru-live-reasoning"}


@app.get("/ontology/concept/{concept_id}")
def ontology_concept(concept_id: str) -> Dict[str, Any]:
    try:
        return registry.get_concept(concept_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
