import pandas as pd
import json
import uuid
from datetime import datetime, timezone
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

records = []

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def new_id():
    return str(uuid.uuid4())

# ---------------------------------------------------------
# PART A: Structured data (Day 4 plans) -> one chunk per plan
# ---------------------------------------------------------
plans = pd.read_csv("data/plans.csv")

for _, row in plans.iterrows():
    text = (
        f"{row['plan_name']}: ${row['monthly_premium']}/month premium, "
        f"${row['annual_deductible']} annual deductible, "
        f"{row['copay_pct']}% coinsurance, "
        f"network tier: {row['network_tier']}, "
        f"coverage type: {row['coverage_type']}."
    )
    records.append({
        "id": new_id(),
        "text": text,
        "source_file": "data/plans.csv",
        "source_type": "structured",
        "plan_type": row["plan_name"],
        "section": "coverage",
        "ingested_at": now_iso()
    })

print(f"Added {len(plans)} structured plan chunks.")

# ---------------------------------------------------------
# PART B: Unstructured text (Day 5 raw_text files) -> chunked
# ---------------------------------------------------------
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

def add_chunks(text, source_file, section, plan_type="general"):
    global unstructured_count
    chunks = splitter.split_text(text)
    for chunk in chunks:
        records.append({
            "id": new_id(),
            "text": chunk,
            "source_file": source_file,
            "source_type": "unstructured",
            "plan_type": plan_type,
            "section": section,
            "ingested_at": now_iso()
        })
        unstructured_count += 1

unstructured_count = 0

# --- benefits.txt: split out the exclusions section specifically ---
with open("raw_text/benefits.txt", "r", encoding="utf-8") as f:
    benefits_text = f.read()

marker = "Excluded Services"
if marker in benefits_text:
    idx = benefits_text.index(marker)
    coverage_part = benefits_text[:idx]
    exclusions_part = benefits_text[idx:]  # includes the "Excluded Services" heading itself

    add_chunks(coverage_part, "raw_text/benefits.txt", section="coverage")
    add_chunks(exclusions_part, "raw_text/benefits.txt", section="exclusions")
else:
    # Fallback: marker not found, chunk the whole thing as coverage
    add_chunks(benefits_text, "raw_text/benefits.txt", section="coverage")

# --- claims_process.txt: whole file is about the claims section ---
with open("raw_text/claims_process.txt", "r", encoding="utf-8") as f:
    claims_text = f.read()
add_chunks(claims_text, "raw_text/claims_process.txt", section="claims")

# --- enrollment.txt: whole file is about enrollment ---
with open("raw_text/enrollment.txt", "r", encoding="utf-8") as f:
    enrollment_text = f.read()
add_chunks(enrollment_text, "raw_text/enrollment.txt", section="enrollment")

print(f"Added {unstructured_count} unstructured text chunks.")

# ---------------------------------------------------------
# PART C: Write knowledge_base.jsonl
# ---------------------------------------------------------
with open("knowledge_base.jsonl", "w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record) + "\n")

print(f"\nTotal chunks written: {len(records)}")
print("Saved knowledge_base.jsonl")