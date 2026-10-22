"""把台電「各機組過去發電量」（每 10 分鐘、約最近三個月）整理成各能源每小時的平均發電量。
輸出 data/power/history.json：{start,end,types:[...],t0:"YYYY-MM-DDTHH",v:{類型:[每小時 MW...]}}"""
import json, urllib.request, collections, datetime, os, re
URL = 'https://service.taipower.com.tw/data/opendata/apply/file/d006010/001.json'
raw = urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (geo-taiwan classroom)'}), timeout=600).read()
d = json.loads(raw.decode('utf-8-sig'))['records']
acc = collections.defaultdict(lambda: collections.defaultdict(float))  # type -> datetime(10min) -> sum MW
for r in d['NET_P']:
    ty = re.sub(r'<[^>]*>', '', re.sub(r'\(.*?\)', '', r.get('FUEL_TYPE') or '')).strip()
    try: v = float(r['NET_P'])
    except Exception: continue
    acc[ty][r['DATETIME'][:16]] += v
times = sorted({t for a in acc.values() for t in a})
t0 = datetime.datetime.fromisoformat(times[0][:13] + ':00'); t1 = datetime.datetime.fromisoformat(times[-1][:13] + ':00')
nh = int((t1 - t0).total_seconds() // 3600) + 1
out = {}
for ty, a in acc.items():
    s = [0.0] * nh; c = [0] * nh
    for t, v in a.items():
        i = int((datetime.datetime.fromisoformat(t) - t0).total_seconds() // 3600); s[i] += v; c[i] += 1
    out[ty] = [round(s[i] / c[i]) if c[i] else None for i in range(nh)]
os.makedirs('data/power', exist_ok=True)
json.dump({'start': d.get('START_DATE'), 'end': d.get('END_DATE'), 't0': t0.strftime('%Y-%m-%dT%H'), 'v': out, 'src': URL},
          open('data/power/history.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(d.get('START_DATE'), d.get('END_DATE'), nh, list(out))
