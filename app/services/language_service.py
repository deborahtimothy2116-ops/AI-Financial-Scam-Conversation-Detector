"""Language Detection Service with Multi-lingual and Romanized Script Support."""

import re
from typing import Optional, Tuple
from app.core.logging import logger

try:
    import langdetect
    from langdetect import DetectorFactory
    DetectorFactory.seed = 42
except ImportError:
    langdetect = None


LANGUAGE_NAME_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "ur": "Urdu",
    "ar": "Arabic",
    "zh-cn": "Chinese (Simplified)",
    "ja": "Japanese",
    "ru": "Russian",
    "hinglish": "Hinglish (Hindi in Roman script)",
    "tanglish": "Tanglish (Tamil in Roman script)",
}

# Hinglish keyword markers to detect Romanized Hindi chat
HINGLISH_MARKERS = {
    "karo", "kijiye", "bhejo", "paise", "rupaye", "aayega", "milega", "karenge",
    "hoga", "nahin", "nahi", "aapka", "tumhara", "khata", "sampark", "turant",
    "jaldi", "dhokha", "inam", "lottery", "dijiye", "khate", "kare", "karna"
}

# Tanglish keyword markers
TANGLISH_MARKERS = {
    "unga", "ungal", "panam", "anupavum", "anuppunga", "kadan", "vetri", "parisu",
    "mudakkappadum", "mudiyum", "udanadi", "seiyavum", "kannakku", "vangi"
}


class LanguageService:
    """Detects and validates message languages."""

    def detect_language(self, text: str, user_override: Optional[str] = None) -> Tuple[str, str, float]:
        """Detect language of the text or validate user override.
        
        Returns:
            Tuple of (iso_code, display_name, confidence_0_to_1)
        """
        # If user explicitly supplied a language override (and not 'auto')
        if user_override and user_override.strip() and user_override.strip().lower() != "auto":
            code = user_override.strip().lower()
            name = LANGUAGE_NAME_MAP.get(code, code.upper())
            return code, name, 1.0

        cleaned = text.strip()
        if not cleaned:
            return "en", "English", 1.0

        # Check for native Tamil Unicode characters (\u0B80 - \u0BFF)
        tamil_chars = re.findall(r"[\u0B80-\u0BFF]", cleaned)
        if len(tamil_chars) >= 2:
            return "ta", "Tamil", 0.99

        # Check for Hinglish / Tanglish
        words = set(re.findall(r"\b[a-zA-Z]{3,}\b", cleaned.lower()))
        tanglish_matches = words.intersection(TANGLISH_MARKERS)
        if len(tanglish_matches) >= 2:
            return "ta", "Tamil (Tanglish)", 0.92

        hinglish_matches = words.intersection(HINGLISH_MARKERS)
        if len(hinglish_matches) >= 2:
            return "hinglish", "Hinglish (Hindi in Roman script)", 0.88

        # Use langdetect if available
        if langdetect is not None:
            try:
                langs = langdetect.detect_langs(cleaned)
                if langs:
                    top_lang = langs[0]
                    code = top_lang.lang
                    confidence = round(top_lang.prob, 2)
                    name = LANGUAGE_NAME_MAP.get(code, code.upper())
                    return code, name, confidence
            except Exception as e:
                logger.debug(f"Langdetect error: {e}, falling back to English default.")

        # Default fallback
        return "en", "English", 0.95


language_service = LanguageService()
