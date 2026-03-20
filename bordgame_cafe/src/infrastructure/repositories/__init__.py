"""Repository implementations using SQLAlchemy."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from application.interfaces.repositories import (
    UserRepository,
    GameRepository,
    GameCopyRepository,
    TableRepository,
    ReservationRepository,
    PaymentRepository,
)
from domain.models import (
    User,
    Game,
    GameCopy,
    Table,
    Reservation,
    Payment,
)
from .models import (
    UserModel,
    GameModel,
    GameCopyModel,
    TableModel,
    ReservationModel,
    PaymentModel,
)


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def add(self, entity: User) -> None:
        """Add a user to the database."""
        db_user = UserModel(
            email=entity.email,
            full_name=entity.full_name,
            phone=entity.phone,
            password_hash=entity.password_hash,
            role=entity.role,
            is_active=entity.is_active,
        )
        self.db.add(db_user)
        self.db.commit()
        entity.id = db_user.id
    
    async def update(self, entity: User) -> None:
        """Update a user in the database."""
        db_user = self.db.query(UserModel).filter(UserModel.id == entity.id).first()
        if db_user:
            db_user.email = entity.email
            db_user.full_name = entity.full_name
            db_user.phone = entity.phone
            db_user.password_hash = entity.password_hash
            db_user.role = entity.role
            db_user.is_active = entity.is_active
            self.db.commit()
    
    async def delete(self, entity_id: int) -> None:
        """Delete a user from the database."""
        self.db.query(UserModel).filter(UserModel.id == entity_id).delete()
        self.db.commit()
    
    async def get_by_id(self, entity_id: int) -> Optional[User]:
        """Get a user by ID."""
        db_user = self.db.query(UserModel).filter(UserModel.id == entity_id).first()
        return self._to_domain(db_user) if db_user else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._to_domain(db_user) if db_user else None
    
    async def get_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role."""
        db_users = self.db.query(UserModel).filter(UserModel.role == role).all()
        return [self._to_domain(user) for user in db_users]
    
    @staticmethod
    def _to_domain(db_user: UserModel) -> User:
        """Convert SQLAlchemy model to domain model."""
        return User(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            phone=db_user.phone,
            password_hash=db_user.password_hash,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )


