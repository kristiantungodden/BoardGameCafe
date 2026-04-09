# src/infrastructure/repositories/game_repository.py
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from features.games.domain.models.game import Game  # Domain model
from shared.infrastructure import db  # Flask-SQLAlchemy instance
from features.games.infrastructure import GameDB  # SQLAlchemy model

class GameRepository:
    """SQLAlchemy implementation of the Game repository."""

    def __init__(self, session: Session = None):
        self.session = session or db.session

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

    def get_all_games(self) -> List[Game]:
        return self.get_all()

    def get_games_filtered(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        min_players: Optional[int] = None,
        max_players: Optional[int] = None,
        complexity: Optional[float] = None,
        tag_name: Optional[str] = None,
    ) -> Tuple[List[Game], int, int, int]:
        """
        Get games with optional filtering and pagination.
        
        Returns: (games, total_count, page, page_size)
        """
        # Validate pagination params
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Max 100 per page
        
        # Build query with filters
        query = self.session.query(GameDB)
        
        # Apply filters
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(GameDB.title.ilike(search_term))
        
        if min_players is not None:
            # Games that can be played with at least min_players
            query = query.filter(GameDB.max_players >= min_players)
        
        if max_players is not None:
            # Games where the maximum player count is at most max_players
            query = query.filter(GameDB.max_players <= max_players)
        
        if complexity is not None:
            query = query.filter(GameDB.complexity == complexity)
        
        if tag_name:
            # Join with tags if filtering by tag
            from features.games.infrastructure.database.game_tag_db import GameTagDB
            from features.games.infrastructure.database.game_tag_link_db import GameTagLinkDB
            
            normalized_tag = tag_name.lower().strip()
            query = query.join(GameTagLinkDB).join(GameTagDB).filter(
                GameTagDB.name == normalized_tag
            ).distinct()
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        db_games = query.offset(offset).limit(page_size).all()
        
        # Convert to domain models
        games = [
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
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return games, total_count, page, page_size

    def _game_db_to_domain(self, db_game: GameDB) -> Game:
        """Convert GameDB model to Game domain model."""
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