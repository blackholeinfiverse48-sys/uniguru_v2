from __future__ import annotations

import hashlib
import os
import re
import threading
import time
import uuid
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from uniguru.service.live_service import LiveUniGuruService
from uniguru.service.query_classifier import QueryType, classify_query


class QueryRoutingType(str, Enum):
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    SYSTEM_QUERY = "SYSTEM_QUERY"
    WORKFLOW_QUERY = "WORKFLOW_QUERY"
    TOOL_QUERY = "TOOL_QUERY"
    GENERAL_LLM_QUERY = "GENERAL_LLM_QUERY"


class RouteTarget(str, Enum):
    ROUTE_UNIGURU = "ROUTE_UNIGURU"
    ROUTE_LLM = "ROUTE_LLM"
    ROUTE_WORKFLOW = "ROUTE_WORKFLOW"
    ROUTE_SYSTEM = "ROUTE_SYSTEM"


_SYSTEM_PATTERNS = (
    r"\bsudo\b",
    r"\brm\s+-",
    r"\bdel\s+",
    r"\bformat\s+",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bsystemctl\b",
    r"\bpowershell\b",
    r"\bcmd\.exe\b",
)

_WORKFLOW_PATTERNS = (
    r"\bcreate\b.*\b(ticket|task|workflow|incident|approval)\b",
    r"\bupdate\b.*\b(ticket|task|workflow|incident|approval)\b",
    r"\bapprove\b.*\b(request|workflow|task|ticket)\b",
    r"\bschedule\b.*\b(call|meeting|job|workflow|task)\b",
    r"\bstart\b.*\bworkflow\b",
    r"\btrigger\b.*\bworkflow\b",
)

_TOOL_PATTERNS = (
    r"\buse\b.*\btool\b",
    r"\binvoke\b.*\bapi\b",
    r"\bexecute\b.*\bscript\b",
    r"\brun\b.*\b(sql|query|tool)\b",
)

_KNOWLEDGE_PATTERNS = (
    r"^(what|who|when|where|why|how)\b",
    r"\bexplain\b",
    r"\bdefine\b",
    r"\btell me about\b",
    r"\bdifference between\b",
)

_GENERAL_CHAT_PATTERNS = (
    r"^(hi|hello|hey)\b",
    r"\bhow are you\b",
    r"\bwhat's up\b",
    r"\bhow is it going\b",
)

SAFE_FALLBACK_PREFIX = "I am still learning this topic, but here is a basic explanation..."


@dataclass(frozen=True)
class RoutingDecision:
    query_type: QueryRoutingType
    route: RouteTarget


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _LatencyCircuitBreaker:
    def __init__(self, threshold_ms: float, open_seconds: float) -> None:
        self.threshold_ms = threshold_ms
        self.open_seconds = open_seconds
        self._open_until = 0.0
        self._lock = threading.Lock()

    def should_fallback(self) -> bool:
        now = time.monotonic()
        with self._lock:
            return now < self._open_until

    def record_latency(self, latency_ms: float) -> None:
        if latency_ms <= self.threshold_ms:
            return
        with self._lock:
            self._open_until = max(self._open_until, time.monotonic() + self.open_seconds)


