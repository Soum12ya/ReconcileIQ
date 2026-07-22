from dotenv import load_dotenv
load_dotenv()
import json
from app.agents.router_agent import classify_invoice

def run_eval():
    with open("evals/golden_datasets/phase2_invoices.json") as f:
        cases = json.load(f)

    correct = 0
    for case in cases:
        result = classify_invoice(case["invoice_id"], "Test Vendor", case["invoice_total"], case["po_total"])
        is_correct = result["route"] == case["expected_route"]
        correct += is_correct
        print(f"{case['invoice_id']}: expected={case['expected_route']} got={result['route']} {'✅' if is_correct else '❌'}")

    print(f"\nAccuracy: {correct}/{len(cases)}")

if __name__ == "__main__":
    run_eval()