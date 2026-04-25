from __future__ import annotations

import secrets

from sqlalchemy.orm import Session

from shared.infrastructure import db

from itsdangerous import BadSignature, URLSafeTimedSerializer
import qrcode
import qrcode.image.svg

DEFAULT_RESERVATION_QR_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
_RESERVATION_QR_PURPOSE = "reservation_check_in"
_RESERVATION_QR_SALT = "reservation-check-in"


def create_reservation_qr_token(secret_key: str, reservation_id: int) -> str:
    serializer = URLSafeTimedSerializer(secret_key, salt=_RESERVATION_QR_SALT)
    return serializer.dumps(
        {
            "purpose": _RESERVATION_QR_PURPOSE,
            "reservation_id": reservation_id,
        }
    )


def decode_reservation_qr_token(
    secret_key: str,
    token: str,
    *,
    max_age_seconds: int = DEFAULT_RESERVATION_QR_MAX_AGE_SECONDS,
) -> int:
    serializer = URLSafeTimedSerializer(secret_key, salt=_RESERVATION_QR_SALT)
    payload = serializer.loads(token, max_age=max_age_seconds)

    if payload.get("purpose") != _RESERVATION_QR_PURPOSE:
        raise BadSignature("Invalid reservation QR token")

    reservation_id = payload.get("reservation_id")
    if not isinstance(reservation_id, int) or reservation_id <= 0:
        raise BadSignature("Invalid reservation QR token")

    return reservation_id


def generate_qr_svg(data: str) -> str:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string().decode(
        "utf-8"
    )


def get_reservation_qr_token(reservation_id: int, *, session: Session | None = None) -> str | None:
    from features.reservations.infrastructure.database.reservation_qr_codes_db import (
        ReservationQRCodeDB,
    )

    active_session = session or db.session
    record = (
        active_session.query(ReservationQRCodeDB)
        .filter(ReservationQRCodeDB.reservation_id == reservation_id)
        .first()
    )
    return None if record is None else record.qr_code


def get_or_create_reservation_qr_token(
    secret_key: str,
    *,
    user_id: int,
    reservation_id: int,
    session: Session | None = None,
) -> str:
    from features.reservations.infrastructure.database.reservation_qr_codes_db import (
        ReservationQRCodeDB,
    )

    active_session = session or db.session
    record = (
        active_session.query(ReservationQRCodeDB)
        .filter(ReservationQRCodeDB.reservation_id == reservation_id)
        .first()
    )
    if record is not None:
        return record.qr_code

    token = create_reservation_qr_token(secret_key, reservation_id)
    active_session.add(
        ReservationQRCodeDB(
            user_id=user_id,
            reservation_id=reservation_id,
            qr_code=token,
        )
    )
    active_session.commit()
    return token


def get_or_create_game_copy_qr_token(
    game_copy_id: int,
    *,
    session: Session | None = None,
) -> str:
    from features.games.infrastructure.database.game_copy_qr_code_db import (
        GameCopyQRCodeDB,
    )

    active_session = session or db.session
    record = (
        active_session.query(GameCopyQRCodeDB)
        .filter(GameCopyQRCodeDB.game_copy_id == game_copy_id)
        .first()
    )
    if record is not None:
        return record.qr_code

    token = secrets.token_urlsafe(24)
    active_session.add(
        GameCopyQRCodeDB(
            game_copy_id=game_copy_id,
            qr_code=token,
        )
    )
    active_session.commit()
    return token


def get_game_copy_id_by_qr_token(
    token: str,
    *,
    session: Session | None = None,
) -> int | None:
    from features.games.infrastructure.database.game_copy_qr_code_db import (
        GameCopyQRCodeDB,
    )

    active_session = session or db.session
    record = (
        active_session.query(GameCopyQRCodeDB)
        .filter(GameCopyQRCodeDB.qr_code == token)
        .first()
    )
    return None if record is None else record.game_copy_id