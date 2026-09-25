"""User repository for database operations on User entities."""

from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.schemas.auth import UserRegisterRequest


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by case-insensitive email."""
        return self.db.query(User).filter(User.email == email.lower().strip()).first()

    def create_user(self, user_in: UserRegisterRequest, is_superuser: bool = False) -> User:
        """Create a new user with hashed password."""
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=True,
            is_superuser=is_superuser,
        )
        return self.create(db_user)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Validate email and password, returning User if credentials are valid."""
        user = self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
