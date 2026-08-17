# MCP Server Test Notes — Day 23

## Setup

### Installation
```bash
pip install mcp
```

### Server Registration

#### Option A: Claude Desktop (Mac/Windows)
1. Locate Claude Desktop config file:
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. Add MCP server to config:
```json
{
  "mcpServers": {
    "health-coverage": {
      "command": "python",
      "args": ["/path/to/ABTalks-30/mcp_server.py"]
    }
  }
}
```

3. Restart Claude Desktop

#### Option B: Cline (VS Code Extension)
1. In VS Code, open Cline settings (gear icon in Cline panel)
2. Navigate to "MCP Servers"
3. Add new server:
   - Name: `health-coverage`
   - Command: `python /path/to/ABTalks-30/mcp_server.py`
4. Reload Cline panel

---

## Test Run: Tool Call Confirmation

### Test 1: Check Coverage Tool
**Setup:**
- MCP server running: `python mcp_server.py`
- Claude Desktop restarted (or Cline reloaded)

**Test Question to Claude:** "Is physical therapy covered under the Gold PPO plan?"

**Expected Flow:**
1. Claude reads available tools from MCP server
2. Claude identifies `check_coverage` as relevant
3. Claude calls: `check_coverage(plan_id="P101", procedure="physical therapy")`
4. MCP server queries `coverage.db`
5. Returns: "physical therapy is covered under Gold PPO..."
6. Claude presents answer to user

**Observed Result:**
✅ Tool call successful
- Tool name: `check_coverage`
- Arguments: `{"plan_id": "P101", "procedure": "physical therapy"}`
- Response: "physical therapy is covered under Gold PPO. Please review your plan documents for copay and coinsurance details."

---

### Test 2: Claim Status Tool
**Test Question to Claude:** "What's the status of claim C1001?"

**Expected Flow:**
1. Claude reads tools from MCP server
2. Claude identifies `get_claim_status` as relevant
3. Claude calls: `get_claim_status(claim_id="C1001")`
4. MCP server queries `coverage.db`
5. Returns: "Claim C1001: Lab work - Status: Pending, Amount: $250"

**Observed Result:**
✅ Tool call successful
- Tool name: `get_claim_status`
- Arguments: `{"claim_id": "C1001"}`
- Response: "Claim C1001: Lab work - Status: Pending, Amount: $250"

---

### Test 3: Plan Details Tool
**Test Question to Claude:** "Tell me about the Silver HMO plan."

**Expected Flow:**
1. Claude reads tools from MCP server
2. Claude identifies `get_plan_details` as relevant
3. Claude calls: `get_plan_details(plan_id="P102")`
4. MCP server queries `coverage.db`
5. Returns plan details

**Observed Result:**
✅ Tool call successful
- Tool name: `get_plan_details`
- Arguments: `{"plan_id": "P102"}`
- Response: "Plan Silver HMO (ID: P102): Monthly Premium: $350, Annual Deductible: $500, Copay: 20%"

---

## Server Manifest (Exposed to Clients)

The MCP server automatically advertises these tools:

| Tool | Description | Required Args |
|---|---|---|
| `check_coverage` | Check procedure coverage by plan | plan_id, procedure |
| `get_claim_status` | Retrieve claim status by ID | claim_id |
| `get_plan_details` | Fetch full plan details | plan_id |

---

## Key Observations

1. **Tool Discovery:** Claude Desktop and Cline automatically discovered all 3 tools from the MCP server
2. **Tool Selection:** LLM correctly chose which tool to call based on question type
3. **Data Accuracy:** Tool responses matched database queries (✅ verified against coverage.db)
4. **Schema Compliance:** All tool arguments matched MCP schema definitions
5. **Response Format:** MCP server returned plain text strings, properly formatted for LLM consumption

---

## Troubleshooting Notes

### Issue: "Tool not found" or tools not appearing
**Solution:** 
- Verify config file path and JSON syntax
- Restart Claude Desktop completely (not just close tab)
- Check that `mcp_server.py` path in config is absolute, not relative

### Issue: Server crashes when tool is called
**Solution:**
- Verify `coverage.db` exists in repo root
- Check database schema matches tool queries
- Run: `sqlite3 coverage.db ".tables"` to verify plans/claims tables exist

### Issue: Slow tool calls (>5 seconds)
**Solution:**
- Normal for first query (server startup)
- Subsequent calls should be <500ms
- If persistent, check SQLite indexes on `plan_id` and `claim_id`

---

## Conclusion

✅ MCP server successfully exposes health insurance tools to Claude Desktop and Cline
✅ All 3 tools functional and discoverable
✅ Tool calls work end-to-end
✅ Integration ready for production use

The MCP approach allows Claude Desktop and other AI clients to access your coverage database without API hosting or authentication complexity. Useful for local-first, privacy-preserving AI workflows.