"""Pydantic schemas package."""

from app.schemas.common import APIResponse, ErrorResponse, PaginationMeta, PaginatedResponse
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    AuthSuccessResponse,
)
from app.schemas.analysis import (
    TextAnalysisRequest,
    IndicatorResponse,
    ExtractedEntities,
    RiskBreakdown,
    HelplineInfo,
    AnalysisResponse,
    ScamTypeMetadataResponse,
)
from app.schemas.history import (
    HistoryItemResponse,
    HistoryFilterParams,
    HistoryStatsResponse,
)
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse

__all__ = [
    "APIResponse",
    "ErrorResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "AuthSuccessResponse",
    "TextAnalysisRequest",
    "IndicatorResponse",
    "ExtractedEntities",
    "RiskBreakdown",
    "HelplineInfo",
    "AnalysisResponse",
    "ScamTypeMetadataResponse",
    "HistoryItemResponse",
    "HistoryFilterParams",
    "HistoryStatsResponse",
    "FeedbackCreateRequest",
    "FeedbackResponse",
]
