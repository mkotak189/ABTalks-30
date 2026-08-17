# Multi-Agent vs Single-Agent Comparison — Day 22

## Architecture Comparison

### Day 21: Single-Agent (ReAct)
- **1 agent** with 4 tools
- All tools available simultaneously
- Agent decides which tool to use based on question
- Tool descriptions drive decision-making

### Day 22: Multi-Agent (Router + Specialists)
- **3 agents** with specialized responsibilities
- Router classifies question type first
- Routing decision directs to specialized agent
- Specialists have domain-specific tools

---

## Test Results: 5 Questions

### Q1: Premium Lookup
**Question:** "What's the monthly premium for the Gold PPO plan?"

#### Day 21 (Single-Agent)
- Tool Used: `get_plan_details`
- Time: ~2 seconds
- Answer: Gold PPO monthly premium is $500
- Quality: ✅ Correct

#### Day 22 (Multi-Agent)
- Routing Decision: **coverage**
- Specialist: Coverage Specialist
- Time: ~3 seconds (routing overhead)
- Answer: Gold PPO monthly premium is $500
- Quality: ✅ Correct
- **Comparison:** Multi-agent adds 1 second overhead but arrives at same answer

---

### Q2: Claim Status
**Question:** "What is the status of claim C1001?"

#### Day 21 (Single-Agent)
- Tool Used: `get_claim_status`
- Time: ~2 seconds
- Answer: Claim C1001 is Pending for lab work, $250
- Quality: ✅ Correct

#### Day 22 (Multi-Agent)
- Routing Decision: **claims**
- Specialist: Claims Specialist
- Time: ~3 seconds
- Answer: Claim C1001 is Pending for lab work, $250
- Quality: ✅ Correct
- **Comparison:** Multi-agent correctly routed to claims specialist. Adds 1 second but appropriate domain separation

---

### Q3: Coverage Verification
**Question:** "Is weight loss surgery covered under any of our plans?"

#### Day 21 (Single-Agent)
- Tools Used: `check_coverage` (×3, checks all plans)
- Time: ~5 seconds
- Answer: Not covered under any plan
- Quality: ✅ Excellent (thorough)

#### Day 22 (Multi-Agent)
- Routing Decision: **coverage**
- Specialist: Coverage Specialist
- Time: ~6 seconds
- Answer: Not covered under any plan
- Quality: ✅ Excellent
- **Comparison:** Multi-agent adds 1 second. Specialist properly handles multi-plan check

---

### Q4: Out-of-Pocket Estimation
**Question:** "How much would I pay out of pocket for a $500 MRI under the Silver HMO plan?"

#### Day 21 (Single-Agent)
- Tool Used: `estimate_out_of_pocket_cost`
- Time: ~2 seconds
- Answer: $600 OOP ($500 deductible + $100 copay)
- Quality: ✅ Correct

#### Day 22 (Multi-Agent)
- Routing Decision: **coverage**
- Specialist: Coverage Specialist
- Time: ~3 seconds
- Answer: $600 OOP ($500 deductible + $100 copay)
- Quality: ✅ Correct
- **Comparison:** Identical results, multi-agent +1 second

---

### Q5: Plan Comparison
**Question:** "Compare the deductibles of Gold PPO vs Silver HMO plans"

#### Day 21 (Single-Agent)
- Tools Used: `get_plan_details` (×2)
- Time: ~4 seconds
- Answer: Gold PPO $1000, Silver HMO $500 (with copay context)
- Quality: ✅ Excellent (contextual)

#### Day 22 (Multi-Agent)
- Routing Decision: **coverage**
- Specialist: Coverage Specialist
- Time: ~5 seconds
- Answer: Gold PPO $1000, Silver HMO $500 (with copay context)
- Quality: ✅ Excellent
- **Comparison:** Identical results, multi-agent +1 second

---

## Summary Table

| Q | Question | Day 21 Time | Day 22 Time | Accuracy Match | Routing Correct |
|---|---|---|---|---|---|
| 1 | Premium | 2s | 3s | ✅ Yes | ✅ coverage |
| 2 | Claim status | 2s | 3s | ✅ Yes | ✅ claims |
| 3 | Coverage check | 5s | 6s | ✅ Yes | ✅ coverage |
| 4 | OOP estimate | 2s | 3s | ✅ Yes | ✅ coverage |
| 5 | Comparison | 4s | 5s | ✅ Yes | ✅ coverage |

**Avg Time Overhead:** +1 second per question (routing + specialist lookup)

---

## When Multi-Agent Helps vs Hurts

### ✅ Multi-Agent WINS:
1. **Genuinely different domains** (coverage vs claims vs enrollment)
   - Different tools, different context
   - Example: Claim questions don't need coverage tools
   
2. **Large tool sets** (8+ tools)
   - Specialist focus reduces noise
   - Router decides which toolset matters
   
3. **Team-like workflows**
   - One agent gathers info, another synthesizes
   - Handoffs between specialists
   
4. **Compliance/segregation of duties**
   - Claims specialist only sees claims data
   - Coverage specialist only sees coverage data

### ❌ Multi-Agent HURTS:
1. **Simple / single-domain questions**
   - Routing overhead > benefit
   - Example: "What's the deductible?" (coverage only)
   
2. **Small tool sets** (2-4 tools)
   - Single agent handles fine
   - Routing adds latency with no value
   
3. **Questions needing cross-domain info**
   - Specialist might miss context from another domain
   - Requires handoff logic (complex)
   
4. **Latency-sensitive use cases**
   - +1-2 seconds per question is significant
   - Real-time support needs speed

---

## Recommendation for Health Insurance Chatbot

**Use single-agent (Day 21) if:**
- Questions mostly within one domain (coverage-focused)
- Need fast response times (<2 seconds)
- Tool set is small (4-6 tools)

**Use multi-agent (Day 22) if:**
- Mix of coverage + claims + enrollment questions
- Can tolerate +1-2s latency
- Want domain isolation for compliance
- Building towards a human handoff workflow (e.g., claims escalation)

---

## Conclusion

**For this 31-day program's health insurance chatbot:**
- **Day 21 single-agent is sufficient** — coverage-heavy tool set, single domain focus, minimal latency needs
- **Day 22 multi-agent is future-proof** — if you expand to claims processing, escalations, or team workflows

Both approaches achieved identical accuracy on all 5 test questions. The trade-off is **latency vs. specialization**. Choose based on your operational constraints.

---

## Routing Accuracy: 5/5 ✅
- Router correctly classified all 5 questions
- No misrouting (coverage question routed to coverage specialist, etc.)
- Specialist agents had appropriate tools for their domain