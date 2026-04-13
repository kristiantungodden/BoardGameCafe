from datetime import datetime, timedelta

import pytest

from features.reservations.application.use_cases.reservation_use_cases import (
    CreateReservationCommand,
)
from features.reservations.presentation.api import reservation_routes
from features.reservations.presentation.api.deps import (
    get_cancel_reservation_use_case,
    get_create_booking_handler,
)
from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.bookings.domain.models.booking import Booking
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


class FakeCurrentUser:
    def __init__(self, *, user_id, is_authenticated, is_staff=False):
        self.id = user_id
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff


@pytest.mark.integration
def test_owner_can_read_reservation_status_history(client, app, test_data):
    with app.app_context():
        owner = UserDB(
            name="history_owner",
            email="history_owner@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(owner)
        db.session.commit()
        owner_id = owner.id

        handler = get_create_booking_handler()
        reservation, _, _ = handler(
            CreateReservationCommand(
                customer_id=owner.id,
                table_id=1,
                start_ts=datetime.now() + timedelta(days=2),
                end_ts=datetime.now() + timedelta(days=2, hours=2),
                party_size=2,
                notes="",
            )
        )

    original_current_user = reservation_routes.current_user
    reservation_routes.current_user = FakeCurrentUser(
        user_id=owner.id, is_authenticated=True, is_staff=False
    )

    try:
        cancel_resp = client.patch(f"/api/reservations/{reservation.id}/cancel")
        assert cancel_resp.status_code == 200
        response = client.get(f"/api/reservations/{reservation.id}/history")
    finally:
        reservation_routes.current_user = original_current_user

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reservation_id"] == reservation.id
    statuses = [entry["to_status"] for entry in payload["history"]]
    assert "confirmed" in statuses
    assert "cancelled" in statuses
    cancelled_entry = next(entry for entry in payload["history"] if entry["to_status"] == "cancelled")
    assert cancelled_entry["actor_user_id"] == owner.id
    assert cancelled_entry["actor_role"] == "customer"


@pytest.mark.integration
def test_non_owner_cannot_read_reservation_status_history(client, app, test_data):
    with app.app_context():
        owner = UserDB(
            name="history_owner2",
            email="history_owner2@example.com",
            password_hash="hashed",
            role="customer",
        )
        other = UserDB(
            name="history_other",
            email="history_other@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(owner)
        db.session.add(other)
        db.session.commit()
        other_id = other.id

        reservation, _, _ = get_create_booking_handler()(
            CreateReservationCommand(
                customer_id=owner.id,
                table_id=1,
                start_ts=datetime.now() + timedelta(days=2),
                end_ts=datetime.now() + timedelta(days=2, hours=2),
                party_size=2,
                notes="",
            )
        )

    original_current_user = reservation_routes.current_user
    reservation_routes.current_user = FakeCurrentUser(
        user_id=other_id, is_authenticated=True, is_staff=False
    )

    try:
        response = client.get(f"/api/reservations/{reservation.id}/history")
    finally:
        reservation_routes.current_user = original_current_user

    assert response.status_code == 403


@pytest.mark.integration
def test_unauthenticated_user_cannot_read_reservation_status_history(client, app, test_data):
    with app.app_context():
        owner = UserDB(
            name="history_owner3",
            email="history_owner3@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(owner)
        db.session.commit()

        reservation, _, _ = get_create_booking_handler()(
            CreateReservationCommand(
                customer_id=owner.id,
                table_id=1,
                start_ts=datetime.now() + timedelta(days=2),
                end_ts=datetime.now() + timedelta(days=2, hours=2),
                party_size=2,
                notes="",
            )
        )

    original_current_user = reservation_routes.current_user
    reservation_routes.current_user = FakeCurrentUser(
        user_id=0, is_authenticated=False, is_staff=False
    )

    try:
        response = client.get(f"/api/reservations/{reservation.id}/history")
    finally:
        reservation_routes.current_user = original_current_user

    assert response.status_code == 401


@pytest.mark.integration
def test_cancel_rejected_within_24_hours_policy(client, app, test_data):
    with app.app_context():
        owner = UserDB(
            name="history_owner4",
            email="history_owner4@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(owner)
        db.session.commit()
        owner_id = owner.id

        reservation_repo = SqlAlchemyReservationRepository()
        start = datetime.now() + timedelta(hours=23)
        reservation = Booking(
            customer_id=owner_id,
            start_ts=start,
            end_ts=start + timedelta(hours=2),
            party_size=2,
            status="confirmed",
        )
        setattr(reservation, "table_id", test_data["tables"][0]["id"])
        reservation = reservation_repo.add(reservation)

    original_current_user = reservation_routes.current_user
    reservation_routes.current_user = FakeCurrentUser(
        user_id=owner_id, is_authenticated=True, is_staff=False
    )

    try:
        response = client.patch(f"/api/reservations/{reservation.id}/cancel")
    finally:
        reservation_routes.current_user = original_current_user

    assert response.status_code == 400
    assert "24 hours" in response.get_json()["error"]
