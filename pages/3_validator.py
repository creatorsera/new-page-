"""
pages/3_validator.py — Email Validator
Notion-inspired spreadsheet UI with premium refinements.
Validates emails from any source.
Source options: paste / upload CSV / use scraper data / use FB data.
Writes to st.session_state["val_results"].
"""
import streamlit as st
import pandas as pd, io, time
from datetime import datetime

from utils import (
    is_valid_email, tier_key, tier_short, sort_by_tier, pick_best,
    confidence_score, conf_color, val_icon,
    validate_email_full, validate_with_fallback,
    build_xlsx_validator,
)

# ── NOTION-STYLE CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --v-surface: #ffffff;
    --v-surface-alt: #f8fafc;
    --v-surface-dim: #f1f5f9;
    --v-bg: #ffffff;
    --v-border: #e2e8f0;
    --v-border-subtle: #f1f5f9;
    --v-text: #0f172a;
    --v-text-secondary: #64748b;
    --v-text-muted: #94a3b8;
    --v-accent: #6366f1;
    --v-accent-dim: rgba(99,102,241,0.06);
    --v-accent-glow: rgba(99,102,241,0.12);
    --v-success: #10b981;
    --v-success-bg: #f0fdf4;
    --v-success-border: #bbf7d0;
    --v-warning: #f59e0b;
    --v-warning-bg: #fffbeb;
    --v-warning-border: #fde68a;
    --v-danger: #ef4444;
    --v-danger-bg: #fff1f2;
    --v-danger-border: #fecdd3;
    --v-radius: 12px;
    --v-radius-sm: 8px;
    --v-shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --v-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --v-shadow-md: 0 4px 12px rgba(0,0,0,0.07);
}

*, html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.6rem 2.5rem 4rem !important; max-width: 100% !important;
    background: var(--v-bg) !important;
    background-image: radial-gradient(circle at 1px 1px, rgba(0,0,0,0.015) 1px, transparent 0) !important;
    background-size: 24px 24px !important;
}

.val-hdr-title {
    font-size: 22px; font-weight: 900; color: var(--v-text);
    letter-spacing: -0.7px; display: flex; align-items: center; gap: 10px;
}
.val-hdr-sub {
    font-size: 11px; color: var(--v-text-muted); margin-top: 3px; font-weight: 500;
}

.src-btn-row { display: flex; gap: 6px; margin: 14px 0; flex-wrap: wrap; }
.src-chip {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 8px 16px; border-radius: var(--v-radius-sm);
    font-size: 12px; font-weight: 600; cursor: pointer;
    border: 1.5px solid transparent; transition: all 0.2s ease; user-select: none;
}
.src-chip.active {
    background: var(--v-text); color: #fff; border-color: var(--v-text);
    box-shadow: 0 2px 8px rgba(15,23,42,0.15);
}
.src-chip.inactive {
    background: var(--v-surface); color: var(--v-text-secondary);
    border-color: var(--v-border);
}
.src-chip.inactive:hover {
    background: var(--v-surface-alt); border-color: var(--v-accent);
    color: var(--v-accent); transform: translateY(-1px);
}
.src-chip-count {
    font-size: 9px; background: rgba(255,255,255,0.2); padding: 1px 6px;
    border-radius: 4px; font-weight: 700; letter-spacing: 0.3px;
}
.src-chip.inactive .src-chip-count {
    background: var(--v-surface-dim); color: var(--v-text-muted);
}

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: var(--v-radius-sm) !important; font-size: 12px !important;
    height: 38px !important; transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--v-accent) 0%, #7c3aed 100%) !important;
    border: none !important; color: #fff !important;
    box-shadow: 0 2px 10px rgba(99,102,241,0.25), inset 0 1px 0 rgba(255,255,255,0.15) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 20px rgba(99,102,241,0.4), inset 0 1px 0 rgba(255,255,255,0.2) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:disabled {
    background: var(--v-surface-dim) !important; border: none !important;
    color: #cbd5e1 !important; box-shadow: none !important; transform: none !important;
}
.stButton > button[kind="secondary"] {
    background: var(--v-surface) !important; border: 1px solid var(--v-border) !important;
    color: var(--v-text-secondary) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--v-accent) !important; color: var(--v-accent) !important;
    background: var(--v-accent-dim) !important;
}
.stDownloadButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: var(--v-radius-sm) !important; font-size: 12px !important;
    height: 38px !important; background: var(--v-surface) !important;
    border: 1px solid var(--v-border) !important; color: var(--v-text-secondary) !important;
}
.stDownloadButton > button:hover { border-color: var(--v-accent) !important; color: var(--v-accent) !important; }

