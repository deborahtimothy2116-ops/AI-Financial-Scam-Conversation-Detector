"""'I've been scammed' emergency response: golden-hour steps and a ready-to-file complaint draft."""

import re
from datetime import datetime
from typing import Dict, List, Optional

from app.services.community_service import UPI_RE, normalize_phone
from app.services.link_xray import find_links
from app.services.message_checks import EMAIL_RE, PHONE_RE

INCIDENT_TYPES: Dict[str, str] = {
    "upi_payment": "Money sent by UPI / QR code",
    "bank_transfer": "Money sent by bank transfer (NEFT / IMPS / RTGS)",
    "card": "Debit / credit card details used",
    "otp_shared": "OTP, PIN or password shared",
    "remote_app": "Remote-access app installed (AnyDesk, TeamViewer, etc.)",
    "digital_arrest": "Fake police / CBI 'digital arrest' call",
    "investment": "Investment / trading / crypto app",
    "no_money_lost": "Nothing lost yet, but I replied or clicked",
}

MONEY_LOST = {"upi_payment", "bank_transfer", "card", "investment", "digital_arrest"}

AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)


def _step(priority: str, title: str, detail: str, label: Optional[str] = None, href: Optional[str] = None) -> Dict:
    step = {"priority": priority, "title": title, "detail": detail}
    if label and href:
        step["action"] = {"label": label, "href": href}
    return step


def emergency_steps(incident_type: str) -> List[Dict]:
    """Ordered, incident-specific steps. 'now' steps belong in the first hour."""
    if incident_type not in INCIDENT_TYPES:
        incident_type = "no_money_lost"
    steps: List[Dict] = []

    if incident_type in MONEY_LOST:
        steps.append(_step(
            "now", "Call 1930 immediately",
            "The National Cyber Crime Helpline can alert banks to freeze the money before it is moved on. "
            "The first hours (the 'golden hour') matter most. Keep your transaction ID (UTR) ready.",
            "Call 1930", "tel:1930"))
    if incident_type in MONEY_LOST | {"otp_shared", "remote_app"}:
        steps.append(_step(
            "now", "Block your bank account, card and UPI",
            "Call your bank on the number printed on your card or in its official app (never a number from the message) "
            "and ask them to block the card / UPI / net banking and raise a fraud dispute. Note the complaint number. "
            "Report within 3 working days: RBI rules limit your liability for unauthorised electronic transactions "
            "when you report quickly."))
    if incident_type == "remote_app":
        steps.append(_step(
            "now", "Cut the scammer's access",
            "Turn on airplane mode or switch off mobile data and Wi-Fi, then uninstall the remote-access app. "
            "Don't open banking apps on that phone until it has been checked."))
    if incident_type in {"otp_shared", "remote_app", "card"}:
        steps.append(_step(
            "now", "Change your passwords and UPI PIN",
            "From a safe device, change your net-banking password, UPI PIN and email password, and log out of other sessions."))
    if incident_type == "digital_arrest":
        steps.append(_step(
            "now", "Hang up. There is no 'digital arrest'",
            "Police, CBI, customs and courts never arrest or question anyone over a video call or ask for money to "
            "'verify' your account. Disconnect, don't call back, and tell your family."))
    if incident_type == "investment":
        steps.append(_step(
            "now", "Stop paying 'fees' or 'taxes' to withdraw",
            "Fake trading apps demand more money to release your 'profits'. Stop all further payments."))

    steps.append(_step(
        "today", "File a complaint on the National Cyber Crime Reporting Portal",
        "Choose 'Report Cyber Crime' > financial fraud and attach screenshots. Use the complaint draft below; "
        "you'll get an acknowledgement number to track it.",
        "Open cybercrime.gov.in", "https://cybercrime.gov.in"))
    steps.append(_step(
        "today", "Keep all the evidence",
        "Don't delete the chat, SMS or call log. Take screenshots showing the scammer's number, UPI ID, links "
        "and your bank debit messages."))
    steps.append(_step(
        "today", "Report the scammer's number on Sanchar Saathi (Chakshu)",
        "Chakshu, from the Department of Telecommunications, takes reports of fraud calls and SMS so the numbers "
        "can be checked and blocked.",
        "Open Sanchar Saathi", "https://sancharsaathi.gov.in"))
    steps.append(_step(
        "today", "Warn others",
        "Report the number, UPI ID or website in ScamShield so it is flagged for everyone who checks it."))
    if incident_type in MONEY_LOST:
        steps.append(_step(
            "later", "Follow up with your bank, then the RBI Ombudsman",
            "If the bank doesn't resolve your complaint within 30 days, or you're unhappy with the reply, "
            "complain to the RBI Ombudsman.",
            "Open RBI complaint portal", "https://cms.rbi.org.in"))
    steps.append(_step(
        "later", "Beware of 'recovery' scams",
        "Anyone who calls offering to recover your money for a fee, even claiming to be police or a lawyer, is "
        "running a second scam. Genuine recovery happens only through your bank and the police."))
    return steps


