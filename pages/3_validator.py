"""
pages/2_facebook.py — Facebook Email Extractor
Dark terminal-style UI. Full-width live feed of results.
Writes to st.session_state["fb_results"].
"""
import streamlit as st
import time, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from utils import (
    extract_emails, sort_by_tier, pick_best, tier_short, tier_key,
    fetch_page, build_xlsx_facebook,
)

# ── DARK TERMINAL CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --dk-bg: #06060f;
    --dk-surface: #0d0d1a;
    --dk-surface-hover: #14142a;
    --dk-border: #1a1a30;
    --dk-border-subtle: #12122a;
    --dk-accent: #34d399;
    --dk-accent-dim: rgba(52,211,153,0.08);
    --dk-accent-glow: rgba(52,211,153,0.2);
    --dk-fb: #1877f2;
    --dk-fb-dim: rgba(24,119,242,0.12);
    --dk-text: #e2e8f0;
    --dk-text-secondary: #94a3b8;
    --dk-text-muted: #475569;
    --dk-danger: #f87171;
    --dk-warning: #fbbf24;
    --dk-radius: 14px;
    --dk-radius-sm: 10px;
}

*, html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.6rem 2rem 4rem !important; max-width: 100% !important;
    background: var(--dk-bg) !important;
    background-image:
        radial-gradient(ellipse at 15% 10%, rgba(52,211,153,0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 90%, rgba(24,119,242,0.03) 0%, transparent 50%) !important;
}

.stMarkdown, .stCaption, label, p, span, div { color: var(--dk-text-secondary) !important; }

.stTextArea textarea {
    font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
    border-radius: var(--dk-radius-sm) !important;
    border: 1px solid var(--dk-border) !important;
    background: var(--dk-surface) !important; color: var(--dk-text) !important;
    resize: none !important; line-height: 1.7 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea:focus {
    border-color: var(--dk-accent) !important;
    box-shadow: 0 0 0 3px var(--dk-accent-dim), 0 0 20px var(--dk-accent-dim) !important;
}
.stTextArea textarea::placeholder { color: #1e293b !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: var(--dk-radius-sm) !important; font-size: 12.5px !important;
    height: 40px !important; transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    border: none !important; color: #022c22 !important;
    box-shadow: 0 4px 16px rgba(52,211,153,0.25), inset 0 1px 0 rgba(255,255,255,0.2) !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 24px rgba(52,211,153,0.4), inset 0 1px 0 rgba(255,255,255,0.25) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:disabled {
    background: var(--dk-surface) !important; color: #1e293b !important;
    box-shadow: none !important; border: 1px solid var(--dk-border) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--dk-surface) !important; border: 1px solid var(--dk-border) !important;
    color: var(--dk-text-muted) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--dk-accent) !important; color: var(--dk-accent) !important;
    background: var(--dk-accent-dim) !important;
}
.stDownloadButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: var(--dk-radius-sm) !important; font-size: 12px !important;
    height: 38px !important; background: var(--dk-surface) !important;
    border: 1px solid var(--dk-border) !important; color: var(--dk-text-muted) !important;
}
.stDownloadButton > button:hover { border-color: var(--dk-accent) !important; color: var(--dk-accent) !important; }

[data-testid="stMetric"] {
    background: var(--dk-surface) !important; border: 1px solid var(--dk-border) !important;
    border-radius: var(--dk-radius-sm) !important; padding: .8rem 1rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    transition: border-color 0.2s !important;
}
[data-testid="stMetric"]:hover { border-color: var(--dk-border-subtle) !important; }
[data-testid="stMetricLabel"] p {
    font-size: 9px !important; font-weight: 700 !important; color: var(--dk-text-muted) !important;
    text-transform: uppercase !important; letter-spacing: 0.8px !important;
}
[data-testid="stMetricValue"] {
    font-size: 24px !important; font-weight: 900 !important;
    color: var(--dk-text) !important; letter-spacing: -0.8px !important;
}

