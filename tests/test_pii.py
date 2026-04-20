from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_phone() -> None:
    out = scrub_text("Call me at 0123456789")
    assert "0123456789" not in out
    assert "REDACTED_PHONE" in out
