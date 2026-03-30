"""
pages/1_scraper.py — MailHunter Scraper
New full-width layout: top input + mode cards + full-width results table.
"""
import streamlit as st
import requests, re, io, time, random, pandas as pd
import xml.etree.ElementTree as ET, urllib.robotparser
from urllib.parse import urljoin, urlparse
from collections import deque
from datetime import datetime
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (is_valid_email, tier_key, tier_short, sort_by_tier, pick_best,
    confidence_score, conf_color, val_icon, validate_email_full, validate_with_fallback,
    fetch_page, extract_emails, extract_social, fetch_disposable_domains, build_xlsx_scraper, TIER1)
from theme import inject_css, page_header, render_log as _render_log

inject_css("scraper")
st.markdown("""<style>
.mh-start .stButton > button { height:46px !important; font-size:14px !important; font-weight:800 !important; border-radius:10px !important; }
.mh-mode-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; margin:8px 0 12px; }
.mh-mode-tile { padding:12px 13px; border-radius:10px; border:2px solid #e8e8e4; background:#fff; }
.mh-mode-tile.on { border-color:var(--ac); background:var(--ac-bg); }
.mh-scanbar { display:flex; align-items:center; gap:14px; background:#fff; border:1px solid #e8e8e4; border-radius:10px; padding:10px 16px; margin:8px 0; }
.mh-val-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 12px; background:#fafaf8; border:1px solid #eee; border-radius:8px; margin-top:8px; font-size:11.5px; }
.mh-val-em { font-family:'JetBrains Mono',monospace; font-weight:700; color:#111; font-size:12px; }
.mh-vtag { background:#f0f0ee; border-radius:4px; padding:1px 6px; font-size:10.5px; font-weight:600; color:#666; }
</style>""", unsafe_allow_html=True)

PRIORITY_KW = [("contact",100),("write-for-us",95),("writeforus",95),("guest-post",90),("guest_post",90),
    ("advertise",88),("advertising",88),("contribute",85),("submit",82),("pitch",80),("about",75),
    ("about-us",75),("team",70),("our-team",70),("staff",70),("work-with-us",68),("partner",65),
    ("reach-us",60),("get-in-touch",60),("press",55)]
HUNT_KW = [("write-for-us",100),("writeforus",100),("guest-post",98),("guest_post",98),
    ("advertise",96),("advertising",96),("sponsor",92),("contribute",90),("submit",86),
    ("pitch",84),("work-with-us",82),("partner",78)]
MODES = {
    "Quick":   {"quick":True,"max_pages":0,"max_depth":0,"sitemap":False,"delay":0.05,"hunt":False,
                "icon":"⚡","color":"#7c3aed","tag":"Sitemap top-4","tip":"~5-15s · reads sitemap, hits contact/about/write-for-us only"},
    "Easy":    {"quick":False,"max_pages":5,"max_depth":0,"sitemap":False,"delay":0.2,"hunt":False,
                "icon":"◎","color":"#16a34a","tag":"Priority + homepage","tip":"~30s · sitemap priority pages + homepage"},
    "Medium":  {"quick":False,"max_pages":50,"max_depth":3,"sitemap":False,"delay":0.4,"hunt":False,
                "icon":"◈","color":"#d97706","tag":"Sitemap then crawl","tip":"2-5 min · up to 50 pages, 3 levels deep"},
    "Extreme": {"quick":False,"max_pages":300,"max_depth":6,"sitemap":True,"delay":0.2,"hunt":False,
                "icon":"⬡","color":"#dc2626","tag":"Full sitemap + crawl","tip":"5-15 min · exhaustive, nothing missed"},
    "Hunt":    {"quick":False,"max_pages":8,"max_depth":1,"sitemap":False,"delay":0.1,"hunt":True,
                "icon":"🎯","color":"#0891b2","tag":"Write-for-us only","tip":"Fast outreach · only advertise/pitch/sponsor pages"},
}

