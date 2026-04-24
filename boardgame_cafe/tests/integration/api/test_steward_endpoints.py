from datetime import datetime, timedelta, timezone

from shared.infrastructure import db
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.bookings.infrastructure.database.booking_status_history_db import BookingStatusHistoryDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from shared.domain.events import ReservationCompleted, ReservationSeated
from shared.domain.events import ReservationUpdated


def _register_and_login_staff(client, email="steward@example.com"):
    staff_payload = {
        "name": "Steward",
        "email": email,
        "password": "password123",
        "role": "staff",
    }
    reg = client.post("/api/auth/register", json=staff_payload)
    assert reg.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 200


def test_steward_list_and_seat_flow(client, app, test_data):
    # Create a booking and table reservation for today
    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=3, status="confirmed")
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=3, status="confirmed")
        db.session.add(tr)
        db.session.commit()

        reservation_id = tr.id

    _register_and_login_staff(client)

    # List active reservations
    resp = client.get("/api/steward/reservations")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(r["id"] == reservation_id for r in data)
    item = next(r for r in data if r["id"] == reservation_id)
    assert item["customer_name"] == test_data["user"]["name"]
    assert item["customer_email"] == test_data["user"]["email"]

    # Seat the reservation
    seat_resp = client.patch(f"/api/steward/reservations/{reservation_id}/seat")
    assert seat_resp.status_code == 200
    seat_data = seat_resp.get_json()
    assert seat_data["id"] == reservation_id
    assert seat_data["status"] == "seated"

    with app.app_context():
        seated_table = db.session.get(TableDB, table_id)
        assert seated_table is not None
        assert seated_table.status == "occupied"

    pending_after_seat = client.get("/api/steward/reservations")
    assert pending_after_seat.status_code == 200
    pending_after_seat_data = pending_after_seat.get_json()
    assert all(r["id"] != reservation_id for r in pending_after_seat_data)

    with app.app_context():
        seated_entry = (
            db.session.query(BookingStatusHistoryDB)
            .filter(BookingStatusHistoryDB.booking_id == reservation_id)
            .filter(BookingStatusHistoryDB.to_status == "seated")
            .order_by(BookingStatusHistoryDB.id.desc())
            .first()
        )
        assert seated_entry is not None
        assert seated_entry.actor_user_id is not None
        assert seated_entry.actor_role == "staff"

    # Confirm it's listed in seated reservations
    seated_resp = client.get("/api/steward/reservations/seated")
    assert seated_resp.status_code == 200
    seated = seated_resp.get_json()
    assert any(r["id"] == reservation_id for r in seated)


