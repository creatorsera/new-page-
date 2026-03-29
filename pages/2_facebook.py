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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.4rem 1.8rem 4rem !important; max-width:100% !important; background:#0d0d0d !important; }

/* all text on dark bg */
.stMarkdown, .stCaption, label, p, span, div { color: #ccc !important; }

/* input */
.stTextArea textarea {
    font-family: 'JetBrains Mono', monospace !important; font-size:12px !important;
    border-radius:8px !important; border:1.5px solid #2a2a2a !important;
    background:#111 !important; color:#e0e0e0 !important; resize:none !important; line-height:1.65 !important;
}
.stTextArea textarea:focus { border-color:#4ade80 !important; box-shadow:0 0 0 3px rgba(74,222,128,.08) !important; }
.stTextArea textarea::placeholder { color:#333 !important; }

/* buttons */
.stButton > button {
    font-family:'Inter',sans-serif !important; font-weight:600 !important;
    border-radius:8px !important; font-size:13px !important; height:40px !important;
    transition:all .15s !important;
}
.stButton > button[kind="primary"] {
    background:#4ade80 !important; border:none !important; color:#0d0d0d !important;
    box-shadow:0 0 15px rgba(74,222,128,.2) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
    background:#22c55e !important; box-shadow:0 0 25px rgba(74,222,128,.35) !important;
    transform:translateY(-1px) !important;
}
.stButton > button[kind="primary"]:disabled {
    background:#1a1a1a !important; color:#444 !important; box-shadow:none !important;
}
.stButton > button[kind="secondary"] {
    background:#1a1a1a !important; border:1px solid #2a2a2a !important; color:#888 !important;
}
.stButton > button[kind="secondary"]:hover { border-color:#555 !important; color:#ccc !important; }
.stDownloadButton > button {
    font-family:'Inter',sans-serif !important; font-weight:600 !important;
    border-radius:8px !important; font-size:12.5px !important; height:38px !important;
    background:#1a1a1a !important; border:1px solid #2a2a2a !important; color:#888 !important;
}
.stDownloadButton > button:hover { border-color:#4ade80 !important; color:#4ade80 !important; }

/* metric cards — dark */
[data-testid="stMetric"] {
    background:#111; border:1px solid #1e1e1e; border-radius:10px; padding:.7rem .85rem !important;
}
[data-testid="stMetricLabel"] p {
    font-size:9.5px !important; font-weight:700 !important; color:#444 !important;
    text-transform:uppercase !important; letter-spacing:.6px !important;
}
[data-testid="stMetricValue"] {
    font-size:22px !important; font-weight:800 !important; color:#e0e0e0 !important; letter-spacing:-.7px !important;
}

/* result card */
.fb-card {
    background:#111; border:1px solid #1e1e1e; border-radius:10px;
    padding:12px 16px; margin-bottom:8px; transition:border-color .2s;
}
.fb-card:hover { border-color:#2a2a2a; }
.fb-card.has-emails { border-left:3px solid #4ade80; }
.fb-card.blocked    { border-left:3px solid #ef4444; opacity:.6; }
.fb-card.no-emails  { border-left:3px solid #374151; }
.fb-handle { font-size:14px; font-weight:700; color:#e0e0e0; font-family:'JetBrains Mono',monospace; }
.fb-status { font-size:10px; color:#555; margin-top:2px; }
.fb-email  { font-family:'JetBrains Mono',monospace; font-size:11.5px; margin-top:6px; display:flex; align-items:center; gap:8px; }
.fb-t1 { color:#fbbf24; font-weight:700; }
.fb-t2 { color:#60a5fa; font-weight:600; }
.fb-t3 { color:#6b7280; }
.tier-badge { font-size:9px; font-weight:700; padding:1px 5px; border-radius:3px; margin-left:4px; }
.tb-t1 { background:#78350f22; color:#fbbf24; border:1px solid #78350f44; }
.tb-t2 { background:#1e3a5f22; color:#60a5fa; border:1px solid #1e3a5f44; }
.tb-t3 { background:#1f293722; color:#6b7280; border:1px solid #1f293744; }
.scanning-card { border-left:3px solid #facc15 !important; animation:scan-pulse 1.5s infinite; }
@keyframes scan-pulse { 0%,100%{border-left-color:#facc15} 50%{border-left-color:#4ade80} }

.hdr-title { font-size:20px; font-weight:800; color:#fff; letter-spacing:-.5px; display:flex; align-items:center; gap:10px; }
.hdr-box { width:34px; height:34px; background:#1877f2; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.hdr-sub { font-size:11px; color:#444; margin-top:3px; }
.prog-strip { display:flex; align-items:center; gap:12px; padding:10px 14px; background:#111; border:1px solid #1e1e1e; border-radius:8px; margin:8px 0; }
.prog-strip-bar { flex:1; height:3px; background:#1e1e1e; border-radius:99px; overflow:hidden; }
.prog-strip-fill { height:100%; background:#4ade80; border-radius:99px; transition:width .4s; }
.prog-strip-text { font-size:11px; color:#555; font-family:'JetBrains Mono',monospace; white-space:nowrap; }
.pulse-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#4ade80; margin-right:8px; animation:dot-pulse 1.4s infinite; }
@keyframes dot-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.2;transform:scale(.75)} }
.sec-label { font-size:10px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; color:#333; display:block; margin-bottom:8px; }
.pill-tag { display:inline-block; font-size:9.5px; font-weight:600; padding:2px 7px; border-radius:4px; }
hr { border-color:#1e1e1e !important; margin:12px 0 !important; }

/* toggle */
[data-testid="stToggle"] > label { color:#888 !important; }
/* selectbox */
[data-testid="stSelectbox"] > div > div { background:#111 !important; border-color:#2a2a2a !important; color:#ccc !important; }
/* number input */
[data-testid="stNumberInput"] input { background:#111 !important; border-color:#2a2a2a !important; color:#ccc !important; }
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
    """Extract handle from raw input (URL or plain handle)."""
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
    """
    Scrapes a Facebook handle. Tries main page + /about.
    Returns dict: {emails, status, time, pages_tried}.
    Thread-safe — no session_state.
    """
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
        '<div class="hdr-sub">Extract contact emails directly from Facebook pages &nbsp;|&nbsp; '
        'tries main page + /about &nbsp;|&nbsp; rate-limit aware</div>',
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

    # import from scraper
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
            '<div style="display:flex;flex-wrap:wrap;gap:4px;margin:5px 0">'
            + "".join(f'<span style="font-family:JetBrains Mono,monospace;font-size:10.5px;'
                      f'background:#1a1a1a;border:1px solid #2a2a2a;border-radius:4px;'
                      f'padding:2px 7px;color:#888">{h}</span>' for h in handles_to_scrape[:8])
            + (f'<span style="font-size:10.5px;color:#444">+{len(handles_to_scrape)-8} more</span>'
               if len(handles_to_scrape) > 8 else "")
            + '</div>', unsafe_allow_html=True)

with col_ctrl:
    st.markdown('<span class="sec-label">Options</span>', unsafe_allow_html=True)
    delay_val = st.slider("Delay between requests (s)", 2, 8, 4, key="fb_delay_s",
                          help="Facebook rate-limits aggressively. Recommended: 3-5s")
    parallel_fb = st.toggle("2x parallel", value=st.session_state.fb_parallel, key="fb_par",
                             help="Scrape 2 handles simultaneously. May increase block rate.")
    st.session_state.fb_parallel = parallel_fb

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

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
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# ── RESULTS FEED ──────────────────────────────────────────────────────────────
if fb_results:
    st.markdown('<span class="sec-label">Results</span>', unsafe_allow_html=True)

    # sort: has emails first, then blocked, then no emails
    def sort_key(item):
        _,r=item
        if r.get("emails"):   return 0
        if r.get("status")=="blocked": return 2
        return 1

    sorted_results = sorted(fb_results.items(), key=sort_key)

    # two-column card grid
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
                status_color= {"scraped":"#4ade80","blocked":"#ef4444","no_emails":"#374151"}.get(status,"#555")

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
                    emails_html += f'<div style="font-size:10px;color:#444;margin-top:4px">+ {len(emails)-4} more email(s)</div>'
                if not emails:
                    emails_html = f'<div style="font-size:10.5px;color:#333;margin-top:4px">' \
                                  f'{"Blocked by Facebook" if status=="blocked" else "No emails found"}</div>'

                st.markdown(f"""
                <div class="{card_cls}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <span class="fb-handle">{handle}</span>
                    <span style="font-size:10px;color:{status_color};font-weight:600">
                      {status_icon} {status} &nbsp;·&nbsp; {elapsed}s
                    </span>
                  </div>
                  {emails_html}
                </div>""", unsafe_allow_html=True)

elif not running:
    st.markdown(
        '<div style="text-align:center;padding:60px 0;color:#333">'
        '<div style="font-size:40px;margin-bottom:12px;opacity:.3">f</div>'
        '<div style="font-size:15px;font-weight:700;color:#444;margin-bottom:8px">No results yet</div>'
        '<div style="font-size:12px;color:#333;line-height:1.8">Paste Facebook handles or page URLs<br>'
        'Import from Scraper if you already ran a scrape<br>'
        '<span style="color:#1d4ed8">Tip: /about pages often have contact emails</span></div>'
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
