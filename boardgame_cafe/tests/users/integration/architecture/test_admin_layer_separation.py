"""Guard rails for admin presentation architecture boundaries."""

import inspect
import re


class TestAdminPresentationLayerBoundaries:
    """Ensure admin routes stay inside presentation/application boundaries."""

    def test_admin_routes_do_not_import_infrastructure_models(self):
        """
        REQUIREMENT: Admin presentation layer must not import infrastructure DB models.

        This keeps HTTP handlers independent from SQLAlchemy table models.
        """
        from features.users.presentation.api import admin_routes

        source = inspect.getsource(admin_routes)

        # Fail on DB model imports/references like UserDB, BookingDB, etc.
        infra_model_references = re.findall(r"\b[A-Z][A-Za-z0-9_]*DB\b", source)
        assert not infra_model_references, (
            "admin_routes.py should not reference infrastructure DB models directly: "
            f"{sorted(set(infra_model_references))}"
        )

        forbidden_import_patterns = [
            ".infrastructure.database",
            ".infrastructure.repositories",
        ]

        for pattern in forbidden_import_patterns:
            assert pattern not in source, (
                f"admin_routes.py should not import '{pattern}' - "
                "presentation must not depend on infrastructure"
            )

    def test_admin_routes_do_not_use_db_session_directly(self):
        """
        REQUIREMENT: Admin presentation layer must not call db.session directly.

        Querying/persistence belongs in repositories or application services.
        """
        from features.users.presentation.api import admin_routes

        source = inspect.getsource(admin_routes)

        assert "db.session" not in source, (
            "admin_routes.py should not call db.session directly - "
            "move persistence access behind application/repository boundaries"
        )
