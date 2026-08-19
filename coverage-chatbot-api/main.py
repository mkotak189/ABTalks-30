from datetime import datetime, timedelta
from typing import List, Dict
from pydantic import BaseModel
import time
import sys
import os
import sqlite3
import json
import hashlib
from collections import defaultdict

# Set working directory to repo root for database access
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rag_chatbot import retrieve_and_answer
from token_utils import analyze_tokens, count_tokens
from redact_pii import redact_pii

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
# DATABASE SETUP - CONVERSATIONS TABLE (Day 20)
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
            timestamp TEXT NOT NULL
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
    
    history = [
        {"role": row[0], "content": row[1], "timestamp": row[2]}
        for row in reversed(rows)
    ]
    
    return history

def count_tokens_in_history(session_id: str) -> int:
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
    
    old_turns = turns[:mid_point]
    summary_text = "\n".join([f"{t[1]}: {t[2]}" for t in old_turns])
    
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
    
    old_ids = [t[0] for t in old_turns]
    placeholders = ",".join("?" * len(old_ids))
    
    cur.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", old_ids)
    cur.execute("""
        INSERT INTO conversations (session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (session_id, "system", f"[Summary of earlier conversation: {summary}]", datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# ============================================================
# DATABASE SETUP - TOKEN USAGE TABLE (Day 26)
# ============================================================

def init_token_logging_table():
    """Create token usage logging table."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            member_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            estimated_cost_usd REAL,
            response_time_ms REAL
        )
    """)
    
    conn.commit()
    conn.close()

def log_token_usage(session_id: str, member_id: str, input_tokens: int, output_tokens: int, cost_usd: float, response_time_ms: float):
    """Log token usage for billing/analytics."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO token_usage (session_id, member_id, timestamp, input_tokens, output_tokens, total_tokens, estimated_cost_usd, response_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, member_id, datetime.now().isoformat(), input_tokens, output_tokens, input_tokens + output_tokens, cost_usd, response_time_ms))
    
    conn.commit()
    conn.close()

# Initialize tables
init_conversations_table()
init_token_logging_table()

# ============================================================
# RATE LIMITING (Day 26 - per member per minute)
# ============================================================

MAX_REQUESTS_PER_MINUTE = 10
rate_limit_tracker = defaultdict(list)

