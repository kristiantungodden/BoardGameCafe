from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Ensure `src/` modules (app, config, domain, etc.) are importable in tests.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="function")
def app():
	"""Create a fresh Flask app for each test using testing config."""
	from app import create_app
	from shared.infrastructure import db

	flask_app = create_app("testing")

	with flask_app.app_context():
		db.drop_all()
		db.create_all()
		yield flask_app
		db.session.remove()
		db.drop_all()


@pytest.fixture(scope="function")
def client(app):
	"""Flask test client fixture for API/integration tests."""
	return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
	"""Flask CLI runner fixture."""
	return app.test_cli_runner()


@pytest.fixture(scope="function")
def db_session(app):
	"""Database session fixture for repository/integration tests."""
	from shared.infrastructure import db

	with app.app_context():
		yield db.session


@pytest.fixture(scope="function")
def test_data(app):
	"""Set up test data (tables, games, game copies, users) for integration tests."""
	from shared.infrastructure import db
	from features.tables.infrastructure.database.table_db import TableDB
	from features.games.infrastructure.database.game_db import GameDB
	from features.games.infrastructure.database.game_copy_db import GameCopyDB
	from features.users.infrastructure.database.user_db import UserDB

	with app.app_context():
		# Create test tables
		table1 = TableDB(table_nr="1", capacity=4, zone="Zone A", status="available")
		table2 = TableDB(table_nr="2", capacity=6, zone="Zone B", status="available")
		db.session.add(table1)
		db.session.add(table2)
		db.session.commit()

		# Create test games
		game1 = GameDB(title="Catan", min_players=2, max_players=4, playtime_min=60, complexity=2.5, description="Resource trading game")
		game2 = GameDB(title="Chess", min_players=2, max_players=2, playtime_min=45, complexity=3.0, description="Strategy board game")
		db.session.add(game1)
		db.session.add(game2)
		db.session.commit()

		# Create test game copies
		copy1 = GameCopyDB(game_id=game1.id, copy_code="CATAN-001", status="available")
		copy2 = GameCopyDB(game_id=game1.id, copy_code="CATAN-002", status="available")
		copy3 = GameCopyDB(game_id=game2.id, copy_code="CHESS-001", status="available")
		db.session.add(copy1)
		db.session.add(copy2)
		db.session.add(copy3)
		db.session.commit()

		# Create test user
		user = UserDB(name="Test User", email="test@example.com", password_hash="hashed", role="customer")
		db.session.add(user)
		db.session.commit()

		# Return data as dictionaries with IDs (to avoid detached instance errors)
		return {
			"tables": [
				{"id": table1.id, "table_nr": "1", "capacity": 4},
				{"id": table2.id, "table_nr": "2", "capacity": 6},
			],
			"games": [
				{"id": game1.id, "title": "Catan"},
				{"id": game2.id, "title": "Chess"},
			],
			"copies": [
				{"id": copy1.id, "game_id": game1.id},
				{"id": copy2.id, "game_id": game1.id},
				{"id": copy3.id, "game_id": game2.id},
			],
			"user": {"id": user.id, "name": "Test User", "email": "test@example.com"},
		}


def pytest_collection_modifyitems(items):
	"""Auto-apply markers based on test folder location."""
	for item in items:
		path = Path(str(item.fspath)).as_posix()
		if "/tests/unit/" in path:
			item.add_marker(pytest.mark.unit)
		if "/tests/integration/" in path:
			item.add_marker(pytest.mark.integration)
		if "/tests/e2e/" in path:
			item.add_marker(pytest.mark.slow)
