# Retrieval Engine Test Results — Day 10

Engine: `retrieval_engine.py` — classifier + sql_lookup + vector_lookup + retrieve()

## Q1: What's my copay for a specialist visit on the Gold PPO plan?
- **Classification:** structured
- **Retrieved context:** "Gold PPO: $500/month premium, $2000 annual deductible, 10% coinsurance, Gold network tier"
- **Score: Poor**
- **Notes:** Misrouted. The question asks about a *specialist visit* copay specifically
  ($50/visit, found only in `benefits.txt`, unstructured). `plans.csv` only has a
  generic `copay_pct` field, not per-service copays. Because "copay" is a
  structured keyword, the classifier never triggered `vector_lookup`, so the
  correct answer was never even considered. **Known limitation:** keyword-based
  classification can't distinguish general vs. service-specific copay questions.

## Q2: Is physical therapy covered under the Silver plan?
- **Classification:** unstructured
- **Retrieved context:** exclusions clause, general SBC intro, claims status text, Silver HMO plan summary, specialist/diagnostic copay list (5 chunks)
- **Score: Partial**
- **Notes:** No source document mentions "physical therapy" at all (confirmed
  same finding as Day 9). Retrieved the closest semantically related chunks
  rather than a direct answer. Correct behavior given the data gap, but not
  a useful final answer for the member.

## Q3: What is the status of claim C1001?
- **Classification:** structured
- **Retrieved context:** "Claim C1001: X-ray, $250, status: Pending"
- **Score: Good**
- **Notes:** Exact, correct, direct answer.

## Q4: Is maternity care covered on the Bronze plan?
- **Classification:** unstructured
- **Retrieved context:** exclusions clause, Bronze HMO summary, general SBC intro, deductible/out-of-pocket limit text, specialist copay list (5 chunks)
- **Score: Partial**
- **Notes:** No source document mentions "maternity" specifically. Retrieved
  relevant Bronze-plan and exclusions context, but not a direct yes/no answer.

## Q5: How many pending claims does member M1001 have?
- **Classification:** structured
- **Retrieved context:** "Member M1001 has 1 pending claim(s)"
- **Score: Good**
- **Notes:** Exact, correct, direct answer.

## Q6: What services are excluded from coverage?
- **Classification:** unstructured
- **Retrieved context:** exclusions clause ranked #1, plus SBC intro, deductible text, claims guide intro, specialist copay list
- **Score: Good**
- **Notes:** The most relevant chunk (exclusions) was correctly ranked first.
  Direct, accurate answer to a general (non-plan-specific) question.

## Q7: What's the monthly premium for Bronze HMO?
- **Classification:** structured
- **Retrieved context:** "Bronze HMO: $150/month premium, $1000 annual deductible, 30% coinsurance, Bronze network tier"
- **Score: Good**
- **Notes:** Exact, correct, direct answer.

## Q8: What's the premium for Bronze HMO and what does it exclude? (mixed test case)
- **Classification:** both
- **Retrieved context:** Bronze HMO plan details (SQL) + all 3 plan summaries, SBC intro, and exclusions clause (vector) — 6 unique merged results
- **Score: Good**
- **Notes:** Correctly routed to both sources and merged without duplicates.
  Both the premium figure and the exclusions clause are present in the final
  context, giving the LLM everything needed to answer both halves of the question.

## Q9: How do I file a claim?
- **Classification:** unstructured
- **Retrieved context:** required documents list, claims process guide intro, claim status explanation, enrollment form text, SBC intro (5 chunks)
- **Score: Good**
- **Notes:** Top 3 results are directly relevant and answer the question well.
  Enrollment form chunk (#4) is a minor irrelevant inclusion but doesn't hurt
  the overall answer quality.

## Q10: Which plans have a premium under $400?
- **Classification:** structured
- **Retrieved context:** "Silver HMO: $300/month premium", "Bronze HMO: $150/month premium"
- **Score: Good**
- **Notes:** Originally returned 0 results — `sql_lookup` had no logic for
  threshold/range queries, only single-plan lookups. Fixed by adding a
  regex-based threshold parser (`under $X`) to `sql_lookup`. After the fix,
  correctly returns both qualifying plans.

## Summary

| Score | Count | Questions |
|---|---|---|
| Good | 6 | Q3, Q5, Q6, Q7, Q8, Q10 |
| Partial | 2 | Q2, Q4 |
| Poor | 1 | Q1 |
| (n/a - fixed before final run) | — | — |

**Key findings for Day 11 baseline:**
1. Keyword-based classification works well for clearly-worded structured
   questions (claim IDs, member IDs, exact plan names) but can misroute
   ambiguous terms like "copay" that exist at both a general (plan-level) and
   specific (per-service) granularity — Q1 is the clearest example.
2. Unstructured/vector queries reliably surface the most topically relevant
   chunks, but several test questions (physical therapy, maternity) have no
   direct answer anywhere in the synthetic dataset — a data coverage gap, not
   a retrieval bug.
3. The "both" routing path (Q8) works correctly — SQL and vector results
   merge cleanly with no duplicates.
4. One real bug was found and fixed during testing: `sql_lookup` initially
   had no support for threshold/range-based questions (Q10), only
   single-plan-name lookups. This is now handled by a dedicated regex branch.