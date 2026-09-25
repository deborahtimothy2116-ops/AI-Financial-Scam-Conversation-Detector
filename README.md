# 🛡️ ScamShield AI - AI Financial Scam Conversation Detector

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ScamShield AI** is an intelligent, defensive cybersecurity system engineered to detect and prevent financial fraud from suspicious SMS, WhatsApp, social media messages, and screenshot uploads **BEFORE** the victim makes a payment, scans a deceptive QR code, or shares authentication credentials.

---

## 📌 Problem Statement

Financial conversational fraud (UPI payment traps, fake bank KYC account suspension notices, electricity bill cutoff scams, part-time job task deposits, and fake lucky draws) accounts for billions of dollars in losses annually. Fraudsters exploit psychological manipulation, artificial deadlines, and spoofed bank branding to force rapid transactions before victims can verify authenticity.

## 💡 Solution

ScamShield AI provides real-time, explainable fraud intelligence:
1. **Pasting Suspicious Text Messages**: Instant multilingual analysis for SMS, WhatsApp, and email messages.
2. **Uploading Chat Screenshots**: Tesseract OCR extraction with automated contrast enhancement to parse conversations from regional mobile captures.
3. **Multi-Factor Risk Scoring Engine**: Calibrated combination of heuristic rule signals, multi-provider AI evaluation, indicator severity weights, and payment entities.
4. **Explainable Scam Deconstruction**: Plain-language explanations in English & Tamil breaking down *why* a message is suspicious.
5. **Actionable Safety Recommendations**: Step-by-step guidance, PIN protection reminders, and direct emergency routing to national cybercrime helplines (**1930**).

---

## 🎨 Google Stitch Frontend Integration

The user interface was designed in **Google Stitch** (Project ID: `2517293446067344339`) and serves as the visual and interaction source of truth.

### Integrated Stitch Screens:
- **Home Dashboard (`home.html`)**: Live threat banner, neural radar telemetry simulation, quick analyzer tabs, metrics counter, and pre-built judge demo cards.
- **Analyze Message (`analyze_message.html`)**: Text input area with PII sanitization status, demo pre-fill triggers, language selectors (`Auto`, `English`, `தமிழ்`), and evaluation telemetry.
- **Upload Screenshot (`upload_screenshot.html`)**: Drag-and-drop OCR dropzone, file type/size validation, and multi-format parser (`PNG`, `JPG`, `WEBP`).
- **Analysis Processing (`processing.html`)**: Animated radial progress dial with sequential 5-step pipeline loading.
- **Dynamic Result Verdict Cards (`result_high.html`, `result_medium.html`, `result_low.html`)**:
  - `HIGH / CRITICAL Risk`: Red-tier alert banner, radial 0–100 risk gauge, extracted trigger chips, and instant **Helpline 1930** button.
  - `MEDIUM Risk`: Amber caution banner, warning badges, and sender verification guidelines.
  - `LOW / SAFE Risk`: Emerald clean status with safe hygiene recommendations.
- **Scan History (`history.html` & `history_detail.html`)**: Filterable timeline (All, High, Medium, Low), live search, per-user data isolation, and report inspection.
- **Settings & Privacy (`settings.html`)**: Model status, OCR configuration, API base URL override, and privacy toggles.

---

## 🏗️ Architecture & Clean Code Structure

