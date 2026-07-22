# infra/demo_scenario.py
import requests, time

BASE = "http://localhost:8000"

print("1. Submitting invoice with price variance...")
r = requests.post(f"{BASE}/invoices", json={
    "invoice_id": "DEMO-009", "vendor": "Meridian Office Supplies", "total": 5900.00,
    "po_number": "PO-40921", "sku": "DSK-220", "unit_price": 510.00, "qty": 20,
})
case = r.json()
print(f"   -> {case}")
case_id = case["case_id"]

print("2. Simulating vendor confirmation...")
requests.post(f"{BASE}/simulate-vendor-reply/{case_id}")
time.sleep(11)  # let the worker pick it up

print("3. Checking status...")
print(f"   -> {requests.get(f'{BASE}/status/DEMO-009').json()}")

print("4. Approving...")
print(f"   -> {requests.post(f'{BASE}/cases/{case_id}/approve').json()}")