/**
 * ScamShield AI - Frontend Application Controller & API Integration Layer
 * Integrates Stitch UI components with FastAPI Backend Endpoints.
 */

// Global State
const state = {
  apiBaseUrl: localStorage.getItem("scamshield_api_url") || "/api/v1",
  token: localStorage.getItem("scamshield_token") || null,
  user: null,
  currentLanguage: localStorage.getItem("scamshield_lang") || "en",
  selectedInputLanguage: "auto",
  selectedFile: null,
  currentAnalysis: null,
  historyFilter: "all",
  historySearch: "",
  historyItems: [],
  historyMeta: {},
  authMode: "login", // 'login' | 'register'
};

// ---------------------------------------------------------------------------
// Pre-built Demo Messages (Hackathon Requirement Section 20)
// ---------------------------------------------------------------------------
const DEMO_CASES = {
  1: {
    title: "Urgent Bank KYC Expiry Scam",
    category: "fake_kyc",
    text: "URGENT! Your bank account will be blocked today. Send ₹2,000 to complete KYC immediately.",
    language: "auto",
  },
  2: {
    title: "Lottery / Prize Fee Scam",
    category: "lottery_prize_scam",
    text: "Congratulations! You have won ₹5,00,000. Pay ₹2,000 processing fee to claim your prize.",
    language: "auto",
  },
  3: {
    title: "Guaranteed Return Investment Scam",
    category: "investment_scam",
    text: "Guaranteed 30% profit every week. Invest ₹10,000 now.",
    language: "auto",
  },
  4: {
    title: "Safe Normal Message",
    category: "safe_conversation",
    text: "Your friend sent the meeting notes. See you tomorrow.",
    language: "auto",
  },
  5: {
    title: "Tamil Fake KYC Bank Block",
    category: "fake_kyc",
    text: "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். KYC update செய்ய உடனே ₹2000 அனுப்பவும்.",
    language: "ta",
  },
};

// ---------------------------------------------------------------------------
// Translations Dictionary (EN / தமிழ்)
// ---------------------------------------------------------------------------
const TRANSLATIONS = {
  en: {
    alertText: "Surge in fake electricity bill & bank KYC SMS APK scams reported this week. Stay alert.",
    heroHeading: 'Stay one step ahead of <span class="text-primary underline decoration-primary-fixed-dim decoration-4 underline-offset-4">financial scams</span>.',
    heroSubheading: "Analyze suspicious messages before you send money or share sensitive information. Instant AI analysis for SMS, WhatsApp, and chat screenshots with English and Tamil support.",
    heroBtnAnalyze: "Analyze a Message",
    heroBtnUpload: "Upload Screenshot",
    analyzeHeading: "Analyze a suspicious message",
    analyzeSubheading: "Paste the message you received and our AI will look for financial scam patterns, coercive urgency, and unauthorized payment paths in seconds.",
    btnAnalyze: "Analyze Message",
    highRiskTitle: "High Risk Financial Scam Detected",
    highRiskChip: "Immediate Action Required",
    highRiskDesc: "Do not transfer money, scan QR codes, or share personal authentication credentials with this sender.",
    lowRiskTitle: "Safe / Low Risk Interaction",
    lowRiskChip: "No Major Scam Detected",
    lowRiskDesc: "No major financial scam indicators detected. Continue exercising standard caution.",
    medRiskTitle: "Caution: Suspicious Patterns Detected",
    medRiskChip: "Verification Recommended",
    medRiskDesc: "This message contains some suspicious financial patterns. Verify the sender before taking action.",
  },
  ta: {
    alertText: "போலி மின் கட்டணம் மற்றும் வங்கி KYC SMS மோசடிகள் இந்த வாரம் அதிகரித்துள்ளன. எச்சரிக்கையாக இருங்கள்.",
    heroHeading: 'நிதி மோசடிகளுக்கு எதிராக <span class="text-primary underline decoration-primary-fixed-dim decoration-4 underline-offset-4">ஒரு படி முன்னால் இருங்கள்</span>.',
    heroSubheading: "பணம் அனுப்புவதற்கு அல்லது ரகசிய விவரங்களை பகிர்வதற்கு முன் சந்தேகத்திற்கிடமான செய்திகளை ஆய்வு செய்யுங்கள். SMS, WhatsApp மற்றும் ஸ்கிரீன்ஷாட்களுக்கான உடனடி AI பாதுகாப்பு.",
    heroBtnAnalyze: "செய்தியை ஆய்வு செய்",
    heroBtnUpload: "ஸ்கிரீன்ஷாட் பதிவேற்று",
    analyzeHeading: "சந்தேகத்திற்கிடமான செய்தியை ஆய்வு செய்",
    analyzeSubheading: "நீங்கள் பெற்ற செய்தியை உள்ளிடவும். எங்களின் AI மோசடி வடிவங்கள் மற்றும் போலி அவசர கோரிக்கைகளை நொடிகளில் கண்டறியும்.",
    btnAnalyze: "செய்தியை ஆய்வு செய்",
    highRiskTitle: "அதிக ஆபத்தான நிதி மோசடி கண்டறியப்பட்டது",
    highRiskChip: "உடனடி எச்சரிக்கை தேவை",
    highRiskDesc: "பணம் அனுப்பவோ, QR குறியீட்டை ஸ்கேன் செய்யவோ, அல்லது OTP/கடவுச்சொல்லை பகிரவோ வேண்டாம்.",
    lowRiskTitle: "பாதுகாப்பான / குறைந்த ஆபத்துடைய செய்தி",
    lowRiskChip: "மோசடி குறிகாட்டிகள் இல்லை",
    lowRiskDesc: "பெரிய நிதி மோசடி குறிகாட்டிகள் எதுவும் கண்டறியப்படவில்லை. தொடர்ந்து கவனமாக இருங்கள்.",
    medRiskTitle: "எச்சரிக்கை: சந்தேகத்திற்கிடமான வடிவங்கள்",
    medRiskChip: "சரிபார்ப்பு பரிந்துரைக்கப்படுகிறது",
    medRiskDesc: "இந்த செய்தியில் சில சந்தேகத்திற்கிடமான நிதி வடிவங்கள் உள்ளன. நடவடிக்கை எடுக்கும் முன் அனுப்புநரை சரிபார்க்கவும்.",
  },
};

