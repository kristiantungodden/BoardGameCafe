# src/infrastructure/repositories/game_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session
from domain.models.game import Game  # Domain model
from infrastructure.database import Game as GameDB  # SQLAlchemy DB model
from infrastructure import db  # Flask-SQLAlchemy instance

class GameRepository:
    """SQLAlchemy implementation of the Game repository."""

    def __init__(self, session: Session = None):
        self.session = session or db.session

    # Compatibility method used by application use cases.
    def add_game(self, game: Game) -> Game:
        return self.add(game)

    # Match test name: add()
    def add(self, game: Game) -> Game:
        db_game = GameDB(
            title=game.title,
            min_players=game.min_players,
            max_players=game.max_players,
            playtime_min=game.playtime_min,
            complexity=game.complexity,
            description=game.description,
            image_url=game.image_url,
        )
        self.session.add(db_game)
        self.session.commit()
        game.id = db_game.id
        game.created_at = db_game.created_at
        return game

    # Match test name: get_by_id()
    def get_by_id(self, game_id: int) -> Optional[Game]:
        db_game = self.session.get(GameDB, game_id)
        if not db_game:
            return None
        return Game(
            id=db_game.id,
            title=db_game.title,
            min_players=db_game.min_players,
            max_players=db_game.max_players,
            playtime_min=db_game.playtime_min,
            complexity=db_game.complexity,
            description=db_game.description,
            image_url=db_game.image_url,
            created_at=db_game.created_at,
        )

    # Compatibility method used by application use cases.
    def get_game(self, game_id: int) -> Optional[Game]:
        return self.get_by_id(game_id)

    # Match test name: get_all()
    def get_all(self) -> List[Game]:
        db_games = self.session.query(GameDB).all()
        return [
            Game(
                id=g.id,
                title=g.title,
                min_players=g.min_players,
                max_players=g.max_players,
                playtime_min=g.playtime_min,
                complexity=g.complexity,
                description=g.description,
                image_url=g.image_url,
                created_at=g.created_at,
            )
            for g in db_games
        ]

    # Compatibility method used by application use cases.
    def get_all_games(self) -> List[Game]:
        return self.get_all()

    # Optional: you can keep these for API/use case usage
    def update_game(self, game: Game) -> Game:
        db_game = self.session.get(GameDB, game.id)
        if not db_game:
            raise ValueError(f"Game with id {game.id} not found")
        db_game.title = game.title
        db_game.min_players = game.min_players
        db_game.max_players = game.max_players
        db_game.playtime_min = game.playtime_min
        db_game.complexity = game.complexity
        db_game.description = game.description
        db_game.image_url = game.image_url
        self.session.commit()
        return game

    def delete_game(self, game_id: int) -> None:
        db_game = self.session.get(GameDB, game_id)
        if db_game:
            self.session.delete(db_game)
            self.session.commit()