"""
theme.py — MailHunter unified design system
All three pages import inject_css(accent) to get consistent styling.
Each page gets a unique accent color; everything else is identical.
"""

# Page accent colors
ACCENT = {
    "scraper":   "#111111",   # near-black — neutral, powerful
    "facebook":  "#1877f2",   # FB blue
    "validator": "#16a34a",   # green — deliverability
}

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, sans-serif !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
    padding: 1.2rem 2rem 4rem !important;
    max-width: 100% !important;
    background: #f6f5f2 !important;
}}

/* ── page header ── */
.mh-page-header {{
    display: flex; align-items: center; gap: 12px;
    padding: 14px 20px; background: #fff;
    border: 1px solid #e8e8e4; border-radius: 12px;
    margin-bottom: 16px;
}}
.mh-page-icon {{
    width: 38px; height: 38px; border-radius: 10px;
    background: {accent}; display: flex; align-items: center;
    justify-content: center; font-size: 18px; color: #fff; flex-shrink: 0;
}}
.mh-page-title {{
    font-size: 17px; font-weight: 800; color: #111; letter-spacing: -.4px;
}}
.mh-page-sub {{
    font-size: 11px; color: #aaa; margin-top: 1px; font-weight: 400;
}}

/* ── card ── */
.mh-card {{
    background: #fff; border: 1px solid #e8e8e4;
    border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
}}
.mh-card-sm {{
    background: #fff; border: 1px solid #e8e8e4;
    border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;
}}

/* ── section label ── */
.mh-sec {{
    font-size: 9.5px; font-weight: 700; letter-spacing: 1.3px;
    text-transform: uppercase; color: #c0bfbb;
    display: block; margin-bottom: 6px;
}}

/* ── buttons ── */
.stButton > button {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; border-radius: 8px !important;
    font-size: 12.5px !important; height: 36px !important;
    transition: all 0.13s ease !important;
}}
.stButton > button[kind="primary"] {{
    background: {accent} !important;
    border: 2px solid {accent} !important;
    color: #fff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.15) !important;
}}
.stButton > button[kind="primary"]:hover {{
    opacity: .88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.2) !important;
}}
.stButton > button[kind="primary"]:disabled {{
    background: #e6e6e4 !important; border-color: #e6e6e4 !important;
    color: #bbb !important; box-shadow: none !important; transform: none !important;
    opacity: 1 !important;
}}
.stButton > button[kind="secondary"] {{
    background: #fff !important; border: 1.5px solid #ddd !important; color: #555 !important;
}}
.stButton > button[kind="secondary"]:hover {{
    border-color: {accent} !important; color: {accent} !important; background: #fafaf8 !important;
}}

/* ── big action button ── */
.mh-bigbtn .stButton > button {{
    height: 44px !important; font-size: 14px !important; font-weight: 700 !important;
    letter-spacing: -.2px !important;
}}

/* ── download button ── */
.stDownloadButton > button {{
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: 8px !important; font-size: 12.5px !important; height: 36px !important;
    background: #fff !important; border: 1.5px solid #ddd !important; color: #555 !important;
}}
.stDownloadButton > button:hover {{
    border-color: {accent} !important; color: {accent} !important;
}}