for k,v in {"scraper_results":{},"scraper_domains":set(),"scan_state":"idle","scan_queue":[],"scan_idx":0,
    "log_lines":[],"scraper_sessions":[],"scraper_mode":"Quick","scraper_filter":"All",
    "skip_t1":True,"respect_robots":False,"scrape_fb":False,"auto_validate":False,
    "parallel":True,"mx_cache":{},"seen_emails":set()}.items():
    if k not in st.session_state: st.session_state[k]=v

def score_url(url,kws):
    path=urlparse(url).path.lower(); best=0
    for kw,sc in kws:
        if kw in path: best=max(best,sc-path.count("/")*3)
    return best

def get_priority_urls(root_url,hunt=False,limit=None):
    kws=HUNT_KW if hunt else PRIORITY_KW; urls=[]
    for c in [urljoin(root_url,"/sitemap.xml"),urljoin(root_url,"/sitemap_index.xml")]:
        html,_=fetch_page(c,timeout=8)
        if not html: continue
        try:
            r_=ET.fromstring(html); ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
            for loc in r_.findall(".//sm:loc",ns):
                u=loc.text.strip()
                if u.endswith(".xml"):
                    sub,_=fetch_page(u,timeout=8)
                    if sub:
                        try:
                            for sl in ET.fromstring(sub).findall(".//sm:loc",ns): urls.append(sl.text.strip())
                        except: pass
                else: urls.append(u)
        except: pass
        if urls: break
    if urls:
        sc=sorted([(u,score_url(u,kws)) for u in urls if score_url(u,kws)>0],key=lambda x:-x[1])
        res=[u for u,_ in sc]; return (res[:limit] if limit else res),True
    base=root_url.rstrip("/")
    paths=["/contact","/contact-us","/about","/about-us","/team","/write-for-us","/advertise",
           "/contribute","/pitch","/submit","/partner","/press","/guest-post","/work-with-us"]
    fb=sorted([(base+p,score_url(base+p,kws)) for p in paths if score_url(base+p,kws)>0],key=lambda x:-x[1])
    res=[u for u,_ in fb]; return (res[:limit] if limit else res),False

def get_links(html,base,domain):
    soup=BeautifulSoup(html,"html.parser"); links=[]
    for a in soup.find_all("a",href=True):
        full=urljoin(base,a["href"]); p=urlparse(full)
        if p.netloc==domain and p.scheme in("http","https"): links.append(full.split("#")[0].split("?")[0])
    return list(set(links))

def find_outreach(html,base,domain):
    KW=["write for us","write-for-us","guest post","contribute","submission","pitch","advertise","sponsor"]
    soup=BeautifulSoup(html,"html.parser"); found=[]
    for a in soup.find_all("a",href=True):
        href=a.get("href",""); text=(a.get_text(" ",strip=True)+" "+href).lower()
        if any(k in text for k in KW):
            full=urljoin(base,href); p=urlparse(full)
            if p.netloc==domain and p.scheme in("http","https"): found.append(full.split("#")[0].split("?")[0])
    return list(set(found))

