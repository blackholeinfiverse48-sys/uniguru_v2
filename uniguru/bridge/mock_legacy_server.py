from typing import Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class LegacyRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
async def chat(request: Dict[str, Any]):
    # Flexible request handling
    message = request.get("message") or request.get("query") or "No message"
    return {
        "production_answer": f"Legacy Production Response for: {message}",
        "retrieved_chunks": [
            {"content": "Legacy source snippet", "source": "VectorDB_v1"}
        ],
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