.stTextArea textarea {
    font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important;
    border-radius: var(--v-radius-sm) !important;
    border: 1.5px solid var(--v-border) !important;
    background: var(--v-surface-alt) !important;
    line-height: 1.7 !important; resize: none !important; color: var(--v-text) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea:focus {
    border-color: var(--v-accent) !important;
    box-shadow: 0 0 0 3px var(--v-accent-glow) !important;
}
.stTextInput > div > input {
    border-radius: var(--v-radius-sm) !important;
    border: 1.5px solid var(--v-border) !important;
    font-size: 13px !important; height: 38px !important;
    background: var(--v-surface-alt) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > input:focus {
    border-color: var(--v-accent) !important;
    box-shadow: 0 0 0 3px var(--v-accent-glow) !important;
}

[data-testid="stMetric"] {
    background: var(--v-surface) !important; border: 1px solid var(--v-border) !important;
    border-radius: var(--v-radius) !important; padding: .85rem 1rem !important;
    box-shadow: var(--v-shadow-sm) !important;
    transition: box-shadow 0.2s, transform 0.2s !important;
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--v-shadow-md) !important; transform: translateY(-1px) !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 9px !important; font-weight: 700 !important;
    color: var(--v-text-muted) !important; text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stMetricValue"] {
    font-size: 24px !important; font-weight: 900 !important;
    color: var(--v-text) !important; letter-spacing: -0.8px !important;
}

.val-prog {
    height: 3px; border-radius: 99px; background: var(--v-surface-dim);
    overflow: hidden; margin: 8px 0;
}
.val-prog-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, var(--v-accent), #a78bfa);
    transition: width 0.5s ease; position: relative; overflow: hidden;
}
.val-prog-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    animation: val-shimmer 1.5s infinite;
}
@keyframes val-shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }

.st-del  {
    color: #15803d; background: var(--v-success-bg); border: 1px solid var(--v-success-border);
    border-radius: 5px; padding: 2px 8px; font-size: 10.5px; font-weight: 700;
    display: inline-block;
}
.st-risk {
    color: #92400e; background: var(--v-warning-bg); border: 1px solid var(--v-warning-border);
    border-radius: 5px; padding: 2px 8px; font-size: 10.5px; font-weight: 700;
    display: inline-block;
}
.st-bad  {
    color: #b91c1c; background: var(--v-danger-bg); border: 1px solid var(--v-danger-border);
    border-radius: 5px; padding: 2px 8px; font-size: 10.5px; font-weight: 700;
    display: inline-block;
}
.st-pend {
    color: var(--v-text-secondary); background: var(--v-surface-dim); border: 1px solid var(--v-border);
    border-radius: 5px; padding: 2px 8px; font-size: 10.5px; font-weight: 600;
    display: inline-block;
}

.info-banner {
    background: var(--v-success-bg); border: 1px solid var(--v-success-border);
    border-radius: var(--v-radius-sm); padding: 10px 16px;
    font-size: 12px; color: #15803d; font-weight: 600; margin: 8px 0;
}
.warn-banner {
    background: var(--v-danger-bg); border: 1px solid var(--v-danger-border);
    border-radius: var(--v-radius-sm); padding: 10px 16px;
    font-size: 12px; color: #be123c; font-weight: 600; margin: 8px 0;
}

