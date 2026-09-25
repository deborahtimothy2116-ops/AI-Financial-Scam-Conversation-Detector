"""Payment proof checker for shopkeepers and online sellers.

A common fraud: the buyer shows or sends a "payment successful" screenshot that is
edited, reused, still pending, or only a payment *request*, and leaves with the
goods. A screenshot can never prove money arrived, so this never says "genuine";
it lists red flags found in the screenshot's text and how to confirm the payment
in your own account.
"""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

UTR_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", re.IGNORECASE)
DATE_PATTERNS = [
    # 25 Sep 2026 / 25 September, 2026
    (re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b"), ("d", "m", "y")),
    # Sep 25, 2026
    (re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b"), ("m", "d", "y")),
    # 25/09/2026, 25-09-2026, 25.09.2026 (Indian day-first order)
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), ("d", "mn", "y")),
]
NOT_COMPLETED = {
    "pending": "The screenshot says the payment is pending. Pending payments often fail or are reversed.",
    "processing": "The payment is still processing, so the money has not reached you yet.",
    "in progress": "The payment is still in progress, so the money has not reached you yet.",
    "awaiting": "The payment is awaiting completion, so the money has not reached you yet.",
    "failed": "The screenshot shows a failed payment.",
    "declined": "The screenshot shows a declined payment.",
    "cancelled": "The screenshot shows a cancelled payment.",
    "reversed": "The payment was reversed.",
    "scheduled": "The payment is only scheduled, not made.",
    "payment request": "This is a payment request, not a payment. Paying or approving it would send YOUR money out.",
    "collect request": "This is a collect request, not a payment. Approving it would send YOUR money out.",
    "request money": "This is a request for money, not a payment.",
}
FAKE_APP_MARKERS = ["prank", "spoof", "fake payment", "for entertainment", "just for fun", "demo payment", "sample receipt"]


def _amount(value: str) -> float:
    return float(value.replace(",", ""))


def _parse_dates(text: str) -> List[date]:
    found = []
    for pattern, order in DATE_PATTERNS:
        for m in pattern.finditer(text):
            parts = dict(zip(order, m.groups()))
            try:
                if "m" in parts:
                    month = MONTHS.get(parts["m"][:3].lower())
                    if not month:
                        continue
                else:
                    month = int(parts["mn"])
                found.append(date(int(parts["y"]), month, int(parts["d"])))
            except ValueError:
                continue
    return found


def check_payment_proof(text: str, expected_amount: Optional[float] = None, today: Optional[date] = None) -> Dict:
    """Return red flags in a payment screenshot's text plus how to verify the payment."""
    text = text or ""
    lowered = text.lower()
    today = today or datetime.now(IST).date()
    flags: List[Dict] = []

    def flag(severity: str, title: str, detail: str):
        flags.append({"severity": severity, "title": title, "detail": detail})

    for word, detail in NOT_COMPLETED.items():
        if re.search(r"\b" + re.escape(word) + r"\b", lowered):
            flag("high", "Payment not completed", detail)
            break

    marker = next((m for m in FAKE_APP_MARKERS if m in lowered), None)
    if marker:
        flag("high", "Made with a fake-payment app", f"Contains '{marker}', text used by apps that generate fake payment screens.")

    amounts = sorted({_amount(a) for a in AMOUNT_RE.findall(text)})
    if expected_amount:
        if not amounts:
            flag("medium", "No amount found", "The screenshot doesn't clearly show a rupee amount.")
        elif not any(abs(a - expected_amount) < 0.01 for a in amounts):
            shown = ", ".join(f"₹{a:,.0f}" for a in amounts[:3])
            flag("high", "Amount doesn't match", f"You expected ₹{expected_amount:,.0f}, but the screenshot shows {shown}.")

    utrs = list(dict.fromkeys(UTR_RE.findall(text)))
    if not utrs:
        flag("medium", "No UPI reference number (UTR)", "Completed UPI payments show a 12-digit reference number. It is missing or unreadable.")

    dates = _parse_dates(text)
    if dates:
        latest = max(dates)
        if latest > today:
            flag("high", "Date is in the future", f"The screenshot is dated {latest:%d %b %Y}, after today. It has been edited.")
        elif (today - latest).days >= 2:
            flag("medium", "Old payment screenshot", f"The payment is dated {latest:%d %b %Y}. An old screenshot may be reused for a new purchase.")
    else:
        flag("low", "No date visible", "The screenshot doesn't show when the payment was made.")

    serious = [f for f in flags if f["severity"] in ("high", "medium")]
    if any(f["severity"] == "high" for f in flags):
        status, headline = "red_flags", "Do not hand over goods. This payment proof has serious red flags."
    elif serious:
        status, headline = "caution", "Check your own account before handing over goods."
    else:
        status, headline = "no_obvious_flags", "No obvious red flags, but a screenshot is not proof of payment."

    verify_steps = [
        "Open your own UPI or bank app and confirm the amount appears in your transaction history or balance.",
        "Look for the credit SMS from your bank's official sender, not a message forwarded by the buyer.",
    ]
    if utrs:
        verify_steps.append(f"Search the reference number {utrs[0]} in your app's transaction history.")
    verify_steps += [
        "Don't hand over goods or cash until the money shows in your own account. Screenshots can be faked in seconds.",
        "If the buyer says they 'sent extra by mistake' and asks for a refund, check your balance first. It's a common refund scam.",
    ]
    return {
        "status": status,
        "headline": headline,
        "flags": flags,
        "found": {"reference_numbers": utrs, "amounts": [f"₹{a:,.2f}".rstrip("0").rstrip(".") for a in amounts],
                  "dates": [d.strftime("%d %b %Y") for d in sorted(set(dates))]},
        "verify_steps": verify_steps,
        "text": text,
    }
