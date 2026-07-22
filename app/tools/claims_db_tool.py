from app.schemas.purchase_order import PurchaseOrder

def get_po(db, po_number: str):
    return db.query(PurchaseOrder).filter_by(po_number=po_number).first()