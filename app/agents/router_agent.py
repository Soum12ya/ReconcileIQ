import json, os
from openai import OpenAI
from langfuse import observe

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

ROUTES = ["clean_match", "price_variance", "duplicate_invoice", "missing_po", "tax_mismatch", "needs_human_triage"]

@observe(name="router_agent")
def classify_invoice(invoice_id: str, vendor: str, total: float, po_total: float | None) -> dict:
    prompt = f"""Classify this invoice discrepancy into exactly one route from {ROUTES}.
Invoice: {invoice_id}, vendor: {vendor}, invoice total: {total}, PO total: {po_total}.
Respond with only JSON: {{"route": "...", "confidence": 0.0}}"""

    response = client.chat.completions.create(
        model=os.environ.get("ROUTER_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)