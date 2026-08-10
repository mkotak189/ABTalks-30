import os
import json
from typing import Optional
from dotenv import load_dotenv
import openai
from pydantic import BaseModel, ValidationError
from retrieval_engine import retrieve
import sqlite3

load_dotenv()

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# ============================================================
# PYDANTIC MODELS (validation for tool responses)
# ============================================================

class CoverageResult(BaseModel):
    plan_id: str
    procedure: str
    covered: bool
    details: str

class ClaimStatusResult(BaseModel):
    claim_id: str
    status: str
    amount: float
    procedure: str

class PlanDetailsResult(BaseModel):
    plan_id: str
    plan_name: str
    monthly_premium: float
    annual_deductible: float
    copay_pct: float

class OutOfPocketResult(BaseModel):
    plan_id: str
    procedure: str
    estimated_cost: float
    breakdown: str

# ============================================================
# TOOL SCHEMAS (passed to the LLM)
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_coverage",
            "description": "Check if a specific procedure is covered under a given plan. Returns coverage status and details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan identifier (e.g., 'P101' for Gold PPO, 'P102' for Silver HMO, 'P103' for Bronze HMO)"
                    },
                    "procedure": {
                        "type": "string",
                        "description": "The medical procedure to check (e.g., 'X-ray', 'surgery', 'physical therapy')"
                    }
                },
                "required": ["plan_id", "procedure"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_claim_status",
            "description": "Retrieve the status of a specific claim by claim ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {
                        "type": "string",
                        "description": "The claim identifier (e.g., 'C1001')"
                    }
                },
                "required": ["claim_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_plan_details",
            "description": "Retrieve the full details of a specific insurance plan including premium, deductible, and copay information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan identifier (e.g., 'P101', 'P102', 'P103')"
                    }
                },
                "required": ["plan_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_out_of_pocket_cost",
            "description": "Estimate the out-of-pocket cost for a procedure under a specific plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan identifier"
                    },
                    "procedure": {
                        "type": "string",
                        "description": "The medical procedure"
                    },
                    "procedure_cost": {
                        "type": "number",
                        "description": "The total cost of the procedure before insurance (optional)"
                    }
                },
                "required": ["plan_id", "procedure"]
            }
        }
    }
]

# ============================================================
# TOOL IMPLEMENTATIONS (mock data from Day 4)
# ============================================================

def check_coverage(plan_id: str, procedure: str) -> CoverageResult:
    """Check if procedure is covered."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    # Get plan info
    cur.execute("SELECT plan_name FROM plans WHERE plan_id = ?", (plan_id,))
    plan_row = cur.fetchone()
    plan_name = plan_row[0] if plan_row else "Unknown Plan"
    
    # Check exclusions list
    excluded = ["cosmetic surgery", "dental care", "long-term care", "weight loss programs"]
    procedure_lower = procedure.lower()
    
    if any(excl in procedure_lower for excl in excluded):
        covered = False
        details = f"{procedure} is listed as an excluded service under {plan_name}."
    else:
        covered = True
        details = f"{procedure} is covered under {plan_name}. Please review your plan documents for copay and coinsurance details."
    
    conn.close()
    return CoverageResult(plan_id=plan_id, procedure=procedure, covered=covered, details=details)

def get_claim_status(claim_id: str) -> ClaimStatusResult:
    """Retrieve claim status from database."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("SELECT claim_id, procedure, claim_amount, status FROM claims WHERE claim_id = ?", (claim_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return ClaimStatusResult(
            claim_id=row[0],
            status=row[3],
            amount=row[2],
            procedure=row[1]
        )
    else:
        raise ValueError(f"Claim {claim_id} not found")

