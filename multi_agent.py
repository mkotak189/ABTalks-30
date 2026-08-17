import os
import json
from dotenv import load_dotenv
import sqlite3
from typing import Optional

from crewai import Agent, Task, Crew
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool

load_dotenv()

# ============================================================
# INITIALIZE LLM
# ============================================================

llm = ChatAnthropic(model="claude-3-5-haiku-20241022")

# ============================================================
# DEFINE TOOLS (reused from Day 21)
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
        Claim status, amount, procedure, and date
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
    Includes premium, deductible, and copay information.
    
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


@tool
def estimate_out_of_pocket_cost(plan_id: str, procedure: str, procedure_cost: Optional[float] = None) -> str:
    """
    Estimate the out-of-pocket cost for a procedure under a specific plan.
    
    Args:
        plan_id: The plan identifier
        procedure: The medical procedure
        procedure_cost: The total cost before insurance (optional)
    
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
# DEFINE MULTI-AGENT CREW
# ============================================================

# Agent 1: ROUTER (classifies question type)
router_agent = Agent(
    role="Router",
    goal="Classify incoming questions and route to the appropriate specialist",
    backstory="You are an expert at understanding health insurance questions. Your job is to classify each question as either about coverage, claims, or enrollment, then route it to the right specialist.",
    tools=[],  # Router doesn't use tools directly
    llm=llm,
    verbose=True
)

# Agent 2: COVERAGE SPECIALIST
coverage_agent = Agent(
    role="Coverage Specialist",
    goal="Answer questions about what medical procedures and services are covered under health plans",
    backstory="You are a coverage expert. You understand plan details, deductibles, copays, and exclusions. Use your tools to look up coverage information and provide clear, accurate answers.",
    tools=[check_coverage, get_plan_details, estimate_out_of_pocket_cost],
    llm=llm,
    verbose=True
)

# Agent 3: CLAIMS SPECIALIST
claims_agent = Agent(
    role="Claims Specialist",
    goal="Answer questions about claim status, processing, and appeals",
    backstory="You are a claims expert. You know how to look up claim statuses and explain claim processes. Use your tools to retrieve claim information and provide clear updates.",
    tools=[get_claim_status, get_plan_details],
    llm=llm,
    verbose=True
)

# ============================================================
# DEFINE TASKS AND CREW
# ============================================================

def create_multi_agent_workflow(question: str):
    """
    Create a workflow for a single question:
    1. Router classifies the question
    2. Appropriate specialist answers it
    """
    
    # Task 1: Router classifies the question
    routing_task = Task(
        description=f"""Classify this question and decide which specialist should handle it:
        
Question: {question}

Respond ONLY with ONE of: "coverage", "claims", or "enrollment"
""",
        agent=router_agent,
        expected_output="One word: coverage, claims, or enrollment"
    )
    
    # Create crew with router only first
    routing_crew = Crew(
        agents=[router_agent],
        tasks=[routing_task],
        verbose=True
    )
    
    # Run router
    print(f"\n{'='*80}")
    print(f"ROUTING QUESTION: {question}")
    print(f"{'='*80}")
    
    routing_result = routing_crew.kickoff()
    routing_decision = routing_result.strip().lower()
    
    print(f"\nROUTER DECISION: {routing_decision}")
    
    # Task 2: Route to appropriate specialist
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
    else:  # enrollment
        specialist_task = Task(
            description=f"Answer this question about enrollment: {question}",
            agent=coverage_agent,  # Use coverage agent as fallback
            expected_output="A clear, accurate answer"
        )
        specialist_crew = Crew(
            agents=[coverage_agent],
            tasks=[specialist_task],
            verbose=True
        )
    
    # Run specialist
    print(f"\n{'='*80}")
    print(f"SPECIALIST TASK ({routing_decision.upper()})")
    print(f"{'='*80}")
    
    specialist_result = specialist_crew.kickoff()
    
    return {
        "question": question,
        "routing_decision": routing_decision,
        "answer": specialist_result
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
    
    print("=" * 80)
    print("MULTI-AGENT ORCHESTRATION TEST - 5 QUESTIONS")
    print("=" * 80)
    
    results = []
    
    for i, question in enumerate(test_questions, 1):
        result = create_multi_agent_workflow(question)
        results.append(result)
        
        print(f"\n{'='*80}")
        print(f"Q{i} RESULT")
        print(f"Question: {result['question']}")
        print(f"Routed to: {result['routing_decision']}")
        print(f"Answer: {result['answer']}\n")
    
    # Save results to file
    with open("multi_agent_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to multi_agent_results.json")