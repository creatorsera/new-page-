"""
app.py — MailHunter router
Registers all three pages and provides a sidebar collective export button.
"""
import streamlit as st
from utils import (build_xlsx_collective, fetch_disposable_domains)
from datetime import datetime

st.set_page_config(
    page_title="MailHunter",
    page_icon="✉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c0a1a 0%, #13102e 50%, #0f0d23 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
    }
    [data-testid="stSidebar"] [class*="css"] { color: #ccc !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        color: #ccc !important;
        border-radius: 6px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        width: 100% !important;
        margin-bottom: 2px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.08) !important;
        border-color: rgba(255,255,255,0.12) !important;
        color: #fff !important;
    }
    [data-testid="stSidebar"] .stDownloadButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        border: none !important;
        color: #fff !important;
        border-radius: 6px !important;
        font-size: 12.5px !important;
        font-weight: 700 !important;
        width: 100% !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.3), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    }
    [data-testid="stSidebar"] .stDownloadButton > button:hover {
        box-shadow: 0 6px 30px rgba(99,102,241,0.45), inset 0 1px 0 rgba(255,255,255,0.2) !important;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.06) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('''
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
        <div style="width:38px;height:38px;border-radius:11px;
            background:linear-gradient(135deg,#6366f1,#a78bfa);
            display:flex;align-items:center;justify-content:center;
            font-size:18px;flex-shrink:0;
            box-shadow:0 4px 16px rgba(99,102,241,0.35)">✉</div>
        <div>
            <span style="font-size:17px;font-weight:800;color:#fff;letter-spacing:-.3px">MailHunter</span>
            <span style="font-size:10px;color:#6366f1;font-weight:600;
                background:rgba(129,140,248,0.15);padding:2px 8px;
                border-radius:4px;margin-left:8px">v2.0</span>
        </div>
    </div>
    <div style="font-size:10px;color:#475569;margin-bottom:16px">three-tool email suite</div>
    ''', unsafe_allow_html=True)

    st.divider()

    scraper_data = st.session_state.get("scraper_results", {})
    fb_data      = st.session_state.get("fb_results", {})
    val_data     = st.session_state.get("val_results", [])
    has_any = bool(scraper_data or fb_data or val_data)

    st.markdown('<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#475569;margin-bottom:10px">Data Status</div>', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="display:grid;grid-template-columns:1fr;gap:6px;margin-bottom:14px">
        <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
            border-radius:8px;background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.06);font-size:11.5px;color:#94a3b8">
            <span style="width:7px;height:7px;border-radius:50%;flex-shrink:0;
                {"background:#34d399;box-shadow:0 0 8px rgba(52,211,153,0.5)" if scraper_data else "background:#334155"}"></span>
            <span>Scraper</span>
            <span style="margin-left:auto;font-weight:700;color:#e2e8f0">{len(scraper_data)}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
            border-radius:8px;background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.06);font-size:11.5px;color:#94a3b8">
            <span style="width:7px;height:7px;border-radius:50%;flex-shrink:0;
                {"background:#34d399;box-shadow:0 0 8px rgba(52,211,153,0.5)" if fb_data else "background:#334155"}"></span>
            <span>Facebook</span>
            <span style="margin-left:auto;font-weight:700;color:#e2e8f0">{len(fb_data)}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
            border-radius:8px;background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.06);font-size:11.5px;color:#94a3b8">
            <span style="width:7px;height:7px;border-radius:50%;flex-shrink:0;
                {"background:#34d399;box-shadow:0 0 8px rgba(52,211,153,0.5)" if val_data else "background:#334155"}"></span>
            <span>Validator</span>
            <span style="margin-left:auto;font-weight:700;color:#e2e8f0">{len(val_data)}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    st.divider()

    st.markdown('<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#475569;margin-bottom:10px">Combined Export</div>', unsafe_allow_html=True)

    if has_any:
        xlsx = build_xlsx_collective(scraper_data, fb_data, val_data)
        st.download_button(
            "⬇  Export All as .xlsx",
            xlsx,
            f"mailhunter_combined_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="collective_export",
        )
        st.markdown('''
        <div style="font-size:9px;color:#334155;margin-top:6px;line-height:1.7">
        6 sheets: Master · Scraper · Facebook<br>
        Validated · All Emails · Stats</div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown('''
        <div style="font-size:11px;color:#334155;line-height:1.7;padding:12px;
            border-radius:8px;background:rgba(255,255,255,0.04);
            border:1px dashed rgba(255,255,255,0.06)">
        Run any tool to unlock<br>the combined export.</div>
        ''', unsafe_allow_html=True)

    st.divider()
    st.markdown('''
    <div style="font-size:9px;color:#1e293b;line-height:1.8">
    Scraper → sitemap-first crawl<br>
    Facebook → page email extraction<br>
    Validator → SMTP + fallback chain</div>
    ''', unsafe_allow_html=True)


# ── Pre-load disposable list ──────────────────────────────────────────────────
fetch_disposable_domains()

# ── Navigation ───────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_scraper.py",   title="Scraper",   icon="🔍", default=True),
    st.Page("pages/2_facebook.py",  title="Facebook",  icon="📘"),
    st.Page("pages/3_validator.py", title="Validator", icon="✅"),
])
pg.run()
