"""Practice messages for the Spot-the-Scam quiz.

Each item has the expected verdict and a one-line lesson. The test suite checks
that the detector agrees with every expected verdict, so the quiz never teaches
something the engine itself would get wrong.
"""

QUIZ_BANK = [
    {
        "id": "q01", "channel": "SMS", "sender": "VM-SBIUPD",
        "message": "Dear Customer, your SBI YONO account will be blocked today. Update PAN immediately at sbi-yono-kyc.xyz/update",
        "answer": "SCAM",
        "lesson": "Banks never send KYC links by SMS, and 'sbi-yono-kyc.xyz' is not an SBI domain. Update KYC only inside the official app or at a branch.",
    },
    {
        "id": "q02", "channel": "SMS", "sender": "AX-AMAZON",
        "message": "Your Amazon order #405-2291 has been delivered. Rate your experience at https://www.amazon.in/review",
        "answer": "SAFE",
        "lesson": "An ordinary delivery update that links to the real amazon.in domain and asks for nothing sensitive.",
    },
    {
        "id": "q03", "channel": "WhatsApp", "sender": "+91 70XXX 11234",
        "message": "Hello sir, I saw your OLX ad. I will pay advance. Please scan this QR code to receive Rs 15,000 in your account.",
        "answer": "SCAM",
        "lesson": "You never scan a QR code or enter a UPI PIN to RECEIVE money. Scanning only sends money out.",
    },
    {
        "id": "q04", "channel": "Email", "sender": "Income Tax Dept <refunds.itd@gmail.com>",
        "message": "Income Tax refund of Rs 18,450 approved. Share your bank account number and IFSC to receive the refund within 24 hours.",
        "answer": "SCAM",
        "lesson": "Government departments don't email from Gmail, and refunds go to the account already on your tax return.",
    },
    {
        "id": "q05", "channel": "WhatsApp", "sender": "Priya (saved contact)",
        "message": "Hey! Are we still on for lunch tomorrow at 1? I'll book the table.",
        "answer": "SAFE",
        "lesson": "A normal message from a known contact with no links, money or pressure.",
    },
    {
        "id": "q06", "channel": "Telegram", "sender": "HR Team - Remote Jobs",
        "message": "Part time job! Earn Rs 5000 daily by liking YouTube videos. Small deposit of Rs 1,000 needed to start tasks.",
        "answer": "SCAM",
        "lesson": "Real jobs never ask you to pay to start. 'Like videos and earn' schemes end with bigger 'deposits' you never get back.",
    },
    {
        "id": "q07", "channel": "SMS", "sender": "+91 98XXX 45012",
        "message": "Hi, this is your cousin's friend Ravi. Can you send me Rs 2,000 on GPay? I'll return it tomorrow.",
        "answer": "SUSPICIOUS",
        "lesson": "Maybe genuine, maybe not. A money request from an unknown number: call your cousin on a number you already have before paying.",
    },
    {
        "id": "q08", "channel": "SMS", "sender": "VK-ELECTB",
        "message": "Dear consumer, your electricity power will be disconnected tonight at 9:30 PM because previous month bill was not updated. Call officer 9876543210 immediately.",
        "answer": "SCAM",
        "lesson": "Power companies send notices with a due date, not a same-night cut-off and a personal mobile number to call.",
    },
    {
        "id": "q09", "channel": "Email", "sender": "PayPal <service@pаypal.com>",
        "message": "Unusual sign-in detected. Confirm your identity at https://pаypal.com/signin to avoid suspension.",
        "answer": "SCAM",
        "lesson": "The 'а' in this pаypal.com is a Cyrillic letter: the address only looks like PayPal. Type the address yourself or use the app.",
    },
    {
        "id": "q10", "channel": "WhatsApp", "sender": "Crypto Mentor Anjali",
        "message": "Join our VIP trading group. Guaranteed 30% profit every week. Invest Rs 10,000 now and double your money.",
        "answer": "SCAM",
        "lesson": "Guaranteed high returns don't exist. This is how investment and 'pig-butchering' scams start.",
    },
    {
        "id": "q11", "channel": "SMS", "sender": "JD-HDFCBK",
        "message": "Rs 1,250.00 debited from a/c **4321 on 24-09 to SWIGGY. Not you? Call the number on the back of your card.",
        "answer": "SAFE",
        "lesson": "A standard transaction alert: no link, no request, and it tells you to use the number on your own card.",
    },
    {
        "id": "q12", "channel": "SMS", "sender": "+91 63XXX 90871",
        "message": "Congratulations! You have won a Rs 25 lakh KBC lottery. Pay Rs 8,500 processing fee to claim your prize.",
        "answer": "SCAM",
        "lesson": "You can't win a lottery you never entered, and real prizes never charge a fee to release them.",
    },
    {
        "id": "q13", "channel": "Email", "sender": "Apple Support <support@apple.com.account-verify.shop>",
        "message": "Your Apple ID has been locked. Verify now: https://apple.com.account-verify.shop/unlock",
        "answer": "SCAM",
        "lesson": "Read the end of the address: this is 'account-verify.shop' with 'apple.com' pasted in front of it.",
    },
    {
        "id": "q14", "channel": "WhatsApp video call", "sender": "+91 89XXX 20417 (profile photo: police logo)",
        "message": "This is CBI. A parcel containing drugs was booked on your Aadhaar. You are under digital arrest. Stay on the video call, do not tell your family, and transfer your savings to the RBI verification account.",
        "answer": "SCAM",
        "lesson": "There is no 'digital arrest' in Indian law. Police and CBI never arrest over video calls or ask you to move money. Hang up and call 1930.",
    },
]

QUIZ_BY_ID = {q["id"]: q for q in QUIZ_BANK}


def quiz_analysis_text(question: dict) -> str:
    """The text the detector analyses for a quiz item: sender line plus message."""
    return f"From: {question['sender']}\n{question['message']}"
