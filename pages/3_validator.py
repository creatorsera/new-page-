"""
pages/3_validator.py — Email Validator
Clean bright spreadsheet UI. Source selector: paste / CSV / scraper data / FB data.
Fallback chain: if best email fails, tries others in tier order automatically.
"""
import streamlit as st
import pandas as pd, io, time
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (is_valid_email, tier_key, tier_short, sort_by_tier, pick_best,
    confidence_score, conf_color, val_icon, validate_email_full, validate_with_fallback,
    build_xlsx_validator)
from theme import inject_css, page_header

inject_css("validator")
st.markdown("""<style>
.mh-start .stButton > button { height:44px !important; font-size:14px !important; font-weight:700 !important; border-radius:10px !important; }
.val-prog { height:4px; background:#f0f0ee; border-radius:99px; overflow:hidden; margin:5px 0; }
.val-prog-fill { height:100%; border-radius:99px; background:#16a34a; transition:width .35s; }
</style>""", unsafe_allow_html=True)

for k,v in {"val_results":[],"val_source":"paste","val_running":False,"val_queue":[],"val_idx":0}.items():
    if k not in st.session_state: st.session_state[k]=v

def collect_from_scraper():
    items=[]
    for domain,r in st.session_state.get("scraper_results",{}).items():
        best=r.get("Best Email",""); all_e=r.get("All Emails",[])
        if best or all_e:
            items.append({"email":best,"domain":domain,"all_emails":all_e,"source":"Scraper",
                          "val":None,"was_fallback":False,"original_email":best,"confidence":None})
    return items

def collect_from_fb():
    items=[]
    for handle,r in st.session_state.get("fb_results",{}).items():
        emails=r.get("emails",[])
        if emails:
            best=pick_best(emails) or ""
            items.append({"email":best,"domain":handle,"all_emails":emails,"source":"Facebook",
                          "val":None,"was_fallback":False,"original_email":best,"confidence":None})
    return items

def collect_from_paste(raw):
    items=[]
    for line in raw.splitlines():
        e=line.strip()
        if is_valid_email(e):
            items.append({"email":e,"domain":e.split("@")[-1],"all_emails":[e],"source":"Manual",
                          "val":None,"was_fallback":False,"original_email":e,"confidence":None})
    return items

def collect_from_csv(df,col):
    items=[]
    for e in df[col].dropna().astype(str):
        e=e.strip()
        if is_valid_email(e):
            items.append({"email":e,"domain":e.split("@")[-1],"all_emails":[e],"source":"CSV",
                          "val":None,"was_fallback":False,"original_email":e,"confidence":None})
    return items

# header
page_header("✅","Validator",
    "SMTP validation  ·  fallback chain  ·  confidence scoring  ·  SPF  ·  DMARC  ·  catch-all",
    "validator")

