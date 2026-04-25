from __future__ import annotations


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Game Mechanics Monitor</title>
  <style>
    :root{--bg:#f6f7f9;--panel:#fff;--soft:#f0f3f6;--text:#17202a;--muted:#647282;--line:#d9e0e7;--accent:#176b87;--good:#1b7f4d;--bad:#b42318;--shadow:0 12px 30px rgba(23,32,42,.08)}
    *{box-sizing:border-box} body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 28px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
    h1{margin:0;font-size:20px;font-weight:750;letter-spacing:0}.sub{color:var(--muted);margin-top:3px;font-size:13px}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    input,select,button{border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--text);min-height:36px;padding:0 11px;font:inherit} button{background:var(--accent);color:#fff;border-color:var(--accent);cursor:pointer;font-weight:650}
    main{display:grid;grid-template-columns:minmax(360px,.9fr) minmax(420px,1.1fr);gap:18px;padding:18px 28px 28px}.metrics{grid-column:1/-1;display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:12px}
    .metric,.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow)}.metric{padding:14px 15px}.metric .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.metric .value{margin-top:4px;font-size:24px;font-weight:750}
    .panel{min-height:640px;overflow:hidden}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 15px;border-bottom:1px solid var(--line);background:var(--soft)}.panel-title{font-weight:750}.list{max-height:590px;overflow:auto}
    .item{width:100%;display:block;padding:14px 15px;border:0;border-bottom:1px solid var(--line);background:#fff;color:var(--text);text-align:left;cursor:pointer}.item:hover,.item.active{background:#edf7fa}.item-title{font-weight:700;overflow-wrap:anywhere}.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.meta{color:var(--muted);font-size:12px;margin-top:7px}
    .pill{display:inline-flex;align-items:center;min-height:22px;padding:0 7px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);font-size:12px;font-weight:650}.pill.good{color:var(--good);border-color:rgba(27,127,77,.3);background:#eef8f2}.pill.bad{color:var(--bad);border-color:rgba(180,35,24,.3);background:#fff0ee}.pill.accent{color:var(--accent);border-color:rgba(23,107,135,.3);background:#edf7fa}
    .detail{padding:18px;max-height:590px;overflow:auto}.detail h2{margin:0 0 10px;font-size:22px;line-height:1.2;letter-spacing:0}.detail a{color:var(--accent);overflow-wrap:anywhere;font-weight:650}.section{margin-top:20px;padding-top:16px;border-top:1px solid var(--line)}.section h3{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.kv{padding:10px;background:var(--soft);border:1px solid var(--line);border-radius:6px}.kv span{display:block;color:var(--muted);font-size:12px;margin-bottom:3px}.kv b{font-size:15px}.snippet{white-space:pre-wrap;background:#fbfcfd;border:1px solid var(--line);border-radius:6px;padding:12px;color:#334252;max-height:220px;overflow:auto}.empty{padding:28px;color:var(--muted)}
    @media(max-width:920px){header{align-items:flex-start;flex-direction:column;padding:16px}main{grid-template-columns:1fr;padding:14px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{min-height:auto}.list,.detail{max-height:none}}
  </style>
</head>
<body>
  <header><div><h1>Game Mechanics Monitor</h1><div class="sub" id="statusLine">Loading dashboard...</div></div><div class="toolbar"><input id="search" type="search" placeholder="Search title, source, URL"><select id="relevance"><option value="all">All findings</option><option value="relevant">Feedback: relevant</option><option value="miss">Feedback: miss</option></select><button id="refresh" type="button">Refresh</button></div></header>
  <main>
    <section class="metrics"><div class="metric"><div class="label">Documents</div><div class="value" id="mDocs">0</div></div><div class="metric"><div class="label">Relevant</div><div class="value" id="mRelevant">0</div></div><div class="metric"><div class="label">Sent</div><div class="value" id="mSent">0</div></div><div class="metric"><div class="label">Feedback</div><div class="value" id="mFeedback">0</div></div><div class="metric"><div class="label">Sources</div><div class="value" id="mSources">0</div></div></section>
    <section class="panel"><div class="panel-head"><div class="panel-title">Findings</div><span class="pill" id="resultCount">0 rows</span></div><div class="list" id="list"></div></section>
    <section class="panel"><div class="panel-head"><div class="panel-title">Analysis</div><span class="pill accent" id="selectedId">No selection</span></div><div class="detail" id="detail"><div class="empty">Select a finding to inspect score breakdown, feedback, source, and text.</div></div></section>
  </main>
  <script>
    const state={rows:[],selected:null};const $=(id)=>document.getElementById(id);const fmt=(v)=>v===null||v===undefined||v===""?"n/a":String(v);
    function esc(v){return fmt(v).replace(/[&<>"']/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
    function pill(row){return `<span class="pill ${row.is_relevant?"good":"bad"}">score ${Number(row.score||0).toFixed(2)}</span>`}
    function fb(row){if(!row.feedback_value)return `<span class="pill">no feedback</span>`;return `<span class="pill ${row.feedback_value==="relevant"?"good":"bad"}">${esc(row.feedback_value)}</span>`}
    function filtered(){const q=$("search").value.trim().toLowerCase(), r=$("relevance").value;return state.rows.filter(row=>{const hay=`${row.title} ${row.source} ${row.url}`.toLowerCase();if(q&&!hay.includes(q))return false;if(r==="relevant"&&row.feedback_value!=="relevant")return false;if(r==="miss"&&row.feedback_value!=="miss")return false;return true})}
    function renderList(){const rows=filtered();$("resultCount").textContent=`${rows.length} rows`;if(!rows.length){$("list").innerHTML=`<div class="empty">No findings match the current filters.</div>`;return}$("list").innerHTML=rows.map(row=>`<button class="item ${state.selected&&state.selected.doc_id===row.doc_id?"active":""}" data-id="${row.doc_id}"><div class="row">${pill(row)}${fb(row)}<span class="pill">${esc(row.source)}</span></div><div class="item-title">${esc(row.title)}</div><div class="meta">ID ${row.doc_id} · ${esc(row.scored_at)}</div></button>`).join("");document.querySelectorAll(".item").forEach(el=>el.addEventListener("click",()=>{state.selected=state.rows.find(row=>String(row.doc_id)===el.dataset.id);renderList();renderDetail()}))}
    function renderDetail(){const row=state.selected;if(!row)return;$("selectedId").textContent=`ID ${row.doc_id}`;const breakdown=Object.entries(row.breakdown||{}).map(([k,v])=>`<div class="kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("");$("detail").innerHTML=`<h2>${esc(row.title)}</h2><div class="row">${pill(row)}${fb(row)}<span class="pill">${row.is_relevant?"relevant":"not relevant"}</span><span class="pill">${esc(row.source)}</span></div><p><a href="${esc(row.url)}" target="_blank" rel="noreferrer">${esc(row.url)}</a></p><div class="section"><h3>Score Breakdown</h3><div class="grid">${breakdown||`<div class="empty">No score breakdown.</div>`}</div></div><div class="section"><h3>Feedback</h3><div class="grid"><div class="kv"><span>value</span><b>${esc(row.feedback_value)}</b></div><div class="kv"><span>created</span><b>${esc(row.feedback_created_at)}</b></div></div>${row.feedback_note?`<p class="snippet">${esc(row.feedback_note)}</p>`:""}</div><div class="section"><h3>Raw Text</h3><div class="snippet">${esc(row.content||"No text captured.")}</div></div>`}
    function renderMetrics(summary,runtime){$("mDocs").textContent=summary.documents||0;$("mRelevant").textContent=summary.relevant||0;$("mSent").textContent=summary.sent||0;$("mFeedback").textContent=summary.feedback||0;$("mSources").textContent=summary.sources||0;$("statusLine").textContent=`Pipeline: ${runtime.pipeline_status||"n/a"} · last finish: ${runtime.last_finished_at||"n/a"}`}
    async function load(){const res=await fetch("/api/dashboard",{cache:"no-store"});if(!res.ok)throw new Error(`HTTP ${res.status}`);const data=await res.json();state.rows=data.findings||[];state.selected=state.rows[0]||null;renderMetrics(data.summary||{},data.runtime||{});renderList();renderDetail()}
    $("refresh").addEventListener("click",()=>load().catch(err=>$("statusLine").textContent=`Failed to load: ${err.message}`));$("search").addEventListener("input",renderList);$("relevance").addEventListener("change",renderList);load().catch(err=>$("statusLine").textContent=`Failed to load: ${err.message}`);
  </script>
</body>
</html>
"""
