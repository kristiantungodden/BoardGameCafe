from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_user(*, role: str, email: str, password: str) -> int:
	user = UserDB(
		name=f"{role.title()} User",
		email=email,
		password_hash=hash_password(password),
		role=role,
	)
	db.session.add(user)
	db.session.commit()
	return int(user.id)


def _login(client, *, email: str, password: str) -> None:
	response = client.post(
		"/api/auth/login",
		json={"email": email, "password": password},
	)
	assert response.status_code == 200


def _create_game_copy() -> int:
	game = GameDB(
		title="Catan",
		min_players=2,
		max_players=4,
		playtime_min=60,
		complexity=2.5,
		description="Resource trading game",
	)
	db.session.add(game)
	db.session.commit()

	copy = GameCopyDB(game_id=game.id, copy_code="CATAN-STAFF-001", status="available")
	db.session.add(copy)
	db.session.commit()
	return int(copy.id)


def test_staff_can_check_out_and_check_in_game_copy_via_steward_route(app, client):
	with app.app_context():
		_create_user(role="staff", email="steward@example.com", password="StaffPass123")
		copy_id = _create_game_copy()

	_login(client, email="steward@example.com", password="StaffPass123")

	check_out_response = client.patch(
		f"/api/steward/game-copies/{copy_id}/status",
		json={"action": "use"},
	)
	assert check_out_response.status_code == 200
	assert check_out_response.get_json()["status"] == "in_use"

	check_in_response = client.patch(
		f"/api/steward/game-copies/{copy_id}/status",
		json={"action": "return"},
	)
	assert check_in_response.status_code == 200
	assert check_in_response.get_json()["status"] == "available"


def test_non_staff_cannot_change_game_copy_status_via_steward_route(app, client):
	with app.app_context():
		_create_user(role="customer", email="customer@example.com", password="CustomerPass123")
		copy_id = _create_game_copy()

	_login(client, email="customer@example.com", password="CustomerPass123")

	response = client.patch(
		f"/api/steward/game-copies/{copy_id}/status",
		json={"action": "use"},
	)
	assert response.status_code == 403
	assert response.get_json()["error"] == "Staff access required"