# infra/consolidate_memory.py
from app.harness.db import SessionLocal
from app.schemas.case_state import CaseState

db = SessionLocal()
closed_cases = db.query(CaseState).filter_by(vendor="Meridian Office Supplies", status="closed").all()

if len(closed_cases) >= 2:
    variances = [abs(c.total - c.corrected_total) for c in closed_cases if c.corrected_total]
    if variances:
        avg_variance = sum(variances) / len(variances)
        print(f"Consolidated fact: Meridian Office Supplies has an average price variance of ${avg_variance:.2f} across {len(closed_cases)} closed cases.")
else:
    print("Not enough closed cases yet to consolidate.")

db.close()