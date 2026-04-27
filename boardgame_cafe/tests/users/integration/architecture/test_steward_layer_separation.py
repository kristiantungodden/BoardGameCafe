"""Guard rails for steward presentation architecture boundaries."""

import inspect


class TestStewardPresentationLayerBoundaries:
    """Ensure steward routes stay inside presentation/application boundaries."""

    def test_steward_routes_do_not_import_infrastructure_models(self):
        """
        REQUIREMENT: Steward presentation layer must not import infrastructure DB models.

        HTTP handlers should work with application services and DTOs, not SQLAlchemy models.
        """
        from features.users.presentation.api import steward_routes

        source = inspect.getsource(steward_routes)

        forbidden_db_references = [
            "TableReservationDB",
            "GameReservationDB",
            "GameCopyDB",
            "BookingDB",
            "UserDB",
            ".infrastructure.database",
            ".infrastructure.repositories",
        ]

        for pattern in forbidden_db_references:
            assert pattern not in source, (
                f"steward_routes.py should not reference '{pattern}' - "
                "presentation must not depend on infrastructure"
            )

    def test_steward_routes_do_not_use_db_session_directly(self):
        """
        REQUIREMENT: Steward presentation layer must not call db.session directly.

        Persistence access belongs in repositories or application services.
        """
        from features.users.presentation.api import steward_routes

        source = inspect.getsource(steward_routes)

        assert "db.session" not in source, (
            "steward_routes.py should not call db.session directly - "
            "move persistence access behind application/repository boundaries"
        )


class TestStewardCompositionLayerBoundaries:
    """Ensure steward composition wires dependencies only."""

    def test_steward_factories_do_not_import_presentation(self):
        """
        REQUIREMENT: Steward composition must not depend on presentation.

        Composition can wire infrastructure repositories to application use cases,
        but it should not reach back into the HTTP layer.
        """
        from features.users.composition import steward_use_case_factories

        source = inspect.getsource(steward_use_case_factories)

        assert "features.users.presentation" not in source, (
            "steward_use_case_factories.py should not import presentation modules"
        )
        assert "db.session" not in source, (
            "steward_use_case_factories.py should not access db.session directly"
        )
