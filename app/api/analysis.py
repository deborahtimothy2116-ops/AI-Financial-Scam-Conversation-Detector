"""Analysis API Endpoints for Text and Screenshot Scam Evaluation."""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from app.api.deps import (
    get_analysis_repo,
    get_feedback_repo,
    get_optional_current_user,
)
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import logger
from app.models.analysis import Analysis
from app.models.user import User
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.analysis import (
    AnalysisResponse,
    ExtractedEntities,
    IndicatorResponse,
    RiskBreakdown,
    ScamTypeMetadataResponse,
    TextAnalysisRequest,
    MessageAnalysisRequest,
)
from app.schemas.common import APIResponse
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse
from app.services.ocr_service import ocr_service
from app.services.recommendation_service import recommendation_service
from app.services.risk_engine import risk_engine
from app.services.scam_detector import scam_detector
from app.utils.constants import (
    SCAM_CATEGORY_METADATA,
    IndicatorSeverity,
    InputSource,
    RiskLevel,
    ScamCategory,
)
from app.utils.validators import validate_image_upload, validate_text_input

router = APIRouter(tags=["Scam Analysis"])


def _format_db_analysis_to_response(db_analysis: Analysis) -> AnalysisResponse:
    """Helper to convert database Analysis record into complete AnalysisResponse schema."""
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

    # Format indicators
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

    # Format extracted entities
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

    # Reconstruct risk breakdown
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


async def _process_text_analysis(
    payload: TextAnalysisRequest,
    current_user: Optional[User],
    analysis_repo: AnalysisRepository,
) -> APIResponse[AnalysisResponse]:
    """Shared pipeline execution for text and message analysis."""
    input_text = payload.text or payload.message or ""
    cleaned_input = validate_text_input(input_text)

    # Execute full analysis pipeline
    analysis_result = await scam_detector.analyze(
        raw_text=cleaned_input,
        input_source=InputSource.TEXT,
        language_override=payload.language,
    )

    # Persist record in database
    db_analysis = analysis_repo.create_analysis_record(
        raw_text=analysis_result["raw_text"],
        cleaned_text=analysis_result["cleaned_text"],
        input_source=InputSource.TEXT.value,
        detected_language=analysis_result["detected_language"],
        language_confidence=analysis_result["language_confidence"],
        scam_category=analysis_result["scam_category"].value if hasattr(analysis_result["scam_category"], "value") else str(analysis_result["scam_category"]),
        risk_score=analysis_result["risk_score"],
        risk_level=analysis_result["risk_level"].value if hasattr(analysis_result["risk_level"], "value") else str(analysis_result["risk_level"]),
        is_scam=analysis_result["is_scam"],
        explanation=analysis_result["explanation"],
        recommendations=analysis_result["recommendations"],
        extracted_entities=analysis_result["extracted_entities"].model_dump() if hasattr(analysis_result["extracted_entities"], "model_dump") else analysis_result["extracted_entities"],
        indicators_data=analysis_result["indicators"],
        llm_provider_used=analysis_result["llm_provider_used"],
        processing_time_ms=analysis_result["processing_time_ms"],
        user_id=current_user.id if current_user else None,
        ai_score=analysis_result.get("ai_score"),
        rule_score=analysis_result.get("rule_score"),
        analysis_mode=analysis_result.get("analysis_mode", "ai_plus_rules"),
    )

    response_data = AnalysisResponse(
        id=db_analysis.id,
        analysis_id=db_analysis.id,
        input_source=InputSource.TEXT,
        input_type="message",
        raw_text=db_analysis.raw_text,
        cleaned_text=db_analysis.cleaned_text,
        detected_language=db_analysis.detected_language,
        language_confidence=db_analysis.language_confidence,
        scam_category=analysis_result["scam_category"],
        category_title=analysis_result["category_title"],
        category_description=analysis_result["category_description"],
        golden_rule=analysis_result["golden_rule"],
        risk_score=db_analysis.risk_score,
        risk_level=analysis_result["risk_level"],
        is_scam=db_analysis.is_scam,
        risk_breakdown=analysis_result["risk_breakdown"],
        explanation=db_analysis.explanation,
        recommendations=analysis_result["recommendations"],
        indicators=analysis_result["indicators"],
        extracted_entities=analysis_result["extracted_entities"],
        helplines=analysis_result["helplines"],
        llm_provider_used=db_analysis.llm_provider_used,
        analysis_mode=analysis_result.get("analysis_mode", "ai_plus_rules"),
        processing_time_ms=db_analysis.processing_time_ms,
        created_at=db_analysis.created_at,
    )

    return APIResponse(
        message="Analysis completed successfully",
        data=response_data,
    )


