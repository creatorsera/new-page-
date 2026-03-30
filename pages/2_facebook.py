"""
pages/2_facebook.py — Facebook Email Extractor
Uses Playwright headless Chromium — real browser, bypasses most FB blocking.
Falls back to mbasic.facebook.com if Playwright unavailable.
"""
import streamlit as st
import re, time, subprocess, sys, os
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (extract_emails, sort_by_tier, pick_best, tier_short,
                   tier_key, fetch_page, build_xlsx_facebook)
from theme import inject_css, page_header
from bs4 import BeautifulSoup

inject_css("facebook")
st.markdown("""
<style>
.mh-start .stButton > button { height:44px !important; font-size:13.5px !important; font-weight:700 !important; }
.fb-card { background:#fff; border:1px solid #e8e8e4; border-radius:10px; padding:13px 15px; margin-bottom:8px; }
.fb-card.hit   { border-left:3px solid #1877f2; }
.fb-card.miss  { border-left:3px solid #e8e8e4; opacity:.75; }
.fb-card.block { border-left:3px solid #dc2626; opacity:.65; }
.fb-handle { font-size:13.5px; font-weight:700; color:#111; font-family:'JetBrains Mono',monospace; }
.fb-email  { font-family:'JetBrains Mono',monospace; font-size:11.5px; font-weight:600; margin-top:5px; }
.fb-badge  { font-size:9px; font-weight:700; padding:1px 5px; border-radius:3px; margin-left:4px; background:#eeeeed; color:#666; }
.mpill { display:inline-block; font-size:9.5px; font-weight:700; padding:2px 7px; border-radius:99px; margin:3px 3px 0 0; }
.mpill-pw { background:#ede9fe; color:#7c3aed; }
.mpill-mb { background:#e0f2fe; color:#0369a1; }
.mpill-ws { background:#f0fdf4; color:#15803d; }
.fb-prog { display:flex; align-items:center; gap:12px; background:#fff; border:1px solid #e8e8e4; border-radius:10px; padding:10px 15px; margin:8px 0; }
</style>
""", unsafe_allow_html=True)

# ── PLAYWRIGHT CHECK ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Setting up Chromium (first run, one-time)...")
def _setup_playwright():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            return True, "ready"
        return False, result.stderr[:200]
    except FileNotFoundError:
        return False, "playwright package not installed"
    except Exception as e:
        return False, str(e)[:100]

pw_ok, pw_msg = _setup_playwright()

# ── SCRAPER FUNCTIONS ─────────────────────────────────────────────────────────
def _website_emails(website):
    """Given a linked website, scrape it and its /contact /about pages for emails."""
    all_e = set()
    if not website: return all_e
    try:
        html, _ = fetch_page(website, timeout=12)
        if html: all_e.update(extract_emails(html))
        for sub in ["/contact", "/contact-us", "/about", "/about-us"]:
            sub_html, _ = fetch_page(urljoin(website, sub), timeout=8)
            if sub_html: all_e.update(extract_emails(sub_html))
            time.sleep(0.5)
    except Exception:
        pass
    return all_e

def _extract_website_mbasic(html):
    """Pull the linked website URL from mbasic Facebook HTML."""
    if not html: return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "l.facebook.com/l.php" in href:
            try:
                qs = parse_qs(urlparse(href).query)
                if "u" in qs:
                    ext = unquote(qs["u"][0])
                    p = urlparse(ext)
                    if p.scheme in ("http","https") and "facebook.com" not in p.netloc:
                        return ext
            except:
                pass
    return None

