from retrieval_engine import retrieve

TEST_QUESTIONS = [
    "What's my copay for a specialist visit on the Gold PPO plan?",
    "Is physical therapy covered under the Silver plan?",
    "What is the status of claim C1001?",
    "Is maternity care covered on the Bronze plan?",
    "How many pending claims does member M1001 have?",
    "What services are excluded from coverage?",
    "What's the monthly premium for Bronze HMO?",
    "What's the premium for Bronze HMO and what does it exclude?",
    "How do I file a claim?",
    "Which plans have a premium under $400?",
]

for i, question in enumerate(TEST_QUESTIONS, 1):
    result = retrieve(question)
    print(f"\n{'='*70}")
    print(f"Q{i}: {question}")
    print(f"Classification: {result['classification']}")
    print(f"\nSQL results ({len(result['sql_results'])}):")
    for r in result['sql_results']:
        print(f"  - {r}")
    print(f"\nVector results ({len(result['vector_results'])}):")
    for r in result['vector_results']:
        print(f"  - {r[:150]}")
    print(f"\nMerged context count: {len(result['merged_context'])}")