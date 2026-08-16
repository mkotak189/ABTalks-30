from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClaimStatusCard(BaseModel):
    claim_id: str
    status: str
    amount: float
    procedure: str
    date_filed: Optional[str] = None

class CoverageSummaryCard(BaseModel):
    plan_name: str
    plan_id: str
    deductible: float
    copay_pct: float
    covered: bool
    details: str