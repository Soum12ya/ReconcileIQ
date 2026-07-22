from fastapi import FastAPI
from pydantic import BaseModel
import redis, os, json, uuid
from dotenv import load_dotenv
from datetime import datetime

from app.harness.db import SessionLocal
from app.schemas.case_state import CaseState
from app.gateway.dedupe import is_duplicate
from app.gateway.pii_scanner import scan_for_pii
from app.agents.reconciliation_planner import plan
from app.policy_guardrails.policy_gate import check_action
from app.agents.status_agent import get_status_by_invoice
from app.tools.claims_db_tool import get_po
load_dotenv()

app = FastAPI()
r = redis.from_url(os.environ["REDIS_URL"])

class Invoice(BaseModel):
    invoice_id: str
    vendor: str
    total: float
    po_number: str | None = None
    sku: str | None = None
    unit_price: float | None = None
    qty: float | None = None


class ManualResolve(BaseModel):
    corrected_total: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoices")
def receive_invoice(inv: Invoice):
    db = SessionLocal()
    try:
        if is_duplicate(db, inv.invoice_id, inv.vendor):
            return {"error": "duplicate_invoice", "status": "rejected"}

        pii_flags = scan_for_pii(f"{inv.invoice_id} {inv.vendor}")
        if pii_flags:
            print(f"PII flags on {inv.invoice_id}: {pii_flags}")

        result = plan(db, inv.invoice_id, inv.vendor, inv.total, inv.po_number,
                       inv.sku, inv.unit_price, inv.qty)

        po = get_po(db, inv.po_number) if inv.po_number else None

        case_id = str(uuid.uuid4())
        case = CaseState(
            case_id=case_id, invoice_id=inv.invoice_id, vendor=inv.vendor, total=inv.total,
            status=result["status"], route=result.get("route"), confidence=result.get("confidence"),
            sku=inv.sku, invoiced_unit_price=inv.unit_price,
            po_unit_price=po.unit_price if po else None, qty=inv.qty,
        )
        db.add(case)
        db.commit()

        if result["status"] == "posted":
            return {"case_id": case_id, "status": "posted", "path": "deterministic", "reason": result["reason"]}

        policy_check = check_action("send_vendor_query", inv.total)
        if not policy_check["allowed"]:
            case.status = "needs_human_triage"
            db.commit()
            return {"case_id": case_id, "status": "needs_human_triage", "reason": policy_check["reason"]}

        r.rpush("vendor_query_queue", json.dumps({"case_id": case_id, "invoice_id": inv.invoice_id}))
        case.vendor_query_sent_at = datetime.utcnow()
        db.commit()

        return {"case_id": case_id, "status": result["status"], "route": result.get("route"),
                "evidence": result.get("evidence")}
    finally:
        db.close()


@app.get("/cases")
def list_cases(limit: int = 20):
    """Returns recent cases for the sidebar list."""
    db = SessionLocal()
    try:
        cases = db.query(CaseState).order_by(CaseState.created_at.desc()).limit(limit).all()
        return [
            {"case_id": c.case_id, "invoice_id": c.invoice_id, "vendor": c.vendor,
             "status": c.status, "route": c.route, "total": c.total,
             "corrected_total": c.corrected_total}
            for c in cases
        ]
    finally:
        db.close()


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    """Returns full detail for one case."""
    db = SessionLocal()
    try:
        case = db.query(CaseState).filter_by(case_id=case_id).first()
        if not case:
            return {"error": "not found"}
        return {
            "case_id": case.case_id, "invoice_id": case.invoice_id, "vendor": case.vendor,
            "status": case.status, "route": case.route, "confidence": case.confidence,
            "original_total": case.total, "corrected_total": case.corrected_total,
        }
    finally:
        db.close()


@app.get("/status/{invoice_id}")
def status(invoice_id: str):
    """Status agent — reads by invoice_id, independent of the pipeline."""
    db = SessionLocal()
    try:
        case = (
            db.query(CaseState)
            .filter_by(invoice_id=invoice_id)
            .order_by(CaseState.created_at.desc())
            .first()
        )
        if not case:
            return {"error": "not found"}
        return {
            "case_id": case.case_id, "invoice_id": case.invoice_id, "vendor": case.vendor,
            "status": case.status, "route": case.route, "confidence": case.confidence,
        }
    finally:
        db.close()


@app.post("/simulate-vendor-reply/{case_id}")
def simulate_reply(case_id: str):
    r.rpush("vendor_reply_queue", json.dumps({"case_id": case_id, "reply": "confirmed"}))
    return {"status": "reply_simulated"}


@app.post("/cases/{case_id}/approve")
def approve_case(case_id: str):
    db = SessionLocal()
    try:
        case = db.query(CaseState).filter_by(case_id=case_id).first()
        if not case:
            return {"error": "not found"}
        if case.status != "pending_approval":
            return {"error": f"case is in status '{case.status}', not ready for approval"}

        print(f"[ERP POST] idempotency_key={case.case_id} invoice={case.invoice_id} amount={case.corrected_total}")
        case.status = "closed"
        db.commit()
        return {"case_id": case.case_id, "status": "closed", "posted_total": case.corrected_total}
    finally:
        db.close()


@app.post("/cases/{case_id}/reject")
def reject_case(case_id: str):
    db = SessionLocal()
    try:
        case = db.query(CaseState).filter_by(case_id=case_id).first()
        if not case:
            return {"error": "not found"}
        case.status = "rejected"
        db.commit()
        return {"case_id": case.case_id, "status": "rejected"}
    finally:
        db.close()


@app.post("/cases/{case_id}/manual-resolve")
def manual_resolve(case_id: str, body: ManualResolve):
    """Lets a human enter a corrected total directly for a triage case,
    moving it into the normal approval path."""
    db = SessionLocal()
    try:
        case = db.query(CaseState).filter_by(case_id=case_id).first()
        if not case:
            return {"error": "not found"}
        if case.status != "needs_human_triage":
            return {"error": f"case is in status '{case.status}', cannot manually resolve"}

        case.corrected_total = body.corrected_total
        case.status = "pending_approval"
        db.commit()
        return {"case_id": case.case_id, "status": "pending_approval", "corrected_total": case.corrected_total}
    finally:
        db.close()