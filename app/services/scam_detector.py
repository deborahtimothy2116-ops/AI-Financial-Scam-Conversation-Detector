"""Scam Detector Pipeline Orchestrator."""

import time
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.schemas.analysis import (
    AnalysisResponse,
    ExtractedEntities,
    IndicatorResponse,
    RiskBreakdown,
)
from app.services.text_preprocessor import text_preprocessor
from app.services.language_service import language_service
from app.services.llm_service import llm_service
from app.services.risk_engine import risk_engine
from app.services.explanation_service import explanation_service
from app.services.recommendation_service import recommendation_service
from app.services.community_service import STRONG_REPORT_THRESHOLD as COMMUNITY_STRONG_THRESHOLD
from app.utils.constants import (
    ScamCategory,
    RiskLevel,
    IndicatorSeverity,
    InputSource,
    SCAM_CATEGORY_METADATA,
)


class ScamDetectorService:
    """Orchestrates multi-stage defensive AI scam analysis pipeline."""

    async def analyze(
        self,
        raw_text: str,
        input_source: InputSource = InputSource.TEXT,
        language_override: Optional[str] = None,
        analysis_id: Optional[str] = None,
        community_reports: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Execute full end-to-end analysis on message conversation."""
        start_time = time.perf_counter()

        # Step 1: Text Cleaning & Preprocessing
        cleaned_text = text_preprocessor.clean_text(raw_text)

        # Step 2: Entity Extraction (URLs, UPI IDs, Crypto, Phones, Remote Tools)
        raw_entities = text_preprocessor.extract_entities(cleaned_text)
        entities_schema = ExtractedEntities(
            urls=raw_entities.get("urls", []),
            suspicious_shorteners=raw_entities.get("suspicious_shorteners", []),
            ip_urls=raw_entities.get("ip_urls", []),
            upi_ids=raw_entities.get("upi_ids", []),
            crypto_wallets=raw_entities.get("crypto_wallets", []),
            phone_numbers=raw_entities.get("phone_numbers", []),
            bank_accounts=raw_entities.get("bank_accounts", []),
            remote_access_tools=raw_entities.get("remote_access_tools", []),
        )

        # Step 3: Language Detection
        lang_code, lang_name, lang_conf = language_service.detect_language(
            cleaned_text, user_override=language_override
        )

        # Step 4: AI Scam Evaluation (LLM with resilient rule-based fallback)
        llm_result = await llm_service.analyze_message(
            text=cleaned_text,
            extracted_entities=raw_entities,
            language=lang_name,
        )

        # Map ScamCategory Enum safely
        raw_cat = llm_result.get("scam_category", "SAFE_NORMAL_CONVERSATION")
        try:
            category = ScamCategory(raw_cat)
        except ValueError:
            category = ScamCategory.SUSPICIOUS_UNKNOWN

        # Step 5: Process and normalize indicators
        raw_indicators = llm_result.get("indicators", [])
        indicator_models: List[IndicatorResponse] = []
        for raw_ind in raw_indicators:
            sev_str = str(raw_ind.get("severity", "MEDIUM")).upper()
            try:
                severity = IndicatorSeverity(sev_str)
            except ValueError:
                severity = IndicatorSeverity.MEDIUM

            conf = float(raw_ind.get("confidence", 0.85))
            indicator_models.append(
                IndicatorResponse(
                    title=raw_ind.get("title", "Suspicious Indicator"),
                    description=raw_ind.get("description", ""),
                    severity=severity,
                    confidence=min(1.0, max(0.0, conf)),
                    snippet=raw_ind.get("snippet") or raw_ind.get("evidence"),
                    evidence=raw_ind.get("evidence") or raw_ind.get("snippet"),
                    rule_id=raw_ind.get("rule_id"),
                )
            )

        # Step 5b: Identifiers the community has already reported (phone, UPI ID, website, email)
        if community_reports:
            top = max(community_reports, key=lambda r: r["report_count"])
            total = sum(r["report_count"] for r in community_reports)
            listed = ", ".join(f"{r['identifier']} ({r['report_count']})" for r in community_reports[:3])
            indicator_models.append(
                IndicatorResponse(
                    title="Reported by the ScamShield Community",
                    description=f"Other users have reported details in this message as used by scammers: {listed}. "
                                f"Reports are unverified, but {total} report(s) is a strong reason not to pay or reply.",
                    severity=IndicatorSeverity.HIGH if top["report_count"] >= COMMUNITY_STRONG_THRESHOLD else IndicatorSeverity.MEDIUM,
                    confidence=0.9 if top["report_count"] >= COMMUNITY_STRONG_THRESHOLD else 0.7,
                    snippet=top["identifier"],
                    evidence=top["identifier"],
                    rule_id="RULE_COMMUNITY_REPORTED",
                )
            )

        # Step 6: Risk Engine Calibration
        urgency_score = float(llm_result.get("urgency_score", 0.0))
        credential_risk = float(llm_result.get("credential_risk", 0.0))
        payment_vector_risk = float(llm_result.get("payment_vector_risk", 0.0))
        coercion_risk = float(llm_result.get("coercion_risk", 0.0))
        link_obfuscation_risk = float(llm_result.get("link_obfuscation_risk", 0.0))
        raw_ai_score = float(llm_result.get("risk_score", 0.0))

        risk_score, risk_level, risk_breakdown = risk_engine.compute_risk(
            urgency_score=urgency_score,
            credential_risk=credential_risk,
            payment_vector_risk=payment_vector_risk,
            coercion_risk=coercion_risk,
            link_obfuscation_risk=link_obfuscation_risk,
            indicators=indicator_models,
            ai_score=raw_ai_score,
            extracted_entities=raw_entities,
            scam_category=category,
        )

        # Community reports set a floor: 1-2 reports => at least SUSPICIOUS, 3+ => SCAM.
        if community_reports:
            top_count = max(r["report_count"] for r in community_reports)
            floor = 70.0 if top_count >= COMMUNITY_STRONG_THRESHOLD else 45.0
            if risk_score < floor:
                risk_score = floor
                risk_level = RiskLevel.HIGH if floor >= 60.0 else RiskLevel.MEDIUM

        is_scam = risk_score >= 30.0
        if not is_scam:
            category = ScamCategory.SAFE_NORMAL_CONVERSATION
            if risk_score < 20.0:
                risk_level = RiskLevel.SAFE
            else:
                risk_level = RiskLevel.LOW
        elif category == ScamCategory.SAFE_NORMAL_CONVERSATION:
            # Score crossed the scam threshold but no specific pattern matched:
            # never label a suspicious message as "safe".
            category = ScamCategory.SUSPICIOUS_UNKNOWN

        # Step 7: Explanation & Actionable Recommendations
        explanation = explanation_service.generate_explanation(
            category=category,
            is_scam=is_scam,
            indicators=indicator_models,
            detected_language=lang_code,
        )
        recommendations = recommendation_service.get_recommendations(
            category=category, is_scam=is_scam, detected_language=lang_code
        )
        helplines = recommendation_service.get_helplines(detected_language=lang_code)

        category_meta = SCAM_CATEGORY_METADATA.get(category, {})
        category_title = category_meta.get("title", category.value)
        category_desc = category_meta.get("description", "")
        golden_rule = category_meta.get("golden_rule", "")

        # Execution timing
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        provider_name = getattr(llm_service, "active_provider_name", "rule_based_fallback")
        analysis_mode = "fallback_rules" if "rule" in str(provider_name).lower() else "ai_plus_rules"

        return {
            "cleaned_text": cleaned_text,
            "raw_text": raw_text,
            "input_source": input_source,
            "detected_language": lang_code,
            "language_confidence": lang_conf,
            "scam_category": category,
            "category_title": category_title,
            "category_description": category_desc,
            "golden_rule": golden_rule,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "is_scam": is_scam,
            "ai_score": raw_ai_score,
            "rule_score": risk_score,
            "analysis_mode": analysis_mode,
            "risk_breakdown": risk_breakdown,
            "explanation": explanation,
            "recommendations": recommendations,
            "indicators": indicator_models,
            "extracted_entities": entities_schema,
            "helplines": helplines,
            "llm_provider_used": provider_name,
            "processing_time_ms": elapsed_ms,
        }


scam_detector = ScamDetectorService()
