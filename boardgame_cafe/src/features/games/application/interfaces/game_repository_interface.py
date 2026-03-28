from abc import ABC, abstractmethod
from typing import List, Optional
from features.games.domain.models.game import Game 

class GameRepositoryInterface(ABC):
    """Interface for game repository operations."""

    @abstractmethod
    def add_game(self, game: Game) -> Game:
        """Add a new game to the repository."""
        pass

    @abstractmethod
    def get_game(self, game_id: int) -> Optional[Game]:
        """Retrieve a game by its ID."""
        pass

    @abstractmethod
    def get_all_games(self) -> List[Game]:
        """Retrieve all games."""
        pass

    @abstractmethod
    def update_game(self, game: Game) -> Game:
        """Update an existing game."""
        pass

    @abstractmethod
    def delete_game(self, game_id: int) -> None:
        """Delete a game by its ID."""
        pass