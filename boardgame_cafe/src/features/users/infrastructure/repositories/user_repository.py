"""SQLAlchemy implementation of UserRepository."""

from typing import Optional, Sequence
from features.users.application.interfaces.user_repository_interface import UserRepositoryInterface
from features.users.domain.models.user import User, Role
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db

#--------------------------------------------------------------------------------------
# This repository handles all database interactions for User entities using SQLAlchemy.
#--------------------------------------------------------------------------------------

class SqlAlchemyUserRepository(UserRepositoryInterface):
    """SQLAlchemy implementation of user repository."""

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        user_db = UserDB.query.get(user_id)
        if user_db is None:
            
            return None
        return self._db_to_domain(user_db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        user_db = UserDB.query.filter_by(email=email).first()
        if user_db is None:
            return None
        return self._db_to_domain(user_db)

    def save(self, user: User) -> User:
        """Save a user to the database. If the user has an ID, it will be updated. Otherwise, a new user will be created."""
        if user.id is None:
            # New user - create
            user_db = self._domain_to_db(user)
            db.session.add(user_db)
        else:
            # Existing user - update
            user_db = UserDB.query.get(user.id)
            if user_db is None:
                raise ValueError(f"User with ID {user.id} not found")
            self._update_db_from_domain(user_db, user)
        
        db.session.commit()
        # Refresh from DB to get any auto-generated values
        db.session.refresh(user_db)
        return self._db_to_domain(user_db)

    def delete(self, user_id: int) -> bool:
        """Delete a user from the database. Returns True if deleted, False if not found."""
        user_db = UserDB.query.get(user_id)
        if user_db is None:
            return False
        db.session.delete(user_db)
        db.session.commit()
        return True

    def list_all(self) -> Sequence[User]:
        """List all users."""
        users_db = UserDB.query.all()
        return [self._db_to_domain(user_db) for user_db in users_db]

    def list_by_role(self, role: str) -> Sequence[User]:
        """List users by role."""
        users_db = UserDB.query.filter_by(role=role).all()
        return [self._db_to_domain(user_db) for user_db in users_db]

    # Helper methods
    def _db_to_domain(self, user_db: UserDB) -> User:
        """Convert database model to domain model."""
        return User(
            id=user_db.id,
            name=user_db.name,
            email=user_db.email,
            password_hash=user_db.password_hash,
            role=Role(user_db.role),
            force_password_change=user_db.force_password_change,
            phone=user_db.phone,
        )

    def _domain_to_db(self, user: User) -> UserDB:
        """Convert domain model to database model."""
        return UserDB(
            id=user.id,
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role.value,
            force_password_change=user.force_password_change,
            phone=user.phone,
        )

    def _update_db_from_domain(self, user_db: UserDB, user: User) -> None:
        """Update database model fields from domain model."""
        user_db.name = user.name
        user_db.email = user.email
        user_db.password_hash = user.password_hash
        user_db.role = user.role.value
        user_db.force_password_change = user.force_password_change
        user_db.phone = user.phone