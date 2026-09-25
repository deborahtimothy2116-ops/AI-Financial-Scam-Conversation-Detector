"""Text Preprocessing, Obfuscation Normalization, and Entity Extraction."""

import re
from urllib.parse import urlparse
import unicodedata
from typing import Any, Dict, List, Set
from app.utils.constants import REGEX_PATTERNS, SUSPICIOUS_TLDS


class TextPreprocessor:
    """Cleans, normalizes text and extracts cybersecurity entities."""

    # Zero-width and hidden unicode characters used in phishing evasion
    INVISIBLE_CHARS = re.compile(
        r"[\u200B-\u200D\uFEFF\u00A0\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]"
    )

    # Obfuscation replacement map for common evasive spellings
    CHAR_DEOBFUSCATION_MAP = {
        "@": "a",
        "$": "s",
        "0": "o",
        "1": "i",
        "3": "e",
        "!": "i",
        "|": "l",
    }

    def clean_text(self, text: str) -> str:
        """Sanitize raw text, strip invisible characters, and normalize unicode."""
        if not text:
            return ""

        # Normalize unicode to NFKC
        normalized = unicodedata.normalize("NFKC", text)

        # Remove invisible/zero-width characters
        normalized = self.INVISIBLE_CHARS.sub(" ", normalized)

        # Normalize excessive whitespace but preserve line breaks for chat flow
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        return normalized.strip()

    def deobfuscate_keywords(self, text: str) -> str:
        """Create a deobfuscated shadow copy of text for fuzzy pattern matching."""
        cleaned = text.lower()

        # Handle spaced characters e.g. "O T P" -> "OTP", "P I N" -> "PIN", "K Y C" -> "KYC"
        cleaned = re.sub(r"\b([a-z])\s+([a-z])\s+([a-z])\b", r"\1\2\3", cleaned)
        cleaned = re.sub(r"\b([a-z])\s+([a-z])\s+([a-z])\s+([a-z])\b", r"\1\2\3\4", cleaned)

        # Character substitutions
        for char, replacement in self.CHAR_DEOBFUSCATION_MAP.items():
            cleaned = cleaned.replace(char, replacement)

        return cleaned

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract high-risk financial and technical entities from text."""
        cleaned = self.clean_text(text)

        # 1. URLs
        raw_urls = REGEX_PATTERNS["url"].findall(cleaned)
        urls: Set[str] = set()
        suspicious_shorteners: Set[str] = set()
        suspicious_tld_urls: Set[str] = set()

        for u in raw_urls:
            # Strip trailing punctuation
            u_clean = re.sub(r"[.,;!?\)\>]+$", "", u)
            urls.add(u_clean)

            # Check for URL shorteners
            if REGEX_PATTERNS["shortened_url"].match(u_clean):
                suspicious_shorteners.add(u_clean)

            # Check for suspicious TLDs (match the host's ending, not any substring:
            # "onlinesbi.sbi" must not match ".online")
            host = (urlparse(u_clean).hostname or "").lower()
            if any(host.endswith(tld) for tld in SUSPICIOUS_TLDS):
                suspicious_tld_urls.add(u_clean)

        # 2. IP URLs
        ip_urls = set(REGEX_PATTERNS["ip_url"].findall(cleaned))

        # 3. UPI IDs
        raw_upi = REGEX_PATTERNS["upi_id"].findall(cleaned)
        upi_ids = set()
        # Common valid bank handles
        valid_handles = {
            "okhdfcbank", "okaxis", "oksbi", "okicici", "paytm", "ybl",
            "ibl", "upi", "axl", "apl", "postbank", "barodampay", "federal",
            "kotak", "indus", "pnb", "cnrb", "unionbank"
        }
        for u in raw_upi:
            # Exclude standard email domains like @gmail.com, @yahoo.com
            parts = u.split("@")
            if len(parts) == 2:
                domain = parts[1].lower()
                if domain not in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "protonmail.com"}:
                    upi_ids.add(u)

        # 4. Crypto Wallets
        btc_addresses = set(REGEX_PATTERNS["crypto_btc"].findall(cleaned))
        eth_addresses = set(REGEX_PATTERNS["crypto_eth"].findall(cleaned))
        trx_addresses = set(REGEX_PATTERNS["crypto_trx"].findall(cleaned))
        crypto_wallets = btc_addresses.union(eth_addresses).union(trx_addresses)

        # 5. Phone numbers
        raw_phones = REGEX_PATTERNS["phone"].findall(cleaned)
        phone_numbers = set()
        for p in raw_phones:
            p_clean = re.sub(r"[\s\-\(\)\.]", "", p)
            if len(p_clean) >= 10:
                phone_numbers.add(p)

        # 6. Bank accounts
        bank_accounts = set(REGEX_PATTERNS["bank_account"].findall(cleaned))

        # 7. Remote Access Tools
        remote_tools = set(REGEX_PATTERNS["remote_access"].findall(cleaned))

        # 8. Suspicious APK/Executable files
        apk_files = set(re.findall(r"\b[\w\-]+\.(?:apk|exe|bat|scr|vbs|zip)\b", cleaned, re.IGNORECASE))

        return {
            "urls": sorted(list(urls)),
            "suspicious_shorteners": sorted(list(suspicious_shorteners)),
            "suspicious_tld_urls": sorted(list(suspicious_tld_urls)),
            "ip_urls": sorted(list(ip_urls)),
            "upi_ids": sorted(list(upi_ids)),
            "crypto_wallets": sorted(list(crypto_wallets)),
            "phone_numbers": sorted(list(phone_numbers)),
            "bank_accounts": sorted(list(bank_accounts)),
            "remote_access_tools": sorted(list(remote_tools)),
            "suspicious_files": sorted(list(apk_files)),
        }


text_preprocessor = TextPreprocessor()
