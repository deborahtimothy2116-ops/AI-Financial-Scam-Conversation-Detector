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
  registerServiceWorker();
  receiveSharedContent();
});

// ---------------------------------------------------------------------------
// Installable app: receive messages / screenshots shared from WhatsApp, SMS, Gallery
// ---------------------------------------------------------------------------
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
  }
}

async function receiveSharedContent() {
  const params = new URLSearchParams(window.location.search);
  let text = params.get("text") || "";
  let file = null;

  if (params.get("shared") === "1" && "caches" in window) {
    try {
      const inbox = await caches.open("scamshield-share-inbox");
      const textRes = await inbox.match("/shared/text");
      if (textRes) text = await textRes.text();
      const fileRes = await inbox.match("/shared/file");
      if (fileRes) {
        const blob = await fileRes.blob();
        const name = decodeURIComponent(fileRes.headers.get("X-File-Name") || "screenshot");
        file = new File([blob], name, { type: blob.type || "image/png" });
      }
      await caches.delete("scamshield-share-inbox");
    } catch (e) {
      // Nothing shared, or storage unavailable.
    }
  }
  if (!text.trim() && !file) return;

  history.replaceState(null, "", "/");
  if (file) {
    setScanMode("image");
    setUploadedFile(file);
  } else {
    setScanMode("text");
    document.getElementById("messageInput").value = text.trim().slice(0, 2500);
    updateCharCount();
  }
  showToast("Shared message received. Scanning now.", "info");
  startScan();
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
const VIEWS = ["scan", "processing", "result", "call", "payment", "history", "community", "quiz", "emergency"];
// Views that belong to a nav tab (processing/result count as "scan")
const NAV_FOR_VIEW = { scan: "scan", processing: "scan", result: "scan", call: "call", payment: "payment", history: "history", community: "community", quiz: "quiz", emergency: "emergency" };

function highlightNav(viewName) {
  const active = NAV_FOR_VIEW[viewName];
  ["scan", "call", "payment", "community", "emergency", "history", "quiz"].forEach((tab) => {
    const on = tab === active;
    const side = document.getElementById(`nav-${tab}`);
    if (side) side.classList.toggle("side-link-active", on);
    const phone = document.getElementById(`mnav-${tab}`);
    if (phone) {
      phone.classList.toggle("text-primary", on);
      phone.classList.toggle("border-primary", on);
      phone.classList.toggle("border-transparent", !on);
    }
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
  if (viewName === "call" && !state.callQuestions) loadCallQuestions();
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
    authBtnLabel.textContent = "Sign in";
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
  ["text", "image"].forEach((key) => {
    const el = document.getElementById(`tab-${key}`);
    el.classList.toggle("tab-active", key === mode);
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
      const color = i < done ? "text-tertiary" : i === done ? "text-primary" : "text-outline";
      const text = i <= done ? "text-on-surface" : "text-on-surface-variant";
      return `<li class="flex items-start gap-2 ${text}"><span class="material-symbols-outlined text-[18px] ${color} ${i === done ? "animate-spin" : ""}">${icon}</span>${escapeHtml(label)}</li>`;
    })
    .join("");
  const pct = Math.round((done / total) * 100);
  document.getElementById("scanner-percent").textContent = `${pct}%`;
  document.getElementById("scanner-progress").style.width = `${pct}%`;
}

function startScannerAnimation(mode, text) {
  const labels = SCAN_CHECKS[mode];
  const doc = document.getElementById("scanner-doc");
  const img = document.getElementById("scanner-image");
  document.getElementById("scanner-mode").textContent = mode === "image" ? "Scanning screenshot" : "Scanning message";
  document.getElementById("scanner-dot").className = "w-2 h-2 rounded-full bg-primary animate-pulse";
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
  const dot = { SCAM: "bg-error", SUSPICIOUS: "bg-amber-500", SAFE: "bg-tertiary" }[verdict];
  document.getElementById("scanner-dot").className = `w-2 h-2 rounded-full ${dot}`;
  document.getElementById("scanner-mode").textContent = "Scan complete";
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
// Check a call
// ---------------------------------------------------------------------------
async function loadCallQuestions() {
  try {
    const res = await fetch(`${state.apiBaseUrl}/call-check/questions`);
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not load questions");
    state.callQuestions = data.data;
    state.callAnswers = {};
    renderCallQuestions();
  } catch (err) {
    document.getElementById("call-questions").innerHTML = `<li class="p-5 text-sm text-error">${escapeHtml(err.message)}. If they ask for money or an OTP, hang up and call 1930.</li>`;
  }
}

function renderCallQuestions() {
  document.getElementById("call-questions").innerHTML = state.callQuestions
    .map((q, i) => {
      const answer = state.callAnswers[q.id];
      const btn = (value, label) => {
        const on = answer === value;
        const onCls = value ? "bg-error text-on-error border-error" : "bg-primary-fixed text-primary border-primary";
        return `<button onclick="answerCall('${q.id}', ${value})" class="h-9 w-16 rounded-md border text-sm font-semibold ${on ? onCls : "bg-surface-container-lowest text-on-surface border-outline-variant hover:bg-surface-container-low"}">${label}</button>`;
      };
      return `
        <li class="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4">
          <span class="flex-1 text-sm text-on-surface"><span class="text-on-surface-variant mr-1">${i + 1}.</span>${escapeHtml(q.text)}</span>
          <span class="flex gap-2 shrink-0">${btn(true, "Yes")}${btn(false, "No")}</span>
        </li>`;
    })
    .join("");
}

async function answerCall(id, value) {
  state.callAnswers[id] = value;
  renderCallQuestions();
  try {
    const res = await fetch(`${state.apiBaseUrl}/call-check/assess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: state.callAnswers }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not assess the call");
    renderCallResult(data.data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderCallResult(r) {
  const style = VERDICT_STYLES[r.verdict];
  document.getElementById("call-result").className = `panel border-l-4 lg:sticky lg:top-16 ${style.border}`;
  document.getElementById("call-headline").textContent = r.headline;
  document.getElementById("call-verdict-row").classList.remove("hidden");
  const tag = document.getElementById("call-verdict-tag");
  tag.className = style.tag;
  tag.textContent = `${style.word} · ${r.score}/100`;
  document.getElementById("call-type").textContent = r.scam_type || "";
  document.getElementById("call-details").classList.remove("hidden");
  document.getElementById("call-say").textContent = r.say_this;
  document.getElementById("call-do").innerHTML = r.do_now.length
    ? r.do_now.map((step, i) => `<li class="flex gap-3"><span class="w-5 h-5 rounded-full bg-surface-container text-on-surface-variant text-[11px] font-semibold flex items-center justify-center shrink-0 mt-0.5">${i + 1}</span><span>${escapeHtml(step)}</span></li>`).join("")
    : `<li class="text-on-surface-variant">Keep going with the questions as the call continues.</li>`;
  document.getElementById("call-reasons").innerHTML = r.reasons.length
    ? r.reasons.map((x) => `<li><span class="font-semibold text-on-surface">${escapeHtml(x.question)}</span> ${escapeHtml(x.why)}</li>`).join("")
    : `<li>No warning signs answered yet.</li>`;
}

function resetCallCheck() {
  state.callAnswers = {};
  if (state.callQuestions) renderCallQuestions();
  document.getElementById("call-result").className = "panel border-l-4 border-l-outline-variant lg:sticky lg:top-16";
  document.getElementById("call-headline").textContent = "Answer the questions to see an assessment.";
  document.getElementById("call-verdict-row").classList.add("hidden");
  document.getElementById("call-details").classList.add("hidden");
}

// ---------------------------------------------------------------------------
// Verify a payment
// ---------------------------------------------------------------------------
const PAY_STATUS = {
  red_flags: { tag: "tag tag-negative", word: "Red flags", border: "border-l-error" },
  caution: { tag: "tag tag-critical", word: "Check first", border: "border-l-amber-500" },
  no_obvious_flags: { tag: "tag tag-neutral", word: "Not proof", border: "border-l-outline" },
};
const FLAG_TAGS = { high: ["tag tag-negative", "High"], medium: ["tag tag-critical", "Medium"], low: ["tag tag-info", "Low"] };

function setPaymentFile(e) {
  state.paymentFile = e.target.files && e.target.files[0] ? e.target.files[0] : null;
  document.getElementById("pay-file-label").textContent = state.paymentFile ? state.paymentFile.name : "Choose screenshot";
}

async function checkPaymentProof() {
  const text = document.getElementById("pay-text").value.trim();
  const amount = document.getElementById("pay-amount").value;
  if (!state.paymentFile && !text) {
    showToast("Choose the payment screenshot or paste its text first.", "error");
    return;
  }
  const btn = document.getElementById("btn-check-payment");
  btn.disabled = true;
  btn.classList.add("opacity-60");
  try {
    const form = new FormData();
    if (state.paymentFile) form.append("file", state.paymentFile);
    else form.append("text", text);
    if (amount) form.append("expected_amount", amount);
    const res = await fetch(`${state.apiBaseUrl}/payment-proof/check`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Could not check the payment");
    renderPaymentResult(data.data);
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.classList.remove("opacity-60");
  }
}

function renderPaymentResult(r) {
  const s = PAY_STATUS[r.status];
  const box = document.getElementById("pay-result");
  box.className = `panel border-l-4 ${s.border}`;
  document.getElementById("pay-headline").textContent = r.headline;
  const tag = document.getElementById("pay-tag");
  tag.className = s.tag;
  tag.textContent = s.word;
  const found = [
    ["Amount", r.found.amounts.join(", ") || "Not found"],
    ["Reference (UTR)", r.found.reference_numbers.join(", ") || "Not found"],
    ["Date", r.found.dates.join(", ") || "Not found"],
  ];
  document.getElementById("pay-found").innerHTML = found
    .map(([k, v]) => `<dt class="text-on-surface-variant">${k}</dt><dd class="text-on-surface font-medium">${escapeHtml(v)}</dd>`)
    .join("");
  document.getElementById("pay-flags").innerHTML = r.flags.length
    ? r.flags.map((f) => {
        const [cls, word] = FLAG_TAGS[f.severity] || FLAG_TAGS.low;
        return `<tr><td><span class="${cls}">${word}</span></td><td><div class="font-semibold text-on-surface">${escapeHtml(f.title)}</div><div class="text-xs text-on-surface-variant mt-0.5">${escapeHtml(f.detail)}</div></td></tr>`;
      }).join("")
    : `<tr><td colspan="2" class="text-on-surface-variant">No red flags in the screenshot text. That still doesn't prove the money arrived.</td></tr>`;
  document.getElementById("pay-steps").innerHTML = r.verify_steps
    .map((step, i) => `<li class="flex gap-3"><span class="w-5 h-5 rounded-full bg-surface-container text-on-surface-variant text-[11px] font-semibold flex items-center justify-center shrink-0 mt-0.5">${i + 1}</span><span>${escapeHtml(step)}</span></li>`)
    .join("");
  box.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------
const VERDICT_STYLES = {
  SCAM: { tag: "tag tag-negative", border: "border-l-error", bar: "bg-error", word: "Scam", text: "text-error" },
  SUSPICIOUS: { tag: "tag tag-critical", border: "border-l-amber-500", bar: "bg-amber-500", word: "Suspicious", text: "text-amber-700" },
  SAFE: { tag: "tag tag-positive", border: "border-l-tertiary", bar: "bg-tertiary", word: "Safe", text: "text-tertiary" },
};
const SEVERITY_TAGS = {
  CRITICAL: ["tag tag-negative", "Critical"],
  HIGH: ["tag tag-negative", "High"],
  MEDIUM: ["tag tag-critical", "Medium"],
  LOW: ["tag tag-info", "Low"],
};

// Business UI: drop decorative emoji the recommendation texts start with.
function plainText(text) {
  return String(text || "").replace(/[\p{Extended_Pictographic}\uFE0F\u200D]/gu, "").replace(/\s{2,}/g, " ").trim();
}

function formatDateTime(value) {
  const d = value ? new Date(value) : new Date();
  return d.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function renderResultView(analysis) {
  if (!analysis) return;
  state.currentAnalysis = analysis;
  const score = Math.round(analysis.risk ? analysis.risk.score : analysis.risk_score || 0);
  const verdict = analysis.verdict || (score >= 60 ? "SCAM" : score >= 30 ? "SUSPICIOUS" : "SAFE");
  const style = VERDICT_STYLES[verdict];
  const indicators = analysis.indicators || [];
  const links = analysis.link_xray || [];
  const isScreenshot = analysis.input_type === "screenshot";

  // Header
  document.getElementById("result-header").className = `panel border-l-4 mb-6 ${style.border}`;
  document.getElementById("result-meta").textContent = `Scan result · ${isScreenshot ? "Screenshot" : "Pasted text"} · ${formatDateTime(analysis.created_at)}`;
  document.getElementById("result-title").textContent =
    verdict === "SAFE" ? "No warning signs found" : analysis.category_title || "Suspicious message";
  const tag = document.getElementById("result-verdict-tag");
  tag.className = style.tag;
  tag.textContent = style.word;
  document.getElementById("result-verdict-label").textContent = (analysis.verdict_label || "").replace(/^\w+ – /, "");

  // KPIs
  const kpiVerdict = document.getElementById("kpi-verdict");
  kpiVerdict.textContent = style.word;
  kpiVerdict.className = `kpi-value ${style.text}`;
  document.getElementById("kpi-score").textContent = score;
  const bar = document.getElementById("kpi-score-bar");
  bar.className = `h-full rounded ${style.bar}`;
  bar.style.width = `${score}%`;
  document.getElementById("kpi-flags").textContent = indicators.length;
  const dangerous = links.filter((l) => l.risk === "danger").length;
  document.getElementById("kpi-links").innerHTML =
    `${links.length}${dangerous ? ` <span class="text-sm font-medium text-error">(${dangerous} dangerous)</span>` : ""}`;

  // Message with highlights
  const rawText = analysis.raw_text || analysis.cleaned_text || "";
  const highlights = analysis.highlights || [];
  document.getElementById("result-raw-text-quote").innerHTML = renderHighlightedText(rawText, highlights);
  document.getElementById("result-highlight-legend").classList.toggle("hidden", highlights.length === 0);
  document.getElementById("result-input-source-badge").textContent = isScreenshot ? "Read from screenshot" : "Pasted text";

  // Findings table
  document.getElementById("result-findings-count").textContent = indicators.length ? `${indicators.length} found` : "";
  document.getElementById("result-red-flags").innerHTML = indicators.length
    ? indicators
        .map((ind) => {
          const [cls, word] = SEVERITY_TAGS[String(ind.severity).toUpperCase()] || SEVERITY_TAGS.LOW;
          return `
          <tr>
            <td><span class="${cls}">${word}</span></td>
            <td>
              <div class="font-semibold text-on-surface">${escapeHtml(ind.title || "")}</div>
              <div class="text-xs text-on-surface-variant leading-relaxed mt-0.5">${escapeHtml(ind.description || "")}</div>
            </td>
          </tr>`;
        })
        .join("")
    : `<tr><td colspan="2" class="text-on-surface-variant">
         <span class="inline-flex items-center gap-2"><span class="material-symbols-outlined text-tertiary text-[18px]">check_circle</span>
         No requests for money, OTPs or passwords, no suspicious links, and no pressure or threats were found.</span>
       </td></tr>`;

  // Link analysis
  renderLinkXray(links);

  // Recommended actions
  document.getElementById("result-recommendations-list").innerHTML = (analysis.recommendations || [])
    .map((rec, i) => `
      <li class="flex items-start gap-3">
        <span class="w-5 h-5 rounded-full bg-surface-container text-on-surface-variant text-[11px] font-semibold flex items-center justify-center shrink-0 mt-0.5">${i + 1}</span>
        <span class="text-on-surface leading-snug">${escapeHtml(plainText(typeof rec === "string" ? rec : rec.text))}</span>
      </li>`)
    .join("");

  // Classification
  document.getElementById("result-category").textContent = verdict === "SAFE" ? "Not a scam pattern" : analysis.category_title || "-";
  const lang = analysis.detected_language || (analysis.language && analysis.language.code) || "en";
  document.getElementById("result-language").textContent = lang === "ta" ? "Tamil" : lang === "en" ? "English" : lang;
  document.getElementById("result-source").textContent = isScreenshot ? "Screenshot (text recognition)" : "Pasted text";

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
      <tr><td colspan="5" class="py-12">
        <div class="flex flex-col items-center text-center gap-2">
          <span class="material-symbols-outlined text-[36px] text-outline">lock</span>
          <p class="text-sm font-semibold text-on-surface">Sign in to keep a scan history</p>
          <p class="text-xs text-on-surface-variant max-w-md">Scans without an account are checked but not stored.</p>
          <button onclick="openAuthModal('login')" class="btn-primary mt-2">Sign in or register</button>
        </div>
      </td></tr>`;
    return;
  }

  container.innerHTML = `<tr><td colspan="5" class="text-center text-xs text-on-surface-variant py-8">Loading scans...</td></tr>`;

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
    container.innerHTML = `<tr><td colspan="5" class="text-xs text-error font-semibold py-6">Could not load scan history: ${escapeHtml(err.message)}</td></tr>`;
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

  container.innerHTML = items
    .map((item) => {
      const score = Math.round(item.risk_score);
      const verdict = score >= 60 ? "SCAM" : score >= 30 ? "SUSPICIOUS" : "SAFE";
      const style = VERDICT_STYLES[verdict];
      return `
        <tr class="hover:bg-surface-container-low">
          <td class="text-on-surface-variant whitespace-nowrap">${escapeHtml(formatDateTime(item.created_at))}</td>
          <td><span class="${style.tag}">${style.word}</span></td>
          <td class="max-w-0 w-full">
            <div class="text-on-surface truncate">${escapeHtml(item.snippet)}</div>
            <div class="text-xs text-on-surface-variant truncate">${escapeHtml(verdict === "SAFE" ? "No scam pattern" : item.category_title || item.scam_category)}</div>
          </td>
          <td class="text-right font-semibold ${style.text}">${score}</td>
          <td class="text-right whitespace-nowrap">
            <button onclick="viewHistoryDetail('${escapeHtml(item.id)}')" class="btn-ghost text-primary">Open</button>
            <button onclick="deleteHistoryItem('${escapeHtml(item.id)}')" class="btn-ghost" title="Delete"><span class="material-symbols-outlined text-[18px]">delete</span></button>
          </td>
        </tr>`;
    })
    .join("");
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
      btn.classList.toggle("seg-active", f === filter);
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
  danger: { tag: "tag tag-negative", label: "Dangerous" },
  caution: { tag: "tag tag-critical", label: "Caution" },
  unknown: { tag: "tag tag-neutral", label: "Unverified" },
  safe: { tag: "tag tag-positive", label: "Official" },
};
const FLAG_ICON = { high: "error", medium: "warning", low: "info", good: "check_circle", info: "info" };
const FLAG_COLOR = { high: "text-error", medium: "text-amber-600", low: "text-sky-700", good: "text-emerald-600", info: "text-on-surface-variant" };

function renderLinkXray(reports) {
  const section = document.getElementById("result-link-xray-section");
  const body = document.getElementById("result-link-xray-list");
  section.classList.toggle("hidden", reports.length === 0);
  body.innerHTML = reports
    .map((r) => {
      const s = XRAY_STYLES[r.risk] || XRAY_STYLES.unknown;
      const issues = r.flags.filter((f) => f.severity !== "good");
      const list = issues.length
        ? `<ul class="space-y-1">${issues.map((f) => `<li title="${escapeHtml(f.detail)}"><span class="${FLAG_COLOR[f.severity] || ""} font-semibold">${escapeHtml(f.title)}.</span> <span class="text-on-surface-variant">${escapeHtml(f.detail)}</span></li>`).join("")}</ul>`
        : `<span class="text-on-surface-variant">${r.risk === "safe" ? "Official domain" : "No known tricks; not a recognised official domain"}</span>`;
      return `
        <tr>
          <td class="font-code text-xs break-all text-on-surface-variant max-w-[14rem]">${escapeHtml(r.link)}</td>
          <td class="font-semibold text-on-surface break-all">${escapeHtml(r.real_domain)}${r.looks_like ? `<div class="text-xs font-normal text-error">Imitates ${escapeHtml(r.looks_like)}</div>` : ""}</td>
          <td><span class="${s.tag}">${s.label}</span></td>
          <td class="text-xs leading-relaxed">${list}</td>
        </tr>`;
    })
    .join("");
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
  now: { chip: "tag tag-negative", label: "Do now" },
  today: { chip: "tag tag-critical", label: "Today" },
  later: { chip: "tag tag-neutral", label: "Next days" },
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
      <button onclick="loadEmergencyGuide('${escapeHtml(key)}')" class="px-3 py-1.5 rounded-md text-xs font-semibold border transition-all ${
 key === guide.incident_type ? "bg-error text-on-error border-error" : "bg-surface-container-lowest text-on-surface border-outline-variant/40 hover:bg-surface-container"
      }">${escapeHtml(label)}</button>`)
    .join("");

  document.getElementById("emergency-steps").innerHTML = guide.steps
    .map((step, i) => {
      const p = PRIORITY_STYLES[step.priority] || PRIORITY_STYLES.later;
      const checked = done.has(step.title);
      const action = step.action
        ? `<a href="${escapeHtml(step.action.href)}" ${step.action.href.startsWith("http") ? 'target="_blank" rel="noopener"' : ""} class="inline-flex items-center gap-1 mt-2 px-3 py-1 rounded-md bg-primary text-on-primary text-[11px] font-semibold"><span class="material-symbols-outlined text-[14px]">${step.action.href.startsWith("tel:") ? "call" : "open_in_new"}</span>${escapeHtml(step.action.label)}</a>`
        : "";
      return `
        <label class="flex items-start gap-3 p-3 rounded-lg border ${checked ? "bg-emerald-50 border-emerald-300" : "bg-surface-container-low border-surface-container"} cursor-pointer">
          <input type="checkbox" ${checked ? "checked" : ""} onchange="toggleEmergencyStep(${i}, this.checked)" class="mt-1 w-4 h-4 accent-emerald-600 shrink-0"/>
          <span class="flex-1 min-w-0">
            <span class="flex items-center gap-2 flex-wrap">
              <span class="${p.chip}">${p.label}</span>
              <span class="text-sm font-semibold text-on-surface ${checked ? "line-through opacity-60" : ""}">${escapeHtml(step.title)}</span>
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
      .map(([c, n]) => `<span class="px-2 py-0.5 rounded-md bg-surface-container-lowest/70 text-[11px] font-semibold">${escapeHtml(labels[c] || c)} &times; ${n}</span>`)
      .join(" ");
    const last = r.last_reported ? new Date(r.last_reported).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : null;
    out.innerHTML = `
      <div class="p-4 rounded-lg border ${s.box}">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <div class="flex items-center gap-2 font-semibold text-sm"><span class="material-symbols-outlined text-[22px]">${s.icon}</span>${s.title}</div>
          <span class="font-code text-xs font-semibold">${escapeHtml(r.identifier_type.toUpperCase())}: ${escapeHtml(r.identifier)}</span>
        </div>
        ${r.report_count ? `<div class="text-2xl font-semibold mt-2">${r.report_count} report${r.report_count === 1 ? "" : "s"}</div>` : ""}
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
  { verdict: "SAFE", style: "border border-outline-variant bg-surface-container-lowest hover:border-tertiary hover:bg-tertiary-container text-tertiary", icon: "verified_user" },
  { verdict: "SUSPICIOUS", style: "border border-outline-variant bg-surface-container-lowest hover:border-amber-500 hover:bg-amber-50 text-amber-700", icon: "gpp_maybe" },
  { verdict: "SCAM", style: "border border-outline-variant bg-surface-container-lowest hover:border-error hover:bg-error-container text-error", icon: "dangerous" },
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
      <span class="px-2.5 py-1 rounded-md bg-surface-container text-on-surface-variant font-semibold">${escapeHtml(q.channel)}</span>
      <span class="text-on-surface-variant">From:</span>
      <span class="font-code font-semibold text-on-surface break-all">${escapeHtml(q.sender)}</span>
    </div>
    <div id="quiz-message" class="p-4 rounded-lg rounded-tl-sm bg-surface-container-low border border-outline-variant text-sm text-on-surface leading-loose mb-6 whitespace-pre-line">${escapeHtml(q.message)}</div>
    <div class="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-2">Your call</div>
    <div class="grid grid-cols-3 gap-2 sm:gap-3">
      ${QUIZ_CHOICES.map((c) => `
        <button onclick="answerQuiz('${c.verdict}')" class="quiz-choice px-3 py-3 rounded-lg font-semibold text-xs sm:text-sm flex items-center justify-center gap-1.5 transition-all ${c.style}">
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
      ? `<div class="flex flex-wrap gap-1.5 mt-3">${r.red_flags.map((f) => `<span class="px-2 py-0.5 rounded-md bg-error-container text-on-error-container text-[11px] font-semibold">${escapeHtml(f)}</span>`).join("")}</div>`
      : "";
    document.getElementById("quiz-feedback").innerHTML = `
      <div class="mt-6 p-4 rounded-lg border ${r.correct ? "bg-emerald-50 border-emerald-300" : "bg-error-container border-error/30"}">
        <div class="flex items-center gap-2 font-semibold text-sm ${r.correct ? "text-emerald-800" : "text-on-error-container"}">
          <span class="material-symbols-outlined text-[20px]">${r.correct ? "celebration" : "school"}</span>
          ${r.correct ? "Correct!" : `Not quite. You said ${escapeHtml(r.guess)}.`}
        </div>
        <div class="text-sm font-semibold text-on-surface mt-2">${escapeHtml(r.answer_label)}</div>
        <p class="text-xs text-on-surface-variant mt-1 leading-relaxed">${escapeHtml(r.lesson)}</p>
        ${flags}
      </div>
      <div class="flex justify-end mt-4">
        <button onclick="${last ? "finishQuiz()" : "nextQuizQuestion()"}" class="px-5 py-2 rounded-md bg-primary text-on-primary hover:bg-primary-container text-xs font-semibold flex items-center gap-1.5 ">
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
      <div class="font-headline text-4xl font-semibold text-on-surface mt-2">${score} / ${total}</div>
      <p class="text-sm text-on-surface-variant mt-2">${verdict}</p>
      <button onclick="startQuiz()" class="mt-6 px-5 py-2 rounded-md bg-primary text-on-primary hover:bg-primary-container text-xs font-semibold inline-flex items-center gap-1.5 ">
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
