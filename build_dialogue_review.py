"""
Build a self-contained HTML review page for the makes_it_a_dialogue synthetic set.
Maya reviews all 18 author-generated transcripts, agrees or overrides each label,
and exports her decisions (download CSV + copy-for-chat summary) back to Claude.

    python build_dialogue_review.py   ->  writes dialogue_review.html
"""
import csv
import json
from pathlib import Path

csv.field_size_limit(10 ** 7)
HERE = Path(__file__).parent

# Full design-intent text per ceo_id, pulled from the TSV Eval Focus column.
FOCUS = {}
for tsv in ["synthetic_makes_it_a_dialogue.tsv",
            "synthetic_makes_it_a_dialogue_negatives.tsv",
            "synthetic_makes_it_a_dialogue_tricky.tsv",
            "synthetic_makes_it_a_dialogue_tricky_negatives.tsv"]:
    for r in csv.DictReader(open(HERE / tsv), delimiter="\t"):
        FOCUS[r["CEO ID"]] = r["Eval Focus"]

# category + short human title per source_row, plus boundary-pair links.
META = {
    "9001": ("clean-pos", "Warehouse — reflective Q up front", None),
    "9002": ("clean-pos", "Retail supervisor — reflective Q mid-session", None),
    "9003": ("clean-pos", "Line cook — two reflective Qs, spaced", None),
    "9004": ("clean-pos", "Front desk — reflective Q after a hard answer", None),
    "9101": ("matched-neg", "Warehouse — same session, reflective Q removed", "9001"),
    "9102": ("matched-neg", "Retail supervisor — reflective Q removed", "9002"),
    "9103": ("matched-neg", "Line cook — reflective Q removed", "9003"),
    "9104": ("matched-neg", "Front desk — reflective Q removed", "9004"),
    "9005": ("tricky-pos", "Buried reflective Q in disfluent STT", "9106"),
    "9006": ("tricky-pos", "One reflective Q amid an otherwise templated coach", "9107"),
    "9007": ("tricky-pos", "Reflective Q in non-canonical phrasing", "9108"),
    "9008": ("tricky-pos", "Reflective Q only at the closing wrap-up", None),
    "9009": ("tricky-pos", "Reflective Q the participant deflects", None),
    "9105": ("tricky-neg", "Comprehension check ('does that make sense?')", None),
    "9106": ("tricky-neg", "Disfluent-STT content follow-up", "9005"),
    "9107": ("tricky-neg", "Reflective Qs present, but zero engagement", "9006"),
    "9108": ("tricky-neg", "Content-add question ('what else could you add?')", "9007"),
    "9109": ("tricky-neg", "Factual clarifier ('was that at your last job?')", None),
}

CAT_LABEL = {
    "clean-pos": "Clean positive",
    "matched-neg": "Matched negative",
    "tricky-pos": "Tricky positive",
    "tricky-neg": "Tricky negative",
}
# review order: clean contrastive pairs first, then the adversarial rows.
ORDER = ["9001", "9101", "9002", "9102", "9003", "9103", "9004", "9104",
         "9005", "9006", "9007", "9008", "9009",
         "9105", "9106", "9107", "9108", "9109"]

cons = {r["source_row"]: r for r in
        csv.DictReader(open(HERE / "judge-suite" / "labels" / "consensus_makes_it_a_dialogue.csv"))}

DATA = []
for sr in ORDER:
    c = cons[sr]
    cat, title, pair = META[sr]
    DATA.append({
        "sr": sr,
        "ceo": c["ceo_id"],
        "cat": cat,
        "catLabel": CAT_LABEL[cat],
        "title": title,
        "intended": c["consensus_label"].upper(),  # PASS / FAIL
        "intent": FOCUS[c["ceo_id"]],
        "pair": pair,
        "transcript": c["excerpt"],
    })

