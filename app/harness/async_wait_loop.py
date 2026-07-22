import redis, os, json, time
from datetime import datetime
from app.harness.db import SessionLocal
from app.schemas.case_state import CaseState
from dotenv import load_dotenv
load_dotenv()

r = redis.from_url(os.environ["REDIS_URL"], socket_timeout=None)
print("Worker started, watching vendor_reply_queue...")

while True:
    try:
        item = r.blpop("vendor_reply_queue", timeout=10)
    except redis.exceptions.TimeoutError:
        continue

    if not item:
        continue

    _, payload = item
    data = json.loads(payload)

    db = SessionLocal()
    try:
        case = db.query(CaseState).filter_by(case_id=data["case_id"]).first()
        if not case:
            print(f"Warning: case {data['case_id']} not found")
            continue

        if case.status != "routed":
            print(f"Skipping case {case.case_id} — status is '{case.status}', not awaiting a vendor reply")
            continue

        if data.get("reply") == "confirmed" and case.po_unit_price and case.qty:
            case.corrected_total = case.po_unit_price * case.qty
            case.status = "pending_approval"
            print(f"Case {case.case_id} re-validated: corrected total ${case.corrected_total:.2f}, pending_approval")
        
        else:
            case.status = "needs_human_triage"
            print(f"Case {case.case_id} could not be auto-resolved, escalated to triage")

        db.commit()
    finally:
        db.close()