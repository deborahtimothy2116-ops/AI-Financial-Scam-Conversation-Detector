"""Explanation Service for Plain-Language Risk and Deception Tactics Breakdown."""

from typing import List
from app.schemas.analysis import IndicatorResponse
from app.utils.constants import ScamCategory, SCAM_CATEGORY_METADATA


class ExplanationService:
    """Generates accessible, jargon-free explanations of detected scam mechanics in English & Tamil."""

    def generate_explanation(
        self,
        category: ScamCategory,
        is_scam: bool,
        indicators: List[IndicatorResponse],
        detected_language: str = "en",
    ) -> str:
        """Construct user-friendly explanation tailored to the category, indicators, and language."""
        is_tamil = detected_language in ["ta", "tamil"]

        if not is_scam or category == ScamCategory.SAFE_NORMAL_CONVERSATION:
            if is_tamil:
                return (
                    "✅ பெரிய நிதி மோசடி குறிகாட்டிகள் எதுவும் கண்டறியப்படவில்லை. "
                    "இந்த உரையாடல் வழக்கமானதாக தெரிகிறது. எனினும் எவரிடமும் உங்கள் OTP, PIN அல்லது கடவுச்சொல்லை பகிர வேண்டாம்."
                )
            return (
                "✅ No major scam indicators detected. "
                "The conversation appears normal. However, always exercise caution and never share OTPs, PINs, or private banking passwords in any digital chat."
            )

        category_meta = SCAM_CATEGORY_METADATA.get(category, {})
        category_title = category_meta.get("title", category.value)

        reasons: List[str] = []
        for ind in indicators[:3]:  # Top 3 indicators
            reasons.append(f"• {ind.title}: {ind.description or ind.evidence or ind.snippet}")

        if is_tamil:
            explanation_lines = [
                f"⚠️ எச்சரிக்கை: இந்த செய்தி '{category_title}' நிதி மோசடி வடிவங்களை கொண்டுள்ளது.",
                "",
                "எச்சரிக்கையாக இருக்க வேண்டிய காரணங்கள்:",
            ]
            explanation_lines.extend(reasons)
            if category_meta.get("golden_rule"):
                explanation_lines.append("")
                explanation_lines.append(f"💡 முக்கிய பாதுகாப்பு விதி: {category_meta['golden_rule']}")
            return "\n".join(explanation_lines)

        explanation_lines = [
            f"⚠️ HIGH RISK ALERT: This message matches known patterns of {category_title}.",
            "",
            "Why this is suspicious:",
        ]
        explanation_lines.extend(reasons)

        if category_meta.get("golden_rule"):
            explanation_lines.append("")
            explanation_lines.append(f"💡 Key Safety Principle: {category_meta['golden_rule']}")

        return "\n".join(explanation_lines)


explanation_service = ExplanationService()
