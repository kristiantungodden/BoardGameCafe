import pytest

from features.payments.domain.models.payment import Payment
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository

import features.payments.infrastructure.repositories.payment_repository as payment_repository_module


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index


class FakeDB:
    def __init__(self):
        self.session = FakeSession()


class FakeQuery:
    def __init__(self, result=None):
        self.result = result
        self.last_id = None

    def get(self, payment_id):
        self.last_id = payment_id
        return self.result


class FakePaymentDB:
    query = FakeQuery()

    def __init__(self, **kwargs):
        self.id = None
        self.table_reservation_id = kwargs["table_reservation_id"]
        self.type = kwargs["type"]
        self.provider = kwargs["provider"]
        self.amount_cents = kwargs["amount_cents"]
        self.currency = kwargs["currency"]
        self.status = kwargs["status"]
        self.provider_ref = kwargs["provider_ref"]

    def to_domain(self):
        return Payment(
            id=self.id,
            table_reservation_id=self.table_reservation_id,
            amount_cents=self.amount_cents,
            currency=self.currency,
            status=self.status,
            provider=self.provider,
            type=self.type,
            provider_ref=self.provider_ref,
        )


def test_add_persists_payment_and_returns_domain_object(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(
        "features.payments.infrastructure.repositories.payment_repository.db", fake_db
    )
    monkeypatch.setattr(
        "features.payments.infrastructure.repositories.payment_repository.PaymentDB",
        FakePaymentDB,
    )
    repository = PaymentRepository()
    payment = Payment(table_reservation_id=3, amount_cents=30000)

    saved = repository.add(payment)

    assert fake_db.session.committed is True
    assert len(fake_db.session.added) == 1
    inserted = fake_db.session.added[0]
    assert inserted.table_reservation_id == 3
    assert inserted.amount_cents == 30000
    assert saved.id == 1
    assert saved.table_reservation_id == 3
    assert saved.amount_cents == 30000


def test_get_by_id_returns_domain_payment_when_found(monkeypatch):
    db_row = FakePaymentDB(
        table_reservation_id=5,
        type="reservation",
        provider="none",
        amount_cents=45000,
        currency="NOK",
        status="calculated",
        provider_ref="not_created",
    )
    db_row.id = 42
    fake_query = FakeQuery(result=db_row)
    class StubQuery:
        def __init__(self):
            self.last_id = None

        def get(self, _id):
            self.last_id = _id
            return db_row


    stub_query = StubQuery()

    class StubPaymentDB:
        query = stub_query


    monkeypatch.setattr(
        payment_repository_module,
        "PaymentDB",
        StubPaymentDB,
    )
    repository = PaymentRepository()

    payment = repository.get_by_id(42)

    assert stub_query.last_id == 42
    assert payment is not None
    assert payment.id == 42
    assert payment.table_reservation_id == 5
    assert payment.amount_cents == 45000


def test_get_by_id_returns_none_when_not_found(monkeypatch):
    repository = PaymentRepository()

    class StubQuery:
        def get(self, _id):
            return None


    class StubPaymentDB:
        query = StubQuery()


    monkeypatch.setattr(
        payment_repository_module,
        "PaymentDB",
        StubPaymentDB,
    )

    result = repository.get_by_id(999)

    assert result is None
