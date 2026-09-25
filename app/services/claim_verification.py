"""Claim verification: pull out what a message claims and show how to check it independently.

Scam messages make specific claims ("your account will be blocked", "your parcel is
held at customs", "a case is registered against you"). Instead of asking the user to
trust or distrust the message, each claim is paired with the question to answer and
an official way to answer it. Links come only from the list below, never from the
message, and the user is told not to use any number or link the message provides.
"""

import re
from typing import Dict, List, Optional

from app.services.multilingual import english_cues

# Organisations a message may claim to be from, with their official website.
ORGANISATIONS: Dict[str, Dict[str, str]] = {
    "sbi": {"name": "SBI", "url": "https://sbi.co.in", "kind": "bank"},
    "hdfc": {"name": "HDFC Bank", "url": "https://www.hdfcbank.com", "kind": "bank"},
    "icici": {"name": "ICICI Bank", "url": "https://www.icicibank.com", "kind": "bank"},
    "axis": {"name": "Axis Bank", "url": "https://www.axisbank.com", "kind": "bank"},
    "kotak": {"name": "Kotak Mahindra Bank", "url": "https://www.kotak.com", "kind": "bank"},
    "bank of baroda": {"name": "Bank of Baroda", "url": "https://www.bankofbaroda.in", "kind": "bank"},
    "canara": {"name": "Canara Bank", "url": "https://canarabank.com", "kind": "bank"},
    "pnb": {"name": "Punjab National Bank", "url": "https://www.pnbindia.in", "kind": "bank"},
    "paytm": {"name": "Paytm", "url": "https://paytm.com", "kind": "payments"},
    "phonepe": {"name": "PhonePe", "url": "https://www.phonepe.com", "kind": "payments"},
    "google pay": {"name": "Google Pay", "url": "https://pay.google.com", "kind": "payments"},
    "gpay": {"name": "Google Pay", "url": "https://pay.google.com", "kind": "payments"},
    "amazon": {"name": "Amazon", "url": "https://www.amazon.in", "kind": "shop"},
    "flipkart": {"name": "Flipkart", "url": "https://www.flipkart.com", "kind": "shop"},
    "netflix": {"name": "Netflix", "url": "https://www.netflix.com", "kind": "shop"},
    "india post": {"name": "India Post", "url": "https://www.indiapost.gov.in", "kind": "courier"},
    "fedex": {"name": "FedEx", "url": "https://www.fedex.com/en-in", "kind": "courier"},
    "dhl": {"name": "DHL", "url": "https://www.dhl.com/in-en", "kind": "courier"},
    "dtdc": {"name": "DTDC", "url": "https://www.dtdc.in", "kind": "courier"},
    "blue dart": {"name": "Blue Dart", "url": "https://www.bluedart.com", "kind": "courier"},
    "income tax": {"name": "Income Tax Department", "url": "https://www.incometax.gov.in", "kind": "government"},
    "uidai": {"name": "UIDAI (Aadhaar)", "url": "https://uidai.gov.in", "kind": "government"},
    "aadhaar": {"name": "UIDAI (Aadhaar)", "url": "https://uidai.gov.in", "kind": "government"},
    "epfo": {"name": "EPFO", "url": "https://www.epfindia.gov.in", "kind": "government"},
    "trai": {"name": "TRAI", "url": "https://www.trai.gov.in", "kind": "government"},
    "rbi": {"name": "Reserve Bank of India", "url": "https://www.rbi.org.in", "kind": "government"},
    "irctc": {"name": "IRCTC", "url": "https://www.irctc.co.in", "kind": "shop"},
    "cbi": {"name": "CBI", "url": None, "kind": "police"},
    "police": {"name": "Police", "url": None, "kind": "police"},
    "customs": {"name": "Customs", "url": None, "kind": "police"},
    "ncb": {"name": "Narcotics Control Bureau", "url": None, "kind": "police"},
    "court": {"name": "Court", "url": None, "kind": "police"},
    "kbc": {"name": "KBC (Kaun Banega Crorepati)", "url": None, "kind": "prize"},
}