```
AI-Financial-Scam-Conversation-Detector/
├── app/
│   ├── main.py                     # FastAPI application entrypoint & static mount
│   ├── api/
│   │   ├── auth.py                 # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── analysis.py             # POST /analyze/message, POST /analyze/image, GET /analyze/{id}
│   │   ├── history.py              # GET /history, GET /history/{id}, DELETE /history/{id}
│   │   ├── health.py               # GET /health, GET /ping, GET /api/v1/health
│   │   └── deps.py                 # Database & JWT auth dependency injection
│   ├── core/
│   │   ├── config.py               # Pydantic v2 settings & environment variables
│   │   ├── security.py             # Password hashing (bcrypt) & JWT tokens
│   │   ├── logging.py              # Log sanitization & structured logging
│   │   └── exceptions.py           # Domain exception classes & error handlers
│   ├── models/
│   │   ├── user.py                 # User SQLAlchemy model
│   │   ├── analysis.py             # Analysis SQLAlchemy model
│   │   ├── indicator.py            # Indicator SQLAlchemy model
│   │   ├── recommendation.py       # Recommendation SQLAlchemy model
│   │   └── feedback.py             # Feedback accuracy model
│   ├── schemas/
│   │   ├── auth.py                 # Registration & token Pydantic schemas
│   │   ├── analysis.py             # Section 8 result contract schemas
│   │   ├── history.py              # Paginated history schemas
│   │   └── common.py               # APIResponse & ErrorResponse envelope
│   ├── services/
│   │   ├── text_preprocessor.py    # Entity extraction (UPI, URLs, phones, crypto, tools)
│   │   ├── language_service.py     # Multilingual detection (Tamil Unicode, Hinglish, English)
│   │   ├── llm_service.py          # Provider-independent AI abstraction (OpenAI, Gemini, Anthropic, Rules)
│   │   ├── risk_engine.py          # Calibrated multi-factor risk scoring engine
│   │   ├── ocr_service.py          # Tesseract OCR with adaptive contrast pre-processing
│   │   ├── explanation_service.py  # Plain-language English & Tamil breakdown generator
│   │   ├── recommendation_service.py # Actionable safety guidance & helpline provider
│   │   └── scam_detector.py        # End-to-end pipeline orchestrator
│   ├── repositories/
│   │   ├── user_repository.py      # User persistence
│   │   └── analysis_repository.py  # Analysis & history query repository
│   └── utils/
│       ├── constants.py            # Scam categories, risk levels, regex patterns
│       └── validators.py           # Text & image upload validation
├── frontend/
│   ├── index.html                  # Single Page Application matching Stitch UI
│   ├── app.js                      # Vanilla JS API Client & controller
│   ├── tailwind.css                # Compiled Tailwind stylesheet (no CDN needed)
│   └── tailwind.config.js          # Design tokens from the Stitch screens
├── frontend_screens/               # Original Google Stitch screen exports (design reference)
├── tests/
│   ├── conftest.py                 # Pytest test fixtures & in-memory SQLite setup
│   ├── test_analysis.py            # Message analysis & demo test cases
│   ├── test_auth.py                # Registration, login & profile tests
│   ├── test_history.py             # History pagination, detail & cross-user isolation tests
│   ├── test_screenshot_analysis.py # Screenshot upload and OCR mock tests
│   ├── test_services.py            # Unit tests for risk engine, preprocessor & language
│   └── test_health.py              # Health check & system diagnostics tests
├── Dockerfile                      # Production Docker container definition
├── docker-compose.yml              # Multi-container orchestration (Backend + PostgreSQL)
├── requirements.txt                # Python package dependencies
├── .env.example                    # Environment configuration template
└── README.md                       # Complete documentation
```

---

## ⚡ API Endpoints

All endpoints are documented via Swagger UI at `/docs` or ReDoc at `/redoc`.

### Authentication
| Method | Endpoint | Description | Protected |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account | No |
| `POST` | `/api/v1/auth/login` | User login (returns JWT access token) | No |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Yes (Bearer) |

### Scam Analysis
| Method | Endpoint | Description | Payload |
|---|---|---|---|
| `POST` | `/api/v1/analyze/message` | Analyze suspicious message | `{"message": "...", "language": "auto"}` |
| `POST` | `/api/v1/analyze/image` | Upload screenshot for OCR analysis | `multipart/form-data` with image file |
| `GET` | `/api/v1/analyze/{analysis_id}` | Fetch past analysis report by ID | Path parameter |

### History & Analytics (User Isolated)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/history` | Get paginated user history with risk filters |
| `GET` | `/api/v1/history/{analysis_id}` | Get specific analysis detail (Authorized user only) |
| `DELETE` | `/api/v1/history/{analysis_id}` | Delete specific scan record |
| `DELETE` | `/api/v1/history/clear` | Clear all scan records for user |
| `GET` | `/api/v1/history/stats` | Aggregated scan analytics |

### System Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health check (Database, OCR, LLM) |
| `GET` | `/ping` | Liveness probe |
| `GET` | `/api/v1/health` | Health check alias |

---

## 📊 Standard API Response Contract (Section 8)

