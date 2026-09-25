"""User Scan History and Analytics API Endpoints."""

import math
from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_analysis_repo, get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.analysis import Analysis
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import (
    AnalysisResponse,
    ExtractedEntities,
    IndicatorResponse,
    RiskBreakdown,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.history import HistoryItemResponse, HistoryStatsResponse
from app.services.recommendation_service import recommendation_service
from app.services.risk_engine import risk_engine
from app.utils.constants import (
    SCAM_CATEGORY_METADATA,
    IndicatorSeverity,
    InputSource,
    RiskLevel,
    ScamCategory,
)

router = APIRouter(prefix="/history", tags=["Scan History & Analytics"])


def _format_history_detail(db_analysis: Analysis) -> AnalysisResponse:
    """Helper to convert db record to full AnalysisResponse schema."""
    try:
        category_enum = ScamCategory(db_analysis.scam_category)
    except ValueError:
        category_enum = ScamCategory.SUSPICIOUS_UNKNOWN

    meta = SCAM_CATEGORY_METADATA.get(category_enum, {})
    category_title = meta.get("title", category_enum.value)
    category_desc = meta.get("description", "")
    golden_rule = meta.get("golden_rule", "")

    try:
        risk_level_enum = RiskLevel(db_analysis.risk_level)
    except ValueError:
        risk_level_enum = RiskLevel.MEDIUM

    try:
        input_source_enum = InputSource(db_analysis.input_source)
    except ValueError:
        input_source_enum = InputSource.TEXT

    indicator_responses = []
    for ind in db_analysis.indicators:
        try:
            sev_enum = IndicatorSeverity(ind.severity)
        except ValueError:
            sev_enum = IndicatorSeverity.MEDIUM

        indicator_responses.append(
            IndicatorResponse(
                id=ind.id,
                title=ind.title,
                description=ind.description or ind.title,
                severity=sev_enum,
                confidence=ind.confidence,
                snippet=ind.snippet,
                evidence=ind.snippet,
                rule_id=ind.rule_id,
            )
        )

    entities_dict = db_analysis.extracted_entities or {}
    extracted_entities = ExtractedEntities(
        urls=entities_dict.get("urls", []),
        suspicious_shorteners=entities_dict.get("suspicious_shorteners", []),
        ip_urls=entities_dict.get("ip_urls", []),
        upi_ids=entities_dict.get("upi_ids", []),
        crypto_wallets=entities_dict.get("crypto_wallets", []),
        phone_numbers=entities_dict.get("phone_numbers", []),
        bank_accounts=entities_dict.get("bank_accounts", []),
        remote_access_tools=entities_dict.get("remote_access_tools", []),
    )

    _, _, risk_breakdown = risk_engine.compute_risk(
        urgency_score=min(100.0, db_analysis.risk_score),
        credential_risk=min(100.0, db_analysis.risk_score),
        payment_vector_risk=min(100.0, db_analysis.risk_score),
        coercion_risk=min(100.0, db_analysis.risk_score),
        link_obfuscation_risk=min(100.0, db_analysis.risk_score),
        indicators=indicator_responses,
    )

    helplines = recommendation_service.get_helplines(db_analysis.detected_language)

    return AnalysisResponse(
        id=db_analysis.id,
        analysis_id=db_analysis.id,
        input_source=input_source_enum,
        input_type="screenshot" if "image" in db_analysis.input_source.lower() else "message",
        raw_text=db_analysis.raw_text,
        cleaned_text=db_analysis.cleaned_text,
        detected_language=db_analysis.detected_language,
        language_confidence=db_analysis.language_confidence,
        scam_category=category_enum,
        category_title=category_title,
        category_description=category_desc,
        golden_rule=golden_rule,
        risk_score=db_analysis.risk_score,
        risk_level=risk_level_enum,
        is_scam=db_analysis.is_scam,
        risk_breakdown=risk_breakdown,
        explanation=db_analysis.explanation,
        recommendations=db_analysis.recommendations,
        indicators=indicator_responses,
        extracted_entities=extracted_entities,
        helplines=helplines,
        llm_provider_used=db_analysis.llm_provider_used,
        analysis_mode=getattr(db_analysis, "analysis_mode", "ai_plus_rules"),
        processing_time_ms=db_analysis.processing_time_ms,
        created_at=db_analysis.created_at,
    )


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[HistoryItemResponse]],
    summary="Get paginated analysis history for authenticated user",
)
def get_user_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    scam_category: Optional[str] = Query(None, description="Filter by scam category"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (all, low, medium, high, critical)"),
    is_scam: Optional[bool] = Query(None, description="Filter by scam classification"),
    search_query: Optional[str] = Query(None, description="Search in text or explanation"),
    current_user: User = Depends(get_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Retrieve filtered, paginated conversation scan records for the logged-in user."""
    items, total = analysis_repo.get_user_history_paginated(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        scam_category=scam_category,
        risk_level=risk_level,
        is_scam=is_scam,
        search_query=search_query,
    )

    history_items = []
    for item in items:
        try:
            cat_enum = ScamCategory(item.scam_category)
        except ValueError:
            cat_enum = ScamCategory.SUSPICIOUS_UNKNOWN

        try:
            risk_enum = RiskLevel(item.risk_level)
        except ValueError:
            risk_enum = RiskLevel.MEDIUM

        try:
            input_enum = InputSource(item.input_source)
        except ValueError:
            input_enum = InputSource.TEXT

        meta = SCAM_CATEGORY_METADATA.get(cat_enum, {})
        snippet = item.cleaned_text[:120] + ("..." if len(item.cleaned_text) > 120 else "")

        history_items.append(
            HistoryItemResponse(
                id=item.id,
                input_source=input_enum,
                snippet=snippet,
                scam_category=cat_enum,
                category_title=meta.get("title", cat_enum.value),
                risk_score=item.risk_score,
                risk_level=risk_enum,
                is_scam=item.is_scam,
                detected_language=item.detected_language,
                indicator_count=len(item.indicators) if item.indicators else 0,
                created_at=item.created_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    paginated_data = PaginatedResponse[HistoryItemResponse](
        items=history_items,
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )

    return APIResponse(
        message="Scan history retrieved successfully",
        data=paginated_data,
    )


@router.get(
    "/stats",
    response_model=APIResponse[HistoryStatsResponse],
    summary="Get user threat statistics and scan metrics",
)
def get_user_stats(
    current_user: User = Depends(get_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Retrieve aggregated scam detection statistics and threat distribution for user dashboard."""
    stats_dict = analysis_repo.get_user_statistics(user_id=current_user.id)
    stats_response = HistoryStatsResponse(**stats_dict)

    return APIResponse(
        message="Threat statistics retrieved successfully",
        data=stats_response,
    )


@router.get(
    "/{analysis_id}",
    response_model=APIResponse[AnalysisResponse],
    summary="Get past analysis detail from user history by ID",
)
def get_history_detail(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Retrieve full analysis report for a specific scan ID belonging to the authenticated user."""
    db_analysis = analysis_repo.get_user_analysis_by_id(user_id=current_user.id, analysis_id=analysis_id)
    if not db_analysis:
        raise NotFoundError(f"Analysis with ID '{analysis_id}' for current user")

    response_data = _format_history_detail(db_analysis)
    return APIResponse(
        message="History detail retrieved successfully",
        data=response_data,
    )


@router.delete(
    "/clear",
    response_model=APIResponse[dict],
    summary="Clear all scan history for current user",
)
def clear_all_history(
    current_user: User = Depends(get_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Permanently delete all scan records associated with current authenticated user."""
    deleted_count = analysis_repo.clear_user_history(user_id=current_user.id)
    return APIResponse(
        message=f"Cleared {deleted_count} scan records from history",
        data={"deleted_count": deleted_count},
    )


@router.delete(
    "/{analysis_id}",
    response_model=APIResponse[dict],
    summary="Delete a single scan record from user history",
)
def delete_single_history_item(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Delete a specific analysis record from the current user's scan history."""
    deleted = analysis_repo.delete_user_analysis(user_id=current_user.id, analysis_id=analysis_id)
    if not deleted:
        raise NotFoundError(f"Analysis with ID '{analysis_id}' for current user")

    return APIResponse(
        message="Scan record deleted successfully",
        data={"id": analysis_id},
    )
