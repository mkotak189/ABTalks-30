# Vector Query Test — Day 9

## Setup
- Collection: `coverage_kb` (Chroma, persistent, local)
- Total chunks upserted: 11
- `collection.count()` after upsert: 11 ✅ (matches `knowledge_base.jsonl` total)
- Embedding model: `all-MiniLM-L6-v2`
- Test query: *"Is physical therapy covered under the Silver plan?"*

## Note on metadata field
The mission's example filter uses `plan_type: "Silver"`. My actual `plan_type`
values (set in Day 6) are `"Gold PPO"`, `"Silver HMO"`, `"Bronze HMO"` for
structured plan chunks, and `"general"` for unstructured text chunks. Chroma's
`where` filter requires an exact string match, so I filtered on `"Silver HMO"`
instead of `"Silver"` to match my real data, while testing the same underlying
capability (scoping results to one plan).

## Unfiltered Query Results (n_results=5)

| Rank | Distance | Section | Source Type | Plan Type | Source File |
|---|---|---|---|---|---|
| 1 | 1.0219 | exclusions | unstructured | general | raw_text/benefits.txt |
| 2 | 1.1027 | coverage | unstructured | general | raw_text/benefits.txt |
| 3 | 1.1945 | claims | unstructured | general | raw_text/claims_process.txt |
| 4 | 1.2041 | coverage | structured | **Silver HMO** | data/plans.csv |
| 5 | 1.2140 | coverage | unstructured | general | raw_text/benefits.txt |

**Observations:**
- Only 1 of the 5 returned chunks is actually Silver-plan-specific (rank 4).
  The rest are general coverage/exclusions/claims text that isn't tied to any
  one plan.
- **Retrieval miss:** None of my source documents (synthetic SBC, claims guide,
  enrollment form) mention "physical therapy" at all — this term doesn't exist
  anywhere in the underlying data. The model correctly surfaced the closest
  semantically-related content (coverage terms, exclusions, claim statuses)
  rather than an exact match, because no exact match exists. This is expected
  behavior given the small, synthetic dataset, not a retrieval bug — it shows
  the system needs either richer source data or a fallback ("I don't have
  information on that") for real deployment.
- The top result (exclusions) has the lowest distance, meaning it's
  semantically *closest* to the query overall — plausible, since "is X
  covered" queries share vocabulary with an exclusions clause listing what's
  *not* covered.

## Filtered Query Results (where plan_type = "Silver HMO", n_results=5)

| Rank | Distance | Section | Source Type | Plan Type | Source File |
|---|---|---|---|---|---|
| 1 | 1.2041 | coverage | structured | Silver HMO | data/plans.csv |

**Observations:**
- The filter correctly scoped results to exactly **1 chunk** — the only chunk
  in the entire 11-chunk knowledge base tagged `plan_type: "Silver HMO"`.
- This confirms metadata filtering works as intended: it excluded 10 other
  chunks that were present in the unfiltered results (including the
  lower-distance exclusions chunk), because they weren't tagged as Silver-plan
  data — even though some were semantically closer to the query.
- This also surfaces a data-coverage gap: with only 1 structured chunk per
  plan, filtered queries have very little to retrieve from. A production
  system would need more granular per-plan documentation (e.g. plan-specific
  benefit PDFs) to make filtered retrieval genuinely useful.

## Summary
Both the raw similarity search and metadata filtering worked correctly at the
mechanical level — the collection count matches, the filter properly excludes
non-matching chunks, and results are ranked by semantic distance. The main
limitation observed is data coverage, not retrieval logic: the synthetic
dataset doesn't contain enough plan-specific detail (e.g. no "physical
therapy" mention anywhere) to produce a precise answer to this particular
query.