/* ── text inputs ── */
.stTextArea textarea {{
    font-size: 12.5px !important; border-radius: 8px !important;
    border: 1.5px solid #e4e4e0 !important; background: #fafaf8 !important;
    line-height: 1.6 !important; resize: none !important; color: #333 !important;
}}
.stTextArea textarea:focus {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px {accent}18 !important;
}}
.stTextArea textarea::placeholder {{ color: #ccc !important; }}
.stTextInput > div > input {{
    border-radius: 8px !important; border: 1.5px solid #e4e4e0 !important;
    font-size: 13px !important; height: 36px !important; background: #fafaf8 !important;
}}
.stTextInput > div > input:focus {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px {accent}18 !important;
}}

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 2px !important; background: #eeeeed !important;
    border-radius: 8px !important; padding: 3px !important;
    border: 1px solid #e2e2e0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-size: 11.5px !important; font-weight: 600 !important;
    border-radius: 6px !important; padding: 4px 12px !important; color: #999 !important;
}}
.stTabs [aria-selected="true"] {{
    background: #fff !important; color: {accent} !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.08) !important;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

/* ── metric cards ── */
[data-testid="stMetric"] {{
    background: #fff; border: 1px solid #e8e8e4;
    border-radius: 10px; padding: .75rem .9rem !important;
}}
[data-testid="stMetricLabel"] p {{
    font-size: 9.5px !important; font-weight: 700 !important; color: #c0bfbb !important;
    text-transform: uppercase !important; letter-spacing: .6px !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 22px !important; font-weight: 800 !important;
    color: #111 !important; letter-spacing: -.7px !important;
}}

/* ── log box ── */
.mh-log {{
    background: #18181b; border-radius: 8px; padding: 10px 12px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10.5px; line-height: 1.8; max-height: 200px;
    overflow-y: auto; margin-top: 6px;
}}
.mh-log::-webkit-scrollbar {{ width: 4px; }}
.mh-log::-webkit-scrollbar-thumb {{ background: #3f3f46; border-radius: 2px; }}
.ll-site   {{ color: #fff; font-weight: 700; border-top: 1px solid #27272a;
              margin-top: 4px; padding-top: 4px; }}
.ll-site:first-child {{ border-top: none; margin-top: 0; padding-top: 0; }}
.ll-email  {{ color: #4ade80; font-weight: 600; }}
.ll-page   {{ color: #3f3f46; }}
.ll-skip   {{ color: #fb923c; }}
.ll-timing {{ color: #27272a; font-size: 10px; }}
.ll-done   {{ color: #52525b; }}
.ll-info   {{ color: #3f3f46; }}
.ll-warn   {{ color: #f87171; }}

/* ── progress bar ── */
.mh-prog-wrap  {{ margin: 6px 0 4px; }}
.mh-prog-row   {{ display:flex; justify-content:space-between; align-items:center;
                  font-size:11.5px; font-weight:600; color:#333; margin-bottom:5px; }}
.mh-prog-right {{ font-size:11px; color:#aaa; font-weight:400; }}
.mh-prog-track {{ height:3px; background:#eee; border-radius:99px; overflow:hidden; }}
.mh-prog-fill  {{ height:100%; border-radius:99px; transition:width .4s ease; }}
.mh-scan-dot   {{ display:inline-block; width:7px; height:7px; border-radius:50%;
                  margin-right:6px; animation:mhpulse 1.5s infinite; }}
@keyframes mhpulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.2;transform:scale(.8)}} }}

/* ── filter chip bar ── */
.mh-flt .stButton > button {{
    height: 27px !important; font-size: 10.5px !important;
    border-radius: 99px !important; padding: 0 10px !important;
    font-weight: 600 !important; border: 1px solid !important;
}}
.mh-flt .stButton > button[kind="secondary"] {{
    background: #eeeeed !important; border-color: #e0e0dc !important; color: #888 !important;
}}
.mh-flt .stButton > button[kind="secondary"]:hover {{
    background: #e4e4e2 !important; color: #333 !important; border-color: #ccc !important;
}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(1) button[kind="primary"]{{background:#111 !important;border-color:#111 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(2) button[kind="primary"]{{background:#d97706 !important;border-color:#d97706 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(3) button[kind="primary"]{{background:#6366f1 !important;border-color:#6366f1 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(4) button[kind="primary"]{{background:#64748b !important;border-color:#64748b !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(5) button[kind="primary"]{{background:#e11d48 !important;border-color:#e11d48 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(6) button[kind="primary"]{{background:#16a34a !important;border-color:#16a34a !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(7) button[kind="primary"]{{background:#d97706 !important;border-color:#d97706 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(8) button[kind="primary"]{{background:#dc2626 !important;border-color:#dc2626 !important;color:#fff !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(2) button[kind="secondary"]{{color:#92400e !important;background:#fffbeb !important;border-color:#fde68a !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(3) button[kind="secondary"]{{color:#4338ca !important;background:#eef2ff !important;border-color:#c7d2fe !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(4) button[kind="secondary"]{{color:#475569 !important;background:#f1f5f9 !important;border-color:#cbd5e1 !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(5) button[kind="secondary"]{{color:#be123c !important;background:#fff1f2 !important;border-color:#fecdd3 !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(6) button[kind="secondary"]{{color:#15803d !important;background:#f0fdf4 !important;border-color:#bbf7d0 !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(7) button[kind="secondary"]{{color:#92400e !important;background:#fffbeb !important;border-color:#fde68a !important;}}
.mh-flt [data-testid="stHorizontalBlock"]>div:nth-child(8) button[kind="secondary"]{{color:#b91c1c !important;background:#fff5f5 !important;border-color:#fecaca !important;}}

/* ── mode radio ── */
[data-testid="stHorizontalRadio"] {{
    background: #eeeeed !important; border-radius: 10px !important;
    padding: 3px !important; border: 1px solid #e2e2e0 !important;
}}
[data-testid="stHorizontalRadio"] label {{
    font-size: 12px !important; font-weight: 600 !important;
    border-radius: 7px !important; padding: 5px 10px !important;
    color: #999 !important; flex: 1 !important; text-align: center !important;
    cursor: pointer !important;
}}
[data-testid="stHorizontalRadio"] label:has(input:checked) {{
    background: {accent} !important; color: #fff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.15) !important;
}}
[data-testid="stHorizontalRadio"] [data-baseweb="radio"] {{ display: none !important; }}

/* ── mode card ── */
.mh-mode-card {{
    padding: 10px 13px; border-radius: 9px;
    background: #f8f8f6; border: 1px solid #e8e8e4;
    margin: 5px 0 0; display: flex; align-items: flex-start; gap: 10px;
}}
.mh-mode-dot {{ width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }}
.mh-mode-name {{ font-size: 12.5px; font-weight: 700; }}
.mh-mode-tip  {{ font-size: 10.5px; color: #888; margin-top: 2px; line-height: 1.45; }}

/* ── url pills ── */
.mh-pills {{ display:flex; flex-wrap:wrap; gap:3px; margin:5px 0 0; }}
.mh-pill  {{ font-size:10.5px; background:#eeeeed; border:1px solid #e0e0dc;
             border-radius:4px; padding:2px 7px; color:#888; }}

/* ── expander ── */
details {{ border:1px solid #e8e8e4 !important; border-radius:8px !important; background:#fff !important; }}
details > summary {{ font-size:12px !important; font-weight:600 !important; color:#444 !important; padding:9px 13px !important; }}
details[open] > summary {{ border-bottom:1px solid #f0f0ee !important; }}

/* ── divider ── */
hr {{ border-color:#eeeeec !important; margin:10px 0 !important; }}
[data-testid="stSlider"] > div > div > div > div {{ background: {accent} !important; }}

/* ── select/file ── */
[data-testid="stFileUploader"] {{ background:#fff !important; border:1.5px dashed #e4e4e0 !important; border-radius:8px !important; }}

/* ── info/warn banners ── */
.mh-info {{ background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px;
             padding:8px 13px; font-size:12px; color:#15803d; font-weight:600; margin:4px 0; }}
.mh-warn {{ background:#fff1f2; border:1px solid #fecdd3; border-radius:8px;
             padding:8px 13px; font-size:12px; color:#be123c; font-weight:600; margin:4px 0; }}
</style>
"""

def inject_css(page="scraper"):
    """Inject unified CSS with page-specific accent color."""
    import streamlit as st
    accent = ACCENT.get(page, "#111111")
    st.markdown(BASE_CSS.format(accent=accent), unsafe_allow_html=True)

def page_header(icon, title, subtitle, page="scraper"):
    """Render consistent page header across all pages."""
    import streamlit as st
    accent = ACCENT.get(page, "#111111")
    st.markdown(f"""
    <div class="mh-page-header">
      <div class="mh-page-icon" style="background:{accent}">{icon}</div>
      <div>
        <div class="mh-page-title">{title}</div>
        <div class="mh-page-sub">{subtitle}</div>
      </div>
    </div>""", unsafe_allow_html=True)

def render_log(ph, log_lines):
    """Render the dark terminal log — shared by scraper and FB pages."""
    h = ""
    for item, kind in log_lines[-80:]:
        _, text, _, _ = item
        t = str(text)[:90]
        if   kind=="site":   h+=f'<div class="ll-site">[ {t} ]</div>'
        elif kind=="active": h+=f'<div class="ll-page">  &gt; {t}</div>'
        elif kind=="email":  h+=f'<div class="ll-email">  @ {t}</div>'
        elif kind=="timing": h+=f'<div class="ll-timing">    {t}</div>'
        elif kind=="skip":   h+=f'<div class="ll-skip">  ! {t}</div>'
        elif kind=="done":   h+=f'<div class="ll-done">  ok {t}</div>'
        elif kind=="info":   h+=f'<div class="ll-info">  . {t}</div>'
        elif kind=="warn":   h+=f'<div class="ll-warn">  !! {t}</div>'
    ph.markdown(f'<div class="mh-log">{h}</div>', unsafe_allow_html=True)
