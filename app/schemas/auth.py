"""Authentication and User Pydantic Schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid user email address", examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="User full name")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered user email", examples=["user@example.com"])
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class AuthSuccessResponse(BaseModel):
    user: UserResponse
    token: TokenResponse
