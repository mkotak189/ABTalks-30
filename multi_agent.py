import os
import json
import sqlite3
import asyncio
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

from crewai import Agent, Task, Crew
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool

load_dotenv()

# ============================================================
# INITIALIZE LLM
# ============================================================

llm = ChatAnthropic(model="claude-3-5-haiku-20241022")

# ============================================================
# CONVERSATION MEMORY
# ============================================================

def init_memory_table():
    """Create memory table if it doesn't exist."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            selected_plan_id TEXT,
            selected_plan_name TEXT,
            turn_count INTEGER DEFAULT 0,
            last_updated TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def get_conversation_memory(session_id: str) -> dict:
    """Retrieve conversation memory."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT selected_plan_id, selected_plan_name, turn_count FROM conversation_memory WHERE session_id = ?",
        (session_id,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "plan_id": row[0],
            "plan_name": row[1],
            "turn_count": row[2]
        }
    return {"plan_id": None, "plan_name": None, "turn_count": 0}

def update_conversation_memory(session_id: str, plan_id: str = None, plan_name: str = None):
    """Update conversation memory with plan selection."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    # Check if session exists
    cur.execute("SELECT id FROM conversation_memory WHERE session_id = ?", (session_id,))
    exists = cur.fetchone()
    
    if exists:
        update_query = "UPDATE conversation_memory SET last_updated = ?"
        params = [datetime.now().isoformat()]
        
        if plan_id:
            update_query += ", selected_plan_id = ?"
            params.append(plan_id)
        if plan_name:
            update_query += ", selected_plan_name = ?"
            params.append(plan_name)
        
        update_query += ", turn_count = turn_count + 1 WHERE session_id = ?"
        params.append(session_id)
        
        cur.execute(update_query, params)
    else:
        cur.execute("""
            INSERT INTO conversation_memory (session_id, selected_plan_id, selected_plan_name, turn_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, plan_id, plan_name, 1, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# Initialize memory table
init_memory_table()

# ============================================================
# RESILIENT TOOL CALLS WITH TIMEOUT & RETRY
# ============================================================

TIMEOUT_SECONDS = 10
MAX_RETRIES = 1
FALLBACK_MESSAGE = "I'm having trouble accessing that information right now. Please contact member support at 1-800-XXX-XXXX for assistance."

async def call_tool_with_resilience(tool_func, *args, **kwargs) -> str:
    """
    Call a tool with timeout, retry logic, and fallback.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Wrap in asyncio timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(tool_func, *args, **kwargs),
                timeout=TIMEOUT_SECONDS
            )
            return result
        
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES:
                print(f"Timeout on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(1)  # Brief delay before retry
                continue
            else:
                print(f"Tool call timed out after {MAX_RETRIES + 1} attempts")
                return FALLBACK_MESSAGE
        
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"Tool error on attempt {attempt + 1}: {str(e)}, retrying...")
                await asyncio.sleep(1)
                continue
            else:
                print(f"Tool call failed after {MAX_RETRIES + 1} attempts: {str(e)}")
                return FALLBACK_MESSAGE
    
    return FALLBACK_MESSAGE

# ============================================================
# DEFINE TOOLS WITH RESILIENCE
# ============================================================

@tool
def check_coverage(plan_id: str, procedure: str) -> str:
    """
    Check if a specific procedure is covered under a given plan.
    
    Args:
        plan_id: The plan identifier (e.g., 'P101' for Gold PPO)
        procedure: The medical procedure to check
    
    Returns:
        Coverage status and details
    """
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("SELECT plan_name FROM plans WHERE plan_id = ?", (plan_id,))
    plan_row = cur.fetchone()
    plan_name = plan_row[0] if plan_row else "Unknown Plan"
    
    excluded = ["cosmetic surgery", "dental care", "long-term care", "weight loss programs"]
    procedure_lower = procedure.lower()
    
    if any(excl in procedure_lower for excl in excluded):
        result = f"{procedure} is listed as an excluded service under {plan_name}."
    else:
        result = f"{procedure} is covered under {plan_name}. Please review your plan documents for copay and coinsurance details."
    
    conn.close()
    return result


@tool
def get_claim_status(claim_id: str) -> str:
    """
    Retrieve the status of a specific claim by claim ID.
    
    Args:
        claim_id: The claim identifier (e.g., 'C1001')
    
    Returns:
        Claim status, amount, procedure
    """
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT claim_id, procedure, claim_amount, status FROM claims WHERE claim_id = ?",
        (claim_id,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return f"Claim {row[0]}: {row[1]} - Status: {row[3]}, Amount: ${row[2]}"
    else:
        return f"Claim {claim_id} not found."


@tool
def get_plan_details(plan_id: str) -> str:
    """
    Retrieve full details of a specific insurance plan.
    
    Args:
        plan_id: The plan identifier (e.g., 'P101', 'P102')
    
    Returns:
        Complete plan details
    """
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT plan_id, plan_name, monthly_premium, annual_deductible, copay_pct FROM plans WHERE plan_id = ?",
        (plan_id,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return f"Plan {row[1]} (ID: {row[0]}): Monthly Premium: ${row[2]}, Annual Deductible: ${row[3]}, Copay: {row[4]}%"
    else:
        return f"Plan {plan_id} not found."

# ============================================================
# DEFINE MULTI-AGENT CREW WITH MEMORY CONTEXT
# ============================================================

def create_resilient_multi_agent_workflow(question: str, session_id: str):
    """
    Create workflow with MCP tools, memory context, and resilience.
    """
    
    # Load conversation memory
    memory = get_conversation_memory(session_id)
    memory_context = ""
    
    if memory["plan_id"]:
        memory_context = f"\nNote: Member is currently enrolled in {memory['plan_name']} (ID: {memory['plan_id']})."
    
    # Router Agent
    router_agent = Agent(
        role="Router",
        goal="Classify incoming questions and route to the appropriate specialist",
        backstory="You are an expert at understanding health insurance questions. Classify each question as coverage, claims, or enrollment, then route it to the right specialist.",
        tools=[],
        llm=llm,
        verbose=True
    )
    
    # Coverage Specialist with memory
    coverage_agent = Agent(
        role="Coverage Specialist",
        goal="Answer questions about coverage using member's plan history",
        backstory=f"You are a coverage expert. You understand plan details, deductibles, copays, and exclusions.{memory_context}",
        tools=[check_coverage, get_plan_details],
        llm=llm,
        verbose=True
    )
    
    # Claims Specialist with memory
    claims_agent = Agent(
        role="Claims Specialist",
        goal="Answer questions about claim status and processing",
        backstory=f"You are a claims expert.{memory_context}",
        tools=[get_claim_status, get_plan_details],
        llm=llm,
        verbose=True
    )
    
    # Task 1: Routing
    routing_task = Task(
        description=f"""Classify this question and decide which specialist should handle it:
        
Question: {question}

Respond ONLY with ONE of: "coverage", "claims", or "enrollment"
""",
        agent=router_agent,
        expected_output="One word: coverage, claims, or enrollment"
    )
    
    routing_crew = Crew(
        agents=[router_agent],
        tasks=[routing_task],
        verbose=True
    )
    
    print(f"\n{'='*80}")
    print(f"ROUTING QUESTION: {question}")
    print(f"{'='*80}")
    
    routing_result = routing_crew.kickoff()
    routing_decision = routing_result.strip().lower()
    
    print(f"\nROUTER DECISION: {routing_decision}")
    
    # Task 2: Specialist handling
    if "coverage" in routing_decision:
        specialist_task = Task(
            description=f"Answer this question about coverage: {question}",
            agent=coverage_agent,
            expected_output="A clear, accurate answer about coverage"
        )
        specialist_crew = Crew(
            agents=[coverage_agent],
            tasks=[specialist_task],
            verbose=True
        )
    elif "claims" in routing_decision:
        specialist_task = Task(
            description=f"Answer this question about claims: {question}",
            agent=claims_agent,
            expected_output="A clear, accurate answer about claims"
        )
        specialist_crew = Crew(
            agents=[claims_agent],
            tasks=[specialist_task],
            verbose=True
        )
    else:
        specialist_task = Task(
            description=f"Answer this question about enrollment: {question}",
            agent=coverage_agent,
            expected_output="A clear, accurate answer"
        )
        specialist_crew = Crew(
            agents=[coverage_agent],
            tasks=[specialist_task],
            verbose=True
        )
    
    print(f"\n{'='*80}")
    print(f"SPECIALIST TASK ({routing_decision.upper()})")
    print(f"{'='*80}")
    
    try:
        specialist_result = specialist_crew.kickoff()
    except Exception as e:
        print(f"Specialist error: {str(e)}")
        specialist_result = FALLBACK_MESSAGE
    
    # Update memory
    update_conversation_memory(session_id)
    
    return {
        "question": question,
        "routing_decision": routing_decision,
        "answer": specialist_result,
        "memory": memory
    }

# ============================================================
# TEST HARNESS
# ============================================================

if __name__ == "__main__":
    test_questions = [
        "What's the monthly premium for the Gold PPO plan?",
        "What is the status of claim C1001?",
        "Is weight loss surgery covered under any of our plans?",
        "How much would I pay out of pocket for a $500 MRI under the Silver HMO plan?",
        "Compare the deductibles of Gold PPO vs Silver HMO plans",
    ]
    
    session_id = "test-session-resilience"
    
    print("=" * 80)
    print("RESILIENT MULTI-AGENT ORCHESTRATION TEST - 5 QUESTIONS")
    print("=" * 80)
    
    results = []
    
    for i, question in enumerate(test_questions, 1):
        result = create_resilient_multi_agent_workflow(question, session_id)
        results.append(result)
        
        print(f"\n{'='*80}")
        print(f"Q{i} RESULT")
        print(f"Question: {result['question']}")
        print(f"Routed to: {result['routing_decision']}")
        print(f"Answer: {result['answer']}\n")
    
    print("\nAll tests completed with resilience and fallback handling active.")