class SQLAlchemyGameRepository(GameRepository):
    """SQLAlchemy implementation of GameRepository."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def add(self, entity: Game) -> None:
        """Add a game to the database."""
        db_game = GameModel(
            title=entity.title,
            description=entity.description,
            min_players=entity.min_players,
            max_players=entity.max_players,
            playtime_minutes=entity.playtime_minutes,
            complexity_weight=entity.complexity_weight,
            image_url=entity.image_url,
            tags=",".join(entity.tags) if entity.tags else "",
            is_active=entity.is_active,
        )
        self.db.add(db_game)
        self.db.commit()
        entity.id = db_game.id
    
    async def update(self, entity: Game) -> None:
        """Update a game in the database."""
        db_game = self.db.query(GameModel).filter(GameModel.id == entity.id).first()
        if db_game:
            db_game.title = entity.title
            db_game.description = entity.description
            db_game.min_players = entity.min_players
            db_game.max_players = entity.max_players
            db_game.playtime_minutes = entity.playtime_minutes
            db_game.complexity_weight = entity.complexity_weight
            db_game.image_url = entity.image_url
            db_game.tags = ",".join(entity.tags) if entity.tags else ""
            db_game.is_active = entity.is_active
            self.db.commit()
    
    async def delete(self, entity_id: int) -> None:
        """Delete a game from the database."""
        self.db.query(GameModel).filter(GameModel.id == entity_id).delete()
        self.db.commit()
    
    async def get_by_id(self, entity_id: int) -> Optional[Game]:
        """Get a game by ID."""
        db_game = self.db.query(GameModel).filter(GameModel.id == entity_id).first()
        return self._to_domain(db_game) if db_game else None
    
    async def search_by_title(self, title: str) -> List[Game]:
        """Search games by title."""
        db_games = self.db.query(GameModel).filter(GameModel.title.ilike(f"%{title}%")).all()
        return [self._to_domain(game) for game in db_games]
    
    async def get_by_tags(self, tags: List[str]) -> List[Game]:
        """Get games by tags."""
        db_games = []
        for tag in tags:
            games = self.db.query(GameModel).filter(GameModel.tags.ilike(f"%{tag}%")).all()
            db_games.extend(games)
        # Remove duplicates
        unique_games = {game.id: game for game in db_games}
        return [self._to_domain(game) for game in unique_games.values()]
    
    @staticmethod
    def _to_domain(db_game: GameModel) -> Game:
        """Convert SQLAlchemy model to domain model."""
        tags = db_game.tags.split(",") if db_game.tags else []
        return Game(
            id=db_game.id,
            title=db_game.title,
            description=db_game.description,
            min_players=db_game.min_players,
            max_players=db_game.max_players,
            playtime_minutes=db_game.playtime_minutes,
            complexity_weight=db_game.complexity_weight,
            image_url=db_game.image_url,
            tags=tags,
            is_active=db_game.is_active,
            created_at=db_game.created_at,
            updated_at=db_game.updated_at,
        )


class SQLAlchemyTableRepository(TableRepository):
    """SQLAlchemy implementation of TableRepository."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def add(self, entity: Table) -> None:
        """Add a table to the database."""
        db_table = TableModel(
            number=entity.number,
            capacity=entity.capacity,
            location=entity.location,
            features=",".join(entity.features) if entity.features else "",
            is_active=entity.is_active,
        )
        self.db.add(db_table)
        self.db.commit()
        entity.id = db_table.id
    
    async def update(self, entity: Table) -> None:
        """Update a table in the database."""
        db_table = self.db.query(TableModel).filter(TableModel.id == entity.id).first()
        if db_table:
            db_table.number = entity.number
            db_table.capacity = entity.capacity
            db_table.location = entity.location
            db_table.features = ",".join(entity.features) if entity.features else ""
            db_table.is_active = entity.is_active
            self.db.commit()
    
    async def delete(self, entity_id: int) -> None:
        """Delete a table from the database."""
        self.db.query(TableModel).filter(TableModel.id == entity_id).delete()
        self.db.commit()
    
    async def get_by_id(self, entity_id: int) -> Optional[Table]:
        """Get a table by ID."""
        db_table = self.db.query(TableModel).filter(TableModel.id == entity_id).first()
        return self._to_domain(db_table) if db_table else None
    
    async def get_by_capacity(self, capacity: int) -> List[Table]:
        """Get tables with at least the specified capacity."""
        db_tables = self.db.query(TableModel).filter(TableModel.capacity >= capacity).all()
        return [self._to_domain(table) for table in db_tables]
    
    async def get_available_tables(self, reserved_at: datetime, reserved_until: datetime, party_size: int) -> List[Table]:
        """Get tables available for a time slot with required capacity."""
        # Get all tables with sufficient capacity
        suitable_tables = self.db.query(TableModel).filter(
            TableModel.capacity >= party_size,
            TableModel.is_active == True
        ).all()
        
        # Filter out tables with overlapping reservations
        available = []
        for table in suitable_tables:
            overlapping = self.db.query(ReservationModel).filter(
                ReservationModel.table_id == table.id,
                ReservationModel.reserved_at < reserved_until,
                ReservationModel.reserved_until > reserved_at,
            ).first()
            if not overlapping:
                available.append(self._to_domain(table))
        
        return available
    
    @staticmethod
    def _to_domain(db_table: TableModel) -> Table:
        """Convert SQLAlchemy model to domain model."""
        features = db_table.features.split(",") if db_table.features else []
        return Table(
            id=db_table.id,
            number=db_table.number,
            capacity=db_table.capacity,
            location=db_table.location,
            features=features,
            is_active=db_table.is_active,
            created_at=db_table.created_at,
            updated_at=db_table.updated_at,
        )


