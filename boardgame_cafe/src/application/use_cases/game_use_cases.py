from typing import List, Optional
from application.interfaces.repositories.game import GameRepositoryInterface
from domain.models.game import Game


class GameUseCases:
    """Application use cases for managing board games."""

    def __init__(self, repository: GameRepositoryInterface):
        self.repository = repository

    def add_game(self, game: Game) -> Game:
        return self.repository.add_game(game)

    def get_game(self, game_id: int) -> Optional[Game]:
        return self.repository.get_game(game_id)

    def get_all_games(self) -> List[Game]:
        return self.repository.get_all_games()

    def update_game(self, game: Game) -> Game:
        return self.repository.update_game(game)

    def delete_game(self, game_id: int) -> None:
        self.repository.delete_game(game_id)