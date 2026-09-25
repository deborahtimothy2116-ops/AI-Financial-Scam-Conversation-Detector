"""Unit tests for specialized domain services."""

import pytest
from app.services.text_preprocessor import TextPreprocessor
from app.services.language_service import LanguageService
from app.services.risk_engine import RiskEngine
from app.services.explanation_service import ExplanationService
from app.services.recommendation_service import RecommendationService
from app.services.llm_service import RuleBasedFallbackProvider
from app.schemas.analysis import IndicatorResponse
from app.utils.constants import ScamCategory, RiskLevel, IndicatorSeverity


def test_text_preprocessor_cleaning_and_entities():
    """Test text preprocessor cleaning, zero-width stripping, and entity extraction."""
    preprocessor = TextPreprocessor()

    # Zero-width spaces & excessive spaces
    dirty_text = "Urgent\u200B\u200C message: pay to user@okhdfcbank or click https://bit.ly/scam-link now! AnyDesk needed."
    cleaned = preprocessor.clean_text(dirty_text)
    assert "\u200B" not in cleaned
    assert "\u200C" not in cleaned

    # Extract entities
    entities = preprocessor.extract_entities(cleaned)
    assert "user@okhdfcbank" in entities["upi_ids"]
    assert "https://bit.ly/scam-link" in entities["urls"]
    assert "https://bit.ly/scam-link" in entities["suspicious_shorteners"]
    assert "AnyDesk" in entities["remote_access_tools"] or "anydesk" in [t.lower() for t in entities["remote_access_tools"]]


def test_language_service_detection():
    """Test language detection for English, Hinglish, and manual override."""
    lang_service = LanguageService()

    # Hinglish
    code, name, conf = lang_service.detect_language("Aapka khata block ho jayega turant paise bhejo")
    assert code == "hinglish"

    # Override
    code_ov, name_ov, conf_ov = lang_service.detect_language("Some text", user_override="fr")
    assert code_ov == "fr"
    assert name_ov == "French"
    assert conf_ov == 1.0


def test_risk_engine_computation():
    """Test risk score calibration and severity floor logic."""
    engine = RiskEngine()

    # Low risk inputs without indicators
    score, level, breakdown = engine.compute_risk(
        urgency_score=10.0,
        credential_risk=10.0,
        payment_vector_risk=10.0,
        coercion_risk=10.0,
        link_obfuscation_risk=10.0,
        indicators=[],
    )
    assert score <= 20.0
    assert level == RiskLevel.SAFE or level == RiskLevel.LOW

    # High severity indicator override
    crit_ind = IndicatorResponse(
        title="Critical OTP Theft",
        description="Asking for OTP",
        severity=IndicatorSeverity.CRITICAL,
        confidence=0.99,
    )
    score_crit, level_crit, _ = engine.compute_risk(
        urgency_score=20.0,
        credential_risk=20.0,
        payment_vector_risk=20.0,
        coercion_risk=20.0,
        link_obfuscation_risk=20.0,
        indicators=[crit_ind],
    )
    assert score_crit >= 88.0
    assert level_crit == RiskLevel.CRITICAL


def test_explanation_and_recommendation_services():
    """Test plain-language explanations and safety recommendations."""
    expl_service = ExplanationService()
    rec_service = RecommendationService()

    # Scam explanation
    ind = IndicatorResponse(
        title="Fake QR Code",
        description="Claims you receive money by scanning",
        severity=IndicatorSeverity.CRITICAL,
        confidence=0.95,
    )
    expl = expl_service.generate_explanation(
        category=ScamCategory.UPI_QR_SCAM,
        is_scam=True,
        indicators=[ind],
        detected_language="en",
    )
    assert "UPI / QR Code Payment Trap" in expl
    assert "Fake QR Code" in expl

    # Recommendations
    recs = rec_service.get_recommendations(ScamCategory.UPI_QR_SCAM, is_scam=True)
    assert len(recs) >= 3
    assert any("UPI PIN" in r for r in recs)

    # Helplines
    helplines = rec_service.get_helplines()
    assert any(h.helpline == "1930" for h in helplines)


def test_rule_based_fallback_provider():
    """Test heuristic detection across major scam categories."""
    import asyncio

    async def _run():
        provider = RuleBasedFallbackProvider()

        # Test QR Scam
        res_qr = await provider.analyze_message(
            text="Open scanner and scan QR code to receive credit of Rs 10000 into your account.",
            extracted_entities={},
            language="English",
        )
        assert res_qr["is_scam"] is True
        assert res_qr["scam_category"] == ScamCategory.UPI_QR_SCAM.value

        # Test Remote Access
        res_remote = await provider.analyze_message(
            text="Download AnyDesk app and share 6-digit OTP code to fix banking error.",
            extracted_entities={"remote_access_tools": ["AnyDesk"]},
            language="English",
        )
        assert res_remote["is_scam"] is True
        assert res_remote["scam_category"] == ScamCategory.OTP_REMOTE_ACCESS_SCAM.value

    asyncio.run(_run())

