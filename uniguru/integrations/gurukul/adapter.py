from typing import Optional, Dict, Any
from pydantic import BaseModel


class GurukulQueryRequest(BaseModel):
    student_query: str
    student_id: Optional[str] = None
    class_id: Optional[str] = None
    session_id: Optional[str] = None


class GurukulIntegrationAdapter:
    """Adapter that binds Gurukul student queries to UniGuru RuleEngine."""

    def __init__(self, engine):
        self.engine = engine

    def process_student_query(self, payload: GurukulQueryRequest) -> Dict[str, Any]:
        metadata = {
            "source_system": "gurukul",
            "student_id": payload.student_id,
            "class_id": payload.class_id,
            "session_id": payload.session_id,
        }
        decision = self.engine.evaluate(payload.student_query, metadata)

        return {
            "integration": "gurukul",
            "student_id": payload.student_id,
            "class_id": payload.class_id,
            "session_id": payload.session_id,
            "verification_status": decision.get("verification_status"),
            "status_action": decision.get("status_action"),
            "response": decision,
        }
