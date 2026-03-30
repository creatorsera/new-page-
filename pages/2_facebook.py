"""
pages/2_facebook.py — Facebook Email Extractor
Uses mbasic.facebook.com + linked website extraction to bypass blocking.
"""
import streamlit as st
import re, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (extract_emails, sort_by_tier, pick_best, tier_short,
    tier_key, fetch_page, build_xlsx_facebook, is_valid_email)
from theme import inject_css, page_header

inject_css("facebook")

# FB-specific extra styles
st.markdown("""<style>
.fb-card { background:#fff; border:1px solid #e8e8e4; border-radius:10px; padding:13px 15px; margin-bottom:8px; }
.fb-card.hit  { border-left:3px solid #1877f2; }
.fb-card.miss { border-left:3px solid #e8e8e4; opacity:.7; }
.fb-card.block{ border-left:3px solid #dc2626; opacity:.6; }
.fb-handle { font-size:13.5px; font-weight:700; color:#111; font-family:'JetBrains Mono',monospace; }
.fb-email  { font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#1877f2; font-weight:600; margin-top:5px; }
.fb-t1 { color:#d97706 !important; }
.fb-t2 { color:#6366f1 !important; }
.fb-badge { font-size:9px; font-weight:700; padding:1px 5px; border-radius:3px; margin-left:4px; background:#eeeeed; color:#666; }
.fb-prog { display:flex; align-items:center; gap:12px; background:#fff; border:1px solid #e8e8e4; border-radius:10px; padding:10px 15px; margin:8px 0; }
.mh-start .stButton > button { height:44px !important; font-size:13.5px !important; font-weight:700 !important; }
</style>""", unsafe_allow_html=True)

for k,v in {"fb_results":{},"fb_running":False,"fb_queue":[],"fb_idx":0,"fb_delay":4,"fb_par":False}.items():
    if k not in st.session_state: st.session_state[k]=v

def normalize_handle(raw):
    raw=raw.strip()
    if not raw: return None
    m=re.search(r'facebook\.com/(?:pages/[^/]+/)?([A-Za-z0-9_.]{3,80})',raw)
    if m:
        s=m.group(1)
        if s.lower() not in {"sharer","share","dialog","login","home","watch","groups","events","tr"}: return s
    if re.match(r'^[A-Za-z0-9_.]{3,80}$',raw): return raw
    return None

def _extract_website_from_mbasic(html):
    """Pull the linked website URL from a mbasic Facebook about page."""
    if not html: return None
    soup=BeautifulSoup(html,"html.parser")
    for a in soup.find_all("a",href=True):
        href=a["href"]; hl=href.lower()
        # mbasic puts external links through l.facebook.com/l.php?u=...
        if "l.facebook.com/l.php" in hl:
            from urllib.parse import urlparse,parse_qs,unquote
            try:
                qs=parse_qs(urlparse(href).query)
                if "u" in qs:
                    ext=unquote(qs["u"][0])
                    p=urlparse(ext)
                    if p.scheme in("http","https") and "facebook.com" not in p.netloc:
                        return ext
            except: pass
        # sometimes direct links appear
        if hl.startswith("http") and "facebook.com" not in hl and "instagram.com" not in hl:
            try:
                p=urlparse(href)
                if p.scheme in("http","https") and len(p.netloc)>4: return href
            except: pass
    return None

