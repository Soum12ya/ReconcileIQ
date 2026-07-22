from app.deterministic_rules.rounding_variance import check_rounding_variance
from app.agents.router_agent import classify_invoice
from app.tools.claims_db_tool import get_po
from app.tools.vector_db_tool import search_contract_clauses

def plan(db, invoice_id: str, vendor: str, total: float, po_number: str | None,
         sku: str | None, unit_price: float | None, qty: float | None) -> dict:

    po = get_po(db, po_number) if po_number else None
    po_total = (po.unit_price * po.qty) if po else None

    rule_result = check_rounding_variance(total, po_total)
    if rule_result:
        return {"path": "deterministic", "status": "posted", **rule_result}

    classification = classify_invoice(invoice_id, vendor, total, po_total)

    evidence = None
    if po and unit_price and unit_price != po.unit_price:
        clauses = search_contract_clauses(db, vendor, f"{sku} pricing")
        evidence = [c.text for c in clauses]

    print(f"Evidence for {invoice_id}: {evidence}")    

    return {"path": "agentic", "status": "routed", "evidence": evidence, **classification}