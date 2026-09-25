"""Risk Engine for Multi-Factor Threat Evaluation and Calibration."""

from typing import Any, Dict, List, Optional, Tuple, Union
from app.schemas.analysis import IndicatorResponse, RiskBreakdown
from app.utils.constants import RiskLevel, IndicatorSeverity, ScamCategory


class RiskEngine:
    """Calculates weighted risk scores combining AI score, rule score, indicator severity, and entities."""

    # Configurable scoring weights
    WEIGHTS = {
        "rule_weight": 0.40,
        "ai_weight": 0.40,
        "indicator_severity_weight": 0.20,
        "credential_risk": 0.30,
        "payment_vector_risk": 0.25,
        "coercion_risk": 0.20,
        "urgency_score": 0.15,
        "link_obfuscation_risk": 0.10,
    }

    def compute_risk(
        self,
        urgency_score: float = 0.0,
        credential_risk: float = 0.0,
        payment_vector_risk: float = 0.0,
        coercion_risk: float = 0.0,
        link_obfuscation_risk: float = 0.0,
        indicators: Optional[List[IndicatorResponse]] = None,
        ai_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        extracted_entities: Optional[Dict[str, Any]] = None,
        scam_category: Optional[Union[ScamCategory, str]] = None,
    ) -> Tuple[float, RiskLevel, RiskBreakdown]:
        """Compute calibrated composite risk score, risk level, and structured breakdown."""
        indicators = indicators or []
        urgency = min(100.0, max(0.0, float(urgency_score)))
        cred = min(100.0, max(0.0, float(credential_risk)))
        pay = min(100.0, max(0.0, float(payment_vector_risk)))
        coercion = min(100.0, max(0.0, float(coercion_risk)))
        link = min(100.0, max(0.0, float(link_obfuscation_risk)))

        # Subscore weighted combination
        dim_score = (
            (cred * self.WEIGHTS["credential_risk"])
            + (pay * self.WEIGHTS["payment_vector_risk"])
            + (coercion * self.WEIGHTS["coercion_risk"])
            + (urgency * self.WEIGHTS["urgency_score"])
            + (link * self.WEIGHTS["link_obfuscation_risk"])
        )

        # Count indicators by severity
        critical_count = sum(
            1 for i in indicators
            if (i.severity == IndicatorSeverity.CRITICAL or str(i.severity).upper() == "CRITICAL")
        )
        high_count = sum(
            1 for i in indicators
            if (i.severity == IndicatorSeverity.HIGH or str(i.severity).upper() == "HIGH")
        )
        med_count = sum(
            1 for i in indicators
            if (i.severity == IndicatorSeverity.MEDIUM or str(i.severity).upper() == "MEDIUM")
        )

        # Entity boost
        entity_boost = 0.0
        if extracted_entities:
            if extracted_entities.get("upi_ids") or extracted_entities.get("ip_urls"):
                entity_boost += 10.0
            if extracted_entities.get("suspicious_shorteners"):
                entity_boost += 8.0
            if extracted_entities.get("remote_access_tools"):
                entity_boost += 15.0

        # Heuristic rule score
        computed_rule_score = dim_score + entity_boost
        if critical_count >= 1:
            computed_rule_score = max(computed_rule_score, 88.0 + min(12.0, critical_count * 4.0))
        elif high_count >= 2:
            computed_rule_score = max(computed_rule_score, 75.0 + min(15.0, high_count * 5.0))
        elif high_count == 1:
            computed_rule_score = max(computed_rule_score, 65.0)
        elif med_count >= 2:
            computed_rule_score = max(computed_rule_score, 45.0)

        eff_rule_score = rule_score if rule_score is not None else computed_rule_score
        eff_ai_score = ai_score if ai_score is not None else computed_rule_score

        # Weighted blend between rule, AI, and severity
        severity_score = (critical_count * 40.0) + (high_count * 25.0) + (med_count * 10.0)
        severity_score = min(100.0, severity_score)

        final_score = (
            (eff_rule_score * self.WEIGHTS["rule_weight"])
            + (eff_ai_score * self.WEIGHTS["ai_weight"])
            + (severity_score * self.WEIGHTS["indicator_severity_weight"])
        )

        # Overriding floors for critical signals
        if critical_count >= 1:
            final_score = max(final_score, 88.0 + min(12.0, critical_count * 4.0))
        elif high_count >= 2:
            final_score = max(final_score, 75.0 + min(15.0, high_count * 5.0))
        elif high_count == 1:
            final_score = max(final_score, 65.0)
        elif med_count >= 2:
            final_score = max(final_score, 45.0)

        # Cap at 100.0 and round
        final_score = round(min(100.0, max(0.0, final_score)), 1)

        # Risk level classification:
        if final_score >= 80.0:
            level = RiskLevel.CRITICAL
        elif final_score >= 60.0:
            level = RiskLevel.HIGH
        elif final_score >= 30.0:
            level = RiskLevel.MEDIUM
        elif final_score >= 20.0:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.SAFE

        breakdown = RiskBreakdown(
            urgency_score=round(urgency, 1),
            credential_risk=round(cred, 1),
            payment_vector_risk=round(pay, 1),
            coercion_risk=round(coercion, 1),
            link_obfuscation_risk=round(link, 1),
        )

        return final_score, level, breakdown


risk_engine = RiskEngine()
