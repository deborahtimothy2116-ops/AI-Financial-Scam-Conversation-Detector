"""Link X-ray: take every link in a message apart to expose the tricks behind it.

Works offline on the text of the link only; links are never fetched or opened.
Detects the structural tricks people miss at a glance:
- user-info trick (``https://sbi.co.in@evil.xyz`` really goes to evil.xyz)
- brand placed in a subdomain (``sbi.co.in.verify-kyc.xyz``)
- homoglyphs / punycode (Cyrillic "а" in ``pаypal.com``, ``xn--...``)
- lookalike spellings (``amaz0n``), URL shorteners, raw IP addresses,
  risky TLDs, plain http, and login/KYC bait in the path.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from app.services.message_checks import OFFICIAL_DOMAINS, SHORTENERS, _DOMAIN_TLDS
from app.utils.constants import SUSPICIOUS_TLDS


# Second-level suffixes where the registrable domain has three labels.
MULTI_PART_SUFFIXES = {
    "co.in", "gov.in", "nic.in", "org.in", "net.in", "ac.in", "bank.in",
    "co.uk", "org.uk", "gov.uk", "com.au", "co.jp", "com.sg", "org.au",
}

# Characters from other scripts that look like Latin letters.
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ԁ": "d", "ɡ": "g", "һ": "h", "ո": "n", "ѕ": "s",
    "ԛ": "q", "ԝ": "w", "ᴠ": "v", "ʏ": "y", "ı": "i", "ⅼ": "l", "ǀ": "l",
    "α": "a", "ο": "o", "ρ": "p", "ν": "v", "τ": "t", "κ": "k", "ι": "i",
    "Α": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X",
}

LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"})

BAIT_PATH_WORDS = (
    "login", "signin", "verify", "kyc", "update", "secure", "account", "unlock",
    "reward", "claim", "refund", "otp", "bank", "wallet", "confirm",
)

URL_RE = re.compile(
    r"https?://[^\s<>\"']+"
    r"|(?<![@\w.-])(?:www\.)?(?:[\w-]+\.)+(?:" + _DOMAIN_TLDS + r")\b(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)

SEVERITY_ORDER = {"info": 0, "good": 0, "low": 1, "medium": 2, "high": 3}


def find_links(text: str) -> List[Tuple[int, int, str]]:
    """Return (start, end, link_text) for every link-like string in the text."""
    links = []
    for match in URL_RE.finditer(text or ""):
        raw = match.group(0)
        trimmed = raw.rstrip(".,;:!?)]}'\"")
        links.append((match.start(), match.start() + len(trimmed), trimmed))
    return links


def registered_domain(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _skeleton(host: str) -> str:
    """ASCII look-alike of a host: map confusable letters to the Latin ones they imitate."""
    return "".join(CONFUSABLES.get(ch, ch) for ch in host)


def _official_brand(domain: str) -> Optional[str]:
    for brand, official in OFFICIAL_DOMAINS.items():
        if any(domain == d or domain.endswith("." + d) for d in official):
            return brand
    return None


def _imitated_brand(text: str) -> Optional[str]:
    squashed = text.translate(LEET).replace("-", "").replace(".", "")
    for brand in OFFICIAL_DOMAINS:
        token = brand.replace(" ", "")
        if len(token) >= 3 and token in squashed:
            return brand
    return None


def _decode_punycode(host: str) -> str:
    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return host


def xray_link(link_text: str) -> Dict:
    """Dissect one link and return what it really points to and which tricks it uses."""
    candidate = link_text if re.match(r"https?://", link_text, re.I) else "http://" + link_text
    parts = urlsplit(candidate)
    netloc = parts.netloc
    flags: List[Dict] = []

    def flag(code, title, detail, severity):
        flags.append({"code": code, "title": title, "detail": detail, "severity": severity})

    # User-info trick: everything before "@" is ignored by the browser.
    if "@" in netloc:
        shown, _, real = netloc.rpartition("@")
        flag("USERINFO_TRICK", "Hidden real destination",
             f"The part before '@' ('{shown}') is ignored by browsers. This link really opens '{real.split(':')[0]}'.",
             "high")
        netloc = real
    host = netloc.split(":")[0].lower().strip(".")
    if host.startswith("www."):
        host = host[4:]

    display_host = host
    if "xn--" in host:
        display_host = _decode_punycode(host)
        flag("PUNYCODE", "Disguised international domain",
             f"'{host}' is punycode for '{display_host}', which can imitate a familiar name with foreign letters.",
             "high")

    if any(ord(ch) > 127 for ch in display_host):
        lookalike = _skeleton(display_host)
        scripts = sorted({unicodedata.name(ch, "?").split(" ")[0] for ch in display_host if ord(ch) > 127})
        flag("HOMOGLYPH", "Look-alike letters from another alphabet",
             f"Contains non-Latin characters ({', '.join(scripts)}) that make it read like '{lookalike}'.",
             "high")
    else:
        lookalike = display_host

    is_ip = bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host))
    domain = host if is_ip else registered_domain(host)
    official_brand = None if is_ip else _official_brand(host)

    if is_ip:
        flag("RAW_IP", "Bare IP address", "Uses a numeric IP instead of a company domain; legitimate sites don't.", "high")

    if host in SHORTENERS or domain in SHORTENERS:
        flag("SHORTENER", "Shortened link hides the destination",
             f"'{domain}' is a link shortener, so you cannot see where it really leads before opening it.",
             "medium")

    if official_brand:
        flag("OFFICIAL_DOMAIN", "Official domain",
             f"'{domain}' is a known official domain of {official_brand.upper()}.", "good")
    elif not is_ip:
        subdomains = host[: -len(domain)].rstrip(".") if host.endswith(domain) else ""
        brand_in_sub = _imitated_brand(subdomains) if subdomains else None
        if brand_in_sub:
            flag("BRAND_IN_SUBDOMAIN", "Brand name placed in front of another domain",
                 f"Starts with '{subdomains}' to look like {brand_in_sub.upper()}, but the real site is '{domain}'.",
                 "high")
        else:
            imitated = _imitated_brand(_skeleton(domain))
            if imitated:
                flag("LOOKALIKE_DOMAIN", "Imitates a well-known brand",
                     f"'{domain}' resembles {imitated.upper()} but is not one of its official domains "
                     f"({', '.join(OFFICIAL_DOMAINS[imitated][:2])}).",
                     "high")

        if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            flag("RISKY_TLD", "High-risk domain ending",
                 f"Ends in '.{domain.rsplit('.', 1)[-1]}', a cheap domain ending heavily used by scam sites.", "medium")

        if ("xn--" not in host and host.count("-") >= 2) or len(host.split(".")) >= 5:
            flag("CLUTTERED_HOST", "Unusually long or hyphenated address",
                 "Long, hyphen-heavy addresses are often used to squeeze in trustworthy-sounding words.", "low")

    path = (parts.path or "") + ("?" + parts.query if parts.query else "")
    bait = [w for w in BAIT_PATH_WORDS if w in path.lower()]
    if bait and not official_brand:
        flag("BAIT_PATH", "Login / verification bait in the link",
             f"The path contains '{', '.join(bait[:3])}', typical of fake login and KYC pages.", "medium")

    if candidate.lower().startswith("http://") and re.match(r"http://", link_text, re.I):
        flag("NO_HTTPS", "Not encrypted (http)", "Uses plain http, so anything typed on the page can be intercepted.", "low")

    worst = max((SEVERITY_ORDER[f["severity"]] for f in flags), default=0)
    risk = "danger" if worst >= 3 else "caution" if worst >= 1 else ("safe" if official_brand else "unknown")

    return {
        "link": link_text,
        "host": display_host,
        "real_domain": domain,
        "looks_like": lookalike if lookalike != display_host else None,
        "official_brand": official_brand.upper() if official_brand else None,
        "risk": risk,
        "flags": flags,
    }


def xray_links(text: str) -> List[Dict]:
    """X-ray every distinct link in the text."""
    seen, reports = set(), []
    for _, _, link in find_links(text):
        if link.lower() in seen:
            continue
        seen.add(link.lower())
        reports.append(xray_link(link))
    return reports
