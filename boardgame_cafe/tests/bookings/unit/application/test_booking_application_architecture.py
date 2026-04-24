import inspect
from typing import get_type_hints


def test_booking_application_modules_do_not_import_infrastructure_session_or_models():
    from features.bookings.application.use_cases import booking_lifecycle_use_cases
    from features.bookings.application.use_cases import booking_use_cases

    source = inspect.getsource(booking_lifecycle_use_cases) + inspect.getsource(booking_use_cases)

    forbidden_patterns = [
        "db.session",
        "from shared.infrastructure import db",
        "BookingDB",
        "TableDB",
        "GameDB",
        ".infrastructure.database",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in source, f"Booking application layer should not contain '{pattern}'"


def test_create_booking_use_case_depends_on_repository_interfaces():
    from features.bookings.application.use_cases.booking_use_cases import CreateBookingUseCase
    from features.games.application.interfaces.game_repository_interface import (
        GameRepositoryInterface,
    )
    from features.tables.application.interfaces.table_repository import (
        TableRepository as TableRepositoryInterface,
    )

    hints = get_type_hints(CreateBookingUseCase.__init__)

    assert hints["table_repo"] == TableRepositoryInterface
    assert hints["game_lookup_repo"] == GameRepositoryInterface