def _scrape_site(root_url,cfg,skip_t1,respect,sfb):
    import urllib.robotparser as urp
    logs=[]; log=lambda i,k: logs.append((i,k))
    t0=time.time(); domain=urlparse(root_url).netloc
    visited=set(); queue=deque(); all_e=set(); all_tw,all_li,all_fb=set(),set(),set()
    rp=None
    if respect:
        rp=urp.RobotFileParser(); rp.set_url(root_url.rstrip("/")+"/robots.txt")
        try: rp.read()
        except: pass
    quick=cfg.get("quick",False); hunt=cfg.get("hunt",False)
    mp=cfg.get("max_pages",0); md=cfg.get("max_depth",0)
    log(("info","scanning sitemap...",None,None),"info")
    lim=4 if quick else None; p_urls,used_sm=get_priority_urls(root_url,hunt=hunt,limit=lim)
    log(("info",f"sitemap: {len(p_urls)} pages" if used_sm else "no sitemap",None,None),"info")
    if not quick and cfg.get("sitemap") and used_sm:
        for c in [urljoin(root_url,"/sitemap.xml")]:
            html,_=fetch_page(c,timeout=8)
            if html:
                try:
                    r_=ET.fromstring(html); ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}; ps=set(p_urls)
                    for loc in r_.findall(".//sm:loc",ns):
                        u=loc.text.strip()
                        if not u.endswith(".xml") and u not in ps: queue.append((u,0,False))
                except: pass
                break
    for u in reversed(p_urls): queue.appendleft((u,0,True))
    if not quick: queue.append((root_url,0,False))
    pd_=0; blocked=False; plim=mp+len(p_urls)
    while queue and (quick or pd_<plim):
        url,depth,isp=queue.popleft()
        if url in visited: continue
        visited.add(url)
        short=url.replace("https://","").replace("http://","")[:55]
        if rp and not (rp.can_fetch("*",url) if rp else True):
            if not isp: pd_+=1; continue
        log(("page_start",short,"P" if isp else str(pd_+1),None),"active")
        tmo=6 if quick else 12; tp=time.time(); html,status=fetch_page(url,timeout=tmo); el=round(time.time()-tp,2)
        if status in(429,503):
            log(("warn","rate limited, retry...",short,None),"warn"); time.sleep(7); html,status=fetch_page(url,timeout=tmo)
        if status==403 and (not html or "cloudflare" in(html or "").lower()):
            log(("warn","blocked - skipping",short,None),"warn"); blocked=True; break
        if html:
            found=extract_emails(html); new=found-all_e
            tw,li,fb=extract_social(html); all_e.update(found); all_tw.update(tw); all_li.update(li); all_fb.update(fb)
            if not hunt:
                for wl in find_outreach(html,url,domain):
                    if wl not in visited: queue.appendleft((wl,0,True)); log(("info",f"outreach: {wl.replace('https://','')[:38]}",None,None),"info")
            for e in sort_by_tier(new): log(("email",e,short,None),"email")
            log(("timing",f"{el}s - {len(new)} email(s)",None,None),"timing")
            if not isp and not quick and depth<md:
                for link in get_links(html,url,domain):
                    if link not in visited: queue.append((link,depth+1,False))
            if skip_t1 and any(TIER1.match(e) for e in all_e):
                t1e=next(e for e in all_e if TIER1.match(e)); log(("skip",f"T1 ({t1e}) done",None,None),"skip"); break
        else: log(("timing",f"{el}s - no response ({status})",None,None),"timing")
        if not isp: pd_+=1
        if quick and pd_>=4: break
    if sfb and all_fb:
        slug=sorted(all_fb)[0].replace("facebook.com/","").strip("/")
        if slug:
            log(("info",f"FB: mbasic.facebook.com/{slug}",None,None),"info")
            for fb_url in [f"https://mbasic.facebook.com/{slug}",f"https://mbasic.facebook.com/{slug}/about"]:
                fb_html,_=fetch_page(fb_url,timeout=14,mobile=True)
                if fb_html: all_e.update(extract_emails(fb_html)); time.sleep(2)
    best=pick_best(all_e); tt=round(time.time()-t0,1)
    log(("done",f"{domain} - {len(all_e)} email(s) in {tt}s",None,None),"done")
    return {"Domain":domain,"Best Email":best or "","Best Tier":tier_short(best) if best else "",
            "All Emails":sort_by_tier(all_e),"Twitter":sorted(all_tw),"LinkedIn":sorted(all_li),
            "Facebook":sorted(all_fb),"Pages Scraped":pd_,"Total Time":tt,
            "Source URL":root_url,"MX":{},"Blocked":blocked}, logs

def rlog(ph): _render_log(ph, st.session_state.log_lines)

# ── UI ────────────────────────────────────────────────────────────────────────
page_header("✦","Scraper","sitemap-first  ·  parallel engine  ·  fallback validation  ·  confidence scoring","scraper")