// ---------------------------------------------------------------------------
// App Initialization
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  initLanguage();
  checkAuth();
  updateHistoryCountBadge();
  setupDropzone();
});

// ---------------------------------------------------------------------------
// Navigation & Router
// ---------------------------------------------------------------------------
function navigateTo(viewName) {
  const views = ["home", "analyze", "upload", "processing", "result", "history", "settings"];
  views.forEach((v) => {
    const el = document.getElementById(`view-${v}`);
    if (el) el.classList.add("hidden");
    const navBtn = document.getElementById(`nav-${v}`);
    if (navBtn) {
      navBtn.classList.remove("bg-surface-container-high", "text-primary", "font-bold");
      navBtn.classList.add("text-on-surface-variant", "font-semibold");
    }
  });

  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) {
    targetView.classList.remove("hidden");
    targetView.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const activeNav = document.getElementById(`nav-${viewName}`);
  if (activeNav) {
    activeNav.classList.add("bg-surface-container-high", "text-primary", "font-bold");
    activeNav.classList.remove("text-on-surface-variant");
  }

  if (viewName === "history") {
    loadHistoryData();
  }
}

// ---------------------------------------------------------------------------
// Language Support (Bilingual EN / தமிழ்)
// ---------------------------------------------------------------------------
function setAppLanguage(lang) {
  state.currentLanguage = lang;
  localStorage.setItem("scamshield_lang", lang);

  const btnEn = document.getElementById("btn-lang-en");
  const btnTa = document.getElementById("btn-lang-ta");

  if (lang === "ta") {
    btnTa.classList.add("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
    btnTa.classList.remove("text-on-surface-variant");
    btnEn.classList.remove("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
    btnEn.classList.add("text-on-surface-variant");
  } else {
    btnEn.classList.add("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
    btnEn.classList.remove("text-on-surface-variant");
    btnTa.classList.remove("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
    btnTa.classList.add("text-on-surface-variant");
  }

  applyTranslations(lang);
}

function initLanguage() {
  setAppLanguage(state.currentLanguage);
}

function applyTranslations(lang) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.en;
  const alertEl = document.getElementById("home-alert-text");
  if (alertEl) alertEl.textContent = t.alertText;

  const heroHeadingEl = document.getElementById("hero-heading");
  if (heroHeadingEl) heroHeadingEl.innerHTML = t.heroHeading;

  const heroSubEl = document.getElementById("hero-subheading");
  if (heroSubEl) heroSubEl.textContent = t.heroSubheading;

  const heroBtnA = document.getElementById("hero-btn-analyze");
  if (heroBtnA) heroBtnA.textContent = t.heroBtnAnalyze;

  const heroBtnU = document.getElementById("hero-btn-upload");
  if (heroBtnU) heroBtnU.textContent = t.heroBtnUpload;

  const analyzeHeadingEl = document.getElementById("analyze-heading");
  if (analyzeHeadingEl) analyzeHeadingEl.textContent = t.analyzeHeading;

  const analyzeSubEl = document.getElementById("analyze-subheading");
  if (analyzeSubEl) analyzeSubEl.textContent = t.analyzeSubheading;

  const btnSubmitA = document.getElementById("btn-submit-analyze-text");
  if (btnSubmitA) btnSubmitA.textContent = t.btnAnalyze;
}

function setInputLanguage(langCode) {
  state.selectedInputLanguage = langCode;
  ["auto", "en", "ta"].forEach((l) => {
    const pill = document.getElementById(`pill-lang-${l}`);
    if (pill) {
      if (l === langCode) {
        pill.classList.add("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
        pill.classList.remove("text-on-surface-variant");
      } else {
        pill.classList.remove("bg-surface-container-lowest", "text-on-surface", "shadow-sm", "font-bold");
        pill.classList.add("text-on-surface-variant");
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Authentication Layer
// ---------------------------------------------------------------------------
function openAuthModal(mode = "login") {
  switchAuthTab(mode);
  document.getElementById("auth-modal").classList.remove("hidden");
}

function closeAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
  document.getElementById("auth-error-msg").classList.add("hidden");
}

function switchAuthTab(mode) {
  state.authMode = mode;
  const tabLogin = document.getElementById("tab-login");
  const tabReg = document.getElementById("tab-register");
  const nameField = document.getElementById("auth-name-field");
  const modalTitle = document.getElementById("auth-modal-title");
  const submitBtn = document.getElementById("auth-submit-btn");

  if (mode === "register") {
    tabReg.classList.add("text-primary", "border-b-2", "border-primary");
    tabReg.classList.remove("text-on-surface-variant");
    tabLogin.classList.remove("text-primary", "border-b-2", "border-primary");
    tabLogin.classList.add("text-on-surface-variant");
    nameField.classList.remove("hidden");
    modalTitle.textContent = "Create an Account";
    submitBtn.textContent = "Register & Start";
  } else {
    tabLogin.classList.add("text-primary", "border-b-2", "border-primary");
    tabLogin.classList.remove("text-on-surface-variant");
    tabReg.classList.remove("text-primary", "border-b-2", "border-primary");
    tabReg.classList.add("text-on-surface-variant");
    nameField.classList.add("hidden");
    modalTitle.textContent = "User Login";
    submitBtn.textContent = "Sign In";
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const fullName = document.getElementById("authFullName").value.trim();
  const errorBox = document.getElementById("auth-error-msg");

  errorBox.classList.add("hidden");
  const endpoint = state.authMode === "register" ? `${state.apiBaseUrl}/auth/register` : `${state.apiBaseUrl}/auth/login`;
  const body = state.authMode === "register" ? { email, password, full_name: fullName || "User" } : { email, password };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      errorBox.textContent = data.message || (data.error && data.error.message) || "Authentication failed. Please check credentials.";
      errorBox.classList.remove("hidden");
      return;
    }

    const tokenData = data.data.token;
    state.token = tokenData.access_token;
    state.user = data.data.user;
    localStorage.setItem("scamshield_token", state.token);

    closeAuthModal();
    updateAuthUI();
    showToast(`Welcome ${state.user.full_name || state.user.email}!`, "success");
    refreshHistoryIfVisible();
  } catch (err) {
    errorBox.textContent = "Network error connecting to backend API: " + err.message;
    errorBox.classList.remove("hidden");
  }
}

async function checkAuth() {
  if (!state.token) {
    updateAuthUI();
    return;
  }
  try {
    const res = await fetch(`${state.apiBaseUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (res.ok) {
      const data = await res.json();
      state.user = data.data;
      updateAuthUI();
    } else {
      logout();
    }
  } catch (e) {
    console.warn("Auth check failed:", e);
  }
}

function updateAuthUI() {
  const authBtnLabel = document.getElementById("auth-btn-label");
  const authBtn = document.getElementById("auth-btn");

  if (state.user) {
    authBtnLabel.textContent = state.user.full_name ? state.user.full_name.split(" ")[0] : "Account";
    authBtn.onclick = () => {
      if (confirm(`Logged in as ${state.user.email}. Do you want to sign out?`)) {
        logout();
      }
    };
  } else {
    authBtnLabel.textContent = "Login";
    authBtn.onclick = () => openAuthModal("login");
  }
}

function refreshHistoryIfVisible() {
  updateHistoryCountBadge();
  const historyView = document.getElementById("view-history");
  if (historyView && !historyView.classList.contains("hidden")) loadHistoryData();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("scamshield_token");
  updateAuthUI();
  refreshHistoryIfVisible();
  showToast("Logged out successfully", "info");
}

// ---------------------------------------------------------------------------
// Demo Pre-population
// ---------------------------------------------------------------------------
function fillQuickScamDemo(type) {
  const input = document.getElementById("messageInput");
  if (type === "kyc") {
    input.value = DEMO_CASES[1].text;
    setInputLanguage("en");
  } else if (type === "lottery") {
    input.value = DEMO_CASES[2].text;
    setInputLanguage("en");
  } else if (type === "tamil") {
    input.value = DEMO_CASES[5].text;
    setInputLanguage("ta");
  }
  updateCharCount();
}

function runPrebuiltDemo(demoId) {
  const demo = DEMO_CASES[demoId];
  if (!demo) return;
  navigateTo("analyze");
  const input = document.getElementById("messageInput");
  input.value = demo.text;
  setInputLanguage(demo.language);
  updateCharCount();
  handleAnalyzeMessageSubmit();
}

function updateCharCount() {
  const input = document.getElementById("messageInput");
  const count = document.getElementById("charCount");
  if (input && count) {
    count.textContent = `${input.value.length} / 2,500`;
  }
}

function clearMessageInput() {
  const input = document.getElementById("messageInput");
  if (input) input.value = "";
  updateCharCount();
}

// ---------------------------------------------------------------------------
// File Upload & OCR Handling
// ---------------------------------------------------------------------------
function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  if (!dropzone) return;
}

function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("dropzone").classList.add("border-primary", "bg-surface-container");
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("dropzone").classList.remove("border-primary", "bg-surface-container");
}

function handleFileDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("dropzone").classList.remove("border-primary", "bg-surface-container");
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    setUploadedFile(e.dataTransfer.files[0]);
  }
}

function handleFileSelect(e) {
  if (e.target.files && e.target.files[0]) {
    setUploadedFile(e.target.files[0]);
  }
}

function setUploadedFile(file) {
  state.selectedFile = file;
  const card = document.getElementById("file-preview-card");
  const nameEl = document.getElementById("preview-filename");
  const sizeEl = document.getElementById("preview-filesize");
  const dropzone = document.getElementById("dropzone");

  if (card && nameEl && sizeEl) {
    nameEl.textContent = file.name;
    sizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    card.classList.remove("hidden");
    dropzone.classList.add("border-primary/50");
  }
}

function clearSelectedFile(e) {
  if (e) e.stopPropagation();
  state.selectedFile = null;
  document.getElementById("screenshotFileInput").value = "";
  document.getElementById("file-preview-card").classList.add("hidden");
  document.getElementById("dropzone").classList.remove("border-primary/50");
}

// ---------------------------------------------------------------------------
// Analysis Execution & Multi-stage Processing
// ---------------------------------------------------------------------------
async function handleAnalyzeMessageSubmit() {
  const text = document.getElementById("messageInput").value.trim();
  if (!text) {
    showToast("Please paste or type a message to analyze.", "error");
    return;
  }

  startProcessingAnimation();

  try {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const res = await fetch(`${state.apiBaseUrl}/analyze/message`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        message: text,
        language: state.selectedInputLanguage,
      }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.message || (data.error && data.error.message) || "Analysis failed");
    }

    state.currentAnalysis = data.data;
    completeProcessingAndShowResult();
    updateHistoryCountBadge();
  } catch (err) {
    navigateTo("analyze");
    showToast("Error during scam analysis: " + err.message, "error");
  }
}

async function handleAnalyzeScreenshotSubmit() {
  if (!state.selectedFile) {
    showToast("Please select or drop a screenshot image file.", "error");
    return;
  }

  startProcessingAnimation();

  try {
    const formData = new FormData();
    formData.append("file", state.selectedFile);
    if (state.selectedInputLanguage && state.selectedInputLanguage !== "auto") {
      formData.append("language", state.selectedInputLanguage);
    }

    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const res = await fetch(`${state.apiBaseUrl}/analyze/image`, {
      method: "POST",
      headers,
      body: formData,
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.message || (data.error && data.error.message) || "Screenshot OCR analysis failed");
    }

    state.currentAnalysis = data.data;
    completeProcessingAndShowResult();
    updateHistoryCountBadge();
  } catch (err) {
    navigateTo("upload");
    showToast("Error during screenshot analysis: " + err.message, "error");
  }
}

function startProcessingAnimation() {
  navigateTo("processing");
  const bar = document.getElementById("processing-bar-fill");
  const percentText = document.getElementById("processing-percent-text");
  const circle = document.getElementById("processing-circle-stroke");

  let progress = 15;
  bar.style.width = "15%";
  percentText.textContent = "15%";

  const interval = setInterval(() => {
    progress += Math.floor(Math.random() * 20) + 10;
    if (progress >= 90) {
      progress = 90;
      clearInterval(interval);
    }
    bar.style.width = `${progress}%`;
    percentText.textContent = `${progress}%`;

    // Highlight sequential steps
    if (progress > 30) highlightStep(2);
    if (progress > 55) highlightStep(3);
    if (progress > 75) highlightStep(4);
    if (progress >= 90) highlightStep(5);
  }, 200);

  state._processingInterval = interval;
}

function highlightStep(stepNum) {
  const stepEl = document.getElementById(`step-${stepNum}`);
  if (stepEl) {
    stepEl.classList.remove("opacity-60");
    const icon = document.getElementById(`step-${stepNum}-icon`);
    if (icon) {
      icon.textContent = "check_circle";
      icon.classList.remove("text-outline-variant", "animate-spin", "text-primary");
      icon.classList.add("text-tertiary", "font-bold");
    }
  }
}

function completeProcessingAndShowResult() {
  if (state._processingInterval) clearInterval(state._processingInterval);
  const bar = document.getElementById("processing-bar-fill");
  const percentText = document.getElementById("processing-percent-text");
  if (bar) bar.style.width = "100%";
  if (percentText) percentText.textContent = "100%";

  setTimeout(() => {
    renderResultView(state.currentAnalysis);
    navigateTo("result");
  }, 400);
}

// ---------------------------------------------------------------------------
// Dynamic Result View Rendering (High / Medium / Low Risk)
// ---------------------------------------------------------------------------
function renderResultView(analysis) {
  if (!analysis) return;

  const score = Math.round(analysis.risk ? analysis.risk.score : (analysis.risk_score || 0));
  const level = (analysis.risk ? analysis.risk.level : (analysis.risk_level || "LOW")).toUpperCase();
  // Server verdict: SAFE / SUSPICIOUS / SCAM (older records fall back to the risk level)
  const verdict = analysis.verdict || (score >= 60 ? "SCAM" : score >= 30 ? "SUSPICIOUS" : "SAFE");
  const isHigh = verdict === "SCAM";
  const isMed = verdict === "SUSPICIOUS";
  const isLow = !isHigh && !isMed;

  // Banner configuration
  const banner = document.getElementById("result-banner");
  const bannerTitle = document.getElementById("result-banner-title");
  const bannerChip = document.getElementById("result-banner-chip");
  const bannerDesc = document.getElementById("result-banner-desc");
  const bannerIcon = document.getElementById("result-banner-icon");
  const verdictBadge = document.getElementById("result-verdict-badge");
  const verdictText = document.getElementById("result-verdict-text");
  const scoreNumber = document.getElementById("result-score-number");
  const gaugeFill = document.getElementById("result-gauge-fill");

  scoreNumber.textContent = score;

  // Calculate SVG stroke offset for 314.159 perimeter (120 viewBox with r=50)
  const offset = 314.159 - (314.159 * score) / 100;
  gaugeFill.style.strokeDashoffset = `${offset}`;

  const lang = state.currentLanguage;
  const t = TRANSLATIONS[lang] || TRANSLATIONS.en;

  if (isHigh) {
    banner.className = "relative overflow-hidden rounded-xl shadow-xl p-6 mb-6 text-on-error bg-error transition-all";
    bannerTitle.textContent = t.highRiskTitle;
    bannerChip.textContent = t.highRiskChip;
    bannerChip.className = "px-2.5 py-0.5 rounded-full bg-on-error text-error text-xs uppercase font-bold tracking-wider";
    bannerDesc.textContent = t.highRiskDesc;
    bannerIcon.textContent = "warning";
    verdictBadge.className = "px-3 py-1 rounded-full bg-error text-on-error text-xs font-bold tracking-wide shadow-sm flex items-center gap-1.5";
    verdictText.textContent = "SCAM";
    scoreNumber.className = "font-display text-4xl font-extrabold text-error leading-none tracking-tight";
    gaugeFill.className = "text-error transition-all duration-1000 ease-out";
  } else if (isMed) {
    banner.className = "relative overflow-hidden rounded-xl shadow-xl p-6 mb-6 text-amber-950 bg-amber-400 transition-all";
    bannerTitle.textContent = t.medRiskTitle;
    bannerChip.textContent = t.medRiskChip;
    bannerChip.className = "px-2.5 py-0.5 rounded-full bg-amber-900 text-amber-50 text-xs uppercase font-bold tracking-wider";
    bannerDesc.textContent = t.medRiskDesc;
    bannerIcon.textContent = "gpp_maybe";
    verdictBadge.className = "px-3 py-1 rounded-full bg-amber-500 text-amber-950 text-xs font-bold tracking-wide shadow-sm flex items-center gap-1.5";
    verdictText.textContent = "SUSPICIOUS";
    scoreNumber.className = "font-display text-4xl font-extrabold text-amber-600 leading-none tracking-tight";
    gaugeFill.className = "text-amber-500 transition-all duration-1000 ease-out";
  } else {
    banner.className = "relative overflow-hidden rounded-xl shadow-xl p-6 mb-6 text-on-tertiary bg-tertiary transition-all";
    bannerTitle.textContent = t.lowRiskTitle;
    bannerChip.textContent = t.lowRiskChip;
    bannerChip.className = "px-2.5 py-0.5 rounded-full bg-on-tertiary text-tertiary text-xs uppercase font-bold tracking-wider";
    bannerDesc.textContent = t.lowRiskDesc;
    bannerIcon.textContent = "verified_user";
    verdictBadge.className = "px-3 py-1 rounded-full bg-tertiary-container text-on-tertiary-container text-xs font-bold tracking-wide shadow-sm flex items-center gap-1.5";
    verdictText.textContent = "SAFE";
    scoreNumber.className = "font-display text-4xl font-extrabold text-tertiary leading-none tracking-tight";
    gaugeFill.className = "text-tertiary transition-all duration-1000 ease-out";
  }

  // Category & Confidence
  const categoryTitle = analysis.category_title || (analysis.scam ? analysis.scam.category_label : "Scam Assessment");
  document.getElementById("result-category-title").textContent = categoryTitle;
  
  const conf = Math.round(((analysis.risk && analysis.risk.confidence) || analysis.language_confidence || 0.95) * 100);
  document.getElementById("result-confidence-text").textContent = `${conf}%`;
  document.getElementById("result-confidence-bar").style.width = `${conf}%`;

  // Raw Quote
  const rawText = analysis.raw_text || analysis.cleaned_text || "";
  document.getElementById("result-raw-text-quote").textContent = `"${rawText}"`;
  document.getElementById("result-input-source-badge").textContent = analysis.input_type === "screenshot" ? "Screenshot OCR" : "Message Text";
  document.getElementById("result-scan-id-label").textContent = `Scan #${(analysis.analysis_id || analysis.id || "REC").slice(0, 8)}`;
  document.getElementById("result-analysis-mode-label").textContent = analysis.analysis_mode === "fallback_rules" ? "Heuristic Rules Mode" : "AI + Rules Active";

  // Detected Language
  const langCode = analysis.detected_language || (analysis.language && analysis.language.code) || "en";
  document.getElementById("result-lang-label").textContent = `Detected: ${langCode === "ta" ? "தமிழ் (Tamil)" : "English"}`;

  // Red Flag Indicators Chips
  const chipsContainer = document.getElementById("result-indicators-chips");
  chipsContainer.innerHTML = "";
  const indicators = analysis.indicators || [];

  if (indicators.length === 0) {
    chipsContainer.innerHTML = `<span class="text-xs text-tertiary font-semibold flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">check</span> No threat red flags extracted</span>`;
  } else {
    indicators.forEach((ind) => {
      const chip = document.createElement("div");
      chip.className = "flex items-center gap-1.5 px-3 py-1 rounded-full bg-error-container text-on-error-container text-xs font-semibold";
      chip.innerHTML = `
        <span class="material-symbols-outlined text-[15px] text-error">flag</span>
        <span>${escapeHtml(ind.title || ind.type)}: <strong>${escapeHtml(ind.evidence || ind.snippet || ind.description || "")}</strong></span>
      `;
      chipsContainer.appendChild(chip);
    });
  }

  // Explanation
  const explanationBox = document.getElementById("result-explanation-box");
  explanationBox.textContent = analysis.explanation || "No suspicious deception tactics were detected.";
  document.getElementById("result-quick-summary").textContent =
    analysis.verdict_label || (analysis.explanation ? analysis.explanation.split("\n")[0] : "");

  // Recommendations
  const recsContainer = document.getElementById("result-recommendations-list");
  recsContainer.innerHTML = "";
  const recs = analysis.recommendations || [];

  recs.forEach((rec, idx) => {
    const text = typeof rec === "string" ? rec : rec.text;
    const prio = typeof rec === "string" ? "high" : rec.priority;
    const item = document.createElement("div");
    item.className = "flex items-start gap-2.5 p-3 rounded-lg bg-surface-container-low border border-surface-container";
    item.innerHTML = `
      <span class="material-symbols-outlined text-[18px] text-tertiary shrink-0 mt-0.5">shield</span>
      <span class="text-on-surface leading-snug font-medium">${escapeHtml(text)}</span>
    `;
    recsContainer.appendChild(item);
  });
}

// ---------------------------------------------------------------------------
// History Management & API Integration
// ---------------------------------------------------------------------------
async function loadHistoryData() {
  const container = document.getElementById("history-items-container");
  const emptyState = document.getElementById("history-empty-state");

  if (!state.token) {
    // History is stored per account; guest scans are analysed but not saved.
    emptyState.classList.add("hidden");
    document.getElementById("count-filter-all").textContent = 0;
    container.innerHTML = `
      <div class="p-8 rounded-xl bg-surface-container-lowest border border-surface-container text-center flex flex-col items-center gap-3">
        <span class="material-symbols-outlined text-[36px] text-primary">lock</span>
        <p class="text-sm font-bold text-on-surface">Sign in to save and review your scans</p>
        <p class="text-xs text-on-surface-variant max-w-md">Guest scans are analysed instantly but not stored. Create a free account to keep a private history of every message and screenshot you check.</p>
        <button onclick="openAuthModal('login')" class="mt-1 px-4 py-2 rounded-full bg-primary text-on-primary font-bold text-xs">Login / Register</button>
      </div>`;
    return;
  }

  container.innerHTML = `<div class="p-8 text-center text-xs text-on-surface-variant flex items-center justify-center gap-2"><span class="material-symbols-outlined animate-spin text-primary">progress_activity</span> Loading scan records...</div>`;

  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    let url = `${state.apiBaseUrl}/history?page=1&page_size=30`;
    if (state.historyFilter && state.historyFilter !== "all") {
      url += `&risk_level=${state.historyFilter}`;
    }
    if (state.historySearch) {
      url += `&search_query=${encodeURIComponent(state.historySearch)}`;
    }

    const res = await fetch(url, { headers });
    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.message || "Failed to fetch history");
    }

    state.historyItems = data.data.items || [];
    state.historyMeta = data.data.meta || {};

    document.getElementById("count-filter-all").textContent = state.historyMeta.total || state.historyItems.length;
    renderHistoryCards(state.historyItems);
  } catch (err) {
    container.innerHTML = `<div class="p-6 rounded-xl bg-error-container text-on-error-container text-xs font-semibold">Error loading scan history: ${escapeHtml(err.message)}</div>`;
  }
}

function renderHistoryCards(items) {
  const container = document.getElementById("history-items-container");
  const emptyState = document.getElementById("history-empty-state");

  if (!items || items.length === 0) {
    container.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  container.innerHTML = "";

  items.forEach((item) => {
    const isHigh = item.risk_level === "CRITICAL" || item.risk_level === "HIGH" || item.risk_score >= 60;
    const isMed = item.risk_level === "MEDIUM" || (item.risk_score >= 30 && item.risk_score < 60);

    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-surface-container-lowest border border-surface-container shadow-sm hover:shadow transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4";

    const badgeColor = isHigh
      ? "bg-error-container text-on-error-container"
      : isMed
      ? "bg-amber-100 text-amber-900"
      : "bg-emerald-100 text-emerald-900";

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "Recent";

    card.innerHTML = `
      <div class="flex items-start gap-3 min-w-0 flex-1">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-display font-bold text-sm ${badgeColor}">
          ${Math.round(item.risk_score)}
        </div>
        <div class="flex flex-col min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <span class="text-xs font-bold text-on-surface">${escapeHtml(item.category_title || item.scam_category)}</span>
            <span class="text-[10px] uppercase tracking-wider px-2 py-0.2 rounded-full font-bold ${badgeColor}">${escapeHtml(item.risk_level)}</span>
            <span class="text-xs text-on-surface-variant font-code">• ${dateStr}</span>
          </div>
          <p class="text-xs text-on-surface-variant truncate pr-2">"${escapeHtml(item.snippet)}"</p>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0 self-end sm:self-auto">
        <button onclick="viewHistoryDetail('${escapeHtml(item.id)}')" class="px-3.5 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-primary font-bold text-xs transition-all">
          View Detail
        </button>
        <button onclick="deleteHistoryItem('${escapeHtml(item.id)}')" class="p-1.5 rounded-full text-on-surface-variant hover:text-error hover:bg-surface-container transition-colors" title="Delete record">
          <span class="material-symbols-outlined text-[18px]">delete</span>
        </button>
      </div>
    `;

    container.appendChild(card);
  });
}

async function viewHistoryDetail(analysisId) {
  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const res = await fetch(`${state.apiBaseUrl}/history/${analysisId}`, { headers });
    const data = await res.json();
    if (res.ok && data.success) {
      state.currentAnalysis = data.data;
      renderResultView(state.currentAnalysis);
      navigateTo("result");
    } else {
      // Fallback to general analyze id endpoint
      const resAlt = await fetch(`${state.apiBaseUrl}/analyze/${analysisId}`);
      const dataAlt = await resAlt.json();
      if (resAlt.ok && dataAlt.success) {
        state.currentAnalysis = dataAlt.data;
        renderResultView(state.currentAnalysis);
        navigateTo("result");
      } else {
        showToast("Could not load history details.", "error");
      }
    }
  } catch (err) {
    showToast("Error loading detail: " + err.message, "error");
  }
}

async function deleteHistoryItem(analysisId) {
  if (!confirm("Are you sure you want to delete this scan record from your history?")) return;
  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const res = await fetch(`${state.apiBaseUrl}/history/${analysisId}`, {
      method: "DELETE",
      headers,
    });
    if (res.ok) {
      showToast("Scan record deleted.", "success");
      loadHistoryData();
      updateHistoryCountBadge();
    } else {
      showToast("Failed to delete record.", "error");
    }
  } catch (e) {
    showToast("Delete failed: " + e.message, "error");
  }
}

async function clearAllHistoryConfirm() {
  if (!confirm("Are you sure you want to clear your entire scan history? This action cannot be undone.")) return;
  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

    const res = await fetch(`${state.apiBaseUrl}/history/clear`, {
      method: "DELETE",
      headers,
    });
    if (res.ok) {
      showToast("History cleared successfully.", "success");
      loadHistoryData();
      updateHistoryCountBadge();
    }
  } catch (e) {
    showToast("Clear history failed: " + e.message, "error");
  }
}

function setHistoryRiskFilter(filter) {
  state.historyFilter = filter;
  ["all", "high", "medium", "low"].forEach((f) => {
    const btn = document.getElementById(`filter-${f}`);
    if (btn) {
      if (f === filter) {
        btn.classList.add("bg-surface-container-lowest", "text-primary", "shadow-sm", "font-bold");
        btn.classList.remove("text-on-surface-variant");
      } else {
        btn.classList.remove("bg-surface-container-lowest", "text-primary", "shadow-sm", "font-bold");
        btn.classList.add("text-on-surface-variant");
      }
    }
  });
  loadHistoryData();
}

function handleHistorySearch() {
  const query = document.getElementById("history-search-input").value;
  state.historySearch = query;
  clearTimeout(state._searchTimeout);
  state._searchTimeout = setTimeout(() => {
    loadHistoryData();
  }, 300);
}

function refreshHistory() {
  loadHistoryData();
}

async function updateHistoryCountBadge() {
  const countEl = document.getElementById("nav-history-count");
  if (!state.token) {
    if (countEl) countEl.textContent = 0;
    return;
  }
  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    const res = await fetch(`${state.apiBaseUrl}/history?page=1&page_size=1`, { headers });
    if (res.ok) {
      const data = await res.json();
      const count = data.data && data.data.meta ? data.data.meta.total : 0;
      if (countEl) countEl.textContent = count;
    }
  } catch (e) {
    // Non-blocking
  }
}

// ---------------------------------------------------------------------------
// Settings and Utilities
// ---------------------------------------------------------------------------
function saveApiSettings() {
  const val = document.getElementById("apiBaseUrlInput").value.trim();
  if (val) {
    state.apiBaseUrl = val;
    localStorage.setItem("scamshield_api_url", val);
    showToast("Backend API URL updated to " + val, "success");
  }
}

function copyAnalysisSummary() {
  if (!state.currentAnalysis) return;
  const a = state.currentAnalysis;
  const score = a.risk ? a.risk.score : a.risk_score;
  const text = `🛡️ ScamShield AI Scam Analysis Report\nRisk Score: ${score}/100 (${a.risk_level || (a.risk && a.risk.level)})\nCategory: ${a.category_title || (a.scam && a.scam.category_label)}\nExplanation:\n${a.explanation}\n\nAnalyzed with ScamShield AI before making payments.`;
  navigator.clipboard.writeText(text).then(() => {
    showToast("Safety report copied to clipboard!", "success");
  });
}

function reportScamOnline() {
  window.open("https://cybercrime.gov.in", "_blank");
}

// Escape untrusted text (scanned messages, OCR output, server errors) before inserting as HTML.
function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bg = type === "error" ? "bg-error text-on-error" : type === "success" ? "bg-tertiary text-on-tertiary" : "bg-inverse-surface text-inverse-on-surface";
  
  toast.className = `px-4 py-2.5 rounded-xl shadow-xl text-xs font-semibold flex items-center gap-2 pointer-events-auto fade-in ${bg}`;
  toast.innerHTML = `
    <span class="material-symbols-outlined text-[16px]">${type === "error" ? "error" : type === "success" ? "check_circle" : "info"}</span>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}
