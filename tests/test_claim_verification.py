"""Tests for claim extraction and official-source verification guidance."""

import pytest
from fastapi.testclient import TestClient

from app.services.claim_verification import ORGANISATIONS, extract_claims

OFFICIAL_URLS = {o["url"] for o in ORGANISATIONS.values() if o["url"]} | {
    "https://cybercrime.gov.in", "https://sancharsaathi.gov.in", "https://www.sebi.gov.in", "https://www.incometax.gov.in",
}


def types(message):
    return [c["type"] for c in extract_claims(message)]


@pytest.mark.parametrize(
    "message, expected",
    [
        ("URGENT! Your SBI account will be blocked today. Update your KYC at sbi-kyc-update.xyz/login", ["account_block", "kyc_update"]),
        ("India Post: Your package could not be delivered due to incomplete address. Update within 12 hours.", ["parcel_held"]),
        ("Congratulations! You have won Rs 25 lakh in the KBC lucky draw. Pay the processing fee.", ["prize"]),
        ("Your electricity will be disconnected tonight. Call the officer.", ["power_cut"]),
        ("TRAI: Your mobile number will be blocked in 2 hours.", ["sim_block"]),
        ("Hi, I sent Rs 5,000 to your number by mistake. Please return it.", ["sent_by_mistake"]),
        ("Hi Mom, this is my new number, my phone broke. Send money urgently.", ["family_emergency"]),
        ("Guaranteed 30% profit every week. Invest now.", ["investment"]),
    ],
)
def test_claims_are_extracted(message, expected):
    assert set(expected) <= set(types(message))


def test_claim_quotes_the_sentence_about_the_reader():
    (claim,) = [c for c in extract_claims(
        "This is Mumbai Police Crime Branch. A parcel containing drugs was found in your name. You are under digital arrest."
    ) if c["type"] == "legal_case"]
    assert claim["claim"] == "A parcel containing drugs was found in your name."
    assert "digital arrest" in claim["fact"]


def test_claimed_organisation_gets_its_official_site_never_the_message_link():
    (claim, *_) = extract_claims("Your SBI account will be blocked today. Verify at https://sbi-secure-login.xyz")
    assert claim["claimed_by"] == "SBI"
    urls = [l["url"] for l in claim["official_links"]]
    assert urls[0] == "https://sbi.co.in"
    assert "sbi-secure-login.xyz" not in " ".join(urls)


def test_all_links_come_from_the_official_list():
    messages = [
        "Your HDFC netbanking is blocked, update KYC at bit.ly/x",
        "Income tax refund of Rs 15,490 approved, click here",
        "CBI: a case is registered against you, join the video call",
        "FedEx: your parcel is held at customs, pay Rs 49",
    ]
    for message in messages:
        for claim in extract_claims(message):
            assert {l["url"] for l in claim["official_links"]} <= OFFICIAL_URLS


def test_hindi_claims_are_extracted():
    assert "account_block" in types("आपका बैंक खाता आज बंद हो जाएगा। केवाईसी के लिए तुरंत ओटीपी बताएं।")


@pytest.mark.parametrize("message", [
    "Hey, are we still meeting for lunch tomorrow at 1?",
    "482913 is your OTP for transaction of Rs 1,250.00 at AMAZON on HDFC Bank card XX4321. Do not share it with anyone.",
])
def test_ordinary_messages_have_no_claims(message):
    assert extract_claims(message) == []


def test_claims_are_returned_with_scan_results(client: TestClient):
    data = client.post("/api/v1/analyze/message", json={"message": "Your SBI account will be blocked today. Update KYC now."}).json()["data"]
    assert data["claims"][0]["question"] == "Is your account really going to be blocked?"
    assert data["claims"][0]["how_to_verify"]
