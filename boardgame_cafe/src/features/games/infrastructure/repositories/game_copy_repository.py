from typing import Optional, Sequence

from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository
from features.games.domain.models.game_copy import GameCopy
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from shared.infrastructure import db


class GameCopyRepositoryImpl(GameCopyRepository):

    def add(self, game_copy: GameCopy) -> GameCopy:
        db_copy = GameCopyDB(
            game_id=game_copy.game_id,
            copy_code=game_copy.copy_code,
            status=game_copy.status,
            location=game_copy.location,
            condition_note=game_copy.condition_note,
        )

        db.session.add(db_copy)
        db.session.commit()

        return self._to_domain(db_copy)

    def get_by_id(self, copy_id: int) -> Optional[GameCopy]:
        db_copy = GameCopyDB.query.get(copy_id)
        if not db_copy:
            return None

        return self._to_domain(db_copy)

    def list_all(self) -> Sequence[GameCopy]:
        db_copies = GameCopyDB.query.all()
        return [self._to_domain(c) for c in db_copies]

    def update(self, game_copy: GameCopy) -> GameCopy:
        db_copy = GameCopyDB.query.get(game_copy.id)

        if not db_copy:
            raise ValueError("Game copy not found")

        db_copy.status = game_copy.status
        db_copy.location = game_copy.location
        db_copy.condition_note = game_copy.condition_note

        db.session.commit()

        return self._to_domain(db_copy)

    def _to_domain(self, db_copy: GameCopyDB) -> GameCopy:
        return GameCopy(
            id=db_copy.id,
            game_id=db_copy.game_id,
            copy_code=db_copy.copy_code,
            status=db_copy.status,
            location=db_copy.location,
            condition_note=db_copy.condition_note,
            updated_at=db_copy.updated_at,
        )