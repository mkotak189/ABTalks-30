from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
import time
import sys
import os
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

import os

# Set working directory to repo root for database access
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
@app.post("/chat")
async def chat(request: ChatMessage):
    start_time = time.time()
    
    try:
        # Initialize session if new
        if request.session_id not in sessions:
            sessions[request.session_id] = []
        
        # Call retrieve_and_answer directly (no import needed)
        result = retrieve_and_answer(request.message, stream=False)
        
        # Rest of the code...
        
        # Store user turn
        user_turn = ConversationTurn(
            role="user",
            content=request.message,
            timestamp=datetime.now().isoformat()
        )
        sessions[request.session_id].append(user_turn)
        
        # Store assistant turn
        assistant_turn = ConversationTurn(
            role="assistant",
            content=result["answer"],
            timestamp=datetime.now().isoformat()
        )
        sessions[request.session_id].append(assistant_turn)
        
        # Calculate timing
        timing_ms = (time.time() - start_time) * 1000
        
        return ChatResponse(
            session_id=request.session_id,
            response=result["answer"],
            timing_ms=timing_ms
        )
    
    except Exception as e:
        timing_ms = (time.time() - start_time) * 1000
        return {
            "error": str(e),
            "session_id": request.session_id,
            "timing_ms": timing_ms,
            "status": 500
        }


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