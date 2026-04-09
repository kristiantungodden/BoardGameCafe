from typing import Optional

from sqlalchemy.orm import Session

from features.games.application.interfaces.game_tag_repository_interface import (
    GameTagRepositoryInterface,
)
from features.games.domain.models.game_tag import GameTag
from features.games.domain.models.game_tag_link import GameTagLink
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_tag_db import GameTagDB
from features.games.infrastructure.database.game_tag_link_db import GameTagLinkDB
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db


class GameTagRepository(GameTagRepositoryInterface):
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().lower()

    def create_tag(self, name: str) -> GameTag:
        normalized = self._normalize_name(name)
        if not normalized:
            raise ValidationError("Tag name cannot be empty")

        existing = self.session.query(GameTagDB).filter_by(name=normalized).first()
        if existing is not None:
            raise ValidationError("Tag already exists")

        row = GameTagDB(name=normalized)
        self.session.add(row)
        self.session.commit()
        return GameTag(id=row.id, name=row.name)

    def list_tags(self) -> list[GameTag]:
        rows = self.session.query(GameTagDB).order_by(GameTagDB.name.asc()).all()
        return [GameTag(id=row.id, name=row.name) for row in rows]

    def get_tag_by_id(self, tag_id: int) -> Optional[GameTag]:
        row = self.session.get(GameTagDB, tag_id)
        if row is None:
            return None
        return GameTag(id=row.id, name=row.name)

    def attach_tag_to_game(self, game_id: int, tag_id: int) -> GameTagLink:
        game = self.session.get(GameDB, game_id)
        if game is None:
            raise ValidationError("Game not found")

        tag = self.session.get(GameTagDB, tag_id)
        if tag is None:
            raise ValidationError("Tag not found")

        existing_link = (
            self.session.query(GameTagLinkDB)
            .filter(GameTagLinkDB.game_id == game_id)
            .filter(GameTagLinkDB.game_tag_id == tag_id)
            .first()
        )
        if existing_link is not None:
            raise ValidationError("Tag is already linked to this game")

        row = GameTagLinkDB(game_id=game_id, game_tag_id=tag_id)
        self.session.add(row)
        self.session.commit()
        return GameTagLink(id=row.id, game_id=row.game_id, game_tag_id=row.game_tag_id)

    def remove_tag_from_game(self, game_id: int, tag_id: int) -> bool:
        row = (
            self.session.query(GameTagLinkDB)
            .filter(GameTagLinkDB.game_id == game_id)
            .filter(GameTagLinkDB.game_tag_id == tag_id)
            .first()
        )
        if row is None:
            return False

        self.session.delete(row)
        self.session.commit()
        return True

    def list_tags_for_game(self, game_id: int) -> list[GameTag]:
        game = self.session.get(GameDB, game_id)
        if game is None:
            raise ValidationError("Game not found")

        rows = (
            self.session.query(GameTagDB)
            .join(GameTagLinkDB, GameTagLinkDB.game_tag_id == GameTagDB.id)
            .filter(GameTagLinkDB.game_id == game_id)
            .order_by(GameTagDB.name.asc())
            .all()
        )
        return [GameTag(id=row.id, name=row.name) for row in rows]
