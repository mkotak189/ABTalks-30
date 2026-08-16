import streamlit as st
import requests
import uuid
import pandas as pd
import sqlite3
import json
from datetime import datetime
from response_cards import ClaimStatusCard, CoverageSummaryCard

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Health Coverage Chatbot",
    page_icon="💬",
    layout="wide"
)

st.title("💬 Health Coverage Chatbot")

# ============================================================
# BACKEND CONFIG
# ============================================================

BACKEND_URL = "http://localhost:8000"

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_plan" not in st.session_state:
    st.session_state.selected_plan = "General"

# ============================================================
# LOAD PLANS FROM DATABASE
# ============================================================

def load_plans():
    try:
        conn = sqlite3.connect("coverage.db")
        cur = conn.cursor()
        cur.execute("SELECT plan_name FROM plans")
        plans = [row[0] for row in cur.fetchall()]
        conn.close()
        return ["General"] + plans
    except Exception as e:
        st.warning(f"Could not load plans: {e}")
        return ["General"]

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    # Plan selector
    plans = load_plans()
    st.session_state.selected_plan = st.selectbox(
        "Select Plan:",
        plans,
        index=plans.index(st.session_state.selected_plan) if st.session_state.selected_plan in plans else 0
    )
    
    st.divider()
    
    # New conversation button
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Session info
    st.caption(f"**Session ID:** {st.session_state.session_id[:8]}...")
    st.caption(f"**Messages:** {len(st.session_state.messages)}")

# ============================================================
# DISPLAY MESSAGE HISTORY
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display citations if available
        if message.get("citations"):
            with st.expander("📋 Policy Sources"):
                st.caption(f"This answer references {len(message['citations'])} policy clause(s)")
                for i, chunk_id in enumerate(message["citations"], 1):
                    st.caption(f"{i}. Chunk ID: {chunk_id}")

# ============================================================
# CHAT INPUT & BACKEND CALL
# ============================================================

user_input = st.chat_input("Ask about your health plan...")

if user_input:
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "citations": []
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Stream response from backend
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        status_placeholder = st.empty()
        
        try:
            with status_placeholder.container():
                st.spinner("Streaming response...")
            
            full_response = ""
            chunk_ids = []
            timing_ms = 0
            
            response = requests.post(
                f"{BACKEND_URL}/chat",
                json={
                    "session_id": st.session_state.session_id,
                    "member_id": "M001",
                    "message": user_input
                },
                stream=True,
                timeout=120
            )
            
            response.raise_for_status()
            
            # Process SSE stream
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse SSE format: "data: {...}"
                        if line.startswith("data: "):
                            json_str = line[6:]  # Remove "data: " prefix
                            data = json.loads(json_str)
                            
                            if data["type"] == "token":
                                # Append token to response
                                full_response += data["content"]
                                message_placeholder.markdown(full_response)
                            
                            elif data["type"] == "done":
                                # Stream complete
                                chunk_ids = data.get("chunk_ids", [])
                                timing_ms = data.get("timing_ms", 0)
                                
                                # Render citations
                                if chunk_ids:
                                    with st.expander("📋 Policy Sources"):
                                        st.caption(f"This answer references {len(chunk_ids)} policy clause(s)")
                                        for i, chunk_id in enumerate(chunk_ids, 1):
                                            st.caption(f"{i}. Chunk ID: {chunk_id}")
                                
                                status_placeholder.caption(f"⏱️ {timing_ms:.1f}ms")
                            
                            elif data["type"] == "error":
                                st.error(f"Error: {data['message']}")
                                break
                    
                    except json.JSONDecodeError:
                        continue
            
            # Add assistant message to history
            if full_response:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "citations": chunk_ids
                })
        
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend. Make sure uvicorn is running on http://localhost:8000")
        except requests.exceptions.Timeout:
            st.error("⏱️ Backend request timed out. The model may be loading.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption("This is a demonstration chatbot. Not medical advice. Always consult with a healthcare provider.")