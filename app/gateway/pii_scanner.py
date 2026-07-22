import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def scan_for_pii(text: str) -> list[str]:
    findings = []
    if EMAIL_RE.search(text):
        findings.append("email_address")
    return findings