"""Constants, Enums, and Pattern Definitions for Scam Detection."""

from enum import Enum
import re
from typing import Dict, List, Any


class ScamCategory(str, Enum):
    UPI_QR_SCAM = "UPI_QR_SCAM"
    LOTTERY_PRIZE_SCAM = "LOTTERY_PRIZE_SCAM"
    URGENT_IMPERSONATION = "URGENT_IMPERSONATION"
    INVESTMENT_CRYPTO_PONZI = "INVESTMENT_CRYPTO_PONZI"
    JOB_OFFER_TASK_FRAUD = "JOB_OFFER_TASK_FRAUD"
    PHISHING_CREDENTIAL_HARVESTING = "PHISHING_CREDENTIAL_HARVESTING"
    REFUND_OVERPAYMENT_SCAM = "REFUND_OVERPAYMENT_SCAM"
    OTP_REMOTE_ACCESS_SCAM = "OTP_REMOTE_ACCESS_SCAM"
    LOAN_APP_EXTORTION = "LOAN_APP_EXTORTION"
    MARKETPLACE_ADVANCE_FEE = "MARKETPLACE_ADVANCE_FEE"
    ROMANCE_PIG_BUTCHERING = "ROMANCE_PIG_BUTCHERING"
    SUSPICIOUS_UNKNOWN = "SUSPICIOUS_UNKNOWN"
    SAFE_NORMAL_CONVERSATION = "SAFE_NORMAL_CONVERSATION"


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IndicatorSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InputSource(str, Enum):
    TEXT = "TEXT"
    IMAGE_OCR = "IMAGE_OCR"


