import os

APPROVAL_THRESHOLD = float(os.environ.get("POLICY_APPROVAL_THRESHOLD_USD", 1000))

def check_action(action_type: str, amount: float) -> dict:
    """Every external-facing action (vendor email, ERP write) must pass through here first."""
    if action_type == "send_vendor_query":
        if amount > APPROVAL_THRESHOLD:
            return {"allowed": False, "reason": f"amount ${amount:.2f} exceeds ${APPROVAL_THRESHOLD:.2f} auto-contact threshold"}
        return {"allowed": True, "reason": "within auto-contact threshold"}

    return {"allowed": False, "reason": f"unknown action_type: {action_type}"}