CYBERCRIME = {"label": "National Cyber Crime Reporting Portal", "url": "https://cybercrime.gov.in"}
SANCHAR_SAATHI = {"label": "Sanchar Saathi (report fraud calls / SMS)", "url": "https://sancharsaathi.gov.in"}
SEBI = {"label": "SEBI (check registered advisers and brokers)", "url": "https://www.sebi.gov.in"}
INCOME_TAX = {"label": "Income Tax e-filing portal", "url": "https://www.incometax.gov.in"}

# Each claim type: what to look for, the question to answer, how to check it and a fact to keep in mind.
CLAIM_TYPES: List[Dict] = [
    {
        "id": "account_block",
        "title": "Your account, card or wallet will be blocked",
        "pattern": r"\b(?:account|a/c|netbanking|net banking|card|wallet|yono|khata)\b.{0,60}?\b(?:block\w*|suspend\w*|deactivat\w*|freez\w*|clos\w*|restrict\w*|band)\b"
                   r"|\bwill be (?:blocked|suspended|deactivated|closed|frozen)\b",
        "question": "Is your account really going to be blocked?",
        "verify": [
            "Open your bank's official app or net banking yourself (not from a link) and check your account and any notices.",
            "Or call the customer care number printed on the back of your debit/credit card, or visit your branch.",
        ],
        "fact": "Banks don't block accounts through SMS or WhatsApp warnings with links, and never ask for OTPs or fees to keep an account open.",
        "org_kinds": ["bank", "payments"],
    },
    {
        "id": "kyc_update",
        "title": "Your KYC / PAN / Aadhaar needs updating",
        "pattern": r"\b(?:kyc|pan|aadhaar|aadhar)\b.{0,60}?\b(?:expir\w*|updat\w*|pending|link\w*|verif\w*|incomplete)\b",
        "question": "Is your KYC or PAN–Aadhaar link really pending?",
        "verify": [
            "Check KYC status inside your bank's official app or at your branch. Re-KYC is done in the app or branch, not through links in messages.",
            "Check PAN–Aadhaar linking status yourself on the Income Tax e-filing portal.",
        ],
        "fact": "No bank or government office collects KYC through a link, a phone call or an APK file.",
        "links": [INCOME_TAX],
        "org_kinds": ["bank", "payments", "government"],
    },
    {
        "id": "prize",
        "title": "You have won a prize, lottery or gift",
        "pattern": r"\b(?:you (?:have )?won|winner|lottery|lucky draw|jackpot|selected for|congratulations|free gift|reward of)\b",
        "question": "Did you actually enter this contest, and is the organiser real?",
        "verify": [
            "Ask yourself whether you ever entered it. You can't win a lottery or draw you didn't take part in.",
            "Check the company's official website or verified social media page for the contest. Don't use contact details from the message.",
        ],
        "fact": "Genuine prizes never ask you to pay a fee, tax or 'processing charge' to receive them.",
        "org_kinds": ["prize", "shop"],
    },
    {
        "id": "parcel_held",
        "title": "Your parcel is held, undelivered or stuck at customs",
        "pattern": r"\b(?:parcel|package|shipment|courier|consignment|delivery)\b.{0,60}?\b(?:held|hold|customs|pending|undeliver\w*|incomplete address|re-?deliver\w*|seiz\w*|return\w*)\b",
        "question": "Are you really expecting this parcel, and is it really held?",
        "verify": [
            "Track it on the courier's official website or app using the tracking number from your own order confirmation.",
            "If you didn't order anything, there is nothing to pay or update.",
        ],
        "fact": "Couriers and customs don't collect duty or 're-delivery fees' through personal UPI IDs or links in SMS.",
        "org_kinds": ["courier", "shop"],
    },
    {
        "id": "refund",
        "title": "A refund, cashback or reward is waiting for you",
        "pattern": r"\b(?:refund|cashback|reward points?|redeem|subsidy|overpayment)\b",
        "question": "Is there really a refund or reward due to you?",
        "verify": [
            "Open the official app or website of the company yourself and check your orders, refunds or reward balance.",
            "Check your bank statement for any genuine credit.",
        ],
        "fact": "Receiving money never needs your UPI PIN, OTP, card details or scanning a QR code.",
        "org_kinds": ["shop", "bank", "payments", "government"],
    },
    {
        "id": "power_cut",
        "title": "Your electricity will be disconnected",
        "pattern": r"\b(?:electricity|power|bijli|light)\b.{0,60}?\b(?:disconnect\w*|cut|off tonight)\b",
        "question": "Is your electricity bill really unpaid?",
        "verify": [
            "Check your bill status in your electricity board's official app or website, or on your last paper bill.",
            "Call the customer care number printed on your bill, not a number from the message.",
        ],
        "fact": "Electricity boards send written notices with due dates; they don't ask you to call an 'officer's' mobile number tonight.",
    },
    {
        "id": "legal_case",
        "title": "Police, CBI, customs or a court have a case against you",
        "pattern": r"\b(?:police|cbi|court|arrest\w*|warrant|digital arrest|case (?:is )?(?:registered|filed)|money laundering|narcotics|ncb|drugs|fir)\b",
        "question": "Is there really a case against you?",
        "verify": [
            "Hang up. Call 112 or visit your nearest police station in person to ask whether any case exists.",
            "Tell a family member. Real investigations don't require secrecy from your family.",
        ],
        "fact": "There is no 'digital arrest' in Indian law. Police and agencies never question or arrest anyone over video call or ask for money to settle a case.",
        "links": [CYBERCRIME],
        "org_kinds": ["police"],
    },
    {
        "id": "sim_block",
        "title": "Your SIM or mobile number will be blocked",
        "pattern": r"\b(?:sim|mobile number|phone number|number)\b.{0,60}?\b(?:block\w*|disconnect\w*|deactivat\w*|suspend\w*|band)\b",
        "question": "Is your mobile number really going to be disconnected?",
        "verify": [
            "Check with your telecom operator through its official app, store or the customer care number on its website.",
        ],
        "fact": "TRAI regulates telecom companies; it does not disconnect individual numbers or call people to do so.",
        "links": [SANCHAR_SAATHI],
        "org_kinds": ["government"],
    },
    {
        "id": "tax",
        "title": "You have a tax refund, dues or penalty",
        "pattern": r"\b(?:income tax|tax refund|tax dues|gst|penalty|it department)\b",
        "question": "Do you really have a tax refund or dues?",
        "verify": ["Log in to the Income Tax e-filing portal yourself and check refund status and any notices under your account."],
        "fact": "Tax refunds go straight to the bank account already linked to your PAN; nobody needs your card details or a fee to release them.",
        "links": [INCOME_TAX],
        "org_kinds": ["government"],
    },
    {
        "id": "job",
        "title": "You have been offered a job or paid tasks",
        "pattern": r"\b(?:job|hiring|part[- ]time|work from home|salary|shortlisted|daily income|tasks?)\b",
        "question": "Is this job offer real?",
        "verify": [
            "Look for the job on the company's official careers page, and contact the company through its official website.",
        ],
        "fact": "Real employers never ask for a registration fee, deposit or 'task' payment before you start.",
    },
    {
        "id": "investment",
        "title": "Guaranteed or unusually high investment returns",
        "pattern": r"\b(?:guaranteed|assured|double your money|\d+% (?:profit|return)s?|daily profit|ipo allotment|trading|crypto|stock tips)\b",
        "question": "Is this adviser or platform registered, and are the returns realistic?",
        "verify": [
            "Check whether the adviser or broker is registered on SEBI's website.",
            "Treat any 'guaranteed' return as a warning sign; real investments carry risk.",
        ],
        "fact": "Fake trading apps show fake profits, then demand 'tax' or 'fees' before you can withdraw.",
        "links": [SEBI],
    },
    {
        "id": "sent_by_mistake",
        "title": "Someone sent you money by mistake",
        "pattern": r"\b(?:by mistake|wrongly (?:sent|credited|transferred)|sent (?:it )?to (?:your|the wrong)|accidentally sent)\b",
        "question": "Did any money actually arrive in your account?",
        "verify": [
            "Check your own bank app or statement. Screenshots and SMS can be faked.",
            "If money really did arrive, ask your bank to reverse it. Don't send money back yourself.",
        ],
        "fact": "The 'sent by mistake, please return' request is a common refund scam.",
    },
    {
        "id": "family_emergency",
        "title": "A family member or friend urgently needs money",
        "pattern": r"\b(?:new number|phone (?:broke|is broken|lost)|my (?:old )?phone|in trouble|accident|hospital|stuck at)\b",
        "question": "Is this really your family member or friend?",
        "verify": [
            "Call them on the number you already have saved, or ask another family member.",
            "Ask a question only the real person would know.",
        ],
        "fact": "Scammers pretend to be relatives using new numbers and urgency so you don't have time to check.",
    },
    {
        "id": "loan",
        "title": "A loan has been approved for you",
        "pattern": r"\b(?:loan|pre-?approved|credit limit)\b.{0,60}?\b(?:approved|sanction\w*|disburs\w*|processing fee|file charge)\b",
        "question": "Did you apply for this loan, and is the lender genuine?",
        "verify": [
            "Check loan offers only inside your own bank's official app or at the branch.",
        ],
        "fact": "Be very wary of any lender that asks for a fee before paying out the loan.",
    },
]

