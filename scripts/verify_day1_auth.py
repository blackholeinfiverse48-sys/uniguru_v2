import requests
import json
import sys
import os

BASE_URL = "http://127.0.0.1:8000"
TOKEN = os.getenv("UNIGURU_API_TOKEN", "")
if not TOKEN:
    print("UNIGURU_API_TOKEN is required to run this script.")
    sys.exit(1)

def test_endpoint(method, path, headers=None, json_data=None):
    url = f"{BASE_URL}{path}"
    print(f"\nTesting {method} {path}...")
    try:
        response = requests.request(method, url, headers=headers, json=json_data)
        print(f"Status: {response.status_code}")
        try:
            print(f"Body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Body: {response.text[:100]}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # 1. Test /health (No auth required)
    test_endpoint("GET", "/health")

    # 2. Test /ask without auth
    test_endpoint("POST", "/ask", json_data={"query": "test"})

    # 3. Test /ask with invalid auth
    test_endpoint("POST", "/ask", headers={"Authorization": "Bearer invalid"}, json_data={"query": "test"})

    # 4. Test /ask with valid auth (should still fail due to missing caller if no context provided)
    test_endpoint("POST", "/ask", headers={"Authorization": f"Bearer {TOKEN}"}, json_data={"query": "test"})

    # 5. Test /ask with valid auth and caller
    test_endpoint("POST", "/ask", headers={"Authorization": f"Bearer {TOKEN}"}, json_data={
        "query": "What is a qubit?",
        "context": {"caller": "bhiv-assistant"}
    })

    # 6. Test /metrics with auth
    test_endpoint("GET", "/metrics", headers={"Authorization": f"Bearer {TOKEN}"})
