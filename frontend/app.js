/**
 * ScamShield - frontend controller.
 * Scan a message or screenshot, show the verdict, and the helper tools
 * (check before you pay, emergency help, quiz, history).
 */

const state = {
  apiBaseUrl: "/api/v1",
  token: localStorage.getItem("scamshield_token") || null,
  user: null,
  scanMode: "text", // 'text' | 'image'
  selectedFile: null,
  currentAnalysis: null,
  historyFilter: "all",
  historySearch: "",
  historyItems: [],
  historyMeta: {},
  authMode: "login", // 'login' | 'register'
};

// Example messages for "Try an example"
const EXAMPLES = {
  kyc: "Dear Customer, your SBI account will be blocked today. Update your KYC immediately at sbi-kyc-update.xyz/login or call 98765 43210.",
  prize: "Congratulations! You have won ₹5,00,000 in the KBC lucky draw. Pay ₹2,000 processing fee to claim your prize.",
  arrest: "This is Mumbai Police Crime Branch. A parcel containing drugs was found in your name. You are under digital arrest. Stay on the video call and do not tell anyone.",
  tamil: "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். KYC update செய்ய உடனே ₹2000 அனுப்பவும்.",
  safe: "Hi! Your Amazon order has been delivered. Track it at https://www.amazon.in/orders",
};

// ---------------------------------------------------------------------------
// App Initialization
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setScanMode("text");
  highlightNav("scan");
  checkAuth();
  updateHistoryCountBadge();
});

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
const VIEWS = ["scan", "processing", "result", "history", "community", "quiz", "emergency"];
// Views that belong to a nav tab (processing/result count as "scan")
const NAV_FOR_VIEW = { scan: "scan", processing: "scan", result: "scan", history: "history", community: "community", quiz: "quiz" };

function highlightNav(viewName) {
  const active = NAV_FOR_VIEW[viewName];
  ["scan", "community", "quiz", "history"].forEach((tab) => {
    const on = tab === active;
    const desktop = document.getElementById(`nav-${tab}`);
    if (desktop) {
      desktop.classList.toggle("bg-surface-container-lowest", on);
      desktop.classList.toggle("text-primary", on);
      desktop.classList.toggle("shadow-sm", on);
    }
    const phone = document.getElementById(`mnav-${tab}`);
    if (phone) phone.classList.toggle("text-primary", on);
  });
}

function navigateTo(viewName) {
  if (!VIEWS.includes(viewName)) viewName = "scan";
  VIEWS.forEach((v) => {
    const el = document.getElementById(`view-${v}`);
    if (el) el.classList.toggle("hidden", v !== viewName);
  });
  highlightNav(viewName);
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (viewName === "history") loadHistoryData();
  if (viewName === "quiz" && !state.quiz) startQuiz();
  if (viewName === "emergency" && !state.emergencyGuide) loadEmergencyGuide(state.emergencyIncident || "upi_payment");
  if (viewName === "community") initCommunityView();
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
// Scan input: paste text or upload a screenshot
// ---------------------------------------------------------------------------
function setScanMode(mode) {
  state.scanMode = mode;
  const on = ["bg-surface-container-lowest", "text-primary", "shadow-sm"];
  const off = ["text-on-surface-variant"];
  const tabs = { text: document.getElementById("tab-text"), image: document.getElementById("tab-image") };
  Object.entries(tabs).forEach(([key, el]) => {
    on.forEach((c) => el.classList.toggle(c, key === mode));
    off.forEach((c) => el.classList.toggle(c, key !== mode));
    el.setAttribute("aria-selected", key === mode ? "true" : "false");
  });
  document.getElementById("scan-text-panel").classList.toggle("hidden", mode !== "text");
  document.getElementById("scan-image-panel").classList.toggle("hidden", mode !== "image");
}

function fillExample(key) {
  setScanMode("text");
  document.getElementById("messageInput").value = EXAMPLES[key] || "";
  updateCharCount();
}

function updateCharCount() {
  const len = document.getElementById("messageInput").value.length;
  document.getElementById("charCount").textContent = `${len.toLocaleString("en-IN")} / 2,500`;
}

function newScan() {
  document.getElementById("messageInput").value = "";
  updateCharCount();
  clearSelectedFile();
  navigateTo("scan");
}

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById("dropzone").classList.add("border-primary", "bg-surface-container");
}

function handleDragLeave(e) {
  e.preventDefault();
  document.getElementById("dropzone").classList.remove("border-primary", "bg-surface-container");
}

function handleFileDrop(e) {
  e.preventDefault();
  handleDragLeave(e);
  if (e.dataTransfer.files && e.dataTransfer.files[0]) setUploadedFile(e.dataTransfer.files[0]);
}

function handleFileSelect(e) {
  if (e.target.files && e.target.files[0]) setUploadedFile(e.target.files[0]);
}