SCAM_CATEGORY_METADATA: Dict[ScamCategory, Dict[str, Any]] = {
    ScamCategory.UPI_QR_SCAM: {
        "title": "UPI / QR Code Payment Trap",
        "description": "The scammer sends a QR code or payment request claiming you will 'receive' money, but scanning it or entering your UPI PIN actually transfers money OUT of your bank account.",
        "common_victims": "Online marketplace sellers, OLX users, reward claimants",
        "golden_rule": "You NEVER need to enter a UPI PIN or scan a QR code to RECEIVE money.",
    },
    ScamCategory.LOTTERY_PRIZE_SCAM: {
        "title": "Fake Lottery / Lucky Draw Scam",
        "description": "Claims you won a massive lottery, iPhone, car, or cash prize from a contest you never entered, demanding an upfront 'processing fee', 'customs clearance', or 'GST' to claim it.",
        "common_victims": "General public, WhatsApp users, SMS recipients",
        "golden_rule": "Legitimate lotteries never ask you to pay taxes or fees in advance to receive prize money.",
    },
    ScamCategory.URGENT_IMPERSONATION: {
        "title": "Urgent Impersonation & Coercion Scam",
        "description": "The scammer pretends to be an official authority (Police, CBI, Customs, Electricity Board, Bank Manager, or a distressed family member) threatening immediate arrest or power cutoff unless money is paid now.",
        "common_victims": "Elderly, home owners, working professionals",
        "golden_rule": "Government agencies and utility providers never demand instant UPI/wire transfers or gift cards over chat.",
    },
    ScamCategory.INVESTMENT_CRYPTO_PONZI: {
        "title": "Crypto / High-Yield Investment Fraud",
        "description": "Promises unrealistic, guaranteed returns (e.g., 'Double your money in 24 hours', 'Daily 10% profit') using fake trading dashboards, Telegram bot signals, or crypto liquidity pools.",
        "common_victims": "Investors, young professionals, crypto enthusiasts",
        "golden_rule": "Guaranteed high returns with zero risk do not exist. Any scheme promising doubling money quickly is 100% fraud.",
    },
    ScamCategory.JOB_OFFER_TASK_FRAUD: {
        "title": "Work From Home / Task-Based Fraud",
        "description": "Offers easy part-time work like 'like YouTube videos', 'rate hotels', or 'write reviews' for high daily pay, then traps the victim into paying 'prepaid security deposits' to unlock higher tasks.",
        "common_victims": "Job seekers, students, homemakers",
        "golden_rule": "Legitimate employers never ask you to pay money to work or complete tasks.",
    },
    ScamCategory.PHISHING_CREDENTIAL_HARVESTING: {
        "title": "Phishing & KYC Expiry Trap",
        "description": "Sends deceptive links warning that your bank account, PAN card, Aadhaar, SIM card, or Netbanking will be blocked unless you immediately click a link and verify your credentials.",
        "common_victims": "Bank account holders, telecom subscribers",
        "golden_rule": "Banks NEVER send links in SMS/WhatsApp asking for Netbanking passwords, PINs, or full card details.",
    },
    ScamCategory.REFUND_OVERPAYMENT_SCAM: {
        "title": "Accidental Overpayment / Fake Refund Trap",
        "description": "The scammer claims they accidentally transferred excess funds to your account (often showing a fake SMS confirmation) and pressures you to quickly send back the difference.",
        "common_victims": "Small business owners, freelance service providers, sellers",
        "golden_rule": "Always check your official bank mobile app / statement directly—never trust SMS screenshots or third-party confirmations.",
    },
    ScamCategory.OTP_REMOTE_ACCESS_SCAM: {
        "title": "OTP Theft & Remote Device Takeover",
        "description": "Tricks the user into sharing an SMS OTP or installing remote screen-sharing tools (AnyDesk, TeamViewer, RustDesk, QuickSupport) to drain bank accounts and wallets.",
        "common_victims": "People seeking tech support, refund helpline callers",
        "golden_rule": "Never share OTPs with anyone, and NEVER install remote access apps at the request of a stranger.",
    },
    ScamCategory.LOAN_APP_EXTORTION: {
        "title": "Predatory Loan App & Blackmail Scam",
        "description": "Offers instant no-documentation loans, then demands extortionate processing fees or uses contact permissions to harass and blackmail contacts.",
        "common_victims": "People in urgent financial need",
        "golden_rule": "Only borrow from RBI/government-registered banks and NBFCs through official verified apps.",
    },
    ScamCategory.MARKETPLACE_ADVANCE_FEE: {
        "title": "Classifieds / Marketplace Advance Fee Scam",
        "description": "Buyer or seller on OLX/Facebook Marketplace refuses in-person meeting and asks for an advance courier/delivery/booking token fee before disappearing.",
        "common_victims": "Second-hand buyers and sellers",
        "golden_rule": "Never pay advance booking amounts to unverified remote sellers. Insist on cash-on-delivery or verified escrow.",
    },
    ScamCategory.ROMANCE_PIG_BUTCHERING: {
        "title": "Romance / Pig Butchering Scam",
        "description": "Scammer builds long-term romantic or friendly rapport on social media/dating apps, then gradually lures the victim to invest in a fraudulent platform they control.",
        "common_victims": "Dating app users, lonely individuals",
        "golden_rule": "Never invest money based on advice from someone you have only met online.",
    },
    ScamCategory.SUSPICIOUS_UNKNOWN: {
        "title": "Suspicious Unclassified Interaction",
        "description": "Contains generic high-risk patterns like extreme pressure, unusual payment links, or obfuscated identity.",
        "common_victims": "General users",
        "golden_rule": "Pause and independently verify any financial request via official channels.",
    },
    ScamCategory.SAFE_NORMAL_CONVERSATION: {
        "title": "Safe / Legitimate Conversation",
        "description": "No significant financial scam indicators or manipulative patterns were detected.",
        "common_victims": "N/A",
        "golden_rule": "Always remain mindful when handling confidential financial information.",
    },
}