def format_inr(amount: float) -> str:
    """Indian digit grouping: 150000 -> ₹1,50,000."""
    whole, _, paise = f"{amount:.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    grouped = ",".join(groups + [tail]) if groups else tail
    return f"₹{grouped}" + (f".{paise}" if paise != "00" else "")


def defang(text: str) -> str:
    """Make links unclickable so the complaint can't be used to open the scam site by accident."""
    out, cursor = [], 0
    for start, end, link in find_links(text):
        out.append(text[cursor:start])
        out.append(re.sub(r"^http", "hxxp", link, flags=re.I).replace(".", "[.]"))
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def extract_evidence(text: str) -> Dict[str, List[str]]:
    text = text or ""
    phones: List[str] = []
    for raw in PHONE_RE.findall(text):
        if normalize_phone(raw) and raw.strip() not in phones:
            phones.append(raw.strip())
    emails = list(dict.fromkeys(m.group(0) for m in EMAIL_RE.finditer(text)))
    upi_ids = list(dict.fromkeys(m.group(0) for m in UPI_RE.finditer(text)))
    links = list(dict.fromkeys(defang(link) for _, _, link in find_links(text)))
    amounts = list(dict.fromkeys(f"₹{m.group(1)}" for m in AMOUNT_RE.finditer(text)))
    return {"phone_numbers": phones, "upi_ids": upi_ids, "links": links, "emails": emails, "amounts_mentioned": amounts}


def build_complaint(
    incident_type: str,
    amount_lost: Optional[float] = None,
    incident_datetime: Optional[datetime] = None,
    payment_method: Optional[str] = None,
    transaction_ids: Optional[List[str]] = None,
    complainant_name: Optional[str] = None,
    bank_name: Optional[str] = None,
    description: Optional[str] = None,
    message_text: Optional[str] = None,
    scam_type: Optional[str] = None,
) -> Dict:
    """Assemble a complaint for 1930 / cybercrime.gov.in / the bank from what the victim knows."""
    evidence = extract_evidence(message_text or "")
    incident_label = INCIDENT_TYPES.get(incident_type, INCIDENT_TYPES["no_money_lost"])
    when = incident_datetime.strftime("%d %b %Y, %I:%M %p") if incident_datetime else "[date and time]"
    amount = format_inr(amount_lost) if amount_lost else None
    subject_amount = f"{amount} lost" if amount else "attempted fraud"

    def listed(values: List[str]) -> str:
        return ", ".join(values) if values else "[not known]"

    lines = [
        "To: National Cyber Crime Reporting Portal (cybercrime.gov.in) / Cyber Crime Helpline 1930",
        f"Copy to: {bank_name or '[your bank]'} - Fraud / Customer Care",
        "",
        f"Subject: Complaint of online financial fraud - {subject_amount} on {when}",
        "",
        f"1. Complainant: {complainant_name or '[your full name, mobile number and address]'}",
        f"2. Type of fraud: {incident_label}" + (f" ({scam_type})" if scam_type else ""),
        f"3. Date and time of incident: {when}",
        f"4. Amount lost: {amount or 'None so far'}" + (f" via {payment_method}" if payment_method else ""),
        f"5. Transaction ID(s) / UTR: {listed([t.strip() for t in (transaction_ids or []) if t.strip()])}",
        f"6. My bank: {bank_name or '[bank name and last 4 digits of account/card]'}",
        "7. Fraudster's details:",
        f"   - Phone number(s): {listed(evidence['phone_numbers'])}",
        f"   - UPI ID(s): {listed(evidence['upi_ids'])}",
        f"   - Website(s) / link(s): {listed(evidence['links'])}",
        f"   - Email(s): {listed(evidence['emails'])}",
        "8. What happened:",
        f"   {description.strip() if description and description.strip() else '[describe in your own words how you were contacted and what you were asked to do]'}",
    ]
    if message_text and message_text.strip():
        quoted = defang(" ".join(message_text.split()))
        lines += ["", "   Message received from the fraudster (links disabled):", f"   \"{quoted[:1500]}\""]
    lines += [
        "",
        "9. Request: Please register my complaint, freeze / place a lien on the account(s) that received the money, "
        "and help me recover the amount.",
        "",
        "Attachments: screenshots of the messages / chat, and the bank SMS or statement showing the debit.",
    ]
    return {
        "incident_type": incident_type,
        "incident_label": incident_label,
        "draft_text": "\n".join(lines),
        "evidence": evidence,
        "where_to_file": [
            {"label": "Call 1930 (National Cyber Crime Helpline)", "href": "tel:1930"},
            {"label": "File at cybercrime.gov.in", "href": "https://cybercrime.gov.in"},
            {"label": "Send to your bank's fraud / customer care team", "href": None},
        ],
    }
