"""Authentication API Routes."""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import get_user_repo, get_current_user
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthSuccessResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[AuthSuccessResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    user_in: UserRegisterRequest,
    user_repo: UserRepository = Depends(get_user_repo),
):
    existing = user_repo.get_by_email(user_in.email)
    if existing:
        raise ValidationError(f"An account with email '{user_in.email}' already exists.")

    user = user_repo.create_user(user_in)
    access_token = create_access_token(subject=user.id)

    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    user_response = UserResponse.model_validate(user)
    return APIResponse(
        message="User registered successfully",
        data=AuthSuccessResponse(user=user_response, token=token_data),
    )


@router.post(
    "/login",
    response_model=APIResponse[AuthSuccessResponse],
    summary="User login with email and password",
)
def login(
    credentials: UserLoginRequest,
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = user_repo.authenticate(credentials.email, credentials.password)
    if not user:
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Account is inactive.")

    access_token = create_access_token(subject=user.id)
    token_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    user_response = UserResponse.model_validate(user)
    return APIResponse(
        message="Login successful",
        data=AuthSuccessResponse(user=user_response, token=token_data),
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 Password Form Token endpoint (for OpenAPI/Swagger UI)",
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = user_repo.authenticate(form_data.username, form_data.password)
    if not user:
        raise AuthenticationError("Incorrect username or password.")

    access_token = create_access_token(subject=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current logged-in user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return APIResponse(
        message="Profile retrieved",
        data=UserResponse.model_validate(current_user),
    )
