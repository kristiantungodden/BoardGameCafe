from abc import ABC, abstractmethod
from typing import Optional, Sequence
 
from features.games.domain.models.incident import Incident
 
 
class IncidentRepositoryInterface(ABC):
 
    @abstractmethod
    def add(self, incident: Incident) -> Incident:
        raise NotImplementedError
 
    @abstractmethod
    def get_by_id(self, incident_id: int) -> Optional[Incident]:
        raise NotImplementedError
 
    @abstractmethod
    def list_all(self) -> Sequence[Incident]:
        raise NotImplementedError
 
    @abstractmethod
    def list_for_game_copy(self, game_copy_id: int) -> Sequence[Incident]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, incident_id: int) -> bool:
        """Delete an incident by id. Returns True if deleted, False if not found."""
        raise NotImplementedError