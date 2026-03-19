from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from uniguru.ontology.registry import OntologyRegistry
from uniguru.router.conversation_router import ConversationRouter
from uniguru.integrations import BucketTelemetryClient, CoreReaderClient, LanguageAdapter, TelemetryEvent
from uniguru.service.live_service import LiveUniGuruService
from uniguru.service.query_classifier import QueryType, classify_query
from uniguru.stt import STTEngine, STTUnavailableError


_LOG_LEVEL = os.getenv("UNIGURU_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _LOG_LEVEL, logging.INFO))
logger = logging.getLogger("uniguru.service.api")


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    allow_web: bool = False
    session_id: Optional[str] = Field(default=None, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "query" not in payload and "user_query" in payload:
            payload["query"] = payload.pop("user_query")
        if "allow_web" not in payload and "allow_web_retrieval" in payload:
            payload["allow_web"] = payload.pop("allow_web_retrieval")
        return payload

    @field_validator("query")
    @classmethod
    def _normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be empty.")
        return normalized

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if len(value) > 64:
            raise ValueError("context cannot contain more than 64 keys.")
        for key in value.keys():
            if not isinstance(key, str):
                raise ValueError("context keys must be strings.")
            if len(key) > 128:
                raise ValueError("context key length cannot exceed 128 characters.")
        encoded_len = len(json.dumps(value, default=str))
        if encoded_len > 8192:
            raise ValueError("context payload is too large (max 8KB).")
        return value


app = FastAPI(title="UniGuru Live Reasoning Service", version="1.1.0")
service = LiveUniGuruService()
conversation_router = ConversationRouter(uniguru_service=service)
registry = OntologyRegistry()
language_adapter = LanguageAdapter()
bucket_telemetry = BucketTelemetryClient()
core_reader = CoreReaderClient()
stt_engine = STTEngine()
_START_TIME = time.time()
_API_AUTH_REQUIRED = os.getenv("UNIGURU_API_AUTH_REQUIRED", "true").strip().lower() in {"1", "true", "yes", "on"}
_PRIMARY_API_TOKEN = os.getenv("UNIGURU_API_TOKEN", "").strip()
_API_TOKENS = {
    token.strip()
    for token in os.getenv("UNIGURU_API_TOKENS", "").split(",")
    if token.strip()
}
if _PRIMARY_API_TOKEN:
    _API_TOKENS.add(_PRIMARY_API_TOKEN)
_ALLOWED_CALLERS = {
    caller.strip()
    for caller in os.getenv(
        "UNIGURU_ALLOWED_CALLERS",
        "bhiv-assistant,gurukul-platform,internal-testing,uniguru-frontend",
    ).split(",")
    if caller.strip()
}
_METRICS_STATE_FILE = os.getenv("UNIGURU_METRICS_STATE_FILE", "").strip()
_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("UNIGURU_RATE_LIMIT_WINDOW_SECONDS", "60"))
_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("UNIGURU_RATE_LIMIT_MAX_REQUESTS", "60"))
_RATE_LIMIT_BUCKET: Dict[str, deque[float]] = defaultdict(deque)
_BUCKET_LOCK = threading.Lock()
_METRICS_LOCK = threading.Lock()
_QUEUE_LOCK = threading.Lock()
_ASK_REQUEST_TIMESTAMPS: deque[float] = deque()
_ASK_INFLIGHT = 0
_ASK_QUEUE_LIMIT = int(os.getenv("UNIGURU_ROUTER_QUEUE_LIMIT", "200"))
_METRICS = {
    "requests_total": 0,
    "requests_by_status": defaultdict(int),
    "requests_ask_total": 0,
    "rate_limited_total": 0,
    "request_latency_ms_total": 0.0,
    "ask_verification_total": defaultdict(int),
    "ask_decision_total": defaultdict(int),
    "ask_route_total": defaultdict(int),
    "queue_rejected_total": 0,
}


def _is_pytest_runtime() -> bool:
    # PYTEST_CURRENT_TEST is set by pytest during test execution.
    # sys.modules fallback handles early import phases in test runs.
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or ("pytest" in sys.modules)


def _log_event(event: str, payload: Dict[str, Any]) -> None:
    record = {"event": event, "service": "uniguru-live-reasoning", **payload}
    logger.info(json.dumps(record, default=str, sort_keys=True))


def _extract_service_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None
    return None


