"""抓台電「各機組發電量」開放資料（每 10 分鐘更新），整理成網頁用的小檔案。
輸出到目前目錄（data 分支的工作樹）：
  now.json            最新一筆：各機組類型的淨發電量與裝置容量，以及風力、太陽能機組明細
  day/YYYY-MM-DD.json 當天每 10 分鐘的各類型發電量
  days.json           有資料的日期清單（最近 14 天）
"""
import json, os, sys, urllib.request, datetime, re, glob
URL = 'https://service.taipower.com.tw/data/opendata/apply/file/d006001/001.json'
def num(s):
    try: return float(str(s).replace(',', '').strip())
    except Exception: return None
raw = urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (geo-taiwan classroom)'}), timeout=60).read()
d = json.loads(raw.decode('utf-8-sig'))
t = d.get('DateTime') or d.get('datetime')
rows = d.get('aaData') or []
types, units = {}, {}
for r in rows:
    ty = (r.get('機組類型') or '').strip(); nm = (r.get('機組名稱') or '').strip()
    if not ty or '小計' in nm or '合計' in nm or '總計' in nm: continue
    ty = re.sub(r'<[^>]*>', '', re.sub(r'\(.*?\)', '', ty)).strip()
    mw, cap = num(r.get('淨發電量(MW)')), num(r.get('裝置容量(MW)'))
    a = types.setdefault(ty, {'mw': 0.0, 'cap': 0.0, 'n': 0})
    if mw is not None: a['mw'] += mw
    if cap is not None: a['cap'] += cap
    a['n'] += 1
    if ty in ('風力', '太陽能'):
        units.setdefault(ty, []).append([nm, mw, cap, (r.get('備註') or '').strip()])
for a in types.values(): a['mw'] = round(a['mw'], 1); a['cap'] = round(a['cap'], 1)
now = {'t': t, 'types': types, 'units': units, 'src': URL}
json.dump(now, open('now.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
day = t[:10]; os.makedirs('day', exist_ok=True); p = f'day/{day}.json'
ser = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []
if not ser or ser[-1][0] != t:
    ser = [s for s in ser if s[0] != t] + [[t, {k: v['mw'] for k, v in types.items()}]]
    ser.sort(key=lambda s: s[0])
json.dump(ser, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
files = sorted(glob.glob('day/*.json'))
for f in files[:-14]: os.remove(f)
json.dump([os.path.basename(f)[:-5] for f in files[-14:]], open('days.json', 'w'), separators=(',', ':'))
print(t, {k: v['mw'] for k, v in types.items()})
