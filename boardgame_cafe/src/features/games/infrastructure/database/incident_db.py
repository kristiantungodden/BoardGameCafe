from shared.infrastructure import db
from features.games.domain.models.incident import Incident as DomainIncident
 
 
class IncidentDB(db.Model):
    __tablename__ = "incidents"
 
    id = db.Column(db.Integer, primary_key=True)
    game_copy_id = db.Column(
        db.Integer, db.ForeignKey("game_copies.id"), nullable=False
    )
    reported_by = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    incident_type = db.Column(db.String(20), nullable=False)   # "damage" or "loss"
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
 
    game_copy = db.relationship("GameCopyDB", backref="incidents")
    steward = db.relationship("UserDB", backref="reported_incidents")
 
    def to_domain(self) -> DomainIncident:
        return DomainIncident(
            id=self.id,
            game_copy_id=self.game_copy_id,
            reported_by=self.reported_by,
            incident_type=self.incident_type,
            note=self.note,
            created_at=self.created_at,
        )