# Structured Queries — Coverage Data

## 1. What's the deductible on the Gold PPO plan?
```sql
SELECT plan_name, annual_deductible
FROM plans
WHERE plan_name = 'Gold PPO';
```
**Result:**
| plan_name | annual_deductible |
|---|---|
| Gold PPO | 2000 |

## 2. How many claims are pending for member M1001?
```sql
SELECT COUNT(*) AS pending_count
FROM claims
WHERE member_id = 'M1001' AND status = 'Pending';
```
**Result:**
| pending_count |
|---|
| 1 |

## 3. Which plans have a monthly premium under $400?
```sql
SELECT plan_name, monthly_premium
FROM plans
WHERE monthly_premium < 400;
```
**Result:**
| plan_name | monthly_premium |
|---|---|
| Silver HMO | 300 |
| Bronze HMO | 150 |

## 4. Claims joined with plan details
```sql
SELECT c.claim_id, c.procedure, c.claim_amount, p.plan_name, p.network_tier
FROM claims c
JOIN plans p ON c.plan_id = p.plan_id;
```
**Result:**
| claim_id | procedure | claim_amount | plan_name | network_tier |
|---|---|---|---|---|
| C1001 | X-ray | 250 | Gold PPO | Gold |
| C1002 | Surgery | 1200 | Gold PPO | Gold |
| C1003 | X-ray | 150 | Silver HMO | Silver |
| C1004 | Surgery | 900 | Silver HMO | Silver |
| C1005 | X-ray | 50 | Bronze HMO | Bronze |

## 5. Top claimed procedures
```sql
SELECT procedure, COUNT(*) AS claim_count
FROM claims
GROUP BY procedure
ORDER BY claim_count DESC
LIMIT 5;
```
**Result:**
| procedure | claim_count |
|---|---|
| X-ray | 3 |
| Surgery | 2 |