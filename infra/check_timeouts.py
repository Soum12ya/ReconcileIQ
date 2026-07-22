# infra/check_timeouts.py
import os
from datetime import datetime, timedelta
from app.harness.db import SessionLocal
from app.schemas.case_state import CaseState

TIMEOUT_DAYS = float(os.environ.get("VENDOR_REPLY_TIMEOUT_DAYS", 5))

db = SessionLocal()
cutoff = datetime.utcnow() - timedelta(days=TIMEOUT_DAYS)

overdue = db.query(CaseState).filter(
    CaseState.status == "routed",
    CaseState.vendor_query_sent_at < cutoff,
).all()

for case in overdue:
    case.status = "needs_human_triage"
    print(f"Escalated {case.invoice_id} — vendor did not reply within {TIMEOUT_DAYS} days")

db.commit()
db.close()
print(f"Checked {len(overdue)} overdue case(s)")