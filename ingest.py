import pandas as pd
import sqlite3

# Load
plans = pd.read_csv("data/plans.csv")
claims = pd.read_csv("data/claims.csv")

# Inspect
print("=== PLANS INFO ===")
plans.info()
print(plans.head())

print("\n=== CLAIMS INFO ===")
claims.info()
print(claims.head())

# Clean: dedupe, handle nulls, coerce types
plans = plans.drop_duplicates()
claims = claims.drop_duplicates()

plans = plans.dropna()
claims = claims.dropna(subset=["claim_id", "member_id", "plan_id"])

claims["date_filed"] = pd.to_datetime(claims["date_filed"])

print("\n=== AFTER CLEANING ===")
print(plans.dtypes)
print(claims.dtypes)

# Load into SQLite
conn = sqlite3.connect("coverage.db")
plans.to_sql("plans", conn, if_exists="replace", index=False)
claims.to_sql("claims", conn, if_exists="replace", index=False)
conn.close()

print("\ncoverage.db created with plans and claims tables.")