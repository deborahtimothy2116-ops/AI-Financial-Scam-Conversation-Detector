from xml.sax.saxutils import escape
W, H = 1600, 1130
out = []
def add(s): out.append(s)
FONT = "DejaVu Sans, Arial, Helvetica, sans-serif"
ACC, INK, MUT, LINE = "#0a5dc2", "#1b2530", "#566273", "#c3cedb"

def text(x, y, s, size=13, weight="normal", fill=INK, anchor="start"):
    add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')

def box(x, y, w, h, title, lines=(), fill="#ffffff", stroke=LINE, dash=False, tcolor=INK, tsize=14, center=True):
    d = ' stroke-dasharray="6 5"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{d}/>')
    cx = x + w / 2 if center else x + 12
    anchor = "middle" if center else "start"
    total = 18 + 16 * len(lines)
    ty = y + (h - total) / 2 + 14
    text(cx, ty, title, tsize, "bold", tcolor, anchor)
    for i, l in enumerate(lines):
        text(cx, ty + 18 + 16 * i, l, 12, "normal", MUT, anchor)

def container(x, y, w, h, title, subtitle, fill):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{LINE}" stroke-width="1.4"/>')
    text(x + 18, y + 28, title, 17, "bold", INK)
    text(x + w - 18, y + 28, subtitle, 12, "normal", MUT, "end")