hc1,hc2=st.columns([4,1])
with hc2:
    vr=st.session_state.get("val_results",[])
    if vr:
        xlsx=build_xlsx_validator(vr)
        st.download_button("⬇ .xlsx",xlsx,f"validated_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="val_xlsx")

# source selector
st.markdown('<span class="mh-sec">Source</span>',unsafe_allow_html=True)
n_sc=len([r for r in st.session_state.get("scraper_results",{}).values() if r.get("Best Email") or r.get("All Emails")])
n_fb=len([r for r in st.session_state.get("fb_results",{}).values() if r.get("emails")])

SRCS=[("paste","✎ Paste emails",None),("csv","⬆ Upload CSV",None),
      ("scraper",f"🔍 Scraper ({n_sc})",n_sc),("fb",f"📘 Facebook ({n_fb})",n_fb)]
sc=st.columns(4)
for col,(key,label,cnt) in zip(sc,SRCS):
    with col:
        is_a=st.session_state.val_source==key
        if st.button(label,key=f"src_{key}",type="primary" if is_a else "secondary",
                     use_container_width=True,
                     disabled=(key=="scraper" and n_sc==0) or (key=="fb" and n_fb==0)):
            st.session_state.val_source=key; st.session_state.val_results=[]; st.rerun()

source=st.session_state.val_source; items_to_validate=[]
if source=="paste":
    paste_text=st.text_area("pe",label_visibility="collapsed",
        placeholder="editor@techcrunch.com\npress@forbes.com\ninfo@wired.com",height=120,key="paste_ta")
    items_to_validate=collect_from_paste(paste_text)
    if items_to_validate: st.caption(f"{len(items_to_validate)} valid email(s)")
elif source=="csv":
    up=st.file_uploader("Upload CSV",type=["csv"],key="val_csv")
    if up:
        try:
            df_up=pd.read_csv(io.BytesIO(up.read())); cols=list(df_up.columns)
            hints=["email","mail","address","contact"]
            dc=next((c for c in cols if any(h in c.lower() for h in hints)),cols[0])
            cs=st.selectbox("Email column",cols,index=cols.index(dc),key="val_csv_col")
            items_to_validate=collect_from_csv(df_up,cs)
            st.caption(f"{len(items_to_validate)} valid email(s) in '{cs}'")
        except Exception as e: st.error(str(e))
elif source=="scraper":
    items_to_validate=collect_from_scraper()
    if items_to_validate: st.markdown(f'<div class="mh-info">{len(items_to_validate)} domains from scraper. Fallback chain active — if best email fails, tries next in tier order.</div>',unsafe_allow_html=True)
    else: st.markdown('<div class="mh-warn">No scraper results. Run Scraper first.</div>',unsafe_allow_html=True)
elif source=="fb":
    items_to_validate=collect_from_fb()
    if items_to_validate: st.markdown(f'<div class="mh-info">{len(items_to_validate)} Facebook pages with emails loaded.</div>',unsafe_allow_html=True)
    else: st.markdown('<div class="mh-warn">No Facebook results. Run Facebook Extractor first.</div>',unsafe_allow_html=True)

# controls
vc1,vc2,vc3=st.columns([3,1,2])
with vc1:
    running=st.session_state.get("val_running",False)
    st.markdown('<div class="mh-start">',unsafe_allow_html=True)
    if not running:
        lbl=f"Validate {len(items_to_validate)} email(s)" if items_to_validate else "Validate"
        if st.button(lbl,type="primary",use_container_width=True,disabled=not items_to_validate,key="val_start"):
            st.session_state.val_results=[{**item,"val":None} for item in items_to_validate]
            st.session_state.val_idx=0; st.session_state.val_running=True; st.rerun()
    else:
        if st.button("Stop",type="secondary",use_container_width=True,key="val_stop"): st.session_state.val_running=False; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
with vc2:
    if st.session_state.val_results:
        if st.button("Clear",type="secondary",use_container_width=True,key="val_clear"): st.session_state.val_results=[]; st.rerun()
with vc3:
    st.markdown('<div style="font-size:10.5px;color:#aaa;padding-top:12px">Fallback: best → next tier if not deliverable</div>',unsafe_allow_html=True)

# live progress
vr=st.session_state.get("val_results",[])
if vr:
    nv=sum(1 for r in vr if r.get("val")); nt=len(vr)
    nd=sum(1 for r in vr if (r.get("val",{}) or {}).get("status")=="Deliverable")
    nri=sum(1 for r in vr if (r.get("val",{}) or {}).get("status")=="Risky")
    nb=sum(1 for r in vr if (r.get("val",{}) or {}).get("status")=="Not Deliverable")
    nfb=sum(1 for r in vr if r.get("was_fallback"))
    if running:
        pct=round(nv/nt*100,1) if nt else 0
        st.markdown(f'<div style="font-size:11px;color:#aaa;margin-bottom:2px">Checking {nv}/{nt}...</div>'
                    f'<div class="val-prog"><div class="val-prog-fill" style="width:{pct}%"></div></div>',unsafe_allow_html=True)
    if nv>0:
        m1,m2,m3,m4,m5=st.columns(5)
        m1.metric("Checked",nv); m2.metric("Deliverable",nd); m3.metric("Risky",nri); m4.metric("Failed",nb); m5.metric("Fallback ↻",nfb)

    # table
    search=st.text_input("vs",placeholder="Search...",label_visibility="collapsed",key="val_s")
    rows=[]
    for r in vr:
        val_=r.get("val") or {}; status=val_.get("status",""); email=r.get("email","")
        was_fb=r.get("was_fallback",False); orig=r.get("original_email",""); conf=r.get("confidence"); src=r.get("source","")
        em_d=email+(" ↻" if was_fb else ""); icon={"Deliverable":"✅","Risky":"⚠️","Not Deliverable":"❌"}.get(status,"⏳")
        orig_n=f"was: {orig}" if was_fb and orig!=email else ""
        rows.append({"#":len(rows)+1,"Status":f"{icon} {status or 'pending'}","Email":em_d,
            "Domain":r.get("domain",""),"Source":src,"Tier":tier_short(email) if email else "—",
            "Score":conf if conf is not None else "—","Reason":val_.get("reason","—") if val_ else "—",
            "SPF":("ok" if val_.get("spf") else "no") if val_ else "—",
            "DMARC":("ok" if val_.get("dmarc") else "no") if val_ else "—",
            "CA":("yes" if val_.get("catch_all") else "—") if val_ else "—",
            "Fallback":"↻ "+orig_n if was_fb else "—"})
    df=pd.DataFrame(rows)
    if search: m=(df["Email"].str.contains(search,case=False,na=False)|df["Domain"].str.contains(search,case=False,na=False)); df=df[m]
    st.caption(f'**{len(df)}** of {len(vr)}  ·  ↻ = fallback email (original not deliverable)')
    st.dataframe(df,use_container_width=True,hide_index=True,height=min(580,44+max(len(df),1)*36),
        column_config={"#":st.column_config.NumberColumn("#",width=40),"Status":st.column_config.TextColumn("Status",width=160),
            "Email":st.column_config.TextColumn("Email",width=210),"Domain":st.column_config.TextColumn("Domain",width=145),
            "Source":st.column_config.TextColumn("Source",width=75),"Tier":st.column_config.TextColumn("Tier",width=65),
            "Score":st.column_config.NumberColumn("Score",width=52),"Reason":st.column_config.TextColumn("Reason",width=165),
            "SPF":st.column_config.TextColumn("SPF",width=40),"DMARC":st.column_config.TextColumn("DMARC",width=50),
            "CA":st.column_config.TextColumn("CA",width=40),"Fallback":st.column_config.TextColumn("Fallback",width=155)})

# engine
if st.session_state.get("val_running"):
    vr=st.session_state.val_results; idx=st.session_state.val_idx; total=len(vr)
    if idx>=total: st.session_state.val_running=False; st.rerun()
    else:
        row=vr[idx]; email=row.get("email",""); all_e=row.get("all_emails",[email]) or [email]; orig=row.get("original_email",email)
        if email and is_valid_email(email):
            ce,vr_,wf,_=validate_with_fallback(all_e,email)
            if vr_:
                cf_=confidence_score(ce,vr_)
                st.session_state.val_results[idx].update({"email":ce,"val":vr_,"was_fallback":wf,"original_email":orig if wf else email,"confidence":cf_})
        else:
            st.session_state.val_results[idx]["val"]={"status":"Not Deliverable","reason":"Invalid format","spf":False,"dmarc":False,"mx":False,"catch_all":False}
        st.session_state.val_idx=idx+1
        if st.session_state.val_idx>=total: st.session_state.val_running=False
        st.rerun()
