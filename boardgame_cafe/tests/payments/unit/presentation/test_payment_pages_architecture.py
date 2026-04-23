from pathlib import Path


def _payment_pages_source() -> str:
    root = Path(__file__).resolve().parents[4]
    target = root / "src" / "ui" / "payment_pages.py"
    return target.read_text(encoding="utf-8")


def test_payment_pages_has_no_infrastructure_imports() -> None:
    source = _payment_pages_source()

    assert "infrastructure" not in source
    assert "PaymentDB" not in source
    assert "db.session" not in source


def test_payment_pages_uses_payment_composition_handlers() -> None:
    source = _payment_pages_source()

    assert "get_payment_success_handler" in source
    assert "get_payment_cancel_handler" in source