def arrow(x1, y1, x2, y2, label=None, dash=False, lx=None, ly=None):
    d = ' stroke-dasharray="6 5"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#6b7887" stroke-width="2"{d} marker-end="url(#arr)"/>')
    if label:
        text(lx if lx is not None else (x1 + x2) / 2 + 8, ly if ly is not None else (y1 + y2) / 2 + 4, label, 12, "normal", MUT)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add('<defs><marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#6b7887"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(60, 52, "ScamShield: System Architecture", 26, "bold", INK)
text(60, 76, "AI financial scam detector · FastAPI backend · installable web app", 14, "normal", MUT)

# ---------- Client layer ----------
container(60, 100, 1180, 150, "Client layer", "frontend/  ·  browser or installed Android app", "#eef3fa")
box(80, 140, 520, 94, "Web app (HTML + JavaScript + Tailwind CSS)",
    ["Scan a message · Result page · Pause-before-you-pay modal",
     "Check a call · Verify a payment · Check number / UPI",
     "Incident response · Scan history · Awareness training"])
box(620, 140, 290, 94, "Installable app (PWA)", ["manifest.webmanifest + icons", "appears in Android Share menu"])
box(930, 140, 290, 94, "Service worker (sw.js)", ["receives shared text & screenshots", "from WhatsApp / SMS / Gallery"])

# ---------- API layer ----------
container(60, 300, 1180, 130, "API layer — FastAPI  /api/v1", "app/api/  ·  JWT auth  ·  JSON", "#f1f1fb")
routers = [("analysis", "scan text / image"), ("history", "past scans"), ("community", "lookup / report"),
           ("emergency", "steps / complaint"), ("tools", "call · payment"), ("pause", "events / stats"),
           ("quiz", "training"), ("auth · health", "login · status")]
bw, gap, x0 = 130, 11, 80
for i, (t, s) in enumerate(routers):
    box(x0 + i * (bw + gap), 344, bw, 66, t, [s], tsize=14)

# ---------- Service layer ----------
container(60, 480, 1180, 330, "Service layer", "app/services/", "#edf6f2")
text(80, 530, "Scan pipeline (scam_detector)", 14, "bold", ACC)
steps = [("OCR", ["screenshot", "to text"]), ("Preprocess", ["clean, extract", "UPI · links · nos."]),
         ("Language", ["EN · HI · TA", "+ multilingual"]), ("Detection", ["rules + checks", "+ link X-ray"]),
         ("Risk engine", ["0–100 score", "→ verdict"]), ("Explain", ["reasons +", "what to do"])]
sw, sg, sx = 104, 20, 80
for i, (t, ls) in enumerate(steps):
    x = sx + i * (sw + sg)
    box(x, 545, sw, 84, t, ls, tsize=13)
    if i < len(steps) - 1:
        arrow(x + sw + 1, 587, x + sw + sg - 1, 587)
# enrichers
text(80, 668, "Result enrichers (attached to every result)", 14, "bold", ACC)
enr = [("Highlighter", "risky phrases"), ("Link X-ray", "real destination"), ("Claim verification", "official checks"), ("Pause check", "SCAM checklist")]
ew, eg = 163, 13
for i, (t, s) in enumerate(enr):
    box(80 + i * (ew + eg), 682, ew, 66, t, [s], tsize=13)
arrow(80 + 4 * (sw + sg) + sw / 2, 630, 80 + 4 * (sw + sg) + sw / 2, 652)
text(80, 780, "Community reports feed the scan: 1–2 reports → at least SUSPICIOUS, 3+ → SCAM", 12, "normal", MUT)
# tools
text(860, 530, "Tools", 14, "bold", ACC)
tools = [("call_check", "live call verdict from yes/no answers"), ("payment_proof", "fake / pending payment screenshots"),
         ("community_service", "normalise & count scam reports"), ("emergency_service", "first-hour steps & complaint draft")]
for i, (t, s) in enumerate(tools):
    box(860, 545 + i * 62, 360, 54, t, [s], tsize=13)

# ---------- Data layer ----------
container(60, 860, 1180, 150, "Data layer — SQLAlchemy ORM", "SQLite (local) / PostgreSQL (Docker)  ·  Alembic migrations 001–003", "#f8f2e8")
tables = [("users", "accounts"), ("analyses", "scans & verdicts"), ("indicators", "findings"), ("recommendations", "actions"),
          ("feedback", "accuracy"), ("scam_reports", "community"), ("pause_events", "pause choices")]
tw, tg = 150, 12
for i, (t, s) in enumerate(tables):
    box(80 + i * (tw + tg), 904, tw, 72, t, [s], tsize=13)

# ---------- vertical flows ----------
arrow(650, 250, 650, 298, "HTTPS · JSON requests", lx=662, ly=279)
arrow(650, 430, 650, 478, "function calls", lx=662, ly=459)
arrow(650, 810, 650, 858, "read / write", lx=662, ly=839)

# ---------- External systems ----------
text(1290, 118, "External", 14, "bold", MUT)
box(1290, 130, 260, 120, "Official channels", ["1930 helpline", "cybercrime.gov.in · Sanchar Saathi", "bank & official apps / websites"],
    fill="#fafbfc", stroke="#8a95a3", dash=True)
arrow(1240, 190, 1288, 190, dash=True)
box(1290, 490, 260, 90, "OCR engines", ["Windows OCR (winocr)", "Tesseract (English + Tamil)"], fill="#fafbfc", stroke="#8a95a3", dash=True)
arrow(1240, 535, 1288, 535, dash=True)
box(1290, 610, 260, 110, "AI providers (optional)", ["Gemini · OpenAI · Claude · Groq", "second opinion; falls back", "to rules if unavailable"],
    fill="#fafbfc", stroke="#8a95a3", dash=True)
arrow(1240, 665, 1288, 665, dash=True)
box(1290, 880, 260, 110, "GitHub Actions CI", ["163 automated tests", "accuracy benchmark", "run on every push"], fill="#fafbfc", stroke="#8a95a3", dash=True)

# ---------- legend ----------
add('<line x1="60" y1="1060" x2="110" y2="1060" stroke="#6b7887" stroke-width="2" marker-end="url(#arr)"/>')
text(120, 1064, "request / data flow", 12, "normal", MUT)
add('<line x1="290" y1="1060" x2="340" y2="1060" stroke="#6b7887" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arr)"/>')
text(350, 1064, "external or optional", 12, "normal", MUT)
text(1550, 1064, "Privacy: links are never opened · screenshots processed in memory · history private per account", 12, "normal", MUT, "end")
add("</svg>")
open(__import__("pathlib").Path(__file__).resolve().parents[1] / "architecture.svg", "w").write("\n".join(out))
