from types import SimpleNamespace

import pytest

from features.payments.domain.models.payment import Payment
from features.payments.infrastructure.stripe.stripe_adapter import StripeAdapter


def test_stripe_adapter_requires_api_key():
    with pytest.raises(ValueError, match="Missing STRIPE_SECRET_KEY"):
        StripeAdapter("", "https://example.com")


def test_stripe_adapter_requires_app_base_url():
    with pytest.raises(ValueError, match="Missing APP_BASE_URL"):
        StripeAdapter("sk_test_123", "")


def test_start_payment_builds_checkout_session_with_environment_urls(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.test/session")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.create",
        fake_create,
    )

    adapter = StripeAdapter("sk_test_123", "https://boardgamecafe.example/")
    payment = Payment(id=99, booking_id=42, amount_cents=2500)

    result = adapter.start_payment(payment)

    assert result.provider_name == "stripe"
    assert result.provider_ref == "cs_test_123"
    assert result.redirect_url == "https://checkout.stripe.test/session"

    assert captured["mode"] == "payment"
    assert captured["payment_method_types"] == ["card"]
    assert captured["metadata"]["payment_id"] == "99"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 2500
    assert captured["success_url"].startswith("https://boardgamecafe.example/payments/success")
    assert captured["cancel_url"] == (
        "https://boardgamecafe.example/payments/cancel"
        "?payment_id=99&booking_id=42"
    )


def test_fetch_status_maps_paid_and_pending(monkeypatch):
    def fake_retrieve_paid(provider_ref):
        assert provider_ref == "cs_paid"
        return SimpleNamespace(payment_status="paid")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.retrieve",
        fake_retrieve_paid,
    )

    adapter = StripeAdapter("sk_test_123", "https://boardgamecafe.example")
    assert adapter.fetch_status("cs_paid") == "paid"

    def fake_retrieve_pending(provider_ref):
        assert provider_ref == "cs_pending"
        return SimpleNamespace(payment_status="unpaid")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.retrieve",
        fake_retrieve_pending,
    )

    assert adapter.fetch_status("cs_pending") == "pending"
