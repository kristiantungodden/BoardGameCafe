from __future__ import annotations

from typing import Optional

from flask_login import current_user, login_user, logout_user

from features.users.application.interfaces import AuthSessionPortInterface
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


class FlaskLoginSessionAdapter(AuthSessionPortInterface):
    def login(self, user_id: int) -> None:
        row = db.session.get(UserDB, user_id)
        if row is None:
            return
        login_user(row)

    def logout(self) -> None:
        logout_user()

    def get_current_user_id(self) -> Optional[int]:
        if getattr(current_user, "is_authenticated", False):
            return int(current_user.get_id())
        return None