```json
{
  "success": true,
  "data": {
    "analysis_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "input_type": "message",
    "language": {
      "code": "en",
      "confidence": 0.98
    },
    "risk": {
      "score": 87.0,
      "level": "HIGH",
      "confidence": 0.95,
      "rule_score": 87.0,
      "ai_score": 87.0
    },
    "scam": {
      "potential_scam": true,
      "category": "fake_kyc",
      "category_label": "Fake KYC / Bank Impersonation"
    },
    "indicators": [
      {
        "type": "urgent_language",
        "title": "Artificial Urgency & Time Pressure",
        "severity": "HIGH",
        "evidence": "Your account will be blocked today."
      },
      {
        "type": "payment_request",
        "title": "Unsolicited Fee / Payment Request",
        "severity": "HIGH",
        "evidence": "Send ₹2,000 to complete KYC"
      }
    ],
    "explanation": "⚠️ HIGH RISK ALERT: This message matches known patterns of Fake KYC / Bank Impersonation.\n\nWhy this is suspicious:\n• Artificial Urgency: Your account will be blocked today.\n• Payment Request: Send ₹2,000 to complete KYC\n\n💡 Key Safety Principle: Banks NEVER send links in SMS/WhatsApp asking for Netbanking passwords, PINs, or advance fees.",
    "recommendations": [
      {
        "priority": "high",
        "text": "⛔ DO NOT click on links claiming your account or KYC is expired."
      },
      {
        "priority": "high",
        "text": "🏦 Open your bank's verified official mobile banking app directly to verify."
      }
    ],
    "analysis_mode": "ai_plus_rules",
    "created_at": "2026-09-25T04:20:00.000000"
  }
}
```

---

## ✅ Verdict: SAFE / SUSPICIOUS / SCAM

Every result carries a plain three-way `verdict` (and a one-line `verdict_label`), shown as the badge on the result screen:

| Verdict | Risk score | Meaning |
|---|---|---|
| `SAFE` | 0 – 29 | No obvious suspicious indicators found. |
| `SUSPICIOUS` | 30 – 59 | Some warning signs found. Verify the sender through an official channel before acting. |
| `SCAM` | 60 – 100 | Strong signs of phishing, fraud or fake content. Do not reply, click, pay or share details. |

Checks behind it, besides the scam-pattern rules (KYC, lottery, QR, OTP, remote access, investment, job tasks, authority threats):
- **Sender / link mismatch**: a message naming a bank, company or government body (SBI, HDFC, Amazon, Income Tax, FedEx…) whose link or email is not on that organisation's official domain, including lookalikes such as `amaz0n-orders.shop`.
- **Free email senders**: an organisation writing from `@gmail.com`, `@yahoo.com` and similar.
- **Unverified contact numbers**: "call/WhatsApp this number" attached to a brand or authority claim.
- **Requests for money or bank/card details**.
- **Urgency, deadlines and threats** ("within 2 hours", "final notice", "will be suspended", penalties).
- **Writing style**: common phishing misspellings, generic greetings ("Dear Customer") and shouting in capitals or `!!!`.

## 🧪 Extra Features

- **🖍️ Red-flag highlighter**: the original message is shown with each suspicious phrase highlighted by severity (danger / warning / worth checking / official link). Hover or tap a highlight to see why it was flagged. API: `highlights` on every analysis.
- **🔬 Link X-ray**: every link is dissected offline (never opened) to show where it *really* goes and which trick it uses: the `@` trick (`sbi.co.in@evil.xyz`), a brand placed in front of another domain (`sbi.co.in.verify-kyc.xyz`), look-alike letters from other alphabets (Cyrillic `а` in `pаypal.com`) and punycode, lookalike spellings (`amaz0n`), link shorteners, raw IP addresses, risky domain endings, plain http and login/KYC bait in the path. Official domains are marked as verified. API: `link_xray` on every analysis. Deceptive link structures also raise the risk score.
- **🎯 Spot-the-Scam quiz**: a practice mode with realistic SMS, WhatsApp and email messages. Guess SAFE / SUSPICIOUS / SCAM, then see the highlighted red flags and a one-line lesson. API: `GET /api/v1/quiz/questions`, `POST /api/v1/quiz/answer`. A test checks that the detector agrees with every quiz answer.
- **👪 Warn family on WhatsApp**: on a SUSPICIOUS or SCAM result, one tap opens WhatsApp with a ready-written warning (verdict, red flags, the 1930 helpline). Links in the quoted message are defanged (`hxxps://evil[.]xyz`) so sharing the warning never spreads the scam link.

## 🧠 Risk Scoring Engine Formula

