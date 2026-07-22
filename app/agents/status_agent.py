from app.schemas.case_state import CaseState

def get_status_by_invoice(db, invoice_id: str) -> dict | None:
    case = db.query(CaseState).filter_by(invoice_id=invoice_id).order_by(CaseState.created_at.desc()).first()
    if not case:
        return None
    return {
        "case_id": case.case_id,
        "invoice_id": case.invoice_id,
        "vendor": case.vendor,
        "status": case.status,
        "route": case.route,
        "confidence": case.confidence,
    }