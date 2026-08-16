from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
import time
import sys
import os
import sqlite3
import json

# Set working directory to repo root for database access
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rag_chatbot import retrieve_and_answer

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ============================================================
# PYDANTIC MODELS
# ============================================================

class ChatMessage(BaseModel):
    session_id: str
    member_id: str
    message: str

class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    timing_ms: float

# ============================================================
# DATABASE SETUP
# ============================================================

def init_conversations_table():
    """Create conversations table if it doesn't exist."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_turn(session_id: str, role: str, content: str):
    """Save a chat turn to the conversations table."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO conversations (session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (session_id, role, content, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def load_history(session_id: str, last_n: int = 10) -> List[Dict]:
    """Load the last N turns from conversation history."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT role, content, timestamp FROM conversations
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (session_id, last_n))
    
    rows = cur.fetchall()
    conn.close()
    
    # Reverse to get chronological order
    history = [
        {"role": row[0], "content": row[1], "timestamp": row[2]}
        for row in reversed(rows)
    ]
    
    return history

def count_tokens(text: str) -> int:
    """Simple token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4

def get_total_history_tokens(session_id: str) -> int:
    """Count total tokens in session history."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT SUM(LENGTH(content)) FROM conversations
        WHERE session_id = ?
    """, (session_id,))
    
    total_chars = cur.fetchone()[0] or 0
    conn.close()
    
    return total_chars // 4

def summarize_old_turns(session_id: str):
    """Summarize oldest half of conversation when exceeding token limit."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    # Get all turns
    cur.execute("""
        SELECT id, role, content FROM conversations
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,))
    
    turns = cur.fetchall()
    mid_point = len(turns) // 2
    
    if mid_point < 1:
        conn.close()
        return
    
    # Get turns to summarize
    old_turns = turns[:mid_point]
    summary_text = "\n".join([f"{t[1]}: {t[2]}" for t in old_turns])
    
    # Create summary via LLM
    import openai
    client = openai.OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )
    
    try:
        response = client.chat.completions.create(
            model="llama3.1",
            messages=[{
                "role": "user",
                "content": f"Summarize this conversation in 1-2 sentences:\n{summary_text}"
            }],
            stream=False,
            timeout=60
        )
        summary = response.choices[0].message.content
    except Exception as e:
        summary = f"[Summary failed: {str(e)}]"
    
    # Delete old turns and insert summary
    old_ids = [t[0] for t in old_turns]
    placeholders = ",".join("?" * len(old_ids))
    
    cur.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", old_ids)
    cur.execute("""
        INSERT INTO conversations (session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (session_id, "system", f"[Summary of earlier conversation: {summary}]", datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# Initialize DB
init_conversations_table()

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
    allow_origins=["http://localhost:5173", "http://localhost:8501"],
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


@app.post("/chat")
async def chat(request: ChatMessage):
    """
    Stream chat responses with conversation memory.
    Saves turns to SQLite and loads history for context.
    """
    start_time = time.time()
    
    # Initialize session if new
    if request.session_id not in sessions:
        sessions[request.session_id] = []
    
    # Save user turn to database
    save_turn(request.session_id, "user", request.message)
    
    # Check if summarization is needed
    total_tokens = get_total_history_tokens(request.session_id)
    if total_tokens > 2000:
        summarize_old_turns(request.session_id)
    
    # Load conversation history (last 10 turns)
    history = load_history(request.session_id, last_n=10)
    history_context = "\n".join([
        f"{turn['role'].upper()}: {turn['content'][:200]}"
        for turn in history
    ])
    
    async def generate():
        """Generator for SSE streaming with memory context."""
        try:
            # Include history in retrieval
            full_context = f"Recent conversation:\n{history_context}\n\nCurrent question: {request.message}"
            
            result = retrieve_and_answer(request.message, stream=True)
            
            # Yield metadata
            yield f"data: {json.dumps({'type': 'metadata', 'total_tokens': total_tokens})}\n\n"
            
            # Stream tokens
            full_answer = ""
            if hasattr(result, '__iter__') and not isinstance(result, dict):
                # It's a generator
                for token in result:
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            else:
                # It's a dict with answer_stream
                for token in result.get("answer_stream", []):
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Save assistant turn to database
            save_turn(request.session_id, "assistant", full_answer)
            
            # Yield completion
            timing_ms = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({'type': 'done', 'timing_ms': timing_ms, 'chunk_ids': []})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Retrieve full conversation history for a session."""
    history = load_history(session_id, last_n=100)
    
    return {
        "session_id": session_id,
        "history": history,
        "turn_count": len(history),
        "total_tokens": get_total_history_tokens(session_id)
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)