# top row: URLs + settings
tc1,tc2=st.columns([4,1],gap="large")
with tc1:
    tp,tf=st.tabs(["Paste URLs","Upload CSV / TXT"])
    urls_to_scrape=[]
    with tp:
        raw=st.text_area("u",label_visibility="collapsed",placeholder="https://magazine.com\nhttps://blog.io\nnewspaper.org",height=95,key="url_input")
        for line in raw.splitlines():
            line=line.strip()
            if not line: continue
            if not line.startswith("http"): line="https://"+line
            urls_to_scrape.append(line)
    with tf:
        up=st.file_uploader("f",type=["csv","txt"],label_visibility="collapsed")
        if up:
            rb=up.read()
            if up.name.endswith(".csv"):
                try:
                    df_up=pd.read_csv(io.BytesIO(rb)); cu=list(df_up.columns)
                    hints=["url","link","website","site","domain","href"]
                    dc=next((c for c in cu if any(h in c.lower() for h in hints)),cu[0])
                    cs=st.selectbox("Column",cu,index=cu.index(dc),key="csv_col")
                    for u in df_up[cs].dropna().astype(str):
                        u=u.strip()
                        if not u.startswith("http"): u="https://"+u
                        urls_to_scrape.append(u)
                    st.caption(f"OK {len(urls_to_scrape)} URLs")
                except Exception as ex: st.error(str(ex))
            else:
                for line in rb.decode("utf-8","ignore").splitlines():
                    line=line.strip()
                    if line:
                        if not line.startswith("http"): line="https://"+line
                        urls_to_scrape.append(line)
                st.caption(f"OK {len(urls_to_scrape)} URLs")
    if urls_to_scrape:
        pills="".join(f'<span class="mh-pill">{u.replace("https://","")[:22]}</span>' for u in urls_to_scrape[:6])
        if len(urls_to_scrape)>6: pills+=f'<span class="mh-pill">+{len(urls_to_scrape)-6}</span>'
        st.markdown(f'<div class="mh-pills">{pills}</div>',unsafe_allow_html=True)
with tc2:
    with st.expander("Settings",expanded=True):
        st.session_state.parallel=st.toggle("4× Parallel",value=st.session_state.parallel,key="t_par")
        st.session_state.skip_t1=st.toggle("Stop at Tier 1",value=st.session_state.skip_t1,key="t_sk")
        st.session_state.respect_robots=st.toggle("Robots.txt",value=st.session_state.respect_robots,key="t_rb")
        st.session_state.auto_validate=st.toggle("Auto-validate",value=st.session_state.auto_validate,key="t_av")
        st.session_state.scrape_fb=st.toggle("Scrape FB",value=st.session_state.scrape_fb,key="t_fb")

# mode selector
st.markdown('<span class="mh-sec" style="margin-top:6px;display:block">Crawl Mode</span>',unsafe_allow_html=True)
mc=st.columns(5,gap="small")
for col,(name,mi) in zip(mc,MODES.items()):
    with col:
        is_on=st.session_state.scraper_mode==name
        bc=mi["color"]; bg=f"{bc}12" if is_on else "#fff"; bord=f"2px solid {bc}" if is_on else "2px solid #e8e8e4"
        st.markdown(f'<div style="padding:11px 12px;border-radius:10px;background:{bg};border:{bord};margin-bottom:3px">'
                    f'<div style="font-size:19px;margin-bottom:3px">{mi["icon"]}</div>'
                    f'<div style="font-size:12px;font-weight:700;color:{"#111"}">{name}</div>'
                    f'<div style="font-size:9.5px;color:#aaa;margin-top:2px;line-height:1.4">{mi["tag"]}</div></div>',unsafe_allow_html=True)
        if st.button("✓" if is_on else "Select",key=f"m_{name}",type="primary" if is_on else "secondary",use_container_width=True):
            st.session_state.scraper_mode=name; st.rerun()