.fb-card {
    background: var(--dk-surface); border: 1px solid var(--dk-border);
    border-radius: var(--dk-radius-sm); padding: 14px 18px;
    margin-bottom: 10px; transition: all 0.25s ease;
    position: relative; overflow: hidden;
}
.fb-card::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%; transition: background 0.3s;
}
.fb-card:hover {
    border-color: var(--dk-border-subtle);
    background: var(--dk-surface-hover);
    transform: translateX(2px);
}
.fb-card.has-emails::before  { background: var(--dk-accent); box-shadow: 0 0 12px var(--dk-accent-glow); }
.fb-card.blocked::before     { background: var(--dk-danger); }
.fb-card.no-emails::before   { background: #1e293b; }
.fb-handle {
    font-size: 14px; font-weight: 700; color: var(--dk-text);
    font-family: 'JetBrains Mono', monospace; letter-spacing: -0.3px;
}
.fb-status { font-size: 10px; color: var(--dk-text-muted); margin-top: 2px; }
.fb-email {
    font-family: 'JetBrains Mono', monospace; font-size: 11.5px;
    margin-top: 8px; display: flex; align-items: center; gap: 10px;
}
.fb-t1 { color: #fbbf24; font-weight: 700; }
.fb-t2 { color: #60a5fa; font-weight: 600; }
.fb-t3 { color: var(--dk-text-muted); }

.tier-badge {
    font-size: 9px; font-weight: 700; padding: 2px 7px;
    border-radius: 5px; margin-left: 4px; letter-spacing: 0.3px;
}
.tb-t1 { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
.tb-t2 { background: rgba(96,165,250,0.1); color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.tb-t3 { background: rgba(71,85,105,0.1); color: #64748b; border: 1px solid rgba(71,85,105,0.15); }

.scanning-card::before {
    background: var(--dk-warning) !important;
    animation: scan-border 1.5s ease-in-out infinite !important;
}
@keyframes scan-border {
    0%, 100% { box-shadow: 0 0 8px rgba(251,191,36,0.3); }
    50% { box-shadow: 0 0 16px rgba(52,211,153,0.4); background: var(--dk-accent); }
}

.hdr-title {
    font-size: 20px; font-weight: 900; color: #fff;
    letter-spacing: -0.5px; display: flex; align-items: center; gap: 12px;
}
.hdr-box {
    width: 38px; height: 38px; background: var(--dk-fb);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; flex-shrink: 0;
    box-shadow: 0 4px 16px rgba(24,119,242,0.35);
    font-weight: 800; color: #fff;
}
.hdr-sub { font-size: 11px; color: var(--dk-text-muted); margin-top: 4px; font-weight: 500; }

.prog-strip {
    display: flex; align-items: center; gap: 14px;
    padding: 12px 16px; background: var(--dk-surface);
    border: 1px solid var(--dk-border); border-radius: var(--dk-radius-sm);
    margin: 10px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.prog-strip-bar {
    flex: 1; height: 3px; background: var(--dk-border);
    border-radius: 99px; overflow: hidden;
}
.prog-strip-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, var(--dk-accent), #6ee7b7);
    transition: width 0.5s ease; position: relative; overflow: hidden;
}
.prog-strip-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
.prog-strip-text {
    font-size: 11px; color: var(--dk-text-muted);
    font-family: 'JetBrains Mono', monospace; white-space: nowrap;
}

.pulse-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--dk-accent); margin-right: 8px;
    animation: dot-pulse 1.4s ease-in-out infinite;
}
@keyframes dot-pulse {
    0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 6px var(--dk-accent-glow); }
    50% { opacity: 0.2; transform: scale(0.7); box-shadow: none; }
}

.sec-label {
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: var(--dk-text-muted);
    display: block; margin-bottom: 8px;
}
.pill-tag { display: inline-block; font-size: 9.5px; font-weight: 600; padding: 2px 8px; border-radius: 5px; }
hr { border-color: var(--dk-border) !important; margin: 14px 0 !important; }

[data-testid="stToggle"] > label { color: var(--dk-text-secondary) !important; }
[data-testid="stSelectbox"] > div > div { background: var(--dk-surface) !important; border-color: var(--dk-border) !important; color: var(--dk-text) !important; }
[data-testid="stNumberInput"] input { background: var(--dk-surface) !important; border-color: var(--dk-border) !important; color: var(--dk-text) !important; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k,v in {
    "fb_results":{},"fb_running":False,"fb_queue":[],"fb_idx":0,
    "fb_parallel":True,"fb_delay":3,
}.items():
    if k not in st.session_state: st.session_state[k]=v

# ── SCRAPER LOGIC ─────────────────────────────────────────────────────────────
def normalize_handle(raw):
    raw=raw.strip()
    if not raw: return None
    m=re.search(r'facebook\.com/(?:pages/[^/]+/)?([A-Za-z0-9_.]{3,80})', raw)
    if m:
        slug=m.group(1)
        skip={'sharer','share','dialog','login','home','watch','groups','events','marketplace','tr'}
        if slug.lower() not in skip: return slug
    if re.match(r'^[A-Za-z0-9_.]{3,80}$', raw): return raw
    return None

def scrape_fb_handle(handle, delay=3):
    t0=time.time(); all_emails=set(); pages_tried=0; status="no_emails"
    urls_to_try=[
        f"https://www.facebook.com/{handle}",
        f"https://www.facebook.com/{handle}/about",
        f"https://m.facebook.com/{handle}",
    ]
    for url in urls_to_try:
        html,code=fetch_page(url,timeout=12,mobile=True)
        if code==403 or (html and "checkpoint" in html.lower() and "facebook" in url):
            status="blocked"; break
        if html:
            found=extract_emails(html)
            if found: all_emails.update(found)
            pages_tried+=1
        time.sleep(delay)
    if all_emails: status="scraped"
    elif status!="blocked": status="no_emails"
    return {
        "emails":sort_by_tier(all_emails),
        "status":status,
        "time":round(time.time()-t0,1),
        "pages_tried":pages_tried,
    }

# ── HEADER ────────────────────────────────────────────────────────────────────
hc1,hc2=st.columns([4,1])
with hc1:
    st.markdown(
        '<div class="hdr-title"><div class="hdr-box">f</div>Facebook Extractor</div>'
        '<div class="hdr-sub">Extract contact emails from Facebook pages &nbsp;·&nbsp; '
        'main page + /about + mobile &nbsp;·&nbsp; rate-limit aware</div>',
        unsafe_allow_html=True)
with hc2:
    fb_results=st.session_state.get("fb_results",{})
    if fb_results:
        from utils import build_xlsx_facebook as _bfb
        xlsx=_bfb(fb_results)
        st.download_button("⬇ Export .xlsx",xlsx,
                           f"facebook_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="fb_xlsx")
st.divider()

# ── INPUT AREA ────────────────────────────────────────────────────────────────
col_in, col_ctrl = st.columns([2, 1], gap="large")

with col_in:
    st.markdown('<span class="sec-label">Facebook pages (one per line)</span>', unsafe_allow_html=True)
    raw_input = st.text_area(
        "fb_input", label_visibility="collapsed",
        placeholder="techcrunch\nforbes\nhttps://facebook.com/entrepreneur\nnytimes",
        height=160, key="fb_raw_input")

    handles_to_scrape = []
    for line in raw_input.splitlines():
        h = normalize_handle(line)
        if h: handles_to_scrape.append(h)

    scraper_data = st.session_state.get("scraper_results", {})
    fb_from_scraper = []
    for r in scraper_data.values():
        for fb in r.get("Facebook",[]):
            h = normalize_handle(fb)
            if h and h not in fb_from_scraper: fb_from_scraper.append(h)

    if fb_from_scraper:
        if st.button(f"+ Import {len(fb_from_scraper)} handles from last scrape",
                     type="secondary", key="import_fb"):
            combined = "\n".join(set(raw_input.splitlines() + fb_from_scraper))
            st.session_state.fb_raw_input_val = combined
            st.rerun()

    if handles_to_scrape:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;gap:5px;margin:6px 0">'
            + "".join(f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;'
                      f'background:var(--dk-surface);border:1px solid var(--dk-border);border-radius:6px;'
                      f'padding:3px 9px;color:var(--dk-text-secondary)">{h}</span>' for h in handles_to_scrape[:8])
            + (f'<span style="font-size:10px;color:var(--dk-text-muted)">+{len(handles_to_scrape)-8} more</span>'
               if len(handles_to_scrape) > 8 else "")
            + '</div>', unsafe_allow_html=True)

with col_ctrl:
    st.markdown('<span class="sec-label">Options</span>', unsafe_allow_html=True)
    delay_val = st.slider("Delay between requests (s)", 2, 8, 4, key="fb_delay_s",
                          help="Facebook rate-limits aggressively. Recommended: 3-5s")
    parallel_fb = st.toggle("2x parallel", value=st.session_state.fb_parallel, key="fb_par",
                             help="Scrape 2 handles simultaneously. May increase block rate.")
    st.session_state.fb_parallel = parallel_fb

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    running = st.session_state.get("fb_running", False)
    if not running:
        if st.button("Start Extraction", type="primary", use_container_width=True,
                     disabled=not handles_to_scrape, key="fb_start"):
            new_handles = [h for h in handles_to_scrape if h not in st.session_state.fb_results]
            if new_handles:
                st.session_state.fb_queue  = new_handles
                st.session_state.fb_idx    = 0
                st.session_state.fb_running = True
                st.rerun()
    else:
        if st.button("Stop", type="secondary", use_container_width=True, key="fb_stop"):
            st.session_state.fb_running = False; st.rerun()

    if st.session_state.fb_results:
        if st.button("Clear results", type="secondary", use_container_width=True, key="fb_clear"):
            st.session_state.fb_results = {}; st.rerun()

st.divider()

# ── PROGRESS STRIP ────────────────────────────────────────────────────────────
fb_results = st.session_state.get("fb_results", {})
queue      = st.session_state.get("fb_queue", [])
idx        = st.session_state.get("fb_idx", 0)
running    = st.session_state.get("fb_running", False)

if running and queue:
    total  = len(queue)
    pct    = round(idx / total * 100, 1) if total else 0
    done   = len(fb_results)
    st.markdown(
        f'<div class="prog-strip">'
        f'<span class="pulse-dot"></span>'
        f'<span class="prog-strip-text">Scraping {idx}/{total}</span>'
        f'<div class="prog-strip-bar"><div class="prog-strip-fill" style="width:{pct}%"></div></div>'
        f'<span class="prog-strip-text">{pct}%</span>'
        f'</div>', unsafe_allow_html=True)

# ── RESULTS METRICS ───────────────────────────────────────────────────────────
if fb_results:
    total_h  = len(fb_results)
    has_em   = sum(1 for r in fb_results.values() if r.get("emails"))
    total_em = sum(len(r.get("emails",[])) for r in fb_results.values())
    blocked  = sum(1 for r in fb_results.values() if r.get("status")=="blocked")
    t1_count = sum(1 for r in fb_results.values()
                   for e in r.get("emails",[]) if tier_key(e)=="1")

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Pages", total_h)
    m2.metric("With Emails", has_em)
    m3.metric("Total Emails", total_em)
    m4.metric("Tier 1", t1_count)
    m5.metric("Blocked", blocked)
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

# ── RESULTS FEED ──────────────────────────────────────────────────────────────
if fb_results:
    st.markdown('<span class="sec-label">Results</span>', unsafe_allow_html=True)

    def sort_key(item):
        _,r=item
        if r.get("emails"):   return 0
        if r.get("status")=="blocked": return 2
        return 1

    sorted_results = sorted(fb_results.items(), key=sort_key)

    n = len(sorted_results)
    left_items  = sorted_results[:n//2 + n%2]
    right_items = sorted_results[n//2 + n%2:]

    gc1, gc2 = st.columns(2, gap="small")
    for col, items in [(gc1, left_items), (gc2, right_items)]:
        with col:
            for handle, r in items:
                emails  = r.get("emails", [])
                status  = r.get("status", "")
                elapsed = r.get("time", "")
                best    = pick_best(emails) or ""

                card_cls = "fb-card"
                if emails:      card_cls += " has-emails"
                elif status=="blocked": card_cls += " blocked"
                else:           card_cls += " no-emails"

                status_icon = {"scraped":"✓","blocked":"✗","no_emails":"○"}.get(status,"?")
                status_color= {"scraped":"var(--dk-accent)","blocked":"var(--dk-danger)","no_emails":"var(--dk-text-muted)"}.get(status,"var(--dk-text-muted)")

                emails_html = ""
                for email in emails[:4]:
                    t = tier_key(email)
                    cls  = {"1":"fb-t1","2":"fb-t2","3":"fb-t3"}[t]
                    badge_cls = {"1":"tb-t1","2":"tb-t2","3":"tb-t3"}[t]
                    emails_html += (
                        f'<div class="fb-email">'
                        f'<span class="{cls}">{email}</span>'
                        f'<span class="tier-badge {badge_cls}">T{t}</span>'
                        f'</div>')
                if len(emails) > 4:
                    emails_html += f'<div style="font-size:10px;color:var(--dk-text-muted);margin-top:5px">+ {len(emails)-4} more</div>'
                if not emails:
                    emails_html = f'<div style="font-size:10.5px;color:var(--dk-text-muted);margin-top:5px">' \
                                  f'{"Blocked by Facebook" if status=="blocked" else "No emails found"}</div>'

                st.markdown(f"""
                <div class="{card_cls}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <span class="fb-handle">{handle}</span>
                    <span style="font-size:10px;color:{status_color};font-weight:600;font-family:JetBrains Mono,monospace">
                      {status_icon} {status} &nbsp;·&nbsp; {elapsed}s
                    </span>
                  </div>
                  {emails_html}
                </div>""", unsafe_allow_html=True)

elif not running:
    st.markdown(
        '<div style="text-align:center;padding:80px 0">'
        '<div style="width:72px;height:72px;border-radius:20px;'
        'background:var(--dk-fb-dim);border:1px solid var(--dk-border);'
        'display:inline-flex;align-items:center;justify-content:center;'
        'margin-bottom:20px;font-size:28px;font-weight:800;color:var(--dk-fb)">f</div>'
        '<div style="font-size:18px;font-weight:800;color:var(--dk-text);'
        'letter-spacing:-.5px;margin-bottom:10px">No results yet</div>'
        '<div style="font-size:12px;color:var(--dk-text-muted);line-height:2;max-width:300px;margin:0 auto">'
        'Paste Facebook handles or page URLs<br>'
        'Import from Scraper if you already ran a scrape<br>'
        '<span style="color:var(--dk-fb);font-weight:600">Tip: /about pages often have contact emails</span></div>'
        '</div>', unsafe_allow_html=True)

# ── SCRAPE ENGINE ─────────────────────────────────────────────────────────────
if st.session_state.get("fb_running") and st.session_state.get("fb_queue"):
    queue = st.session_state.fb_queue
    idx   = st.session_state.fb_idx
    total = len(queue)
    delay = st.session_state.get("fb_delay_s", 4)
    par   = st.session_state.get("fb_parallel", True)
    BATCH = 2 if par else 1

    if idx >= total:
        st.session_state.fb_running = False; st.rerun()
    else:
        batch = queue[idx:idx+BATCH]

        def run_fb(handle):
            return handle, scrape_fb_handle(handle, delay=delay)

        if BATCH > 1 and len(batch) > 1:
            with ThreadPoolExecutor(max_workers=BATCH) as ex:
                futs = [ex.submit(run_fb, h) for h in batch]
                for fut in as_completed(futs):
                    try:
                        handle, result = fut.result()
                        st.session_state.fb_results[handle] = result
                    except Exception:
                        pass
        else:
            try:
                handle, result = run_fb(batch[0])
                st.session_state.fb_results[handle] = result
            except Exception:
                pass

        st.session_state.fb_idx = idx + len(batch)
        if st.session_state.fb_idx >= total:
            st.session_state.fb_running = False
        st.rerun()
