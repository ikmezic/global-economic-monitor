#!/usr/bin/env python3
"""Public economic dashboard. Standard library only; compatible with existing GitHub workflow."""
import csv, io, json, sys, time, urllib.request, html
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# id, display name, section, unit, cadence, risk direction (up/down/none)
SERIES=[
('DGS10','US 10Y nominal yield','Tržišta kapitala','%', 'daily','up'),
('DFII10','US 10Y real yield (TIPS)','Tržišta kapitala','%', 'daily','up'),
('T10Y2Y','US yield curve: 10Y–2Y','Tržišta kapitala','pp','daily','down'),
('BAMLH0A0HYM2','US high-yield credit spread','Tržišta kapitala','pp','daily','up'),
('STLFSI4','St. Louis financial stress','Tržišta kapitala','index','weekly','up'),
('VIXCLS','VIX volatility','Tržišta kapitala','index','daily','up'),
('DTWEXBGS','Broad USD trade-weighted index','Monetarni sustav','index','daily','none'),
('M2SL','US M2 money supply','Monetarni sustav','USD bn','monthly','none'),
('WALCL','Fed balance sheet','Monetarni sustav','USD mn','weekly','none'),
('DEXUSEU','USD per 1 EUR','Monetarni sustav','USD/EUR','daily','none'),
('GFDEBTN','US gross federal debt','Javni dug','USD mn','quarterly','none'),
('GFDEGDQ188S','US gross federal debt / GDP','Javni dug','%','quarterly','up'),
('A091RC1Q027SBEA','US federal interest payments (SAAR)','Javni dug','USD bn','quarterly','up'),
('CPIAUCSL','US CPI index','Globalna ekonomija','index','monthly','none'),
('UNRATE','US unemployment','Globalna ekonomija','%','monthly','up'),
('INDPRO','US industrial production','Globalna ekonomija','index','monthly','down'),
('PAYEMS','US nonfarm payroll employment','Globalna ekonomija','thousands','monthly','down'),
('DCOILBRENTEU','Brent oil','Energija i sirovine','USD/bbl','daily','none'),
('DCOILWTICO','WTI oil','Energija i sirovine','USD/bbl','daily','none'),
('DHHNGSP','Henry Hub natural gas','Energija i sirovine','USD/MMBtu','daily','none'),
]
HEADERS={'User-Agent':'Mozilla/5.0 GlobalEconomicRiskMonitor/2.0'}
def fetch(code):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+code
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=35) as res: raw=res.read().decode('utf-8-sig')
    rows=list(csv.reader(io.StringIO(raw))); points=[]
    for row in rows[1:]:
        if len(row)<2 or row[1].strip() in ('','.','NaN'): continue
        try: points.append([row[0],float(row[1])])
        except ValueError: pass
    if not points: raise ValueError('No numeric observations')
    return points,url

