import re

PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[redacted-email]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[redacted-phone]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[redacted-card]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[redacted-ssn]"),
)


def redact_pii(text: str) -> tuple[str, bool]:
    redacted = text
    changed = False
    for pattern, replacement in PII_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        changed = changed or count > 0
    return redacted, changed
