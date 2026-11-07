#!/usr/bin/env python3
"""Public economic dashboard. Standard library only; compatible with existing GitHub workflow."""
import csv, io, json, sys, time, urllib.request, html
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# id, display name, section, unit, cadence, risk direction (up/down/none)
SERIES=[('DGS10', 'US 10-year Treasury yield', 'Capital Markets', '%', 'daily', 'up', 'Benchmark long-term borrowing cost for the US government; rising yields can increase refinancing costs.'), ('DFII10', 'US 10-year real yield (TIPS)', 'Capital Markets', '%', 'daily', 'up', 'Inflation-adjusted US Treasury yield; a measure of real financing conditions.'), ('T10Y2Y', 'US yield curve (10Y minus 2Y)', 'Capital Markets', 'pp', 'daily', 'down', 'Difference between 10-year and 2-year Treasury yields; inversion has historically preceded some recessions.'), ('BAMLH0A0HYM2', 'US high-yield credit spread', 'Capital Markets', 'pp', 'daily', 'up', 'Extra yield demanded for riskier corporate bonds relative to Treasuries; a gauge of credit stress.'), ('STLFSI4', 'St. Louis Financial Stress Index', 'Capital Markets', 'index', 'weekly', 'up', 'Composite measure of stress across US financial markets; higher values indicate more stress.'), ('VIXCLS', 'VIX equity volatility index', 'Capital Markets', 'index', 'daily', 'up', 'Options-implied near-term volatility for the S&P 500; not a direct recession probability.'), ('SP500', 'S&P 500 index', 'Capital Markets', 'index', 'daily', 'none', 'Broad index of large US listed companies; market prices may diverge from economic fundamentals.'), ('DTWEXBGS', 'Broad trade-weighted US dollar', 'Monetary System', 'index', 'daily', 'none', 'US dollar exchange value against a broad basket of trading-partner currencies.'), ('M2SL', 'US M2 money stock', 'Monetary System', 'USD bn', 'monthly', 'none', 'Cash and liquid deposits held by the public; not equivalent to physical money printing.'), ('WALCL', 'Federal Reserve total assets', 'Monetary System', 'USD mn', 'weekly', 'none', 'Size of the Federal Reserve balance sheet, including securities and lending assets.'), ('DEXUSEU', 'US dollars per euro', 'Monetary System', 'USD/EUR', 'daily', 'none', 'Exchange rate: US dollars required to buy one euro; a higher value means a stronger euro.'), ('DEXCHUS', 'Chinese yuan per US dollar', 'Monetary System', 'CNY/USD', 'daily', 'none', 'Exchange rate: Chinese yuan required to buy one US dollar.'), ('DEXJPUS', 'Japanese yen per US dollar', 'Monetary System', 'JPY/USD', 'daily', 'none', 'Exchange rate: Japanese yen required to buy one US dollar.'), ('GFDEBTN', 'US gross federal debt', 'Public Debt', 'USD mn', 'quarterly', 'none', 'Total federal debt outstanding, including debt held by the public and intragovernmental holdings.'), ('GFDEGDQ188S', 'US gross federal debt to GDP', 'Public Debt', '%', 'quarterly', 'up', 'Gross federal debt as a share of US GDP; differs from debt held by the public.'), ('A091RC1Q027SBEA', 'US federal interest payments (annual rate)', 'Public Debt', 'USD bn', 'quarterly', 'up', 'Federal interest payments at a seasonally adjusted annual rate; not the same as net budget interest.'), ('CPIAUCSL', 'US consumer price index', 'Global Economy', 'index', 'monthly', 'none', 'Price level for a broad US consumer basket; year-over-year changes measure inflation.'), ('UNRATE', 'US unemployment rate', 'Global Economy', '%', 'monthly', 'up', 'Share of the US labor force unemployed and actively seeking work.'), ('INDPRO', 'US industrial production', 'Global Economy', 'index', 'monthly', 'down', 'Real output of US manufacturing, mining and utilities.'), ('PAYEMS', 'US nonfarm payroll employment', 'Global Economy', 'thousands', 'monthly', 'down', 'Number of US payroll jobs outside farming; revisions can be substantial.'), ('GDPC1', 'US real GDP', 'Global Economy', 'bn chained USD', 'quarterly', 'down', 'Inflation-adjusted output of the US economy, measured quarterly.'), ('IRLTLT01EZM156N', 'Euro area long-term government bond yield', 'Global Economy', '%', 'monthly', 'none', 'Harmonized long-term government bond yield indicator for the euro area (OECD via FRED).'), ('IRLTLT01DEM156N', 'Germany long-term government bond yield', 'Global Economy', '%', 'monthly', 'none', 'Long-term German government bond yield, a benchmark for euro-area borrowing conditions.'), ('JPNCPIALLMINMEI', 'Japan consumer price index', 'Global Economy', 'index', 'monthly', 'none', 'Japan consumer price level; compare annual percentage changes to track inflation.'), ('CHNCPIALLMINMEI', 'China consumer price index', 'Global Economy', 'index', 'monthly', 'none', 'China consumer price level, subject to source updates and reporting lags.'), ('DCOILBRENTEU', 'Brent crude oil price', 'Energy & Commodities', 'USD/bbl', 'daily', 'none', 'International crude oil benchmark, sensitive to supply, demand and geopolitical disruption.'), ('DCOILWTICO', 'WTI crude oil price', 'Energy & Commodities', 'USD/bbl', 'daily', 'none', 'US crude oil benchmark; its difference from Brent reflects regional market conditions.'), ('DHHNGSP', 'Henry Hub natural gas price', 'Energy & Commodities', 'USD/MMBtu', 'daily', 'none', 'US natural gas spot benchmark; not the same as European gas prices.'), ('IPMAN', 'US manufacturing production', 'Industry & Trade', 'index', 'monthly', 'down', 'Inflation-adjusted US manufacturing output, excluding mining and utilities.'), ('IPG3344S', 'US semiconductor manufacturing output', 'Industry & Trade', 'index', 'monthly', 'down', 'US semiconductor and electronic component manufacturing production proxy; not global chip sales.'), ('HOUST', 'US housing starts', 'Industry & Trade', 'thousands SAAR', 'monthly', 'down', 'New US residential construction starts at a seasonally adjusted annual rate.'), ('PERMIT', 'US building permits', 'Industry & Trade', 'thousands SAAR', 'monthly', 'down', 'US residential building permits, a forward-looking indicator for construction.'), ('IPG3361T3S', 'US motor vehicle and parts production', 'Industry & Trade', 'index', 'monthly', 'down', 'US motor vehicle and parts industrial production; not worldwide vehicle sales.')]
HEADERS={'User-Agent':'Mozilla/5.0 GlobalEconomicRiskMonitor/4.2'}
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


