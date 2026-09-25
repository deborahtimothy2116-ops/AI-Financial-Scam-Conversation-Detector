"""Services package."""

from app.services.ocr_service import ocr_service, BaseOCRService, TesseractOCRService
from app.services.text_preprocessor import text_preprocessor, TextPreprocessor
from app.services.language_service import language_service, LanguageService
from app.services.llm_service import llm_service, BaseLLMProvider, RuleBasedFallbackProvider
from app.services.risk_engine import risk_engine, RiskEngine
from app.services.explanation_service import explanation_service, ExplanationService
from app.services.recommendation_service import recommendation_service, RecommendationService
from app.services.scam_detector import scam_detector, ScamDetectorService

__all__ = [
    "ocr_service",
    "BaseOCRService",
    "TesseractOCRService",
    "text_preprocessor",
    "TextPreprocessor",
    "language_service",
    "LanguageService",
    "llm_service",
    "BaseLLMProvider",
    "RuleBasedFallbackProvider",
    "risk_engine",
    "RiskEngine",
    "explanation_service",
    "ExplanationService",
    "recommendation_service",
    "RecommendationService",
    "scam_detector",
    "ScamDetectorService",
]
