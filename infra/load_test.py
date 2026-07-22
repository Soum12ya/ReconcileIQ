import requests, time, statistics

URL = "http://localhost:8000/invoices"
N = 20

latencies = []
for i in range(N):
    payload = {
        "invoice_id": f"LOADTEST-{i}",
        "vendor": "Meridian Office Supplies",
        "total": 900.00,
        "po_number": "PO-40921",
        "sku": "DSK-220",
        "unit_price": 45.00,
        "qty": 20,
    }
    start = time.time()
    resp = requests.post(URL, json=payload)
    latencies.append(time.time() - start)

latencies.sort()
p50 = statistics.median(latencies)
p95 = latencies[int(len(latencies) * 0.95) - 1]

print(f"Requests: {N}")
print(f"p50: {p50:.2f}s")
print(f"p95: {p95:.2f}s")
print(f"max: {max(latencies):.2f}s")