# World Bank Open Data API: international country and world aggregates.
# World Bank figures are generally annual and may lag by one or more years.
COUNTRIES = {'WLD':'World','EUU':'European Union','NAC':'North America','EAS':'East Asia & Pacific','ECS':'Europe & Central Asia','LCN':'Latin America & Caribbean','MEA':'Middle East & North Africa','SAS':'South Asia','SSF':'Sub-Saharan Africa','HIC':'High income','MIC':'Middle income','LIC':'Low income','USA':'United States','CHN':'China',
             'DEU':'Germany','JPN':'Japan','IND':'India','GBR':'United Kingdom',
             'FRA':'France','BRA':'Brazil','KOR':'South Korea','CAN':'Canada',
             'ITA':'Italy','IDN':'Indonesia','MEX':'Mexico','AUS':'Australia',
             'ZAF':'South Africa','SAU':'Saudi Arabia'}
WB_INDICATORS = [
 ('NY.GDP.MKTP.KD.ZG','Real GDP growth','Global Economy','%','down','Annual change in inflation-adjusted GDP; negative values indicate contraction.'),
 ('NY.GDP.MKTP.CD','Nominal GDP','Global Economy','USD','none','Economic output at current US dollar exchange rates; not adjusted for inflation.'),
 ('FP.CPI.TOTL.ZG','Consumer price inflation','Global Economy','%','up','Annual change in consumer prices; international methodologies may differ.'),
 ('SL.UEM.TOTL.ZS','Unemployment rate (ILO estimate)','Global Economy','%','up','ILO-modelled unemployment as a share of the labor force; not directly comparable with every national release.'),
 ('NV.IND.MANF.ZS','Manufacturing value added / GDP','Industry & Trade','%','none','Manufacturing contribution to GDP; a structural share, not a measure of monthly factory output.'),
 ('NE.TRD.GNFS.ZS','Trade / GDP','Industry & Trade','%','none','Exports plus imports of goods and services as a share of GDP; measures trade openness.'),
 ('GC.DOD.TOTL.GD.ZS','Central government debt / GDP','Public Debt','%','up','Central-government debt where reported; NOT general-government debt and often unavailable for some economies.'),
 ('BX.KLT.DINV.WD.GD.ZS','FDI net inflows / GDP','Industry & Trade','%','none','Net foreign direct investment inflows as a share of GDP; can be negative.'),
]
def fetch_world_bank(indicator):
    countries=';'.join(COUNTRIES)
    url=f'https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}?format=json&per_page=2000'
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=45) as res:
        payload=json.load(res)
    if not isinstance(payload,list) or len(payload)<2 or not isinstance(payload[1],list):
        raise ValueError('Unexpected World Bank response')
    out={key:[] for key in COUNTRIES}
    for row in payload[1]:
        key=row.get('countryiso3code') or row.get('country',{}).get('id')
        # World Bank aggregates may use the country id rather than an ISO3 code.
        if key not in out:
            key=row.get('country',{}).get('id')
        if key not in out or row.get('value') is None:continue
        try: out[key].append([str(row['date'])+'-01-01',float(row['value'])])
        except (TypeError,ValueError,KeyError):pass
    for points in out.values():points.sort(key=lambda p:p[0])
    return out,url

