import inspect
from typing import get_type_hints


def test_payment_application_modules_do_not_import_infrastructure_session_or_models():
    from features.payments.application.services import booking_payment_lifecycle
    from features.payments.application.use_cases import payment_use_cases

    source = inspect.getsource(booking_payment_lifecycle) + inspect.getsource(payment_use_cases)

    forbidden_patterns = [
        "db.session",
        "from shared.infrastructure import db",
        "PaymentDB",
        "BookingDB",
        "TableReservationDB",
        "GameReservationDB",
        "ReservationQRCodeDB",
        ".infrastructure.database",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in source, f"Payment application layer should not contain '{pattern}'"


def test_payment_lifecycle_helpers_require_repository_dependencies():
    from features.bookings.application.interfaces.booking_repository_interface import (
        BookingRepositoryInterface,
    )
    from features.bookings.application.interfaces.booking_status_history_repository_interface import (
        BookingStatusHistoryRepositoryInterface,
    )
    from features.payments.application.interfaces.payment_repository_interface import (
        PaymentRepositoryInterface,
    )
    from features.payments.application.services.booking_payment_lifecycle import (
        confirm_booking_after_success,
        fail_payment_and_cleanup_created_booking,
    )
    from features.reservations.application.interfaces.game_reservation_repository_interface import (
        GameReservationRepositoryInterface,
    )
    from features.reservations.application.interfaces.reservation_qr_repository_interface import (
        ReservationQRCodeRepositoryInterface,
    )
    from features.reservations.application.interfaces.table_reservation_repository_interface import (
        TableReservationRepositoryInterface,
    )

    confirm_hints = get_type_hints(confirm_booking_after_success)
    fail_hints = get_type_hints(fail_payment_and_cleanup_created_booking)

    assert confirm_hints["payment_repo"] == PaymentRepositoryInterface
    assert confirm_hints["booking_repo"] == BookingRepositoryInterface
    assert confirm_hints["status_history_repo"] == BookingStatusHistoryRepositoryInterface

    assert fail_hints["payment_repo"] == PaymentRepositoryInterface
    assert fail_hints["booking_repo"] == BookingRepositoryInterface
    assert fail_hints["status_history_repo"] == BookingStatusHistoryRepositoryInterface
    assert fail_hints["table_reservation_repo"] == TableReservationRepositoryInterface
    assert fail_hints["game_reservation_repo"] == GameReservationRepositoryInterface
    assert fail_hints["reservation_qr_repo"] == ReservationQRCodeRepositoryInterface