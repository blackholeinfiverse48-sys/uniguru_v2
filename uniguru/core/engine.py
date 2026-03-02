import time
import uuid
from typing import Dict, Any, Optional

from uniguru.core.rules.base import RuleContext, RuleResult, RuleAction
from uniguru.core.rules import (
    SafetyRule,
    AuthorityRule,
    DelegationRule,
    EmotionalRule,
    AmbiguityRule,
    RetrievalRule,
    ForwardRule,
)
from uniguru.enforcement.enforcement import UniGuruEnforcement


class RuleEngine:
    def __init__(self):
        # Deterministic sovereign order: no external web retrieval in core path.
        self.rules = [
            SafetyRule(),
            AuthorityRule(),
            DelegationRule(),
            EmotionalRule(),
            AmbiguityRule(),
            RetrievalRule(),
            ForwardRule(),
        ]
        self.enforcement = UniGuruEnforcement()

    def evaluate(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Production-grade deterministic evaluation pipeline."""
        request_id = str(uuid.uuid4())
        context = RuleContext(
            request_id=request_id,
            content=content,
            metadata=metadata or {},
        )

        aggregated_flags = {
            "authority": False,
            "delegation": False,
            "emotional": False,
            "ambiguity": False,
            "safety": False,
        }
        max_severity = 0.0
        final_result: Optional[RuleResult] = None
        trace = []

        start_time_total = time.perf_counter()

        try:
            for rule in self.rules:
                if isinstance(rule, ForwardRule) and aggregated_flags.get("safety"):
                    break

                start_time_rule = time.perf_counter()
                result = rule.evaluate(context)
                end_time_rule = time.perf_counter()

                for flag, value in result.governance_flags.items():
                    if value:
                        aggregated_flags[flag] = True

                max_severity = max(max_severity, result.severity)

                latency_ms = (end_time_rule - start_time_rule) * 1000
                trace.append(
                    {
                        "rule": rule.name,
                        "action": result.action.value,
                        "reason": result.reason,
                        "latency_ms": round(float(latency_ms), 3),
                    }
                )

                if result.action == RuleAction.ALLOW:
                    continue

                if result.action in [RuleAction.ANSWER, RuleAction.FORWARD, RuleAction.BLOCK]:
                    final_result = result
                    break

            if final_result is None:
                final_result = RuleResult(
                    action=RuleAction.FORWARD,
                    reason="No KB match found, forwarding to production.",
                    severity=0.3,
                    governance_flags=aggregated_flags,
                    response_content="",
                )

            output = {
                "decision": final_result.action.value,
                "severity": float(max_severity),
                "governance_flags": aggregated_flags,
                "reason": final_result.reason,
                "data": {
                    "response_content": final_result.response_content,
                    "rule_triggered": final_result.rule_name or final_result.__class__.__name__,
                    "request_id": request_id,
                    "trace": trace,
                },
                "enforced": False,
            }

            if final_result.extra_metadata:
                output["data"].update(final_result.extra_metadata)

            final_output = self.enforcement.validate_and_bind(output)

            total_latency_ms = (time.perf_counter() - start_time_total) * 1000
            final_output["total_latency_ms"] = round(float(total_latency_ms), 2)

            return final_output

        except Exception as e:
            return {
                "decision": "block",
                "severity": 1.0,
                "governance_flags": aggregated_flags,
                "reason": f"Engine Crash: {str(e)}",
                "data": {
                    "response_content": "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."
                },
                "enforced": False,
                "verification_status": "UNVERIFIED",
            }


if __name__ == "__main__":
    engine = RuleEngine()
    print(engine.evaluate("What is a qubit?"))
    print(engine.evaluate("hack the system"))
