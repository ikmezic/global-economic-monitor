#!/usr/bin/env python3
"""Global risk monitor: public FRED CSV data, no API key or pip packages."""
import csv, io, json, os, sys, time, urllib.request, urllib.error, html
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SERIES=[
('DGS10','US 10Y Treasury yield','Rates','%', 'daily'),
('DFII10','US 10Y real TIPS yield','Rates','%', 'daily'),
('T10Y2Y','US 10Y minus 2Y yield','Rates','pp', 'daily'),
('BAMLH0A0HYM2','US high-yield credit spread','Credit','pp','daily'),
('STLFSI4','St Louis Financial Stress Index','Credit','index','weekly'),
('VIXCLS','VIX volatility index','Markets','index','daily'),
('DTWEXBGS','Broad trade-weighted USD index','Dollar','index','daily'),
('M2SL','US M2 money stock','Money','USD bn','monthly'),
('WALCL','Federal Reserve total assets','Money','USD mn','weekly'),
('GFDEBTN','US gross federal debt','Debt','USD mn','quarterly'),
('GFDEGDQ188S','US federal debt / GDP','Debt','%','quarterly'),
('A091RC1Q027SBEA','US federal interest payments','Debt','USD bn SAAR','quarterly'),
('CPIAUCSL','US CPI','Inflation','index','monthly'),
('UNRATE','US unemployment rate','Economy','%','monthly'),
('INDPRO','US industrial production','Economy','index','monthly'),
('DCOILBRENTEU','Brent crude oil','Energy','USD/bbl','daily'),
('DCOILWTICO','WTI crude oil','Energy','USD/bbl','daily'),
('DHHNGSP','Henry Hub natural gas','Energy','USD/MMBtu','daily'),
('WCESTUS1','US crude oil inventories','Energy','thousand bbl','weekly'),
('WDI11','US distillate fuel inventories','Energy','thousand bbl','weekly'),
]
HEADERS={'User-Agent':'GlobalEconomicRiskMonitor/1.0 (public data educational dashboard)'}
def fetch(code):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+code
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=30) as res: data=res.read().decode('utf-8-sig')
    rows=list(csv.reader(io.StringIO(data)))
    if len(rows)<3: raise ValueError('empty CSV')
    output=[]
    for row in rows[1:]:
        if len(row)<2 or row[1].strip() in ('','.','NaN'):continue
        try: output.append((row[0],float(row[1])))
        except ValueError: pass
    if not output:raise ValueError('no numeric observations')
    return output,url

def svg_line(values):
    if len(values)<2:return ''
    pts=values[-80:]; yy=[x[1] for x in pts];lo=min(yy);hi=max(yy);span=hi-lo or 1
    coords=' '.join(f'{10+i*300/(len(pts)-1):.1f},{92-(v-lo)/span*75:.1f}' for i,(_,v) in enumerate(pts))
    return f'<svg viewBox="0 0 320 105" aria-label="Recent trend"><line x1="10" y1="95" x2="310" y2="95" stroke="#CBD5E1"/><polyline points="{coords}" fill="none" stroke="#2563eb" stroke-width="2.5"/></svg>'

def main():
    out=ROOT/'data';out.mkdir(exist_ok=True)
    snapshot=[];all_rows=[];errors=[]
    for code,name,category,unit,freq in SERIES:
        try:
            observations,url=fetch(code)
            lastdate,lastval=observations[-1]
            previous=observations[-2][1] if len(observations)>1 else None
            snapshot.append({'id':code,'name':name,'category':category,'unit':unit,'frequency':freq,'date':lastdate,'value':lastval,'previous':previous,'source':url,'points':observations[-80:]})
            all_rows.extend((code,name,category,unit,d,v,url) for d,v in observations)
            print(f'OK {code} {lastdate} {lastval}')
        except Exception as ex:
            errors.append(f'{code}: {ex}');print('ERROR',errors[-1],file=sys.stderr)
        time.sleep(0.1)
    if not snapshot:
        print('No data downloaded; existing files left unchanged.',file=sys.stderr);sys.exit(2)
    timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    with (out/'latest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['series_id','name','category','unit','observation_date','value','frequency','source_url','download_utc'])
        for s in snapshot:w.writerow([s['id'],s['name'],s['category'],s['unit'],s['date'],s['value'],s['frequency'],s['source'],timestamp])
    with (out/'history.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['series_id','name','category','unit','observation_date','value','source_url']);w.writerows(all_rows)
    (out/'latest.json').write_text(json.dumps({'updated_utc':timestamp,'series':snapshot,'errors':errors},ensure_ascii=False),encoding='utf-8')
    cards=[]
    for s in snapshot:
        name=html.escape(s['name']);unit=html.escape(s['unit']);url=html.escape(s['source'],quote=True)
        val=f"{s['value']:,.2f}";previous=s['previous'];delta='' if previous is None else f" | change vs prior: {s['value']-previous:+,.2f}"
        cards.append(f'<article class="card"><div class="category">{html.escape(s["category"])} · {html.escape(s["frequency"])}</div><h3>{name}</h3><div class="value">{val} <small>{unit}</small></div><div class="date">Observation {s["date"]}{delta}</div>{svg_line(s["points"])}<a href="{url}">FRED source</a></article>')
    status=f'{len(snapshot)}/{len(SERIES)} series refreshed; {len(errors)} failed'
    errors_html='<p class="error">Failed series: '+html.escape('; '.join(errors))+'</p>' if errors else ''
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Global Economic & Financial Risk Monitor</title><style>body{font:15px system-ui,-apple-system,Segoe UI,sans-serif;background:#f3f6fa;color:#14213d;margin:0}header{background:#10213b;color:white;padding:26px max(20px,5vw)}header p{color:#c8d4e4}.wrap{padding:24px max(20px,5vw)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(275px,1fr));gap:16px}.card{background:white;border:1px solid #dfe5ed;border-radius:12px;padding:17px;box-shadow:0 2px 6px #14213d09}.category{font-size:12px;text-transform:uppercase;color:#64748b;letter-spacing:.07em}h3{font-size:16px;min-height:38px;margin:10px 0}.value{font-size:27px;font-weight:750}.value small{font-size:12px;color:#64748b}.date{font-size:11px;color:#64748b;margin-top:6px;min-height:28px}svg{width:100%;height:105px}a{font-size:12px;color:#1d4ed8}.error{color:#b91c1c}footer{padding:22px;color:#64748b;font-size:12px}</style></head><body><header><h1>Global Economic & Financial Risk Monitor</h1><p>Updated '''+timestamp+''' · '''+status+'''</p></header><div class="wrap"><p>Official FRED observations, not a recession forecast. Different series have different release delays and units. Missing series are explicitly reported.</p>'''+errors_html+'''<div class="grid">'''+''.join(cards)+'''</div></div><footer>Data: Federal Reserve Bank of St. Louis FRED; original providers listed on source pages. Last 80 observations shown. No market prices are guaranteed real time.</footer></body></html>'''
    (ROOT/'dashboard.html').write_text(page,encoding='utf-8')
    print('Wrote dashboard.html, data/latest.csv, data/history.csv')
if __name__=='__main__':main()
