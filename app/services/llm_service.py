"""LLM Provider Abstraction and Multi-Provider Integrations with Resilient Fallback."""

from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMServiceError
from app.services.link_xray import xray_links
from app.services.message_checks import run_message_checks
from app.utils.constants import ScamCategory, IndicatorSeverity, REGEX_PATTERNS

URGENCY_PHRASES = [
    "immediately", "within 15 minutes", "within 24 hours", "within 2 hours", "within 1 hour",
    "urgent", "hurry", "last chance", "today only", "act now", "final notice", "last warning",
    "expires today", "expire today", "today itself", "will be suspended", "will be terminated",
    "will be deactivated", "will be closed", "penalty", "failure to comply",
]


class BaseLLMProvider(ABC):
    """Abstract interface for LLM AI scam analysis providers."""

    @abstractmethod
    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        """Analyze message content and return structured scam evaluation."""
        pass


LLM_ANALYSIS_SYSTEM_PROMPT = """You are an elite Defensive Financial Cybersecurity and Fraud Intelligence AI.
Your objective is to inspect user-provided conversation snippets/messages and detect if they are financial scams or fraud attempts BEFORE the victim makes a payment or shares credentials.

You must categorize the message into exactly one of the following ScamCategory enum values:
- UPI_QR_SCAM (e.g. asking user to scan QR code / enter PIN to "receive" money)
- LOTTERY_PRIZE_SCAM (fake prize/lottery/customs fee)
- URGENT_IMPERSONATION (police, bank manager, electricity board, CBI, family emergency)
- INVESTMENT_CRYPTO_PONZI (guaranteed high daily return, doubling money, telegram signals)
- JOB_OFFER_TASK_FRAUD (like youtube videos, prepaid task deposit)
- PHISHING_CREDENTIAL_HARVESTING (fake KYC link, account suspended notice)
- REFUND_OVERPAYMENT_SCAM (accidental excess transfer refund claim)
- OTP_REMOTE_ACCESS_SCAM (asking for OTP or AnyDesk/TeamViewer/RustDesk install)
- LOAN_APP_EXTORTION (instant loan processing advance fee)
- MARKETPLACE_ADVANCE_FEE (OLX/FB marketplace advance deposit)
- ROMANCE_PIG_BUTCHERING (emotional rapport leading to crypto investment)
- SUSPICIOUS_UNKNOWN (generic high-pressure financial solicitation)
- SAFE_NORMAL_CONVERSATION (legitimate normal conversation without fraud indicators)

Return STRICTLY a valid JSON object with the following schema:
{
  "scam_category": "<SCAM_CATEGORY_ENUM>",
  "is_scam": <true_or_false>,
  "risk_score": <number_between_0_and_100>,
  "risk_level": "<SAFE|LOW|MEDIUM|HIGH|CRITICAL>",
  "urgency_score": <number_between_0_and_100>,
  "credential_risk": <number_between_0_and_100>,
  "payment_vector_risk": <number_between_0_and_100>,
  "coercion_risk": <number_between_0_and_100>,
  "link_obfuscation_risk": <number_between_0_and_100>,
  "explanation": "<Clear, plain-language 2-3 sentence explanation of why this is or is not safe>",
  "indicators": [
    {
      "title": "<Short indicator title>",
      "description": "<Detailed explanation of the specific red flag>",
      "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
      "confidence": <float_between_0.0_and_1.0>,
      "snippet": "<Exact suspicious phrase from the message>",
      "rule_id": "<RULE_ID>"
    }
  ],
  "recommendations": [
    "<Actionable safety step 1>",
    "<Actionable safety step 2>"
  ]
}
"""


