
import sys
import os
from pathlib import Path

# Add project root to path
root = Path("c:/Users/Yass0/OneDrive/Desktop/TASK14").absolute()
sys.path.append(str(root))

from uniguru.router.conversation_router import route_query

try:
    results = {}
    
    res1 = route_query("What is a qubit?")
    results["knowledge"] = res1["routing"]["route"]
    
    res2 = route_query("hi")
    results["llm"] = res2["routing"]["route"]
    
    res3 = route_query("sudo rm -rf /")
    results["system"] = res3["routing"]["route"]
    
    res4 = route_query("create workflow ticket")
    results["workflow"] = res4["routing"]["route"]
    
    import json
    print("RESULTS_JSON_START")
    print(json.dumps(results, indent=2))
    print("RESULTS_JSON_END")
except Exception as e:
    print("ERROR")
    import traceback
    traceback.print_exc()
