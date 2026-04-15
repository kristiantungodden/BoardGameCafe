from typing import Sequence
 
from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository
from features.games.application.interfaces.incident_repository_interface import IncidentRepositoryInterface
from features.games.domain.models.incident import Incident
from shared.domain.exceptions import InvalidStatusTransition
 
 
class ReportIncidentUseCase:
    """Workflow 6 — Steward marks a game copy as damaged or lost.
 
    Always sends the copy to maintenance regardless of incident type,
    since both damage and loss mean the copy is no longer available.
    Updates the condition note with the incident description.
    """
 
    def __init__(
        self,
        incident_repo: IncidentRepositoryInterface,
        game_copy_repo: GameCopyRepository,
    ):
        self.incident_repo = incident_repo
        self.game_copy_repo = game_copy_repo
 
    def execute(
        self,
        game_copy_id: int,
        steward_id: int,
        incident_type: str,   # "damage" or "loss"
        note: str,
    ) -> Incident:
        game_copy = self.game_copy_repo.get_by_id(game_copy_id)
        if not game_copy:
            raise ValueError(f"Game copy {game_copy_id} not found")
 
        # Send to maintenance — guard against already being there
        try:
            game_copy.send_to_maintenance()
        except InvalidStatusTransition:
            pass  # already in maintenance, still record the incident
 
        # Update condition note so stewards can see the reason at a glance
        game_copy.update_condition_note(note)
        self.game_copy_repo.update(game_copy)
 
        incident = Incident(
            game_copy_id=game_copy_id,
            reported_by=steward_id,
            incident_type=incident_type,
            note=note,
        )
        return self.incident_repo.add(incident)
 
 
class ListIncidentsUseCase:
    """List all incidents — for admin overview."""
 
    def __init__(self, incident_repo: IncidentRepositoryInterface):
        self.incident_repo = incident_repo
 
    def execute(self) -> Sequence[Incident]:
        return self.incident_repo.list_all()
 
 
class ListIncidentsForGameCopyUseCase:
    """List all incidents for a specific game copy — full history."""
 
    def __init__(self, incident_repo: IncidentRepositoryInterface):
        self.incident_repo = incident_repo
 
    def execute(self, game_copy_id: int) -> Sequence[Incident]:
        return self.incident_repo.list_for_game_copy(game_copy_id)