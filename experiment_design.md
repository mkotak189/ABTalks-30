# A/B Experiment Design: Prompt Engineering Variants — Day 26

## Hypothesis
**Prompt Variant E (Hybrid, Day 12) will produce higher-quality coverage answers than Prompt Variant A (Strict/Formal, Day 12) because it balances compliance with warmth and explicit reasoning.**

---

## Variants Under Test

### Variant A (Control): Strict/Formal (Day 12)


### Variant E (Treatment): Hybrid (Day 12)


---

## Primary Metric
**Answer Quality Score (1-5 scale):**
- 5 = Accurate, warm, actionable, no scope creep
- 4 = Accurate, mostly warm, actionable
- 3 = Accurate but cold, or partially answered
- 2 = Inaccurate or incomplete
- 1 = Incorrect or off-topic

---

## Secondary Metrics
- **Member Satisfaction** (would member take action based on this answer?)
- **Compliance** (does answer include medical disclaimer when needed?)
- **Scope Adherence** (stays within coverage/claims/enrollment, doesn't give medical advice)

---

## Sample Size
**n = 15 questions** covering:
- Coverage questions: 7
- Claims questions: 5
- Enrollment questions: 3

All questions use synthetic data (no real member PHI).

---

## Questions (Test Set)
1. What's the monthly premium for the Gold PPO plan?
2. What is the status of claim C1001?
3. Is physical therapy covered under the Silver HMO plan?
4. How much would I pay out of pocket for an MRI under Silver HMO?
5. What's the annual deductible for Bronze HMO?
6. I'm worried about medical costs. How does coinsurance work?
7. What procedures are excluded from coverage?
8. How do I file a claim?
9. When do I need prior authorization?
10. What's the difference between copay and deductible?
11. Can I see any doctor with my plan?
12. What happens when I hit my deductible?
13. Are maternity services covered?
14. How long does a claim take to process?
15. What is an out-of-network provider?

---

## Decision Rule
**Variant E wins if:**
- Mean score for E > Mean score for A, AND
- Difference ≥ 0.5 points (meaningful margin given small sample)

**No winner if:**
- Difference < 0.5 points (too close to call with n=15)

**Variant A wins if:**
- Mean score for A ≥ Mean score for E

---

## Scoring Rubric

### Accuracy (most important)
- Correct facts about plan benefits: +2 points
- Partially correct or missing detail: +1 point
- Incorrect or contradicts plan documents: 0 points

### Warmth & Empathy
- Acknowledges member concern ("I understand..."), shows respect: +1 point
- Neutral tone, no acknowledgment: 0 points
- Cold or dismissive tone: -0.5 points

### Actionability
- Member could take next step based on answer: +1 point
- Answer is informational but doesn't guide action: 0 points

### Compliance & Scope
- Includes disclaimers where needed, stays in scope: +1 point
- Misses disclaimer or ventures into medical advice: -0.5 points

**Max score per answer: 5 points**

---

## Success Criteria for Production
If Variant E wins:
- Roll out Variant E as default system prompt in production
- Retain Variant A as fallback for edge cases

If no winner or Variant A wins:
- Continue with current prompt (Day 12 Variant E already deployed)
- Flag that prompt engineering has ceiling; investigate other levers (retrieval quality, tool availability)

---

## Limitations of This Experiment
- **Small sample (n=15):** High variance, low power to detect small effects
- **Synthetic data:** Real conversations might differ
- **Manual scoring:** Subjective; inter-rater reliability not measured
- **Single evaluator:** No blinding; potential bias
- **No user feedback:** Scores don't reflect actual member satisfaction

**Recommendation:** If result is close, run larger experiment (n=100+) with real conversations and user feedback.

---

## Timeline
- Run both variants: ~2 hours
- Score all 15 questions: ~1 hour
- Analyze & write conclusions: ~30 min
- **Total: ~3.5 hours**