The Risk Engine combines signals to eliminate false negatives:
$$\text{Final Risk Score} = (S_{\text{rule}} \times 0.40) + (S_{\text{AI}} \times 0.40) + (S_{\text{severity}} \times 0.20) + E_{\text{boost}}$$

### Score Brackets:
- **`0 – 29` (LOW / SAFE)**: No major scam indicators detected.
- **`30 – 59` (MEDIUM)**: Suspicious patterns detected; sender verification recommended.
- **`60 – 79` (HIGH)**: Known deception tactics (e.g. artificial urgency, advance payment).
- **`80 – 100` (CRITICAL)**: Direct credential theft, OTP harvesting, or unauthorized remote access tools.

---

## 🌐 Multilingual English & Tamil (தமிழ்) Support

ScamShield AI includes native Tamil script (`\u0B80–\u0BFF`) and Tanglish keyword recognition:
- **Example**: `"உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். KYC update செய்ய உடனே ₹2000 அனுப்பவும்."`
- **Output**: Detects `fake_kyc`, flags urgency, extracts ₹2,000 payment demand, and renders localized Tamil explanations and recommendations.

---

## 🚀 Running Locally

### 1. Prerequisites
- Python 3.10+
- (Optional) Tesseract OCR

### 2. Setup Virtual Environment
```bash
git clone https://github.com/deborahtimothy2116-ops/AI-Financial-Scam-Conversation-Detector.git
cd AI-Financial-Scam-Conversation-Detector

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

> Screenshot scanning needs a text reader (OCR). **On Windows** nothing extra is needed: `requirements.txt` installs `winocr`, which uses the OCR built into Windows 10/11. **On Linux/macOS** install Tesseract (`apt install tesseract-ocr tesseract-ocr-tam` / `brew install tesseract`). Without one, text analysis still works, `/health` reports `ocr_engine_ready: false`, and screenshot uploads explain what to install.

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

### 4. Run Test Suite
```bash
python -m pytest
```

### 5. Launch FastAPI Backend & UI
```bash
uvicorn app.main:app --reload --port 8000
```
- 🌐 **Web UI**: [http://localhost:8000](http://localhost:8000)
- 📚 **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

Scans work without an account. Log in or register from the top-right button to keep a private scan history — guest scans are analysed but not saved.

### 6. (Optional) Rebuild the Stylesheet
The UI ships with a precompiled `frontend/tailwind.css`. If you add or change Tailwind classes in `index.html` or `app.js`, rebuild it:
```bash
npx tailwindcss@3 -c frontend/tailwind.config.js -i frontend/tailwind.input.css -o frontend/tailwind.css --minify
```

---

## 🐳 Docker Deployment

The entire stack (FastAPI backend + PostgreSQL 16) runs via Docker Compose:

```bash
docker compose up --build
```
- Backend container includes pre-installed `tesseract-ocr`, `tesseract-ocr-tam`, and `tesseract-ocr-hin`.

---

## 🔒 Privacy and Security by Design

- **Non-Transactional**: The app does not connect to bank accounts or execute money transfers.
- **Data Minimization**: Screenshots are processed in-memory and deleted immediately.
- **PII Sanitization**: Passwords, OTPs, and phone numbers are masked in logs.
- **Per-User Isolation**: User A cannot access or delete User B's scan history (`test_cross_user_history_isolation`).
- **Safe Rendering**: Scanned message text and OCR output are HTML-escaped in the UI, so a malicious message cannot inject script into the page.

---

## 📜 Hackathon Demo Verification Scenarios

| Scenario | Input Snippet | Expected Result |
|---|---|---|
| **Demo 1** | `"URGENT! Your bank account will be blocked today. Send ₹2,000 to complete KYC immediately."` | `HIGH/CRITICAL` • Fake KYC |
| **Demo 2** | `"Congratulations! You have won ₹5,00,000. Pay ₹2,000 processing fee to claim your prize."` | `CRITICAL` • Lottery Prize Scam |
| **Demo 3** | `"Guaranteed 30% profit every week. Invest ₹10,000 now."` | `HIGH` • Investment Fraud |
| **Demo 4** | `"Your friend sent the meeting notes. See you tomorrow."` | `LOW/SAFE` • Clean Conversation |
| **Demo 5** | `"உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். KYC update செய்ய உடனே ₹2000 அனுப்பவும்."` | `HIGH/CRITICAL` • Fake KYC (Tamil) |
