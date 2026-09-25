"""Analysis Pydantic schemas for request and rich response representation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.utils.constants import ScamCategory, RiskLevel, IndicatorSeverity, InputSource


class TextAnalysisRequest(BaseModel):
    """Request schema accepting either 'text' or 'message' field."""
    text: Optional[str] = Field(
        None,
        min_length=1,
        max_length=20000,
        description="The message / conversation text to analyze for financial scam indicators.",
        examples=[
            "Dear Customer, your SBI A/C will be suspended today due to KYC expired. Click here to update: http://sbi-verify-kyc.xyz"
        ],
    )
    message: Optional[str] = Field(
        None,
        description="Alias for text message to analyze.",
    )
    language: Optional[str] = Field(
        "auto",
        description="Optional language code (e.g. 'auto', 'en', 'ta', 'hi'). If omitted or 'auto', language is detected automatically.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_text_or_message(cls, values: Any) -> Any:
        if isinstance(values, dict):
            text_val = values.get("text") or values.get("message")
            if not text_val or not str(text_val).strip():
                raise ValueError("The message or text field cannot be empty.")
            values["text"] = str(text_val)
            values["message"] = str(text_val)
        return values


class MessageAnalysisRequest(TextAnalysisRequest):
    """Alias for message analysis request."""
    pass


class IndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    type: Optional[str] = "urgent_language"
    title: str
    description: str = ""
    severity: Union[IndicatorSeverity, str] = IndicatorSeverity.MEDIUM
    confidence: float = Field(0.9, ge=0.0, le=1.0)
    evidence: Optional[str] = None
    snippet: Optional[str] = None
    rule_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_evidence_and_type(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if not values.get("evidence"):
                values["evidence"] = values.get("snippet") or values.get("description") or values.get("title")
            if not values.get("snippet"):
                values["snippet"] = values.get("evidence")
            if not values.get("type"):
                rule = values.get("rule_id", "").lower()
                if "urgent" in rule or "urgency" in values.get("title", "").lower():
                    values["type"] = "urgent_language"
                elif "kyc" in rule or "phishing" in rule:
                    values["type"] = "fake_kyc"
                elif "qr" in rule or "upi" in rule or "payment" in rule:
                    values["type"] = "payment_request"
                elif "otp" in rule or "credential" in rule:
                    values["type"] = "credential_theft"
                else:
                    values["type"] = "suspicious_indicator"
        return values


class ExtractedEntities(BaseModel):
    urls: List[str] = []
    suspicious_shorteners: List[str] = []
    ip_urls: List[str] = []
    upi_ids: List[str] = []
    crypto_wallets: List[str] = []
    phone_numbers: List[str] = []
    bank_accounts: List[str] = []
    remote_access_tools: List[str] = []


class RiskBreakdown(BaseModel):
    urgency_score: float = Field(..., ge=0.0, le=100.0, description="Pressure and artificial urgency factor")
    credential_risk: float = Field(..., ge=0.0, le=100.0, description="Attempts to steal OTP/PIN/KYC")
    payment_vector_risk: float = Field(..., ge=0.0, le=100.0, description="Unverifiable or reversed payment mechanics")
    coercion_risk: float = Field(..., ge=0.0, le=100.0, description="Legal threats, police impersonation, utility cut")
    link_obfuscation_risk: float = Field(..., ge=0.0, le=100.0, description="Deceptive domains or URL shorteners")


class HelplineInfo(BaseModel):
    name: str
    helpline: str
    website: str
    description: str


class LanguageDetail(BaseModel):
    code: str = "en"
    confidence: float = 0.98
    name: Optional[str] = "English"


class RiskDetail(BaseModel):
    score: float = 0.0
    level: str = "LOW"
    confidence: float = 0.95
    rule_score: Optional[float] = 0.0
    ai_score: Optional[float] = 0.0


class ScamDetail(BaseModel):
    potential_scam: bool = False
    category: str = "SAFE_NORMAL_CONVERSATION"
    category_label: str = "Safe / Normal Conversation"


class StructuredRecommendation(BaseModel):
    priority: str = "high"  # high, medium, low
    text: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Core IDs
    id: str
    analysis_id: Optional[str] = None
    input_source: InputSource = InputSource.TEXT
    input_type: str = "message"

    # Raw / Cleaned
    raw_text: str = ""
    cleaned_text: str = ""

    # Language details
    detected_language: str = "en"
    language_confidence: float = 1.0
    language: Optional[LanguageDetail] = None

    # Risk details
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: Union[RiskLevel, str] = RiskLevel.SAFE
    is_scam: bool = False
    risk: Optional[RiskDetail] = None

    # Scam classification
    scam_category: Union[ScamCategory, str] = ScamCategory.SAFE_NORMAL_CONVERSATION
    category_title: str = "Safe / Legitimate Conversation"
    category_description: str = ""
    golden_rule: str = ""
    scam: Optional[ScamDetail] = None

    # Red flag indicators & explanations
    explanation: str = "No major scam indicators detected."
    indicators: List[IndicatorResponse] = []
    recommendations: Union[List[StructuredRecommendation], List[str]] = []

    # Risk breakdown & Entities
    risk_breakdown: Optional[RiskBreakdown] = None
    extracted_entities: Optional[ExtractedEntities] = None
    helplines: List[HelplineInfo] = []

    # Telemetry
    llm_provider_used: str = "rule_based"
    analysis_mode: str = "ai_plus_rules"
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    @classmethod
    def populate_nested_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # analysis_id alias
            if not values.get("analysis_id") and values.get("id"):
                values["analysis_id"] = str(values["id"])
            if not values.get("id") and values.get("analysis_id"):
                values["id"] = str(values["analysis_id"])

            # input_type
            src = str(values.get("input_source", "TEXT")).lower()
            values["input_type"] = "screenshot" if "image" in src or "ocr" in src else "message"

            # language detail
            lang_code = values.get("detected_language", "en")
            lang_conf = float(values.get("language_confidence", 0.98))
            if not values.get("language"):
                values["language"] = LanguageDetail(code=lang_code, confidence=lang_conf)

            # risk detail
            score = float(values.get("risk_score", 0.0))
            lvl = values.get("risk_level", "LOW")
            lvl_str = lvl.value if hasattr(lvl, "value") else str(lvl)
            if not values.get("risk"):
                values["risk"] = RiskDetail(
                    score=score,
                    level=lvl_str,
                    confidence=0.95,
                    rule_score=float(values.get("rule_score", score)),
                    ai_score=float(values.get("ai_score", score)),
                )

            # scam detail
            cat = values.get("scam_category", "SAFE_NORMAL_CONVERSATION")
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            is_scam_val = bool(values.get("is_scam", score >= 30.0))
            cat_label = values.get("category_title") or cat_str.replace("_", " ").title()
            if not values.get("scam"):
                values["scam"] = ScamDetail(
                    potential_scam=is_scam_val,
                    category=cat_str.lower(),
                    category_label=cat_label,
                )

            # structured recommendations
            raw_recs = values.get("recommendations", [])
            if raw_recs and isinstance(raw_recs[0], str):
                structured = []
                for i, r in enumerate(raw_recs):
                    priority = "high" if i < 2 else ("medium" if i < 4 else "low")
                    structured.append(StructuredRecommendation(priority=priority, text=r))
                values["recommendations"] = structured

            # analysis_mode
            if not values.get("analysis_mode"):
                provider = str(values.get("llm_provider_used", "rule_based"))
                values["analysis_mode"] = "fallback_rules" if "rule" in provider else "ai_plus_rules"

        return values


class ScamTypeMetadataResponse(BaseModel):
    category: Union[ScamCategory, str]
    title: str
    description: str
    common_victims: str
    golden_rule: str