function setUploadedFile(file) {
  if (!file.type.startsWith("image/")) {
    showToast("Please choose an image file (PNG, JPG or WEBP).", "error");
    return;
  }
  state.selectedFile = file;
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.previewUrl = URL.createObjectURL(file);
  document.getElementById("preview-image").src = state.previewUrl;
  document.getElementById("preview-filename").textContent = file.name;
  document.getElementById("preview-filesize").textContent = `${(file.size / 1024).toFixed(0)} KB`;
  document.getElementById("file-preview-card").classList.remove("hidden");
  document.getElementById("dropzone").classList.add("hidden");
}

function clearSelectedFile(e) {
  if (e) e.stopPropagation();
  state.selectedFile = null;
  document.getElementById("screenshotFileInput").value = "";
  document.getElementById("file-preview-card").classList.add("hidden");
  document.getElementById("dropzone").classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Scanner
// ---------------------------------------------------------------------------
const SCAN_CHECKS = {
  text: ["Reading the message", "Checking links and where they really go", "Looking for OTP, PIN and money requests",
         "Checking who it claims to be from", "Comparing with community reports"],
  image: ["Reading text from the screenshot", "Checking links and where they really go", "Looking for OTP, PIN and money requests",
          "Checking who it claims to be from", "Comparing with community reports"],
};
const MIN_SCAN_MS = 2200; // long enough for one clear pass of the beam over every check

function renderScannerChecks(done, total, labels) {
  document.getElementById("scanner-checks").innerHTML = labels
    .map((label, i) => {
      const icon = i < done ? "check_circle" : i === done ? "progress_activity" : "radio_button_unchecked";
      const color = i < done ? "text-emerald-400" : i === done ? "text-sky-300" : "text-slate-500";
      return `<div class="flex items-center gap-2 ${color}"><span class="material-symbols-outlined text-[16px] ${i === done ? "animate-spin" : ""}">${icon}</span>${escapeHtml(label)}</div>`;
    })
    .join("");
  document.getElementById("scanner-percent").textContent = `${Math.round((done / total) * 100)}%`;
}

function startScannerAnimation(mode, text) {
  const labels = SCAN_CHECKS[mode];
  const doc = document.getElementById("scanner-doc");
  const img = document.getElementById("scanner-image");
  document.getElementById("scanner-mode").textContent = mode === "image" ? "SCANNING SCREENSHOT" : "SCANNING MESSAGE";
  document.getElementById("scanner-dot").className = "w-2 h-2 rounded-full bg-sky-400 animate-pulse";
  document.getElementById("scanner-beam").classList.remove("done");
  document.getElementById("scanner-result-line").textContent = "";
  doc.classList.remove("scan-reveal");

  if (mode === "image") {
    doc.classList.add("hidden");
    img.classList.remove("hidden");
    img.src = state.previewUrl;
  } else {
    img.classList.add("hidden");
    doc.classList.remove("hidden");
    doc.textContent = text;
  }

  navigateTo("processing");
  let done = 0;
  renderScannerChecks(done, labels.length, labels);
  // Tick checks off steadily, but never finish the last one before the server answers.
  const stepMs = MIN_SCAN_MS / labels.length;
  const timer = setInterval(() => {
    if (done < labels.length - 1) {
      done += 1;
      renderScannerChecks(done, labels.length, labels);
    }
  }, stepMs);
  return { labels, timer, startedAt: Date.now() };
}

async function finishScannerAnimation(scan, analysis) {
  const wait = MIN_SCAN_MS - (Date.now() - scan.startedAt);
  if (wait > 0) await new Promise((r) => setTimeout(r, wait));
  clearInterval(scan.timer);
  renderScannerChecks(scan.labels.length, scan.labels.length, scan.labels);
  document.getElementById("scanner-beam").classList.add("done");

  // Reveal the red flags on the scanned document itself.
  const doc = document.getElementById("scanner-doc");
  const highlights = analysis.highlights || [];
  if (state.scanMode === "image") {
    // Show what was read from the screenshot, with highlights.
    document.getElementById("scanner-image").classList.add("hidden");
    doc.classList.remove("hidden");
  }
  doc.innerHTML = renderHighlightedText(analysis.raw_text || "", highlights);
  doc.classList.add("scan-reveal");

  const verdict = analysis.verdict || "SAFE";
  const flags = (analysis.indicators || []).length;
  const dot = { SCAM: "bg-red-500", SUSPICIOUS: "bg-amber-400", SAFE: "bg-emerald-400" }[verdict];
  document.getElementById("scanner-dot").className = `w-2 h-2 rounded-full ${dot}`;
  document.getElementById("scanner-mode").textContent = "SCAN COMPLETE";
  document.getElementById("scanner-result-line").textContent =
    flags ? `Found ${flags} warning sign${flags === 1 ? "" : "s"}` : "No warning signs found";

  await new Promise((r) => setTimeout(r, 1300));
  renderResultView(analysis);
  navigateTo("result");
}

async function startScan() {
  const mode = state.scanMode;
  const text = document.getElementById("messageInput").value.trim();
  if (mode === "text" && !text) {
    showToast("Paste the message you want to check first.", "error");
    return;
  }
  if (mode === "image" && !state.selectedFile) {
    showToast("Choose a screenshot to scan first.", "error");
    return;
  }

  const scan = startScannerAnimation(mode, text);
  try {
    const headers = {};
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    let res;
    if (mode === "text") {
      headers["Content-Type"] = "application/json";
      res = await fetch(`${state.apiBaseUrl}/analyze/message`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: text, language: "auto" }),
      });
    } else {
      const formData = new FormData();
      formData.append("file", state.selectedFile);
      res = await fetch(`${state.apiBaseUrl}/analyze/image`, { method: "POST", headers, body: formData });
    }
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "The scan failed. Please try again.");
    state.currentAnalysis = data.data;
    updateHistoryCountBadge();
    await finishScannerAnimation(scan, data.data);
  } catch (err) {
    clearInterval(scan.timer);
    navigateTo("scan");
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------
const VERDICT_STYLES = {
  SCAM: { banner: "bg-error text-on-error", pill: "bg-on-error text-error", icon: "dangerous", why: "Why this looks like a scam" },
  SUSPICIOUS: { banner: "bg-amber-400 text-amber-950", pill: "bg-amber-950 text-amber-50", icon: "gpp_maybe", why: "Why you should be careful" },
  SAFE: { banner: "bg-tertiary text-on-tertiary", pill: "bg-on-tertiary text-tertiary", icon: "verified_user", why: "What we checked" },
};
const SEVERITY_DOT = { CRITICAL: "bg-red-600", HIGH: "bg-red-500", MEDIUM: "bg-amber-500", LOW: "bg-sky-500" };

function renderResultView(analysis) {
  if (!analysis) return;
  state.currentAnalysis = analysis;
  const score = Math.round(analysis.risk ? analysis.risk.score : analysis.risk_score || 0);
  const verdict = analysis.verdict || (score >= 60 ? "SCAM" : score >= 30 ? "SUSPICIOUS" : "SAFE");
  const style = VERDICT_STYLES[verdict];

  // Verdict banner
  document.getElementById("result-banner").className = `rounded-2xl p-6 shadow-lg mb-5 flex items-start gap-4 ${style.banner}`;
  document.getElementById("result-banner-icon").textContent = style.icon;
  document.getElementById("result-verdict-text").textContent = verdict;
  const pill = document.getElementById("result-score-pill");
  pill.className = `px-2.5 py-0.5 rounded-full text-xs font-bold ${style.pill}`;
  pill.textContent = `Risk ${score} / 100`;
  document.getElementById("result-verdict-label").textContent = (analysis.verdict_label || "").replace(/^\w+ – /, "");
  const category = analysis.category_title || "";
  document.getElementById("result-category").textContent =
    verdict === "SAFE" || !category ? "" : `Looks like: ${category}`;

  // Message with highlights
  const rawText = analysis.raw_text || analysis.cleaned_text || "";
  const highlights = analysis.highlights || [];
  document.getElementById("result-raw-text-quote").innerHTML = renderHighlightedText(rawText, highlights);
  document.getElementById("result-highlight-legend").classList.toggle("hidden", highlights.length === 0);
  document.getElementById("result-input-source-badge").textContent =
    analysis.input_type === "screenshot" ? "Read from screenshot" : "Pasted text";

  // Why: one clear list of red flags
  document.getElementById("result-why-title").textContent = style.why;
  const indicators = analysis.indicators || [];
  document.getElementById("result-red-flags").innerHTML = indicators.length
    ? indicators
        .map((ind) => `
          <li class="flex items-start gap-3">
            <span class="w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${SEVERITY_DOT[String(ind.severity).toUpperCase()] || "bg-sky-500"}"></span>
            <span class="min-w-0">
              <span class="block text-sm font-bold text-on-surface">${escapeHtml(ind.title || "")}</span>
              <span class="block text-xs text-on-surface-variant leading-relaxed mt-0.5">${escapeHtml(ind.description || "")}</span>
            </span>
          </li>`)
        .join("")
    : `<li class="flex items-start gap-3 text-sm text-on-surface-variant">
         <span class="material-symbols-outlined text-tertiary text-[20px]">check_circle</span>
         <span>No requests for money, OTPs or passwords, no suspicious links, no pressure or threats. It still pays to be careful with messages from people you don't know.</span>
       </li>`;

  // Link X-ray
  renderLinkXray(analysis.link_xray || []);

  // What to do
  const recs = analysis.recommendations || [];
  document.getElementById("result-recommendations-list").innerHTML = recs
    .map((rec, i) => {
      const text = typeof rec === "string" ? rec : rec.text;
      return `
        <li class="flex items-start gap-3">
          <span class="w-6 h-6 rounded-full bg-surface-container text-primary text-xs font-bold flex items-center justify-center shrink-0">${i + 1}</span>
          <span class="text-on-surface leading-snug pt-0.5">${escapeHtml(text)}</span>
        </li>`;
    })
    .join("");

  // Actions that only make sense for risky messages
  ["btn-warn-family", "btn-report-community", "btn-emergency-from-result"].forEach((id) =>
    document.getElementById(id).classList.toggle("hidden", verdict === "SAFE")
  );
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
// Red-flag Highlighter
// ---------------------------------------------------------------------------
const HIGHLIGHT_STYLES = {
  high: "bg-red-200 text-red-950 border-b-2 border-red-500",
  medium: "bg-amber-100 text-amber-950 border-b-2 border-amber-500",
  low: "bg-sky-100 text-sky-950 border-b-2 border-sky-400",
  safe: "bg-emerald-100 text-emerald-950 border-b-2 border-emerald-500",
};

// Build escaped HTML for `text` with each highlight span wrapped in a <mark>.
function renderHighlightedText(text, highlights) {
  state.activeHighlights = highlights || [];
  let html = "";
  let cursor = 0;
  state.activeHighlights.forEach((h, i) => {
    if (h.start < cursor || h.end > text.length) return;
    html += escapeHtml(text.slice(cursor, h.start));
    const style = HIGHLIGHT_STYLES[h.severity] || HIGHLIGHT_STYLES.low;
    html += `<mark class="${style} rounded px-0.5 cursor-help" tabindex="0" title="${escapeHtml(h.label + ": " + h.reason)}" onclick="showHighlightReason(${i})">${escapeHtml(text.slice(h.start, h.end))}</mark>`;
    cursor = h.end;
  });
  html += escapeHtml(text.slice(cursor));
  return html;
}

function showHighlightReason(index) {
  const h = (state.activeHighlights || [])[index];
  if (h) showToast(`${h.label}: ${h.reason}`, h.severity === "safe" ? "success" : "info");
}

// ---------------------------------------------------------------------------
// Link X-ray
// ---------------------------------------------------------------------------
const XRAY_STYLES = {
  danger: { chip: "bg-error text-on-error", label: "DANGEROUS", icon: "dangerous", border: "border-error/40" },
  caution: { chip: "bg-amber-400 text-amber-950", label: "CAUTION", icon: "warning", border: "border-amber-400/60" },
  unknown: { chip: "bg-surface-container-high text-on-surface-variant", label: "UNVERIFIED", icon: "help", border: "border-outline-variant/40" },
  safe: { chip: "bg-emerald-600 text-white", label: "OFFICIAL", icon: "verified", border: "border-emerald-400/60" },
};
const FLAG_ICON = { high: "error", medium: "warning", low: "info", good: "check_circle", info: "info" };
const FLAG_COLOR = { high: "text-error", medium: "text-amber-600", low: "text-sky-700", good: "text-emerald-600", info: "text-on-surface-variant" };

function renderLinkXray(reports) {
  const section = document.getElementById("result-link-xray-section");
  const list = document.getElementById("result-link-xray-list");
  list.innerHTML = "";
  section.classList.toggle("hidden", reports.length === 0);

  reports.forEach((r) => {
    const s = XRAY_STYLES[r.risk] || XRAY_STYLES.unknown;
    const flags = r.flags.length
      ? r.flags.map((f) => `
          <li class="flex items-start gap-2">
            <span class="material-symbols-outlined text-[16px] ${FLAG_COLOR[f.severity] || ""} shrink-0 mt-0.5">${FLAG_ICON[f.severity] || "info"}</span>
            <span><strong class="text-on-surface">${escapeHtml(f.title)}.</strong> ${escapeHtml(f.detail)}</span>
          </li>`).join("")
      : `<li class="text-on-surface-variant">No known tricks found, but this is not a recognised official domain. Open the organisation's app or type its address yourself.</li>`;
    const card = document.createElement("div");
    card.className = `p-4 rounded-xl bg-surface-container-low border ${s.border}`;
    card.innerHTML = `
      <div class="flex items-start justify-between gap-3 mb-2">
        <div class="min-w-0">
          <div class="text-[11px] uppercase tracking-wider font-bold text-on-surface-variant">Really goes to</div>
          <div class="font-code text-sm font-bold text-on-surface break-all">${escapeHtml(r.real_domain)}</div>
          ${r.looks_like ? `<div class="text-[11px] text-error font-semibold mt-0.5">Made to look like: ${escapeHtml(r.looks_like)}</div>` : ""}
        </div>
        <span class="px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider flex items-center gap-1 shrink-0 ${s.chip}">
          <span class="material-symbols-outlined text-[14px]">${s.icon}</span>${s.label}
        </span>
      </div>
      <div class="text-[11px] text-on-surface-variant font-code break-all mb-3">${escapeHtml(r.link)}</div>
      <ul class="space-y-1.5 text-xs text-on-surface-variant">${flags}</ul>`;
    list.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// Warn Family on WhatsApp
// ---------------------------------------------------------------------------
// Make links unclickable in shared text so the warning doesn't spread the scam link.
function defangLinks(text) {
  return text.replace(/\b(?:https?:\/\/|www\.)?[\w-]+(?:\.[\w-]+)+(?:\/\S*[^\s.,;:!?)\]])?/gi, (m) =>
    /[a-z]/i.test(m) && /\.[a-z]{2,}/i.test(m) ? m.replace(/^http/i, "hxxp").replace(/\./g, "[.]") : m
  );
}

function warnFamilyOnWhatsApp() {
  const a = state.currentAnalysis;
  if (!a) return;
  const score = Math.round(a.risk ? a.risk.score : a.risk_score || 0);
  const flags = (a.indicators || []).slice(0, 4).map((i) => i.title).join("; ");
  const raw = (a.raw_text || "").replace(/\s+/g, " ").trim();
  const snippet = defangLinks(raw.length > 220 ? raw.slice(0, 220) + "..." : raw);
  const text = [
    "⚠️ Scam alert - please be careful!",
    `I received a message that ScamShield AI rated ${a.verdict || "SUSPICIOUS"} (${score}/100): ${a.category_title || "suspicious message"}.`,
    flags ? `Red flags: ${flags}.` : "",
    snippet ? `The message (links disabled): "${snippet}"` : "",
    "If you get something similar: don't click links, don't pay, and never share OTP, PIN or passwords. Report fraud by calling 1930 or at cybercrime.gov.in",
  ].filter(Boolean).join("\n\n");
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
}

// ---------------------------------------------------------------------------
// Emergency: "I've been scammed"
// ---------------------------------------------------------------------------
const PRIORITY_STYLES = {
  now: { chip: "bg-error text-on-error", label: "DO NOW" },
  today: { chip: "bg-amber-400 text-amber-950", label: "TODAY" },
  later: { chip: "bg-surface-container-high text-on-surface-variant", label: "NEXT DAYS" },
};

function emergencyProgressKey(incident) {
  return `scamshield_emergency_done_${incident}`;
}

function loadEmergencyProgress(incident) {
  try {
    return new Set(JSON.parse(localStorage.getItem(emergencyProgressKey(incident)) || "[]"));
  } catch (e) {
    return new Set();
  }
}

function saveEmergencyProgress(incident, done) {
  try {
    localStorage.setItem(emergencyProgressKey(incident), JSON.stringify([...done]));
  } catch (e) {
    // Progress is a convenience; ignore storage failures.
  }
}

async function loadEmergencyGuide(incident) {
  state.emergencyIncident = incident;
  const stepsEl = document.getElementById("emergency-steps");
  stepsEl.innerHTML = `<div class="text-xs text-on-surface-variant">Loading steps...</div>`;
  try {
    const res = await fetch(`${state.apiBaseUrl}/emergency/guide?incident_type=${encodeURIComponent(incident)}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not load steps");
    state.emergencyGuide = data.data;
    renderEmergencyGuide();
  } catch (err) {
    stepsEl.innerHTML = `<div class="text-xs text-error font-semibold">Could not load steps: ${escapeHtml(err.message)}. Call 1930 now.</div>`;
  }
}

function renderEmergencyGuide() {
  const guide = state.emergencyGuide;
  const done = loadEmergencyProgress(guide.incident_type);

  document.getElementById("emergency-incident-chips").innerHTML = Object.entries(guide.incident_types)
    .map(([key, label]) => `
      <button onclick="loadEmergencyGuide('${escapeHtml(key)}')" class="px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
        key === guide.incident_type ? "bg-error text-on-error border-error" : "bg-surface-container-lowest text-on-surface border-outline-variant/40 hover:bg-surface-container"
      }">${escapeHtml(label)}</button>`)
    .join("");

  document.getElementById("emergency-steps").innerHTML = guide.steps
    .map((step, i) => {
      const p = PRIORITY_STYLES[step.priority] || PRIORITY_STYLES.later;
      const checked = done.has(step.title);
      const action = step.action
        ? `<a href="${escapeHtml(step.action.href)}" ${step.action.href.startsWith("http") ? 'target="_blank" rel="noopener"' : ""} class="inline-flex items-center gap-1 mt-2 px-3 py-1 rounded-full bg-primary text-on-primary text-[11px] font-bold"><span class="material-symbols-outlined text-[14px]">${step.action.href.startsWith("tel:") ? "call" : "open_in_new"}</span>${escapeHtml(step.action.label)}</a>`
        : "";
      return `
        <label class="flex items-start gap-3 p-3 rounded-lg border ${checked ? "bg-emerald-50 border-emerald-300" : "bg-surface-container-low border-surface-container"} cursor-pointer">
          <input type="checkbox" ${checked ? "checked" : ""} onchange="toggleEmergencyStep(${i}, this.checked)" class="mt-1 w-4 h-4 accent-emerald-600 shrink-0"/>
          <span class="flex-1 min-w-0">
            <span class="flex items-center gap-2 flex-wrap">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider ${p.chip}">${p.label}</span>
              <span class="text-sm font-bold text-on-surface ${checked ? "line-through opacity-60" : ""}">${escapeHtml(step.title)}</span>
            </span>
            <span class="block text-xs text-on-surface-variant mt-1 leading-relaxed">${escapeHtml(step.detail)}</span>
            ${action}
          </span>
        </label>`;
    })
    .join("");
}

function toggleEmergencyStep(index, checked) {
  const guide = state.emergencyGuide;
  const done = loadEmergencyProgress(guide.incident_type);
  const title = guide.steps[index].title;
  checked ? done.add(title) : done.delete(title);
  saveEmergencyProgress(guide.incident_type, done);
  renderEmergencyGuide();
}

// From a result: carry the scanned message into the emergency form.
function openEmergencyFromResult() {
  const a = state.currentAnalysis;
  if (a) {
    document.getElementById("em-message").value = a.raw_text || "";
    state.emergencyScamType = a.category_title || null;
    const category = String(a.scam_category || "");
    const incident = category.includes("OTP") ? "otp_shared"
      : category.includes("INVESTMENT") ? "investment"
      : (a.indicators || []).some((i) => i.rule_id === "RULE_DIGITAL_ARREST") ? "digital_arrest"
      : "upi_payment";
    state.emergencyGuide = null;
    state.emergencyIncident = incident;
  }
  navigateTo("emergency");
}

async function generateComplaintDraft() {
  const val = (id) => document.getElementById(id).value.trim();
  const amount = parseFloat(val("em-amount"));
  const payload = {
    incident_type: state.emergencyIncident || "upi_payment",
    amount_lost: Number.isFinite(amount) && amount > 0 ? amount : null,
    incident_datetime: val("em-datetime") || null,
    payment_method: val("em-method") || null,
    transaction_ids: val("em-txn").split(/[,\s]+/).filter(Boolean),
    complainant_name: val("em-name") || null,
    bank_name: val("em-bank") || null,
    description: val("em-desc") || null,
    message_text: val("em-message") || null,
    scam_type: state.emergencyScamType || null,
  };
  try {
    const res = await fetch(`${state.apiBaseUrl}/emergency/complaint-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not create the draft");
    document.getElementById("em-draft").value = data.data.draft_text;
    document.getElementById("em-draft-section").classList.remove("hidden");
    document.getElementById("em-draft").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (err) {
    showToast("Could not create the complaint draft: " + err.message, "error");
  }
}

function copyComplaintDraft() {
  navigator.clipboard.writeText(document.getElementById("em-draft").value).then(() => showToast("Complaint copied. Paste it into the portal or an email to your bank.", "success"));
}

function downloadComplaintDraft() {
  const blob = new Blob([document.getElementById("em-draft").value], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `fraud-complaint-${new Date().toISOString().slice(0, 10)}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ---------------------------------------------------------------------------
// Community: check before you pay / report a scammer
// ---------------------------------------------------------------------------
const REPORT_CATEGORIES = [
  ["", "Not sure"],
  ["PHISHING_CREDENTIAL_HARVESTING", "Fake KYC / bank phishing"],
  ["UPI_QR_SCAM", "UPI / QR code payment trap"],
  ["URGENT_IMPERSONATION", "Fake police / official / digital arrest"],
  ["OTP_REMOTE_ACCESS_SCAM", "OTP theft / remote access"],
  ["LOTTERY_PRIZE_SCAM", "Lottery / prize"],
  ["JOB_OFFER_TASK_FRAUD", "Part-time job / task"],
  ["INVESTMENT_CRYPTO_PONZI", "Investment / trading / crypto"],
  ["MARKETPLACE_ADVANCE_FEE", "OLX / marketplace advance"],
  ["LOAN_APP_EXTORTION", "Loan app harassment"],
  ["ROMANCE_PIG_BUTCHERING", "Romance / friendship"],
  ["SUSPICIOUS_UNKNOWN", "Other"],
];
const LOOKUP_STYLES = {
  strongly_reported: { box: "bg-error-container border-error/30 text-on-error-container", icon: "dangerous", title: "Reported as a scam" },
  reported: { box: "bg-amber-50 border-amber-300 text-amber-950", icon: "warning", title: "Reported by the community" },
  official: { box: "bg-emerald-50 border-emerald-300 text-emerald-900", icon: "verified", title: "Official website" },
  no_reports: { box: "bg-surface-container-low border-surface-container text-on-surface", icon: "info", title: "No reports yet" },
};

function initCommunityView() {
  const select = document.getElementById("report-category");
  if (!select.options.length) {
    select.innerHTML = REPORT_CATEGORIES.map(([v, l]) => `<option value="${v}">${escapeHtml(l)}</option>`).join("");
  }
}

async function lookupIdentifier() {
  const q = document.getElementById("community-query").value.trim();
  const out = document.getElementById("community-result");
  if (!q) return;
  out.innerHTML = `<div class="text-xs text-on-surface-variant">Checking...</div>`;
  try {
    const res = await fetch(`${state.apiBaseUrl}/community/lookup?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Lookup failed");
    const r = data.data;
    const s = LOOKUP_STYLES[r.status] || LOOKUP_STYLES.no_reports;
    const labels = Object.fromEntries(REPORT_CATEGORIES);
    const cats = Object.entries(r.categories || {})
      .map(([c, n]) => `<span class="px-2 py-0.5 rounded-full bg-surface-container-lowest/70 text-[11px] font-semibold">${escapeHtml(labels[c] || c)} &times; ${n}</span>`)
      .join(" ");
    const last = r.last_reported ? new Date(r.last_reported).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null;
    out.innerHTML = `
      <div class="p-4 rounded-xl border ${s.box}">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <div class="flex items-center gap-2 font-bold text-sm"><span class="material-symbols-outlined text-[22px]">${s.icon}</span>${s.title}</div>
          <span class="font-code text-xs font-semibold">${escapeHtml(r.identifier_type.toUpperCase())}: ${escapeHtml(r.identifier)}</span>
        </div>
        ${r.report_count ? `<div class="text-2xl font-extrabold mt-2">${r.report_count} report${r.report_count === 1 ? "" : "s"}</div>` : ""}
        <p class="text-xs mt-1 leading-relaxed">${escapeHtml(r.advice)}</p>
        ${cats ? `<div class="flex flex-wrap gap-1.5 mt-2">${cats}</div>` : ""}
        ${last ? `<div class="text-[11px] opacity-80 mt-2">Last reported ${escapeHtml(last)}</div>` : ""}
      </div>`;
    if (r.status !== "official") document.getElementById("report-identifier").value = q;
  } catch (err) {
    out.innerHTML = `<div class="text-xs text-error font-semibold">${escapeHtml(err.message)}</div>`;
  }
}

async function submitCommunityReport() {
  if (!state.token) {
    showToast("Please log in to report. It keeps reports trustworthy.", "info");
    openAuthModal("login");
    return;
  }
  const payload = {
    identifier: document.getElementById("report-identifier").value.trim(),
    scam_category: document.getElementById("report-category").value || null,
    note: document.getElementById("report-note").value.trim() || null,
  };
  try {
    const res = await fetch(`${state.apiBaseUrl}/community/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Report failed");
    showToast(`${data.message} (${data.data.report_count} report${data.data.report_count === 1 ? "" : "s"} in total)`, data.data.created ? "success" : "info");
    document.getElementById("community-query").value = data.data.identifier;
    lookupIdentifier();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function reportFromCurrentAnalysis() {
  const a = state.currentAnalysis;
  if (!a) return;
  if (!state.token) {
    showToast("Please log in to report scammer details.", "info");
    openAuthModal("login");
    return;
  }
  try {
    const res = await fetch(`${state.apiBaseUrl}/community/reports/from-analysis/${encodeURIComponent(a.analysis_id || a.id)}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${state.token}` },
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Report failed");
    const list = data.data.map((r) => r.identifier).join(", ");
    showToast(`${data.message} ${list}`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Spot-the-Scam Quiz
// ---------------------------------------------------------------------------
const QUIZ_CHOICES = [
  { verdict: "SAFE", style: "bg-emerald-600 hover:bg-emerald-700 text-white", icon: "verified_user" },
  { verdict: "SUSPICIOUS", style: "bg-amber-400 hover:bg-amber-500 text-amber-950", icon: "gpp_maybe" },
  { verdict: "SCAM", style: "bg-error hover:bg-red-700 text-on-error", icon: "dangerous" },
];

async function startQuiz() {
  state.quiz = { questions: [], index: 0, score: 0, answered: false };
  document.getElementById("quiz-card").innerHTML = `<div class="text-sm text-on-surface-variant">Loading questions...</div>`;
  try {
    const res = await fetch(`${state.apiBaseUrl}/quiz/questions?count=5`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not load quiz");
    state.quiz.questions = data.data;
    renderQuizQuestion();
  } catch (err) {
    state.quiz = null;
    document.getElementById("quiz-card").innerHTML = `<div class="text-sm text-error font-semibold">Could not load the quiz: ${escapeHtml(err.message)}</div>`;
  }
}

function renderQuizQuestion() {
  const q = state.quiz.questions[state.quiz.index];
  state.quiz.answered = false;
  document.getElementById("quiz-progress").textContent = `Question ${state.quiz.index + 1} of ${state.quiz.questions.length}`;
  document.getElementById("quiz-score").textContent = `Score ${state.quiz.score}`;
  document.getElementById("quiz-card").innerHTML = `
    <div class="flex items-center gap-2 mb-3 text-xs">
      <span class="px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant font-bold">${escapeHtml(q.channel)}</span>
      <span class="text-on-surface-variant">From:</span>
      <span class="font-code font-semibold text-on-surface break-all">${escapeHtml(q.sender)}</span>
    </div>
    <div id="quiz-message" class="p-4 rounded-2xl rounded-tl-sm bg-surface-container-low border border-surface-container text-sm text-on-surface leading-loose mb-6 whitespace-pre-line">${escapeHtml(q.message)}</div>
    <div class="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">Your call</div>
    <div class="grid grid-cols-3 gap-2 sm:gap-3">
      ${QUIZ_CHOICES.map((c) => `
        <button onclick="answerQuiz('${c.verdict}')" class="quiz-choice px-3 py-3 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-1.5 shadow-sm transition-all ${c.style}">
          <span class="material-symbols-outlined text-[18px]">${c.icon}</span>${c.verdict}
        </button>`).join("")}
    </div>
    <div id="quiz-feedback"></div>`;
}

async function answerQuiz(guess) {
  if (!state.quiz || state.quiz.answered) return;
  state.quiz.answered = true;
  document.querySelectorAll(".quiz-choice").forEach((b) => (b.disabled = true, b.classList.add("opacity-60")));
  const q = state.quiz.questions[state.quiz.index];
  try {
    const res = await fetch(`${state.apiBaseUrl}/quiz/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: q.id, guess }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not check answer");
    const r = data.data;
    if (r.correct) state.quiz.score += 1;
    document.getElementById("quiz-score").textContent = `Score ${state.quiz.score}`;
    document.getElementById("quiz-message").innerHTML = renderHighlightedText(q.message, r.highlights);

    const last = state.quiz.index >= state.quiz.questions.length - 1;
    const flags = r.red_flags.length
      ? `<div class="flex flex-wrap gap-1.5 mt-3">${r.red_flags.map((f) => `<span class="px-2 py-0.5 rounded-full bg-error-container text-on-error-container text-[11px] font-semibold">${escapeHtml(f)}</span>`).join("")}</div>`
      : "";
    document.getElementById("quiz-feedback").innerHTML = `
      <div class="mt-6 p-4 rounded-xl border ${r.correct ? "bg-emerald-50 border-emerald-300" : "bg-error-container border-error/30"}">
        <div class="flex items-center gap-2 font-bold text-sm ${r.correct ? "text-emerald-800" : "text-on-error-container"}">
          <span class="material-symbols-outlined text-[20px]">${r.correct ? "celebration" : "school"}</span>
          ${r.correct ? "Correct!" : `Not quite. You said ${escapeHtml(r.guess)}.`}
        </div>
        <div class="text-sm font-semibold text-on-surface mt-2">${escapeHtml(r.answer_label)}</div>
        <p class="text-xs text-on-surface-variant mt-1 leading-relaxed">${escapeHtml(r.lesson)}</p>
        ${flags}
      </div>
      <div class="flex justify-end mt-4">
        <button onclick="${last ? "finishQuiz()" : "nextQuizQuestion()"}" class="px-5 py-2 rounded-full bg-primary text-on-primary hover:bg-primary-container text-xs font-bold flex items-center gap-1.5 shadow-sm">
          ${last ? "See my score" : "Next message"}<span class="material-symbols-outlined text-[16px]">arrow_forward</span>
        </button>
      </div>`;
  } catch (err) {
    state.quiz.answered = false;
    showToast("Could not check answer: " + err.message, "error");
  }
}

function nextQuizQuestion() {
  state.quiz.index += 1;
  renderQuizQuestion();
}

function finishQuiz() {
  const { score, questions } = state.quiz;
  const total = questions.length;
  const verdict = score === total ? "Scam-proof! You spotted every one." : score >= total - 1 ? "Sharp eyes. Just one slipped past." : "Scammers rely on speed. Slow down, check the sender and the real link.";
  document.getElementById("quiz-progress").textContent = "Finished";
  document.getElementById("quiz-card").innerHTML = `
    <div class="text-center py-6">
      <span class="material-symbols-outlined text-[48px] text-primary">emoji_events</span>
      <div class="font-headline text-4xl font-extrabold text-on-surface mt-2">${score} / ${total}</div>
      <p class="text-sm text-on-surface-variant mt-2">${verdict}</p>
      <button onclick="startQuiz()" class="mt-6 px-5 py-2 rounded-full bg-primary text-on-primary hover:bg-primary-container text-xs font-bold inline-flex items-center gap-1.5 shadow-sm">
        <span class="material-symbols-outlined text-[16px]">replay</span>Play again
      </button>
    </div>`;
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
