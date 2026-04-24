from pathlib import Path


def _public_pages_source() -> str:
    root = Path(__file__).resolve().parents[3]
    target = root / "src" / "ui" / "public_pages.py"
    return target.read_text(encoding="utf-8")


def test_public_pages_has_no_direct_infrastructure_access() -> None:
    source = _public_pages_source()

    assert "shared.infrastructure" not in source
    assert "announcement_db" not in source.lower()
    assert "db.session" not in source


def test_public_pages_uses_application_layer_handler() -> None:
    source = _public_pages_source()

    assert "get_list_latest_published_announcements_handler" in source