def main():
    out=ROOT/'data';out.mkdir(exist_ok=True)
    snapshot=[];all_rows=[];errors=[]
    for code,name,section,unit,freq,direction in SERIES:
        try:
            points,url=fetch(code)
            recent=points[-1]; prior=points[-2][1] if len(points)>1 else None
            snapshot.append({'id':code,'name':name,'category':section,'unit':unit,'frequency':freq,'direction':direction,'date':recent[0],'value':recent[1],'previous':prior,'source':url,'points':points})
            all_rows.extend((code,name,section,unit,d,v,url) for d,v in points)
            print('OK',code,recent)
        except Exception as ex:
            errors.append(code+': '+str(ex));print('ERROR',errors[-1],file=sys.stderr)
        time.sleep(.12)
    if not snapshot: raise SystemExit('No valid data; publication aborted')
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    with (out/'latest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['series_id','name','category','unit','observation_date','value','frequency','source_url','download_utc'])
        for s in snapshot:w.writerow([s['id'],s['name'],s['category'],s['unit'],s['date'],s['value'],s['frequency'],s['source'],stamp])
    with (out/'history.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['series_id','name','category','unit','observation_date','value','source_url']);w.writerows(all_rows)
    (out/'latest.json').write_text(json.dumps({'updated_utc':stamp,'series':snapshot,'errors':errors},ensure_ascii=False),encoding='utf-8')
    # Embed limited history (max 30 years per series) to keep public page fast.
    compact=[]
    for s in snapshot:
        v=dict(s);v['points']=s['points'][-11000:];compact.append(v)
    template=(ROOT/'dashboard_template.html').read_text(encoding='utf-8') if (ROOT/'dashboard_template.html').exists() else TEMPLATE
    page=template.replace('__DATA_JSON__',json.dumps({'updated':stamp,'series':compact,'errors':errors},ensure_ascii=False).replace('</','<\/'))
    (ROOT/'dashboard.html').write_text(page,encoding='utf-8')
    print(f'Published {len(snapshot)}/{len(SERIES)} series; errors={len(errors)}')

TEMPLATE=r'''<!doctype html><html lang="hr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Global Economic Risk Monitor</title>
<style>
:root{color-scheme:dark;--bg:#091322;--panel:#111f32;--line:#27384c;--text:#e9f0fa;--muted:#9eb0c7;--accent:#70b9ff;--green:#53d3a0;--amber:#f5c56a;--red:#f07f88}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,Segoe UI,sans-serif}header{padding:27px max(18px,5vw);border-bottom:1px solid var(--line);background:#0d1b2e}h1{margin:0;font-size:clamp(25px,3vw,38px)}header p,.sub,.hint{color:var(--muted)}.wrap{max-width:1450px;margin:auto;padding:24px 18px}.top{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}.pill{background:var(--panel);border:1px solid var(--line);padding:10px 15px;border-radius:12px}.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}button,select{font:inherit;color:var(--text);background:#192b41;border:1px solid #38506b;border-radius:9px;padding:9px 12px;cursor:pointer}button.active{background:#23548a;border-color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:17px;cursor:pointer}.card:hover{border-color:var(--accent)}.card h3{margin:8px 0 10px;font-size:16px}.meta{color:var(--muted);font-size:12px}.value{font-size:27px;font-weight:750}.unit{font-size:12px;color:var(--muted)}.flag{display:inline-block;font-size:11px;padding:4px 8px;border-radius:8px;background:#23364a}.flag.warn{background:#574422;color:#ffda8c}.flag.high{background:#5c2732;color:#ffb0b8}.flag.ok{background:#1d493c;color:#92ebc5}.chartbox{margin-top:23px;background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:19px}canvas{width:100%;height:320px;display:block}.charthead{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}.charthead h2{margin:0}.periods{display:flex;gap:5px;flex-wrap:wrap}.periods button{font-size:12px;padding:7px 10px}.footer{margin:24px 0;color:var(--muted);font-size:12px}.alert{border-left:4px solid var(--amber);padding:12px 15px;background:#28283a;border-radius:8px;margin-bottom:14px}.bad{border-left-color:var(--red)}a{color:#91c9ff}.hide{display:none}@media(max-width:600px){canvas{height:240px}.value{font-size:23px}}
</style></head><body><header><h1>Global Economic &amp; Financial Risk Monitor</h1><p>Automatski ažurirani javni podaci · pet analitičkih područja · povijesni trendovi</p></header><main class="wrap"><div id="summary" class="top"></div><div class="nav" id="nav"></div><div id="alerts"></div><div id="cards" class="grid"></div><section class="chartbox"><div class="charthead"><div><h2 id="chartTitle">Povijesni trend</h2><div id="chartMeta" class="meta"></div></div><div class="periods" id="periods"></div></div><canvas id="plot" aria-label="Grafikon povijesnih vrijednosti"></canvas><p id="stats" class="hint"></p><p class="meta">Odaberite pokazatelj klikom na karticu. Usporedbe i pragovi služe za praćenje promjena, ne za predviđanje krize.</p><a id="source" target="_blank" rel="noopener">Izvor: FRED</a></section><div class="footer">Izvor: Federal Reserve Bank of St. Louis (FRED), izvorni izdavatelji navedeni na povezanim stranicama. Datum podatka može biti stariji od datuma preuzimanja. Ne predstavlja investicijski savjet. Bez osobnih podataka.</div></main>
<script id="payload" type="application/json">__DATA_JSON__</script><script>
const D=JSON.parse(document.getElementById('payload').textContent), S=D.series, groups=['Sve','Globalna ekonomija','Monetarni sustav','Javni dug','Energija i sirovine','Tržišta kapitala'];let group='Sve',selected=S[0],years=5;
const $=id=>document.getElementById(id), fmt=(v,d=2)=>Number(v).toLocaleString('hr-HR',{maximumFractionDigits:d}),today=new Date(D.updated.replace(' UTC','Z'));
function dateAge(s){return Math.round((today-new Date(s.date+'T00:00:00Z'))/86400000)}
function risk(s){let pts=s.points,dir=s.direction;if(dir==='none'||pts.length<35)return ['—','neutral'];let now=s.value,prev=pts.slice(Math.max(0,pts.length-261),-1).map(x=>x[1]);if(prev.length<30)return ['—','neutral'];let sorted=[...prev].sort((a,b)=>a-b),pct=sorted.filter(x=>x<=now).length/sorted.length;let score=dir==='up'?pct:1-pct;return score>=.95?['Povijesni ekstrem','high']:score>=.85?['Povišena razina','warn']:['Uobičajen raspon','ok']}
function spark(s){let p=s.points.slice(-60);if(p.length<2)return '';let vals=p.map(x=>x[1]),lo=Math.min(...vals),hi=Math.max(...vals),range=hi-lo||1;let points=p.map((x,i)=>`${(i/(p.length-1)*100).toFixed(1)},${(35-(x[1]-lo)/range*30).toFixed(1)}`).join(' ');return `<svg viewBox="0 0 100 40" preserveAspectRatio="none" style="width:100%;height:55px;margin-top:12px"><polyline points="${points}" fill="none" stroke="#70b9ff" stroke-width="1.4" vector-effect="non-scaling-stroke"/></svg>`}
function nav(){ $('nav').innerHTML=groups.map(g=>`<button class="${g===group?'active':''}" data-group="${g}">${g}</button>`).join('');document.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>{group=b.dataset.group;render()}) }
function render(){nav();let items=S.filter(s=>group==='Sve'||s.category===group),extreme=items.filter(s=>risk(s)[1]==='high');$('summary').innerHTML=`<div class="pill"><b>${S.length}</b> pokazatelja</div><div class="pill">Ažurirano: <b>${D.updated}</b></div><div class="pill">Neuspjela preuzimanja: <b>${D.errors.length}</b></div><div class="pill">Ekstremi (statistički): <b>${extreme.length}</b></div>`;
$('alerts').innerHTML=(D.errors.length?`<div class="alert bad">Nedostupne serije: ${D.errors.map(x=>x.replaceAll('<','&lt;')).join('; ')}</div>`:'')+(extreme.length?`<div class="alert">Povijesni ekstremi u odabranom području: ${extreme.map(s=>s.name).join(', ')}. <b>To nije prognoza krize.</b></div>`:'');
$('cards').innerHTML=items.map(s=>{let [label,cls]=risk(s),age=dateAge(s);return `<article class="card" data-id="${s.id}"><div class="meta">${s.category} · ${s.frequency}</div><h3>${s.name}</h3><div class="value">${fmt(s.value)} <span class="unit">${s.unit}</span></div><div class="meta">Podatak: ${s.date} · starost ${age} dana</div><div style="margin-top:10px"><span class="flag ${cls}">${label}</span></div>${spark(s)}</article>`}).join('');document.querySelectorAll('[data-id]').forEach(c=>c.onclick=()=>{selected=S.find(s=>s.id===c.dataset.id);chart();$('plot').scrollIntoView({behavior:'smooth',block:'center'})});if(!items.includes(selected))selected=items[0];chart()}
function chart(){if(!selected)return;let s=selected;$('chartTitle').textContent=s.name;$('chartMeta').textContent=`${s.id} · ${s.category} · ${s.unit} · posljednje opažanje ${s.date}`;$('source').href=s.source;
$('periods').innerHTML=[1,3,5,10,25,50].map(y=>`<button class="${years===y?'active':''}" data-years="${y}">${y} g.</button>`).join('');document.querySelectorAll('[data-years]').forEach(b=>b.onclick=()=>{years=+b.dataset.years;chart()});
let end=new Date(s.points[s.points.length-1][0]+'T00:00:00Z'),cut=new Date(end);cut.setUTCFullYear(cut.getUTCFullYear()-years);let p=s.points.filter(x=>new Date(x[0]+'T00:00:00Z')>=cut);if(p.length<2)p=s.points.slice(-2);let first=p[0][1],last=p[p.length-1][1];$('stats').textContent=`Razdoblje: ${p[0][0]} – ${p[p.length-1][0]} · promjena ${fmt(last-first)} ${s.unit} (${first!==0?fmt((last/first-1)*100):'—'} %) · ${p.length} opažanja`;
let canvas=$('plot'),r=canvas.getBoundingClientRect(),dpr=devicePixelRatio||1,w=Math.max(r.width,300),h=Math.max(r.height,200);canvas.width=w*dpr;canvas.height=h*dpr;let c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);let l=66,t=18,right=14,bottom=35,vals=p.map(x=>x[1]),min=Math.min(...vals),max=Math.max(...vals),pad=(max-min||1)*.12;min-=pad;max+=pad;let x=i=>l+i/(p.length-1)*(w-l-right),y=v=>t+(max-v)/(max-min)*(h-t-bottom);c.font='12px system-ui';c.textAlign='right';c.strokeStyle='#31465d';c.fillStyle='#a5b6cc';for(let i=0;i<=4;i++){let v=min+(max-min)*i/4,yy=y(v);c.beginPath();c.moveTo(l,yy);c.lineTo(w-right,yy);c.stroke();c.fillText(fmt(v),l-8,yy+4)}c.strokeStyle='#70b9ff';c.lineWidth=2;c.beginPath();p.forEach((pt,i)=>{if(i===0)c.moveTo(x(i),y(pt[1]));else c.lineTo(x(i),y(pt[1]))});c.stroke();c.fillStyle='#a5b6cc';c.textAlign='left';c.fillText(p[0][0],l,h-10);c.textAlign='right';c.fillText(p[p.length-1][0],w-right,h-10)}
window.addEventListener('resize',()=>chart());render();
</script></body></html>'''
if __name__=='__main__':main()
