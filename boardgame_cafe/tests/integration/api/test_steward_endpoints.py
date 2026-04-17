from datetime import datetime, timedelta, timezone

from shared.infrastructure import db
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.bookings.infrastructure.database.booking_status_history_db import BookingStatusHistoryDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB


def test_steward_list_and_seat_flow(client, app, test_data):
    # Create a booking and table reservation for today
    with app.app_context():
        user_id = test_data["user"]["id"]
        table_id = test_data["tables"][0]["id"]
        start_ts = datetime.now(timezone.utc)
        end_ts = start_ts + timedelta(hours=2)
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=3)
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=3, status="confirmed")
        db.session.add(tr)
        db.session.commit()

        reservation_id = tr.id

    # Register and login a staff user
    staff_payload = {"name": "Steward", "email": "steward@example.com", "password": "password123", "role": "staff"}
    reg = client.post("/api/auth/register", json=staff_payload)
    assert reg.status_code == 201

    login = client.post("/api/auth/login", json={"email": "steward@example.com", "password": "password123"})
    assert login.status_code == 200

    # List active reservations
    resp = client.get("/api/steward/reservations")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(r["id"] == reservation_id for r in data)

    # Seat the reservation
    seat_resp = client.patch(f"/api/steward/reservations/{reservation_id}/seat")
    assert seat_resp.status_code == 200
    seat_data = seat_resp.get_json()
    assert seat_data["id"] == reservation_id
    assert seat_data["status"] == "seated"

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
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

    staff_payload = {"name": "Steward", "email": "steward@example.com", "password": "password123", "role": "staff"}
    client.post("/api/auth/register", json=staff_payload)
    client.post("/api/auth/login", json={"email": "steward@example.com", "password": "password123"})

    # Seat then complete
    client.patch(f"/api/steward/reservations/{reservation_id}/seat")
    comp = client.patch(f"/api/steward/reservations/{reservation_id}/complete")
    assert comp.status_code == 200
    data = comp.get_json()
    assert data["id"] == reservation_id
    assert data["status"] == "completed"

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
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
        db.session.add(booking)
        db.session.commit()

        tr = TableReservationDB(booking_id=booking.id, table_id=table_id, customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2, status="confirmed")
        db.session.add(tr)
        db.session.commit()
        reservation_id = tr.id

    staff_payload = {"name": "Steward2", "email": "steward2@example.com", "password": "password123", "role": "staff"}
    client.post("/api/auth/register", json=staff_payload)
    client.post("/api/auth/login", json={"email": "steward2@example.com", "password": "password123"})

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
        booking = BookingDB(customer_id=user_id, start_ts=start_ts, end_ts=end_ts, party_size=2)
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

    staff_payload = {"name": "Steward3", "email": "steward3@example.com", "password": "password123", "role": "staff"}
    client.post("/api/auth/register", json=staff_payload)
    client.post("/api/auth/login", json={"email": "steward3@example.com", "password": "password123"})

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

    # Update new copy status to 'lost' via steward endpoint
    status_resp = client.patch(f"/api/steward/game-copies/{copy_b}/status", json={"action": "lost"})
    assert status_resp.status_code == 200
    st = status_resp.get_json()
    assert st["status"] == "lost"

    # Report an incident on copy_b
    incident_payload = {"incident_type": "damage", "note": "Edge broken"}
    rep = client.post(f"/api/steward/game-copies/{copy_b}/incidents", json=incident_payload)
    assert rep.status_code == 201
    incident = rep.get_json()
    assert incident["incident_type"] == "damage"
    assert incident["note"] == "Edge broken"

    # List incidents for the copy
    list_inc = client.get(f"/api/steward/game-copies/{copy_b}/incidents")
    assert list_inc.status_code == 200
    incidents = list_inc.get_json()
    assert any(i["id"] == incident["id"] for i in incidents)
