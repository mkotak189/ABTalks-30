import os
import json
from dotenv import load_dotenv
import sqlite3
from typing import Optional

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain import hub

load_dotenv()

# ============================================================
# INITIALIZE LLM
# ============================================================

llm = ChatAnthropic(model="claude-3-5-haiku-20241022")

# ============================================================
# DEFINE TOOLS AS LANGCHAIN TOOL OBJECTS
# ============================================================

@tool
def check_coverage(plan_id: str, procedure: str) -> str:
    """
    Check if a specific procedure is covered under a given plan.
    Returns coverage status and details.
    
    Args:
        plan_id: The plan identifier (e.g., 'P101' for Gold PPO, 'P102' for Silver HMO)
        procedure: The medical procedure to check (e.g., 'X-ray', 'surgery')
    
    Returns:
        Coverage status and details for the procedure under the plan
    """
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    # Get plan info
    cur.execute("SELECT plan_name FROM plans WHERE plan_id = ?", (plan_id,))
    plan_row = cur.fetchone()
    plan_name = plan_row[0] if plan_row else "Unknown Plan"
    
    # Check exclusions
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
        Claim status, amount, procedure, and date filed
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
        return f"Claim {claim_id} not found in the system."


@tool
def get_plan_details(plan_id: str) -> str:
    """
    Retrieve the full details of a specific insurance plan.
    Includes premium, deductible, and copay information.
    
    Args:
        plan_id: The plan identifier (e.g., 'P101', 'P102', 'P103')
    
    Returns:
        Complete plan details including premium, deductible, and copay percentage
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


@tool
def estimate_out_of_pocket_cost(plan_id: str, procedure: str, procedure_cost: Optional[float] = None) -> str:
    """
    Estimate the out-of-pocket cost for a procedure under a specific plan.
    
    Args:
        plan_id: The plan identifier
        procedure: The medical procedure
        procedure_cost: The total cost of the procedure before insurance (optional, defaults to $500)
    
    Returns:
        Estimated out-of-pocket cost breakdown
    """
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT annual_deductible, copay_pct FROM plans WHERE plan_id = ?",
        (plan_id,)
    )
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return f"Plan {plan_id} not found."
    
    deductible, copay_pct = row
    
    if procedure_cost is None:
        procedure_cost = 500
    
    estimated_cost = min(deductible, procedure_cost) + (procedure_cost * copay_pct / 100)
    breakdown = f"Estimated deductible portion: ${min(deductible, procedure_cost)}, copay ({copay_pct}%): ${procedure_cost * copay_pct / 100:.2f}, Total OOP: ${estimated_cost:.2f}"
    
    return breakdown


# ============================================================
# CREATE REACT AGENT
# ============================================================

tools = [check_coverage, get_claim_status, get_plan_details, estimate_out_of_pocket_cost]

# Use the standard ReAct prompt from LangChain hub
prompt = hub.pull("hwchase17/react")

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)

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
    
    print("=" * 80)
    print("LANGCHAIN REACT AGENT TEST - 5 QUESTIONS")
    print("=" * 80)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Q{i}: {question}")
        print("=" * 80)
        
        result = agent_executor.invoke({"input": question})
        print(f"\nFinal Answer: {result['output']}\n")