for _claim in CLAIM_TYPES:
    _claim["regex"] = re.compile(_claim["pattern"], re.IGNORECASE)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def _organisations(text: str) -> List[Dict]:
    lowered = text.lower()
    found, seen = [], set()
    for key, org in ORGANISATIONS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", lowered) and org["name"] not in seen:
            seen.add(org["name"])
            found.append(org)
    return found


ABOUT_YOU = re.compile(r"\b(?:you|your|yours|aapka|aapke|unga|ungal)\b|आपका|आपके|உங்கள்", re.IGNORECASE)


def _claim_sentence(text: str, regex: re.Pattern) -> str:
    """The sentence that makes the claim, preferring one that says something about the reader."""
    best, best_score = None, 0
    for sentence in SENTENCE_SPLIT.split(text):
        hits = len(regex.findall(sentence)) or len(regex.findall(english_cues(sentence)))
        if not hits:
            continue
        score = hits + (1 if ABOUT_YOU.search(sentence) else 0)
        if score > best_score:
            best, best_score = sentence, score
    return (best or " ".join(text.split())).strip()[:220]


def extract_claims(text: str, max_claims: int = 4) -> List[Dict]:
    """Claims the message makes, each with how to verify it through an official source."""
    if not text or not text.strip():
        return []
    searchable = f"{text} {english_cues(text)}"
    orgs = _organisations(searchable)
    claims: List[Dict] = []
    for claim in CLAIM_TYPES:
        if not claim["regex"].search(searchable):
            continue
        relevant = [o for o in orgs if o["kind"] in claim.get("org_kinds", [])]
        claimed_by: Optional[Dict] = relevant[0] if relevant else None
        links = []
        if claimed_by and claimed_by.get("url"):
            links.append({"label": f"{claimed_by['name']} official website", "url": claimed_by["url"]})
        links += [l for l in claim.get("links", []) if l["url"] not in {x["url"] for x in links}]
        claims.append({
            "type": claim["id"],
            "title": claim["title"],
            "claim": _claim_sentence(text, claim["regex"]),
            "claimed_by": claimed_by["name"] if claimed_by else None,
            "question": claim["question"],
            "how_to_verify": claim["verify"],
            "fact": claim["fact"],
            "official_links": links,
        })
        if len(claims) >= max_claims:
            break
    return claims
