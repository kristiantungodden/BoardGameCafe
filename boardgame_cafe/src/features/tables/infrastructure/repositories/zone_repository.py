from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from features.tables.application.interfaces.zone_repository import ZoneRepository as ZoneRepositoryInterface
from features.tables.domain.models.zone import Zone
from features.tables.infrastructure.database import ZoneDB
from shared.infrastructure import db


class ZoneRepository(ZoneRepositoryInterface):
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    def add(self, zone: Zone) -> Zone:
        db_zone = ZoneDB(
            floor=zone.floor,
            name=zone.name,
            active=zone.active,
            notes=zone.notes,
        )
        self.session.add(db_zone)
        self.session.commit()
        return self._to_domain(db_zone)

    def get_by_id(self, zone_id: int) -> Optional[Zone]:
        db_zone = self.session.get(ZoneDB, zone_id)
        return None if db_zone is None else self._to_domain(db_zone)

    def get_by_floor_and_name(self, floor: int, name: str) -> Optional[Zone]:
        db_zone = (
            self.session.query(ZoneDB)
            .filter(ZoneDB.floor == floor, ZoneDB.name == name)
            .first()
        )
        return None if db_zone is None else self._to_domain(db_zone)

    def list(self, floor: Optional[int] = None) -> list[Zone]:
        query = self.session.query(ZoneDB)
        if floor is not None:
            query = query.filter(ZoneDB.floor == floor)
        rows = query.order_by(ZoneDB.floor.asc(), ZoneDB.name.asc()).all()
        return [self._to_domain(item) for item in rows]

    def update(self, zone: Zone) -> Zone:
        zone_id = getattr(zone, "id", None)
        if zone_id is None:
            raise ValueError("Cannot update zone without an id")

        db_zone = self.session.get(ZoneDB, zone_id)
        if db_zone is None:
            raise ValueError(f"Zone with id {zone_id} does not exist")

        db_zone.floor = zone.floor
        db_zone.name = zone.name
        db_zone.active = zone.active
        db_zone.notes = zone.notes
        self.session.commit()
        return self._to_domain(db_zone)

    def delete(self, zone_id: int) -> None:
        db_zone = self.session.get(ZoneDB, zone_id)
        if db_zone is None:
            raise ValueError(f"Zone with id {zone_id} does not exist")
        self.session.delete(db_zone)
        self.session.commit()

    @staticmethod
    def _to_domain(db_zone: ZoneDB) -> Zone:
        zone = Zone(
            floor=db_zone.floor,
            name=db_zone.name,
            active=db_zone.active,
            notes=db_zone.notes,
        )
        zone.id = db_zone.id
        return zone