mi=MODES[st.session_state.scraper_mode]; mode_key=st.session_state.scraper_mode
st.markdown(f'<div style="font-size:11px;color:#aaa;margin:0 0 6px"><strong style="color:{mi["color"]}">{mode_key}:</strong> {mi["tip"]}</div>',unsafe_allow_html=True)
cfg={k:v for k,v in mi.items() if k not in("icon","color","tag","tip")}
if mode_key=="Medium":
    sc1,sc2=st.columns(2)
    with sc1: cfg["max_depth"]=st.slider("Depth",1,6,3,key="sl_d")
    with sc2: cfg["max_pages"]=st.slider("Pages/site",10,200,50,key="sl_p")
elif mode_key=="Extreme":
    cfg["max_pages"]=st.slider("Pages/site",50,500,300,key="sl_px")

# scan controls
scan_state=st.session_state.scan_state
sc1,sc2,sc3,sc4=st.columns([3,1,1,1],gap="small")
with sc1:
    st.markdown('<div class="mh-start">',unsafe_allow_html=True)
    if scan_state=="idle":
        do_start=st.button("▶  Start Scan",type="primary",use_container_width=True,disabled=not urls_to_scrape,key="btn_s")
    elif scan_state=="running":
        do_start=False
        if st.button("⏸  Pause",type="primary",use_container_width=True,key="btn_p"): st.session_state.scan_state="paused"; st.rerun()
    elif scan_state=="paused":
        do_start=False
        if st.button("▶  Resume",type="primary",use_container_width=True,key="btn_r"): st.session_state.scan_state="running"; st.rerun()
    else:
        do_start=st.button("▶  New Scan",type="primary",use_container_width=True,disabled=not urls_to_scrape,key="btn_ns")
    st.markdown('</div>',unsafe_allow_html=True)
with sc2:
    if scan_state in("running","paused"):
        if st.button("■  Stop",type="secondary",use_container_width=True,key="btn_st"): st.session_state.scan_state="done"; st.rerun()
with sc3:
    if st.button("🗑 Clear",type="secondary",use_container_width=True,key="btn_cl"):
        for k in("scraper_results","scan_queue","log_lines"): st.session_state[k]={} if k=="scraper_results" else []
        st.session_state.scan_state="idle"; st.session_state.scan_idx=0; st.rerun()
