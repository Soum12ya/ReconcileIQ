from app.schemas.case_state import CaseState

def is_duplicate(db, invoice_id: str, vendor: str) -> bool:
    existing = db.query(CaseState).filter_by(invoice_id=invoice_id, vendor=vendor).first()
    return existing is not None