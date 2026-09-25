"""Multilingual scam vocabulary: Hindi (Devanagari), Hinglish, Tamil and Tanglish.

Scam rules are written against English cue words. Many Indian scam messages are
written fully in Hindi or Tamil (or in Roman-script Hinglish / Tanglish), so this
module finds the native cue words and returns their English equivalents. The
detector appends those equivalents to the text it matches rules against, and the
highlighter uses the same table to mark the native words in the message.
"""

import re
from typing import Dict, List, Tuple

# (native phrase, English cue words, highlight category, reason)
KEYWORDS: List[Tuple[str, str, str]] = [
    # --- Hindi (Devanagari) ---
    ("खाता बंद", "account will be blocked", "threat"),
    ("खाता ब्लॉक", "account will be blocked", "threat"),
    ("बंद हो जाएगा", "will be blocked", "threat"),
    ("ब्लॉक हो जाएगा", "will be blocked", "threat"),
    ("केवाईसी", "kyc update", "impersonation"),
    ("ओटीपी बताएं", "share otp", "credentials"),
    ("ओटीपी बताइए", "share otp", "credentials"),
    ("ओटीपी बताओ", "share otp", "credentials"),
    ("ओटीपी भेजें", "share otp", "credentials"),
    ("ओटीपी शेयर", "share otp", "credentials"),
    ("ओटीपी", "otp", "credentials"),
    ("पिन", "pin", "credentials"),
    ("पासवर्ड", "password", "credentials"),
    ("तुरंत", "immediately", "urgency"),
    ("जल्दी", "urgent", "urgency"),
    ("आज ही", "today only", "urgency"),
    ("पैसे भेजें", "send rs 1", "money"),
    ("पैसे भेजो", "send rs 1", "money"),
    ("भुगतान करें", "pay rs 1", "money"),
    ("शुल्क", "processing fee", "money"),
    ("इनाम", "won prize claim", "bait"),
    ("लॉटरी", "lottery won prize", "bait"),
    ("बधाई हो", "congratulations", "bait"),
    ("गिरफ्तार", "arrest warrant", "threat"),
    ("गिरफ़्तार", "arrest warrant", "threat"),
    ("पुलिस", "police", "impersonation"),
    ("सीबीआई", "cbi", "impersonation"),
    ("डिजिटल अरेस्ट", "digital arrest", "threat"),
    ("किसी को मत बताना", "do not tell anyone", "threat"),
    ("बिजली कट", "power cut disconnected tonight", "threat"),
    ("क्यूआर कोड स्कैन", "scan qr code to receive", "qr"),
    # --- Hinglish (Roman script) ---
    ("khata band", "account will be blocked", "threat"),
    ("account band", "account will be blocked", "threat"),
    ("band ho jayega", "will be blocked", "threat"),
    ("block ho jayega", "will be blocked", "threat"),
    ("otp batao", "share otp", "credentials"),
    ("otp bhejo", "share otp", "credentials"),
    ("otp bataiye", "share otp", "credentials"),
    ("pin batao", "share pin", "credentials"),
    ("turant", "immediately", "urgency"),
    ("jaldi karo", "urgent", "urgency"),
    ("paise bhejo", "send rs 1", "money"),
    ("paisa bhejo", "send rs 1", "money"),
    ("paise bhejiye", "send rs 1", "money"),
    ("payment karo", "pay rs 1", "money"),
    ("inaam", "won prize claim", "bait"),
    ("inam jeeta", "won prize claim", "bait"),
    ("lottery lagi", "won lottery prize", "bait"),
    ("giraftar", "arrest warrant", "threat"),
    ("kisi ko mat batana", "do not tell anyone", "threat"),
    ("qr scan karo", "scan qr code to receive", "qr"),
    # --- Tamil ---
    ("முடக்கப்படும்", "will be blocked", "threat"),
    ("முடக்கப்படும", "will be blocked", "threat"),
    ("கணக்கு", "account", "impersonation"),
    ("வங்கி", "bank", "impersonation"),
    ("உடனே", "immediately", "urgency"),
    ("உடனடியாக", "immediately", "urgency"),
    ("அனுப்பவும்", "send rs 1", "money"),
    ("அனுப்புங்கள்", "send rs 1", "money"),
    ("கட்டணம்", "processing fee", "money"),
    ("ஓடிபி", "otp", "credentials"),
    ("பரிசு", "won prize claim", "bait"),
    ("லாட்டரி", "lottery won prize", "bait"),
    ("கைது", "arrest warrant", "threat"),
    ("காவல்துறை", "police", "impersonation"),
    ("போலீஸ்", "police", "impersonation"),
    # --- Tanglish (Roman script) ---
    ("mudakkappadum", "will be blocked", "threat"),
    ("udane", "immediately", "urgency"),
    ("udanadi", "immediately", "urgency"),
    ("anuppunga", "send rs 1", "money"),
    ("anupavum", "send rs 1", "money"),
    ("parisu", "won prize claim", "bait"),
    ("otp sollunga", "share otp", "credentials"),
]

_LATIN = re.compile(r"^[a-z ]+$")


def _pattern(phrase: str) -> re.Pattern:
    # Word boundaries only make sense for Latin script; Indic scripts use combining marks.
    if _LATIN.match(phrase):
        return re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
    return re.compile(re.escape(phrase))


COMPILED = [(phrase, english, category, _pattern(phrase)) for phrase, english, category in KEYWORDS]


def english_cues(text: str) -> str:
    """English cue words for every native scam phrase found in the text."""
    cues = [english for _, english, _, pattern in COMPILED if pattern.search(text or "")]
    return " ".join(dict.fromkeys(cues))


def native_matches(text: str) -> List[Dict]:
    """Spans of native scam phrases, for the highlighter."""
    spans = []
    for phrase, english, category, pattern in COMPILED:
        for m in pattern.finditer(text or ""):
            spans.append({"start": m.start(), "end": m.end(), "category": category, "meaning": english})
    return spans
