from app.pii import redact_pii


def test_redacts_common_pii() -> None:
    text, changed = redact_pii("Email me at shopper@example.com or 415-555-1212.")
    assert changed
    assert "shopper@example.com" not in text
    assert "415-555-1212" not in text
