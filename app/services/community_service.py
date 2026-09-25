"""Community scam reports: normalise, extract and look up scammer identifiers.

Users report the phone numbers, UPI IDs, websites and emails scammers used.
Anyone can then check an identifier before paying, and every scan warns when a
message contains something the community already reported.

Safeguards against misuse: only logged-in users can report, one report per
user per identifier, official brand domains and shared link-shortener domains
can't be reported, and counts are always shown as unverified user reports.
"""

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.scam_report import ScamReport
from app.services.link_xray import find_links, registered_domain, _official_brand
from app.services.message_checks import EMAIL_RE, FREE_EMAIL_DOMAINS, PHONE_RE, SHORTENERS

UPI_RE = re.compile(r"\b[a-z0-9._-]{2,256}@[a-z]{2,64}\b(?![.\w-])", re.IGNORECASE)
IDENTIFIER_TYPES = ("phone", "upi", "domain", "email")

# Reports needed before a scan treats an identifier as strongly suspect.
STRONG_REPORT_THRESHOLD = 3


class InvalidIdentifier(ValueError):
    pass


def normalize_phone(raw: str) -> Optional[str]:
    """Indian numbers become their 10 digits; other countries keep '+' and the country code.
    Anything else (e.g. a 12-digit UPI transaction ID) is not treated as a phone number."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        return digits
    if raw.strip().startswith("+") and 11 <= len(digits) <= 13:
        return "+" + digits
    return None


def normalize_domain(raw: str) -> Optional[str]:
    host = re.sub(r"^[a-z]+://", "", raw.strip().lower()).split("/")[0].split("?")[0]
    host = host.rpartition("@")[2].split(":")[0].strip(".")
    if host.startswith("www."):
        host = host[4:]
    if "." not in host:
        return None
    return registered_domain(host)


def is_reportable_domain(domain: str) -> bool:
    return not (_official_brand(domain) or domain in SHORTENERS or domain in FREE_EMAIL_DOMAINS)


def normalize_identifier(raw: str) -> Tuple[str, str]:
    """Detect the identifier type and return (type, normalised value)."""
    value = (raw or "").strip()
    if not value:
        raise InvalidIdentifier("Enter a phone number, UPI ID, website or email address.")
    if "@" in value and not value.lower().startswith(("http://", "https://")):
        local, _, domain = value.lower().rpartition("@")
        if "." in domain:
            if not EMAIL_RE.fullmatch(value.lower()):
                raise InvalidIdentifier("That email address doesn't look valid.")
            return "email", value.lower()
        if not UPI_RE.fullmatch(value.lower()):
            raise InvalidIdentifier("That UPI ID doesn't look valid (example: name@okaxis).")
        return "upi", value.lower()
    if re.fullmatch(r"[+\d\s().-]{10,20}", value):
        phone = normalize_phone(value)
        if not phone:
            raise InvalidIdentifier("That phone number doesn't look valid.")
        return "phone", phone
    domain = normalize_domain(value)
    if not domain:
        raise InvalidIdentifier("Enter a phone number, UPI ID, website or email address.")
    return "domain", domain


def extract_identifiers(text: str) -> List[Tuple[str, str]]:
    """Find reportable scammer identifiers (type, normalised value) in a message."""
    found: List[Tuple[str, str]] = []

    def add(item):
        if item not in found:
            found.append(item)

    for email in EMAIL_RE.finditer(text or ""):
        add(("email", email.group(0).lower()))
    for upi in UPI_RE.finditer(text or ""):
        add(("upi", upi.group(0).lower()))
    for phone in PHONE_RE.findall(text or ""):
        normalized = normalize_phone(phone)
        if normalized:
            add(("phone", normalized))
    for _, _, link in find_links(text or ""):
        domain = normalize_domain(link)
        if domain and is_reportable_domain(domain):
            add(("domain", domain))
    return found


class ScamReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_report(self, identifier_type: str, identifier: str, reporter_user_id: str,
                   scam_category: Optional[str] = None, note: Optional[str] = None,
                   analysis_id: Optional[str] = None) -> Tuple[ScamReport, bool]:
        """Add a report; returns (report, created). Re-reporting the same identifier is a no-op."""
        existing = (
            self.db.query(ScamReport)
            .filter(ScamReport.identifier == identifier, ScamReport.reporter_user_id == reporter_user_id)
            .first()
        )
        if existing:
            return existing, False
        report = ScamReport(identifier_type=identifier_type, identifier=identifier, scam_category=scam_category,
                            note=note, reporter_user_id=reporter_user_id, analysis_id=analysis_id)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report, True

    def summary(self, identifier: str) -> Dict:
        rows = self.db.query(ScamReport).filter(ScamReport.identifier == identifier).all()
        categories = Counter(r.scam_category for r in rows if r.scam_category)
        dates = sorted(r.created_at for r in rows)
        return {
            "report_count": len(rows),
            "categories": dict(categories.most_common()),
            "first_reported": dates[0] if dates else None,
            "last_reported": dates[-1] if dates else None,
        }

    def counts_for(self, identifiers: List[str]) -> Dict[str, int]:
        if not identifiers:
            return {}
        rows = (
            self.db.query(ScamReport.identifier, func.count(ScamReport.id))
            .filter(ScamReport.identifier.in_(identifiers))
            .group_by(ScamReport.identifier)
            .all()
        )
        return {identifier: count for identifier, count in rows}


def find_reported_in_text(db: Session, text: str) -> List[Dict]:
    """Identifiers in the text that the community has reported, with their report counts."""
    identifiers = extract_identifiers(text)
    counts = ScamReportRepository(db).counts_for([value for _, value in identifiers])
    return [
        {"identifier_type": kind, "identifier": value, "report_count": counts[value]}
        for kind, value in identifiers
        if counts.get(value)
    ]
