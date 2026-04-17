from typing import Optional, Sequence
 
from sqlalchemy.orm import Session
 
from features.games.application.interfaces.incident_repository_interface import (
    IncidentRepositoryInterface,
)
from features.games.domain.models.incident import Incident as DomainIncident
from features.games.infrastructure.database.incident_db import IncidentDB
from shared.infrastructure import db
 
 
class SqlAlchemyIncidentRepository(IncidentRepositoryInterface):
    def __init__(self, session: Optional[Session] = None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit
 
    def add(self, incident: DomainIncident) -> DomainIncident:
        row = IncidentDB(
            game_copy_id=incident.game_copy_id,
            reported_by=incident.reported_by,
            incident_type=incident.incident_type,
            note=incident.note,
        )
        self.session.add(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return row.to_domain()
 
    def get_by_id(self, incident_id: int) -> Optional[DomainIncident]:
        row = self.session.get(IncidentDB, incident_id)
        if row is None:
            return None
        return row.to_domain()
 
    def list_all(self) -> Sequence[DomainIncident]:
        rows = (
            self.session.query(IncidentDB)
            .order_by(IncidentDB.created_at.desc())
            .all()
        )
        return [row.to_domain() for row in rows]
 
    def list_for_game_copy(self, game_copy_id: int) -> Sequence[DomainIncident]:
        rows = (
            self.session.query(IncidentDB)
            .filter(IncidentDB.game_copy_id == game_copy_id)
            .order_by(IncidentDB.created_at.desc())
            .all()
        )
        return [row.to_domain() for row in rows]

    def delete(self, incident_id: int) -> bool:
        row = self.session.get(IncidentDB, incident_id)
        if row is None:
            return False
        self.session.delete(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return True