class RuleBasedFallbackProvider(BaseLLMProvider):
    """High-precision, offline rule-based heuristic detector and fallback."""

    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        logger.info("Executing rule-based heuristic scam analysis engine.")
        cleaned = text.lower()

        indicators: List[Dict[str, Any]] = []
        urgency_score = 0.0
        credential_risk = 0.0
        payment_vector_risk = 0.0
        coercion_risk = 0.0
        link_obfuscation_risk = 0.0
        detected_category = ScamCategory.SAFE_NORMAL_CONVERSATION

        # 1. Check for QR / UPI Reverse Fraud ("Scan to receive")
        if REGEX_PATTERNS["qr_receive_trick"].search(cleaned) or (
            "scan" in cleaned and ("receive" in cleaned or "credit" in cleaned or "inr" in cleaned)
        ):
            indicators.append({
                "title": "Reverse QR Code Payment Trap",
                "description": "Scammer requests you to scan a QR code or enter your UPI PIN claiming you will receive money. Scanning a QR code or entering a PIN ONLY debits money from your account.",
                "severity": IndicatorSeverity.CRITICAL.value,
                "confidence": 0.98,
                "snippet": "scan QR / collect payment",
                "rule_id": "RULE_QR_RECEIVE_FRAUD",
            })
            payment_vector_risk = max(payment_vector_risk, 95.0)
            credential_risk = max(credential_risk, 90.0)
            detected_category = ScamCategory.UPI_QR_SCAM

        # 2. Check for OTP / PIN / CVV credential harvesting
        if REGEX_PATTERNS["otp_pin_request"].search(cleaned) or (
            ("otp" in cleaned or "pin" in cleaned or "password" in cleaned or "cvv" in cleaned)
            and ("share" in cleaned or "send" in cleaned or "verify" in cleaned or "tell" in cleaned)
        ):
            indicators.append({
                "title": "Confidential Security Credential Solicitation",
                "description": "The message explicitly asks to share an OTP, UPI PIN, password, or card CVV. Legitimate banks and support teams never ask for these under any circumstances.",
                "severity": IndicatorSeverity.CRITICAL.value,
                "confidence": 0.99,
                "snippet": "share OTP / PIN / password",
                "rule_id": "RULE_CREDENTIAL_SOLICITATION",
            })
            credential_risk = max(credential_risk, 98.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.OTP_REMOTE_ACCESS_SCAM

        # 3. Check for Remote Desktop Tools
        if extracted_entities.get("remote_access_tools") or REGEX_PATTERNS["remote_access"].search(cleaned):
            tools = ", ".join(extracted_entities.get("remote_access_tools", ["AnyDesk/TeamViewer"]))
            indicators.append({
                "title": "Remote Device Control Installation Request",
                "description": f"Requesting installation of remote control software ({tools}). Fraudsters use this to gain full screen and mouse control of your banking app.",
                "severity": IndicatorSeverity.CRITICAL.value,
                "confidence": 0.95,
                "snippet": tools,
                "rule_id": "RULE_REMOTE_DESKTOP_ACCESS",
            })
            credential_risk = max(credential_risk, 95.0)
            detected_category = ScamCategory.OTP_REMOTE_ACCESS_SCAM

        # 4. Check for Lottery / Lucky Draw Advance Fee
        if (
            ("lottery" in cleaned or "won" in cleaned or "lucky draw" in cleaned or "winner" in cleaned) and (
                "claim" in cleaned or "processing fee" in cleaned or "tax" in cleaned or "charge" in cleaned or "prize" in cleaned or "fee" in cleaned
            )
        ) or (
            ("congratulations" in cleaned or "you are selected" in cleaned or "you have been selected" in cleaned)
            and ("free gift" in cleaned or "reward" in cleaned or "prize" in cleaned or "cash" in cleaned or "claim" in cleaned)
        ):
            indicators.append({
                "title": "Unsolicited Prize / Advance Fee Scam",
                "description": "Claims you won a massive prize or lottery you never entered, asking for an advance processing fee, tax, or customs clearance to release funds.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.95,
                "snippet": "lottery prize / claim processing fee",
                "rule_id": "RULE_LOTTERY_ADVANCE_FEE",
            })
            payment_vector_risk = max(payment_vector_risk, 90.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.LOTTERY_PRIZE_SCAM

        # 5. Check for Task / Job / YouTube Fraud
        if REGEX_PATTERNS["job_task_fraud"].search(cleaned) or (
            ("part time" in cleaned or "daily income" in cleaned or "task" in cleaned or "like video" in cleaned)
            and ("earn" in cleaned or "deposit" in cleaned or "commission" in cleaned)
        ):
            indicators.append({
                "title": "Prepaid Task / Work-From-Home Fraud Scheme",
                "description": "Promises high daily income for trivial tasks (e.g. liking YouTube videos, rating hotels), followed by requests for prepaid deposits to release earnings.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.92,
                "snippet": "part time job / daily task earnings",
                "rule_id": "RULE_JOB_TASK_FRAUD",
            })
            payment_vector_risk = max(payment_vector_risk, 85.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.JOB_OFFER_TASK_FRAUD

        # 6. Check for Guaranteed High-Yield / Crypto Ponzi
        if REGEX_PATTERNS["guaranteed_profit"].search(cleaned) or (
            ("double" in cleaned or "guaranteed profit" in cleaned or "100% return" in cleaned)
            and ("invest" in cleaned or "crypto" in cleaned or "forex" in cleaned or "trading" in cleaned)
        ):
            indicators.append({
                "title": "Unrealistic Guaranteed Investment Returns",
                "description": "Promises guaranteed high returns with zero risk, classic sign of a Ponzi/Pig Butchering crypto scheme.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.90,
                "snippet": "guaranteed double returns / investment",
                "rule_id": "RULE_CRYPTO_PONZI_PROMISE",
            })
            payment_vector_risk = max(payment_vector_risk, 88.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.INVESTMENT_CRYPTO_PONZI

        # 7. Check for KYC / Account Expiry Phishing
        if REGEX_PATTERNS["kyc_block_threat"].search(cleaned) or (
            ("kyc" in cleaned or "pan" in cleaned or "sim" in cleaned) and ("block" in cleaned or "expire" in cleaned or "update" in cleaned)
        ):
            indicators.append({
                "title": "Deceptive KYC / Account Suspension Threat",
                "description": "Claims your bank account, PAN card, or SIM will be permanently blocked unless you update KYC immediately via an unverified link.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.93,
                "snippet": "KYC update / Account blocked",
                "rule_id": "RULE_KYC_EXPIRY_SCARE",
            })
            urgency_score = max(urgency_score, 90.0)
            link_obfuscation_risk = max(link_obfuscation_risk, 80.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.PHISHING_CREDENTIAL_HARVESTING

        # 8. Check for Authority Impersonation & Coercive Threats (unless it's an advance fee prize pretext)
        if REGEX_PATTERNS["threat_authority"].search(cleaned) and detected_category != ScamCategory.LOTTERY_PRIZE_SCAM:
            indicators.append({
                "title": "Authority Coercion & Intimidation Tactic",
                "description": "Impersonating law enforcement (Police, CBI, Cyber Cell, RBI) or utility providers with threats of immediate arrest or power disconnection.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.92,
                "snippet": "Authority/Police/Disconnection threat",
                "rule_id": "RULE_AUTHORITY_INTIMIDATION",
            })
            coercion_risk = max(coercion_risk, 90.0)
            urgency_score = max(urgency_score, 85.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.URGENT_IMPERSONATION


        # 9. Suspicious URL Shorteners & Phishing Links
        if extracted_entities.get("suspicious_shorteners") or extracted_entities.get("suspicious_tld_urls"):
            short_links = extracted_entities.get("suspicious_shorteners", []) + extracted_entities.get("suspicious_tld_urls", [])
            indicators.append({
                "title": "Obfuscated / High-Risk Phishing Link",
                "description": f"Message contains suspicious shortened or untrusted domain links ({', '.join(short_links[:2])}) designed to mask the true destination.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.88,
                "snippet": short_links[0] if short_links else "shortened link",
                "rule_id": "RULE_OBFUSCATED_URL",
            })
            link_obfuscation_risk = max(link_obfuscation_risk, 90.0)
            if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                detected_category = ScamCategory.PHISHING_CREDENTIAL_HARVESTING

        # 10. Crypto Wallets in conversation
        if extracted_entities.get("crypto_wallets"):
            indicators.append({
                "title": "Irreversible Cryptocurrency Wallet Address Provided",
                "description": "Direct crypto transfer addresses are untraceable and irreversible, heavily favored by financial scammers.",
                "severity": IndicatorSeverity.HIGH.value,
                "confidence": 0.85,
                "snippet": extracted_entities["crypto_wallets"][0],
                "rule_id": "RULE_CRYPTO_WALLET_PRESENT",
            })
            payment_vector_risk = max(payment_vector_risk, 80.0)

        # 11. Sender, link, request and writing-style checks
        checks = run_message_checks(text)
        indicators.extend(checks.indicators)
        credential_risk = max(credential_risk, checks.credential_risk)
        payment_vector_risk = max(payment_vector_risk, checks.payment_vector_risk)
        link_obfuscation_risk = max(link_obfuscation_risk, checks.link_obfuscation_risk)
        coercion_risk = max(coercion_risk, checks.coercion_risk)
        if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION and checks.category_hint:
            detected_category = checks.category_hint

        # 12. Link X-ray: structural link tricks (hidden destination, homoglyphs, brand in subdomain, raw IP)
        deceptive_codes = {"USERINFO_TRICK", "PUNYCODE", "HOMOGLYPH", "BRAND_IN_SUBDOMAIN", "RAW_IP"}
        for report in xray_links(text):
            tricks = [f for f in report["flags"] if f["code"] in deceptive_codes]
            if tricks:
                indicators.append({
                    "title": "Deceptive Link Structure",
                    "description": f"{tricks[0]['title']}: {tricks[0]['detail']}",
                    "severity": IndicatorSeverity.CRITICAL.value,
                    "confidence": 0.95,
                    "snippet": report["link"][:80],
                    "rule_id": "RULE_DECEPTIVE_LINK",
                })
                link_obfuscation_risk = max(link_obfuscation_risk, 98.0)
                if detected_category == ScamCategory.SAFE_NORMAL_CONVERSATION:
                    detected_category = ScamCategory.PHISHING_CREDENTIAL_HARVESTING
                break

        # 13. Urgency, deadline and threat keywords check
        if any(w in cleaned for w in URGENCY_PHRASES):
            urgency_score = max(urgency_score, 75.0)
            if not any(i["rule_id"] == "RULE_FALSE_URGENCY" for i in indicators):
                indicators.append({
                    "title": "Artificial Urgency & Time Pressure",
                    "description": "Creates synthetic panic to pressure you into acting hastily without verifying the legitimacy of the request.",
                    "severity": IndicatorSeverity.MEDIUM.value,
                    "confidence": 0.80,
                    "snippet": "urgent / immediate action required",
                    "rule_id": "RULE_FALSE_URGENCY",
                })

        # Calculate composite score
        max_subscore = max(urgency_score, credential_risk, payment_vector_risk, coercion_risk, link_obfuscation_risk)
        if len(indicators) >= 2:
            composite_score = min(100.0, max_subscore * 0.7 + (len(indicators) * 10))
        elif len(indicators) == 1:
            composite_score = max_subscore
        else:
            composite_score = 5.0  # Clean normal message

        is_scam = composite_score >= 40.0

        if composite_score >= 85.0:
            risk_level = "CRITICAL"
        elif composite_score >= 65.0:
            risk_level = "HIGH"
        elif composite_score >= 40.0:
            risk_level = "MEDIUM"
        elif composite_score >= 20.0:
            risk_level = "LOW"
        else:
            risk_level = "SAFE"
            detected_category = ScamCategory.SAFE_NORMAL_CONVERSATION

        # Explanation
        if is_scam:
            explanation = (
                f"This conversation exhibits strong indicators of a financial scam ({detected_category.value}). "
                f"The sender is utilizing psychological pressure, deceptive links, or credential requests to misappropriate funds."
            )
        else:
            explanation = "No overt financial scam indicators or credential theft patterns were detected in this message."

        # Recommendations
        recs = [
            "DO NOT make any financial payment or transfer funds.",
            "NEVER share your OTP, UPI PIN, password, or card CVV with anyone.",
            "Do not click on unverified links or download remote access tools (AnyDesk/TeamViewer).",
            "Independently verify with official support numbers found on the official website or bank card.",
        ]

        return {
            "scam_category": detected_category.value,
            "is_scam": is_scam,
            "risk_score": round(composite_score, 1),
            "risk_level": risk_level,
            "urgency_score": round(urgency_score, 1),
            "credential_risk": round(credential_risk, 1),
            "payment_vector_risk": round(payment_vector_risk, 1),
            "coercion_risk": round(coercion_risk, 1),
            "link_obfuscation_risk": round(link_obfuscation_risk, 1),
            "explanation": explanation,
            "indicators": indicators,
            "recommendations": recs,
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Integration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"
        self.fallback = RuleBasedFallbackProvider()

    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("OpenAI API key missing. Falling back to Rule-based engine.")
            return await self.fallback.analyze_message(text, extracted_entities, language)

        prompt_user = (
            f"Analyze this suspicious message snippet for potential financial scams:\n"
            f"--- MESSAGE TEXT ---\n{text}\n"
            f"--- EXTRACTED ENTITIES ---\n{json.dumps(extracted_entities)}\n"
            f"--- LANGUAGE ---\n{language}\n"
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": LLM_ANALYSIS_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_user},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    if settings.LLM_FALLBACK_TO_RULE_BASED:
                        return await self.fallback.analyze_message(text, extracted_entities, language)
                    raise LLMServiceError(f"OpenAI error: {response.text}")

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed = json.loads(raw_content)
                return parsed

        except Exception as e:
            logger.error(f"Failed OpenAI LLM analysis: {e}. Falling back to Rule-based engine.")
            if settings.LLM_FALLBACK_TO_RULE_BASED:
                return await self.fallback.analyze_message(text, extracted_entities, language)
            raise LLMServiceError(str(e))


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Integration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or "gemini-1.5-flash"
        self.fallback = RuleBasedFallbackProvider()

    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("Gemini API key missing. Falling back to Rule-based engine.")
            return await self.fallback.analyze_message(text, extracted_entities, language)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        prompt = f"{LLM_ANALYSIS_SYSTEM_PROMPT}\n\nUser Message:\n{text}\nEntities: {json.dumps(extracted_entities)}\nLanguage: {language}"

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"},
                    },
                )
                if response.status_code != 200:
                    logger.error(f"Gemini API error {response.status_code}: {response.text}")
                    return await self.fallback.analyze_message(text, extracted_entities, language)

                data = response.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_content)
        except Exception as e:
            logger.error(f"Gemini error: {e}. Falling back to rule-based.")
            return await self.fallback.analyze_message(text, extracted_entities, language)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API Integration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or "claude-3-5-sonnet-20241022"
        self.fallback = RuleBasedFallbackProvider()

    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("Anthropic API key missing. Falling back to Rule-based engine.")
            return await self.fallback.analyze_message(text, extracted_entities, language)

        user_content = f"Analyze this message:\n{text}\nExtracted entities: {json.dumps(extracted_entities)}\nLanguage: {language}"
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "system": LLM_ANALYSIS_SYSTEM_PROMPT,
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                )
                if response.status_code != 200:
                    logger.error(f"Anthropic error: {response.text}")
                    return await self.fallback.analyze_message(text, extracted_entities, language)

                data = response.json()
                raw_text = data["content"][0]["text"]
                # Extract json from potential markdown code block
                json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Anthropic error: {e}. Falling back.")
            return await self.fallback.analyze_message(text, extracted_entities, language)


class GroqProvider(BaseLLMProvider):
    """Groq High-Speed LLM Integration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or "llama-3.3-70b-versatile"
        self.fallback = RuleBasedFallbackProvider()

    async def analyze_message(
        self, text: str, extracted_entities: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("Groq API key missing. Falling back to Rule-based engine.")
            return await self.fallback.analyze_message(text, extracted_entities, language)

        prompt_user = f"Analyze:\n{text}\nEntities: {json.dumps(extracted_entities)}\nLanguage: {language}"
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": LLM_ANALYSIS_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_user},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                    },
                )
                if response.status_code != 200:
                    return await self.fallback.analyze_message(text, extracted_entities, language)

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                return json.loads(raw_content)
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return await self.fallback.analyze_message(text, extracted_entities, language)


def get_llm_provider() -> BaseLLMProvider:
    """Factory to instantiate the configured LLM provider."""
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "anthropic":
        return AnthropicProvider()
    elif provider_name == "groq":
        return GroqProvider()
    else:
        return RuleBasedFallbackProvider()


llm_service: BaseLLMProvider = get_llm_provider()
