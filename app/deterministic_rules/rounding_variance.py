ROUNDING_THRESHOLD_USD = 50.0

def check_rounding_variance(total: float, po_total: float | None) -> dict | None:
    if po_total is None:
        return None  # no PO to compare against, can't apply this rule
    variance = abs(total - po_total)
    if variance <= ROUNDING_THRESHOLD_USD:
        return {"resolved": True, "reason": "rounding_variance", "variance": variance}
    return None