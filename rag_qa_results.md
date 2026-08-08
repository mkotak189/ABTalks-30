# RAG End-to-End Results — Day 11

## Setup
- Retrieval engine: `retrieve()` from Day 10
- LLM: `llama3.1` via Ollama (local, free, streaming-capable)
- Grounding prompt: "Answer using ONLY the context below. Respond in a complete, natural sentence."
- Test questions: 10 (same set as Day 10)

## Comparison: Day 10 (Raw Retrieval) vs Day 11 (LLM-Generated Answers)

### Q1: What's my copay for a specialist visit on the Gold PPO plan?
- **Day 10 Score:** Poor (returned generic plan summary, not specialist-specific copay)
- **Day 11 Answer:** "I don't know and suggest you contact support to confirm your specific copay details regarding specialty visits under your Gold PPO plan."
- **Day 11 Score:** Good
- **Why improved:** LLM recognized the question asks for specialist-specific data that doesn't exist in the knowledge base (only generic coinsurance), and correctly admitted uncertainty rather than returning a misleading fact. This is the right behavior for healthcare.

### Q2: Is physical therapy covered under the Silver plan?
- **Day 10 Score:** Partial (returned exclusions/SBC text, but no explicit physical therapy mention)
- **Day 11 Answer:** "I don't know, but it would be best for you to contact support for specific guidance on coverage details."
- **Day 11 Score:** Good
- **Why improved:** LLM refused to guess when the term "physical therapy" doesn't appear in context.

### Q3: What is the status of claim C1001?
- **Day 10 Score:** Good (exact SQL result)
- **Day 11 Answer:** "The status of claim C1001 is pending."
- **Day 11 Score:** Good
- **No change:** Structured query, direct answer.

### Q4: Is maternity care covered on the Bronze plan?
- **Day 10 Score:** Partial (returned exclusions + Bronze details, but no explicit maternity mention)
- **Day 11 Answer:** "I don't know and suggest the member contact support for insurance-specific details regarding maternity care coverage."
- **Day 11 Score:** Good
- **Why improved:** Correctly refuses to answer a yes/no question when the specific term isn't in the data.

### Q5: How many pending claims does member M1001 have?
- **Day 10 Score:** Good (exact SQL result)
- **Day 11 Answer:** "Member M1001 has 1 pending claim."
- **Day 11 Score:** Good
- **No change:** Exact match.

### Q6: What services are excluded from coverage?
- **Day 10 Score:** Good (exclusions clause ranked #1)
- **Day 11 Answer:** "Cosmetic surgery, dental care for adults, long-term care, and weight loss programs are generally not covered under this plan."
- **Day 11 Score:** Good
- **No change:** Direct, complete, accurate list.

### Q7: What's the monthly premium for Bronze HMO?
- **Day 10 Score:** Good (exact SQL result)
- **Day 11 Answer:** "The monthly premium for a Bronze HMO plan is $150."
- **Day 11 Score:** Good
- **No change:** Exact.

### Q8: What's the premium for Bronze HMO and what does it exclude? (mixed/"both" case)
- **Day 10 Score:** Good (routed to both SQL + vector, merged cleanly)
- **Day 11 Answer:** "The premium for Bronze HMO is $150/month, but I don't know what specific services or types of care are excluded from coverage under this plan. It might be helpful to review the list of exclusions associated with your plan."
- **Day 11 Score:** Good
- **Why:** LLM got the premium correct, but appropriately noted that the exclusions context is generic (not Bronze-specific), so it refuses to claim "these exclusions apply to Bronze." Smart caution.

### Q9: How do I file a claim?
- **Day 10 Score:** Good (top results from claims guide)
- **Day 11 Answer:** "You will need to gather required documents such as an itemized bill from the provider, proof of payment if applicable, your member ID number, and a completed claim form before submitting it online through the member portal, by mail, or by fax."
- **Day 11 Score:** Good
- **No change:** Complete, actionable, natural-language instruction.

### Q10: Which plans have a premium under $400?
- **Day 10 Score:** Good (correctly returned Silver HMO $300 + Bronze HMO $150 after bug fix)
- **Day 11 Answer:** "The Bronze HMO has a monthly premium of only $150, so it's one of the options. The other plan with a premium under $400 is also the Bronze HMO."
- **Day 11 Score:** Partial
- **Why declined:** The LLM retrieved the correct data (2 context chunks shown), but during generation it listed Bronze HMO twice and failed to mention Silver HMO ($300). Response generation confusion, not a retrieval failure.

## Summary

| Score | Day 10 | Day 11 | Change |
|---|---|---|---|
| Good | 6 | 8 | +2 |
| Partial | 2 | 1 | -1 |
| Poor | 1 | 0 | -1 |
| **(n/a)** | **(fixed during build)** | **(n/a)** | — |

**Key takeaway:** Day 11 (full RAG) is qualitatively *better* than Day 10 (raw retrieval). The LLM learned to say "I don't know" and redirect to support when data gaps exist (Q1, Q2, Q4), which is exactly the right behavior for health insurance queries. One regression (Q10) due to response-generation confusion, not retrieval. For production, that single case would need prompt refinement or post-processing logic.

## Streaming Test
Confirmed: `llama3.1` streaming works (mechanically active via `stream=True`). Perception is imperceptible due to fast local generation, but the mechanism is correct and functional.

## Files Committed
- `rag_chatbot.py` — `generate_answer()` + `retrieve_and_answer()` pipeline
- `rag_qa_results.md` — this document (test results logged with scores)
- `.env` — model configuration (git-ignored, never committed)