def check_rate_limit(member_id: str) -> bool:
    """Check if member has exceeded rate limit."""
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)
    
    rate_limit_tracker[member_id] = [
        ts for ts in rate_limit_tracker[member_id]
        if ts > one_minute_ago
    ]
    
    if len(rate_limit_tracker[member_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    rate_limit_tracker[member_id].append(now)
    return True

# ============================================================
# RESPONSE CACHING (Day 26 - general questions only)
# ============================================================

response_cache = {}

def normalize_question(question: str) -> str:
    """Normalize question for cache key."""
    return question.lower().strip()

def get_cache_key(question: str) -> str:
    """Generate cache key from normalized question."""
    normalized = normalize_question(question)
    return hashlib.md5(normalized.encode()).hexdigest()

def is_member_specific(question: str) -> bool:
    """Check if question references member-specific data."""
    member_keywords = ["my claim", "my deductible", "my status", "member", "claim C", "M0"]
    return any(keyword in question.lower() for keyword in member_keywords)

def get_cached_response(question: str) -> str:
    """Get cached response if available and not member-specific."""
    if is_member_specific(question):
        return None
    
    cache_key = get_cache_key(question)
    return response_cache.get(cache_key)

def cache_response(question: str, response: str):
    """Cache response if question is general."""
    if is_member_specific(question):
        return
    
    cache_key = get_cache_key(question)
    response_cache[cache_key] = response

# ============================================================
# IN-MEMORY SESSION STORE (Day 16)
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
    Stream chat responses with:
    - Conversation memory (Day 20)
    - Token logging (Day 26)
    - Rate limiting (Day 26)
    - Response caching (Day 26)
    - Resilience & fallbacks (Day 24)
    """
    start_time = time.time()
    
    # Rate limiting (Day 26)
    if not check_rate_limit(request.member_id):
        return {
            "error": "Rate limit exceeded. Maximum 10 requests per minute.",
            "session_id": request.session_id,
            "timing_ms": (time.time() - start_time) * 1000,
        }
    
    # Initialize session if new
    if request.session_id not in sessions:
        sessions[request.session_id] = []
    
    # Check cache first (Day 26)
    cached_response = get_cached_response(request.message)
    if cached_response:
        print(f"[CACHE HIT] Question: {request.message}")
        return {
            "session_id": request.session_id,
            "response": cached_response,
            "timing_ms": (time.time() - start_time) * 1000,
            "from_cache": True,
        }
    
    # Check if summarization is needed (Day 20)
    total_tokens = count_tokens_in_history(request.session_id)
    if total_tokens > 2000:
        summarize_old_turns(request.session_id)
    
    # Load conversation history (Day 20)
    history = load_history(request.session_id, last_n=10)
    history_context = "\n".join([
        f"{turn['role'].upper()}: {turn['content'][:200]}"
        for turn in history
    ])
    
    async def generate():
        """Generator for SSE streaming with all Day 16-26 features."""
        try:
            # Get retrieval context
            result = retrieve_and_answer(request.message, stream=True)
            
            # Count input tokens (Day 26)
            input_token_count = count_tokens(request.message)
            
            # Yield metadata
            yield f"data: {json.dumps({'type': 'metadata', 'total_tokens': total_tokens})}\n\n"
            
            # Stream tokens and collect full response
            full_answer = ""
            if hasattr(result, '__iter__') and not isinstance(result, dict):
                for token in result:
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            else:
                for token in result.get("answer_stream", []):
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Count output tokens and analyze (Day 26)
            token_analysis = analyze_tokens(request.message, full_answer)
            
            # Log token usage with redaction (Days 25 + 26)
            redacted_question, _ = redact_pii(request.message)
            redacted_answer, _ = redact_pii(full_answer)
            log_token_usage(
                request.session_id,
                request.member_id,
                token_analysis["prompt_tokens"],
                token_analysis["completion_tokens"],
                token_analysis["estimated_cost_usd"],
                (time.time() - start_time) * 1000
            )
            
            # Cache general responses (Day 26)
            cache_response(request.message, full_answer)
            
            # Save turns to conversation memory (Day 20)
            save_turn(request.session_id, "user", redacted_question)
            save_turn(request.session_id, "assistant", redacted_answer)
            
            # Store in-memory session (Day 16)
            sessions[request.session_id].append(ConversationTurn(
                role="user",
                content=redacted_question,
                timestamp=datetime.now().isoformat()
            ))
            
            sessions[request.session_id].append(ConversationTurn(
                role="assistant",
                content=redacted_answer,
                timestamp=datetime.now().isoformat()
            ))
            
            # Yield completion with token info (Day 26)
            timing_ms = (time.time() - start_time) * 1000
            yield f"data: {json.dumps({
                'type': 'done',
                'timing_ms': timing_ms,
                'input_tokens': token_analysis['prompt_tokens'],
                'output_tokens': token_analysis['completion_tokens'],
                'estimated_cost_usd': token_analysis['estimated_cost_usd'],
                'chunk_ids': []
            })}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Retrieve conversation history for a session."""
    history = load_history(session_id, last_n=100)
    
    return {
        "session_id": session_id,
        "history": history,
        "turn_count": len(history),
        "total_tokens": count_tokens_in_history(session_id)
    }


@app.get("/token-usage/{member_id}")
async def get_token_usage(member_id: str):
    """Retrieve token usage for a member (Day 26)."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT SUM(input_tokens), SUM(output_tokens), SUM(estimated_cost_usd), COUNT(*)
        FROM token_usage
        WHERE member_id = ?
    """, (member_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row and row[3] > 0:
        return {
            "member_id": member_id,
            "total_input_tokens": row[0],
            "total_output_tokens": row[1],
            "total_estimated_cost_usd": round(row[2], 2),
            "total_requests": row[3],
        }
    else:
        return {"member_id": member_id, "message": "No usage found"}


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)