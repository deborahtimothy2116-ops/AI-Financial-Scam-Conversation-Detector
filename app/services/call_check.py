"""Live call check: assess a phone or video call from a few yes/no answers.

The most damaging scams (fake police "digital arrest", fake bank officers, OTP and
remote-access calls) happen on calls, so there is no message to paste. The person
answers what the caller is saying or asking for, and gets a verdict, what to say,
and what to do next, while still on the call.
"""

from typing import Dict, List

# id, question, weight, and whether a "yes" alone is enough to call it a scam
QUESTIONS: List[Dict] = [
    {"id": "otp_pin", "weight": 45, "decisive": True,
     "text": "Are they asking for an OTP, UPI PIN, CVV, card number or password?",
     "why": "No bank, company or officer ever needs these. Anyone asking is trying to take your money."},
    {"id": "remote_app", "weight": 45, "decisive": True,
     "text": "Have they asked you to install an app (AnyDesk, TeamViewer, QuickSupport) or open an APK file?",
     "why": "These apps give the caller control of your phone, including your banking apps."},
    {"id": "secrecy", "weight": 35, "decisive": True,
     "text": "Have they told you to stay on the call or video call, or not to tell your family?",
     "why": "Isolation is the core tactic of 'digital arrest' scams. Real officials never ask for secrecy."},
    {"id": "pay_transfer", "weight": 40, "decisive": True,
     "text": "Are they asking you to pay, move money to a 'safe' or 'verification' account, or scan a QR code?",
     "why": "No agency or bank asks you to move money to protect it. Scanning a QR code only sends money out."},
    {"id": "threat", "weight": 30, "decisive": False,
     "text": "Are they threatening arrest, a police case, account or SIM block, or power disconnection?",
     "why": "Threats are used to make you panic and stop checking."},
    {"id": "authority", "weight": 25, "decisive": False,
     "text": "Do they say they are from the police, CBI, customs, a court, TRAI, RBI or another government agency?",
     "why": "Impersonating officials is common. Agencies send written notices; they don't demand action on a call."},
    {"id": "video_uniform", "weight": 20, "decisive": False,
     "text": "Is it a video call showing a uniform, a police station, an office or an ID card?",
     "why": "Uniforms, backdrops and ID cards on video are easy to fake."},
    {"id": "bank_company", "weight": 15, "decisive": False,
     "text": "Do they say they are from your bank, card company, a payment app or a company like Amazon?",
     "why": "Callers can fake caller ID and know personal details. Call back on the official number yourself."},
    {"id": "offer", "weight": 20, "decisive": False,
     "text": "Are they offering a prize, refund, cashback, loan, job or high investment returns?",
     "why": "Offers you didn't ask for are the hook; the fee or 'verification' comes next."},
    {"id": "they_called", "weight": 10, "decisive": False,
     "text": "Did they call you first (you did not call them)?",
     "why": "Unexpected calls about money or legal trouble deserve extra caution."},
]
QUESTION_IDS = {q["id"] for q in QUESTIONS}


def _scam_type(yes: set) -> str:
    if "authority" in yes and yes & {"threat", "secrecy", "video_uniform", "pay_transfer"}:
        return "Fake police / 'digital arrest' call"
    if "remote_app" in yes:
        return "Remote-access takeover call"
    if "bank_company" in yes and yes & {"otp_pin", "pay_transfer", "threat"}:
        return "Fake bank / company officer call"
    if "offer" in yes and yes & {"pay_transfer", "otp_pin"}:
        return "Prize / refund / job fee call"
    if "otp_pin" in yes:
        return "OTP theft call"
    return "Suspicious call"


def assess_call(answers: Dict[str, bool]) -> Dict:
    """Score the answers and return a verdict, reasons, what to say and what to do."""
    yes = {qid for qid, value in answers.items() if value and qid in QUESTION_IDS}
    score = min(100, sum(q["weight"] for q in QUESTIONS if q["id"] in yes))
    if any(q["decisive"] for q in QUESTIONS if q["id"] in yes):
        score = max(score, 80)
    verdict = "SCAM" if score >= 60 else "SUSPICIOUS" if score >= 30 else "SAFE"
    reasons = [{"question": q["text"], "why": q["why"], "weight": q["weight"]} for q in QUESTIONS if q["id"] in yes]
    scam_type = _scam_type(yes) if verdict != "SAFE" else None

    if verdict == "SCAM":
        headline = "Hang up now. This call has the signs of a scam."
        say_this = "\"I don't share OTPs or make payments on calls. I will contact the office myself on its official number.\" Then disconnect."
    elif verdict == "SUSPICIOUS":
        headline = "Be careful. Don't share anything or pay while on this call."
        say_this = "\"Please send this in writing. I will call back on the official number.\" Then disconnect and check independently."
    else:
        headline = "No major warning signs so far."
        say_this = "Still never share an OTP, PIN or password, and hang up if they ask for money or secrecy."

    do_now: List[str] = []
    if verdict != "SAFE":
        do_now.append("Disconnect the call. Don't call back on the same number.")
    if "authority" in yes or "video_uniform" in yes:
        do_now.append("Police, CBI and courts never arrest or question anyone over a video call, and there is no 'digital arrest'. Tell a family member what happened.")
    if "bank_company" in yes:
        do_now.append("Call your bank using the number printed on your card or in its official app.")
    if "remote_app" in yes:
        do_now.append("Uninstall the app they asked for and turn off mobile data and Wi-Fi until the phone is checked.")
    if yes & {"otp_pin", "pay_transfer", "remote_app"}:
        do_now.append("If you already shared a code or paid, call 1930 immediately and block your card/UPI through your bank.")
    if verdict != "SAFE":
        do_now.append("Report the number on Sanchar Saathi (Chakshu) and in ScamShield's Check number / UPI page.")

    return {
        "verdict": verdict,
        "score": score,
        "headline": headline,
        "scam_type": scam_type,
        "reasons": reasons,
        "say_this": say_this,
        "do_now": do_now,
        "answered_yes": sorted(yes),
    }
