"""Pause Before You Pay: interrupt high-risk moments with a short verification checklist.

Scams work by rushing people. When a scan is rated SCAM (or a number / UPI ID has
been reported by several users) the app stops the user with a clear warning, a
10-second cooling-off period and a checklist of things that must be true before
paying. Checklist items that this particular message contradicts are marked with
the reason, so the user sees exactly which "safe to pay" condition fails.
"""

from typing import Dict, Iterable, List, Optional

WAIT_SECONDS = 10

# Each item: what the user must be able to confirm, and which findings contradict it.
CHECKLIST = [
    {
        "id": "known_contact",
        "text": "I know this person or company, and I contacted them myself on a number or app I already had.",
        "contradicted_by": {
            "RULE_SENDER_DOMAIN_MISMATCH": "The message's link doesn't belong to the organisation it names.",
            "RULE_FREE_EMAIL_SENDER": "An 'official' sender is using a free email account.",
            "RULE_UNVERIFIED_CONTACT_NUMBER": "It asks you to contact a number given in the message itself.",
            "RULE_DECEPTIVE_LINK": "Its link is disguised to hide where it really goes.",
            "RULE_COMMUNITY_REPORTED": "Other users have reported details in this message as used by scammers.",
        },
        "claims": {"family_emergency": "It claims to be a relative on a new number. Call them on the number you already have."},
    },
    {
        "id": "verified_claim",
        "text": "I checked the claim through the official app, website or branch, not through the message's link or number.",
        "contradicted_by": {
            "RULE_KYC_EXPIRY_SCARE": "It pushes you to update KYC or unblock an account through the message.",
            "RULE_OBFUSCATED_URL": "It relies on a shortened or high-risk link.",
        },
    },
    {
        "id": "no_fee_to_receive",
        "text": "I'm not paying a fee, tax or deposit to receive money, a prize, a refund, a loan or a job.",
        "contradicted_by": {
            "RULE_LOTTERY_ADVANCE_FEE": "It asks for a fee to release a prize.",
            "RULE_JOB_TASK_FRAUD": "It asks for a deposit to start a job or tasks.",
            "RULE_QR_RECEIVE_FRAUD": "It asks you to scan a QR code or enter a PIN to 'receive' money. That only sends money out.",
            "RULE_CRYPTO_PONZI_PROMISE": "It promises guaranteed returns in exchange for money.",
        },
        "claims": {
            "prize": "It says you won something but wants money first.",
            "loan": "It asks for a fee before a loan is paid out.",
            "sent_by_mistake": "It asks you to 'return' money. Check your own bank app first.",
        },
    },
    {
        "id": "no_codes",
        "text": "Nobody has asked me for an OTP, UPI PIN, card number or password, or to install an app.",
        "contradicted_by": {
            "RULE_CREDENTIAL_SOLICITATION": "It asks for an OTP, PIN or password.",
            "RULE_BANK_DETAILS_REQUEST": "It asks for bank or card details.",
            "RULE_REMOTE_DESKTOP_ACCESS": "It asks you to install a screen-sharing app.",
        },
    },
    {
        "id": "no_pressure",
        "text": "I'm not being threatened, rushed or told to keep this secret.",
        "contradicted_by": {
            "RULE_DIGITAL_ARREST": "It's a fake police / 'digital arrest' threat.",
            "RULE_AUTHORITY_INTIMIDATION": "It threatens you in the name of an authority.",
            "RULE_FALSE_URGENCY": "It rushes you with a deadline.",
        },
        "claims": {"legal_case": "It claims there is a case against you. Real police don't settle cases for money."},
    },
]


def build_pause(verdict: str, rule_ids: Iterable[str], claim_types: Iterable[str] = (),
                category_title: Optional[str] = None) -> Optional[Dict]:
    """Pause screen for a SCAM verdict, or None when no pause is needed."""
    if verdict != "SCAM":
        return None
    rules, claims = set(rule_ids), set(claim_types)
    checklist: List[Dict] = []
    for item in CHECKLIST:
        warnings = [reason for rule, reason in item["contradicted_by"].items() if rule in rules]
        warnings += [reason for claim, reason in item.get("claims", {}).items() if claim in claims]
        checklist.append({"id": item["id"], "text": item["text"], "warning": warnings[0] if warnings else None})
    failing = sum(1 for c in checklist if c["warning"])
    what = f"This looks like {category_title}." if category_title else "This message has strong signs of a scam."
    return {
        "title": "Pause before you pay",
        "message": f"{what} {failing} of the {len(checklist)} safety checks below fail for this message. "
                   "Don't send money, share codes or click links until every item is true.",
        "checklist": checklist,
        "failing_checks": failing,
        "wait_seconds": WAIT_SECONDS,
    }


def build_lookup_pause(identifier: str, report_count: int) -> Dict:
    """Pause screen before paying a number / UPI ID that several users have reported."""
    checklist = [{"id": item["id"], "text": item["text"], "warning": None} for item in CHECKLIST]
    checklist[0]["warning"] = f"{identifier} has been reported {report_count} times by other users."
    return {
        "title": "Pause before you pay",
        "message": f"{identifier} has been reported as used by scammers. Don't pay it until you have confirmed "
                   "who it belongs to through a channel you already trust.",
        "checklist": checklist,
        "failing_checks": 1,
        "wait_seconds": WAIT_SECONDS,
    }
