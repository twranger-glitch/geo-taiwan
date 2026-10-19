"""Fetch Taiwan reservoir storage from the Water Resources Agency open data API.

Writes, under data/reservoirs/:
  latest.json  every reservoir's most recent reading
  daily.csv    one row per reservoir per day (the day's latest reading), kept forever
  hourly.csv   every reading, kept for the last 45 days (for watching a typhoon pass)

Storage percent = effective storage / effective capacity. Sources:
  WRA open data 41568 (daily operations: name, effective capacity)
  WRA open data 45501 (hourly status: effective storage, water level)
"""
import csv
import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

TW = timezone(timedelta(hours=8))
DAILY_URL = "https://opendata.wra.gov.tw/api/v2/51023e88-4c76-4dbc-bbb9-470da690d539?format=JSON"
HOURLY_URL = "https://opendata.wra.gov.tw/api/v2/2be9044c-6e44-4856-aad5-dd108c2e6679?format=JSON"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "reservoirs")
KEEP_HOURLY_DAYS = 45
REGION = {"1": "北部", "2": "中部", "3": "南部", "4": "東部", "5": "離島"}
ISLAND_IDS = {"31301"}  # 澎湖成功水庫


def tls_context():
    # Some government certificates lack fields that Python 3.13's strict mode requires.
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "geo-taiwan-education/1.0"})
            with urllib.request.urlopen(req, timeout=90, context=tls_context()) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as ex:
            if i == tries - 1:
                raise
            print(f"retry {url}: {ex}", file=sys.stderr)
            time.sleep(15 * (i + 1))


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    raise ValueError("unexpected payload shape")


def lower(row):
    return {str(k).strip().lower(): v for k, v in row.items()}


def num(v):
    try:
        f = float(str(v).replace(",", "").strip())
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def parse_time(v):
    if not v:
        return None
    s = str(v).strip().replace("/", "-")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            t = datetime.strptime(s[:25] if "%z" in fmt else s[:19], fmt)
            return t if t.tzinfo else t.replace(tzinfo=TW)
        except ValueError:
            continue
    return None


def latest_by_id(rows, time_key):
    best = {}
    for r in rows:
        rid = str(r.get("reservoiridentifier") or "").strip()
        t = parse_time(r.get(time_key))
        if not rid or t is None:
            continue
        if rid not in best or t > best[rid][0]:
            best[rid] = (t, r)
    return best


def main():
    now = datetime.now(TW)
    daily = latest_by_id([lower(r) for r in rows_of(get_json(DAILY_URL))], "datetime")
    hourly = latest_by_id([lower(r) for r in rows_of(get_json(HOURLY_URL))], "observationtime")
    out = []
    for rid in sorted(set(daily) | set(hourly)):
        _, d = daily.get(rid, (None, {}))
        h_t, h = hourly.get(rid, (None, {}))
        name = (d.get("reservoirname") or "").strip()
        cap = num(d.get("capacity"))
        sto = num(h.get("effectivewaterstoragecapacity"))
        if not name or not cap or cap <= 0 or sto is None or sto < 0 or h_t is None:
            continue
        if (now - h_t).days > 7:  # stale station
            continue
        pct = round(sto / cap * 100, 2)
        out.append({
            "id": rid, "name": name, "region": "離島" if rid in ISLAND_IDS else REGION.get(rid[:1], "其他"),
            "capacity": round(cap, 2), "storage": round(sto, 2), "percent": pct,
            "water_level": num(h.get("waterlevel")), "observed_at": h_t.isoformat(),
            "suspect": pct > 105,
        })
    if len(out) < 10:
        raise SystemExit(f"only {len(out)} reservoirs parsed; refusing to overwrite data")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": now.isoformat(timespec="seconds"), "count": len(out), "reservoirs": out},
                  f, ensure_ascii=False, separators=(",", ":"))

    # daily.csv: replace today's row for each reservoir with the newest reading
    fields = ["date", "id", "name", "capacity", "storage", "percent"]
    path = os.path.join(OUT, "daily.csv")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    keyed = {(r["date"], r["id"]): r for r in rows}
    for r in out:
        day = r["observed_at"][:10]
        keyed[(day, r["id"])] = {"date": day, "id": r["id"], "name": r["name"], "capacity": r["capacity"],
                                 "storage": r["storage"], "percent": r["percent"]}
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(keyed):
            w.writerow(keyed[k])

    # hourly.csv: append new readings, drop anything older than KEEP_HOURLY_DAYS
    hfields = ["time", "id", "percent", "storage"]
    hpath = os.path.join(OUT, "hourly.csv")
    hrows = []
    if os.path.exists(hpath):
        with open(hpath, encoding="utf-8") as f:
            hrows = list(csv.DictReader(f))
    hk = {(r["time"], r["id"]): r for r in hrows}
    for r in out:
        hk[(r["observed_at"], r["id"])] = {"time": r["observed_at"], "id": r["id"], "percent": r["percent"], "storage": r["storage"]}
    cutoff = (now - timedelta(days=KEEP_HOURLY_DAYS)).isoformat()
    with open(hpath, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hfields)
        w.writeheader()
        for k in sorted(hk):
            if k[0] >= cutoff:
                w.writerow(hk[k])
    print(f"{len(out)} reservoirs, newest reading {max(r['observed_at'] for r in out)}")


if __name__ == "__main__":
    main()