class ConversationRouter:
    def __init__(
        self,
        uniguru_service: Optional[LiveUniGuruService] = None,
        latency_threshold_ms: Optional[float] = None,
        breaker_open_seconds: Optional[float] = None,
        allow_unverified_fallback: Optional[bool] = None,
    ) -> None:
        self._service = uniguru_service or LiveUniGuruService()
        threshold = latency_threshold_ms or float(os.getenv("UNIGURU_ROUTER_LATENCY_THRESHOLD_MS", "1200"))
        open_seconds = breaker_open_seconds or float(os.getenv("UNIGURU_ROUTER_CIRCUIT_OPEN_SECONDS", "30"))
        if allow_unverified_fallback is None:
            allow_unverified_fallback = (
                os.getenv("UNIGURU_ROUTER_UNVERIFIED_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}
            )
        self._allow_unverified_fallback = bool(allow_unverified_fallback)
        self._breaker = _LatencyCircuitBreaker(threshold_ms=threshold, open_seconds=open_seconds)
        # Always default to internal demo mode so ROUTE_LLM remains available
        # even when env files are missing in demo/smoke runs.
        self._llm_url = os.getenv("UNIGURU_LLM_URL", "internal://demo-llm").strip()
        self._llm_model = os.getenv("UNIGURU_LLM_MODEL", "demo-safety-llm").strip()
        self._llm_timeout = float(os.getenv("UNIGURU_LLM_TIMEOUT_SECONDS", "20"))

    def llm_status(self) -> Dict[str, Any]:
        configured = bool(self._llm_url)
        internal_demo = self._llm_url.startswith("internal://")
        return {
            "configured": configured,
            "endpoint": self._llm_url or None,
            "model": self._llm_model or None,
            "internal_demo_mode": internal_demo,
            "available": True,  # safety fallback is always available
        }

    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        context_map = dict(context or {})
        query_type = self.classify(query=query, context=context_map)
        target = self.select_route(query_type=query_type)
        session_id = context_map.get("session_id")

        if target == RouteTarget.ROUTE_SYSTEM:
            response = self._build_system_block_response(query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_WORKFLOW:
            response = self._build_workflow_response(query=query, query_type=query_type, session_id=session_id)
        elif target == RouteTarget.ROUTE_LLM:
            response = self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=None,
            )
        else:
            response = self._dispatch_to_uniguru(query=query, context=context_map, query_type=query_type)

        resolved_route = str(response.pop("_resolved_route", target.value))
        routing_latency = (time.perf_counter() - started) * 1000
        response["routing"] = {
            "query_type": query_type.value,
            "route": resolved_route,
            "router_latency_ms": round(routing_latency, 3),
        }
        return response

    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryRoutingType:
        text = query.strip().lower()
        if not text:
            return QueryRoutingType.GENERAL_LLM_QUERY

        if any(re.search(pattern, text) for pattern in _SYSTEM_PATTERNS):
            return QueryRoutingType.SYSTEM_QUERY
        if any(re.search(pattern, text) for pattern in _WORKFLOW_PATTERNS):
            return QueryRoutingType.WORKFLOW_QUERY
        if any(re.search(pattern, text) for pattern in _TOOL_PATTERNS):
            return QueryRoutingType.TOOL_QUERY
        if any(re.search(pattern, text) for pattern in _GENERAL_CHAT_PATTERNS):
            return QueryRoutingType.GENERAL_LLM_QUERY

        upstream_type = classify_query(text)
        if upstream_type in {QueryType.KNOWLEDGE_QUERY, QueryType.CONCEPT_QUERY, QueryType.EXPLANATION_QUERY, QueryType.WEB_LOOKUP}:
            if any(re.search(pattern, text) for pattern in _KNOWLEDGE_PATTERNS) or upstream_type != QueryType.KNOWLEDGE_QUERY:
                return QueryRoutingType.KNOWLEDGE_QUERY
        return QueryRoutingType.GENERAL_LLM_QUERY

    @staticmethod
    def select_route(query_type: QueryRoutingType) -> RouteTarget:
        if query_type == QueryRoutingType.KNOWLEDGE_QUERY:
            return RouteTarget.ROUTE_UNIGURU
        if query_type == QueryRoutingType.SYSTEM_QUERY:
            return RouteTarget.ROUTE_SYSTEM
        if query_type in {QueryRoutingType.WORKFLOW_QUERY, QueryRoutingType.TOOL_QUERY}:
            return RouteTarget.ROUTE_WORKFLOW
        return RouteTarget.ROUTE_LLM

    def _dispatch_to_uniguru(
        self,
        query: str,
        context: Dict[str, Any],
        query_type: QueryRoutingType,
    ) -> Dict[str, Any]:
        session_id = context.get("session_id")
        allow_web = bool(context.get("allow_web", False))
        legacy_type = classify_query(query)
        effective_allow_web = allow_web or legacy_type == QueryType.WEB_LOOKUP

        if self._breaker.should_fallback():
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru latency circuit breaker active. Response delegated to LLM.",
            )

        started = time.perf_counter()
        try:
            response = self._service.ask(
                user_query=query,
                session_id=session_id,
                context=context,
                allow_web_retrieval=effective_allow_web,
            )
        except Exception as exc:
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning=f"UniGuru KB path failed ({exc}). Falling back to conversational mode.",
            )
        latency_ms = (time.perf_counter() - started) * 1000
        self._breaker.record_latency(latency_ms)

        if not str(response.get("answer") or "").strip():
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru KB response was empty. Falling back to conversational mode.",
            )

        verification_status = str(response.get("verification_status") or "UNVERIFIED").upper()
        if verification_status == "UNVERIFIED" and self._allow_unverified_fallback:
            return self._build_llm_response(
                query=query,
                query_type=query_type,
                session_id=session_id,
                warning="UniGuru could not verify this query. This is an LLM fallback response.",
            )
        return response

    def _build_system_block_response(
        self,
        query_type: QueryRoutingType,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        return self._build_router_contract_response(
            decision="block",
            answer="System-level command requests are blocked by BHIV routing policy.",
            reason="ROUTE_SYSTEM policy enforced.",
            query_type=query_type,
            route=RouteTarget.ROUTE_SYSTEM,
            verification_status="UNVERIFIED",
            session_id=session_id,
            governance_allowed=False,
            governance_reason="System command blocked by router policy.",
        )

    def _build_workflow_response(
        self,
        query: str,
        query_type: QueryRoutingType,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        return self._build_router_contract_response(
            decision="answer",
            answer=f"Delegated to workflow engine: {query}",
            reason="ROUTE_WORKFLOW policy applied.",
            query_type=query_type,
            route=RouteTarget.ROUTE_WORKFLOW,
            verification_status="PARTIAL",
            session_id=session_id,
            governance_allowed=True,
            governance_reason="Delegated workflow response.",
        )

    def _build_llm_response(
        self,
        query: str,
        query_type: QueryRoutingType,
        session_id: Optional[str],
        warning: Optional[str],
    ) -> Dict[str, Any]:
        llm_result = self._request_llm(query=query, session_id=session_id)
        answer = llm_result["answer"]
        if warning:
            answer = f"{warning} {answer}"
        return self._build_router_contract_response(
            decision="answer",
            answer=answer,
            reason=llm_result["reason"],
            query_type=query_type,
            route=RouteTarget.ROUTE_LLM,
            verification_status="UNVERIFIED",
            session_id=session_id,
            governance_allowed=True,
            governance_reason=llm_result["governance_reason"],
        )

    def _request_llm(self, query: str, session_id: Optional[str]) -> Dict[str, str]:
        if self._llm_url.startswith("internal://"):
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM served by internal demo mode.",
                "governance_reason": "Delegated to internal safety LLM fallback.",
            }

        if not self._llm_url:
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM selected but UNIGURU_LLM_URL is not configured.",
                "governance_reason": "LLM route unavailable because no endpoint is configured.",
            }

        payload = {
            "model": self._llm_model or None,
            "prompt": query,
            "query": query,
            "input": query,
            "session_id": session_id,
            "stream": False,
        }
        sanitized_payload = {key: value for key, value in payload.items() if value is not None}

        try:
            response = requests.post(self._llm_url, json=sanitized_payload, timeout=self._llm_timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "answer": self._build_local_demo_answer(query),
                "reason": "ROUTE_LLM request to configured endpoint failed.",
                "governance_reason": f"LLM route returned an integration failure: {exc}",
            }

        answer = str(
            data.get("answer")
            or data.get("response")
            or data.get("output")
            or data.get("content")
            or (data.get("message") or {}).get("content")
            or ""
        ).strip()
        if not answer and isinstance(data.get("choices"), list) and data["choices"]:
            answer = str(
                (data["choices"][0].get("message") or {}).get("content")
                or data["choices"][0].get("text")
                or ""
            ).strip()

        if not answer:
            answer = self._build_local_demo_answer(query)

        return {
            "answer": answer,
            "reason": "ROUTE_LLM policy applied via configured LLM endpoint.",
            "governance_reason": "Delegated open-chat response through configured LLM service.",
        }

    @staticmethod
    def _build_local_demo_answer(query: str) -> str:
        text = str(query or "").strip()
        lower = text.lower()
        if "joke" in lower:
            body = "Here is one: Why did the developer go broke? Because they used up all their cache."
        elif any(token in lower for token in ("news", "current", "latest", "happening in the world")):
            body = (
                "In demo mode I do not fetch live internet updates, but a good snapshot usually includes "
                "major world news, economic movement, and local developments from trusted sources."
            )
        elif text:
            body = (
                f"{text} can be understood by starting with the core idea, then examples, and then practical usage."
            )
        else:
            body = "Let us start with the basics and build up step by step."
        return f"{SAFE_FALLBACK_PREFIX} {body}"

    def _build_router_contract_response(
        self,
        decision: str,
        answer: str,
        reason: str,
        query_type: QueryRoutingType,
        route: RouteTarget,
        verification_status: str,
        session_id: Optional[str],
        governance_allowed: bool,
        governance_reason: str,
    ) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        signature_payload = f"{decision}|{answer}|{route.value}|{request_id}"
        signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
        return {
            "decision": decision,
            "answer": answer,
            "session_id": session_id,
            "reason": reason,
            "_resolved_route": route.value,
            "ontology_reference": {
                "concept_id": f"router::{query_type.value.lower()}",
                "domain": "routing",
                "snapshot_version": 0,
                "snapshot_hash": "router-delegated",
                "truth_level": 0,
            },
            "reasoning_trace": {
                "sources_consulted": ["conversation_router"],
                "retrieval_confidence": 0.0,
                "ontology_domain": "routing",
                "verification_status": verification_status,
                "verification_details": f"Delegated via {route.value}",
            },
            "governance_flags": {"safety": not governance_allowed},
            "governance_output": {
                "allowed": governance_allowed,
                "reason": governance_reason,
                "flags": {"router_route": route.value},
            },
            "verification_status": verification_status,
            "status_action": "ALLOW_WITH_DISCLAIMER" if governance_allowed else "REFUSE",
            "enforcement_signature": signature,
            "request_id": request_id,
            "sealed_at": _utc_now_iso(),
            "latency_ms": 0.0,
        }


_DEFAULT_ROUTER = ConversationRouter()


def route_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _DEFAULT_ROUTER.route_query(query=query, context=context)
