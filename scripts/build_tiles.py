"""High-detail (1 arc-second, about 30 m) tiles for zooming in on sealevel.html.

Each tile is a 512 x 512 RGB PNG covering part of the grid lon 119.3-122.1, lat 21.85-25.4:
  R  elevation code (0 ocean; 1-201 = 0-100 m in 0.5 m steps; 202-255 = 100 m + 75 m steps)
  G  flood code: the lowest sea-level code at which the cell joins the ocean (priority flood)
  B  hillshade (0-255)
The page only has to compare G with the chosen sea level, so no flood fill runs in the browser.

Elevation: FABDEM V1-2 (bare earth, buildings and trees removed; Hawker et al. 2022, CC BY-NC-SA 4.0)
where available, otherwise Copernicus GLO-30. Coastline: GSHHG full resolution via GMT grdlandmask.
"""
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

import numpy as np
from netCDF4 import Dataset
from PIL import Image
import rasterio
from numba import njit

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "sealevel", "hr")
TMP = "/tmp/hr"
LON0, LON1, LAT0, LAT1 = 119.3, 122.1, 21.85, 25.4
PER = 3600
TS = 512
UA = {"User-Agent": "geo-taiwan-education/1.0"}


def download(url, path):
    if os.path.exists(path):
        return path
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=900) as r, open(path + ".part", "wb") as f:
            while True:
                b = r.read(1 << 22)
                if not b:
                    break
                f.write(b)
    except urllib.error.HTTPError as e:
        print("http", e.code, url, flush=True)
        return None
    os.replace(path + ".part", path)
    return path


def fabdem_tiles():
    """Return {(lat, lon): path} of FABDEM tiles, or {} if the archive cannot be fetched."""
    url = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/N20E120-N30E130_FABDEM_V1-2.zip"
    try:
        z = download(url, f"{TMP}/fab.zip")
    except Exception as e:
        print("FABDEM download failed:", e, flush=True)
        return {}
    if not z:
        return {}
    out = {}
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            b = os.path.basename(n)
            if not b.endswith(".tif"):
                continue
            # e.g. N23E120_FABDEM_V1-2.tif
            lat, lon = int(b[1:3]), int(b[4:7])
            if 21 <= lat <= 25 and 119 <= lon <= 121:
                p = f"{TMP}/{b}"
                if not os.path.exists(p):
                    with zf.open(n) as src, open(p, "wb") as dst:
                        dst.write(src.read())
                out[(lat, lon)] = p
    print("FABDEM tiles", sorted(out), flush=True)
    return out


def cop_tile(lat, lon):
    t = f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM"
    return download(f"https://copernicus-dem-30m.s3.amazonaws.com/{t}/{t}.tif", f"{TMP}/{t}.tif")


def mosaic():
    fab = fabdem_tiles()
    L0, L1, A0, A1 = 119, 122, 21, 26
    big = np.zeros(((A1 - A0) * PER, (L1 - L0) * PER), dtype=np.float32)
    src = {}
    for lat in range(A0, A1):
        for lon in range(L0, L1):
            p = fab.get((lat, lon))
            kind = "fabdem"
            if not p:
                p = cop_tile(lat, lon)
                kind = "copernicus"
            if not p:
                continue
            with rasterio.open(p) as ds:
                a = ds.read(1).astype(np.float32)
                nod = ds.nodata
            if nod is not None:
                a[a == nod] = 0
            a[a < -1000] = 0
            if a.shape != (PER, PER):
                raise SystemExit(f"tile shape {a.shape} at {lat},{lon}")
            r0 = (A1 - 1 - lat) * PER
            c0 = (lon - L0) * PER
            big[r0:r0 + PER, c0:c0 + PER] = a
            src[f"N{lat}E{lon}"] = kind
    r0 = int(round((A1 - LAT1) * PER)); r1 = int(round((A1 - LAT0) * PER))
    c0 = int(round((LON0 - L0) * PER)); c1 = int(round((LON1 - L0) * PER))
    return big[r0:r1, c0:c1].copy(), src


