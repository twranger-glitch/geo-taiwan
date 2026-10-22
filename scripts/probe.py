import urllib.request,sys,os,json
os.makedirs('data/_probe',exist_ok=True);out=open('data/_probe/log.txt','w')
for u in sys.argv[1:]:
  try:
    r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60);b=r.read()
    out.write(f'== {u} {r.status} CT={r.headers.get("Content-Type")} len={len(b)}\n{b[:6000].decode("utf-8-sig","replace")}\n\n')
  except Exception as e: out.write(f'== {u} ERR {e}\n')
