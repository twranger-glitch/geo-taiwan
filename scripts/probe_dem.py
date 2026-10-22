"""One-off probe: find downloadable elevation sources for the sea-level page."""
import csv, io, os, urllib.request, urllib.parse, ssl
ctx = ssl.create_default_context(); ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
UA = {"User-Agent": "geo-taiwan-education/1.0"}
out = []
def get(url, n=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        return r.status, dict(r.headers), (r.read(n) if n else r.read())
def head(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            out.append(f"OK {r.status} {r.headers.get('Content-Length')} {r.headers.get('Content-Type')} {url}")
    except Exception as e:
        out.append(f"FAIL {e} {url}")
try:
    url = "https://file.data.gov.tw/opendatafile/" + urllib.parse.quote("政府資料開放平臺資料集清單.csv")
    s, h, b = get(url)
    text = b.decode("utf-8-sig", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    out.append("header: " + " | ".join(rows[0]))
    for r in rows[1:]:
        j = " | ".join(r)
        if ("20公尺" in j or "數值地形" in j or "DTM" in j or "DEM" in j) and "內政部" in j:
            out.append("ROW: " + j[:1500])
except Exception as e:
    out.append(f"csv fail {e}")
for u in ["https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N23_00_E120_00_DEM/Copernicus_DSM_COG_30_N23_00_E120_00_DEM.tif",
          "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N23_00_E120_00_DEM/Copernicus_DSM_COG_10_N23_00_E120_00_DEM.tif",
          "https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_05m_g.grd",
          "https://sdsc-opentopography.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_05m_g.grd",
          "https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_10m_g.grd",
          "https://oceania.generic-mapping-tools.org/server/earth/earth_mask/earth_mask_05m_g.grd",
          "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc",
          "https://data.moi.gov.tw/MoiOD/default/20m_readme.doc"]:
    head(u)
os.makedirs("data/sealevel", exist_ok=True)
open("data/sealevel/_probe.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
