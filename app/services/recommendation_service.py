"""Recommendation Service for Actionable Safety Guidance and Helpline Routing."""

from typing import List
from app.schemas.analysis import HelplineInfo
from app.utils.constants import ScamCategory, SAFETY_HELPLINES


class RecommendationService:
    """Provides defensive action steps and emergency contact helplines in English & Tamil."""

    CATEGORY_RECOMMENDATIONS = {
        ScamCategory.UPI_QR_SCAM: [
            "⛔ DO NOT scan the QR code or accept any payment requests on Google Pay / PhonePe / Paytm.",
            "🔒 NEVER enter your 4-digit or 6-digit UPI PIN to receive money. PIN is ONLY used to send/debit money.",
            "🚫 Block and report the scammer's phone number or UPI handle on your payment app.",
            "ℹ️ If you already entered your PIN and lost money, immediately call 1930 (India) or your bank to freeze transactions within the Golden Hour.",
        ],
        ScamCategory.OTP_REMOTE_ACCESS_SCAM: [
            "⛔ NEVER share SMS OTPs, verification codes, or PINs with anyone over call or chat.",
            "❌ DO NOT download or install remote access software like AnyDesk, TeamViewer, RustDesk, or QuickSupport.",
            "📱 If you installed any remote tool, immediately disconnect Wi-Fi/mobile data and uninstall the app.",
            "💳 If credentials were leaked, call your bank's 24/7 card hotlisting number to freeze your account instantly.",
        ],
        ScamCategory.PHISHING_CREDENTIAL_HARVESTING: [
            "🔗 DO NOT click on links received via SMS, WhatsApp, or email claiming your account or KYC is expired.",
            "🏦 Open your bank's verified official mobile banking application directly to check account status.",
            "🚫 Banks never send links to update PAN card, Aadhaar, or Netbanking passwords via SMS.",
            "✉️ Report the phishing link to your service provider and the National Cyber Crime portal (1930).",
        ],
        ScamCategory.URGENT_IMPERSONATION: [
            "✋ PAUSE and DO NOT panic. Legitimate law enforcement (Police/CBI/Customs) never demands money via UPI/crypto.",
            "⚡ Electricity departments never disconnect power on the same night based on an informal WhatsApp/SMS message.",
            "📞 Hang up/stop messaging and call the official customer care number listed on your physical utility bill.",
        ],
        ScamCategory.INVESTMENT_CRYPTO_PONZI: [
            "💰 DO NOT invest or transfer any money. Guaranteed high returns with zero risk are mathematically impossible and fraudulent.",
            "🚫 Ignore Telegram groups, WhatsApp 'trading mentors', and fake investment screenshots.",
            "📊 Check if the investment company is registered with national regulatory bodies (e.g. SEBI in India, SEC in US).",
        ],
        ScamCategory.JOB_OFFER_TASK_FRAUD: [
            "💼 DO NOT pay any 'security deposit', 'prepaid task fee', or 'system activation fee' to work.",
            "🚫 Legitimate companies never pay high daily salaries for simple tasks like liking videos or rating hotels.",
            "⏹️ Stop communication immediately. Any money already deposited will not be returned by the scammer.",
        ],
        ScamCategory.LOTTERY_PRIZE_SCAM: [
            "🎁 You cannot win a lottery or contest that you never entered.",
            "🚫 NEVER pay advance 'customs clearance', 'GST tax', or 'processing fees' to receive a prize.",
            "🗑️ Delete the message and block the sender.",
        ],
        ScamCategory.REFUND_OVERPAYMENT_SCAM: [
            "🔍 Check your official bank account statement in your banking app before believing any payment screenshot or SMS.",
            "❌ Do not refund any money without verifying that actual settled funds exist in your bank balance.",
        ],
        ScamCategory.LOAN_APP_EXTORTION: [
            "🚫 Do not pay advance processing fees to unverified instant loan apps.",
            "🔒 Do not grant contacts, gallery, or camera permissions to unknown loan APK files.",
            "🏦 Only apply for credit from RBI/government licensed banks and NBFCs.",
        ],
        ScamCategory.MARKETPLACE_ADVANCE_FEE: [
            "🤝 Insist on in-person meeting in a safe public location or verified escrow/cash on delivery.",
            "🚫 Never pay advance courier or delivery booking deposits to an unknown seller.",
        ],
        ScamCategory.ROMANCE_PIG_BUTCHERING: [
            "💔 Never send money, gift cards, or invest in crypto platforms recommended by an online acquaintance.",
            "🔍 Conduct a reverse image search on their profile photos.",
        ],
        ScamCategory.SUSPICIOUS_UNKNOWN: [
            "⚠️ Exercise extreme caution. Do not share financial details, OTPs, or make hasty payments.",
            "🔍 Independently verify the sender's identity through official trusted channels.",
        ],
        ScamCategory.SAFE_NORMAL_CONVERSATION: [
            "✅ No immediate action needed. Continue following standard digital hygiene.",
            "🔒 Keep your banking PINs and passwords private.",
        ],
    }

    TAMIL_RECOMMENDATIONS = {
        ScamCategory.UPI_QR_SCAM: [
            "⛔ QR குறியீட்டை ஸ்கேன் செய்யவோ அல்லது Google Pay/PhonePe-ல் பண கோரிக்கையை ஏற்கவோ வேண்டாம்.",
            "🔒 பணம் பெறுவதற்கு ஒருபோதும் UPI PIN உள்ளிட தேவையில்லை.",
            "🚫 மோசடி செய்பவரின் எண் மற்றும் UPI முகவரியை உடனே பிளாக் செய்யவும்.",
            "ℹ️ பணம் இழந்திருந்தால் உடனே 1930 எண்ணை அழைத்து பரிவர்த்தனையை முடக்கவும்.",
        ],
        ScamCategory.PHISHING_CREDENTIAL_HARVESTING: [
            "🔗 SMS/WhatsApp மூலம் வரும் போலி KYC மற்றும் வங்கி இணைப்புகளை கிளிக் செய்ய வேண்டாம்.",
            "🏦 வங்கியின் அதிகாரப்பூர்வ செயலியை மட்டுமே பயன்படுத்தி சரிபார்க்கவும்.",
            "🚫 வங்கிகள் SMS மூலம் PAN அல்லது கடவுச்சொல் மாற்ற கோருவதில்லை.",
        ],
        ScamCategory.URGENT_IMPERSONATION: [
            "✋ பதற்றமடைய வேண்டாம். அரசு மற்றும் காவல்துறை அதிகாரிகள் UPI மூலம் பணம் கோருவதில்லை.",
            "⚡ மின்சார வாரியங்கள் SMS மூலம் உடனே மின் இணைப்பை துண்டிப்பதில்லை.",
            "📞 உங்களது கட்டண ரசீதில் உள்ள அதிகாரப்பூர்வ எண்ணை தொடர்பு கொள்ளவும்.",
        ],
        ScamCategory.SAFE_NORMAL_CONVERSATION: [
            "✅ உடனடி நடவடிக்கை எதுவும் தேவையில்லை.",
            "🔒 உங்கள் வங்கி PIN மற்றும் கடவுச்சொற்களை பாதுகாப்பாக வைத்திருக்கவும்.",
        ],
    }

    def get_recommendations(self, category: ScamCategory, is_scam: bool, detected_language: str = "en") -> List[str]:
        """Return structured list of safety recommendations."""
        if detected_language in ["ta", "tamil"]:
            if not is_scam:
                return self.TAMIL_RECOMMENDATIONS.get(
                    ScamCategory.SAFE_NORMAL_CONVERSATION,
                    self.CATEGORY_RECOMMENDATIONS[ScamCategory.SAFE_NORMAL_CONVERSATION],
                )
            if category in self.TAMIL_RECOMMENDATIONS:
                return self.TAMIL_RECOMMENDATIONS[category]

        if not is_scam:
            return self.CATEGORY_RECOMMENDATIONS[ScamCategory.SAFE_NORMAL_CONVERSATION]
        return self.CATEGORY_RECOMMENDATIONS.get(
            category, self.CATEGORY_RECOMMENDATIONS[ScamCategory.SUSPICIOUS_UNKNOWN]
        )

    def get_helplines(self, detected_language: str = "en") -> List[HelplineInfo]:
        """Return emergency reporting portals and cybercrime hotlines."""
        helplines_list = [
            HelplineInfo(
                name=SAFETY_HELPLINES["IN"]["name"],
                helpline=SAFETY_HELPLINES["IN"]["helpline"],
                website=SAFETY_HELPLINES["IN"]["website"],
                description=SAFETY_HELPLINES["IN"]["description"],
            ),
            HelplineInfo(
                name=SAFETY_HELPLINES["US"]["name"],
                helpline=SAFETY_HELPLINES["US"]["helpline"],
                website=SAFETY_HELPLINES["US"]["website"],
                description=SAFETY_HELPLINES["US"]["description"],
            ),
            HelplineInfo(
                name=SAFETY_HELPLINES["UK"]["name"],
                helpline=SAFETY_HELPLINES["UK"]["helpline"],
                website=SAFETY_HELPLINES["UK"]["website"],
                description=SAFETY_HELPLINES["UK"]["description"],
            ),
        ]
        return helplines_list


recommendation_service = RecommendationService()
