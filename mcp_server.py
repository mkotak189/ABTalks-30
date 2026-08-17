import os
import json
import sqlite3
from typing import Any
import asyncio

from mcp.server.models import InitializationOptions
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# ============================================================
# INITIALIZE MCP SERVER
# ============================================================

server = Server("health-coverage-mcp")

# ============================================================
# DEFINE TOOLS
# ============================================================

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List all available tools."""
    return [
        types.Tool(
            name="check_coverage",
            description="Check if a specific procedure is covered under a given health plan. Returns coverage status and details.",
            inputSchema={
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
        ),
        types.Tool(
            name="get_claim_status",
            description="Retrieve the status of a specific claim by claim ID. Returns claim status, procedure, amount, and date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "claim_id": {
                        "type": "string",
                        "description": "The claim identifier (e.g., 'C1001')"
                    }
                },
                "required": ["claim_id"]
            }
        ),
        types.Tool(
            name="get_plan_details",
            description="Retrieve the full details of a specific insurance plan including premium, deductible, and copay information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan identifier (e.g., 'P101', 'P102', 'P103')"
                    }
                },
                "required": ["plan_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> Any:
    """Handle tool calls."""
    
    if name == "check_coverage":
        return check_coverage(arguments["plan_id"], arguments["procedure"])
    
    elif name == "get_claim_status":
        return get_claim_status(arguments["claim_id"])
    
    elif name == "get_plan_details":
        return get_plan_details(arguments["plan_id"])
    
    else:
        return f"Unknown tool: {name}"


# ============================================================
# TOOL IMPLEMENTATIONS
# ============================================================

def check_coverage(plan_id: str, procedure: str) -> str:
    """
    Check if procedure is covered under a plan.
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


def get_claim_status(claim_id: str) -> str:
    """
    Retrieve claim status from database.
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


def get_plan_details(plan_id: str) -> str:
    """
    Retrieve plan details from database.
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
# MAIN
# ============================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="health-coverage-mcp",
                server_version="1.0.0",
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())