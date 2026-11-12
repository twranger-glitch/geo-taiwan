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
def shade(*a): pass
# 3. OSM: plant outlines for all of Taiwan; lines and plants for Kinmen / Matsu
OV = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
def ov(q, name):
    for h in OV:
        b = get(h + '?data=' + urllib.parse.quote(q, safe=''), 320, 1)
        if b and len(b) > 600: open(O + name, 'wb').write(b); log.write(f'{name} {len(b)} from {h}\n'); log.flush(); return
    log.write(f'{name} FAILED\n')
for nm, bb in [('kinmen.json', '24.38,118.20,24.53,118.50')]:
    ov(f'[out:json][timeout:180];(way["power"~"line|cable|minor_line"]({bb});nwr["power"~"plant|generator"]({bb}););out geom tags;', nm)
log.close()
