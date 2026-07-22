# infra/seed_data.py
from app.harness.db import SessionLocal
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.contract_clause import ContractClause
from app.tools.vector_db_tool import embed

db = SessionLocal()

if not db.query(PurchaseOrder).filter_by(po_number="PO-40921").first():
    db.add(PurchaseOrder(po_number="PO-40921", vendor="Meridian Office Supplies",
                          sku="DSK-220", unit_price=295.00, qty=20))
    db.commit()
    print("Seeded PO-40921")
else:
    print("PO-40921 already exists, skipping")

clause_text = "DSK-220 standing desk is contracted at $295.00 per unit for Meridian Office Supplies, effective Q2 2026."
if not db.query(ContractClause).filter_by(text=clause_text).first():
    db.add(ContractClause(vendor="Meridian Office Supplies", text=clause_text, embedding=embed(clause_text)))
    db.commit()
    print("Seeded contract clause")
else:
    print("Contract clause already exists, skipping")

db.close()