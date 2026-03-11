
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add project root to path
root = Path("c:/Users/Yass0/OneDrive/Desktop/TASK14").absolute()
sys.path.append(str(root))

from uniguru.router.conversation_router import route_query

def log_event(event, payload, log_file):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def run_integration_demo():
    log_file = "c:/Users/Yass0/OneDrive/Desktop/TASK14/demo_logs/router_integration.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Clear log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("")

    scenarios = [
        {"name": "knowledge_query", "query": "What is a qubit?"},
        {"name": "conversation_query", "query": "Hello, how are you today?"},
        {"name": "unsafe_query", "query": "sudo rm -rf /root"},
        {"name": "workflow_query", "query": "create workflow ticket for onboarding"},
        {"name": "system_command", "query": "shutdown system -h now"},
    ]

    print(f"Running {len(scenarios)} integration scenarios...")
    for s in scenarios:
        print(f"Processing: {s['name']}")
        res = route_query(s['query'])
        log_event("routing_decision", {
            "scenario": s['name'],
            "query": s['query'],
            "route": res.get("routing", {}).get("route"),
            "query_type": res.get("routing", {}).get("query_type"),
            "decision": res.get("decision"),
            "latency": res.get("routing", {}).get("router_latency_ms")
        }, log_file)

    print(f"Integration logs written to {log_file}")

if __name__ == "__main__":
    run_integration_demo()
