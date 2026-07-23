import sqlite3

conn = sqlite3.connect("coverage.db")
cur = conn.cursor()

queries = {
    "Deductible on Gold PPO plan": """
        SELECT plan_name, annual_deductible
        FROM plans
        WHERE plan_name = 'Gold PPO';
    """,
    "Pending claims for member M1001": """
        SELECT COUNT(*) AS pending_count
        FROM claims
        WHERE member_id = 'M1001' AND status = 'Pending';
    """,
    "Plans with premium under $400": """
        SELECT plan_name, monthly_premium
        FROM plans
        WHERE monthly_premium < 400;
    """,
    "Claims joined with plan details": """
        SELECT c.claim_id, c.procedure, c.claim_amount, p.plan_name, p.network_tier
        FROM claims c
        JOIN plans p ON c.plan_id = p.plan_id;
    """,
    "Top procedures by claim count": """
        SELECT procedure, COUNT(*) AS claim_count
        FROM claims
        GROUP BY procedure
        ORDER BY claim_count DESC
        LIMIT 5;
    """
}

for question, sql in queries.items():
    print(f"\n--- {question} ---")
    cur.execute(sql)
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    print(col_names)
    for row in rows:
        print(row)

conn.close()