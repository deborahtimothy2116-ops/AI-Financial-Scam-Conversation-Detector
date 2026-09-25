"""Sender, link, request and writing-style checks for suspicious messages.

These complement the scam-pattern rules in the rule-based provider with the
generic phishing signals people look for by eye: a brand whose link or email
does not match its official domain, requests for money or bank details,
spelling mistakes, generic greetings and shouty formatting.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.utils.constants import IndicatorSeverity, ScamCategory

# Brand / authority keywords mapped to the domains they really send from.
OFFICIAL_DOMAINS: Dict[str, List[str]] = {
    "sbi": ["sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "sbicard.com"],
    "hdfc": ["hdfcbank.com", "hdfc.bank.in", "hdfc.com"],
    "icici": ["icicibank.com", "icici.bank.in"],
    "axis bank": ["axisbank.com", "axis.bank.in"],
    "kotak": ["kotak.com", "kotak.bank.in"],
    "paytm": ["paytm.com", "paytmbank.com"],
    "phonepe": ["phonepe.com"],
    "google pay": ["google.com", "pay.google.com"],
    "gpay": ["google.com", "pay.google.com"],
    "amazon": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
    "netflix": ["netflix.com"],
    "paypal": ["paypal.com"],
    "apple": ["apple.com", "icloud.com"],
    "microsoft": ["microsoft.com", "outlook.com", "live.com"],
    "whatsapp": ["whatsapp.com"],
    "irctc": ["irctc.co.in"],
    "income tax": ["incometax.gov.in"],
    "uidai": ["uidai.gov.in"],
    "aadhaar": ["uidai.gov.in"],
    "epfo": ["epfindia.gov.in"],
    "india post": ["indiapost.gov.in"],
    "rbi": ["rbi.org.in"],
    "npci": ["npci.org.in"],
    "fedex": ["fedex.com"],
    "dhl": ["dhl.com"],
    "electricity board": ["gov.in", "nic.in"],
    "tneb": ["tnebltd.gov.in", "tangedco.gov.in"],
}

# Link shorteners hide the destination; they are flagged as such, not as impersonation.
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "v.gd", "rb.gy",
    "shorturl.at", "goo.gl", "tiny.cc", "ow.ly", "buff.ly", "s.id", "t.ly",
    "rebrand.ly", "shorte.st", "bl.ink", "lnkd.in", "wa.link",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
    "rediffmail.com", "protonmail.com", "proton.me", "aol.com", "mail.com",
    "ymail.com", "zoho.com",
}

# Common misspellings seen in phishing messages (typo -> correct word).
COMMON_MISSPELLINGS: Dict[str, str] = {
    "acount": "account", "accout": "account", "acc0unt": "account",
    "verfy": "verify", "verifiy": "verify", "verificaton": "verification",
    "verifcation": "verification", "suspened": "suspended",
    "suspendd": "suspended", "immediatly": "immediately",
    "imediately": "immediately", "immediatelly": "immediately",
    "recieve": "receive", "recieved": "received", "benificiary": "beneficiary",
    "congradulations": "congratulations", "congratulation you": "congratulations",
    "custmer": "customer", "costumer": "customer", "pasword": "password",
    "passwrd": "password", "securty": "security", "secuirty": "security",
    "updte": "update", "adress": "address", "bussiness": "business",
    "transction": "transaction", "tranfer": "transfer", "debitted": "debited",
    "creditted": "credited", "blockd": "blocked", "expird": "expired",
    "informations": "information", "kindly revert back": "kindly reply",
}

GENERIC_GREETINGS = [
    "dear customer", "dear user", "dear valued customer", "dear account holder",
    "dear sir/madam", "dear sir / madam", "dear beneficiary", "dear winner",
    "dear card holder", "dear cardholder", "dear client",
]

# Acronyms that are normal in upper case and should not count as shouting.
COMMON_ACRONYMS = {
    "KYC", "OTP", "UPI", "SBI", "PAN", "ATM", "RBI", "CVV", "PIN", "SMS",
    "URL", "HDFC", "ICICI", "NEFT", "IMPS", "RTGS", "IFSC", "EMI", "GST",
    "USD", "INR", "CEO", "HR", "OK", "FAQ", "APP", "NPCI", "EPFO", "IRCTC",
}

_DOMAIN_TLDS = (
    "com|in|net|org|co|info|xyz|top|online|site|club|live|link|app|io|me|biz|gov|"
    "bank|shop|ru|cn|tk|ml|ga|cf|gq|ly|gl|cc|ws|us|uk|pw|vip|icu|buzz|click|work|sbi"
)
DOMAIN_RE = re.compile(
    r"(?<![@\w.-])(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+(?:" + _DOMAIN_TLDS + r"))\b(?:/\S*)?",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[a-z0-9._%+-]+@((?:[a-z0-9-]+\.)+[a-z]{2,})\b", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:\+91[\s-]?|(?<!\d)0)?(?<!\d)[6-9]\d{4}[\s-]?\d{5}(?!\d)"  # Indian mobile: 98765 43210, +91-98765-43210
    r"|(?:\+?\d{1,3}[-\s]?)?\b\d{3,5}[-\s]?\d{3,4}[-\s]?\d{3,4}\b"  # other grouped / landline formats
)
BANK_DETAILS_RE = re.compile(
    r"\b(?:share|send|provide|give|enter|update|confirm|submit|fill|reply with)\b.{0,40}?"
    r"\b(?:bank details|account number|account details|a/c (?:no|number)|card number|card details|"
    r"debit card|credit card|net\s?banking|login details|login credentials|ifsc|expiry date)\b",
    re.IGNORECASE,
)
MONEY_REQUEST_RE = re.compile(
    r"(?<!fixed )\b(?:pay|send|transfer|deposit|remit)\b(?!\s+(?:of|has|was|is|made|received)\b).{0,30}?(?:₹|rs\.?\s?|inr\s?|\$|usd\s?)\s?\d[\d,]*"
    r"|(?:₹|rs\.?\s?|inr\s?|\$)\s?\d[\d,]*.{0,25}?\b(?:fee|charge|charges|deposit|advance|penalty|fine)\b",
    re.IGNORECASE,
)
CALL_TO_CONTACT_RE = re.compile(r"\b(?:call|whatsapp|contact|dial|sms|text|reach)\b", re.IGNORECASE)

_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a"})


@dataclass
class MessageCheckResult:
    indicators: List[Dict] = field(default_factory=list)
    credential_risk: float = 0.0
    payment_vector_risk: float = 0.0
    link_obfuscation_risk: float = 0.0
    coercion_risk: float = 0.0
    category_hint: Optional[ScamCategory] = None

    def add(self, title, description, severity, confidence, snippet, rule_id):
        self.indicators.append({
            "title": title,
            "description": description,
            "severity": severity.value,
            "confidence": confidence,
            "snippet": snippet,
            "rule_id": rule_id,
        })

    def hint(self, category: ScamCategory):
        if self.category_hint is None:
            self.category_hint = category


def _is_official(domain: str, official: List[str]) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in official)


def _claimed_brands(lowered: str) -> List[str]:
    return [b for b in OFFICIAL_DOMAINS if re.search(r"\b" + re.escape(b) + r"\b", lowered)]


def _extract_domains(text: str) -> List[str]:
    domains = []
    for match in DOMAIN_RE.finditer(text):
        host = match.group(1).lower().strip(".")
        if match.group(0).lower().startswith("http"):
            host = (urlparse(match.group(0)).hostname or host).lower()
        if host.startswith("www."):
            host = host[4:]
        if host not in domains:
            domains.append(host)
    return domains


def _find_domain_mismatch(domains: List[str], brands: List[str]):
    """Return (domain, brand, official_domains, claimed) for the first domain that
    names or imitates a brand without belonging to it, else None."""
    for domain in domains:
        if domain in FREE_EMAIL_DOMAINS or domain in SHORTENERS:
            continue
        normalized = domain.translate(_LEET).replace("-", "")
        for brand, official in OFFICIAL_DOMAINS.items():
            if _is_official(domain, official):
                continue
            claimed = brand in brands
            brand_token = brand.replace(" ", "")
            lookalike = len(brand_token) >= 3 and brand_token in normalized
            if claimed or lookalike:
                return domain, brand, official, claimed
    return None


def run_message_checks(text: str) -> MessageCheckResult:
    """Inspect a message for sender, link, request and writing-style red flags."""
    result = MessageCheckResult()
    lowered = text.lower()
    brands = _claimed_brands(lowered)
    email_domains = [d.lower() for d in EMAIL_RE.findall(text)]
    link_domains = _extract_domains(text)

    # 1. Claimed sender vs the links / email addresses actually used
    mismatch = _find_domain_mismatch(link_domains + email_domains, brands)
    if mismatch:
        domain, brand, official, claimed = mismatch
        result.add(
            "Sender / Link Mismatch (Possible Impersonation)",
            f"The message {'claims to be from' if claimed else 'imitates'} {brand.upper()}, "
            f"but points to '{domain}', which is not an official {brand.upper()} domain "
            f"({', '.join(official[:2])}). Fraudsters register lookalike domains to steal logins and money.",
            IndicatorSeverity.HIGH, 0.9, domain, "RULE_SENDER_DOMAIN_MISMATCH",
        )
        result.link_obfuscation_risk = max(result.link_obfuscation_risk, 90.0)
        result.credential_risk = max(result.credential_risk, 75.0)
        result.hint(ScamCategory.PHISHING_CREDENTIAL_HARVESTING)

    # 2. Official-sounding sender using a free email account
    free_senders = [d for d in email_domains if d in FREE_EMAIL_DOMAINS]
    if free_senders and brands:
        result.add(
            "Organisation Using a Free Email Address",
            f"The message presents itself as {brands[0].upper()} but uses a free email account "
            f"(@{free_senders[0]}). Banks, companies and government offices send from their own domains.",
            IndicatorSeverity.HIGH, 0.88, "@" + free_senders[0], "RULE_FREE_EMAIL_SENDER",
        )
        result.coercion_risk = max(result.coercion_risk, 60.0)
        result.hint(ScamCategory.URGENT_IMPERSONATION)

    # 3. Unverified phone number to call back, attached to a brand or authority claim
    phones = PHONE_RE.findall(text)
    if phones and brands and CALL_TO_CONTACT_RE.search(text):
        result.add(
            "Unverified Contact Number",
            "Asks you to call or message a number given in the message itself. Always use the number "
            "printed on your card or the official website instead.",
            IndicatorSeverity.MEDIUM, 0.75, phones[0].strip(), "RULE_UNVERIFIED_CONTACT_NUMBER",
        )
        result.hint(ScamCategory.URGENT_IMPERSONATION)

    # 4. Requests for bank / card details
    bank_match = BANK_DETAILS_RE.search(text)
    if bank_match:
        result.add(
            "Request for Banking or Card Details",
            "Asks you to share or 'update' bank account, card or net-banking details. Legitimate "
            "organisations never collect these over SMS, chat or email.",
            IndicatorSeverity.HIGH, 0.92, bank_match.group(0)[:80], "RULE_BANK_DETAILS_REQUEST",
        )
        result.credential_risk = max(result.credential_risk, 90.0)
        result.hint(ScamCategory.PHISHING_CREDENTIAL_HARVESTING)

    # 5. Requests for money
    money_match = MONEY_REQUEST_RE.search(text)
    if money_match:
        result.add(
            "Request for Money",
            "The message asks you to pay, transfer or deposit money. Confirm who is asking through a "
            "channel you already trust before sending anything.",
            IndicatorSeverity.MEDIUM, 0.8, money_match.group(0)[:80], "RULE_MONEY_REQUEST",
        )
        result.payment_vector_risk = max(result.payment_vector_risk, 60.0)
        result.hint(ScamCategory.SUSPICIOUS_UNKNOWN)

    # 6. Spelling mistakes typical of phishing
    typos = [t for t in COMMON_MISSPELLINGS if re.search(r"\b" + re.escape(t) + r"\b", lowered)]
    if typos:
        fixes = ", ".join(f"'{t}' ({COMMON_MISSPELLINGS[t]})" for t in typos[:3])
        result.add(
            "Spelling / Grammar Mistakes",
            f"Contains misspellings such as {fixes}. Official messages are proofread; errors are a "
            "common sign of phishing.",
            IndicatorSeverity.MEDIUM if len(typos) >= 2 else IndicatorSeverity.LOW,
            0.7, ", ".join(typos[:3]), "RULE_SPELLING_MISTAKES",
        )

    # 7. Generic greeting instead of your name
    greeting = next((g for g in GENERIC_GREETINGS if g in lowered), None)
    if greeting:
        result.add(
            "Generic Greeting",
            f"Opens with '{greeting.title()}' instead of your name. Mass phishing messages address "
            "everyone the same way.",
            IndicatorSeverity.LOW, 0.6, greeting, "RULE_GENERIC_GREETING",
        )

    # 8. Unusual formatting: shouting in capitals or piled-up punctuation
    words = re.findall(r"\b[A-Za-z]{3,}\b", text)
    caps = [w for w in words if w.isupper() and w not in COMMON_ACRONYMS]
    heavy_punctuation = re.search(r"[!?]{2,}", text) or text.count("!") >= 3
    if (len(caps) >= 4 and len(caps) / max(len(words), 1) >= 0.3) or heavy_punctuation:
        snippet = " ".join(caps[:4]) if caps else re.search(r"[!?]{2,}|!", text).group(0)
        result.add(
            "Unusual Formatting",
            "Uses excessive capital letters or exclamation marks to create alarm or excitement, a "
            "style legitimate organisations avoid.",
            IndicatorSeverity.LOW, 0.6, snippet, "RULE_UNUSUAL_FORMATTING",
        )

    return result
