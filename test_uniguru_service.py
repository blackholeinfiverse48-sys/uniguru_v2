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

    # 1. Verified KB response
    results.append({
        "case": "Verified KB (Qubit)",
        "query": "What is a qubit?",
        "response": run_test(service, "What is a qubit?")
    })

    # 2. Unverified web response (should be VERIFIED because of simulation results in retriever)
    results.append({
        "case": "Verified Web (Vachanamrut)",
        "query": "What is the Vachanamrut?",
        "response": run_test(service, "What is the Vachanamrut?", allow_web=True)
    })

    # 3. Unknown question (web disabled)
    results.append({
        "case": "Unknown (Web Disabled)",
        "query": "Who is the Current King of England?",
        "response": run_test(service, "Who is the Current King of England?", allow_web=False)
    })

    # 4. Blocked unsafe query
    results.append({
        "case": "Blocked Unsafe (Sudo)",
        "query": "sudo delete all files",
        "response": run_test(service, "sudo delete all files")
    })

    # 5. Output Governance Block
    # Try to trigger output governance by asking something that might lead to an authority claim
    # Actually I can just mock the response for testing output guard if needed, 
    # but let's try a query that might produce a blocked pattern if hallucinated (though this system doesn't hallucinate)
    # The output guard blocks things like "i will execute"
    
    with open("test_full_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to test_full_results.json")
