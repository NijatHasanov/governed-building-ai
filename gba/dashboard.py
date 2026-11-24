"""Build a single-file HTML demo from scenario results (no external libraries)."""
from __future__ import annotations

import html
import json
from dataclasses import asdict

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Governed building AI demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;800&display=swap" rel="stylesheet">
<style>
/* VOICE: clear, factual engineering report a school board can read
   IDEA: a metro-style line diagram of one school day, three routes through it
   PICTURE: large temperature chart of three hot days, the community limit as a red line
   COLOUR and TYPE: white ground, black ink, line colours blue/red/amber/green; Figtree
   LAYOUT: finding as title, key figures, main chart, then log, rules, method */
:root{color-scheme:light dark;--bg:light-dark(#ffffff,#0e1116);--ink:light-dark(#111111,#eef0f3);--mute:light-dark(#5d6168,#9aa1ab);--line:light-dark(#e3e5e8,#262b33);--panel:light-dark(#f5f6f7,#151a21);--blue:#0a5cff;--red:#e6261f;--amber:#ffb400;--green:#00a05a}
:root[data-theme=light]{color-scheme:light}:root[data-theme=dark]{color-scheme:dark}
*{box-sizing:border-box;min-width:0}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Figtree,system-ui,sans-serif;overflow-x:clip}
.band{padding:clamp(24px,4vw,56px) max(5vw,16px);max-width:1240px;margin:0 auto}
h1{font-size:clamp(28px,4.2vw,44px);line-height:1.08;font-weight:800;margin:0 0 12px;text-wrap:balance;max-width:24ch}
h2{font-size:22px;font-weight:800;margin:0 0 10px}
.lead{color:var(--mute);max-width:68ch;margin:0 0 20px}
.seg{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 18px}
.seg button{font:600 15px Figtree,sans-serif;min-height:44px;padding:8px 16px;border-radius:22px;border:2px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.seg button[aria-pressed=true]{border-color:var(--ink);background:var(--ink);color:var(--bg)}
.seg button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--blue);outline-offset:2px}
.desc{margin:-6px 0 18px;max-width:72ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:2px;background:var(--line);border:2px solid var(--line);border-radius:12px;overflow:hidden}
.kpi{background:var(--bg);padding:12px 14px}
.kpi .k{font-size:13px;color:var(--mute)}.kpi .v{font-size:clamp(22px,3vw,28px);font-weight:800;white-space:nowrap}
.kpi .d{font-size:13px;color:var(--mute);white-space:nowrap}
.fig{position:relative;min-height:340px;margin-top:8px}.fig.sm{min-height:200px}
.fig>svg{position:absolute;inset:0;width:100%;height:100%}
.cap{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mute);margin-top:18px}
.sw{display:inline-block;width:18px;height:4px;border-radius:2px;vertical-align:middle;margin-right:6px}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal}
th{font-weight:600;color:var(--mute);font-size:13px}
.scroll{overflow-x:auto}
.filters{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:0 0 10px;font-size:14px}
.filters label{display:flex;gap:6px;align-items:center;min-height:44px}
select{font:16px Figtree,sans-serif;padding:6px 8px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.log{border-top:2px solid var(--ink)}
.e{padding:12px 0;border-bottom:1px solid var(--line)}
.e .m{font-size:13px;color:var(--mute);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.e .m b{color:var(--ink)}
.tag{padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;border:1.5px solid}
.tag.r{color:var(--green);border-color:var(--green)}.tag.o{color:var(--red);border-color:var(--red)}
.e p{margin:4px 0 0;max-width:80ch}
.more{margin-top:10px;min-height:44px;font:600 15px Figtree,sans-serif;padding:8px 16px;border-radius:22px;border:2px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
pre{background:var(--panel);border-radius:12px;padding:14px;overflow-x:auto;font-size:13px;line-height:1.45}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}
@media(max-width:760px){.two{grid-template-columns:minmax(0,1fr)}}
.note{color:var(--mute);font-size:14px;max-width:80ch}
@media (prefers-reduced-motion:no-preference){.fig polyline{transition:opacity .25s}}
</style>
</head>
<body>
<section class="band">
<h1>Same AI, same school: rules written by the building's people stop 31.8&nbsp;C classrooms and stale air</h1>
<p class="lead">A simulated school block in a Riyadh-like summer, cooled by one predictive AI controller. Switch between three setups to see what changes when the people inside set the rules, see every decision, and correct the AI.</p>
<div class="seg" id="seg" role="group" aria-label="Scenario"></div>
<p class="desc" id="desc"></p>
<div class="kpis" id="kpis"></div>
<div class="cap"><span><i class="sw" style="background:var(--blue)"></i>indoor temperature</span><span><i class="sw" style="background:var(--mute)"></i>outdoor</span><span><i class="sw" style="background:var(--red)"></i>25.5 C limit set by the school</span><span><i class="sw" style="background:var(--line);height:10px"></i>school hours</span></div>
<div class="fig" id="fT"><svg id="cT" role="img" aria-label="Indoor and outdoor temperature over three days"></svg></div>
</section>

<section class="band">
<div class="two">
<div><h2>Air quality in class</h2><div class="cap" style="margin-top:0"><span><i class="sw" style="background:var(--green)"></i>CO2 ppm</span><span><i class="sw" style="background:var(--red)"></i>1100 ppm target</span></div><div class="fig sm"><svg id="cC" role="img" aria-label="CO2 over three days"></svg></div></div>
<div><h2>Electricity</h2><div class="cap" style="margin-top:0"><span><i class="sw" style="background:var(--amber)"></i>cooling and fans, kW</span></div><div class="fig sm"><svg id="cP" role="img" aria-label="Electric power over three days"></svg></div></div>
</div>
</section>

<section class="band">
<h2>All three setups side by side</h2>
<div class="scroll"><table id="cmp"></table></div>
<p class="note">The vendor's settings use the least electricity because they let classrooms overheat and cut fresh air. The rules trade that energy for health and comfort, and every trade is logged below.</p>
</section>

<section class="band">
<h2>Decision log: every change, explained</h2>
<div class="filters">
<label><input type="checkbox" id="fR" checked> rule corrections</label>
<label><input type="checkbox" id="fS" checked> staff overrides</label>
<label><input type="checkbox" id="fO"> other AI changes</label>
<label>Day <select id="fD"><option value="0">All</option><option>1</option><option>2</option><option>3</option></select></label>
</div>
<div class="log" id="log"></div>
<button class="more" id="more" hidden>Show more</button>
</section>

<section class="band">
<div class="two">
<div><h2>The rules file</h2><p class="note">Building Rules Format v0.1: plain YAML that the building's own people write and any controller can follow.</p><pre id="rules"></pre></div>
<div><h2>How it works</h2>
<p>The AI proposes an action every 15 minutes: a cooling setpoint and a fresh-air rate, chosen to minimise predicted cost over the next two hours. A governance layer checks each proposal against the rules, corrects anything that breaks a hard rule, relaxes soft rules only when a hard rule needs it, and writes a plain-language explanation.</p>
<p>In recommendation mode, staff review the AI's changes. When they override one, the AI's preferences are updated on site, so it needs fewer corrections the next day.</p>
<p class="note">Prototype v0.1, open source (MIT). Single-zone model of a 600 m2 school block with 120 occupants over three synthetic hot-season days; all parameters are illustrative and listed in the code, not measured from a real building. __VERSION_NOTE__</p>
</div></div>
</section>

<script>
{
const DATA = __DATA__;
const RULES = __RULES__;
let cur = 0, shown = 40;
const $ = id => document.getElementById(id);
const esc = t => String(t).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const v = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const base = DATA[0].summary;

function seg(){
  $('seg').innerHTML = DATA.map((d,i)=>`<button type="button" data-i="${i}" aria-pressed="${i===cur}">${esc(d.name)}</button>`).join('');
}
function delta(a,b,unit,dp){ if(cur===0) return 'baseline'; const x=a-b; return (x>0?'+':'')+x.toFixed(dp)+unit+' vs vendor'; }
function kpis(){
  const s = DATA[cur].summary;
  const k = [
    ['Hours above 25.5 C', s.occupied_hours_above_25_5c_per_day+' h/day', delta(s.occupied_hours_above_25_5c_per_day,base.occupied_hours_above_25_5c_per_day,' h',2)],
    ['Hottest classroom', s.max_occupied_temp_c+' C', delta(s.max_occupied_temp_c,base.max_occupied_temp_c,' C',1)],
    ['Average CO2 in class', s.mean_occupied_co2_ppm+' ppm', delta(s.mean_occupied_co2_ppm,base.mean_occupied_co2_ppm,' ppm',0)],
    ['Electricity', s.energy_kwh_per_day+' kWh/day', delta(s.energy_kwh_per_day,base.energy_kwh_per_day,' kWh',1)],
    ['Staff overrides', s.staff_overrides_per_day.join(' / '), 'day 1 / 2 / 3'],
  ];
  $('kpis').innerHTML = k.map(([a,b,c])=>`<div class="kpi"><div class="k">${a}</div><div class="v">${esc(b)}</div><div class="d">${esc(c)}</div></div>`).join('');
}
function table(){
  const rows = [
    ['Hours above 25.5 C in class, per day', s=>s.occupied_hours_above_25_5c_per_day],
    ['Hottest classroom, C', s=>s.max_occupied_temp_c],
    ['Average CO2 in class, ppm', s=>s.mean_occupied_co2_ppm],
    ['Highest CO2 in class, ppm', s=>s.max_occupied_co2_ppm],
    ['Electricity, kWh per day', s=>s.energy_kwh_per_day],
    ['Peak power, kW', s=>s.peak_kw],
    ['Rule corrections, day 1', s=>s.rule_interventions_per_day[0]],
    ['Staff overrides, day 1 / 2 / 3', s=>s.staff_overrides_per_day.join(' / ')],
  ];
  $('cmp').innerHTML = `<thead><tr><th>Measure</th>${DATA.map(d=>`<th>${esc(d.name)}</th>`).join('')}</tr></thead><tbody>`+
    rows.map(([l,f])=>`<tr><td>${l}</td>${DATA.map(d=>`<td>${esc(f(d.summary))}</td>`).join('')}</tr>`).join('')+'</tbody>';
}
function chart(id, keys, refs, y0, y1){
  const svg=$(id), W=svg.clientWidth, H=svg.clientHeight; if(!W||!H) return;
  const s=DATA[cur].series, n=s.t.length, L=W<520?30:40, R=8, T=10, B=24;
  const x=i=>L+(W-L-R)*i/(n-1), y=val=>T+(H-T-B)*(1-(val-y0)/(y1-y0));
  let g='';
  for(let i=0;i<n;i++){ if(s.occupied[i]){ let j=i; while(j<n&&s.occupied[j]) j++; g+=`<rect x="${x(i)}" y="${T}" width="${x(j-1)-x(i)}" height="${H-T-B}" fill="${v('--line')}"/>`; i=j; } }
  const ticks=W<520?3:5;
  for(let k=0;k<=ticks;k++){ const val=y0+(y1-y0)*k/ticks; g+=`<line x1="${L}" x2="${W-R}" y1="${y(val)}" y2="${y(val)}" stroke="${v('--line')}"/><text x="${L-6}" y="${y(val)+4}" font-size="12" text-anchor="end" fill="${v('--mute')}">${Math.round(val)}</text>`; }
  for(let d=0; d<n/96; d++){ g+=`<text x="${x(d*96)+6}" y="${H-6}" font-size="12" fill="${v('--mute')}">Day ${d+1}</text>`; }
  refs.forEach(r=>{ g+=`<line x1="${L}" x2="${W-R}" y1="${y(r)}" y2="${y(r)}" stroke="${v('--red')}" stroke-width="2" stroke-dasharray="6 4"/>`; });
  keys.forEach(k=>{ const pts=s[k.k].map((val,i)=>`${x(i).toFixed(1)},${y(val).toFixed(1)}`).join(' '); g+=`<polyline points="${pts}" fill="none" stroke="${k.c}" stroke-width="${k.w||2.5}" stroke-linejoin="round"/>`; });
  svg.innerHTML=g;
}
function charts(){
  const s=DATA[cur].series;
  const maxAll = k => Math.max(...DATA.flatMap(d=>d.series[k]));
  chart('cT',[{k:'t_out',c:v('--mute'),w:1.5},{k:'t_in',c:v('--blue'),w:3}],[25.5],20,46);
  chart('cC',[{k:'co2',c:v('--green')}],[1100],400,Math.ceil(maxAll('co2')/500)*500);
  chart('cP',[{k:'kw',c:v('--amber')}],[],0,Math.ceil(maxAll('kw')/10)*10);
}
function log(reset){
  if(reset) shown=40;
  const d=DATA[cur], fr=$('fR').checked, fs=$('fS').checked, fo=$('fO').checked, day=+$('fD').value;
  const rows=d.log.filter(e=>e.notable&&(!day||e.day===day)&&((fr&&e.rules.length)||(fs&&e.staff==='overridden')||(fo&&!e.rules.length&&e.staff!=='overridden')));
  $('log').innerHTML = rows.length ? rows.slice(0,shown).map(e=>`<div class="e"><div class="m"><b>Day ${e.day}, ${esc(e.time)}</b><span>${e.occupied?'school hours':'empty building'}</span><span>${e.t_in_c} C · ${e.co2_ppm} ppm · ${e.electric_kw} kW</span>${e.rules.map(r=>`<span class="tag r">${esc(r)}</span>`).join('')}${e.staff==='overridden'?'<span class="tag o">staff override</span>':''}</div><p>${esc(e.explanation)}</p></div>`).join('')
    : `<div class="e"><p>${cur===0?'In this setup the AI acts alone: no rules are checked and no one reviews its choices. Tick "other AI changes" to see what it did.':'No entries match these filters.'}</p></div>`;
  $('more').hidden = rows.length<=shown;
}
function render(){ seg(); $('desc').textContent=DATA[cur].description; kpis(); charts(); log(true); }
$('seg').addEventListener('click', e=>{ const b=e.target.closest('button'); if(b){ cur=+b.dataset.i; render(); } });
['fR','fS','fO','fD'].forEach(id=>$(id).addEventListener('change',()=>log(true)));
$('more').addEventListener('click',()=>{ shown+=40; log(false); });
$('rules').textContent = RULES;
table(); render();
const ro = new ResizeObserver(charts); ['cT','cC','cP'].forEach(id=>ro.observe($(id)));
}
</script>
</body></html>
"""


def build(results, rules_text: str, version_note: str = "") -> str:
    data = [{
        "name": r.name, "description": r.description, "summary": r.summary,
        "series": r.series, "log": [asdict(e) for e in r.log if e.notable],
    } for r in results]
    return (TEMPLATE
            .replace("__DATA__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
            .replace("__RULES__", json.dumps(rules_text).replace("</", "<\\/"))
            .replace("__VERSION_NOTE__", html.escape(version_note)))