class SQLAlchemyReservationRepository(ReservationRepository):
    """SQLAlchemy implementation of ReservationRepository."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def add(self, entity: Reservation) -> None:
        """Add a reservation to the database."""
        db_reservation = ReservationModel(
            customer_id=entity.customer_id,
            table_id=entity.table_id,
            party_size=entity.party_size,
            reserved_at=entity.reserved_at,
            reserved_until=entity.reserved_until,
            status=entity.status,
            special_requests=entity.special_requests,
        )
        self.db.add(db_reservation)
        self.db.commit()
        entity.id = db_reservation.id
    
    async def update(self, entity: Reservation) -> None:
        """Update a reservation in the database."""
        db_reservation = self.db.query(ReservationModel).filter(ReservationModel.id == entity.id).first()
        if db_reservation:
            db_reservation.customer_id = entity.customer_id
            db_reservation.table_id = entity.table_id
            db_reservation.party_size = entity.party_size
            db_reservation.reserved_at = entity.reserved_at
            db_reservation.reserved_until = entity.reserved_until
            db_reservation.status = entity.status
            db_reservation.special_requests = entity.special_requests
            self.db.commit()
    
    async def delete(self, entity_id: int) -> None:
        """Delete a reservation from the database."""
        self.db.query(ReservationModel).filter(ReservationModel.id == entity_id).delete()
        self.db.commit()
    
    async def get_by_id(self, entity_id: int) -> Optional[Reservation]:
        """Get a reservation by ID."""
        db_reservation = self.db.query(ReservationModel).filter(ReservationModel.id == entity_id).first()
        return self._to_domain(db_reservation) if db_reservation else None
    
    async def get_by_customer_id(self, customer_id: int) -> List[Reservation]:
        """Get all reservations for a customer."""
        db_reservations = self.db.query(ReservationModel).filter(ReservationModel.customer_id == customer_id).all()
        return [self._to_domain(res) for res in db_reservations]
    
    async def get_by_table_id(self, table_id: int) -> List[Reservation]:
        """Get all reservations for a table."""
        db_reservations = self.db.query(ReservationModel).filter(ReservationModel.table_id == table_id).all()
        return [self._to_domain(res) for res in db_reservations]
    
    async def get_overlapping(self, table_id: int, reserved_at: datetime, reserved_until: datetime) -> List[Reservation]:
        """Get reservations that overlap with the given time slot."""
        db_reservations = self.db.query(ReservationModel).filter(
            ReservationModel.table_id == table_id,
            ReservationModel.reserved_at < reserved_until,
            ReservationModel.reserved_until > reserved_at,
        ).all()
        return [self._to_domain(res) for res in db_reservations]
    
    @staticmethod
    def _to_domain(db_reservation: ReservationModel) -> Reservation:
        """Convert SQLAlchemy model to domain model."""
        return Reservation(
            id=db_reservation.id,
            customer_id=db_reservation.customer_id,
            table_id=db_reservation.table_id,
            party_size=db_reservation.party_size,
            reserved_at=db_reservation.reserved_at,
            reserved_until=db_reservation.reserved_until,
            status=db_reservation.status,
            special_requests=db_reservation.special_requests,
            created_at=db_reservation.created_at,
            updated_at=db_reservation.updated_at,
        )


class SQLAlchemyPaymentRepository(PaymentRepository):
    """SQLAlchemy implementation of PaymentRepository."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def add(self, entity: Payment) -> None:
        """Add a payment to the database."""
        db_payment = PaymentModel(
            reservation_id=entity.reservation_id,
            user_id=entity.user_id,
            amount=str(entity.amount),
            currency=entity.currency,
            payment_type=entity.payment_type,
            status=entity.status,
            provider=entity.provider,
            provider_transaction_id=entity.provider_transaction_id,
            description=entity.description,
        )
        self.db.add(db_payment)
        self.db.commit()
        entity.id = db_payment.id
    
    async def update(self, entity: Payment) -> None:
        """Update a payment in the database."""
        db_payment = self.db.query(PaymentModel).filter(PaymentModel.id == entity.id).first()
        if db_payment:
            db_payment.reservation_id = entity.reservation_id
            db_payment.user_id = entity.user_id
            db_payment.amount = str(entity.amount)
            db_payment.currency = entity.currency
            db_payment.payment_type = entity.payment_type
            db_payment.status = entity.status
            db_payment.provider = entity.provider
            db_payment.provider_transaction_id = entity.provider_transaction_id
            db_payment.description = entity.description
            self.db.commit()
    
    async def delete(self, entity_id: int) -> None:
        """Delete a payment from the database."""
        self.db.query(PaymentModel).filter(PaymentModel.id == entity_id).delete()
        self.db.commit()
    
    async def get_by_id(self, entity_id: int) -> Optional[Payment]:
        """Get a payment by ID."""
        db_payment = self.db.query(PaymentModel).filter(PaymentModel.id == entity_id).first()
        return self._to_domain(db_payment) if db_payment else None
    
    async def get_by_reservation_id(self, reservation_id: int) -> Optional[Payment]:
        """Get payment for a reservation."""
        db_payment = self.db.query(PaymentModel).filter(PaymentModel.reservation_id == reservation_id).first()
        return self._to_domain(db_payment) if db_payment else None
    
    async def get_by_user_id(self, user_id: int) -> List[Payment]:
        """Get all payments for a user."""
        db_payments = self.db.query(PaymentModel).filter(PaymentModel.user_id == user_id).all()
        return [self._to_domain(payment) for payment in db_payments]
    
    @staticmethod
    def _to_domain(db_payment: PaymentModel) -> Payment:
        """Convert SQLAlchemy model to domain model."""
        from decimal import Decimal
        return Payment(
            id=db_payment.id,
            reservation_id=db_payment.reservation_id,
            user_id=db_payment.user_id,
            amount=Decimal(db_payment.amount),
            currency=db_payment.currency,
            payment_type=db_payment.payment_type,
            status=db_payment.status,
            provider=db_payment.provider,
            provider_transaction_id=db_payment.provider_transaction_id,
            description=db_payment.description,
            created_at=db_payment.created_at,
            updated_at=db_payment.updated_at,
        )