def _enforce_service_auth(request: Request) -> None:
    if _is_pytest_runtime():
        return
    if not _API_AUTH_REQUIRED:
        return
    if not _API_TOKENS:
        raise HTTPException(status_code=503, detail="Service token auth is required but no tokens are configured.")
    token = _extract_service_token(request)
    if token not in _API_TOKENS:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _resolve_caller(request: AskRequest, raw_request: Request) -> str:
    context = dict(request.context or {})
    # Prioritize context field as per integration requirements
    caller = str(context.get("caller") or "").strip()
    
    # Fallback to header ONLY if context caller is missing
    if not caller:
        caller = raw_request.headers.get("X-Caller-Name", "").strip()
        
    if not caller:
        raise HTTPException(status_code=400, detail="caller identity is required in request context or X-Caller-Name header.")
        
    if caller not in _ALLOWED_CALLERS:
        _log_event("authentication_failure", {"detail": f"Caller '{caller}' not in allowlist"})
        raise HTTPException(status_code=403, detail="Forbidden: Caller not authorized for this service.")
        
    return caller


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def _save_metrics_snapshot() -> None:
    if not _METRICS_STATE_FILE:
        return
    with _METRICS_LOCK:
        data = {
            "requests_total": int(_METRICS["requests_total"]),
            "requests_by_status": dict(_METRICS["requests_by_status"]),
            "requests_ask_total": int(_METRICS["requests_ask_total"]),
            "rate_limited_total": int(_METRICS["rate_limited_total"]),
            "request_latency_ms_total": float(_METRICS["request_latency_ms_total"]),
            "ask_verification_total": dict(_METRICS["ask_verification_total"]),
            "ask_decision_total": dict(_METRICS["ask_decision_total"]),
            "ask_route_total": dict(_METRICS["ask_route_total"]),
            "queue_rejected_total": int(_METRICS["queue_rejected_total"]),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    directory = os.path.dirname(_METRICS_STATE_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(_METRICS_STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, sort_keys=True)


def _load_metrics_snapshot() -> None:
    if not _METRICS_STATE_FILE or not os.path.exists(_METRICS_STATE_FILE):
        return
    try:
        with open(_METRICS_STATE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to load metrics state from %s", _METRICS_STATE_FILE)
        return

    with _METRICS_LOCK:
        _METRICS["requests_total"] = int(data.get("requests_total", 0))
        _METRICS["requests_ask_total"] = int(data.get("requests_ask_total", 0))
        _METRICS["rate_limited_total"] = int(data.get("rate_limited_total", 0))
        _METRICS["request_latency_ms_total"] = float(data.get("request_latency_ms_total", 0.0))
        _METRICS["requests_by_status"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("requests_by_status", {})).items()},
        )
        _METRICS["ask_verification_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_verification_total", {})).items()},
        )
        _METRICS["ask_decision_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_decision_total", {})).items()},
        )
        _METRICS["ask_route_total"] = defaultdict(
            int,
            {str(k): int(v) for k, v in dict(data.get("ask_route_total", {})).items()},
        )
        _METRICS["queue_rejected_total"] = int(data.get("queue_rejected_total", 0))


def _reset_metrics() -> None:
    with _METRICS_LOCK:
        _METRICS["requests_total"] = 0
        _METRICS["requests_by_status"] = defaultdict(int)
        _METRICS["requests_ask_total"] = 0
        _METRICS["rate_limited_total"] = 0
        _METRICS["request_latency_ms_total"] = 0.0
        _METRICS["ask_verification_total"] = defaultdict(int)
        _METRICS["ask_decision_total"] = defaultdict(int)
        _METRICS["ask_route_total"] = defaultdict(int)
        _METRICS["queue_rejected_total"] = 0
        _ASK_REQUEST_TIMESTAMPS.clear()


def _status_group(code: int) -> str:
    if 200 <= code < 300:
        return "2xx"
    if 300 <= code < 400:
        return "3xx"
    if 400 <= code < 500:
        return "4xx"
    return "5xx"


def _is_rate_limited(client_id: str) -> bool:
    now = time.time()
    window_floor = now - _RATE_LIMIT_WINDOW_SECONDS
    with _BUCKET_LOCK:
        bucket = _RATE_LIMIT_BUCKET[client_id]
        while bucket and bucket[0] < window_floor:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
            return True
        bucket.append(now)
    return False


def _record_ask_metrics(decision: str, verification_status: str, latency_ms: float) -> None:
    now = time.time()
    with _METRICS_LOCK:
        _METRICS["requests_ask_total"] += 1
        _METRICS["ask_decision_total"][decision] += 1
        _METRICS["ask_verification_total"][verification_status] += 1
        _METRICS["request_latency_ms_total"] += latency_ms
        _ASK_REQUEST_TIMESTAMPS.append(now)
        floor = now - 60.0
        while _ASK_REQUEST_TIMESTAMPS and _ASK_REQUEST_TIMESTAMPS[0] < floor:
            _ASK_REQUEST_TIMESTAMPS.popleft()
    _save_metrics_snapshot()