def test_steward_waitlist_mutations_publish_realtime_events(client, test_data, monkeypatch):
    _register_and_login_staff(client, email="steward-events@example.com")

    published = []

    def _capture(payload, channel=None):
        published.append(payload)

    monkeypatch.setattr(
        "features.users.presentation.api.steward_routes.publish_realtime_event",
        _capture,
    )

    create_resp = client.post(
        "/api/steward/waitlist",
        json={
            "customer_id": test_data["user"]["id"],
            "party_size": 2,
            "notes": "Window seat preferred",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()

    delete_resp = client.delete(f"/api/steward/waitlist/{created['id']}")
    assert delete_resp.status_code == 204

    event_types = [item.get("event_type") for item in published]
    assert "waitlist.created" in event_types
    assert "waitlist.deleted" in event_types


def test_steward_complete_flow(client, app, test_data):
    # Create a booking and table reservation, seat it, then complete
    from datetime import datetime, timedelta, timezone
    from shared.infrastructure import db
    from features.bookings.infrastructure.database.booking_db import BookingDB
    from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB

    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

    _register_and_login_staff(client)

    # Seat then complete
    client.patch(f"/api/steward/reservations/{reservation_id}/seat")
    comp = client.patch(f"/api/steward/reservations/{reservation_id}/complete")
    assert comp.status_code == 200
    data = comp.get_json()
    assert data["id"] == reservation_id
    assert data["status"] == "completed"

    with app.app_context():
        freed_table = db.session.get(TableDB, table_id)
        assert freed_table is not None
        assert freed_table.status == "available"

    seated_after_complete = client.get("/api/steward/reservations/seated")
    assert seated_after_complete.status_code == 200
    seated_after_complete_data = seated_after_complete.get_json()
    assert all(r["id"] != reservation_id for r in seated_after_complete_data)

    with app.app_context():
        completed_entry = (
            db.session.query(BookingStatusHistoryDB)
            .filter(BookingStatusHistoryDB.booking_id == reservation_id)
            .filter(BookingStatusHistoryDB.to_status == "completed")
            .order_by(BookingStatusHistoryDB.id.desc())
            .first()
        )
        assert completed_entry is not None
        assert completed_entry.actor_user_id is not None
        assert completed_entry.actor_role == "staff"


def test_steward_no_show_flow(client, app, test_data):
    # Create a booking and table reservation, then mark no-show
    from datetime import datetime, timedelta, timezone
    from shared.infrastructure import db
    from features.bookings.infrastructure.database.booking_db import BookingDB
    from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB

    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

    _register_and_login_staff(client, email="steward2@example.com")

    no_show = client.patch(f"/api/steward/reservations/{reservation_id}/no-show")
    assert no_show.status_code == 200
    data = no_show.get_json()
    assert data["id"] == reservation_id
    assert data["status"] == "no_show"

    with app.app_context():
        no_show_entry = (
            db.session.query(BookingStatusHistoryDB)
            .filter(BookingStatusHistoryDB.booking_id == reservation_id)
            .filter(BookingStatusHistoryDB.to_status == "no_show")
            .order_by(BookingStatusHistoryDB.id.desc())
            .first()
        )
        assert no_show_entry is not None
        assert no_show_entry.actor_user_id is not None
        assert no_show_entry.actor_role == "staff"


def test_steward_swap_and_game_copy_status_and_incident_flow(client, app, test_data):
    # Create booking + table reservation + a reservation_game linking a copy, then swap to another copy
    from datetime import datetime, timedelta, timezone
    from shared.infrastructure import db
    from features.bookings.infrastructure.database.booking_db import BookingDB
    from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
    from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
    from features.games.infrastructure.database.game_copy_db import GameCopyDB

    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

        # create a reservation_game row using the first copy
        copy_a = test_data["copies"][0]["id"]
        copy_b = test_data["copies"][1]["id"]
        requested_game = test_data["games"][0]["id"]

        rg = GameReservationDB(booking_id=reservation_id, game_copy_id=copy_a, requested_game_id=requested_game)
        db.session.add(rg)
        db.session.commit()
        reservation_game_id = rg.id

    _register_and_login_staff(client, email="steward3@example.com")

    # Swap to copy_b
    swap_resp = client.patch(f"/api/steward/reservations/{reservation_id}/games/{reservation_game_id}/swap", json={"new_copy_id": copy_b})
    assert swap_resp.status_code == 200
    swap_data = swap_resp.get_json()
    assert swap_data["game_copy_id"] == copy_b

    # Verify game copy statuses: old should be available, new should be reserved
    with app.app_context():
        old = db.session.get(GameCopyDB, copy_a)
        new = db.session.get(GameCopyDB, copy_b)
        assert old.status == "available"
        assert new.status == "reserved"

    # Staff can no longer update copy status directly
    status_resp = client.patch(f"/api/steward/game-copies/{copy_b}/status", json={"action": "lost"})
    assert status_resp.status_code == 403

    # Report an incident on copy_b
    incident_payload = {"incident_type": "damage", "note": "Edge broken"}
    rep = client.post(f"/api/steward/game-copies/{copy_b}/incidents", json=incident_payload)
    assert rep.status_code == 201
    incident = rep.get_json()
    assert incident["incident_type"] == "damage"
    assert incident["note"] == "Edge broken"

    with app.app_context():
        updated_copy = db.session.get(GameCopyDB, copy_b)
        assert updated_copy is not None
        assert updated_copy.status == "maintenance"

    # List incidents for the copy
    list_inc = client.get(f"/api/steward/game-copies/{copy_b}/incidents")
    assert list_inc.status_code == 200
    incidents = list_inc.get_json()
    assert any(i["id"] == incident["id"] for i in incidents)


def test_steward_game_copies_support_browse_filters(client, test_data):
    _register_and_login_staff(client, email="stewardbrowse@example.com")

    all_resp = client.get("/api/steward/game-copies")
    assert all_resp.status_code == 200
    all_copies = all_resp.get_json()
    assert len(all_copies) >= 2
    assert all("game_title" in c for c in all_copies)

    catan_game_id = test_data["games"][0]["id"]
    by_game_resp = client.get(f"/api/steward/game-copies?game_id={catan_game_id}")
    assert by_game_resp.status_code == 200
    by_game = by_game_resp.get_json()
    assert len(by_game) >= 1
    assert all(c["game_id"] == catan_game_id for c in by_game)

    by_search_resp = client.get("/api/steward/game-copies?q=CHESS")
    assert by_search_resp.status_code == 200
    by_search = by_search_resp.get_json()
    assert len(by_search) >= 1
    assert all(
        ("chess" in (c.get("game_title") or "").lower())
        or ("chess" in (c.get("copy_code") or "").lower())
        for c in by_search
    )


def test_steward_reservation_lists_enforce_status_boundaries(client, app, test_data):
    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]

        # Confirmed-only reservation (should remain in /reservations)
        start_a = datetime.now(timezone.utc)
        booking_a = BookingDB(
            customer_id=user_id,
            start_ts=start_a,
            end_ts=start_a + timedelta(hours=2),
            party_size=2,
            status="confirmed",
        )
        db.session.add(booking_a)
        db.session.commit()
        tr_a = TableReservationDB(
            booking_id=booking_a.id,
            table_id=table_id,
            customer_id=user_id,
            start_ts=booking_a.start_ts,
            end_ts=booking_a.end_ts,
            party_size=2,
            status="confirmed",
        )
        db.session.add(tr_a)

        # Reservation to become seated (should appear only in /reservations/seated)
        start_b = start_a + timedelta(minutes=30)
        booking_b = BookingDB(
            customer_id=user_id,
            start_ts=start_b,
            end_ts=start_b + timedelta(hours=2),
            party_size=3,
            status="confirmed",
        )
        db.session.add(booking_b)
        db.session.commit()
        tr_b = TableReservationDB(
            booking_id=booking_b.id,
            table_id=table_id,
            customer_id=user_id,
            start_ts=booking_b.start_ts,
            end_ts=booking_b.end_ts,
            party_size=3,
            status="confirmed",
        )
        db.session.add(tr_b)

        # Reservation to become completed (should appear in neither list)
        start_c = start_a + timedelta(minutes=60)
        booking_c = BookingDB(
            customer_id=user_id,
            start_ts=start_c,
            end_ts=start_c + timedelta(hours=2),
            party_size=4,
            status="confirmed",
        )
        db.session.add(booking_c)
        db.session.commit()
        tr_c = TableReservationDB(
            booking_id=booking_c.id,
            table_id=table_id,
            customer_id=user_id,
            start_ts=booking_c.start_ts,
            end_ts=booking_c.end_ts,
            party_size=4,
            status="confirmed",
        )
        db.session.add(tr_c)
        db.session.commit()

        confirmed_id = tr_a.id
        seated_id = tr_b.id
        completed_id = tr_c.id

    _register_and_login_staff(client, email="stewardboundaries@example.com")

    assert client.patch(f"/api/steward/reservations/{seated_id}/seat").status_code == 200
    assert client.patch(f"/api/steward/reservations/{completed_id}/seat").status_code == 200
    assert client.patch(f"/api/steward/reservations/{completed_id}/complete").status_code == 200

    pending_resp = client.get("/api/steward/reservations")
    assert pending_resp.status_code == 200
    pending_ids = {item["id"] for item in pending_resp.get_json()}
    assert confirmed_id in pending_ids
    assert seated_id not in pending_ids
    assert completed_id not in pending_ids

    seated_resp = client.get("/api/steward/reservations/seated")
    assert seated_resp.status_code == 200
    seated_ids = {item["id"] for item in seated_resp.get_json()}
    assert seated_id in seated_ids
    assert confirmed_id not in seated_ids
    assert completed_id not in seated_ids


def test_steward_status_transitions_publish_domain_events(client, app, test_data):
    class FakeEventBus:
        def __init__(self):
            self.events = []

        def publish(self, event):
            self.events.append(event)

    app.event_bus = FakeEventBus()

    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(
            booking_id=booking.id,
            table_id=table_id,
            customer_id=user_id,
            start_ts=start_ts,
            end_ts=end_ts,
            party_size=2,
            status="confirmed",
        )
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

    _register_and_login_staff(client, email="stewardevents@example.com")

    seat_resp = client.patch(f"/api/steward/reservations/{reservation_id}/seat")
    assert seat_resp.status_code == 200
    assert any(isinstance(event, ReservationSeated) for event in app.event_bus.events)
    seated_event = next(event for event in app.event_bus.events if isinstance(event, ReservationSeated))
    assert seated_event.reservation_id == reservation_id
    assert seated_event.seated_by_role == "staff"

    app.event_bus.events.clear()
    complete_resp = client.patch(f"/api/steward/reservations/{reservation_id}/complete")
    assert complete_resp.status_code == 200
    assert any(isinstance(event, ReservationCompleted) for event in app.event_bus.events)
    completed_event = next(event for event in app.event_bus.events if isinstance(event, ReservationCompleted))
    assert completed_event.reservation_id == reservation_id
    assert completed_event.completed_by_role == "staff"


def test_update_reservation_publishes_realtime_event(client, app, test_data, monkeypatch):
    class FakeEventBus:
        def __init__(self):
            self.events = []

        def publish(self, event):
            self.events.append(event)

    app.event_bus = FakeEventBus()

    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
        db.session.add(booking)
        db.session.commit()

        reservation = TableReservationDB(
            booking_id=booking.id,
            table_id=table_id,
            customer_id=user_id,
            start_ts=start_ts,
            end_ts=end_ts,
            party_size=2,
            status="confirmed",
            notes="Initial",
        )
        db.session.add(reservation)
        db.session.commit()
        reservation_id = reservation.id

    _register_and_login_staff(client, email="stewardrealtime@example.com")

    updated_start = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(second=0, microsecond=0, tzinfo=None)
    updated_end = updated_start + timedelta(hours=2)
    payload = {
        "table_id": table_id,
        "start_ts": updated_start.isoformat(timespec="minutes"),
        "end_ts": updated_end.isoformat(timespec="minutes"),
        "party_size": 4,
        "notes": "Updated by steward",
    }
    resp = client.patch(f"/api/steward/reservations/{reservation_id}", json=payload)

    assert resp.status_code == 200
    assert any(isinstance(event, ReservationUpdated) for event in app.event_bus.events)
    updated_event = next(event for event in app.event_bus.events if isinstance(event, ReservationUpdated))
    assert updated_event.reservation_id == reservation_id
    assert updated_event.updated_by_role == "staff"
