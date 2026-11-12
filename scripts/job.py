"""One-off data job run by .github/workflows/job.yml (outputs go to data/_job/)."""
import urllib.request, urllib.parse, json, math, io, os, time
import numpy as np
from PIL import Image
O = 'data/_job/'; os.makedirs(O, exist_ok=True)
UA = {'User-Agent': 'geo-taiwan-classroom/1.0 (+https://geo.twranger.com/)', 'Accept': '*/*'}
log = open(O + 'log.txt', 'w')
def get(u, t=300, tries=3):
    for k in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception as e: log.write(f'retry {k} {u[:90]} {e}\n'); log.flush(); time.sleep(5 + 10 * k)
    return None
# 1. county boundaries (MOI data via taiwan-atlas)
for f in ['counties-10t.json', 'towns-10t.json']:
    for base in ['https://unpkg.com/taiwan-atlas/', 'https://cdn.jsdelivr.net/npm/taiwan-atlas/']:
        b = get(base + f, 60, 2)
        if b: open(O + f, 'wb').write(b); log.write(f'{f} {len(b)}\n'); break
# 2. hillshade from Terrarium elevation tiles (Web Mercator)
def tx(lon, z): return (lon + 180) / 360 * 2 ** z
def ty(lat, z): r = math.radians(lat); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z
def lat_of(y, z): n = math.pi - 2 * math.pi * y / 2 ** z; return math.degrees(math.atan(math.sinh(n)))
def shade(name, lon0, lon1, lat0, lat1, z):
    x0, x1 = int(tx(lon0, z)), int(tx(lon1, z)); y0, y1 = int(ty(lat1, z)), int(ty(lat0, z))
    W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256; E = np.zeros((H, W), np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            b = get(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png', 60)
            if not b: log.write(f'missing tile {z}/{x}/{y}\n'); continue
            a = np.asarray(Image.open(io.BytesIO(b)).convert('RGB')).astype(np.float32)
            E[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    lat_c = (lat0 + lat1) / 2; px = 156543.03 * math.cos(math.radians(lat_c)) / 2 ** z
    gy, gx = np.gradient(E * 1.6, px)
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(315), math.radians(42)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    flat = math.sin(alt)
    v = 128 + (hs - flat) * 190
    land = E > 0.5
    sea = np.clip(128 - np.sqrt(np.clip(-E, 0, 6000)) * 1.15, 40, 128)  # deeper sea = darker
    v = np.where(land, v, sea)
    img = Image.fromarray(np.clip(v, 0, 255).astype(np.uint8), 'L')
    mask = Image.fromarray((land * 255).astype(np.uint8), 'L')
    img.save(O + name + '_hs.webp', quality=82); mask.save(O + name + '_land.png', optimize=True)
    bounds = [[lat_of(y1 + 1, z), x0 / 2 ** z * 360 - 180], [lat_of(y0, z), (x1 + 1) / 2 ** z * 360 - 180]]
    json.dump({'z': z, 'bounds': bounds, 'w': W, 'h': H, 'emax': float(E.max())}, open(O + name + '_hs.json', 'w'))
    log.write(f'{name} {W}x{H} max {E.max():.0f}\n'); log.flush()
shade('tw', 119.25, 122.15, 21.8, 25.45, 10)
shade('km', 118.12, 118.52, 24.36, 24.54, 12)
shade('mz', 119.85, 120.56, 25.92, 26.42, 12)
# 3. OSM: plant outlines for all of Taiwan; lines and plants for Kinmen / Matsu
OV = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
def ov(q, name):
    for h in OV:
        b = get(h + '?data=' + urllib.parse.quote(q, safe=''), 320, 1)
        if b and len(b) > 600: open(O + name, 'wb').write(b); log.write(f'{name} {len(b)} from {h}\n'); log.flush(); return
    log.write(f'{name} FAILED\n')
ov('[out:json][timeout:250];area["ISO3166-1"="TW"][admin_level=2]->.a;(way["power"="plant"](area.a);relation["power"="plant"](area.a););out geom tags;', 'plant_geom.json')
ov('[out:json][timeout:200];(way["power"~"line|cable|minor_line"](24.36,118.12,24.54,118.52);way["power"~"line|cable|minor_line"](25.92,119.85,26.42,120.56);nwr["power"~"plant|generator"](24.36,118.12,24.54,118.52);nwr["power"~"plant|generator"](25.92,119.85,26.42,120.56););out geom tags;', 'islands.json')
ov('[out:json][timeout:250];(way["power"="line"](23.3,119.3,23.9,119.75);nwr["power"="substation"]["voltage"~"345000|161000"](21.8,119.3,25.4,122.1););out geom tags;', 'penghu_subs.json')
log.close()
