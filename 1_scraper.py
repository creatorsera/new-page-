"""
pages/1_scraper.py — MailHunter Scraper
Left-panel controls + right results table.
Writes to st.session_state["scraper_results"].
"""
import streamlit as st
import requests, re, io, time, random, pandas as pd
import xml.etree.ElementTree as ET, urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from collections import deque
from datetime import datetime

from utils import (
    is_valid_email, tier_key, tier_short, sort_by_tier, pick_best,
    confidence_score, conf_color, val_icon,
    validate_email_full, validate_with_fallback,
    fetch_page, extract_emails, extract_social,
    fetch_disposable_domains, build_xlsx_scraper,
    TIER1, TIER2, USER_AGENTS,
)

# ── PAGE CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.4rem 1.8rem 4rem !important; max-width:100% !important; background:#f5f5f3 !important; }

[data-testid="column"]:first-of-type {
    background:#fff; border-radius:14px; border:1px solid #e8e8e6;
    padding:1.2rem 1.1rem 1rem !important;
}
.logo { font-size:18px; font-weight:800; color:#111; letter-spacing:-.5px;
        display:flex; align-items:center; gap:9px; margin-bottom:2px; }
.logo-box { width:32px; height:32px; background:#111; border-radius:8px;
            display:flex; align-items:center; justify-content:center;
            font-size:16px; flex-shrink:0; color:#fff; }
.logo-tag { font-size:11px; color:#bbb; font-weight:400; }
.sec { font-size:9.5px; font-weight:700; letter-spacing:1.3px;
       text-transform:uppercase; color:#c0c0bc; display:block; margin-bottom:5px; }

.stButton > button {
    font-family:'Inter',sans-serif !important; font-weight:600 !important;
    border-radius:8px !important; font-size:12.5px !important; height:36px !important;
    transition:all 0.13s !important;
}
.stButton > button[kind="primary"] {
    background:#111 !important; border:2px solid #111 !important;
    color:#fff !important; box-shadow:0 1px 2px rgba(0,0,0,.15) !important;
}
.stButton > button[kind="primary"]:hover {
    background:#2d2d2d !important; transform:translateY(-1px) !important;
    box-shadow:0 3px 10px rgba(0,0,0,.2) !important;
}
.stButton > button[kind="primary"]:disabled {
    background:#e4e4e4 !important; border-color:#e4e4e4 !important;
    color:#aaa !important; box-shadow:none !important; transform:none !important;
}
.stButton > button[kind="secondary"] {
    background:#fff !important; border:1.5px solid #ddd !important; color:#555 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color:#999 !important; color:#111 !important; background:#fafaf8 !important;
}
.start-wrap .stButton > button { height:42px !important; font-size:14px !important; font-weight:700 !important; }
.stDownloadButton > button {
    font-family:'Inter',sans-serif !important; font-weight:600 !important;
    border-radius:8px !important; font-size:12.5px !important; height:36px !important;
    background:#fff !important; border:1.5px solid #ddd !important; color:#555 !important;
}
.stDownloadButton > button:hover { border-color:#999 !important; color:#111 !important; }
.stTextArea textarea {
    font-size:12px !important; border-radius:8px !important;
    border:1.5px solid #e4e4e0 !important; background:#fafaf8 !important;
    line-height:1.6 !important; resize:none !important; color:#333 !important;
}
.stTextArea textarea:focus { border-color:#111 !important; box-shadow:0 0 0 3px rgba(0,0,0,.05) !important; }
.stTextArea textarea::placeholder { color:#ccc !important; }
.stTextInput > div > input {
    border-radius:8px !important; border:1.5px solid #e4e4e0 !important;
    font-size:13px !important; height:36px !important; background:#fafaf8 !important;
}
.stTextInput > div > input:focus { border-color:#111 !important; box-shadow:0 0 0 3px rgba(0,0,0,.05) !important; }
[data-testid="stHorizontalRadio"] {
    background:#eeeeed !important; border-radius:10px !important;
    padding:3px !important; border:1px solid #e2e2e0 !important;
}
[data-testid="stHorizontalRadio"] label {
    font-size:11.5px !important; font-weight:600 !important; border-radius:7px !important;
    padding:5px 10px !important; color:#999 !important; flex:1 !important;
    text-align:center !important; cursor:pointer !important;
}
[data-testid="stHorizontalRadio"] label:has(input:checked) {
    background:#fff !important; color:#111 !important; box-shadow:0 1px 4px rgba(0,0,0,.1) !important;
}
[data-testid="stHorizontalRadio"] [data-baseweb="radio"] { display:none !important; }
[data-testid="stMetric"] { background:#fff; border:1px solid #eaeae6; border-radius:10px; padding:.7rem .85rem !important; }
[data-testid="stMetricLabel"] p { font-size:9.5px !important; font-weight:700 !important; color:#bbb !important; text-transform:uppercase !important; letter-spacing:.6px !important; }
[data-testid="stMetricValue"] { font-size:22px !important; font-weight:800 !important; color:#111 !important; letter-spacing:-.7px !important; }
.log-box { background:#1c1c1c; border-radius:8px; padding:10px 12px;
    font-family:'Courier New',Courier,monospace; font-size:10.5px; line-height:1.8;
    max-height:210px; overflow-y:auto; margin-top:6px; }
.log-box::-webkit-scrollbar { width:4px; }
.log-box::-webkit-scrollbar-thumb { background:#444; border-radius:2px; }
.ll-site  { color:#fff; font-weight:700; border-top:1px solid #2a2a2a; margin-top:4px; padding-top:4px; }
.ll-site:first-child { border-top:none; margin-top:0; padding-top:0; }
.ll-email { color:#4ade80; font-weight:600; }
.ll-page  { color:#444; }
.ll-skip  { color:#fb923c; }
.ll-timing{ color:#3a3a3a; font-size:10px; }
.ll-done  { color:#555; }
.ll-info  { color:#444; }
.ll-warn  { color:#f87171; }
.prog-wrap { margin:8px 0 2px; }
.prog-top  { display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:600; color:#333; margin-bottom:5px; }
.prog-right{ font-size:11px; color:#aaa; font-weight:400; }
.prog-track{ height:4px; background:#eee; border-radius:99px; overflow:hidden; }
.prog-fill { height:100%; border-radius:99px; transition:width .4s ease; }
.scan-dot  { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; animation:pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.25;transform:scale(.8)} }
.mode-strip { display:flex; align-items:flex-start; gap:9px; padding:8px 11px;
    border-radius:8px; background:#f8f8f6; border:1px solid #e8e8e4; margin:5px 0 0; }
.mode-dot  { width:8px; height:8px; border-radius:50%; flex-shrink:0; margin-top:4px; }
.mode-name { font-size:12px; font-weight:700; }
.mode-tip  { font-size:10.5px; color:#888; margin-top:2px; line-height:1.45; }
.pills { display:flex; flex-wrap:wrap; gap:3px; margin:5px 0 0; }
.pill  { font-size:10.5px; background:#eeeeed; border:1px solid #e0e0dc; border-radius:4px; padding:2px 7px; color:#888; }
.flt-bar .stButton > button { height:27px !important; font-size:10.5px !important; border-radius:99px !important; padding:0 9px !important; font-weight:600 !important; }
.flt-bar .stButton > button[kind="secondary"] { background:#eeeeed !important; border:1px solid #e0e0dc !important; color:#888 !important; }
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(1) button[kind="primary"]{background:#111 !important;border-color:#111 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(2) button[kind="primary"]{background:#d97706 !important;border-color:#d97706 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(3) button[kind="primary"]{background:#6366f1 !important;border-color:#6366f1 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(4) button[kind="primary"]{background:#64748b !important;border-color:#64748b !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(5) button[kind="primary"]{background:#e11d48 !important;border-color:#e11d48 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(6) button[kind="primary"]{background:#16a34a !important;border-color:#16a34a !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(7) button[kind="primary"]{background:#d97706 !important;border-color:#d97706 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(8) button[kind="primary"]{background:#dc2626 !important;border-color:#dc2626 !important;color:#fff !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(2) button[kind="secondary"]{color:#92400e !important;background:#fffbeb !important;border-color:#fde68a !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(3) button[kind="secondary"]{color:#4338ca !important;background:#eef2ff !important;border-color:#c7d2fe !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(4) button[kind="secondary"]{color:#475569 !important;background:#f1f5f9 !important;border-color:#cbd5e1 !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(5) button[kind="secondary"]{color:#be123c !important;background:#fff1f2 !important;border-color:#fecdd3 !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(6) button[kind="secondary"]{color:#15803d !important;background:#f0fdf4 !important;border-color:#bbf7d0 !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(7) button[kind="secondary"]{color:#92400e !important;background:#fffbeb !important;border-color:#fde68a !important;}
.flt-bar [data-testid="stHorizontalBlock"]>div:nth-child(8) button[kind="secondary"]{color:#b91c1c !important;background:#fff5f5 !important;border-color:#fecaca !important;}
.act-card { background:#fafaf8; border:1px solid #e8e8e4; border-radius:10px; padding:11px 13px; margin-top:3px; }
.val-result { margin-top:8px; font-size:11.5px; color:#666; padding:6px 9px;
    background:#fff; border:1px solid #eee; border-radius:6px; line-height:1.6; }
.stTabs [data-baseweb="tab-list"] { gap:2px !important; background:#eeeeed !important; border-radius:8px !important; padding:3px !important; border:1px solid #e2e2e0 !important; }
.stTabs [data-baseweb="tab"] { font-size:11.5px !important; font-weight:600 !important; border-radius:6px !important; padding:4px 12px !important; color:#999 !important; }
.stTabs [aria-selected="true"] { background:#fff !important; color:#111 !important; box-shadow:0 1px 3px rgba(0,0,0,.08) !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none !important; }
details { border:1px solid #e8e8e4 !important; border-radius:8px !important; }
details > summary { font-size:12px !important; font-weight:600 !important; color:#444 !important; padding:9px 13px !important; }
details[open] > summary { border-bottom:1px solid #f0f0ee !important; }
hr { border-color:#eeeeec !important; margin:10px 0 !important; }
[data-testid="stSlider"] > div > div > div > div { background:#111 !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
PRIORITY_KEYWORDS = [
    ("contact",100),("write-for-us",95),("writeforus",95),("write_for_us",95),
    ("guest-post",90),("guest_post",90),("guestpost",90),("advertise",88),("advertising",88),
    ("contribute",85),("contributor",85),("submit",82),("submission",82),("pitch",80),
    ("about",75),("about-us",75),("about_us",75),("team",70),("our-team",70),("staff",70),
    ("people",70),("work-with-us",68),("partner",65),("reach-us",60),("get-in-touch",60),
    ("press",55),("media",50),
]
HUNT_KEYWORDS = [
    ("write-for-us",100),("writeforus",100),("write_for_us",100),("guest-post",98),
    ("guest_post",98),("guestpost",98),("advertise",96),("advertising",96),("sponsor",92),
    ("contribute",90),("contributor",90),("submit",86),("submission",86),("pitch",84),
    ("work-with-us",82),("partner",78),
]
MODE_CFG = {
    "Quick":   {"quick":True,"max_pages":0,"max_depth":0,"sitemap":False,"delay":0.05,"hunt":False,
                "color":"#7c3aed","tag":"Sitemap top-4 priority pages",
                "tip":"Reads sitemap, scores URLs, scrapes top 4 contact/about pages. ~5-15s per site."},
    "Easy":    {"quick":False,"max_pages":5,"max_depth":0,"sitemap":False,"delay":0.2,"hunt":False,
                "color":"#16a34a","tag":"Priority pages + homepage",
                "tip":"Sitemap priority pages + homepage. Good for well-structured sites. ~30s."},
    "Medium":  {"quick":False,"max_pages":50,"max_depth":3,"sitemap":False,"delay":0.4,"hunt":False,
                "color":"#d97706","tag":"Sitemap-first then crawl",
                "tip":"Priority pages then up to 50 internal pages, 3 levels deep. 2-5 min."},
    "Extreme": {"quick":False,"max_pages":300,"max_depth":6,"sitemap":True,"delay":0.2,"hunt":False,
                "color":"#dc2626","tag":"Full sitemap + deep crawl",
                "tip":"Exhaustive — full sitemap plus 300-page crawl. 5-15 min per site."},
    "Hunt":    {"quick":False,"max_pages":8,"max_depth":1,"sitemap":False,"delay":0.1,"hunt":True,
                "color":"#0891b2","tag":"Write-for-us and advertise only",
                "tip":"Outreach mode — only scores write-for-us, advertise, sponsor, pitch pages."},
}

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k,v in {
    "scraper_results":{},"scraper_domains":set(),"scan_state":"idle",
    "scan_queue":[],"scan_idx":0,"log_lines":[],"scraper_sessions":[],
    "scraper_mode":"Quick","scraper_filter":"All",
    "skip_t1":True,"respect_robots":False,"scrape_fb":False,
    "auto_validate":False,"parallel":True,"mx_cache":{},
    "seen_emails":set(),
}.items():
    if k not in st.session_state: st.session_state[k]=v

# ── SCRAPING ENGINE ───────────────────────────────────────────────────────────
def score_url(url, kws):
    from urllib.parse import urlparse as _up
    path = _up(url).path.lower(); best=0
    for kw,sc in kws:
        if kw in path: best=max(best,sc-path.count("/")*3)
    return best

def get_priority_urls(root_url, hunt_mode=False, limit=None):
    from urllib.parse import urljoin
    import xml.etree.ElementTree as ET_
    kws = HUNT_KEYWORDS if hunt_mode else PRIORITY_KEYWORDS
    urls=[]
    for c in [urljoin(root_url,"/sitemap.xml"), urljoin(root_url,"/sitemap_index.xml")]:
        html,_=fetch_page(c,timeout=8)
        if not html: continue
        try:
            re_=ET_.fromstring(html); ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
            for loc in re_.findall(".//sm:loc",ns):
                u=loc.text.strip()
                if u.endswith(".xml"):
                    sub,_=fetch_page(u,timeout=8)
                    if sub:
                        try:
                            for sl in ET_.fromstring(sub).findall(".//sm:loc",ns): urls.append(sl.text.strip())
                        except: pass
                else: urls.append(u)
        except: pass
        if urls: break
    if urls:
        scored=sorted([(u,score_url(u,kws)) for u in urls if score_url(u,kws)>0],key=lambda x:-x[1])
        result=[u for u,_ in scored]
        return (result[:limit] if limit else result), True
    base=root_url.rstrip("/")
    paths=["/contact","/contact-us","/about","/about-us","/team","/write-for-us",
           "/advertise","/contribute","/pitch","/submit","/partner","/press",
           "/guest-post","/work-with-us","/sponsor","/submission","/staff","/people"]
    fb=sorted([(base+p,score_url(base+p,kws)) for p in paths if score_url(base+p,kws)>0],key=lambda x:-x[1])
    result=[u for u,_ in fb]
    return (result[:limit] if limit else result), False

def get_internal_links(html, base_url, root_domain):
    from urllib.parse import urljoin, urlparse
    soup=BeautifulSoup(html,"html.parser") if False else __import__('bs4').BeautifulSoup(html,"html.parser")
    links=[]
    for a in soup.find_all("a",href=True):
        full=urljoin(base_url,a["href"]); p=urlparse(full)
        if p.netloc==root_domain and p.scheme in ("http","https"):
            links.append(full.split("#")[0].split("?")[0])
    return list(set(links))

def find_outreach_links(html, base_url, root_domain):
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup as BS
    KW=["write for us","write-for-us","guest post","contribute","submission","pitch","advertise","sponsor"]
    soup=BS(html,"html.parser"); found=[]
    for a in soup.find_all("a",href=True):
        href=a.get("href",""); text=(a.get_text(" ",strip=True)+" "+href).lower()
        if any(kw in text for kw in KW):
            full=urljoin(base_url,href); p=urlparse(full)
            if p.netloc==root_domain and p.scheme in ("http","https"):
                found.append(full.split("#")[0].split("?")[0])
    return list(set(found))

def load_robots(root_url, respect):
    if not respect: return None
    rp=urllib.robotparser.RobotFileParser()
    rp.set_url(root_url.rstrip("/")+"/robots.txt")
    try: rp.read()
    except: pass
    return rp

def robots_ok(rp, url):
    if rp is None: return True
    try: return rp.can_fetch("*",url)
    except: return True

def _scrape_site(root_url, cfg_snap, skip_t1, respect_robots, scrape_fb_flag):
    """Thread-safe — no session_state access."""
    from urllib.parse import urlparse, urljoin
    from bs4 import BeautifulSoup as BS
    logs=[]; log=lambda i,k: logs.append((i,k))
    t0=time.time(); root_domain=urlparse(root_url).netloc
    visited=set(); queue=deque()
    all_emails=set(); all_tw,all_li,all_fb=set(),set(),set()
    rp=load_robots(root_url,respect_robots)
    quick_mode=cfg_snap.get("quick",False); hunt_mode=cfg_snap.get("hunt",False)
    max_pages=cfg_snap.get("max_pages",0); max_depth=cfg_snap.get("max_depth",0)
    use_sitemap=cfg_snap.get("sitemap",False)

    log(("info","scanning sitemap...",None,None),"info")
    limit=4 if quick_mode else None
    priority_urls,used_sm=get_priority_urls(root_url,hunt_mode=hunt_mode,limit=limit)
    log(("info",f"sitemap: {len(priority_urls)} pages" if used_sm else "no sitemap, using known paths",None,None),"info")

    if not quick_mode and use_sitemap and used_sm:
        from utils import fetch_page as fp_
        import xml.etree.ElementTree as ET_
        for c in [urljoin(root_url,"/sitemap.xml"),urljoin(root_url,"/sitemap_index.xml")]:
            html,_=fp_(c,timeout=8)
            if html:
                try:
                    r_=ET_.fromstring(html); ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
                    pset=set(priority_urls)
                    for loc in r_.findall(".//sm:loc",ns):
                        u=loc.text.strip()
                        if not u.endswith(".xml") and u not in pset: queue.append((u,0,False))
                except: pass
                break

    for u in reversed(priority_urls): queue.appendleft((u,0,True))
    if not quick_mode: queue.append((root_url,0,False))
    pages_done=0; domain_blocked=False; page_limit=max_pages+len(priority_urls)

    while queue and (quick_mode or pages_done<page_limit):
        url,depth,is_priority=queue.popleft()
        if url in visited: continue
        visited.add(url)
        short=url.replace("https://","").replace("http://","")[:55]
        if not robots_ok(rp,url):
            if not is_priority: pages_done+=1; continue
        log(("page_start",short,"P" if is_priority else str(pages_done+1),None),"active")
        tmo=6 if quick_mode else 12
        t_p=time.time(); html,status=fetch_page(url,timeout=tmo); elapsed=round(time.time()-t_p,2)
        if status in (429,503):
            log(("warn",f"rate limited ({status}), retry...",short,None),"warn"); time.sleep(7)
            html,status=fetch_page(url,timeout=tmo)
        if status==403 and (not html or "cloudflare" in (html or "").lower()):
            log(("warn",f"blocked - skipping domain",short,None),"warn"); domain_blocked=True; break
        if html:
            found=extract_emails(html); new=found-all_emails
            tw,li,fb=extract_social(html); new_tw=tw-all_tw; new_li=li-all_li; new_fb=fb-all_fb
            all_emails.update(found); all_tw.update(tw); all_li.update(li); all_fb.update(fb)
            if not hunt_mode:
                for wlink in find_outreach_links(html,url,root_domain):
                    if wlink not in visited:
                        queue.appendleft((wlink,0,True))
                        log(("info",f"outreach: {wlink.replace('https://','')[:38]}",None,None),"info")
            for e in sort_by_tier(new): log(("email",e,short,None),"email")
            log(("timing",f"{elapsed}s - {len(new)} email(s)",None,None),"timing")
            if not is_priority and not quick_mode and depth<max_depth:
                for link in get_internal_links(html,url,root_domain):
                    if link not in visited: queue.append((link,depth+1,False))
            if skip_t1 and any(TIER1.match(e) for e in all_emails):
                t1e=next(e for e in all_emails if TIER1.match(e))
                log(("skip",f"T1 found ({t1e}) - done",None,None),"skip"); break
        else:
            log(("timing",f"{elapsed}s - no response ({status})",None,None),"timing")
        if not is_priority: pages_done+=1
        if quick_mode and pages_done>=4: break

    if scrape_fb_flag and all_fb:
        slug=sorted(all_fb)[0].replace("facebook.com/","").strip("/")
        if slug:
            log(("info",f"FB: {slug}",None,None),"info")
            fb_html,_=fetch_page(f"https://www.facebook.com/{slug}",timeout=14,mobile=True)
            if fb_html:
                fb_emails=extract_emails(fb_html)
                for e in sort_by_tier(fb_emails): log(("email",e,"fb",""),"email")
                all_emails.update(fb_emails)

    best=pick_best(all_emails); total_t=round(time.time()-t0,1)
    log(("done",f"{root_domain} - {len(all_emails)} email(s) in {total_t}s",None,None),"done")
    return {
        "Domain":root_domain,"Best Email":best or "","Best Tier":tier_short(best) if best else "",
        "All Emails":sort_by_tier(all_emails),"Twitter":sorted(all_tw),
        "LinkedIn":sorted(all_li),"Facebook":sorted(all_fb),
        "Pages Scraped":pages_done,"Total Time":total_t,"Source URL":root_url,
        "MX":{},"Blocked":domain_blocked,
    }, logs

def render_log(ph):
    h=""
    for item,kind in st.session_state.log_lines[-80:]:
        _,text,_,extra=item; t=str(text)[:88]
        if   kind=="site":   h+=f'<div class="ll-site">[ {t} ]</div>'
        elif kind=="active": h+=f'<div class="ll-page">  &gt; {t}</div>'
        elif kind=="email":  h+=f'<div class="ll-email">  @ {t}</div>'
        elif kind=="timing": h+=f'<div class="ll-timing">    {t}</div>'
        elif kind=="skip":   h+=f'<div class="ll-skip">  ! {t}</div>'
        elif kind=="done":   h+=f'<div class="ll-done">  ok {t}</div>'
        elif kind=="info":   h+=f'<div class="ll-info">  . {t}</div>'
        elif kind=="warn":   h+=f'<div class="ll-warn">  !! {t}</div>'
    ph.markdown(f'<div class="log-box">{h}</div>',unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────────────────────────────────────
h1,h2=st.columns([5,1])
with h1:
    st.markdown('<div class="logo"><div class="logo-box">S</div>Scraper</div>'
                '<div class="logo-tag">sitemap-first &nbsp;|&nbsp; parallel engine &nbsp;|&nbsp; '
                'fallback validation &nbsp;|&nbsp; confidence scoring</div>',unsafe_allow_html=True)
with h2:
    results=st.session_state.get("scraper_results",{})
    if results:
        xlsx=build_xlsx_scraper(results)
        st.download_button("⬇ Export .xlsx",xlsx,
                           f"scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="scraper_xlsx")
st.divider()
left,right=st.columns([1,2.8],gap="large")

with left:
    st.markdown('<span class="sec">Target URLs</span>',unsafe_allow_html=True)
    tp,tc=st.tabs(["Paste","Upload"])
    urls_to_scrape=[]
    with tp:
        raw=st.text_area("u",label_visibility="collapsed",
                         placeholder="https://magazine.com\nhttps://techblog.io\nnewspaper.org",
                         height=105,key="url_input")
        for line in raw.splitlines():
            line=line.strip()
            if not line: continue
            if not line.startswith("http"): line="https://"+line
            urls_to_scrape.append(line)
    with tc:
        uploaded=st.file_uploader("f",type=["csv","txt"],label_visibility="collapsed")
        if uploaded:
            rb=uploaded.read()
            if uploaded.name.endswith(".csv"):
                try:
                    df_up=pd.read_csv(io.BytesIO(rb)); cols_u=list(df_up.columns)
                    hints=["url","link","website","site","domain","href"]
                    defcol=next((c for c in cols_u if any(h in c.lower() for h in hints)),cols_u[0])
                    col_sel=st.selectbox("Column",cols_u,index=cols_u.index(defcol),key="csv_col")
                    for u in df_up[col_sel].dropna().astype(str):
                        u=u.strip()
                        if not u.startswith("http"): u="https://"+u
                        urls_to_scrape.append(u)
                    st.caption(f"OK {len(urls_to_scrape)} URLs")
                except Exception as ex: st.error(f"CSV error: {ex}")
            else:
                for line in rb.decode("utf-8","ignore").splitlines():
                    line=line.strip()
                    if not line: continue
                    if not line.startswith("http"): line="https://"+line
                    urls_to_scrape.append(line)
                st.caption(f"OK {len(urls_to_scrape)} URLs")

    if urls_to_scrape:
        pills="".join(f'<span class="pill">{u.replace("https://","")[:20]}</span>' for u in urls_to_scrape[:5])
        if len(urls_to_scrape)>5: pills+=f'<span class="pill">+{len(urls_to_scrape)-5}</span>'
        st.markdown(f'<div class="pills">{pills}</div>',unsafe_allow_html=True)

    st.markdown('<span class="sec" style="margin-top:14px;display:block">Crawl Mode</span>',unsafe_allow_html=True)
    MODE_LABELS=list(MODE_CFG.keys())
    cur_mode=st.session_state.get("scraper_mode","Quick")
    if cur_mode not in MODE_LABELS: cur_mode="Quick"
    chosen=st.radio("mode_r",MODE_LABELS,index=MODE_LABELS.index(cur_mode),horizontal=True,label_visibility="collapsed",key="mode_radio")
    if chosen!=st.session_state.scraper_mode: st.session_state.scraper_mode=chosen; st.rerun()
    mi=MODE_CFG[chosen]
    st.markdown(f'<div class="mode-strip"><div class="mode-dot" style="background:{mi["color"]}"></div>'
                f'<div><div class="mode-name" style="color:{mi["color"]}">{chosen} &mdash; {mi["tag"]}</div>'
                f'<div class="mode-tip">{mi["tip"]}</div></div></div>',unsafe_allow_html=True)
    mode_key=chosen
    cfg={k:v for k,v in mi.items() if k not in ("color","tag","tip")}
    if mode_key=="Medium":
        cfg["max_depth"]=st.slider("Depth",1,6,3,key="sl_d")
        cfg["max_pages"]=st.slider("Pages/site",10,200,50,key="sl_p")
    elif mode_key=="Extreme":
        cfg["max_pages"]=st.slider("Pages/site",50,500,300,key="sl_px")

    st.divider()
    scan_state=st.session_state.scan_state
    if scan_state=="idle":
        st.markdown('<div class="start-wrap">',unsafe_allow_html=True)
        do_start=st.button("Start Scan",type="primary",use_container_width=True,disabled=not urls_to_scrape,key="btn_s")
        st.markdown('</div>',unsafe_allow_html=True)
    elif scan_state=="running":
        do_start=False
        c1,c2=st.columns(2)
        with c1:
            if st.button("Pause",type="primary",use_container_width=True,key="btn_p"): st.session_state.scan_state="paused"; st.rerun()
        with c2:
            if st.button("Stop",type="secondary",use_container_width=True,key="btn_st"): st.session_state.scan_state="done"; st.rerun()
    elif scan_state=="paused":
        do_start=False
        c1,c2=st.columns(2)
        with c1:
            if st.button("Resume",type="primary",use_container_width=True,key="btn_r"): st.session_state.scan_state="running"; st.rerun()
        with c2:
            if st.button("Stop",type="secondary",use_container_width=True,key="btn_st2"): st.session_state.scan_state="done"; st.rerun()
    else:
        st.markdown('<div class="start-wrap">',unsafe_allow_html=True)
        do_start=st.button("New Scan",type="primary",use_container_width=True,disabled=not urls_to_scrape,key="btn_ns")
        st.markdown('</div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("Clear",type="secondary",use_container_width=True,key="btn_cl"):
            for k in ("scraper_results","scan_queue","log_lines"): st.session_state[k]={} if k=="scraper_results" else []
            st.session_state.scan_state="idle"; st.session_state.scan_idx=0; st.rerun()
    with c2:
        if st.session_state.get("scraper_results") and scan_state!="running":
            if st.button("Save",type="secondary",use_container_width=True,key="btn_sv"):
                ts=datetime.now().strftime("%b %d %H:%M")
                for r in st.session_state.scraper_results.values():
                    for e in r.get("All Emails",[]): st.session_state.seen_emails.add(e)
                st.session_state.scraper_sessions.append({"name":f"Scan {len(st.session_state.scraper_sessions)+1} - {ts}","results":dict(st.session_state.scraper_results)})
                st.rerun()

    do_start=do_start if "do_start" in dir() else False
    if do_start and urls_to_scrape:
        new_urls=[u for u in urls_to_scrape if urlparse(u).netloc not in st.session_state.scraper_domains]
        if new_urls:
            if scan_state=="done": st.session_state.scraper_results={}
            st.session_state.update(scan_queue=new_urls,scan_idx=0,scan_state="running",log_lines=[])
            st.rerun()

    prog_ph=st.empty(); log_ph=st.empty()
    if scan_state in ("running","paused") and st.session_state.scan_queue:
        idx=st.session_state.scan_idx; total=len(st.session_state.scan_queue)
        pct=round(idx/total*100,1) if total else 0; done=len(st.session_state.scraper_results)
        paused_=scan_state=="paused"; dot_c="#fb923c" if paused_ else "#4ade80"; bar_c="#fb923c" if paused_ else "#16a34a"
        lbl="Paused" if paused_ else "Scanning"
        par_n=" | 4x parallel" if st.session_state.get("parallel",True) else ""
        prog_ph.markdown(f'<div class="prog-wrap"><div class="prog-top"><span><span class="scan-dot" style="background:{dot_c}"></span>{lbl}</span><span class="prog-right">{done} done / {total} total{par_n}</span></div><div class="prog-track"><div class="prog-fill" style="width:{pct}%;background:{bar_c}"></div></div><div style="font-size:10px;color:#bbb;margin-top:2px;text-align:right">{pct}%</div></div>',unsafe_allow_html=True)
    if st.session_state.log_lines: render_log(log_ph)

    st.divider()
    with st.expander("Settings"):
        st.session_state.parallel=st.toggle("Parallel scraping (4x)",value=st.session_state.parallel,key="t_par")
        st.session_state.skip_t1=st.toggle("Stop once Tier 1 found",value=st.session_state.skip_t1,key="t_sk")
        st.session_state.respect_robots=st.toggle("Respect robots.txt",value=st.session_state.respect_robots,key="t_rb")
        st.session_state.auto_validate=st.toggle("Auto-validate after scan",value=st.session_state.auto_validate,key="t_av")
        st.session_state.scrape_fb=st.toggle("Auto-scrape Facebook",value=st.session_state.scrape_fb,key="t_fb")
        n_mem=len(st.session_state.scraper_domains); n_seen=len(st.session_state.seen_emails)
        if n_mem or n_seen:
            st.caption(f"Memory: {n_mem} domains | {n_seen} seen")
            if st.button("Clear memory",key="btn_mem",use_container_width=True):
                st.session_state.scraper_domains=set(); st.session_state.seen_emails=set(); st.rerun()
    if st.session_state.scraper_sessions:
        with st.expander(f"Saved sessions ({len(st.session_state.scraper_sessions)})"):
            for i,sess in enumerate(st.session_state.scraper_sessions):
                nd=len(sess["results"]); ne=sum(len(r.get("All Emails",[])) for r in sess["results"].values())
                a,b,c=st.columns([3,1,1])
                with a: st.caption(f"**{sess['name']}** | {nd} sites | {ne} emails")
                with b:
                    if st.button("Load",key=f"ld_{i}",use_container_width=True):
                        st.session_state.scraper_results=sess["results"]; st.session_state.scan_state="done"; st.rerun()
                with c:
                    if st.button("Del",key=f"dl_{i}",use_container_width=True):
                        st.session_state.scraper_sessions.pop(i); st.rerun()

with right:
    results=st.session_state.get("scraper_results",{}); scan_state=st.session_state.scan_state
    if not results:
        mi_=MODE_CFG.get(st.session_state.scraper_mode,MODE_CFG["Quick"])
        st.markdown(f'<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 0;text-align:center"><div style="font-size:38px;margin-bottom:14px;opacity:.12">S</div><div style="font-size:17px;font-weight:800;color:#111;letter-spacing:-.4px;margin-bottom:12px">No results yet</div><div style="font-size:12px;color:#aaa;line-height:2;max-width:320px">Paste URLs on the left and hit <strong style="color:#333">Start Scan</strong><br><span style="color:{mi_["color"]};font-weight:600">{chosen} mode:</span> {mi_["tag"]}<br><span style="color:#bbb">Enable Parallel in Settings for 4x speed</span></div></div>',unsafe_allow_html=True)
    else:
        tot_d=len(results); tot_e=sum(len(r.get("All Emails",[])) for r in results.values())
        t1_cnt=sum(1 for r in results.values() if r.get("Best Tier","").startswith("Tier 1"))
        val_ok=sum(1 for r in results.values() if (r.get("Validation",{}) or {}).get("status")=="Deliverable")
        fallbk=sum(1 for r in results.values() if r.get("WasFallback")); no_e=sum(1 for r in results.values() if not r.get("Best Email"))
        m1,m2,m3,m4,m5,m6=st.columns(6)
        m1.metric("Sites",tot_d); m2.metric("Emails",tot_e); m3.metric("Tier 1",t1_cnt)
        m4.metric("Validated",val_ok); m5.metric("Fallback",fallbk); m6.metric("No Email",no_e)

        if scan_state=="done":
            to_val=[d for d,r in results.items() if r.get("All Emails") and not r.get("Validation")]
            if to_val:
                v1,v2=st.columns([4,1.3])
                with v1: st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:8px 13px;font-size:12px;color:#15803d;font-weight:600;margin:2px 0">{len(to_val)} domain(s) ready - uses fallback if best email fails</div>',unsafe_allow_html=True)
                with v2:
                    if st.button("Validate All",key="val_all",type="primary",use_container_width=True): st.session_state["run_validate_all"]=True; st.rerun()

        search=st.text_input("s",placeholder="Search...",label_visibility="collapsed",key="srch")
        FLT=[("All","All"),("T1","T1"),("T2","T2"),("T3","T3"),("None","None"),("OK","val_ok"),("Risk","val_risky"),("Fail","val_bad")]
        st.markdown('<div class="flt-bar">',unsafe_allow_html=True)
        fc=st.columns(len(FLT))
        for col,(lbl,val) in zip(fc,FLT):
            with col:
                active=st.session_state.scraper_filter==val
                if st.button(lbl,key=f"flt_{val}",type="primary" if active else "secondary",use_container_width=True):
                    st.session_state.scraper_filter=val; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

        seen=st.session_state.seen_emails; rows=[]
        for domain,r in results.items():
            all_e=r.get("All Emails",[]); best=r.get("Best Email",""); bt=r.get("Best Tier","")
            vbest=r.get("ValidatedBestEmail","") or best; val=r.get("Validation",{}) or {}
            val_st=val.get("status",""); conf=r.get("Confidence"); fb_=r.get("WasFallback",False)
            is_dup=best in seen and best and scan_state!="running"
            ed=(vbest or "---")+(" [fb]" if fb_ else "")+(" [dup]" if is_dup else "")
            rows.append({"Domain":domain,"Email":ed,"Tier":bt or "---","Score":conf if conf is not None else "",
                "Val":val_icon(val_st) if val_st else "---","Reason":val.get("reason","---") if val else "---",
                "SPF":("ok" if val.get("spf") else "no") if val else "---","DMARC":("ok" if val.get("dmarc") else "no") if val else "---",
                "CA":("yes" if val.get("catch_all") else "no") if val else "---",
                "+":f'+{len(all_e)-1}' if len(all_e)>1 else "","Pages":r.get("Pages Scraped",0),"s":r.get("Total Time","")})
        df=pd.DataFrame(rows)
        if search: m=(df["Domain"].str.contains(search,case=False,na=False)|df["Email"].str.contains(search,case=False,na=False)); df=df[m]
        flt=st.session_state.scraper_filter
        if   flt=="T1": df=df[df["Tier"].str.startswith("Tier 1",na=False)]
        elif flt=="T2": df=df[df["Tier"].str.startswith("Tier 2",na=False)]
        elif flt=="T3": df=df[df["Tier"].str.startswith("Tier 3",na=False)]
        elif flt=="None": df=df[df["Email"]=="---"]
        elif flt=="val_ok": df=df[df["Val"]=="✅"]
        elif flt=="val_risky": df=df[df["Val"]=="⚠️"]
        elif flt=="val_bad": df=df[df["Val"]=="❌"]
        st.caption(f'Showing {len(df)} of {tot_d}')
        st.dataframe(df,use_container_width=True,hide_index=True,height=min(560,44+max(len(df),1)*36),
                     column_config={"Domain":st.column_config.TextColumn("Domain",width=148),"Email":st.column_config.TextColumn("Email",width=200),
                         "Tier":st.column_config.TextColumn("Tier",width=65),"Score":st.column_config.NumberColumn("Score",width=50),
                         "Val":st.column_config.TextColumn("Val",width=40),"Reason":st.column_config.TextColumn("Reason",width=160),
                         "SPF":st.column_config.TextColumn("SPF",width=38),"DMARC":st.column_config.TextColumn("DMARC",width=48),
                         "CA":st.column_config.TextColumn("CA",width=40),"+":st.column_config.TextColumn("+",width=35),
                         "Pages":st.column_config.NumberColumn("Pages",width=48),"s":st.column_config.NumberColumn("s",width=42)})

        st.divider(); st.markdown('<span class="sec">Per-domain actions</span>',unsafe_allow_html=True)
        st.markdown('<div class="act-card">',unsafe_allow_html=True)
        pa1,pa2,pa3,pa4=st.columns([2.8,1,1,1])
        with pa1: sel=st.selectbox("d",list(results.keys()),label_visibility="collapsed",key="sel_d")
        r_sel=results.get(sel,{}); all_e_s=r_sel.get("All Emails",[]); best_s=r_sel.get("Best Email","")
        with pa2:
            if st.button("Validate",key="v1",type="primary",disabled=not all_e_s,use_container_width=True): st.session_state[f"vrun_{sel}"]=True; st.rerun()
        with pa3:
            if st.button("MX Check",key="mx1",type="secondary",disabled=not all_e_s,use_container_width=True): st.session_state[f"mxrun_{sel}"]=True; st.rerun()
        with pa4:
            if all_e_s: st.download_button("Get emails","\n".join(all_e_s),f"{sel}_emails.txt",key="cp1",use_container_width=True)
        val_d=r_sel.get("Validation",{}) or {}
        if val_d:
            vbest=r_sel.get("ValidatedBestEmail","") or best_s; icon=val_icon(val_d.get("status",""))
            conf=r_sel.get("Confidence"); cc=conf_color(conf); fb_fl=" [fallback]" if r_sel.get("WasFallback") else ""
            spf="SPF ok" if val_d.get("spf") else "no SPF"; dmarc=" | DMARC ok" if val_d.get("dmarc") else ""
            score_h=f' | <strong style="color:{cc}">{conf}/100</strong>' if conf is not None else ""
            st.markdown(f'<div class="val-result"><strong>[{icon}] {vbest}</strong>{fb_fl}{score_h} &nbsp;|&nbsp; {val_d.get("reason","")} &nbsp;|&nbsp; {spf}{dmarc}</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

        # validate single
        if sel and st.session_state.get(f"vrun_{sel}"):
            st.session_state[f"vrun_{sel}"]=False
            with st.spinner(f"Validating {sel}..."):
                chosen_e,vres,was_fb,orig_st=validate_with_fallback(all_e_s,best_s)
            if vres:
                conf_=confidence_score(chosen_e,vres)
                st.session_state.scraper_results[sel].update({"Validation":vres,"ValidatedBestEmail":chosen_e,"WasFallback":was_fb,"Confidence":conf_})
            st.rerun()
        # validate all
        if st.session_state.get("run_validate_all"):
            st.session_state["run_validate_all"]=False
            todo=[(d,r) for d,r in results.items() if r.get("All Emails") and not r.get("Validation")]
            if todo:
                vph=st.empty()
                for i,(dom,r) in enumerate(todo):
                    vph.markdown(f'<div class="log-box"><div class="ll-site">[ {dom} ]</div><div class="ll-info">  . checking {r.get("Best Email","")} ({i+1}/{len(todo)})</div></div>',unsafe_allow_html=True)
                    chosen_e,vres,was_fb,orig_st=validate_with_fallback(r.get("All Emails",[]),r.get("Best Email",""))
                    if vres:
                        conf_=confidence_score(chosen_e,vres)
                        st.session_state.scraper_results[dom].update({"Validation":vres,"ValidatedBestEmail":chosen_e,"WasFallback":was_fb,"Confidence":conf_})
                vph.empty(); st.rerun()

# ── SCAN ENGINE ───────────────────────────────────────────────────────────────
if st.session_state.scan_state=="running":
    queue=st.session_state.scan_queue; idx=st.session_state.scan_idx; total=len(queue)
    if idx>=total: st.session_state.scan_state="done"; st.rerun()
    else:
        use_parallel=st.session_state.get("parallel",True); BATCH=4 if use_parallel else 1
        cfg_snap=dict(cfg); skip_t1_=bool(st.session_state.skip_t1)
        respect_=bool(st.session_state.respect_robots); scrape_fb_=bool(st.session_state.scrape_fb)
        batch_urls=queue[idx:idx+BATCH]
        def run_one(url):
            if not url.startswith("http"): url="https://"+url
            row,logs=_scrape_site(url,cfg_snap,skip_t1_,respect_,scrape_fb_)
            return row,[((("site",row["Domain"],None,None),"site"))]+logs
        batch_results=[]
        if use_parallel and len(batch_urls)>1:
            with ThreadPoolExecutor(max_workers=BATCH) as ex:
                futs=[ex.submit(run_one,u) for u in batch_urls]
                for fut in as_completed(futs):
                    try: batch_results.append(fut.result())
                    except Exception as e: st.session_state.log_lines.append((("warn",f"error: {str(e)[:50]}",None,None),"warn"))
        else:
            try: batch_results.append(run_one(batch_urls[0]))
            except Exception as e: st.session_state.log_lines.append((("warn",f"error: {str(e)[:50]}",None,None),"warn"))
        for row,logs in batch_results:
            domain=row["Domain"]
            st.session_state.scraper_results[domain]=row
            st.session_state.scraper_domains.add(domain)
            st.session_state.log_lines.extend(logs)
        st.session_state.scan_idx=idx+len(batch_urls)
        time.sleep(cfg_snap.get("delay",0.1))
        if st.session_state.scan_idx>=total:
            st.session_state.scan_state="done"
            if st.session_state.get("auto_validate"): st.session_state["run_validate_all"]=True
        st.rerun()
