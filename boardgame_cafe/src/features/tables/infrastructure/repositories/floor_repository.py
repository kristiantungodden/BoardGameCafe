from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from features.tables.application.interfaces.floor_repository import FloorRepository as FloorRepositoryInterface
from features.tables.domain.models.floor import Floor
from features.tables.infrastructure.database import FloorDB
from shared.infrastructure import db


class FloorRepository(FloorRepositoryInterface):
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    def add(self, floor: Floor) -> Floor:
        db_floor = FloorDB(
            floor_nr=floor.number,
            name=floor.name,
            active=floor.active,
            notes=floor.notes,
        )
        self.session.add(db_floor)
        self.session.commit()
        return self._to_domain(db_floor)

    def get_by_id(self, floor_id: int) -> Optional[Floor]:
        db_floor = self.session.get(FloorDB, floor_id)
        return None if db_floor is None else self._to_domain(db_floor)

    def get_by_number(self, floor_number: int) -> Optional[Floor]:
        db_floor = self.session.query(FloorDB).filter(FloorDB.floor_nr == floor_number).first()
        return None if db_floor is None else self._to_domain(db_floor)

    def list(self) -> list[Floor]:
        return [self._to_domain(item) for item in self.session.query(FloorDB).order_by(FloorDB.floor_nr.asc()).all()]

    def update(self, floor: Floor) -> Floor:
        floor_id = getattr(floor, "id", None)
        if floor_id is None:
            raise ValueError("Cannot update floor without an id")

        db_floor = self.session.get(FloorDB, floor_id)
        if db_floor is None:
            raise ValueError(f"Floor with id {floor_id} does not exist")

        db_floor.floor_nr = floor.number
        db_floor.name = floor.name
        db_floor.active = floor.active
        db_floor.notes = floor.notes
        self.session.commit()
        return self._to_domain(db_floor)

    def delete(self, floor_id: int) -> None:
        db_floor = self.session.get(FloorDB, floor_id)
        if db_floor is None:
            raise ValueError(f"Floor with id {floor_id} does not exist")
        self.session.delete(db_floor)
        self.session.commit()

    @staticmethod
    def _to_domain(db_floor: FloorDB) -> Floor:
        floor = Floor(
            number=db_floor.floor_nr,
            name=db_floor.name,
            active=db_floor.active,
            notes=db_floor.notes,
        )
        floor.id = db_floor.id
        return floor