hr { border-color: var(--v-border-subtle) !important; margin: 16px 0 !important; }
.sec-lbl {
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: var(--v-text-muted);
    display: block; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k,v in {
    "val_results":[],"val_source":"paste","val_running":False,
    "val_queue":[],"val_idx":0,"val_search":"",
}.items():
    if k not in st.session_state: st.session_state[k]=v

# ── HELPERS ───────────────────────────────────────────────────────────────────
def collect_from_scraper():
    items = []
    for domain, r in st.session_state.get("scraper_results", {}).items():
        best = r.get("Best Email","")
        all_e = r.get("All Emails",[])
        if best or all_e:
            items.append({
                "email": best, "domain": domain,
                "all_emails": all_e,
                "source": "Scraper",
                "val": None, "was_fallback": False,
                "original_email": best, "confidence": None,
            })
    return items

def collect_from_fb():
    items = []
    for handle, r in st.session_state.get("fb_results", {}).items():
        emails = r.get("emails", [])
        if emails:
            best = pick_best(emails) or ""
            items.append({
                "email": best, "domain": handle,
                "all_emails": emails,
                "source": "Facebook",
                "val": None, "was_fallback": False,
                "original_email": best, "confidence": None,
            })
    return items

def collect_from_paste(raw_text):
    items = []
    for line in raw_text.splitlines():
        email = line.strip()
        if is_valid_email(email):
            items.append({
                "email": email, "domain": email.split("@")[-1],
                "all_emails": [email],
                "source": "Manual",
                "val": None, "was_fallback": False,
                "original_email": email, "confidence": None,
            })
    return items

def collect_from_csv(df, email_col):
    items = []
    for email in df[email_col].dropna().astype(str):
        email = email.strip()
        if is_valid_email(email):
            items.append({
                "email": email, "domain": email.split("@")[-1],
                "all_emails": [email],
                "source": "CSV",
                "val": None, "was_fallback": False,
                "original_email": email, "confidence": None,
            })
    return items

# ── HEADER ────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4,1])
with hc1:
    st.markdown(
        '<div class="val-hdr-title">✅ Validator</div>'
        '<div class="val-hdr-sub">SMTP validation &nbsp;·&nbsp; fallback chain &nbsp;·&nbsp; '
        'confidence scoring &nbsp;·&nbsp; DMARC &nbsp;·&nbsp; SPF &nbsp;·&nbsp; catch-all detection</div>',
        unsafe_allow_html=True)
with hc2:
    val_res = st.session_state.get("val_results",[])
    if val_res:
        xlsx = build_xlsx_validator(val_res)
        st.download_button("⬇ Export .xlsx", xlsx,
                           f"validated_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="val_xlsx")
st.divider()

# ── SOURCE SELECTOR ───────────────────────────────────────────────────────────
st.markdown('<span class="sec-lbl">Source</span>', unsafe_allow_html=True)

n_scraper = len([r for r in st.session_state.get("scraper_results",{}).values() if r.get("Best Email") or r.get("All Emails")])
n_fb      = len([r for r in st.session_state.get("fb_results",{}).values() if r.get("emails")])

SOURCES = [
    ("paste",   "✎ Paste emails",       None),
    ("csv",     "⬆ Upload CSV",         None),
    ("scraper", "🔍 Scraper data",       n_scraper),
    ("fb",      "📘 Facebook data",      n_fb),
]

src_cols = st.columns(len(SOURCES))
for col, (key, label, count) in zip(src_cols, SOURCES):
    with col:
        is_active = st.session_state.val_source == key
        count_str = f" ({count})" if count is not None else ""
        if st.button(
            label + count_str,
            key=f"src_{key}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
            disabled=(key == "scraper" and n_scraper == 0) or (key == "fb" and n_fb == 0),
        ):
            st.session_state.val_source = key
            st.session_state.val_results = []
            st.rerun()

source = st.session_state.val_source
st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# ── INPUT BASED ON SOURCE ─────────────────────────────────────────────────────
items_to_validate = []
paste_text = ""
uploaded_csv = None
email_col_sel = None

if source == "paste":
    paste_text = st.text_area(
        "paste_emails", label_visibility="collapsed",
        placeholder="editor@techcrunch.com\npress@forbes.com\ninfo@wired.com\ncontact@example.org",
        height=130, key="paste_emails_ta")
    items_to_validate = collect_from_paste(paste_text)
    if items_to_validate:
        st.caption(f"{len(items_to_validate)} valid email(s) detected")

elif source == "csv":
    uploaded_csv = st.file_uploader("Upload CSV with email column", type=["csv"], key="val_csv_up")
    if uploaded_csv:
        try:
            df_up = pd.read_csv(io.BytesIO(uploaded_csv.read()))
            cols = list(df_up.columns)
            hints = ["email","mail","address","contact"]
            default_col = next((c for c in cols if any(h in c.lower() for h in hints)), cols[0])
            email_col_sel = st.selectbox("Email column", cols, index=cols.index(default_col), key="val_csv_col")
            items_to_validate = collect_from_csv(df_up, email_col_sel)
            st.caption(f"{len(items_to_validate)} valid email(s) in column '{email_col_sel}'")
        except Exception as e:
            st.error(f"CSV error: {e}")

elif source == "scraper":
    items_to_validate = collect_from_scraper()
    if items_to_validate:
        st.markdown(
            f'<div class="info-banner">'
            f'{len(items_to_validate)} domains from last scrape loaded. '
            f'Validator will use the fallback chain — if the best email is not deliverable, '
            f'it tries the next email in tier order automatically.'
            f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warn-banner">No scraper results found. Run the Scraper first.</div>',
                    unsafe_allow_html=True)

elif source == "fb":
    items_to_validate = collect_from_fb()
    if items_to_validate:
        st.markdown(
            f'<div class="info-banner">'
            f'{len(items_to_validate)} Facebook pages with emails loaded.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<div class="warn-banner">No Facebook results found. Run the Facebook extractor first.</div>',
                    unsafe_allow_html=True)

# ── VALIDATE CONTROLS ─────────────────────────────────────────────────────────
st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
vc1, vc2, vc3 = st.columns([2, 1, 1])

with vc1:
    already_validated = len([r for r in st.session_state.val_results if r.get("val")])
    running = st.session_state.get("val_running", False)

    if not running:
        can_start = bool(items_to_validate)
        btn_label = f"Validate {len(items_to_validate)} email(s)" if items_to_validate else "Validate"
        if st.button(btn_label, type="primary", use_container_width=True,
                     disabled=not can_start, key="val_start"):
            st.session_state.val_results  = [{**item, "val":None} for item in items_to_validate]
            st.session_state.val_queue    = list(range(len(items_to_validate)))
            st.session_state.val_idx      = 0
            st.session_state.val_running  = True
            st.rerun()
    else:
        if st.button("Stop", type="secondary", use_container_width=True, key="val_stop"):
            st.session_state.val_running = False; st.rerun()

with vc2:
    if st.session_state.val_results:
        if st.button("Clear", type="secondary", use_container_width=True, key="val_clear"):
            st.session_state.val_results = []; st.rerun()

with vc3:
    st.markdown(
        '<div style="font-size:10px;color:var(--v-text-muted);padding-top:11px;line-height:1.6">'
        'Fallback chain: if best email fails,<br>tries others in tier order</div>',
        unsafe_allow_html=True)

# ── LIVE PROGRESS ─────────────────────────────────────────────────────────────
val_results = st.session_state.get("val_results", [])

if running or val_results:
    n_total     = len(val_results)
    n_validated = sum(1 for r in val_results if r.get("val"))
    n_del   = sum(1 for r in val_results if (r.get("val") or {}).get("status")=="Deliverable")
    n_risk  = sum(1 for r in val_results if (r.get("val") or {}).get("status")=="Risky")
    n_bad   = sum(1 for r in val_results if (r.get("val") or {}).get("status")=="Not Deliverable")
    n_fb_   = sum(1 for r in val_results if r.get("was_fallback"))

    if running:
        pct = round(n_validated / n_total * 100, 1) if n_total else 0
        st.markdown(
            f'<div style="font-size:11px;color:var(--v-text-secondary);margin-bottom:4px;font-weight:500">'
            f'Validating {n_validated} / {n_total}...</div>'
            f'<div class="val-prog"><div class="val-prog-fill" style="width:{pct}%"></div></div>',
            unsafe_allow_html=True)

    if n_validated > 0:
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Checked",     n_validated)
        m2.metric("Deliverable", n_del)
        m3.metric("Risky",       n_risk)
        m4.metric("Failed",      n_bad)
        m5.metric("Fallback ↻",  n_fb_)

# ── RESULTS TABLE ─────────────────────────────────────────────────────────────
if val_results:
    st.divider()

    search = st.text_input("vs", placeholder="Search emails or domains...", label_visibility="collapsed", key="val_search_in")

    rows = []
    for r in val_results:
        val_    = r.get("val") or {}
        status  = val_.get("status","")
        email   = r.get("email","")
        was_fb  = r.get("was_fallback",False)
        orig    = r.get("original_email","")
        conf    = r.get("confidence")
        source  = r.get("source","")

        email_disp = email
        if was_fb: email_disp += " ↻"

        status_icon = {"Deliverable":"✅","Risky":"⚠️","Not Deliverable":"❌"}.get(status,"")
        if not val_: status_icon = "⏳"

        orig_note = f"was: {orig}" if was_fb and orig and orig!=email else ""

        rows.append({
            "#":       len(rows)+1,
            "Status":  status_icon + (" " + status if status else " pending"),
            "Email":   email_disp,
            "Domain":  r.get("domain",""),
            "Source":  source,
            "Tier":    tier_short(email) if email else "—",
            "Score":   conf if conf is not None else "—",
            "Reason":  val_.get("reason","—") if val_ else "—",
            "SPF":     ("✓" if val_.get("spf") else "✗") if val_ else "—",
            "DMARC":   ("✓" if val_.get("dmarc") else "✗") if val_ else "—",
            "Catch-all":("⚠" if val_.get("catch_all") else "—") if val_ else "—",
            "Fallback": "↻ " + orig_note if was_fb else "—",
        })

    df = pd.DataFrame(rows)

    if search:
        m = (df["Email"].str.contains(search,case=False,na=False) |
             df["Domain"].str.contains(search,case=False,na=False))
        df = df[m]

    st.caption(f'Showing **{len(df)}** of {len(val_results)} &nbsp;·&nbsp; '
               f'↻ = fallback email used (original was not deliverable)')

    st.dataframe(df, use_container_width=True, hide_index=True,
                 height=min(600, 44+max(len(df),1)*36),
                 column_config={
                     "#":          st.column_config.NumberColumn("#",       width=40),
                     "Status":     st.column_config.TextColumn("Status",    width=160),
                     "Email":      st.column_config.TextColumn("Email",     width=220),
                     "Domain":     st.column_config.TextColumn("Domain",    width=150),
                     "Source":     st.column_config.TextColumn("Source",    width=75),
                     "Tier":       st.column_config.TextColumn("Tier",      width=65),
                     "Score":      st.column_config.NumberColumn("Score",   width=52),
                     "Reason":     st.column_config.TextColumn("Reason",    width=180),
                     "SPF":        st.column_config.TextColumn("SPF",       width=38),
                     "DMARC":      st.column_config.TextColumn("DMARC",     width=50),
                     "Catch-all":  st.column_config.TextColumn("Catch-all", width=68),
                     "Fallback":   st.column_config.TextColumn("Fallback",  width=170),
                 })

# ── VALIDATION ENGINE ─────────────────────────────────────────────────────────
if st.session_state.get("val_running"):
    val_results = st.session_state.val_results
    idx         = st.session_state.val_idx
    total       = len(val_results)

    if idx >= total:
        st.session_state.val_running = False; st.rerun()
    else:
        row = val_results[idx]
        email    = row.get("email","")
        all_e    = row.get("all_emails",[email]) or [email]
        original = row.get("original_email", email)

        if email and is_valid_email(email):
            chosen, vres, was_fb, orig_status = validate_with_fallback(all_e, email)
            if vres:
                conf_ = confidence_score(chosen, vres)
                st.session_state.val_results[idx].update({
                    "email":      chosen,
                    "val":        vres,
                    "was_fallback": was_fb,
                    "original_email": original if was_fb else email,
                    "confidence": conf_,
                })
        else:
            st.session_state.val_results[idx]["val"] = {
                "status":"Not Deliverable","reason":"Invalid format",
                "spf":False,"dmarc":False,"mx":False,"catch_all":False,
            }

        st.session_state.val_idx = idx + 1
        if st.session_state.val_idx >= total:
            st.session_state.val_running = False
        st.rerun()
