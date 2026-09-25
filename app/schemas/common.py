"""Common Pydantic models and response wrappers."""

from typing import Generic, Optional, TypeVar, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard unified API response wrapper."""
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Standard unified error response."""
    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    model_config = ConfigDict(from_attributes=True)

    items: List[T]
    meta: PaginationMeta
