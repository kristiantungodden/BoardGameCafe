"""SQLAlchemy ORM models for database."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from domain.models import GameCopyStatus, ReservationStatus, PaymentStatus, PaymentType, UserRole


Base = declarative_base()


# Association table for many-to-many relationship between Reservations and GameCopies
reservation_games = Table(
    'reservation_games',
    Base.metadata,
    Column('reservation_id', Integer, ForeignKey('reservations.id'), primary_key=True),
    Column('game_copy_id', Integer, ForeignKey('game_copies.id'), primary_key=True),
)


class UserModel(Base):
    """User ORM model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    phone = Column(String, nullable=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reservations = relationship("ReservationModel", back_populates="customer")
    payments = relationship("PaymentModel", back_populates="user")


class GameModel(Base):
    """Game ORM model."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    min_players = Column(Integer)
    max_players = Column(Integer)
    playtime_minutes = Column(Integer)
    complexity_weight = Column(Float)
    image_url = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # Comma-separated or JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    copies = relationship("GameCopyModel", back_populates="game")


class GameCopyModel(Base):
    """Game Copy ORM model."""
    __tablename__ = "game_copies"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), index=True)
    barcode = Column(String, nullable=True, unique=True)
    condition = Column(String, default="good")
    status = Column(Enum(GameCopyStatus), default=GameCopyStatus.AVAILABLE)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    game = relationship("GameModel", back_populates="copies")
    reservations = relationship("ReservationModel", secondary=reservation_games, back_populates="games")


class TableModel(Base):
    """Table ORM model."""
    __tablename__ = "tables"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, index=True)
    capacity = Column(Integer)
    location = Column(String)
    features = Column(String, nullable=True)  # Comma-separated or JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reservations = relationship("ReservationModel", back_populates="table")


class ReservationModel(Base):
    """Reservation ORM model."""
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), index=True)
    party_size = Column(Integer)
    reserved_at = Column(DateTime, index=True)
    reserved_until = Column(DateTime, index=True)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.SUBMITTED)
    special_requests = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("UserModel", back_populates="reservations")
    table = relationship("TableModel", back_populates="reservations")
    games = relationship("GameCopyModel", secondary=reservation_games, back_populates="reservations")
    payment = relationship("PaymentModel", back_populates="reservation", uselist=False)


class PaymentModel(Base):
    """Payment ORM model."""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(String)  # Store as string to preserve decimal precision
    currency = Column(String, default="USD")
    payment_type = Column(Enum(PaymentType))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    provider = Column(String, default="stripe")
    provider_transaction_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserModel", back_populates="payments")
    reservation = relationship("ReservationModel", back_populates="payment")
