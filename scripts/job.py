# One-off: inputs for the 3D earthquake page.
#  - CWA earthquake catalog, current year (E-A0073-001, monthly)
#  - ETOPO 2022 15-arc-second surface elevation (land + sea floor), cropped to 118.5-123.5E, 20.5-26.5N
#  - USGS Slab2 depth grids for the Ryukyu (ryu) and Manila (man) subduction zones
import urllib.request,os,subprocess,sys,tarfile,io,json,traceback
subprocess.run([sys.executable,'-m','pip','install','-q','netCDF4'],check=True)
import numpy as np
from netCDF4 import Dataset
O='data/_job';os.makedirs(O,exist_ok=True);log=open(f'{O}/log.txt','w')
UA={'User-Agent':'geo-taiwan-classroom/1.0 (+https://geo.twranger.com/)'}
def dl(u,p,t=900):
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t) as r, open(p,'wb') as f:
        while True:
            b=r.read(1<<20)
            if not b:break
            f.write(b)
    log.write(f'downloaded {u} {os.path.getsize(p)}\n');log.flush();return p
L0,L1,A0,A1=118.5,123.5,20.5,26.5
try:
    dl('https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/E-A0073-001?Authorization=rdec-key-123-45678-011121314&downloadType=WEB&format=JSON',f'{O}/cat_current.json')
except Exception: log.write(traceback.format_exc())
try:
    parts=[]
    for tile,lo in [('N30E105',105),('N30E120',120)]:
        p=dl(f'https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/15s/15s_surface_elev_netcdf/ETOPO_2022_v1_15s_{tile}_surface.nc','/tmp/'+tile+'.nc')
        with Dataset(p) as d:
            lat=np.array(d.variables['lat'][:]);lon=np.array(d.variables['lon'][:])
            log.write(f'{tile} lat {lat[0]}..{lat[-1]} n={len(lat)} lon {lon[0]}..{lon[-1]} n={len(lon)} vars={list(d.variables)}\n')
            ri=np.where((lat>A0)&(lat<A1))[0];ci=np.where((lon>L0)&(lon<L1))[0]
            if len(ci)==0: continue
            z=np.array(d.variables['z'][ri[0]:ri[-1]+1,ci[0]:ci[-1]+1],dtype=np.float32)
            parts.append((lon[ci[0]],lon[ci[-1]],lat[ri[0]],lat[ri[-1]],z))
        os.remove(p)
    z=np.concatenate([p[4] for p in sorted(parts,key=lambda q:q[0])],axis=1)
    meta={'lon0':float(min(p[0] for p in parts)),'lon1':float(max(p[1] for p in parts)),'lat0':float(parts[0][2]),'lat1':float(parts[0][3]),'shape':z.shape,'rows':'south to north' }
    np.save(f'{O}/etopo15s.npy',np.round(z).astype(np.int16));json.dump(meta,open(f'{O}/etopo15s.json','w'),default=str)
    log.write(f'etopo {z.shape} min {z.min()} max {z.max()} {meta}\n')
except Exception: log.write(traceback.format_exc())
try:
    p=dl('https://www.sciencebase.gov/catalog/file/get/5aa1b00ee4b0b1c392e86467?f=__disk__d5%2F91%2F39%2Fd591399bf4f249ab49ffec8a366e5070fe96e0ba','/tmp/slab2.tgz')
    with tarfile.open(p) as t:
        names=t.getnames();log.write('slab2 files: '+' '.join(n for n in names if 'ryu' in n or 'man' in n)+'\n')
        for n in names:
            b=os.path.basename(n)
            if (b.startswith('ryu_') or b.startswith('man_')) and ('_dep_' in b or '_dip_' in b or '_unc_' in b) and b.endswith('.grd'):
                f=t.extractfile(n);open('/tmp/'+b,'wb').write(f.read())
                with Dataset('/tmp/'+b) as d:
                    v=list(d.variables);x=np.array(d.variables[v[0]][:]);y=np.array(d.variables[v[1]][:]);zz=np.ma.filled(d.variables[v[2]][:].astype(np.float32),np.nan)
                    log.write(f'{b} vars {v} x {x.min()}..{x.max()} y {y.min()}..{y.max()} z {np.nanmin(zz)}..{np.nanmax(zz)} shape {zz.shape}\n')
                    np.savez_compressed(f'{O}/{b[:-4]}.npz',x=x,y=y,z=zz)
except Exception: log.write(traceback.format_exc())
log.close()