with sc4:
    if st.session_state.get("scraper_results") and scan_state!="running":
        xlsx=build_xlsx_scraper(st.session_state.scraper_results)
        st.download_button("⬇ .xlsx",xlsx,f"scraper_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="dl_xlsx",use_container_width=True)

do_start=do_start if "do_start" in dir() else False
if do_start and urls_to_scrape:
    new_urls=[u for u in urls_to_scrape if urlparse(u).netloc not in st.session_state.scraper_domains]
    if new_urls:
        if scan_state=="done": st.session_state.scraper_results={}
        st.session_state.update(scan_queue=new_urls,scan_idx=0,scan_state="running",log_lines=[])
        st.rerun()

# progress + log
if scan_state in("running","paused") and st.session_state.scan_queue:
    idx=st.session_state.scan_idx; total=len(st.session_state.scan_queue)
    pct=round(idx/total*100,1) if total else 0; done=len(st.session_state.scraper_results)
    paused_=scan_state=="paused"; bc="#fb923c" if paused_ else "#111"; dc="#fb923c" if paused_ else "#4ade80"
    lbl="Paused" if paused_ else "Scanning"; par_n=" · 4× parallel" if st.session_state.get("parallel") else ""
    st.markdown(f'<div class="mh-scanbar"><div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{dc};margin-right:6px;animation:mhpulse 1.5s infinite"></span></div>'
                f'<div style="flex:1"><div style="font-size:13px;font-weight:700;color:#111">{lbl}{par_n}</div>'
                f'<div style="font-size:11px;color:#aaa">{done} done · {total-done} left</div>'
                f'<div style="height:3px;background:#f0f0ee;border-radius:99px;overflow:hidden;margin-top:5px"><div style="height:100%;width:{pct}%;background:{bc};border-radius:99px;transition:width .4s"></div></div></div>'
                f'<div style="font-size:20px;font-weight:800;color:#111">{pct}%</div></div>',unsafe_allow_html=True)
log_ph=st.empty()
if st.session_state.log_lines: rlog(log_ph)

# results
results=st.session_state.get("scraper_results",{})
if not results:
    if scan_state=="idle":
        st.markdown(f'<div style="text-align:center;padding:50px 0;color:#bbb">'
                    f'<div style="font-size:40px;opacity:.1;margin-bottom:12px">✦</div>'
                    f'<div style="font-size:17px;font-weight:800;color:#111;margin-bottom:8px">Ready to scrape</div>'
                    f'<div style="font-size:12px;line-height:1.9;max-width:360px;margin:0 auto">'
                    f'Paste URLs above and hit <strong>Start Scan</strong><br>'
                    f'<strong style="color:{mi["color"]}">{mode_key}:</strong> {mi["tip"]}</div></div>',unsafe_allow_html=True)
else:
    tot_d=len(results); tot_e=sum(len(r.get("All Emails",[])) for r in results.values())
    t1_c=sum(1 for r in results.values() if r.get("Best Tier","").startswith("Tier 1"))
    val_ok=sum(1 for r in results.values() if (r.get("Validation",{}) or {}).get("status")=="Deliverable")
    fallbk=sum(1 for r in results.values() if r.get("WasFallback"))
    no_e=sum(1 for r in results.values() if not r.get("Best Email"))
    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Sites",tot_d); m2.metric("Emails",tot_e); m3.metric("Tier 1",t1_c)
    m4.metric("Validated",val_ok); m5.metric("Fallback",fallbk); m6.metric("No Email",no_e)

    if scan_state=="done":
        to_val=[d for d,r in results.items() if r.get("All Emails") and not r.get("Validation")]
        if to_val:
            v1,v2=st.columns([5,1.5])
            with v1: st.markdown(f'<div class="mh-info">{len(to_val)} domain(s) ready — uses fallback chain automatically</div>',unsafe_allow_html=True)
            with v2:
                if st.button("Validate All",key="val_all",type="primary",use_container_width=True): st.session_state["run_validate_all"]=True; st.rerun()

    sf1,sf2=st.columns([2,4],gap="small")
    with sf1: search=st.text_input("s",placeholder="Search...",label_visibility="collapsed",key="srch")
    with sf2:
        FLT=[("All","All"),("T1","T1"),("T2","T2"),("T3","T3"),("None","None"),("OK","val_ok"),("Risk","val_risky"),("Fail","val_bad")]
        st.markdown('<div class="mh-flt">',unsafe_allow_html=True)
        fc=st.columns(len(FLT))
        for col,(lbl,val) in zip(fc,FLT):
            with col:
                if st.button(lbl,key=f"flt_{val}",type="primary" if st.session_state.scraper_filter==val else "secondary",use_container_width=True):
                    st.session_state.scraper_filter=val; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

    seen=st.session_state.seen_emails; rows=[]
    for domain,r in results.items():
        all_e=r.get("All Emails",[]); best=r.get("Best Email","")
        vbest=r.get("ValidatedBestEmail","") or best; val=r.get("Validation",{}) or {}
        val_st=val.get("status",""); conf=r.get("Confidence"); fb_=r.get("WasFallback",False)
        is_dup=best in seen and best and scan_state!="running"
        ed=(vbest or "—")+(" ↻" if fb_ else "")+(" ★" if is_dup else "")
        rows.append({"Domain":domain,"Email":ed,"Tier":r.get("Best Tier","") or "—","Score":conf if conf is not None else "",
            "Val":val_icon(val_st) if val_st else "—","Reason":val.get("reason","—") if val else "—",
            "SPF":("ok" if val.get("spf") else "no") if val else "—",
            "DMARC":("ok" if val.get("dmarc") else "no") if val else "—",
            "CA":("yes" if val.get("catch_all") else "—") if val else "—",
            "+":f'+{len(all_e)-1}' if len(all_e)>1 else "","Pages":r.get("Pages Scraped",0),"s":r.get("Total Time","")})
    df=pd.DataFrame(rows)
    if search: m=(df["Domain"].str.contains(search,case=False,na=False)|df["Email"].str.contains(search,case=False,na=False)); df=df[m]
    flt=st.session_state.scraper_filter
    if flt=="T1": df=df[df["Tier"].str.startswith("Tier 1",na=False)]
    elif flt=="T2": df=df[df["Tier"].str.startswith("Tier 2",na=False)]
    elif flt=="T3": df=df[df["Tier"].str.startswith("Tier 3",na=False)]
    elif flt=="None": df=df[df["Email"]=="—"]
    elif flt=="val_ok": df=df[df["Val"]=="✅"]
    elif flt=="val_risky": df=df[df["Val"]=="⚠️"]
    elif flt=="val_bad": df=df[df["Val"]=="❌"]
    st.caption(f'**{len(df)}** of {tot_d}  ·  ↻ fallback  ·  ★ seen before')
    st.dataframe(df,use_container_width=True,hide_index=True,height=min(540,44+max(len(df),1)*36),
        column_config={"Domain":st.column_config.TextColumn("Domain",width=150),"Email":st.column_config.TextColumn("Email",width=205),
            "Tier":st.column_config.TextColumn("Tier",width=65),"Score":st.column_config.NumberColumn("Score",width=52),
            "Val":st.column_config.TextColumn("Val",width=42),"Reason":st.column_config.TextColumn("Reason",width=165),
            "SPF":st.column_config.TextColumn("SPF",width=38),"DMARC":st.column_config.TextColumn("DMARC",width=48),
            "CA":st.column_config.TextColumn("CA",width=40),"+":st.column_config.TextColumn("+",width=36),
            "Pages":st.column_config.NumberColumn("Pages",width=50),"s":st.column_config.NumberColumn("s",width=44)})

    pa1,pa2,pa3,pa4,pa5=st.columns([3,1,1,1,1])
    with pa1: sel=st.selectbox("d",list(results.keys()),label_visibility="collapsed",key="sel_d")
    r_sel=results.get(sel,{}); all_e_s=r_sel.get("All Emails",[]); best_s=r_sel.get("Best Email","")
    with pa2:
        if st.button("Validate",key="v1",type="primary",disabled=not all_e_s,use_container_width=True): st.session_state[f"vrun_{sel}"]=True; st.rerun()
    with pa3:
        if st.button("Save",key="btn_sv",type="secondary",use_container_width=True):
            ts=datetime.now().strftime("%b %d %H:%M")
            for r in results.values():
                for e in r.get("All Emails",[]): st.session_state.seen_emails.add(e)
            st.session_state.scraper_sessions.append({"name":f"Scan {len(st.session_state.scraper_sessions)+1} - {ts}","results":dict(results)}); st.rerun()
    with pa4:
        if all_e_s: st.download_button("Emails","\n".join(all_e_s),f"{sel}_emails.txt",key="cp1",use_container_width=True)
    with pa5:
        if all_e_s: st.button("MX",key="mx1",type="secondary",use_container_width=True)

    val_d=r_sel.get("Validation",{}) or {}
    if val_d:
        vbest=r_sel.get("ValidatedBestEmail","") or best_s; icon_=val_icon(val_d.get("status",""))
        conf=r_sel.get("Confidence"); cc=conf_color(conf); fb_fl="↻ fallback" if r_sel.get("WasFallback") else ""
        sc_h=f'<span class="mh-vtag" style="color:{cc};font-weight:800">{conf}/100</span>' if conf is not None else ""
        st.markdown(f'<div class="mh-val-row"><span class="mh-val-em">{icon_} {vbest}</span>'
                    + (f'<span class="mh-vtag">{fb_fl}</span>' if fb_fl else "")
                    + sc_h + f'<span class="mh-vtag">{val_d.get("reason","")}</span>'
                    + (f'<span class="mh-vtag">SPF ok</span>' if val_d.get("spf") else f'<span class="mh-vtag">no SPF</span>')
                    + (f'<span class="mh-vtag">DMARC ok</span>' if val_d.get("dmarc") else "")
                    + '</div>',unsafe_allow_html=True)

    if sel and st.session_state.get(f"vrun_{sel}"):
        st.session_state[f"vrun_{sel}"]=False
        with st.spinner(f"Validating {sel}..."):
            chosen_e,vres,was_fb,_=validate_with_fallback(all_e_s,best_s)
        if vres:
            cf_=confidence_score(chosen_e,vres)
            st.session_state.scraper_results[sel].update({"Validation":vres,"ValidatedBestEmail":chosen_e,"WasFallback":was_fb,"Confidence":cf_})
        st.rerun()
    if st.session_state.get("run_validate_all"):
        st.session_state["run_validate_all"]=False
        todo=[(d,r) for d,r in results.items() if r.get("All Emails") and not r.get("Validation")]
        if todo:
            vph=st.empty()
            for i,(dom,r) in enumerate(todo):
                vph.markdown(f'<div class="mh-log"><div class="ll-site">[ {dom} ]</div><div class="ll-info">  . {r.get("Best Email","")} ({i+1}/{len(todo)})</div></div>',unsafe_allow_html=True)
                ce,vr,wf,_=validate_with_fallback(r.get("All Emails",[]),r.get("Best Email",""))
                if vr:
                    cf_=confidence_score(ce,vr)
                    st.session_state.scraper_results[dom].update({"Validation":vr,"ValidatedBestEmail":ce,"WasFallback":wf,"Confidence":cf_})
            vph.empty(); st.rerun()

    if st.session_state.scraper_sessions:
        with st.expander(f"Saved sessions ({len(st.session_state.scraper_sessions)})"):
            for i,sess in enumerate(st.session_state.scraper_sessions):
                nd=len(sess["results"]); ne=sum(len(r.get("All Emails",[])) for r in sess["results"].values())
                a,b,c=st.columns([3,1,1])
                with a: st.caption(f"**{sess['name']}** · {nd} sites · {ne} emails")
                with b:
                    if st.button("Load",key=f"ld_{i}",use_container_width=True): st.session_state.scraper_results=sess["results"]; st.session_state.scan_state="done"; st.rerun()
                with c:
                    if st.button("Del",key=f"dl_{i}",use_container_width=True): st.session_state.scraper_sessions.pop(i); st.rerun()

if st.session_state.scan_state=="running":
    q=st.session_state.scan_queue; idx=st.session_state.scan_idx; total=len(q)
    if idx>=total:
        st.session_state.scan_state="done"; st.rerun()
    else:
        url=q[idx]
        if not url.startswith("http"): url="https://"+url
        # snapshot config — pure values only
        cfg_snap=dict(cfg)
        skip_t1_=bool(st.session_state.skip_t1)
        respect_=bool(st.session_state.respect_robots)
        sfb_=bool(st.session_state.scrape_fb)
        # add site marker to log
        domain=urlparse(url).netloc
        st.session_state.log_lines.append((("site",domain,None,None),"site"))
        rlog(log_ph)
        # scrape — sequential, no threading, errors surface properly
        try:
            row,logs=_scrape_site(url,cfg_snap,skip_t1_,respect_,sfb_)
            st.session_state.scraper_results[row["Domain"]]=row
            st.session_state.scraper_domains.add(row["Domain"])
            st.session_state.log_lines.extend(logs)
        except Exception as e:
            err=str(e)[:80]
            st.session_state.log_lines.append((("warn",f"failed: {err}",None,None),"warn"))
            # store a placeholder so domain shows as attempted
            st.session_state.scraper_results[domain]={"Domain":domain,"Best Email":"",
                "Best Tier":"","All Emails":[],"Twitter":[],"LinkedIn":[],"Facebook":[],
                "Pages Scraped":0,"Total Time":0,"Source URL":url,"MX":{},"Blocked":False}
            st.session_state.scraper_domains.add(domain)
        st.session_state.scan_idx=idx+1
        if st.session_state.scan_idx>=total:
            st.session_state.scan_state="done"
            if st.session_state.get("auto_validate"): st.session_state["run_validate_all"]=True
        st.rerun()
