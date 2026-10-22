import urllib.request,ssl,os,json
U=['https://www.taipower.com.tw/d006/loadGraph/loadGraph/data/genary.json',
'https://www.taipower.com.tw/d006/loadGraph/loadGraph/data/loadpara.json',
'https://www.taipower.com.tw/d006/loadGraph/loadGraph/data/loadfueltype.csv',
'https://www.taipower.com.tw/d006/loadGraph/loadGraph/data/genloadareaperc.csv',
'https://service.taipower.com.tw/data/opendata/apply/file/d006001/001.json',
'https://data.taipower.com.tw/opendata/apply/file/d006001/001.json',
'https://taipower-api.jacob.workers.dev/']
os.makedirs('data/power',exist_ok=True);out=open('data/power/_probe.log','w')
ctx=ssl.create_default_context();ctx2=ssl._create_unverified_context()
for u in U:
  for c,lab in ((ctx,'ssl'),(ctx2,'nossl')):
    try:
      r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30,context=c);b=r.read()
      out.write(f'== {u} [{lab}] {r.status} ACAO={r.headers.get("Access-Control-Allow-Origin")} CT={r.headers.get("Content-Type")} len={len(b)}\n{b[:2500].decode("utf-8","replace")}\n\n');break
    except Exception as e: out.write(f'== {u} [{lab}] ERR {e}\n')