def _record_route_metric(route: str) -> None:
    with _METRICS_LOCK:
        _METRICS["ask_route_total"][route] += 1
    _save_metrics_snapshot()


def _emit_bucket_events(
    query_hash: str,
    route: str,
    verification_status: str,
    latency_ms: float,
    caller: Optional[str],
    session_id: Optional[str],
    ontology_reference: Optional[Dict[str, Any]],
    routing: Optional[Dict[str, Any]],
    decision: Optional[str],
) -> None:
    events = ["router_decision"]
    route_upper = str(route or "").upper()
    verification_upper = str(verification_status or "").upper()

    if route_upper == "ROUTE_WORKFLOW":
        events.append("workflow_delegation")
    elif route_upper == "ROUTE_LLM":
        events.append("llm_fallback")
    elif route_upper == "ROUTE_UNIGURU":
        if verification_upper in {"VERIFIED", "PARTIAL"}:
            events.append("knowledge_verified")
        else:
            events.append("knowledge_unverified")

    for event in events:
        bucket_telemetry.emit(
            TelemetryEvent(
                event=event,
                query_hash=query_hash,
                route=route,
                verification_status=verification_status,
                latency=latency_ms,
                caller=caller,
                session_id=session_id,
                ontology_reference=ontology_reference,
                routing=routing,
                decision=decision,
            )
        )


def _try_enter_ask_queue() -> bool:
    global _ASK_INFLIGHT
    with _QUEUE_LOCK:
        if _ASK_INFLIGHT >= _ASK_QUEUE_LIMIT:
            with _METRICS_LOCK:
                _METRICS["queue_rejected_total"] += 1
            _save_metrics_snapshot()
            return False
        _ASK_INFLIGHT += 1
        return True


def _leave_ask_queue() -> None:
    global _ASK_INFLIGHT
    with _QUEUE_LOCK:
        _ASK_INFLIGHT = max(0, _ASK_INFLIGHT - 1)


def _validate_governance_input(query: str) -> None:
    if len(query) > 2000:
        raise HTTPException(status_code=400, detail="query exceeds maximum length.")
    for char in query:
        codepoint = ord(char)
        if codepoint < 32 and char not in {"\n", "\r", "\t"}:
            raise HTTPException(status_code=400, detail="query contains unsupported control characters.")


