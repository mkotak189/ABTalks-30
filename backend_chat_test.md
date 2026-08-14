# Backend Chat API Test — Day 16

## Test Setup
- Base URL: http://localhost:8000
- Session ID: test-session-1
- Member ID: M001
- 3 sequential messages with same session_id

## Endpoint Tests

### POST /chat — Message 1
**Request:** "What's the Gold PPO premium?"
- **Status:** 200 OK
- **Response time:** ~27 ms
- **Answer:** The monthly premium for the Gold PPO plan is $500/month.

### POST /chat — Message 2
**Request:** "What's the deductible?"
- **Status:** 200 OK
- **Response time:** ~40 ms
- **Answer:** Model asked for clarification on which plan's deductible (Gold PPO, Silver HMO, or Bronze HMO)

### POST /chat — Message 3
**Request:** "How do I file a claim?"
- **Status:** 200 OK
- **Response time:** ~35 ms
- **Answer:** Detailed step-by-step process for filing a claim (confirm coverage, gather documents, submit online/mail/fax, track status, appeal if needed)

## GET /history/{session_id}

**Request:** GET /history/test-session-1
- **Status:** 200 OK
- **Response:** All 6 turns stored (3 user + 3 assistant messages)
- **Timestamps:** Correct ISO format timestamps for each turn
- **Turn count:** 6 ✓

## Error Handling
- Invalid requests return 500 with error message ✓
- Missing session returns empty history with message ✓
- Timing logged for all requests ✓

## Summary
✓ POST /chat orchestrates retrieve → generate → store
✓ GET /history/{session_id} returns full conversation state
✓ Session management works across 3+ sequential messages
✓ Timing information captured for all requests
✓ Error handling functional