def scrape_fb_handle(handle, delay=4):
    """
    Strategy:
    1. mbasic.facebook.com/{handle} — stripped HTML, less blocked
    2. mbasic.facebook.com/{handle}/about — often has contact email
    3. Extract linked website URL → scrape that for emails
    4. If still nothing, try regular mobile FB as last resort
    """
    t0=time.time(); all_emails=set(); status="no_emails"; website=None; pages_tried=0

    # Step 1 & 2: mbasic
    for path in [f"/{handle}", f"/{handle}/about", f"/{handle}/info"]:
        url=f"https://mbasic.facebook.com{path}"
        html,code=fetch_page(url,timeout=14,mobile=True)
        if code in(301,302): pass  # redirected, try next
        if code==200 and html:
            found=extract_emails(html)
            if found: all_emails.update(found)
            # try extracting website on about page
            if "/about" in path or "/info" in path:
                ws=_extract_website_from_mbasic(html)
                if ws and not website: website=ws
            pages_tried+=1
        elif code in(400,403,429):
            # hard blocked — note it but keep trying
            status="blocked_mbasic"
        time.sleep(max(1, delay//2))

    # Step 3: scrape linked website
    if website:
        try:
            ws_html,ws_code=fetch_page(website,timeout=12)
            if ws_html:
                ws_emails=extract_emails(ws_html); all_emails.update(ws_emails); pages_tried+=1
                # also try /contact on that website
                from urllib.parse import urljoin
                for path in ["/contact","/contact-us","/about"]:
                    sub_html,_=fetch_page(urljoin(website,path),timeout=8)
                    if sub_html: all_emails.update(extract_emails(sub_html)); time.sleep(1)
        except: pass

    # Step 4: last resort — regular mobile FB
    if not all_emails and status!="blocked_mbasic":
        html,code=fetch_page(f"https://m.facebook.com/{handle}/about",timeout=14,mobile=True)
        if html and code==200:
            all_emails.update(extract_emails(html)); pages_tried+=1

    if all_emails: status="scraped"
    elif "blocked" not in status: status="no_emails"

    return {
        "emails": sort_by_tier(all_emails),
        "status": status,
        "website": website or "",
        "time": round(time.time()-t0,1),
        "pages_tried": pages_tried,
    }

# ── UI ────────────────────────────────────────────────────────────────────────
page_header("f","Facebook Extractor",
    "Uses mbasic.facebook.com + linked website extraction  ·  rate-limit aware  ·  2 workers max",
    "facebook")

hc1,hc2=st.columns([4,1])
with hc2:
    fb_res=st.session_state.get("fb_results",{})
    if fb_res:
        xlsx=build_xlsx_facebook(fb_res)
        st.download_button("⬇ .xlsx",xlsx,f"facebook_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="fb_xlsx")

col_in,col_opt=st.columns([3,1],gap="large")
with col_in:
    st.markdown('<span class="mh-sec">Facebook pages — one per line</span>',unsafe_allow_html=True)
    raw_input=st.text_area("fbi",label_visibility="collapsed",
        placeholder="techcrunch\nforbes\nhttps://facebook.com/nytimes\nentrepreneur",
        height=140,key="fb_raw")
    handles_to_scrape=[]
    for line in raw_input.splitlines():
        h=normalize_handle(line)
        if h and h not in handles_to_scrape: handles_to_scrape.append(h)

    # import from scraper
    fb_from_scraper=[]
    for r in st.session_state.get("scraper_results",{}).values():
        for fb in r.get("Facebook",[]):
            h=normalize_handle(fb)
            if h and h not in fb_from_scraper: fb_from_scraper.append(h)
    if fb_from_scraper:
        if st.button(f"+ Import {len(fb_from_scraper)} handle(s) found in last scrape",type="secondary",key="import_fb"):
            existing=set(raw_input.splitlines())
            new_lines="\n".join(h for h in fb_from_scraper if h not in existing)
            st.session_state.fb_raw=(raw_input+"\n"+new_lines).strip(); st.rerun()

    if handles_to_scrape:
        pills="".join(f'<span class="mh-pill">{h[:22]}</span>' for h in handles_to_scrape[:8])
        if len(handles_to_scrape)>8: pills+=f'<span class="mh-pill">+{len(handles_to_scrape)-8}</span>'
        st.markdown(f'<div class="mh-pills">{pills}</div>',unsafe_allow_html=True)

with col_opt:
    st.markdown('<span class="mh-sec">Options</span>',unsafe_allow_html=True)
    delay_val=st.slider("Delay (s)",2,10,4,key="fb_delay_s",
        help="mbasic rate-limits less aggressively than regular FB. 3-5s recommended.")
    st.session_state.fb_par=st.toggle("2 workers (riskier)",value=st.session_state.fb_par,key="fb_par_t",
        help="Scraping 2 pages at once increases speed but may trigger blocks faster.")
    st.markdown('<div style="height:6px"></div>',unsafe_allow_html=True)
    running=st.session_state.get("fb_running",False)
    st.markdown('<div class="mh-start">',unsafe_allow_html=True)
    if not running:
        if st.button("Start Extraction",type="primary",use_container_width=True,
                     disabled=not handles_to_scrape,key="fb_start"):
            new_h=[h for h in handles_to_scrape if h not in st.session_state.fb_results]
            if new_h: st.session_state.fb_queue=new_h; st.session_state.fb_idx=0; st.session_state.fb_running=True; st.rerun()
    else:
        if st.button("Stop",type="secondary",use_container_width=True,key="fb_stop"): st.session_state.fb_running=False; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    if st.session_state.fb_results:
        if st.button("Clear",type="secondary",use_container_width=True,key="fb_clear"): st.session_state.fb_results={}; st.rerun()

st.markdown('<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 13px;font-size:11.5px;color:#92400e;margin:4px 0">'
            '<strong>How it works:</strong> Tries mbasic.facebook.com (less blocked than regular FB) + /about page, '
            'then extracts the linked website and scrapes that for contact emails. '
            'Much higher success rate than direct facebook.com scraping.</div>',unsafe_allow_html=True)

# progress
fb_results=st.session_state.get("fb_results",{}); queue=st.session_state.get("fb_queue",[]); idx=st.session_state.get("fb_idx",0); running=st.session_state.get("fb_running",False)
if running and queue:
    total=len(queue); pct=round(idx/total*100,1) if total else 0; done=len(fb_results)
    st.markdown(f'<div class="fb-prog"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#1877f2;margin-right:4px;animation:mhpulse 1.5s infinite"></span>'
                f'<div style="flex:1"><div style="font-size:12.5px;font-weight:700;color:#111">Extracting</div>'
                f'<div style="font-size:11px;color:#aaa">{done} done · {total-done} left</div>'
                f'<div style="height:3px;background:#eee;border-radius:99px;overflow:hidden;margin-top:5px"><div style="height:100%;width:{pct}%;background:#1877f2;border-radius:99px;transition:width .4s"></div></div></div>'
                f'<div style="font-size:20px;font-weight:800;color:#1877f2">{pct}%</div></div>',unsafe_allow_html=True)

# metrics
if fb_results:
    th=len(fb_results); he=sum(1 for r in fb_results.values() if r.get("emails")); te=sum(len(r.get("emails",[])) for r in fb_results.values())
    bl=sum(1 for r in fb_results.values() if "block" in r.get("status","")); ws=sum(1 for r in fb_results.values() if r.get("website"))
    t1c=sum(1 for r in fb_results.values() for e in r.get("emails",[]) if tier_key(e)=="1")
    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Pages",th); m2.metric("With Emails",he); m3.metric("Total Emails",te)
    m4.metric("Tier 1",t1c); m5.metric("Via Website",ws); m6.metric("Blocked",bl)

    st.markdown('<span class="mh-sec" style="margin-top:10px;display:block">Results</span>',unsafe_allow_html=True)
    # two-column card grid
    items=sorted(fb_results.items(),key=lambda x:(0 if x[1].get("emails") else 2 if "block" in x[1].get("status","") else 1))
    n=len(items); lf=items[:n//2+n%2]; rf=items[n//2+n%2:]
    gc1,gc2=st.columns(2,gap="small")
    for col,side in [(gc1,lf),(gc2,rf)]:
        with col:
            for handle,r in side:
                emails=r.get("emails",[]); status=r.get("status",""); ws_=r.get("website",""); tt=r.get("time","")
                cls="hit" if emails else ("block" if "block" in status else "miss")
                src_tag=f'<span style="font-size:9px;color:#aaa;margin-left:6px">via website</span>' if ws_ and emails else ""
                emails_html=""
                for email in emails[:4]:
                    t=tier_key(email); ec={"1":"#d97706","2":"#6366f1","3":"#666"}.get(t,"#666")
                    emails_html+=f'<div class="fb-email" style="color:{ec}">{email} <span class="fb-badge">T{t}</span></div>'
                if len(emails)>4: emails_html+=f'<div style="font-size:10px;color:#aaa;margin-top:3px">+{len(emails)-4} more</div>'
                if not emails:
                    msg="Blocked (will try website next time)" if "block" in status else "No emails found"
                    emails_html=f'<div style="font-size:11px;color:#aaa;margin-top:5px">{msg}</div>'
                status_c={"scraped":"#16a34a","blocked_mbasic":"#dc2626","no_emails":"#aaa"}.get(status,"#aaa")
                st.markdown(f'<div class="fb-card {cls}"><div style="display:flex;justify-content:space-between;align-items:center">'
                            f'<span class="fb-handle">{handle}</span>{src_tag}'
                            f'<span style="font-size:10px;color:{status_c};font-weight:600">{status} · {tt}s</span></div>'
                            f'{emails_html}</div>',unsafe_allow_html=True)
else:
    if not running:
        st.markdown('<div style="text-align:center;padding:50px 0;color:#bbb">'
                    '<div style="font-size:40px;opacity:.1;margin-bottom:12px">f</div>'
                    '<div style="font-size:17px;font-weight:800;color:#111;margin-bottom:8px">No results yet</div>'
                    '<div style="font-size:12px;line-height:1.9;max-width:360px;margin:0 auto">'
                    'Paste Facebook handles above and hit <strong>Start Extraction</strong><br>'
                    'Import handles from Scraper if you already ran a scrape</div></div>',unsafe_allow_html=True)

# engine
if st.session_state.get("fb_running") and st.session_state.get("fb_queue"):
    q=st.session_state.fb_queue; idx=st.session_state.fb_idx; total=len(q); delay=st.session_state.get("fb_delay_s",4); par=st.session_state.get("fb_par",False)
    if idx>=total: st.session_state.fb_running=False; st.rerun()
    else:
        BATCH=2 if par else 1; batch=q[idx:idx+BATCH]
        def run_fb(h): return h,scrape_fb_handle(h,delay=delay)
        if BATCH>1 and len(batch)>1:
            with ThreadPoolExecutor(max_workers=2) as ex:
                futs=[ex.submit(run_fb,h) for h in batch]
                for fut in as_completed(futs):
                    try: h,r=fut.result(); st.session_state.fb_results[h]=r
                    except: pass
        else:
            try: h,r=run_fb(batch[0]); st.session_state.fb_results[h]=r
            except: pass
        st.session_state.fb_idx=idx+len(batch)
        if st.session_state.fb_idx>=total: st.session_state.fb_running=False
        st.rerun()
