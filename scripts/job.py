# One-off: find the CWA earthquake catalog files (data.gov.tw dataset 97095) and record what they contain.
import urllib.request,os,json,zipfile,io
os.makedirs('data/_job',exist_ok=True);log=open('data/_job/log.txt','w')
K='rdec-key-123-45678-011121314';UA={'User-Agent':'geo-taiwan-classroom/1.0 (+https://geo.twranger.com/)'}
def get(u,t=300):
    r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t);return r.status,r.headers.get('Content-Type'),r.read()
for code in ['E-A0073-001','E-A0073-002','E-A0073-004','E-A0073-005']:
    for fmt in ['JSON','ZIP','XML']:
        u=f'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{code}?Authorization={K}&downloadType=WEB&format={fmt}'
        try:
            st,ct,b=get(u);log.write(f'== {code} {fmt} {st} {ct} len={len(b)}\n')
            if b[:2]==b'PK':
                z=zipfile.ZipFile(io.BytesIO(b));names=z.namelist();log.write(f'  zip {len(names)} files: {names[:5]} ... {names[-3:]}\n')
                open(f'data/_job/{code}.zip','wb').write(b) if len(b)<90e6 else None
                n=names[0];log.write(z.read(n)[:3000].decode('utf-8','replace')+'\n')
            else:
                log.write(b[:2500].decode('utf-8','replace')+'\n')
            if fmt=='JSON' and st==200: break
        except Exception as e: log.write(f'== {code} {fmt} ERR {e}\n')
for u in ['https://opendata.cwa.gov.tw/dataset/earthquake/E-A0073-002','https://opendata.cwa.gov.tw/dataset/earthquake/E-A0073-001']:
    try:st,ct,b=get(u,60);s=b.decode('utf-8','replace');i=s.find('E-A0073');log.write(f'== {u} {st}\n{s[i-1500:i+2500]}\n')
    except Exception as e: log.write(f'== {u} ERR {e}\n')
