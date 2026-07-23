import json
import random

records = []
with open("knowledge_base.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

print(f"Total chunks: {len(records)}")

structured = [r for r in records if r["source_type"] == "structured"]
unstructured = [r for r in records if r["source_type"] == "unstructured"]
print(f"Structured chunks: {len(structured)}")
print(f"Unstructured chunks: {len(unstructured)}")

print("\n--- 5 random chunks ---")
for r in random.sample(records, min(5, len(records))):
    print(f"\n[{r['section']} | {r['source_type']} | {r['source_file']}]")
    print(r["text"][:300])