def get_plan_details(plan_id: str) -> PlanDetailsResult:
    """Retrieve plan details from database."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT plan_id, plan_name, monthly_premium, annual_deductible, copay_pct FROM plans WHERE plan_id = ?",
        (plan_id,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return PlanDetailsResult(
            plan_id=row[0],
            plan_name=row[1],
            monthly_premium=row[2],
            annual_deductible=row[3],
            copay_pct=row[4]
        )
    else:
        raise ValueError(f"Plan {plan_id} not found")

def estimate_out_of_pocket_cost(plan_id: str, procedure: str, procedure_cost: Optional[float] = None) -> OutOfPocketResult:
    """Estimate out-of-pocket cost for a procedure."""
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    
    cur.execute("SELECT annual_deductible, copay_pct FROM plans WHERE plan_id = ?", (plan_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        raise ValueError(f"Plan {plan_id} not found")
    
    deductible, copay_pct = row
    
    if procedure_cost is None:
        procedure_cost = 500  # Mock default
    
    # Simplified estimate: deductible + copay
    estimated_cost = min(deductible, procedure_cost) + (procedure_cost * copay_pct / 100)
    
    breakdown = f"Estimated deductible portion: ${min(deductible, procedure_cost)}, copay ({copay_pct}%): ${procedure_cost * copay_pct / 100}"
    
    return OutOfPocketResult(
        plan_id=plan_id,
        procedure=procedure,
        estimated_cost=estimated_cost,
        breakdown=breakdown
    )

# ============================================================
# TOOL EXECUTION DISPATCHER
# ============================================================

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and validate output with Pydantic."""
    try:
        if tool_name == "check_coverage":
            result = check_coverage(**tool_input)
        elif tool_name == "get_claim_status":
            result = get_claim_status(**tool_input)
        elif tool_name == "get_plan_details":
            result = get_plan_details(**tool_input)
        elif tool_name == "estimate_out_of_pocket_cost":
            result = estimate_out_of_pocket_cost(**tool_input)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        # Validate with Pydantic (already done in return statement above)
        return json.dumps(result.model_dump())
    except ValidationError as e:
        return json.dumps({"error": f"Validation error: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ============================================================
# MAIN FUNCTION CALLING LOOP
# ============================================================

def answer_with_tools(question: str) -> dict:
    """Full loop: LLM decides if tools are needed, executes them, then answers."""
    
    # Step 1: Get retrieval context (still needed for grounding)
    retrieval_result = retrieve(question)
    context = "\n".join(f"- {c}" for c in retrieval_result["merged_context"]) if retrieval_result["merged_context"] else "(no context)"
    
    # Step 2: First LLM call with tools
    system_prompt = """You are a compassionate health insurance coverage assistant committed to accuracy and clarity.

Your responsibilities:
1. Answer ONLY using information from the provided context or by calling available tools
2. Be warm and understanding—members often have stressful questions about medical costs
3. Be precise about coverage—do not speculate or infer what isn't explicitly stated
4. Refuse medical advice—redirect diagnosis or treatment questions to a licensed healthcare provider
5. Admit information gaps—if you don't have the answer, say so clearly and suggest contacting support

Before answering, briefly identify: (a) which plan is being asked about, (b) what section (coverage/claims/exclusions/enrollment) is relevant.

Important disclaimer: This is not medical advice. Coverage details may vary by your specific plan, rider, or enrollment date. For complex questions or exceptions, please contact support.

If the question would benefit from calling a tool (e.g., to check specific claim status, plan details, or coverage), call the appropriate tool. Otherwise, answer based on context alone."""
    
    messages = [
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    
    tool_calls_made = []
    max_iterations = 5  # Maximum tool calls before stopping
    iteration = 0
    final_answer = None
    
    # Agentic loop: keep calling LLM until it stops requesting tools
    while iteration < max_iterations:
        iteration += 1
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            stream=False,
        )
        
        # Check if model wants to call a tool
        if response.choices[0].finish_reason == "tool_calls" and response.choices[0].message.tool_calls:
            # Execute each tool call
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                tool_result = execute_tool(tool_name, tool_input)
                
                tool_calls_made.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": json.loads(tool_result)
                })
                
                # Add tool result back to messages for next iteration
                messages.append({"role": "assistant", "content": response.choices[0].message.content or ""})
                messages.append({
                    "role": "user",
                    "content": f"Tool {tool_name} returned: {tool_result}"
                })
        else:
            # Model is done with tools, extract final answer
            final_answer = response.choices[0].message.content
            break
    
    # If loop ended without breaking (hit max iterations), get whatever answer is there
    if final_answer is None:
        final_answer = response.choices[0].message.content if response else "Unable to generate answer after maximum tool calls"
    
    return {
        "question": question,
        "tool_calls": tool_calls_made,
        "answer": final_answer,
        "used_tools": len(tool_calls_made) > 0
    }

# ============================================================
# TEST HARNESS
# ============================================================

if __name__ == "__main__":
    # 5 tool-triggering questions + 1 no-tool control
    TEST_QUESTIONS = [
        "What's the monthly premium for the Gold PPO plan?",  # → get_plan_details
        "What is the status of claim C1001?",                 # → get_claim_status
        "Is weight loss surgery covered?",                     # → check_coverage
        "How much would I pay out of pocket for an X-ray under Silver HMO if it costs $500?",  # → estimate_out_of_pocket_cost
        "How do I file a claim?",                              # → NO TOOL (retrieval only)
        "Is maternity care covered under Bronze HMO?",         # → check_coverage
    ]
    
    log = []
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'='*70}")
        print(f"Q{i}: {question}")
        result = answer_with_tools(question)
        
        print(f"Used tools: {result['used_tools']}")
        if result['tool_calls']:
            for tc in result['tool_calls']:
                print(f"  → {tc['tool']}({tc['input']}) = {tc['result']}")
        print(f"Answer: {result['answer'][:200]}...")
        
        log.append(result)
    
    # Write log
    with open("tool_call_log.md", "w") as f:
        f.write("# Tool Calling Log — Day 13\n\n")
        for i, result in enumerate(log, 1):
            f.write(f"## Q{i}: {result['question']}\n")
            f.write(f"**Tools called:** {len(result['tool_calls'])}\n")
            if result['tool_calls']:
                for tc in result['tool_calls']:
                    f.write(f"- {tc['tool']}({tc['input']}) → {tc['result']}\n")
            f.write(f"**Answer:** {result['answer']}\n\n")
    
    print("\n\nTool calls logged to tool_call_log.md")