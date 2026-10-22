"""Build the small elevation grids used by sealevel.html.

Sources (downloaded inside GitHub Actions):
  Taiwan  Copernicus GLO-30 DEM (ESA, 1 arc-second), reduced to coarser cells with a low
          percentile so that buildings and trees count less (the DEM is a surface model);
          sea/land from OpenStreetMap land polygons (osmdata.openstreetmap.de, ODbL).
  World   GMT earth_relief 10 arc-minute (SRTM15+) and earth_mask 5 arc-minute.

Each grid is written as an 8-bit grayscale PNG plus a JSON description:
  0            ocean
  1 .. 201     land 0 .. 100 m in 0.5 m steps (land below sea level is stored as 0 m)
  202 .. 255   land above 100 m in 75 m steps
"""
import io
import json
import os
import ssl
import sys
import urllib.request

import numpy as np
from netCDF4 import Dataset
from PIL import Image
from scipy import ndimage
import rasterio

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "sealevel")
TMP = "/tmp/dem"
UA = {"User-Agent": "geo-taiwan-education/1.0"}
ctx = ssl.create_default_context()


def download(url, path):
    if os.path.exists(path):
        return path
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=600, context=ctx) as r, open(path + ".part", "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise
    os.replace(path + ".part", path)
    return path


def encode(elev, ocean):
    e = np.asarray(elev, dtype=np.float64)
    code = np.where(e <= 100, 1 + np.clip(np.round(e * 2), 0, 200), 201 + np.clip(np.round((e - 100) / 75), 1, 54))
    code = code.astype(np.uint8)
    code[ocean] = 0
    return code


def osm_land(lon0, lon1, lat0, lat1, cell):
    """Rasterise OpenStreetMap land polygons (coastline-derived) onto the grid."""
    import zipfile
    import fiona
    from rasterio import features
    from rasterio.transform import from_origin
    z = download("https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip", f"{TMP}/land.zip")
    d = f"{TMP}/land"
    if not os.path.exists(d):
        zipfile.ZipFile(z).extractall(d)
    shp = [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith(".shp")][0]
    w, h = int(round((lon1 - lon0) / cell)), int(round((lat1 - lat0) / cell))
    with fiona.open(shp) as src:
        geoms = [f["geometry"] for f in src.filter(bbox=(lon0, lat0, lon1, lat1))]
    return features.rasterize(((g, 1) for g in geoms), out_shape=(h, w),
                              transform=from_origin(lon0, lat1, cell, cell), fill=0, dtype="uint8").astype(bool)


def ocean_from_low(elev, thresh=0.3):
    low = elev <= thresh
    lab, n = ndimage.label(low)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    return np.isin(lab, list(edge))


def save(name, code, meta):
    Image.fromarray(code, mode="L").save(os.path.join(OUT, name + ".png"), optimize=True)
    meta = dict(meta, w=int(code.shape[1]), h=int(code.shape[0]),
                encoding="0 ocean; 1-201 land (c-1)/2 m; 202-255 land 100+(c-201)*75 m")
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(name, code.shape, os.path.getsize(os.path.join(OUT, name + ".png")), "bytes")


def cop_tile(lat, lon):
    t = f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM"
    return download(f"https://copernicus-dem-30m.s3.amazonaws.com/{t}/{t}.tif", f"{TMP}/{t}.tif")


def taiwan_grid(lon0, lon1, lat0, lat1, factor, pct):
    """Mosaic Copernicus 1" tiles over whole degrees, reduce by `factor`, crop to bounds."""
    per = 3600 // factor
    L0, L1, A0, A1 = int(np.floor(lon0)), int(np.ceil(lon1)), int(np.floor(lat0)), int(np.ceil(lat1))
    big = np.zeros(((A1 - A0) * per, (L1 - L0) * per), dtype=np.float32)
    for lat in range(A0, A1):
        for lon in range(L0, L1):
            p = cop_tile(lat, lon)
            if not p:
                print("no tile (sea)", lat, lon)
                continue
            with rasterio.open(p) as ds:
                a = ds.read(1).astype(np.float32)
            if a.shape != (3600, 3600):
                raise SystemExit(f"unexpected tile shape {a.shape} at {lat},{lon}")
            a[a < -1000] = 0
            blk = a.reshape(per, factor, per, factor).transpose(0, 2, 1, 3).reshape(per, per, factor * factor)
            red = np.percentile(blk, pct, axis=2) if factor > 1 else a
            r0 = (A1 - 1 - lat) * per
            c0 = (lon - L0) * per
            big[r0:r0 + per, c0:c0 + per] = red
    # crop: row 0 is the north edge at A1
    r0 = int(round((A1 - lat1) * per)); r1 = int(round((A1 - lat0) * per))
    c0 = int(round((lon0 - L0) * per)); c1 = int(round((lon1 - L0) * per))
    g = big[r0:r1, c0:c1]
    return g, 1.0 / per


def world_grid():
    rel = download("https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_10m_g.grd", f"{TMP}/relief10.grd")
    msk = download("https://oceania.generic-mapping-tools.org/server/earth/earth_mask/earth_mask_05m_g.grd", f"{TMP}/mask05.grd")
    with Dataset(rel) as d:
        z = np.array(d.variables["z"][:], dtype=np.float32)
        lat = np.array(d.variables["lat"][:])
    with Dataset(msk) as d:
        m = np.array(d.variables["z"][:], dtype=np.int16)
        mlat = np.array(d.variables["lat"][:])
    # gridline grids include both edges: drop the last row/column so sizes divide evenly
    if lat[0] < lat[-1]:
        z = z[::-1]
    if mlat[0] < mlat[-1]:
        m = m[::-1]
    z = z[:-1, :-1]                      # 1080 x 2160, 1/6 degree
    m = m[:-1, :-1]                      # 2160 x 4320, 1/12 degree
    z2 = z.reshape(540, 2, 1080, 2).mean(axis=(1, 3))
    ocean_frac = (m == 0).reshape(540, 4, 1080, 4).mean(axis=(1, 3))
    ocean = ocean_frac >= 0.5
    return z2, ocean


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    which = sys.argv[1:] or ["world", "tw", "tn"]
    for part in which:
        try:
            build(part)
        except Exception:
            import traceback
            traceback.print_exc()
            print("FAILED", part, flush=True)


def build(part):
    which = [part]
    if "world" in which:
        z, ocean = world_grid()
        save("world", encode(np.maximum(z, 0), ocean),
             {"lon0": -180, "lon1": 180, "lat0": -90, "lat1": 90, "cell_deg": 1 / 3,
              "source": "GMT earth_relief 10m (SRTM15+) and earth_mask 5m"})
    if "tw" in which:
        g, cell = taiwan_grid(119.3, 122.1, 21.85, 25.4, 12, 15)
        land = osm_land(119.3, 122.1, 21.85, 25.4, cell)
        save("tw", encode(np.maximum(g, 0), ~land),
             {"lon0": 119.3, "lon1": 122.1, "lat0": 21.85, "lat1": 25.4, "cell_deg": cell,
              "source": "Copernicus GLO-30 DEM, 12 arc-second cells, 15th percentile; coastline from OpenStreetMap land polygons"})
    if "tn" in which:
        g, cell = taiwan_grid(120.0, 120.8, 22.8, 23.45, 3, 10)
        land = osm_land(120.0, 120.8, 22.8, 23.45, cell)
        save("tn", encode(np.maximum(g, 0), ~land),
             {"lon0": 120.0, "lon1": 120.8, "lat0": 22.8, "lat1": 23.45, "cell_deg": cell,
              "source": "Copernicus GLO-30 DEM, 3 arc-second cells, 10th percentile; coastline from OpenStreetMap land polygons"})


if __name__ == "__main__":
    main()
