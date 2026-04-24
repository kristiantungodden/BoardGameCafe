from __future__ import annotations

from features.reservations.application.interfaces.reservation_qr_repository_interface import (
    ReservationQRCodeRepositoryInterface,
)
from features.reservations.infrastructure.database.reservation_qr_codes_db import (
    ReservationQRCodeDB,
)
from shared.infrastructure import db


class SqlAlchemyReservationQRCodeRepository(ReservationQRCodeRepositoryInterface):
    def __init__(self, session=None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit

    def delete_for_reservation(self, reservation_id: int) -> None:
        self.session.query(ReservationQRCodeDB).filter(
            ReservationQRCodeDB.reservation_id == reservation_id
        ).delete(synchronize_session=False)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()