def land_mask(h, w):
    out = f"{TMP}/land1s.nc"
    subprocess.run(["gmt", "grdlandmask", f"-R{LON0}/{LON1}/{LAT0}/{LAT1}", "-I1s", "-r", "-Df", "-N0/1", f"-G{out}"], check=True)
    with Dataset(out) as d:
        z = np.array(d.variables["z"][:])
        lat = np.array(d.variables["lat"][:])
    if lat[0] < lat[-1]:
        z = z[::-1]
    if z.shape != (h, w):
        raise SystemExit(f"mask {z.shape} vs {(h, w)}")
    return z > 0.5


@njit(cache=True)
def priority_flood(code, w, h):
    n = w * h
    lev = np.full(n, 255, np.uint8)
    done = np.zeros(n, np.uint8)
    nxt = np.full(n, -1, np.int32)
    head = np.full(256, -1, np.int64)
    tail = np.full(256, -1, np.int64)
    for i in range(n):
        if code[i] == 0:
            done[i] = 1
            if tail[0] < 0:
                head[0] = i
            else:
                nxt[tail[0]] = i
            tail[0] = i
    for L in range(256):
        i = head[L]
        while i >= 0:
            lev[i] = L
            x = i % w
            y = i // w
            for k in range(4):
                if k == 0:
                    if x == 0:
                        continue
                    j = i - 1
                elif k == 1:
                    if x == w - 1:
                        continue
                    j = i + 1
                elif k == 2:
                    if y == 0:
                        continue
                    j = i - w
                else:
                    if y == h - 1:
                        continue
                    j = i + w
                if done[j]:
                    continue
                done[j] = 1
                c = code[j]
                l2 = c if c > L else L
                if tail[l2] < 0:
                    head[l2] = j
                else:
                    nxt[tail[l2]] = j
                tail[l2] = j
            i = nxt[i]
    return lev


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    elev, src = mosaic()
    h, w = elev.shape
    print("grid", w, h, flush=True)
    land = land_mask(h, w)
    e = np.maximum(elev, 0)
    code = np.where(e <= 100, 1 + np.clip(np.round(e * 2), 0, 200), 201 + np.clip(np.round((e - 100) / 75), 1, 54)).astype(np.uint8)
    code[~land] = 0
    lev = priority_flood(code.ravel(), w, h).reshape(h, w)
    print("flood done", flush=True)
    dy = 30.87
    dx = dy * np.cos(np.radians(23.6))
    gy, gx = np.gradient(e, dy, dx)
    nx, ny = -gx * 1.6, gy * 1.6
    L = np.sqrt(nx * nx + ny * ny + 1)
    s = 0.55 + 0.6 * ((nx * -0.5 + ny * 0.5 + 0.7071) / L)
    shade = np.clip((s - 0.4) / 0.8 * 255, 0, 255).astype(np.uint8)
    del gx, gy, nx, ny, L, s
    tiles = []
    for ty in range(0, (h + TS - 1) // TS):
        for tx in range(0, (w + TS - 1) // TS):
            y0, x0 = ty * TS, tx * TS
            c = code[y0:y0 + TS, x0:x0 + TS]
            if not c.any():
                continue
            rgb = np.zeros((TS, TS, 3), np.uint8)
            hh, ww = c.shape
            rgb[:hh, :ww, 0] = c
            rgb[:hh, :ww, 1] = lev[y0:y0 + TS, x0:x0 + TS]
            rgb[:hh, :ww, 2] = shade[y0:y0 + TS, x0:x0 + TS]
            Image.fromarray(rgb, "RGB").save(os.path.join(OUT, f"{tx}_{ty}.png"), optimize=True)
            tiles.append([tx, ty])
    meta = {"lon0": LON0, "lat1": LAT1, "cell_deg": 1 / PER, "tile": TS, "w": w, "h": h, "tiles": tiles, "sources": src,
            "shade": "B/255*0.8+0.4"}
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(meta, f, separators=(",", ":"))
    total = sum(os.path.getsize(os.path.join(OUT, f"{a}_{b}.png")) for a, b in tiles)
    print("tiles", len(tiles), "bytes", total, flush=True)


if __name__ == "__main__":
    main()
