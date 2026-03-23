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
	from infrastructure import db

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
	from infrastructure import db

	with app.app_context():
		yield db.session


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
