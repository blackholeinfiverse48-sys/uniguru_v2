import sys
import os
import json
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path("c:/Users/Yass0/OneDrive/Desktop/TASK14").absolute()))

from uniguru.service.live_service import LiveUniGuruService

def run_test(service, query: str, allow_web: bool = False):
    print(f"\n--- Testing Query: {query} (allow_web={allow_web}) ---")
    try:
        response = service.ask(user_query=query, allow_web_retrieval=allow_web)
        return response
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    service = LiveUniGuruService()
    results = []

    # 1. Web-only Unverified (Matches randomblog.xyz in simulation candidates)
    results.append({
        "case": "Web-only Unverified (randomblog.xyz)",
        "query": "My Thoughts on Jainism",
        "response": run_test(service, "My Thoughts on Jainism", allow_web=True)
    })

    # 2. Web-only Verified (Should trigger if we use something that is not in KB but in candidates)
    # Let's use a query that matches a verified candidate
    # "Stanford University Religious Studies" is a candidate
    results.append({
        "case": "Web-only Verified (Stanford)",
        "query": "Jainism Stanford University",
        "allow_web": True,
        "response": run_test(service, "Jainism Stanford University", allow_web=True)
    })

    with open("web_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to web_test_results.json")