TEMPLATE = r"""<title>makes_it_a_dialogue — label review</title>
<style>
  :root {
    --ground:#f7f8fa; --surface:#ffffff; --surface-2:#eef1f6; --inset:#f4f6fa;
    --ink:#16181d; --ink-2:#565b66; --ink-3:#878d99; --line:#e4e7ec; --line-2:#d8dce3;
    --accent:#4b56c6; --accent-2:#ecedfb; --accent-ink:#ffffff;
    --pass:#1f8a5b; --pass-bg:rgba(31,138,91,.12);
    --fail:#c0453b; --fail-bg:rgba(192,69,59,.12);
    --na:#8a6d1f; --na-bg:rgba(138,109,31,.14);
    --override:#b06a12; --override-bg:rgba(176,106,18,.13);
    --shadow:0 1px 2px rgba(20,24,35,.05), 0 6px 18px rgba(20,24,35,.05);
  }
  @media (prefers-color-scheme:dark){
    :root{
      --ground:#0f1116; --surface:#161922; --surface-2:#1e222d; --inset:#12151d;
      --ink:#eef0f4; --ink-2:#a6acba; --ink-3:#6f7686; --line:#2a2f3b; --line-2:#333a48;
      --accent:#8b93f0; --accent-2:#242840; --accent-ink:#0f1116;
      --pass:#4ec98a; --pass-bg:rgba(78,201,138,.15);
      --fail:#e8776b; --fail-bg:rgba(232,119,107,.15);
      --na:#d6b45f; --na-bg:rgba(214,180,95,.15);
      --override:#e0a24a; --override-bg:rgba(224,162,74,.15);
      --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.28);
    }
  }
  :root[data-theme="light"]{
    --ground:#f7f8fa; --surface:#ffffff; --surface-2:#eef1f6; --inset:#f4f6fa;
    --ink:#16181d; --ink-2:#565b66; --ink-3:#878d99; --line:#e4e7ec; --line-2:#d8dce3;
    --accent:#4b56c6; --accent-2:#ecedfb; --accent-ink:#ffffff;
    --pass:#1f8a5b; --pass-bg:rgba(31,138,91,.12);
    --fail:#c0453b; --fail-bg:rgba(192,69,59,.12);
    --na:#8a6d1f; --na-bg:rgba(138,109,31,.14);
    --override:#b06a12; --override-bg:rgba(176,106,18,.13);
    --shadow:0 1px 2px rgba(20,24,35,.05), 0 6px 18px rgba(20,24,35,.05);
  }
  :root[data-theme="dark"]{
    --ground:#0f1116; --surface:#161922; --surface-2:#1e222d; --inset:#12151d;
    --ink:#eef0f4; --ink-2:#a6acba; --ink-3:#6f7686; --line:#2a2f3b; --line-2:#333a48;
    --accent:#8b93f0; --accent-2:#242840; --accent-ink:#0f1116;
    --pass:#4ec98a; --pass-bg:rgba(78,201,138,.15);
    --fail:#e8776b; --fail-bg:rgba(232,119,107,.15);
    --na:#d6b45f; --na-bg:rgba(214,180,95,.15);
    --override:#e0a24a; --override-bg:rgba(224,162,74,.15);
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.28);
  }
  *{box-sizing:border-box}
  html{-webkit-text-size-adjust:100%}
  body{margin:0}
  .app{
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
    font-family:var(--sans); color:var(--ink); background:var(--ground);
    line-height:1.55; min-height:100vh;
  }
  .wrap{max-width:980px; margin:0 auto; padding:0 20px 96px}

  /* ---- header ---- */
  header.bar{
    position:sticky; top:0; z-index:20; background:color-mix(in srgb,var(--ground) 88%, transparent);
    backdrop-filter:saturate(1.4) blur(10px); border-bottom:1px solid var(--line);
  }
  .bar-in{max-width:980px; margin:0 auto; padding:14px 20px; display:flex; align-items:center; gap:18px; flex-wrap:wrap}
  .brand{display:flex; flex-direction:column; gap:2px; margin-right:auto}
  .eyebrow{font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3)}
  .brand h1{margin:0; font-size:16px; font-weight:650; letter-spacing:-.01em}
  .tally{display:flex; gap:10px; align-items:center; font-family:var(--mono); font-size:12px}
  .stat{display:flex; flex-direction:column; align-items:center; line-height:1.15; padding:4px 10px; border:1px solid var(--line); border-radius:8px; background:var(--surface)}
  .stat b{font-size:15px; font-weight:650; font-variant-numeric:tabular-nums}
  .stat span{font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-3)}
  .stat.ov b{color:var(--override)}
  .btn{font-family:var(--sans); font-size:13px; font-weight:600; border:1px solid var(--line-2); background:var(--surface); color:var(--ink); padding:8px 14px; border-radius:9px; cursor:pointer; transition:.14s}
  .btn:hover{border-color:var(--accent); color:var(--accent)}
  .btn.primary{background:var(--accent); color:var(--accent-ink); border-color:var(--accent)}
  .btn.primary:hover{filter:brightness(1.06); color:var(--accent-ink)}
  .btn:focus-visible, .seg button:focus-visible, .note:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

  /* ---- intro + filters ---- */
  .intro{padding:26px 0 8px}
  .intro p{color:var(--ink-2); font-size:14.5px; max-width:70ch; margin:0 0 10px}
  .intro .lead{color:var(--ink); font-size:17px; max-width:66ch}
  .legendrow{display:flex; gap:8px; flex-wrap:wrap; margin-top:14px}
  .filters{display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:20px 0 8px; position:sticky; top:60px; z-index:10}
  .chip{font-family:var(--mono); font-size:11.5px; letter-spacing:.02em; padding:6px 11px; border-radius:999px; border:1px solid var(--line-2); background:var(--surface); color:var(--ink-2); cursor:pointer; transition:.14s}
  .chip[aria-pressed="true"]{background:var(--ink); color:var(--ground); border-color:var(--ink)}
  .chip .n{opacity:.6; margin-left:5px}

  /* ---- cards ---- */
  main{display:flex; flex-direction:column; gap:16px; margin-top:12px}
  .card{position:relative; background:var(--surface); border:1px solid var(--line); border-radius:14px; box-shadow:var(--shadow); overflow:hidden; scroll-margin-top:130px}
  .card::before{content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--line-2); transition:.18s}
  .card[data-state="agree"]::before{background:var(--pass)}
  .card[data-state="override"]::before{background:var(--override)}
  .card[data-state="na"]::before{background:var(--na)}
  .card-top{display:flex; align-items:flex-start; gap:14px; padding:16px 18px 12px; flex-wrap:wrap}
  .idcol{display:flex; flex-direction:column; gap:3px; min-width:96px}
  .sr{font-family:var(--mono); font-size:15px; font-weight:650; letter-spacing:.01em}
  .catlab{font-family:var(--mono); font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-3)}
  .titlecol{flex:1; min-width:220px}
  .titlecol h3{margin:0 0 3px; font-size:15.5px; font-weight:620; letter-spacing:-.005em; text-wrap:balance}
  .ceo{font-family:var(--mono); font-size:11px; color:var(--ink-3)}
  .intended{display:inline-flex; align-items:center; gap:6px; font-family:var(--mono); font-size:11px; font-weight:600; padding:5px 10px; border-radius:999px; white-space:nowrap}
  .intended .dot{width:7px; height:7px; border-radius:50%}
  .intended.PASS{background:var(--pass-bg); color:var(--pass)} .intended.PASS .dot{background:var(--pass)}
  .intended.FAIL{background:var(--fail-bg); color:var(--fail)} .intended.FAIL .dot{background:var(--fail)}
  .intent{padding:0 18px 14px; color:var(--ink-2); font-size:13.5px; max-width:78ch}
  .intent b{color:var(--ink); font-weight:600}
  .pair{display:inline-block; margin-top:8px; font-family:var(--mono); font-size:11px; color:var(--accent); background:var(--accent-2); border-radius:6px; padding:3px 8px; cursor:pointer; border:1px solid transparent}
  .pair:hover{border-color:var(--accent)}

  .tr-toggle{width:100%; text-align:left; font-family:var(--mono); font-size:11.5px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-3); background:var(--inset); border:none; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:9px 18px; cursor:pointer; display:flex; align-items:center; gap:8px}
  .tr-toggle:hover{color:var(--accent)}
  .tr-toggle .caret{transition:transform .18s}
  .card[data-open="true"] .tr-toggle .caret{transform:rotate(90deg)}
  .transcript{display:none; padding:6px 18px 16px; background:var(--inset); max-height:460px; overflow:auto}
  .card[data-open="true"] .transcript{display:block}
  .turn{display:grid; grid-template-columns:78px 1fr; gap:12px; padding:7px 0; border-bottom:1px solid var(--line)}
  .turn:last-child{border-bottom:none}
  .turn .who{font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; padding-top:3px}
  .turn.ai .who{color:var(--accent)} .turn.user .who{color:var(--ink-3)}
  .turn .say{font-size:13.5px; color:var(--ink); white-space:pre-wrap; word-break:break-word}
  .turn.ai .say{color:var(--ink)} .turn.user .say{color:var(--ink-2)}
  .turn .say strong{font-weight:660}

  .verdict{display:flex; align-items:center; gap:14px; flex-wrap:wrap; padding:13px 18px; border-top:1px solid var(--line)}
  .vlabel{font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-3)}
  .seg{display:inline-flex; border:1px solid var(--line-2); border-radius:9px; overflow:hidden}
  .seg button{font-family:var(--mono); font-size:12px; font-weight:600; letter-spacing:.03em; background:var(--surface); color:var(--ink-2); border:none; border-left:1px solid var(--line-2); padding:8px 14px; cursor:pointer; transition:.12s}
  .seg button:first-child{border-left:none}
  .seg button:hover{background:var(--surface-2)}
  .seg button[aria-pressed="true"][data-v="PASS"]{background:var(--pass); color:#fff}
  .seg button[aria-pressed="true"][data-v="FAIL"]{background:var(--fail); color:#fff}
  .seg button[aria-pressed="true"][data-v="N/A"]{background:var(--na); color:#fff}
  .verdict-state{font-family:var(--mono); font-size:11.5px; font-weight:600; margin-left:auto}
  .verdict-state.pending{color:var(--ink-3)}
  .verdict-state.agree{color:var(--pass)}
  .verdict-state.override{color:var(--override)}
  .note{flex-basis:100%; font-family:var(--sans); font-size:13px; color:var(--ink); background:var(--inset); border:1px solid var(--line-2); border-radius:8px; padding:8px 11px; resize:vertical; min-height:0; height:36px}
  .note::placeholder{color:var(--ink-3)}
  .card[data-state="override"] .note{border-color:var(--override)}

  .toast{position:fixed; left:50%; bottom:26px; transform:translateX(-50%) translateY(20px); background:var(--ink); color:var(--ground); font-size:13px; font-weight:550; padding:11px 18px; border-radius:10px; box-shadow:var(--shadow); opacity:0; pointer-events:none; transition:.24s; z-index:40; max-width:90vw}
  .toast.show{opacity:1; transform:translateX(-50%) translateY(0)}
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
  @media (max-width:640px){
    .turn{grid-template-columns:1fr; gap:2px} .turn .who{padding-top:0}
    .bar-in{gap:10px} .brand{margin-right:0; width:100%}
  }
</style>

<div class="app">
  <header class="bar">
    <div class="bar-in">
      <div class="brand">
        <span class="eyebrow">Judge-suite · label review</span>
        <h1>makes_it_a_dialogue — synthetic seed set</h1>
      </div>
      <div class="tally">
        <div class="stat"><b id="t-rev">0/18</b><span>reviewed</span></div>
        <div class="stat"><b id="t-agree">0</b><span>agree</span></div>
        <div class="stat ov"><b id="t-ov">0</b><span>override</span></div>
      </div>
      <button class="btn" id="copyBtn">Copy for chat</button>
      <button class="btn primary" id="exportBtn">Export CSV</button>
    </div>
  </header>

  <div class="wrap">
    <section class="intro">
      <p class="lead">Every label in this set was written by Claude, not by a human grader. Before it can seed judge calibration, you decide whether each intended label is right.</p>
      <p>18 transcripts: <b>9 PASS</b> (a reflective question — "how did that feel?" — plus engagement with what the participant actually said) and <b>9 FAIL</b>. The pass bar is target behavior — no real coach in the corpus meets it. Read each transcript, then set your verdict. Agree by picking the intended label; override by picking a different one. Add a note on any override so the reason survives. Export when done.</p>
    </section>

    <div class="filters" id="filters"></div>
    <main id="cards"></main>
  </div>
  <div class="toast" id="toast"></div>
</div>

<script id="rows" type="application/json">__DATA_JSON__</script>
<script>
(function(){
  const ROWS = JSON.parse(document.getElementById('rows').textContent);
  const state = {}; // sr -> {verdict, note}
  ROWS.forEach(r => state[r.sr] = {verdict:null, note:''});
  let filter = 'all';

  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  function renderTranscript(text){
    const segs = text.split(/\n(?=AI:|User:)/);
    return segs.map(seg => {
      const isAI = seg.startsWith('AI:');
      const who = isAI ? 'Coach' : 'Participant';
      let body = seg.replace(/^(AI:|User:)\s*/, '');
      body = esc(body).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      return '<div class="turn '+(isAI?'ai':'user')+'"><div class="who">'+who+'</div><div class="say">'+body+'</div></div>';
    }).join('');
  }

  function cardState(sr){
    const v = state[sr].verdict;
    if(!v) return 'pending';
    if(v === 'N/A') return 'na';
    return v === ROWS.find(r=>r.sr===sr).intended ? 'agree' : 'override';
  }

  const cardsEl = document.getElementById('cards');
  function build(){
    cardsEl.innerHTML = ROWS.map(r => {
      const pairHtml = r.pair ? '<span class="pair" data-goto="'+r.pair+'">↔ boundary pair · #'+r.pair+'</span>' : '';
      return `
      <article class="card" id="card-${r.sr}" data-cat="${r.cat}" data-open="false" data-state="pending">
        <div class="card-top">
          <div class="idcol"><span class="sr">#${r.sr}</span><span class="catlab">${r.catLabel}</span></div>
          <div class="titlecol"><h3>${esc(r.title)}</h3><span class="ceo">${esc(r.ceo)}</span></div>
          <span class="intended ${r.intended}"><span class="dot"></span>intended · ${r.intended}</span>
        </div>
        <div class="intent"><b>Why this label:</b> ${esc(r.intent)}${pairHtml}</div>
        <button class="tr-toggle" data-toggle="${r.sr}"><span class="caret">▸</span> Read transcript</button>
        <div class="transcript">${renderTranscript(r.transcript)}</div>
        <div class="verdict">
          <span class="vlabel">Your call</span>
          <div class="seg" role="group" aria-label="verdict for ${r.sr}">
            <button data-v="PASS" data-sr="${r.sr}" aria-pressed="false">PASS</button>
            <button data-v="FAIL" data-sr="${r.sr}" aria-pressed="false">FAIL</button>
            <button data-v="N/A" data-sr="${r.sr}" aria-pressed="false">N/A</button>
          </div>
          <span class="verdict-state pending" id="vs-${r.sr}">not reviewed</span>
          <textarea class="note" data-note="${r.sr}" placeholder="Note (required if you override)…"></textarea>
        </div>
      </article>`;
    }).join('');
  }

  function refreshCard(sr){
    const st = cardState(sr);
    const card = document.getElementById('card-'+sr);
    card.dataset.state = st;
    const v = state[sr].verdict;
    card.querySelectorAll('.seg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v===v)));
    const vs = document.getElementById('vs-'+sr);
    const intended = ROWS.find(r=>r.sr===sr).intended;
    if(st==='pending'){ vs.className='verdict-state pending'; vs.textContent='not reviewed'; }
    else if(st==='agree'){ vs.className='verdict-state agree'; vs.textContent='✓ agrees with intended'; }
    else if(st==='na'){ vs.className='verdict-state override'; vs.textContent='△ N/A · differs from '+intended; }
    else { vs.className='verdict-state override'; vs.textContent='△ OVERRIDE · you say '+v+', intended '+intended; }
  }

  function refreshTally(){
    let rev=0, agree=0, ov=0;
    ROWS.forEach(r => { const s=cardState(r.sr); if(s!=='pending'){rev++;} if(s==='agree'){agree++;} if(s==='override'||s==='na'){ov++;} });
    document.getElementById('t-rev').textContent = rev+'/'+ROWS.length;
    document.getElementById('t-agree').textContent = agree;
    document.getElementById('t-ov').textContent = ov;
  }

  // filters
  const cats=[['all','All'],['clean-pos','Clean positive'],['matched-neg','Matched negative'],['tricky-pos','Tricky positive'],['tricky-neg','Tricky negative'],['pending','Pending'],['override','Overrides']];
  function buildFilters(){
    document.getElementById('filters').innerHTML = cats.map(([k,label])=>{
      let n;
      if(k==='all') n=ROWS.length;
      else if(k==='pending') n=ROWS.filter(r=>cardState(r.sr)==='pending').length;
      else if(k==='override') n=ROWS.filter(r=>['override','na'].includes(cardState(r.sr))).length;
      else n=ROWS.filter(r=>r.cat===k).length;
      return '<button class="chip" data-f="'+k+'" aria-pressed="'+(filter===k)+'">'+label+'<span class="n">'+n+'</span></button>';
    }).join('');
  }
  function applyFilter(){
    ROWS.forEach(r=>{
      const card=document.getElementById('card-'+r.sr);
      const s=cardState(r.sr);
      let show = filter==='all' || r.cat===filter || (filter==='pending'&&s==='pending') || (filter==='override'&&['override','na'].includes(s));
      card.style.display = show ? '' : 'none';
    });
  }

  let toastT;
  function toast(msg){ const t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('show'),2200); }

  // events
  document.addEventListener('click', e=>{
    const seg=e.target.closest('.seg button');
    if(seg){ const sr=seg.dataset.sr; state[sr].verdict = state[sr].verdict===seg.dataset.v ? null : seg.dataset.v; refreshCard(sr); refreshTally(); buildFilters(); return; }
    const tog=e.target.closest('[data-toggle]');
    if(tog){ const c=document.getElementById('card-'+tog.dataset.toggle); c.dataset.open = c.dataset.open==='true'?'false':'true'; return; }
    const goto=e.target.closest('[data-goto]');
    if(goto){ const c=document.getElementById('card-'+goto.dataset.goto); c.dataset.open='true'; c.scrollIntoView({behavior:'smooth',block:'center'}); c.animate([{boxShadow:'0 0 0 3px var(--accent)'},{boxShadow:'var(--shadow)'}],{duration:1100}); return; }
    const chip=e.target.closest('.chip');
    if(chip){ filter=chip.dataset.f; buildFilters(); applyFilter(); return; }
  });
  document.addEventListener('input', e=>{ const n=e.target.closest('[data-note]'); if(n){ state[n.dataset.note].note=n.value; } });

  // export
  function rowsCsv(){
    const head=['source_row','ceo_id','category','intended_label','your_verdict','agrees','note'];
    const lines=[head.join(',')];
    ROWS.forEach(r=>{
      const v=state[r.sr].verdict||'';
      const agrees = v ? (v===r.intended?'1':'0') : '';
      const note='"'+(state[r.sr].note||'').replace(/"/g,'""')+'"';
      lines.push([r.sr,r.ceo,r.cat,r.intended,v,agrees,note].join(','));
    });
    return lines.join('\n');
  }
  document.getElementById('exportBtn').addEventListener('click', ()=>{
    const blob=new Blob([rowsCsv()],{type:'text/csv'});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='dialogue_review_maya.csv'; a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href),1000); toast('CSV downloaded — hand it back to Claude');
  });
  function summary(){
    let rev=0; const ov=[];
    ROWS.forEach(r=>{ const s=cardState(r.sr); if(s!=='pending')rev++;
      if(s==='override'||s==='na'){ ov.push('  #'+r.sr+' ('+r.cat+') intended '+r.intended+' → you '+state[r.sr].verdict+(state[r.sr].note?' — '+state[r.sr].note:'')); }});
    let out='makes_it_a_dialogue review — Maya\nreviewed '+rev+'/'+ROWS.length+' · overrides '+ov.length+'\n';
    out += ov.length ? 'OVERRIDES:\n'+ov.join('\n') : 'No overrides — all intended labels confirmed.';
    return out;
  }
  document.getElementById('copyBtn').addEventListener('click', async ()=>{
    const txt=summary();
    try{ await navigator.clipboard.writeText(txt); toast('Summary copied — paste it into chat'); }
    catch(_){ const ta=document.createElement('textarea'); ta.value=txt; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); toast('Summary copied — paste it into chat'); }
  });

  build(); buildFilters(); ROWS.forEach(r=>refreshCard(r.sr)); refreshTally();
})();
</script>
"""

html = TEMPLATE.replace("__DATA_JSON__", json.dumps(DATA))
out = HERE / "dialogue_review.html"
out.write_text(html)
print(f"Wrote {out}  ({len(DATA)} transcripts, {len(html)} bytes)")