def international_series():
    for indicator,name,section,unit,direction,description in WB_INDICATORS:
        try:
            countries,url=fetch_world_bank(indicator)
            count=0
            for code,label in COUNTRIES.items():
                points=countries.get(code,[])
                if not points:continue
                recent=points[-1]
                count+=1
                yield {'id':'WB_'+indicator+'_'+code,'name':name,'category':section,
                       'unit':unit,'frequency':'annual','direction':direction,
                       'description':description,'date':recent[0],'value':recent[1],
                       'previous':points[-2][1] if len(points)>1 else None,
                       'source':url,'points':points,'country':label,'provider':'World Bank'}
            print('WORLD BANK',indicator,count,'countries',flush=True)
        except Exception as exc:
            print('WORLD BANK ERROR',indicator,str(exc),file=sys.stderr,flush=True)
        time.sleep(.15)

def main():
    out=ROOT/'data';out.mkdir(exist_ok=True)
    snapshot=[];all_rows=[];errors=[]
    for code,name,section,unit,freq,direction,description in SERIES:
        try:
            points,url=fetch(code)
            recent=points[-1]; prior=points[-2][1] if len(points)>1 else None
            snapshot.append({'id':code,'name':name,'category':section,'unit':unit,'frequency':freq,'direction':direction,'description':description,'date':recent[0],'value':recent[1],'previous':prior,'source':url,'points':points,'country':'United States' if name.startswith('US ') or name.startswith('Federal Reserve') or name.startswith('St. Louis') or name.startswith('S&P') or name.startswith('VIX') else ('Germany' if name.startswith('Germany') else 'Japan' if name.startswith('Japan') else 'China' if name.startswith('China') else 'European Union' if name.startswith('Euro area') else 'Cross-market / US-linked'), 'provider':'FRED'})
            all_rows.extend((code,name,section,unit,d,v,url) for d,v in points)
            print('OK',code,recent)
        except Exception as ex:
            errors.append(code+': '+str(ex));print('ERROR',errors[-1],file=sys.stderr)
        time.sleep(.12)
    for s in international_series():
        snapshot.append(s)
        all_rows.extend((s['id'],s['name'],s['category'],s['unit'],d,v,s['source']) for d,v in s['points'])
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
    page=template.replace('__DATA_JSON__',json.dumps({'updated':stamp,'series':compact,'errors':errors},ensure_ascii=False).replace('</','<\\/'))
    (ROOT/'dashboard.html').write_text(page,encoding='utf-8')
    print(f'Published {len(snapshot)} metrics (FRED + World Bank); FRED errors={len(errors)}')

TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Global Economic Risk Monitor</title>
<style>
:root{color-scheme:dark;--bg:#091322;--panel:#111f32;--line:#27384c;--text:#e9f0fa;--muted:#9eb0c7;--accent:#70b9ff;--green:#53d3a0;--amber:#f5c56a;--red:#f07f88}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,Segoe UI,sans-serif}header{padding:27px max(18px,5vw);border-bottom:1px solid var(--line);background:#0d1b2e}h1{margin:0;font-size:clamp(25px,3vw,38px)}header p,.sub,.hint{color:var(--muted)}.wrap{max-width:1450px;margin:auto;padding:24px 18px}.top{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}.pill{background:var(--panel);border:1px solid var(--line);padding:10px 15px;border-radius:12px}.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}button,select{font:inherit;color:var(--text);background:#192b41;border:1px solid #38506b;border-radius:9px;padding:9px 12px;cursor:pointer}button.active{background:#23548a;border-color:var(--accent)}.filters{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.filters .hint{font-size:12px}.risk-summary{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:15px}.risk-pill{background:#192b41;border:1px solid #38506b;border-radius:9px;padding:10px 13px;font-size:12px}.risk-pill strong{display:block;margin-top:4px;font-size:15px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:17px;cursor:pointer}.card:hover{border-color:var(--accent)}.card h3{margin:8px 0 10px;font-size:16px}.explain{font-size:12px;line-height:1.55;color:var(--muted);margin:10px 0 0}.meta{color:var(--muted);font-size:12px}.value{font-size:27px;font-weight:750}.unit{font-size:12px;color:var(--muted)}.flag{display:inline-block;font-size:11px;padding:4px 8px;border-radius:8px;background:#23364a}.flag.warn{background:#574422;color:#ffda8c}.flag.high{background:#5c2732;color:#ffb0b8}.flag.ok{background:#1d493c;color:#92ebc5}.chartbox{margin-top:23px;background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:19px}canvas{width:100%;height:360px;display:block;cursor:crosshair}.chart-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px}.chart-controls label{color:var(--muted);font-size:13px}.chart-controls input{accent-color:var(--accent)}.charthead{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}.charthead h2{margin:0}.periods{display:flex;gap:5px;flex-wrap:wrap}.periods button{font-size:12px;padding:7px 10px}.footer{margin:24px 0;color:var(--muted);font-size:12px}.alert{border-left:4px solid var(--amber);padding:12px 15px;background:#28283a;border-radius:8px;margin-bottom:14px}.bad{border-left-color:var(--red)}a{color:#91c9ff}.hide{display:none}@media(max-width:600px){canvas{height:240px}.value{font-size:23px}}
</style></head><body><header><h1>Global Economic &amp; Financial Risk Monitor</h1><p>World and major economies · trusted public sources · historical trends · dated chart axes</p></header><main class="wrap"><div id="summary" class="top"></div><div class="nav" id="nav"></div><div class="filters"><label for="country">Economy: </label><select id="country"></select><span class="hint">Geography: World Bank regional aggregates and countries. Income groups overlap with geographic groups. Annual observations may lag.</span></div><div class="hint" style="margin-bottom:15px">Geographic grouping follows World Bank regions; income groups are a separate classification. IMF advanced/emerging economies are not interchangeable with World Bank income groups. US indicators are labelled United States, not Other economies. World Bank region totals and country observations should not be added together.</div><div id="riskSummary" class="risk-summary"></div><div id="alerts"></div><div id="cards" class="grid"></div><section class="chartbox"><div class="charthead"><div><h2 id="chartTitle">Historical trend</h2><div id="chartMeta" class="meta"></div></div><div class="periods" id="periods"></div></div><div class="chart-controls"><label><input type="checkbox" id="events"> Show major historical events</label><span class="hint">Hover over the chart for exact date and value</span></div><canvas id="plot" aria-label="Historical data chart with calendar-year horizontal axis"></canvas><p id="stats" class="hint"></p><p id="chartDescription" class="explain"></p><p class="meta">Forecasts are not generated in this version. For forward-looking analysis, use IMF WEO published projections as an independently labelled forecast source, then validate any in-house models with historical backtests. </p><p class="meta">Select a metric card to view its history. Percentile flags describe historical extremes, not crisis forecasts. Risk warnings use transparent thresholds: GDP growth below 0%, inflation above 8%, unemployment above 10%, or central-government debt above 100% of GDP. These are screening rules, not forecasts or comparable sovereign credit ratings.</p><a id="source" target="_blank" rel="noopener">Open original data source</a></section><div class="footer">Sources: World Bank Open Data API and Federal Reserve Bank of St. Louis (FRED). Observation dates may lag behind the refresh date. Educational use only; not investment advice. No personal data.</div></main>
<script id="payload" type="application/json">__DATA_JSON__</script><script>
const D=JSON.parse(document.getElementById('payload').textContent), S=D.series, groups=['All','Global Economy','Monetary System','Public Debt','Energy & Commodities','Industry & Trade','Capital Markets'];let group='All',selected=S[0],years=5,country='All',hoverX=null;
const $=id=>document.getElementById(id), fmt=(v,d=2)=>Number(v).toLocaleString('en-US',{maximumFractionDigits:d}),today=new Date(D.updated.replace(' UTC','Z'));
function dateAge(s){return Math.round((today-new Date(s.date+'T00:00:00Z'))/86400000)}
function risk(s){let pts=s.points,dir=s.direction;if(dir==='none'||pts.length<35)return ['—','neutral'];let now=s.value,prev=pts.slice(Math.max(0,pts.length-261),-1).map(x=>x[1]);if(prev.length<30)return ['—','neutral'];let sorted=[...prev].sort((a,b)=>a-b),pct=sorted.filter(x=>x<=now).length/sorted.length;let score=dir==='up'?pct:1-pct;return score>=.95?['Historical extreme','high']:score>=.85?['Elevated percentile','warn']:['Typical percentile','ok']}
function spark(s){let p=s.points.slice(-60);if(p.length<2)return '';let vals=p.map(x=>x[1]),lo=Math.min(...vals),hi=Math.max(...vals),range=hi-lo||1;let points=p.map((x,i)=>`${(i/(p.length-1)*100).toFixed(1)},${(35-(x[1]-lo)/range*30).toFixed(1)}`).join(' ');return `<svg viewBox="0 0 100 40" preserveAspectRatio="none" style="width:100%;height:55px;margin-top:12px"><polyline points="${points}" fill="none" stroke="#70b9ff" stroke-width="1.4" vector-effect="non-scaling-stroke"/></svg>`}
function setupCountries(){let names=['All','World','European Union','North America','East Asia & Pacific','Europe & Central Asia','Latin America & Caribbean','Middle East & North Africa','South Asia','Sub-Saharan Africa','High income','Middle income','Low income','United States','China','Germany','Japan','India','United Kingdom','France','Brazil','South Korea','Canada','Italy','Indonesia','Mexico','Australia','South Africa','Saudi Arabia'];$('country').innerHTML=names.map(n=>`<option value="${n}">${n==='All'?'All economies':n}</option>`).join('');$('country').value=country;$('country').onchange=()=>{country=$('country').value;render()}}
function warning(s){if(s.provider!=='World Bank')return '';let v=s.value,n=s.name;
 if(n==='Real GDP growth'&&v<0)return 'Contraction';
 if(n==='Consumer price inflation'&&v>8)return 'High inflation';
 if(n==='Unemployment rate (ILO estimate)'&&v>10)return 'High unemployment';
 if(n==='Central government debt / GDP'&&v>100)return 'High central debt';
 return ''}
function riskOverview(items){let wb=items.filter(s=>s.provider==='World Bank'),latest={};for(let s of wb){let k=s.country+'|'+s.name;if(!latest[k]||latest[k].date<s.date)latest[k]=s}let warnings=Object.values(latest).filter(s=>warning(s));let economies=new Set(wb.map(s=>s.country)).size;
 $('riskSummary').innerHTML=`<div class="risk-pill">World Bank economies<strong>${economies}</strong></div><div class="risk-pill">World Bank metrics<strong>${wb.length}</strong></div><div class="risk-pill">Rule-based risk warnings<strong>${warnings.length}</strong></div><div class="risk-pill">Interpretation<strong>Not a crisis probability</strong></div>`;
}
function nav(){ $('nav').innerHTML=groups.map(g=>`<button class="${g===group?'active':''}" data-group="${g}">${g}</button>`).join('');document.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>{group=b.dataset.group;render()}) }
function render(){nav();setupCountries();let items=S.filter(s=>(group==='All'||s.category===group)&&(country==='All'||s.country===country)),extreme=items.filter(s=>risk(s)[1]==='high');riskOverview(items);$('summary').innerHTML=`<div class="pill"><b>${S.length}</b> metrics</div><div class="pill">Updated: <b>${D.updated}</b></div><div class="pill">Unavailable series: <b>${D.errors.length}</b></div><div class="pill">Statistical extremes (selected): <b>${extreme.length}</b></div>`;
$('alerts').innerHTML=(D.errors.length?`<div class="alert bad">Unavailable series: ${D.errors.map(x=>x.replaceAll('<','&lt;')).join('; ')}</div>`:'')+(extreme.length?`<div class="alert">Historical extremes in selected section: ${extreme.map(s=>s.name).join(', ')}. <b>This is not a crisis forecast.</b></div>`:'');
$('cards').innerHTML=items.map(s=>{let [label,cls]=risk(s),age=dateAge(s);return `<article class="card" data-id="${s.id}"><div class="meta">${s.country||'World'} · ${s.category} · ${s.frequency}</div><h3>${s.name}</h3><div class="value">${fmt(s.value)} <span class="unit">${s.unit}</span></div><div class="meta">Observation: ${s.date} · age ${age} days</div><div style="margin-top:10px"><span class="flag ${cls}">${label}</span>${warning(s)?` <span class="flag high">Risk warning: ${warning(s)}</span>`:''}</div><p class="explain">${s.description||""}</p>${spark(s)}</article>`}).join('');document.querySelectorAll('[data-id]').forEach(c=>c.onclick=()=>{selected=S.find(s=>s.id===c.dataset.id);chart();$('plot').scrollIntoView({behavior:'smooth',block:'center'})});if(!items.includes(selected))selected=items[0];chart()}
function chart(){if(!selected){$('chartTitle').textContent='No metrics for this selection';$('chartMeta').textContent='Choose another economy or analytical area';$('stats').textContent='';$('chartDescription').textContent='';$('plot').getContext('2d').clearRect(0,0,$('plot').width,$('plot').height);return}let s=selected;$('chartTitle').textContent=s.name;$('chartMeta').textContent=`${s.country||'World'} · ${s.provider||'FRED'} · ${s.id} · ${s.category} · ${s.unit} · latest observation ${s.date}`;$('source').href=s.source;$('chartDescription').textContent=s.description||'';
$('periods').innerHTML=[1,3,5,10,20,50,0].map(y=>`<button class="${years===y?'active':''}" data-years="${y}">${y?y+'Y':'ALL'}</button>`).join('');document.querySelectorAll('[data-years]').forEach(b=>b.onclick=()=>{years=+b.dataset.years;chart()});
let end=new Date(s.points[s.points.length-1][0]+'T00:00:00Z'),cut=new Date(end);if(years)cut.setUTCFullYear(cut.getUTCFullYear()-years);else cut=new Date('1900-01-01T00:00:00Z');let p=s.points.filter(x=>new Date(x[0]+'T00:00:00Z')>=cut);if(p.length<2)p=s.points.slice(-2);let first=p[0][1],last=p[p.length-1][1];$('stats').textContent=`Period: ${p[0][0]} – ${p[p.length-1][0]} · change ${fmt(last-first)} ${s.unit} (${first!==0?fmt((last/first-1)*100):'—'} %) · ${p.length} observations`;
let canvas=$('plot'),r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=Math.max(r.width,300),h=Math.max(r.height,200);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);let c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
let l=72,t=30,right=25,bottom=58,vals=p.map(q=>q[1]),min=Math.min(...vals),max=Math.max(...vals),pad=(max-min||1)*.12;min-=pad;max+=pad;
let times=p.map(q=>Date.parse(q[0]+'T00:00:00Z')),startMs=times[0],endMs=times[times.length-1],span=endMs-startMs||1;
let x=ms=>l+(ms-startMs)/span*(w-l-right),y=v=>t+(max-v)/(max-min)*(h-t-bottom);
c.font='12px system-ui';c.textAlign='right';c.strokeStyle='#31465d';c.fillStyle='#a5b6cc';
for(let i=0;i<=4;i++){let v=min+(max-min)*i/4,yy=y(v);c.beginPath();c.moveTo(l,yy);c.lineTo(w-right,yy);c.stroke();c.fillText(fmt(v),l-8,yy+4)}
// Real calendar ticks: use actual timestamps, not observation indices.
let startYear=new Date(startMs).getUTCFullYear(),endYear=new Date(endMs).getUTCFullYear(),spanYears=(endMs-startMs)/31557600000;
let tickDates=[];
if(spanYears<=2){let step=spanYears<=.55?1:spanYears<=1?2:3;let d=new Date(Date.UTC(startYear,new Date(startMs).getUTCMonth(),1));while(d.getTime()<=endMs){if(d.getTime()>=startMs&&d.getUTCMonth()%step===0)tickDates.push(new Date(d));d.setUTCMonth(d.getUTCMonth()+1)}}
else{let target=Math.max(2,Math.floor((w-l-right)/100)),step=Math.max(1,Math.ceil(spanYears/target));if(step>2&&step<5)step=5;else if(step>5&&step<10)step=10;else if(step>10)step=Math.ceil(step/5)*5;for(let yr=Math.ceil(startYear/step)*step;yr<=endYear;yr+=step){let d=new Date(Date.UTC(yr,0,1));if(d.getTime()>=startMs&&d.getTime()<=endMs)tickDates.push(d)}}
c.textAlign='center';c.fillStyle='#b5c6dc';c.strokeStyle='#2a3d52';
for(let d of tickDates){let xx=x(d.getTime());c.beginPath();c.moveTo(xx,t);c.lineTo(xx,h-bottom);c.stroke();let label=spanYears<=2?d.toLocaleDateString('en-GB',{month:'short',year:'2-digit',timeZone:'UTC'}):String(d.getUTCFullYear());c.fillText(label,xx,h-bottom+21)}
c.fillStyle='#a5b6cc';c.fillText('Year / date',l+(w-l-right)/2,h-9);
// Context markers are optional and are not evidence of causation.
if($('events').checked){let markers=[['2008-09-15','Financial crisis'],['2020-03-11','COVID-19'],['2022-02-24','Ukraine war']];c.setLineDash([4,4]);c.strokeStyle='#d7ad70';c.fillStyle='#e7c48e';c.font='10px system-ui';for(let [ds,label] of markers){let ms=Date.parse(ds+'T00:00:00Z');if(ms<startMs||ms>endMs)continue;let xx=x(ms);c.beginPath();c.moveTo(xx,t);c.lineTo(xx,h-bottom);c.stroke();c.save();c.translate(xx+4,t+8);c.rotate(-Math.PI/2);c.textAlign='right';c.fillText(label,0,0);c.restore()}c.setLineDash([])}
c.strokeStyle='#70b9ff';c.lineWidth=2;c.beginPath();p.forEach((pt,i)=>{let xx=x(times[i]);if(i===0)c.moveTo(xx,y(pt[1]));else c.lineTo(xx,y(pt[1]))});c.stroke();
// Exact extrema with dates; labels below the chart in the statistics line.
let low=p.reduce((a,b)=>b[1]<a[1]?b:a),high=p.reduce((a,b)=>b[1]>a[1]?b:a);
$('stats').textContent=`Period: ${p[0][0]} – ${p[p.length-1][0]} · change ${fmt(last-first)} ${s.unit} (${first!==0?fmt((last/first-1)*100):'—'}%) · low ${fmt(low[1])} (${low[0]}) · high ${fmt(high[1])} (${high[0]}) · ${p.length} observations`;
if(hoverX!==null){let mouseTime=startMs+(hoverX-l)/(w-l-right)*span;if(hoverX>=l&&hoverX<=w-right){let lo=0,hi=times.length-1;while(lo<hi){let mid=(lo+hi)>>1;if(times[mid]<mouseTime)lo=mid+1;else hi=mid}let idx=lo>0&&Math.abs(times[lo-1]-mouseTime)<Math.abs(times[lo]-mouseTime)?lo-1:lo,xx=x(times[idx]),yy=y(p[idx][1]);c.strokeStyle='#cbd8e7';c.lineWidth=1;c.setLineDash([3,4]);c.beginPath();c.moveTo(xx,t);c.lineTo(xx,h-bottom);c.stroke();c.setLineDash([]);c.fillStyle='#fff';c.beginPath();c.arc(xx,yy,4,0,Math.PI*2);c.fill();let label=`${p[idx][0]}  |  ${fmt(p[idx][1])} ${s.unit}`,tw=c.measureText(label).width+20,tx=Math.max(l,Math.min(w-right-tw,xx-tw/2));c.fillStyle='#223951';c.fillRect(tx,3,tw,23);c.fillStyle='#fff';c.textAlign='left';c.fillText(label,tx+10,19)}}
}
$('plot').addEventListener('mousemove',e=>{hoverX=e.clientX-$('plot').getBoundingClientRect().left;chart()});$('plot').addEventListener('mouseleave',()=>{hoverX=null;chart()});$('events').addEventListener('change',()=>chart());window.addEventListener('resize',()=>chart());render();
</script></body></html>'''
if __name__=='__main__':main()