# ---------------------------------------------------------------------------
# Message / Text Analysis Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/analyze/message",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Analyze suspicious message/conversation text",
)
async def analyze_message_endpoint(
    payload: TextAnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return await _process_text_analysis(payload, current_user, analysis_repo)


@router.post(
    "/analysis/text",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Analyze suspicious message text (legacy alias)",
    include_in_schema=False,
)
async def analyze_text_legacy(
    payload: TextAnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return await _process_text_analysis(payload, current_user, analysis_repo)


@router.post(
    "/analyze/text",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Analyze suspicious text alias",
    include_in_schema=False,
)
async def analyze_text_alias(
    payload: TextAnalysisRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return await _process_text_analysis(payload, current_user, analysis_repo)


# ---------------------------------------------------------------------------
# Screenshot / Image OCR Analysis Endpoints
# ---------------------------------------------------------------------------
async def _process_image_analysis(
    file: UploadFile,
    language: Optional[str],
    current_user: Optional[User],
    analysis_repo: AnalysisRepository,
) -> APIResponse[AnalysisResponse]:
    """Execute screenshot upload OCR and scam analysis pipeline."""
    image_bytes, mime_type, file_size = await validate_image_upload(file)

    logger.info(f"Extracting OCR text from uploaded screenshot ({file.filename}, {file_size} bytes)")
    extracted_text, ocr_confidence = await ocr_service.extract_text(image_bytes, language=language)

    if not extracted_text.strip():
        raise ValidationError("No readable text could be recognized from the uploaded image.")

    analysis_result = await scam_detector.analyze(
        raw_text=extracted_text,
        input_source=InputSource.IMAGE_OCR,
        language_override=language,
    )

    db_analysis = analysis_repo.create_analysis_record(
        raw_text=analysis_result["raw_text"],
        cleaned_text=analysis_result["cleaned_text"],
        input_source=InputSource.IMAGE_OCR.value,
        detected_language=analysis_result["detected_language"],
        language_confidence=analysis_result["language_confidence"],
        scam_category=analysis_result["scam_category"].value if hasattr(analysis_result["scam_category"], "value") else str(analysis_result["scam_category"]),
        risk_score=analysis_result["risk_score"],
        risk_level=analysis_result["risk_level"].value if hasattr(analysis_result["risk_level"], "value") else str(analysis_result["risk_level"]),
        is_scam=analysis_result["is_scam"],
        explanation=analysis_result["explanation"],
        recommendations=analysis_result["recommendations"],
        extracted_entities=analysis_result["extracted_entities"].model_dump() if hasattr(analysis_result["extracted_entities"], "model_dump") else analysis_result["extracted_entities"],
        indicators_data=analysis_result["indicators"],
        llm_provider_used=analysis_result["llm_provider_used"],
        processing_time_ms=analysis_result["processing_time_ms"],
        user_id=current_user.id if current_user else None,
        ai_score=analysis_result.get("ai_score"),
        rule_score=analysis_result.get("rule_score"),
        analysis_mode=analysis_result.get("analysis_mode", "ai_plus_rules"),
    )

    response_data = AnalysisResponse(
        id=db_analysis.id,
        analysis_id=db_analysis.id,
        input_source=InputSource.IMAGE_OCR,
        input_type="screenshot",
        raw_text=db_analysis.raw_text,
        cleaned_text=db_analysis.cleaned_text,
        detected_language=db_analysis.detected_language,
        language_confidence=db_analysis.language_confidence,
        scam_category=analysis_result["scam_category"],
        category_title=analysis_result["category_title"],
        category_description=analysis_result["category_description"],
        golden_rule=analysis_result["golden_rule"],
        risk_score=db_analysis.risk_score,
        risk_level=analysis_result["risk_level"],
        is_scam=db_analysis.is_scam,
        risk_breakdown=analysis_result["risk_breakdown"],
        explanation=db_analysis.explanation,
        recommendations=analysis_result["recommendations"],
        indicators=analysis_result["indicators"],
        extracted_entities=analysis_result["extracted_entities"],
        helplines=analysis_result["helplines"],
        llm_provider_used=db_analysis.llm_provider_used,
        analysis_mode=analysis_result.get("analysis_mode", "ai_plus_rules"),
        processing_time_ms=db_analysis.processing_time_ms,
        created_at=db_analysis.created_at,
    )

    return APIResponse(
        message="Screenshot analyzed successfully",
        data=response_data,
    )


@router.post(
    "/analyze/image",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload screenshot and analyze extracted conversation",
)
async def analyze_image_endpoint(
    file: UploadFile = File(..., description="Screenshot image file (PNG, JPG, WEBP, BMP)"),
    language: Optional[str] = Form(None, description="Optional language code (e.g. 'auto', 'en', 'ta')"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return await _process_image_analysis(file, language, current_user, analysis_repo)


@router.post(
    "/analysis/image",
    response_model=APIResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload screenshot legacy alias",
    include_in_schema=False,
)
async def analyze_image_legacy(
    file: UploadFile = File(..., description="Screenshot image file (PNG, JPG, WEBP, BMP)"),
    language: Optional[str] = Form(None, description="Optional language code (e.g. 'en', 'hi')"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return await _process_image_analysis(file, language, current_user, analysis_repo)


# ---------------------------------------------------------------------------
# Analysis Lookup and Metadata Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/analysis/categories/metadata",
    response_model=APIResponse[List[ScamTypeMetadataResponse]],
    summary="Get scam types taxonomy, definitions, and safety rules",
)
def get_categories_metadata():
    """Retrieve educational metadata on all detectable financial scam categories."""
    items = []
    for cat, data in SCAM_CATEGORY_METADATA.items():
        items.append(
            ScamTypeMetadataResponse(
                category=cat,
                title=data["title"],
                description=data["description"],
                common_victims=data["common_victims"],
                golden_rule=data["golden_rule"],
            )
        )
    return APIResponse(
        message="Categories metadata retrieved",
        data=items,
    )


@router.get(
    "/analyze/{analysis_id}",
    response_model=APIResponse[AnalysisResponse],
    summary="Get past analysis result by ID",
)
def get_analysis_by_id_analyze_route(
    analysis_id: str,
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    """Retrieve full analysis report for a specific scan ID."""
    db_analysis = analysis_repo.get_analysis_with_relations(analysis_id)
    if not db_analysis:
        raise NotFoundError(f"Analysis with ID '{analysis_id}'")

    response_data = _format_db_analysis_to_response(db_analysis)
    return APIResponse(
        message="Analysis report retrieved",
        data=response_data,
    )


@router.get(
    "/analysis/{analysis_id}",
    response_model=APIResponse[AnalysisResponse],
    summary="Get past analysis result by ID (alias)",
    include_in_schema=False,
)
def get_analysis_by_id_analysis_route(
    analysis_id: str,
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
):
    return get_analysis_by_id_analyze_route(analysis_id, analysis_repo)


@router.post(
    "/analysis/{analysis_id}/feedback",
    response_model=APIResponse[FeedbackResponse],
    summary="Submit user accuracy feedback or category correction for an analysis",
)
def submit_analysis_feedback(
    analysis_id: str,
    feedback_in: FeedbackCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
    feedback_repo: FeedbackRepository = Depends(get_feedback_repo),
):
    """Submit user accuracy evaluation or category correction for continuous AI improvement."""
    analysis = analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise NotFoundError(f"Analysis with ID '{analysis_id}'")

    feedback = feedback_repo.create_or_update_feedback(
        analysis_id=analysis_id,
        feedback_in=feedback_in,
        user_id=current_user.id if current_user else None,
    )

    return APIResponse(
        message="Feedback submitted successfully",
        data=FeedbackResponse.model_validate(feedback),
    )