# Regex patterns for high-risk entity detection
REGEX_PATTERNS = {
    # UPI IDs (e.g. name@okhdfcbank, 9876543210@paytm, user@upi)
    "upi_id": re.compile(
        r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", re.IGNORECASE
    ),
    # URLs including suspicious shorteners
    "url": re.compile(
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
        re.IGNORECASE,
    ),
    # IP Address URLs (e.g. http://192.168.1.1/login)
    "ip_url": re.compile(
        r"https?://(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s]*)?",
        re.IGNORECASE,
    ),
    # Crypto Wallet Addresses: Bitcoin, Ethereum, Solana, TRC20 USDT
    "crypto_btc": re.compile(r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b"),
    "crypto_eth": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "crypto_trx": re.compile(r"\bT[A-Za-z1-9]{33}\b"),
    # Phone numbers (international and 10-digit Indian/US)
    "phone": re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b[6-9]\d{9}\b",
    ),
    # Bank Account numbers (9 to 18 digits)
    "bank_account": re.compile(
        r"\b(?:account|a/c|acct|acc\.?\s*no\.?)\s*[:#-]?\s*(\d{9,18})\b", re.IGNORECASE
    ),
    # OTP / PIN requests
    "otp_pin_request": re.compile(
        r"\b(?:share|send|enter|give|provide|tell)\b.*?\b(?:otp|one time password|pin|mpin|cvv|password|passcode)\b",
        re.IGNORECASE,
    ),
    # QR Code reverse fraud ("scan to receive")
    "qr_receive_trick": re.compile(
        r"\b(?:scan|open)\b.*?\b(?:qr|code|scanner)\b.*?\b(?:receive|get|credit|collect|claim)\b",
        re.IGNORECASE,
    ),
    # Remote access tools
    "remote_access": re.compile(
        r"\b(?:anydesk|teamviewer|rustdesk|quicksupport|ultraviewer|airdroid|screenshare|screen\s*share|zoho\s*assist)\b",
        re.IGNORECASE,
    ),
    # Threat / Coercion / Authority
    "threat_authority": re.compile(
        r"\b(?:cbi|police|customs|cyber\s*crime|rbi|income\s*tax|court|warrant|arrest|legal\s*action|electricity\s*bill|disconnected\s*tonight|power\s*cut)\b",
        re.IGNORECASE,
    ),
    # KYC / Account Block threats
    "kyc_block_threat": re.compile(
        r"\b(?:kyc|pan|aadhaar|sim|account|debit\s*card|atm)\b.*?\b(?:suspended|blocked|deactivated|expire|expired|terminate|locked)\b",
        re.IGNORECASE,
    ),
    # Guaranteed quick profit / Ponzi
    "guaranteed_profit": re.compile(
        r"\b(?:guaranteed|100%|daily\s*profit|double\s*your\s*money|instant\s*return|zero\s*risk|easy\s*earning|vip\s*signal)\b",
        re.IGNORECASE,
    ),
    # Job Task Fraud triggers
    "job_task_fraud": re.compile(
        r"\b(?:part\s*time\s*job|like\s*youtube|rate\s*hotel|daily\s*income|earn\s*(?:rs\.?|\$|inr)\s*\d{3,6}|prepaid\s*task|task\s*commission)\b",
        re.IGNORECASE,
    ),
    # Suspicious shortener links
    "shortened_url": re.compile(
        r"https?://(?:bit\.ly|tinyurl\.com|t\.co|cutt\.ly|is\.gd|v\.gd|rb\.gy|shorturl\.at|goo\.gl|tiny\.cc)/[a-zA-Z0-9_\-]+",
        re.IGNORECASE,
    ),
}

# Suspicious TLDs commonly seen in phishing kits
SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".club",
    ".click", ".live", ".work", ".shop", ".online", ".site", ".cc", ".icu",
]

# Official Helpline info to suggest to users
SAFETY_HELPLINES = {
    "IN": {
        "name": "National Cyber Crime Reporting Portal (India)",
        "helpline": "1930",
        "website": "https://cybercrime.gov.in",
        "description": "Report financial cyber frauds within 2-4 hours to block fraudulent fund transfers (Golden Hour).",
    },
    "US": {
        "name": "Federal Trade Commission (FTC) / IC3 (USA)",
        "helpline": "1-877-382-4357",
        "website": "https://reportfraud.ftc.gov",
        "description": "Report scams, identity theft, and internet crimes to the FTC and FBI IC3.",
    },
    "UK": {
        "name": "Action Fraud (UK)",
        "helpline": "0300 123 2040",
        "website": "https://www.actionfraud.police.uk",
        "description": "National fraud and cyber crime reporting centre for the UK.",
    },
    "GLOBAL": {
        "name": "Global Financial Safety Guidelines",
        "helpline": "Contact your local bank's official card loss helpline immediately",
        "website": "https://www.consumer.ftc.gov",
        "description": "Block compromised payment cards and report unauthorized debits directly to your issuing bank.",
    }
}