def scrape_playwright(handle, delay=2):
    """Full headless Chromium scrape — real browser, best hit rate."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    all_emails = set(); website = None; pages_tried = 0; status = "no_emails"
    t0 = time.time()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled",
                      "--disable-web-security"])
            ctx = browser.new_context(
                user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                            "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"),
                viewport={"width":390,"height":844},
                locale="en-US")
            pg = ctx.new_page()
            pg.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,woff,woff2}", lambda r: r.abort())

            for path in [handle, f"{handle}/about"]:
                try:
                    pg.goto(f"https://www.facebook.com/{path}",
                            timeout=22000, wait_until="domcontentloaded")
                    time.sleep(delay)
                    content = pg.content()
                    found = extract_emails(content)
                    if found: all_emails.update(found)
                    pages_tried += 1
                    # grab external links
                    if "about" in path and not website:
                        try:
                            hrefs = pg.eval_on_selector_all("a[href]","els=>els.map(e=>e.href)")
                            for href in hrefs:
                                if href and "facebook.com" not in href and href.startswith("http"):
                                    try:
                                        p_ = urlparse(href)
                                        if p_.netloc and len(p_.netloc) > 4:
                                            website = href; break
                                    except:
                                        pass
                        except:
                            pass
                except Exception:
                    pass
                time.sleep(1)

            browser.close()
    except Exception:
        return None

    # scrape website
    ws_emails = _website_emails(website)
    all_emails.update(ws_emails)
    if all_emails: status = "scraped"

    return {
        "emails": sort_by_tier(all_emails),
        "status": status, "website": website or "",
        "time": round(time.time()-t0, 1),
        "pages_tried": pages_tried, "method": "playwright",
    }

def scrape_mbasic(handle, delay=3):
    """mbasic.facebook.com fallback — stripped HTML, less bot detection."""
    all_emails = set(); website = None; pages_tried = 0; status = "no_emails"
    t0 = time.time()

    for path in [handle, f"{handle}/about", f"{handle}/info"]:
        url = f"https://mbasic.facebook.com/{path}"
        html, code = fetch_page(url, timeout=14, mobile=True)
        if code in (403, 429, 503):
            status = "blocked"; break
        if html:
            all_emails.update(extract_emails(html))
            pages_tried += 1
            if "about" in path or "info" in path:
                ws = _extract_website_mbasic(html)
                if ws and not website: website = ws
        time.sleep(max(1, delay // 2))

    ws_emails = _website_emails(website)
    all_emails.update(ws_emails)
    if all_emails: status = "scraped"
    elif "blocked" not in status: status = "no_emails"

    return {
        "emails": sort_by_tier(all_emails),
        "status": status, "website": website or "",
        "time": round(time.time()-t0, 1),
        "pages_tried": pages_tried, "method": "mbasic",
    }

def scrape_handle(handle, use_playwright=True, delay=2):
    if use_playwright and pw_ok:
        result = scrape_playwright(handle, delay)
        if result: return result
    return scrape_mbasic(handle, delay)

def normalize(raw):
    raw = raw.strip()
    if not raw: return None
    m = re.search(r'facebook\.com/(?:pages/[^/]+/)?([A-Za-z0-9_.]{3,80})', raw)
    if m:
        s = m.group(1)
        SKIP = {"sharer","share","dialog","login","home","watch","groups","events","tr","marketplace","permalink"}
        if s.lower() not in SKIP: return s
    if re.match(r'^[A-Za-z0-9_.]{3,80}$', raw): return raw
    return None

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k,v in {"fb_results":{},"fb_running":False,"fb_queue":[],"fb_idx":0}.items():
    if k not in st.session_state: st.session_state[k]=v

# ── HEADER ────────────────────────────────────────────────────────────────────
page_header("f","Facebook Extractor",
    "Playwright headless Chromium  ·  real browser  ·  visits page + /about  ·  extracts linked website",
    "facebook")

hc1,hc2=st.columns([4,1])
with hc2:
    if st.session_state.fb_results:
        xlsx=build_xlsx_facebook(st.session_state.fb_results)
        st.download_button("⬇ .xlsx",xlsx,
            f"facebook_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="fb_xlsx")

# status banner
if pw_ok:
    st.markdown('<div class="mh-info">✓ Playwright + Chromium ready — real browser mode active</div>',unsafe_allow_html=True)
else:
    st.markdown(f'<div class="mh-warn">Playwright unavailable ({pw_msg}). Add <code>playwright</code> to requirements.txt + system deps to packages.txt. Using mbasic fallback.</div>',unsafe_allow_html=True)

# ── INPUT ─────────────────────────────────────────────────────────────────────
c1,c2=st.columns([3,1],gap="large")
with c1:
    st.markdown('<span class="mh-sec">Facebook pages — one per line</span>',unsafe_allow_html=True)
    raw=st.text_area("fbi",label_visibility="collapsed",
        placeholder="techcrunch\nforbes\nhttps://facebook.com/nytimes\nentrepreneur",
        height=130,key="fb_raw")
    handles=[]
    for line in raw.splitlines():
        h=normalize(line)
        if h and h not in handles: handles.append(h)

    fb_from_scraper=[]
    for r in st.session_state.get("scraper_results",{}).values():
        for fb in r.get("Facebook",[]):
            h=normalize(fb)
            if h and h not in fb_from_scraper: fb_from_scraper.append(h)
    if fb_from_scraper:
        if st.button(f"+ Import {len(fb_from_scraper)} handle(s) from Scraper",type="secondary",key="import_fb"):
            existing={l.strip() for l in raw.splitlines() if l.strip()}
            extra="\n".join(h for h in fb_from_scraper if h not in existing)
            st.session_state.fb_raw=(raw+"\n"+extra).strip(); st.rerun()
    if handles:
        pills="".join(f'<span class="mh-pill">{h[:20]}</span>' for h in handles[:8])
        if len(handles)>8: pills+=f'<span class="mh-pill">+{len(handles)-8}</span>'
        st.markdown(f'<div class="mh-pills">{pills}</div>',unsafe_allow_html=True)

with c2:
    st.markdown('<span class="mh-sec">Options</span>',unsafe_allow_html=True)
    delay_v=st.slider("Wait per page (s)",1,8,2,key="fb_delay_s")
    use_pw=st.toggle("Use Playwright",value=pw_ok,disabled=not pw_ok,key="fb_pw_t")
    st.markdown('<div style="height:6px"></div>',unsafe_allow_html=True)
    running=st.session_state.get("fb_running",False)
    st.markdown('<div class="mh-start">',unsafe_allow_html=True)
    if not running:
        if st.button("Start Extraction",type="primary",use_container_width=True,
                     disabled=not handles,key="fb_start"):
            new_h=[h for h in handles if h not in st.session_state.fb_results]
            if new_h:
                st.session_state.fb_queue=new_h; st.session_state.fb_idx=0
                st.session_state.fb_running=True; st.rerun()
    else:
        if st.button("Stop",type="secondary",use_container_width=True,key="fb_stop"):
            st.session_state.fb_running=False; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    if st.session_state.fb_results:
        if st.button("Clear",type="secondary",use_container_width=True,key="fb_clear"):
            st.session_state.fb_results={}; st.rerun()

with st.expander("Strategy explanation"):
    st.markdown("""
