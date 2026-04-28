from types import SimpleNamespace

from features.payments.domain.models.payment import Payment
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.presentation.api import payment_routes


payment_routes.current_user = SimpleNamespace(
    id=1,
    is_authenticated=True,
    role="admin",
    is_staff=True,
    is_admin=True,
)


def test_start_payment_route_sets_provider_and_returns_redirect_url(client, app, monkeypatch):
    repo = PaymentRepository()

    with app.app_context():
        payment = Payment(booking_id=77, amount_cents=3500)
        saved = repo.add(payment)

    def fake_create(**kwargs):
        return SimpleNamespace(id="cs_test_start_1", url="https://checkout.stripe.test/cs_test_start_1")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.create",
        fake_create,
    )

    resp = client.post(f"/api/payments/start/{saved.id}")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["redirect_url"] == "https://checkout.stripe.test/cs_test_start_1"
    assert data["payment"]["provider"] == "stripe"
    assert data["payment"]["provider_ref"] == "cs_test_start_1"
    assert data["payment"]["status"] == "pending"


def test_start_payment_route_returns_400_when_stripe_fails(client, app, monkeypatch):
    repo = PaymentRepository()

    with app.app_context():
        payment = Payment(booking_id=78, amount_cents=3600)
        saved = repo.add(payment)

    def fake_create(**kwargs):
        raise RuntimeError("stripe down")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.create",
        fake_create,
    )

    resp = client.post(f"/api/payments/start/{saved.id}")
    assert resp.status_code == 500
    body = resp.get_json()
    assert "stripe down" in body["error"]
