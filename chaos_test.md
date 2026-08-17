# Chaos Test: Resilience & Fallback Validation — Day 24

## Test Objective
Verify that broken tools trigger fallback gracefully without exposing raw errors to users.

---

## Test Setup

**Configuration:**
- Timeout: 10 seconds per tool call
- Max Retries: 1 (retry once on failure, then fallback)
- Fallback Message: "I'm having trouble accessing that information right now. Please contact member support at 1-800-XXX-XXXX for assistance."

**Baseline (All Tools Working):**
- ✅ 5 questions answered accurately
- ✅ Tools responding in <1 second each
- ✅ No fallbacks triggered

---

## Chaos Scenario 1: Broken Tool (Simulate Database Unavailable)

### Setup
Temporarily break `check_coverage` function:
```python
# BEFORE (working):
def check_coverage(plan_id: str, procedure: str) -> str:
    conn = sqlite3.connect("coverage.db")
    ...

# AFTER (broken - simulate DB unavailable):
def check_coverage(plan_id: str, procedure: str) -> str:
    raise Exception("Database connection refused")
    # Intentional failure
```

### Test Question
"Is physical therapy covered under the Gold PPO plan?"

### Expected Behavior
1. Router classifies as "coverage"
2. Coverage Specialist calls `check_coverage` tool
3. Tool raises exception
4. Timeout/retry logic activates:
   - Attempt 1: Fails with database error
   - Retry delay: 1 second
   - Attempt 2 (MAX_RETRIES=1): Fails again
5. Fallback triggered
6. Member receives: "I'm having trouble accessing that information right now. Please contact member support..."

### Observed Result
**✅ PASS**
- Tool error caught at attempt 1
- Retry attempted at 1-second delay
- Failed at attempt 2
- Fallback message returned (no raw error exposed)
- Member-friendly message displayed
- No traceback or 500 status code sent to UI

---

## Chaos Scenario 2: Timeout Test (Simulate Slow Database)

### Setup
Inject artificial delay into `get_plan_details`:
```python
import time

def get_plan_details(plan_id: str) -> str:
    time.sleep(15)  # 15 seconds > 10 second timeout
    conn = sqlite3.connect("coverage.db")
    ...
```

### Test Question
"Tell me about the Silver HMO plan."

### Expected Behavior
1. Router classifies as "coverage"
2. Coverage Specialist calls `get_plan_details`
3. Tool starts but takes 15 seconds (exceeds 10-second timeout)
4. `asyncio.wait_for()` raises `TimeoutError`
5. Retry logic activates:
   - Attempt 1: Timeout at 10 seconds
   - Retry delay: 1 second
   - Attempt 2: Timeout again at 10 seconds
6. Fallback triggered after ~21 seconds total

### Observed Result
**✅ PASS**
- Timeout detected at 10 seconds (not 15)
- Retry occurred at 1-second delay
- Second attempt also timed out
- Fallback activated gracefully
- User received friendly message within ~22 seconds
- No raw timeout exception exposed

---

## Chaos Scenario 3: Recovery Test (Tool Restored)

### Setup
Fix the broken `check_coverage` tool:
```python
# Restore to working state:
def check_coverage(plan_id: str, procedure: str) -> str:
    conn = sqlite3.connect("coverage.db")
    cur = conn.cursor()
    # ... (normal implementation)
```

### Test Question
"Is physical therapy covered under the Gold PPO plan?"

### Expected Behavior
1. Tool now working
2. `check_coverage` executes successfully
3. Result returned within timeout window
4. No retry or fallback needed

### Observed Result
**✅ PASS**
- Tool call succeeded on first attempt
- Response time: <1 second
- Accurate coverage information returned
- No fallback triggered
- Normal flow resumed

---

## Failure Modes Tested

| Scenario | Trigger | Detection | Outcome | Member Sees |
|---|---|---|---|---|
| Tool Exception | Broken function | Try/except in resilience wrapper | Retry → Fallback | Friendly message |
| Timeout | Slow DB | asyncio.wait_for timeout | Retry → Fallback | Friendly message |
| Max Retries Exceeded | Persistent failure | Attempt counter | Fallback | Friendly message |
| Tool Recovery | Fix function | Successful execution | Normal response | Accurate answer |

---

## Resilience Metrics

**Timeout Configuration:**
- Per-tool timeout: 10 seconds
- Retry delay: 1 second
- Max retry attempts: 1 (total attempts: 2)
- Total failure window: ~22 seconds max

**Fallback Quality:**
- ✅ User-friendly message
- ✅ Actionable (contact support)
- ✅ No technical jargon
- ✅ No raw error codes/tracebacks
- ✅ No 500 status codes exposed

**Recovery:**
- ✅ Tool restoration automatically detected
- ✅ No manual restart required
- ✅ Immediate return to normal operation

---

## Conclusion

**Resilience Test Result: PASS ✅**

All three chaos scenarios confirmed:
1. **Graceful fallback works** — Broken tools don't crash the system
2. **Timeouts are enforced** — No indefinite hangs
3. **Retry logic functions** — Transient failures get a second chance
4. **Recovery is automatic** — Fixed tools resume operation immediately

**Member Experience:**
- No exposure to raw errors
- Friendly, actionable fallback messages
- Predictable timeout behavior
- No data corruption or partial responses

The multi-agent chatbot with MCP tools, memory, and resilience fallbacks is production-ready.