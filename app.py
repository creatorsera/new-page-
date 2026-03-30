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

# ── Sidebar — always visible across all pages ─────────────────────────────────
with st.sidebar:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { background: #111 !important; }
    [data-testid="stSidebar"] * { color: #ccc !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: #1e1e1e !important; border: 1px solid #333 !important;
        color: #ccc !important; border-radius: 6px !important;
        font-size: 12px !important; font-weight: 600 !important;
        width: 100% !important; margin-bottom: 2px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #2a2a2a !important; border-color: #555 !important; color: #fff !important;
    }
    [data-testid="stSidebar"] .stDownloadButton > button {
        background: #16a34a !important; border: none !important;
        color: #fff !important; border-radius: 6px !important;
        font-size: 12px !important; font-weight: 700 !important; width: 100% !important;
    }
    [data-testid="stSidebar"] .stDownloadButton > button:hover { background: #15803d !important; }
    [data-testid="stSidebar"] hr { border-color: #222 !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:17px;font-weight:800;color:#fff;letter-spacing:-.3px;margin-bottom:4px">✉ MailHunter</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:10px;color:#555;margin-bottom:16px">v2.0 · three-tool suite</div>', unsafe_allow_html=True)

    st.divider()

    # Collective export — only available when at least one tool has data
    scraper_data = st.session_state.get("scraper_results", {})
    fb_data      = st.session_state.get("fb_results", {})
    val_data     = st.session_state.get("val_results", [])

    has_any = bool(scraper_data or fb_data or val_data)

    st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#444;margin-bottom:8px">Combined Export</div>', unsafe_allow_html=True)

    if has_any:
        n_scraper = len(scraper_data)
        n_fb      = len(fb_data)
        n_val     = len(val_data)
        st.markdown(
            f'<div style="font-size:11px;color:#666;margin-bottom:8px;line-height:1.7">'
            f'{"✓" if scraper_data else "○"} Scraper: {n_scraper} sites<br>'
            f'{"✓" if fb_data      else "○"} Facebook: {n_fb} pages<br>'
            f'{"✓" if val_data     else "○"} Validator: {n_val} emails'
            f'</div>', unsafe_allow_html=True)

        xlsx = build_xlsx_collective(scraper_data, fb_data, val_data)
        st.download_button(
            "⬇  Export All as .xlsx",
            xlsx,
            f"mailhunter_combined_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="collective_export",
        )
        st.markdown(
            '<div style="font-size:9px;color:#444;margin-top:4px;line-height:1.6">'
            '6 sheets: Master · Scraper · Facebook<br>'
            'Validated · All Emails · Stats'
            '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:11px;color:#444;line-height:1.6">Run any tool to unlock<br>the combined export.</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:9px;color:#333;line-height:1.8">Scraper → finds emails via sitemap<br>Facebook → extracts from FB pages<br>Validator → SMTP checks + fallback</div>', unsafe_allow_html=True)


# ── Pre-load disposable list ──────────────────────────────────────────────────
fetch_disposable_domains()

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_scraper.py",   title="Scraper",   icon="🔍", default=True),
    st.Page("pages/2_facebook.py",  title="Facebook",  icon="📘"),
    st.Page("pages/3_validator.py", title="Validator", icon="✅"),
])
pg.run()
