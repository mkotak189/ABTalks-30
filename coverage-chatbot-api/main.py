from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
import time
import sys
import os

# Set working directory to repo root for database access
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rag_chatbot import retrieve_and_answer

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# PYDANTIC MODELS
# ============================================================

class ChatMessage(BaseModel):
    session_id: str
    member_id: str
    message: str

class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    timing_ms: float

# ============================================================
# IN-MEMORY SESSION STORE
# ============================================================

sessions: Dict[str, List[ConversationTurn]] = {}

# ============================================================
# FASTAPI APP SETUP
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok"}

from fastapi.responses import StreamingResponse
import json

@app.post("/chat")
async def chat(request: ChatMessage):
    """
    Stream chat responses token-by-token using Server-Sent Events (SSE).
    """
    start_time = time.time()
    
    # Initialize session if new
    if request.session_id not in sessions:
        sessions[request.session_id] = []
    
    # Store user turn immediately
    user_turn = ConversationTurn(
        role="user",
        content=request.message,
        timestamp=datetime.now().isoformat()
    )
    sessions[request.session_id].append(user_turn)
    
    async def generate():
        """Generator function that yields SSE-formatted chunks."""
        try:
            # Call retrieve_and_answer with stream=True
            result = retrieve_and_answer(request.message, stream=True)
            
            # Yield metadata first
            yield f"data: {json.dumps({'type': 'metadata', 'classification': result.get('classification', 'unknown')})}\n\n"
            
            # Stream the answer token by token
            full_answer = ""
            for token in result.get("answer_stream", []):
                full_answer += token
                # Yield each token as SSE data
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Store assistant turn after streaming complete
            assistant_turn = ConversationTurn(
                role="assistant",
                content=full_answer,
                timestamp=datetime.now().isoformat()
            )
            sessions[request.session_id].append(assistant_turn)
            
            # Yield completion signal
            timing_ms = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({'type': 'done', 'timing_ms': timing_ms})}\n\n"
        
        except Exception as e:
            # Yield error as SSE
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Retrieve conversation history for a session_id.
    Returns all stored turns (user + assistant).
    """
    if session_id not in sessions:
        return {
            "session_id": session_id,
            "history": [],
            "message": "No history found for this session"
        }
    
    return {
        "session_id": session_id,
        "history": sessions[session_id],
        "turn_count": len(sessions[session_id])
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)