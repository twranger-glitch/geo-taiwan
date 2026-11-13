"""Build data/eq/eq.bin + eq.json from the CWA earthquake catalog (data.gov.tw dataset 97095).

Sources (Open Government Data License v1.0):
  E-A0073-002  history, one XML per year from 1990 to last year (ZIP)
  E-A0073-001  this year, January to last month (JSON), updated monthly

eq.bin: structure of arrays, little-endian, events sorted by time, N = meta['n']
  Uint32 t    minutes since 1990-01-01 00:00 (UTC+8)
  Uint16 lon  (lon-118)/6*65535
  Uint16 lat  (lat-20)/7*65535
  Uint16 dep  depth km * 10
  Uint8  mag  ML * 10
  Uint8  q    quality A=0 B=1 C=2 D=3
Usage: python scripts/fetch_eq.py [history.zip] [current.json]   (downloads when not given)
"""
import sys, os, io, re, json, zipfile, urllib.request, datetime as dt
import numpy as np

KEY = 'rdec-key-123-45678-011121314'   # public key published on data.gov.tw for this dataset
URL = 'https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{}?Authorization=' + KEY + '&downloadType=WEB&format={}'
UA = {'User-Agent': 'geo-taiwan-classroom/1.0 (+https://geo.twranger.com/)'}
T0 = dt.datetime(1990, 1, 1, tzinfo=dt.timezone(dt.timedelta(hours=8)))


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=600) as r:
        return r.read()


def rows_xml(s):
    for m in re.finditer(r'<EarthquakeInfo>(.*?)</EarthquakeInfo>', s, re.S):
        b = m.group(1)
        g = lambda k: re.search(f'<{k}[^>]*>([^<]*)</{k}>', b).group(1).strip()
        yield g('OriginTime'), g('EpicenterLongitude'), g('EpicenterLatitude'), g('FocalDepth'), g('LocalMagnitude'), g('Quality')


def rows_json(d):
    for e in d['cwaopendata']['Dataset']['Catalog']['EarthquakeInfo']:
        yield e['OriginTime'], e['EpicenterLongitude'], e['EpicenterLatitude'], e['FocalDepth'], e['LocalMagnitude'], e['Quality']


def main():
    hz = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else get(URL.format('E-A0073-002', 'ZIP'))
    cj = json.load(open(sys.argv[2], encoding='utf-8-sig')) if len(sys.argv) > 2 else json.loads(get(URL.format('E-A0073-001', 'JSON')).decode('utf-8-sig'))
    rows, years = {}, []
    z = zipfile.ZipFile(io.BytesIO(hz))
    for n in sorted(z.namelist()):
        if n.endswith('.xml'):
            years.append(int(re.search(r'(\d{4})', n).group(1)))
            for r in rows_xml(z.read(n).decode('utf-8-sig')):
                rows[r[:3]] = r
    nh = len(rows)
    cur = cj['cwaopendata']['Dataset']['Catalog']['CatalogInfo']
    for r in rows_json(cj):
        rows[r[:3]] = r
    ev = sorted(rows.values())
    t = np.array([(dt.datetime.fromisoformat(r[0]) - T0).total_seconds() // 60 for r in ev], dtype=np.uint32)
    lon = np.array([float(r[1]) for r in ev]); lat = np.array([float(r[2]) for r in ev])
    dep = np.array([float(r[3]) for r in ev]); mag = np.array([float(r[4]) for r in ev])
    q = np.array(['ABCD'.index(r[5]) if r[5] in 'ABCD' else 3 for r in ev], dtype=np.uint8)
    os.makedirs('data/eq', exist_ok=True)
    with open('data/eq/eq.bin', 'wb') as f:
        f.write(t.astype('<u4').tobytes())
        f.write(np.round((lon - 118) / 6 * 65535).clip(0, 65535).astype('<u2').tobytes())
        f.write(np.round((lat - 20) / 7 * 65535).clip(0, 65535).astype('<u2').tobytes())
        f.write(np.round(dep * 10).clip(0, 65535).astype('<u2').tobytes())
        f.write(np.round(mag * 10).clip(0, 255).astype(np.uint8).tobytes())
        f.write(q.tobytes())
    meta = {'n': len(ev), 'n_history': nh, 'first': ev[0][0], 'last': ev[-1][0],
            'history_years': [min(years), max(years)], 'current_period': [cur['StartTime'], cur['EndTime']],
            'current_records': int(cur['RecordNumber']), 'mag_range': cur['MagnitudeRange'],
            'region': cur['Region'], 'built': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'source': '交通部中央氣象署 地震目錄（政府資料開放平臺 97095：E-A0073-002、E-A0073-001），政府資料開放授權條款第 1 版'}
    json.dump(meta, open('data/eq/eq.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main()
