"""Red-flag highlighter: locate the exact suspicious phrases in a message.

Returns non-overlapping character spans over the original text, each with a
short label and plain-language reason, so the UI can highlight them inline.
"""

import re
from typing import Dict, List, Pattern, Tuple

from app.services.link_xray import find_links, xray_link
from app.services.multilingual import native_matches
from app.services.llm_service import CREDENTIAL_ASK, PROTECTIVE_PHRASE, without_protective
from app.services.message_checks import (
    BANK_DETAILS_RE,
    COMMON_MISSPELLINGS,
    EMAIL_RE,
    GENERIC_GREETINGS,
    MONEY_REQUEST_RE,
    PHONE_RE,
)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _words(*phrases: str) -> Pattern:
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in phrases) + r")\b", re.IGNORECASE)


# (category, label, reason, severity, pattern)
PHRASE_RULES: List[Tuple[str, str, str, str, Pattern]] = [
    ("credentials", "Asks for secret codes",
     "No bank, company or official ever needs your OTP, PIN, CVV or password.", "high",
     re.compile(r"\b(?:otp|one[- ]time password|upi pin|m?pin|cvv|password|passcode|net\s?banking password)\b", re.I)),
    ("credentials", "Asks for bank or card details",
     "Genuine organisations never collect account or card details by message.", "high", BANK_DETAILS_RE),
    ("remote", "Remote-control app",
     "Screen-sharing apps let the sender control your phone and banking apps.", "high",
     _words("anydesk", "teamviewer", "rustdesk", "quicksupport", "ultraviewer", "airdroid", "screen share")),
    ("qr", "QR code 'to receive' money",
     "Scanning a QR code or entering a PIN only ever sends money out of your account.", "high",
     re.compile(r"\bscan\b[^.\n]{0,40}\bqr\b|\bqr code\b", re.I)),
    ("money", "Money request",
     "Asks you to pay or deposit money; confirm through a channel you already trust.", "medium", MONEY_REQUEST_RE),
    ("bait", "Too-good-to-be-true offer",
     "Unexpected prizes, gifts and guaranteed returns are the classic hook.", "medium",
     re.compile(r"\b(?:congratulations|you (?:have )?won|lottery|lucky draw|free gift|jackpot|cash prize|"
                r"guaranteed (?:profit|returns?)|double your money|\d+% (?:profit|return)s?)\b", re.I)),
    ("threat", "Threat or scare tactic",
     "Threats of blocking, arrest, fines or disconnection are used to stop you thinking.", "medium",
     re.compile(r"\b(?:(?:will be|has been|is) (?:blocked|suspended|deactivated|terminated|closed|disconnected)|"
                r"arrest(?:ed)?|legal action|warrant|penalty|fine of|disconnected tonight|power cut)\b", re.I)),
    ("urgency", "Pressure to act fast",
     "Artificial deadlines rush you before you can verify.", "medium",
     re.compile(r"\b(?:urgent(?:ly)?|immediately|right now|act now|hurry|last chance|final (?:notice|warning)|"
                r"today only|expires? today|within \d+\s*(?:minutes?|mins?|hours?|hrs?)|today itself)\b", re.I)),
    ("impersonation", "Claims official authority",
     "Scammers pose as banks, police or government; verify on the official app or website.", "low",
     _words("kyc", "rbi", "cbi", "police", "customs", "income tax", "cyber cell", "electricity board", "court")),
    ("greeting", "Generic greeting",
     "Real service messages usually use your name, not a mass-mail greeting.", "low",
     re.compile("|".join(re.escape(g) for g in GENERIC_GREETINGS), re.I)),
    ("typo", "Spelling mistake",
     "Official messages are proofread; typos are a common phishing tell.", "low",
     re.compile(r"\b(?:" + "|".join(re.escape(t) for t in COMMON_MISSPELLINGS) + r")\b", re.I)),
    ("contact", "Contact details to reach the sender",
     "Only use numbers and emails from the official website or your card, not from the message.", "low", EMAIL_RE),
    ("contact", "Contact details to reach the sender",
     "Only use numbers and emails from the official website or your card, not from the message.", "low", PHONE_RE),
]

CATEGORY_INFO = {}
for _category, _label, _reason, _severity, _ in PHRASE_RULES:
    CATEGORY_INFO.setdefault(_category, (_label, _reason, _severity))

LINK_RISK_TO_SEVERITY = {"danger": "high", "caution": "medium", "unknown": "low"}


def find_highlights(text: str) -> List[Dict]:
    """Return sorted, non-overlapping highlight spans for the suspicious parts of the text."""
    if not text:
        return []
    candidates: List[Dict] = []

    for start, end, link in find_links(text):
        report = xray_link(link)
        if report["risk"] == "safe":
            candidates.append({"start": start, "end": end, "category": "link", "severity": "safe",
                               "label": "Official link", "reason": f"Verified official domain of {report['official_brand']}."})
            continue
        worst = next((f for f in report["flags"] if f["severity"] == "high"), None) or (report["flags"] or [None])[0]
        candidates.append({
            "start": start, "end": end, "category": "link",
            "severity": LINK_RISK_TO_SEVERITY.get(report["risk"], "low"),
            "label": worst["title"] if worst else "Unverified link",
            "reason": worst["detail"] if worst else "Not a known official domain; open the organisation's app or website yourself instead.",
        })

    # Native-language scam words (Hindi, Hinglish, Tamil, Tanglish) use the same labels as their English rule.
    for span in native_matches(text):
        label, reason, severity = CATEGORY_INFO.get(span["category"], ("Warning sign", "", "low"))
        candidates.append({**span, "severity": severity, "label": label,
                           "reason": f"Means \"{span['meaning']}\". {reason}".strip()})

    # "Do not share your OTP" is a safety warning, not a request: don't flag secret-code words
    # inside such warnings, or anywhere if nothing in the message actually asks for them.
    protective = [(m.start(), m.end()) for m in PROTECTIVE_PHRASE.finditer(text)]
    asks_for_credentials = bool(CREDENTIAL_ASK.search(without_protective(text)))

    for category, label, reason, severity, pattern in PHRASE_RULES:
        for match in pattern.finditer(text):
            if category == "credentials" and (
                not asks_for_credentials or any(s <= match.start() < e for s, e in protective)
            ):
                continue
            if match.end() > match.start():
                candidates.append({"start": match.start(), "end": match.end(), "category": category,
                                   "severity": severity, "label": label, "reason": reason})

    # Keep the most severe (then longest) span wherever candidates overlap.
    rank = lambda c: (SEVERITY_RANK.get(c["severity"], 4 if c["severity"] == "safe" else 0), c["end"] - c["start"])
    chosen: List[Dict] = []
    for cand in sorted(candidates, key=rank, reverse=True):
        if all(cand["end"] <= c["start"] or cand["start"] >= c["end"] for c in chosen):
            chosen.append(cand)
    for c in chosen:
        c["text"] = text[c["start"]:c["end"]]
    return sorted(chosen, key=lambda c: c["start"])