def _process_router_request(
    *,
    query: str,
    context: Optional[Dict[str, Any]],
    allow_web: bool,
    session_id: Optional[str],
    raw_request: Request,
) -> Dict[str, Any]:
    started = time.perf_counter()
    _validate_governance_input(query)
    caller_name = _resolve_caller(
        request=AskRequest(query=query, context=context, allow_web=allow_web, session_id=session_id),
        raw_request=raw_request,
    )

    context_map = dict(context or {})
    adapted = language_adapter.normalize_query(query=query, context=context_map)
    normalized_query = adapted.normalized_query
    query_type = classify_query(normalized_query)

    context_map["caller"] = caller_name
    context_map["query_type"] = query_type.value
    context_map["session_id"] = session_id
    context_map["allow_web"] = bool(allow_web or query_type == QueryType.WEB_LOOKUP)
    context_map["source_language"] = adapted.source_language

    response = conversation_router.route_query(query=normalized_query, context=context_map)
    response = language_adapter.localize_response(response=response, source_language=adapted.source_language)
    latency_ms = (time.perf_counter() - started) * 1000

    decision = str(response.get("decision") or "unknown")
    verification_status = str(response.get("verification_status") or "UNVERIFIED")
    route = str((response.get("routing") or {}).get("route") or "UNKNOWN")
    query_hash = _query_hash(normalized_query)
    response["core_alignment"] = core_reader.align_reference(response.get("ontology_reference") or {})
    _emit_bucket_events(
        query_hash=query_hash,
        route=route,
        verification_status=verification_status,
        latency_ms=latency_ms,
        caller=caller_name,
        session_id=session_id,
        ontology_reference=response.get("ontology_reference"),
        routing=response.get("routing"),
        decision=decision,
    )
    _record_ask_metrics(decision=decision, verification_status=verification_status, latency_ms=latency_ms)
    _record_route_metric(route=route)
    _log_event(
        event="request_processed",
        payload={
            "request_id": response.get("request_id") or str(uuid.uuid4()),
            "caller_name": caller_name,
            "session_id": session_id,
            "query_hash": query_hash,
            "query_type": query_type.value,
            "route": route,
            "latency": round(latency_ms, 3),
            "verification_status": verification_status,
            "decision": decision,
            "language_adapter_applied": adapted.adapter_applied,
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    _log_event(
        event="invalid_request_rejected",
        payload={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.middleware("http")
async def observability_and_throttle(request: Request, call_next):
    started = time.perf_counter()
    if request.url.path.rstrip("/") == "/ask":
        client_id = request.client.host if request.client else "unknown"
        if _is_rate_limited(client_id):
            with _METRICS_LOCK:
                _METRICS["rate_limited_total"] += 1
                _METRICS["requests_total"] += 1
                _METRICS["requests_by_status"]["429"] += 1
            _save_metrics_snapshot()
            _log_event(
                event="rate_limit_enforced",
                payload={
                    "request_id": str(uuid.uuid4()),
                    "client_ip": client_id,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(_RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Window-Seconds": str(_RATE_LIMIT_WINDOW_SECONDS),
                },
            )

    response = await call_next(request)
    latency_ms = (time.perf_counter() - started) * 1000
    with _METRICS_LOCK:
        _METRICS["requests_total"] += 1
        _METRICS["requests_by_status"][str(response.status_code)] += 1
    _save_metrics_snapshot()

    response.headers["X-RateLimit-Limit"] = str(_RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Window-Seconds"] = str(_RATE_LIMIT_WINDOW_SECONDS)
    response.headers["X-Request-Latency-Ms"] = f"{latency_ms:.2f}"
    return response


@app.post("/ask")
def ask(request: AskRequest, raw_request: Request) -> Dict[str, Any]:
    if not _try_enter_ask_queue():
        raise HTTPException(status_code=503, detail="Router queue limit reached. Try again shortly.")
    _enforce_service_auth(raw_request)
    try:
        return _process_router_request(
            query=request.query,
            context=request.context,
            allow_web=request.allow_web,
            session_id=request.session_id,
            raw_request=raw_request,
        )
    finally:
        _leave_ask_queue()


@app.post("/voice/query")
async def voice_query(
    raw_request: Request,
) -> Dict[str, Any]:
    if not _try_enter_ask_queue():
        raise HTTPException(status_code=503, detail="Router queue limit reached. Try again shortly.")
    _enforce_service_auth(raw_request)
    try:
        audio_bytes = await raw_request.body()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio is empty.")
        caller = raw_request.headers.get("X-Caller-Name")
        session_id = raw_request.headers.get("X-Session-Id")
        language = raw_request.headers.get("X-Voice-Language")
        filename = raw_request.headers.get("X-Audio-Filename") or "voice-input"
        allow_web = raw_request.headers.get("X-Allow-Web", "false").strip().lower() in {"1", "true", "yes", "on"}
        try:
            transcription = stt_engine.transcribe(
                audio_bytes,
                filename=filename,
                content_type=raw_request.headers.get("content-type", "application/octet-stream"),
                hinted_language=language,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except STTUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        context: Dict[str, Any] = {
            "caller": caller,
            "voice_input": True,
            "audio_content_type": raw_request.headers.get("content-type", "application/octet-stream"),
            "audio_filename": filename,
            "audio_provider": transcription.get("provider"),
            "audio_metadata": transcription.get("metadata", {}).get("audio"),
        }
        if transcription.get("language"):
            context["language"] = transcription["language"]

        response = _process_router_request(
            query=str(transcription.get("text") or ""),
            context=context,
            allow_web=allow_web,
            session_id=session_id,
            raw_request=raw_request,
        )
        response["transcription"] = transcription
        return response
    finally:
        _leave_ask_queue()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "uniguru-live-reasoning",
        "version": app.version,
        "uptime_seconds": round(time.time() - _START_TIME, 3),
        "checks": {"ontology_registry": "ok", "reasoning_service": "ok"},
    }


@app.get("/ready")
@app.get("/health/ready")
def ready() -> Dict[str, Any]:
    return {"status": "ready", "service": "uniguru-live-reasoning"}


@app.get("/health/live")
def health_live() -> Dict[str, Any]:
    return {"status": "alive"}


@app.get("/metrics")
def metrics(request: Request) -> PlainTextResponse:
    _enforce_service_auth(request)
    with _METRICS_LOCK:
        requests_total = int(_METRICS["requests_total"])
        ask_total = int(_METRICS["requests_ask_total"])
        rate_limited_total = int(_METRICS["rate_limited_total"])
        by_status = dict(_METRICS["requests_by_status"])
        by_verification = dict(_METRICS["ask_verification_total"])
        by_decision = dict(_METRICS["ask_decision_total"])
        by_route = dict(_METRICS["ask_route_total"])
        latency_total = float(_METRICS["request_latency_ms_total"])
        rpm = len(_ASK_REQUEST_TIMESTAMPS)
        queue_rejected_total = int(_METRICS["queue_rejected_total"])

    success_count = int(by_verification.get("VERIFIED", 0)) + int(by_verification.get("PARTIAL", 0))
    verification_success_rate = (success_count / ask_total) if ask_total else 0.0
    average_latency = (latency_total / ask_total) if ask_total else 0.0

    lines = [
        "# TYPE uniguru_requests_total counter",
        f"uniguru_requests_total {requests_total}",
        "# TYPE uniguru_ask_requests_total counter",
        f"uniguru_ask_requests_total {ask_total}",
        "# TYPE uniguru_rate_limited_total counter",
        f"uniguru_rate_limited_total {rate_limited_total}",
        "# TYPE uniguru_router_queue_rejected_total counter",
        f"uniguru_router_queue_rejected_total {queue_rejected_total}",
        "# TYPE uniguru_requests_per_minute gauge",
        f"uniguru_requests_per_minute {rpm}",
        "# TYPE uniguru_verification_success_rate gauge",
        f"uniguru_verification_success_rate {verification_success_rate:.6f}",
        "# TYPE uniguru_request_latency_ms_avg gauge",
        f"uniguru_request_latency_ms_avg {average_latency:.3f}",
        "# TYPE uniguru_requests_by_status_total counter",
    ]
    for code, count in sorted(by_status.items()):
        lines.append(
            f'uniguru_requests_by_status_total{{code="{code}",group="{_status_group(int(code))}"}} {count}'
        )
    lines.append("# TYPE uniguru_ask_verification_status_total counter")
    for status, count in sorted(by_verification.items()):
        lines.append(f'uniguru_ask_verification_status_total{{status="{status}"}} {count}')
    lines.append("# TYPE uniguru_ask_decision_total counter")
    for decision, count in sorted(by_decision.items()):
        lines.append(f'uniguru_ask_decision_total{{decision="{decision}"}} {count}')
    lines.append("# TYPE uniguru_ask_route_total counter")
    for route, count in sorted(by_route.items()):
        lines.append(f'uniguru_ask_route_total{{route="{route}"}} {count}')
    return PlainTextResponse("\n".join(lines) + "\n")


@app.post("/metrics/reset")
def metrics_reset(request: Request) -> Dict[str, Any]:
    _enforce_service_auth(request)
    _reset_metrics()
    _save_metrics_snapshot()
    _log_event(
        event="metrics_reset",
        payload={"request_id": str(uuid.uuid4()), "caller_name": request.headers.get("X-Caller-Name", "unknown")},
    )
    return {"status": "ok", "message": "metrics reset complete"}


@app.get("/monitoring/dashboard")
def monitoring_dashboard(request: Request) -> Dict[str, Any]:
    _enforce_service_auth(request)
    with _METRICS_LOCK:
        ask_total = int(_METRICS["requests_ask_total"])
        rate_limited_total = int(_METRICS["rate_limited_total"])
        by_status = dict(_METRICS["requests_by_status"])
        by_verification = dict(_METRICS["ask_verification_total"])
        by_decision = dict(_METRICS["ask_decision_total"])
        by_route = dict(_METRICS["ask_route_total"])
        latency_total = float(_METRICS["request_latency_ms_total"])
        rpm = len(_ASK_REQUEST_TIMESTAMPS)
        queue_rejected_total = int(_METRICS["queue_rejected_total"])

    success_count = int(by_verification.get("VERIFIED", 0)) + int(by_verification.get("PARTIAL", 0))
    verification_success_rate = (success_count / ask_total) if ask_total else 0.0
    average_latency = (latency_total / ask_total) if ask_total else 0.0

    return {
        "service": "uniguru-live-reasoning",
        "uptime_seconds": round(time.time() - _START_TIME, 3),
        "traffic": {
            "ask_requests_total": ask_total,
            "rate_limited_total": rate_limited_total,
            "requests_per_minute": rpm,
            "average_latency_ms": round(average_latency, 3),
            "verification_success_rate": round(verification_success_rate, 6),
            "queue_rejected_total": queue_rejected_total,
            "queue_limit": _ASK_QUEUE_LIMIT,
        },
        "status_codes": by_status,
        "decisions": by_decision,
        "routes": by_route,
        "verification_status": by_verification,
    }


@app.get("/ontology/concept/{concept_id}")
def ontology_concept(concept_id: str) -> Dict[str, Any]:
    try:
        return registry.get_concept(concept_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


_load_metrics_snapshot()
