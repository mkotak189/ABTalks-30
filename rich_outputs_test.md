# Rich Outputs Test — Day 19

## Test Setup
- 3 sequential questions to test citations + card rendering
- Session ID: same across all 3 messages
- Goal: Confirm markdown, citations, and cards render correctly

## Test 1: Policy Citations
**Question:** "What's covered under the Gold PPO plan?"
- Expected: Answer about coverage + "Policy Sources" expandable showing chunk IDs
- Result: ✅ Citations displayed correctly

## Test 2: Claim Status Card
**Question:** "What is the status of claim C1001?"
- Expected: Answer mentioning claim status + formatted claim card showing:
  - Claim ID
  - Status (Approved/Pending/Denied)
  - Amount
  - Procedure
- Result: ✅ Card rendered with borders/spacing

## Test 3: Coverage Summary Card
**Question:** "Compare the Silver HMO plan details."
- Expected: Answer + formatted plan card showing:
  - Plan name
  - Deductible
  - Copay %
  - Coverage status
- Result: ✅ Card styled and readable

## Markdown Rendering Checklist
- [ ] Bullet lists render correctly in chat
- [ ] Tables display properly in messages
- [ ] Code blocks (if any) are formatted
- [ ] Bold/italic text works
- [ ] Numbered lists work
- [ ] Expandable sections work

## Summary
All 3 question types tested. Citations + cards working end-to-end.