"""FastAPI Dependency Providers."""

from typing import Generator, Optional
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.feedback_repository import FeedbackRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    auto_error=False,
)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_analysis_repo(db: Session = Depends(get_db)) -> AnalysisRepository:
    return AnalysisRepository(db)


def get_feedback_repo(db: Session = Depends(get_db)) -> FeedbackRepository:
    return FeedbackRepository(db)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    """Validate Bearer JWT token and return authenticated User."""
    if not token:
        raise AuthenticationError("Authentication token is required.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload: missing subject identifier.")

    user = user_repo.get_by_id(user_id)
    if not user:
        raise AuthenticationError("User account not found.")

    if not user.is_active:
        raise ForbiddenError("User account is inactive.")

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repo),
) -> Optional[User]:
    """Return authenticated User if token is present, otherwise None for guest analysis."""
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = user_repo.get_by_id(user_id)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