**Playwright (when available):** Launches real headless Chromium on mobile viewport. 
Facebook cannot distinguish this from an actual iPhone browser. Visits main page + /about, waits for JS, extracts emails, finds linked website.

**mbasic fallback:** `mbasic.facebook.com` is Facebook's feature-phone version — less JavaScript, different CDN path, less aggressive bot detection from cloud IPs.

**Website extraction (both methods):** Every FB page has a "Website" field in about. 
The extractor finds that URL and scrapes the actual website's contact/about pages. 
This is often the highest-yield step — many businesses list emails there but not on FB.

**packages.txt needed for Playwright on Streamlit Cloud:**
```
libnss3
libnspr4  
libatk1.0-0
libatk-bridge2.0-0
libcups2
libdrm2
libxkbcommon0
libxcomposite1
libxdamage1
libxrandr2
libgbm1
libasound2
```
""")

# ── PROGRESS ──────────────────────────────────────────────────────────────────
fb_results=st.session_state.get("fb_results",{}); q=st.session_state.get("fb_queue",[])
idx=st.session_state.get("fb_idx",0); running=st.session_state.get("fb_running",False)
if running and q:
    total=len(q); pct=round(idx/total*100,1) if total else 0; done=len(fb_results)
    cur=q[idx] if idx<total else "done"
    st.markdown(f'<div class="fb-prog"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#1877f2;margin-right:4px;animation:mhpulse 1.5s infinite"></span>'
                f'<div style="flex:1"><div style="font-size:12.5px;font-weight:700;color:#111">Scraping <code>{cur}</code></div>'
                f'<div style="font-size:11px;color:#aaa">{done} done · {total-done} left</div>'
                f'<div style="height:3px;background:#eee;border-radius:99px;overflow:hidden;margin-top:5px">'
                f'<div style="height:100%;width:{pct}%;background:#1877f2;border-radius:99px;transition:width .4s"></div></div></div>'
                f'<div style="font-size:20px;font-weight:800;color:#1877f2">{pct}%</div></div>',unsafe_allow_html=True)

# ── METRICS ───────────────────────────────────────────────────────────────────
if fb_results:
    th=len(fb_results); he=sum(1 for r in fb_results.values() if r.get("emails"))
    te=sum(len(r.get("emails",[])) for r in fb_results.values())
    bl=sum(1 for r in fb_results.values() if "block" in r.get("status",""))
    ws=sum(1 for r in fb_results.values() if r.get("website"))
    t1c=sum(1 for r in fb_results.values() for e in r.get("emails",[]) if tier_key(e)=="1")
    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Pages",th); m2.metric("With Emails",he); m3.metric("Total Emails",te)
    m4.metric("Tier 1",t1c); m5.metric("Via Website",ws); m6.metric("Blocked",bl)

    st.markdown('<span class="mh-sec" style="margin-top:10px;display:block">Results</span>',unsafe_allow_html=True)
    items=sorted(fb_results.items(),key=lambda x:(0 if x[1].get("emails") else 2 if "block" in x[1].get("status","") else 1))
    n=len(items); lf=items[:n//2+n%2]; rf=items[n//2+n%2:]
    gc1,gc2=st.columns(2,gap="small")
    for col,side in [(gc1,lf),(gc2,rf)]:
        with col:
            for handle,r in side:
                emails=r.get("emails",[]); status=r.get("status",""); ws_=r.get("website",""); tt=r.get("time",""); meth=r.get("method","")
                cls="hit" if emails else ("block" if "block" in status else "miss")
                mpills=""
                if meth=="playwright": mpills+='<span class="mpill mpill-pw">Playwright</span>'
                elif meth=="mbasic":   mpills+='<span class="mpill mpill-mb">mbasic</span>'
                if ws_: mpills+=f'<span class="mpill mpill-ws">+website</span>'
                emails_html=""
                for email in emails[:4]:
                    t=tier_key(email); tc={"1":"#d97706","2":"#6366f1","3":"#888"}.get(t,"#888")
                    emails_html+=f'<div class="fb-email" style="color:{tc}">{email}<span class="fb-badge">T{t}</span></div>'
                if len(emails)>4: emails_html+=f'<div style="font-size:10px;color:#aaa;margin-top:3px">+{len(emails)-4} more</div>'
                if not emails:
                    msg="Blocked" if "block" in status else ("No emails found — try Playwright mode" if meth!="playwright" else "No emails found")
                    emails_html=f'<div style="font-size:11px;color:#aaa;margin-top:5px">{msg}</div>'
                sc={"scraped":"#16a34a","blocked":"#dc2626","no_emails":"#aaa"}.get(status,"#aaa")
                st.markdown(f'<div class="fb-card {cls}"><div style="display:flex;justify-content:space-between;align-items:flex-start">'
                            f'<span class="fb-handle">{handle}</span><span style="font-size:10px;color:{sc};font-weight:600">{tt}s</span></div>'
                            f'<div style="margin:3px 0">{mpills}</div>{emails_html}</div>',unsafe_allow_html=True)
else:
    if not running:
        st.markdown('<div style="text-align:center;padding:50px 0"><div style="font-size:40px;opacity:.1;margin-bottom:12px">f</div>'
                    '<div style="font-size:17px;font-weight:800;color:#111;margin-bottom:8px">No results yet</div>'
                    '<div style="font-size:12px;color:#aaa;line-height:1.9;max-width:360px;margin:0 auto">'
                    'Paste Facebook handles above<br>Import from Scraper if you already ran a scan<br>'
                    '<span style="color:#7c3aed">Playwright mode uses a real browser — much better results</span></div></div>',unsafe_allow_html=True)

# ── ENGINE ────────────────────────────────────────────────────────────────────
if st.session_state.get("fb_running") and st.session_state.get("fb_queue"):
    q=st.session_state.fb_queue; idx=st.session_state.fb_idx; total=len(q)
    if idx>=total: st.session_state.fb_running=False; st.rerun()
    else:
        handle=q[idx]; use_pw_=bool(st.session_state.get("fb_pw_t",True) and pw_ok); dv=int(st.session_state.get("fb_delay_s",2))
        try:
            result=scrape_handle(handle,use_playwright=use_pw_,delay=dv)
            st.session_state.fb_results[handle]=result
        except Exception as e:
            st.session_state.fb_results[handle]={"emails":[],"status":"error","website":"","time":0,"pages_tried":0,"method":"error"}
        st.session_state.fb_idx=idx+1
        if st.session_state.fb_idx>=total: st.session_state.fb_running=False
        st.rerun()
