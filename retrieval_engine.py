import re
import json
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# Setup: shared connections
# ---------------------------------------------------------
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_sql_conn():
    return sqlite3.connect("coverage.db")

def get_chroma_collection():
    client = chromadb.PersistentClient(path="chroma_data")
    return client.get_or_create_collection(name="coverage_kb")


# ---------------------------------------------------------
# Step 1: Classifier
# ---------------------------------------------------------
STRUCTURED_KEYWORDS = [
    "deductible", "premium", "copay", "coinsurance", "claim status",
    "status of claim", "pending claim", "how many claims", "monthly cost",
    "cost of", "price of"
]
UNSTRUCTURED_KEYWORDS = [
    "covered", "coverage", "cover ", "excluded", "exclusion", "exclude",
    "policy", "benefit", "procedure", "therapy", "maternity", "how do i",
    "process", "appeal", "surgery"
]

CLAIM_ID_PATTERN = re.compile(r"\bC\d{3,}\b", re.IGNORECASE)
MEMBER_ID_PATTERN = re.compile(r"\bM\d{3,}\b", re.IGNORECASE)

def classify(question: str) -> str:
    """Returns 'structured', 'unstructured', or 'both'."""
    q = question.lower()

    has_structured = any(kw in q for kw in STRUCTURED_KEYWORDS)
    has_unstructured = any(kw in q for kw in UNSTRUCTURED_KEYWORDS)

    # Claim/member IDs are a strong structured signal
    if CLAIM_ID_PATTERN.search(question) or MEMBER_ID_PATTERN.search(question):
        has_structured = True

    if has_structured and has_unstructured:
        return "both"
    elif has_structured:
        return "structured"
    elif has_unstructured:
        return "unstructured"
    else:
        # Default fallback: try both rather than returning nothing
        return "both"


# ---------------------------------------------------------
# Step 2: sql_lookup
# ---------------------------------------------------------
PLAN_NAMES = ["Gold PPO", "Silver HMO", "Bronze HMO"]

def extract_plan_name(question: str):
    q = question.lower()
    for plan in PLAN_NAMES:
        if plan.lower() in q:
            return plan
    # also match just the tier word (Gold/Silver/Bronze)
    for tier, full in [("gold", "Gold PPO"), ("silver", "Silver HMO"), ("bronze", "Bronze HMO")]:
        if tier in q:
            return full
    return None

def sql_lookup(question: str) -> list[str]:
    """Returns a list of plain-text result strings from SQL."""
    conn = get_sql_conn()
    cur = conn.cursor()
    results = []
    q = question.lower()

    claim_id_match = CLAIM_ID_PATTERN.search(question)
    member_id_match = MEMBER_ID_PATTERN.search(question)
    plan_name = extract_plan_name(question)

    # Claim status lookup
    if claim_id_match and ("status" in q or "claim" in q):
        claim_id = claim_id_match.group(0).upper()
        cur.execute(
            "SELECT claim_id, procedure, claim_amount, status FROM claims WHERE claim_id = ?",
            (claim_id,)
        )
        row = cur.fetchone()
        if row:
            results.append(f"Claim {row[0]}: {row[1]}, ${row[2]}, status: {row[3]}")
        else:
            results.append(f"No claim found with ID {claim_id}")

    # Premium threshold query (e.g. "under $400", "less than $300")
    threshold_match = re.search(r"under\s*\$?(\d+)|less than\s*\$?(\d+)|below\s*\$?(\d+)", q)
    if threshold_match and "premium" in q:
        threshold = int(next(g for g in threshold_match.groups() if g))
        cur.execute(
            "SELECT plan_name, monthly_premium FROM plans WHERE monthly_premium < ?",
            (threshold,)
        )
        rows = cur.fetchall()
        for row in rows:
            results.append(f"{row[0]}: ${row[1]}/month premium")
        conn.close()
        return results

    # Pending claims for a member
    elif member_id_match and "pending" in q:
        member_id = member_id_match.group(0).upper()
        cur.execute(
            "SELECT COUNT(*) FROM claims WHERE member_id = ? AND status = 'Pending'",
            (member_id,)
        )
        count = cur.fetchone()[0]
        results.append(f"Member {member_id} has {count} pending claim(s)")

    # Deductible / premium / copay for a specific plan
    elif plan_name and any(kw in q for kw in ["deductible", "premium", "copay", "coinsurance", "cost"]):
        cur.execute(
            "SELECT plan_name, monthly_premium, annual_deductible, copay_pct, network_tier FROM plans WHERE plan_name = ?",
            (plan_name,)
        )
        row = cur.fetchone()
        if row:
            results.append(
                f"{row[0]}: ${row[1]}/month premium, ${row[2]} annual deductible, "
                f"{row[3]}% coinsurance, {row[4]} network tier"
            )

    # Generic fallback: if a plan name was mentioned but nothing else matched
    elif plan_name:
        cur.execute(
            "SELECT plan_name, monthly_premium, annual_deductible, copay_pct, network_tier FROM plans WHERE plan_name = ?",
            (plan_name,)
        )
        row = cur.fetchone()
        if row:
            results.append(
                f"{row[0]}: ${row[1]}/month premium, ${row[2]} annual deductible, "
                f"{row[3]}% coinsurance, {row[4]} network tier"
            )

    conn.close()
    return results


# ---------------------------------------------------------
# Step 3: vector_lookup
# ---------------------------------------------------------
def vector_lookup(question: str, n_results: int = 5) -> list[str]:
    model = get_model()
    collection = get_chroma_collection()
    query_embedding = model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    output = []
    for i in range(len(results["ids"][0])):
        text = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        output.append(f"[{meta.get('section', 'unknown')}] {text}")
    return output


# ---------------------------------------------------------
# Step 4: retrieve - the router
# ---------------------------------------------------------
def retrieve(question: str) -> dict:
    classification = classify(question)

    sql_results = []
    vector_results = []

    if classification in ("structured", "both"):
        sql_results = sql_lookup(question)

    if classification in ("unstructured", "both"):
        vector_results = vector_lookup(question)

    # Merge and de-duplicate
    combined = []
    seen = set()
    for r in sql_results + vector_results:
        key = r.strip().lower()
        if key not in seen:
            seen.add(key)
            combined.append(r)

    return {
        "question": question,
        "classification": classification,
        "sql_results": sql_results,
        "vector_results": vector_results,
        "merged_context": combined,
    }


if __name__ == "__main__":
    # Quick manual smoke test
    test_q = "What's the deductible on the Gold PPO plan?"
    result = retrieve(test_q)
    print(json.dumps(result, indent=2))